"""KNX042 eight-motor 1s LED sequence: strictly offline host/source regression.

No USB opening or GPIO access; FakeSerial simulates protocol.
"""
import contextlib
import importlib.util
import io
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
CODE = (ROOT / "tools/knx042_led_sequence/src/main.cpp").read_text(encoding="utf-8")
PIO = (ROOT / "tools/knx042_led_sequence/platformio.ini").read_text(encoding="utf-8")
HOST = ROOT / "tools/knx042_led_sequence_control.py"

class FakeSerial:
    instances = []

    def __init__(self):
        self.port = None
        self.baudrate = None
        self.timeout = None
        self.write_timeout = None
        self.dtr = False
        self.rts = False
        self.closed = False
        self.commands = []
        self.replies = [b"KNX042 LED SEQUENCE READY; USB ONLY KNX MOTORS DISCONNECTED\n"]
        self.active = False
        self.__class__.instances.append(self)

    def open(self):
        pass
    def close(self):
        self.closed = True
    def flush(self):
        pass
    def readline(self):
        return self.replies.pop(0) if self.replies else b""
    def write(self, data):
        self.commands.append(data)
        if data == b"STATUS\n":
            self.replies.append(
                (b"KNX042 STATUS armed=0 active=1 seq=1 step=1/16 round=1/5 completed=0\n"
                 if self.active else
                 b"KNX042 STATUS armed=0 active=0 seq=0 step=1/16 round=1/5 completed=0\n"))
        elif data == b"ARM LEDS_ONLY\n":
            self.replies.append(b"KNX042 ARMED 15s; NO KNX OR MOTORS\n")
        elif data == b"START ALL 5\n":
            self.active = True
            self.replies.append(b"KNX042 SEQ START rounds=5 on_ms=1000 off_ms=1000\n")
        elif data == b"STOP\n":
            self.active = False
            self.replies.append(b"KNX042 SEQ STOPPED\n")
        return len(data)


def load_host():
    spec = importlib.util.spec_from_file_location("knx042_led_sequence_test_host", HOST)
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    return host


class LedSequenceTests(unittest.TestCase):
    def test_exact_order_1s_with_finite_round_limit(self):
        for token in (
            "kMotorEnable[8] = {10, 11, 12, 13, 14, 15, 16, 17}",
            "kIn1Open = 18",
            "kIn2Close = 19",
            "kMaxRounds = 5",
            "kOnMs = 1000",
            "kOffMs = 1000",
            "kMaxRunMs = 180000",
            "stepIndex / 2",
            "(stepIndex % 2) == 0",
            "digitalWrite(kIn1Open, close ? LOW : HIGH)",
            "digitalWrite(kIn2Close, close ? HIGH : LOW)",
            "digitalWrite(kMotorEnable[motor], HIGH)",
            "phase == Phase::On",
            "phase == Phase::Off",
            "stepIndex == kStepsPerRound",
            "roundIndex >= kMaxRounds",
            "allPinsOff();",
            'strcmp(line, "START ALL 5")',
            'strcmp(line, "STATUS")',
            'strcmp(line, "STOP")',
            'strcmp(line, "ARM LEDS_ONLY")',
        ):
            self.assertIn(token, CODE)

    def test_no_automatic_sequence_on_boot_and_upload_disabled(self):
        setup=CODE.split("void setup() {",1)[1].split("void loop() {",1)[0]
        self.assertNotIn("startCurrentLedStep(", setup)
        self.assertNotIn("sequenceRunning = true;", setup)
        self.assertIn("allPinsOff();", setup)
        self.assertIn("digitalWrite(kKnxTx, LOW);", setup)
        self.assertIn("upload_protocol = custom", PIO)
        self.assertIn("upload_command = cmd /c exit 91", PIO)
        self.assertNotIn("knx.loop", CODE)
        self.assertNotIn("TPUart", CODE)

    def run_fake(self, action, with_flags=False):
        FakeSerial.instances.clear()
        fake_serial=types.ModuleType("serial")
        fake_serial.Serial=FakeSerial
        fake_tools=types.ModuleType("serial.tools")
        fake_ports=types.ModuleType("serial.tools.list_ports")
        fake_ports.comports=lambda: [types.SimpleNamespace(
            device="COM7",vid=0x2E8A,pid=0x000A,serial_number="E464401787522D33")]
        fake_serial.tools=fake_tools
        fake_tools.list_ports=fake_ports
        cmd=[action,"--port","COM7","--expect-serial","E464401787522D33"]
        if with_flags:
            cmd += ["--knx-disconnected","--motors-unplugged","--usb-only","--leds-current-limited"]
        with mock.patch.dict(sys.modules, {
            "serial":fake_serial,
            "serial.tools":fake_tools,
            "serial.tools.list_ports":fake_ports
        }):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code=load_host().run(cmd)
        self.assertEqual(code,0)
        self.assertEqual(len(FakeSerial.instances),1)
        self.assertTrue(FakeSerial.instances[0].closed)
        return FakeSerial.instances[0].commands, output.getvalue()

    def test_start_is_explicitly_armed_and_nothing_starts_automatically(self):
        commands, output=self.run_fake("start",True)
        self.assertEqual(commands,[b"STATUS\n",b"ARM LEDS_ONLY\n",b"START ALL 5\n"])
        self.assertIn('"nominal_total_seconds": 160', output)
        self.assertIn('"autostart_after_boot": false', output)

    def test_status_never_stops_sequence(self):
        commands,_=self.run_fake("status")
        self.assertEqual(commands,[b"STATUS\n"])

    def test_stop_is_explicit(self):
        commands,_=self.run_fake("stop")
        self.assertEqual(commands,[b"STOP\n",b"STATUS\n"])

    def test_start_requires_all_safety_flags(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                load_host().run(["start","--expect-serial","E464401787522D33"])
        self.assertEqual(cm.exception.code,2)


if __name__ == "__main__":
    unittest.main()
