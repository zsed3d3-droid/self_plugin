import {chromium} from '../../browser/playwright.mjs';
import {mkdir,writeFile} from 'node:fs/promises';
import {createHash,randomUUID} from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {isAbsolute,resolve,dirname} from 'node:path';
const requested=process.env.REFERENCE_EVIDENCE_ROOT;if(!requested||!isAbsolute(requested))throw new Error('Set REFERENCE_EVIDENCE_ROOT to an absolute private directory outside the checkout.');
const checkout=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');const output=resolve(requested,'canvas',`browser-${Date.now()}-${randomUUID()}`);if(output===checkout||output.startsWith(checkout+'/'))throw new Error('Evidence must remain outside the source checkout.');await mkdir(dirname(output),{recursive:true});await mkdir(output);const folder=pathToFileURL(output+'/');
const baseURL=process.env.REFERENCE_BASE_URL||'http://127.0.0.1:8872';
const report={author:'Motion Canvas lab implementer',scope:'Actual native Player/Stage preview+PNG; no video/audio performance claim',at:new Date().toISOString(),frames:[],errors:[],checks:[]};
console.log('EVIDENCE '+fileURLToPath(folder));
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1100}});page.on('pageerror',error=>report.errors.push(error.stack||error.message));
 await page.goto(baseURL);
 await page.waitForFunction(()=>window.motionCanvasLab&&document.querySelector('#loading').hidden,{timeout:15000});
 report.browser=await page.evaluate(()=>navigator.userAgent);report.runtime=await page.evaluate(()=>motionCanvasLab.snapshot());
 assert.equal(report.runtime.nativePlayer,true);assert.equal(report.runtime.nativeStage,true);assert.equal(report.runtime.versions.core,'3.17.2');
 for(const frame of [0,150,299]){
  const saved=await page.evaluate(async frame=>{await motionCanvasLab.seek(frame);return await motionCanvasLab.save();},frame);
  const image=await page.request.get(baseURL+saved.url);const bytes=await image.body();const hash=createHash('sha256').update(bytes).digest('hex');assert.equal(hash,saved.sha256);
  await writeFile(new URL(`frame-${frame}.png`,folder),bytes);await page.screenshot({path:fileURLToPath(new URL(`page-${frame}-1440.png`,folder)),fullPage:true});
  const outside=saved.geometry.filter(g=>g.opacity>.05&&(g.x<0||g.y<0||g.x+g.width>1280||g.y+g.height>720));
  const overlaps=[];const visible=saved.geometry.filter(g=>g.opacity>.5);for(let i=0;i<visible.length;i++)for(let j=i+1;j<visible.length;j++){const a=visible[i],b=visible[j];if(Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>1&&Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>1)overlaps.push([a.name,b.name]);}
  report.frames.push({frame,url:saved.url,sha256:hash,bytes:bytes.length,geometry:saved.geometry,outside,overlaps});
  assert.equal(outside.length,0,'visible text stays inside canvas');assert.equal(overlaps.length,0,'visible text boxes do not overlap');
 }
 const repeat=await page.evaluate(async()=>{await motionCanvasLab.seek(150);return await motionCanvasLab.save();});assert.equal(repeat.sha256,report.frames[1].sha256,'repeat seek renders identical frame pixels');report.checks.push('fixed-frame pixel determinism');
 await page.evaluate(()=>motionCanvasLab.seek(0));await page.getByRole('button',{name:'재생',exact:true}).click();await page.waitForFunction(()=>motionCanvasLab.snapshot().renderedFrame>=20);await page.getByRole('button',{name:'일시정지',exact:true}).click();const paused=await page.evaluate(()=>motionCanvasLab.snapshot());await page.waitForTimeout(250);const afterPause=await page.evaluate(()=>motionCanvasLab.snapshot());assert.equal(afterPause.paused,true);assert.equal(afterPause.renderedFrame,paused.renderedFrame);report.playback={paused,afterPause};
 for(const width of [390,320]){await page.setViewportSize({width,height:1000});await page.screenshot({path:fileURLToPath(new URL(`mobile-${width}.png`,folder)),fullPage:true});const fit=await page.evaluate(()=>({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,canvas:document.querySelector('canvas').getBoundingClientRect().toJSON()}));report.checks.push({mobile:width,geometry:fit});assert.ok(fit.documentWidth<=width);}
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.querySelector('#play').disabled&&motionCanvasLab.snapshot().paused);await page.screenshot({path:fileURLToPath(new URL('reduced-320.png',folder)),fullPage:true});report.reduced=await page.evaluate(()=>motionCanvasLab.snapshot());await page.getByRole('button',{name:'중간',exact:true}).click();await page.waitForFunction(()=>motionCanvasLab.snapshot().renderedFrame===150);assert.equal(await page.getByRole('button',{name:'재생',exact:true}).isDisabled(),true);report.checks.push('reduced-motion static end/readable transcript/explicit step seek');
 assert.deepEqual(report.errors,[]);report.status='pass';
}catch(error){report.status='failed';report.failure={message:error.message,stack:error.stack};for(const page of browser.contexts().flatMap(c=>c.pages()))await page.screenshot({path:fileURLToPath(new URL('failure.png',folder)),fullPage:true}).catch(()=>{});process.exitCode=1;}
finally{await browser.close();await writeFile(new URL('results.json',folder),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
