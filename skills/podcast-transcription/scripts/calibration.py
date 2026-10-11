#!/usr/bin/env python3
"""Nonblocking semantic investigation; immutable, bounded evidence and Scout decisions."""
import argparse
import base64
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import urllib.error

BINDING_KEYS = ('episode_key', 'audio_sha256', 'timeline_sha256', 'content_sha256', 'glossary_sha256')
POLICY = {'version': 1, 'repeat_count': 8, 'gap_seconds': 15, 'max_snippet_seconds': 60, 'max_total_seconds': 180}

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def write_new(path, data):
    with open(path, 'x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())

def run_key(stage, inputs):
    """Caller supplies only upstream identities, never this stage's outputs."""
    if any(k in inputs for k in ('output', 'outputs', 'output_sha256', 'result_sha256')):
        raise ValueError('run identity must contain inputs only')
    return digest({'stage': stage, 'inputs': inputs, 'policy': POLICY, 'implementation': sha(__file__)})

def segments(data):
    rows = data if isinstance(data, list) else data.get('segments', data.get('transcription', []))
    return [{'id': r.get('id', i), 'text': r.get('text', '').strip(),
             'start': r['offsets']['from'] / 1000 if 'offsets' in r else r['start'],
             'end': r['offsets']['to'] / 1000 if 'offsets' in r else r['end']} for i, r in enumerate(rows)]

def detect_anomalies(data, duration, repeat_count=8, gap_seconds=15):
    if not math.isfinite(duration) or duration <= 0 or repeat_count < 2 or gap_seconds <= 0:
        raise ValueError('invalid detector policy/duration')
    rows = segments(data); flags = []; previous = 0
    occurrences = collections.defaultdict(list)
    for row in rows:
        a, b = row['start'], row['end']
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (a, b)) or a < 0 or b <= a or b > duration or a < previous:
            flags.append({'kind': 'timeline', 'segment_id': row['id']})
        if a - previous > gap_seconds: flags.append({'kind': 'coverage_gap', 'start': previous, 'end': a})
        previous = max(previous, b) if math.isfinite(b) else previous
        normalized = re.sub(r'\W', '', row['text']).casefold()
        if len(normalized) >= 4: occurrences[normalized].append(row)
    if duration - previous > gap_seconds: flags.append({'kind': 'coverage_gap', 'start': previous, 'end': duration})
    for value, matches in occurrences.items():
        if len(matches) >= repeat_count:
            flags.append({'kind': 'repeated_phrase', 'text': matches[0]['text'], 'count': len(matches), 'segment_ids': [r['id'] for r in matches], 'start': matches[0]['start'], 'end': matches[-1]['end']})
    # Adjacent multi-segment cycles are detectable even when individual phrases are short.
    for width in range(2, 5):
        texts = [r['text'] for r in rows]
        for i in range(len(rows) - width * repeat_count + 1):
            pattern = texts[i:i + width]
            if len(set(pattern)) < 2: continue
            count = 1
            while texts[i + count * width:i + (count + 1) * width] == pattern: count += 1
            if count >= repeat_count:
                flags.append({'kind': 'repeated_cycle', 'start': rows[i]['start'], 'end': rows[i + count * width - 1]['end'], 'count': count, 'width': width})
                break
    return {'version': 1, 'publication_blocked': False, 'route': 'investigate' if flags else 'normal', 'policy': {'repeat_count': repeat_count, 'gap_seconds': gap_seconds}, 'flags': flags, 'timing_accuracy': 'asr_estimated'}

def parse_glossary(markdown):
    """Candidate hints only; keep ambiguous aliases and conflicting source lines."""
    entries = []; mappings = collections.defaultdict(set)
    for line, raw in enumerate(markdown.splitlines(), 1):
        match = re.match(r'^\s*[-*]\s+(.+)$', raw)
        if not match: continue
        value = match[1].strip()
        if '**' in value: continue
        sides = re.split(r'\s*(?:=>|=|→)\s*', value, maxsplit=1)
        canonical = sides[-1].strip()
        aliases = [s.strip() for s in sides[0].split('/') if s.strip()] if len(sides) == 2 else [canonical]
        for alias in aliases:
            mappings[alias.casefold()].add(canonical)
            entries.append({'alias': alias, 'canonical': canonical, 'line': line, 'short_alias': len(alias.replace(' ', '')) <= 2, 'source': 'living_glossary', 'user_confirmed': False})
    for entry in entries: entry['conflict'] = len(mappings[entry['alias'].casefold()]) > 1
    return {'source_sha256': hashlib.sha256(markdown.encode()).hexdigest(), 'entries': entries}

def relevant_terms(glossary, text):
    def present(alias):
        # Latin aliases require boundaries; a single F must not match Felix.
        return bool(re.search(r'(?<![\w])' + re.escape(alias) + r'(?![\w])', text, re.I)) if alias.isascii() else alias in text
    return {'glossary_sha256': glossary['source_sha256'], 'candidates': [e for e in glossary['entries'] if present(e['alias'])], 'automatic_replacement': False}

