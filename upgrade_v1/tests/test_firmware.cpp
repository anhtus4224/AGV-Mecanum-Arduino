#include "Arduino.h"
#include "../mega_vector_v1/mega_vector_v1.ino"
#include <cassert>
#include <cstdio>
#include <iostream>
void command(std::string body,bool corrupt=false){
 char c[8];snprintf(c,sizeof(c),"*%04X\n",vectorCrc(body.c_str())^(corrupt?1:0));Serial.feed("@"+body+c);vectorRead();
}
int main(){
 for(int i=0;i<80;i++)inputs[i]=HIGH;
 command("V1,12,1,H,0,0,0,250");assert(hostOwned&&hostSession==12);
 command("V1,12,2,D,255,130,0,250");assert(vectorManual&&vectorTarget[0]==80&&vectorTarget[1]<80);
 fakeNow=10;vectorService();assert(actualWheels[0]==8);
 command("V1,12,3,S,0,0,0,250");assert(!vectorManual);for(int w:actualWheels)assert(w==0);
 command("V1,12,2,D,255,0,0,250");assert(!vectorManual); // replay after STOP
 command("V1,12,4,D,255,0,0,250",true);assert(!vectorManual); // bad CRC
 command("V1,12,4,D,99999999999999,0,0,250");assert(!vectorManual);
 command("V1,13,1,H,0,0,0,250");assert(hostSession==12); // no live takeover
 command("V1,12,5,A,0,0,0,250");assert(isLineTrackingMode);
 drive(255,120,255,120);assert(actualWheels[0]==80&&actualWheels[1]<80);
 fakeNow=800;vectorService();assert(!isLineTrackingMode); // host watchdog includes AUTO
 command("V1,13,1,H,0,0,0,250");assert(hostSession==13); // reconnect after expiry
 command("V1,12,100,D,255,0,0,250");assert(!vectorManual); // old session fenced
 command("V1,13,2,D,255,0,0,250");fakeNow=1060;vectorService();assert(!vectorManual);
 Serial.feed("DEF");vectorRead();assert(!vectorManual&&!isLineTrackingMode);
 Serial2.feed("F");vectorRead();for(int w:actualWheels)assert(w==0); // USB owns output
 // Scanning reads advance millis(): fresh samples must not appear "in the future".
 fakeNow=1500;hostAt=fakeNow;vectorAvoid.enabled=true;vectorAvoid.cap=80;
 vectorAvoid.enter(VmAvoid::SCAN_CENTER,1000);scanLeft=scanRight=100;pulseEcho=5882;
 for(int i=0;i<4;i++){fakeNow+=40;hostAt=fakeNow;vectorService();}
 assert(vectorAvoid.phase==VmAvoid::OUT||vectorAvoid.phase==VmAvoid::PASS);
 // 5882 us * .034 / 2 truncates to 99 cm in the existing conversion.
 assert(Serial.output.find(",99,99,100,100,4,1\n")!=std::string::npos);
 // Finite side rays do not authorize motion when both diagonal echoes are unknown.
 fakeNow=2100;hostAt=fakeNow;vectorAvoid.enter(VmAvoid::SCAN_CENTER,1600);
 scanLeft=scanRight=999;scanCenterSlot=0;Serial.output.clear();
 for(int i=0;i<4;i++){fakeNow+=40;hostAt=fakeNow;vectorService();}
 assert(Serial.output.find(",99,99,999,999,9,0\n")!=std::string::npos);
 assert(Serial.output.find("AVOID_FAULT:NO_CONFIRMED_CORRIDOR")!=std::string::npos);
 assert(vectorAvoid.phase==VmAvoid::OFF);for(int w:actualWheels)assert(w==0);
 std::cout<<"Firmware protocol: CRC/replay/bounds/ownership/manual timeout/AUTO watchdog/reconnect OK\n";
}
