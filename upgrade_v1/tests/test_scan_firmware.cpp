#include "Arduino.h"
#include "../mega_vector_v1/mega_vector_v1.ino"
#include <cassert>
#include <iostream>
int main(){
 for(int &x:inputs)x=HIGH;
 pulseEcho=12000;
 assert(readUltrasonicCM(TRIG_FRONT,ECHO_FRONT)==999); // 8 ms cannot see this echo.
 assert(vectorScanCM()==204);assert(lastPulseTimeout==24000);
 pulseEcho=0;unsigned long before=fakeNow;
 assert(vectorScanCM()==999&&fakeNow-before==24); // Timeout is NOT free space.

 // One transient timeout on the good side, all unknown on the other side.
 fakeNow=100;hostOwned=true;hostAt=fakeNow;vectorAvoid.enabled=true;
 vectorBeginAvoidance();Serial.output.clear();pulseTimeoutHistory.clear();pulseStartHistory.clear();
 pulseEchoScript={12000,0,11765,0,0,0,3120,4200,2400,4000};
 for(int i=0;i<250&&vectorAvoid.phase!=VmAvoid::OUT;i++){
  fakeNow+=10;hostAt=fakeNow;vectorRead();vectorService();
  if(vectorAvoid.phase>=VmAvoid::SCAN_LEFT&&vectorAvoid.phase<=VmAvoid::SCAN_CENTER)
   for(int w:actualWheels)assert(w==0);
 }
 assert(vectorAvoid.phase==VmAvoid::OUT&&vectorAvoid.side==-1);
 assert(scanLeft==200&&scanRight==999&&scanSamplesLeft.validCount==2);
 assert(Serial.output.find(",71,40,200,999,4,-1\n")!=std::string::npos);
 assert(pulseTimeoutHistory.size()==10);
 for(int i=0;i<6;i++)assert(pulseTimeoutHistory[i]==24000);
 for(int i=6;i<10;i++)assert(pulseTimeoutHistory[i]==8000);
 for(int i:{1,2,4,5})assert(pulseStartHistory[i]-pulseStartHistory[i-1]>=60);
 assert(pulseStartHistory[3]-pulseStartHistory[2]>=440);

 // STOP while waiting for the next scan sample cannot auto-resume the scan.
 vectorBeginAvoidance();fakeNow+=450;hostAt=fakeNow;pulseEcho=6000;
 vectorService();assert(vectorAvoid.phase==VmAvoid::SCAN_LEFT&&scanSamplesLeft.count==1);
 Serial.feed("Z");vectorRead();assert(vectorAvoid.phase==VmAvoid::OFF);
 fakeNow+=1000;vectorService();for(int w:actualWheels)assert(w==0);
 // Host watchdog is still 700 ms during scanning.
 vectorBeginAvoidance();hostAt=fakeNow;fakeNow+=701;vectorService();
 assert(vectorAvoid.phase==VmAvoid::OFF);for(int w:actualWheels)assert(w==0);
 // Reproduce the observed four scan values: extended all-unknown still refuses.
 hostAt=fakeNow;vectorBeginAvoidance();Serial.output.clear();
 pulseEchoScript={0,0,0,0,0,0,3120,4200,2400,4000};
 for(int i=0;i<250&&vectorAvoid.phase!=VmAvoid::OFF;i++){
  fakeNow+=10;hostAt=fakeNow;vectorService();
 }
 assert(scanSamplesLeft.count==3&&scanSamplesRight.count==3);
 assert(vectorAvoid.phase==VmAvoid::OFF);
 assert(Serial.output.find(",71,40,999,999,9,0\n")!=std::string::npos);
 assert(Serial.output.find("AVOID_FAULT:NO_CONFIRMED_CORRIDOR")!=std::string::npos);
 for(int w:actualWheels)assert(w==0);
 std::cout<<"Scan integration: >8ms echo, one confirmed side, 3 spaced pings, unknown, STOP/watchdog OK\n";
}