def import_user_decisions(document, binding, terms, actor_kind, source_ref):
    """The caller's actual interaction provenance is authoritative, not JSON claims."""
    if actor_kind != 'human' or not source_ref: raise ValueError('user decisions require actual human source')
    if any(not binding.get(k) or document.get('bindings', {}).get(k) != binding[k] for k in BINDING_KEYS): raise ValueError('stale or incomplete decision binding')
    allowed = {t['id'] for t in terms}; seen = set(); output = []
    for row in document.get('decisions', []):
        if row.get('term_id') not in allowed or row['term_id'] in seen or row.get('decision') not in ('confirm', 'edit', 'defer'): raise ValueError('unknown/duplicate/invalid decision')
        if row['decision'] == 'edit' and (not isinstance(row.get('text'), str) or not row['text'].strip()): raise ValueError('replacement required')
        seen.add(row['term_id']); output.append({**row, 'reviewed_by_kind': 'human', 'source_ref': source_ref, 'bindings': dict(binding)})
    return output

def reconcile(term, votes, mode, user_decision=None):
    if mode not in ('interactive', 'autonomous'): raise ValueError('invalid operating mode')
    if user_decision and user_decision.get('decision') != 'defer':
        if user_decision.get('reviewed_by_kind') != 'human' or not user_decision.get('source_ref') or user_decision.get('term_id') != term['id']: raise ValueError('unverified user decision')
        if any(user_decision.get('bindings', {}).get(k) != term.get('bindings', {}).get(k) or not term.get('bindings', {}).get(k) for k in BINDING_KEYS): raise ValueError('stale user decision')
        return {'text': user_decision['text'] if user_decision['decision'] == 'edit' else term['current'], 'status': 'user_confirmed', 'evidence': user_decision}
    if mode == 'interactive':
        if votes: raise ValueError('model election only in autonomous mode')
        return {'text': term['current'], 'status': 'awaiting_user', 'publication_blocked': False}
    models = set(); accepted = []
    for vote in votes:
        if vote.get('reviewed_by_kind') != 'agent' or not vote.get('model_id') or not vote.get('request_sha256') or not vote.get('source_ref') or 'raw_response' not in vote: raise ValueError('vote provenance missing')
        if vote['model_id'] in models: raise ValueError('duplicate model is not independent election')
        if vote.get('independent') is not True: raise ValueError('vote must record independent request')
        if vote.get('response_sha256') != digest(vote['raw_response']): raise ValueError('response hash mismatch')
        models.add(vote['model_id']); accepted.append(vote)
    counts = collections.Counter(v['choice'] for v in accepted if isinstance(v.get('choice'), str) and v['choice'].strip())
    ranked = counts.most_common(); selected = term['current']
    if ranked and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]): selected = ranked[0][0]
    return {'text': selected, 'status': 'provisional', 'degraded': 'single_model' if len(models) == 1 else ('no_model' if not models else None), 'needs_user_confirmation': True, 'publication_blocked': False, 'votes': accepted, 'dissent': len(counts) > 1, 'confidence': 'not_established_by_vote_count'}

def probe_duration(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(path)], text=True))

def validate_ranges(authorization, source_sha256, duration):
    if authorization.get('source_sha256') != source_sha256 or authorization.get('source_kind') != 'final_delivery' or not authorization.get('source_ref') or authorization.get('external_snippet_asr_authorized') is not True:
        raise ValueError('explicit final delivery snippet authorization required')
    ranges = authorization.get('ranges', []); total = 0; last = -1
    if not ranges: raise ValueError('empty ranges')
    for row in ranges:
        a, b = row.get('start'), row.get('end')
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in (a, b)) or a < 0 or b > duration or b <= a or a < last or b - a > 60:
            raise ValueError('range invalid/overlapping/over 60 seconds')
        if a == 0 and b >= duration: raise ValueError('full episode upload forbidden')
        total += b - a; last = b
    if total > 180 or total >= duration: raise ValueError('total over 180 seconds or full episode coverage')
    return ranges

def extract_snippets(delivery, authorization, output):
    delivery = Path(delivery).resolve(); output = Path(output); source_hash = sha(delivery); duration = probe_duration(delivery)
    ranges = validate_ranges(authorization, source_hash, duration)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'version': 1, 'source_path': str(delivery), 'source_sha256': source_hash, 'source_duration': duration, 'authorization': authorization, 'authorization_sha256': digest(authorization), 'snippets': []}
    for i, row in enumerate(ranges):
        path = output / ('snippet-%03d.wav' % i)
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(delivery), '-ss', str(row['start']), '-t', str(row['end'] - row['start']), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(path)], check=True)
        actual = probe_duration(path)
        if abs(actual - (row['end'] - row['start'])) > .05: raise ValueError('extracted duration mismatch')
        manifest['snippets'].append({'id': i, 'path': str(path.resolve()), 'sha256': sha(path), 'start': row['start'], 'end': row['end'], 'duration': actual, 'timing_accuracy': 'asr_estimated'})
    if sha(delivery) != source_hash: raise ValueError('source changed during extraction')
    write_new(output / 'manifest.json', manifest)
    return manifest

