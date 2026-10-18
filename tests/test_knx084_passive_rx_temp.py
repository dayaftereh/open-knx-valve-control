"""KNX084 regression contract: TP receiver only + ATtiny temperature snapshots.

Static source guards complement PlatformIO compilation and live USB checks.
No tests actuate KNX, UPDI or motors.
"""
from __future__ import annotations
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
CPP=ROOT/"tools"/"knx084_passive_rx_temp"/"src"/"main.cpp"
INI=CPP.parent.parent/"platformio.ini"
CODE=CPP.read_text(encoding="utf-8")

class TestKNX084SafetyAndSensorBridge(unittest.TestCase):
    def test_stknx_tx_gpio0_only_written_low(self):
        self.assertIn("constexpr uint8_t kKnxTx=0;",CODE)
        self.assertIn("outputLow(kKnxTx);",CODE)
        self.assertIn("gpio_put(kKnxTx,0);",CODE)
        self.assertNotRegex(CODE,r"gpio_put\s*\(\s*kKnxTx\s*,\s*(1|true|HIGH)\s*\)")
        self.assertNotRegex(CODE,r"digitalWrite\s*\(\s*kKnxTx\s*,\s*HIGH\s*\)")
        self.assertNotIn("pio_sm_put_blocking",CODE)
        self.assertNotIn("Serial1.",CODE)
        self.assertNotIn("GroupValueWrite",CODE)

    def test_all_motor_enables_low_and_no_driver_implementation(self):
        self.assertIn("constexpr uint8_t kMotorEnables[8]={10,11,12,13,14,15,16,17};",CODE)
        self.assertIn("constexpr uint8_t kMotorDirection[2]={18,19};",CODE)
        self.assertIn("for(uint8_t pin:kMotorEnables)outputLow(pin);",CODE)
        self.assertIn("for(uint8_t pin:kMotorDirection)outputLow(pin);",CODE)
        self.assertIn("for(uint8_t pin:kMotorEnables)gpio_put(pin,0);",CODE)
        self.assertIn("for(uint8_t pin:kMotorDirection)gpio_put(pin,0);",CODE)
        self.assertNotRegex(CODE,r"(analogWrite|pwm_set|digitalWrite)\s*\([^;\n]*HIGH")
        self.assertNotRegex(CODE,r"gpio_put\s*\([^;\n]*,\s*(1|HIGH)\s*\)")

    def test_outputs_first_thing_setup_and_safety_refresh(self):
        setup=CODE.split("void setup() {",1)[1].split("void loop() {",1)[0]
        self.assertLess(setup.index("outputLow(kKnxTx);"),setup.index("Serial.begin"))
        self.assertLess(setup.index("forceAllInactive();"),setup.index("Serial2.begin"))
        self.assertIn("forceAllInactive();",CODE.split("void loop() {",1)[1])
        self.assertIn("gpio_put(pin,0)",CODE)

    def test_only_read_only_usb_command_whitelist(self):
        for command in ['"STATUS"','"TEMPS"','"RXSTATS"','"RXDUMP"','"HELP"']:
            self.assertIn(command,CODE)
        for forbidden in ('"ARM FRAME"','"FIRE FRAME"','"PULSE"','"M1"','"M2"','"MOTOR"'):
            self.assertNotIn(forbidden,CODE)
        self.assertIn("REFUSED_UNRECOGNIZED_OR_ACTUATING_COMMAND",CODE)

    def test_temperature_uart_and_validity(self):
        self.assertIn("kAttinyTx=8",CODE)
        self.assertIn("kAttinyRx=9",CODE)
        self.assertIn("kUartBaud=115200",CODE)
        self.assertIn("Serial2.setTX(kAttinyTx)",CODE)
        self.assertIn("Serial2.setRX(kAttinyRx)",CODE)
        self.assertIn("Serial2.availableForWrite()<=0",CODE)
        self.assertIn("TemperatureProtocol::encodeRequest",CODE)
        self.assertIn("TemperatureProtocol::Parser",CODE)
        self.assertIn("TemperatureProtocol::decodeSnapshot",CODE)
        self.assertIn("frame.sequence!=pendingSeq",CODE)
        self.assertIn("tempParser.feed(",CODE)
        self.assertIn("ch.fault==0",CODE)
        self.assertIn("temp_c=",CODE)
        self.assertIn('"NA"',CODE.replace('F("NA")','"NA"'))

    def test_four_channels_but_parse_nine(self):
        self.assertIn("n<4",CODE)
        self.assertIn("n<TemperatureProtocol::Channels",CODE)
        self.assertIn("NoSensor",CODE)
        self.assertIn("PowerOn85",CODE)
        self.assertIn("SampleStale",CODE)

    def test_passive_knx_rx_and_bounded_ring(self):
        self.assertIn("kKnxRx=1",CODE)
        self.assertIn("attachInterrupt(digitalPinToInterrupt(kKnxRx),isrKnxRx,CHANGE)",CODE)
        self.assertIn("kRxRingCapacity=4096",CODE)
        self.assertIn("if(next==rxRead)",CODE)
        self.assertIn("rxDump=true",CODE)
        self.assertIn("n<48",CODE)
        self.assertIn("RXSTATS edges=",CODE)

    def test_upload_requires_deliberate_uf2_flow(self):
        ini=INI.read_text(encoding="utf-8")
        self.assertIn("-DKNX084_RECEIVE_TEMP_ONLY=1",ini)
        self.assertIn("upload_protocol = custom",ini)
        self.assertIn("upload_command = cmd /c exit 91",ini)

    def test_usb_monitor_parses_status_and_prevents_ring_overflow(self):
        text=(ROOT/"tools"/"knx084_passive_rx_temp"/"knx084_live_monitor.py").read_text(encoding="utf8")
        self.assertIn("STATUS.match(line)",text)
        self.assertIn("nextdump=0.0",text)
        self.assertIn("nextdump=elapsed+8.0",text)
        self.assertIn('ser.write(b"RXDUMP\\n")',text)
        self.assertNotIn("FIRE FRAME",text)

    def test_offline_bus_decoder_accepts_pio_golden_rx_edges(self):
        import tempfile
        from tools.knx081_tp1_frame import active_bits,byte_bits
        from tools.knx084_passive_rx_temp.knx084_decode_capture import decode_log
        data=active_bits()
        # A valid 9-byte frame with its remote ACK, at 104us per bit.
        ack=byte_bits(0xCC)
        lines=[]
        origin=10000
        for i,bit in enumerate(data):
            if bit:
                t=origin+i*104
                lines.extend([f"KNX084 RXEDGE t_us={t} level=1",
                              f"KNX084 RXEDGE t_us={t+35} level=0"])
        for i,bit in enumerate(ack):
            if bit==0:
                t=origin+10*13*104+i*104
                lines.extend([f"KNX084 RXEDGE t_us={t} level=1",
                              f"KNX084 RXEDGE t_us={t+35} level=0"])
        lines.sort(key=lambda row:int(row.split("t_us=")[1].split(" ")[0]))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"rx_serial.txt"
            path.write_text("\n".join(lines)+"\n",encoding="utf8")
            result=decode_log(path)
            good=[x for x in result["decoded"] if
                  x.get("quality",{}).get("even_parity_ok") and
                  x.get("quality",{}).get("checksum_ok")]
            self.assertTrue(good,result)
            self.assertEqual(good[0]["source"],"1.3.250")
            self.assertEqual(good[0]["destination"],"29/7/241")

if __name__=="__main__":
    unittest.main()
