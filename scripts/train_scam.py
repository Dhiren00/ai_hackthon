"""Reproduce the compact model. The holdout is never loaded for training."""
import hashlib
import json
from pathlib import Path
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from detector.scam import features

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'data' / 'scam_train.tsv'
rows = [line.split('\t', 1) for line in source.read_text().splitlines()]
vectorizer = TfidfVectorizer(analyzer=lambda text: list(features(text).elements()), sublinear_tf=True)
x = vectorizer.fit_transform([text for _, text in rows])
classifier = LogisticRegression(C=8, random_state=42, max_iter=1000)
classifier.fit(x, [int(label) for label, _ in rows])
model = {
    'name': 'PhysioCheck synthetic impersonation classifier v1',
    'algorithm': 'word unigram/bigram TF-IDF + logistic regression',
    'training_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'training_examples': len(rows), 'language': 'en',
    'intercept': round(float(classifier.intercept_[0]), 8),
    'features': {term: [round(float(vectorizer.idf_[i]), 8), round(float(classifier.coef_[0][i]), 8)]
                 for term, i in sorted(vectorizer.vocabulary_.items())},
}
(ROOT / 'detector' / 'scam_model.json').write_text(json.dumps(model, indent=2) + '\n')
# Catch drift between the pure-Python runtime and sklearn's vectorization.
from detector.scam import assess_message, load_classifier
load_classifier.cache_clear()
for (_, text), expected in zip(rows, classifier.predict_proba(x)[:, 1]):
    assert abs(assess_message(text, 'en')['score'] - expected) < 1e-6
print(f'Reproduced model from {len(rows)} disclosed training cases.')
