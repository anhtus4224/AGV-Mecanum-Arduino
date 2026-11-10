const assert=require('assert');const{chromium}=require('playwright');
const base=process.env.AGV_TEST_URL||'http://127.0.0.1:18767';
(async()=>{
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
 const context=await b.newContext({httpCredentials:{username:'test',password:'test-only-passphrase'},viewport:{width:390,height:844},hasTouch:true,isMobile:true});
 const p=await context.newPage();let errors=[],rejections=[];
 p.on('pageerror',e=>errors.push(e.message));p.on('response',async r=>{if(r.url().includes('/control/vector')&&r.status()>=400)rejections.push(await r.text());});
 await p.route('**/video_feed',r=>r.fulfill({body:''}));
 // Deliberately deliver telemetry 450 ms late, without delaying control/renew.
 await p.route('**/telemetry*',async route=>{const response=await route.fetch();await new Promise(r=>setTimeout(r,450));await route.fulfill({response});});
 await p.goto(base);await p.waitForFunction(()=>latestTelemetry!==null);
 await p.locator('#claim_control').click();await p.waitForFunction(()=>ownsControl);
 await p.locator('#drive_environment').selectOption('simulation');
 await p.waitForFunction(()=>latestTelemetry.visualization.environment==='simulation');await p.waitForTimeout(1500);
 const j=p.locator('#vector_joystick');await j.scrollIntoViewIfNeeded();const box=await j.boundingBox();
 const cdp=await context.newCDPSession(p);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x+box.width*.7,y:box.y+box.height*.3}]});
 await p.waitForTimeout(4000);
 const owned=await p.evaluate(()=>ownsControl),pose=await p.evaluate(()=>latestTelemetry.visualization);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await p.waitForFunction(()=>latestTelemetry.visualization.speed===0,{},{timeout:5000});
 const end=await p.evaluate(()=>latestTelemetry.visualization);
 console.log(JSON.stringify({owned,x:pose.x,y:pose.y,rejections,pageErrors:errors,stoppedSpeed:end.speed}));
 assert(owned);assert(pose.x>.1&&pose.y<-.05);assert.equal(end.speed,0);assert.deepEqual(rejections,[]);assert.deepEqual(errors,[]);
 await p.evaluate(()=>releaseControl());await context.close();
 }finally{await b.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
