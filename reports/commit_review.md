# Commit review and connected-flow verification

Reviewed the remote main history:

| Commit | Purpose | Observed checks / action |
|---|---|---|
| `fc19645` | Initialise repository | README-only initialisation; no inference claim. |
| `1a72193` | Video demo | Local checks passed earlier, but Actions run `43753148757` failed on CPU NCHW convolution. Fixed by preserving interfaces/weights while converting spatial operations internally to NHWC. Tested with oneDNN explicitly disabled. |
| `08c976c` | Voice/text UI and benchmarks | Actions run `43756321249` installed models successfully, then failed two tests because FFmpeg was not installed on the runner. CI now explicitly installs FFmpeg, Tesseract and required fonts. Voice/text accuracy limitations remain visible. |

The current unified workflow replaces manual media tabs with one composer and content inspection. Screenshots use OCR, then the text route. Audio-only MP4/other containers are inspected through actual streams. Status polling exposes actual processing stages and recoverable failures. Language options translate interface/results into English, Hindi and Telugu. Hindi/Telugu text can be extracted but is not falsely scored by the English-only model.

Local verification: **27 tests passed**, covering the actual video/voice/text models, routing, English/Hindi/Telugu screenshot extraction, invalid inputs, queue bounds, failed-job cleanup, expiry and recovery. The full video upload fixture processed 99 frame pairs and returned the same model result (0.818583 genuine model score). Python compilation and JavaScript syntax checks passed.

The workflow runs these checks again in GitHub Actions and adds real Chromium checks: pasted text, screenshots, voice input, Hindi/Telugu language switching, mobile overflow, interrupted polling, and recovery after a bad upload. Generated screenshots are an Actions artifact. Local browser launch was blocked by the execution environment's socket restrictions, so browser verification is performed on the GitHub runner.

Execution checks are not accuracy claims. Voice detection remains poor on the small held-out sample, text detection is a GPT-2-era experimental estimate, and video detection accuracy has not been established on a labelled benchmark here. The demo has no autonomous future code-repair service; Actions detects regressions, while runtime failures receive explicit error states.
