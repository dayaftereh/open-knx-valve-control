// KNX042 – USB-only motor LED sequence, never connect KNX or motor actuators.
// Diagnostic only; TB6612 STBY is hard HIGH, no independent hardware STO.
// KNX_TX GPIO0 may be unsafe during ROM/reset: KNX bus MUST remain unplugged.
// A fresh boot NEVER starts the sequence. Explicit USB ARM + START required.
#include <Arduino.h>
#ifndef ARDUINO_ARCH_RP2040
#error "This isolated diagnostic runs on the RP2040 only"
#endif
#ifndef KNX042_LED_SEQUENCE_ONLY
#error "Build this source exclusively for the isolated LED sequence"
#endif

namespace {
constexpr uint8_t kKnxTx = 0;
constexpr uint8_t kMotorEnable[8] = {10, 11, 12, 13, 14, 15, 16, 17};
constexpr uint8_t kIn1Open = 18;
constexpr uint8_t kIn2Close = 19;
constexpr uint8_t kMotorCount = 8;
constexpr uint8_t kStepsPerRound = kMotorCount * 2; // CLOSE, OPEN each motor
constexpr uint8_t kMaxRounds = 5;                   // five repeats, never infinite
constexpr uint32_t kOnMs = 1000;
constexpr uint32_t kOffMs = 1000;
constexpr uint32_t kMaxRunMs = 180000; // 160s nominal + conservative time cap
constexpr uint32_t kArmExpiresMs = 15000;
constexpr uint32_t kHelloEveryMs = 2000;
enum class Phase : uint8_t { Idle, On, Off };
Phase phase = Phase::Idle;
bool armed = false;
bool sequenceRunning = false;
uint32_t armedAt = 0;
uint32_t phaseAt = 0;
uint32_t runAt = 0;
uint32_t lastHelloAt = 0;
uint8_t stepIndex = 0;    // 0=M1 CLOSE, 1=M1 OPEN, ... 15=M8 OPEN
uint8_t roundIndex = 0;   // 0..4
uint8_t finishedRounds = 0;
uint16_t completedSteps = 0;
char inputLine[32] = {};
uint8_t inputLen = 0;
}

void allPinsOff() {
    for (uint8_t pin : kMotorEnable) digitalWrite(pin, LOW);
    digitalWrite(kIn1Open, LOW);
    digitalWrite(kIn2Close, LOW);
}

void stopSequence() {
    allPinsOff();
    sequenceRunning = false;
    armed = false;
    phase = Phase::Idle;
}

// Only one motor enable can ever be HIGH. Direction lines are shared.
void startCurrentLedStep(uint32_t now) {
    allPinsOff();
    const uint8_t motor = static_cast<uint8_t>(stepIndex / 2);
    const bool close = (stepIndex % 2) == 0;
    digitalWrite(kIn1Open, close ? LOW : HIGH);
    digitalWrite(kIn2Close, close ? HIGH : LOW);
    delayMicroseconds(25); // direction settles before enabling bridge
    digitalWrite(kMotorEnable[motor], HIGH);
    phase = Phase::On;
    phaseAt = now;
    if (Serial) {
        Serial.print(F("KNX042 SEQ ON round="));
        Serial.print(roundIndex + 1);
        Serial.print('/');
        Serial.print(kMaxRounds);
        Serial.print(F(" channel=M"));
        Serial.print(motor + 1);
        Serial.print(F(" dir="));
        Serial.println(close ? F("CLOSE") : F("OPEN"));
    }
}

void tickSequence(uint32_t now) {
    if (!sequenceRunning) return;
    if (static_cast<uint32_t>(now - runAt) >= kMaxRunMs) {
        stopSequence();
        if (Serial) Serial.println(F("KNX042 SEQ TIMEOUT ALL_OFF"));
        return;
    }
    if (phase == Phase::On &&
        static_cast<uint32_t>(now - phaseAt) >= kOnMs) {
        allPinsOff();
        phase = Phase::Off;
        phaseAt = now;
        ++completedSteps;
        if (Serial) Serial.println(F("KNX042 SEQ OFF"));
        return;
    }
    if (phase == Phase::Off &&
        static_cast<uint32_t>(now - phaseAt) >= kOffMs) {
        ++stepIndex;
        if (stepIndex == kStepsPerRound) {
            stepIndex = 0;
            ++roundIndex;
            finishedRounds = roundIndex;
        }
        if (roundIndex >= kMaxRounds) {
            stopSequence();
            if (Serial) Serial.println(F("KNX042 SEQ DONE ALL_OFF"));
            return;
        }
        startCurrentLedStep(now);
    }
}

