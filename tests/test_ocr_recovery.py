"""Reproduce slow OCR without sleeping or loading the large media models."""
import io
from pathlib import Path
import subprocess
import time
import textwrap
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
import pytest

from app import app
from detector import ingest

MESSAGE = "Hi mom this is my new number. My phone broke. Send money to my friend's account urgently and don't call."


def image_bytes(size=(3200, 2600)):
    data = io.BytesIO()
    Image.new('RGB', size, 'white').save(data, format='PNG')
    return data.getvalue()


def completed(client, key):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = client.get('/api/jobs/' + key).json()
        if job['status'] in {'completed', 'failed'}:
            return job
        time.sleep(.01)
    pytest.fail('OCR workflow did not finish')


def mock_ocr(monkeypatch, run):
    monkeypatch.setattr(ingest.shutil, 'which', lambda name: '/usr/bin/tesseract')
    monkeypatch.setattr(ingest, '_check_ocr_languages', lambda *args: None)
    monkeypatch.setattr(ingest.subprocess, 'run', run)


def test_valid_small_upload_recovers_from_first_ocr_timeout(monkeypatch):
    attempts = []
    def run(args, **kwargs):
        with Image.open(args[1]) as image:
            attempts.append((image.size, image.mode, args[args.index('--psm') + 1]))
        assert kwargs['env']['OMP_THREAD_LIMIT'] == '1'
        assert kwargs['env']['OMP_NUM_THREADS'] == '1'
        if len(attempts) == 1:
            raise subprocess.TimeoutExpired(args, kwargs['timeout'])
        return SimpleNamespace(returncode=0, stdout=MESSAGE, stderr='')
    mock_ocr(monkeypatch, run)
    data = image_bytes()
    assert len(data) < 50 * 1024 * 1024
    with TestClient(app) as client:
        submitted = client.post('/api/jobs', files={'file': ('phone.png', data, 'image/png')})
        assert submitted.status_code == 202
        assert submitted.headers['x-shield-release'] == 'screenshot-safe-default-v4'
        job = completed(client, submitted.json()['id'])
    assert job['status'] == 'completed', job
    assert job['result']['extracted_text'] == MESSAGE
    assert job['result']['scam']['level'] == 'high'
    assert len(attempts) == 2
    assert attempts[0][0][0] * attempts[0][0][1] <= 1_200_000
    assert attempts[1][0][0] * attempts[1][0][1] <= 600_000
    assert [attempt[2] for attempt in attempts] == ['11', '6']
    assert all(attempt[1] == 'L' for attempt in attempts)


@pytest.mark.parametrize(('on_render', 'setting'), [('true', None), (None, '0')])
def test_long_screenshot_keeps_ocr_and_scam_results_without_provenance(monkeypatch, on_render, setting):
    from detector import text

    for name, value in [('RENDER', on_render), ('SHIELD_TEXT_PROVENANCE', setting)]:
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    passage = ' '.join([MESSAGE] * 5)

    def unexpected_inference(_):
        pytest.fail('Screenshot assessment must bypass the authorship inference lock')

    monkeypatch.setattr(text, 'analyze_text', unexpected_inference)
    mock_ocr(monkeypatch, lambda *args, **kwargs:
             SimpleNamespace(returncode=0, stdout=passage, stderr=''))
    with TestClient(app) as client:
        submitted = client.post('/api/jobs', files={'file': ('phone.png', image_bytes())})
        assert submitted.status_code == 202
        job = completed(client, submitted.json()['id'])
    assert job['status'] == 'completed', job
    assert job['result']['extracted_text'] == passage
    assert job['result']['scam']['score'] is not None
    assert job['result']['is_ai'] is None
    assert job['result']['verdict_key'] == 'provenance_unavailable'


