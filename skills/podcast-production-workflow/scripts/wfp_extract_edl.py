#!/usr/bin/env python3
"""Extract a NOMINAL delete-only cut list from a Filmora .wfp project. Read-only, fail-closed.

A .wfp is a ZIP (members are stored or deflated) holding JSON timelines
(`ProjectFolder/Medias/<id>/timeline.wesproj`). Audio clips carry `inPoint/outPoint` (source),
`tlBegin/tlEnd` (timeline) in 10 MHz ticks, `streamId`, `sourceUuid`, `filename` and a `speed` block.

Scope (anything else exits non-zero BEFORE any output is written):
  * one selected leaf timeline + one audible audio track, all clips media clips (type 2),
  * a single source (one sourceUuid/filename) and a single streamId,
  * contiguous, ordered timeline; monotonic non-overlapping source ranges (delete-only),
  * constant speed 1.0, not reversed; positive, consistent sample intervals after rounding.
Automatic selection follows: current timeline -> its single audible audio track -> one identity wrapper clip (type 16,
in=tlBegin=0, out=tlEnd=child duration, speed 1.0, not reversed) -> leaf timeline -> its single audible audio track.
Routing assumption (verified on EP04 only): standard DAW semantics -- if any audio track is soloed only soloed tracks are
audible, otherwise non-muted tracks are; unknown or conflicting flags fail closed. Video tracks are ignored.
An explicitly selected leaf (--timeline-member and/or --timeline-id, optionally with --track-index; --track-index alone is rejected) is a *diagnostic* extraction: export association stays unverified.
Nominal source positions are only coordinate resolution, NOT acoustic accuracy (EP04: -27..+26 ms vs the user-accepted
refined candidate). Refine every boundary against the raw stems before using this as a sample-exact EDL. Effects are NOT
interpreted (`effects_status: unknown_not_verified`). The Filmora streamId is not an FFmpeg stream index.
Usage: wfp_extract_edl.py PROJECT.wfp --output out.json [--sample-rate 48000] [--source-total-samples N]
       wfp_extract_edl.py PROJECT.wfp --inventory   (prints candidates, writes nothing)
"""
import argparse
import hashlib
import io
import json
import os
import stat
import sys
from fractions import Fraction
from pathlib import Path
from zipfile import BadZipFile, ZipFile

TICKS = 10_000_000
LIMITS = dict(archive_bytes=512 << 20, members=5000, json_member_bytes=64 << 20, total_json_bytes=256 << 20, nest_depth=4)
SUPPORTED_RATES = (44100, 48000, 96000)


class Unsupported(Exception):
    pass


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def to_sample(ticks, rate):
    f = Fraction(ticks * rate, TICKS)
    return (2 * f.numerator + f.denominator) // (2 * f.denominator)  # round half up


def as_dict(v, path):
    if not isinstance(v, dict):
        raise Unsupported(f'{path}: expected an object, got {type(v).__name__}')
    return v


def as_list(v, path):
    if not isinstance(v, list):
        raise Unsupported(f'{path}: expected a list, got {type(v).__name__}')
    return v


def flag(d, key, path):
    v = d.get(key)
    if v is None:
        return False
    if not isinstance(v, bool):
        raise Unsupported(f'{path}.{key}: expected a boolean, got {v!r}')
    return v


def load_archive(path, limits):
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode):
        raise Unsupported(f'input is not a regular file: {path}')
    if st.st_size > limits['archive_bytes']:
        raise Unsupported(f'archive_bytes limit exceeded ({st.st_size} > {limits["archive_bytes"]})')
    with open(path, 'rb') as f:
        data = f.read(limits['archive_bytes'] + 1)
    if len(data) > limits['archive_bytes']:
        raise Unsupported('archive_bytes limit exceeded while reading')
    st2 = os.lstat(path)
    if st2.st_mtime_ns != st.st_mtime_ns or st2.st_size != st.st_size:
        raise Unsupported('input changed while being read')
    return data, hashlib.sha256(data).hexdigest()


