import fs from 'node:fs/promises';
import path from 'node:path';
import {args,dependency} from './runtime.mjs';
import {loadBrand,palette} from './brand.mjs';
const cli=args(),source=cli['brand-root']||process.env.ASF_BRAND_ROOT,dest=cli['output-dir'];
if(!source||!dest)throw Error('Usage: test-portability.mjs --brand-root SOURCE --output-dir NEW_WORK_DIR');
const {lock}=await loadBrand(source),snapshot=path.resolve(dest,'standalone-brand');await fs.mkdir(snapshot,{recursive:true});
for(const file of Object.keys(lock.files)){await fs.mkdir(path.dirname(path.join(snapshot,file)),{recursive:true});await fs.copyFile(path.join(source,file),path.join(snapshot,file));}
const verified=await loadBrand(snapshot);if(verified.data.version!=='1.2.2')throw Error('Standalone snapshot rejected');
const paper=palette(verified.data,'paper'),ink=palette(verified.data,'ink');if(paper.bg===ink.bg)throw Error('Register palette not resolved');
await fs.appendFile(path.join(snapshot,'tokens/tokens.css'),'\n/* hash mismatch fixture */\n');
let rejected=false;try{await loadBrand(snapshot)}catch(e){rejected=e.message.includes('hash mismatch')}
if(!rejected)throw Error('Modified brand snapshot was accepted');
// Restore our temporary fixture only, never upstream.
await fs.copyFile(path.join(source,'tokens/tokens.css'),path.join(snapshot,'tokens/tokens.css'));
const {Presentation}=await dependency('@oai/artifact-tool');if(!Presentation)throw Error('Configured package resolution failed');
await fs.writeFile(path.join(dest,'portability.json'),JSON.stringify({standaloneSnapshotWithoutGit:true,all10LockedAssetsVerified:true,modifiedSnapshotRejected:true,dependencyPackageResolution:true,palettesDerivedFromLockedTokens:true},null,2));
console.log('Standalone snapshot and dependency portability checks passed');
