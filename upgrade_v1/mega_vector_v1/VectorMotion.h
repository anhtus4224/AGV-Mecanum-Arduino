#pragma once
#include <stdint.h>
#include <math.h>
#include <stdlib.h>
const int VM_OBSTACLE_CM=55;
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
 // Mode 2 permits ONE unknown side only with a confirmed farther diagonal,
 // a measured opposite side and operator-armed experimental avoidance.
 uint8_t selectionMode=0,candidateMask=0;
 bool diagonalProof=false;
 // Commissioning envelope in cm. Measure the COMPLETE protruding body before arming.
 // User measured full wheel envelope 47 cm, length 34 cm including line bar.
 float halfWidth=23.5f;int frontOverhang=17,rearOverhang=17,margin=12;
 void enter(Phase p,uint32_t now){phase=p;since=now;centerSince=0;}
 void fail(const char *reason,uint32_t now){fault=reason;enter(FAULT,now);}
 void start(uint32_t now){seenSide=false;closest=400;edgeSamples=0;lastRange=0;fault="";selectionMode=candidateMask=0;diagonalProof=false;side=0;enter(SCAN_LEFT,now);}
 bool active()const{return phase!=OFF&&phase!=HANDOFF&&phase!=FAULT;}
 // Scan samples are taken by the non-blocking firmware integration.
 void choose(int left,int right,int diagLeft,int diagRight,uint32_t now){
  float need=2*halfWidth+margin;
  // Conservative corner envelope. Sensor origins/blind sectors still need measuring;
  // these sparse rays do not prove the entire swept rectangle is unobstructed.
  float diagonal=sqrtf((halfWidth+margin)*(halfWidth+margin)+(frontOverhang+margin)*(frontOverhang+margin));
  selectionMode=0;diagonalProof=false;
  bool l=left>need&&left<400&&diagLeft>diagonal&&diagLeft<400;
  bool r=right>need&&right<400&&diagRight>diagonal&&diagRight<400;
  // At a commanded 45-degree scan, require both nominal projections > need.
  // This is a sparse-ray experimental condition, not proof of a swept free area.
  float fartherDiagonal=1.414214f*need;
  bool ld=left==999&&right>halfWidth+margin&&right<400&&diagLeft>fartherDiagonal&&diagLeft<400;
  bool rd=right==999&&left>halfWidth+margin&&left<400&&diagRight>fartherDiagonal&&diagRight<400;
  candidateMask=(l?1:0)|(r?2:0)|(ld?4:0)|(rd?8:0);
  if(!enabled){fail("AVOID_NOT_ARMED",now);return;}
  if(l||r){selectionMode=1;side=r&&(!l||right>=left)?1:-1;}
  else if(ld||rd){selectionMode=2;side=rd&&(!ld||diagRight>=diagLeft)?1:-1;}
  else{fail("NO_CONFIRMED_CORRIDOR",now);return;}
  int selectedDiag=side>0?diagRight:diagLeft;
  diagonalProof=selectedDiag>fartherDiagonal&&selectedDiag<400;
  enter(OUT,now);
 }
 void tick(uint32_t now,VmRange front,VmRange back,VmRange left,VmRange right,bool center,int &f,int &s){
  f=s=0;if(!active()||phase<OUT)return;
  VmRange near=side>0?left:right,outer=side>0?right:left;
  if(!front.valid(now)){fail("SONAR_FRONT_UNKNOWN",now);return;}
  if(!back.valid(now)){fail("SONAR_REAR_UNKNOWN",now);return;}
  if(!near.valid(now)){fail("SONAR_SIDE_UNKNOWN",now);return;}
  bool diagonalUnknown=diagonalProof&&outer.cm==999&&(uint32_t)(now-outer.at)<350;
  if(!outer.valid(now)&&!diagonalUnknown){fail("SONAR_SIDE_UNKNOWN",now);return;}
  // Front sensor points forward again before motion. Never use EMA for collision guards.
  if(front.cm<frontOverhang+margin||(outer.valid(now)&&outer.cm<halfWidth+margin)||near.cm<halfWidth+margin){fail("CLEARANCE",now);return;}
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
   // Blend into the return diagonal over 400 ms; retain wheel slew and all guards.
   int blend=vmClamp((uint32_t)(now-since)>400?400:(int)(now-since),0,400);
   f=255-(long)55*blend/400;s=-(long)side*100*blend/400;
   if(center)enter(CENTER,now);
  } else if(phase==CENTER){
   f=90;s=0;
   if(!center){enter(RETURN,now);return;}
   if(!centerSince)centerSince=now;
   if((uint32_t)(now-centerSince)>=80)enter(HANDOFF,now);
  }
 }
};
