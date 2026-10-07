#!/usr/bin/env python3
"""Check a packaged ASF family and native samples without changing them."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
errors=[];results={}
def require(ok,message):
    if not ok:errors.append(message)
def read_json(p):return json.loads(p.read_text(encoding='utf-8'))
try:
    card=read_json(root/'artifact-template.json')
    require(card.get('kind')=='presentation','Gallery kind must be presentation')
    for field in ['reference','preview']:require((root/card[field]).is_file(),f'Missing {field}')
    registry=read_json(root/'references/template-registry.json')
    for variant in ['paper','ink']:
        spec=registry['variants'][variant];p=root/spec['reference']
        require((root/spec['preview']).is_file(),f'Missing {variant} preview')
        layout=read_json(root/spec['layout']);source=root/'assets/source'/f'{variant}.html'
        require(hashlib.sha256(source.read_bytes()).hexdigest()==layout['source']['sha256'],f'{variant} native capture is stale')
        require(p.is_file(),f'Missing {variant} native reference')
        if not p.is_file():continue
        with zipfile.ZipFile(p) as z:
            slides=sorted(n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n));ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
            require(len(slides)==12,f'{variant} expected12 slides')
            counts={'slides':len(slides),'text_shapes':0,'tables':0,'chart_links':0,'connectors':0}
            for name in slides:
                tree=ET.fromstring(z.read(name));counts['text_shapes']+=len(tree.findall('.//p:sp[p:txBody]',ns));counts['tables']+=len(tree.findall('.//a:tbl',ns));counts['chart_links']+=len(tree.findall('.//c:chart',ns));counts['connectors']+=len(tree.findall('.//p:cxnSp',ns))
            require(counts['text_shapes']>=100,f'{variant} missing native text')
            for key in ['tables','chart_links','connectors']:require(counts[key]>0,f'{variant} missing native {key}')
            require(any(n.startswith('ppt/slideMasters/') and n.endswith('.xml') for n in z.namelist()),f'{variant} missing master')
            require(any(n.startswith('ppt/slideLayouts/') and n.endswith('.xml') for n in z.namelist()),f'{variant} missing layout')
            require(any(n.startswith('ppt/embeddings/') for n in z.namelist()),f'{variant} missing embedded chart data')
            counts['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();results[variant]=counts
        inp=read_json(root/f'assets/native/inputs/{variant}.sample.json');require(inp['register']==variant and len(inp['slides'])==12,f'{variant} content contract')
    lock=read_json(root/'scripts/native/brand-lock.json');brand=root/'assets/source/assets/asf-brand-v1.2.2';entries=lock.get('files',{});require(len(entries)>=10,'Brand lock must retain all ten critical dependencies')
    for name,digest in entries.items():require((brand/name).is_file() and hashlib.sha256((brand/name).read_bytes()).hexdigest()==digest,f'Brand hash mismatch: {name}')
    for file in root.rglob('*'):
        if not file.is_file() or file.suffix not in {'.md','.json','.js','.mjs','.cjs','.py','.yaml','.css','.html'}:continue
        text=file.read_text(encoding='utf-8')
        require(not re.search(r'/(?:Users|home)/[A-Za-z0-9_.-]+/',text),f'Host path in {file.relative_to(root)}')
except (OSError,KeyError,ValueError,ET.ParseError,zipfile.BadZipFile) as e:errors.append(str(e))
print(json.dumps({'ok':not errors,'native':results,'errors':errors},indent=2));sys.exit(bool(errors))
