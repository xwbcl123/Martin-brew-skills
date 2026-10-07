"""Bounded OOXML styling unavailable in the facade: font scheme and character tracking."""
import json,sys,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
A='http://schemas.openxmlformats.org/drawingml/2006/main';P='http://schemas.openxmlformats.org/presentationml/2006/main'
ET.register_namespace('a',A);ET.register_namespace('p',P)
source,layout,target,palette_file=sys.argv[1:]
palette=json.loads(Path(palette_file).read_text(encoding='utf8'))
STYLE_ID='{18554961-3B54-4E7B-A050-ASF000000001}'.replace('ASF','A5F')
data=json.loads(Path(layout).read_text(encoding='utf8'))
with zipfile.ZipFile(source) as z,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
 for info in z.infolist():
  content=z.read(info.filename)
  if info.filename=='ppt/tableStyles.xml':
   root=ET.Element(f'{{{A}}}tblStyleLst',{'def':STYLE_ID});style=ET.SubElement(root,f'{{{A}}}tblStyle',{'styleId':STYLE_ID,'styleName':'ASF Explicit Native Rules'})
   whole=ET.SubElement(style,f'{{{A}}}wholeTbl');tcstyle=ET.SubElement(whole,f'{{{A}}}tcStyle');bdr=ET.SubElement(tcstyle,f'{{{A}}}tcBdr')
   for side in ['left','right','top','bottom','insideH','insideV']:
    node=ET.SubElement(bdr,f'{{{A}}}{side}');ln=ET.SubElement(node,f'{{{A}}}ln',{'w':'0'});ET.SubElement(ln,f'{{{A}}}noFill')
   content=ET.tostring(root,encoding='utf-8',xml_declaration=True)
  if info.filename.startswith('ppt/theme/') and info.filename.endswith('.xml'):
   root=ET.fromstring(content);font=root.find(f'.//{{{A}}}fontScheme')
   if font is not None:
    font.set('name','ASF Georgia Arial');font.find(f'{{{A}}}majorFont/{{{A}}}latin').set('typeface','Georgia');font.find(f'{{{A}}}minorFont/{{{A}}}latin').set('typeface','Arial')
   content=ET.tostring(root,encoding='utf-8',xml_declaration=True)
  if info.filename.startswith('ppt/slides/slide') and info.filename.endswith('.xml'):
   num=int(Path(info.filename).stem[5:]);root=ET.fromstring(content);slots={f'slide-{num}-{t["id"]}':t for t in data['slides'][num-1]['texts']}
   for sh in root.findall(f'.//{{{P}}}sp'):
    nv=sh.find(f'{{{P}}}nvSpPr/{{{P}}}cNvPr');t=slots.get(nv.get('name')) if nv is not None else None
    if t:
     for r in sh.findall(f'.//{{{A}}}rPr')+sh.findall(f'.//{{{A}}}defRPr'):r.set('spc',str(round(t.get('letterSpacing',0)*50)))
   for tblpr in root.findall(f'.//{{{A}}}tblPr'):
    for old in list(tblpr):
     if old.tag in [f'{{{A}}}tableStyleId',f'{{{A}}}tableStyle']:tblpr.remove(old)
    ET.SubElement(tblpr,f'{{{A}}}tableStyleId').text=STYLE_ID
   for tc in root.findall(f'.//{{{A}}}tcPr'):
    for child in list(tc):
     if child.tag.rsplit('}',1)[-1].startswith('ln'):tc.remove(child)
    for side in ['L','R','T','B']:
     ln=ET.Element(f'{{{A}}}ln{side}',{'w':'6350' if side in ['T','B'] else '0'});tc.insert(['L','R','T','B'].index(side),ln)
     if side in ['T','B']:
      fill=ET.SubElement(ln,f'{{{A}}}solidFill');ET.SubElement(fill,f'{{{A}}}srgbClr',{'val':palette['border'].lstrip('#')})
     else:ET.SubElement(ln,f'{{{A}}}noFill')
   content=ET.tostring(root,encoding='utf-8',xml_declaration=True)
  out.writestr(info,content)