def test_text_provenance_defaults_and_explicit_override(monkeypatch):
    from detector.text import text_provenance_enabled

    monkeypatch.delenv('SHIELD_TEXT_PROVENANCE', raising=False)
    monkeypatch.delenv('RENDER', raising=False)
    assert text_provenance_enabled()
    monkeypatch.setenv('RENDER', 'true')
    assert not text_provenance_enabled()
    monkeypatch.setenv('SHIELD_TEXT_PROVENANCE', '1')
    assert text_provenance_enabled()


def test_both_attempts_fail_honestly_then_queue_recovers(monkeypatch):
    def run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs['timeout'])
    mock_ocr(monkeypatch, run)
    with TestClient(app) as client:
        submitted = client.post('/api/jobs', files={'file': ('phone.png', image_bytes())})
        job = completed(client, submitted.json()['id'])
        assert job['status'] == 'failed'
        assert job['error']['code'] == 'ocr_timed_out'
        assert job['result'] is None
        next_job = client.post('/api/jobs', data={'text': MESSAGE})
        assert completed(client, next_job.json()['id'])['status'] == 'completed'


def test_cached_local_language_packs_need_no_subprocess(monkeypatch, tmp_path):
    for name in ['eng', 'hin', 'tel']:
        (tmp_path / (name + '.traineddata')).touch()
    def unexpected(*args, **kwargs):
        pytest.fail('Local pack lookup must not launch Tesseract')
    monkeypatch.setattr(ingest.subprocess, 'run', unexpected)
    ingest._check_ocr_languages.cache_clear()
    ingest._check_ocr_languages('/tesseract', ('--tessdata-dir', str(tmp_path)))
    ingest._check_ocr_languages('/tesseract', ('--tessdata-dir', str(tmp_path)))
    assert ingest._check_ocr_languages.cache_info().hits == 1
    ingest._check_ocr_languages.cache_clear()


def test_transparency_is_white_and_retry_never_upscales():
    transparent = Image.new('RGBA', (200, 100), (0, 0, 0, 0))
    prepared = ingest._prepare_ocr_image(transparent)
    assert prepared.getpixel((0, 0)) == 255
    retry = ingest._prepare_ocr_image(prepared, 600_000, 1100, upscale=False)
    assert retry.width <= prepared.width and retry.height <= prepared.height


def test_media_timeout_has_specific_error_code(monkeypatch, tmp_path):
    path = tmp_path / 'voice.wav'
    path.write_bytes(b'RIFF' + bytes(20))
    monkeypatch.setattr(ingest.shutil, 'which', lambda name: '/usr/bin/ffprobe')
    def run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs['timeout'])
    monkeypatch.setattr(ingest.subprocess, 'run', run)
    with pytest.raises(ingest.InputError) as caught:
        ingest.identify(path)
    assert caught.value.code == 'media_inspection_timeout'


def test_language_inspection_timeout_is_distinct(monkeypatch):
    def run(args, **kwargs):
        assert kwargs['env']['OMP_THREAD_LIMIT'] == '1'
        raise subprocess.TimeoutExpired(args, kwargs['timeout'])
    monkeypatch.setattr(ingest.subprocess, 'run', run)
    ingest._check_ocr_languages.cache_clear()
    with pytest.raises(ingest.InputError) as caught:
        ingest._check_ocr_languages('/tesseract', ())
    assert caught.value.code == 'ocr_setup_timeout'


def test_real_short_screenshot_upload_completes():
    image = Image.new('RGB', (1200, 300), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 32)
    for row, line in enumerate(textwrap.wrap(MESSAGE, 60)):
        draw.text((30, 30 + row * 50), line, font=font, fill='black')
    data = io.BytesIO()
    image.save(data, format='PNG')
    with TestClient(app) as client:
        submitted = client.post('/api/jobs', files={'file': ('message.png', data.getvalue(), 'image/png')})
        # Real OCR can take longer than the mocked timeout tests.
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            job = client.get('/api/jobs/' + submitted.json()['id']).json()
            if job['status'] in {'completed', 'failed'}:
                break
            time.sleep(.05)
        assert job['status'] == 'completed', job
        assert 'mom' in job['result']['extracted_text'].lower()
        assert job['result']['scam']['score'] is not None
