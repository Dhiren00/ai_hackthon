# AI-FEST 2026 requirement and code audit

Reviewed against the supplied 10-page **AI-FEST 2026 CSE Stream Track Guide**, Digital Identity Theft, on 16 November 2026. The supplied PDF is available in the conversation but is not checked into this public GitHub repository.

## Focus and threat model

**Main stage:** during an impersonation attempt. **Users:** students and their families who receive unfamiliar-number requests claiming to be a relative or college official. Recovery is the secondary stage.

| Element | Project focus |
| --- | --- |
| Attacker | A scammer posing as a relative, college employee or other trusted contact |
| Target | Students and family members faced with an urgent request |
| Goal | Money, credentials or remote account access |
| Method | A message or a fabricated recording asks for a payment, secrecy or access |
| Signals | Learned request-language patterns; experimental acoustic/video manipulation estimates; independently reported identity mismatch |
| Defence | Assess the submitted input, explain uncertainty, verify the contact through an independent channel, preserve a fingerprinted record and prepare a complaint |

## Requirement mapping

| PDF requirement | Implementation and evidence | Status / limit |
| --- | --- | --- |
| AI is the engine, p2/4 | Learned TF-IDF/logistic classifier for request language, acoustic neural model, physiology-based video model, GPT-2-era text provenance model | Implemented. Message classification works without a manually selected keyword checklist. Recovery steps and user verification are deterministic support features. |
| Clear threat and target, p4 | Threat model above and `submission.md` | Implemented |
| One focused problem, p4/10 | Impersonation requests, especially student/family payments | Focus documented. Broader provenance inputs remain experimental tools. |
| Working live app, p2/9 | Unified upload → identification → OCR if needed → inference → result → identity check → evidence/draft export | Automated execution/browser checks required on final commit. Hosting is optional under p10. Render live inference remains unverified. |
| Measure catches and false alarms, p5/8/9 | `data/scam_holdout.tsv`, `reports/scam_benchmark.json`, public audio/text results | Message test has 60 separate synthetic cases. Voice generalization is poor. Labelled video accuracy and modern AI-text accuracy are still missing. |
| At least 50 labelled examples suggested, p8 | 100 synthetic training cases plus 60 separate synthetic evaluation cases | Implemented for message risk. Same author/session, not a blind external benchmark. |
| Risk levels, explanations, correction, p5 | High / review / unknown / urgent; feature contributions; correction saved locally in evidence summary | Implemented. Model scores never establish that an incident is a scam. |
| Privacy and misuse protection, p4/5 | No API keys, no external inference, no URL visits, bounded worker queue, secret-pattern checks, no-store headers, expiry worker, local complaint fields | Implemented controls. Public production needs gateway request/body rate limits and process isolation. Model scores can still be probed. Secret detection is best-effort. |
| Phone-friendly plain-language demo, p5/9 | Single detection composer, translated recovery panels, fictional demo buttons, progressive disclosure | English/Hindi/Telugu interface. Automatic message and AI-writing classifiers are English-only (Latin-script heuristic). |
| Original approach, p5/10 | Independent verification recorded with model uncertainty, exportable input fingerprint, local re-check of evidence and recovery progress | Working product differentiation. No claim of scientific novelty or that this is the first system of its kind. |
| 4–5 slides or short document, p2/9 | `docs/submission.md`, five sections, with threat model and measured results | Ready as a short submission document. Rehearse with the team. |
| Third-party attribution, p2/9 | `THIRD_PARTY_NOTICES.md`, pinned registries, licences in `third_party/` | Credited. DeepFakesON-Phys has no explicit upstream licence. Its availability is not a redistribution licence. |
| Synthetic, public or consented data, p2/4/8 | New fictional text cases, existing public sample benchmarks | No real victim data committed. Team must obtain consent for any demonstration voices/faces. |
| Work created within 48 hours of registration, p1/2/9 | Git history provides commit times | Registration time and team eligibility cannot be verified from code. Team must confirm. |

## Bugs and engineering fixes

