const assert=require('assert');const{chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({httpCredentials:{username:'test',password:'test-only-passphrase'},viewport:{width:1440,height:1000}});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/video_feed',r=>r.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg"/>'}));
  await page.goto('http://127.0.0.1:18768');await page.waitForFunction(()=>latestTelemetry!==null);
  await page.locator('#claim_control').click();await page.waitForFunction(()=>ownsControl);
  await page.locator('#teach_turn_seconds').fill('0.3');await page.locator('#teach_calibrated').check();
  await page.locator('#teach_begin').click();await page.waitForFunction(()=>!teachAction&&document.getElementById('teach_status').textContent.includes('Đang ghi'));
  for(const key of ['w','d','a','d','w']){
   await page.keyboard.down(key);await page.waitForTimeout(260);await page.keyboard.up(key);await page.waitForTimeout(160);
  }
  await page.locator('#teach_finish').click();await page.waitForFunction(()=>!teachAction&&document.getElementById('teach_status').textContent.includes('Đã chốt'));
  const taught=await page.evaluate(()=>latestTelemetry.visualization.trail.filter(p=>p.leg==='teach'));
  assert(taught.length>5,'manual route must produce a red estimated trail');
  await page.locator('#teach_return').click();await page.waitForFunction(()=>teachReturning);
  // No manual vectors can interleave with server-driven return.
  await page.keyboard.down('w');await page.waitForTimeout(160);assert.deepEqual(await page.evaluate(()=>intentVector()),[0,0,0]);await page.keyboard.up('w');
  await page.waitForFunction(()=>!teachReturning&&!teachAction,{},{timeout:10000});
  await page.waitForTimeout(1200);
  const result=await page.evaluate(()=>latestTelemetry.teach_return);
  assert(result.message.includes('Đã phát hết'),JSON.stringify(result));
  assert(await page.evaluate(()=>latestTelemetry.visualization.trail.some(p=>p.leg==='return')),'return produces a blue estimated trail');
  const returnedPose=await page.evaluate(()=>latestTelemetry.visualization);
  assert(Math.hypot(returnedPose.x,returnedPose.y)<0.05,'estimated reverse trace should return near its estimated origin in fake physics');
  assert(Math.abs(returnedPose.theta-180)<10,'map uses the declared timed-turn calibration, not a fictitious yaw measurement');
  // Record a second route, then cancel return by losing the browser lease.
  await page.locator('#teach_begin').click();await page.waitForFunction(()=>!teachAction&&document.getElementById('teach_status').textContent.includes('Đang ghi'));
  await page.keyboard.down('w');await page.waitForTimeout(300);await page.keyboard.up('w');await page.waitForTimeout(180);
  await page.locator('#teach_finish').click();await page.waitForFunction(()=>!teachAction);
  await page.locator('#teach_return').click();await page.waitForFunction(()=>teachReturning);
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await page.waitForTimeout(300);
  assert.equal(await page.evaluate(()=>ownsControl),false);
  const stopped=await page.evaluate(()=>fetch('/control/diagnostics').then(r=>r.json()));
  assert.equal(stopped.teach_return.active,false);assert(stopped.current_pwm.every(x=>x===0));
  assert.deepEqual(errors,[]);
  console.log('PASS: origin, five manual gestures, red trail, stop/finish, 180 + reverse playback, blue trail, manual exclusion, blur cancels; fake USB only');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
