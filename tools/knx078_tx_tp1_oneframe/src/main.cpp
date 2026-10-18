// KNX078: exactly one deliberately authorized TP1 frame on GPIO0 -> STKNX.
// Fixed 1.0.250 -> 29/7/241, GroupValueWrite 0, STANDARD frame
// BC 10 FA EF F1 D1 00 80 E6 (checksum XOR FF).
// No frame / no pulse on boot or serial STATUS. ARM FRAME + FIRE FRAME only.
// Hardware PIO bit cell=104us, logical0: GPIO0 HIGH35us then LOW69us,
// logical1: GPIO0 LOW104us. 9 chars x 13 bits =117 bits.
// No retransmissions. Enforces minimum 10ms KNX_RX quiet preflight, optionally
// aborts immediately on unexpected remote KNX_RX rising during logical1.
// This experimental direct PHY is NOT a KNX-certified link layer.
#include <Arduino.h>
#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/pio.h"
#include "hardware/pio_instructions.h"
#include "pico/time.h"

namespace {
constexpr uint kTxPin = 0;
constexpr uint kRxPin = 1;
constexpr uint32_t kArmTtlMs = 4000;
constexpr uint32_t kIdleFreeUs = 10000;  // conservative >53*104us incl last char stop
constexpr float kPioHz = 1000000.0f;
constexpr int kRxLogCapacity = 384;
constexpr int kFrameOctets = 9;
constexpr int kFrameBits = 117;
constexpr int kFifoWords = 4;
const uint8_t kFrame[kFrameOctets] = {0xBC,0x10,0xFA,0xEF,0xF1,0xD1,0x00,0x80,0xE6};
const uint32_t kGoldenWords[kFifoWords] = {
    0x2C3BE087,0x01D01088,0xF8FFC4BA,0x00003307,
};

// PIO 0: OUT X,1 (autopull threshold 32, LSB-first), then JMP !X idle.
// High path 1+16+16+2 = 35us HIGH, then deassert LOW.
// Both high/idle branches are exactly 37us, common 65us, prelude 2us.
// 2+37+65 = 104us per cell. Absolute JMP addresses are relocated by SDK.
const uint16_t kInstructions[] = {
    pio_encode_out(pio_x,1),              //  0: 1us
    pio_encode_jmp_not_x(8),             //  1: 1us
    pio_encode_set(pio_pins,1),          //  2: 1us HIGH
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), //  3 16us HIGH
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), //  4 16us HIGH
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(1)),  //  5 2us HIGH
    pio_encode_set(pio_pins,0),          //  6 LOW, 1us
    pio_encode_jmp(13),                  //  7 1us
    pio_encode_set(pio_pins,0),          //  8 LOW, 1us
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), //  9 16us LOW
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), // 10 16us LOW
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(2)),  // 11 3us LOW
    pio_encode_jmp(13),                  // 12 1us
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), // 13 16us LOW
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), // 14 16us LOW
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), // 15 16us LOW
    static_cast<uint16_t>(pio_encode_nop()|pio_encode_delay(15)), // 16 16us LOW
    pio_encode_nop(),                    // 17 1us LOW
};
const pio_program kProgram={
    kInstructions,
    static_cast<uint16_t>(sizeof(kInstructions)/sizeof(kInstructions[0])),
    -1
};
PIO kPio=pio0;
int sm=-1;
bool ready=false;
bool armed=false;
bool attempted=false;
uint32_t armAtMs=0;
volatile uint32_t lastRxActivityUs=0;
volatile bool transmitting=false;
volatile bool collisionDetected=false;
volatile uint32_t collisionAtUs=0;
volatile uint32_t lastTxEdgeUs=0;
volatile uint32_t lastOwnFallingUs=0;
struct Edge {uint32_t usec;uint8_t level;};
Edge edgeLog[kRxLogCapacity];
volatile uint16_t edgeCount=0;
volatile uint16_t edgeOverflow=0;
volatile uint16_t unexpectedRises=0;
String commandBuffer;

