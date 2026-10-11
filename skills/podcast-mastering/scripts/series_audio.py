#!/usr/bin/env python3
"""Hash-bound series bookends and explicit, synchronized channel matrices."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

RATE = 48000

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def run(argv):
    return subprocess.run(list(map(str, argv)), capture_output=True, check=True, text=True)

def observe(path, stream=0):
    if type(stream) is not int or stream < 0:
        raise ValueError('invalid audio stream index')
    s = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', f'a:{stream}',
                       '-show_streams', '-of', 'json', path]).stdout)['streams'][0]
    channels = int(s['channels'])
    with tempfile.TemporaryFile() as f:
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', f'0:a:{stream}',
                        '-c:a', 'pcm_s32le', '-f', 's32le', '-'], stdout=f,
                       stderr=subprocess.PIPE, check=True)
        frames = f.tell() // (4 * channels)
    return dict(sample_rate=int(s['sample_rate']), samples=frames, channels=channels)

def relative_asset(profile, value):
    p = Path(value)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('series asset must be a bounded relative path')
    resolved = (profile.parent / p).resolve()
    if not resolved.is_relative_to(profile.parent.resolve()):
        raise ValueError('series asset escapes profile directory')
    return resolved

def load_series(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text())
    if data.get('schema_version') != '1.0' or not data.get('series_id'):
        raise ValueError('invalid series profile')
    if data.get('intro_required') is not True or data.get('outro_required') is not True:
        raise ValueError('series mastering requires both intro and outro')
    assets = {}
    for role in ('intro', 'outro'):
        entry = data[role]
        asset = relative_asset(path, entry['path'])
        if sha(asset) != entry['sha256']:
            raise ValueError(role + ' asset hash mismatch')
        info = observe(asset)
        if info['sample_rate'] != RATE or info['channels'] != 2:
            raise ValueError(role + ' must be 48 kHz stereo')
        if info['samples'] != entry['samples'] or entry['sample_rate'] != RATE:
            raise ValueError(role + ' observed sample count mismatch')
        if not 3 * RATE <= info['samples'] <= 5 * RATE:
            raise ValueError(role + ' must last 3-5 seconds')
        gain = entry.get('gain_db', 0)
        if not isinstance(gain, (int, float)) or not math.isfinite(gain):
            raise ValueError('invalid music gain')
        assets[role] = dict(path=str(asset), sha256=entry['sha256'], gain_db=gain, **info)
    return dict(profile_path=str(path), profile_sha256=sha(path),
                series_id=data['series_id'], assets=assets)

def load_mix(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text())
    if data.get('schema_version') != '1.0' or not data.get('tracks'):
        raise ValueError('invalid mix manifest')
    tracks = []
    for entry in data['tracks']:
        source = Path(entry['path'])
        source = source.resolve() if source.is_absolute() else (path.parent / source).resolve()
        if sha(source) != entry['sha256']:
            raise ValueError('mix input hash mismatch')
        stream = entry.get('audio_stream', 0)
        info = observe(source, stream)
        matrix = entry['matrix']
        if len(matrix) != 2 or any(len(row) != info['channels'] for row in matrix):
            raise ValueError('matrix must map observed input channels to stereo')
        if any(not isinstance(x, (float, int)) or not math.isfinite(x)
               for row in matrix for x in row):
            raise ValueError('non-finite matrix coefficient')
        if info['sample_rate'] != RATE:
            raise ValueError('mix tracks must share the 48 kHz sample clock')
        if tracks and info['samples'] != tracks[0]['samples']:
            raise ValueError('mix tracks have unequal decoded sample counts')
        tracks.append(dict(path=str(source), sha256=entry['sha256'], audio_stream=stream,
                           matrix=matrix, role=entry.get('role', 'unspecified'), **info))
    if not any(x for track in tracks for row in track['matrix'] for x in row):
        raise ValueError('mix matrix is entirely muted')
    return dict(manifest_path=str(path), manifest_sha256=sha(path), tracks=tracks,
                sample_rate=RATE, samples=tracks[0]['samples'])

def render_mix(mix, output):
    argv = ['ffmpeg', '-v', 'error', '-nostdin', '-n']
    filters = []
    for i, track in enumerate(mix['tracks']):
        argv += ['-i', track['path']]
        rows = ['c%d=' % j + '+'.join(f'{float(v)}*c{k}' for k, v in enumerate(row))
                for j, row in enumerate(track['matrix'])]
        filters.append(f"[{i}:a:{track['audio_stream']}]aformat=sample_fmts=fltp,pan=stereo|" + '|'.join(rows) + f'[t{i}]')
    labels = ''.join(f'[t{i}]' for i in range(len(mix['tracks'])))
    filters.append(labels + f"amix=inputs={len(mix['tracks'])}:duration=longest:normalize=0[out]")
    run(argv + ['-filter_complex', ';'.join(filters), '-map', '[out]', '-c:a', 'pcm_f32le', output])
    if observe(output)['samples'] != mix['samples']:
        raise ValueError('mixed sample accounting mismatch')

def compose(body, series, output):
    info = observe(body)
    if info['sample_rate'] != RATE:
        raise ValueError('series body must be 48 kHz; resample explicitly before composition')
    intro, outro = (series['assets'][role] for role in ('intro', 'outro'))
    filters = (f"[0:a:0]aformat=sample_fmts=fltp,volume={intro['gain_db']}dB:precision=double[i];"
               '[1:a:0]aformat=sample_fmts=fltp:channel_layouts=stereo[b];'
               f"[2:a:0]aformat=sample_fmts=fltp,volume={outro['gain_db']}dB:precision=double[o];"
               '[i][b][o]concat=n=3:v=0:a=1[out]')
    run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-i', intro['path'], '-i', body,
         '-i', outro['path'], '-filter_complex', filters, '-map', '[out]',
         '-ar', RATE, '-c:a', 'pcm_f32le', output])
    expected = intro['samples'] + info['samples'] + outro['samples']
    if observe(output)['samples'] != expected:
        raise ValueError('composed sample accounting mismatch')
    return dict(sample_rate=RATE, samples=expected, body_offset_samples=intro['samples'],
                segments=[dict(role='intro', start_sample=0, end_sample=intro['samples']),
                          dict(role='body', start_sample=intro['samples'],
                               end_sample=intro['samples'] + info['samples']),
                          dict(role='outro', start_sample=intro['samples'] + info['samples'],
                               end_sample=expected)],
                overlap_samples=0, mapping_kind='concatenation-with-slope-one-body',
                final_asr_required=True, final_chapters_required=True)

def recheck(contract):
    if not contract:
        return
    for key in ('profile_path', 'manifest_path'):
        if key in contract and sha(contract[key]) != contract[key.replace('_path', '_sha256')]:
            raise ValueError('configuration changed during rendering')
    entries = contract.get('tracks', list(contract.get('assets', {}).values()))
    for entry in entries:
        if sha(entry['path']) != entry['sha256']:
            raise ValueError('audio asset changed during rendering')
