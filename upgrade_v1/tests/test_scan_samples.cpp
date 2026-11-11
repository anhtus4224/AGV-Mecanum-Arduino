#include "../mega_vector_v1/ScanSamples.h"
#include "../mega_vector_v1/VectorMotion.h"
#include <cassert>
#include <iostream>
int main(){
 VmScanSamples left,right;
 left.add(999);left.add(80);assert(left.confirmedCm()==999);
 left.add(75);assert(left.done()&&left.validCount==2&&left.confirmedCm()==75);
 right.add(999);right.add(999);right.add(999);assert(right.confirmedCm()==999);
 // One confirmed free side suffices; an unknown opposite diagonal cannot override it.
 VmAvoid a;a.enabled=true;a.choose(71,41,left.confirmedCm(),right.confirmedCm(),100);
 assert(a.phase==VmAvoid::OUT&&a.side==-1);
 // Never average away a close echo or authorize a sole distant return.
 left.reset();left.add(20);left.add(100);left.add(100);assert(left.confirmedCm()==20);
 a.start(200);a.choose(71,41,left.confirmedCm(),right.confirmedCm(),200);
 assert(a.phase==VmAvoid::FAULT);
 left.reset();left.add(80);left.add(999);left.add(999);assert(left.confirmedCm()==999);
 a.start(300);a.choose(71,41,left.confirmedCm(),right.confirmedCm(),300);
 assert(a.phase==VmAvoid::FAULT);
 // A below-range numeric echo is not discarded in favor of two far echoes.
 left.reset();left.add(2);left.add(152);left.add(152);assert(left.confirmedCm()==2);
 a.start(400);a.choose(999,45,left.confirmedCm(),118,400);assert(a.phase==VmAvoid::FAULT);
 std::cout<<"Scan samples: transient loss, quorum, one-sided choice, close return, all unknown OK\n";
}
