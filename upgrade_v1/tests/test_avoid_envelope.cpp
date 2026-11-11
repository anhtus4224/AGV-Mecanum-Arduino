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
 int f=0,s=0;VmRange good={100,310},near={40,310},unknown={999,310};
 a.tick(310,good,unknown,near,good,false,f,s);
 assert(a.phase==VmAvoid::FAULT&&f==0&&s==0&&!strcmp(a.fault,"SONAR_REAR_UNKNOWN"));
 a.enter(VmAvoid::RETURN,400);good.at=near.at=400;
 a.tick(400,good,good,near,good,false,f,s);assert(f==255&&s==0);
 good.at=near.at=600;a.tick(600,good,good,near,good,false,f,s);assert(f==228&&s==-50);
 good.at=near.at=800;a.tick(800,good,good,near,good,false,f,s);assert(f==200&&s==-100);
 VmRange tight={35,810};good.at=810;
 a.tick(810,good,good,tight,good,false,f,s);assert(a.phase==VmAvoid::FAULT);
 a.enter(VmAvoid::RETURN,900);good.at=near.at=900;
 a.tick(900,unknown,good,near,good,false,f,s);assert(!strcmp(a.fault,"SONAR_FRONT_UNKNOWN"));
 a.enter(VmAvoid::RETURN,1000);good.at=near.at=1000;
 a.tick(1000,good,good,unknown,good,false,f,s);assert(!strcmp(a.fault,"SONAR_SIDE_UNKNOWN"));
 std::cout<<"Avoid: measured envelope, corner corridor, gradual return, directional unknown stops OK\n";
}