- Latest baseline commit `4e1c345` failed Actions because its old test counted all textareas, including newly added complaint fields. The main detection composer remains a single input. The test now checks that actual requirement, and the browser suite checks the complaint fields separately.
- A short impersonation SMS previously failed the 50-word authorship requirement. Short text/screenshot requests now get the learned message assessment, while authorship remains unavailable below its supported length.
- The earlier checklist-based risk meter did not analyze the submitted request. A reproducible trained classifier now produces that assessment. A negative score remains unknown, with an independent-check step.
- Checksum verification previously allocated an entire 478 MB text checkpoint. It now streams the file in bounded chunks.
- The unified queue serialized its own work, but legacy endpoints could invoke heavy models concurrently. A shared inference lock now covers the three heavy entry points.
- Results previously expired only when another job was accessed. A background cleanup worker now prunes completed jobs every 30 seconds. They stop being retrievable at the 15-minute TTL. Memory release can lag by up to 30 seconds.
- OCR language-list timeout now maps to a useful input error.
- Complaint UI is now translated, supports local draft download, and checks common secret-number patterns before copying/exporting.
- The added training step initially allowed a newer SciPy to replace NumPy 1.26 with NumPy 2, breaking TensorFlow. Training now pins compatible NumPy/SciPy versions and CI checks dependency consistency.
- API responses include no-store, nosniff and no-referrer headers. User-entered strings render with textContent or textarea values.
- Evidence exports distinguish uploaded file bytes from trimmed pasted text, and include the actual input hash. The local checker can detect a changed input relative to a saved summary.

## Algorithm and source review boundary

Reviewed all tracked file categories: application/API, queue/routing, media preprocessing, inference wrappers, asset registries, training and benchmark scripts, frontend/translations, CI/Docker/Render configuration, tests, reports and licences. Vendored architectures are retained with upstream notices and exercised through integration tests. Source review and successful tests cannot prove every possible input or the models' statistical correctness.

The video model estimates physiological manipulation signals through the released neural model. The app does not independently measure a verified heart rate. The audio model classifies acoustic spoofing without transcription. The old text model estimates GPT-2-style authorship. The new message model learns word/bigram weights from synthetic examples. Only the supported text/screenshot route receives automated message-risk scoring. Voice/video request meaning is not transcribed or inferred.

## Remaining limitations that matter to the jury

1. Message evaluation is 23/30 attacks caught, 7 missed, 2/30 genuine cases flagged, 28 correctly unflagged at the fixed 0.65 threshold. Precision 92%, recall 76.7%, false-positive rate 6.7% on this synthetic set only. Unflagged is not a safe verdict.
2. Voice model held-out clean balanced accuracy was 50%. It is an execution demo, not a dependable voice-clone defence.
3. Video has no labelled attack/genuine evaluation here. GPT-2 authorship results do not validate current generative models.
4. A SHA-256 fingerprint detects a changed input relative to a saved record. The record itself is unsigned and editable. It does not establish a real identity, time, truth or legal admissibility.
5. Complaint assistance prepares a reviewed draft and official handoff. There is no implemented government submission API or autonomous filing integration. Authentication, verification, evidence attachments and submission happen on the official portal.
6. Full TensorFlow/PyTorch/RoBERTa inference has not been demonstrated within Render Free's 512 MB. The lightweight message route avoids those heavyweight imports, but the whole app still needs a suitable laptop/server.
7. New local model and synthetic data are project work under GPL-3.0. The upstream physiology model lacks an explicit licence, so full redistribution/commercial permission remains unresolved.

## Innovation options considered

| Direction | Why it was or was not selected |
| --- | --- |
| Larger voice/video foundation model | Could improve detection, but new weights, resources and labelled evaluation exceed a reliable free demo scope. |
| Universal AI/scam percentage | A single number would combine unrelated and uncalibrated tasks. It would be difficult to defend to judges. |
| Fully autonomous government filing | No supported submission integration established. Incorrect filing and authentication make this an unreliable demo dependency. |
| Generic scam chatbot | Easy to confuse with the brief's examples and difficult to ground its advice without more infrastructure. |
| Verification plus fingerprinted recovery record | Selected. Works with uncertain model outputs, shows the source of each fact, supports a changed-file demonstration, keeps sensitive complaint fields local, and connects detection to action. |

## Official recovery sources checked

- https://cybercrime.gov.in/
- https://cybercrime.gov.in/webform/FAQ.aspx
- https://cybercrime.gov.in/webform/Citizen_Manual.aspx

Indian financial cyber fraud guidance supports prompt reporting through 1930 and the official portal. No government endorsement of this application is implied.
