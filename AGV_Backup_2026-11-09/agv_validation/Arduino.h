#pragma once
#include <cmath>
#include <cstring>
#include <cstdint>
#include <algorithm>
using std::min;
using std::max;
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define HEX 16
#define A0 54
#define A1 55
#define A2 56
#define A3 57
#define A4 58
#define A5 59
inline unsigned long fakeNow = 0;
inline int inputs[80] = {};
inline int pwm[80] = {};
inline unsigned long millis(){return fakeNow;}
inline void delay(unsigned long n){fakeNow += n;}
inline void delayMicroseconds(unsigned int){}
inline void pinMode(int,int){}
inline int digitalRead(int p){return inputs[p];}
inline void digitalWrite(int,int){}
inline int analogRead(int){return 512;}
inline void analogWrite(int p,int v){pwm[p]=v;}
inline unsigned long pulseIn(int,int,unsigned long){return 0;}
inline long map(long x,long a,long b,long c,long d){return (x-a)*(d-c)/(b-a)+c;}
#define constrain(x,a,b) ((x)<(a)?(a):((x)>(b)?(b):(x)))
struct MockSerial {
 void begin(long){}
 int available(){return 0;}
 int read(){return -1;}
 template<class T> void print(T){}
 template<class T> void print(T,int){}
 template<class T> void println(T){}
 template<class T> void println(T,int){}
 void println(){}
};
inline MockSerial Serial,Serial2;
