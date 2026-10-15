// KNX043: passive STKNX receive-edge logger for a future isolated KNX bench.
// NEVER attach to a KNX bus while V1.2 R17/U11/U9/rail/reset gates are OPEN.
// This image sends ZERO KNX bus pulses. It does NOT implement TPUart or ETS.
//
// PIN CONTRACT FROM V1.2 PCB: GPIO0 -> JMP3 -> U9 pin24 KNX_TX,
// GPIO1 <- JMP2 <- U9 pin23 KNX_RX; STKNX RX is LOW in bus idle state,
// and HIGH during a physical KNX active pulse (~35us).
//
// GPIO0 is driven LOW only AFTER the RP2040 program starts.
// On BOOTSEL, RESET, POWER LOSS and brownout, software cannot enforce LOW.
// Remove erroneous R17 10k pull-up and provide a qualified reset-safe
// hardware transmit-inhibit before any physical bus connection.

#include <Arduino.h>
#include <string.h>
#include <stdio.h>
#ifndef ARDUINO_ARCH_RP2040
#error "KNX043 passive receive diagnostic requires RP2040"
#endif
#ifndef KNX043_STKNX_RECEIVE_ONLY
#error "This firmware must be built as an isolated RX-only diagnostic"
#endif

namespace {
constexpr uint8_t kKnxTx = 0;   // LOW is inactive
constexpr uint8_t kKnxRx = 1;   // STKNX U9 pin23, through JMP2
constexpr uint8_t kDirection1 = 18;
constexpr uint8_t kDirection2 = 19;
constexpr uint8_t kMotorEnables[8] = {10, 11, 12, 13, 14, 15, 16, 17};
constexpr uint32_t kArmLifetimeMs = 15000;
constexpr uint32_t kMaxListenMs = 120000; // software-only
constexpr uint32_t kHelloMs = 5000;
// 16,384 slots * 8 bytes = 128 KiB (16,383 usable, around 0.85 s
// of worst-case 19,200 RX transitions/s). USB backpressure can still overflow.
constexpr unsigned kRing = 16384;
static_assert((kRing & (kRing - 1)) == 0, "Ring must be power-of-two");
struct Edge {
    uint32_t timeUs;
    uint8_t level;
};
static_assert(sizeof(Edge) == 8, "RX edge must consume exactly 8 bytes");
volatile Edge rxEdges[kRing] = {};
volatile unsigned writeIndex = 0;
volatile unsigned readIndex = 0;
volatile uint32_t lostEdges = 0;
volatile uint32_t totalEdges = 0;
volatile uint32_t highWater = 0;
volatile bool listenEnabled = false;
bool armed = false;
bool listening = false;
uint32_t armTime = 0;
uint32_t listenTime = 0;
uint32_t lastHello = 0;
char commandBuffer[32] = {};
uint8_t inputSize = 0;
}

void allOutputsInactive() {
    for (const uint8_t pin : kMotorEnables) digitalWrite(pin, LOW);
    digitalWrite(kDirection1, LOW);
    digitalWrite(kDirection2, LOW);
    digitalWrite(kKnxTx, LOW);   // KNX TX never HIGH, including any command
}

void onKnxRxChange() {
    if (!listenEnabled) return;
    ++totalEdges;  // counts attempted RX edges, including ring overflows
    const unsigned next = (writeIndex + 1U) & (kRing - 1U);
    if (next == readIndex) {
        ++lostEdges;
        return;
    }
    rxEdges[writeIndex].timeUs = micros();
    rxEdges[writeIndex].level = digitalRead(kKnxRx) ? 1 : 0;
    writeIndex = next;
    const unsigned buffered = (writeIndex - readIndex) & (kRing - 1U);
    if (buffered > highWater) highWater = buffered;
}

void stopListen() {
    noInterrupts();
    listenEnabled = false;
    interrupts();
    armed = false;
    listening = false;
    allOutputsInactive();
}

void printStatus() {
    if (!Serial) return;
    uint32_t missing;
    uint32_t observed;
    uint32_t peak;
    unsigned buffered;
    noInterrupts();
    missing = lostEdges;
    observed = totalEdges;
    peak = highWater;
    buffered = (writeIndex - readIndex) & (kRing - 1);
    interrupts();
    Serial.print(F("KNX043 STATUS armed="));
    Serial.print(armed ? 1 : 0);
    Serial.print(F(" listen="));
    Serial.print(listening ? 1 : 0);
    Serial.print(F(" buffered="));
    Serial.print(buffered);
    Serial.print(F(" dropped="));
    Serial.print(missing);
    Serial.print(F(" capacity="));
    Serial.print(kRing - 1U);
    Serial.print(F(" high_water="));
    Serial.print(peak);
    Serial.print(F(" observed="));
    Serial.println(observed);
}

