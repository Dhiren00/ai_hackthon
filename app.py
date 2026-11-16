from pathlib import Path
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from detector.assets import checkpoint
from detector.video import VideoError

from contextlib import asynccontextmanager
from detector.workflow import JobManager, BusyError, SPEC

@asynccontextmanager
async def lifespan(app):
    app.state.jobs=JobManager()
    try:
        yield
    finally:
        await run_in_threadpool(app.state.jobs.shutdown)

app = FastAPI(title='S.H.I.E.L.D. — Unified media assessment',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
MAX_BYTES = 50 * 1024 * 1024

@app.middleware('http')
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.get('/')
def home():
    return FileResponse(Path(__file__).parent / 'static' / 'index.html')

@app.get('/health')
def health():
    try:
        checkpoint()
        return {'status':'ready','model_files_verified':True}
    except (FileNotFoundError,ValueError) as exc:
        return {'status':'setup_required','detail':str(exc)}

@app.post('/analyze')
async def analyze_video(file: UploadFile = File(...)):
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.mp4','.avi','.mov','.mkv','.webm'}:
        await file.close()
        raise HTTPException(400,'Upload an MP4, AVI, MOV, MKV or WebM video.')
    try:
        with tempfile.TemporaryDirectory(prefix='physiocheck-') as folder:
            path = Path(folder) / ('upload'+suffix)
            size = 0
            with path.open('wb') as output:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(413,'Maximum upload size is 50 MB.')
                    output.write(chunk)
            if not size:
                raise HTTPException(400,'The uploaded file is empty.')
            from detector.engine import analyze
            return await run_in_threadpool(analyze,path)
    except VideoError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (FileNotFoundError,ValueError) as exc:
        raise HTTPException(503,str(exc)) from exc
    finally:
        await file.close()


@app.post('/analyze/audio')
async def analyze_recording(file: UploadFile = File(...)):
    from detector.audio import analyze_audio, AudioError
    suffix = Path(file.filename or '').suffix.lower()
    try:
        if suffix not in {'.wav','.mp3','.flac','.ogg','.m4a','.aac','.webm','.mp4'}:
            raise HTTPException(400,'Upload a WAV, MP3, FLAC, OGG, M4A, AAC, WebM or MP4 recording.')
        with tempfile.TemporaryDirectory(prefix='physiocheck-audio-') as folder:
            path = Path(folder) / ('upload'+suffix)
            size = 0
            with path.open('wb') as output:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(413,'Maximum upload size is 50 MB.')
                    output.write(chunk)
            if not size:
                raise HTTPException(400,'The uploaded file is empty.')
            return await run_in_threadpool(analyze_audio,path)
    except AudioError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (FileNotFoundError,ValueError,RuntimeError) as exc:
        raise HTTPException(503,str(exc)) from exc
    finally:
        await file.close()


from pydantic import BaseModel, Field

class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=20000)

@app.post('/analyze/text')
async def analyze_writing(body: TextInput):
    from detector.text import analyze_text, TextError
    try:
        return await run_in_threadpool(analyze_text,body.text)
    except TextError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (FileNotFoundError,ValueError,RuntimeError) as exc:
        raise HTTPException(503,str(exc)) from exc


@app.post('/api/jobs',status_code=202)
async def create_job(request: Request, text: str = Form(''), file: UploadFile | None = File(None)):
    text=text.strip()
    folder=None
    try:
        if bool(text)==bool(file):
            raise HTTPException(422,detail={'code':'choose_one'})
        if len(text)>20000:
            raise HTTPException(422,detail={'code':'text_large'})
        path=None
        if file:
            folder=tempfile.mkdtemp(prefix='physiocheck-job-')
            suffix=Path(file.filename or '').suffix.lower()
            allowed={'.txt','.png','.jpg','.jpeg','.webp','.gif','.bmp','.mp4','.mov','.avi','.mkv','.webm','.wav','.mp3','.flac','.m4a','.aac','.ogg'}
            path=Path(folder)/('input'+(suffix if suffix in allowed else '.bin'))
            size=0
            with path.open('wb') as target:
                while chunk:=await file.read(1024*1024):
                    size+=len(chunk)
                    if size>MAX_BYTES:
                        raise HTTPException(413,detail={'code':'file_large'})
                    target.write(chunk)
            if not size:
                raise HTTPException(422,detail={'code':'empty_file'})
        key=request.app.state.jobs.submit(path,text,folder)
        folder=None  # The worker owns cleanup after successful submission.
        return {'id':key,'status':'queued','poll_url':'/api/jobs/'+key}
    except BusyError as exc:
        raise HTTPException(429,detail={'code':'queue_full'}) from exc
    finally:
        if file:await file.close()
        if folder:
            import shutil
            shutil.rmtree(folder,ignore_errors=True)

@app.get('/api/jobs/{key}')
def get_job(key: str,request: Request):
    result=request.app.state.jobs.get(key)
    if result is None:
        raise HTTPException(404,detail={'code':'job_expired'})
    return result

@app.get('/api/workflow')
def workflow_definition():
    return SPEC

@app.get('/api/health')
def readiness():
    import shutil
    from detector.assets import ROOT
    from detector.audio_assets import selection
    from detector.text_assets import REGISTRY_PATH
    import json
    components={
        'scam':(ROOT/'detector'/'scam_model.json').is_file(),
        'ffmpeg':bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),
        'tesseract':bool(shutil.which('tesseract')),
        'video':(ROOT/'external'/'DeepFakesON-Phys'/'pretrained models'/'DeepFakesON-Phys_CelebDF_V2.h5').is_file(),
        'voice':(ROOT/'external'/'audio_weights'/(selection()['model']+'.pth')).is_file(),
        'text':all((ROOT/'external'/'text_model'/name).is_file() for name in json.loads(REGISTRY_PATH.read_text())),
        'ocr_packs':all((ROOT/'external'/'tessdata'/(lang+'.traineddata')).is_file() for lang in ['eng','hin','tel']),
    }
    return {'status':'files_present' if all(components.values()) else 'setup_required','components':components,
            'note':'File presence check only; inference is verified by tests.'}
