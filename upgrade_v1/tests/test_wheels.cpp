// Host Arduino stub: exercises frame parser -> mixer -> ramp -> drive -> PWM pins.
// This checks software output, not electrical signals or wheel motion on a Mega.
#include "Arduino.h"
#include "../mega_vector_v1/mega_vector_v1.ino"
#include <cassert>
#include <cstdio>
#include <iostream>
void sendFrame(unsigned seq,char op,int f=0,int s=0,int r=0){
 char body[96],crc[8];snprintf(body,sizeof(body),"V1,77,%u,%c,%d,%d,%d,250",seq,op,f,s,r);
 snprintf(crc,sizeof(crc),"*%04X\n",vectorCrc(body));Serial.feed(std::string("@")+body+crc);vectorRead();
}
void pinsMatch(const int *expected){
 const int rp[4]={44,5,7,11},lp[4]={3,9,8,12};
 const int polarity[4]={-1,1,-1,1};
 for(int i=0;i<4;i++){
  assert(actualWheels[i]==expected[i]);int e=expected[i]*polarity[i];
  assert(pwm[rp[i]]==(e>0?e:0));assert(pwm[lp[i]]==(e<0?-e:0));
 }
}
int main(){
 for(int &i:inputs)i=HIGH;
 sendFrame(1,'H');unsigned seq=2;
 const int vectors[10][3]={{255,0,0},{-255,0,0},{0,-255,0},{0,255,0},{255,-255,0},{255,255,0},{-255,-255,0},{-255,255,0},{0,0,-255},{0,0,255}};
 const int signs[10][4]={{1,1,1,1},{-1,-1,-1,-1},{-1,1,1,-1},{1,-1,-1,1},{0,1,1,0},{1,0,0,1},{-1,0,0,-1},{0,-1,-1,0},{-1,1,-1,1},{1,-1,1,-1}};
 const char* names[10]={"F","B","L","R","NW","NE","SW","SE","Q","E"};
 for(int cap:{80,120,160,200,255}){
  vectorAvoid.cap=cap;
  for(int k=0;k<10;k++){
   sendFrame(seq++,'S');sendFrame(seq++,'D',vectors[k][0],vectors[k][1],vectors[k][2]);
   int expected[4];for(int i=0;i<4;i++)expected[i]=signs[k][i]*cap;
   for(int step=0;step<35;step++){
    if(step%8==0)sendFrame(seq++,'D',vectors[k][0],vectors[k][1],vectors[k][2]);
    fakeNow+=10;vectorService();
   }
   pinsMatch(expected);
   std::cout<<cap<<","<<names[k];for(int w:expected)std::cout<<","<<w;std::cout<<"\n";
   sendFrame(seq++,'S');const int zero[4]={0,0,0,0};pinsMatch(zero);
  }
 }
 // Reverse pure strafe: every wheel must reach zero before changing sign.
 vectorAvoid.cap=80;sendFrame(seq++,'D',0,255,0);
 for(int i=0;i<10;i++){fakeNow+=10;vectorService();}
 sendFrame(seq++,'D',0,-255,0);
 bool zero[4]={false,false,false,false};const int oldSign[4]={1,-1,-1,1};
 for(int step=0;step<22;step++){
  fakeNow+=10;vectorService();
  for(int i=0;i<4;i++){if(actualWheels[i]==0)zero[i]=true;if(actualWheels[i]*oldSign[i]<0)assert(zero[i]);}
 }
 const int left[4]={-80,80,80,-80};pinsMatch(left);
 fakeNow+=251;vectorService();const int stopped[4]={0,0,0,0};pinsMatch(stopped);
 // Source constants are tested here; no board upload or physical motion.
 assert(VM_OBSTACLE_CM==55);assert(!vectorAvoid.enabled);
 hostAt=fakeNow;rangeF={56,(uint32_t)fakeNow};turnState=IDLE_LINE;
 handleLineAndObstacleMode();assert(vectorAvoid.phase==VmAvoid::OFF);
 rangeF={55,(uint32_t)fakeNow};turnState=IDLE_LINE;
 handleLineAndObstacleMode();assert(vectorAvoid.phase==VmAvoid::SCAN_LEFT);
 sendFrame(seq++,'S');pinsMatch(stopped);
 vectorMotion();assert(Serial.output.find("VECTOR_TARGET:")!=std::string::npos);
 std::cout<<"Wheels: 50 direction/cap cases, all 8 PWM pins, STOP/reversal/watchdog OK\n";
}
