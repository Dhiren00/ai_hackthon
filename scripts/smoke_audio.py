"""Check actual upload-to-inference execution on a supplied speech file."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app import app
if len(sys.argv)!=2:
    raise SystemExit('Usage: python scripts/smoke_audio.py path/to/speech.wav')
path=Path(sys.argv[1])
with path.open('rb') as audio:
    response=TestClient(app).post('/analyze/audio',files={'file':(path.name,audio)})
assert response.status_code==200,response.text
result=response.json()
assert isinstance(result['is_ai'],bool)
assert result['segments_analyzed']>=1
print(result)
