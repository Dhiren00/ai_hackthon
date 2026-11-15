# Verification record

Environment: Linux x86_64 CPU, Python 3.12.14, TensorFlow 2.16.2, tf-keras 2.16.0, OpenCV 4.10.0, NumPy 1.26.4.

- `python -m detector.assets`: both upstream model SHA-256 checks passed.
- `python -m pytest -q`: 7 passed. Both actual checkpoints executed with finite outputs.
- `python scripts/smoke_video.py`: HTTP 200; 99 consecutive frame pairs, 30 fps, 100% face coverage, 3.33 seconds. Generated fixture from upstream illustration; not a genuine/deepfake accuracy test.
- `python -m compileall -q app.py detector scripts tests`: passed.

Two legacy protobuf deprecation warnings occur under Python 3.12. TensorFlow may print CUDA registration messages in environments containing both CPU/GPU packages; execution here used CPU successfully.

No labelled-video detection-accuracy claim is made. Browser interaction and native Windows/macOS execution were not tested.

## Video / Voice / Text integration verification

- Four free GitHub audio model checkpoints were executed on the public sample comparison documented in `reports/README.md`. No API keys or paid services were used. The selected voice model did not generalize reliably and is explicitly labelled experimental.
- The real OpenAI GPT-2-era text checkpoint executed on 19 eligible published passages (16 correct), with one short passage excluded. This does not validate modern AI-text detection.
- Final regression run: **14 tests passed**, covering new audio/text inputs and actual model inference, existing video preprocessing and both video checkpoints.
- Full video upload smoke test: HTTP 200, 99 frame pairs, 30 fps, complete face coverage, raw genuine model score 0.818583. This is execution verification on a generated fixture, not an accuracy benchmark.
- Full voice upload smoke test: HTTP 200 on a decoded public speech sample, actual selected checkpoint inference and binary estimate returned. Execution is verified; the sample's verdict is not treated as an accuracy assertion.
- JavaScript syntax and Python compilation checks passed. Automated browser rendering could not be verified because the browser runtime download failed. The page is a single responsive HTML file with three mode controls; HTTP content and mode declarations are checked in the tests.
- Final integration inference tests used CPU PyTorch 2.5.1, NumPy 1.26.4, Transformers 4.46.3, TensorFlow CPU 2.16.2 and tf-keras 2.16.0 on Python 3.12 / Linux.
