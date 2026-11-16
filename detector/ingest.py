"""Identify uploaded content and extract screenshot text using local tools."""
import json
from functools import lru_cache
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unicodedata
from PIL import Image, ImageOps, UnidentifiedImageError
from .assets import ROOT

class InputError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code=code


def identify(path):
    """Use signatures, image decoding and media streams, never client MIME alone."""
    head=path.read_bytes()[:512] if path.stat().st_size<1024 else _head(path)
    if head.startswith((b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff',b'GIF8',b'BM')) or (head[:4]==b'RIFF' and head[8:12]==b'WEBP'):
        try:
            with Image.open(path) as image:
                if image.width*image.height>16_000_000:
                    raise InputError('image_large','Screenshot is too large. Resize it below 16 megapixels.')
                if image.format not in {'PNG','JPEG','WEBP'}:
                    raise InputError('unsupported_file','Use a PNG, JPEG or WebP screenshot.')
                image.verify()
            return 'screenshot'
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
            raise InputError('invalid_file','This image cannot be decoded.') from exc
    # An image extension with no valid signature is not accepted as arbitrary text.
    if path.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.gif','.bmp'}:
        raise InputError('invalid_file','This image cannot be decoded.')
    if path.suffix.lower()=='.txt':
        read_text(path)
        return 'text'
    ffprobe=shutil.which('ffprobe')
    if not ffprobe:
        raise InputError('tools_missing','FFmpeg/ffprobe is missing. Run the documented setup.')
    try:
        response=subprocess.run([ffprobe,'-v','error','-show_streams','-of','json',str(path)],capture_output=True,timeout=20)
    except subprocess.TimeoutExpired as exc:
        raise InputError('media_inspection_timeout','Media inspection timed out on the server.') from exc
    if response.returncode:
        raise InputError('unsupported_file','Use text, a screenshot, an audio recording or a video.')
    try:
        streams=json.loads(response.stdout).get('streams',[])
    except (ValueError,AttributeError) as exc:
        raise InputError('invalid_file','Could not inspect this media.') from exc
    # Album art is a video stream but must not turn a voice recording into video.
    if any(s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic') for s in streams):
        return 'video'
    if any(s.get('codec_type')=='audio' for s in streams):
        return 'audio'
    raise InputError('unsupported_file','No supported audio or video stream was found.')


def _head(path):
    with path.open('rb') as source:
        return source.read(512)


def read_text(path):
    if path.stat().st_size>100_000:
        raise InputError('text_large','Text file is too large.')
    try:
        text=path.read_text(encoding='utf-8-sig')
    except UnicodeError as exc:
        raise InputError('invalid_file','Text files must use UTF-8 encoding.') from exc
    if '\x00' in text:
        raise InputError('invalid_file','This is not a plain text file.')
    return text.strip()


def text_language(text):
    letters=[c for c in text if c.isalpha()]
    if not letters:
        return 'unknown'
    if sum('\u0c00'<=c<='\u0c7f' for c in letters)>0.1*len(letters):
        return 'te'
    if sum('\u0900'<=c<='\u097f' for c in letters)>0.1*len(letters):
        return 'hi'
    # Do not mistake other scripts for supported English prose.
    if sum('LATIN' in unicodedata.name(c,'') for c in letters)<0.9*len(letters):
        return 'other'
    return 'en'  # Latin-script assumption, not full language identification.


def ocr_config():
    local=ROOT/'external'/'tessdata'
    directory=os.environ.get('PHYSIOCHECK_TESSDATA')
    if directory:
        return ['--tessdata-dir',directory]
    if all((local/f'{lang}.traineddata').is_file() for lang in ['eng','hin','tel']):
        return ['--tessdata-dir',str(local)]
    return []


def _ocr_environment():
    return {**os.environ, 'OMP_THREAD_LIMIT': '1', 'OMP_NUM_THREADS': '1'}


@lru_cache(maxsize=4)
def _check_ocr_languages(executable, config):
    # The pinned local packs can be inspected without starting a subprocess.
    if '--tessdata-dir' in config:
        directory = Path(config[config.index('--tessdata-dir') + 1])
        available = {name for name in ('eng', 'hin', 'tel') if (directory / (name + '.traineddata')).is_file()}
    else:
        try:
            response = subprocess.run([executable, '--list-langs', *config],
                capture_output=True, text=True, timeout=30, env=_ocr_environment())
        except subprocess.TimeoutExpired as exc:
            raise InputError('ocr_setup_timeout', 'OCR language inspection timed out.') from exc
        if response.returncode:
            raise InputError('tools_missing', 'Tesseract language inspection failed.')
        available = set(response.stdout.split())
    if not {'eng', 'hin', 'tel'}.issubset(available):
        raise InputError('ocr_languages_missing', 'Install English, Hindi and Telugu OCR packs, or run python scripts/setup_ocr.py.')


def _prepare_ocr_image(original, max_pixels=1_200_000, max_side=1600, upscale=True):
    image = ImageOps.exif_transpose(original)
    scale = min(1.0, max_side / max(image.size), (max_pixels / (image.width * image.height)) ** .5)
    if scale < 1:
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)
    # Upscale genuinely tiny screenshots only, without exceeding the budget.
    elif upscale and image.width < 640 and image.width * image.height * 4 <= max_pixels:
        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    # Composite only after resizing, avoiding several full-resolution RGBA
    # copies in the memory-limited server. Transparent screenshots use white.
    image = image.convert('RGBA')
    background = Image.new('RGBA', image.size, 'white')
    background.alpha_composite(image)
    return background.convert('L')


def extract_screenshot(path):
    executable=shutil.which('tesseract')
    if not executable:
        raise InputError('tools_missing','Tesseract is missing. Run the documented setup.')
    config=ocr_config()
    _check_ocr_languages(executable, tuple(config))
    with Image.open(path) as original:
        image = _prepare_ocr_image(original)
    with tempfile.TemporaryDirectory(prefix='physiocheck-ocr-') as folder:
        clean = Path(folder) / 'screenshot.png'
        # Retry only OCR, with less pixel work and a simple block layout. Never
        # turn an OCR failure into an invented text or scam classification.
        for attempt, (pixels, side, psm, seconds) in enumerate([
                (1_200_000, 1600, '11', 90), (600_000, 1100, '6', 60)]):
            prepared = image if attempt == 0 else _prepare_ocr_image(image, pixels, side, upscale=False)
            prepared.save(clean)
            try:
                response = subprocess.run([executable, str(clean), 'stdout', *config,
                    '-l', 'eng+hin+tel', '--psm', psm], capture_output=True, text=True,
                    timeout=seconds, env=_ocr_environment())
                break
            except subprocess.TimeoutExpired as exc:
                if attempt == 1:
                    raise InputError('ocr_timed_out', 'Both bounded OCR attempts timed out on the server.') from exc
    if response.returncode:
        raise InputError('ocr_failed','Text extraction failed. Try a clearer screenshot.')
    text=response.stdout.strip()
    if not text:
        raise InputError('ocr_empty','No readable text was found. Try a clearer screenshot.')
    if len(text)>20000:
        raise InputError('text_large','Screenshot contains more than 20,000 characters. Crop it first.')
    return text
