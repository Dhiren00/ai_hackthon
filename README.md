# S.H.I.E.L.D.

**Check suspicious requests, verify who sent them, and decide what to do next.**

S.H.I.E.L.D. is an AI-FEST 2026 hackathon project for students and families facing impersonation scams. Paste a message or attach a screenshot, voice recording, or video. The app identifies the input and runs the appropriate check. For suspicious requests, it guides you through verifying the sender via a saved number or official app, then helps you decide what to do based on what you’ve already shared.

**[Try the live demo](https://ai-hackthon-apo9.onrender.com/)** · [Hackathon submission](docs/submission.md)

## Try it in three steps

1. Open **Try a fictional example**, choose **Urgent family request**, and select **Check input**.
2. Review the warning. Under **Check who is really asking**, record what happened when you contacted the person independently. If you’ve already sent money or shared access, select that too to see the relevant recovery steps.
3. Download the safety report, or use **Prepare a complaint** to draft a description in your browser. You can review and submit it yourself through India’s official cybercrime portal.

## What you can check

| Input | What S.H.I.E.L.D. gives you |
| --- | --- |
| Message or text file | An English scam warning score based on patterns learned from fictional requests, with terms that contributed to the warning. |
| Screenshot | Text extraction in English, Hindi, and Telugu. Extracted English messages can also be screened for scam patterns. |
| Voice recording | An experimental Inc-TSSDNet assessment of acoustic spoofing signals. |
| Face video | An experimental DeepFakesON-Phys assessment with a score timeline for a single visible face. |

The interface is available in English, Hindi, and Telugu. **Scam watch** shows source-linked reports in the selected language. The experimental text authorship model can assess English passages of at least 50 words on a host where it is enabled.

The app removes uploaded files after processing, and server results expire after 15 minutes. Complaint drafts stay in the browser. Verification answers are recorded separately from model estimates in the downloadable report.

## What we measured

The English scam classifier uses TF-IDF and logistic regression trained on **100 fictional messages**. We evaluated it at a fixed warning threshold on **60 separate fictional messages**:

| Outcome | Result |
| --- | ---: |
| Scam requests flagged | 23 / 30 |
| Scam requests missed | 7 / 30 |
| Genuine requests flagged | 2 / 30 |
| Genuine requests left unflagged | 28 / 30 |

That is **92% precision** and **76.7% recall** on this dataset. Both sets were written during the same development session, so the results describe this controlled test. A low score leaves risk unknown. Check the sender independently before acting on a request. [Read the benchmark](reports/scam_benchmark.json).

The voice, video, and authorship models are research demonstrations. The voice comparison found unreliable detection on the held-out sample, video accuracy has yet to be benchmarked on labelled real and fake clips, and the authorship model was developed for GPT-2-era text. [Read the model comparison and limitations](reports/README.md).

## Run locally

Use **Python 3.10–3.12**, Git, FFmpeg, and Tesseract. Linux and WSL2 are the tested setup paths. On Ubuntu, install the system tools with `sudo apt-get install ffmpeg tesseract-ocr`.

```bash
git clone https://github.com/Dhiren00/ai_hackthon.git
cd ai_hackthon
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-full.txt
python scripts/setup_models.py
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

Open [localhost:8000](http://127.0.0.1:8000). Setup downloads and verifies the model and OCR files. Inference runs on the server hosting the app and requires no external inference API or API key. Uploads are limited to 50 MB.

The [Dockerfile](Dockerfile) packages the full app. The [Render configuration](render.yaml) uses one worker for its in-memory jobs. The current code defaults to disabling text authorship on Render so screenshot OCR and scam screening can run without loading that model. Use `SHIELD_TEXT_PROVENANCE=1` on a host with enough memory if you need authorship checks. Full media inference on Render Free is unverified. `GET /api/health` reports the deployed release and, on the current code, whether the authorship model is enabled.

## How the repository fits together

| Path | Purpose |
| --- | --- |
| [App and API](app.py) | FastAPI serves the site, starts checks at `POST /api/jobs`, and returns progress and results at `GET /api/jobs/{id}`. |
| [Analysis workflow](workflow/README.md) | Content identification, OCR and model routing, progress, retries, and cleanup. |
| [Web interface](static/) | The unified input, translations, independent verification, recovery checklist, and complaint drafting. |
| [Data and reports](reports/) | Model comparisons and benchmark results. The message classifier’s fictional examples are in [data/](data/). |
| [Checks](VERIFICATION.md) | Test coverage for model execution, OCR, upload routing, browser behavior, and recovery. |

To run the automated checks after setup, install `requirements-dev.txt` and run `python -m pytest -q`. The [GitHub Actions workflow](.github/workflows/test.yml) also exercises uploads and the Chromium demo.

The application integration is [GPL-3.0](LICENSE). Model credits, upstream terms, and dataset attribution are in [Third-party notices](THIRD_PARTY_NOTICES.md).
