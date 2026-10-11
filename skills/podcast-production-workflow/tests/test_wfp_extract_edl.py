import contextlib
import copy
import importlib.util
import io
import json
import os
import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

spec = importlib.util.spec_from_file_location('wfp', Path(__file__).resolve().parents[1] / 'scripts' / 'wfp_extract_edl.py')
wfp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wfp)
T = 10_000_000


def speed(v=1.0, rev=False):
    return {'offset': 0, 'offsetEnd': 0, 'reverse': rev, 'speedParam': json.dumps({'keyframeSets': [{'_time': 0, '_value': v}, {'_time': 9, '_value': v}]})}


def clip(i, o, tb, **kw):
    c = {'type': 2, 'inPoint': i * T, 'outPoint': o * T, 'tlBegin': tb * T, 'tlEnd': (tb + o - i) * T, 'streamId': 1, 'filename': 'file://x/raw.mp4',
         'sourceUuid': 'u1', 'thisUId': f'c{i}', 'speed': speed(), 'effectChainList': [{'effectList': [{'display': 'fade'}]}]}
    c.update(kw)
    return c


def leaf(clips, tid=10):
    return {'timelineId': tid, 'trackInfos': [{'trackType': 2, 'clipList': clips}, {'trackType': 1, 'clipList': clips}]}


def duration_of(leaf_tl):
    return max(c['tlEnd'] for tr in leaf_tl['trackInfos'] for c in tr['clipList'])


def wrapper(leaf_tl, **kw):
    d = duration_of(leaf_tl)
    w = {'type': 16, 'timelineId': leaf_tl['timelineId'], 'inPoint': 0, 'outPoint': d, 'tlBegin': 0, 'tlEnd': d, 'speed': speed(), 'streamId': 1, 'filename': ''}
    w.update(kw)
    return w


def project(leaf_tl, outer=True, extra_members=None, wrap=None, outer_track=None, outer_tracks=None):
    members = {}
    if outer:
        w = wrap or wrapper(leaf_tl)
        tr = {'trackType': 2, 'solo': True, 'clipList': [w]}
        tr.update(outer_track or {})
        o = {'timelineId': 9, 'trackInfos': outer_tracks if outer_tracks is not None else [tr]}
        members['ProjectFolder/Medias/AA/timeline.wesproj'] = {'currentTimelineId': 9, 'timelineInfos': [o, leaf_tl]}
    else:
        members['ProjectFolder/Medias/AA/timeline.wesproj'] = {'currentTimelineId': leaf_tl['timelineId'], 'timelineInfos': [leaf_tl]}
    members.update(extra_members or {})
    members['ProjectFolder/project_info.json'] = {'timeline_mediaId': 'AA', 'project_editor_name': 'Filmora'}
    return members


def write_wfp(path, members, raw_overrides=None, compress=ZIP_DEFLATED):
    with ZipFile(path, 'w') as z:
        for n, v in members.items():
            data = (raw_overrides or {}).get(n, json.dumps(v).encode())
            z.writestr(n, data, compress_type=compress)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, members, *args, raw=None, name='p.wfp', out='o.json'):
        p = self.d / name
        write_wfp(p, members, raw)
        o = self.d / out
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = wfp.main([str(p), '--output', str(o), *args])
        return rc, o, err.getvalue()

    def good(self):
        return project(leaf([clip(0, 2, 0), clip(3, 5, 2)]))

    def assertRejected(self, members, *args, **kw):
        rc, o, err = self.run_tool(members, *args, **kw)
        self.assertEqual(rc, 2, err)
        self.assertFalse(o.exists(), 'no EDL may be written on failure')
        self.assertNotIn('Traceback', err)
        return err


