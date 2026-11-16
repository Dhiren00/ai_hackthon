# Mana Kavacham — verify the request, preserve the evidence

## 1. Problem and threat model

We focus on students and families receiving impersonation requests from someone claiming to be a relative or college official. The attacker wants an urgent payment or account access. They may use an unfamiliar number, a convincing message, or fabricated media. Our main stage is **during the request**, with guided recovery after exposure.

The threat model and full requirement mapping are in `hackathon-audit.md`. Use fictional messages or explicitly consented recordings in the demo.

## 2. Where AI is essential

A locally trained TF-IDF/logistic language classifier assesses English requests from text or screenshot OCR. Its weights are learned from 100 disclosed synthetic training cases. It can assess short messages without requiring users to tick suspicious-word checklists. Inference uses a portable JSON model and standard Python, with no paid API.

Existing neural models assess acoustic spoofing, video physiological manipulation signals and GPT-2-era writing patterns. Their estimates have separate limits. Audio is not transcribed. Hindi/Telugu OCR and interface translation are supported, but automatic message and authorship scoring are English-only.

Removing the trained models removes the automatic assessment and learned explanations. The independent contact check and recovery plan provide the next steps after that assessment.

## 3. The product difference

The result remains useful when the detector is uncertain. A user checks the claimed identity through a saved contact or official app, records whether the contact confirmed or denied the request, and indicates whether money or access was already shared. These user-reported facts update the action plan without being presented as model observations.

An evidence summary records the original input's SHA-256 fingerprint, model limits, verification outcome and completed recovery steps. Users can later compare the original input with that summary entirely inside the browser. Changing the input causes a mismatch. The summary is unsigned and can itself be edited; the hash is a byte-comparison aid.

Complaint fields stay in the browser. Users review and download a draft, then open the official cybercrime portal to complete reporting.

## 4. Effectiveness, privacy and limits

At the fixed 0.65 message-warning threshold on **60 separate synthetic cases**:

| Measure | Result |
| --- | --- |
| Attacks caught | 23 / 30 |
| Attacks missed | 7 / 30 |
| Genuine messages wrongly flagged | 2 / 30 |
| Genuine messages left unflagged | 28 / 30 |
| Precision / recall | 92% / 76.7% |

Training and evaluation have no identical texts, but both were authored in the same development session. These results are not an external blind benchmark or a real-world accuracy estimate.

Voice detection performed poorly in the earlier held-out test. Labelled video and modern AI-writing accuracy remain unvalidated. The interface exposes these limits and keeps low message scores as **unknown risk**.

Uploads are removed after processing. Completed server results expire after 15 minutes. Complaint details and downloaded evidence stay under the user's control. The app never visits submitted links, uses no external inference service, bounds the job queue and rejects some common secret-number patterns. Public production would need stronger gateway rate limits and isolated workers. Full-model operation on a 512 MB Render instance is unverified.

Third-party software and checkpoints are credited in `THIRD_PARTY_NOTICES.md`. The physics model's upstream licence is unresolved. The team must confirm the PDF's registration-window and consent rules before submission.

## 5. Three-minute jury demonstration

1. Open **Try a fictional example → Urgent family request** and run the check. Show the learned message warning and its limitations.
2. Explain that the user calls a saved contact. Select **The known contact denied the request**. Then select **I sent money**. The plan now prioritises the bank and 1930. Tick a completed action.
3. Download the evidence summary. Compare it with a text file containing the submitted message. Append a word to the file and compare again to show the fingerprint mismatch.
4. Open **Prepare a complaint**, enter a fictional account of the incident, and download the editable draft. Show that official submission remains on the government portal.
5. Reset and try the genuine placement reminder. It remains **Risk unknown**, with no claim that a low model score proves safety. Switch to Hindi or Telugu to demonstrate the recovery interface.

Rehearse the run on the actual laptop/server. Have one consented or public audio/video example ready to show the existing media workflow, while explaining its measured accuracy limits.
