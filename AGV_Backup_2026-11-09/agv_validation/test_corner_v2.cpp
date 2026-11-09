#include "Arduino.h"
#include <cassert>
#include <iostream>
#include "/workspace/agv_chuandet90_v2/agv_chuandet90_v2/agv_chuandet90_v2.ino"
void init(){fakeNow=10000;isLineTrackingMode=true;turnState=IDLE_LINE;frontHits=0;distF=120;
curL=curR=0;lastErr=0;lastLeftCmd=lastRightCmd=120;lastControlTime=0;lastCornerFinished=0;
postAvoidanceBlindTimer=0;lostLineTimer=fakeNow;cornerCount=0;lostReported=false;
cornerBlankSeen=cornerSideSeen=cornerAutoResume=cornerResumePending=false;
cornerBlankCount=cornerCenterCount=0;resetLineTracking();stopAllMotors();}
void tick(int mask,int dt=10){for(int i=0;i<5;i++)inputs[A0+i]=((mask>>i)&1)?LOW:HIGH;
fakeNow+=dt;handleLineAndObstacleMode();assert(abs(curL)<=255&&abs(curR)<=255);}
void fast(){for(int i=0;i<100;i++)tick(4);assert(curL==255&&curR==255);}
void enter(bool right,bool blank=true){tick(right?28:7);tick(right?28:7);assert(turnState==RUNOUT_90);
for(int i=0;i<60;i++)tick(blank?0:4);assert(turnState==RUNOUT_90);
tick(blank?0:4);assert(turnState==TURNING_90);
assert(right?curL==255&&curR==-255:curL==-255&&curR==255);}
int main(){int groups=0;
for(bool right:{true,false}){init();fast();enter(right);
assert(cornerBlankSeen);for(int i=0;i<21;i++)tick(0);
assert(!cornerSideSeen);tick(4);assert(turnState==SETTLE_90&&curL==0&&curR==0);
for(int i=0;i<8;i++)tick(4);assert(turnState==IDLE_LINE);
for(int i=0;i<100;i++)tick(4);assert(curL==255&&curR==255);}groups++;
init();fast();enter(true,false);for(int i=0;i<25;i++)tick(4);
assert(!cornerBlankSeen&&turnState==TURNING_90);
tick(0);tick(0);tick(4);assert(turnState==SETTLE_90);groups++;
init();fast();enter(true);for(int i=0;i<230;i++)tick(0);
assert(turnState==CORNER_FAULT&&cornerAutoResume&&curL==0&&curR==0);
for(int i=0;i<100;i++)tick(0);assert(turnState==CORNER_FAULT);
for(int i=0;i<14;i++)tick(4);assert(turnState==IDLE_LINE);
for(int i=0;i<100;i++)tick(4);assert(curL==255&&curR==255);groups++;
init();fast();enter(true);for(int i=0;i<25;i++)tick(0);tick(4);
assert(turnState==SETTLE_90);for(int i=0;i<8;i++)tick(0);
assert(turnState==CORNER_FAULT&&cornerAutoResume);
for(int i=0;i<14;i++)tick(4);assert(turnState==IDLE_LINE);groups++;
init();cornerFail("SPIN_TIMEOUT");for(int i=0;i<10;i++)tick(4);tick(0);
for(int i=0;i<10;i++)tick(4);assert(turnState==CORNER_FAULT);
for(int i=0;i<4;i++)tick(4);assert(turnState==IDLE_LINE);groups++;
init();fast();enter(true);frontHits=2;tick(0);assert(turnState==CORNER_FAULT&&!cornerAutoResume);
for(int i=0;i<200;i++)tick(4);assert(turnState==CORNER_FAULT);groups++;
init();cornerFail("SPIN_TIMEOUT");distF=10;for(int i=0;i<100;i++)tick(4);
assert(turnState==CORNER_FAULT);distF=120;for(int i=0;i<14;i++)tick(4);assert(turnState==IDLE_LINE);groups++;
init();fast();enter(false);parseSingleChar('S','E');assert(!isLineTrackingMode&&turnState==IDLE_LINE);
for(int p:{3,5,7,8,9,11,12,44})assert(pwm[p]==0);groups++;
for(char c:{'E','Q'}){init();isLineTrackingMode=false;parseSingleChar(c,'E');fakeNow+=180;handleManualMode();assert(currentCommand==c);
fakeNow+=1;handleManualMode();assert(currentCommand=='S');}groups++;
init();fast();tick(0);for(int i=0;i<130;i++)tick(0);assert(curL==0&&curR==0);
for(int i=0;i<100;i++)tick(4);assert(curL==255&&curR==255);groups++;
assert(RUNOUT_RIGHT_MS==608&&RUNOUT_LEFT_MS==608&&TURN_TIMEOUT_MS==2200);
assert(WIFI_MAX_SPEED==255&&AVOID_FORWARD_SPEED==200&&AVOID_OUT_MS==2900&&AVOID_FORWARD_MS==3500);groups++;
std::cout<<"PASS "<<groups<<" groups: shorter runout, direct center catch both directions, rearm/resume, obstacle lock, WiFi stop.\n";}
