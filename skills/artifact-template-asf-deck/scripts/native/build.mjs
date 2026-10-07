import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {dependency,args,helpers} from './runtime.mjs';
import {loadBrand,palette} from './brand.mjs';
process.env.RUNTIME_NODE_MODULES ||= process.env.ASF_RUNTIME_NODE_MODULES || (process.env.NODE_PATH||'').split(path.delimiter)[0];
const cli=args(),inputPath=cli.input,outputDir=cli['output-dir'];
if(!inputPath||!outputDir)throw Error('Usage: build.mjs --input CONTENT.json --output-dir NATIVE_ROOT [--resource-root NATIVE_ROOT] [--brand-root BRAND_ROOT]');
const root=path.resolve(outputDir),resource=path.resolve(cli['resource-root']||outputDir);
const input=JSON.parse(await fs.readFile(inputPath,'utf8'));
if(input.schema!==1||!['paper','ink'].includes(input.register)||input.slides?.length!==12)throw Error('Require schema 1, paper/ink register and exactly 12 slides');
const layout=JSON.parse(await fs.readFile(path.join(resource,'layouts',input.register+'.json'),'utf8'));
if(layout.source.brandVersion!=='1.2.2'||layout.source.brandCommit!=='13741fedd7d3b28b57aa9e74d99700c2f663aa9c')throw Error('Unsupported brand lineage');
const brandRoot=cli['brand-root']||process.env.ASF_BRAND_ROOT||path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../assets/source/assets/asf-brand-v1.2.2');
const brand=await loadBrand(brandRoot);
const {Presentation,PresentationFile,FileBlob}=await dependency('@oai/artifact-tool');
const {GlobalFonts}=await dependency('@napi-rs/canvas');
const installed=GlobalFonts.families.map(x=>x.family);
const has=x=>installed.some(f=>f.toLowerCase()===x.toLowerCase());
const fontMeta={requested:{display:'Georgia',body:'Arial',meta:'Consolas'},available:installed,renderFallback:{display:has('Georgia')?'Georgia':null,body:has('Arial')?'Arial':null,meta:has('Consolas')?'Consolas':has('Courier New')?'Courier New':null},embeddedFonts:false};
if(!fontMeta.renderFallback.display||!fontMeta.renderFallback.body||!fontMeta.renderFallback.meta)throw Error('Required display/body or verified metadata fallback unavailable');
const {finalizePresentation}=await helpers();
const reg=input.register,stamp=cli.name||`asf-${reg}-native`,work=path.join(root,'work',stamp),finalPath=path.join(root,'output',stamp+'.pptx');
await fs.mkdir(work,{recursive:true});await fs.mkdir(path.dirname(finalPath),{recursive:true});
const p=Presentation.create({slideSize:layout.slideSize}),ink=reg==='ink';
const c=palette(brand.data,reg);
p.theme.colorScheme={name:`ASF ${reg} v1.2.2`,themeColors:{accent1:c.accent,accent2:c.info,accent3:c.warning,accent4:c.cyan,accent5:c.muted,accent6:c.teal,bg1:c.bg,bg2:c.raised,tx1:c.fg,tx2:c.muted,dk1:c.dk1,dk2:c.dk2,lt1:c.lt1,lt2:c.lt2,hlink:c.accent,folHlink:c.info}};
const master=p.masters.add(`ASF ${reg} production`);master.setColorMap({bg1:'lt1',tx1:'dk1',bg2:'lt2',tx2:'dk2',accent1:'accent1',accent2:'accent2',accent3:'accent3',accent4:'accent4',accent5:'accent5',accent6:'accent6',hlink:'hlink',folHlink:'folHlink'});master.background.fill=c.bg;
const blank=p.layouts.add(`ASF ${reg} native canvas`);blank.setParentLayoutId(master.id);
const record=[];
function shape(slide,pos,fill='none',line='none',width=0,name=''){return slide.shapes.add({name,geometry:'rect',position:pos,fill,line:{fill:line,width}})}
for(let i=0;i<12;i++){
 const l=layout.slides[i],data=input.slides[i],slide=p.slides.add();slide.setLayout(blank);slide.background.fill=c.bg;
 const textValues=data.texts;if(!textValues||Object.keys(textValues).length!==l.texts.length||l.texts.some(t=>typeof textValues[t.id]!=='string'))throw Error(`Slide ${i+1}: all text slots are required`);
 for(const b of l.boxes){if(b.fill!=='none')shape(slide,b.position,b.fill,'none',0,b.id);for(const edge of b.borders){let pos={...b.position};if(edge.side==='Top'||edge.side==='Bottom'){pos.top+=edge.side==='Bottom'?pos.height:0;pos.height=0;}else{pos.left+=edge.side==='Right'?pos.width:0;pos.width=0;}slide.shapes.add({name:b.id+'-'+edge.side,geometry:'line',position:pos,fill:'none',line:{fill:edge.color,width:edge.width}})}}
 const anchors=new Map();for(const node of l.nodes)anchors.set(node.id,shape(slide,node.selector==='step'?{...node.position,left:node.position.left-4,top:node.position.top+(node.connectorOffset||40)-8,width:node.position.width-12,height:16}:node.position,'none','none',0,node.id));
 for(const link of l.connectors){const a=anchors.get(link.from),b=anchors.get(link.to);if(!a||!b)throw Error('Broken connector node');
  // Pipeline connections share dedicated gaps at mid-height; numbering stays above them.
  slide.shapes.connect(a,b,{kind:link.fromSide==='right'?'straight':'elbow',fromSide:link.fromSide,toSide:link.toSide,line:{fill:c.muted,width:1.2},...(link.arrow?{tail:{type:'triangle',width:'sm',length:'sm'}}:{})});
 }
 for(const im of l.images){slide.images.add({blob:im.png?new Uint8Array(Buffer.from(im.png,'base64')):new TextEncoder().encode(im.svg),contentType:im.png?'image/png':'image/svg+xml',alt:im.alt,fit:'contain',position:im.position});}
 for(const t of l.texts){const text=textValues[t.id].replace('Editable DOM / SVG shapes and connectors; selectable text.','Editable native shapes and connectors; selectable text.');if(!text.trim())throw Error(`Empty text slot ${i+1}/${t.id}`);
  // Fixed layout, fresh strings. Allow bounded growth, fail instead of silent shrink/drop.
  if(text.length>Math.max(t.text.length*1.45,t.text.length+15))throw Error(`Slide ${i+1}/${t.id}: text exceeds fixed-layout capacity; shorten or author a new layout`);
  const sh=slide.shapes.add({name:`slide-${i+1}-${t.id}`,geometry:'textbox',position:{...t.position,...(t.rotation?{rotation:t.rotation}:{})},fill:'none',line:{fill:'none',width:0}});sh.text=text;
  sh.text.style={typeface:t.font==='Consolas'?fontMeta.renderFallback.meta:t.font,fontSize:t.size,color:t.color,bold:t.bold,italic:t.italic,alignment:'left',verticalAlignment:'top',autoFit:'none',wrap:'none',insets:{top:0,right:0,bottom:0,left:0},lineSpacing:1.12};
 }
 if(l.table){const values=data.table;if(values?.length!==5||values.some(r=>r.length!==4))throw Error('Evidence table requires five rows / four columns');const b=l.table.position;
  const tb=slide.tables.add({rows:5,columns:4,left:b.left,top:b.top,width:b.width,height:b.height,columnWidths:l.table.widths,values});
  tb.borders.assign({fill:c.border,width:.67});for(let r=0;r<5;r++){tb.rows[r].height=l.table.rowHeights[r];for(let k=0;k<4;k++){const cell=tb.getCell(r,k);cell.fill=r===0?(l.table.headerFill||c.raised):c.bg;cell.text.style={typeface:r===0||k===3?fontMeta.renderFallback.meta:'Arial',fontSize:r===0||k===3?16:18.67,color:k===3&&r>0?(String(values[r][k]).toLowerCase().includes('ready')?c.accent:String(values[r][k]).toLowerCase().includes('review')?c.info:c.warning):c.fg,autoFit:'none',insets:{left:16,right:8,top:8,bottom:8}};}}
 }
 if(l.chart){const ch=data.chart;if(ch?.categories.length!==3||ch.series?.length!==3||ch.series.some(s=>s.values.length!==3||s.values.some(v=>!Number.isFinite(v)||v<0||v>100)))throw Error('Chart requires 3 categories × 3 numeric series, 0–100');
  const b=l.chart.position;slide.charts.add('bar',{position:b,categories:[...ch.categories].reverse(),series:ch.series.map((s,k)=>({name:s.name,values:[...s.values].reverse(),fill:l.chart.series[k].fill,valuesFormatCode:'0'})).reverse(),barOptions:{direction:'bar',grouping:'clustered',gapWidth:60,overlap:0},hasLegend:true,legend:{position:'top',textStyle:{typeface:'Arial',fontSize:18.67,fill:c.fg}},dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:fontMeta.renderFallback.meta,fontSize:16,fill:c.fg}},yAxis:{visible:true,min:0,max:100,majorUnit:50,numberFormatCode:'0',textStyle:{typeface:fontMeta.renderFallback.meta,fontSize:16,fill:c.muted},line:{fill:c.border,width:.67},majorGridlines:null},xAxis:{visible:true,textStyle:{typeface:'Arial',fontSize:18.67,fill:c.fg},line:{fill:c.border,width:.67},majorGridlines:null},chartFill:c.bg,plotAreaFill:c.bg,chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0}});
 }
 slide.speakerNotes.textFrame.setText(`${data.notes||l.notes}\nSource: accepted production v1.0.0 ${reg}.html SHA256 ${layout.source.sha256}. ASF brand v1.2.2. Illustrative template content.`);
 record.push({slide:i+1,textSlots:l.texts.length,connectors:l.connectors.length,nativeTable:!!l.table,nativeChart:!!l.chart});
}
await fs.writeFile(path.join(work,'proto.json'),JSON.stringify(p.toProto(),null,2));
const rawPath=path.join(work,'raw.pptx'),candidatePath=path.join(work,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(rawPath);
await fs.writeFile(path.join(work,'palette.json'),JSON.stringify(c));
execFileSync(process.env.RUNTIME_PYTHON||'python3',[fileURLToPath(new URL('style_ooxml.py',import.meta.url)),rawPath,path.join(resource,'layouts',reg+'.json'),candidatePath,path.join(work,'palette.json')]);
const finalized=await finalizePresentation({workspaceDir:root,candidatePath,finalPath,pythonExecutable:process.env.RUNTIME_PYTHON||'python3',integrityValidatorPath:path.join(process.env.PRESENTATIONS_SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(process.env.PRESENTATIONS_SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','5'],explicitTotalSlideCount:12,requiredNativeTableOwnerSlides:[5],requiredNativeChartOwnerSlides:[4],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['Georgia','Arial',fontMeta.renderFallback.meta]},verifyArtifactToolImport:true,receiptPath:path.join(work,'validation.json')});
// Finalizer stages chart snapshots at its workspace root; keep them as private intermediates.
for (const entry of await fs.readdir(root)) if(entry.startsWith('.chart-data-')) {
  try { await fs.rename(path.join(root,entry),path.join(work,entry)); }
  catch(error) { if(error.code!=='ENOENT') throw error; } // concurrent register may already collect it
}

const reopened=await PresentationFile.importPptx(await FileBlob.load(finalPath));
await fs.mkdir(path.join(work,'render'),{recursive:true});for(let i=0;i<12;i++){const s=reopened.slides.getItem(i),blob=await reopened.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(work,'render',String(i+1).padStart(2,'0')+'.png'),new Uint8Array(await blob.arrayBuffer()));}
await fs.writeFile(path.join(work,'font-policy.json'),JSON.stringify(fontMeta,null,2));await fs.writeFile(path.join(work,'build-manifest.json'),JSON.stringify({inputSha256:createHash('sha256').update(await fs.readFile(inputPath)).digest('hex'),source:layout.source,finalSha256:createHash('sha256').update(await fs.readFile(finalPath)).digest('hex'),nativeObjects:record,fontPolicy:fontMeta,validation:finalized},null,2));
console.log(finalPath);
