#!/usr/bin/env node
// Two-layer composition adapter. Semantic source/background review remains human/agent-owned.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL, fileURLToPath } from 'node:url';

export const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const assert = (ok, message) => { if (!ok) throw new Error(message); };
const positive = x => Number.isFinite(x) && x > 0;
export async function validateManifest(m, base) {
  assert(m.schema_version === 2, 'schema_version must be 2');
  assert(['image-deck','text-editable'].includes(m.route), 'route must be image-deck or text-editable');
  assert(positive(m.slide_size?.width) && positive(m.slide_size?.height), 'slide_size must be positive');
  assert(Array.isArray(m.slides) && m.slides.length > 0, 'slides must be nonempty');
  const ids = new Set();
  for (const s of m.slides) {
    assert(typeof s.id === 'string' && s.id.length && !ids.has(s.id), 'slide IDs must be unique'); ids.add(s.id);
    assert(positive(s.source_size?.width) && positive(s.source_size?.height), `${s.id}: source_size required`);
    const ratio = s.source_size.width / s.source_size.height / (m.slide_size.width / m.slide_size.height);
    assert(Math.abs(ratio - 1) < 0.005, `${s.id}: aspect ratio distortion`);
    const src = await fs.readFile(path.resolve(base, s.source));
    assert(sha256(src) === s.source_sha256, `${s.id}: source hash mismatch`);
    assert(Array.isArray(s.texts), `${s.id}: texts must be an array`);
    if (m.route === 'image-deck') { assert(s.texts.length === 0, 'image-deck cannot have overlay text'); continue; }
    const bg = await fs.readFile(path.resolve(base, s.background));
    assert(sha256(bg) === s.background_sha256, `${s.id}: background hash mismatch`);
    assert(['image-edit','provided-textless'].includes(s.background_origin), `${s.id}: background_origin required`);
    assert(s.qa?.background_review === 'pass' && s.qa.background_review_note?.trim(), `${s.id}: background visual review has not passed`);
    if (s.background_origin === 'image-edit') {
      assert(s.source_sha256 !== s.background_sha256, `${s.id}: unchanged source cannot be edited background`);
      assert(s.generation?.input_sha256 === s.source_sha256 && s.generation.tool && s.generation.generated_source, `${s.id}: image edit provenance incomplete`);
      assert((await fs.readFile(path.resolve(base,s.generation.prompt),'utf8')).trim(), `${s.id}: prompt empty`);
    }
    const textIds = new Set();
    for (const t of s.texts) {
      assert(typeof t.id === 'string' && t.id.length && !textIds.has(t.id), `${s.id}: text IDs must be unique`);textIds.add(t.id);
      assert(typeof t.text === 'string' && t.text.trim(), `${s.id}: empty text`);
      assert(Array.isArray(t.bbox) && t.bbox.length === 4 && t.bbox.every(Number.isFinite), `${s.id}/${t.id}: invalid bbox`);
      const [x,y,w,h]=t.bbox;
      assert(x>=0 && y>=0 && w>0 && h>0 && x+w<=s.source_size.width && y+h<=s.source_size.height, `${s.id}/${t.id}: bbox outside page`);
      assert(positive(t.font_px) && t.font_family?.trim(), `${s.id}/${t.id}: font required`);
      assert(t.confidence >= 0 && t.confidence <= 1, `${s.id}/${t.id}: confidence required`);
      assert(['left','center','right','justify'].includes(t.align ?? 'left'), `${s.id}/${t.id}: invalid align`);
    }
  }
  return m;
}

async function main() {
  const [manifestArg,outArg,previewArg] = process.argv.slice(2);
  assert(manifestArg && outArg && previewArg, 'Usage: compose_layers.mjs manifest.json draft.pptx preview-dir');
  const manifestPath = path.resolve(manifestArg), out = path.resolve(outArg), previewDir = path.resolve(previewArg);
  const base = path.dirname(manifestPath), m = await validateManifest(JSON.parse(await fs.readFile(manifestPath,'utf8')),base);
  await fs.access(out).then(()=>{throw new Error('Refusing to overwrite existing output')},()=>{});
  const modules = process.env.RUNTIME_NODE_MODULES;
  assert(path.isAbsolute(modules ?? ''), 'Set RUNTIME_NODE_MODULES from load_workspace_dependencies');
  const pkg = JSON.parse(await fs.readFile(path.join(modules,'@oai/artifact-tool/package.json'),'utf8'));
  const entry = typeof pkg.exports?.['.'] === 'string' ? pkg.exports['.'] : pkg.exports?.['.']?.import ?? pkg.module ?? pkg.main;
  const {Presentation,PresentationFile} = await import(pathToFileURL(path.join(modules,'@oai/artifact-tool',entry)).href);
  const p = Presentation.create({slideSize:m.slide_size});
  await fs.mkdir(path.dirname(out),{recursive:true});await fs.mkdir(previewDir,{recursive:true});
  const evidence = {schema_version:2,route:m.route,manifest_sha256:sha256(await fs.readFile(manifestPath)),slides:[]};
  for (const [i,s] of m.slides.entries()) {
    const slide = p.slides.add(), imagePath = path.resolve(base,m.route==='image-deck'?s.source:s.background);
    const ext=path.extname(imagePath).toLowerCase();
    assert(['.png','.jpg','.jpeg'].includes(ext),'Background must be PNG or JPEG');
    slide.images.add({blob:new Uint8Array(await fs.readFile(imagePath)),contentType:ext==='.png'?'image/png':'image/jpeg',alt:`${s.id} ${m.route==='image-deck'?'image-only slide':'non-text background'}`,fit:'contain',position:{left:0,top:0,width:m.slide_size.width,height:m.slide_size.height}});
    for (const t of s.texts) {
      const sx=m.slide_size.width/s.source_size.width, sy=m.slide_size.height/s.source_size.height;
      const [x,y,w,h]=t.bbox;
      const box=slide.shapes.add({geometry:'textbox',position:{left:x*sx,top:y*sy,width:w*sx,height:h*sy},fill:'none',line:{fill:'none',width:0}});
      box.text=t.text;
      box.text.style={typeface:t.font_family,fontSize:t.font_px*sy,bold:t.bold??false,italic:t.italic??false,color:t.color??'#000000',alignment:t.align??'left',verticalAlignment:'top',autoFit:'none',wrap:'square',insets:{top:0,right:0,bottom:0,left:0}};
    }
    slide.speakerNotes.textFrame.setText(s.notes??'');
    const png = new Uint8Array(await (await p.export({slide,format:'png',scale:1})).arrayBuffer());
    const preview=path.join(previewDir,`slide-${String(i+1).padStart(2,'0')}.png`);await fs.writeFile(preview,png);
    const layout=await slide.export({format:'layout'});await fs.writeFile(preview.replace('.png','.layout.json'),await layout.text());
    evidence.slides.push({id:s.id,preview,preview_sha256:sha256(png),text_count:s.texts.length});
  }
  await(await PresentationFile.exportPptx(p)).save(out);
  evidence.output=out;evidence.output_sha256=sha256(await fs.readFile(out));evidence.status='draft_requires_host_finalization_and_visual_review';
  await fs.writeFile(path.join(previewDir,'composition.json'),JSON.stringify(evidence,null,2)+'\n');
  console.log(JSON.stringify({output:out,slides:m.slides.length,status:evidence.status}));
}
if(process.argv[1] && path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url))) main().catch(e=>{console.error(e.message);process.exitCode=1});
