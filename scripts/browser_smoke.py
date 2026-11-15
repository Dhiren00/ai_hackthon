"""Real browser smoke checks of the unified app; GitHub CI saves screenshots."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
import math
import struct
from PIL import Image,ImageDraw,ImageFont
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'browser-results'
TEXT=('The students recorded their observations in a notebook during the afternoon lesson. '
      'They compared the temperature of water in several containers and discussed why the measurements changed. '
      'Each group repeated the experiment carefully before sharing its results with the class. '
      'The teacher asked everyone to explain the evidence and describe one improvement for the next experiment.')
OUTPUT.mkdir(exist_ok=True)
server=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8765'],cwd=ROOT)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=1).close();break
        except Exception:
            if server.poll() is not None:raise RuntimeError('App server exited')
            time.sleep(.2)
    else:raise RuntimeError('App did not start')
    with tempfile.TemporaryDirectory() as folder,sync_playwright() as p:
        options={'headless':True}
        if os.getenv('PHYSIOCHECK_BROWSER'):
            options['executable_path']=os.environ['PHYSIOCHECK_BROWSER']
        browser=p.chromium.launch(**options)
        page=browser.new_page(viewport={'width':1100,'height':900})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8765',wait_until='networkidle')
        assert page.locator('textarea').count()==1
        polls={'failures':0}
        def interrupted_poll(route):
            if polls['failures']<2:
                polls['failures']+=1;route.abort()
            else:route.continue_()
        page.route('**/api/jobs/*',interrupted_poll)
        page.locator('#input').fill(TEXT)
        page.locator('#submit').click()
        page.locator('#result').wait_for(state='visible',timeout=120000)
        assert 'text' in page.locator('#kind').inner_text().lower()
        page.screenshot(path=str(OUTPUT/'desktop-text.png'),full_page=True)
        page.locator('#language').select_option('hi')
        assert page.locator('html').get_attribute('lang')=='hi'
        assert page.locator('#submit').inner_text()=='जाँच करें'
        page.locator('#language').select_option('te')
        assert page.locator('#submit').inner_text()=='తనిఖీ చేయండి'
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(OUTPUT/'mobile-telugu.png'),full_page=True)
        page.locator('#again').click()
        page.locator('#input').fill('ఇది తెలుగులో రాసిన వాక్యం. భాషను సరిగ్గా గుర్తించాలి.')
        page.locator('#submit').click()
        page.locator('#result').wait_for(state='visible',timeout=30000)
        assert 'ఈ భాషలో' in page.locator('#verdict').inner_text()
        page.locator('#language').select_option('en')
        page.locator('#again').click()
        # Actual screenshot OCR and model inference.
        import textwrap
        image=Image.new('RGB',(1200,650),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',26)
        for i,line in enumerate(textwrap.wrap(TEXT,75)):draw.text((35,35+i*45),line,font=font,fill='black')
        screenshot=Path(folder)/'screenshot.png';image.save(screenshot)
        page.locator('#file').set_input_files(str(screenshot))
        page.locator('#submit').click()
        page.locator('#result').wait_for(state='visible',timeout=120000)
        assert 'screenshot' in page.locator('#kind').inner_text().lower()
        assert 'observations' in page.locator('#ocr-text').text_content().lower()
        page.screenshot(path=str(OUTPUT/'mobile-screenshot.png'),full_page=True)
        page.locator('#again').click()
        voice=Path(folder)/'voice.wav'
        with wave.open(str(voice),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
            wav.writeframes(b''.join(struct.pack('<h',int(4000*math.sin(i*2*math.pi*250/16000))) for i in range(64000)))
        page.locator('#file').set_input_files(str(voice));page.locator('#submit').click()
        page.locator('#result').wait_for(state='visible',timeout=120000)
        assert 'voice' in page.locator('#kind').inner_text().lower()
        assert 'performed poorly' in page.locator('#notice').inner_text()
        page.locator('#again').click()
        # A corrupt upload must show an error, then allow a new check.
        page.locator('#file').set_input_files({'name':'broken.png','mimeType':'image/png','buffer':b'invalid'})
        page.locator('#submit').click();page.locator('#error').wait_for(state='visible',timeout=30000)
        assert page.locator('#submit').is_enabled()
        page.locator('#remove').click();page.locator('#input').fill(TEXT)
        page.locator('#submit').click();page.locator('#result').wait_for(state='visible',timeout=120000)
        assert not errors,errors
        browser.close()
        print('Browser checks passed: text, screenshot, voice, languages, mobile layout, error recovery.')
finally:
    server.terminate()
    try:server.wait(timeout=15)
    except subprocess.TimeoutExpired:server.kill();server.wait()
