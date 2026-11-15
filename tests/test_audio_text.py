"""Input failures and actual pretrained inference; no mocked predictions."""
import io
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app import app
from detector.audio import AudioError, decode_audio, windows, raw_score, analyze_audio
from detector.audio_assets import selection
from detector.text import analyze_text, TextError

client=TestClient(app)

def test_audio_windows_include_tail():
    samples=np.arange(13,dtype=np.float32)
    assert windows(samples,6).tolist()==[list(range(6)),list(range(6,12)),list(range(7,13))]
    assert windows(np.array([1,2],np.float32),5).tolist()==[[1,2,1,2,1]]
    with pytest.raises(AudioError): windows(np.array([],np.float32),6)

def test_audio_invalid_uploads():
    assert client.post('/analyze/audio',files={'file':('x.txt',b'no')}).status_code==400
    assert client.post('/analyze/audio',files={'file':('x.wav',b'')}).status_code==400
    assert client.post('/analyze/audio',files={'file':('x.mp3',b'invalid audio')}).status_code==422

def test_silent_audio_rejected(tmp_path):
    path=tmp_path/'silent.wav'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','3',str(path)],check=True)
    with pytest.raises(AudioError,match='silent'):
        decode_audio(path)

def test_audio_actual_model_is_deterministic():
    samples=np.random.default_rng(42).normal(0,.1,96000).astype(np.float32)
    name=selection()['model']
    first,n=raw_score(samples,name);second,_=raw_score(samples,name)
    assert np.isfinite(first) and first==second and n==1

def test_short_text_rejected():
    assert client.post('/analyze/text',json={'text':'short input'}).status_code==422
    assert client.post('/analyze/text',json={'text':'a'*20001}).status_code==422

def test_text_actual_checkpoint():
    text=('This is a test passage describing a classroom experiment with several observations and a written record. '*6)
    result=client.post('/analyze/text',json={'text':text})
    assert result.status_code==200,result.text
    data=result.json()
    assert isinstance(data['is_ai'],bool)
    assert 0<=data['model_ai_score']<=1
    assert data['tokens_analyzed']>0 and 'GPT-2' in data['notice']

def test_home_has_one_unified_input():
    html=client.get('/').text
    assert html.count('<textarea')==1
    assert 'id="file"' in html
    assert 'id="language"' in html
    assert 'data-mode=' not in html
