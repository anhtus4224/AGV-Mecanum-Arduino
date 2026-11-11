#include "Arduino.h"
#include "../mega_vector_v1/mega_vector_v1.ino"
#include <cassert>
#include <iostream>
int main(){
 for(int &x:inputs)x=HIGH;
 hostOwned=true;hostAt=fakeNow=100;vectorAvoid.cap=80;
 pulseEcho=12000;pulseTimeoutHistory.clear();pulseStartHistory.clear();sonarSlot=0;
 // Idle/manual dashboard rays now have the same range as the scan rays.
 for(int i=0;i<4;i++){
  fakeNow+=40;hostAt=fakeNow;size_t count=pulseTimeoutHistory.size();loop();
  assert(pulseTimeoutHistory.size()==count+1&&lastPulseTimeout==24000);
 }
 assert(rangeF.cm==204&&rangeL.cm==204&&rangeR.cm==204&&rangeB.cm==204);
 assert(rangeF.valid(fakeNow)&&rangeL.valid(fakeNow)&&rangeR.valid(fakeNow)&&rangeB.valid(fakeNow));
 // Reproduce the latest JSON, but new policy can choose left with unknown left side.
 vectorAvoid.enabled=true;vectorBeginAvoidance();Serial.output.clear();pulseTimeoutHistory.clear();
 pulseEchoScript={8942,8942,8942,6942,6942,6942,3120,0,2680,2883};
 for(int i=0;i<300&&vectorAvoid.phase!=VmAvoid::OUT;i++){
  fakeNow+=10;hostAt=fakeNow;size_t count=pulseTimeoutHistory.size();loop();
  assert(pulseTimeoutHistory.size()<=count+1); // At most one bounded echo wait per full loop.
  if(vectorAvoid.phase>=VmAvoid::SCAN_LEFT&&vectorAvoid.phase<=VmAvoid::SCAN_CENTER)
   for(int w:actualWheels)assert(w==0);
 }
 assert(vectorAvoid.phase==VmAvoid::OUT&&vectorAvoid.side==-1&&vectorAvoid.selectionMode==2);
 assert(scanLeft==152&&scanRight==118&&rangeL.cm==999&&rangeR.cm==45);
 assert(Serial.output.find(",999,45,152,118,4,-1\n")!=std::string::npos);
 assert(Serial.output.find(",2,4,80,1\n")!=std::string::npos);
 assert(pulseTimeoutHistory.size()==10);
 for(auto timeout:pulseTimeoutHistory)assert(timeout==24000);
 assert(rangeF.valid(fakeNow)&&rangeR.valid(fakeNow)&&rangeB.valid(fakeNow));
 assert((uint32_t)(fakeNow-rangeL.at)<350); // Fresh timeout, not stale data authorized as clear.
 // Framed Web STOP also cancels this new moving branch, not just legacy raw Z.
 hostSession=77;char crc[8];const char* body="V1,77,1,S,0,0,0,250";
 snprintf(crc,sizeof(crc),"*%04X\n",vectorCrc(body));Serial.feed(std::string("@")+body+crc);
 loop();assert(vectorAvoid.phase==VmAvoid::OFF);for(int w:actualWheels)assert(w==0);
 Serial.feed("?");vectorRead();assert(Serial.output.find("VECTOR_BUILD:AVOID_DIRECTIONAL_V4")!=std::string::npos);
 // A later valid close return on that side still stops the whole motion.
 vectorAvoid.choose(999,45,152,118,fakeNow);
 rangeL={8,(uint32_t)fakeNow};fakeNow+=10;hostAt=fakeNow;vectorService();
 assert(vectorAvoid.phase==VmAvoid::OFF);for(int w:actualWheels)assert(w==0);
 // UART STOP is serviced between bounded center reads, before any motion decision.
 vectorBeginAvoidance();scanCenterSlot=0;vectorAvoid.enter(VmAvoid::SCAN_CENTER,fakeNow-450);
 fakeNow+=40;hostAt=fakeNow;pulseEcho=12000;vectorService();assert(scanCenterSlot==1);
 Serial.feed("Z");loop();assert(vectorAvoid.phase==VmAvoid::OFF);
 for(int w:actualWheels)assert(w==0);
 // Legacy read remains 8 ms; it has not been silently extended.
 assert(readUltrasonicCM(TRIG_LEFT,ECHO_LEFT)==999&&lastPulseTimeout==8000);
 // The persistent USB round-robin index must not overflow a 16-bit AVR int.
 sonarSlot=32767;
 for(int i=0;i<8;i++){
  fakeNow+=40;hostAt=fakeNow;vectorSonar();assert(sonarSlot>=0&&sonarSlot<4);
 }
 std::cout<<"VECTOR1 range: 24ms all rays, one wait/loop, current case left, close/framed STOP/build ID OK\n";
}
