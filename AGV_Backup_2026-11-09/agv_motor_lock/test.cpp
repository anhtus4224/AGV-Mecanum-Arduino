#include "agv_motor_lock/agv_motor_lock.ino"
#include <cassert>
#include <iostream>
int main(){for(int p:MOTOR_PINS)pwm[p]=255;setup();
for(int p:MOTOR_PINS)assert(pwm[p]==0);
for(int i=0;i<1000;i++){for(int p:MOTOR_PINS)pwm[p]=255;loop();for(int p:MOTOR_PINS)assert(pwm[p]==0);}
std::cout<<"PASS: setup and 1000 loops request zero PWM on all8 motor pins.\n";}
