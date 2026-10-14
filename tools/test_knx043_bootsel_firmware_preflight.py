"""Read-only KNX043 RP2040 UF2 + BOOTSEL preflash validation (offline tests)."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knx043_bootsel_firmware_preflight as p

BOOT_TEXT = "UF2 Bootloader v3.0\nModel: Raspberry Pi RP2\nBoard-ID: RPI-RP2\n"


def make_uf2(address=0x10000000, data_size=256) -> bytes:
    buf = bytearray(512)
    struct.pack_into("<8I", buf, 0,
                     p.FIRST_MAGIC, p.SECOND_MAGIC,
                     0, address, data_size, 0, 1, 0)
    struct.pack_into("<I", buf, 508, p.END_MAGIC)
    return bytes(buf)


class ReadonlyUf2Tests(unittest.TestCase):
    def test_valid_checksum_and_block(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "fw.uf2"
            f.write_bytes(make_uf2())
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            info = p.check_uf2(f, digest)
            self.assertTrue(info["hash_ok"])
            self.assertEqual(info["blocks"], 1)
            self.assertEqual(info["address_min"], "0x10000000")

    def test_invalid_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "fw.uf2"
            f.write_bytes(make_uf2())
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                p.check_uf2(f, "0" * 64)

    def test_wrong_memory_address_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "fw.uf2"
            f.write_bytes(make_uf2(0x20000000))
            sha = hashlib.sha256(f.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "wrong flash address"):
                p.check_uf2(f, sha)

    def test_bad_magic_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "fw.uf2"
            v = bytearray(make_uf2())
            v[0] = 0
            f.write_bytes(bytes(v))
            sha = hashlib.sha256(f.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "Invalid UF2 magic"):
                p.check_uf2(f, sha)

    def test_board_id_and_volume_label_both_required(self):
        with tempfile.TemporaryDirectory() as d:
            info = Path(d) / "INFO_UF2.TXT"
            info.write_text(BOOT_TEXT, encoding="utf-8")
            ok = p.check_bootsel("Q", lambda x: "RPI-RP2", Path(d))
            self.assertTrue(ok["RP2040_UF2_rom_verified"])
            with self.assertRaisesRegex(ValueError, "not RPI-RP2"):
                p.check_bootsel("Q", lambda x: "SOME_OTHER_DEVICE", Path(d))
            info.write_text("Other device", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Bootloader info"):
                p.check_bootsel("Q", lambda x: "RPI-RP2", Path(d))

    def test_live_script_contains_no_flash_or_bus_driver_api(self):
        source = (Path(__file__).resolve().parent / "knx043_bootsel_firmware_preflight.py").read_text(encoding="utf-8")
        self.assertNotIn("Copy-Item", source)
        self.assertNotIn("shutil.copy", source)
        self.assertNotIn("picotool load", source)
        self.assertNotIn("socket.socket(", source)
        self.assertNotIn("open(\"wb\"", source)
        self.assertNotIn("write_bytes(", source)

    def test_real_template_candidate_hashes_match(self):
        # No USB connection, flash access, or serial driver calls in this test.
        # The LLO Home and LLO Desktop archive directories differ.
        candidates = [
            p.BUILD,
            Path(r"C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX043_HOME_KNX_BENCH_20261014"),
        ]
        available = [folder for folder in candidates if
                     all((folder / name).is_file() for name, _ in p.IMAGES.values())]
        self.assertTrue(available, "Local KNX043 UF2 backup images are missing")
        for _, (name, sha) in p.IMAGES.items():
            checked = p.check_uf2(available[0] / name, sha)
            self.assertTrue(checked["hash_ok"])


if __name__ == "__main__":
    unittest.main()
