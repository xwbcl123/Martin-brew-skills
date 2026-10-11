#!/usr/bin/env python3
"""Validate grounded episode copy and render a local, complete listening/reading edition."""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlsplit


def fail(message):
    raise ValueError(message)


def string(value, label, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        fail(f'{label}: expected non-empty text')
    return value


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        fail(f'{label}: expected finite nonnegative seconds')
    return value


def inside(root, value, existing=True):
    """Reject lexical traversal and all symlinks, including links to inside root."""
    string(value, 'package path')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or '\\' in value:
        fail(f'unsafe package path: {value}')
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            fail(f'symlink forbidden: {value}')
    resolved = current.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        fail(f'path outside package: {value}')
    if existing and (not resolved.is_file() or resolved.stat().st_size == 0):
        fail(f'missing or empty artifact: {value}')
    return resolved


def url(value):
    string(value, 'URL')
    parsed = urlsplit(value)
    if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.username or parsed.password or any(ord(c) < 32 for c in value):
        fail('resource/publication URL must be http(s), without credentials')
    return value


def exact_keys(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or not set(required) <= set(value):
        fail('unknown or missing content fields')


def public_parts(data):
    """Render authoring-only v1 nodes; never accept arbitrary HTML."""
    source = data.get('public_content')
    exact_keys(source, ('version', 'nodes'))
    if type(source['version']) is not int or source['version'] != 1: fail('unknown public_content version')
    if not isinstance(source['nodes'], list) or not source['nodes']: fail('public nodes required')
    def inline(nodes, depth=0):
        if depth > 8 or not isinstance(nodes, list) or not nodes: fail('invalid inline content')
        result, plain = [], []
        for node in nodes:
            if not isinstance(node, dict): fail('inline node required')
            kind = node.get('type')
            if kind == 'text':
                exact_keys(node, ('type','text')); text = string(node['text'], 'inline text')
                result.append(esc(text)); plain.append(text)
            elif kind in ('strong','em','link'):
                exact_keys(node, ('type','children','url') if kind == 'link' else ('type','children'))
                h, t = inline(node['children'], depth+1)
                result.append(f'<a href="{esc(url(node["url"]))}">{h}</a>' if kind == 'link' else f'<{kind}>{h}</{kind}>')
                plain.append(t + (' ('+node['url']+')' if kind == 'link' else ''))
            else: fail('unknown inline node')
        return ''.join(result), ''.join(plain)
    parts, seen = [], set()
    for node in source['nodes']:
        if not isinstance(node, dict): fail('public node required')
        kind = node.get('type')
        if kind in ('paragraph','heading','erratum'):
            exact_keys(node, ('type','children','level') if kind == 'heading' else ('type','children'))
            h, t = inline(node['children'])
            if kind == 'heading':
                if type(node['level']) is not int or node['level'] not in (2,3): fail('heading level must be 2 or 3')
                tag = 'h'+str(node['level'])
            else: tag = 'p'
            parts.append((kind, f'<{tag}>{h}</{tag}>', t))
        elif kind == 'list':
            exact_keys(node, ('type','ordered','items'))
            if type(node['ordered']) is not bool or not isinstance(node['items'], list) or not node['items']: fail('invalid list')
            items = [inline(item) for item in node['items']]; tag = 'ol' if node['ordered'] else 'ul'
            parts.append((kind, '<'+tag+'>'+''.join('<li>'+h+'</li>' for h,t in items)+'</'+tag+'>', '\n'.join((str(i+1)+'. ' if node['ordered'] else '• ')+t for i,(h,t) in enumerate(items))))
        elif kind in ('chapters','resources','transcript'):
            if kind in seen: fail('duplicate public reference node')
            seen.add(kind)
            exact_keys(node, ('type','url','label') if kind == 'transcript' else ('type',))
            if kind == 'chapters':
                rows = [(timestamp(number(c['start'],'chapter start'))+' '+string(c['title'],'chapter title')) for c in data['chapters']]
                parts.append((kind, '<h2>本集章节</h2><ul>'+''.join('<li>'+esc(t)+'</li>' for t in rows)+'</ul>', '本集章节\n'+'\n'.join(rows)))
            elif kind == 'resources':
                rows = [(string(r['title'],'resource title'),url(r['url'])) for r in data['resources']]
                parts.append((kind, '<h2>延伸阅读</h2><ul>'+''.join('<li><a href="'+esc(u)+'">'+esc(t)+'</a></li>' for t,u in rows)+'</ul>', '延伸阅读\n'+'\n'.join(t+' ('+u+')' for t,u in rows)))
            else:
                u, t = url(node['url']), string(node['label'],'transcript label')
                parts.append((kind, '<p><a href="'+esc(u)+'">'+esc(t)+'</a></p>', t+' ('+u+')'))
        else: fail('unknown public node')
    if not any(k == 'paragraph' for k,h,t in parts): fail('public content requires a paragraph')
    return parts


def public_html(data): return ''.join(h for k,h,t in public_parts(data))
def public_text(data): return '\n\n'.join(t for k,h,t in public_parts(data))
def public_summary(data): return next(t for k,h,t in public_parts(data) if k == 'paragraph')[:240]


def terminology_content_hash(data):
    return hashlib.sha256(json.dumps({k:v for k,v in data.items() if k != 'terminology_review'}, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()).hexdigest()


def validate_terminology(data):
    review = data.get('terminology_review')
    if review is None: return None
    exact_keys(review, ('bindings','terms'))
    bindings = review['bindings']
    exact_keys(bindings, ('episode_key','audio_sha256','timeline_sha256','content_sha256','glossary_sha256'))
    string(bindings['episode_key'], 'episode key')
    for key,value in bindings.items():
        if key != 'episode_key' and (not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value)): fail('invalid terminology hash')
    if bindings['content_sha256'] != terminology_content_hash(data): fail('stale terminology content binding')
    if not isinstance(review['terms'],list): fail('terminology terms must be a list')
    ids=set()
    for term in review['terms']:
        exact_keys(term, ('id','current','alternatives','start','end','reason'))
        for key in ('id','current','reason'): string(term[key], 'term '+key)
        if term['id'] in ids: fail('duplicate term id')
        ids.add(term['id'])
        if not isinstance(term['alternatives'], list): fail('invalid term alternatives')
        for value in term['alternatives']: string(value,'term alternative')
        if number(term['end'],'term end') <= number(term['start'],'term start') or term['end'] > data['duration']: fail('term outside timeline')
    return review


def import_terminology_decisions(data, exported):
    review = validate_terminology(data)
    if review is None: fail('no terminology review context')
    exact_keys(exported, ('version','origin','attestation','bindings','decisions'))
    if type(exported['version']) is not int or exported['version'] != 1 or exported['origin'] != 'user_preview' or exported['attestation'] != 'I reviewed these term decisions': fail('explicit user preview attestation required')
    if exported['bindings'] != review['bindings']: fail('stale terminology decision bindings')
    if not isinstance(exported['decisions'],list) or not exported['decisions']: fail('term decisions required')
    terms={t['id']:t for t in review['terms']}; seen=set()
    for decision in exported['decisions']:
        exact_keys(decision, ('term_id','decision','text'))
        tid=decision['term_id']
        if not isinstance(tid,str) or tid not in terms or tid in seen: fail('unknown or duplicate decision term')
        seen.add(tid)
        if decision['decision'] not in ('confirm','edit'): fail('invalid term decision')
        string(decision['text'],'decision text')
        if decision['decision'] == 'confirm' and decision['text'] != terms[tid]['current']: fail('confirmation text changed')
    return {'version':1,'provenance':'user_preview_attestation','bindings':dict(review['bindings']), 'decisions':exported['decisions']}


def terminology_html(data):
    review=validate_terminology(data)
    if not review or not review['terms']: return ''
    rows=''
    for term in review['terms']:
        rows += f'<article class="term-card" data-term-id="{esc(term["id"])}" data-current="{esc(term["current"])}"><button class="copy" data-seek="{term["start"]}">{timestamp(term["start"])}–{timestamp(term["end"])}</button><h3>{esc(term["current"])}</h3><p>其他听法：{esc(" / ".join(term["alternatives"]) or "暂无")}</p><p>{esc(term["reason"])}</p><label>我的选择 <select class="term-action"><option value="skip">稍后再看</option><option value="confirm">确认当前用词</option><option value="edit">改为下方用词</option></select></label><label>用词 <input class="term-text" value="{esc(term["current"])}" maxlength="200"></label></article>'
    bindings=esc(json.dumps(review['bindings'],ensure_ascii=False,sort_keys=True))
    return f'<details class="editor terminology" id="terminology-review" data-bindings="{bindings}"><summary>一起核对几个词 · {len(review["terms"])} 处</summary><p>听一小段，再留下你的选择。导出的文件交回后会用于下一版；页面操作不会直接更新节目。</p><div class="term-grid">{rows}</div><label class="term-attestation"><input type="checkbox" id="term-attestation"> 这些选择是我听过、核对后填写的</label><button class="copy" id="export-terms">导出我的确认</button></details>'


def validate(data, root):
    if not isinstance(data, dict): fail('content must be an object')
    modern = 'public_content' in data
    for key in ('title', 'show_title', 'launch_copy', 'language') + (() if modern else ('summary','description','show_notes','ai_disclosure')):
        string(data.get(key), key)
    if modern: public_parts(data)
    validate_terminology(data)
    segments = data.get('segments')
    if not isinstance(segments, list) or not segments: fail('segments must be a non-empty list')
    ids = set()
    last = -1
    for segment in segments:
        sid = segment.get('id')
        if isinstance(sid, bool) or not ((isinstance(sid, int) and sid >= 0) or (isinstance(sid, str) and sid.strip())): fail('segment id must be nonnegative integer or non-empty string')
        sid = str(sid)
        if sid in ids: fail('duplicate segment id')
        ids.add(sid)
        start, end = number(segment.get('start'), 'segment start'), number(segment.get('end'), 'segment end')
        if start < last or end <= start: fail('segments must have ordered starts and positive duration')
        last = start
        string(segment.get('text'), 'segment text')
        if 'speaker' in segment: string(segment['speaker'], 'speaker', empty=True)
    duration = number(data.get('duration', max(s['end'] for s in segments)), 'duration')
    if any(s['end'] > duration + .1 for s in segments): fail('segment exceeds delivery duration')
    def refs(item):
        result = item.get('source_segment_ids')
        if not isinstance(result, list) or not result or any(isinstance(i, bool) or not isinstance(i, (str, int)) or str(i) not in ids for i in result):
            fail('source_segment_ids must reference existing segments')
        return {str(i) for i in result}
    chapters = data.get('chapters')
    if not isinstance(chapters, list) or not chapters: fail('chapters required')
    last = -1
    for chapter in chapters:
        start = number(chapter.get('start'), 'chapter start')
        if start <= last or start >= duration: fail('chapter starts must increase within audio')
        last = start
        string(chapter.get('title'), 'chapter title'); string(chapter.get('summary'), 'chapter summary')
        refs(chapter)
    reading = data.get('reading_transcript')
    if not isinstance(reading, list) or not reading: fail('reading_transcript must be paragraph objects')
    covered = set()
    for paragraph in reading:
        string(paragraph.get('text'), 'reading text'); covered.update(refs(paragraph))
    if covered != ids: fail('reading transcript does not cover every source segment')
    metadata = data.get('metadata')
    if not isinstance(metadata, dict): fail('metadata required')
    string(metadata.get('reading_language'), 'reading_language')
    if metadata.get('reading_mode') not in ('edited', 'translation'): fail('reading_mode must be edited or translation')
    if metadata['reading_language'] != data['language'] and metadata['reading_mode'] != 'translation': fail('different reading language requires translation label')
    if not isinstance(metadata.get('corrections'), list): fail('corrections must be a list (empty if none)')
    for correction in metadata['corrections']:
        if str(correction.get('source_segment_id')) not in ids: fail('correction source missing')
        for key in ('original', 'corrected', 'reason'): string(correction.get(key), 'correction '+key)
    for key in ('cover_path', 'audio_path'):
        inside(root, data.get(key))
    if Path(data['cover_path']).suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'): fail('cover must be a raster image')
    if Path(data['audio_path']).suffix.lower() not in ('.mp3', '.m4a', '.wav', '.ogg', '.opus', '.aac'): fail('unsupported audio extension')
    if not isinstance(data.get('resources'), list): fail('resources must be a list')
    for resource in data['resources']:
        string(resource.get('title'), 'resource title'); url(resource.get('url'))
    status = data.get('status', {})
    if not isinstance(status, dict): fail('status must be an object')
    if 'label' in status: string(status['label'], 'status label')
    if 'publication_url' in status: url(status['publication_url'])
    for key in ('audit_links', 'assets'):
        if not isinstance(data.get(key, []), list): fail(f'{key} must be a list')
        for asset in data.get(key, []):
            string(asset.get('title'), 'asset title'); inside(root, asset.get('path'))
            if key == 'assets':
                if asset.get('kind') not in ('image', 'audio', 'text', 'download'): fail('asset kind invalid')
                if asset['kind'] == 'image' and Path(asset['path']).suffix.lower() not in ('.png','.jpg','.jpeg','.webp'): fail('asset image must be raster')
    if data.get('terminology_review') and data['terminology_review']['bindings']['audio_sha256'] != digest(inside(root,data['audio_path'])): fail('stale terminology audio binding')
    return {'segment_count': len(segments), 'reading_paragraph_count': len(reading), 'covered_source_segments': len(covered), 'duration': duration, 'semantic_grounding': 'requires_content_review', 'experience_ready': False}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def esc(value): return html.escape(str(value), quote=True)
def timestamp(seconds):
    value = int(seconds)
    return f'{value//3600:02d}:{value%3600//60:02d}:{value%60:02d}' if value >= 3600 else f'{value//60:02d}:{value%60:02d}'


def prose(text):
    # Plain text is the public content contract: never evaluate Markdown HTML.
    return ''.join(f'<p>{esc(p).replace(chr(10), "<br>")}</p>' for p in re.split(r'\n\s*\n', text.strip()))


def render(data, root, output, report):
    def link(path): return esc(quote(os.path.relpath(inside(root, path), output.parent), safe='/'))
    cover, audio = link(data['cover_path']), link(data['audio_path'])
    chapters = ''.join(f'<button class="chapter" data-seek="{c["start"]}"><span class="chapter-time">{timestamp(c["start"])}</span><span><strong>{esc(c["title"])}</strong><span class="chapter-summary">{esc(c["summary"])}</span></span><span aria-hidden="true">↗</span></button>' for c in data['chapters'])
    segments = ''.join(f'<article class="segment searchable" data-start="{s["start"]}" data-end="{s["end"]}" data-source-id="{esc(s["id"])}"><button data-seek="{s["start"]}" aria-label="跳转到 {timestamp(s["start"])}">{timestamp(s["start"])}</button><div>{"<strong class=speaker>"+esc(s["speaker"])+"</strong>" if s.get("speaker") not in (None, "", "unknown") else ""}<p>{esc(s["text"])}</p></div></article>' for s in data['segments'])
    reading = ''.join(f'<p class="searchable" data-source-ids="{esc(json.dumps(p["source_segment_ids"], ensure_ascii=False))}">{esc(p["text"]).replace(chr(10), "<br>")}</p>' for p in data['reading_transcript'])
    resources = ''.join(f'<li><a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">{esc(r["title"])} <span aria-hidden="true">↗</span></a></li>' for r in data['resources']) or '<li>本集未附外部链接。</li>'
    audit = ''.join(f'<li><a href="{link(a["path"])}">{esc(a["title"])}</a></li>' for a in data.get('audit_links', []))
    assets = ''
    for asset in data.get('assets', []):
        href = link(asset['path']); kind = asset['kind']
        body = f'<img class="extra-image" src="{href}" alt="{esc(asset["title"])}">' if kind == 'image' else f'<audio controls preload="metadata" src="{href}"></audio>' if kind == 'audio' else prose(inside(root, asset['path']).read_text()) if kind == 'text' else ''
        assets += f'<article class="extra-asset"><h3>{esc(asset["title"])}</h3>{body}<a href="{href}" download>下载完整素材</a></article>'
    corrections = ''.join(f'<li><strong>{esc(c["original"])} → {esc(c["corrected"])}</strong><br>{esc(c["reason"])}</li>' for c in data['metadata']['corrections']) or '<li>未提供单独纠错记录。</li>'
    status = data.get('status', {})
    published = f'<a class="publication" href="{esc(status["publication_url"])}" target="_blank" rel="noopener noreferrer">打开已提供的发布链接 ↗</a>' if status.get('publication_url') else ''
    modern = 'public_content' in data
    parts = public_parts(data) if modern else []
    core = ''.join(h for k,h,t in parts if k not in ('chapters','resources'))
    values = {
        'LANG': esc(data['language']), 'TITLE': esc(data['title']), 'SHOW': esc(data['show_title']),
        'SUMMARY': esc(public_summary(data) if modern else data['summary']), 'COVER': cover, 'AUDIO': audio,
        'STATUS': esc(status.get('label', '本地预览 · 待核验')), 'PUBLISHED': published,
        'DURATION': timestamp(report['duration']), 'DESCRIPTION': '' if modern else prose(data['description']),
        'DISCLOSURE': '' if modern else esc(data['ai_disclosure']), 'CHAPTERS': chapters, 'NOTES': core if modern else prose(data['show_notes']),
        'READING': reading, 'SEGMENTS': segments, 'SEGMENT_COUNT': str(len(data['segments'])),
        'READING_LABEL': '中文译写阅读稿' if data['metadata']['reading_mode'] == 'translation' and data['metadata']['reading_language'].startswith('zh') else '译写阅读稿' if data['metadata']['reading_mode'] == 'translation' else '整理阅读稿',
        'READING_LANGUAGE': esc(data['metadata']['reading_language']), 'LAUNCH': prose(data['launch_copy']),
        'NOTES_RAW': esc(public_text(data) if modern else data['show_notes']), 'LAUNCH_RAW': esc(data['launch_copy']),
        'TERMINOLOGY': terminology_html(data), 'MODERN': ' modern' if modern else '', 'RESOURCES': resources, 'ASSETS': assets, 'CORRECTIONS': corrections, 'AUDIT': audit,
    }
    template = (Path(__file__).parent.parent / 'templates' / 'episode.html').read_text()
    return re.sub(r'@@([A-Z_]+)@@', lambda match: values[match.group(1)], template)


def build(data, root, output, content_path):
    report = validate(data, root)
    output = inside(root, os.path.relpath(output, root), existing=False)
    if output.suffix != '.html': fail('output must be .html')
    modern = 'public_content' in data
    names = (['description.html'] if modern else []) + ['aligned-transcript.json','reading-transcript.json','transcript.txt','reading-transcript.txt','show-notes.txt','launch-copy.txt','chapters.json','summary.txt','description.txt','ai-disclosure.txt','content-metadata.json','enrichment-manifest.json']
    sources = {inside(root, data[k]) for k in ('audio_path','cover_path')} | {content_path.resolve()} | {inside(root, a['path']) for k in ('assets','audit_links') for a in data.get(k,[])}
    targets = [output] + [inside(root, os.path.relpath(output.parent / n, root), existing=False) for n in names]
    if len(set(targets)) != len(targets) or set(targets) & sources: fail('output collides with an input or another generated artifact')
    html_text = render(data, root, output, report)
    output.parent.mkdir(parents=True, exist_ok=True)
    artifacts = {
        output.name: html_text,
        'aligned-transcript.json': json.dumps(data['segments'], ensure_ascii=False, indent=2),
        'reading-transcript.json': json.dumps(data['reading_transcript'], ensure_ascii=False, indent=2),
        'transcript.txt': '\n'.join(f'[{timestamp(s["start"])}] '+(s.get('speaker','')+': ' if s.get('speaker') else '')+s['text'] for s in data['segments']),
        'reading-transcript.txt': '\n\n'.join(p['text'] for p in data['reading_transcript']),
        'show-notes.txt': public_text(data) if modern else data['show_notes'], 'launch-copy.txt': data['launch_copy'], 'summary.txt': public_summary(data) if modern else data['summary'], 'description.txt': public_text(data) if modern else data['description'], 'ai-disclosure.txt': data.get('ai_disclosure') or ('' if modern else data['ai_disclosure']),
        'chapters.json': json.dumps(data['chapters'], ensure_ascii=False, indent=2),
        'content-metadata.json': json.dumps(data['metadata'], ensure_ascii=False, indent=2),
    }
    if modern: artifacts['description.html'] = public_html(data)
    for name, content in artifacts.items(): (output.parent / name).write_text(content, encoding='utf-8')
    manifest = {'schema_version': 1, 'content_sha256': digest(content_path), 'audio_sha256': digest(inside(root,data['audio_path'])), 'cover_sha256': digest(inside(root,data['cover_path'])), 'validation': report, 'source_assets': [{'path': p, 'sha256': digest(inside(root,p))} for p in [data['audio_path'],data['cover_path']] + [a['path'] for k in ('assets','audit_links') for a in data.get(k,[])]], 'coverage_map': {'title':'h1','summary':'.lede','description':'#about','audio':'#player','cover':'.cover','chapters':'#chapters','show_notes':'#notes','reading_transcript':'#reading-panel','aligned_transcript':'#aligned-panel','launch_copy':'#launch-text','resources':'.resources','ai_disclosure':'.disclosure','additional_assets':'.extra-asset'}, 'coverage': list(artifacts), 'artifacts': [{'path': str((output.parent/name).relative_to(root)), 'sha256': digest(output.parent/name)} for name in artifacts]}
    (output.parent/'enrichment-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate','build'])
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--package-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.package_root.is_symlink(): fail('package root cannot be a symlink')
        root = args.package_root.resolve(strict=True)
        if not root.is_dir(): fail('package root must be a directory')
        data = json.loads(args.content.read_text(encoding='utf-8'))
        if args.command == 'build':
            if args.output is None: fail('--output required for build')
            result = build(data, root, args.output.absolute(), args.content)
        else: result = validate(data, root)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__': sys.exit(main())
