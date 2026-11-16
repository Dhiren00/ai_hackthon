"""Download the MIT-licensed OpenAI GPT-2 output detector for local use."""
import hashlib
import json
from pathlib import Path
import urllib.request
from .assets import ROOT, file_sha256

FOLDER=ROOT/'external'/'text_model'
REGISTRY_PATH=Path(__file__).parent/'text_files.json'

def files():
    registry=json.loads(REGISTRY_PATH.read_text())
    for name,entry in registry.items():
        path=FOLDER/name
        if not path.is_file():
            raise FileNotFoundError('Text model missing. Run: python -m detector.text_assets')
        if file_sha256(path)!=entry['sha256']:
            raise ValueError('Text model file checksum mismatch. Re-run text model setup.')
    return FOLDER

def setup():
    registry=json.loads(REGISTRY_PATH.read_text())
    FOLDER.mkdir(parents=True,exist_ok=True)
    for name,entry in registry.items():
        path=FOLDER/name
        if path.is_file() and file_sha256(path)==entry['sha256']:
            continue
        temp=FOLDER/(name+'.download')
        try:
            with urllib.request.urlopen(entry['url'],timeout=60) as response,temp.open('wb') as target:
                while chunk:=response.read(1024*1024):
                    target.write(chunk)
            if file_sha256(temp)!=entry['sha256']:
                raise ValueError(f'Checksum mismatch: {name}')
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
    print(f'Verified text model: {files()}')

if __name__=='__main__':
    setup()
