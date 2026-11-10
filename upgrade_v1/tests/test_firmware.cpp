#include "Arduino.h"
#include "../mega_vector_v1/mega_vector_v1.ino"
#include <cassert>
#include <cstdio>
#include <iostream>
void command(std::string body,bool corrupt=false){
 char c[8];snprintf(c,sizeof(c),"*%04X\n",vectorCrc(body.c_str())^(corrupt?1:0));Serial.feed("@"+body+c);vectorRead();
}
int main(){
 for(int i=0;i<80;i++)inputs[i]=HIGH;
 command("V1,12,1,H,0,0,0,250");assert(hostOwned&&hostSession==12);
 command("V1,12,2,D,255,130,0,250");assert(vectorManual&&vectorTarget[0]==80&&vectorTarget[1]<80);
 fakeNow=10;vectorService();assert(actualWheels[0]==8);
 command("V1,12,3,S,0,0,0,250");assert(!vectorManual);for(int w:actualWheels)assert(w==0);
 command("V1,12,2,D,255,0,0,250");assert(!vectorManual); // replay after STOP
 command("V1,12,4,D,255,0,0,250",true);assert(!vectorManual); // bad CRC
 command("V1,12,4,D,99999999999999,0,0,250");assert(!vectorManual);
 command("V1,13,1,H,0,0,0,250");assert(hostSession==12); // no live takeover
 command("V1,12,5,A,0,0,0,250");assert(isLineTrackingMode);
 drive(255,120,255,120);assert(actualWheels[0]==80&&actualWheels[1]<80);
 fakeNow=800;vectorService();assert(!isLineTrackingMode); // host watchdog includes AUTO
 command("V1,13,1,H,0,0,0,250");assert(hostSession==13); // reconnect after expiry
 command("V1,12,100,D,255,0,0,250");assert(!vectorManual); // old session fenced
 command("V1,13,2,D,255,0,0,250");fakeNow=1060;vectorService();assert(!vectorManual);
 Serial.feed("DEF");vectorRead();assert(!vectorManual&&!isLineTrackingMode);
 Serial2.feed("F");vectorRead();for(int w:actualWheels)assert(w==0); // USB owns output
 std::cout<<"Firmware protocol: CRC/replay/bounds/ownership/manual timeout/AUTO watchdog/reconnect OK\n";
}
