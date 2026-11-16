# S.H.I.E.L.D. — impersonation request triage

A single input for text, screenshots, audio and video, with a local English message-warning classifier, independent contact verification, and a downloadable evidence/recovery summary. The jury-facing focus is impersonation requests targeting students and families.

- **Start here:** [hackathon audit](docs/hackathon-audit.md), [five-section submission document](docs/submission.md).
- Short English messages now receive an actual learned warning assessment. Authorship needs at least 50 words. Hindi/Telugu interface and OCR are supported; automatic message scoring remains English-only.
- **Measured demo result:** 23/30 synthetic attacks caught, 7 missed, 2/30 genuine messages flagged. See [the complete report](reports/scam_benchmark.json). No real-world accuracy claim.
- The verification/recovery flow keeps model evidence separate from user-reported identity checks. Download a fingerprinted summary and compare the original file later, locally in the browser.
- Complaint descriptions stay in the browser, with copy/download and a link to the official reporting portal. Actual official submission is a separate user action.
- The lightweight message model is included. Reproduce it with `pip install -r requirements-training.txt`, `python scripts/train_scam.py`, then `python scripts/benchmark_scam.py`. No additional inference package is required.
- Full media model setup and limitations are below. Full-model inference within Render Free's 512 MB remains unverified.

# S.H.I.E.L.D. — One input for text, screenshots, voice and video

A minimal, mobile-friendly page with one input area. The app identifies the content automatically:

- **Video** — upload a face video; run the actual BiDAlab DeepFakesON-Phys model.
- **Voice** — upload speech; run an acoustic anti-spoofing model locally, without transcription.
- **Text / screenshots** — paste prose or upload a screenshot for OCR and an experimental GPT-2-era text assessment.

**Accuracy limits:** the four voice models tested performed poorly on the held-out public recordings. The integrated Inc-TSSDNet model is an experimental demo, not a reliable authenticity check. The text model is old and not validated for modern ChatGPT output. These limitations appear before input and alongside results. See [measured comparisons](reports/README.md).

## Run the website

Use Python **3.10–3.12**, Git, **Tesseract OCR** and **FFmpeg** (the `ffmpeg` command must be on PATH). Linux CPU / WSL2 is the tested environment. Native Windows/macOS inference has not been verified. Models run locally after download; no API keys, paid services or cloud inference accounts are required.

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

The page is one readable file: **`static/index.html`**. Change the colours in `:root` and the HTML layout in that file. Edit `static/i18n.json` for English/Hindi/Telugu interface labels and result messages. No frontend build tools are required. `app.py` serves the page and exposes:

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

## Unified input update

The current page has **one input area**, not separate media tabs. Paste text, attach/drop a file, or paste a clipboard screenshot. The server identifies the content and follows the [local analysis workflow](workflow/README.md). It reports actual progress and then the result. The language selector translates the interface and result messages into English, Hindi or Telugu.

Screenshots use local Tesseract OCR in all three languages. **This does not make the text detector multilingual**: Hindi/Telugu writing can be extracted, but receives an unsupported-language assessment instead of a misleading AI score. Translation into English before detection would change the evidence, so it is not done. General translation of arbitrary user content is not included.

Install the Tesseract executable as well as FFmpeg (`sudo apt-get install ffmpeg tesseract-ocr` on Ubuntu/WSL). `python scripts/setup_models.py` now also fetches pinned, checksum-verified English/Hindi/Telugu OCR packs from `tesseract-ocr/tessdata_fast`. This avoids requiring system-wide OCR-language installation. `python scripts/setup_ocr.py` installs just those packs. Optional `PHYSIOCHECK_TESSDATA` points to a directory containing all three packs.

The new `POST /api/jobs` route accepts multipart `text` or `file`, and returns a job ID; `GET /api/jobs/{id}` reports status and result. Original endpoints are retained for compatibility. Maximum four queued/running jobs, a single worker, 15-minute result expiry and bounded file/analysis limits keep the demo predictable. Restart loses in-memory jobs. Always run Uvicorn with `--workers 1`.

The Dockerfile packages the backend, FFmpeg, Tesseract and all models. Build with `docker build -t physiocheck .`, then run `docker run --rm -p 8000:8000 physiocheck`. This is packaging for deployment, not an already deployed public website. The full multi-model demo needs substantially more memory than a basic static site; Render Free compatibility is not claimed.

The video model now executes spatial operations in NHWC internally while retaining upstream NCHW interfaces, BatchNorm/Flatten axes and all learned weights. This fixes the CPU error seen in the first GitHub Actions run without requiring oneDNN. CI disables oneDNN to exercise that portable path.

## Scam watch

The caution box uses short extracts from BleepingComputer and The Hacker News RSS feeds. A local experimental classifier helps select one extractive sentence per article and rank articles after an AI/scam relevance filter; it does not verify claims or generate a free-form summary. Only linked source reports from the last 14 days appear. General precaution guidance is displayed alongside them. Articles remain in English, while controls and guidance support English, Hindi and Telugu.

`.github/workflows/cautions.yml` runs daily at 02:30 UTC and can be run manually in GitHub Actions. It commits the latest snapshot, then triggers demo checks for the updated revision. Scheduled GitHub jobs can be delayed; the box shows its last check, partial source failures and a warning after 48 hours. If every source fails, the previous snapshot is retained and the scheduled job fails visibly. The first snapshot appears after the first successful refresh. Deployments must update from `main` for the box to reflect refreshed data. No API key is required.
