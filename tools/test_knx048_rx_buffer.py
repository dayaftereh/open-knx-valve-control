"""KNX048 regression: buffered STKNX RX-only edge diagnostics, no hardware access."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import knx043_rx_capture as capture

SOURCE = (ROOT / "tools" / "knx043_passive_rx" / "src" / "main.cpp").read_text(encoding="utf8")


class FakeChunkPort:
    def __init__(self, blocks):
        self.blocks = [bytes(b) for b in blocks]
        self.writes = []

    @property
    def in_waiting(self):
        return len(self.blocks[0]) if self.blocks else 0

    def read(self, n):
        if not self.blocks:
            return b""
        data = self.blocks[0][:n]
        self.blocks[0] = self.blocks[0][n:]
        if not self.blocks[0]:
            self.blocks.pop(0)
        return data

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def flush(self):
        pass


class MockCapturePort(FakeChunkPort):
    instances = []
    report_observed = 6
    report_dropped = 0

    def __init__(self):
        super().__init__([])
        self.port = None
        self.baudrate = None
        self.timeout = None
        self.write_timeout = None
        self.dtr = False
        self.rts = False
        self.opened = False
        self.lines = [b"KNX043 PASSIVE RX READY; TX_LOW NO KNX_TX_PULSES\n"]
        self.__class__.instances.append(self)

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def read(self, n):
        if not self.blocks:
            time.sleep(0.003)
        return super().read(n)

    def write(self, cmd):
        super().write(cmd)
        if cmd == b"STATUS\n" and not any(x == b"STOP\n" for x in self.writes):
            self.lines.append(b"KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0\n")
        elif cmd == b"ARM LISTEN_ONLY\n":
            self.lines.append(b"KNX043 ARMED LISTEN_ONLY 15s TX_LOW\n")
        elif cmd == b"START LISTEN\n":
            self.lines.append(b"KNX043 LISTENING RX_ONLY 120s TX_LOW\n")
            self.blocks.append(b"E 100 1\nE 135 0\nE 400 1\nE 435 0\n")
        elif cmd == b"STOP\n":
            self.blocks.append(b"E 700 1\nE 735 0\nKNX043 STOPPED RX_ONLY\n")
        elif cmd == b"STATUS\n":
            self.blocks.append(
                (f"KNX043 STATUS armed=0 listen=0 buffered=0 "
                 f"dropped={self.report_dropped} capacity=16383 "
                 f"high_water=81 observed={self.report_observed}\n").encode("ascii")
            )
        return len(cmd)


class Knx048BufferTests(unittest.TestCase):
    def test_large_ring_and_no_tx_or_autostart(self):
        self.assertIn("constexpr unsigned kRing = 16384;", SOURCE)
        self.assertIn('static_assert(sizeof(Edge) == 8', SOURCE)
        self.assertIn("++totalEdges;", SOURCE)
        self.assertIn("++lostEdges;", SOURCE)
        self.assertIn("highWater =", SOURCE)
        self.assertIn('"E %lu %u\\n"', SOURCE)
        self.assertIn("digitalWrite(kKnxTx, LOW)", SOURCE)
        self.assertNotIn("digitalWrite(kKnxTx, HIGH)", SOURCE)
        setup = SOURCE.split("void setup() {", 1)[1].split("void loop() {", 1)[0]
        self.assertNotIn("listenEnabled = true", setup)

    def test_legacy_and_compact_edges(self):
        self.assertEqual(capture.parse_edge("E 12345 1"), {"time_us": 12345, "level": 1})
        self.assertEqual(capture.parse_edge("KNX043 RX_EDGE time_us=12345 level=1"),
                         {"time_us": 12345, "level": 1})
        self.assertIsNone(capture.parse_edge("KNX043 STATUS listen=0"))
        self.assertIsNone(capture.parse_edge("E nan 1"))

    def test_status_and_incremental_counter(self):
        fields = capture.parse_status(
            "KNX043 STATUS armed=0 listen=0 buffered=0 dropped=3 "
            "capacity=16383 high_water=987 observed=1001"
        )
        self.assertEqual(fields["capacity"], 16383)
        self.assertEqual(fields["observed"], 1001)
        self.assertEqual(fields["dropped"], 3)
        stats = capture.EdgeStatistics()
        for t, level in [(0xFFFFFFF0, 1), (0x00000013, 0), (110, 1),
                         (145, 0), (200, 1), (235, 0)]:
            stats.add({"time_us": t, "level": level})
        self.assertEqual(stats.edge_count, 6)
        self.assertEqual(stats.pulse_count, 3)
        self.assertEqual(stats.nominal_count, 3)
        self.assertEqual(stats.pulse_widths_sample_us, [35, 35, 35])
        self.assertEqual(stats.sequence_errors, 0)

    def test_chunked_lines_and_control_ack_do_not_discard_edges(self):
        p = FakeChunkPort([b"E 100", b" 1\nE 135 0\nKNX043 STA",
                           b"TUS armed=0 listen=0 buffered=0 dropped=0\n"])
        reader = capture.BufferedSerialLines(p)
        seen = []
        ack = capture.send_collect(p, reader, "STATUS", "KNX043 STATUS",
                                   seen.append, seconds=1)
        self.assertEqual(p.writes, [b"STATUS\n"])
        self.assertEqual(seen, ["E 100 1", "E 135 0"])
        self.assertEqual(capture.parse_status(ack)["buffered"], 0)

    def test_bulk_parser_50000_edges_no_missing_records(self):
        # Synthetic byte stream exercises chunked parsing at high event counts;
        # it does not prove real MCU or Windows USB throughput.
        count = 50000
        raw = "".join(f"E {i * 35} {i & 1}\n" for i in range(count)).encode("ascii")
        port = FakeChunkPort([raw[i:i + 8192] for i in range(0, len(raw), 8192)])
        reader = capture.BufferedSerialLines(port)
        stats = capture.EdgeStatistics()
        for _ in range(count):
            line = reader.readline()
            self.assertTrue(line)
            edge = capture.parse_edge(line)
            self.assertIsNotNone(edge)
            stats.add(edge)
        self.assertEqual(stats.edge_count, count)
        self.assertEqual(stats.pulse_count, 24999)
        self.assertEqual(stats.sequence_errors, 0)
        self.assertFalse(port.blocks)

    def run_mock_capture(self, *, expected, dropped):
        MockCapturePort.instances.clear()
        MockCapturePort.report_observed = expected
        MockCapturePort.report_dropped = dropped
        serial = types.ModuleType("serial")
        serial.Serial = MockCapturePort
        tools = types.ModuleType("serial.tools")
        ports = types.ModuleType("serial.tools.list_ports")
        ports.comports = lambda: [types.SimpleNamespace(
            device="COM8", vid=0x2E8A, pid=0x000A,
            serial_number="E464401787522D33"
        )]
        serial.tools = tools
        tools.list_ports = ports
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.jsonl"
            with mock.patch.dict(sys.modules, {
                "serial": serial, "serial.tools": tools,
                "serial.tools.list_ports": ports
            }), mock.patch.object(capture, "require_physical_gate", return_value=None):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = capture.run([
                        "capture", "--port", "COM8",
                        "--expect-serial", "E464401787522D33",
                        "--seconds", "1", "--output", str(path),
                        "--independent-electrical-review-complete",
                        "--isolated-knx-testbus",
                    ])
            entries = [json.loads(line) for line in path.read_text().splitlines()]
        return rc, entries, MockCapturePort.instances

    def test_simulated_six_edges_and_drain_complete(self):
        rc, entries, ports = self.run_mock_capture(expected=6, dropped=0)
        self.assertEqual(rc, 0)
        self.assertEqual(sum(1 for e in entries if e["kind"] == "edge"), 6)
        s = entries[-1]
        self.assertEqual(s["edge_count"], 6)
        self.assertEqual(s["pulse_count"], 3)
        self.assertTrue(s["pc_delivery_count_verified"])
        self.assertTrue(s["ring_and_usb_drained"])
        self.assertTrue(s["capture_coverage_complete"])
        self.assertFalse(ports[0].opened)
        self.assertEqual(ports[0].writes,
                         [b"STATUS\n", b"ARM LISTEN_ONLY\n", b"START LISTEN\n",
                          b"STOP\n", b"STATUS\n"])

    def test_simulated_overflow_marks_capture_incomplete(self):
        rc, entries, _ = self.run_mock_capture(expected=7, dropped=1)
        self.assertEqual(rc, 2)
        s = entries[-1]
        self.assertEqual(s["firmware_dropped"], 1)
        self.assertTrue(s["pc_delivery_count_verified"])
        self.assertFalse(s["capture_coverage_complete"])


if __name__ == "__main__":
    unittest.main()
