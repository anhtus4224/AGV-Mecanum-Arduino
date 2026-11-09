#include "/workspace/agv_connection_repair/ArduinoTest.h"
#include <cassert>
#include <iostream>
#include "/workspace/agv_web_safe1_final/agv_mega_safe/agv_mega_safe.ino"
void zero(){for(int p:{44,3,5,9,7,8,11,12})assert(pwm[p]==0);}
void feed(const std::string& s){Serial.feed(s);readSerialCommands();}
int main(){fakeNow=10000;hostIoReady=true;hostStop();zero();
feed("CFG:OBS=22,OUT=3300,FWD=5400,BACK=2300,SPD=160,BASE=120,FAST=190\nFQEM");zero();assert(!isLineTrackingMode);
feed("@DRIVE:E\n");zero();
feed("@HELLO\n");assert(hostSession&&Serial.output.find("AGV:SAFE1")!=std::string::npos);zero();
feed("@DRIVE:E\n");assert(currentCommand=='E'&&pwm[3]==255);
fakeNow+=181;handleManualMode();zero();
feed("@MODE:AUTO\n");assert(isLineTrackingMode);feed("@MODE:AUTO\n");assert(isLineTrackingMode);
feed("@STOP\n");assert(!isLineTrackingMode);zero();
feed("@MODE:AUTO\n");fakeNow+=1501;hostWatchdog();assert(!hostSession&&!isLineTrackingMode);zero();
feed("@HELLO\n@DRIVE:F\n");fakeNow+=500;feed("@PING\n");fakeNow+=201;handleManualMode();zero();
feed("@MODE:AUTO\n");bool completed=nonBlockingAction('F',120,2000);assert(!completed&&!isLineTrackingMode);zero();
feed("@HELLO\n@MODE:AUTO\n@MODE:MANUAL\n");assert(!isLineTrackingMode);zero();
feed("@HELLO\n@DRIVE:");zero();feed("F\n");assert(currentCommand=='F');feed("@STOP\n");zero();
feed("@"+std::string(100,'F')+"\n");zero();
feed("@HELLO\n@MODE:AUTO\n");
auto before = Serial.output.size();
nonBlockingAction('F',120,350);
assert(Serial.output.substr(before).find("DATA:") != std::string::npos);
feed("@STOP\n");zero();
feed("@HELLO\n"); Serial2.feed("FEEM");readSerialCommands();zero();assert(!isLineTrackingMode);
feed("@MODE:AUTO\n");servoMove(90,1600);zero();assert(!hostSession&&!isLineTrackingMode);
std::cout<<"PASS firmware: CFG/raw rejection, handshake, framed drive, stop, idempotent AUTO, watchdog, abort during avoidance, fragmentation/overflow.\n";}
