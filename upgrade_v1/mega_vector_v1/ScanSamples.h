#pragma once
#include <stdint.h>

// Three spaced pings at one settled angle. A close valid return always wins;
// unknown samples never become evidence of free space.
struct VmScanSamples {
 uint8_t count=0,validCount=0;int closest=999;bool tooClose=false;
 void reset(){count=validCount=0;closest=999;tooClose=false;}
 bool done()const{return count>=3;}
 void add(int cm){
  if(done())return;
  count++;
  if(cm>=0&&cm<=3){tooClose=true;if(cm<closest)closest=cm;}
  else if(cm>3&&cm<400){validCount++;if(cm<closest)closest=cm;}
 }
 int confirmedCm()const{return done()&&(tooClose||validCount>=2)?closest:999;}
};
