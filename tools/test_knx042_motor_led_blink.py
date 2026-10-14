"""Offline safety/command regression for configurable M1..M8 F/R blink (no COM ports)."""
import contextlib
import io
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knx042_motor_led_blink as blink


class FakePort:
    instances = []

    def __init__(self):
        self.commands = []
        self.lines = [
            b"KNX042 USB MOTOR-LED diagnostic; KNX/MOTORS DISCONNECTED ONLY\n"]
        self.dtr = False
        self.rts = False
        self.closed = False
        self.__class__.instances.append(self)

    def open(self):
        pass

    def close(self):
        self.closed = True

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def write(self, data):
        self.commands.append(data)
        replies = {
            b"STOP\n": [b"KNX042 STOPPED\n"],
            b"STATUS\n": [b"KNX042 STATUS armed=0 active=0\n"],
            b"ARM LEDS_ONLY\n": [b"KNX042 ARMED 15s; NO KNX OR MOTORS\n"],
            b"PULSE 2 F\n": [b"KNX042 PULSE M2 F 400ms\n", b"KNX042 AUTO-STOP\n"],
        }
        self.lines.extend(replies.get(data, []))
        return len(data)

    def flush(self):
        pass


class CloseLedBlinkTests(unittest.TestCase):
    def test_repeated_m2_forward_pulses_bounded_and_stopped(self):
        FakePort.instances.clear()
        serial = types.ModuleType("serial")
        serial.Serial = FakePort
        tools = types.ModuleType("serial.tools")
        list_ports = types.ModuleType("serial.tools.list_ports")
        list_ports.comports = lambda: [types.SimpleNamespace(
            device="COM7", vid=0x2E8A, pid=0x000A,
            serial_number="E464401787522D33")]
        tools.list_ports = list_ports
        serial.tools = tools
        flags = ["--port", "COM7", "--expect-serial",
                 "E464401787522D33", "--channel", "2", "--direction", "F", "--cycles", "2",
                 "--knx-disconnected", "--motors-unplugged",
                 "--usb-only", "--leds-current-limited"]
        with mock.patch.dict(sys.modules, {
            "serial": serial,
            "serial.tools": tools,
            "serial.tools.list_ports": list_ports
        }):
            with mock.patch.object(blink.time, "sleep", return_value=None):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(blink.run(flags), 0)
        obj = FakePort.instances[0]
        self.assertTrue(obj.closed)
        self.assertEqual(obj.commands, [
            b"STOP\n", b"STATUS\n",
            b"ARM LEDS_ONLY\n", b"PULSE 2 F\n",
            b"ARM LEDS_ONLY\n", b"PULSE 2 F\n",
            b"STOP\n", b"STATUS\n", b"STOP\n"
        ])
        self.assertIn('"pulses_completed": 2', output.getvalue())

    def test_requires_all_safety_flags(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as err:
                blink.run(["--expect-serial", "E464401787522D33"])
        self.assertEqual(err.exception.code, 2)

    def test_cycles_have_hard_upper_bound(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as err:
                blink.run(["--expect-serial", "E464401787522D33",
                           "--channel", "2", "--direction", "F", "--cycles", "121"])
        self.assertEqual(err.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
