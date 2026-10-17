// KNX072: bounded, operator-armed GPIO0/JMP3 TX waveform test.
// HARD REQUIREMENT: BOTH physical KNX+ and KNX- bus wires disconnected.
// Output remains LOW at startup and unless a specific USB command is armed.
// This is NOT a KNX telegram PHY / production firmware; no automatic TX.
#include <Arduino.h>
#include "hardware/gpio.h"
#include "pico/time.h"

constexpr unsigned kTxPin = 0;  // RP2040 U18 GPIO0 -> JMP3 pad3 -> pad2 -> U9 KNX_TX
constexpr uint32_t kArmWindowMs = 8000;
constexpr int kMaxPulses = 8;
constexpr uint32_t kHighUs = 35;
constexpr uint32_t kLowUs = 69;

String line;
bool armed = false;
uint32_t armStartMs = 0;
unsigned long oneShots = 0;

void holdLow() {
  gpio_put(kTxPin, 0);
}

void printStatus() {
  Serial.print("KNX072 STATUS mode=USB_ONLY gpio=0 tx_low=");
  Serial.print(gpio_get(kTxPin) == 0 ? "1" : "0");
  Serial.print(" armed=");
  Serial.print(armed ? "1" : "0");
  Serial.print(" oneshots=");
  Serial.print(oneShots);
  Serial.println(" NO_KNX_BUS_REQUIRED");
}

void pulse8Once() {
  if (!armed || (uint32_t)(millis() - armStartMs) > kArmWindowMs) {
    armed = false;
    holdLow();
    Serial.println("KNX072 REFUSED NOT_ARMED_OR_EXPIRED");
    return;
  }
  armed = false;  // fails closed; must re-arm for any other pulse train
  Serial.println("KNX072 EXECUTING_ONESHOT_8x35us_HIGH_69us_LOW");
  Serial.flush();
  delay(30);  // give host time to be ready after ACK before pulse train
  noInterrupts();
  for (int i = 0; i < kMaxPulses; ++i) {
    gpio_put(kTxPin, 1);
    busy_wait_us_32(kHighUs);
    gpio_put(kTxPin, 0);
    busy_wait_us_32(kLowUs);
  }
  holdLow();
  interrupts();
  ++oneShots;
  Serial.println("KNX072 TX_BENCH_COMPLETE 8_PULSES PIN_LOW");
  printStatus();
}

void command(String s) {
  s.trim();
  if (s == "STATUS") {
    printStatus();
  } else if (s == "ARM USB_ONLY") {
    holdLow();
    armed = true;
    armStartMs = millis();
    Serial.println("KNX072 ARMED USB_ONLY 8s TTL NO_BUS");
  } else if (s == "PULSE8") {
    pulse8Once();
  } else if (s == "DISARM" || s == "STOP") {
    armed = false;
    holdLow();
    Serial.println("KNX072 DISARMED TX_LOW");
  } else if (s.length()) {
    Serial.println("KNX072 UNKNOWN_COMMAND REFUSED");
  }
}

void setup() {
  // Force output latch LOW before direction changes; never high at startup.
  gpio_init(kTxPin);
  gpio_put(kTxPin, 0);
  gpio_set_dir(kTxPin, GPIO_OUT);
  gpio_pull_down(kTxPin);
  armed = false;
  line.reserve(64);
  Serial.begin(115200);
  Serial.println("KNX072 READY USB_ONLY NO_AUTOMATIC_PULSES TX_LOW");
  printStatus();
}

void loop() {
  if (armed && (uint32_t)(millis() - armStartMs) > kArmWindowMs) {
    armed = false;
    holdLow();
    Serial.println("KNX072 ARM_EXPIRED TX_LOW");
  }
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      command(line);
      line = "";
    } else if (line.length() < 62) {
      line += c;
    } else {
      line = "";
      armed = false;
      holdLow();
      Serial.println("KNX072 INPUT_OVERFLOW DISARMED");
    }
  }
}
