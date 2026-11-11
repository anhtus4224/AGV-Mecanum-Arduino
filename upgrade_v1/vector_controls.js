// One keyboard handler, Pointer Events, and one bounded vector stream.
const controllerId=crypto.randomUUID?crypto.randomUUID():'web_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2);
const heldKeys=new Map(),heldPointers=new Map();
const KEY_COMMANDS={KeyW:[1,0,0],KeyS:[-1,0,0],KeyA:[0,-1,0],KeyD:[0,1,0],KeyQ:[0,0,-1],KeyE:[0,0,1],DiagNW:[1,-1,0],DiagNE:[1,1,0],DiagSW:[-1,-1,0],DiagSE:[-1,1,0]};
const BUTTON_KEYS={W:'KeyW',B:'KeyS',A:'KeyA',D:'KeyD',Q:'KeyQ',E:'KeyE',NW:'DiagNW',NE:'DiagNE',SW:'DiagSW',SE:'DiagSE'};
let ownerLease="";
let teachReturning=false,teachAction=false;
let controlSequence=0,ownsControl=false,vectorFlight=false,joystickVector=[0,0,0],joyPointer=null;
let controlEpoch=0,intentEpoch=0,nextTicket=null,stopFlight=null,releaseFlight=null,claimFlight=false;
function controlStatus(text,error=false){byId('control_status').textContent=text;byId('control_status').style.color=error?'#fda4af':'#94a3b8';}
function clearHeldInputs(){intentEpoch++;const had=heldKeys.size||heldPointers.size||joystickVector.some(x=>x);heldKeys.clear();heldPointers.clear();joystickVector=[0,0,0];joyPointer=null;return Boolean(had);}
function intentVector(){
 const keys=new Set([...heldKeys.keys(),...heldPointers.values()]);let v=joystickVector.slice();
 for(const key of keys){const a=KEY_COMMANDS[key];if(a)v=v.map((x,i)=>x+a[i]);}
 return v.map(x=>Math.max(-1,Math.min(1,x)));
}
async function api(url,body,lease=ownerLease){
 const res=await fetch(url+(url.includes('?')?'&':'?')+'controller='+encodeURIComponent(controllerId),{
  method:'POST',headers:{'Content-Type':'application/json','X-AGV-CSRF':AGV_CSRF,'X-AGV-Lease':lease},body:JSON.stringify(body||{}),signal:AbortSignal.timeout?AbortSignal.timeout(500):undefined});
 const result=await res.json();if(!res.ok)throw Error(result.msg||result.error||res.status);return result;
}
async function controlFetch(url,options={}){
 try{
  const v=latestTelemetry&&latestTelemetry.visualization;
  const suffix='&environment='+encodeURIComponent(v?v.environment:'real')+'&generation='+(v?v.generation:0)+'&sequence='+(++controlSequence)+'&issued_ms='+(latestTelemetry?latestTelemetry.control_server_time_ms+performance.now()-lastServerControlReceived:0);
  const res=await fetch(url+suffix+'&controller='+encodeURIComponent(controllerId),{headers:{'X-AGV-CSRF':AGV_CSRF,'X-AGV-Lease':ownerLease},keepalive:Boolean(options.keepalive)});
  const d=await res.json();if(!res.ok)throw Error(d.msg||d.error);controlStatus(d.msg||d.command||'Đã gửi');return d;
 }catch(e){controlStatus(e.message,true);return null;}
}
async function transmitVector(v,ticket){
 if(!ownsControl)return;
 const d=latestTelemetry;
 if(!d)return;
 return api('/control/vector',{drive:v[0],strafe:v[1],rotate:v[2],sequence:++controlSequence,
  ticket:ticket,
  environment:d.visualization.environment,generation:d.visualization.generation});
}
function stopCmd(force=false){
 teachReturning=false;clearHeldInputs();nextTicket=null;
 if(stopFlight&&!force)return stopFlight;
 if(!ownsControl&&!force)return Promise.resolve();
 // Do not let a fresh hold overtake a STOP still travelling to the server.
 const epoch=controlEpoch;
 const flight=controlFetch('/mecanum_control?estop=1&scope='+(force?'all':'owner'),{keepalive:true})
  .then(result=>{if(!result&&epoch===controlEpoch)loseControl('Lỗi request DỪNG; kiểm tra kết nối trước khi nhận quyền lại');return result;})
  .finally(()=>{if(stopFlight===flight)stopFlight=null;});
 stopFlight=flight;
 return stopFlight;
}
function loseControl(message){teachReturning=false;controlEpoch++;ownsControl=false;nextTicket=null;clearHeldInputs();controlStatus(message,true);}
async function releaseControl(){
 if(releaseFlight)return releaseFlight;
 const had=ownsControl,lease=ownerLease;loseControl('Đã nhả quyền lái');if(!had)return;
 releaseFlight=(async()=>{try{await api('/control/release',{},lease);}catch(e){controlStatus(e.message,true);}finally{releaseFlight=null;}})();
 return releaseFlight;
}
byId('claim_control').onclick=async()=>{
 if(claimFlight||ownsControl)return;claimFlight=true;
 try{
  await releaseFlight;await stopFlight;clearHeldInputs();const epoch=++controlEpoch;
  const claim=await api('/control/claim');
  if(epoch!==controlEpoch){await api('/control/release',{},claim.lease);return;}
  ownerLease=claim.lease;nextTicket=null;ownsControl=true;byId('claim_control').blur();controlStatus('Bạn đang lái · nhả để dừng');
 }catch(e){controlStatus(e.message,true);}finally{claimFlight=false;}
};
byId('release_control').onclick=releaseControl;
byId('set_profile').onclick=async()=>{try{
 if(!byId('profile_confirm').checked)throw Error('Cần xác nhận khu vực thử, kích thước thân xe và dừng xe');
 await api('/control/profile',{cap:Number(byId('profile_cap').value),armed:byId('profile_armed').checked,confirmed:true});
 controlStatus('Đã gửi cấu hình thử; xem phản hồi Mega trong telemetry');
}catch(e){controlStatus(e.message,true);}};
setInterval(async()=>{
 if(!ownsControl||vectorFlight||stopFlight)return;
 vectorFlight=true;const epoch=controlEpoch,intentStamp=intentEpoch;
 try{
  // Active vectors return the next one-use ticket. Only one network round trip
  // per hold update, instead of renew RTT + vector RTT between every setpoint.
  if(teachAction||teachReturning){
   const d=await api('/control/renew');
   if(epoch===controlEpoch&&ownsControl){
    nextTicket=null;
    if(d.teach_return){
     byId('teach_status').textContent=d.teach_return.message+' · bước '+d.teach_return.step+'/'+d.teach_return.steps;
     if(!teachAction)teachReturning=d.teach_return.active;
    }
   }
   return;
  }
  let v=intentVector();
  if(!nextTicket||!v.some(x=>x)){
   const renewal=await api('/control/renew');
   if(epoch!==controlEpoch||intentStamp!==intentEpoch||!ownsControl||stopFlight)return;
   nextTicket=renewal.ticket;v=intentVector();
   if(!v.some(x=>x)){nextTicket=null;return;}
  }
  if(v.some(x=>x)){
   const ticket=nextTicket;nextTicket=null;
   const result=await transmitVector(v,ticket);
   if(epoch===controlEpoch&&intentStamp===intentEpoch&&ownsControl&&!stopFlight)nextTicket=result&&result.ticket;
  }
 }
 catch(e){if(epoch===controlEpoch&&intentStamp===intentEpoch&&ownsControl){try{await stopCmd();}finally{loseControl(e.message);}}}
 finally{vectorFlight=false;}
},80);
function refreshIntent(){if(!ownsControl)return;if(!intentVector().some(x=>x))stopCmd();}
function editingTarget(t){return t.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName);}
window.addEventListener('keydown',e=>{
 if(editingTarget(e.target)||e.ctrlKey||e.altKey||e.metaKey||byId('drawing_start_dialog').open)return;
 if(e.code==='Space'||e.code==='KeyZ'){e.preventDefault();if(!e.repeat)stopCmd(true);return;}
 if(!ownsControl||teachReturning||teachAction)return;
 if(e.code==='KeyX'){e.preventDefault();if(!e.repeat){clearHeldInputs();controlFetch('/toggle_mode?');}return;}
 if(!KEY_COMMANDS[e.code])return;e.preventDefault();heldKeys.set(e.code,true);
});
window.addEventListener('keyup',e=>{if(heldKeys.delete(e.code))refreshIntent();});
document.querySelectorAll('.ctrl-btn').forEach(b=>{
 const key=BUTTON_KEYS[b.dataset.act];
 if(b.dataset.act==='X'){b.onclick=()=>{clearHeldInputs();if(ownsControl)controlFetch('/toggle_mode?');};return;}
 if(!key){b.onclick=()=>stopCmd(true);return;}
 b.addEventListener('pointerdown',e=>{if(!ownsControl||teachReturning||teachAction||(e.pointerType==='mouse'&&e.button!==0))return;e.preventDefault();b.setPointerCapture(e.pointerId);heldPointers.set(e.pointerId,key);});
 for(const event of ['pointerup','pointercancel','lostpointercapture'])b.addEventListener(event,e=>{if(heldPointers.delete(e.pointerId))refreshIntent();});
 b.addEventListener('contextmenu',e=>e.preventDefault());
});
const joy=byId('vector_joystick');
function joyMove(e){
 const box=joy.getBoundingClientRect(),x=(e.clientX-box.left-box.width/2)/(box.width/2),y=(e.clientY-box.top-box.height/2)/(box.height/2);
 const norm=Math.max(1,Math.hypot(x,y));joystickVector=[-y/norm,x/norm,0].map(v=>Math.abs(v)<.12?0:v);
}
joy.addEventListener('pointerdown',e=>{if(!ownsControl||teachReturning||teachAction||(e.pointerType==='mouse'&&e.button!==0))return;e.preventDefault();joyPointer=e.pointerId;joy.setPointerCapture(e.pointerId);joyMove(e);});
joy.addEventListener('pointermove',e=>{if(e.pointerId===joyPointer)joyMove(e);});
for(const ev of ['pointerup','pointercancel','lostpointercapture'])joy.addEventListener(ev,e=>{if(e.pointerId===joyPointer){joyPointer=null;joystickVector=[0,0,0];refreshIntent();}});
window.addEventListener('blur',releaseControl);
window.addEventListener('pagehide',()=>{if(ownsControl)controlFetch('/mecanum_control?estop=1&scope=owner',{keepalive:true});loseControl('Đã rời trang');});
document.addEventListener('visibilitychange',()=>{if(document.hidden)releaseControl();});
document.addEventListener('focusin',e=>{if(editingTarget(e.target)&&clearHeldInputs())stopCmd();});

