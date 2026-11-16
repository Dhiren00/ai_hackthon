import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS','2')
os.environ.setdefault('TF_NUM_INTEROP_THREADS','2')
from .runtime import serial_inference
from functools import lru_cache
from threading import Lock
import numpy as np
from .assets import checkpoint
from .video import extract_faces, preprocess

LOCK = Lock()

@lru_cache(maxsize=2)
def load_model(name='CelebDF_V2'):
    import tf_keras
    original = tf_keras.models.load_model(str(checkpoint(name)), compile=False)
    return portable_model(original)


def portable_model(original):
    """Keep upstream NCHW interfaces/weights; execute spatial ops as NHWC.

    Restoring NCHW after each convolution/pool preserves the unusual upstream
    BatchNorm/Flatten axes exactly, without relying on oneDNN CPU support.
    """
    import tf_keras as keras
    def clone(layer):
        config = layer.get_config()
        if isinstance(layer, (keras.layers.Conv2D, keras.layers.AveragePooling2D)) and config.get('data_format') == 'channels_first':
            config['data_format'] = 'channels_last'
            config['name'] = 'spatial_op'
            return keras.Sequential([
                keras.layers.Permute((2,3,1)),
                layer.__class__.from_config(config),
                keras.layers.Permute((3,1,2)),
            ], name=layer.name)
        return layer.__class__.from_config(config)
    portable = keras.models.clone_model(original, clone_function=clone)
    portable.set_weights(original.get_weights())
    return portable

@serial_inference
def analyze(path, name='CelebDF_V2'):
    crops, indices, fps, coverage, truncated = extract_faces(path)
    motion, raw, frame_indices = preprocess(crops,indices)
    with LOCK:
        model = load_model(name)
        scores = np.concatenate([model([motion[i:i+64],raw[i:i+64]],training=False).numpy().reshape(-1)
                                 for i in range(0,len(raw),64)])
    if not np.isfinite(scores).all():
        raise RuntimeError('Model returned non-finite scores.')
    mean = float(scores.mean())
    # Upstream examples put genuine videos near 1.0. These are raw model
    # scores, NOT calibrated probabilities. Use a conservative unsure band.
    assessment = 'more consistent with genuine' if mean >= 0.7 else 'suspicious manipulation signals' if mean <= 0.3 else 'inconclusive'
    return dict(model=name, assessment=assessment, genuine_model_score=mean,
                frames_analyzed=len(scores), fps=fps, face_coverage=round(coverage,3),
                analyzed_seconds=round((int(indices[-1])+1)/fps,2), analysis_limit_reached=truncated,
                timeline=[{'seconds':round(int(frame_indices[i])/fps,3),'genuine_model_score':float(scores[i])}
                          for i in range(0,len(scores),max(1,len(scores)//100))],
                limitations='Experimental research model; score is not a probability or proof of authenticity. No audio analysis. Not validated here on a labelled real/deepfake benchmark.')
