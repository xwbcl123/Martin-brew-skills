#!/usr/bin/env python3
"""Validate recorded design/asset/build evidence; never certify visual meaning.

Standard library only. Paths are relative to the contract directory and contained
there (including symlink resolution). Exit 0=pass, 1=invalid contract/evidence.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
FORMS = {'infographic', 'diagram', 'chart', 'illustration', 'photo', 'background', 'evidence', 'text'}
MODES = {'native', 'integrated_native', 'embedded_text', 'none'}
LIMIT = 'Checks files, hashes, declared geometry, package objects and recorded review/order only. It cannot prove review truth, image wording, chart geometry correctness or actual tool-call chronology.'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plan_hash(c):
    return digest(json.dumps({k: v for k, v in c.items() if k != 'evidence'}, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def unique(items, key='id'):
    require(isinstance(items, list), 'Expected a list')
    ids = [x.get(key) for x in items if isinstance(x, dict)]
    require(len(ids) == len(items) and all(nonempty(x) for x in ids) and len(set(ids)) == len(ids), f'Empty/duplicate {key}')
    return {x[key]: x for x in items}


def box(value, canvas):
    require(isinstance(value, list) and len(value) == 4 and all(number(x) for x in value), 'Invalid finite box [x,y,w,h]')
    x, y, w, h = value
    require(x >= 0 and y >= 0 and w > 0 and h > 0 and x+w <= canvas[0]+0.01 and y+h <= canvas[1]+0.01, 'Box outside canvas')
    return value


def inside(point, rect):
    return isinstance(point, list) and len(point) == 2 and all(number(x) for x in point) and rect[0] <= point[0] <= rect[0]+rect[2] and rect[1] <= point[1] <= rect[1]+rect[3]


def gap(a, b):
    return math.hypot(max(a[0]-b[0]-b[2], b[0]-a[0]-a[2], 0), max(a[1]-b[1]-b[3], b[1]-a[1]-a[3], 0))


def stamp(value):
    require(nonempty(value), 'Missing timestamp')
    t = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(t.tzinfo is not None and t <= dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=5), 'Timestamp requires timezone and must not be future')
    return t


class Verifier:
    def __init__(self, contract):
        self.path = Path(contract).resolve()
        self.root = self.path.parent
        self.c = json.loads(self.path.read_text(encoding='utf-8'))
        require(isinstance(self.c, dict), 'Contract must be an object')
        self.binding = plan_hash(self.c)

    def file(self, rel):
        require(nonempty(rel) and not Path(rel).is_absolute(), 'Paths must be relative to contract root')
        p = (self.root/rel).resolve()
        require(p.is_relative_to(self.root), 'Path/symlink escapes contract root')
        require(p.is_file() and p.stat().st_size > 0, f'Missing/empty evidence: {rel}')
        return p

    def ref(self, obj):
        require(isinstance(obj, dict), 'Expected {path,sha256} reference')
        p = self.file(obj.get('path'))
        require(isinstance(obj.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', obj['sha256']), 'Invalid SHA-256')
        require(digest(p.read_bytes()) == obj['sha256'], f'File changed: {obj["path"]}')
        return p

    def plan(self):
        c = self.c
        require(c.get('schema_version') == 1, 'Unsupported visual contract schema')
        self.canvas = c.get('canvas')
        require(isinstance(self.canvas, list) and len(self.canvas) == 2 and all(number(x) and x > 0 for x in self.canvas), 'Invalid canvas')
        self.ref(c.get('outline'))
        require(nonempty(c['outline'].get('approval_ref')), 'Bind existing outline approval/decision reference')
        style = c.get('style', {})
        self.ref(style.get('source'))
        require(isinstance(style.get('palette'), dict) and style['palette'] and all(re.fullmatch('#[0-9A-Fa-f]{6}', x) for x in style['palette'].values()), 'Invalid palette roles/HEX')
        self.assets = unique(c.get('assets', []))
        self.slides = unique(c.get('slides', []))
        require(bool(self.slides), 'No slides')
        used = set()
        for a in self.assets.values():
            require(nonempty(a.get('path')) and not Path(a['path']).is_absolute(), 'Asset path required')
            require((self.root/a['path']).resolve().is_relative_to(self.root), 'Planned asset escapes contract root')
            require(a.get('origin') in {'generated', 'source', 'reused'}, 'Asset origin required')
            if a['origin'] == 'generated':
                self.ref(a.get('prompt'))
                require(nonempty(a.get('tool')), 'Generated asset tool required')
        for s in self.slides.values():
            require(nonempty(s.get('message')) and nonempty(s.get('reading_order')), 'Message and reading order required')
            require(s.get('visual_form') in FORMS and s.get('text_mode') in MODES, 'Unknown visual form/text mode')
            placements = unique(s.get('placements', []), 'asset_id')
            for aid, p in placements.items():
                require(aid in self.assets, 'Placement references unknown asset')
                used.add(aid)
                box(p.get('box'), self.canvas)
                require(p.get('fit') in {'contain', 'cover'}, 'Declare image fit')
            labels = unique(s.get('labels', []))
            for label in labels.values():
                require(nonempty(label.get('text')), 'Empty native label')
                lb = box(label.get('box'), self.canvas)
                if s['text_mode'] == 'integrated_native':
                    require(label.get('asset_id') in placements and nonempty(label.get('component_id')), 'Native label lacks asset/component mapping')
                    cb = box(label.get('component_box'), self.canvas)
                    region = placements[label['asset_id']]['box']
                    require(inside(cb[:2], region) and inside([cb[0]+cb[2], cb[1]+cb[3]], region), 'Component outside placed image')
                    maximum = s.get('max_label_gap_px', 48)
                    require(number(maximum) and 0 <= maximum <= min(self.canvas)*0.1, 'Label gap must be <=10% of shorter canvas dimension')
                    if gap(lb, cb) > maximum or 'connector' in label:
                        connector = label.get('connector', [])
                        require(isinstance(connector, list) and len(connector) == 2 and inside(connector[0], cb) and inside(connector[1], lb), 'Detached label needs component-to-label connector')
            if s['text_mode'] == 'integrated_native':
                require(bool(labels) and bool(placements), 'Integrated mode needs image and native labels')
            if s['text_mode'] == 'embedded_text':
                require(bool(placements) and isinstance(s.get('embedded_text'), list) and s['embedded_text'] and all(nonempty(t) for t in s['embedded_text']), 'Embedded text truth required')
                require(s.get('editable_visual_text') is False, 'Embedded text must disclose noneditability')
            if s['text_mode'] == 'none' and s['visual_form'] in {'diagram', 'infographic'}:
                require(nonempty(s.get('unlabeled_reason')), 'Explain genuinely unlabeled explanatory visual')
            if s['visual_form'] == 'chart':
                self.ref(s.get('data_source'))
                require(s.get('chart_mode') in {'native', 'image'}, 'Declare chart mode')
                require(s['chart_mode'] == 'native' or s.get('editable_data') is False, 'Raster chart cannot promise editable data')
        require(used == set(self.assets), 'Unused assets in contract')

    def review(self, ref, subject_sha, checks):
        r = json.loads(self.ref(ref).read_text(encoding='utf-8'))
        require(r.get('plan_sha256') == self.binding and r.get('subject_sha256') == subject_sha, 'Review is stale or bound to another file/plan')
        require(nonempty(r.get('reviewer')) and nonempty(r.get('notes')), 'Review requires attribution and concrete observations')
        stamp(r.get('reviewed_at'))
        require(isinstance(r.get('checks'), dict) and all(r['checks'].get(k) == 'pass' for k in checks), 'Missing/pending/failed visual review checks')
        return r

    def assets_stage(self):
        self.asset_hashes = {aid: digest(self.ref(a).read_bytes()) for aid, a in self.assets.items()}
        evidence = self.c.get('evidence', {})
        reviews = evidence.get('asset_reviews', {})
        for aid, sha in self.asset_hashes.items():
            checks = {'subject', 'style', 'placement'}
            owners = [s for s in self.slides.values() if any(p['asset_id'] == aid for p in s.get('placements', []))]
            if any(s['text_mode'] == 'integrated_native' for s in owners): checks |= {'textless', 'mapping'}
            if any(s['text_mode'] == 'embedded_text' for s in owners): checks |= {'text_accuracy', 'mapping'}
            if any(s['visual_form'] == 'chart' for s in owners): checks |= {'data_geometry'}
            self.review(reviews.get(aid), sha, checks)

    def final(self):
        e = self.c['evidence']
        gate_file = self.ref(e.get('assembly_gate'))
        gate = json.loads(gate_file.read_text(encoding='utf-8'))
        require(gate.get('ok') is True and gate.get('stage') == 'assets' and gate.get('plan_sha256') == self.binding and gate.get('asset_hashes') == self.asset_hashes, 'Missing/stale assembly gate')
        require(stamp(e.get('build_started_at')) >= stamp(gate.get('checked_at')), 'Recorded build started before asset gate')
        final = e.get('final', {})
        pptx = self.ref(final.get('pptx'))
        renders = unique(final.get('renders', []), 'slide_id')
        require(set(renders) == set(self.slides), 'Render set differs from slide set')
        with zipfile.ZipFile(pptx) as z:
            require(z.testzip() is None, 'Broken ZIP')
            prs = ET.fromstring(z.read('ppt/presentation.xml'))
            dims = prs.find('p:sldSz', NS)
            require(dims is not None and all(abs(float(dims.attrib[k])/9525-v) <= 1 for k,v in zip(('cx','cy'),self.canvas)), 'PPTX canvas mismatch')
            rels = self.rels(z, 'ppt/presentation.xml')
            ids = prs.findall('p:sldIdLst/p:sldId', NS)
            require(len(ids) == len(self.slides), 'PPTX slide count mismatch')
            for declared, sid in zip(self.slides.values(), ids):
                part = rels[sid.attrib['{'+NS['r']+'}id']]
                slide = ET.fromstring(z.read(part)); sr = self.rels(z, part)
                texts = []
                for sp in slide.findall('.//p:sp', NS):
                    text = '\n'.join(''.join(t.text or '' for t in p.findall('.//a:t', NS)) for p in sp.findall('p:txBody/a:p', NS))
                    texts.append((text, sp))
                norm = lambda t: ' '.join(t.split())
                for label in declared.get('labels', []):
                    matches = [sp for t,sp in texts if norm(t) == norm(label['text'])]
                    require(len(matches) == 1, f'Native label missing/duplicated: {label["id"]}')
                    require(not any(matches[0] is child for group in slide.findall('.//p:grpSp', NS) for child in group.iter()), 'Grouped label geometry requires an explicit adapter')
                    xf = matches[0].find('p:spPr/a:xfrm', NS)
                    require(xf is not None, 'Label needs explicit ungrouped slide geometry')
                    off, ext = xf.find('a:off', NS), xf.find('a:ext', NS)
                    got = [float(off.attrib['x'])/9525,float(off.attrib['y'])/9525,float(ext.attrib['cx'])/9525,float(ext.attrib['cy'])/9525]
                    require(all(abs(a-b) <= 2 for a,b in zip(got,label['box'])), 'Native label geometry drifted from contract')
                for label in declared.get('labels', []):
                    if 'connector' not in label: continue
                    p1, p2 = label['connector']
                    expected = [min(p1[0],p2[0]), min(p1[1],p2[1]), abs(p2[0]-p1[0]), abs(p2[1]-p1[1])]
                    found = False
                    for connector in slide.findall('.//p:cxnSp', NS):
                        xf = connector.find('p:spPr/a:xfrm', NS)
                        if xf is None: continue
                        off, ext = xf.find('a:off', NS), xf.find('a:ext', NS)
                        actual = [float(off.attrib['x'])/9525,float(off.attrib['y'])/9525,float(ext.attrib['cx'])/9525,float(ext.attrib['cy'])/9525]
                        if all(abs(a-b)<=2 for a,b in zip(actual,expected)): found=True
                    require(found, 'Declared label connector absent or moved in PPTX')
                media = {digest(z.read(sr[b.attrib['{'+NS['r']+'}embed']])) for b in slide.findall('.//a:blip', NS) if '{'+NS['r']+'}embed' in b.attrib}
                require(all(self.asset_hashes[p['asset_id']] in media for p in declared.get('placements', [])), 'Slide image bytes differ from accepted assets')
                for placement in declared.get('placements', []):
                    matched = False
                    for pic in slide.findall('.//p:pic', NS):
                        blip = pic.find('.//a:blip', NS)
                        if blip is None: continue
                        rid = blip.attrib.get('{'+NS['r']+'}embed')
                        if not rid or digest(z.read(sr[rid])) != self.asset_hashes[placement['asset_id']]: continue
                        require(not any(pic is child for group in slide.findall('.//p:grpSp', NS) for child in group.iter()), 'Grouped image geometry requires an explicit adapter')
                        xf = pic.find('p:spPr/a:xfrm', NS)
                        if xf is None: continue
                        off, ext = xf.find('a:off', NS), xf.find('a:ext', NS)
                        got = [float(off.attrib['x'])/9525,float(off.attrib['y'])/9525,float(ext.attrib['cx'])/9525,float(ext.attrib['cy'])/9525]
                        if all(abs(a-b) <= 2 for a,b in zip(got,placement['box'])): matched = True
                    require(matched, 'Accepted image placement drifted from contract')
                if declared.get('chart_mode') == 'native':
                    require(any(el.tag.endswith('}chart') for el in slide.iter()), 'Declared native chart missing')
                render = renders[declared['id']]
                self.ref(render)
                require(render.get('pptx_sha256') == final['pptx']['sha256'], 'Render not bound to current PPTX')
                checks = {'content', 'style', 'legibility', 'mapping'}
                if declared['text_mode'] == 'embedded_text': checks.add('text_accuracy')
                if declared['visual_form'] == 'chart': checks.add('data_geometry')
                self.review(render.get('review'), render['sha256'], checks)
        return final['pptx']['sha256']

    @staticmethod
    def rels(z, part):
        directory, filename = posixpath.split(part)
        root = ET.fromstring(z.read(posixpath.join(directory, '_rels', filename+'.rels')))
        return {el.attrib['Id']: posixpath.normpath(posixpath.join(directory, el.attrib['Target'])) if not el.attrib['Target'].startswith('/') else el.attrib['Target'].lstrip('/') for el in root if el.attrib.get('TargetMode') != 'External'}


def verify(path, stage):
    result = {'validator': 'visual-contract-v1', 'stage': stage, 'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'ok': False, 'limitations': LIMIT}
    try:
        v = Verifier(path); v.plan(); result['plan_sha256'] = v.binding
        if stage in {'assets', 'final'}:
            v.assets_stage(); result['asset_hashes'] = v.asset_hashes
        if stage == 'final': result['pptx_sha256'] = v.final()
        result['ok'] = True; result['errors'] = []
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError, ET.ParseError, zipfile.BadZipFile) as exc:
        result['errors'] = [str(exc)]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    parser.add_argument('--stage', required=True, choices=['plan', 'assets', 'final'])
    parser.add_argument('--out', type=Path, help='Write a NEW receipt (never overwrites)')
    args = parser.parse_args()
    result = verify(args.contract, args.stage)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        try:
            with args.out.open('x', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')
        except OSError as exc:
            print(json.dumps({'ok': False, 'errors': [f'Receipt not written: {exc}']})); return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
