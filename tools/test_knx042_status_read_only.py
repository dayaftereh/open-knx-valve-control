"""KNX042 host CLI regression: read-only STATUS may never turn off M1.

All tests use a mocked serial port. No USB port, hardware, KNX or motor is touched.
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
HOST = ROOT / "tools" / "knx042_motor_led_control.py"


class FakeSerial:
    instances = []

    def __init__(self):
        self.port = None
        self.baudrate = None
        self.timeout = None
        self.write_timeout = None
        self.dtr = None
        self.rts = None
        self.opened = False
        self.closed = False
        self.commands = []
        self.lines = [b"KNX042 USB MOTOR-LED diagnostic; KNX/MOTORS DISCONNECTED ONLY\n"]
        self.__class__.instances.append(self)

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def write(self, data):
        self.commands.append(data)
        acknowledgments = {
            b"STATUS\n": b"KNX042 STATUS armed=0 active=1\n",
            b"STOP\n": b"KNX042 STOPPED\n",
            b"ARM LEDS_ONLY\n": b"KNX042 ARMED 15s; NO KNX OR MOTORS\n",
            b"HOLD M1 F\n": b"KNX042 HOLD M1 F 180s\n",
        }
        if data in acknowledgments:
            self.lines.append(acknowledgments[data])
        return len(data)

    def flush(self):
        pass


def load_host():
    spec = importlib.util.spec_from_file_location("knx042_motor_led_host_for_test", HOST)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class ReadOnlyStatusTests(unittest.TestCase):
    def run_fake(self, action):
        host = load_host()
        FakeSerial.instances.clear()
        fake_serial = types.ModuleType("serial")
        fake_tools = types.ModuleType("serial.tools")
        fake_ports = types.ModuleType("serial.tools.list_ports")
        fake_serial.Serial = FakeSerial
        fake_ports.comports = lambda: [types.SimpleNamespace(
            device="COM7", vid=0x2E8A, pid=0x000A, serial_number="E464401787522D33")]
        fake_tools.list_ports = fake_ports
        fake_serial.tools = fake_tools
        args = [action, "--port", "COM7", "--expect-serial", "E464401787522D33"]
        if action == "hold":
            args += ["--channel", "1", "--direction", "F", "--knx-disconnected",
                     "--motors-unplugged", "--usb-only", "--leds-current-limited"]
        with mock.patch.dict(sys.modules, {
            "serial": fake_serial,
            "serial.tools": fake_tools,
            "serial.tools.list_ports": fake_ports,
        }):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(host.run(args), 0)
        self.assertEqual(len(FakeSerial.instances), 1)
        self.assertTrue(FakeSerial.instances[0].closed)
        return FakeSerial.instances[0].commands

    def test_status_is_truly_read_only_during_active_hold(self):
        self.assertEqual(self.run_fake("status"), [b"STATUS\n"])

    def test_manual_stop_sends_only_one_stop(self):
        self.assertEqual(self.run_fake("stop"), [b"STOP\n"])

    def test_hold_does_not_stop_after_success(self):
        self.assertEqual(self.run_fake("hold"), [
            b"STOP\n", b"ARM LEDS_ONLY\n", b"HOLD M1 F\n"])


if __name__ == "__main__":
    unittest.main()
