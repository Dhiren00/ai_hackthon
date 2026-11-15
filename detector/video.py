"""Bounded video decoding and deterministic, paired preprocessing."""
from pathlib import Path
import cv2
import numpy as np

class VideoError(ValueError):
    pass

def extract_faces(path: Path, max_seconds=20, max_frames=600):
    cap = cv2.VideoCapture(str(path))
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    crops, indices = [], []
    try:
        if not cap.isOpened():
            raise VideoError('Cannot decode this video. Try an MP4 (H.264) or AVI file.')
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if not np.isfinite(fps) or fps <= 0 or fps > 240:
            raise VideoError('Video has invalid or unsupported frame rate.')
        limit = min(max_frames, int(fps * max_seconds))
        decoded = 0
        for index in range(limit):
            ok, frame = cap.read()
            if not ok:
                break
            decoded += 1
            h, w = frame.shape[:2]
            scale = min(1.0, 640 / max(h, w))
            small = cv2.resize(frame, (max(1,int(w*scale)), max(1,int(h*scale))))
            boxes = cascade.detectMultiScale(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), 1.1, 4, minSize=(40,40))
            # Haar can return smaller detections inside the same face. Suppress
            # contained duplicates before enforcing the single-person limit.
            kept = []
            for box in sorted(boxes, key=lambda b: int(b[2])*int(b[3]), reverse=True):
                x,y,bw,bh = map(int,box)
                duplicate = False
                for xx,yy,ww,hh in kept:
                    overlap = max(0,min(x+bw,xx+ww)-max(x,xx))*max(0,min(y+bh,yy+hh)-max(y,yy))
                    if overlap / (bw*bh) > 0.8:
                        duplicate = True
                        break
                if not duplicate:
                    kept.append((x,y,bw,bh))
            boxes = kept
            if len(boxes) > 1:
                raise VideoError('Multiple faces detected. Use a clip containing one person.')
            if len(boxes) == 0:
                continue
            x,y,bw,bh = boxes[0]
            # Preserve BGR channel order used by the released inference script.
            crop = cv2.resize(small[y:y+bh,x:x+bw], (36,36), interpolation=cv2.INTER_AREA)
            crops.append(crop)
            indices.append(index)
        if len(crops) < max(16, int(fps * 2)):
            raise VideoError('Need at least two seconds of a clearly visible frontal face.')
        coverage = len(crops) / max(decoded,1)
        if coverage < 0.7:
            raise VideoError('Face visibility is too low. Use a well-lit frontal clip.')
        return np.asarray(crops,dtype=np.float32), np.asarray(indices), fps, coverage, decoded == limit
    finally:
        cap.release()

def preprocess(crops, indices):
    if len(crops) < 2:
        raise VideoError('Not enough frames.')
    # Never invent a temporal transition across a missed face detection.
    paired = np.diff(indices) == 1
    if not paired.any():
        raise VideoError('No consecutive face frames available.')
    a, b = crops[:-1][paired], crops[1:][paired]
    motion = (b-a) / np.maximum(b+a, 1e-6)
    def normalize(x):
        return (x-x.mean(axis=0)) / (x.std(axis=0)+0.1)
    # Upstream writes normalized frames to uint8 PNG then reloads them.
    # Explicit modulo reproduces that representation deterministically,
    # without its uninitialized arrays, undefined divisions or disk roundtrip.
    def encode(x):
        return np.mod(np.trunc(x),256).astype(np.uint8).astype(np.float32).transpose(0,3,1,2)
    raw = normalize(crops)[:-1][paired]
    return encode(normalize(motion)), encode(raw), indices[:-1][paired]