void command(const char *line) {
    if (strcmp(line, "STOP") == 0) {
        stopSequence();
        if (Serial) Serial.println(F("KNX042 SEQ STOPPED"));
        return;
    }
    if (strcmp(line, "STATUS") == 0) {
        if (Serial) {
            Serial.print(F("KNX042 STATUS armed="));
            Serial.print(armed ? 1 : 0);
            Serial.print(F(" active="));
            Serial.print(phase == Phase::On ? 1 : 0);
            Serial.print(F(" seq="));
            Serial.print(sequenceRunning ? 1 : 0);
            Serial.print(F(" step="));
            Serial.print(sequenceRunning ? (stepIndex + 1) : 0);
            Serial.print(F("/16 round="));
            Serial.print(sequenceRunning ? (roundIndex + 1) : finishedRounds);
            Serial.print(F("/5 completed="));
            Serial.println(completedSteps);
        }
        return; // STATUS is strictly read-only, no hidden STOP!
    }
    if (strcmp(line, "ARM LEDS_ONLY") == 0) {
        if (sequenceRunning) {
            if (Serial) Serial.println(F("KNX042 REFUSED busy"));
            return;
        }
        allPinsOff();
        armedAt = millis();
        armed = true;
        if (Serial) Serial.println(F("KNX042 ARMED 15s; NO KNX OR MOTORS"));
        return;
    }
    if (strcmp(line, "START ALL 5") == 0) {
        if (!armed || sequenceRunning ||
            static_cast<uint32_t>(millis() - armedAt) >= kArmExpiresMs) {
            armed = false;
            if (Serial) Serial.println(F("KNX042 REFUSED not-armed-or-busy"));
            return;
        }
        armed = false;
        allPinsOff();
        stepIndex = 0;
        roundIndex = 0;
        finishedRounds = 0;
        completedSteps = 0;
        runAt = millis();
        sequenceRunning = true;
        if (Serial) {
            Serial.println(F("KNX042 SEQ START rounds=5 on_ms=1000 off_ms=1000"));
        }
        startCurrentLedStep(runAt); // first: M1 CLOSE, only after USB START
        return;
    }
    if (Serial) Serial.println(F("KNX042 REFUSED unknown-command"));
}

void pollUsb() {
    // Bounded input processing, no output activation from spontaneous telemetry.
    for (uint8_t n = 0; n < 32 && Serial.available() > 0; ++n) {
        const int ch = Serial.read();
        if (ch < 0) break;
        if (ch == '\r') continue;
        if (ch == '\n') {
            inputLine[inputLen] = '\0';
            command(inputLine);
            inputLen = 0;
            continue;
        }
        if (ch < 32 || ch > 126 || inputLen >= sizeof(inputLine) - 1) {
            inputLen = 0;
            stopSequence(); // invalid serial input fails closed
            if (Serial) Serial.println(F("KNX042 SEQ INPUT_ERROR ALL_OFF"));
            continue;
        }
        inputLine[inputLen++] = static_cast<char>(ch);
    }
}

void setup() {
    // This does not protect GPIO0 in BOOTSEL / ROM / reset. KNX is unplugged.
    digitalWrite(kKnxTx, LOW);
    pinMode(kKnxTx, OUTPUT);
    for (uint8_t pin : kMotorEnable) {
        digitalWrite(pin, LOW);
        pinMode(pin, OUTPUT);
    }
    digitalWrite(kIn1Open, LOW);
    pinMode(kIn1Open, OUTPUT);
    digitalWrite(kIn2Close, LOW);
    pinMode(kIn2Close, OUTPUT);
    allPinsOff();
    Serial.begin(115200); // USB CDC
    lastHelloAt = millis() - kHelloEveryMs;
}

void loop() {
    const uint32_t now = millis();
    tickSequence(now);
    if (armed && static_cast<uint32_t>(now - armedAt) >= kArmExpiresMs) {
        armed = false;
        if (Serial) Serial.println(F("KNX042 DISARMED time-expired"));
    }
    pollUsb();
    if (Serial && static_cast<uint32_t>(now - lastHelloAt) >= kHelloEveryMs) {
        lastHelloAt = now;
        Serial.println(F("KNX042 LED SEQUENCE READY; USB ONLY KNX MOTORS DISCONNECTED"));
    }
}