def read_json_members(data, limits):
    try:
        z = ZipFile(io.BytesIO(data))
    except BadZipFile as e:
        raise Unsupported(f'not a ZIP archive: {e}')
    infos = z.infolist()
    if len(infos) > limits['members']:
        raise Unsupported(f'members limit exceeded ({len(infos)})')
    names = [i.filename for i in infos]
    if len(set(names)) != len(names):
        raise Unsupported('duplicate ZIP member names')
    out, total = {}, 0
    for i in infos:
        if i.flag_bits & 0x1:
            raise Unsupported(f'encrypted member: {i.filename}')
        base = i.filename.rsplit('/', 1)[-1]
        if base not in ('timeline.wesproj', 'project_info.json'):
            continue
        if i.file_size > limits['json_member_bytes']:
            raise Unsupported(f'json_member_bytes limit exceeded: {i.filename} ({i.file_size})')
        total += i.file_size
        if total > limits['total_json_bytes']:
            raise Unsupported('total_json_bytes limit exceeded')
        with z.open(i) as f:
            raw = f.read(i.file_size + 1)
        if len(raw) != i.file_size:
            raise Unsupported(f'member size mismatch: {i.filename}')
        try:
            doc = json.loads(raw)
        except ValueError as e:
            raise Unsupported(f'invalid JSON in {i.filename}: {e}')
        as_dict(doc, i.filename)
        out[i.filename] = (doc, hashlib.sha256(raw).hexdigest(), i.compress_type)
    return out


def check_structure(members):
    """Validate object/list shapes of everything we traverse, with field paths in the error."""
    for name, (j, _, _) in members.items():
        if not name.endswith('timeline.wesproj'):
            continue
        for ti, tl in enumerate(as_list(j.get('timelineInfos', []), f'{name}.timelineInfos')):
            tp = f'{name}.timelineInfos[{ti}]'
            as_dict(tl, tp)
            for k, tr in enumerate(as_list(tl.get('trackInfos', []), f'{tp}.trackInfos')):
                kp = f'{tp}.trackInfos[{k}]'
                as_dict(tr, kp)
                flag(tr, 'solo', kp)
                flag(tr, 'mute', kp)
                for ci, c in enumerate(as_list(tr.get('clipList', []), f'{kp}.clipList')):
                    cp = f'{kp}.clipList[{ci}]'
                    as_dict(c, cp)
                    for ch in as_list(c.get('effectChainList', []), f'{cp}.effectChainList'):
                        for e in as_list(as_dict(ch, f'{cp}.effectChainList[]').get('effectList', []), f'{cp}.effectList'):
                            as_dict(e, f'{cp}.effectList[]')


def timelines_of(members):
    inv = []
    for name, (j, h, _) in sorted(members.items()):
        if not name.endswith('timeline.wesproj'):
            continue
        for ti, tl in enumerate(j.get('timelineInfos') or []):
            tracks = []
            for k, tr in enumerate(tl.get('trackInfos') or []):
                cl = tr.get('clipList') or []
                tracks.append(dict(index=k, track_type=tr.get('trackType'), clips=len(cl), solo=tr.get('solo'), mute=tr.get('mute'),
                                   nested=[c.get('timelineId') for c in cl if c.get('type') == 16]))
            inv.append(dict(member=name, member_sha256=h, timeline_index=ti, timeline_id=tl.get('timelineId'), is_current=(tl.get('timelineId') == j.get('currentTimelineId')), tracks=tracks))
    return inv


def timeline_fingerprint(members, member, ti):
    tl = members[member][0]['timelineInfos'][ti]
    return hashlib.sha256(json.dumps(tl.get('trackInfos'), sort_keys=True).encode()).hexdigest()


def _ranges(members, member, ti):
    tl = members[member][0]['timelineInfos'][ti]
    return [[(c.get('inPoint'), c.get('outPoint'), c.get('tlBegin'), c.get('tlEnd')) for c in (tr.get('clipList') or [])] for tr in tl.get('trackInfos') or [] if tr.get('trackType') == 2]


def timeline_duration(tl):
    ends = [c.get('tlEnd') for tr in tl.get('trackInfos') or [] for c in tr.get('clipList') or []]
    if not ends or any(not is_int(e) or e <= 0 for e in ends):
        raise Unsupported(f'cannot determine duration of timeline {tl.get("timelineId")}')
    return max(ends)


