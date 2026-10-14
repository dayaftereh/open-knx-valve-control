"""KNX043 offline regression for receive-only USB capture and RP2040 GPIO contract."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import knx043_home_knx_preflight as gate
import knx043_rx_capture as capture

SOURCE = (ROOT/"tools"/"knx043_passive_rx"/"src"/"main.cpp").read_text(encoding="utf-8")
PIO = (ROOT/"tools"/"knx043_passive_rx"/"platformio.ini").read_text(encoding="utf-8")


class FakePort:
    instances: list["FakePort"] = []

    def __init__(self):
        self.port=None
        self.baudrate=None
        self.timeout=None
        self.write_timeout=None
        self.dtr=False
        self.rts=False
        self.closed=False
        self.commands=[]
        self.lines=[b"KNX043 PASSIVE RX READY; TX_LOW NO KNX_TX_PULSES\n"]
        self.__class__.instances.append(self)

    def open(self):
        pass

    def close(self):
        self.closed=True

    def flush(self):
        pass

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def write(self, command):
        self.commands.append(command)
        responses={
            b"STATUS\n": b"KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0\n",
            b"STOP\n": b"KNX043 STOPPED RX_ONLY\n",
            b"ARM LISTEN_ONLY\n": b"KNX043 ARMED LISTEN_ONLY 15s TX_LOW\n",
            b"START LISTEN\n": b"KNX043 LISTENING RX_ONLY 120s TX_LOW\n",
        }
        if command in responses: self.lines.append(responses[command])
        return len(command)


class Knx043RxTests(unittest.TestCase):

    def test_compile_only_rx_source_does_not_create_tx_or_motor_activity(self):
        self.assertIn("kKnxTx = 0", SOURCE)
        self.assertIn("kKnxRx = 1", SOURCE)
        self.assertIn("kMotorEnables[8] = {10, 11, 12, 13, 14, 15, 16, 17}", SOURCE)
        self.assertIn("digitalWrite(kKnxTx, LOW)", SOURCE)
        self.assertNotIn("digitalWrite(kKnxTx, HIGH)", SOURCE)
        self.assertNotIn("Serial1.begin", SOURCE)
        self.assertNotIn("#include <TPUart", SOURCE)
        self.assertIn("pinMode(kKnxRx, INPUT)", SOURCE)
        self.assertIn("kMaxListenMs = 120000", SOURCE)
        self.assertIn("strcmp(line, \"ARM LISTEN_ONLY\")", SOURCE)
        self.assertIn("strcmp(line, \"START LISTEN\")", SOURCE)
        self.assertIn("strcmp(line, \"STOP\")", SOURCE)
        self.assertIn("strcmp(line, \"STATUS\")", SOURCE)
        self.assertIn("upload_protocol = custom", PIO)
        self.assertIn("upload_command = cmd /c exit 91", PIO)
        setup=SOURCE.split("void setup() {",1)[1].split("void loop() {",1)[0]
        self.assertIn("allOutputsInactive();",setup)
        self.assertNotIn("listenEnabled = true",setup)

    def test_rising_and_falling_edges_widths(self):
        text="KNX043 RX_EDGE time_us=25100 level=1"
        self.assertEqual(capture.parse_edge(text),{"time_us":25100,"level":1})
        self.assertIsNone(capture.parse_edge("KNX043 STATUS armed=0"))
        widths=capture.pulse_widths([
            {"time_us":25100,"level":1},
            {"time_us":25135,"level":0},
            {"time_us":25932,"level":1},
            {"time_us":25966,"level":0},
        ])
        self.assertEqual(widths,[35,34])

    def test_us_counter_rollover(self):
        self.assertEqual(capture.pulse_widths([
            {"time_us":0xFFFFFFF0,"level":1},
            {"time_us":0x00000013,"level":0},
        ]),[35])

    def test_capture_requires_independent_hardware_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"gate.json"
            p.write_text(json.dumps({
                "schema":gate.SCHEMA,
                "observations":{key:True for key in gate.REQUIRED_PHYSICAL_GATES}
            }),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"independent"):
                capture.require_physical_gate(p,False,False)
            # Complete checklist AND explicit operator review flags required.
            capture.require_physical_gate(p,True,True)

    def test_real_template_blocks_capture(self):
        path=ROOT/"docs"/"KNX043_HOME_KNX_GATE.json"
        with self.assertRaisesRegex(ValueError, "hardware gate not complete"):
            capture.require_physical_gate(path,True,True)

    def fake_run(self, action):
        FakePort.instances.clear()
        serial=types.ModuleType("serial")
        serial.Serial=FakePort
        tools=types.ModuleType("serial.tools")
        ports=types.ModuleType("serial.tools.list_ports")
        ports.comports=lambda:[types.SimpleNamespace(
            device="COM7",vid=0x2E8A,pid=0x000A,
            serial_number="E464401787522D33")]
        tools.list_ports=ports
        serial.tools=tools
        with mock.patch.dict(sys.modules,{
            "serial":serial,"serial.tools":tools,"serial.tools.list_ports":ports
        }):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                rc=capture.run([action,"--port","COM7",
                    "--expect-serial","E464401787522D33"])
        self.assertEqual(rc,0)
        return list(FakePort.instances),output.getvalue()

    def test_status_does_not_transmit_stop_or_arming(self):
        ports,out=self.fake_run("status")
        self.assertEqual(len(ports),1)
        self.assertTrue(ports[0].closed)
        self.assertEqual(ports[0].commands,[b"STATUS\n"])
        self.assertIn("read_only_status",out)

    def test_stop_only_sends_explicit_stop(self):
        ports,_=self.fake_run("stop")
        self.assertEqual(ports[0].commands,[b"STOP\n"])

    def test_probe_does_not_open_usb(self):
        ports,out=self.fake_run("probe")
        self.assertEqual(ports,[])
        self.assertIn('"opened": false',out)


if __name__=="__main__":
    unittest.main()