void processCommand(const char *line) {
    if (strcmp(line, "STOP") == 0) {
        stopListen();
        if (Serial) Serial.println(F("KNX043 STOPPED RX_ONLY"));
        return;
    }
    if (strcmp(line, "STATUS") == 0) {
        printStatus(); // read-only, never disarm or cause output changes
        return;
    }
    if (strcmp(line, "ARM LISTEN_ONLY") == 0) {
        if (listening) {
            if (Serial) Serial.println(F("KNX043 REFUSED ALREADY_LISTENING"));
            return;
        }
        allOutputsInactive();
        armed = true;
        armTime = millis();
        if (Serial) Serial.println(F("KNX043 ARMED LISTEN_ONLY 15s TX_LOW"));
        return;
    }
    if (strcmp(line, "START LISTEN") == 0) {
        if (!armed || listening ||
            static_cast<uint32_t>(millis() - armTime) > kArmLifetimeMs) {
            armed = false;
            if (Serial) Serial.println(F("KNX043 REFUSED NOT_ARMED"));
            return;
        }
        noInterrupts();
        readIndex = 0;
        writeIndex = 0;
        lostEdges = 0;
        totalEdges = 0;
        highWater = 0;
        listenEnabled = true;
        interrupts();
        armed = false;
        listening = true;
        listenTime = millis();
        allOutputsInactive();
        if (Serial) Serial.println(F("KNX043 LISTENING RX_ONLY 120s TX_LOW"));
        return;
    }
    if (Serial) Serial.println(F("KNX043 REFUSED UNKNOWN"));
}

void pollUsb() {
    for (unsigned i = 0; i < 32 && Serial.available() > 0; ++i) {
        const int c = Serial.read();
        if (c < 0) break;
        if (c == '\r') continue;
        if (c == '\n') {
            commandBuffer[inputSize] = '\0';
            processCommand(commandBuffer);
            inputSize = 0;
            continue;
        }
        if (c < 32 || c > 126 || inputSize >= sizeof(commandBuffer) - 1) {
            inputSize = 0;
            stopListen(); // fail-closed on invalid serial bytes
            if (Serial) Serial.println(F("KNX043 BAD_COMMAND ALL_OFF"));
            continue;
        }
        commandBuffer[inputSize++] = static_cast<char>(c);
    }
}

void emitRxEdges() {
    if (!Serial) return;
    // Bounded batches keep polling USB commands responsive while the ISR
    // independently queues new samples. Short records reduce CDC load.
    for (unsigned n = 0; n < 96; ++n) {
        Edge edge{};
        bool got = false;
        noInterrupts();
        if (readIndex != writeIndex) {
            edge.timeUs = rxEdges[readIndex].timeUs;
            edge.level = rxEdges[readIndex].level;
            readIndex = (readIndex + 1U) & (kRing - 1U);
            got = true;
        }
        interrupts();
        if (!got) return;
        char line[32];
        const int count = snprintf(line, sizeof(line), "E %lu %u\n",
                static_cast<unsigned long>(edge.timeUs),
                static_cast<unsigned>(edge.level));
        if (count > 0 && count < static_cast<int>(sizeof(line))) {
            Serial.write(reinterpret_cast<const uint8_t *>(line),
                         static_cast<size_t>(count));
        }
    }
}

void setup() {
    // ALL outputs LOW from the earliest possible firmware-controlled point.
    digitalWrite(kKnxTx, LOW);
    pinMode(kKnxTx, OUTPUT);
    for (const uint8_t pin : kMotorEnables) {
        digitalWrite(pin, LOW);
        pinMode(pin, OUTPUT);
    }
    digitalWrite(kDirection1, LOW);
    pinMode(kDirection1, OUTPUT);
    digitalWrite(kDirection2, LOW);
    pinMode(kDirection2, OUTPUT);
    allOutputsInactive();
    pinMode(kKnxRx, INPUT); // no internal pullup, U9 drives CMOS
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(kKnxRx), onKnxRxChange, CHANGE);
    lastHello = millis() - kHelloMs;
}

void loop() {
    const uint32_t now = millis();
    if (armed && static_cast<uint32_t>(now - armTime) >= kArmLifetimeMs) {
        armed = false;
        if (Serial) Serial.println(F("KNX043 ARM_EXPIRED"));
    }
    if (listening && static_cast<uint32_t>(now - listenTime) >= kMaxListenMs) {
        stopListen();
        if (Serial) Serial.println(F("KNX043 AUTO_STOP RX_ONLY"));
    }
    pollUsb();
    emitRxEdges();
    if (Serial && static_cast<uint32_t>(now - lastHello) >= kHelloMs) {
        lastHello = now;
        Serial.println(F("KNX043 PASSIVE RX READY; TX_LOW NO KNX_TX_PULSES"));
        printStatus();
    }
}
