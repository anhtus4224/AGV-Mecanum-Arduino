#pragma once
#include <deque>
#include <string>
#include <sstream>
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
 std::deque<char> q; std::string output;
 void feed(const std::string& s){ for(char c:s) q.push_back(c); }
 void begin(long){}
 int available(){return q.size();}
 int read(){if(q.empty())return -1;char c=q.front();q.pop_front();return (unsigned char)c;}
 template<class T> void print(T x){std::ostringstream o;o<<x;output+=o.str();}
 template<class T> void print(T x,int){print(x);}
 template<class T> void println(T x){print(x);output+='\n';}
 template<class T> void println(T x,int){println(x);}
 void println(){output+='\n';}
};
inline MockSerial Serial,Serial2;
