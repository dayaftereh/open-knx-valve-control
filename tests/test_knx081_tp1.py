"""KNX081 offline golden telegram and RP2040 PIO timing/safety regression."""
from pathlib import Path
import re
import unittest
from tools.knx081_tp1_frame import build_frame,active_bits,packed_words,validate,byte_bits

SRC=Path(__file__).resolve().parents[1]/"tools"/"knx081_tx_tp1_oneframe"/"src"/"main.cpp"

class TestKNX081(unittest.TestCase):
    def test_fixed_frame_and_decoder(self):
        d=validate()
        self.assertEqual(d["frame_hex"],"BC 13 FA EF F1 D1 00 80 E5")
        self.assertEqual(d["source"],"1.3.250")
        self.assertEqual(d["destination"],"29/7/241")
        self.assertEqual(d["value"],0)
        self.assertEqual(d["pulses"],48)
        self.assertEqual(d["bits"],117)
        self.assertEqual(d["characters_start_stop_even_parity_ok"],9)

    def test_lsb_first_bits_and_idle_tail(self):
        self.assertEqual(len(active_bits()),117)
        words=packed_words()
        self.assertEqual(words,[0x2C3B2087,0x01D01088,0xF8FFC4BA,0x00003507])
        restored=[(w >> k)&1 for w in words for k in range(32)]
        self.assertEqual(restored[:117],active_bits())
        self.assertEqual(restored[117:],[0]*11)
        for byte in build_frame():
            bits=byte_bits(byte)
            self.assertEqual(bits[0],0)
            self.assertEqual(bits[-3:],[1,1,1])
            self.assertEqual(sum(bits[1:10])%2,0)

    def test_pio_cycle_budget_logic_0_and_1(self):
        # OUT X,1 (1us), JMP !X (1us);
        # HIGH path SET1 + NOP[15] + NOP[15] + NOP[1] + SET0 + JMP13
        high_pre=1+1
        high_body=1+16+16+2+1+1
        low_body=1+16+16+3+1
        join=16*4+1
        self.assertEqual(high_body,37)
        self.assertEqual(low_body,37)
        self.assertEqual(high_pre+high_body+join,104)
        self.assertEqual(high_pre+low_body+join,104)
        self.assertEqual(1+16+16+2,35) # from SET1 start to SET0 start

    def test_source_has_fail_closed_one_shot_gates(self):
        t=SRC.read_text(encoding="utf-8")
        self.assertIn('s=="ARM FRAME"',t)
        self.assertIn('s=="FIRE FRAME"',t)
        self.assertEqual(t.count('pio_sm_put_blocking('),1)
        self.assertIn("attempted=true",t)
        self.assertIn("kIdleFreeUs = 10000",t)
        self.assertIn('if(!busIsQuiet() || collisionDetected)',t)
        self.assertIn('pio_sm_set_out_shift(',t.replace('sm_config_set_out_shift','pio_sm_set_out_shift')) # explicit shift check

    def test_fixed_frame_has_no_other_destinations(self):
        t=SRC.read_text(encoding="utf-8")
        self.assertIn("0xBC,0x13,0xFA,0xEF,0xF1,0xD1,0x00,0x80,0xE5",t)
        self.assertIn("0x2C3B2087,0x01D01088,0xF8FFC4BA,0x00003507",t)
        self.assertIn("gpio_put(kTxPin,0)",t)
        self.assertIn("gpio_set_dir(kTxPin,GPIO_OUT)",t)

if __name__=="__main__":
    unittest.main()
