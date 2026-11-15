# Verification record

Environment: Linux x86_64 CPU, Python 3.12.14, TensorFlow 2.16.2, tf-keras 2.16.0, OpenCV 4.10.0, NumPy 1.26.4.

- `python -m detector.assets`: both upstream model SHA-256 checks passed.
- `python -m pytest -q`: 7 passed. Both actual checkpoints executed with finite outputs.
- `python scripts/smoke_video.py`: HTTP 200; 99 consecutive frame pairs, 30 fps, 100% face coverage, 3.33 seconds. Generated fixture from upstream illustration; not a genuine/deepfake accuracy test.
- `python -m compileall -q app.py detector scripts tests`: passed.

Two legacy protobuf deprecation warnings occur under Python 3.12. TensorFlow may print CUDA registration messages in environments containing both CPU/GPU packages; execution here used CPU successfully.

No labelled-video detection-accuracy claim is made. Browser interaction and native Windows/macOS execution were not tested.
