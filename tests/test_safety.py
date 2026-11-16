"""Normal entry points for message triage, privacy and evidence metadata."""
import hashlib
import json
from pathlib import Path
import time
from fastapi.testclient import TestClient
import pytest
from app import app
from detector.scam import assess_message, contains_secret, input_digest

ROOT = Path(__file__).resolve().parents[1]


def wait_result(client, key):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get('/api/jobs/' + key).json()
        if job['status'] in {'completed', 'failed'}:
            return job
        time.sleep(.01)
    pytest.fail('Short message workflow did not finish')


def test_short_impersonation_message_uses_actual_trained_classifier():
    text = "Hi mom this is my new number. My phone broke. Send money to my friend's account urgently and don't call."
    with TestClient(app) as client:
        response = client.post('/api/jobs', data={'text': text})
        result = wait_result(client, response.json()['id'])
        assert result['status'] == 'completed', result
        assert result['result']['is_ai'] is None
        assert result['result']['scam']['level'] == 'high'
        assert result['result']['input_sha256'] == hashlib.sha256(text.encode()).hexdigest()
        assert client.get('/api/jobs/' + response.json()['id']).headers['cache-control'] == 'no-store'


def test_warning_message_is_not_marked_high_risk():
    result = assess_message('The placement cell says no employer should ask you for a joining deposit.', 'en')
    assert result['level'] == 'unknown'
    assert result['score'] < .35


@pytest.mark.parametrize('language', ['hi', 'te', 'unknown'])
def test_language_limit_has_no_invented_message_score(language):
    result = assess_message('अनजान संदेश ఇది ఒక సందేశం', language)
    assert result['score'] is None and result['level'] == 'unknown'


@pytest.mark.parametrize('text', ['My OTP is 123456', 'PIN: 1234', '1234 5678 9012', '1234 5678 9012 3456'])
def test_detect_secret_patterns(text):
    assert contains_secret(text)


def test_secret_input_fails_without_a_verdict_and_queue_recovers():
    with TestClient(app) as client:
        response = client.post('/api/jobs', data={'text': 'My OTP is 123456'})
        result = wait_result(client, response.json()['id'])
        assert result['status'] == 'failed' and result['error']['code'] == 'secret_detected'
        assert result['result'] is None
        follow = client.post('/api/jobs', data={'text': 'See you at class tomorrow.'})
        assert wait_result(client, follow.json()['id'])['status'] == 'completed'


def test_hash_is_sensitive_to_original_file_bytes(tmp_path):
    path = tmp_path / 'evidence.txt'
    path.write_bytes(b'the original file\n')
    original = input_digest(path)
    path.write_bytes(b'the changed file\n')
    assert original != input_digest(path)
    assert original == hashlib.sha256(b'the original file\n').hexdigest()


def test_holdout_does_not_overlap_training_and_artifacts_match():
    train = (ROOT/'data/scam_train.tsv').read_bytes()
    holdout = (ROOT/'data/scam_holdout.tsv').read_bytes()
    texts = lambda data: {line.split('\t', 1)[1] for line in data.decode().splitlines()}
    assert not texts(train).intersection(texts(holdout))
    model = json.loads((ROOT/'detector/scam_model.json').read_text())
    report = json.loads((ROOT/'reports/scam_benchmark.json').read_text())
    assert model['training_sha256'] == report['model_training_sha256'] == hashlib.sha256(train).hexdigest()
    assert report['holdout_sha256'] == hashlib.sha256(holdout).hexdigest()
    assert len(report['predictions']) == 60
    for prediction, line in zip(report['predictions'], holdout.decode().splitlines()):
        assert prediction['score'] == assess_message(line.split('\t', 1)[1], 'en')['score']


def test_ui_handlers_reference_existing_elements_and_translation_keys():
    import re
    html = (ROOT/'static/index.html').read_text()
    js = (ROOT/'static/safety.js').read_text()
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    references = set(re.findall(r"\$\('([^']+)'\)", html + js))
    assert references <= ids, references - ids
    keys = set(re.findall(r'data-i18n="([^"]+)"', html))
    keys.update(re.findall(r"\bt\('([^']+)'\)", js))
    locales = json.loads((ROOT/'static/i18n.json').read_text())
    for locale in locales.values():
        assert keys <= set(locale), keys - set(locale)
