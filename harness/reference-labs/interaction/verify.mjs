import {chromium} from '../../browser/playwright.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
const root=path.dirname(new URL(import.meta.url).pathname);
const stamp=new Date().toISOString().replace(/[:.]/g,'-');
const evidenceRoot=process.env.REFERENCE_EVIDENCE_ROOT||process.env.INTERACTION_VERIFY_OUTPUT;
if(!evidenceRoot)throw new Error('Set REFERENCE_EVIDENCE_ROOT to a private output directory outside the checkout');
const repo=path.resolve(root,'../../..');
const outputRoot=path.resolve(evidenceRoot);
if(outputRoot===repo||outputRoot.startsWith(repo+path.sep))throw new Error('Evidence must stay outside the checkout');
const out=path.resolve(outputRoot,stamp+'-'+crypto.randomUUID());
await fs.mkdir(outputRoot,{recursive:true});await fs.mkdir(out);
const browser=await chromium.launch({headless:true});
const report={created_at:new Date().toISOString(),base:process.env.REFERENCE_LAB_BASE||'http://127.0.0.1:8871',scope:'Synthetic browser task, no human adoption or preference claim',cases:[],errors:[],source_hashes:{},script_sha256:crypto.createHash('sha256').update(await fs.readFile(new URL(import.meta.url))).digest('hex')};
const assert=(condition,message)=>{if(!condition)throw new Error(message);};
const modes=['css','motion','anime','animate-css','gsap'];
try{
 for(const mode of modes){for(const width of [320,390,1440]){
  const entry={mode,width,reduced:false,events:[],console:[],network:[],frames:[],assertions:[]};report.cases.push(entry);
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'no-preference'});const page=await context.newPage();
  page.on('pageerror',error=>entry.console.push({kind:'pageerror',message:error.message}));page.on('console',msg=>{if(msg.type()==='error')entry.console.push({kind:'console',message:msg.text()});});
  page.on('requestfailed',request=>entry.network.push({failed:request.url(),failure:request.failure()}));
  const chunks=[];page.on('response',response=>{if(response.url().includes('/_next/static/')&&response.url().includes('.js'))chunks.push((async()=>{const bytes=await response.body();return {url:response.url(),bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};})());});
  try{
   await page.goto(report.base+'/lab/'+mode,{waitUntil:'networkidle'});await page.locator('[data-ready=true]').waitFor();
   const theme=await page.evaluate(()=>({background:getComputedStyle(document.body).backgroundColor,font:getComputedStyle(document.querySelector('h1')).fontSize,overflow:document.documentElement.scrollWidth>innerWidth}));entry.theme=theme;
   assert(theme.background==='rgb(247, 248, 244)','Tailwind semantic bg-paper not compiled/applied');assert(!theme.overflow,'horizontal overflow');entry.assertions.push('Tailwind theme utility and mobile fit');
   await page.locator('.document-row').filter({hasText:'Budget summary'}).click();assert(await page.locator('.task').getAttribute('data-selected')==='budget','selection did not update');
   const opacity=()=>page.locator('#document-details').evaluate(el=>({opacity:Number(getComputedStyle(el).opacity),visibility:getComputedStyle(el).visibility,animations:el.getAnimations().map(a=>({state:a.playState,time:a.currentTime,duration:a.effect?.getComputedTiming().duration}))}));
   entry.frames.push({phase:'before-hide',...await opacity()});await page.locator('#reveal-control').click();await page.waitForTimeout(80);entry.frames.push({phase:'mid-hide',...await opacity()});
   if(width===390){await page.screenshot({path:path.join(out,mode+'-390-mid-hide.png'),fullPage:true});}
   await page.waitForTimeout(350);entry.frames.push({phase:'after-hide',...await opacity()});assert((await opacity()).visibility==='hidden','hide final visibility wrong');assert(entry.frames[1].opacity>0&&entry.frames[1].opacity<1,'no intermediate opacity observed');entry.assertions.push('before/mid/after actual animation sampling');
   await page.locator('#reveal-control').click();await page.waitForTimeout(35);await page.locator('#reveal-control').click();await page.waitForTimeout(35);await page.locator('#reveal-control').click();await page.waitForTimeout(400);
   assert(await page.locator('#reveal-control').getAttribute('aria-expanded')==='true','rapid reverse semantic state wrong');assert((await opacity()).opacity===1,'rapid reverse visual state stale');assert((await opacity()).visibility==='visible','rapid reverse hidden');assert((await opacity()).animations.length===0,'residual browser animations');entry.assertions.push('interrupted hide/show/hide/show final state');
   const mark=page.getByRole('button',{name:'Mark reviewed',exact:true});await mark.focus();await page.keyboard.press('Enter');await page.locator('dialog[open]').waitFor();await page.keyboard.press('Escape');assert(await mark.evaluate(el=>el===document.activeElement),'Escape focus did not return');assert(!(await page.locator('.task').getAttribute('data-reviewed')).includes('budget'),'cancel mutated review');entry.assertions.push('keyboard open/cancel and focus return');
   await mark.click();await page.getByRole('button',{name:'Confirm review',exact:true}).click();assert((await page.locator('.task').getAttribute('data-reviewed')).includes('budget'),'confirmation not saved');
   await page.locator('.document-row').filter({hasText:'Delivery schedule'}).click();await page.locator('.document-row').filter({hasText:'Budget summary'}).click();assert(await page.getByRole('button',{name:'Review again',exact:true}).count()===1,'review lost on selection change');
   entry.interaction_events=await page.evaluate(()=>window.__interactionProof);const completions=entry.interaction_events.filter(e=>e.event==='api-complete');assert(completions.length>0,'no actual API completion');for(const event of completions)assert(completions.filter(e=>e.revision===event.revision).length===1,'duplicate completion for revision '+event.revision);assert(entry.interaction_events.some(e=>e.event==='api-cancel'&&!e.finished),'rapid reversal did not exercise cancellation');entry.assertions.push('one completion per revision, real interrupted call');
   await page.reload({waitUntil:'networkidle'});await page.locator('[data-ready=true]').waitFor();assert(await page.locator('.task').getAttribute('data-selected')==='budget','selected state lost on direct reload');assert((await page.locator('.task').getAttribute('data-reviewed')).includes('budget'),'review lost on direct reload');entry.assertions.push('confirmation preserved across selection/direct reload');
   await page.screenshot({path:path.join(out,mode+'-'+width+'-final.png'),fullPage:true});entry.events=await page.evaluate(()=>window.__interactionProof);assert(entry.events.some(e=>e.event==='module-loaded'),'no runtime module load evidence');assert(!entry.console.length,'runtime console error');
  }catch(error){entry.failure=error.message;report.errors.push({mode,width,error:error.message});await page.screenshot({path:path.join(out,mode+'-'+width+'-failure.png'),fullPage:true}).catch(()=>{});entry.events=await page.evaluate(()=>window.__interactionProof).catch(()=>[]);}
  entry.chunks=await Promise.all(chunks);await context.close();
 }}
 for(const mode of modes){
  const entry={mode,width:390,reduced:true,events:[],assertions:[]};report.cases.push(entry);const context=await browser.newContext({viewport:{width:390,height:1000},reducedMotion:'reduce'});const page=await context.newPage();
  try{await page.goto(report.base+'/lab/'+mode,{waitUntil:'networkidle'});await page.locator('[data-ready=true]').waitFor();await page.locator('#reveal-control').click();await page.waitForTimeout(100);assert(await page.locator('#document-details').evaluate(el=>getComputedStyle(el).visibility)==='hidden','reduced hide not immediate');await page.locator('#reveal-control').click();await page.waitForTimeout(100);assert(await page.locator('#document-details').evaluate(el=>getComputedStyle(el).opacity)==='1','reduced show not immediate');entry.events=await page.evaluate(()=>window.__interactionProof);assert(entry.events.filter(e=>e.event==='api-start').every(e=>e.duration===0&&e.reduced),'reduced mode still requests nonzero duration');entry.assertions.push('reduced-motion immediate semantic and visual state');await page.screenshot({path:path.join(out,mode+'-390-reduced.png'),fullPage:true});}catch(error){entry.failure=error.message;report.errors.push({mode,reduced:true,error:error.message});}await context.close();
 }
 const sourceFiles=await fs.readdir(root,{recursive:true});for(const name of sourceFiles){if(/^(?:node_modules|\.next|verification)\//.test(name))continue;const full=path.join(root,name);if((await fs.stat(full)).isFile())report.source_hashes[name]=crypto.createHash('sha256').update(await fs.readFile(full)).digest('hex');}
}finally{await browser.close();report.status=report.errors.length?'FAIL':'PASS';await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,cases:report.cases.length,errors:report.errors,report:path.join(out,'report.json')}));}
if(report.errors.length)process.exitCode=1;
