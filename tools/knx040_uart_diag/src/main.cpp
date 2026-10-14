// KNX040: isolate RP2040 USB CDC <-> ATtiny3216 CRC-protected UART1, no KNX.
#include <Arduino.h>
#include "../../../lib/common/temperature_protocol.hpp"
#ifndef ARDUINO_ARCH_RP2040
#error "KNX040 diagnostic requires RP2040"
#endif
#ifndef KNX040_TEMPERATURE_UART_DIAG
#error "Build only as isolated KNX040 UART diagnostic"
#endif

// U9/STKNX KNX_TX is active-HIGH, so drive GPIO0 LOW after setup.
// THIS IS NOT A RESET-LEVEL HARDWARE INTERLOCK: never connect KNX.
namespace {
constexpr uint8_t kStknxTx = 0;
constexpr uint8_t kAttinyRx = 9; // RP GPIO9 UART1 RX <- ATtiny PA1 TX
constexpr uint8_t kAttinyTx = 8; // RP GPIO8 UART1 TX -> ATtiny PA2 RX
constexpr uint32_t kBaud = 115200;
constexpr uint32_t kFirstPollMs = 7000;
constexpr uint32_t kPollIntervalMs = 2000;
constexpr uint32_t kReplyTimeoutMs = 1200;
constexpr uint32_t kHelloIntervalMs = 7000;
TemperatureProtocol::Parser parser;
uint8_t sequence = 0;
uint8_t outstandingSequence = 0;
uint32_t requestedAt = 0;
uint32_t lastSerialByteAt = 0;
uint32_t lastRequestAt = 0;
uint32_t lastHelloAt = 0;
uint32_t acceptedSnapshots = 0;
uint32_t timedOut = 0;
uint32_t rejected = 0;
bool inFlight = false;
bool uartConfigured = false;
}

void setup() {
    digitalWrite(kStknxTx, LOW);
    pinMode(kStknxTx, OUTPUT);
    Serial.begin(115200); // USB CDC, not a KNX-UART
    const bool tx = Serial2.setTX(kAttinyTx);
    const bool rx = Serial2.setRX(kAttinyRx);
    uartConfigured = tx && rx;
    if (uartConfigured) {
        Serial2.begin(kBaud); // RP UART1 to ATtiny USART0 ALT1 PA1/PA2
    }
    lastSerialByteAt = millis();
    lastHelloAt = millis() - kHelloIntervalMs;
}

void printSnapshot(uint8_t seq, const TemperatureProtocol::Snapshot& snap) {
    uint8_t valid = 0;
    uint8_t missing = 0;
    uint8_t faults = 0;
    for (uint8_t i = 0; i < TemperatureProtocol::Channels; ++i) {
        const auto& ch = snap.channels[i];
        if (ch.flags & 0x02) ++valid;
        if (!(ch.flags & 0x02) && ch.fault == 1 &&
            ch.ageSeconds == 0xFFFF) ++missing;
        if (ch.fault != 0) ++faults;
    }
    if (!Serial) return;
    Serial.print(F("KNX040 SNAPSHOT seq="));
    Serial.print(seq);
    Serial.print(F(" up_ms="));
    Serial.print(snap.uptimeMs);
    Serial.print(F(" valid="));
    Serial.print(valid);
    Serial.print(F(" no_sensor="));
    Serial.print(missing);
    Serial.print(F(" faults="));
    Serial.print(faults);
    Serial.print(F(" accepted="));
    Serial.print(acceptedSnapshots);
    Serial.print(F(" timeout="));
    Serial.print(timedOut);
    Serial.print(F(" rejected="));
    Serial.println(rejected);
    for (uint8_t i = 0; i < TemperatureProtocol::Channels; ++i) {
        const auto& ch = snap.channels[i];
        Serial.print(F("KNX040 CH T"));
        Serial.print(i);
        Serial.print(F(" flags="));
        Serial.print(ch.flags);
        Serial.print(F(" fault="));
        Serial.print(ch.fault);
        Serial.print(F(" age_s="));
        Serial.print(ch.ageSeconds);
        Serial.print(F(" centiC="));
        Serial.println(ch.centiC);
    }
}

void loop() {
    const uint32_t now = millis();
    if (Serial && static_cast<uint32_t>(now - lastHelloAt) >=
                  kHelloIntervalMs) {
        lastHelloAt = now;
        Serial.print(F("KNX040 USB-CONTROL UART1-only uart_configured="));
        Serial.print(uartConfigured ? 1 : 0);
        Serial.print(F(" accepted="));
        Serial.print(acceptedSnapshots);
        Serial.print(F(" timeout="));
        Serial.println(timedOut);
    }

    if (!uartConfigured) return;
    if (parser.inProgress() &&
        static_cast<uint32_t>(now - lastSerialByteAt) >
            TemperatureProtocol::MaxInterByteGapMs) parser.reset();
    // Bounded receive work; never send KNX or touch motor pins.
    for (uint8_t n = 0; n < 48 && Serial2.available() > 0; ++n) {
        const int next = Serial2.read();
        if (next < 0) break;
        lastSerialByteAt = millis();
        TemperatureProtocol::Frame frame{};
        if (!parser.feed(static_cast<uint8_t>(next), frame)) continue;
        if (!inFlight || frame.sequence != outstandingSequence ||
            frame.type != TemperatureProtocol::SnapshotResponse) {
            ++rejected;
            continue;
        }
        TemperatureProtocol::Snapshot snapshot{};
        if (!TemperatureProtocol::decodeSnapshot(frame, snapshot)) {
            ++rejected;
            continue;
        }
        inFlight = false;
        ++acceptedSnapshots;
        printSnapshot(frame.sequence, snapshot);
    }
    if (inFlight && static_cast<uint32_t>(now - requestedAt) >
                   kReplyTimeoutMs) {
        inFlight = false;
        ++timedOut;
        if (Serial) {
            Serial.print(F("KNX040 TIMEOUT seq="));
            Serial.print(outstandingSequence);
            Serial.print(F(" count="));
            Serial.println(timedOut);
        }
    }
    if (now < kFirstPollMs || inFlight ||
        (lastRequestAt != 0 &&
         static_cast<uint32_t>(now - lastRequestAt) < kPollIntervalMs)) return;

    uint8_t request[TemperatureProtocol::FrameOverhead]{};
    const uint8_t seq = ++sequence;
    const size_t count = TemperatureProtocol::encodeRequest(
        seq, request, sizeof(request));
    // Arduino-Pico SerialUART::availableForWrite() is a BOOLEAN (0 or 1),
    // not TX FIFO free byte count; checking for 8 would suppress all polls.
    if (count != 8 || Serial2.availableForWrite() <= 0) return;
    if (Serial2.write(request, count) != count) return;
    lastRequestAt = millis();
    requestedAt = lastRequestAt;
    outstandingSequence = seq;
    inFlight = true;
}
