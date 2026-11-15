"""Actual content routing, OCR, status transitions and failure handling."""
import io
import json
import subprocess
import textwrap
import time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import pytest
from fastapi.testclient import TestClient
from app import app
from detector.ingest import identify,extract_screenshot,text_language,InputError
from detector.workflow import run_flow,JobManager,BusyError

PASSAGE=('The students recorded their observations in a notebook during the afternoon lesson. '
         'They compared the temperature of water in several containers and discussed why the measurements changed. '
         'Each group repeated the experiment carefully before sharing its results with the class. '
         'The teacher asked everyone to explain the evidence and describe one improvement for the next experiment.')

def screenshot(text=PASSAGE,font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
    image=Image.new('RGB',(1200,650),'white')
    draw=ImageDraw.Draw(image);chosen=ImageFont.truetype(font,26)
    y=35
    for line in textwrap.wrap(text,75):
        draw.text((35,y),line,font=chosen,fill='black');y+=45
    data=io.BytesIO();image.save(data,format='PNG');return data.getvalue()

def wait_job(client,key):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        response=client.get('/api/jobs/'+key);assert response.status_code==200
        job=response.json()
        if job['status'] in {'completed','failed'}:return job
        time.sleep(.05)
    pytest.fail('Workflow did not complete within 90 seconds')

def test_pasted_text_job_runs_real_model():
    with TestClient(app) as client:
        response=client.post('/api/jobs',data={'text':PASSAGE})
        assert response.status_code==202,response.text
        job=wait_job(client,response.json()['id'])
        assert job['status']=='completed',job
        assert job['result']['kind']=='text'
        assert isinstance(job['result']['is_ai'],bool)
        assert job['history']==['queued','identify','analyse','complete']

def test_screenshot_job_uses_ocr_and_text_model():
    with TestClient(app) as client:
        response=client.post('/api/jobs',files={'file':('notes.png',screenshot(),'image/png')})
        job=wait_job(client,response.json()['id'])
        assert job['status']=='completed',job
        assert job['result']['kind']=='screenshot'
        assert 'observations' in job['result']['extracted_text'].lower()
        assert job['history']==['queued','identify','extract','analyse','complete']
        assert isinstance(job['result']['is_ai'],bool)

def test_media_container_is_inspected_not_extension(tmp_path):
    # Real WAV container, deceptive .mp4 name: it must route to voice.
    path=tmp_path/'recording.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=250:sample_rate=16000','-t','3','-f','wav',str(path)],check=True)
    assert identify(path)=='audio'
    stages=[];result=run_flow(path=path,progress=stages.append)
    assert result['kind']=='audio' and isinstance(result['is_ai'],bool)
    assert stages==['identify','analyse','complete']

def test_video_route_uses_real_model(tmp_path):
    import cv2
    import numpy as np
    from detector.assets import UPSTREAM
    image=cv2.imread(str(UPSTREAM/'images'/'cases_scores.png'))[140:390,350:620]
    image=cv2.resize(image,(320,320));path=tmp_path/'face.avi'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),30,(320,320))
    assert writer.isOpened()
    for i in range(100):
        matrix=np.float32([[1,0,2*np.sin(i/8)],[0,1,2*np.cos(i/9)]])
        frame=cv2.warpAffine(image,matrix,(320,320),borderMode=cv2.BORDER_REFLECT)
        writer.write(cv2.convertScaleAbs(frame,alpha=1+.01*np.sin(i/4)))
    writer.release()
    assert identify(path)=='video'
    result=run_flow(path=path)
    assert result['kind']=='video' and result['frames_analyzed']>=60

def test_invalid_file_fails_without_a_verdict():
    with TestClient(app) as client:
        response=client.post('/api/jobs',files={'file':('fake.png',b'not an image','image/png')})
        job=wait_job(client,response.json()['id'])
        assert job['status']=='failed' and job['error']['code']=='invalid_file'
        assert job['result'] is None
        # A failure must not poison the worker for subsequent requests.
        new=client.post('/api/jobs',data={'text':PASSAGE})
        assert wait_job(client,new.json()['id'])['status']=='completed'

