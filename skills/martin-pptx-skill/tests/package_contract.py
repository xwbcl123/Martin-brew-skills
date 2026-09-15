#!/usr/bin/env python3
"""Reject swapped embedded backgrounds and actual package text/page mutations."""
import sys,zipfile,tempfile,importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('validator',Path(__file__).parents[1]/'scripts/validate_layers.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
manifest,pptx=map(Path,sys.argv[1:3]);assert mod.validate(manifest,pptx)['status']=='pass'
with tempfile.TemporaryDirectory(prefix='pptx-contract-',dir=pptx.parent) as d:
 with zipfile.ZipFile(pptx) as z: data={n:z.read(n)for n in z.namelist()}
 cases=[('wrong embedded background','ppt/media/image.png',data['ppt/media/image2.png']),('wrong page size','ppt/presentation.xml',data['ppt/presentation.xml'].replace(b'12192000',b'13192000')),('wrong native text','ppt/slides/slide1.xml',data['ppt/slides/slide1.xml'].replace('知识管理与验证'.encode(),'文本发生变化'.encode()))]
 for i,(name,target,content)in enumerate(cases):
  out=Path(d)/f'bad-{i}.pptx'
  with zipfile.ZipFile(out,'w')as z:
   for n,body in data.items():z.writestr(n,content if n==target else body)
  result=mod.validate(manifest,out)
  assert result['status']=='fail',(name,result)
 print(json.dumps({'passed':len(cases)+1,'cases':['valid package']+[c[0]for c in cases]}))
