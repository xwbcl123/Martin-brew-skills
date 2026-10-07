import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
export async function loadBrand(root){
 const lock=JSON.parse(await fs.readFile(new URL('brand-lock.json',import.meta.url),'utf8'));
 for(const [file,expected] of Object.entries(lock.files)){
  const actual=createHash('sha256').update(await fs.readFile(path.join(root,file))).digest('hex');
  if(actual!==expected)throw Error(`Locked ASF v1.2.2 hash mismatch: ${file}`);
 }
 const data=JSON.parse(await fs.readFile(path.join(root,'tokens/tokens.json'),'utf8'));
 if(data.version!=='1.2.2')throw Error('Brand version must be 1.2.2');
 return {data,lock};
}
export function palette(data,register){
 const map={...data.tokens,...data.registers[register]};
 const value=key=>{let v=map[key];for(let i=0;i<10&&/^var\(/.test(v);i++)v=map[v.slice(4,-1)];if(!v)throw Error(`Unresolved brand token ${key}`);return v;};
 return {bg:value(register==='ink'?'--asf-ink-900':'--asf-paper'),fg:value(register==='ink'?'--asf-on-ink':'--asf-ink-900'),raised:value('--asf-raised'),border:value('--asf-border'),muted:value('--asf-text-muted'),accent:value('--asf-accent'),info:value('--asf-info'),warning:value('--asf-warning'),cyan:value('--asf-signal-400'),teal:value('--asf-signal-600'),dk1:value('--asf-ink-900'),dk2:value('--asf-ink-800'),lt1:value('--asf-surface'),lt2:value('--asf-paper')};
}
