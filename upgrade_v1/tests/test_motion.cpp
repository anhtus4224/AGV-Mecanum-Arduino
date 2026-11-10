#include <cassert>
#include <iostream>
#include "../mega_vector_v1/VectorMotion.h"
int main(){
 int w[4];vmMix(255,0,0,255,w);for(int i:w)assert(i==255);
 vmMix(255,130,0,255,w);assert(w[0]==255&&w[3]==255);assert(w[1]>0&&w[1]<w[0]&&w[1]==w[2]);
 vmMix(0,-255,0,255,w);assert(w[0]==-255&&w[1]==255&&w[2]==255&&w[3]==-255);
 vmMix(0,0,-255,255,w);assert(w[0]==-255&&w[1]==255&&w[2]==-255&&w[3]==255);
 for(int f=-255;f<=255;f+=51)for(int s=-255;s<=255;s+=51)for(int r=-255;r<=255;r+=51){vmMix(f,s,r,255,w);for(int a:w)assert(abs(a)<=255);}
 assert(vmRamp(3,-80,8)==0);assert(vmRamp(0,-80,8)==-8);
 VmAvoid a;a.start(10);a.choose(90,90,100,100,20);assert(a.phase==VmAvoid::FAULT);
 a.enabled=true;a.start(30);a.choose(10,10,100,100,40);assert(a.phase==VmAvoid::FAULT);
 a.start(50);a.choose(80,90,100,100,60);assert(a.phase==VmAvoid::OUT);
 int f,s;VmRange good={100,100},near={40,100},bad={999,100};
 a.tick(110,good,good,near,good,false,f,s);assert(a.phase==VmAvoid::PASS&&f>0);
 // Missing echo must stop, never be treated as the object's far edge.
 a.tick(120,good,good,bad,good,false,f,s);assert(a.phase==VmAvoid::FAULT);
 a.enter(VmAvoid::RETURN,200);a.tick(210,good,good,near,good,true,f,s);assert(a.phase==VmAvoid::CENTER);
 good.at=near.at=220;a.tick(220,good,good,near,good,false,f,s);assert(a.phase==VmAvoid::RETURN);
 a.enter(VmAvoid::CENTER,230);good.at=near.at=240;a.tick(240,good,good,near,good,true,f,s);
 good.at=near.at=330;a.tick(330,good,good,near,good,true,f,s);assert(a.phase==VmAvoid::HANDOFF);
 // Full bounded demonstration: valid edge samples, return, then A2 handoff.
 a.start(1000);a.choose(80,90,100,100,1000);
 good.at=near.at=1010;a.tick(1010,good,good,near,good,false,f,s);assert(a.phase==VmAvoid::PASS);
 for(uint32_t t=1800;t<=2000;t+=100){VmRange edge={70,t};good.at=t;a.tick(t,good,good,edge,good,false,f,s);}
 assert(a.phase==VmAvoid::RETURN);
 good.at=near.at=2010;a.tick(2010,good,good,near,good,true,f,s);
 good.at=near.at=2020;a.tick(2020,good,good,near,good,true,f,s);
 good.at=near.at=2110;a.tick(2110,good,good,near,good,true,f,s);assert(a.phase==VmAvoid::HANDOFF);
 a.enter(VmAvoid::RETURN,2200);good.at=near.at=2201;a.tick(2201,good,bad,near,good,false,f,s);assert(a.phase==VmAvoid::FAULT);
 std::cout<<"Motion: mixer, reversal, corridor rejection, invalid echo, A2 stability OK\n";
}
