// Native KNX085 motor safety state transitions, no GPIO/KNX/hardware needed.
#include "../../tools/knx085_motor_diag/src/motor_gate.hpp"
#include <cassert>
#include <iostream>
using namespace Knx085;
int main() {
    InaSample healthy{true,false,3300,0};
    InaSample undervolt{true,false,2800,0};
    InaSample overcurrent{true,false,3300,121};
    InaSample missing{};
    MotorGate m;
    assert(!m.arm(0,false,healthy) && m.state()==Phase::Idle);
    assert(!m.arm(0,true,missing));
    assert(!m.arm(0,true,undervolt));
    assert(m.arm(10,true,healthy));
    assert(!m.arm(11,true,healthy)); // no re-arm while armed
    assert(!m.start(12,3,'F',100,true,healthy)); // M3 forbidden
    assert(!m.start(12,2,'X',100,true,healthy));
    assert(!m.start(12,2,'R',49,true,healthy));
    assert(!m.start(12,2,'R',251,true,healthy));
    assert(!m.start(12,2,'R',100,false,healthy));
    assert(m.start(12,1,'F',100,true,healthy));
    assert(m.active() && m.channel()==1 && m.direction()=='F');
    assert(!m.start(13,2,'R',100,true,healthy)); // no concurrent channel
    m.tick(50,true,healthy);
    assert(m.active());
    m.tick(112,true,healthy);
    assert(m.state()==Phase::Idle && !m.active());
    assert(m.arm(200,true,healthy));
    m.tick(5201,true,healthy);
    assert(m.state()==Phase::Idle); // arm lease expires
    assert(m.arm(7000,true,healthy));
    assert(!m.start(12001,1,'F',100,true,healthy));
    m.stop();
    assert(m.arm(9000,true,healthy));
    assert(m.start(9001,2,'R',80,true,healthy));
    assert(m.channel()==2);
    m.tick(9010,true,overcurrent);
    assert(m.state()==Phase::Fault && !m.active());
    assert(!m.arm(9020,true,healthy));
    assert(!m.clearFault(undervolt));
    assert(m.clearFault(healthy));
    assert(m.state()==Phase::Idle);
    assert(m.arm(11000,true,healthy));
    assert(m.start(11001,1,'F',50,true,healthy));
    m.tick(11002,false,healthy); // USB loss => fault immediately
    assert(m.state()==Phase::Fault);
    m.stop(); // manual STOP wins even in fault
    assert(m.state()==Phase::Idle);
    assert(m.arm(0xfffffffeu,true,healthy));
    assert(m.start(1u,2,'F',100,true,healthy)); // millis wrap
    m.tick(101u,true,healthy);
    assert(m.state()==Phase::Idle);
    InaSample reverse{true,false,3300,-6};
    assert(!powerOkay(reverse,false));
    assert(!powerOkay(overcurrent,false));
    assert(powerOkay(healthy,true));
    std::cout<<"KNX085 MOTOR_GATE 25+ checks PASS\n";
}