def audible_audio_tracks(tl, where):
    """Indices of audible audio tracks with clips under standard solo/mute semantics; conflicting flags fail closed."""
    audio = [(k, tr) for k, tr in enumerate(tl.get('trackInfos') or []) if tr.get('trackType') == 2]
    for k, tr in audio:
        if flag(tr, 'solo', f'{where}.trackInfos[{k}]') and flag(tr, 'mute', f'{where}.trackInfos[{k}]'):
            raise Unsupported(f'{where}.trackInfos[{k}]: track is both solo and muted (unknown routing semantics)')
    soloed = [k for k, tr in audio if flag(tr, 'solo', where)]
    pool = soloed if soloed else [k for k, tr in audio if not flag(tr, 'mute', where)]
    return [k for k in pool if tl['trackInfos'][k].get('clipList')]


def check_speed(c, label):
    sp = c.get('speed')
    if not isinstance(sp, dict) or sp.get('reverse') is not False or not isinstance(sp.get('speedParam'), str):
        raise Unsupported(f'{label}: missing/unknown speed semantics')
    try:
        vals = [k['_value'] for k in json.loads(sp['speedParam'])['keyframeSets']]
    except (ValueError, KeyError, TypeError):
        raise Unsupported(f'{label}: unreadable speed keyframes')
    if not vals or any(isinstance(v, bool) or v != 1.0 for v in vals):
        raise Unsupported(f'{label}: non-constant or non-1.0 speed {vals}')


def resolve_chain(members, project_info, limits):
    """current timeline -> single audible track -> identity wrapper -> ... -> leaf. Raises Unsupported if any link is unproven."""
    mid = project_info.get('timeline_mediaId')
    outer = [n for n in members if n.endswith('timeline.wesproj') and (f'/{mid}/' in n)]
    if len(outer) != 1:
        raise Unsupported(f'cannot resolve the project timeline member from timeline_mediaId={mid!r}; use --timeline-member/--timeline-id (--inventory lists candidates)')
    member, chain = outer[0], []
    j = members[member][0]
    cur = j.get('currentTimelineId')
    for _ in range(limits['nest_depth']):
        idx = [i for i, t in enumerate(j['timelineInfos']) if t.get('timelineId') == cur]
        if len(idx) != 1:
            raise Unsupported(f'timeline id {cur} not unique in {member}')
        tl = j['timelineInfos'][idx[0]]
        where = f'{member}:timeline {cur}'
        audible = audible_audio_tracks(tl, where)
        if len(audible) != 1:
            raise Unsupported(f'{where}: {len(audible)} audible audio tracks with clips ({audible}); automatic selection needs exactly one (solo/mute routing); select explicitly')
        k = audible[0]
        clips = tl['trackInfos'][k]['clipList']
        wrappers = [c for c in clips if c.get('type') == 16]
        link = dict(member=member, timeline_id=cur, audible_track_index=k)
        if not wrappers:
            if len(chain) == 0:
                others = [t.get('timelineId') for n, (jj, _, _) in members.items() if n.endswith('timeline.wesproj')
                          for t in jj.get('timelineInfos') or [] if t.get('timelineId') != cur and any(tr.get('trackType') == 2 and tr.get('clipList') for tr in t.get('trackInfos') or [])]
                if others:
                    raise Unsupported(f'current timeline {cur} has no nesting proof and other timelines carry audio clips {sorted(set(others))}; select explicitly (--inventory)')
            chain.append(link)
            return member, idx[0], k, chain
        if len(clips) != 1 or len(wrappers) != 1:
            raise Unsupported(f'{where}: the audible track must hold exactly one wrapper clip, found {len(clips)} clips ({len(wrappers)} nested)')
        w = clips[0]
        cp = f'{where}.track[{k}].wrapper'
        for key in ('inPoint', 'outPoint', 'tlBegin', 'tlEnd'):
            if not is_int(w.get(key)) or w[key] < 0:
                raise Unsupported(f'{cp}: {key} must be a non-negative integer tick value, got {w.get(key)!r}')
        if not is_int(w.get('timelineId')):
            raise Unsupported(f'{cp}: missing child timelineId')
        check_speed(w, cp)
        child = w['timelineId']
        all_homes = [(n, i) for n, (jj, _, _) in members.items() if n.endswith('timeline.wesproj') for i, t in enumerate(jj.get('timelineInfos') or []) if t.get('timelineId') == child]
        if not all_homes:
            raise Unsupported(f'nested timeline {child} is not present in the project')
        homes = [h for h in all_homes if h[0] == member] or all_homes
        if len(set(homes)) != 1 and len({timeline_fingerprint(members, n, i) for n, i in homes}) != 1:
            raise Unsupported(f'timeline {child} exists in several members with different content; select explicitly with --timeline-member')
        cm, ci = homes[0]
        dur = timeline_duration(members[cm][0]['timelineInfos'][ci])
        if not (w['inPoint'] == 0 and w['tlBegin'] == 0 and w['outPoint'] == dur and w['tlEnd'] == dur):
            raise Unsupported(f'{cp}: not an identity wrapper (in={w["inPoint"]}, out={w["outPoint"]}, tlBegin={w["tlBegin"]}, tlEnd={w["tlEnd"]}, child duration={dur}); trims/stretches are not flattened')
        others = [h for h in all_homes if h != homes[0]]
        link.update(wrapper=dict(child_timeline_id=child, in_ticks=w['inPoint'], out_ticks=w['outPoint'], tl_begin_ticks=w['tlBegin'], tl_end_ticks=w['tlEnd'], child_duration_ticks=dur, speed='validated constant 1.0, not reversed'),
                    sibling_copies=[dict(member=n, timeline_index=i, identical_track_content=(timeline_fingerprint(members, n, i) == timeline_fingerprint(members, cm, ci)),
                                         clip_ranges_equal=_ranges(members, n, i) == _ranges(members, cm, ci)) for n, i in others])
        chain.append(link)
        member, cur, j = cm, child, members[cm][0]
    raise Unsupported('nesting too deep or cyclic')


