"""Pinned, checksum-verified public checkpoints; no API keys required."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from .assets import ROOT

REGISTRY = json.loads((Path(__file__).parent / 'audio_models.json').read_text())
SELECTION = Path(__file__).parent / 'audio_selection.json'

def selection():
    return json.loads(SELECTION.read_text())

def checkpoint(name):
    if name not in REGISTRY:
        raise ValueError('Unknown audio model')
    path = ROOT / 'external' / 'audio_weights' / (name + '.pth')
    if not path.is_file():
        raise FileNotFoundError('Audio model missing. Run: python -m detector.audio_assets')
    expected = REGISTRY[name]['sha256']
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Audio checkpoint checksum mismatch. Re-run audio model setup.')
    return path

def setup(names):
    folder = ROOT / 'external' / 'audio_weights'
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        if name not in REGISTRY:
            raise ValueError('Unknown audio model')
        try:
            checkpoint(name)
            print(f'Already verified: {name}')
            continue
        except (FileNotFoundError,ValueError):
            pass
        entry = REGISTRY[name]
        with tempfile.TemporaryDirectory(prefix='audio-model-') as temp:
            source = Path(temp) / 'upstream'
            subprocess.run(['git','clone',entry['repository'],str(source)],check=True)
            subprocess.run(['git','-C',str(source),'checkout','--detach',entry['revision']],check=True)
            original = source / entry['file']
            if hashlib.sha256(original.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError(f'Upstream checkpoint checksum mismatch: {name}')
            staging = folder / (name + '.tmp')
            shutil.copyfile(original, staging)
            staging.replace(folder / (name + '.pth'))
        print(f'Verified: {checkpoint(name)}')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true',help='Download every benchmark candidate')
    args=parser.parse_args()
    setup(list(REGISTRY) if args.all else [selection()['model']])
