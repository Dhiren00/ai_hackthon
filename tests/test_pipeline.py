import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app import app
from detector.video import preprocess, extract_faces, VideoError
from detector.engine import load_model

client = TestClient(app)

def test_static_frames_are_finite():
    for value in [0,100,255]:
        x=np.full((60,36,36,3),value,dtype=np.float32)
        motion,raw,idx=preprocess(x,np.arange(60))
        assert motion.shape == raw.shape == (59,3,36,36)
        assert np.isfinite(motion).all() and np.isfinite(raw).all()
        assert not motion.any() and not raw.any()

def test_png_roundtrip(tmp_path):
    x=np.random.default_rng(12).integers(0,256,(30,36,36,3)).astype(np.float32)
    motion,raw,_=preprocess(x,np.arange(30))
    diff=(x[1:]-x[:-1])/np.maximum(x[1:]+x[:-1],1e-6)
    normalized=(diff-diff.mean(0))/(diff.std(0)+0.1)
    path=str(tmp_path/'frame.png')
    cv2.imwrite(path,np.mod(np.trunc(normalized[5]),256).astype(np.uint8))
    assert np.array_equal(motion[5],cv2.imread(path).transpose(2,0,1))

def test_missed_detections_not_joined():
    _,_,indices=preprocess(np.ones((4,36,36,3),np.float32),np.array([0,1,5,6]))
    assert indices.tolist()==[0,5]

def test_upload_errors():
    assert client.get('/').status_code==200
    assert client.post('/analyze',files={'file':('bad.txt',b'x')}).status_code==400
    assert client.post('/analyze',files={'file':('empty.mp4',b'')}).status_code==400
    assert client.post('/analyze',files={'file':('bad.mp4',b'not a video')}).status_code==422

def test_no_face_rejected(tmp_path):
    path=tmp_path/'blank.avi'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),30,(128,128))
    for _ in range(90): writer.write(np.zeros((128,128,3),np.uint8))
    writer.release()
    with pytest.raises(VideoError,match='frontal face'):
        extract_faces(path)

@pytest.mark.parametrize('name',['CelebDF_V2','DFDC_Preview'])
def test_actual_checkpoint_inference(name):
    model=load_model(name)
    x=np.random.default_rng(1).uniform(0,255,(3,3,36,36)).astype(np.float32)
    result=model([x,x],training=False).numpy()
    assert result.shape==(3,1)
    assert np.isfinite(result).all()
    assert ((result>=0)&(result<=1)).all()
