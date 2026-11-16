# Verification and limits

## Current request-triage upgrade, 16 November 2026

The latest Actions run is authoritative for the exact commit tested. It runs actual neural model checkpoints, OCR, routing/failure checks, a full video upload and Chromium UI interactions. See the repository's Actions tab.

Local checks for the upgrade:

- Safety-specific tests passed through the actual API and classifier. They cover short requests, genuine safety reminders, unsupported languages, secret-pattern errors, recovery, dataset separation and UI reference/translation integrity.
- The model training script reproduced the portable runtime's predictions against scikit-learn. Runtime uses standard Python and the committed JSON weights.
- The 60-case synthetic benchmark produced 23 true positives, 2 false positives, 7 false negatives and 28 true negatives at the fixed 0.65 threshold. Both training and holdout were written during the same development session. This is a small controlled evaluation, not independent real-world validation.
- Python compilation, JavaScript syntax, JSON parsing and Git whitespace checks passed.
- Vendored AASIST/TSSD source files were compared to their pinned upstream revisions and matched byte for byte.

The full CI suite additionally checks existing media/OCR models, desktop/mobile layout, English/Hindi/Telugu interface switching, interrupted polling, error recovery, independent verification, downloaded report content, local-only complaint preparation and secret-number export rejection. Screenshots are saved in the run's `demo-browser-screenshots` artifact. Passing local checks alone does not establish that full CI passed.

## Accuracy and usage boundaries

- **Message risk:** 100 synthetic training / 60 separate synthetic evaluation cases. English-only learned TF-IDF/logistic classifier. A low model score stays unknown risk.
- **Voice:** four free GitHub checkpoints were compared as recorded in `reports/README.md`. Selected Inc-TSSDNet held-out clean balanced accuracy was 50%; it missed 18/24 AI clips and flagged 2/8 genuine clips. It is unreliable for real decisions.
- **Text authorship:** the real GPT-2-era model classified 16/19 eligible published in-domain passages correctly. It is not validated for modern generative models. Authorship assessment requires 50 English words.
- **Video:** both released checkpoints have executed under CPU. The upload smoke fixture processes 99 frame pairs at 30 fps with complete face coverage. It is a synthetic clip derived from an upstream illustration, not a labelled accuracy benchmark. No reliable blood-flow/heart-rate measurement claim is made.
- **Evidence:** hashes compare an input to a user-controlled saved record. Records are unsigned and editable, and do not prove identity, truth or legal admissibility.
- **Complaint:** copy/download and official portal handoff are implemented. Autonomous government submission is not implemented or tested.
- **Hosting:** no Render URL or full-model inference on a 512 MB instance has been verified. Use a suitable laptop for the complete live demo if server resources are insufficient.

## Earlier CI findings

The initial video run failed on NCHW CPU operations. Spatial layers now run as NHWC internally while preserving original interfaces and weights. An integration run lacked FFmpeg, now installed in CI. Browser installation required pinning Ubuntu 24.04. Later UI checks were corrected for CSS uppercase labels. The immediate baseline `4e1c345` passed 26 tests and failed one obsolete all-textareas count; the test now checks the main detection form and separately exercises the complaint form.

The full requirement mapping and outstanding eligibility/licensing questions are in `docs/hackathon-audit.md`. Test success establishes execution on tested cases, not perfect code or detector accuracy.
