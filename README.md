# PhysioCheck — DeepFakesON-Phys video demo

A local video-upload application and CLI using the **actual released BiDAlab DeepFakesON-Phys checkpoints**. This is not Intel FakeCatcher and does not recreate Intel's proprietary platform.

## Start the demo

Use Python **3.10–3.12** and Git. Linux/WSL2 CPU execution has been tested. Native Windows and macOS have not been verified; the upstream model uses channels-first convolutions, which depend on TensorFlow backend support. On a Windows laptop, use WSL2 if the native backend reports NCHW errors.

```bash
git clone https://github.com/Dhiren00/ai_hackthon.git
cd ai_hackthon
python -m venv .venv
# Linux / WSL2:
source .venv/bin/activate
# Windows PowerShell alternative: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m detector.assets
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Upload a 3–20 second clip with one well-lit, frontal face. The app does not use a cloud inference API. TensorFlow runs locally. No GPU is required on the tested Linux CPU setup. Network access is needed for the initial dependency and checkpoint downloads.

CLI:

```bash
python -m detector path/to/video.mp4
python -m detector path/to/video.mp4 --model DFDC_Preview
```

## What is implemented

- Video upload, face detection, preprocessing, pretrained inference and result timeline.
- Both CelebDF_V2 and DFDC_Preview checkpoints, verified with SHA-256 checksums.
- Immutable upstream revision `941a4b42842039f8c0cc709990ba0fa7f0c35833`.
- Legacy `tf-keras` loader for the older HDF5 format; no retraining or fabricated predictions.
- Temporary uploads deleted after the request; 50 MB upload limit, first 20 seconds / 600 frames maximum, face detection at bounded resolution, serialized inference.
- Clear rejection of invalid videos, inadequate face visibility and multiple detected faces.

## Interpretation and preprocessing

The model uses physiological cues related to rPPG. It does **not** output a measured heart rate, a blood-flow proof or an authenticated identity. High raw outputs correspond to genuine examples in upstream `images/cases_scores.png`; the API reports `genuine_model_score`, never a fake probability. Scores are uncalibrated. Demo labels use a conservative 0.3–0.7 inconclusive band; those cutoffs are not validated decision thresholds.

The original scripts contain dataset-specific Windows paths, uninitialized frame slots, division-by-zero risks and independent unsorted file reads. The wrapper removes those problems. It retains the upstream 36×36 BGR, channels-first two-stream representation, temporal per-pixel normalization and normalized-to-uint8 representation used by the released PNG/inference workflow. Only consecutive detected frames become motion pairs. Correcting undefined preprocessing means this is **not a bit-for-bit reproduction of the authors' benchmark**. Temporal normalization is performed over the analysed clip; no benchmark performance is claimed.

A detectable pulse does not prove a video is real. Compression, lighting, motion, cropping, skin appearance, generator changes and face-detection jitter can affect outputs. Multiple people and audio-only manipulations are not supported. Face tracking across identity changes is not implemented. Run locally for demonstrations; this is not a production hosting service.

## Verification

```bash
python -m pip install -r requirements-dev.txt
python -m detector.assets
python -m pytest -q
python scripts/smoke_video.py
```

Tests exercise real checkpoint loading/inference for both models, finite preprocessing of black/static clips, PNG representation equivalence, temporal gaps, invalid/empty inputs and no-face rejection. The smoke test sends a generated moving-face AVI through the actual upload endpoint, face detector, preprocessing and checkpoint. It uses a crop of the upstream illustration, fetched during setup. It tests **execution, not detection accuracy**. No evaluation media is committed.

**Not yet verified:** accuracy on an independent labelled set of real and deepfake videos; real-time calling integration; native Windows/macOS execution; visual browser interaction. A functioning pipeline does not guarantee correct classifications.

## Attribution and upstream terms

Source: https://github.com/BiDAlab/DeepFakesON-Phys

Hernandez-Ortega, Javier; Tolosana, Ruben; Fierrez, Julian; Morales, Aythami. *DeepFakesON-Phys: DeepFakes Detection based on Heart Rate Estimation* (2020), https://arxiv.org/abs/2010.00400.

The inspected upstream revision provides no explicit LICENSE file. Its public availability is not a general redistribution licence. This repository therefore **does not vendor or redistribute its source, weights or images**. Setup fetches the original repository into ignored `external/`. Upstream assets remain subject to their owners' terms; contact the authors to clarify your intended reuse/distribution. No permissions are implied by this wrapper. This integration does not claim authorship of the model.
