import argparse
import json
from pathlib import Path
from .engine import analyze
parser = argparse.ArgumentParser(description='Assess a video using DeepFakesON-Phys')
parser.add_argument('video',type=Path)
parser.add_argument('--model',choices=['CelebDF_V2','DFDC_Preview'],default='CelebDF_V2')
args = parser.parse_args()
print(json.dumps(analyze(args.video,args.model),indent=2))
