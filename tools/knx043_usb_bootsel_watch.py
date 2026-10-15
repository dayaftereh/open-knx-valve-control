"""KNX043 read-only Windows USB enumeration monitor for BOOTSEL tests.

Observes RP2040 CDC USB VID:PID 2E8A:000A, ROM BOOTSEL mass storage
volume RPI-RP2 (USB VID:PID 2E8A:0003), and the current COM port.
The script never opens the serial port, writes USB media, or flashes.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
from serial.tools import list_ports


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.GetLogicalDrives.restype = wintypes.DWORD
kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
kernel.GetDriveTypeW.restype = wintypes.UINT
kernel.GetVolumeInformationW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD,
]
kernel.GetVolumeInformationW.restype = wintypes.BOOL


def read_volumes() -> list[dict]:
    mask = kernel.GetLogicalDrives()
    records = []
    for i in range(26):
        if not mask & (1 << i):
            continue
        drive = chr(ord("A") + i) + ":\\"
        dtype = kernel.GetDriveTypeW(drive)
        if dtype not in (2, 3):
            continue
        label = ctypes.create_unicode_buffer(260)
        serial = wintypes.DWORD(0)
        max_component = wintypes.DWORD(0)
        flags = wintypes.DWORD(0)
        filesystem = ctypes.create_unicode_buffer(64)
        if kernel.GetVolumeInformationW(
            drive, label, len(label), ctypes.byref(serial),
            ctypes.byref(max_component), ctypes.byref(flags),
            filesystem, len(filesystem)
        ):
            if label.value.upper() == "RPI-RP2":
                records.append({"drive": drive[:2], "label": label.value, "volume_serial": int(serial.value)})
    return sorted(records, key=lambda x: x["drive"])


def snapshot() -> dict:
    app_ports = []
    rom_ports = []
    for p in list_ports.comports():
        if p.vid != 0x2E8A:
            continue
        observed = {
            "port": p.device, "description": p.description,
            "vid": p.vid, "pid": p.pid, "serial": p.serial_number,
        }
        if p.pid == 0x000A:
            app_ports.append(observed)
        elif p.pid == 0x0003:
            # Windows can expose the ROM Boot interface as COM6 without
            # mounting RPI-RP2: this is NOT a CDC app reconnect.
            rom_ports.append(observed)
    return {
        "rp2040_cdc_ports": sorted(app_ports, key=lambda x: x["port"]),
        "rp2040_rom_boot_ports": sorted(rom_ports, key=lambda x: x["port"]),
        "rpi_rp2_boot_volume": read_volumes(),
    }


def atomic_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run() -> None:
    parser = argparse.ArgumentParser(description="Read-only RP2040 USB CDC/BOOTSEL monitor")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--duration-sec", type=int, default=1900)
    parser.add_argument("--interval-sec", type=float, default=0.4)
    args = parser.parse_args()
    if not 60 <= args.duration_sec <= 4000 or not 0.2 <= args.interval_sec <= 5:
        parser.error("Out-of-range watch interval or duration")
    folder = args.output_dir
    if folder.exists():
        parser.error(f"Refusing to reuse USB watcher output folder: {folder}")
    folder.mkdir(parents=True, exist_ok=False)
    events_file = folder / "usb_events.jsonl"
    state_file = folder / "usb_watch_state.json"
    stop_file = folder / "stop-request.txt"
    start = datetime.now(timezone.utc)
    deadline = start + timedelta(seconds=args.duration_sec)
    events = 0
    previous = None
    found_cdc_detach = False
    found_rom_mass_storage = False
    found_rom_boot_pid_0003 = False
    found_cdc_reconnect = False
    try:
        while True:
            snap = snapshot()
            if snap != previous:
                item = {"utc": timestamp(), "event": "USB_STATE_CHANGE", **snap}
                with events_file.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(item, ensure_ascii=False) + "\n")
                    stream.flush()
                print("USB_EVENT", json.dumps(item, ensure_ascii=True), flush=True)
                events += 1
                if previous is not None:
                    if previous["rp2040_cdc_ports"] and not snap["rp2040_cdc_ports"]:
                        found_cdc_detach = True
                    if found_cdc_detach and snap["rp2040_cdc_ports"]:
                        found_cdc_reconnect = True
                if snap["rpi_rp2_boot_volume"]:
                    found_rom_mass_storage = True
                if snap["rp2040_rom_boot_ports"]:
                    found_rom_boot_pid_0003 = True
                previous = snap
            now = datetime.now(timezone.utc)
            if stop_file.exists() or now >= deadline:
                reason = "STOP_REQUESTED" if stop_file.exists() else "WINDOW_EXPIRED"
                atomic_json(state_file, {
                    "status": reason, "started_utc": start.isoformat(),
                    "deadline_utc": deadline.isoformat(),
                    "ended_utc": now.isoformat(), "event_count": events,
                    "RP2040_CDC_detach_observed": found_cdc_detach,
                    "RPI_RP2_ROM_mass_storage_seen": found_rom_mass_storage,
                    "RP2040_ROM_BOOT_USB_PID_0003_seen": found_rom_boot_pid_0003,
                    "RP2040_CDC_reconnect_seen": found_cdc_reconnect,
                    "last_snapshot": previous,
                    "interpretation": "Enumeration evidence only; does not measure electrical KNX_TX and never flashes ROM.",
                })
                print("WATCH_END", reason, flush=True)
                return
            atomic_json(state_file, {
                "status": "MONITORING", "started_utc": start.isoformat(),
                "deadline_utc": deadline.isoformat(),
                "last_checked_utc": now.isoformat(),
                "event_count": events,
                "RP2040_CDC_detach_observed": found_cdc_detach,
                "RPI_RP2_ROM_mass_storage_seen": found_rom_mass_storage,
                "RP2040_ROM_BOOT_USB_PID_0003_seen": found_rom_boot_pid_0003,
                    "RP2040_CDC_reconnect_seen": found_cdc_reconnect,
                "last_snapshot": previous,
                "read_only_no_firmware_or_mass_storage_writes": True,
            })
            time.sleep(args.interval_sec)
    except Exception as exc:
        atomic_json(state_file, {"status": "ERROR", "error": str(exc), "event_count": events, "utc": timestamp()})
        raise


if __name__ == "__main__":
    run()
