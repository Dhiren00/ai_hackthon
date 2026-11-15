# Third-party model sources

The new application integration and benchmark code is GPL-3.0 licensed. Retain the licence and notices when redistributing. Pre-existing external DeepFakesON-Phys assets are not relicensed or redistributed by this repository.

- **AASIST / AASIST-L** — NAVER Corp., MIT. `third_party/aasist/model.py` is copied unchanged from `models/AASIST.py`, revision `a04c9863f63d44471dde8a6abcb3b082b07cd1d1`, https://github.com/clovaai/aasist. Original LICENSE and NOTICE are adjacent. Checkpoint paths, revisions and SHA-256 checksums are in `detector/audio_models.json`.
- **Res-TSSDNet / Inc-TSSDNet** — G. Hua et al., GPL-3.0. `third_party/tssd/model.py` is copied unchanged from `models.py`, revision `36c9705a5bdbb68d01fae484f1b758dd673d9f43`, https://github.com/ghua-ac/end-to-end-synthetic-speech-detection. Original LICENSE is adjacent. Model weights are downloaded from the original repository during setup.
- **GPT-2 output detector** — OpenAI, MIT, https://github.com/openai/gpt-2-output-dataset, revision `b76f67c651fea691b37abe01a6de762bc43330e7`. Original licence is in `third_party/openai_text/LICENSE`. This app independently wraps the published RoBERTa-base checkpoint. The detector was trained on GPT-2 outputs, not modern ChatGPT. Older unused pooler and constant position buffers are omitted for compatibility with Transformers 4.46; learned classifier/encoder weights load strictly.
- **RoBERTa base configuration/tokenizer** — Facebook AI / Hugging Face Transformers ecosystem. Transformers is Apache-2.0 licensed. Setup retrieves public tokenizer files; pinned checksums and URLs are in `detector/text_files.json`.
- **DeepFakesON-Phys** — BiDAlab. The upstream revision has no explicit licence. Source and weights are fetched into ignored `external/`, as described in README. No permission to redistribute those assets is implied.

## Evaluation data

- UniData public voice samples: https://github.com/UniData-NLP/real-vs-fake-human-voice-deepfake-audio, revision `b9680b1c490c6dd6d79f3868db0ff9c66bcfda46`. The public sample contains 16 source groups, each with one original and three synthetic recordings. Files and the original spreadsheet are **not redistributed**. The full dataset is commercial and was not purchased or used. Paths, source hashes, split assignments and model predictions are recorded for reproducibility. Access and usage of source media remain subject to the source's terms.
- Text smoke evaluation uses the first ten lines each of `webtext.test.jsonl` and `xl-1542M.test.jsonl` from the GPT-2 output dataset release. Text is not redistributed in this repository. Scores and source row indices are recorded. This is an in-domain sanity test only.

- **Tesseract OCR / tessdata_fast** — Apache-2.0, https://github.com/tesseract-ocr/tessdata_fast. The OCR executable is installed separately; pinned English/Hindi/Telugu language packs are fetched into ignored `external/tessdata`. Revision and SHA-256 hashes are in `detector/ocr_files.json`. No OCR model files are redistributed here.
