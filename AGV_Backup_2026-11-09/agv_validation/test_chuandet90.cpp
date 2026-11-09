#include "Arduino.h"
#include <cassert>
#include <iostream>
#include "/workspace/agv_chuandet90/agv_chuandet90/agv_chuandet90.ino"
void init(){fakeNow=10000;isLineTrackingMode=true;turnState=IDLE_LINE;frontHits=0;
curL=curR=0;lastErr=0;lastLeftCmd=lastRightCmd=120;lastControlTime=0;lastCornerFinished=0;
postAvoidanceBlindTimer=0;lostLineTimer=fakeNow;cornerCount=0;lostReported=false;
resetLineTracking();stopAllMotors();}
void tick(int mask,int dt=10){for(int i=0;i<5;i++)inputs[A0+i]=((mask>>i)&1)?LOW:HIGH;
fakeNow+=dt;handleLineAndObstacleMode();assert(abs(curL)<=255&&abs(curR)<=255);}
void straight(){for(int i=0;i<100;i++)tick(4);assert(curL==255&&curR==255);}
void enter(bool right){tick(right?28:7);assert(turnState==IDLE_LINE);tick(right?28:7);assert(turnState==RUNOUT_90);
for(int i=0;i<121;i++)tick(0);assert(turnState==RUNOUT_90&&curL==255&&curR==255);
tick(0);assert(turnState==TURNING_90);assert(right?curL==255&&curR==-255:curL==-255&&curR==255);}
int main(){int groups=0;
init();straight();groups++;
for(bool right:{true,false}){
 init();straight();enter(right);
 for(int i=0;i<25;i++)tick(4); // never blank: cannot recapture old line
 assert(turnState==TURNING_90&&!cornerBlankSeen);
 tick(0);tick(0);assert(cornerBlankSeen);
 tick(right?2:8);tick(4);tick(4);assert(turnState==TURNING_90&&!cornerSideSeen);
 tick(right?8:2);tick(4);tick(4);assert(turnState==SETTLE_90&&curL==0&&curR==0);
 for(int i=0;i<8;i++)tick(4);assert(turnState==IDLE_LINE);
 tick(right?28:7);tick(right?28:7);assert(turnState==IDLE_LINE); // lock prevents retrigger
}groups++;
init();straight();enter(true);for(int i=0;i<405;i++)tick(0);
assert(turnState==CORNER_FAULT&&curL==0&&curR==0);tick(4);assert(turnState==CORNER_FAULT);groups++;
init();straight();enter(true);for(int i=0;i<25;i++)tick(0);tick(8);tick(4);tick(4);
assert(turnState==SETTLE_90);for(int i=0;i<8;i++)tick(0);
assert(turnState==CORNER_FAULT&&curL==0&&curR==0);groups++;
init();straight();enter(true);frontHits=2;tick(0);assert(turnState==CORNER_FAULT);groups++;
init();straight();enter(false);parseSingleChar('S','E');assert(!isLineTrackingMode&&turnState==IDLE_LINE);
for(int p:{3,5,7,8,9,11,12,44})assert(pwm[p]==0);groups++;
for(char c:{'E','Q'}){init();isLineTrackingMode=false;parseSingleChar(c,'E');fakeNow+=180;handleManualMode();assert(currentCommand==c);
fakeNow+=1;handleManualMode();assert(currentCommand=='S');for(int p:{3,5,7,8,9,11,12,44})assert(pwm[p]==0);}groups++;
init();isLineTrackingMode=false;parseSingleChar('F','E');fakeNow+=181;handleManualMode();assert(currentCommand=='F');
fakeNow+=520;handleManualMode();assert(currentCommand=='S');groups++;
init();straight();tick(0);for(int i=0;i<130;i++)tick(0);assert(curL==0&&curR==0&&lostReported);groups++;
init();straight();for(int i=0;i<5;i++)tick(16);assert(turnState==IDLE_LINE);groups++;
assert(RUNOUT_RIGHT_MS==1216&&RUNOUT_LEFT_MS==1216&&WIFI_MAX_SPEED==255);
assert(AVOID_FORWARD_SPEED==200&&AVOID_OUT_MS==2900&&AVOID_FORWARD_MS==3500);groups++;
std::cout<<"PASS "<<groups<<" groups: runout, both directions, acquisition gates, timeouts, obstacle, stop, WiFi expiry.\n";
}
