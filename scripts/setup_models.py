"""Fetch and verify all three feature models. Requires Git and internet."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from detector.assets import setup as video_setup
from detector.audio_assets import setup as audio_setup, selection
from detector.text_assets import setup as text_setup
video_setup()
audio_setup([selection()['model']])
text_setup()
print('Video, voice and text models are ready.')
