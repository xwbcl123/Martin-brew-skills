import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const here=createRequire(import.meta.url);
export async function dependency(name){
 let resolved;
 try{resolved=here.resolve(name)}catch(original){
  const roots=[process.env.ASF_RUNTIME_NODE_MODULES,...(process.env.NODE_PATH||'').split(path.delimiter)].filter(Boolean);
  for(const root of roots){try{resolved=createRequire(path.join(path.resolve(root),'package.json')).resolve(name);break}catch{}}
  if(!resolved)throw Error(`Cannot resolve ${name}. Install/configure package by name or set ASF_RUNTIME_NODE_MODULES / NODE_PATH.`,{cause:original});
 }
 const mod=await import(pathToFileURL(resolved).href);return {...(mod.default||{}),...mod};
}
export function args(argv=process.argv.slice(2)) {const result={};for(let i=0;i<argv.length;i+=2){if(!argv[i].startsWith('--')||!argv[i+1])throw Error('Expected --option value');result[argv[i].slice(2)]=argv[i+1];}return result;}
export async function helpers(){const root=process.env.PRESENTATIONS_SKILL_DIR;if(!root)throw Error('Set PRESENTATIONS_SKILL_DIR to the bundled Presentations skill');return import(pathToFileURL(path.join(root,'container_tools/artifact_tool_utils.mjs')).href);}
