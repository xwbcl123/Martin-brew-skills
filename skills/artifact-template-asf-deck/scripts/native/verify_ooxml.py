"""Verify native output against its actual source layout and supplied content."""
import argparse,json,zipfile,re,hashlib,xml.etree.ElementTree as E
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--layout',required=True);p.add_argument('--content',required=True);p.add_argument('--report',required=True);a=p.parse_args()
A='http://schemas.openxmlformats.org/drawingml/2006/main';P='http://schemas.openxmlformats.org/presentationml/2006/main';C='http://schemas.openxmlformats.org/drawingml/2006/chart'
layout=json.loads(Path(a.layout).read_text(encoding='utf8'));content=json.loads(Path(a.content).read_text(encoding='utf8'));checks=[];counts=[]
def check(name,value):
 checks.append({'name':name,'pass':bool(value)})
 if not value:raise AssertionError(name)
with zipfile.ZipFile(a.input) as z:
 names=z.namelist();slides=sorted([n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)],key=lambda n:int(re.search(r'(\d+)\.xml',n)[1]));check('12 native slides',len(slides)==12)
 masters=[n for n in names if re.fullmatch(r'ppt/slideMasters/slideMaster\d+\.xml',n)];layouts=[n for n in names if re.fullmatch(r'ppt/slideLayouts/slideLayout\d+\.xml',n)];themes=[n for n in names if re.fullmatch(r'ppt/theme/theme\d+\.xml',n)]
 check('master/layout/theme parts present',masters and layouts and themes)
 for i,n in enumerate(slides):
  root=E.fromstring(z.read(n));native=root.findall(f'.//{{{P}}}sp');tables=root.findall(f'.//{{{A}}}tbl');connectors=root.findall(f'.//{{{P}}}cxnSp');images=root.findall(f'.//{{{P}}}pic')
  check(f'slide {i+1} native text exists',len(native)>=len(layout['slides'][i]['texts']))
  for t in layout['slides'][i]['texts']:
   expected=content['slides'][i]['texts'][t['id']].replace('Editable DOM / SVG shapes and connectors; selectable text.','Editable native shapes and connectors; selectable text.')
   sh=next(s for s in native if s.find(f'{{{P}}}nvSpPr/{{{P}}}cNvPr').get('name')==f'slide-{i+1}-{t["id"]}')
   actual=''.join(x.text or '' for x in sh.findall(f'.//{{{A}}}t'));check(f'slide {i+1} {t["id"]} exact text',actual==expected)
   for r in sh.findall(f'.//{{{A}}}rPr'):check(f'slide {i+1} {t["id"]} >=12pt',int(r.get('sz','0'))>=1200)
  check(f'slide {i+1} connector count',len(connectors)==len(layout['slides'][i]['connectors']))
  for j,c in enumerate(connectors):
   nv=c.find(f'{{{P}}}nvCxnSpPr/{{{P}}}cNvCxnSpPr');check(f'slide {i+1} connector {j} attached',nv is not None and nv.find(f'{{{A}}}stCxn') is not None and nv.find(f'{{{A}}}endCxn') is not None)
   ln=c.find(f'{{{P}}}spPr/{{{A}}}ln');head=ln.find(f'{{{A}}}headEnd');tail=ln.find(f'{{{A}}}tailEnd');check(f'slide {i+1} connector {j} no reversed arrow',head is None or head.get('type')=='none')
  if i==4:
   check('slide5 native table',len(tables)==1)
   cells=tables[0].findall(f'.//{{{A}}}tcPr');check('table ordered borders before fill',all([x.tag.rsplit('}',1)[-1] for x in c][:4]==['lnL','lnR','lnT','lnB'] for c in cells))
   check('table named no-grid style',tables[0].find(f'{{{A}}}tblPr/{{{A}}}tableStyleId') is not None)
   check('table vertical grid removed',all(c.find(f'{{{A}}}lnL/{{{A}}}noFill') is not None and c.find(f'{{{A}}}lnR/{{{A}}}noFill') is not None for c in cells))
  for pic in images:
   ext=pic.find(f'{{{P}}}spPr/{{{A}}}xfrm/{{{A}}}ext');check(f'slide {i+1} no full slide image',int(ext.get('cx','0'))<12192000 and int(ext.get('cy','0'))<6858000)
  counts.append({'slide':i+1,'nativeShapes':len(native),'nativeTables':len(tables),'nativeConnectors':len(connectors),'sourceImages':len(images)})
 charts=[n for n in names if n.endswith('.xml') and '/charts/' in n and '/_rels/' not in n];check('one native chart',len(charts)==1);chart=E.fromstring(z.read(charts[0]));axis=chart.find(f'.//{{{C}}}valAx');check('chart0/50/100',axis.find(f'{{{C}}}scaling/{{{C}}}min').get('val')=='0' and axis.find(f'{{{C}}}scaling/{{{C}}}max').get('val')=='100' and axis.find(f'{{{C}}}majorUnit').get('val')=='50')
 check('embedded chart workbook',bool([n for n in names if '/embeddings/' in n and n.endswith('.xlsx')]))
 for n in themes:
  root=E.fromstring(z.read(n));major=root.find(f'.//{{{A}}}majorFont/{{{A}}}latin');minor=root.find(f'.//{{{A}}}minorFont/{{{A}}}latin');check(n+' Georgia/Arial theme',major is not None and major.get('typeface')=='Georgia' and minor is not None and minor.get('typeface')=='Arial')
 report={'sha256':hashlib.sha256(Path(a.input).read_bytes()).hexdigest(),'checks':checks,'counts':counts,'masterParts':masters,'layoutParts':layouts,'themeParts':themes,'officeVerified':False}
Path(a.report).parent.mkdir(parents=True,exist_ok=True);Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf8');print(f'{len(checks)} OOXML checks passed')
