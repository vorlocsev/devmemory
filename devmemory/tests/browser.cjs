// Real standalone API + Chromium; simulated Ingress proxy for UI routing only.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {once}=require('node:events');
const token='browser-fixture-only-not-a-real-secret-0000';
const origin='http://127.0.0.1:18099';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function ready(page){await page.waitForFunction(()=>!document.querySelector('#workspace').inert&&!document.querySelector('#auth').inert)}
async function visible(page,selector){await page.locator(selector).waitFor({state:'visible'})}
async function createProject(page,slug){
  await page.locator('[data-tab=projects]').click();
  await page.locator('#projectForm [name=slug]').fill(slug);
  await page.locator('#projectForm [name=name]').fill(slug);
  await page.locator('#projectForm button').click();
  await ready(page);
  await visible(page,'[data-panel=memory]');
  assert.equal(await page.locator('#project').inputValue(),slug);
}
async function main(){
  const data=await fs.mkdtemp(path.join(os.tmpdir(),'devmemory-browser-'));
  const child=spawn('python',['devmemory/server.py','--host','127.0.0.1','--port','18099','--data',data,'--mode','standalone'],{env:{...process.env,DEVMEMORY_TOKEN:token},stdio:'inherit'});
  let browser;
  try{
    let up=false;
    for(let i=0;i<80;i++){try{if((await fetch(origin+'/health')).ok){up=true;break}}catch{}await sleep(100)}
    assert.ok(up,'server startup');
    browser=await chromium.launch();
    const context=await browser.newContext({locale:'en-US',viewport:{width:390,height:844},acceptDownloads:true});
    const page=await context.newPage(); const errors=[];
    page.on('pageerror',err=>errors.push(err.message));
    await page.goto(origin+'/'); await visible(page,'#auth'); await ready(page);
    assert.equal(await page.locator('#workspace').isVisible(),false);
    await page.locator('#token').fill('incorrect');
    await page.locator('#authForm button').click();await ready(page);
    assert.match(await page.locator('#status').textContent(),/Forbidden/);
    await page.locator('#token').fill(token);
    await page.locator('#authForm button').click();await visible(page,'#workspace');await ready(page);
    assert.equal(await page.locator('#auth').isVisible(),false);
    await createProject(page,'alpha-test');
    await page.locator('#newEntry').click();
    await page.locator('#entryForm [name=title]').fill('Проверка ядра');
    await page.locator('#entryForm [name=body]').fill('Сборка прошивки');
    await page.locator('#entryForm button[data-i=save]').click();await ready(page);
    await visible(page,'#entries article');
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'no horizontal page overflow in connected mobile workspace');
    assert.match(await page.locator('#entries').textContent(),/Проверка ядра/);
    await page.locator('#query').fill('провер'); await page.locator('#searchForm button').click(); await ready(page);
    assert.equal(await page.locator('#entries article').count(),1);
    await page.locator('#query').fill('nomatch');await page.locator('#searchForm button').click();await ready(page);
    assert.equal(await page.locator('#entries article').count(),0);
    await createProject(page,'beta_test');
    assert.equal(await page.locator('#entries article').count(),0);
    await page.locator('#project').selectOption('alpha-test');await ready(page);
    assert.equal(await page.locator('#entries article').count(),1);
    await page.locator('[data-tab=integrations]').click();
    assert.equal(await page.locator('#githubSync').isDisabled(),true);
    await page.locator('#githubRepo').fill('Owner/Repo');
    await page.locator('#githubForm button').click();await ready(page);
    assert.equal(await page.locator('#githubRepo').inputValue(),'owner/repo');
    assert.equal(await page.locator('#githubSync').isDisabled(),false);
    // Browser routing fixture exercises sync controls without hitting public API.
    let syncCalls=0;
    await page.route(origin+'/api/github/sync',async route=>{
      const req=route.request();
      assert.equal(req.method(),'POST');
      assert.equal(req.headers().authorization,'Bearer '+token);
      assert.equal(req.headers()['x-devmemory'],'1');
      assert.deepEqual(req.postDataJSON(),{project:'alpha-test'});
      syncCalls++;
      return route.fulfill({json:{repository:'owner/repo',observed:3,inserted:syncCalls===1?3:0,duplicates:syncCalls===1?0:3}});
    });
    await page.locator('#githubSync').click();await ready(page);
    assert.match(await page.locator('#githubResult').textContent(),/3 \/ 0/);
    await page.locator('#githubSync').click();await ready(page);
    assert.match(await page.locator('#githubResult').textContent(),/0 \/ 3/);
    await page.unroute(origin+'/api/github/sync');
    await page.locator('#project').selectOption('beta_test');await ready(page);
    assert.equal(await page.locator('#githubRepo').inputValue(),'');
    assert.equal(await page.locator('#githubSync').isDisabled(),true);
    await page.locator('#project').selectOption('alpha-test');await ready(page);
    assert.equal(await page.locator('#githubRepo').inputValue(),'owner/repo');
    await page.locator('[data-tab=memory]').click();
    const dl=page.waitForEvent('download');await page.locator('#export').click();
    assert.equal((await dl).suggestedFilename(),'alpha-test-context.md');await ready(page);
    await page.locator('#lang').selectOption('ru');
    assert.equal(await page.locator('[data-tab=memory]').textContent(),'Память');
    await page.locator('[data-tab=settings]').click();await page.locator('#theme').selectOption('dark');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    const backupDownload=page.waitForEvent('download');await page.locator('#backupExport').click();
    const backupFile=await backupDownload;assert.match(backupFile.suggestedFilename(),/^devmemory-backup-.*\.json$/);await ready(page);
    const backupPath=await backupFile.path();const backup=JSON.parse(await fs.readFile(backupPath,'utf8'));
    assert.equal(backup.format,'devmemory-backup-v2');assert.deepEqual(backup.payload.github_bindings,[{project:'alpha-test',repository:'owner/repo'}]);assert.equal(backup.payload.projects.length,2);assert.equal(backup.payload.entries.length,1);
    await page.locator('#disconnect').click();await visible(page,'#auth');
    await page.reload();await visible(page,'#auth');await ready(page);
    assert.equal(await page.locator('#lang').inputValue(),'ru');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    assert.equal(await page.locator('#token').inputValue(),'');
    assert.deepEqual(errors,[]);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'no horizontal page overflow on mobile');
    await context.close();
    console.log('PASS: standalone authentication, CRUD, Cyrillic FTS, isolation, export, locale/theme persistence, mobile layout');

    // Simulate the HA ingress path rewrite without weakening production authorization.
    // The browser must send no bearer token. The fixture injects one only upstream.
    const ing=await browser.newContext({locale:'ru-RU',viewport:{width:1280,height:800}});
    const ip=await ing.newPage();const ingressErrors=[];
    ip.on('pageerror',err=>ingressErrors.push(err.message));
    await ip.route(origin+'/fixture-ingress/**',async route=>{
      const req=route.request(),u=new URL(req.url());
      assert.equal(req.headers().authorization,undefined,'browser must not send token in ingress mode');
      const target=u.pathname.slice('/fixture-ingress'.length)+u.search;
      if(target==='/health')return route.fulfill({json:{status:'ok',version:'0.3.0',mode:'ingress'}});
      const response=await route.fetch({url:origin+target,headers:{...req.headers(),authorization:'Bearer '+token}});
      return route.fulfill({response});
    });
    await ip.goto(origin+'/fixture-ingress/');await visible(ip,'#workspace');await ready(ip);
    assert.equal(await ip.locator('#auth').isVisible(),false);
    assert.equal(await ip.locator('#disconnect').isVisible(),false);
    assert.match(await ip.locator('#entries').textContent(),/Проверка ядра/);
    assert.ok(await ip.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'no horizontal page overflow in desktop workspace');
    await ip.locator('[data-tab=integrations]').click();await visible(ip,'[data-panel=integrations]');
    assert.match(await ip.locator('[data-panel=integrations]').textContent(),/GitHub/);
    assert.deepEqual(ingressErrors,[]);await ing.close();
    console.log('PASS: simulated ingress path, automatic workspace, token hidden, navigation');
  }finally{
    if(browser)await browser.close();
    if(child.exitCode===null){child.kill('SIGTERM');await once(child,'exit')}
    await fs.rm(data,{recursive:true,force:true});
  }
}
main().catch(e=>{console.error(e);process.exitCode=1});
