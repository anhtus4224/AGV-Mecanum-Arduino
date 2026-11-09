#include "Arduino.h"
#include <cassert>
#include <iostream>
#include "/workspace/agv_delivery_v2/agv_mecanum_190_v2/agv_mecanum_190_v2.ino"
void init(){
 fakeNow=10000; isLineTrackingMode=true; turnState=IDLE_LINE; frontHits=0;
 curL=curR=0;lastLeftCmd=lastRightCmd=120;cruiseSpeed=120;lastErr=0;
 lastControlTime=0;lostLineTimer=fakeNow;lostReported=false;wasPulsing=false;
 resetLineTracking();stopAllMotors();
}
void tick(int mask){
 inputs[A4]=mask&1;inputs[A3]=(mask>>1)&1;inputs[A2]=(mask>>2)&1;
 inputs[A1]=(mask>>3)&1;inputs[A0]=(mask>>4)&1;
 fakeNow+=10;handleLineAndObstacleMode();
 assert(curL>=0&&curL<=190&&curR>=0&&curR<=190);
 assert(pwm[D1_RPWM]==0&&pwm[D3_RPWM]==0&&pwm[D2_LPWM]==0&&pwm[D4_LPWM]==0);
 assert(!wasPulsing);
}
void fast(){for(int i=0;i<5;i++)tick(4);assert(curL==190&&curR==190);}
int main(){
 int groups=0;
 // Regression: all seven nonempty middle-only patterns held for 5 seconds.
 for(int mask:{2,4,6,8,10,12,14}){
  init();tick(mask);assert(cruiseSpeed==190&&lineZone=='S');
  for(int i=0;i<500;i++)tick(mask);
  assert(!curveActive&&cruiseSpeed==190&&lineZone=='S');
  assert(curL>=170&&curR>=170&&max(curL,curR)==190);
 }groups++;
 init();for(int i=0;i<500;i++)tick(4);assert(curL==190&&curR==190);groups++;
 init();int mild[]={4,6,2,8,12,14,10};
 for(int i=0;i<1000;i++)tick(mild[i%7]);
 assert(cruiseSpeed==190&&lineZone=='S'&&curL>=170&&curR>=170);groups++;
 for(int mask:{1,3,16,24}){
  init();fast();tick(mask);assert(curveActive&&lineZone=='C'&&cruiseSpeed==120);
  assert(max(lineTargetL,lineTargetR)<=190&&min(lineTargetL,lineTargetR)==0);
  for(int i=0;i<100;i++)tick(mask);
  assert(max(curL,curR)==190&&min(curL,curR)==0);
 }groups++;
 // Exit must work even if line remains ONLY under sensor 2 or 4.
 for(int mask:{2,4,6,8,10,12,14}){
  init();fast();tick(1);
  for(int i=0;i<6;i++)tick(mask);assert(curveActive);
  tick(mask);assert(!curveActive&&lineZone=='S'&&cruiseSpeed==190);
  for(int i=0;i<500;i++)tick(mask);
  assert(curL>=170&&curR>=170&&max(curL,curR)==190);
 }groups++;
 init();fast();tick(1);for(int i=0;i<5;i++)tick(4);tick(1);
 for(int i=0;i<6;i++)tick(4);assert(curveActive);
 tick(4);assert(!curveActive);groups++;
 init();fast();tick(31);assert(lineZone=='X'&&cruiseSpeed==120);
 for(int i=0;i<10;i++)tick(31);assert(curL==120&&curR==120);groups++;
 init();fast();tick(0);assert(lineZone=='L'&&curL<190&&curR<190);
 assert(lineTargetL<=120&&lineTargetR<=120);
 tick(0);assert(curL<=120&&curR<=120);
 for(int i=0;i<125;i++)tick(0);
 assert(curL==0&&curR==0&&lostReported&&currentCommand=='S');groups++;
 for(int mask:{2,4,8}){
  init();fast();tick(0);for(int i=0;i<12;i++)tick(mask);
  assert(lineZone=='S'&&cruiseSpeed==190&&curL>=170&&curR>=170);
 }groups++;
 init();fast();parseSingleChar('S','E');assert(!isLineTrackingMode&&currentCommand=='S');
 for(int p:{3,5,7,8,9,11,12,44})assert(pwm[p]==0);groups++;
 init();fast();tick(1);toggleMode("TEST");
 assert(!curveActive&&curL==0&&curR==0&&lineTargetL==0&&lineTargetR==0);groups++;
 for(int mask=0;mask<32;mask++){init();for(int i=0;i<140;i++)tick(mask);}groups++;
 init();unsigned int seed=1;for(int i=0;i<10000;i++){
  seed=seed*1664525u+1013904223u;tick((seed>>16)&31);
 }groups++;
 std::cout<<"PASS V2: "<<groups<<" groups; sustained middle-only patterns; curve/recovery; 32 patterns; 10000 mixed ticks.\n";
}
