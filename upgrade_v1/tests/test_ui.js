const assert=require('assert');const{chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});let checks=[];
 try{
  const c=await b.newContext({httpCredentials:{username:'test',password:'test-only-passphrase'},viewport:{width:1440,height:900}});
  const p=await c.newPage();let errors=[],vectors=[];p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/video_feed',r=>r.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg"/>'}));
  p.on('request',r=>{if(r.url().includes('/control/vector'))vectors.push(JSON.parse(r.postData()));});
  await p.goto('http://127.0.0.1:18766');await p.waitForFunction(()=>latestTelemetry!==null);
  await p.locator('#claim_control').click();await p.waitForFunction(()=>ownsControl);
  await p.keyboard.down('w');await p.keyboard.down('a');await p.waitForTimeout(240);
  assert(vectors.some(v=>v.drive===1&&v.strafe===-1));checks.push('W+A produces a simultaneous vector');
  await p.keyboard.up('a');await p.waitForTimeout(200);assert(vectors.some(v=>v.drive===1&&v.strafe===0));
  await p.keyboard.up('w');
  for(const [one,two,f,s] of [['w','d',1,1],['s','a',-1,-1],['s','d',-1,1]]){await p.keyboard.down(one);await p.keyboard.down(two);await p.waitForTimeout(220);await p.keyboard.up(one);await p.keyboard.up(two);assert(vectors.some(v=>v.drive===f&&v.strafe===s));}
  checks.push('All four diagonal keyboard combinations');checks.push('Release A retains W; release all sends STOP');
  await p.locator('#show_drawing_start').click();assert(await p.locator('#drawing_start_dialog').evaluate(e=>e.open));
  await p.locator('#drawing_start_confirm').check();await p.locator('#drawing_start_submit').click();
  await p.waitForFunction(()=>!document.getElementById('drawing_start_dialog').open);checks.push('Origin reset dialog works with authenticated owner');
  assert.deepEqual(errors,[]);
  const c2=await b.newContext({httpCredentials:{username:'test',password:'test-only-passphrase'},viewport:{width:390,height:844}});
  const p2=await c2.newPage();await p2.route('**/video_feed',r=>r.fulfill({body:''}));
  await p2.goto('http://127.0.0.1:18766');await p2.waitForFunction(()=>latestTelemetry!==null);
  // New browser cannot steal an active lease. Keep first owner alive explicitly while testing API.
  const denied=await p2.evaluate(async()=>{try{await api('/control/claim');return false;}catch(e){return true;}});assert(denied);checks.push('Second browser cannot steal active owner');
  await p.evaluate(()=>releaseControl());await p2.locator('#claim_control').click();await p2.waitForFunction(()=>ownsControl);
  const j=p2.locator('#vector_joystick');await j.scrollIntoViewIfNeeded();const box=await j.boundingBox();assert(box.width>80&&box.height>80);
  let mobile=[];p2.on('request',r=>{if(r.url().includes('/control/vector'))mobile.push(JSON.parse(r.postData()));});
  await p2.mouse.move(box.x+box.width*.8,box.y+box.height*.2);await p2.mouse.down();await p2.waitForTimeout(200);await p2.mouse.up();
  assert(mobile.some(v=>v.drive>0&&v.strafe>0));checks.push('Phone viewport joystick generates diagonal vector');
  await p2.evaluate(()=>releaseControl());await c2.close();await c.close();
  console.log(JSON.stringify({checks,passed:checks.length},null,2));
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
