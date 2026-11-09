#include "Arduino.h"
#include <cassert>
#include <iostream>
#include "/workspace/agv_delivery/agv_mecanum_chuan/agv_mecanum_chuan.ino"
void init(){
 fakeNow=10000; isLineTrackingMode=true; turnState=IDLE_LINE;
 frontHits=0; curL=curR=0; lastLeftCmd=lastRightCmd=120;
 cruiseSpeed=120; lastErr=0; lastControlTime=0; lostLineTimer=fakeNow;
 lostReported=false; wasPulsing=false; resetLineTracking();
}
// Bits are logical L2,L1,M,R1,R2, after configured sensor reversal.
void tick(int mask){
 inputs[A4]=(mask>>0)&1; inputs[A3]=(mask>>1)&1; inputs[A2]=(mask>>2)&1;
 inputs[A1]=(mask>>3)&1; inputs[A0]=(mask>>4)&1;
 fakeNow+=10; handleLineAndObstacleMode();
 assert(curL>=0&&curL<=255&&curR>=0&&curR<=255);
 // No reverse PWM on any of the four motors during line tracking.
 assert(pwm[D1_RPWM]==0&&pwm[D3_RPWM]==0);
 assert(pwm[D2_LPWM]==0&&pwm[D4_LPWM]==0);
}
void fast(){for(int i=0;i<70;i++)tick(4); assert(cruiseSpeed==190);}
int main(){
 int cases=0;
 init();
 const int mild[]={4,6,4,12,2,4,8,4};
 for(int i=0;i<300;i++)tick(mild[i%8]);
 assert(cruiseSpeed==190&&lineZone=='S'&&curL>=170&&curR>=170); cases++;
 for(int mask: {2,6,8,12}){
  init();fast();tick(mask);
  assert(lineZone=='S'&&cruiseSpeed==190);
  assert(curL>=170&&curR>=170&&!wasPulsing);
 } cases++;
 for(int mask:{2,8}){
  init();fast();for(int i=0;i<10;i++)tick(mask);assert(lineZone=='S');
  tick(mask);assert(curveActive&&lineZone=='C'&&cruiseSpeed==120);
  for(int i=0;i<10;i++)tick(mask);
  assert((mask==2?curL:curR)==0);
 } cases++;
 for(int mask:{1,16,3,24}){
  init();fast();tick(mask);assert(curveActive&&lineZone=='C');
  assert(cruiseSpeed==120&&!wasPulsing);
 } cases++;
 init();fast();tick(1);
 for(int i=0;i<9;i++)tick(6);assert(curveActive);
 tick(1); // another edge cancels exit debounce
 for(int i=0;i<10;i++)tick(6);assert(curveActive);
 tick(6);assert(!curveActive&&cruiseSpeed==120);
 for(int i=0;i<60;i++)tick(4);assert(cruiseSpeed==190);cases++;
 init();fast();tick(0);assert(lineZone=='L'&&curL<190&&curR<190);
 tick(0);assert(curL<=120&&curR<=120);
 for(int i=0;i<125;i++)tick(0);
 assert(curL==0&&curR==0&&lostReported&&currentCommand=='S'&&lineZone=='L');cases++;
 init();fast();tick(0);tick(4);
 assert(cruiseSpeed==120&&curveActive);
 for(int i=0;i<11;i++)tick(4);assert(!curveActive);cases++;
 init();fast();tick(31);assert(lineZone=='X'&&cruiseSpeed==120);cases++;
 init();fast();parseSingleChar('S','E');
 assert(!isLineTrackingMode&&currentCommand=='S');
 for(int p:{3,5,7,8,9,11,12,44})assert(pwm[p]==0);cases++;
 init();fast();tick(1);toggleMode("TEST");
 assert(!curveActive&&!sidePending&&cruiseSpeed==120&&curL==0&&curR==0);cases++;
 for(int mask=0;mask<32;mask++){
  init();for(int i=0;i<140;i++)tick(mask);
 } cases++;
 init();unsigned int seed=1;
 for(int i=0;i<10000;i++){seed=seed*1664525u+1013904223u;tick((seed>>16)&31);}
 cases++;
 std::cout<<"PASS: "<<cases<<" scenario groups; 32 sensor patterns; 10000 mixed-input ticks.\n";
}
