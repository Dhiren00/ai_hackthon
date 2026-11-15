"""Fetch free Tesseract language packs; the Tesseract binary is installed separately."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from detector.assets import ROOT

def setup():
    entries=json.loads((ROOT/'detector'/'ocr_files.json').read_text())
    folder=ROOT/'external'/'tessdata'
    folder.mkdir(parents=True,exist_ok=True)
    if all((folder/f).is_file() and hashlib.sha256((folder/f).read_bytes()).hexdigest()==v['sha256'] for f,v in entries['files'].items()):
        print('OCR language packs verified.');return
    with tempfile.TemporaryDirectory(prefix='tessdata-') as temp:
        repo=Path(temp)/'upstream'
        subprocess.run(['git','clone','--filter=blob:none','--no-checkout','https://github.com/tesseract-ocr/tessdata_fast.git',str(repo)],check=True)
        subprocess.run(['git','-C',str(repo),'checkout',entries['revision'],'--',*entries['files']],check=True)
        for name,entry in entries['files'].items():
            source=repo/name
            if hashlib.sha256(source.read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('OCR pack checksum mismatch: '+name)
            shutil.copyfile(source,folder/name)
    print('English, Hindi and Telugu OCR packs verified.')

if __name__=='__main__':setup()