def select_track_explicit(tl, track_index):
    cands = [(k, tr) for k, tr in enumerate(tl.get('trackInfos') or []) if tr.get('trackType') == 2 and (tr.get('clipList') or [])]
    if track_index is not None:
        sel = [(k, tr) for k, tr in cands if k == track_index]
        if len(sel) != 1:
            raise Unsupported(f'--track-index {track_index} is not an audio track with clips')
        return sel[0]
    if len(cands) != 1:
        raise Unsupported(f'{len(cands)} audio tracks with clips ({[(k, len(t["clipList"])) for k, t in cands]}); select with --track-index')
    return cands[0]


def validate_clips(clips, rate):
    if rate not in SUPPORTED_RATES:
        raise Unsupported(f'unsupported sample rate {rate!r}; supported {SUPPORTED_RATES}')
    if not clips:
        raise Unsupported('empty clip list')
    ident, prev_tl, prev_out = set(), 0, None
    prev_src_end_sample = 0
    for i, c in enumerate(clips):
        for key in ('inPoint', 'outPoint', 'tlBegin', 'tlEnd'):
            if not is_int(c.get(key)):
                raise Unsupported(f'clip {i}: {key} must be an integer tick value, got {c.get(key)!r}')
        if c.get('type') != 2:
            raise Unsupported(f'clip {i}: unsupported clip type {c.get("type")!r} (only media clips, type 2)')
        if not is_int(c.get('streamId')):
            raise Unsupported(f'clip {i}: streamId must be an integer')
        if not isinstance(c.get('filename'), str) or not c['filename']:
            raise Unsupported(f'clip {i}: missing source filename')
        if not isinstance(c.get('sourceUuid'), str) or not c['sourceUuid']:
            raise Unsupported(f'clip {i}: sourceUuid must be a non-empty string')
        ident.add((c['filename'], c['sourceUuid'], c['streamId']))
        if not (0 <= c['inPoint'] < c['outPoint'] and 0 <= c['tlBegin'] < c['tlEnd']):
            raise Unsupported(f'clip {i}: invalid or reversed range')
        if c['outPoint'] - c['inPoint'] != c['tlEnd'] - c['tlBegin']:
            raise Unsupported(f'clip {i}: source/timeline durations differ')
        if c['tlBegin'] != prev_tl:
            raise Unsupported(f'clip {i}: timeline gap/overlap ({c["tlBegin"] - prev_tl} ticks)')
        if prev_out is not None and c['inPoint'] < prev_out:
            raise Unsupported(f'clip {i}: source goes backwards (reorder/overlap)')
        check_speed(c, f'clip {i}')
        s0, s1 = to_sample(c['inPoint'], rate), to_sample(c['outPoint'], rate)
        t0, t1 = to_sample(c['tlBegin'], rate), to_sample(c['tlEnd'], rate)
        if s1 <= s0 or t1 <= t0:
            raise Unsupported(f'clip {i}: degenerate (zero-frame) interval after conversion to {rate} Hz')
        if s1 - s0 != t1 - t0:
            raise Unsupported(f'clip {i}: source/timeline frame counts differ after rounding ({s1 - s0} vs {t1 - t0})')
        if s0 < prev_src_end_sample:
            raise Unsupported(f'clip {i}: source ranges overlap after rounding')
        prev_tl, prev_out, prev_src_end_sample = c['tlEnd'], c['outPoint'], s1
    if len(ident) != 1:
        raise Unsupported(f'multiple source identities/streams in one track: {sorted(map(str, ident))}')
    return next(iter(ident))


