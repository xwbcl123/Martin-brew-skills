#!/usr/bin/env python3
"""Offline intake only: never reads credentials or grants release authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

KEYS = set('workspace whisper_cli whisper_model transistor_cli transistor_cli_repo language approver artwork_registry planning_profiles_dir shows'.split())

PATH_KEYS = KEYS - {'language', 'approver', 'shows'}

def resolve(value, base):
    p = Path(value)
    return (p if p.is_absolute() else base / p).resolve()


def atomic_new(path, data):
    """Publish complete bytes without replacing an existing file (including symlinks)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.startup-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.link(tmp, path)
    finally:
        os.unlink(tmp)


def fingerprint(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def check(args):
    root = Path(args.episode_dir).resolve()
    meta, config = root / '_meta.md', Path(args.config).absolute()
    report = dict(mode=args.mode, readiness_scope='input_preflight_only', status='needs_input', issues=[], pending_checks=[], files=[], roles=[],
                  publish_authorized=False, audio_review='unverified',
                  local_acceptance='unverified', next_stage='resolve_intake')
    protected = {meta.resolve(), config.resolve()}

    def gap(code, action, blocked=False):
        report['issues'].append(dict(code=code, action=action,
                                     severity='blocked' if blocked else 'needs_input'))

    def record(path, kind):
        protected.add(path.resolve())
        try:
            item = fingerprint(path)
            item['kind'] = kind
            report['files'].append(item)
            return True
        except OSError:
            gap('missing_' + kind, 'Provide a readable ' + kind + ' file.')
            return False

    cfg = {}
    try:
        raw = json.loads(config.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raise ValueError()
        if set(raw) - KEYS:
            gap('unknown_config_keys', 'Remove unsupported config keys; only the ten documented keys are supported.', True)
        cfg = {k: v for k, v in raw.items() if k in KEYS}
        for k, v in cfg.items():
            if k == 'shows':
                if not isinstance(v, dict):
                    gap('invalid_shows', 'shows must be an object keyed by numeric show ID.', True)
                    continue
                for sid, entry in v.items():
                    if not re.fullmatch(r'[0-9]+', str(sid)) or not isinstance(entry, dict) or set(entry) - {'author', 'brand_name', 'brand_tagline'}:
                        gap('invalid_show_entry', 'Use numeric show IDs and only author/brand_name/brand_tagline fields.', True)
                        continue
                    if any(field in entry and (not isinstance(entry[field], str) or not entry[field].strip()) for field in ('author', 'brand_name')) or ('brand_tagline' in entry and not isinstance(entry['brand_tagline'], str)):
                        gap('invalid_show_value', 'author/brand_name must be non-empty strings; brand_tagline must be a string.', True)
            elif not isinstance(v, str) or not v.strip():
                gap('invalid_config_value', 'Correct supported configuration value types: ' + k, True)
            elif k in PATH_KEYS and not Path(v).expanduser().is_absolute():
                gap('relative_config_path', 'Set an absolute configuration path for ' + k + '.', True)
        # Config may hold private data: never echo or hash its contents.
    except (OSError, ValueError, UnicodeError):
        gap('missing_or_invalid_config', 'Provide a readable JSON object config with supported keys.')
    fields, roles, duplicates = {}, [], set()
    if record(meta, 'meta'):
        try:
            text = meta.read_text(encoding='utf-8')
            for line in text.splitlines():
                match = re.fullmatch(r'- ([A-Za-z][A-Za-z -]*):\s*(.*)', line)
                if match:
                    key = match[1]
                    if key in fields or key in duplicates:
                        duplicates.add(key)
                        fields.pop(key, None)
                    else:
                        fields[key] = match[2].strip()
                elif re.match(r'\s+- ', line):
                    roles.append(line.strip()[2:])
            if duplicates:
                gap('duplicate_meta_fields', 'Resolve repeated metadata fields: ' + ', '.join(sorted(duplicates)) + '; no occurrence was selected.', True)
            if not text.startswith('# Episode handoff') or not fields:
                gap('unsupported_template', 'Use the Episode handoff Markdown template.', True)
        except (OSError, UnicodeError):
            gap('invalid_meta', 'Provide UTF-8 episode metadata.', True)

    def value(key, required=True):
        if key in duplicates:
            return ''
        v = fields.get(key, '')
        if not v or '<' in v or '>' in v:
            if required:
                gap('missing_' + key.lower().replace(' ', '_'), 'Fill the template field: ' + key)
            return ''
        return v

    value('Episode')
    intent = value('Edit intent')
    finished = 'finished audio' in intent.lower()
    source_text = value('Original media')
    sources = [resolve(v.strip(), meta.parent) for v in source_text.split(';') if v.strip()]
    if len(sources) > 1:
        gap('ambiguous_sources', 'Bind each speaker and WFP source to an exact original; this intake supports one source.', True)
    streams = []
    for source in sources:
        if not record(source, 'source'):
            continue
        if not shutil.which('ffprobe'):
            gap('missing_ffprobe', 'Install/expose ffprobe for actual media geometry.', True)
            continue
        try:
            result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                                     '-of', 'json', str(source)], capture_output=True, timeout=30)
            data = json.loads(result.stdout)
            if result.returncode:
                raise ValueError()
            audio = [s for s in data['streams'] if s.get('codec_type') == 'audio']
            geometry = [{k: s.get(k) for k in ('index', 'codec_name', 'channels', 'channel_layout', 'sample_rate', 'duration')} for s in audio]
            report['files'][-1]['audio_streams'] = geometry
            report['files'][-1]['duration'] = data.get('format', {}).get('duration')
            if len(sources) == 1:
                streams = audio
            if not audio:
                gap('no_audio', 'Supply media with at least one audio stream.', True)
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            gap('probe_failed', 'ffprobe could not inspect the original media.', True)
    if not shutil.which('ffmpeg'):
        gap('missing_ffmpeg', 'Install/expose FFmpeg before local production.', True)
    wfp = value('Rough-cut WFP', not finished)
    if wfp:
        path = resolve(wfp, meta.parent)
        if record(path, 'wfp'):
            try:
                with zipfile.ZipFile(path) as z:
                    names = z.namelist()
                    if not names or not any(n.lower().endswith('.json') for n in names):
                        raise ValueError()
                    report['wfp'] = dict(inventory=names, route='wfp_extract_edl',
                                         source_references='unverified', nominal_structure='unverified',
                                         unknown_dsp='unverified')
                report['pending_checks'].append(dict(code='wfp_semantics_unverified',
                    action='Run read-only wfp_extract_edl validation of source paths, nominal deletion structure and unknown DSP before rendering.'))
            except (OSError, ValueError, zipfile.BadZipFile):
                gap('invalid_wfp', 'Provide a WFP ZIP containing a JSON project inventory.', True)
    used = set()
    if not roles and not finished:
        gap('missing_speakers', 'Declare speaker names and absolute/audio-relative stream indices with channels.')
    for declaration in roles:
        m = re.fullmatch(r'([^:<>]+): absolute stream (\d+), audio-relative index (\d+), (left|right|dual mono)', declaration)
        if not m:
            gap('invalid_role', 'Use Speaker name: absolute stream N, audio-relative index M, left/right/dual mono; replace placeholders.')
            continue
        name, absolute, relative, channel = m.groups()
        absolute, relative = int(absolute), int(relative)
        report['roles'].append(dict(speaker=name, absolute_stream=absolute, audio_relative_index=relative, channel=channel))
        if relative >= len(streams) or streams[relative].get('index') != absolute:
            gap('role_stream_mismatch', 'Correct the declared absolute stream and audio-relative index against ffprobe.', True)
            continue
        count = streams[relative].get('channels', 0)
        if count != 2:
            gap('role_channel_geometry', 'Left/right/dual mono declarations require a verified two-channel stream.', True)
        channels = (0, 1) if channel == 'dual mono' else (0,) if channel == 'left' else (1,)
        for c in channels:
            if (absolute, c) in used:
                gap('role_conflict', 'Assign each source channel to one speaker; resolve overlapping declarations.', True)
            used.add((absolute, c))
        if channel == 'dual mono':
            report['pending_checks'].append(dict(code='dual_mono_unverified',
                action='Verify channel equivalence acoustically before selecting one channel; never sum twice.'))
    for key in ('whisper_cli', 'whisper_model'):
        v = cfg.get(key)
        path = Path(v).expanduser().resolve() if isinstance(v, str) and v.strip() and Path(v).expanduser().is_absolute() else None
        if path:
            protected.add(path)
        if not path or not path.is_file() or (key == 'whisper_cli' and not os.access(path, os.X_OK)):
            gap('missing_' + key, 'Configure a readable model / executable Whisper CLI for ASR.')
    if args.mode == 'publish':
        value('Target show ID')
        report['pending_checks'].extend([
            dict(code='publication_identity_unverified', action='Resolve actual provider/show ownership through the publisher read/plan route; no credential is read here.'),
            dict(code='publication_authority_unverified', action='Downstream publisher must bind the real episode-specific instruction and frozen package; --mode never grants authority.'),
        ])
    report['capabilities'] = dict(audio_review='unverified: actual audio required', preview='unverified: playback/seek required', asr_execution='unverified')
    report['status'] = 'blocked' if any(i['severity'] == 'blocked' for i in report['issues']) else 'needs_input' if report['issues'] else 'ready'
    if report['status'] == 'ready':
        report['next_stage'] = 'transcription_and_audio_review' if finished else 'validate_wfp_structure'
        report['readiness_scope'] = 'ready_to_start_' + report['next_stage']
    if args.output:
        out = Path(args.output).absolute()
        if out.resolve() in protected or any(out.exists() and p.exists() and os.path.samefile(out, p) for p in protected):
            raise ValueError('Output must not overwrite an input.')
        atomic_new(out, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    setup = sub.add_parser('setup')
    setup.add_argument('--config', required=True)
    setup.add_argument('--workspace', required=True)
    setup.add_argument('--language', default='auto')
    setup.add_argument('--whisper-cli')
    setup.add_argument('--whisper-model')
    probe = sub.add_parser('check')
    probe.add_argument('--episode-dir', required=True)
    probe.add_argument('--mode', choices=('local', 'publish'), required=True)
    probe.add_argument('--config', required=True)
    probe.add_argument('--output')
    args = parser.parse_args(argv)
    try:
        if args.command == 'setup':
            base = Path(args.config).absolute().parent
            data = dict(workspace=str(resolve(args.workspace, base)), language=args.language)
            for key in ('whisper_cli', 'whisper_model'):
                if getattr(args, key):
                    data[key] = str(resolve(getattr(args, key), base))
            atomic_new(Path(args.config).absolute(), data)
            result = dict(status='ready', scope='configuration_created')
        else:
            result = check(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'ready' else 2
    except (OSError, ValueError):
        print(json.dumps(dict(status='blocked', error='Cannot complete operation: invalid input or output unavailable/existing. No overwrite permitted.')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
