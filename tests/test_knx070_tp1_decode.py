"""Offline KNX070 TP1 pulse and frame decoder tests (no hardware/network)."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import knx070_tp1_decode as decoder


def pulses_for_byte(value: int, start: int, bit_us: int = 104) -> list[tuple[int, int, str | None]]:
    bits = [0]
    bits.extend((value >> i) & 1 for i in range(8))
    bits.append(sum(bits[1:9]) % 2)  # even total parity
    bits.append(1)
    return [(start + i * bit_us, start + i * bit_us + 35, None)
            for i, bit in enumerate(bits) if bit == 0]


def packet(raw: bytes, start: int = 100000,
           ack: int = 0xCC) -> list[tuple[int, int, str | None]]:
    result = []
    for i, byte in enumerate(raw):
        result.extend(pulses_for_byte(byte, start + i * 13 * 104))
    ack_start = start + ((len(raw) - 1) * 13 + 26) * 104
    result.extend(pulses_for_byte(ack, ack_start))
    return sorted(result)


class TestTP1Decoder(unittest.TestCase):
    def test_short_read_and_ack(self) -> None:
        raw = bytes.fromhex("BC 10 02 18 03 D1 00 00 9B")
        result = decoder.decode_group(packet(raw))
        self.assertEqual(result["frame"], list(raw))
        self.assertEqual(result["source"], "1.0.2")
        self.assertEqual(result["destination"], "3/0/3")
        self.assertEqual(result["service"], "GroupValueRead")
        self.assertEqual(result["quality"]["ack_code"], "CC")
        self.assertTrue(all(result["quality"].values()))

    def test_short_response_value(self) -> None:
        raw = bytes.fromhex("BC 12 0A 18 03 C1 00 41 C0")
        result = decoder.decode_group(packet(raw))
        self.assertEqual(result["service"], "GroupValueResponse")
        self.assertEqual(result["short_value"], 1)
        self.assertEqual(result["destination"], "3/0/3")

    def test_long_write_payload(self) -> None:
        raw = bytes.fromhex("BC 16 32 25 06 C3 00 80 19 18 06")
        result = decoder.decode_group(packet(raw))
        self.assertEqual(result["length_bytes"], 11)
        self.assertEqual(result["source"], "1.6.50")
        self.assertEqual(result["destination"], "4/5/6")
        self.assertEqual(result["service"], "GroupValueWrite")
        self.assertEqual(result["payload_hex"], "1918")
        self.assertTrue(result["quality"]["checksum_ok"])

    def test_checksum_mismatch_detected(self) -> None:
        raw = bytes.fromhex("BC 16 32 25 06 C3 00 80 19 18 07")
        result = decoder.decode_group(packet(raw))
        self.assertFalse(result["quality"]["checksum_ok"])
        self.assertTrue(result["quality"]["even_parity_ok"])

    def test_grouping_two_telegrams(self) -> None:
        short = bytes.fromhex("BC 10 02 18 03 D1 00 00 9B")
        long = bytes.fromhex("BC 16 32 25 06 C3 00 80 19 18 06")
        pulses = packet(short) + packet(long, start=200000)
        groups = decoder.group_pulses(sorted(pulses))
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(decoder.decode_group(groups[0])["frame"]), 9)
        self.assertEqual(len(decoder.decode_group(groups[1])["frame"]), 11)


if __name__ == "__main__":
    unittest.main()
