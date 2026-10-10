#!/usr/bin/env python3
"""Read-only PCB-vs-firmware audit for the KNX013/KNX014 temperature bridge.

--scope sensors --strict: require KNX013 pins, async sampler, SPI disabled.
--scope all --strict: additionally require the later KNX014 UART transport.
No hardware, programming, EDA or KNX access is performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "schematic" / "pcb_knx-valve-control_v1.2.json"
CONFIG = ROOT / "src" / "temperature" / "config.hpp"
TEMPERATURE = ROOT / "src" / "temperature" / "temperature.cpp"
SAMPLER = ROOT / "src" / "temperature" / "sampler_core.hpp"
SPI = ROOT / "src" / "temperature" / "spi-slave.cpp"
MAIN = ROOT / "src" / "temperature" / "main.cpp"
RP_MAIN = ROOT / "src" / "controller" / "main.cpp"

# Physical SOIC-20 pin numbers, per ATtiny3216 package pinout.
AT_TINY_SOIC20 = {
    1: "VDD", 2: "PA4", 3: "PA5", 4: "PA6", 5: "PA7",
    6: "PB5", 7: "PB4", 8: "PB3", 9: "PB2", 10: "PB1",
    11: "PB0", 12: "PC0", 13: "PC1", 14: "PC2", 15: "PC3",
    16: "PA0", 17: "PA1", 18: "PA2", 19: "PA3", 20: "GND",
}

# Installed megaTinyCore variants/txy6 Arduino digital IDs.
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
        pads = {}
        for chunk in chunks:
            if chunk.startswith("PAD~"):
                data = chunk.split("~")
                if len(data) > 8 and data[8].isdigit():
                    pads[int(data[8])] = data[7]
        return pads
    raise RuntimeError(f"PCB component {reference} not found")


def pin_port(expr: str | None) -> str | None:
    if expr is None:
        return None
    if expr.startswith("PIN_"):
        return expr[4:]
    if expr.isdigit():
        return ARDUINO_PORT.get(int(expr))
    return None


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--scope", choices=("all", "sensors"), default="all")
    cli.add_argument("--strict", action="store_true",
                     help="exit 2 if required software capabilities are missing")
    args = cli.parse_args()

    data = json.loads(PCB.read_text(encoding="utf-8-sig"))
    tiny = read_pads("U25", data["shape"])
    rp = read_pads("U18", data["shape"])
    config = CONFIG.read_text(encoding="utf-8")
    temperature = TEMPERATURE.read_text(encoding="utf-8")
    main_src = MAIN.read_text(encoding="utf-8")
    core = SAMPLER.read_text(encoding="utf-8") if SAMPLER.exists() else ""
    rp_main = RP_MAIN.read_text(encoding="utf-8")
    sensor_issues = []
    transport_issues = []

    print("KNX013 V1.2 PCB sensor pins:")
    for index in range(9):
        net = f"T{index}"
        physical_pin = next((p for p, v in tiny.items() if v == net), None)
        hardware_port = AT_TINY_SOIC20.get(physical_pin)
        match = re.search(
            rf"\bT{index}\s*=\s*(PIN_P[A-C]\d+|\d+)\s*;", config
        )
        firmware = match.group(1) if match else None
        fw_port = pin_port(firmware)
        ok = hardware_port is not None and fw_port == hardware_port
        print(f"  {net}: PCB SOIC pin{physical_pin}={hardware_port}, "
              f"source {firmware}={fw_port}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            sensor_issues.append(f"{net}_PIN")

    if "setWaitForConversion(false)" not in temperature:
        sensor_issues.append("ASYNC_DALLAS")
    if "requestTemperaturesByAddress(address_)" not in temperature:
        sensor_issues.append("SENSOR_CONVERSION")
    if "getTempC(address_)" not in temperature:
        sensor_issues.append("SENSOR_CRC_READ")
    for token in ("SampleStale", "HasSample", "PowerOn85",
                  "acceptableTemperature", "centiC", "ageSeconds"):
        if token not in core:
            sensor_issues.append("SNAPSHOT_" + token)
    if "temperature > 0.0" in temperature or "return 0.0f;" in temperature:
        sensor_issues.append("FAKE_ZERO_OR_NEGATIVE")
    if SPI.exists() or "SPISlave::setup(" in main_src:
        sensor_issues.append("UNROUTED_SPI_STILL_ACTIVE")

    print("  asynchronous conversion, CRC read, snapshot flags, stale and "
          f"SPI-disabled: {'PASS' if not any(k for k in sensor_issues if not k.endswith('_PIN')) else 'FAIL'}")
    if tiny.get(19, "") == "":
        print("  PCB physical SPI0 SCK PA3 is not netted: SPI0 must stay disabled")
    else:
        print("  NOTE: PCB SPI0 SCK net has changed; re-verify schematic")

    for net, (at_pin, rp_pin) in {
        "T_TX": (18, 11),
        "T_RX": (17, 12),
        "T_INT": (14, 34),
        "CS": (2, 32),
    }.items():
        present = tiny.get(at_pin) == net and rp.get(rp_pin) == net
        print(f"  transport PCB {net}: {'PRESENT' if present else 'MISMATCH'}")
        if not present:
            transport_issues.append("PCB_" + net)

    if "Serial.begin(" in main_src and "Serial.swap(" not in main_src:
        print("  KNX014 TODO: ATtiny Serial default PB2/PB3; "
              "PORTMUX USART0 ALT1 PA1/PA2 not configured")
        transport_issues.append("ATtiny_UART_ROUTE")
    if "Temperatures" not in rp_main and "temperature" not in rp_main.lower():
        print("  KNX014 TODO: no RP2040 temperature transport implementation")
        transport_issues.append("RP_UART")
    print(f"RESULT: KNX013 sensor gaps={len(sensor_issues)}, "
          f"KNX014 transport gaps={len(transport_issues)} "
          f"(scope={args.scope})")
    if sensor_issues:
        print("SENSOR ISSUES:", ", ".join(sensor_issues))
    if transport_issues:
        print("TRANSPORT ISSUES:", ", ".join(transport_issues))
    selected = sensor_issues + (
        transport_issues if args.scope == "all" else []
    )
    return 2 if args.strict and selected else 0


if __name__ == "__main__":
    raise SystemExit(main())