def test_ambiguous_empty_and_expired_inputs():
    with TestClient(app) as client:
        assert client.post('/api/jobs').status_code==422
        assert client.post('/api/jobs',data={'text':PASSAGE},files={'file':('a.txt',b'hi')}).status_code==422
        assert client.post('/api/jobs',files={'file':('a.txt',b'')}).status_code==422
        assert client.get('/api/jobs/not-a-job').status_code==404

@pytest.mark.parametrize('text,language',[
    ('यह हिन्दी में लिखा हुआ वाक्य है। हमें भाषा की सही जानकारी देनी चाहिए।','hi'),
    ('ఇది తెలుగులో రాసిన వాక్యం. సరైన భాషను గుర్తించడం అవసరం.','te'),
])
def test_non_english_text_is_not_given_a_fabricated_ai_score(text,language):
    with TestClient(app) as client:
        response=client.post('/api/jobs',data={'text':text})
        job=wait_job(client,response.json()['id'])
        assert job['status']=='completed'
        assert job['result']['language']==language
        assert job['result']['is_ai'] is None
        assert job['result']['verdict_key']=='unsupported_language'

@pytest.mark.parametrize('text,font,script',[
    ('यह एक हिन्दी वाक्य है। यह स्क्रीनशॉट पढ़ने की जाँच है।','/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf','hi'),
    ('ఇది తెలుగు వాక్యం. ఇది స్క్రీన్‌షాట్ చదవడానికి ఒక పరీక్ష.','/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf','te'),
])
def test_hindi_and_telugu_screenshot_extraction(tmp_path,text,font,script):
    path=tmp_path/'screen.png';path.write_bytes(screenshot(text,font))
    extracted=extract_screenshot(path)
    assert text_language(extracted)==script,extracted

def test_locale_keys_and_workflow_are_complete():
    with TestClient(app) as client:
        locales=client.get('/static/i18n.json').json()
        assert set(locales)=={'en','hi','te'}
        assert set(locales['en'])==set(locales['hi'])==set(locales['te'])
        assert all(all(values.values()) for values in locales.values())
        definition=client.get('/api/workflow').json()
        assert set(definition['routes'])=={'text','screenshot','audio','video'}
        assert client.get('/api/health').status_code==200

def test_blank_screenshot_fails_cleanly():
    image=Image.new('RGB',(400,300),'white');data=io.BytesIO();image.save(data,format='PNG')
    with TestClient(app) as client:
        response=client.post('/api/jobs',files={'file':('blank.png',data.getvalue())})
        job=wait_job(client,response.json()['id'])
        assert job['status']=='failed' and job['error']['code']=='ocr_empty'
        assert job['result'] is None

def test_queue_capacity_and_cleanup(monkeypatch,tmp_path):
    from threading import Event
    import detector.workflow as workflow
    entered=Event();release=Event()
    def blocked(*args,**kwargs):
        entered.set();release.wait(10)
        raise FileNotFoundError('missing model fixture')
    monkeypatch.setattr(workflow,'run_flow',blocked)
    manager=JobManager();folders=[]
    try:
        keys=[]
        for i in range(4):
            folder=tmp_path/str(i);folder.mkdir();folders.append(folder)
            keys.append(manager.submit(text=PASSAGE,folder=folder))
        assert entered.wait(2)
        with pytest.raises(BusyError):manager.submit(text=PASSAGE)
        release.set();manager.shutdown()
        assert all(manager.get(key)['status']=='failed' for key in keys)
        assert all(manager.get(key)['error']['code']=='model_missing' for key in keys)
        assert all(not folder.exists() for folder in folders)
        manager.jobs[keys[0]]['_updated']-=901
        assert manager.get(keys[0]) is None
    finally:
        release.set();manager.shutdown()
