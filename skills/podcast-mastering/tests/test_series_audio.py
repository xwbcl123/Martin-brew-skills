import importlib.util
import json
from pathlib import Path
import subprocess
import array
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('master', Path(__file__).parents[1]/'scripts/mastering.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
s = m.series_audio

class SeriesTests(unittest.TestCase):
    def audio(self, path, seconds=3, rate=48000, frequency=440):
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',
                        f'sine=frequency={frequency}:duration={seconds}',
                        '-ar',str(rate),'-ac','2','-c:a','pcm_s16le',str(path)],check=True)

    def profile(self, d):
        self.audio(d/'theme.wav')
        entry=dict(path='theme.wav',sha256=s.sha(d/'theme.wav'),sample_rate=48000,samples=144000)
        data=dict(schema_version='1.0',series_id='fixture',intro_required=True,outro_required=True,
                  intro=entry.copy(),outro=entry.copy())
        path=d/'series.json'; path.write_text(json.dumps(data)); return path,data

    def test_bookends_actual_pcm_mp3_timeline_and_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); profile,data=self.profile(d); self.audio(d/'body.wav',seconds=4,frequency=900)
            r=m.produce(d/'body.wav',d/'out',mode='loudness_only',series_profile=profile)
            self.assertEqual(r['qc_status'],'pass')
            self.assertEqual(r['output']['sample_count'],480000)
            self.assertFalse(r['timeline_trusted']); self.assertTrue(r['checks']['sample_accounting'])
            t=json.loads((d/'out/timeline.json').read_text())
            self.assertEqual(t['body_offset_samples'],144000)
            self.assertEqual([x['role'] for x in t['segments']],['intro','body','outro'])
            self.assertEqual(t['delivery_sha256'],s.sha(d/'out/delivery.mp3'))
            self.assertEqual(m.produce(d/'body.wav',d/'out',mode='loudness_only',series_profile=profile)['run_key'],r['run_key'])
            (d/'theme.wav').write_bytes(b'changed')
            with self.assertRaises(ValueError):m.produce(d/'body.wav',d/'out',mode='loudness_only',series_profile=profile)

    def test_reject_missing_escape_and_observed_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); profile,data=self.profile(d)
            for change in ('escape','length','required','missing'):
                bad=json.loads(json.dumps(data))
                if change=='escape':bad['intro']['path']='../outside.wav'
                elif change=='length':bad['intro']['samples']=48000
                elif change=='required':bad['outro_required']=False
                else:del bad['outro']
                profile.write_text(json.dumps(bad))
                with self.assertRaises((ValueError,KeyError)):s.load_series(profile)

    def test_mix_explicit_matrix_and_unequal_clock_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);self.audio(d/'a.wav',seconds=4);self.audio(d/'b.wav',seconds=4,frequency=1000)
            tracks=[dict(path=n,sha256=s.sha(d/n),matrix=[[.5,0],[0,.5]]) for n in ('a.wav','b.wav')]
            manifest=d/'mix.json';manifest.write_text(json.dumps(dict(schema_version='1.0',tracks=tracks)))
            r=m.produce(None,d/'out',mode='loudness_only',mix_manifest=manifest)
            self.assertEqual(r['qc_status'],'pass');self.assertEqual(r['output']['sample_count'],192000)
            # A shorter route must fail before any silence-padding mix can conceal it.
            self.audio(d/'short.wav',seconds=3)
            tracks[1].update(path='short.wav',sha256=s.sha(d/'short.wav'))
            manifest.write_text(json.dumps(dict(schema_version='1.0',tracks=tracks)))
            with self.assertRaisesRegex(ValueError,'unequal'):s.load_mix(manifest)
            self.assertFalse((d/'other').exists())

    def test_cache_rejects_forged_report_and_missing_delivery(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); self.audio(d/'body.wav',seconds=4)
            m.produce(d/'body.wav',d/'out',mode='loudness_only')
            path=d/'out/report.json'; original=path.read_text(); r=json.loads(original)
            r['qc_status']='fail'; path.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'integrity'): m.produce(d/'body.wav',d/'out',mode='loudness_only')
            r=json.loads(original); del r['outputs']['delivery.mp3']; path.write_text(json.dumps(r))
            (d/'out/report.sha256').write_text(s.sha(path)+'\n'); (d/'out/delivery.mp3').unlink()
            with self.assertRaisesRegex(ValueError,'required artifact'): m.produce(d/'body.wav',d/'out',mode='loudness_only')

    def test_float_intermediates_preserve_over_full_scale(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','aevalsrc=0.75*sin(2*PI*440*t):d=4',
                            '-ar','48000','-ac','2','-c:a','pcm_f32le',str(d/'a.wav')],check=True)
            tracks=[dict(path='a.wav',sha256=s.sha(d/'a.wav'),matrix=[[1,0],[0,1]]) for _ in range(2)]
            manifest=d/'mix.json'; manifest.write_text(json.dumps(dict(schema_version='1.0',tracks=tracks)))
            s.render_mix(s.load_mix(manifest),d/'mixed.wav')
            def peak(path):
                raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-'])
                values=array.array('f'); values.frombytes(raw); return max(map(abs,values))
            self.assertGreater(peak(d/'mixed.wav'),1)
            self.assertAlmostEqual(peak(d/'mixed.wav'),2*peak(d/'a.wav'),places=5)
            profile,data=self.profile(d); data['intro']['gain_db']=30; data['outro']['gain_db']=30
            profile.write_text(json.dumps(data)); s.compose(d/'a.wav',s.load_series(profile),d/'composed.wav')
            self.assertGreater(peak(d/'composed.wav'),1)
            self.assertAlmostEqual(peak(d/'composed.wav'),peak(d/'theme.wav')*10**(30/20),places=4)
            self.assertEqual(m.probe(d/'composed.wav')['codec'],'pcm_f32le')
            result=m.produce(None,d/'out',mode='loudness_only',mix_manifest=manifest)
            self.assertEqual(result['qc_status'],'pass'); self.assertLess(result['metrics']['true_peak_dbtp'],0)

    def test_resampling_accounts_for_new_clock(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); self.audio(d/'body.wav',seconds=4,rate=32000)
            r=m.produce(d/'body.wav',d/'out',mode='loudness_only')
            self.assertEqual(r['qc_status'],'pass'); self.assertEqual(r['output']['sample_count'],176400)
            self.assertEqual(r['sample_accounting_expected'],176400)
            source=d/'fractional.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=32000',
                            '-af','atrim=end_sample=128001','-c:a','pcm_s16le',str(source)],check=True)
            r=m.produce(source,d/'fractional-out',mode='loudness_only')
            self.assertEqual(r['body_input']['sample_count'],128001)
            self.assertEqual(r['input']['sample_count'],176402)
            self.assertEqual(r['output']['sample_count'],176402)
            self.assertEqual(r['qc_status'],'pass')
            self.assertEqual(m.produce(source,d/'fractional-out',mode='loudness_only')['qc_status'],'pass')

if __name__=='__main__':unittest.main()
