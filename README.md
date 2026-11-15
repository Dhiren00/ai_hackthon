# PhysioCheck — Video, Voice and Text

A simple one-page HTML interface with three options:

- **Video** — upload a face video; run the actual BiDAlab DeepFakesON-Phys model.
- **Voice** — upload speech; run an acoustic anti-spoofing model locally, without transcription.
- **Text** — paste English prose; run an experimental GPT-2-era RoBERTa detector locally.

**Accuracy limits:** the four voice models tested performed poorly on the held-out public recordings. The integrated Inc-TSSDNet model is an experimental demo, not a reliable authenticity check. The text model is old and not validated for modern ChatGPT output. These limitations appear before input and alongside results. See [measured comparisons](reports/README.md).

## Run the website

Use Python **3.10–3.12**, Git and **FFmpeg** (the `ffmpeg` command must be on PATH). Linux CPU / WSL2 is the tested environment. Native Windows/macOS inference has not been verified. Models run locally after download; no API keys, paid services or cloud inference accounts are required.

```bash
git clone https://github.com/Dhiren00/ai_hackthon.git
cd ai_hackthon
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell alternative: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-full.txt
python scripts/setup_models.py
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

On Ubuntu/WSL, install FFmpeg with `sudo apt-get install ffmpeg`. On Windows, install FFmpeg and add its `bin` folder to PATH before starting. All required models are fetched from public original sources and SHA-256 verified. The text checkpoint alone is about 478 MB. Setup needs internet access; inference does not. The first request loads its model and takes longer. In a freshly created environment, dependencies can take several minutes to install.

Open **http://127.0.0.1:8000**. A public deployment must run the Python backend as well as serving the HTML. GitHub hosts the code; GitHub Pages alone cannot run these models. This full app has not been tested within Render Free's 512 MB memory limit.

## Easy design changes

The page is one readable file: **`static/index.html`**. Change the colours in `:root`, labels in the `settings` object, and the HTML layout in that file. No frontend build tools are required. `app.py` serves the page and exposes:

| Route | Input | Output |
|---|---|---|
| `POST /analyze` | Multipart `file`: video | Face-video model assessment and timeline |
| `POST /analyze/audio` | Multipart `file`: recording | Binary experimental voice estimate, raw score, limits |
| `POST /analyze/text` | JSON `{"text":"..."}` | Experimental AI-like / human-like text estimate |
| `GET /health` | None | Existing video checkpoint file readiness; not a full inference health check |

No inputs are saved as application records. Uploads use temporary directories removed after requests. No transcripts are generated. Default web server access logs contain request routes/status, not uploaded content or text bodies. API scores are raw model outputs, not calibrated probabilities.

Limits: 50 MB upload; video first 20 seconds / 600 frames and one frontal face; voice 2 seconds minimum and first 30 seconds; text 50 words minimum / 20,000 characters maximum, with the first 510 tokens assessed. The result states when an input exceeds the analysis limit. Silence and invalid inputs return an error. The voice detector does not establish the speaker's identity, and neither voice nor text output is proof of AI generation.

## Models and licences

Model sources, pinned revisions, licences and data attribution are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). AASIST is MIT; TSSDNet is GPL-3.0; the GPT-2 detector is MIT. The new integration code is GPL-3.0. Upstream source licences and notices are preserved. BiDAlab's DeepFakesON-Phys has no explicit licence in the inspected revision; it is fetched from its original repository into ignored `external/`, not redistributed or relicensed here.

Voice setup only: `python -m detector.audio_assets` (or `--all` for all four benchmark checkpoints). Text setup only: `python -m detector.text_assets`. Video setup only: `python -m detector.assets`. Missing or changed checkpoints produce a clear setup error rather than fabricated results.

The video wrapper retains upstream 36×36 BGR, channels-first input and normalized-to-uint8 PNG representation. It fixes uninitialized frame arrays, undefined divisions, hard-coded dataset paths and unsorted pairing. It never creates a motion pair across a missing-face gap. Correcting undefined behaviour means it does not claim bit-identical reproduction of the paper's benchmark. A visible pulse does not prove a genuine video.

## Verification

```bash
python -m pip install -r requirements-dev.txt
python scripts/setup_models.py
python -m pytest -q
python scripts/smoke_video.py
```

The tests use actual selected audio/text model inference, invalid input cases, static/black preprocessing checks, temporal pairing checks and both video checkpoints. The video smoke test creates a moving-face fixture from an upstream illustration and checks the full upload pipeline. It proves execution only, not accuracy. GitHub Actions runs these checks on Ubuntu.

To reproduce the small voice comparison, install `requirements-benchmark.txt` and run `python scripts/benchmark_audio.py`. For the text sanity check, run `python scripts/benchmark_text.py`. Original evaluation media and model files are not committed. Reports include the exact scope and known failures.