class HappyPath(Base):
    def test_extracts_nominal_edl_through_nested_chain(self):
        rc, o, err = self.run_tool(self.good(), '--source-total-samples', '300000')
        self.assertEqual(rc, 0, err)
        r = json.loads(o.read_text())
        self.assertEqual(r['summary']['audio_clips'], 2)
        self.assertEqual(r['summary']['internal_deletions'], 1)
        self.assertEqual(r['summary']['leading_trim_samples'], 0)
        self.assertEqual(r['summary']['trailing_trim_samples'], 300000 - 5 * 48000)
        self.assertEqual(r['effects_status'], 'unknown_not_verified')
        self.assertEqual(r['internal_deletions'][0]['source_from_sample'], 2 * 48000)
        self.assertEqual(r['selection']['chain'][0]['wrapper']['child_timeline_id'], 10)
        self.assertEqual(r['selection']['export_association'], 'chain_proven_structurally_unverified_against_export_audio')
        self.assertEqual(r['source']['source_total_samples_provenance'], 'caller_supplied_unverified')

    def test_half_sample_rounds_up(self):
        m = self.good()
        m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1]['trackInfos'][0]['clipList'][0]['inPoint'] = 0
        self.assertEqual(wfp.to_sample(125, 48000), 1)  # 0.6 sample -> 1
        self.assertEqual(wfp.to_sample(104167, 48000), 500)  # 500.0016
        self.assertEqual(wfp.to_sample(1, 5_000_000), 1)  # exactly 0.5 -> up

    def test_existing_output_and_dangling_symlink_refused(self):
        rc, o, _ = self.run_tool(self.good())
        self.assertEqual(rc, 0)
        rc2, _, err = self.run_tool(self.good())
        self.assertEqual(rc2, 2)
        link = self.d / 'link.json'
        os.symlink(self.d / 'nowhere.json', link)
        rc3, _, err3 = self.run_tool(self.good(), out='link.json')
        self.assertEqual(rc3, 2)
        self.assertFalse((self.d / 'nowhere.json').exists())


