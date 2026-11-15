"""Reproduce the small public-sample comparison. No media is redistributed.
Install requirements-benchmark.txt and FFmpeg before running.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hashlib
import json
import subprocess
import time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, butter, sosfilt
from sklearn.metrics import balanced_accuracy_score, roc_auc_score, confusion_matrix
from detector.assets import ROOT
from detector.audio_assets import setup, REGISTRY
from detector.audio import raw_score

WORK=ROOT/'external'/'audio_benchmark'
SOURCE=WORK/'samples'
DATA_REV='b9680b1c490c6dd6d79f3868db0ff9c66bcfda46'

def prepare():
    WORK.mkdir(parents=True,exist_ok=True)
    if not SOURCE.exists():
        subprocess.run(['git','clone','https://github.com/UniData-NLP/real-vs-fake-human-voice-deepfake-audio.git',str(SOURCE)],check=True)
    subprocess.run(['git','-C',str(SOURCE),'checkout','--detach',DATA_REV],check=True)
    groups=sorted({str(p.parent.relative_to(SOURCE)) for p in SOURCE.rglob('original*')})
    np.random.default_rng(42).shuffle(groups)
    calibration=set(groups[:len(groups)//2])
    records=[]
    (WORK/'decoded').mkdir(exist_ok=True)
    for group in sorted(groups):
        for path in sorted((SOURCE/group).iterdir()):
            if not path.name.startswith(('original','synthetic')): continue
            key=hashlib.sha256(str(path.relative_to(SOURCE)).encode()).hexdigest()[:16]
            wav=WORK/'decoded'/f'{key}.wav'
            if not wav.exists():
                subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-t','6','-ar','16000','-ac','1',str(wav)],check=True)
            records.append({'id':key,'source_path':str(path.relative_to(SOURCE)),'source_group':group,
                            'label':int(path.name.startswith('synthetic')),
                            'split':'calibration' if group in calibration else 'test',
                            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return records

def variants(samples,seed):
    rng=np.random.default_rng(seed)
    rms=float(np.sqrt(np.mean(samples*samples)))
    noise=(samples+rng.normal(0,rms/10,len(samples))).astype(np.float32)
    phone=sosfilt(butter(4,[300,3400],btype='bandpass',fs=16000,output='sos'),samples)
    phone=resample_poly(resample_poly(phone,1,2),2,1)[:len(samples)].astype(np.float32)
    return {'clean':samples,'noise20db':noise,'telephone_band':phone}

def metrics(rows,threshold):
    y=np.array([r['label'] for r in rows]);scores=np.array([r['score'] for r in rows]);pred=scores>=threshold
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'n':len(y),'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
            'accuracy':float(np.mean(y==pred)),'auc':float(roc_auc_score(y,scores)),
            'human_flagged_as_ai':int(fp),'human_count':int(tn+fp),'ai_missed':int(fn),'ai_count':int(tp+fn)}

def summarize(rows):
    cal=[r for r in rows if r['split']=='calibration']
    values=np.unique([r['score'] for r in cal])
    thresholds=np.r_[values[0]-1,values,values[-1]+1]
    threshold=float(max(thresholds,key=lambda t:(metrics(cal,t)['balanced_accuracy'],-abs(t))))
    return {'threshold':threshold,'median_seconds_inference':float(np.median([r['seconds_inference'] for r in rows])),
            'calibration':metrics(cal,threshold),
            'test':{v:metrics([r for r in rows if r['split']=='test' and r['variant']==v],threshold)
                    for v in ['clean','noise20db','telephone_band']}}

if __name__=='__main__':
    setup(list(REGISTRY));records=prepare();results={}
    for name in REGISTRY:
        raw_score(np.ones(96000,dtype=np.float32)*.01,name)
        rows=[]
        for i,record in enumerate(records):
            samples,_=sf.read(WORK/'decoded'/f"{record['id']}.wav",dtype='float32')
            for variant,data in variants(samples,int(record['id'][:8],16)).items():
                start=time.perf_counter();score,_=raw_score(data,name)
                rows.append({**record,'variant':variant,'score':score,'seconds_inference':time.perf_counter()-start})
            if i%16==0:print(name,i,'/',len(records),flush=True)
        results[name]=summarize(rows)
        (WORK/f'{name}_predictions.json').write_text(json.dumps(rows,indent=2))
        (WORK/'results.json').write_text(json.dumps(results,indent=2))
    winner=max(results,key=lambda n:(results[n]['calibration']['balanced_accuracy'],-results[n]['median_seconds_inference']))
    (WORK/'selection.json').write_text(json.dumps({'model':winner,'threshold':results[winner]['threshold']},indent=2))
    print('Selected on calibration only:',winner)
    print(json.dumps(results,indent=2))
