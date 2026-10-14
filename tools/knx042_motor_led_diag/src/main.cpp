// KNX042: retain KNX040 temperature USB diagnostics and add time-bounded LED motor drive (NO KNX / NO MOTORS).
#include <Arduino.h>
#include "../../../lib/common/temperature_protocol.hpp"
#ifndef ARDUINO_ARCH_RP2040
#error "KNX040 diagnostic requires RP2040"
#endif
#ifndef KNX042_MOTOR_LED_DIAG
#error "Build only as isolated KNX042 USB motor LED diagnostic"
#endif

// U9/STKNX KNX_TX is active-HIGH, so drive GPIO0 LOW after setup.
// THIS IS NOT A RESET-LEVEL HARDWARE INTERLOCK: never connect KNX.
namespace {
constexpr uint8_t kStknxTx = 0;
// Eight RP2040 PWM EN outputs from PCB V1.2; two COMMON direction pins.
constexpr uint8_t kMotorEnable[8] = {10, 11, 12, 13, 14, 15, 16, 17};
constexpr uint8_t kDir1 = 18;
constexpr uint8_t kDir2 = 19;
constexpr uint32_t kPulseMs = 400; // fixed maximum, no arbitrary run-time pulse length
constexpr uint32_t kHoldMs = 180000; // M1 LED observation only: hard software auto-stop at 3 minutes
constexpr uint32_t kArmMs = 15000; // permission expires, never autonomous
uint32_t pulseStartedAt = 0;
uint32_t armedAt = 0;
bool pulseActive = false;
bool holdActive = false;
bool armed = false;
char inputLine[24] = {};
uint8_t inputLen = 0;
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


// No motor is allowed to remain asserted after a pulse or transport failure.
// STBY on the PCB is hardwired HIGH: this SOFTWARE gate is NOT a hardware STO.
void stopMotorOutputs() {
    for (uint8_t pin : kMotorEnable) digitalWrite(pin, LOW);
    digitalWrite(kDir1, LOW);
    digitalWrite(kDir2, LOW);
    pulseActive = false;
    holdActive = false;
}

void receiveCommand() {
    // Only deliberate, EXACT USB commands can arm or pulse the test outputs.
    // No commands are accepted via UART1, KNX or autonomous boot behavior.
    if (strcmp(inputLine, "STOP") == 0) {
        stopMotorOutputs();
        armed = false;
        if (Serial) Serial.println(F("KNX042 STOPPED"));
        return;
    }
    if (strcmp(inputLine, "STATUS") == 0) {
        if (Serial) {
            Serial.print(F("KNX042 STATUS armed="));
            Serial.print(armed ? 1 : 0);
            Serial.print(F(" active="));
            Serial.println(pulseActive ? 1 : 0);
        }
        return;
    }
    if (strcmp(inputLine, "ARM LEDS_ONLY") == 0) {
        stopMotorOutputs();
        armedAt = millis();
        armed = true;
        if (Serial) Serial.println(F("KNX042 ARMED 15s; NO KNX OR MOTORS"));
        return;
    }
    // Human-visible first-contact check: M1 only, fixed 180s timeout.
    // This never arms itself on boot. No KNX bus or physical motors allowed.
    if (strcmp(inputLine, "HOLD M1 F") == 0) {
        if (!armed || pulseActive ||
            static_cast<uint32_t>(millis() - armedAt) >= kArmMs) {
            stopMotorOutputs();
            armed = false;
            if (Serial) Serial.println(F("KNX042 REFUSED not-armed-or-busy"));
            return;
        }
        stopMotorOutputs();
        digitalWrite(kDir1, HIGH);
        digitalWrite(kDir2, LOW);
        delayMicroseconds(20);
        digitalWrite(kMotorEnable[0], HIGH);
        pulseStartedAt = millis();
        pulseActive = true;
        holdActive = true;
        armed = false; // single-shot, cannot chain without explicit new ARM
        if (Serial) Serial.println(F("KNX042 HOLD M1 F 180s"));
        return;
    }
    if (strlen(inputLine) == 9 &&
        memcmp(inputLine, "PULSE ", 6) == 0 &&
        inputLine[6] >= '1' && inputLine[6] <= '8' &&
        inputLine[7] == ' ' &&
        (inputLine[8] == 'F' || inputLine[8] == 'R')) {
        if (!armed || pulseActive ||
            static_cast<uint32_t>(millis() - armedAt) >= kArmMs) {
            stopMotorOutputs();
            armed = false;
            if (Serial) Serial.println(F("KNX042 REFUSED not-armed-or-busy"));
            return;
        }
        stopMotorOutputs(); // no overlap between channels/directions
        const uint8_t motorIndex = static_cast<uint8_t>(inputLine[6] - '1');
        const bool forward = inputLine[8] == 'F';
        digitalWrite(kDir1, forward ? HIGH : LOW);
        digitalWrite(kDir2, forward ? LOW : HIGH);
        delayMicroseconds(20); // settle common direction before PWM enable
        digitalWrite(kMotorEnable[motorIndex], HIGH);
        pulseStartedAt = millis();
        pulseActive = true;
        if (Serial) {
            Serial.print(F("KNX042 PULSE M"));
            Serial.print(motorIndex + 1);
            Serial.println(forward ? F(" F 400ms") : F(" R 400ms"));
        }
        return;
    }
    if (Serial) Serial.println(F("KNX042 REFUSED unknown-command"));
}

void pollUsbCommands() {
    for (uint8_t i = 0; i < 24 && Serial.available() > 0; ++i) {
        const int byte = Serial.read();
        if (byte < 0) break;
        if (byte == '\r') continue;
        if (byte == '\n') {
            inputLine[inputLen] = '\0';
            receiveCommand();
            inputLen = 0;
            continue;
        }
        if (byte < 32 || byte > 126 || inputLen >= sizeof(inputLine) - 1) {
            inputLen = 0;
            // Overflow/invalid bytes must not accidentally concatenate commands.
            armed = false;
            stopMotorOutputs();
            continue;
        }
        inputLine[inputLen++] = static_cast<char>(byte);
    }
}

void setup() {
    // GPIO0 must be LOW as soon as our application gains control.
    // This cannot enforce a safe KNX_TX level during ROM/reset.
    digitalWrite(kStknxTx, LOW);
    pinMode(kStknxTx, OUTPUT);
    // Disable ALL eight enables before the common direction signals.
    // Never use this image with motors connected or a live KNX bus.
    for (uint8_t pin : kMotorEnable) {
        digitalWrite(pin, LOW);
        pinMode(pin, OUTPUT);
    }
    digitalWrite(kDir1, LOW);
    pinMode(kDir1, OUTPUT);
    digitalWrite(kDir2, LOW);
    pinMode(kDir2, OUTPUT);
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
    if (pulseActive && static_cast<uint32_t>(now - pulseStartedAt) >=
        (holdActive ? kHoldMs : kPulseMs)) {
        stopMotorOutputs();
        if (Serial) Serial.println(F("KNX042 AUTO-STOP"));
    }
    if (armed && static_cast<uint32_t>(now - armedAt) >= kArmMs) {
        stopMotorOutputs();
        armed = false;
        if (Serial) Serial.println(F("KNX042 DISARMED time-expired"));
    }
    pollUsbCommands();
    if (Serial && static_cast<uint32_t>(now - lastHelloAt) >=
                  kHelloIntervalMs) {
        lastHelloAt = now;
        Serial.println(F("KNX042 USB MOTOR-LED diagnostic; KNX/MOTORS DISCONNECTED ONLY"));
        Serial.print(F("KNX040 USB-CONTROL UART1+KNX042-motorled uart_configured="));
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
    // Bounded temperature receive work; only the explicit KNX042 USB gate touches motor pins.
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