void forceLow() {
    gpio_set_function(kTxPin,GPIO_FUNC_SIO);
    gpio_put(kTxPin,0);
    gpio_set_dir(kTxPin,GPIO_OUT);
}
void stopTxFromIsr(uint32_t now) {
    if (collisionDetected) return;
    collisionDetected=true;
    collisionAtUs=now;
    if (sm >= 0) pio_sm_set_enabled(kPio,static_cast<uint>(sm),false);
    forceLow();
}
void onPinIrq(uint gpio,uint32_t events) {
    uint32_t now=time_us_32();
    if(gpio==kTxPin) {
        lastTxEdgeUs=now;
        if (events & GPIO_IRQ_EDGE_FALL) lastOwnFallingUs=now;
        return;
    }
    if(gpio!=kRxPin) return;
    lastRxActivityUs=now;
    uint8_t level=(events & GPIO_IRQ_EDGE_RISE)?1:0;
    if(transmitting) {
        uint16_t slot=edgeCount;
        if (slot < kRxLogCapacity) {
            edgeLog[slot]={now,level};
            edgeCount=slot+1;
        } else if(edgeOverflow<65535) ++edgeOverflow;
        // A second sender's pulse during a logical 1 is a collision. Allow
        // <7us echo tail after our own TX output fall before deciding.
        // Side-effect is fail-LOW; false positive abort is safer than overload.
        if(level && !gpio_get(kTxPin) && (uint32_t)(now-lastOwnFallingUs)>7) {
            ++unexpectedRises;
            stopTxFromIsr(now);
        }
    }
}
void status() {
    Serial.print("KNX078 STATUS tx_low=");
    Serial.print(gpio_get(kTxPin)==0?"1":"0");
    Serial.print(" pio_ready=");Serial.print(ready?"1":"0");
    Serial.print(" armed=");Serial.print(armed?"1":"0");
    Serial.print(" attempted=");Serial.print(attempted?"1":"0");
    Serial.print(" collision=");Serial.print(collisionDetected?"1":"0");
    Serial.print(" rx_edges=");Serial.print(edgeCount);
    Serial.println(" FIXED_SRC_1.0.250_TO_GA29/7/241_VAL0");
}
bool frameAndWordsValid(){
    uint8_t x=0;
    for(uint8_t c:kFrame) x^=c;
    if(x!=0xFF) return false;
    uint32_t actual[kFifoWords]={};
    int bitpos=0;
    for(int idx=0;idx<kFrameOctets;++idx){
        uint8_t data=kFrame[idx];
        int bits[13]={};
        bits[0]=0;
        for(int j=0;j<8;++j)bits[j+1]=(data>>j)&1;
        bits[9]=__builtin_popcount(static_cast<unsigned>(data)) & 1;
        bits[10]=bits[11]=bits[12]=1;
        for(int j=0;j<13;++j,++bitpos)
            if(bits[j]==0) actual[bitpos/32]|=(1u<<(bitpos%32));
    }
    if(bitpos!=kFrameBits)return false;
    for(int i=0;i<kFifoWords;++i)
        if(actual[i]!=kGoldenWords[i])return false;
    return true;
}
bool initPio(){
    if(!pio_can_add_program(kPio,&kProgram))return false;
    sm=pio_claim_unused_sm(kPio,false);
    if(sm<0)return false;
    uint offset=pio_add_program(kPio,&kProgram);
    pio_sm_config cfg=pio_get_default_sm_config();
    sm_config_set_wrap(&cfg,offset,offset+17);
    sm_config_set_set_pins(&cfg,kTxPin,1);
    sm_config_set_out_shift(&cfg,true,true,32);
    sm_config_set_clkdiv(&cfg,static_cast<float>(clock_get_hz(clk_sys))/kPioHz);
    pio_sm_init(kPio,static_cast<uint>(sm),offset,&cfg);
    pio_sm_set_enabled(kPio,static_cast<uint>(sm),false);
    pio_sm_clear_fifos(kPio,static_cast<uint>(sm));
    pio_gpio_init(kPio,kTxPin);
    pio_sm_set_consecutive_pindirs(kPio,static_cast<uint>(sm),kTxPin,1,true);
    pio_sm_set_enabled(kPio,static_cast<uint>(sm),true);
    return true;
}
bool busIsQuiet() {
    const uint32_t now=time_us_32();
    return gpio_get(kRxPin)==0 &&
        (uint32_t)(now-lastRxActivityUs)>=kIdleFreeUs;
}
void fireFrame() {
    if(!armed || attempted || (uint32_t)(millis()-armAtMs)>=kArmTtlMs){
        armed=false;
        Serial.println("KNX078 REFUSED_NOT_ARMED_OR_USED");
        return;
    }
    // Lock any repeat attempt even if the next bus-free gate rejects firing.
    armed=false;
    attempted=true;
    if(!ready||!frameAndWordsValid()||collisionDetected||!busIsQuiet()||
       gpio_get(kTxPin)||!pio_sm_is_tx_fifo_empty(kPio,static_cast<uint>(sm))){
        Serial.println("KNX078 NO_TRANSMISSION_PREFLIGHT_FAIL_LOCKED");
        status();
        return;
    }
    noInterrupts();
    edgeCount=0;
    edgeOverflow=0;
    collisionDetected=false;
    unexpectedRises=0;
    transmitting=true;
    interrupts();
    Serial.println("KNX078 FIRING_FIXED_FRAME_ONCE BC10FAEFF1D10080E6");
    Serial.flush();
    // Recheck immediately after the serial flush, because the bus may have
    // changed between the initial gate and the actual PIO start.
    if(!busIsQuiet() || collisionDetected){
        transmitting=false;
        Serial.println("KNX078 ABORTED_BUS_BECAME_BUSY_PRE_START");
        return;
    }
    for(int w=0;w<kFifoWords;++w) {
        if(collisionDetected)break;
        pio_sm_put_blocking(kPio,static_cast<uint>(sm),kGoldenWords[w]);
    }
    // Last frame bit is done at t~12.168ms. Remaining padding is idle LOW.
    sleep_ms(13);
    transmitting=false;             // permits remote ACK (no collision flag)
    sleep_ms(18);                    // let ACK/NAK arrive
    forceLow();                      // stop PIO and leave MCU GPIO0 held LOW
    if(sm>=0)pio_sm_set_enabled(kPio,static_cast<uint>(sm),false);
    Serial.print("KNX078 FRAME_TX_COMPLETED_ONCE collision=");
    Serial.print(collisionDetected?"1":"0");
    Serial.print(" unexpected_rx_rises=");Serial.print(unexpectedRises);
    Serial.print(" edge_overflows=");Serial.println(edgeOverflow);
    status();
}
void cmd(String s){
    s.trim();
    if(s=="STATUS")status();
    else if(s=="ARM FRAME") {
        if(ready&&!attempted&&!armed&&!gpio_get(kTxPin)&&frameAndWordsValid()){
            armed=true;armAtMs=millis();
            Serial.println("KNX078 ARMED_4S_ONE_FIXED_FRAME");
        } else {
            armed=false;Serial.println("KNX078 ARM_REFUSED");
        }
    } else if(s=="FIRE FRAME")fireFrame();
    else if(s=="STOP"||s=="DISARM"){
        armed=false;Serial.println("KNX078 DISARMED_NO_TX");
    } else if(s=="RXLOG") {
        Serial.print("KNX078 RXLOG_COUNT ");Serial.println(edgeCount);
        for(uint16_t i=0;i<edgeCount;++i){
            Serial.print("E ");Serial.print(edgeLog[i].usec);
            Serial.print(" ");Serial.println(edgeLog[i].level);
        }
        Serial.println("KNX078 RXLOG_END");
    } else if(s.length()) {
        armed=false;Serial.println("KNX078 UNKNOWN_COMMAND_DISARMED");
    }
}
} // namespace

