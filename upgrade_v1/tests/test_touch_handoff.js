// Real Chromium touch events; loopback serve_ui.py only, fake USB/camera.
const assert=require('assert');
const {chromium}=require('playwright');
const base=process.env.AGV_TEST_URL||'http://127.0.0.1:18766';
const baseline=process.env.AGV_EXPECT_BASELINE==='1';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const errors=[],rejections=[],cancelledRejections=[];let checks=0,cancelFence=0;
 try{
  const options={httpCredentials:{username:'test',password:'test-only-passphrase'}};
  const laptop=await browser.newContext({...options,viewport:{width:1440,height:900}});
  const phone=await browser.newContext({...options,viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const a=await laptop.newPage(),p=await phone.newPage();
  await p.addInitScript(()=>{
   window.netTrace=[];const f=window.fetch.bind(window);
   window.fetch=async(url,options)=>{
    const path=String(url).split('?')[0],start=Date.now();
    const response=await f(url,options);
    if(path.startsWith('/control/'))window.netTrace.push([path,start,Date.now(),response.status]);
    return response;
   };
  });
  for(const page of [a,p]){
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/video_feed',r=>r.fulfill({body:''}));
   await page.goto(base);await page.waitForFunction(()=>latestTelemetry!==null);
  }
  await a.locator('#claim_control').click();await a.waitForFunction(()=>ownsControl);
  await a.evaluate(()=>stopCmd(true));await a.evaluate(()=>releaseControl());
  await p.locator('#claim_control').tap();await p.waitForFunction(()=>ownsControl);checks++;
  if(!baseline){
   const denied=await p.evaluate(async()=>{try{await api('/control/release',{},'obsolete-lease');return false;}catch(e){return true;}});
   assert(denied,'fetch wrapper must preserve an explicitly supplied old lease');assert(await p.evaluate(()=>ownsControl));checks++;
  }
  const cdp=await phone.newCDPSession(p);
  await p.evaluate(()=>{window.touchTrace=[];for(const b of document.querySelectorAll('.ctrl-btn'))for(const type of ['pointerdown','pointerup','pointercancel','lostpointercapture','contextmenu'])b.addEventListener(type,e=>touchTrace.push([b.dataset.act,type,Math.round(performance.now())]));});
  let arrivals=[],vectors=[],stops=0,delayStop=false;
  // Model a 130 ms round trip for EACH control request, excluding telemetry.
  await p.route('**/control/renew*',async r=>{await sleep(130);await r.continue();});
  await p.route('**/control/vector*',async r=>{
   await sleep(130);arrivals.push(Date.now());vectors.push(JSON.parse(r.request().postData()));await r.continue();
  });
  await p.route('**/mecanum_control*',async r=>{stops++;if(delayStop)await sleep(350);await r.continue();});
  p.on('response',async r=>{
   if(r.url().includes('/control/vector')&&r.status()>=400){
    const seq=JSON.parse(r.request().postData()).sequence;
    (seq<=cancelFence?cancelledRejections:rejections).push({sequence:seq,status:r.status(),body:await r.text()});
   }
  });
  async function down(act){
   const btn=p.locator('.ctrl-btn[data-act="'+act+'"]');await btn.scrollIntoViewIfNeeded();const b=await btn.boundingBox();
   await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:b.x+b.width/2,y:b.y+b.height/2}]});
  }
  async function up(type='touchEnd'){await cdp.send('Input.dispatchTouchEvent',{type,touchPoints:[]});}
  let gaps=[];
  const directions=[['W',1,0],['B',-1,0],['A',0,-1],['D',0,1],['NW',1,-1],['NE',1,1],['SW',-1,-1],['SE',-1,1]];
  for(const [act,f,s] of baseline?directions.slice(0,1):directions){
   arrivals=[];vectors=[];await down(act);await sleep(1500);
   assert(await p.evaluate(()=>ownsControl),'lease lost during '+act+': '+await p.locator('#control_status').textContent()+' '+JSON.stringify(rejections)+' '+JSON.stringify(await p.evaluate(()=>netTrace)));
   assert(vectors.length>=3,'too few vectors '+act+': '+JSON.stringify(await p.evaluate(()=>({events:touchTrace,intent:intentVector(),status:byId('control_status').textContent,net:netTrace}))));
   assert(vectors.every(v=>v.drive===f&&v.strafe===s&&v.rotate===0),'wrong vector '+act);
   const local=arrivals.slice(1).map((t,i)=>t-arrivals[i]);gaps.push(...local);
   const before=stops;await up();await sleep(380);
   if(!baseline)assert.equal(stops-before,1,'release '+act+' + lost capture must send one STOP: '+JSON.stringify(await p.evaluate(()=>touchTrace)));
   checks++;
  }
  console.log(JSON.stringify({baseline,checks,maxVectorGapMs:Math.max(...gaps),gaps}));
  if(baseline){assert(Math.max(...gaps)>250,'baseline must reproduce watchdog-sized gap');return;}
  assert(Math.max(...gaps)<250,'steady hold must feed the unchanged 250 ms watchdog');
  assert.deepEqual(rejections,[]);
  // Pointer cancellation is a stop, with no automatic resumption.
  await down('NE');await sleep(500);const beforeCancel=stops;cancelFence=await p.evaluate(()=>controlSequence);await up('touchCancel');await sleep(400);
  assert.equal(stops-beforeCancel,1);assert.deepEqual(await p.evaluate(()=>intentVector()),[0,0,0]);checks++;
  // Rapid release/repress cannot overtake delayed STOP on another HTTP request.
  await down('A');await sleep(500);delayStop=true;cancelFence=await p.evaluate(()=>controlSequence);await up();await sleep(30);
  const atStop=vectors.filter(v=>v.strafe===1).length;await down('D');await sleep(230);
  assert.equal(vectors.filter(v=>v.strafe===1).length,atStop,'new hold overtook pending STOP');
  await sleep(650);assert(vectors.some(v=>v.strafe===1));delayStop=false;await up();await sleep(400);checks++;
  // Release during a pending renewal: its response must not resurrect ownership/input.
  await p.evaluate(()=>{nextTicket=null;});await down('W');await sleep(30);
  cancelFence=await p.evaluate(()=>controlSequence);
  await p.evaluate(()=>releaseControl());await up();await sleep(500);
  assert.equal(await p.evaluate(()=>ownsControl),false);assert.deepEqual(await p.evaluate(()=>intentVector()),[0,0,0]);checks++;
  await a.locator('#claim_control').click();await a.waitForFunction(()=>ownsControl);checks++;
  await a.evaluate(()=>releaseControl());await p.locator('#claim_control').tap();await p.waitForFunction(()=>ownsControl);
  await down('SE');await sleep(400);cancelFence=await p.evaluate(()=>controlSequence);await p.evaluate(()=>window.dispatchEvent(new Event('blur')));await up();await sleep(400);
  assert.equal(await p.evaluate(()=>ownsControl),false);checks++;
  await p.locator('#claim_control').tap();await p.waitForFunction(()=>ownsControl);
  await p.route('**/mecanum_control*',r=>r.fulfill({status:503,contentType:'application/json',body:'{"msg":"test STOP connection failure"}'}));
  await down('W');await sleep(400);cancelFence=await p.evaluate(()=>controlSequence);await up();await sleep(400);
  assert.equal(await p.evaluate(()=>ownsControl),false,'failed STOP request must prevent resuming');checks++;
  assert.deepEqual(errors,[]);assert.deepEqual(rejections,[]);
  console.log(JSON.stringify({passed:checks,pageErrors:errors,unexpectedVectorRejections:rejections,cancelledRequestRejections:cancelledRejections.length}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
