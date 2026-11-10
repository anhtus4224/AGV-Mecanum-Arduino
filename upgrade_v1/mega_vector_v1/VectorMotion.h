#pragma once
#include <stdint.h>
#include <math.h>
#include <stdlib.h>
// Logical FL FR RL RR: preserve the existing drive() motor polarity mapping.
inline int vmClamp(int x,int a,int b){return x<a?a:x>b?b:x;}
inline void vmMix(int f,int right,int clockwise,int cap,int *out){
 int raw[4]={f+right+clockwise,f-right-clockwise,f-right+clockwise,f+right-clockwise};
 int peak=255;for(int i=0;i<4;i++)if(abs(raw[i])>peak)peak=abs(raw[i]);
 for(int i=0;i<4;i++)out[i]=(long)raw[i]*cap/peak;
}
inline int vmRamp(int current,int target,int step){
 // Reverse through zero before applying the opposite polarity.
 if((current>0&&target<0)||(current<0&&target>0))target=0;
 return current+vmClamp(target-current,-step,step);
}
struct VmRange {int cm;uint32_t at;bool valid(uint32_t now)const{return cm>3&&cm<400&&(uint32_t)(now-at)<350;}};
struct VmAvoid {
 enum Phase {OFF,SCAN_LEFT,SCAN_RIGHT,SCAN_CENTER,OUT,PASS,RETURN,CENTER,HANDOFF,FAULT};
 Phase phase=OFF;uint32_t since=0,centerSince=0,lastRange=0;int side=0,closest=400,edgeSamples=0;
 bool enabled=false,seenSide=false;int cap=80;const char *fault="";
 // Commissioning envelope in cm. Measure the COMPLETE protruding body before arming.
 int halfWidth=15,frontOverhang=15,rearOverhang=15,margin=12;
 void enter(Phase p,uint32_t now){phase=p;since=now;centerSince=0;}
 void fail(const char *reason,uint32_t now){fault=reason;enter(FAULT,now);}
 void start(uint32_t now){seenSide=false;closest=400;edgeSamples=0;fault="";enter(SCAN_LEFT,now);}
 bool active()const{return phase!=OFF&&phase!=HANDOFF&&phase!=FAULT;}
 // Scan samples are taken by the non-blocking firmware integration.
 void choose(int left,int right,int diagLeft,int diagRight,uint32_t now){
  int need=2*halfWidth+margin;
  bool l=left>need&&left<400&&diagLeft>frontOverhang+margin&&diagLeft<400;
  bool r=right>need&&right<400&&diagRight>frontOverhang+margin&&diagRight<400;
  if(!enabled||(!l&&!r)){fail(!enabled?"AVOID_NOT_ARMED":"NO_CONFIRMED_CORRIDOR",now);return;}
  side=r&&(!l||right>=left)?1:-1;enter(OUT,now);
 }
 void tick(uint32_t now,VmRange front,VmRange back,VmRange left,VmRange right,bool center,int &f,int &s){
  f=s=0;if(!active()||phase<OUT)return;
  VmRange near=side>0?left:right,outer=side>0?right:left;
  if(!front.valid(now)||!back.valid(now)||!near.valid(now)||!outer.valid(now)) {fail("SONAR_UNKNOWN",now);return;}
  // Front sensor points forward again before motion. Never use EMA for collision guards.
  if(front.cm<frontOverhang+margin||outer.cm<halfWidth+margin||near.cm<halfWidth+margin){fail("CLEARANCE",now);return;}
  if(back.valid(now)&&back.cm<rearOverhang+margin){fail("REAR_CLEARANCE",now);return;}
  if((uint32_t)(now-since)>10000){fail("PHASE_TIMEOUT",now);return;}
  if(phase==OUT){
   f=255;s=side*130; // ~27 degrees nominal, wheel response must be calibrated.
   if(near.cm<100){seenSide=true;if(near.cm<closest)closest=near.cm;}
   if(seenSide&&front.cm>frontOverhang+margin+30)enter(PASS,now);
  } else if(phase==PASS){
   f=255;s=0;
   if(near.cm<closest)closest=near.cm;
   // Require fresh, VALID side evidence of an edge; timeout/no echo is NOT an edge.
   if(near.at!=lastRange){lastRange=near.at;if(near.cm>closest+20)edgeSamples++;else edgeSamples=0;}
   if(edgeSamples>=3&&(uint32_t)(now-since)>700)enter(RETURN,now);
  } else if(phase==RETURN){
   f=200;s=-side*100;
   if(center)enter(CENTER,now);
  } else if(phase==CENTER){
   f=90;s=0;
   if(!center){enter(RETURN,now);return;}
   if(!centerSince)centerSince=now;
   if((uint32_t)(now-centerSince)>=80)enter(HANDOFF,now);
  }
 }
};