void setup() {
    gpio_init(kTxPin);
    gpio_put(kTxPin,0);
    gpio_set_dir(kTxPin,GPIO_OUT);
    gpio_pull_down(kTxPin);
    gpio_init(kRxPin);
    gpio_set_dir(kRxPin,GPIO_IN);
    gpio_pull_down(kRxPin);
    lastRxActivityUs=time_us_32();
    gpio_set_irq_enabled_with_callback(kRxPin,
        GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL,true,&onPinIrq);
    // Pin0 output IRQ is used to recognize our own falling edges when
    // classifying RX collisions. PIO GPIO0 remains a hardware-only output.
    gpio_set_irq_enabled(kTxPin,
        GPIO_IRQ_EDGE_RISE|GPIO_IRQ_EDGE_FALL,true);
    ready=frameAndWordsValid()&&initPio();
    commandBuffer.reserve(64);
    Serial.begin(115200);
    Serial.println(ready?
        "KNX078 READY_NO_AUTO_FRAMES_TX_LOW":
        "KNX078 ERROR_INIT_REFUSE_TX");
    status();
}
void loop(){
    if(armed && (uint32_t)(millis()-armAtMs)>=kArmTtlMs) {
        armed=false;Serial.println("KNX078 ARM_TIMED_OUT");
    }
    while(Serial.available()){
        char c=static_cast<char>(Serial.read());
        if(c=='\r')continue;
        if(c=='\n'){cmd(commandBuffer);commandBuffer="";}
        else if(commandBuffer.length()<60)commandBuffer+=c;
        else{
            commandBuffer="";armed=false;
            Serial.println("KNX078 INPUT_OVERFLOW_DISARMED");
        }
    }
}
