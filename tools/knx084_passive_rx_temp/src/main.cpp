// KNX084 - passive KNX TP RX + ATtiny3216 temperature UART diagnostic.
// KNX bus is LIVE on cellar line 1.3. DO NOT drive GPIO0 HIGH.
// M1..M8 TB6612 enables and common direction outputs are ALWAYS LOW.
// No KNX TX PIO, TPUart, Serial1, ACK generation, motor PWM or drive commands.
// NOTE: firmware cannot guarantee GPIO0 and motor levels during BOOTSEL/reset.
// The board's U11/D1/F1/CN1 and multi-source supply gates remain unresolved.
#include <Arduino.h>
#include "hardware/gpio.h"
#include "../../../lib/common/temperature_protocol.hpp"
#include <stdio.h>
#include <string.h>
#ifndef ARDUINO_ARCH_RP2040
#error "KNX084 requires an RP2040 board"
#endif
#ifndef KNX084_RECEIVE_TEMP_ONLY
#error "KNX084 must be built in the isolated receive/temp-only environment"
#endif

namespace {
constexpr uint8_t kKnxTx=0;       // STKNX U9 pin24, active HIGH, idle LOW
constexpr uint8_t kKnxRx=1;       // STKNX U9 pin23, input only
constexpr uint8_t kAttinyTx=8;    // RP GPIO8 UART1 TX -> ATtiny PA2 RX
constexpr uint8_t kAttinyRx=9;    // RP GPIO9 UART1 RX <- ATtiny PA1 TX
constexpr uint8_t kMotorEnables[8]={10,11,12,13,14,15,16,17};
constexpr uint8_t kMotorDirection[2]={18,19};
constexpr uint32_t kUartBaud=115200;
constexpr uint32_t kFirstPollMs=3500;
constexpr uint32_t kPollIntervalMs=2100;
constexpr uint32_t kReplyTimeoutMs=1300;
constexpr uint32_t kStatusIntervalMs=5000;
constexpr unsigned kRxRingCapacity=4096;
static_assert((kRxRingCapacity&(kRxRingCapacity-1))==0,"RX ring must be power-of-two");
struct RxEdge {uint32_t timeUs;uint8_t level;};
static_assert(sizeof(RxEdge)==8,"RX edge layout changed");
volatile RxEdge rxBuffer[kRxRingCapacity]={};
volatile unsigned rxWrite=0;
volatile unsigned rxRead=0;
volatile uint32_t rxLost=0;
volatile uint32_t rxTotal=0;
volatile uint32_t rxRises=0;
volatile uint32_t rxFalls=0;
volatile uint32_t rxLastUs=0;
bool rxDump=false;

TemperatureProtocol::Parser tempParser;
TemperatureProtocol::Snapshot latestSnapshot{};
bool hasSnapshot=false;
bool uartReady=false;
bool requestOutstanding=false;
uint32_t requestAtMs=0;
uint32_t lastPollMs=0;
uint32_t lastUartByteMs=0;
uint32_t lastStatusMs=0;
uint32_t tempAccepted=0;
uint32_t tempRejected=0;
uint32_t tempTimeout=0;
uint32_t tempRxBytes=0;
uint8_t nextSeq=0;
uint8_t pendingSeq=0;
char inputLine[32]={};
uint8_t inputLength=0;

void outputLow(uint8_t pin) {
    // Explicitly preload LOW before enabling SIO output driver.
    gpio_init(pin);
    gpio_put(pin,0);
    gpio_set_dir(pin,GPIO_OUT);
    gpio_pull_down(pin);
}
void forceAllInactive() {
    // This code path NEVER writes a HIGH value to any KNX or motor output.
    gpio_put(kKnxTx,0);
    for(uint8_t pin:kMotorEnables)gpio_put(pin,0);
    for(uint8_t pin:kMotorDirection)gpio_put(pin,0);
}
bool motorsLow() {
    for(uint8_t pin:kMotorEnables)if(gpio_get(pin))return false;
    for(uint8_t pin:kMotorDirection)if(gpio_get(pin))return false;
    return true;
}
void isrKnxRx() {
    const uint8_t level=digitalRead(kKnxRx)?1:0;
    const uint32_t t=micros();
    ++rxTotal;
    if(level)++rxRises;else ++rxFalls;
    rxLastUs=t;
    const unsigned next=(rxWrite+1u)&(kRxRingCapacity-1u);
    if(next==rxRead) {
        ++rxLost;
        return;
    }
    rxBuffer[rxWrite].timeUs=t;
    rxBuffer[rxWrite].level=level;
    rxWrite=next;
}
void printRxStats() {
    uint32_t e,r,f,l,t;
    unsigned buffered;
    noInterrupts();
    e=rxTotal;r=rxRises;f=rxFalls;l=rxLost;t=rxLastUs;
    buffered=(rxWrite-rxRead)&(kRxRingCapacity-1u);
    interrupts();
    if(!Serial)return;
    Serial.print(F("KNX084 RXSTATS edges="));Serial.print(e);
    Serial.print(F(" rises="));Serial.print(r);
    Serial.print(F(" falls="));Serial.print(f);
    Serial.print(F(" lost="));Serial.print(l);
    Serial.print(F(" buffered="));Serial.print(buffered);
    Serial.print(F(" last_us="));Serial.print(t);
    Serial.print(F(" current_level="));Serial.println(digitalRead(kKnxRx)?1:0);
}
void printStatus() {
    if(!Serial)return;
    Serial.print(F("KNX084 STATUS tx_low="));
    Serial.print(gpio_get(kKnxTx)==0?1:0);
    Serial.print(F(" motors_low="));Serial.print(motorsLow()?1:0);
    Serial.print(F(" uart_ready="));Serial.print(uartReady?1:0);
    Serial.print(F(" snapshots="));Serial.print(tempAccepted);
    Serial.print(F(" timeout="));Serial.print(tempTimeout);
    Serial.print(F(" rejected="));Serial.print(tempRejected);
    Serial.print(F(" rx_edges="));Serial.print(rxTotal);
    Serial.println(F(" NO_KNX_TX_NO_MOTOR_ACTUATION"));
}
const char *faultName(uint8_t fault) {
    switch(fault) {
      case 0:return "None";
      case 1:return "NoSensor";
      case 2:return "ParasitePower";
      case 3:return "ReadFailed";
      case 4:return "PowerOn85";
      case 5:return "OutsideRange";
      case 6:return "SampleStale";
      case 7:return "NoSample";
      case 8:return "Recovering";
      default:return "InvalidFault";
    }
}
bool channelFresh(const TemperatureProtocol::Channel& ch) {
    return (ch.flags&0x03)==0x03 &&
           (ch.flags&0x18)==0 &&
           ch.fault==0 && ch.ageSeconds!=0xFFFF && ch.ageSeconds<=30;
}
void printTemps() {
    if(!Serial)return;
    if(!hasSnapshot) {
        Serial.println(F("KNX084 TEMPS NO_SNAPSHOT_YET"));
        return;
    }
    unsigned valid=0,missing=0,faults=0;
    for(uint8_t n=0;n<TemperatureProtocol::Channels;++n){
        const auto &c=latestSnapshot.channels[n];
        if(channelFresh(c))++valid;
        if(c.fault==1 && !(c.flags&0x02))++missing;
        if(c.fault)++faults;
    }
    Serial.print(F("KNX084 SNAPSHOT seq="));Serial.print(pendingSeq);
    Serial.print(F(" attiny_up_ms="));Serial.print(latestSnapshot.uptimeMs);
    Serial.print(F(" valid_all9="));Serial.print(valid);
    Serial.print(F(" no_sensor_all9="));Serial.print(missing);
    Serial.print(F(" faults_all9="));Serial.print(faults);
    Serial.print(F(" accepted="));Serial.print(tempAccepted);
    Serial.print(F(" timeout="));Serial.print(tempTimeout);
    Serial.print(F(" rejected="));Serial.println(tempRejected);
    // Deliberately report T0-T3 only. Never interpret an invalid raw 0 as 0 deg C.
    for(uint8_t n=0;n<4;++n){
        const auto& c=latestSnapshot.channels[n];
        Serial.print(F("KNX084 CH T"));Serial.print(n);
        Serial.print(F(" valid="));Serial.print(channelFresh(c)?1:0);
        Serial.print(F(" temp_c="));
        if(channelFresh(c))Serial.print(c.centiC/100.0f,2);
        else Serial.print(F("NA"));
        Serial.print(F(" flags="));Serial.print(c.flags);
        Serial.print(F(" fault="));Serial.print(c.fault);
        Serial.print(F(" fault_name="));Serial.print(faultName(c.fault));
        Serial.print(F(" age_s="));Serial.println(c.ageSeconds);
    }
}
void readOnlyCommand(const char *cmd) {
    if(strcmp(cmd,"STATUS")==0) printStatus();
    else if(strcmp(cmd,"TEMPS")==0) printTemps();
    else if(strcmp(cmd,"RXSTATS")==0) printRxStats();
    else if(strcmp(cmd,"RXDUMP")==0) {
        rxDump=true; // USB dump of already-captured input edges only
        if(Serial)Serial.println(F("KNX084 RXDUMP_START PASSIVE_ONLY"));
    }
    else if(strcmp(cmd,"HELP")==0){
        if(Serial)Serial.println(F("KNX084 COMMANDS STATUS TEMPS RXSTATS RXDUMP HELP"));
    }
    else if(Serial)Serial.println(F("KNX084 REFUSED_UNRECOGNIZED_OR_ACTUATING_COMMAND"));
}
void pollUsb() {
    for(unsigned n=0;n<32 && Serial.available()>0;++n){
        int c=Serial.read();
        if(c<0)break;
        if(c=='\r')continue;
        if(c=='\n'){
            inputLine[inputLength]=0;
            readOnlyCommand(inputLine);
            inputLength=0;
        } else if(c>=32 && c<=126 && inputLength<sizeof(inputLine)-1){
            inputLine[inputLength++]=static_cast<char>(c);
        } else {
            inputLength=0;
            if(Serial)Serial.println(F("KNX084 REFUSED_BAD_COMMAND_INPUT"));
        }
    }
}
void drainRxToUsb() {
    if(!rxDump || !Serial)return;
    for(unsigned n=0;n<48;++n){
        RxEdge e{};bool have=false;
        noInterrupts();
        if(rxRead!=rxWrite){
            e.timeUs=rxBuffer[rxRead].timeUs;
            e.level=rxBuffer[rxRead].level;
            rxRead=(rxRead+1u)&(kRxRingCapacity-1u);
            have=true;
        }
        interrupts();
        if(!have) {
            rxDump=false;
            Serial.println(F("KNX084 RXDUMP_END"));
            return;
        }
        Serial.print(F("KNX084 RXEDGE t_us="));Serial.print(e.timeUs);
        Serial.print(F(" level="));Serial.println(e.level);
    }
}
void pollTemperature() {
    if(!uartReady)return;
    const uint32_t now=millis();
    if(tempParser.inProgress() &&
       static_cast<uint32_t>(now-lastUartByteMs)>TemperatureProtocol::MaxInterByteGapMs)
        tempParser.reset();

    for(uint8_t n=0;n<64 && Serial2.available()>0;++n){
        const int next=Serial2.read();
        if(next<0)break;
        ++tempRxBytes;
        lastUartByteMs=millis();
        TemperatureProtocol::Frame frame{};
        if(!tempParser.feed(static_cast<uint8_t>(next),frame))continue;
        if(!requestOutstanding ||
           frame.type!=TemperatureProtocol::SnapshotResponse ||
           frame.sequence!=pendingSeq) {
            ++tempRejected;
            continue;
        }
        TemperatureProtocol::Snapshot snapshot{};
        if(!TemperatureProtocol::decodeSnapshot(frame,snapshot)){
            ++tempRejected;
            continue;
        }
        latestSnapshot=snapshot;
        requestOutstanding=false;
        hasSnapshot=true;
        ++tempAccepted;
        printTemps();
    }

    if(requestOutstanding &&
       static_cast<uint32_t>(now-requestAtMs)>kReplyTimeoutMs){
        requestOutstanding=false;
        ++tempTimeout;
        if(Serial) {
            Serial.print(F("KNX084 TEMP_TIMEOUT seq="));
            Serial.print(pendingSeq);
            Serial.print(F(" total="));Serial.println(tempTimeout);
        }
    }
    if(now<kFirstPollMs || requestOutstanding ||
       (lastPollMs && static_cast<uint32_t>(now-lastPollMs)<kPollIntervalMs))
        return;

    uint8_t request[TemperatureProtocol::FrameOverhead]={};
    const uint8_t sequence=++nextSeq;
    const size_t length=TemperatureProtocol::encodeRequest(sequence,request,sizeof(request));
    // Arduino-Pico 5.5.0 SerialUART::availableForWrite() is Boolean (0/1), not bytes.
    if(length!=8 || Serial2.availableForWrite()<=0)return;
    if(Serial2.write(request,length)!=length)return;
    lastPollMs=millis();
    requestAtMs=lastPollMs;
    pendingSeq=sequence;
    requestOutstanding=true;
}
} // namespace

