"""Evaluate the locked classifier on 60 separate synthetic cases. No tuning."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from detector.scam import assess_message, load_classifier
ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'data' / 'scam_holdout.tsv'
training = {line.split('\t', 1)[1] for line in (ROOT/'data/scam_train.tsv').read_text().splitlines()}
rows = [line.split('\t', 1) for line in source.read_text().splitlines()]
assert len(rows) >= 50 and all(text not in training for _, text in rows)
predictions = []
for i, (label, text) in enumerate(rows):
    result = assess_message(text, 'en')
    predictions.append({'case': i + 1, 'label': int(label), 'flagged': result['level'] == 'high', **result})
tp = sum(p['label'] == 1 and p['flagged'] for p in predictions)
fp = sum(p['label'] == 0 and p['flagged'] for p in predictions)
fn = sum(p['label'] == 1 and not p['flagged'] for p in predictions)
tn = sum(p['label'] == 0 and not p['flagged'] for p in predictions)
report = {'dataset': '60 hand-written synthetic demo cases, 30 attack / 30 genuine',
          'independence_limit': 'Written in the same development session as training data. Not an external blind benchmark. No real-world accuracy claim.',
          'model_training_sha256': load_classifier()['training_sha256'],
          'holdout_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'threshold': .65, 'true_positive': tp, 'false_positive': fp,
          'false_negative': fn, 'true_negative': tn,
          'precision': tp/(tp+fp) if tp+fp else 0, 'recall': tp/(tp+fn),
          'false_positive_rate': fp/(fp+tn), 'predictions': predictions}
(ROOT/'reports/scam_benchmark.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'predictions'}, indent=2))
