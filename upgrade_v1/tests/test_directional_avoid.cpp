#include "../mega_vector_v1/VectorMotion.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <initializer_list>
int main(){
 for(int cap:{80,120,160,200,255})for(int side:{-1,1}){
  VmAvoid a;a.enabled=true;a.cap=cap;a.start(100);
  a.choose(side<0?999:25,side<0?25:999,side<0?173:91,side<0?91:173,100);
  assert(a.phase==VmAvoid::OUT&&a.side==side&&a.selectionMode==2);
  VmRange front={181,110},back={999,110},left={side<0?999:25,110},right={side<0?25:999,110};
  int f,s,w[4]={0,0,0,0};
  // Reproduces V3 fault: opposite side 25, left/diagonal open. Background
  // ahead must not cause an immediate transition to straight driving.
  a.tick(110,front,back,left,right,false,f,s);
  assert(a.phase==VmAvoid::OUT&&f==120&&s==side*255);
  a.observeWheels(110,w);
  for(uint32_t t=120;t<1000;t+=10){
   front.at=left.at=right.at=t;
   a.observeWheels(t,w);a.tick(t,front,back,left,right,false,f,s);
   assert(a.phase==VmAvoid::OUT&&a.phaseTravel==0); // No issued lateral PWM, no PASS.
  }
  vmMix(f,s,0,cap,w);
  uint32_t t=1000;
  while(a.phase==VmAvoid::OUT&&t<25000){
   t+=10;front.at=left.at=right.at=t;
   a.observeWheels(t,w);a.tick(t,front,back,left,right,false,f,s);
  }
  assert(a.phase==VmAvoid::PASS&&a.outTravel>=35.5f);
  assert(t>2000); // Minimum travel scales down with cap, not one fixed short timer.
  // Confirm a side object, then three fresh edge readings; require body travel too.
  VmRange *near=side<0?&right:&left;
  near->cm=30;a.closest=30;a.seenSide=true;
  vmMix(255,0,0,cap,w);
  for(int i=0;i<3;i++){
   t+=80;front.at=left.at=right.at=t;near->cm=70;
   a.observeWheels(t,w);a.tick(t,front,back,left,right,false,f,s);
  }
  assert(a.phase==VmAvoid::PASS); // Edges alone cannot skip body length.
  while(a.phase==VmAvoid::PASS&&t<30000){
   t+=80;front.at=left.at=right.at=t;
   a.observeWheels(t,w);a.tick(t,front,back,left,right,false,f,s);
  }
  assert(a.phase==VmAvoid::RETURN);
  t+=10;front.at=left.at=right.at=t;
  a.tick(t,front,back,left,right,true,f,s);assert(a.phase==VmAvoid::RETURN); // Starting line cannot instantly hand off.
  a.phaseTravel=a.outTravel*.7f;
  t+=10;front.at=left.at=right.at=t;
  a.tick(t,front,back,left,right,true,f,s);assert(a.phase==VmAvoid::CENTER);
  for(int i=0;i<10;i++){t+=10;front.at=left.at=right.at=t;a.tick(t,front,back,left,right,true,f,s);}
  assert(a.phase==VmAvoid::HANDOFF);
 }
 VmAvoid a;a.enabled=true;
 a.start(100);a.choose(999,25,60,118,100);assert(a.phase==VmAvoid::FAULT);
 a.start(100);a.choose(999,8,173,91,100);assert(a.phase==VmAvoid::FAULT);
 a.start(100);a.choose(999,999,999,999,100);assert(a.phase==VmAvoid::FAULT);
 // Both side rays unknown is permissible only when a selected diagonal is confirmed.
 a.start(100);a.choose(999,999,173,999,100);assert(a.phase==VmAvoid::OUT&&a.side==-1);
 int f,s;VmRange good={181,110},unknown={999,110},tight={8,110};
 a.tick(110,good,unknown,unknown,tight,false,f,s);
 assert(a.phase==VmAvoid::FAULT&&!strcmp(a.fault,"CLEARANCE")&&a.faultPhase==VmAvoid::OUT);
 a.start(100);a.choose(999,25,173,91,100);good.at=110;unknown.at=0;
 a.tick(400,good,good,unknown,good,false,f,s);assert(a.phase==VmAvoid::FAULT);
 std::cout<<"V4: one-sided corridor, narrow opposite, five caps, issued-PWM travel, edge/body dwell, return and guards OK\n";
}
