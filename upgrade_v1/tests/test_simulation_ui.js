const assert=require('assert');const{chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const c=await b.newContext({httpCredentials:{username:'test',password:'test-only-passphrase'}});const p=await c.newPage();let errors=[];
  p.on('pageerror',e=>errors.push(e.message));await p.route('**/video_feed',r=>r.fulfill({body:''}));
  await p.goto('http://127.0.0.1:18767');await p.waitForFunction(()=>latestTelemetry!==null);
  await p.locator('#claim_control').click();await p.waitForFunction(()=>ownsControl);
  await p.waitForTimeout(1500);assert(await p.evaluate(()=>ownsControl));
  await p.locator('#drive_environment').selectOption('simulation');
  await p.waitForFunction(()=>latestTelemetry.visualization.environment==='simulation');
  await p.locator('#drive_environment').evaluate(e=>e.blur());
  const x=await p.evaluate(()=>latestTelemetry.visualization.x);
  await p.keyboard.down('w');await p.keyboard.down('a');await p.waitForTimeout(1500);await p.keyboard.up('a');await p.keyboard.up('w');
  assert(await p.evaluate(()=>ownsControl));assert((await p.evaluate(()=>latestTelemetry.visualization.x))>x);
  assert.deepEqual(errors,[]);await p.evaluate(()=>releaseControl());await c.close();
  console.log('PASS: claim and simulation movement survive repeated absent-USB retries; no page errors');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
