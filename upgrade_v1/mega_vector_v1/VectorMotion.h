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
 Phase faultPhase=OFF,phase=OFF;uint32_t since=0,centerSince=0,lastRange=0;int side=0,closest=400,edgeSamples=0;
 bool enabled=false,seenSide=false;int cap=80;const char *fault="";
 // Mode 2 permits an unknown selected side only with a confirmed farther
 // diagonal and operator-armed experimental avoidance; no second corridor.
 uint8_t selectionMode=0,candidateMask=0;
 bool diagonalProof=false;
 // Sensor-to-body inset, NOT body half-width. Front sonar is at the front edge
 // (up to 2 cm proud); side heads reported at the outside edge. Increase these
 // offsets by the measured recess if a head is mounted inside the wheel envelope.
 float leftInset=0,rightInset=0,frontInset=0;
 // PWM-time estimates only, inherited visualization gains, NOT wheel odometry.
 float forwardCmPerSecond=23.6f,strafeCmPerSecond=18.0f;
 float phaseTravel=0,outTravel=0;uint32_t observedAt=0;int frontClearSamples=0;
 void observeWheels(uint32_t now,const int *w){
  uint32_t dt=observedAt?(uint32_t)(now-observedAt):0;observedAt=now;
  if(dt>100||phase<OUT||phase>CENTER)return;
  float lateral=(w[0]-w[1]-w[2]+w[3])/4.0f;
  float forward=(w[0]+w[1]+w[2]+w[3])/4.0f;
  if(phase==OUT)phaseTravel+=fmaxf(0,side*lateral)*strafeCmPerSecond*dt/255000.0f;
  if(phase==PASS)phaseTravel+=fmaxf(0,forward)*forwardCmPerSecond*dt/255000.0f;
  if(phase==RETURN||phase==CENTER)phaseTravel+=fmaxf(0,-side*lateral)*strafeCmPerSecond*dt/255000.0f;
 }
 // Commissioning envelope in cm. Measure the COMPLETE protruding body before arming.
 // User measured full wheel envelope 47 cm, length 34 cm including line bar.
 float halfWidth=23.5f;int frontOverhang=17,rearOverhang=17,margin=12;
 void enter(Phase p,uint32_t now){bool keep=(phase==RETURN&&p==CENTER)||(phase==CENTER&&p==RETURN);phase=p;since=now;centerSince=0;if(!keep)phaseTravel=0;frontClearSamples=0;}
 void fail(const char *reason,uint32_t now){faultPhase=phase;fault=reason;enter(FAULT,now);}
 void start(uint32_t now){seenSide=false;closest=400;edgeSamples=0;lastRange=0;fault="";selectionMode=candidateMask=0;diagonalProof=false;side=0;observedAt=now;outTravel=0;enter(SCAN_LEFT,now);}
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
  bool ld=left==999&&(right==999||(right>rightInset+margin&&right<400))&&diagLeft>fartherDiagonal&&diagLeft<400;
  bool rd=right==999&&(left==999||(left>leftInset+margin&&left<400))&&diagRight>fartherDiagonal&&diagRight<400;
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
  bool frontUnknown=diagonalProof&&front.cm==999&&(uint32_t)(now-front.at)<350;
  if(!front.valid(now)&&!frontUnknown){fail("SONAR_FRONT_UNKNOWN",now);return;}
  // Opposite side is receding during OUT. It need not be a second corridor.
  // Still reject an actual too-close return on either side. On the return leg
  // the three fresh side-edge samples below must have confirmed passage first.
  bool nearUnknown=near.cm==999&&(uint32_t)(now-near.at)<350;
  if(!near.valid(now)&&!nearUnknown){fail("SONAR_SIDE_UNKNOWN",now);return;}
  bool diagonalUnknown=diagonalProof&&outer.cm==999&&(uint32_t)(now-outer.at)<350;
  if(!outer.valid(now)&&!diagonalUnknown){fail("SONAR_SIDE_UNKNOWN",now);return;}
  if((front.cm!=999&&front.cm<frontInset+margin)||
     (left.cm!=999&&left.cm<leftInset+margin)||
     (right.cm!=999&&right.cm<rightInset+margin)){fail("CLEARANCE",now);return;}
  // No backward component in this avoidance trajectory: rear clearance is not
  // a prerequisite for moving away from a rear wall. STOP/link guards remain.
  (void)back;
  if((uint32_t)(now-since)>30000){fail("PHASE_TIMEOUT",now);return;}
  if(phase==OUT){
   f=120;s=side*255; // Dominant lateral component before committing forward.
   if(near.valid(now)&&near.cm<100){seenSide=true;if(near.cm<closest)closest=near.cm;}
   // Seeing background ahead is insufficient: first issue enough lateral wheel
   // effort to clear a half-body + margin, then require three fresh front clears.
   // This estimate scales with actual issued PWM, including ramp and selected cap.
   if(front.at!=lastRange){lastRange=front.at;
    if((front.valid(now)&&front.cm>VM_OBSTACLE_CM+margin)||frontUnknown)frontClearSamples++;
    else frontClearSamples=0;
   }
   if(phaseTravel>=halfWidth+margin&&frontClearSamples>=3){
    outTravel=phaseTravel;closest=near.valid(now)?near.cm:400;seenSide=near.valid(now)&&near.cm<100;
    edgeSamples=0;lastRange=near.at;enter(PASS,now);
   }
  } else if(phase==PASS){
   f=255;s=0;
   if(near.valid(now)&&near.cm<100){seenSide=true;if(near.cm<closest)closest=near.cm;}
   // No echo may be an edge only AFTER a measured nearby object, never by itself.
   if(near.at!=lastRange){lastRange=near.at;
    if(seenSide&&(nearUnknown||(near.valid(now)&&near.cm>closest+20)))edgeSamples++;else edgeSamples=0;
   }
   if(edgeSamples>=3&&phaseTravel>=frontOverhang+rearOverhang+margin)enter(RETURN,now);
  } else if(phase==RETURN){
   int blend=vmClamp((uint32_t)(now-since)>400?400:(int)(now-since),0,400);
   f=255-(long)135*blend/400;s=-(long)side*255*blend/400;
   if(phaseTravel>outTravel*1.5f+margin){fail("LINE_NOT_REACQUIRED",now);f=s=0;return;}
   if(center&&phaseTravel>=outTravel*.6f)enter(CENTER,now);
  } else if(phase==CENTER){
   f=90;s=0;
   if(!center){enter(RETURN,now);return;}
   if(!centerSince)centerSince=now;
   if((uint32_t)(now-centerSince)>=80)enter(HANDOFF,now);
  }
 }
};
