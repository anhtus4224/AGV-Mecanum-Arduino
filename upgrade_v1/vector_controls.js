// One keyboard handler, Pointer Events, and one bounded vector stream.
const controllerId=crypto.randomUUID?crypto.randomUUID():'web_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2);
const heldKeys=new Map(),heldPointers=new Map();
const KEY_COMMANDS={KeyW:[1,0,0],KeyS:[-1,0,0],KeyA:[0,-1,0],KeyD:[0,1,0],KeyQ:[0,0,-1],KeyE:[0,0,1],DiagNW:[1,-1,0],DiagNE:[1,1,0],DiagSW:[-1,-1,0],DiagSE:[-1,1,0]};
const BUTTON_KEYS={W:'KeyW',B:'KeyS',A:'KeyA',D:'KeyD',Q:'KeyQ',E:'KeyE',NW:'DiagNW',NE:'DiagNE',SW:'DiagSW',SE:'DiagSE'};
let ownerLease="";
let controlSequence=0,ownsControl=false,vectorFlight=false,joystickVector=[0,0,0],inputOrder=0;
function controlStatus(text,error=false){byId('control_status').textContent=text;byId('control_status').style.color=error?'#fda4af':'#94a3b8';}
function clearHeldInputs(){const had=heldKeys.size||heldPointers.size||joystickVector.some(x=>x);heldKeys.clear();heldPointers.clear();joystickVector=[0,0,0];return Boolean(had);}
function intentVector(){
 const keys=new Set([...heldKeys.keys(),...heldPointers.values()]);let v=joystickVector.slice();
 for(const key of keys){const a=KEY_COMMANDS[key];if(a)v=v.map((x,i)=>x+a[i]);}
 return v.map(x=>Math.max(-1,Math.min(1,x)));
}
async function api(url,body){
 const res=await fetch(url+(url.includes('?')?'&':'?')+'controller='+encodeURIComponent(controllerId),{
  method:'POST',headers:{'Content-Type':'application/json','X-AGV-CSRF':AGV_CSRF,'X-AGV-Lease':ownerLease},body:JSON.stringify(body||{}),signal:AbortSignal.timeout?AbortSignal.timeout(500):undefined});
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
async function stopCmd(force=false){clearHeldInputs();if(!ownsControl&&!force)return;return controlFetch('/mecanum_control?estop=1',{keepalive:true});}
function loseControl(message){ownsControl=false;clearHeldInputs();controlStatus(message,true);}
async function releaseControl(){
 const had=ownsControl;clearHeldInputs();if(!had)return;
 try{await api('/control/release');}catch(e){}finally{loseControl('Đã nhả quyền lái');}
}
byId('claim_control').onclick=async()=>{try{clearHeldInputs();const claim=await api('/control/claim');ownerLease=claim.lease;ownsControl=true;byId('claim_control').blur();controlStatus('Bạn đang lái · nhả để dừng');}catch(e){controlStatus(e.message,true);}};
byId('release_control').onclick=releaseControl;
byId('set_profile').onclick=async()=>{try{
 if(!byId('profile_confirm').checked)throw Error('Cần xác nhận khu vực thử, kích thước thân xe và dừng xe');
 await api('/control/profile',{cap:Number(byId('profile_cap').value),armed:byId('profile_armed').checked,confirmed:true});
 controlStatus('Đã gửi cấu hình thử; xem phản hồi Mega trong telemetry');
}catch(e){controlStatus(e.message,true);}};
setInterval(async()=>{
 if(!ownsControl||vectorFlight)return;
 vectorFlight=true;
 try{const renewal=await api('/control/renew');const v=intentVector();if(v.some(x=>x))await transmitVector(v,renewal.ticket);}
 catch(e){try{await stopCmd();}finally{loseControl(e.message);}}
 finally{vectorFlight=false;}
},80);
function refreshIntent(){if(!ownsControl)return;if(!intentVector().some(x=>x))stopCmd();}
function editingTarget(t){return t.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName);}
window.addEventListener('keydown',e=>{
 if(editingTarget(e.target)||e.ctrlKey||e.altKey||e.metaKey||byId('drawing_start_dialog').open)return;
 if(e.code==='Space'||e.code==='KeyZ'){e.preventDefault();if(!e.repeat)stopCmd(true);return;}
 if(!ownsControl)return;
 if(e.code==='KeyX'){e.preventDefault();if(!e.repeat){clearHeldInputs();controlFetch('/toggle_mode?');}return;}
 if(!KEY_COMMANDS[e.code])return;e.preventDefault();heldKeys.set(e.code,true);
});
window.addEventListener('keyup',e=>{heldKeys.delete(e.code);refreshIntent();});
document.querySelectorAll('.ctrl-btn').forEach(b=>{
 const key=BUTTON_KEYS[b.dataset.act];
 if(b.dataset.act==='X'){b.onclick=()=>{clearHeldInputs();if(ownsControl)controlFetch('/toggle_mode?');};return;}
 if(!key){b.onclick=()=>stopCmd(true);return;}
 b.addEventListener('pointerdown',e=>{if(!ownsControl||(e.pointerType==='mouse'&&e.button!==0))return;e.preventDefault();b.setPointerCapture(e.pointerId);heldPointers.set(e.pointerId,key);});
 for(const event of ['pointerup','pointercancel','lostpointercapture'])b.addEventListener(event,e=>{heldPointers.delete(e.pointerId);refreshIntent();});
 b.addEventListener('contextmenu',e=>e.preventDefault());
});
const joy=byId('vector_joystick');let joyPointer=null;
function joyMove(e){
 const box=joy.getBoundingClientRect(),x=(e.clientX-box.left-box.width/2)/(box.width/2),y=(e.clientY-box.top-box.height/2)/(box.height/2);
 const norm=Math.max(1,Math.hypot(x,y));joystickVector=[-y/norm,x/norm,0].map(v=>Math.abs(v)<.12?0:v);
}
joy.addEventListener('pointerdown',e=>{if(!ownsControl||(e.pointerType==='mouse'&&e.button!==0))return;e.preventDefault();joyPointer=e.pointerId;joy.setPointerCapture(e.pointerId);joyMove(e);});
joy.addEventListener('pointermove',e=>{if(e.pointerId===joyPointer)joyMove(e);});
for(const ev of ['pointerup','pointercancel','lostpointercapture'])joy.addEventListener(ev,e=>{if(e.pointerId===joyPointer){joyPointer=null;joystickVector=[0,0,0];refreshIntent();}});
window.addEventListener('blur',releaseControl);
window.addEventListener('pagehide',()=>{if(ownsControl)controlFetch('/mecanum_control?estop=1',{keepalive:true});clearHeldInputs();ownsControl=false;});
document.addEventListener('visibilitychange',()=>{if(document.hidden)releaseControl();});
document.addEventListener('focusin',e=>{if(editingTarget(e.target)&&clearHeldInputs())stopCmd();});
