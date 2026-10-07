#!/usr/bin/env python3
"""Check source truth, package text, layers, geometry and hashes; never infer visual QA."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import posixpath
from PIL import Image

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(manifest_path,pptx,require_visual=False):
    m=json.loads(manifest_path.read_text(encoding='utf-8'));base=manifest_path.parent;errors=[]
    if m.get('schema_version') != 2: errors.append('schema_version must be 2')
    if m.get('route') not in ('image-deck','text-editable'): errors.append('unsupported route')
    with zipfile.ZipFile(pptx) as z:
        size=ET.fromstring(z.read('ppt/presentation.xml')).find('p:sldSz',NS)
        expected_size=(round(m['slide_size']['width']*9525),round(m['slide_size']['height']*9525))
        if size is None or (int(size.get('cx')),int(size.get('cy'))) != expected_size: errors.append('PPTX page size mismatch')
        pages=sorted((n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')),key=lambda n:int(n.rsplit('slide',1)[1].split('.')[0]))
        if len(pages)!=len(m['slides']): errors.append('slide count mismatch')
        for s,n in zip(m['slides'],pages):
            prefix=s['id'];x=ET.fromstring(z.read(n));src=base/s['source']
            if digest(src)!=s['source_sha256']: errors.append(prefix+': source hash mismatch')
            with Image.open(src) as im:
                if im.size != (s['source_size']['width'],s['source_size']['height']): errors.append(prefix+': source dimensions mismatch')
            if m['route']=='text-editable':
                if digest(base/s['background'])!=s['background_sha256']: errors.append(prefix+': background hash mismatch')
                with Image.open(base/s['background']) as im:
                    if abs(im.width/im.height/(m['slide_size']['width']/m['slide_size']['height'])-1)>0.005: errors.append(prefix+': background aspect distortion')
                if s.get('qa',{}).get('background_review')!='pass': errors.append(prefix+': background review missing')
            pics=x.findall('.//p:pic',NS);shapes=x.findall('.//p:sp',NS)
            actual=[]
            for shape in shapes:
                paragraphs=[]
                for p in shape.findall('./p:txBody/a:p',NS): paragraphs.append(''.join(t.text or '' for t in p.findall('.//a:t',NS)))
                value='\n'.join(paragraphs)
                if value: actual.append(value)
            expected=[t['text'] for t in s['texts']]
            if actual!=expected: errors.append(prefix+': ordered native text mismatch '+repr({'expected':expected,'actual':actual}))
            if len(pics)!=1: errors.append(prefix+': expected one background image')
            if len(pics)==1:
                blip=pics[0].find('.//a:blip',NS)
                rid=blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed') if blip is not None else None
                relpath=posixpath.join(posixpath.dirname(n),'_rels',posixpath.basename(n)+'.rels')
                rels=ET.fromstring(z.read(relpath))
                match=next((r for r in rels if r.get('Id')==rid),None)
                if match is None or match.get('TargetMode')=='External': errors.append(prefix+': embedded background relationship missing')
                else:
                    media=posixpath.normpath(posixpath.join(posixpath.dirname(n),match.get('Target',''))).lstrip('/')
                    expected_hash=s['source_sha256'] if m['route']=='image-deck' else s['background_sha256']
                    if hashlib.sha256(z.read(media)).hexdigest()!=expected_hash: errors.append(prefix+': embedded background bytes mismatch')
                transform=pics[0].find('./p:spPr/a:xfrm',NS)
                if transform is None: errors.append(prefix+': background transform missing')
                else:
                    off=transform.find('a:off',NS);ext=transform.find('a:ext',NS)
                    image_path=src if m['route']=='image-deck' else base/s['background']
                    with Image.open(image_path) as im:
                        scale=min(expected_size[0]/im.width,expected_size[1]/im.height)
                        iw,ih=im.width*scale,im.height*scale
                    expected_frame=((expected_size[0]-iw)/2,(expected_size[1]-ih)/2,iw,ih)
                    if off is None or ext is None or any(abs(a-b)>2 for a,b in zip((int(off.get('x')),int(off.get('y')),int(ext.get('cx')),int(ext.get('cy'))),expected_frame)): errors.append(prefix+': background differs from full-page contain geometry')
            for shape,t in zip(shapes,s['texts']):
                transform=shape.find('./p:spPr/a:xfrm',NS)
                if transform is None: errors.append(prefix+': text transform missing');continue
                off=transform.find('a:off',NS);ext=transform.find('a:ext',NS)
                got=(int(off.get('x')),int(off.get('y')),int(ext.get('cx')),int(ext.get('cy')))
                sx=m['slide_size']['width']/s['source_size']['width']*9525;sy=m['slide_size']['height']/s['source_size']['height']*9525
                expected_box=[round(v*scale) for v,scale in zip(t['bbox'],[sx,sy,sx,sy])]
                if any(abs(a-b)>2 for a,b in zip(got,expected_box)):errors.append(prefix+': text bbox differs from source mapping')
            if len(shapes)!=len(expected): errors.append(prefix+': unexpected non-text shapes')
            if require_visual and (s.get('qa',{}).get('visual_review')!='pass' or not s.get('qa',{}).get('visual_review_note','').strip()): errors.append(prefix+': visual review missing')
    return {'status':'fail' if errors else 'pass','checks':['source and background hashes','slide count','embedded image byte hashes via slide relationships','page and layer geometry','one image plus native text layers','ordered text fidelity']+(['recorded visual acceptance'] if require_visual else []),'visual_semantics_automated':False,'errors':errors,'output_sha256':digest(pptx)}

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('pptx',type=Path);p.add_argument('--require-visual-review',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
    try: result=validate(a.manifest,a.pptx,a.require_visual_review)
    except Exception as e: result={'status':'fail','errors':[str(e)]}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n';print(text)
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text,encoding='utf-8')
    return 1 if result['status']=='fail' else 0
if __name__=='__main__':raise SystemExit(main())