class Selection(Base):
    def test_ambiguous_timelines_fail_without_selector(self):
        m = project(leaf([clip(0, 2, 0)]), outer=False)
        extra = leaf([clip(0, 1, 0), clip(2, 4, 1)], tid=11)
        m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'].append(extra)
        err = self.assertRejected(m)
        self.assertIn('select', err)

    def test_equal_length_different_cuts_are_not_same(self):
        m = project(leaf([clip(0, 2, 0), clip(3, 5, 2)]), outer=False)
        m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'].append(leaf([clip(0, 3, 0), clip(4, 6, 3)], tid=11))
        self.assertRejected(m)
        rc, o, err = self.run_tool(m, '--timeline-id', '11', '--timeline-member', 'ProjectFolder/Medias/AA/timeline.wesproj')
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(o.read_text())['selection']['timeline_id'], 11)

    def test_nested_clip_with_offset_is_unsupported(self):
        lf = leaf([clip(0, 2, 0), clip(3, 5, 2)])
        self.assertRejected(project(lf, wrap=wrapper(lf, inPoint=T)))

    def test_duplicate_embedded_timeline_prefers_same_member_and_reports_sibling(self):
        m = self.good()
        sib = copy.deepcopy(m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1])
        sib['trackInfos'][0]['clipList'][0]['thisUId'] = 'different'
        m['ProjectFolder/Medias/BB/timeline.wesproj'] = {'currentTimelineId': 10, 'timelineInfos': [sib]}
        rc, o, err = self.run_tool(m)
        self.assertEqual(rc, 0, err)
        sc = json.loads(o.read_text())['selection']['chain'][0]['sibling_copies']
        self.assertFalse(sc[0]['identical_track_content'])
        self.assertTrue(sc[0]['clip_ranges_equal'])

    def test_cycle_and_missing_nested_timeline_fail(self):
        m = self.good()
        m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][0]['trackInfos'][0]['clipList'][0]['timelineId'] = 99
        self.assertRejected(m)
        m2 = self.good()
        leaf_tl = m2['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1]
        leaf_tl['trackInfos'][0]['clipList'] = [wrapper({'timelineId': 9, 'trackInfos': [{'clipList': [{'tlEnd': T}]}]})]
        self.assertRejected(m2)


class Validation(Base):
    def mutate(self, fn):
        m = self.good()
        fn(m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1]['trackInfos'][0]['clipList'])
        return m

    def test_unsupported_edits_never_succeed(self):
        cases = {
            'speed keyframes 0.5': lambda c: c[0].update(speed=speed(0.5)),
            'mixed speed values': lambda c: c[0].update(speed={'reverse': False, 'speedParam': json.dumps({'keyframeSets': [{'_value': 0.5}, {'_value': 1.5}]})}),
            'reverse': lambda c: c[0].update(speed=speed(1.0, rev=True)),
            'missing speed': lambda c: c[0].pop('speed'),
            'nested clip type': lambda c: c[0].update(type=16),
            'empty filename': lambda c: c[0].update(filename=''),
            'two filenames': lambda c: c[1].update(filename='file://x/other.mp4'),
            'two streams': lambda c: c[1].update(streamId=2),
            'string streamId': lambda c: c[0].update(streamId='1'),
            'None streamId': lambda c: c[0].update(streamId=None),
            'bool tick': lambda c: c[0].update(inPoint=True),
            'float tick': lambda c: c[0].update(inPoint=0.0),
            'missing outPoint': lambda c: c[0].pop('outPoint'),
            'reversed range': lambda c: c[0].update(inPoint=3 * T, outPoint=T),
            'zero length': lambda c: c[0].update(outPoint=0),
            'source goes backwards': lambda c: c[1].update(inPoint=T, outPoint=3 * T),
            'overlapping source': lambda c: c[1].update(inPoint=int(1.5 * T), outPoint=int(3.5 * T)),
            'timeline gap': lambda c: c[1].update(tlBegin=3 * T, tlEnd=5 * T),
            'duration mismatch': lambda c: c[0].update(tlEnd=3 * T),
            'empty list': lambda c: c.clear(),
        }
        for name, fn in cases.items():
            with self.subTest(name):
                self.assertRejected(self.mutate(fn), out=f'{abs(hash(name))}.json')

    def test_sample_rate_validation(self):
        for rate in ('0', '-48000', '12345'):
            with self.subTest(rate):
                self.assertRejected(self.good(), '--sample-rate', rate, out=f'r{rate}.json')

    def test_trailing_trim_cannot_be_negative(self):
        self.assertRejected(self.good(), '--source-total-samples', '1000')


class Wrapper(Base):
    def lf(self):
        return leaf([clip(0, 2, 0), clip(3, 5, 2)])  # child duration 4 s

    def test_wrapper_must_be_identity(self):
        lf = self.lf()
        d = duration_of(lf)
        cases = {
            'trailing trim (out shorter)': wrapper(lf, outPoint=T, tlEnd=T),
            'shorter wrapper': wrapper(lf, outPoint=d - T, tlEnd=d - T),
            'longer wrapper': wrapper(lf, outPoint=d + T, tlEnd=d + T),
            'duration mismatch in/out vs tl': wrapper(lf, tlEnd=d - T),
            'speed 2': wrapper(lf, speed=speed(2.0)),
            'reverse': wrapper(lf, speed=speed(1.0, rev=True)),
            'missing speed': {k: v for k, v in wrapper(lf).items() if k != 'speed'},
            'variable speed': wrapper(lf, speed={'reverse': False, 'speedParam': json.dumps({'keyframeSets': [{'_value': 0.5}, {'_value': 1.5}]})}),
            'negative in': wrapper(lf, inPoint=-1),
            'non-int out': wrapper(lf, outPoint=float(d)),
            'tlBegin offset': wrapper(lf, tlBegin=T, tlEnd=d + T),
        }
        for name, w in cases.items():
            with self.subTest(name):
                self.assertRejected(project(lf, wrap=w), out=f'w{abs(hash(name))}.json')

    def test_two_nesting_levels(self):
        lf = self.lf()
        mid = {'timelineId': 8, 'trackInfos': [{'trackType': 2, 'clipList': [wrapper(lf)]}]}
        d = duration_of(lf)
        o = {'timelineId': 9, 'trackInfos': [{'trackType': 2, 'solo': True, 'clipList': [wrapper(mid, outPoint=d, tlEnd=d)]}]}
        m = {'ProjectFolder/Medias/AA/timeline.wesproj': {'currentTimelineId': 9, 'timelineInfos': [o, mid, lf]},
             'ProjectFolder/project_info.json': {'timeline_mediaId': 'AA'}}
        mid['trackInfos'][0]['clipList'][0]['outPoint'] = d
        rc, out, err = self.run_tool(m)
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(json.loads(out.read_text())['selection']['chain']), 3)


