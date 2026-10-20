// KNX099: Replay REAL KNX097 INA219 motor traces through the new
// portable homing/position state machine. No USB, GPIO or actuator APIs.
#include "../../lib/common/knx099_m1_position_model.hpp"
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
using namespace Knx099;

static const int cutoffMs[6]={24423,22767,24479,22815,24263,22671};
static const size_t counts[6]={3053,2846,3060,2852,3033,2834};

static std::string pathJoin(const std::string& dir,const std::string& file)
{
    if(dir.empty())return file;
    return dir + "\\" + file;
}

static void replay(const std::string& data, int i)
{
    const bool isR=(i%2==0);
    const Direction direction=isR?Direction::R:Direction::F;
    const std::string path=pathJoin(data,std::string("KNX097_LEG_0")+
                          static_cast<char>('1'+i)+"_"+(isR?"R":"F")+".csv");
    std::ifstream in(path);
    if(!in) {
        std::cerr<<"Missing original trace "<<path<<"\n";
        std::exit(20);
    }
    Model model;
    const Sample idle{true,false,true,3292,0};
    const Action a=model.requestReference(direction,0,idle,true,true);
    assert(a.type==(isR?ActionType::StartR:ActionType::StartF));
    assert(model.acknowledgeStarted(0,direction).type==ActionType::None);
    std::string line;
    std::getline(in,line); // header: ms,shunt_raw,shunt_uV,bus_mv,valid,ma
    size_t count=0;
    int last=-1;
    bool stopped=false;
    while(std::getline(in,line))
    {
        if(line.empty())continue;
        std::stringstream s(line);
        std::string cell;
        std::string col[6];
        for(int k=0;k<6;k++) {
            assert(static_cast<bool>(std::getline(s,cell,',')));
            col[k]=cell;
        }
        const int t=std::stoi(col[0]);
        const int raw=std::stoi(col[1]);
        const int uv=std::stoi(col[2]);
        const int mv=std::stoi(col[3]);
        const bool valid=col[4]=="True";
        const double milliamps=std::stod(col[5]);
        assert(valid && raw*10==uv && std::abs(milliamps-raw/20.0)<0.0001);
        assert(t>=7 && (last<0 || t-last==8));
        const Sample sample{valid,false,true,mv,raw/20};
        const Action next=model.tick(static_cast<uint32_t>(t),sample);
        if(next.type==ActionType::Stop) {
            assert(!stopped);
            assert(next.reason==StopReason::EndstopCandidate);
            assert(t==cutoffMs[i]);
            stopped=true;
        }
        else
            assert(next.type==ActionType::None);
        last=t;
        ++count;
    }
    assert(count==counts[i]);
    assert(last==cutoffMs[i]);
    assert(stopped);
    assert(model.snapshot().phase==Phase::StopPending);
    assert(!model.acknowledgeAllOff(false));
    assert(model.acknowledgeAllOff(true));
    assert(model.snapshot().phase==Phase::Idle);
    assert(model.snapshot().evidence==Evidence::CurrentEndstopCandidate);
    assert(model.positionTowardR()==(isR?1000:0));
    std::cout<<"KNX099 REAL TRACE LEG "<<(i+1)<<" "<<(isR?"R":"F")
             <<" "<<last<<"ms "<<count<<" INA samples: MATCH\n";
}

int main(int argc,char** argv)
{
    if(argc!=2) {
        std::cerr<<"Usage: knx099_replay.exe <KNX097_private_runtime_dir>\n";
        return 2;
    }
    for(int i=0;i<6;i++)replay(argv[1],i);
    std::cout<<"KNX099 REAL 6/6 CURRENT ENDPOINT REPLAYS PASS\n";
    return 0;
}
