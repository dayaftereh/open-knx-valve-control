#!/usr/bin/env python3
"""KNX043 RX-only firmware and RP2040 BOOTSEL READ-ONLY verification.

This program never flashes, uploads, copies UF2, opens USB serial, or sends
KNXnet/IP/KNX TP frames. It can only inspect files and mounted device metadata.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import sys

HOME = Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl")
BUILD = HOME / "KNX043_HOME_KNX_BENCH_20261014"
IMAGES = {
    "rx_only_not_flashed": (
        "knx043-passive-rx-only-NOT-FLASHED.uf2",
        "8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f",
    ),
    "rollback_usb_diagnostic": (
        "rollback-knx042-led-diagnostic.uf2",
        "7e3dc4fe5cb92544558d3d42c71fbb54afb61c3bb29e21d9bb1676fb4961cb6d",
    ),
}
FIRST_MAGIC = 0x0A324655
SECOND_MAGIC = 0x9E5D5157
END_MAGIC = 0x0AB16F30
RP2040_FLASH_START = 0x10000000
RP2040_FLASH_END = 0x11000000


def check_uf2(path: Path, expected_hash: str) -> dict:
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_hash:
        raise ValueError(f"SHA256 mismatch for {path.name}: {actual}")
    if not data or len(data) % 512:
        raise ValueError(f"Non-512-byte UF2 image: {path.name}")
    blocks = len(data) // 512
    addresses = []
    for ix in range(blocks):
        block = data[ix * 512:(ix + 1) * 512]
        a, b, flags, address, payload, index, total, family = struct.unpack_from("<8I", block)
        end, = struct.unpack_from("<I", block, 508)
        if (a, b, end) != (FIRST_MAGIC, SECOND_MAGIC, END_MAGIC):
            raise ValueError(f"Invalid UF2 magic in {path.name} block {ix}")
        if (index, total) != (ix, blocks):
            raise ValueError(f"Invalid UF2 ordering in {path.name} block {ix}")
        if not 0 < payload <= 476:
            raise ValueError(f"Invalid UF2 payload in {path.name} block {ix}")
        if not RP2040_FLASH_START <= address < RP2040_FLASH_END:
            raise ValueError(f"UF2 targets wrong flash address {address:#x}")
        if address + payload > RP2040_FLASH_END:
            raise ValueError(f"UF2 payload exceeds RP2040 flash {address:#x}")
        addresses.append(address)
    return {
        "path": str(path),
        "hash_ok": True,
        "sha256": actual,
        "bytes": len(data),
        "blocks": blocks,
        "address_min": hex(min(addresses)),
        "address_max": hex(max(addresses)),
    }


def volume_label(letter: str) -> str:
    """Windows kernel API; strictly READ-ONLY filesystem metadata."""
    label = ctypes.create_unicode_buffer(256)
    serial = ctypes.c_ulong()
    max_component = ctypes.c_ulong()
    filesystem_flags = ctypes.c_ulong()
    filesystem = ctypes.create_unicode_buffer(256)
    if sys.platform != "win32":
        raise OSError("Volume label verification requires Windows")
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        f"{letter}:\\", label, len(label),
        ctypes.byref(serial), ctypes.byref(max_component),
        ctypes.byref(filesystem_flags), filesystem, len(filesystem),
    )
    if not ok:
        raise OSError(f"Unable to read volume label of {letter}:")
    return label.value


def check_bootsel(letter: str, label_reader=volume_label, info_root: Path | None = None) -> dict:
    if len(letter) != 1 or not letter.isalpha():
        raise ValueError("Boot volume argument must be exactly one letter")
    label = label_reader(letter.upper())
    if label != "RPI-RP2":
        raise ValueError(f"REFUSED: boot volume {letter}: label is {label!r}, not RPI-RP2")
    info_path = (info_root / "INFO_UF2.TXT") if info_root is not None else Path(f"{letter.upper()}:\\INFO_UF2.TXT")
    raw = info_path.read_text(encoding="utf-8")
    if "UF2 Bootloader" not in raw or "Model: Raspberry Pi RP2" not in raw or "Board-ID: RPI-RP2" not in raw:
        raise ValueError("REFUSED: Bootloader info is not Raspberry Pi RP2")
    return {
        "drive": f"{letter.upper()}:",
        "label": label,
        "bootloader_info_path": str(info_path),
        "RP2040_UF2_rom_verified": True,
    }


def inspect(build: Path = BUILD, boot_letter: str = "D", label_reader=volume_label) -> dict:
    checked = {}
    for name, (filename, sha) in IMAGES.items():
        checked[name] = check_uf2(build / filename, sha)
    target = check_bootsel(boot_letter, label_reader)
    return {
        "operation": "KNX043_BOOTSEL_FIRMWARE_READ_ONLY_PREFLIGHT",
        "status": "USB_BOOTSEL_AND_IMAGE_CHECKS_PASS_NO_BUS_APPROVAL",
        "board": target,
        "verified_images": checked,
        "knx_tp_bus_connected": "NOT_VERIFIED_BY_SOFTWARE",
        "motor_loads_disconnected": "NOT_VERIFIED_BY_SOFTWARE",
        "R17_removed_user_report": "CANNOT_ELECTRICALLY_VERIFY",
        "U9_U11_and_reset_power_safety": "NOT_CLEARED",
        "firmware_flashing_attempted": False,
        "knx_frame_sent": False,
        "warning": "The RX-only UF2 is NOT a KNX ETS application. Its GPIO0 LOW requires functioning application code; it is not reset/BOOTSEL fail-safe. Never connect KNX before electrical safety review.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=BUILD)
    parser.add_argument("--boot-letter", default="D")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.build, args.boot_letter)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"KNX043 BOOTSEL PREFLIGHT REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
