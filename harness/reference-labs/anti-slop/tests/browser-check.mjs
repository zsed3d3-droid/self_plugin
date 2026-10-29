import {chromium} from '../../../browser/playwright.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {dirname,resolve,join,isAbsolute} from 'node:path';
const project=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const requestedRoot=process.env.REFERENCE_EVIDENCE_ROOT;if(!requestedRoot||!isAbsolute(requestedRoot))throw new Error('Set REFERENCE_EVIDENCE_ROOT to an absolute private directory outside this checkout.');
const root=resolve(requestedRoot,'anti-slop');const checkout=resolve(project,'../../..');if(root===checkout||root.startsWith(checkout+'/'))throw new Error('Evidence must be outside the source checkout.');
const baseURL=process.env.REFERENCE_BASE_URL||'http://127.0.0.1:8873';
const run=join(root,'browser-runs',new Date().toISOString().replace(/[:.]/g,'-')+'-'+randomUUID());
await mkdir(dirname(run),{recursive:true});await mkdir(run);
const files=['tests/browser-check.mjs','Dockerfile','compose.yaml','adapter.md','rules.json','web/app.js','web/style.css','web/before.html','web/after.html','web/countercase.html'];
const source={};for(const file of files)source[file]=createHash('sha256').update(await readFile(join(project,file))).digest('hex');
const report={format:'scenario-reference-lab-observation/v1',lab:'anti-slop',started_at:new Date().toISOString(),run_path:run,source_files:source,source_fingerprint:createHash('sha256').update(JSON.stringify(source)).digest('hex'),scope:'Synthetic fixture only; no human timing or preference claim.',observations:[],screenshots:[],failures:[]};
const check=(value,message)=>{if(!value){report.failures.push(message);throw new Error(message);}};
const browser=await chromium.launch({headless:true});
async function capture(page,name){const path=join(run,name+'.png');await page.screenshot({path,fullPage:true,animations:'disabled'});const sha256=createHash('sha256').update(await readFile(path)).digest('hex');report.screenshots.push({name,path,sha256});return path;}
try{
for(const width of [320,390,1440]){
 for(const variant of ['before','after','countercase']){
  const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});const page=await context.newPage();const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(baseURL+'/'+variant+'.html',{waitUntil:'networkidle'});
  await page.locator('.row').last().waitFor();
  const titles=await page.locator('.row h3').allTextContents();const states=await page.locator('.row .status').allTextContents();
  const geometry=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,rows:[...document.querySelectorAll('.row')].map(el=>({id:el.dataset.id,width:el.getBoundingClientRect().width,boundaries:[...el.parentElement.closest('#groups').querySelectorAll('.panel,.tile,.row,.workspace')].length})),groups:[...document.querySelectorAll('fieldset')].map(el=>({legend:el.querySelector('legend').textContent,border:getComputedStyle(el).borderTopWidth,radius:getComputedStyle(el).borderRadius}))}));
  check(titles.join('|')==='검색 필터|상태 문구|키보드 경로',variant+' '+width+' titles changed');check(!geometry.overflow,variant+' '+width+' horizontal overflow');
  await capture(page,width+'-'+variant+'-initial');
  const action=page.getByRole('button',{name:'검색 필터 상세 열기',exact:true});await action.focus();const focused=await action.evaluate(el=>({tag:el.tagName,radius:getComputedStyle(el).borderRadius,outline:getComputedStyle(el).outlineStyle}));await action.press('Enter');const keyboardOpen=await page.locator('dialog[open]').count()===1;
  if(variant==='before'){check(!keyboardOpen,'Before keyboard diagnostic unexpectedly absent');await action.click();}
  else{check(keyboardOpen,variant+' '+width+' Enter did not open detail');}
  check(await page.locator('#detail-owner').textContent()==='작업자 A',variant+' '+width+' wrong owner');check(await page.locator('#detail-status').textContent()==='검토 대기',variant+' '+width+' wrong detail state');
  await capture(page,width+'-'+variant+'-detail');await page.keyboard.press('Escape');check(await page.locator('dialog[open]').count()===0,variant+' '+width+' Escape did not close');const focusReturned=await action.evaluate(el=>el===document.activeElement);check(focusReturned,variant+' '+width+' focus did not return');if(variant!=='before')await capture(page,width+'-'+variant+'-keyboard-return');
  if(variant!=='before'){check(states.join('|')==='검토 대기|진행 중|완료','State text lost');check(focused.tag==='BUTTON'&&focused.outline!=='none','Native focus contract lost');}
  const search=page.getByRole('searchbox',{name:'작업 검색'});await search.fill('검색');check(await page.locator('.row').count()===1,'Search did not preserve task');check((await page.locator('.row').textContent()).includes('작업자 A'),'Search owner missing');
  await search.fill('');await page.getByRole('button',{name:'검토 대기',exact:true}).click();check(await page.locator('.row').count()===1,'Ready filter returned wrong group');await page.getByRole('button',{name:'전체',exact:true}).click();check(await page.locator('.row').count()===3,'Reset lost records');
  let countercase=null;if(variant==='countercase'){check(geometry.groups.length===2&&geometry.groups.every(g=>g.border!=='0px'),'Meaningful groups lost their borders');const personal=page.getByRole('radio',{name:'개인 작업을 현재 범위로 선택'});await personal.focus();await personal.press('Space');check(await personal.isChecked(),'Radio scope not keyboard selectable');countercase={groups:geometry.groups,personal_checked:await personal.isChecked(),owner_markers:await page.locator('.owner-mark').count(),focus:await personal.evaluate(el=>({outline:getComputedStyle(el).outlineStyle,shadow:getComputedStyle(el).boxShadow,radius:getComputedStyle(el).borderRadius,appearance:getComputedStyle(el).appearance}))};check(countercase.focus.appearance==='none'&&countercase.focus.outline==='none'&&countercase.focus.shadow!=='none','Radio custom focus ring missing');check(countercase.owner_markers===3,'Identity markers lost');await capture(page,width+'-countercase-scope-selected');await search.fill('키보드');await capture(page,width+'-countercase-scope-after-search');const retained=await page.getByRole('radio',{name:'개인 작업을 현재 범위로 선택'}).isChecked();countercase.selected_scope_retained_after_search=retained;check(retained,'COUNTERCASE '+width+' search resets selected workspace');}
  check(errors.length===0,'Runtime page error');report.observations.push({width,variant,titles,visible_states:states,keyboard_opened_detail:keyboardOpen,focus_returned:focusReturned,focused,geometry,countercase,search_and_status_filter:'pass',page_errors:errors});await context.close();
 }
}
report.status='pass';
}catch(error){report.status='fail';report.error=error.message;}finally{await browser.close();report.finished_at=new Date().toISOString();await writeFile(join(run,'observation.json'),JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({status:report.status,observations:report.observations.length,screenshots:report.screenshots.length,failures:report.failures,run_path:run}));process.exitCode=report.status==='pass'?0:1;