class Routing(Base):
    def lf(self):
        return leaf([clip(0, 2, 0), clip(3, 5, 2)])

    def ordinary(self, **kw):
        t = {'trackType': 2, 'clipList': [clip(0, 4, 0)]}
        t.update(kw)
        return t

    def test_ordinary_solo_track_masks_nested_route(self):
        lf = self.lf()
        nested = {'trackType': 2, 'solo': False, 'clipList': [wrapper(lf)]}
        self.assertRejected(project(lf, outer_tracks=[nested, self.ordinary(solo=True)]))

    def test_additional_audible_track_rejected(self):
        lf = self.lf()
        nested = {'trackType': 2, 'clipList': [wrapper(lf)]}
        self.assertRejected(project(lf, outer_tracks=[nested, self.ordinary()]))

    def test_two_solo_tracks_rejected(self):
        lf = self.lf()
        self.assertRejected(project(lf, outer_tracks=[{'trackType': 2, 'solo': True, 'clipList': [wrapper(lf)]}, self.ordinary(solo=True)]))

    def test_muted_nested_or_leaf_rejected(self):
        lf = self.lf()
        self.assertRejected(project(lf, outer_tracks=[{'trackType': 2, 'mute': True, 'clipList': [wrapper(lf)]}]))
        lf2 = self.lf()
        lf2['trackInfos'][0]['mute'] = True
        self.assertRejected(project(lf2))

    def test_solo_and_mute_conflict_and_string_flags(self):
        lf = self.lf()
        self.assertRejected(project(lf, outer_tracks=[{'trackType': 2, 'solo': True, 'mute': True, 'clipList': [wrapper(lf)]}]))
        self.assertRejected(project(lf, outer_tracks=[{'trackType': 2, 'solo': 'false', 'clipList': [wrapper(lf)]}]), out='s.json')

    def test_ep04_shape_passes_with_other_tracks_unsoloed(self):
        lf = self.lf()
        others = [self.ordinary(), self.ordinary(), {'trackType': 2, 'solo': True, 'clipList': [wrapper(lf)]}]
        rc, o, err = self.run_tool(project(lf, outer_tracks=others))
        self.assertEqual(rc, 0, err)

    def test_explicit_selection_is_labelled_unverified(self):
        m = project(self.lf(), outer=False)
        rc, o, err = self.run_tool(m, '--timeline-id', '10')
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(o.read_text())['selection']['export_association'], 'explicit_selector_unverified')


class TrackSelector(Base):
    def test_track_index_alone_is_rejected(self):
        m = project(leaf([clip(0, 2, 0), clip(3, 5, 2)]), outer=False)
        for idx in ('0', '99'):
            with self.subTest(idx):
                self.assertRejected(m, '--track-index', idx, out=f'ti{idx}.json')

    def test_timeline_plus_valid_track_is_explicit_and_invalid_track_rejected(self):
        m = project(leaf([clip(0, 2, 0), clip(3, 5, 2)]), outer=False)
        rc, o, err = self.run_tool(m, '--timeline-id', '10', '--track-index', '0')
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(o.read_text())['selection']['export_association'], 'explicit_selector_unverified')
        self.assertRejected(m, '--timeline-id', '10', '--track-index', '99', out='bad.json')


