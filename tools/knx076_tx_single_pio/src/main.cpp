// KNX076 one bounded STKNX TX impulse on GPIO0, only after explicit USB commands.
// This is a diagnostic waveform (35 us HIGH), NOT a valid KNX telegram.
// NEVER issues a signal on boot. Only ARM ONE + FIRE ONE may queue one PIO word.
// PIO automatically returns LOW after exactly 35 hardware clock cycles, even
// if the RP2040 application core stalls during the pulse.
// Hardware test buses require separate verification of U9/U11 and KNX supply.
#include <Arduino.h>
#include "hardware/gpio.h"
#include "hardware/pio.h"
#include "hardware/pio_instructions.h"
#include "hardware/clocks.h"

namespace {
constexpr uint kTxPin = 0;  // RP2040 GPIO0 -> JMP3 pad3 -> pad2 -> STKNX U9 pin24
constexpr uint32_t kArmWindowMs = 4000;
constexpr float kPioHz = 1000000.0f;  // nominal 1.0 us per PIO cycle
// One side-set bit reduces the instruction delay to 4 bits (max 15).
// pull block side 0: hold idle low as long as FIFO is empty.
// three high NOPs: (1+15)+(1+15)+(1+2) = exactly 35 PIO cycles.
// trailing low NOP 1 cycle, then return to blocking pull (side 0).
const uint16_t kInstructions[] = {
    static_cast<uint16_t>(pio_encode_pull(false, true) | pio_encode_sideset(1, 0)),
    static_cast<uint16_t>(pio_encode_nop() | pio_encode_delay(15) | pio_encode_sideset(1, 1)),
    static_cast<uint16_t>(pio_encode_nop() | pio_encode_delay(15) | pio_encode_sideset(1, 1)),
    static_cast<uint16_t>(pio_encode_nop() | pio_encode_delay(2)  | pio_encode_sideset(1, 1)),
    static_cast<uint16_t>(pio_encode_nop() | pio_encode_sideset(1, 0)),
};
const struct pio_program kProgram = {
    kInstructions,
    static_cast<uint16_t>(sizeof(kInstructions) / sizeof(kInstructions[0])),
    -1,
};
PIO selectedPio = pio0;
int selectedSm = -1;
bool ready = false;
bool armed = false;
bool alreadyFired = false;
uint32_t armedAt = 0;
String inputLine;

void printStatus() {
    Serial.print("KNX076 STATUS gpio0_measured=");
    Serial.print(gpio_get(kTxPin) ? "HIGH" : "LOW");
    Serial.print(" pio_ready=");
    Serial.print(ready ? "1" : "0");
    Serial.print(" armed=");
    Serial.print(armed ? "1" : "0");
    Serial.print(" shots=");
    Serial.print(alreadyFired ? "1" : "0");
    Serial.println(" SINGLE_35US_PIO_NO_AUTO_TX");
}
void disarm() {
    armed = false;
}
void executeCommand(String cmd) {
    cmd.trim();
    if (cmd == "STATUS") {
        printStatus();
    } else if (cmd == "DISARM" || cmd == "STOP") {
        disarm();
        Serial.println("KNX076 DISARMED");
        printStatus();
    } else if (cmd == "ARM ONE") {
        if (!ready || alreadyFired || gpio_get(kTxPin)) {
            disarm();
            Serial.println("KNX076 REFUSED NOT_READY_OR_FIRED_OR_TX_NOT_LOW");
            return;
        }
        armedAt = millis();
        armed = true;
        Serial.println("KNX076 ARMED ONE_SHOT_4S_TTL (no pulse yet)");
    } else if (cmd == "FIRE ONE") {
        if (!ready || !armed || alreadyFired ||
            (uint32_t)(millis() - armedAt) >= kArmWindowMs ||
            gpio_get(kTxPin) || !pio_sm_is_tx_fifo_empty(selectedPio, (uint)selectedSm)) {
            disarm();
            Serial.println("KNX076 REFUSED_NOT_ARMED_EXPIRED_BUSY_OR_TX_NOT_LOW");
            return;
        }
        // One shot per boot: lock FIRST, then issue ONE FIFO command.
        disarm();
        alreadyFired = true;
        Serial.println("KNX076 COMMITTING_ONE_35US_PIO_PULSE");
        Serial.flush();
        pio_sm_put_blocking(selectedPio, (uint)selectedSm, 0x1);
        // Firmware only counts a single token; PIO closes HIGH autonomously.
        Serial.println("KNX076 ONE_SHOT_QUEUED_LOCKED_REBOOT_TO_REARM");
        printStatus();
    } else if (cmd.length() != 0) {
        disarm();
        Serial.println("KNX076 INVALID_COMMAND_DISARMED");
    }
}
bool configurePio() {
    if (!pio_can_add_program(selectedPio, &kProgram)) return false;
    selectedSm = pio_claim_unused_sm(selectedPio, false);
    if (selectedSm < 0) return false;
    uint offset = pio_add_program(selectedPio, &kProgram);
    pio_sm_config cfg = pio_get_default_sm_config();
    sm_config_set_wrap(&cfg, offset, offset + 4);
    sm_config_set_sideset(&cfg, 1, false, false);
    sm_config_set_sideset_pins(&cfg, kTxPin);
    sm_config_set_clkdiv(&cfg, (float)clock_get_hz(clk_sys) / kPioHz);
    // The pin output latch has already been set LOW; change function to PIO
    // only after the SM is configured with its idle-low blocking PULL.
    pio_sm_init(selectedPio, (uint)selectedSm, offset, &cfg);
    pio_sm_set_enabled(selectedPio, (uint)selectedSm, false);
    pio_sm_clear_fifos(selectedPio, (uint)selectedSm);
    pio_gpio_init(selectedPio, kTxPin);
    pio_sm_set_consecutive_pindirs(selectedPio, (uint)selectedSm, kTxPin, 1, true);
    pio_sm_set_enabled(selectedPio, (uint)selectedSm, true);
    return true;
}
} // namespace

void setup() {
    // Software-safe startup: drive LOW first. Neither boot ROM nor upstream
    // power supply states are guaranteed by software.
    gpio_init(kTxPin);
    gpio_put(kTxPin, 0);
    gpio_set_dir(kTxPin, GPIO_OUT);
    gpio_pull_down(kTxPin);
    armed = false;
    alreadyFired = false;
    inputLine.reserve(48);
    ready = configurePio();
    Serial.begin(115200);
    Serial.println(ready ? "KNX076 READY_IDLE_LOW_NO_AUTO_PULSES" :
                           "KNX076 PIO_INIT_FAILED_NO_FIRE_ALLOWED");
    printStatus();
}
void loop() {
    if (armed && (uint32_t)(millis() - armedAt) >= kArmWindowMs) {
        disarm();
        Serial.println("KNX076 ARM_TIMEOUT_DISARMED");
    }
    while (Serial.available()) {
        char ch = (char)Serial.read();
        if (ch == '\r') continue;
        if (ch == '\n') {
            executeCommand(inputLine);
            inputLine = "";
        } else if (inputLine.length() < 46) {
            inputLine += ch;
        } else {
            inputLine = "";
            disarm();
            Serial.println("KNX076 INPUT_OVERFLOW_DISARMED");
        }
    }
}
