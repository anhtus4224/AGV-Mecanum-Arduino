#include "../mega_vector_v1/VectorMotion.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <initializer_list>
int main(){
 for(int cap:{80,120,160,200,255}){
  VmAvoid a;a.enabled=true;a.cap=cap;
  a.start(100);a.choose(999,45,152,118,100);
  assert(a.phase==VmAvoid::OUT&&a.side==-1&&a.selectionMode==2&&a.diagonalProof);
  int f,s,w[4];VmRange front={53,110},back={49,110},unknown={999,110},near={45,110};
  a.tick(110,front,back,unknown,near,false,f,s);assert(f==255&&s==-130&&a.phase==VmAvoid::OUT);
  vmMix(f,s,0,a.cap,w);assert(w[1]==cap&&w[2]==cap);for(int x:w)assert(abs(x)<=cap);
  // A real close return still overrides the diagonal proof.
  VmRange close={20,120};front.at=back.at=near.at=120;
  a.tick(120,front,back,close,near,false,f,s);assert(a.phase==VmAvoid::FAULT&&!strcmp(a.fault,"CLEARANCE")&&f==0&&s==0);
  a.start(200);a.choose(45,999,118,152,200);assert(a.side==1&&a.selectionMode==2);
  front.at=back.at=near.at=unknown.at=210;
  a.tick(210,front,back,near,unknown,false,f,s);assert(s==130&&a.phase==VmAvoid::OUT);
  vmMix(f,s,0,cap,w);assert(w[0]==cap&&w[3]==cap);
 }
 VmAvoid a;a.enabled=true;
 for(const auto &caseValues:{std::initializer_list<int>{999,999,152,152},
   {999,25,152,152},{999,45,60,118},{20,45,300,300},{0,45,152,118}}){
  auto p=caseValues.begin();int l=*p++,r=*p++,dl=*p++,dr=*p;
  a.start(300);a.choose(l,r,dl,dr,300);assert(a.phase==VmAvoid::FAULT);
 }
 // Normal finite-side choice may use the same stronger diagonal if echo later disappears.
 a.start(400);a.choose(200,45,152,118,400);assert(a.selectionMode==1&&a.diagonalProof);
 int f,s;VmRange front={53,410},back={49,410},unknown={999,410},near={45,410};
 a.tick(410,front,back,unknown,near,false,f,s);assert(a.phase==VmAvoid::OUT);
 // The exception is only the chosen outer side. Front, rear, near side and freshness stay guarded.
 for(int kind=0;kind<4;kind++){
  a.start(500);a.choose(999,45,152,118,500);
  front={53,510};back={49,510};near={45,510};unknown={999,510};
  if(kind==0)front.cm=999;
  if(kind==1)back.cm=999;
  if(kind==2)near.cm=999;
  if(kind==3)unknown.at=100;
  a.tick(510,front,back,unknown,near,false,f,s);assert(a.phase==VmAvoid::FAULT&&f==0&&s==0);
 }
 // Full ideal FSM with the chosen outer side remaining unknown, valid edge on near side.
 a.start(1000);a.choose(999,45,152,118,1000);
 front={70,1010};back={49,1010};near={45,1010};unknown={999,1010};
 a.tick(1010,front,back,unknown,near,false,f,s);assert(a.phase==VmAvoid::PASS&&f>0);
 for(uint32_t t=1800;t<=2000;t+=100){
  front.at=back.at=unknown.at=t;near={70,t};
  a.tick(t,front,back,unknown,near,false,f,s);assert(f>0);
 }
 assert(a.phase==VmAvoid::RETURN);
 for(uint32_t t:{2010u,2020u,2110u}){
  front.at=back.at=unknown.at=near.at=t;
  a.tick(t,front,back,unknown,near,true,f,s);assert(f>0);
 }
 assert(a.phase==VmAvoid::HANDOFF);
 std::cout<<"Directional avoid: observed case + mirrored, 5 caps, close/weak/all-unknown/stale guards OK\n";
}
