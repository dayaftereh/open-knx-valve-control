// KNX103: replay five REAL KNX101 INA219 complete current traces
// through the same C++17 KNX099 positional state machine as the firmware.
// NO USB, KNX, GPIO, or motor action. Input: private runtime data directory.
#include "../../lib/common/knx099_m1_position_model.hpp"
#include <cassert>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
using namespace Knx099;

struct Case {
    const char* file;
    Direction direction;
    uint16_t target;
    uint32_t cutoffMs;
    size_t samples;
    StopReason stop;
    Evidence evidence;
};
static const Case runs[]={
 {"KNX101_STEP_01_R.csv",Direction::R,1000,12951,1619,StopReason::EndstopCandidate,Evidence::CurrentEndstopCandidate},
 {"KNX101_STEP_02_F.csv",Direction::F,500,11383,1423,StopReason::TimedTarget,Evidence::TimedEstimate},
 {"KNX101_STEP_03_F.csv",Direction::F,250,5694,712,StopReason::TimedTarget,Evidence::TimedEstimate},
 {"KNX101_STEP_04_R.csv",Direction::R,750,12199,1525,StopReason::TimedTarget,Evidence::TimedEstimate},
 {"KNX101_STEP_05_F.csv",Direction::F,0,16599,2075,StopReason::EndstopCandidate,Evidence::CurrentEndstopCandidate},
};
static Sample idle() {return Sample{true,false,true,3292,0};}

int main(int argc,char** argv) {
    if(argc!=2) {std::cerr<<"KNX101 runtime dir required\n";return 3;}
    Model model;
    for(size_t i=0;i<sizeof(runs)/sizeof(runs[0]);i++) {
        const auto& c=runs[i];
        const bool seek=i==0 || i==4;
        const Action a=seek
           ? model.requestReference(c.direction,0,idle(),true,true)
           : model.requestTarget(c.target,0,idle(),true,true);
        assert(a.type==(c.direction==Direction::R?ActionType::StartR:ActionType::StartF));
        assert(model.acknowledgeStarted(0,c.direction).type==ActionType::None);
        const std::string file=std::string(argv[1])+"\\"+c.file;
        std::ifstream in(file);
        if(!in) {std::cerr<<"Cannot read "<<file<<"\n";return 5;}
        std::string line;
        assert(static_cast<bool>(std::getline(in,line)));
        assert(line=="ms,shunt_raw,shunt_uV,bus_mv,valid,ma");
        size_t count=0;
        int last=-1;
        bool hasStop=false;
        while(std::getline(in,line)) {
            if(line.empty())continue;
            std::stringstream stream(line);
            std::string cells[6];
            for(auto& cell:cells)
                assert(static_cast<bool>(std::getline(stream,cell,',')));
            const int ms=std::stoi(cells[0]);
            const int raw=std::stoi(cells[1]);
            const int uV=std::stoi(cells[2]);
            const int mv=std::stoi(cells[3]);
            const double mA=std::stod(cells[5]);
            assert(cells[4]=="True");
            assert(raw*10==uV);
            assert(std::abs(mA-raw/20.0)<1e-6);
            assert(ms>=0 && (last<0 || ms-last==8));
            assert(mv>=3100 && mv<=3450);
            const Sample sample{true,false,true,mv,raw/20};
            const Action action=model.tick(static_cast<uint32_t>(ms),sample);
            if(action.type==ActionType::Stop) {
                assert(!hasStop && ms==static_cast<int>(c.cutoffMs));
                assert(action.reason==c.stop);
                hasStop=true;
            } else {
                assert(action.type==ActionType::None);
            }
            last=ms;
            ++count;
        }
        assert(count==c.samples && last==static_cast<int>(c.cutoffMs) && hasStop);
        assert(model.phase()==Phase::StopPending);
        assert(!model.acknowledgeAllOff(false));
        assert(model.acknowledgeAllOff(true));
        const auto snap=model.snapshot();
        assert(snap.phase==Phase::Idle);
        assert(snap.estimatedPositionTowardR==c.target);
        assert(snap.evidence==c.evidence);
        std::cout<<"KNX103 REPLAY "<<i+1<<" "<<c.file
                 <<" "<<c.cutoffMs<<"ms "<<count<<" samples: PASS\n";
    }
    assert(model.snapshot().completedReferences==2);
    assert(model.snapshot().completedTimedSegments==3);
    assert(model.positionTowardR()==0);
    std::cout<<"KNX103 REAL 5/5 POSITIONED, 7354/7354 INA RAW SAMPLES: PASS\n";
    return 0;
}
