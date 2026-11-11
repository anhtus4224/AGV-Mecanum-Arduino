#include "../mega_vector_v1/VectorMotion.h"
#include <cassert>
#include <cstring>
#include <iostream>
int main(){
 VmAvoid a;a.enabled=true;
 assert(a.halfWidth==23.5f&&a.frontOverhang==17&&a.rearOverhang==17&&a.margin==12);
 a.start(100);a.choose(50,50,100,100,100);assert(a.phase==VmAvoid::FAULT);
 a.start(200);a.choose(100,100,40,40,200);assert(a.phase==VmAvoid::FAULT);
 a.start(300);a.choose(100,100,100,100,300);assert(a.phase==VmAvoid::OUT);
 int f=0,s=0;VmRange good={100,310},near={25,310},unknown={999,310};
 a.tick(310,good,unknown,near,good,false,f,s);assert(a.phase==VmAvoid::OUT); // Moving away from rear, not toward it.
 a.enter(VmAvoid::RETURN,400);good.at=near.at=400;
 a.tick(400,good,good,near,good,false,f,s);assert(f==255&&s==0);
 good.at=near.at=600;a.tick(600,good,good,near,good,false,f,s);assert(f==188&&s==-127);
 good.at=near.at=800;a.tick(800,good,good,near,good,false,f,s);assert(f==120&&s==-255);
 VmRange tight={8,810};good.at=810;
 a.tick(810,good,good,tight,good,false,f,s);assert(a.phase==VmAvoid::FAULT);
 // Sensor inset must be added to margin, not body half-width.
 a.start(900);a.choose(100,100,100,100,900);a.leftInset=15;
 near={25,910};good.at=910;
 a.tick(910,good,good,near,good,false,f,s);assert(!strcmp(a.fault,"CLEARANCE"));
 a.leftInset=0;a.start(1000);a.choose(100,100,100,100,1000);good.at=1010;unknown.at=0;
 a.tick(1010,unknown,good,good,good,false,f,s);assert(!strcmp(a.fault,"SONAR_FRONT_UNKNOWN"));
 std::cout<<"V4: body corridor vs sensor-origin margin, gradual return, stale and close guards OK\n";
}
