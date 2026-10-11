#!/usr/bin/env python3
"""Immutable MP3 delivery and measured, explicit loudness-only derivatives."""
import argparse, hashlib, importlib.util, json, math, os, pathlib, shutil, subprocess, tempfile
P = pathlib.Path
ROOT = P(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('legacy_master_compute', ROOT/'podcast-production-workflow/scripts/master_audio_local.py')
legacy = importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
sha256 = legacy.sha256
series_spec = importlib.util.spec_from_file_location('series_audio', P(__file__).with_name('series_audio.py'))
series_audio = importlib.util.module_from_spec(series_spec); series_spec.loader.exec_module(series_audio)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def run(argv):
    return subprocess.run(list(map(str, argv)), check=True, capture_output=True, text=True)

def artifact(path):
    return {'sha256':sha256(path), 'bytes':path.stat().st_size}

def probe(path):
    data=json.loads(run(['ffprobe','-v','error','-select_streams','a:0','-show_streams','-show_format','-of','json',path]).stdout)
    s=data['streams'][0]; f=data['format']; rate=int(s['sample_rate']); channels=int(s['channels'])
    # Count decoded samples, rather than estimating from container duration or codec packets.
    with tempfile.TemporaryFile() as out:
        subprocess.run(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-f','s16le','-acodec','pcm_s16le','-'],stdout=out,stderr=subprocess.PIPE,check=True)
        samples=out.tell()//(2*channels)
    return {'codec':s['codec_name'],'sample_rate':rate,'channels':channels,'sample_count':samples,'duration':samples/rate,'container_duration':float(f.get('duration',samples/rate)), 'bitrate_kbps':int(s.get('bit_rate') or f.get('bit_rate') or 0)/1000,'encoder_delay':'unknown','encoder_padding':'unknown'}

def profile_load(path, profile_id):
    data=json.loads(P(path).read_text()); profile=data['profiles'][profile_id]
    for key in ('target_lufs','tolerance_lu','max_true_peak_dbtp','sample_rates','min_bitrate_kbps'):
        if key not in profile: raise ValueError('profile missing '+key)
    return profile

def qc_checks(before, after, metrics, profile, series):
    expected=before['sample_count']
    checks={'codec':after['codec']=='mp3','sample_rate':after['sample_rate'] in profile['sample_rates'],
            'bitrate':after['bitrate_kbps']>=profile['min_bitrate_kbps'],
            'loudness':abs(metrics['integrated_lufs']-profile['target_lufs'])<=profile['tolerance_lu'],
            'true_peak':metrics['true_peak_dbtp']<=profile['max_true_peak_dbtp'],
            'sample_accounting':after['sample_count']==expected and after['sample_rate']==before['sample_rate']}
    return checks,expected

def cache(output, identity, source):
    report_path=output/'report.json'
    if not output.exists(): return None
    if (output/'report.sha256').read_text().strip()!=sha256(report_path): raise ValueError('cache report integrity mismatch')
    report=json.loads(report_path.read_text())
    required={'delivery.mp3','measurement-before.log','measurement-after.log','encoding.log'}
    if identity['mix']: required.add('mixed-body.wav')
    if identity['series']: required.add('composed.wav'); required.add('timeline.json')
    if identity['source_sample_rate'] not in identity['profile']['sample_rates']: required.add('resampled-input.wav')
    if set(report['outputs'])!=required: raise ValueError('cache required artifact set mismatch')
    if report['identity'] != identity or not report['outputs']: raise ValueError('immutable output collision')
    for name, item in report['outputs'].items():
        if P(name).name != name or artifact(output/name)!=item: raise ValueError('cache artifact changed: '+name)
    observed=probe(output/'delivery.mp3')
    metrics,_=legacy.loudness(output/'delivery.mp3',identity['profile']['target_lufs'],identity['profile']['max_true_peak_dbtp'],50)
    measured_input=probe(output/'composed.wav' if identity['series'] else output/'resampled-input.wav' if identity['source_sample_rate'] not in identity['profile']['sample_rates'] else output/'mixed-body.wav' if identity['mix'] else source)
    verified_checks,_=qc_checks(measured_input,observed,metrics,identity['profile'],identity['series'])
    if observed!=report['output'] or measured_input!=report['input'] or metrics!=report['metrics'] or verified_checks!=report['checks'] or report['qc_status']!=('pass' if all(verified_checks.values()) else 'fail'): raise ValueError('cache measured QC evidence mismatch')
    return report

def produce(source, output, profile_file=None, profile_id='podcast_mp3', mode='encode_only', bitrate=192, peak_headroom=2.0, series_profile=None, mix_manifest=None):
    if (source is None) == (mix_manifest is None): raise ValueError('choose exactly one source or mix manifest')
    source=P(source).resolve() if source is not None else None; output=P(output).resolve()
    profile_file=P(profile_file or ROOT/'podcast-release-package/references/v2/profiles.json')
    profile=profile_load(profile_file,profile_id)
    if mode not in ('encode_only','loudness_only'): raise ValueError('unknown mode')
    if bitrate<profile['min_bitrate_kbps'] or not math.isfinite(peak_headroom) or peak_headroom<0: raise ValueError('invalid encoding options')
    series=series_audio.load_series(series_profile) if series_profile else None
    mix=series_audio.load_mix(mix_manifest) if mix_manifest else None
    if series and 48000 not in profile['sample_rates']: raise ValueError('series timebase incompatible with delivery profile')
    source_hash=sha256(source) if source else None
    identity={'stage':'delivery-v3','source_sample_rate':probe(source)['sample_rate'] if source else 48000,'implementation':sha256(P(__file__)),'series_implementation':sha256(P(__file__).with_name('series_audio.py')),'legacy_compute':sha256(ROOT/'podcast-production-workflow/scripts/master_audio_local.py'),'audio_sha256':source_hash,'series':series,'mix':mix,'profile':profile,'mode':mode,'bitrate':bitrate,'peak_headroom':peak_headroom,'ffmpeg':run(['ffmpeg','-version']).stdout}
    cached=cache(output,identity,source)
    if cached: return cached
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp=P(tempfile.mkdtemp(prefix='.'+output.name+'-',dir=output.parent))
    try:
        original_source=source
        composition=None
        if mix:
            source=tmp/'mixed-body.wav'; series_audio.render_mix(mix,source)
        body_info=probe(source)
        if series:
            body=source; source=tmp/'composed.wav'
            composition=series_audio.compose(body,series,source)
        before=probe(source)
        resampling=None
        if before['sample_rate'] not in profile['sample_rates']:
            input_before_resampling=source; source=tmp/'resampled-input.wav'
            run(['ffmpeg','-v','error','-nostdin','-n','-i',input_before_resampling,'-map','0:a:0','-af',f"aresample={profile['sample_rates'][0]}",'-c:a','pcm_f32le',source])
            resampling={'source':before,'actual_resampled':probe(source),'method':'explicit_ffmpeg_aresample_before_mastering'}
            before=resampling['actual_resampled']
        target_peak=profile['max_true_peak_dbtp']-peak_headroom
        measured,log=legacy.loudness(source,profile['target_lufs'],target_peak,50)
        if not all(math.isfinite(v) for v in measured.values()): raise ValueError('non-finite source loudness')
        (tmp/'measurement-before.log').write_text(log)
        rate=before['sample_rate'] if before['sample_rate'] in profile['sample_rates'] else profile['sample_rates'][0]
        argv=['ffmpeg','-v','info','-nostdin','-n','-i',source,'-map','0:a:0','-vn']
        gain_db=profile['target_lufs']-measured['integrated_lufs']
        if mode=='loudness_only':
            limit=10**(target_peak/20)
            if not 0.0625<=limit<=1: raise ValueError('limiter threshold outside supported range')
            argv+=['-af',f'aresample=192000,volume={gain_db}dB,alimiter=limit={limit}:level=false:latency=true,aresample={rate}']
        argv+=['-ar',str(rate),'-c:a','libmp3lame','-b:a',str(bitrate)+'k',tmp/'delivery.mp3']
        result=run(argv); (tmp/'encoding.log').write_text(result.stderr)
        after=probe(tmp/'delivery.mp3'); metrics,log=legacy.loudness(tmp/'delivery.mp3',profile['target_lufs'],profile['max_true_peak_dbtp'],50)
        (tmp/'measurement-after.log').write_text(log)
        if not all(math.isfinite(v) for v in metrics.values()): raise ValueError('non-finite final loudness')
        checks,expected_samples=qc_checks(before,after,metrics,profile,series)
        if original_source and sha256(original_source)!=identity['audio_sha256']: raise ValueError('input changed during encode')
        series_audio.recheck(series); series_audio.recheck(mix)
        report={'schema_version':'2.0','stage':'delivery','identity':identity,'run_key':digest(identity),'mode':mode,'processing':{'method':'static_gain_oversampled_peak_limiter' if mode=='loudness_only' else 'encode_only','normalization_type':'static_gain_plus_peak_limiting' if mode=='loudness_only' else 'none','gain_db':gain_db if mode=='loudness_only' else 0,'preencode_peak_target_dbtp':target_peak if mode=='loudness_only' else None,'oversample_rate':192000 if mode=='loudness_only' else None,'limiter_latency_compensated':mode=='loudness_only'},'input':before,'output':after,'before_metrics':measured,'metrics':metrics,'checks':checks,'qc_status':'pass' if all(checks.values()) else 'fail','precision':'codec_frame','timeline_changed':False,'limitations':['Source clipping cannot be restored.','Encoder delay/padding unavailable; decoded sample counts are observed.','Oversampled sample limiter approximates true-peak control; only final encoded measurement establishes compliance.'],'outputs':{p.name:artifact(p) for p in tmp.iterdir()}}
        report['schema_version']='3.0'
        report['body_input']=body_info
        report['resampling']=resampling
        report['series_contract']=series
        report['mix_contract']=mix
        report['composition_timeline']=composition
        report['timeline_changed']=bool(series)
        report['final_asr_required']=True
        report['final_chapters_required']=bool(series)
        report['delivery_sha256']=sha256(tmp/'delivery.mp3')
        report['timeline_trusted']=False
        report['sample_accounting_expected']=expected_samples
        report['timeline_verification']='nominal samples accounted; decoded boundary alignment not yet verified'
        if composition:
            composition['body_sha256']=sha256(body)
            composition['composed_sha256']=sha256(source)
            composition['delivery_sha256']=report['delivery_sha256']
            composition['sample_accounting_verified']=checks['sample_accounting']
            composition['mapping_valid_on_decoded_delivery']=False
            write_json(tmp/'timeline.json',composition)
        report['outputs']={p.name:artifact(p) for p in tmp.iterdir()}
        write_json(tmp/'report.json',report)
        (tmp/'report.sha256').write_text(sha256(tmp/'report.json')+'\n')
        # mkdir reservation prevents overwrite including concurrent producers.
        os.mkdir(output)
        try:
            for p in tmp.iterdir(): os.rename(p,output/p.name)
        finally: tmp.rmdir()
        return report
    finally:
        shutil.rmtree(tmp,ignore_errors=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__); inputs=ap.add_mutually_exclusive_group(required=True); inputs.add_argument('--input',type=P); inputs.add_argument('--mix-manifest',type=P); ap.add_argument('--series-profile',type=P); ap.add_argument('--output-dir',type=P,required=True); ap.add_argument('--mode',choices=['encode_only','loudness_only'],default='encode_only'); ap.add_argument('--profile-file',type=P); ap.add_argument('--profile-id',default='podcast_mp3'); ap.add_argument('--bitrate',type=int,default=192); ap.add_argument('--peak-headroom',type=float,default=2.0)
    a=ap.parse_args(); report=produce(a.input,a.output_dir,a.profile_file,a.profile_id,a.mode,a.bitrate,a.peak_headroom,a.series_profile,a.mix_manifest); print(json.dumps({'report':str(a.output_dir/'report.json'),'report_sha256':sha256(a.output_dir/'report.json'),'run_key':report['run_key'],'qc_status':report['qc_status']}))
if __name__=='__main__': main()