PROMPT = 'Transcribe only the attached audio verbatim in its original language. Keep audible fillers and uncertainty. Do not invent missing speech. Return JSON with segments [{"start": seconds relative to this clip, "end": seconds, "text": "..."}]. Times are estimates. No commentary.'

def gemini_transcribe(manifest, output, models=('gemini-3.5-transcribe', 'gemini-3.8-flash'), transport=None):
    """Explicit invocation uploads validated snippets only. Never receives Whisper/glossary text."""
    output = Path(output)
    if digest(manifest['authorization']) != manifest['authorization_sha256']: raise ValueError('authorization changed')
    ranges = validate_ranges(manifest['authorization'], manifest['source_sha256'], manifest['source_duration'])
    if sha(manifest['source_path']) != manifest['source_sha256']: raise ValueError('final source changed')
    if len(ranges) != len(manifest['snippets']): raise ValueError('snippet set mismatch')
    for row, snippet in zip(ranges, manifest['snippets']):
        if any(row[k] != snippet[k] for k in ('start', 'end')) or sha(snippet['path']) != snippet['sha256'] or abs(probe_duration(snippet['path']) - (row['end'] - row['start'])) > .05: raise ValueError('snippet binding mismatch')
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key and transport is None: raise ValueError('Gemini credential unavailable')
    output.mkdir(parents=True, exist_ok=False); reports = []
    for snippet in manifest['snippets']:
        for model in models:
            if not re.fullmatch(r'[a-zA-Z0-9._-]+', model): raise ValueError('invalid model id')
            payload = {'contents': [{'role': 'user', 'parts': [{'text': PROMPT}, {'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(Path(snippet['path']).read_bytes()).decode()}}]}]}
            record = {'model_id': model, 'snippet': snippet, 'request_sha256': digest(payload), 'independent': True, 'whisper_context_provided': False, 'status': 'failed'}
            try:
                if transport: raw = transport(model, payload)
                else:
                    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
                    with urllib.request.urlopen(req, timeout=120) as response: raw = json.loads(response.read())
                record['raw_response'] = raw; record['response_sha256'] = digest(raw)
                text = '\n'.join(p.get('text', '') for c in raw.get('candidates', []) for p in c.get('content', {}).get('parts', []) if not p.get('thought'))
                record['text'] = text
                if text.strip():
                    record['status'] = 'ok'; record['timing_accuracy'] = 'asr_estimated'
                    try:
                        parsed = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip()))
                        timed = segments(parsed)
                        if any(not math.isfinite(r['start'] + r['end']) or r['start'] < 0 or r['end'] <= r['start'] or r['end'] > snippet['duration'] + .25 for r in timed): raise ValueError('invalid estimated clip times')
                        record['segments'] = [{**r, 'relative_start': r['start'], 'relative_end': r['end'], 'start': r['start'] + snippet['start'], 'end': r['end'] + snippet['start']} for r in timed]
                    except (ValueError, KeyError, TypeError): record['timing_parse_status'] = 'unavailable_raw_text_retained'
                else: record['error'] = 'empty_response'
            except Exception as exc:
                # No server body, URL, request payload, or credential appears in exception logs.
                record['error'] = type(exc).__name__
                if isinstance(exc, urllib.error.HTTPError): record['http_status'] = exc.code
            write_new(output / ('snippet-%03d-%s.json' % (snippet['id'], model)), record); reports.append(record)
            if record['status'] == 'ok': break
    result = {'version': 1, 'manifest_sha256': digest(manifest), 'attempts': reports, 'publication_blocked': False}
    write_new(output / 'report.json', result)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('detect'); p.add_argument('--input', required=True); p.add_argument('--duration', type=float, required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('glossary'); p.add_argument('--source', required=True); p.add_argument('--episode-text', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('extract'); p.add_argument('--delivery', required=True); p.add_argument('--authorization', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('gemini'); p.add_argument('--manifest', required=True); p.add_argument('--output', required=True)
    a = parser.parse_args(); read = lambda p: json.loads(Path(p).read_text())
    if a.command == 'detect': write_new(a.output, detect_anomalies(read(a.input), a.duration))
    elif a.command == 'glossary': write_new(a.output, relevant_terms(parse_glossary(Path(a.source).read_bytes().decode('utf-8')), Path(a.episode_text).read_text()))
    elif a.command == 'extract': extract_snippets(a.delivery, read(a.authorization), a.output)
    else: gemini_transcribe(read(a.manifest), a.output)

if __name__ == '__main__': main()
