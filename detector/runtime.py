"""A single inference lock shared by all heavyweight model entry points."""
from functools import wraps
from threading import RLock
INFERENCE_LOCK = RLock()


def serial_inference(function):
    @wraps(function)
    def invoke(*args, **kwargs):
        with INFERENCE_LOCK:
            return function(*args, **kwargs)
    return invoke
