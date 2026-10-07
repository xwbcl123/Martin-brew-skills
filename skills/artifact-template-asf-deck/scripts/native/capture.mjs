// Compile the frozen accepted HTML into portable native layout geometry; never edit source.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {dependency,args} from './runtime.mjs';
import {loadBrand} from './brand.mjs';
const cli=args();
const sourceRoot=cli['source-root'],destination=cli['output-dir'],brandRoot=cli['brand-root']||process.env.ASF_BRAND_ROOT;
if(!brandRoot)throw Error('Set --brand-root or ASF_BRAND_ROOT');
await loadBrand(brandRoot);
if(!sourceRoot || !destination) throw Error('Usage: capture.mjs --source-root DIR --output-dir DIR --brand-root DIR');
const {chromium}=await dependency('playwright');
const browser=await chromium.launch({channel:'chrome',headless:true});
await fs.mkdir(path.join(destination,'layouts'),{recursive:true});
await fs.mkdir(path.join(destination,'inputs'),{recursive:true});
await fs.mkdir(path.join(destination,'work/reference'),{recursive:true});
for(const register of ['paper','ink']) {
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:2});
 await page.goto(pathToFileURL(path.resolve(sourceRoot,register+'.html')).href);
 await page.addStyleTag({content:'.deck-stage{transform:none!important;left:0!important;top:0!important}.deck-counter{display:none!important}'});
 await page.evaluate(()=>document.fonts.ready);
 const slides=[];
 const officialLogo=await fs.readFile(path.join(brandRoot,'logo',`asf-logo-${register}.svg`),'utf8');
 await page.evaluate(svg=>document.querySelectorAll('svg.logo').forEach(e=>{const d=new DOMParser().parseFromString(svg,'image/svg+xml').documentElement;d.setAttribute('class','logo');e.replaceWith(d.cloneNode(true))}),officialLogo);
 await page.evaluate(()=>document.fonts.load('700 48px "Spline Sans"'));
 for(let i=0;i<12;i++) {
  await page.evaluate(i=>{document.querySelectorAll('section.slide').forEach((s,k)=>s.classList.toggle('active',k===i));},i);
  const data=await page.evaluate(()=>{
   const root=document.querySelector('section.slide.active'), rs=root.getBoundingClientRect();
   const box=e=>{const b=e.getBoundingClientRect();return {left:(b.left-rs.left)*2/3,top:(b.top-rs.top)*2/3,width:b.width*2/3,height:b.height*2/3}};
   const cv=document.createElement('canvas');cv.width=cv.height=1;const ctx=cv.getContext('2d',{willReadFrequently:true});
   const color=c=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=c;ctx.fillRect(0,0,1,1);const p=ctx.getImageData(0,0,1,1).data;if(!p[3])return 'none';return '#'+[...p].slice(0,3).map(x=>x.toString(16).padStart(2,'0')).join('');};
   const texts=[],boxes=[],images=[],nodes=[],connectors=[];
   let n=0;
   for(const e of root.querySelectorAll('*')){
    if(e.closest('svg,.plot,table'))continue;
    const st=getComputedStyle(e),b=box(e); if(b.width<=0||b.height<=0)continue;
    const sides=['Top','Right','Bottom','Left'].filter(x=>parseFloat(st['border'+x+'Width'])>0);
    if(color(st.backgroundColor)!=='none'||sides.length){boxes.push({id:'box-'+(++n),selector:e.className,position:b,fill:color(st.backgroundColor),borders:sides.map(side=>({side,color:color(st['border'+side+'Color']),width:parseFloat(st['border'+side+'Width'])*2/3}))})}
    if(e.matches('.architecture-core,.architecture-leaves>div,.step,.mini-node,.layer-input span,.layer-core,.layer-output'))nodes.push({id:'node-'+nodes.length,selector:e.className,position:b,...(e.matches('.step')?{connectorOffset:box(e.querySelector('h3')).top+box(e.querySelector('h3')).height/2-b.top}:{})});
    for(const t of e.childNodes){
     if(t.nodeType!==Node.TEXT_NODE||!t.textContent.trim())continue;
     const family=st.fontFamily.includes('Georgia')?'Georgia':st.fontFamily.includes('Consolas')?'Consolas':'Arial';
     const size=Math.max(16,parseFloat(st.fontSize)*2/3),lines=[];
     // Preserve actual browser lines, including wrapping inside a single text node.
     for(let c=0;c<t.length;c++){
      const r=document.createRange();r.setStart(t,c);r.setEnd(t,c+1);const rect=r.getBoundingClientRect();
      if(!rect.width && !rect.height)continue;
      const y=st.writingMode==='vertical-rl'?rect.left:rect.top;
      let line=lines.find(l=>Math.abs(l.y-y)<2);
      if(!line){line={y,text:'',left:rect.left,top:rect.top,right:rect.right,bottom:rect.bottom};lines.push(line);}
      line.text+=t.textContent[c];line.left=Math.min(line.left,rect.left);line.top=Math.min(line.top,rect.top);line.right=Math.max(line.right,rect.right);line.bottom=Math.max(line.bottom,rect.bottom);
     }
     for(const line of lines){let text=line.text.replace(/\s+/g,' ').trim();if(!text)continue;if(st.textTransform==='uppercase')text=text.toUpperCase();
      let pos={left:(line.left-rs.left)*2/3,top:(line.top-rs.top)*2/3,width:(line.right-line.left)*2/3+24,height:Math.max((line.bottom-line.top)*2/3+6,size*1.25)};
      let rotation=0;
      if(st.writingMode==='vertical-rl'){
       // PowerPoint rotates about frame centre: keep the vertical marker in right safe margin.
       const h=(line.bottom-line.top)*2/3,w=size*1.4;
       const cx=(line.left-rs.left)*2/3+w/2,cy=(line.top-rs.top)*2/3+h/2;
       pos={left:cx-h/2,top:cy-w/2,width:h+12,height:w};rotation=90;
      }
      texts.push({id:'text-'+texts.length,text,position:pos,font:family,size,color:color(st.color),italic:st.fontStyle==='italic',bold:parseInt(st.fontWeight)>=600,rotation,letterSpacing:parseFloat(st.letterSpacing)||0});
     }
    }
   }
   for(const e of root.querySelectorAll('svg.logo,svg.deck-icon')){
    let svg=e.cloneNode(true),use=svg.querySelector('use');
    if(use){const symbol=document.querySelector(use.getAttribute('href')); if(!symbol)throw Error('Missing icon');for(const attr of ['fill','stroke','stroke-width','stroke-linecap','stroke-linejoin'])if(symbol.hasAttribute(attr))svg.setAttribute(attr,symbol.getAttribute(attr));use.replaceWith(...[...symbol.childNodes].map(x=>x.cloneNode(true)));}
    svg.setAttribute('xmlns','http://www.w3.org/2000/svg');svg.setAttribute('color',getComputedStyle(e).color);
    svg.removeAttribute('class');images.push({id:'image-'+images.length,position:box(e),svg:svg.outerHTML,alt:e.classList.contains('logo')?'ASF original logo':'ASF '+(e.querySelector('use')?.getAttribute('href')||'icon')});
   }
   const conn=(a,b,fromSide='right',toSide='left',arrow=true)=>{if(a&&b)connectors.push({from:a.id,to:b.id,fromSide,toSide,arrow})};
   const subset=selector=>nodes.filter(x=>x.selector===selector);
   const steps=subset('step');for(let j=0;j<steps.length-1;j++)conn(steps[j],steps[j+1]);
   const mini=subset('mini-node');for(let j=0;j<mini.length-1;j++)conn(mini[j],mini[j+1]);
   const core=subset('architecture-core')[0];if(core)for(const leaf of nodes.filter(x=>x.selector===''&&x.position.top>core.position.top))conn(core,leaf,'bottom','top',false);
   const layerCore=subset('layer-core')[0],out=subset('layer-output')[0];
   if(layerCore){const candidates=nodes.filter(x=>x.selector===''&&x.position.left>layerCore.position.left-1&&x.position.top<layerCore.position.top);for(const a of candidates)conn(a,layerCore,'bottom','top');conn(layerCore,out,'bottom','top');}
   const plot=root.querySelector('.plot');let chart=null;
   if(plot){const groups=[...plot.querySelectorAll('.chart-group')];const names=[...plot.querySelectorAll('.legend span')].map(e=>e.textContent.trim());chart={position:box(plot),categories:groups.map(e=>e.querySelector('.group-name').textContent.trim()),series:names.map((name,k)=>({name,values:groups.map(e=>Number(e.querySelectorAll('.value')[k].textContent)),fill:color(getComputedStyle(groups[0].querySelectorAll('.bar')[k]).backgroundColor)}))};}
   const table=root.querySelector('table');let evidence=null;
   if(table)evidence={position:box(table),values:[...table.rows].map((r,i)=>[...r.cells].map(c=>i===0?c.textContent.trim().toUpperCase():c.textContent.trim())),headerFill:color(getComputedStyle(table.rows[0].cells[0]).backgroundColor),headerBorder:color(getComputedStyle(table.rows[0].cells[0]).borderBottomColor),widths:[...table.rows[0].cells].map(c=>box(c).width),rowHeights:[...table.rows].map(r=>box(r).height)};
   return {label:root.dataset.screenLabel,notes:root.dataset.notes,background:color(getComputedStyle(root).backgroundColor),texts,boxes,images,nodes,connectors,chart,table:evidence};
  });
  const logoBytes=await page.locator('section.slide.active svg.logo').screenshot();
  for(const im of data.images)if(im.alt==='ASF original logo'){delete im.svg;im.png=logoBytes.toString('base64');}
  // Normalize outdated 10-page markers while keeping 10 core + 2 appendices.
  // Preserve the source's 10 core + 2 appendix markers verbatim.
  slides.push(data);
  await page.screenshot({path:path.join(destination,'work/reference',`${register}-${String(i+1).padStart(2,'0')}.png`)});
 }
 const html=await fs.readFile(path.join(sourceRoot,register+'.html'));
 const layout={schema:1,register,source:{path:path.relative(process.cwd(),path.join(sourceRoot,register+'.html')),sha256:createHash('sha256').update(html).digest('hex'),brandVersion:'1.2.2',brandCommit:'13741fedd7d3b28b57aa9e74d99700c2f663aa9c'},slideSize:{width:1280,height:720},slides};
 await fs.writeFile(path.join(destination,'layouts',register+'.json'),JSON.stringify(layout,null,2));
 const input={schema:1,register,slides:slides.map(s=>({texts:Object.fromEntries(s.texts.map(t=>[t.id,t.text])),...(s.chart?{chart:{categories:s.chart.categories,series:s.chart.series}}:{}),...(s.table?{table:s.table.values}:{}),notes:s.notes}))};
 await fs.writeFile(path.join(destination,'inputs',register+'.sample.json'),JSON.stringify(input,null,2));
 await page.close();
}
await browser.close();
