#!/usr/bin/env python3
"""Read-only ATtiny3216/RP2040 temperature-interface audit for PCB V1.2.

Reports design/firmware disagreements as warnings; --strict fails until
sensor pins and communication protocol are implemented. No hardware I/O.
Pin facts were reconciled with Microchip ATtiny3216 SOIC-20 and the
installed megaTinyCore variants/txy6/pins_arduino.h (2026-10-10).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "schematic" / "pcb_knx-valve-control_v1.2.json"
CONFIG = ROOT / "src" / "temperature" / "config.hpp"
TEMP = ROOT / "src" / "temperature" / "temperature.cpp"
SPI = ROOT / "src" / "temperature" / "spi-slave.cpp"
MAIN = ROOT / "src" / "temperature" / "main.cpp"
RP_MAIN = ROOT / "src" / "controller" / "main.cpp"

# Datasheet: SOIC-20 physical pin -> port. A pin number is NOT an Arduino pin.
AT_TINY_SOIC20 = {
    1: "VDD", 2: "PA4", 3: "PA5", 4: "PA6", 5: "PA7",
    6: "PB5", 7: "PB4", 8: "PB3", 9: "PB2", 10: "PB1",
    11: "PB0", 12: "PC0", 13: "PC1", 14: "PC2", 15: "PC3",
    16: "PA0", 17: "PA1", 18: "PA2", 19: "PA3", 20: "GND",
}

# megaTinyCore / variants/txy6/pins_arduino.h: Arduino digital number -> port.
ARDUINO_PORT = {
    0: "PA4", 1: "PA5", 2: "PA6", 3: "PA7", 4: "PB5",
    5: "PB4", 6: "PB3", 7: "PB2", 8: "PB1", 9: "PB0",
    10: "PC0", 11: "PC1", 12: "PC2", 13: "PC3",
    14: "PA1", 15: "PA2", 16: "PA3", 17: "PA0",
}


def read_pads(reference: str, shape: list[str]) -> dict[int, str]:
    for record in shape:
        if not record.startswith("LIB~"):
            continue
        chunks = record.split("#@$")
        name = next((
            chunk.split("~")[10] for chunk in chunks
            if chunk.startswith("TEXT~P~") and len(chunk.split("~")) > 10
        ), "")
        if name != reference:
            continue
        result = {}
        for chunk in chunks:
            if not chunk.startswith("PAD~"):
                continue
            data = chunk.split("~")
            if len(data) > 8 and data[8].isdigit():
                result[int(data[8])] = data[7]
        return result
    raise RuntimeError(f"PCB component not found: {reference}")


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--strict", action="store_true",
                     help="fail if there are known firmware/pin mismatches")
    args = cli.parse_args()
    layout = json.loads(PCB.read_text(encoding="utf-8-sig"))
    tiny = read_pads("U25", layout["shape"])
    rp = read_pads("U18", layout["shape"])
    config = CONFIG.read_text(encoding="utf-8")
    main_src = MAIN.read_text(encoding="utf-8")
    sampler = TEMP.read_text(encoding="utf-8")
    spi_code = SPI.read_text(encoding="utf-8")
    rp_code = RP_MAIN.read_text(encoding="utf-8")
    mismatches = []
    print("ATtiny SOIC-20: sensor PCB nets versus configured Arduino pins")
    for sensor in range(9):
        signal = f"T{sensor}"
        board_pin = next((p for p, net in tiny.items() if net == signal), None)
        actual_port = AT_TINY_SOIC20.get(board_pin)
        match = re.search(r"\bT" + str(sensor) +
                          r"\s*=\s*(\d+)\s*;", config)
        configured = int(match.group(1)) if match else None
        firmware_port = ARDUINO_PORT.get(configured)
        ok = actual_port is not None and actual_port == firmware_port
        print(f"  {signal}: PCB pin {board_pin}={actual_port}, "
              f"firmware {configured}={firmware_port}, "
              f"{'MATCH' if ok else 'MISMATCH'}")
        if not ok:
            mismatches.append(signal)

    expected_links = {
        "T_TX": (18, 11),  # ATtiny PA2 -> RP2040 GPIO8 (TX from RP)
        "T_RX": (17, 12),  # ATtiny PA1 -> RP2040 GPIO9 (RX on RP)
        "T_INT": (14, 34),
        "CS": (2, 32),
    }
    for signal, (at_pin, rp_pin) in expected_links.items():
        ok = tiny.get(at_pin) == signal and rp.get(rp_pin) == signal
        print(f"  link {signal}: ATtiny pin {at_pin} / RP pin {rp_pin}: "
              f"{'PRESENT' if ok else 'NOT AS EXPECTED'}")
        if not ok:
            mismatches.append(f"link:{signal}")

    if tiny.get(19, "") == "":
        print("  BLOCKER: ATtiny PA3/SPI0 SCK (SOIC pin 19) unconnected")
        mismatches.append("SPI0_SCK")
    cs_match = re.search(r"\bSPI_CS\s*=\s*(\d+)\s*;", config)
    if cs_match and ARDUINO_PORT.get(int(cs_match.group(1))) != "PA4":
        print("  BLOCKER: SPI_CS pinMode uses PC2 (T_INT), "
              "but SPI0 SS is PA4 (PCB signal CS)")
        mismatches.append("SPI_CS")
    if "SPI0.CTRLA" in spi_code and "Serial.begin(" in main_src:
        print("  WARNING: SPI0 uses PA1/PA2 and conflicts with "
              "the proposed USART0 alternate PA1/PA2 link")
    if "Serial.begin(" in main_src and "Serial.swap(" not in main_src:
        print("  WARNING: Serial default USART0 on megaTinyCore txy6 "
              "is PB2/PB3 (debug RXD/TXD), NOT wired RP T_RX/T_TX")
        mismatches.append("USART_ROUTE")
    if "requestTemperatures()" in sampler and "setWaitForConversion(false)" not in sampler:
        print("  WARNING: 12-bit OneWire requests currently block; "
              "nonblocking state machine is needed")
        mismatches.append("BLOCKING_CONVERSION")
    if "return this->temperature > 0.0" in sampler:
        print("  WARNING: valid 0 C/negative readings rejected")
        mismatches.append("TEMP_ZERO_OR_NEGATIVE")
    if "SPI0.DATA = data" in spi_code:
        print("  WARNING: SPI sends one scaled byte without "
              "sensor status, age or CRC")
        mismatches.append("SPI_DATA_CONTRACT")
    if "Temperatures" not in rp_code and "temperature" not in rp_code.lower():
        print("  WARNING: RP2040 firmware has no temperature "
              "transport implementation yet")
        mismatches.append("RP_TRANSPORT")

    print(f"RESULT: {len(mismatches)} software/physical integration "
          f"gaps; nine physical sensor ports checked")
    if args.strict and mismatches:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
