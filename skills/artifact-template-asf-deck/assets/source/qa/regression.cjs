/* Repeatable real-browser checks. No dependencies installed, no external server. */
const fs = require('fs'), path = require('path'), http = require('http'), assert = require('assert/strict'), crypto = require('crypto');
const { chromium } = require(process.env.ASF_PLAYWRIGHT || 'playwright');
const root = path.resolve(__dirname, '..'), out = path.join(__dirname, 'evidence');
fs.mkdirSync(out, {recursive:true});
const report = {browser:null,slides:[],interactions:[],responsive:[],print:[],contrast:[],fonts:[],checks:[],errors:[]};
const check = (label, condition, details) => { report.checks.push({label,pass:!!condition,details}); assert.ok(condition,label); };
const server = http.createServer((req,res) => {
  const p = path.resolve(root, '.' + decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(root + path.sep)) return res.writeHead(403).end();
  try { res.setHeader('Content-Type',p.endsWith('.html')?'text/html; charset=utf-8':p.endsWith('.css')?'text/css':p.endsWith('.js')?'text/javascript':p.endsWith('.woff2')?'font/woff2':'application/octet-stream');res.end(fs.readFileSync(p)); }
  catch { res.writeHead(404).end(); }
});
(async () => {
  let browser;
  try {
    await new Promise(r => server.listen(0,'127.0.0.1',r));
    const base = `http://127.0.0.1:${server.address().port}`;
    browser = await chromium.launch({channel:'chrome',headless:true}); report.browser = browser.version();
    const ctx = await browser.newContext({viewport:{width:1920,height:1080}}), page = await ctx.newPage();
    page.on('pageerror',e => report.errors.push(String(e)));
    page.on('response',r => {if(r.status()>=400) report.errors.push(`${r.status()} ${r.url()}`);});
    const active = () => page.locator('.slide.active').getAttribute('data-slide-id');
    const open = async (file,n) => { await page.goto(`${base}/${file}.html${n?'#'+n:''}`); await page.evaluate(() => document.fonts.ready); };
    const expectSlide = async (file,test,n) => { const actual = await active(); report.interactions.push({file,test,actual,expected:String(n)});check(`${file}: ${test}`,actual===String(n)); };
    for (const file of ['paper','ink']) {
      for (let n=1;n<=12;n++) {
        await open(file,n);await expectSlide(file,`deep link ${n}`,n);
        await page.screenshot({path:path.join(out,`${file}-${String(n).padStart(2,'0')}.png`)});
        const layout = await page.evaluate(() => {
          const s=document.querySelector('.slide.active'), sr=s.getBoundingClientRect(), scale=sr.width/1920, range=document.createRange(), outside=[], small=[];
          for(const el of s.querySelectorAll('*')) {
            if(el.closest('svg') || ['SCRIPT','STYLE'].includes(el.tagName)) continue;
            for(const node of el.childNodes) {
              if(node.nodeType!==3 || !node.textContent.trim()) continue;
              range.selectNodeContents(node);
              for(const r of range.getClientRects()) {
                if(!r.width)continue;
                const rect={x:(r.x-sr.x)/scale,y:(r.y-sr.y)/scale,w:r.width/scale,h:r.height/scale};
                const item={text:node.textContent.trim(),tag:el.tagName,cls:el.className,rect,size:parseFloat(getComputedStyle(el).fontSize)};
                if(rect.x < -1 || rect.y < -1 || rect.x+rect.w>1921 || rect.y+rect.h>1081) outside.push(item);
                if(item.size<24)small.push(item);
              }
            }
          }
          const arrows=[...s.querySelectorAll('.step:not(:last-child)')].map(el => {
            const ps=getComputedStyle(el,'::after'), r=el.getBoundingClientRect(),m=el.querySelector('.meta').getBoundingClientRect();
            const canvas=document.createElement('canvas'), c=canvas.getContext('2d');c.font=ps.font;
            const w=c.measureText(ps.content.replace(/^['"]|['"]$/g,'')).width*scale;
            const right=r.right-parseFloat(ps.right)*scale;
            return {numberRight:m.right,arrowLeft:right-w,separated:m.right+4<=right-w};
          });
          return {slide:s.dataset.slideId,outside,small,arrows,headingFont:getComputedStyle(s.querySelector('h1,h2,blockquote')).fontFamily};
        });
        report.slides.push({file,n,...layout});check(`${file} ${n}: canvas text bounds`,!layout.outside.length,layout.outside);check(`${file} ${n}: metadata >=24px`,!layout.small.length,layout.small);
        check(`${file} ${n}: Georgia retained`,layout.headingFont.startsWith('Georgia'));
        if(n===3 || n===6){
          const hierarchy=await page.evaluate(()=>{
            const groups=[...document.querySelectorAll('.slide.active .argument,.slide.active .step')];
            const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};
            return groups.map(el=>{
              const icon=box(el.querySelector('.node-icon')),number=box(el.querySelector('.meta')),title=box(el.querySelector('h3')),body=box(el.querySelector('p')),group=box(el);
              return {icon,number,title,body,group,valid:icon.right<title.x && Math.abs(number.x-title.x)<1 && number.bottom<=title.y && title.right<=group.right+1 && body.right<=group.right+1 && body.bottom<=group.bottom+1};
            });
          });
          report.slides[report.slides.length-1].hierarchy=hierarchy;
          check(`${file} ${n}: left icon and number above title`,hierarchy.every(g=>g.valid),hierarchy);
        }
        const contrast = await page.evaluate(() => {
          const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
          const ctx=canvas.getContext('2d',{willReadFrequently:true});
          const rgba=color=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=color;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data].map((v,i)=>i===3?v/255:v)};
          const over=(fg,bg)=>[0,1,2].map(i=>fg[i]*fg[3]+bg[i]*(1-fg[3]));
          const luminance=rgb=>rgb.map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
          const items=[];
          for(const el of document.querySelectorAll('.slide.active *')) {
            if(['SCRIPT','STYLE'].includes(el.tagName.toUpperCase()))continue;
            const text=[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).filter(Boolean).join(' ');
            if(!text)continue;
            const style=getComputedStyle(el);const chain=[];let node=el;
            while(node){chain.unshift(node);node=node.parentElement}
            let bg=[255,255,255];for(const parent of chain){bg=over(rgba(getComputedStyle(parent).backgroundColor),bg)}
            const color=el.closest('svg')?style.fill:style.color;
            if(color==='none')continue;
            const fg=over(rgba(color),bg),a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
            items.push({text,color,background:style.backgroundColor,foregroundRGB:fg,backgroundRGB:bg,ratio});
          }
          const surfaces=[...document.querySelectorAll('.slide.active .architecture-core,.slide.active .evidence th,.slide.active .photo-slot,.slide.active .option,.slide.active .mini-node,.slide.active .layer-core,.slide.active .chart-note,.slide.active .pipeline')].map(el=>{const st=getComputedStyle(el);return {selector:el.className||el.tagName,cssBackground:st.backgroundColor,resolvedBackground:rgba(st.backgroundColor),cssBorder:st.borderColor,resolvedBorder:rgba(st.borderColor)}});
          return {items,surfaces,minimum:Math.min(...items.map(i=>i.ratio)),failures:items.filter(i=>i.ratio<4.5)};
        });
        report.contrast.push({file,n,...contrast});check(`${file} ${n}: text contrast >=4.5`,contrast.failures.length===0,contrast.failures);
        if(n===6)check(`${file}: F04 arrow/number separation`,layout.arrows.every(a=>a.separated),layout.arrows);
        if(n===12)check(`${file}: C01 three stems + bus`,await page.evaluate(()=>[...document.querySelectorAll('.slide.active .layer-input span')].every(e=>getComputedStyle(e,'::after').content!=='none')&&getComputedStyle(document.querySelector('.slide.active .layer-input'),'::after').content!=='none'));
      }
      const cdp=await ctx.newCDPSession(page);await cdp.send('DOM.enable');await cdp.send('CSS.enable');const doc=await cdp.send('DOM.getDocument');
      for(const selector of ['.slide.active h2','.slide.active .meta','.slide.active .logo text']){const {nodeId}=await cdp.send('DOM.querySelector',{nodeId:doc.root.nodeId,selector});if(nodeId)report.fonts.push({file,selector,...await cdp.send('CSS.getPlatformFontsForNode',{nodeId})});}await cdp.detach();
      for(const [selector,key,n] of [['#deck-prev','Space',4],['#deck-prev','Enter',4],['#deck-next','Space',6],['#deck-next','Enter',6]]){
        await open(file,5);await page.locator(selector).focus();await page.keyboard.press(key);await expectSlide(file,`${selector} ${key}`,n);
      }
      await open(file,5);await page.locator('.deck-count').click();await expectSlide(file,'counter click protected',5);
      for(const [key,n] of [['ArrowRight',6],['ArrowLeft',5],['PageDown',6],['PageUp',5],['Space',6],['Home',1],['End',12],['r',1]]){await page.locator('.slide.active').focus();await page.keyboard.press(key);await expectSlide(file,key,n);}
      await open(file,1);check(`${file}: previous disabled`,await page.locator('#deck-prev').isDisabled());await open(file,12);check(`${file}: next disabled`,await page.locator('#deck-next').isDisabled());
      await open(file,5);await page.locator('.slide.active .foot a').focus();await page.keyboard.press('ArrowRight');await expectSlide(file,'footer ArrowRight',6);
      check(`${file}: focus restored to new slide`,await page.evaluate(()=>document.activeElement===document.querySelector('.slide.active')));
      check(`${file}: live counter`,await page.locator('#deck-cur').getAttribute('aria-live')==='polite');
      await open(file,7);await page.reload();await expectSlide(file,'hash reload',7);await open(file);await expectSlide(file,'stored position',7);
      await page.mouse.click(1500,520);await expectSlide(file,'right half click',8);await page.mouse.click(400,520);await expectSlide(file,'left half click',7);
      await page.locator('.slide.active .foot a').focus();await page.keyboard.press('Enter');await page.waitForURL('**/index.html');check(`${file}: footer Enter return`,page.url().endsWith('/index.html'));
      await open(file,5);await page.emulateMedia({media:'print'});check(`${file}: print all 12 visible`,await page.locator('.slide:visible').count()===12);
      check(`${file}: print chrome hidden`,!(await page.locator('.deck-counter').isVisible()));
      const pdf=await page.pdf({path:path.join(out,`${file}-print.pdf`),preferCSSPageSize:true,printBackground:true});
      const text=require('child_process').spawnSync(process.env.ASF_PDFTOTEXT || 'pdftotext',['-layout','-','-'],{input:pdf});
      if(text.error || text.status!==0)throw new Error('pdftotext is required for printed page-order validation');
      const printed=text.stdout.toString('utf8').split('\f').filter(s=>s.trim());
      const markers=['One forum.','From discussion','A forum becomes useful','Make the difference visible.','Evidence needs a visible state.','Give every discussion a path.','The value of a forum','Show the moment. Explain the outcome.','What should leave the room?','Bring a question.','Small icons. Clear meaning.','Let shapes explain relationships.'];
      check(`${file}: printed page order and headings`,printed.length===12&&printed.every((s,i)=>s.replace(/\s+/g,' ').includes(markers[i])),printed.map(s=>s.trim().slice(0,180)));
      const pages=(pdf.toString('latin1').match(/\/Type\s*\/Page\b/g)||[]).length;report.print.push({file,pages,sha256:crypto.createHash('sha256').update(pdf).digest('hex')});check(`${file}: PDF 12 pages`,pages===12);await page.emulateMedia({media:'screen'});
    }
    for(const file of ['index','overview'])for(const width of [320,360,390,430,600,768,820,1024,1366,1440,1920]){
      await page.setViewportSize({width,height:900});await open(file);
      const sw=await page.evaluate(()=>document.documentElement.scrollWidth);report.responsive.push({file,width,scrollWidth:sw});check(`${file} ${width}: no horizontal scroll`,sw<=width);
      if([390,1440].includes(width))await page.screenshot({path:path.join(out,`${file}-${width}.png`),fullPage:true});
    }
    await open('index');check('F06: selected voice and 24 count',await page.locator('body').innerText().then(s=>s.includes('24-slide overview')&&s.includes('Georgia Ink is selected.')&&/historical reference/i.test(s)));
    check('F08: CJK language/spacing',await page.locator('[lang="zh-CN"] h2, h2[lang="zh-CN"]').evaluate(e=>(getComputedStyle(e).letterSpacing==='normal'||parseFloat(getComputedStyle(e).letterSpacing)===0)&&parseFloat(getComputedStyle(e).lineHeight)/parseFloat(getComputedStyle(e).fontSize)>=1.3));
    await page.setViewportSize({width:390,height:844});await open('index');check('F08: phrase stays on one line',await page.locator('.cjk-phrase').evaluate(e=>{const r=document.createRange();r.selectNodeContents(e);return r.getClientRects().length===1}));
    await page.setViewportSize({width:1440,height:900});await open('overview');
    check('F09: all page pairs ordered',await page.locator('.thumb-card').evaluateAll(es=>es.map(e=>e.dataset.odId).join(',')===Array.from({length:12},(_,i)=>[`thumb-paper-${i+1}`,`thumb-ink-${i+1}`]).flat().join(',')));
    for(const [filter,n] of [['paper',12],['ink',12],['all',24]]){await page.locator(`[data-show="${filter}"]`).click();check(`filter ${filter}`,await page.locator('.thumb-card:visible').count()===n);}
    for(const reg of ['paper','ink']){
      const a=page.locator(`[data-od-id="thumb-${reg}-1"] .thumb-frame a`);await page.keyboard.press('Tab');await a.focus();
      const f=await a.evaluate(e=>({visible:e.matches(':focus-visible'),offset:getComputedStyle(e).outlineOffset,width:getComputedStyle(e).outlineWidth,color:getComputedStyle(e).outlineColor}));check(`F03: ${reg} inset keyboard focus`,f.visible&&parseFloat(f.offset)<0&&parseFloat(f.width)>=3,f);
      await page.screenshot({path:path.join(out,`${reg}-overview-focus.png`)});
    }
    await page.locator('.notes summary').first().focus();await page.keyboard.press('Enter');check('notes Enter',await page.locator('.notes').first().getAttribute('open')!==null);
    for(const n of [6,11,12]){await page.goto(`${base}/overview.html#pair-${n}`);check(`pair anchor ${n}`,await page.locator(`#pair-${n}`).count()===1);}
    await page.locator('[data-od-id="thumb-ink-12"] .thumb-frame a').focus();await page.keyboard.press('Enter');await page.waitForURL('**/ink.html#12');await expectSlide('ink','thumbnail Enter',12);
    const ledger=JSON.parse(fs.readFileSync(path.join(root,'assets/asf-brand-v1.2.2/PROVENANCE.json'),'utf8'));
    check('F07: peeled commit',ledger.commit==='13741fedd7d3b28b57aa9e74d99700c2f663aa9c');
    const iconLedger=JSON.parse(fs.readFileSync(path.join(root,'assets/asf-brand-v1.2.2/ICON-PROVENANCE.json'),'utf8'));
    check('F07: icons peeled commit',iconLedger.commit===ledger.commit);
    for(const [file,sha] of Object.entries({...ledger.files,...iconLedger.files}))check(`brand immutable ${file}`,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'assets/asf-brand-v1.2.2',file))).digest('hex')===sha);
    check('no browser or HTTP failures',report.errors.length===0,report.errors);
    report.pass=true;
  } finally {
    fs.writeFileSync(path.join(out,'regression.json'),JSON.stringify(report,null,2)+'\n');
    if(browser)await browser.close();await new Promise(r=>server.close(r));
  }
})().catch(e=>{console.error(e);process.exitCode=1});
