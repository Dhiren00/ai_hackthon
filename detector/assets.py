"""Retrieve immutable upstream checkpoints without redistributing them."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'external' / 'DeepFakesON-Phys'
REVISION = '941a4b42842039f8c0cc709990ba0fa7f0c35833'
def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


CHECKSUMS = {
    'CelebDF_V2': 'bb2a19bad2bcc4eb209f6b6ea115e1fc59b9597c77651a28f8cee63b7ad58ed1',
    'DFDC_Preview': '147922af933c01c92f892b65785dd43af28d0cc1f916f78dce1c9c597b1f710d',
}

def checkpoint(name='CelebDF_V2'):
    if name not in CHECKSUMS:
        raise ValueError('Unknown model')
    path = UPSTREAM / 'pretrained models' / f'DeepFakesON-Phys_{name}.h5'
    if not path.is_file():
        raise FileNotFoundError('Models missing. Run: python -m detector.assets')
    if file_sha256(path) != CHECKSUMS[name]:
        raise ValueError('Model checksum mismatch. Restore the pinned upstream files.')
    return path

def setup():
    UPSTREAM.parent.mkdir(parents=True, exist_ok=True)
    if not UPSTREAM.exists():
        subprocess.run(['git', 'clone', 'https://github.com/BiDAlab/DeepFakesON-Phys.git', str(UPSTREAM)], check=True)
    subprocess.run(['git', '-C', str(UPSTREAM), 'checkout', '--detach', REVISION], check=True)
    for name in CHECKSUMS:
        print(f'Verified: {checkpoint(name)}')

if __name__ == '__main__':
    setup()
