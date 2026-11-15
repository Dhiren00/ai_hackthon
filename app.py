from pathlib import Path
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from detector.engine import analyze
from detector.assets import checkpoint
from detector.video import VideoError

app = FastAPI(title='PhysioCheck — Video and Voice Assessment')
MAX_BYTES = 50 * 1024 * 1024

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
