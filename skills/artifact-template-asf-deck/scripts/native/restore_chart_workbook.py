"""Retain the generator's literal workbook after Artifact Tool drops it on re-export.
Only snapshots authored by this generator are supported; no formulas are invented.
"""
import sys,zipfile,io,re,posixpath,xml.etree.ElementTree as E
C='http://schemas.openxmlformats.org/drawingml/2006/chart';R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';S='http://schemas.openxmlformats.org/spreadsheetml/2006/main';PKG='http://schemas.openxmlformats.org/package/2006/relationships';CT='http://schemas.openxmlformats.org/package/2006/content-types'
E.register_namespace('',CT)
source,candidate,target=sys.argv[1:]
with zipfile.ZipFile(source) as src,zipfile.ZipFile(candidate) as fresh:
 entries={n:fresh.read(n) for n in fresh.namelist()}
 for chartpath in [n for n in entries if '/charts/' in n and n.endswith('.xml') and '/_rels/' not in n]:
  oldchart=E.fromstring(src.read(chartpath));external=oldchart.find(f'{{{C}}}externalData');assert external is not None
  relpath=posixpath.join(posixpath.dirname(chartpath),'_rels',posixpath.basename(chartpath)+'.rels');rels=E.fromstring(src.read(relpath));rel=next(x for x in rels if x.get('Id')==external.get(f'{{{R}}}id'))
  wbpath=posixpath.normpath(posixpath.join(posixpath.dirname(chartpath),rel.get('Target')));wbbytes=src.read(wbpath)
  with zipfile.ZipFile(io.BytesIO(wbbytes)) as wb:
   parts={n:wb.read(n) for n in wb.namelist()};sheetpaths=[n for n in parts if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n)];assert len(sheetpaths)==1,'Only the generator single-sheet literal snapshot is supported'
   sheet=E.fromstring(parts[sheetpaths[0]]);cells={c.get('r'):c for c in sheet.findall(f'.//{{{S}}}c')};chart=E.fromstring(entries[chartpath])
   for kind,cache in [('strRef','strCache'),('numRef','numCache')]:
    for reference in chart.findall(f'.//{{{C}}}{kind}'):
     formula=reference.find(f'{{{C}}}f');data=reference.find(f'{{{C}}}{cache}')
     if formula is None or data is None:continue
     match=re.fullmatch(r"(?:'Chart Data'|Chart Data)!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)",formula.text or '')
     assert match and match[1]==match[3],f'Unsupported range {formula.text}'
     for pt in data.findall(f'{{{C}}}pt'):
      address=f'{match[1]}{int(match[2])+int(pt.get("idx"))}';cell=cells[address];assert cell.find(f'{{{S}}}f') is None,'Refuse to overwrite formulas'
      for child in list(cell):cell.remove(child)
      value=pt.find(f'{{{C}}}v').text
      if kind=='strRef':cell.set('t','inlineStr');inline=E.SubElement(cell,f'{{{S}}}is');E.SubElement(inline,f'{{{S}}}t').text=value
      else:cell.pop('t',None) if hasattr(cell,'pop') else cell.attrib.pop('t',None);E.SubElement(cell,f'{{{S}}}v').text=value
   parts[sheetpaths[0]]=E.tostring(sheet,encoding='utf-8',xml_declaration=True);buf=io.BytesIO()
   with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as out:
    for n,b in parts.items():out.writestr(n,b)
   entries[wbpath]=buf.getvalue()
  entries[relpath]=src.read(relpath);chart.append(external);entries[chartpath]=E.tostring(chart,encoding='utf-8',xml_declaration=True)
  ct=E.fromstring(entries['[Content_Types].xml']);
  if not any(x.get('Extension')=='xlsx' for x in ct):E.SubElement(ct,f'{{{CT}}}Default',{'Extension':'xlsx','ContentType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
  entries['[Content_Types].xml']=E.tostring(ct,encoding='utf-8',xml_declaration=True)
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
  for n,b in entries.items():out.writestr(n,b)
