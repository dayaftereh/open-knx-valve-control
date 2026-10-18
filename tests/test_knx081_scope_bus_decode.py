"""KNX081 analogue BUS/A decoder tests using synthetic waveform, no hardware."""
from __future__ import annotations
import array
import json
import tempfile
from pathlib import Path
import unittest

from tools.knx081_tp1_frame import active_bits,byte_bits
from tools.knx081_scope_bus_decode import decode_analog_bus

ADC=32512
SCALE=50/ADC


class TestBusAnalogueDecode(unittest.TestCase):
    def make_capture(self,tmp:Path,frame_bits=None):
        baseline=31.
        origin=950
        total=17500
        a=array.array("h",[round(baseline/SCALE)]*total)
        bits=active_bits() if frame_bits is None else frame_bits
        for idx,bit in enumerate(bits):
            if bit:
                for j in range(origin+idx*104,origin+idx*104+35):
                    a[j]=round(23.6/SCALE)
        ack_offset=10*13*104
        for idx,bit in enumerate(byte_bits(0xCC)):
            if not bit:
                for j in range(origin+ack_offset+idx*104,
                               origin+ack_offset+idx*104+35):
                    a[j]=round(23.6/SCALE)
        a_path=tmp/"bus_a.s16le";a_path.write_bytes(a.tobytes())
        meta=tmp/"capture.json"
        meta.write_text(json.dumps({
            "path_a":str(a_path),"adc_max":ADC,
            "dt_us":1,"first_tx_sample":origin,
            "A_bus_idle_baseline_V":baseline, "pico_overflow":0
        }),encoding="utf-8")
        return meta

    def test_full_9byte_frame_and_ack_from_analogue(self):
        with tempfile.TemporaryDirectory() as directory:
            p=self.make_capture(Path(directory))
            result=decode_analog_bus(p)
            self.assertTrue(result["frame_and_ack_pass"],result)
            self.assertEqual(result["frame_hex"],"BC 13 FA EF F1 D1 00 80 E5")
            self.assertEqual(result["checksum_XOR"],"FF")
            self.assertEqual(result["ack_byte"],"CC")
            self.assertEqual(result["physical_active_pulses_total"],54)
            self.assertEqual(result["decoded"]["source"],"1.3.250")
            self.assertEqual(result["decoded"]["destination"],"29/7/241")

    def test_invalid_payload_checksum_is_rejected_even_with_ack(self):
        bits=active_bits()
        # Invert a data bit in the APDU field without updating checksum.
        bit_index=6*13+1
        bits[bit_index]=1-bits[bit_index]
        with tempfile.TemporaryDirectory() as directory:
            p=self.make_capture(Path(directory),bits)
            result=decode_analog_bus(p)
            self.assertFalse(result["frame_and_ack_pass"])
            self.assertFalse(result["frame_matches_intended"])
            self.assertNotEqual(result["checksum_XOR"],"FF")

    def test_one_transmission_token_in_host_driver(self):
        path=(Path(__file__).resolve().parents[1]/"tools"/
              "knx081_tx_tp1_oneframe"/"knx081_scope_send.py")
        source=path.read_text(encoding="utf-8")
        self.assertEqual(source.count('usb_send("FIRE FRAME")'),1)
        self.assertIn('fire_one_sent=True',source)
        self.assertIn('not args.confirm_lab_setup',source)


if __name__=="__main__":
    unittest.main()
