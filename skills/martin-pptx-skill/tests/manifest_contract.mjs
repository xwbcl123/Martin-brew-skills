// Bounded input-validation regression checks. No image or PPTX generation.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {validateManifest} from '../scripts/compose_layers.mjs';
const file=path.resolve(process.argv[2]),base=path.dirname(file),m=JSON.parse(await fs.readFile(file,'utf8'));
await validateManifest(m,base);
const cases=[
 ['bad hash',x=>x.slides[0].source_sha256='0'.repeat(64)],
 ['off-page bbox',x=>x.slides[0].texts[0].bbox[0]=-1],
 ['double lettering source background',x=>{x.slides[0].background=x.slides[0].source;x.slides[0].background_sha256=x.slides[0].source_sha256}],
 ['unreviewed background',x=>x.slides[0].qa.background_review='pending'],
 ['distorted aspect',x=>x.slide_size.height*=2],
 ['duplicate text ID',x=>x.slides[0].texts.push({...x.slides[0].texts[0]})],
 ['missing image input proof',x=>x.slides[0].generation.input_sha256='wrong']
];
for(const[name,mutate]of cases){const x=structuredClone(m);mutate(x);await assert.rejects(validateManifest(x,base),undefined,name);}
console.log(JSON.stringify({passed:cases.length+1,cases:['valid manifest',...cases.map(c=>c[0])]}));