async function teachActionRequest(action){
 if(!ownsControl){controlStatus('Nhận quyền lái trước',true);return;}
 if(teachAction)return;
 teachAction=true;clearHeldInputs();nextTicket=null;
 const epoch=controlEpoch;
 try{
  // Let an already-sent manual vector settle BEFORE STOP. No new manual vectors
  // are sent while this action owns the UI. Backend still checks stopped PWM.
  while(vectorFlight&&epoch===controlEpoch)await new Promise(resolve=>setTimeout(resolve,10));
  if(epoch!==controlEpoch)return;
  await stopCmd();
  if(epoch!==controlEpoch||!ownsControl)return;
  const until=performance.now()+1500;
  while(true){
   const status=await api('/control/teach',{action:'status'});
   if(epoch!==controlEpoch||!ownsControl)return;
   if(status.stopped)break;
   if(performance.now()>until)throw Error('Mega chưa xác nhận STOP/PWM 0; kiểm tra rồi thử lại');
   await new Promise(resolve=>setTimeout(resolve,80));
  }
  if(action==='begin'){
   const anchor=await api('/drive/reset-estimate',{confirmed:true,x:0,y:0,theta:0});
   resetFence={server_instance:anchor.visualization.server_instance,generation:anchor.visualization.generation};
   stopVehicleAnimation();smoothedVehicle=null;vehicleTarget=null;
   renderTelemetry({...latestTelemetry,visualization:anchor.visualization,navigation:anchor.navigation,
    control_server_time_ms:anchor.control_server_time_ms});
  }
  const permit=await api('/control/renew');
  if(epoch!==controlEpoch||!ownsControl)return;
  const result=await api('/control/teach',{action:action,sequence:++controlSequence,ticket:permit.ticket,
   turn_seconds:Number(byId('teach_turn_seconds').value),calibrated:byId('teach_calibrated').checked});
  if(epoch!==controlEpoch||!ownsControl){await stopCmd(true);return;}
  teachReturning=result.active;
  byId('teach_status').textContent=result.message+' · '+result.segments+' đoạn · '+result.seconds+' giây';
 }catch(e){await stopCmd(true);controlStatus(e.message,true);byId('teach_status').textContent=e.message;}
 finally{teachAction=false;}
}
byId('teach_begin').onclick=()=>teachActionRequest('begin');
byId('teach_finish').onclick=()=>teachActionRequest('finish');
byId('teach_return').onclick=()=>teachActionRequest('return');
byId('teach_cancel').onclick=()=>stopCmd(true);
