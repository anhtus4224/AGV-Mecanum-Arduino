#include "Arduino.h"
#include <cassert>
#include <iostream>
#include "/workspace/agv_smooth/agv_mecanum_smooth/agv_mecanum_smooth.ino"
void init(){fakeNow=10000;frontHits=0;turnState=IDLE_LINE;isLineTrackingMode=true;
curL=curR=0;lastErr=0;lastLeftCmd=lastRightCmd=120;cruiseSpeed=120;
lastControlTime=0;lostLineTimer=fakeNow;lostReported=false;resetLineTracking();stopAllMotors();}
void tick(int mask,int dt=10){
 for(int i=0;i<5;i++)inputs[A0+i]=((mask>>i)&1)?LOW:HIGH;
 fakeNow+=dt;handleLineAndObstacleMode();
 assert(curL>=0&&curL<=250&&curR>=0&&curR<=250);
 assert(pwm[D1_RPWM]==0&&pwm[D3_RPWM]==0&&pwm[D2_LPWM]==0&&pwm[D4_LPWM]==0);
}
void fast(){for(int i=0;i<100;i++)tick(4);assert(curL==250&&curR==250);}
int main(){int groups=0;
init();fast();groups++;
for(int side:{2,8}){init();fast();for(int i=0;i<10;i++)tick(side);assert(!curveActive);
for(int i=0;i<50;i++)tick(side);assert(curveActive&&cruiseSpeed==190&&min(curL,curR)>=90);
assert(side==2?curL<curR:curR<curL);}groups++;
for(int edge:{1,3,16,24}){init();fast();int prevL=curL,prevR=curR;
for(int i=0;i<100;i++){tick(edge);assert(abs(curL-prevL)<=40&&abs(curR-prevR)<=40);
assert(curL>=90&&curR>=90);prevL=curL;prevR=curR;}
assert(cruiseSpeed==190);assert(edge<4?curL<curR:curR<curL);}groups++;
init();fast();for(int i=0;i<100;i++)tick(16);
for(int i=0;i<200;i++)tick(i%2?8:16);
assert(curveActive&&cruiseSpeed==190&&curL>=90&&curR>=90);groups++;
init();fast();for(int i=0;i<80;i++)tick(1);for(int i=0;i<16;i++)tick(4);assert(curveActive);
tick(4);assert(!curveActive&&cruiseSpeed<=194);for(int i=0;i<100;i++)tick(4);
assert(curL==250&&curR==250);groups++;
init();fast();for(int i=0;i<60;i++)tick(31);assert(lineZone=='X'&&curL==120&&curR==120);groups++;
init();fast();tick(0);assert(lineTargetL<=120&&lineTargetR<=120);
for(int i=0;i<130;i++)tick(0);assert(curL==0&&curR==0&&lostReported);groups++;
init();fast();for(int i=0;i<80;i++)tick(16);tick(0);for(int i=0;i<100;i++)tick(0);
assert(curL==160&&curR==0);for(int i=0;i<25;i++)tick(0);assert(curL==0&&curR==0);groups++;
init();fast();tick(0);for(int i=0;i<200;i++)tick(4);assert(curL==250&&curR==250);groups++;
init();fast();parseSingleChar('S','E');assert(!isLineTrackingMode&&currentCommand=='S');
for(int p:{3,5,7,8,9,11,12,44})assert(pwm[p]==0);groups++;
for(int mask=0;mask<32;mask++){init();for(int i=0;i<150;i++)tick(mask);}groups++;
init();unsigned seed=1;for(int i=0;i<10000;i++){seed=seed*1664525u+1013904223u;tick((seed>>16)&31,(i%3)?10:18);}groups++;
// Confirm uploaded avoidance/manual constants retained.
assert(WIFI_MAX_SPEED==250&&AVOID_STRAFE_SPD==160&&AVOID_FORWARD_SPEED==200);
assert(AVOID_OUT_MS==2900&&AVOID_FORWARD_MS==3500&&AVOID_BACK_BLIND_MS==2000);groups++;
std::cout<<"PASS "<<groups<<" groups, 32 patterns, 10000 mixed ticks.\n";}
