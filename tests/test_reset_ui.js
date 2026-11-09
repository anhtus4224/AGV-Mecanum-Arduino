// Requires the loopback-only serve_reset_fixture.py. All USB is a rejecting fake.
const assert = require('assert');
const fs = require('fs');
const {chromium} = require('playwright');
const base = process.env.AGV_RESET_TEST_URL || 'http://127.0.0.1:18765';
const transparent = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5xkAAAAASUVORK5CYII=', 'base64');

async function setup(browser, viewport, profile='ready') {
    const context = await browser.newContext({viewport});
    const page = await context.newPage();
    const errors = [];
    const motorRequests = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/video_feed', route => route.fulfill({contentType:'image/png', body:transparent}));
    // Existing pagehide/blur STOPs are mocked separately. They must not turn a
    // test-fixture serial rejection into a fictitious disconnect on reload.
    await page.route('**/mecanum_control?**', route => {
        motorRequests.push(route.request().url());
        return route.fulfill({contentType:'application/json',body:JSON.stringify({status:'sent',command:'Z',sent:true,acknowledged:false})});
    });
    await page.request.post(base+'/__test__/seed', {data:{profile}});
    await page.goto(base);
    await page.waitForFunction(() => latestTelemetry !== null);
    if(viewport.width < 700) await page.evaluate(() => setMobileView('map'));
    return {page, context, errors, motorRequests};
}

async function openDialog(page) {
    await page.locator('#show_drawing_start').click();
    assert(await page.locator('#drawing_start_dialog').evaluate(e => e.open));
    const box = await page.locator('#drawing_start_dialog').boundingBox();
    const viewport = page.viewportSize();
    assert(box.y >= 0 && box.y + box.height <= viewport.height + 1);
}

async function submit(page) {
    await page.locator('#drawing_start_confirm').check();
    const reply = page.waitForResponse(r => r.url().endsWith('/drive/reset-estimate'));
    await page.locator('#drawing_start_submit').click();
    return reply;
}

(async () => {
    const browser = await chromium.launch({
        executablePath:process.env.AGV_CHROMIUM_PATH || '/usr/bin/chromium',
        headless:true, args:['--no-sandbox']
    });
    const results = [];
    try {
        {
            const {page, context, errors, motorRequests} = await setup(browser, {width:1440,height:900});
            assert((await page.locator('#val_pos').innerText()).startsWith('9.78'));
            await openDialog(page);
            await page.keyboard.press('Escape');
            assert(!(await page.locator('#drawing_start_dialog').evaluate(e => e.open)));
            assert((await page.locator('#val_pos').innerText()).startsWith('9.78'));
            results.push('Desktop: opening/cancelling dialog does not reset coordinates');

            await openDialog(page);
            await page.locator('#drawing_start_submit').click();
            assert.equal((await (await page.request.get(base+'/__test__/stats')).json()).reset_requests,0);
            const response = await submit(page);
            assert.equal(response.status(),200);
            await page.waitForFunction(() => !document.getElementById('drawing_start_dialog').open);
            assert.equal(await page.locator('#val_pos').innerText(),'0.00, 0.00 m');
            assert.equal(await page.locator('#val_deg').innerText(),'0.0°');
            assert.equal(await page.locator('#val_dist').innerText(),'0.00 m');
            const stats = await (await page.request.get(base+'/__test__/stats')).json();
            assert.equal(stats.reset_requests,1);
            assert.equal(stats.reset_usb_writes,0);
            assert.equal(motorRequests.length,0);
            results.push('Confirmation required; successful reset immediately displays origin/distance zero; no USB write');

            const oldPoll = await (await page.request.get(base+'/__test__/stale')).json();
            await page.evaluate(data => renderTelemetry(data), oldPoll);
            assert.equal(await page.locator('#val_pos').innerText(),'0.00, 0.00 m');
            results.push('Old pre-reset poll cannot restore the 9.78 m pose');

            await page.reload();
            await page.waitForFunction(() => latestTelemetry !== null);
            assert.equal(await page.locator('#val_pos').innerText(),'0.00, 0.00 m');
            results.push('Browser refresh keeps the reset server session');

            const restarted = await (await page.request.get(base+'/telemetry')).json();
            restarted.visualization.server_instance='another-test-server';
            restarted.visualization.generation=0;
            restarted.visualization.x=2;
            const displayed = await page.evaluate(data => {
                resetFence={server_instance:latestTelemetry.visualization.server_instance,generation:8};
                renderTelemetry(data);
                return document.getElementById('val_pos').textContent;
            }, restarted);
            assert(displayed.startsWith('2.00'));
            results.push('A new server instance is not blocked by the old generation fence');
            assert.deepEqual(errors,[]);
            await context.close();
        }

        for(const profile of ['no_motion','moving','auto','stale']) {
            const {page, context, errors} = await setup(browser,{width:1440,height:900},profile);
            await openDialog(page);
            const response = await submit(page);
            assert.equal(response.status(),409);
            assert(await page.locator('#drawing_start_dialog').evaluate(e => e.open));
            await page.waitForFunction(() => document.getElementById('drawing_start_status').textContent.startsWith('Chưa đặt lại:'));
            if(profile==='no_motion')assert((await page.locator('#drawing_start_status').innerText()).includes('MOTION'));
            assert.equal((await (await page.request.get(base+'/__test__/stats')).json()).reset_usb_writes,0);
            results.push('Visible in-dialog server rejection: '+profile);
            assert.deepEqual(errors,[]);
            await context.close();
        }

        {
            const {page, context, errors} = await setup(browser,{width:390,height:844});
            await openDialog(page);
            const response = await submit(page);
            assert.equal(response.status(),200);
            await page.waitForFunction(() => !document.getElementById('drawing_start_dialog').open);
            assert.equal(await page.locator('#val_pos').innerText(),'0.00, 0.00 m');
            assert.equal((await (await page.request.get(base+'/__test__/stats')).json()).reset_usb_writes,0);
            results.push('Mobile 390×844: dialog visible and reset succeeds');
            assert.deepEqual(errors,[]);
            await context.close();
        }
        console.log(JSON.stringify({browser:'Chromium headless',passed:results.length,checks:results},null,2));
    } finally {
        await browser.close();
    }
})().catch(error => {console.error(error);process.exitCode=1;});