class Shapes(Base):
    def test_non_object_roots_and_shapes_give_structured_errors(self):
        self.assertRejected(self.good(), raw={'ProjectFolder/Medias/AA/timeline.wesproj': b'[1,2]'})
        m = self.good()
        m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1]['trackInfos'][0]['clipList'][0]['effectChainList'] = [3]
        err = self.assertRejected(m, out='e.json')
        self.assertIn('effectChainList', err)
        m2 = self.good()
        m2['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1]['trackInfos'][0] = 'x'
        self.assertRejected(m2, out='t.json')

    def test_source_uuid_required(self):
        for bad in (None, [], ''):
            m = self.good()
            m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1]['trackInfos'][0]['clipList'][0]['sourceUuid'] = bad
            self.assertRejected(m, out=f'u{abs(hash(str(bad)))}.json')

    def test_sub_sample_and_rounding_phase_rejected(self):
        m = self.good()
        c = m['ProjectFolder/Medias/AA/timeline.wesproj']['timelineInfos'][1]['trackInfos'][0]['clipList']
        c[0]['outPoint'] = c[0]['inPoint'] + 1
        c[0]['tlEnd'] = c[0]['tlBegin'] + 1
        c[1]['tlBegin'] = c[0]['tlEnd']
        c[1]['tlEnd'] = c[1]['tlBegin'] + (c[1]['outPoint'] - c[1]['inPoint'])
        self.assertRejected(m)


class Archive(Base):
    def test_corrupt_json_and_not_a_zip(self):
        m = self.good()
        self.assertRejected(m, raw={'ProjectFolder/Medias/AA/timeline.wesproj': b'{not json'})
        p = self.d / 'bad.wfp'
        p.write_bytes(b'not a zip')
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = wfp.main([str(p), '--output', str(self.d / 'x.json')])
        self.assertEqual(rc, 2)

    def test_member_and_total_limits_fail_closed(self):
        m = self.good()
        old = dict(wfp.LIMITS)
        try:
            wfp.LIMITS['json_member_bytes'] = 10
            self.assertRejected(m)
            wfp.LIMITS.update(old)
            wfp.LIMITS['total_json_bytes'] = 300
            self.assertRejected(m, out='t.json')
            wfp.LIMITS.update(old)
            wfp.LIMITS['archive_bytes'] = 10
            self.assertRejected(m, out='a.json')
        finally:
            wfp.LIMITS.update(old)

    def test_oversized_project_info_is_checked_too(self):
        m = self.good()
        old = dict(wfp.LIMITS)
        try:
            wfp.LIMITS['json_member_bytes'] = 60
            m['ProjectFolder/project_info.json']['pad'] = 'x' * 100
            self.assertRejected(m)
        finally:
            wfp.LIMITS.update(old)

    def test_duplicate_member_names_rejected(self):
        p = self.d / 'dup.wfp'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with ZipFile(p, 'w') as z:
                z.writestr('ProjectFolder/project_info.json', '{}')
                z.writestr('ProjectFolder/project_info.json', '{}')
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = wfp.main([str(p), '--output', str(self.d / 'x.json')])
        self.assertEqual(rc, 2)
        self.assertIn('duplicate', err.getvalue())

    def test_stored_and_deflated_both_read(self):
        for comp in (ZIP_STORED, ZIP_DEFLATED):
            p = self.d / f'c{comp}.wfp'
            write_wfp(p, self.good(), compress=comp)
            with contextlib.redirect_stdout(io.StringIO()):
                rc = wfp.main([str(p), '--output', str(self.d / f'c{comp}.json')])
            self.assertEqual(rc, 0)

    def test_inventory_writes_nothing(self):
        p = self.d / 'i.wfp'
        write_wfp(p, self.good())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = wfp.main([str(p), '--inventory'])
        self.assertEqual(rc, 0)
        self.assertIn('candidates', buf.getvalue())
        self.assertEqual(sorted(x.name for x in self.d.iterdir()), ['i.wfp'])


if __name__ == '__main__':
    unittest.main()
