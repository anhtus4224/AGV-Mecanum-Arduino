#include <cassert>
#include <iostream>
#include "../mega_vector_v1/VectorMotion.h"
int main(){
 int w[4];vmMix(255,0,0,255,w);for(int i:w)assert(i==255);
 vmMix(255,130,0,255,w);assert(w[0]==255&&w[3]==255);assert(w[1]>0&&w[1]<w[0]&&w[1]==w[2]);
 vmMix(0,-255,0,255,w);assert(w[0]==-255&&w[1]==255&&w[2]==255&&w[3]==-255);
 vmMix(0,0,-255,255,w);assert(w[0]==-255&&w[1]==255&&w[2]==-255&&w[3]==255);
 for(int f=-255;f<=255;f+=51)for(int s=-255;s<=255;s+=51)for(int r=-255;r<=255;r+=51){vmMix(f,s,r,255,w);for(int a:w)assert(abs(a)<=255);}
 assert(vmRamp(3,-80,8)==0);assert(vmRamp(0,-80,8)==-8);
 std::cout<<"Motion: mixer, reversal, cap limits OK\n";
}
