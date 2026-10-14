// KNX036 isolated USB-CDC self-identification. BUILD ONLY, no flashing.
// Critical: this does NOT protect U9 during boot or while the KNX bus is attached.
// Never run the first contact with a KNX bus, motor or UPDI connector attached.
// USB CDC Serial only. No UART0, UART1, KNX/ETS, I2C or motor GPIO activity.
#include <Arduino.h>

#ifndef ARDUINO_ARCH_RP2040
#error "KNX036 diagnostic firmware is RP2040-only"
#endif
#ifndef KNX036_USB_DIAGNOSTIC
#error "KNX036 source must be compiled only in isolated diagnostic environment"
#endif

namespace {
constexpr uint8_t kKnxTxGpio = 0;  // U9 STKNX KNX_TX: inactive LOW.
constexpr uint32_t kHeartbeatIntervalMs = 2000;
uint32_t lastHeartbeatMs = 0;
uint32_t heartbeats = 0;
}  // namespace

void setup() {
    // Synchronous LOW before configuring GPIO0 as output; no pulses allowed.
    digitalWrite(kKnxTxGpio, LOW);
    pinMode(kKnxTxGpio, OUTPUT);

    Serial.begin(115200);  // RP2040 USB CDC, NOT UART0/1.
    lastHeartbeatMs = millis();
}

void loop() {
    const uint32_t now = millis();
    if (static_cast<uint32_t>(now - lastHeartbeatMs) >= kHeartbeatIntervalMs) {
        lastHeartbeatMs = now;
        if (Serial) {
            Serial.print(F("KNX036 USB-ONLY RP2040 ALIVE uptime_ms="));
            Serial.print(now);
            Serial.print(F(" seq="));
            Serial.println(++heartbeats);
        }
    }
    // All GPIO except GPIO0 remain at default core startup state.
    // In particular no GPIO8/9 (ATtiny UART) and no GPIO10..19 (motors).
}
