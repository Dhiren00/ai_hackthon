# Measured results and limitations

## Voice comparison

Four freely licensed GitHub models were executed locally: AASIST, AASIST-L (MIT), Res-TSSDNet and Inc-TSSDNet (GPL-3.0). No API was used. This is a bounded comparison of four accessible checkpoints, not every model in existence. SSL Anti-spoofing was not benchmarked: its separate pretrained-weight/fairseq integration was not established in this run. Commercial APIs and Hugging Face-only community models were excluded after the requested scope change.

**None demonstrated reliable detection on this small held-out sample.** The integrated voice feature is an experimental demo and states that clearly in the interface and API.

Data: 64 public UniData recordings: 16 human originals and 48 matching synthetic recordings, across 16 source groups and four country/gender speaker categories. First six seconds are decoded to 16 kHz mono. Seed 42 assigns eight complete source groups to calibration and eight to held-out testing. Matching original/synthetic source groups never cross the split; speaker categories do overlap. This is not a speaker-independent evaluation. Original sample media is not redistributed.

Each recording is tested clean, with deterministic 20 dB additive Gaussian noise, and with a simulated 300–3400 Hz / 8 kHz telephone-band roundtrip. These are transformations of the same recordings, not independent new observations and not actual phone calls. Both classes occur in every split. All models see the same decoded recordings and variants; each uses its own required input length. Long inputs are windowed, covering the tail; short inputs repeat-pad as in upstream workflows. Window logit margins are averaged. A positive margin means AI for every model after accounting for the upstream class order.

Each model's decision threshold is chosen **only on calibration** by balanced accuracy over all variants. The application model is selected on calibration too; test results do not choose thresholds or the winner. Inc-TSSDNet won calibration, then generalized poorly. Do not describe it as the most accurate detector overall.

| Model | Calibration balanced accuracy, all variants | Held-out clean balanced accuracy | Held-out clean humans wrongly flagged | Held-out clean AI clips missed |
|---|---:|---:|---:|---:|
| AASIST | 51.39% | 50.00% | 0 / 8 | 24 / 24 |
| AASIST-L | 50.00% | 50.00% | 0 / 8 | 24 / 24 |
| Res-TSSDNet | 62.50% | 52.08% | 1 / 8 | 20 / 24 |
| Inc-TSSDNet | 73.61% | 50.00% | 2 / 8 | 18 / 24 |

Balanced accuracy averages the human recall and AI recall, so a detector cannot win simply by predicting the majority AI class. Ordinary accuracy is also in the JSON. Inc-TSSDNet clean ordinary accuracy was only 37.5% (12 / 32). A 32-recording test is too small to support population accuracy claims. Multiple synthetic versions share source content, and generator identities are not fully documented. This is an initial compatibility/generalization check, not a definitive benchmark.

Results: `audio_benchmark.json`, per-model predictions and `audio_manifest.json` include file IDs, source hashes, labels, split, scores, thresholds, confusion counts, AUROC and CPU timings. No training/fine-tuning was performed. AASIST was rechecked with the final overlapping-tail window implementation; only those final results are included. Timings vary by CPU and competing work. PyTorch 2.15 CPU ran the initial four-model sweep; the deployed PyTorch 2.5.1 CPU implementation was checked for the selected model and AASIST. Tiny floating-point differences can occur between versions.

Reproduce using `python scripts/benchmark_audio.py` after installing `requirements-benchmark.txt`, Git and FFmpeg. It fetches original source media and checkpoints. This may take several minutes. Fresh output goes into ignored `external/audio_benchmark/`; committed reports are never silently replaced.

## Text sanity check

The actual MIT-licensed OpenAI RoBERTa-base GPT-2 output detector was loaded and run on the first ten lines of each official `webtext.test.jsonl` and `xl-1542M.test.jsonl` release. One human passage failed the app's minimum 50-word rule and was recorded as excluded. **16 of the 19 eligible passages were classified correctly.** This is a tiny in-domain sanity check and does not estimate performance on current ChatGPT or other modern generators. No threshold tuning was done (0.5 raw softmax cutoff). Text is not redistributed; source row indices and scores are in `text_smoke_results.json`.

Reproduce: `python scripts/benchmark_text.py`. The UI and API explicitly warn that this older model is not validated for modern AI text. Never use this estimate as proof that a person used AI.

## Video

The existing DeepFakesON-Phys upload pipeline is retained. Its previous CPU execution check is documented in `../VERIFICATION.md`. Real/deepfake video accuracy has not been benchmarked here.
