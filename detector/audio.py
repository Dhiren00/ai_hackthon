"""Local acoustic anti-spoofing inference, with no speech transcription."""
from functools import lru_cache
import importlib.util
from pathlib import Path
import shutil
import subprocess
from threading import Lock
import numpy as np
from .audio_assets import REGISTRY, ROOT, checkpoint, selection

AUDIO_LOCK=Lock()
SAMPLE_RATE=16000
MAX_SECONDS=30

class AudioError(ValueError):
    pass

def decode_audio(path):
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('FFmpeg is required for audio decoding. Install it and add it to PATH.')
    try:
        result=subprocess.run([ffmpeg,'-nostdin','-v','error','-i',str(path),'-t',str(MAX_SECONDS+1),'-vn','-ac','1','-ar',str(SAMPLE_RATE),'-f','f32le','pipe:1'],capture_output=True,timeout=40)
    except subprocess.TimeoutExpired as exc:
        raise AudioError('Audio decoding timed out. Try a shorter recording.') from exc
    if result.returncode != 0:
        raise AudioError('Cannot decode this recording. Upload a valid audio file.')
    samples=np.frombuffer(result.stdout,dtype='<f4').copy()
    if len(samples)<2*SAMPLE_RATE:
        raise AudioError('Use a recording with at least two seconds of speech.')
    if not np.isfinite(samples).all():
        raise AudioError('Audio contains invalid sample values.')
    limited=len(samples)>MAX_SECONDS*SAMPLE_RATE
    samples=samples[:MAX_SECONDS*SAMPLE_RATE]
    if float(np.sqrt(np.mean(samples*samples)))<1e-5:
        raise AudioError('Recording is silent or too quiet to assess.')
    if float(np.max(np.abs(samples)))>2:
        raise AudioError('Audio amplitude is invalid. Export a standard WAV or MP3 recording.')
    return samples,limited

def windows(samples,length):
    if len(samples)==0 or not np.isfinite(samples).all():
        raise AudioError('Audio samples must be non-empty and finite.')
    if len(samples)<length:
        return np.tile(samples,int(np.ceil(length/len(samples))))[:length][None,:].astype(np.float32)
    starts=list(range(0,len(samples)-length+1,length))
    if starts[-1]!=len(samples)-length:
        starts.append(len(samples)-length)
    return np.stack([samples[i:i+length] for i in starts]).astype(np.float32)

@lru_cache(maxsize=4)
def load_audio_model(name):
    import torch
    torch.set_num_threads(2)
    entry=REGISTRY[name]
    architecture='aasist' if name.startswith('AASIST') else 'tssd'
    spec=importlib.util.spec_from_file_location('physiocheck_'+architecture,ROOT/'third_party'/architecture/'model.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if architecture=='aasist':
        model=module.Model(entry['config'])
    else:
        model=module.SSDNet1D() if name=='Res-TSSDNet' else module.DilatedNet()
    state=torch.load(checkpoint(name),map_location='cpu',weights_only=True)
    if architecture=='tssd':
        state=state['model_state_dict']
    model.load_state_dict(state,strict=True)
    return model.eval()

def raw_score(samples,name):
    import torch
    entry=REGISTRY[name]
    inputs=windows(samples,entry['length'])
    model=load_audio_model(name)
    scores=[]
    with torch.inference_mode():
        # Bound inference memory; every segment is inspected.
        for i in range(0,len(inputs),2):
            batch=torch.from_numpy(inputs[i:i+2])
            logits=model(batch) if name.startswith('AASIST') else model(batch.unsqueeze(1))
            if isinstance(logits,tuple):
                logits=logits[1]
            values=(logits[:,1-entry['genuine_index']]-logits[:,entry['genuine_index']]).cpu().numpy()
            scores.extend(float(v) for v in values)
    if not np.isfinite(scores).all():
        raise RuntimeError('Audio model produced an invalid score.')
    return float(np.mean(scores)),len(scores)

def analyze_audio(path):
    samples,limited=decode_audio(path)
    chosen=selection()
    with AUDIO_LOCK:
        value,count=raw_score(samples,chosen['model'])
    is_ai=value>=chosen['threshold']
    return {'model':chosen['model'],'is_ai':bool(is_ai),'verdict':'AI-generated (estimate)' if is_ai else 'Human (estimate)',
            'raw_ai_score':value,'decision_threshold':chosen['threshold'],
            'analyzed_seconds':round(len(samples)/SAMPLE_RATE,3),'segments_analyzed':count,
            'analysis_limit_reached':limited,
            'notice':'Experimental demo only. This model performed poorly on the held-out voice test (50% balanced accuracy on clean recordings). Do not rely on its verdict. Score is not a probability.'}
