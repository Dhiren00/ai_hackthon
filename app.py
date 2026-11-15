from pathlib import Path
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from detector.engine import analyze
from detector.assets import checkpoint
from detector.video import VideoError

app = FastAPI(title='PhysioCheck — DeepFakesON-Phys demo')
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