def effect_names(clip):
    return sorted({e['display'] for ch in clip.get('effectChainList') or [] for e in ch.get('effectList') or [] if isinstance(e.get('display'), str) and e['display']})


def build_report(path, sha, members, args):
    check_structure(members)
    info_items = [v for k, v in members.items() if k.endswith('project_info.json')]
    project_info = info_items[0][0] if len(info_items) == 1 else {}
    if args.track_index is not None and not args.timeline_member and args.timeline_id is None:
        raise Unsupported('--track-index requires --timeline-member and/or --timeline-id to identify exactly one timeline; use --inventory first')
    if args.timeline_member or args.timeline_id is not None:
        homes = [(n, i) for n, (jj, _, _) in members.items() if n.endswith('timeline.wesproj') and (not args.timeline_member or n == args.timeline_member)
                 for i, t in enumerate(jj.get('timelineInfos') or []) if args.timeline_id is None or t.get('timelineId') == args.timeline_id]
        if len(homes) != 1:
            raise Unsupported(f'--timeline-member/--timeline-id match {len(homes)} timelines; need exactly one')
        member, ti = homes[0]
        k, track = select_track_explicit(members[member][0]['timelineInfos'][ti], args.track_index)
        chain, association = [dict(selected_explicitly=True)], 'explicit_selector_unverified'
    else:
        member, ti, k, chain = resolve_chain(members, project_info, LIMITS)
        track = members[member][0]['timelineInfos'][ti]['trackInfos'][k]
        association = 'chain_proven_structurally_unverified_against_export_audio'
    tl = members[member][0]['timelineInfos'][ti]
    clips = track['clipList']
    ident = validate_clips(clips, args.sample_rate)
    rate = args.sample_rate
    rows = [dict(index=i, clip_uid=c.get('thisUId'), in_ticks=c['inPoint'], out_ticks=c['outPoint'], tl_begin_ticks=c['tlBegin'], tl_end_ticks=c['tlEnd'],
                 source_start_sample=to_sample(c['inPoint'], rate), source_end_sample_exclusive=to_sample(c['outPoint'], rate),
                 timeline_start_sample=to_sample(c['tlBegin'], rate), timeline_end_sample_exclusive=to_sample(c['tlEnd'], rate), effects=effect_names(c))
            for i, c in enumerate(clips)]
    dels = [dict(after_clip=i - 1, source_from_ticks=clips[i - 1]['outPoint'], source_to_ticks=clips[i]['inPoint'],
                 source_from_sample=rows[i - 1]['source_end_sample_exclusive'], source_to_sample=rows[i]['source_start_sample'])
            for i in range(1, len(clips)) if clips[i]['inPoint'] != clips[i - 1]['outPoint']]
    lead = rows[0]['source_start_sample']
    trail = (args.source_total_samples - rows[-1]['source_end_sample_exclusive']) if args.source_total_samples is not None else None
    if trail is not None and trail < 0:
        raise Unsupported('last clip ends beyond --source-total-samples')
    sums = dict(audio_clips=len(clips), internal_deletions=len(dels),
                timeline_samples=rows[-1]['timeline_end_sample_exclusive'], kept_ticks=sum(c['outPoint'] - c['inPoint'] for c in clips),
                internal_deleted_ticks=sum(d['source_to_ticks'] - d['source_from_ticks'] for d in dels),
                leading_trim_samples=lead, trailing_trim_samples=trail)
    me = members[member]
    return dict(
        schema_version='2.1', status='nominal_edl_requires_native_rate_refinement',
        conventions=dict(interval='half-open [start, end)', ticks_per_second=TICKS, sample_rate_hz=rate, rounding='round half up from exact ticks*rate/ticks_per_second',
                         seconds='display only; use ticks/samples'),
        tool=dict(name='wfp_extract_edl.py', sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        project=dict(path=str(path), sha256=sha, editor=project_info.get('project_editor_name'), editor_version=project_info.get('project_editor_modify_version'),
                     timeline_media_id=project_info.get('timeline_mediaId'), limits=LIMITS),
        selection=dict(timeline_member=member, timeline_member_sha256=me[1], member_compression=me[2], timeline_index=ti, timeline_id=tl.get('timelineId'),
                       track_index=k, track_solo=bool(track.get('solo')), track_mute=bool(track.get('mute')), export_association=association,
                       routing_semantics='standard solo/mute assumption, verified on EP04 only', chain=chain),
        source=dict(filename=ident[0], source_uuid=ident[1], filmora_stream_id=ident[2],
                    note='Filmora streamId is not an FFmpeg stream index; map to the raw container explicitly and verify against decoded audio.',
                    source_total_samples=args.source_total_samples,
                    source_total_samples_provenance='caller_supplied_unverified' if args.source_total_samples is not None else 'unknown'),
        summary=sums, effects_status='unknown_not_verified', effects_seen=sorted({e for r in rows for e in r['effects']}),
        warnings=[], internal_deletions=dels, clips=rows,
        note='Nominal positions are coordinate resolution only (EP04: -27..+26 ms vs the user-accepted refined candidate). Structural checks passing does not verify effects, fades, acoustic alignment, source identity or the export association; this is not a renderer EDL.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project', type=Path)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--inventory', action='store_true')
    ap.add_argument('--sample-rate', type=int, default=48000)
    ap.add_argument('--source-total-samples', type=int)
    ap.add_argument('--timeline-member')
    ap.add_argument('--timeline-id', type=int)
    ap.add_argument('--track-index', type=int)
    a = ap.parse_args(argv)
    try:
        if not a.inventory and a.output is None:
            raise Unsupported('--output is required unless --inventory')
        data, sha = load_archive(a.project, LIMITS)
        members = read_json_members(data, LIMITS)
        if a.inventory:
            check_structure(members)
            print(json.dumps(dict(project_sha256=sha, candidates=timelines_of(members)), ensure_ascii=False, indent=2))
            return 0
        try:
            report = build_report(a.project, sha, members, a)
        except (KeyError, TypeError, AttributeError, ValueError, IndexError) as e:
            raise Unsupported(f'malformed project structure ({type(e).__name__}: {e})')
        if a.output.is_symlink() or os.path.lexists(a.output):
            raise Unsupported(f'refusing to write: {a.output} exists or is a symlink')
        with a.output.open('x', encoding='utf-8') as f:
            f.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(report['summary'], ensure_ascii=False), 'effects_status:', report['effects_status'], 'export_association:', report['selection']['export_association'])
        return 0
    except Unsupported as e:
        print(f'wfp_extract_edl: unsupported/failed: {e}', file=sys.stderr)
        return 2
    except FileExistsError:
        print(f'wfp_extract_edl: output exists: {a.output}', file=sys.stderr)
        return 2
    except OSError as e:
        print(f'wfp_extract_edl: I/O error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
