"""Small, locally trained language classifier for impersonation requests.

TF-IDF + logistic regression. Weights are learned from the disclosed synthetic
training corpus. Output is a model score, never a probability of fraud.
"""
from collections import Counter
from functools import lru_cache
import json
import math
from pathlib import Path
import re

MODEL_PATH = Path(__file__).with_name('scam_model.json')
TOKEN_PATTERN = re.compile(r'(?u)\b\w\w+\b')
SECRET_PATTERNS = [
    re.compile(r'(?i)\b(?:otp|pin|password|passcode|verification code)\s*(?:is|:|=)?\s*\d{4,8}\b'),
    re.compile(r'(?<!\d)(?:\d[ -]?){15}\d(?!\d)'),
    re.compile(r'(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}(?!\d)'),
]


def contains_secret(text):
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def features(text):
    tokens = TOKEN_PATTERN.findall(text.lower())
    return Counter(tokens + [' '.join(pair) for pair in zip(tokens, tokens[1:])])


@lru_cache(maxsize=1)
def load_classifier():
    return json.loads(MODEL_PATH.read_text())


def assess_message(text, language):
    if language != 'en' or len(text.split()) < 3:
        return {'status': 'unsupported', 'level': 'unknown', 'score': None, 'terms': []}
    model = load_classifier()
    counts = features(text)
    values = []
    for term, count in counts.items():
        entry = model['features'].get(term)
        if entry:
            idf, weight = entry
            values.append((term, (1 + math.log(count)) * idf, weight))
    norm = math.sqrt(sum(value * value for _, value, _ in values))
    if not norm:
        return {'status': 'out_of_vocabulary', 'level': 'unknown', 'score': None, 'terms': []}
    contributions = [(term, value * weight / norm) for term, value, weight in values]
    logit = model['intercept'] + sum(value for _, value in contributions)
    score = 1 / (1 + math.exp(-max(-50, min(50, logit))))
    level = 'high' if score >= .65 else 'review' if score >= .35 else 'unknown'
    terms = [term for term, value in sorted(contributions, key=lambda item: item[1], reverse=True)[:3] if value > .01]
    return {'status': 'assessed', 'model': model['name'], 'level': level,
            'score': round(score, 6), 'terms': terms, 'word_count': len(text.split()),
            'notice_key': 'scam_model_limit'}
