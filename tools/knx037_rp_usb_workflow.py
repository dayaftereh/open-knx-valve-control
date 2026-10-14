#!/usr/bin/env python3
"""KNX037: guarded RP2040 CDC workflow. No KNX, no ATtiny, no motor commands.

Default 'plan' has no hardware access. 'probe' queries local COM metadata only.
'listen' reads RP2040 USB-CDC heartbeat at 115200; never writes payload bytes.
'flash' (operator-controlled, explicit confirmations) performs ONE verified
RP2040 1200-baud USB-CDC bootloader touch followed by one picotool UF2 flash
and verify. Does NOT open CH340/UPDI COM4, switch RTS on CH340 or toggle GPIO.
Only use after independent confirmation of safe supply, KNX disconnected,
motors disconnected, and U9 post-overheat risks reviewed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEARTBEAT = "KNX036 USB-ONLY RP2040 ALIVE"
PICOTOOL = (Path.home() / ".platformio/packages/"
            "tool-picotool-rp2040-earlephilhower/picotool.exe")
VID_RPI = 0x2E8A
PID_CDC = frozenset({0x00C0, 0x000A})
PID_ROM = 0x0003
SHA = re.compile(r"[0-9a-fA-F]{64}")
COM = re.compile(r"COM([1-9][0-9]{0,3})", re.IGNORECASE)


class SafeUSBError(RuntimeError):
    pass


def require(cond: bool, reason: str) -> None:
    if not cond:
        raise SafeUSBError(reason)


def ports() -> list[Any]:
    # Imported lazily so default no-I/O plan has no USB or pyserial actions.
    from serial.tools import list_ports
    return list(list_ports.comports())


def find_app_port(port: str, expected_vidpid: str,
                  expected_serial: str, observed: list[Any]) -> Any:
    require(COM.fullmatch(port) is not None, "Expected explicit COMn port")
    require("2E8A:" in expected_vidpid.upper(), "Only RP2040 USB, not CH340")
    require(expected_vidpid.upper() in ("2E8A:00C0", "2E8A:000A"),
            "Refusing unexpected RP2040 VID/PID")
    valid = [p for p in observed if getattr(p, "vid", None) == VID_RPI and
             getattr(p, "pid", None) in PID_CDC]
    require(len(valid) == 1, "Require exactly ONE RP2040 application USB CDC")
    selected = valid[0]
    require(selected.device.upper() == port.upper(), "RP2040 COM port changed")
    actual = f"{selected.vid:04X}:{selected.pid:04X}"
    require(actual == expected_vidpid.upper(), "RP2040 VID:PID mismatch")
    require(bool(expected_serial) and
            str(selected.serial_number or "").upper() ==
            expected_serial.upper(), "RP2040 USB serial mismatch")
    return selected


def plan() -> dict[str, Any]:
    return {
        "operation": "PLAN_ONLY_NO_SERIAL_OPEN",
        "supported": ["plan", "probe", "listen", "flash"],
        "rp2040_app_vidpid": ["2E8A:00C0", "2E8A:000A"],
        "bootrom_vidpid": "2E8A:0003",
        "usb_heartbeat": HEARTBEAT,
        "baud": 115200,
        "flash_bootloader_touch": "RP2040 CDC 1200 baud DTR true->false only",
        "flash_only_with_all_electrical_confirmations": True,
        "no_ch340_or_updi_access": True,
        "knx_or_motor_commands": False,
        "automatic_upload_allowed": False,
    }


def read_heartbeat(port: str, seconds: float = 6.5) -> dict[str, Any]:
    import serial
    s = serial.Serial()
    s.port = port
    s.baudrate = 115200
    s.timeout = 0.35
    s.write_timeout = 0.35
    s.dtr = False
    s.rts = False
    try:
        s.open()
        # CDC host-ready handshake, never use CH340/ATtiny on this path.
        s.dtr = True
        begun = time.monotonic()
        data = bytearray()
        while time.monotonic() - begun < seconds and len(data) < 4096:
            data += s.read(128)
    finally:
        s.dtr = False
        if s.is_open:
            s.close()
    lines = data.decode("utf-8", errors="replace").splitlines()
    matches = [line for line in lines if HEARTBEAT in line]
    return {"port": port, "baud": 115200, "bytes": len(data),
            "heartbeat_count": len(matches), "sample": matches[:5],
            "pass": len(matches) >= 2, "com_payload_bytes_written": 0}


def touch_rom(port: str) -> None:
    import serial
    s = serial.Serial()
    s.port = port
    s.baudrate = 1200
    s.timeout = 0.25
    s.write_timeout = 0.25
    s.rts = False
    s.dtr = True
    try:
        s.open()
        time.sleep(0.15)
        s.dtr = False
    finally:
        if s.is_open:
            s.close()


def wait_for_rom(timeout: float = 8.0) -> None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        present = [p for p in ports() if
                   getattr(p, "vid", None) == VID_RPI and
                   getattr(p, "pid", None) == PID_ROM]
        if len(present) == 1:
            return
        require(len(present) == 0, "Multiple RP2040 ROM boots; abort")
        time.sleep(0.2)
    raise SafeUSBError("RP2040 did not enter ROM boot mode; no image uploaded")


def verify_image(path: str, expected_sha: str) -> Path:
    require(SHA.fullmatch(expected_sha) is not None, "Expected full UF2 SHA256")
    image = Path(path).resolve()
    require(image.suffix.lower() == ".uf2" and image.is_file(),
            "UF2 file missing")
    raw = image.read_bytes()
    require(1024 <= len(raw) <= 1024*1024 and len(raw) % 512 == 0,
            "Unexpected diagnostic UF2 file size")
    require(raw[:4] == bytes.fromhex("5546320A"), "UF2 magic missing")
    require(hashlib.sha256(raw).hexdigest() == expected_sha.lower(),
            "UF2 hash does not match approved diagnostic build")
    require(image.name == "rp2040-usb-only-diagnostic.uf2",
            "Only verified KNX036 diagnostic image is accepted")
    manifest = image.with_name("manifest.json")
    require(manifest.is_file(), "Expected KNX036 nonrelease build manifest")
    obj = json.loads(manifest.read_text(encoding="utf-8"))
    require(obj.get("schema") ==
            "openknx-valvecontrol/knx036-isolated-usb-diagnostic-v1",
            "Not a KNX036 diagnostic image")
    require(obj["images"][image.name]["sha256"] == expected_sha.lower(),
            "Manifest SHA does not match")
    require(obj.get("knx_bus_authorized") is False and
            obj.get("motor_authorized") is False,
            "Diagnostic image manifest safety contract invalid")
    return image


def flash(args: argparse.Namespace) -> dict[str, Any]:
    # All checks are before any serial open or 1200-baud reset.
    require(args.execute and args.confirm_no_knx and
            args.confirm_no_motors and args.confirm_safe_power and
            args.confirm_updi_cable_disconnected,
            "Explicit no-KNX/no-motors/protected-power/ATtiny-isolated confirmations required")
    require(PICOTOOL.is_file(), "Installed picotool binary missing")
    image = verify_image(args.uf2, args.expected_sha)
    app = find_app_port(args.port, args.expect_vidpid,
                        args.expect_serial, ports())
    require(app.device.upper() not in ("COM1", "COM3", "COM4"),
            "Protected host/CH340 serial port")
    touch_rom(app.device)
    wait_for_rom()
    cmd = [str(PICOTOOL), "load", "-v", "-x", str(image)]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                       text=True, errors="replace", timeout=35, check=False)
    require(p.returncode == 0 and "OK" in p.stdout,
            "picotool flash/verify failure (leave board disconnected from KNX): "
            + (p.stdout + p.stderr)[-500:])
    # USB VID/PID changes after Arduino-Pico new image; COM number may change.
    selected = None
    for _ in range(40):
        matches = [p for p in ports() if getattr(p, "vid", None) == VID_RPI
                   and getattr(p, "pid", None) == 0x000A]
        if len(matches) == 1:
            selected = matches[0]
            break
        time.sleep(0.2)
    require(selected is not None, "Flash verified but USB-CDC did not reappear")
    live = read_heartbeat(selected.device)
    require(live["pass"], "Diagnostic UF2 runs but heartbeat missing")
    return {"result": "FLASH_AND_HEARTBEAT_PASS", "initial_com": args.port,
            "new_com": selected.device, "program": image.name,
            "uf2_sha256": args.expected_sha.lower(),
            "heartbeats": live["heartbeat_count"], "sample": live["sample"],
            "com4_rts_touched": False, "knx_bus_used": False,
            "motors_used": False}


def cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("plan", "probe", "listen", "flash"),
                   nargs="?", default="plan")
    p.add_argument("--port")
    p.add_argument("--expect-vidpid")
    p.add_argument("--expect-serial")
    p.add_argument("--uf2")
    p.add_argument("--expected-sha")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--confirm-no-knx", action="store_true")
    p.add_argument("--confirm-no-motors", action="store_true")
    p.add_argument("--confirm-safe-power", action="store_true")
    p.add_argument("--confirm-updi-cable-disconnected", action="store_true")
    return p


def main() -> int:
    args = cli().parse_args()
    try:
        if args.action == "plan":
            print(json.dumps(plan(), indent=2))
            return 0
        if args.action == "probe":
            result = [{"com": p.device, "vidpid":
                       f"{p.vid:04X}:{p.pid:04X}" if p.vid else None,
                       "role": ("RP2040 app" if p.vid == VID_RPI and p.pid in PID_CDC
                                else "RP2040 ROM" if p.vid == VID_RPI and p.pid == PID_ROM
                                else "CH340 UPDI (NOT ACCESSED)" if
                                p.vid == 0x1A86 and p.pid == 0x7523
                                else "other")} for p in ports()]
            print(json.dumps({"ports": result, "hardware_io": "PnP-only"},
                             indent=2))
            return 0
        if args.action == "listen":
            require(args.port and args.expect_vidpid and args.expect_serial,
                    "listen requires port, VID/PID, and serial")
            selected = find_app_port(args.port, args.expect_vidpid,
                                     args.expect_serial, ports())
            value = read_heartbeat(selected.device)
            print(json.dumps(value, indent=2))
            return 0 if value["pass"] else 2
        require(args.port and args.expect_vidpid and args.expect_serial
                and args.uf2 and args.expected_sha,
                "flash requires exact COM+VID/PID+serial+UF2+SHA")
        print(json.dumps(flash(args), indent=2))
        return 0
    except (SafeUSBError, OSError, ValueError, KeyError,
            subprocess.TimeoutExpired) as exc:
        print("KNX037 ABORT:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