void setup() {
    // First actions under firmware control: never expose a HIGH on KNX TX or motors.
    outputLow(kKnxTx);
    for(uint8_t pin:kMotorEnables)outputLow(pin);
    for(uint8_t pin:kMotorDirection)outputLow(pin);
    forceAllInactive();
    pinMode(kKnxRx,INPUT); // U9 actively drives KNX RX, do NOT pull HIGH.
    Serial.begin(115200); // USB only; no KNX transmit facility.
    const bool txConfigured=Serial2.setTX(kAttinyTx);
    const bool rxConfigured=Serial2.setRX(kAttinyRx);
    uartReady=txConfigured && rxConfigured;
    if(uartReady)Serial2.begin(kUartBaud);
    lastUartByteMs=millis();
    attachInterrupt(digitalPinToInterrupt(kKnxRx),isrKnxRx,CHANGE);
    lastStatusMs=millis()-kStatusIntervalMs;
}

void loop() {
    pollTemperature();
    pollUsb();
    drainRxToUsb();
    // Reassert both safety states periodically; command handlers can never enable them.
    static uint32_t lastOffMs=0;
    const uint32_t now=millis();
    if(static_cast<uint32_t>(now-lastOffMs)>100){
        forceAllInactive();
        lastOffMs=now;
    }
    if(static_cast<uint32_t>(now-lastStatusMs)>=kStatusIntervalMs){
        lastStatusMs=now;
        if(Serial){
            Serial.println(F("KNX084 PASSIVE_KNX_RX_AND_ATtiny_TEMPERATURES"));
            printStatus();
            printRxStats();
        }
    }
}
