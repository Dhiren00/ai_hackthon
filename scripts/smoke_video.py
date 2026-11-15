"""End-to-end transport/inference test, NOT a detector accuracy benchmark.
Uses the upstream illustration to synthesize a short moving-face clip.
No fixture media is committed or presented as genuine benchmark footage.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tempfile
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app import app
from detector.assets import UPSTREAM

with tempfile.TemporaryDirectory() as folder:
    image=cv2.imread(str(UPSTREAM/'images'/'cases_scores.png'))
    if image is None:
        raise RuntimeError('Run python -m detector.assets first.')
    face=image[140:390,350:620]
    face=cv2.resize(face,(320,320))
    path=Path(folder)/'fixture.avi'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),30,(320,320))
    if not writer.isOpened(): raise RuntimeError('MJPG encoder unavailable')
    for i in range(100):
        transform=np.float32([[1,0,2*np.sin(i/8)],[0,1,2*np.cos(i/9)]])
        frame=cv2.warpAffine(face,transform,(320,320),borderMode=cv2.BORDER_REFLECT)
        frame=cv2.convertScaleAbs(frame,alpha=1+0.01*np.sin(i/4))
        writer.write(frame)
    writer.release()
    with path.open('rb') as video:
        response=TestClient(app).post('/analyze',files={'file':('fixture.avi',video,'video/x-msvideo')})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['frames_analyzed']>=60,result
    assert np.isfinite(result['genuine_model_score'])
    print({k:v for k,v in result.items() if k!='timeline'})
