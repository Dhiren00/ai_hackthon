"""Deterministic inspect → extract → assess workflow and bounded demo job queue."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import logging
from pathlib import Path
import shutil
from threading import Event, RLock, Thread
import time
from uuid import uuid4
from .scam import assess_message, contains_secret
from .assets import ROOT
from .ingest import InputError, identify, read_text, text_language, extract_screenshot

SPEC=json.loads((ROOT/'workflow'/'analysis.json').read_text())
LOGGER = logging.getLogger('shield.workflow')


def text_result(text):
    if contains_secret(text):
        raise InputError('secret_detected', 'Remove secret codes and identity numbers before checking.')
    language = text_language(text)
    scam = assess_message(text, language)
    if language != 'en':
        return {'verdict_key': 'unsupported_language', 'kind': 'text', 'language': language,
                'notice_key': 'language_limit', 'is_ai': None, 'scam': scam}
    if len(text.split()) < 50:
        return {'verdict_key': 'short_assessed', 'kind': 'text', 'language': language,
                'notice_key': 'short_limit', 'is_ai': None, 'scam': scam}
    from .text import analyze_text
    try:
        result = analyze_text(text)
    except (FileNotFoundError, RuntimeError, ValueError):
        # Message safety still works if the optional large provenance model fails.
        result = {'is_ai': None, 'verdict_key': 'provenance_unavailable', 'notice_key': 'provenance_limit'}
    else:
        result.update(verdict_key='text_ai' if result['is_ai'] else 'text_human', notice_key='text_limit')
    result.update(language=language, scam=scam)
    return result


def run_flow(path=None,text='',progress=lambda stage:None):
    progress('identify')
    kind=identify(path) if path else 'text'
    extracted=None
    if kind=='screenshot':
        progress('extract')
        extracted=extract_screenshot(path)
        text=extracted
    elif kind=='text' and path:
        text=read_text(path)
    progress('analyse')
    if kind in {'text','screenshot'}:
        if len(text)>20000:
            raise InputError('text_large','Maximum input length is 20,000 characters.')
        result=text_result(text)
        if extracted is not None:
            result['extracted_text']=extracted
    elif kind=='audio':
        from .audio import analyze_audio
        result=analyze_audio(path)
        result.update(verdict_key='voice_ai' if result['is_ai'] else 'voice_human',notice_key='voice_limit')
    else:
        from .engine import analyze
        result=analyze(path)
        verdict={'more consistent with genuine':'video_human','suspicious manipulation signals':'video_ai','inconclusive':'inconclusive'}[result['assessment']]
        result.update(verdict_key=verdict,notice_key='video_limit')
    result['input_source'] = 'file_bytes' if path else 'pasted_text'
    result['kind']=kind
    progress('complete')
    return result


class BusyError(RuntimeError):
    pass


class JobManager:
    def __init__(self):
        self.lock=RLock()
        self.jobs={}
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='physiocheck')
        self.closed = Event()
        self.janitor = Thread(target=self._expire, daemon=True, name='result-expiry')
        self.janitor.start()

    def _expire(self):
        while not self.closed.wait(30):
            with self.lock:
                self._prune()

    def _prune(self):
        now=time.monotonic()
        for key in list(self.jobs):
            job=self.jobs[key]
            if job['status'] in {'completed','failed'} and now-job['_updated']>SPEC['limits']['finished_job_ttl_seconds']:
                del self.jobs[key]
        finished=[key for key in self.jobs if self.jobs[key]['status'] in {'completed','failed'}]
        for key in finished[:-32]:
            del self.jobs[key]

    def submit(self,path=None,text='',folder=None):
        with self.lock:
            self._prune()
            if sum(j['status'] in {'queued','running'} for j in self.jobs.values())>=SPEC['limits']['pending_jobs']:
                raise BusyError('The demo queue is full. Try again shortly.')
            key=uuid4().hex
            self.jobs[key]={'id':key,'status':'queued','stage':'queued','history':['queued'],'_updated':time.monotonic(),'result':None,'error':None}
        try:
            self.executor.submit(self._execute,key,path,text,folder)
        except RuntimeError:
            with self.lock:del self.jobs[key]
            raise
        return key

    def _update(self,key,stage):
        if stage not in SPEC['stages']:raise ValueError('Unknown workflow stage')
        with self.lock:
            job=self.jobs[key]
            job.update(stage=stage,status='running',_updated=time.monotonic())
            job['history'].append(stage)

    def _execute(self,key,path,text,folder):
        try:
            result=run_flow(path,text,lambda stage:self._update(key,stage))
            with self.lock:
                self.jobs[key].update(status='completed',result=result,_updated=time.monotonic())
        except Exception as exc:
            # A failed analysis is never converted into a real/fake verdict.
            if isinstance(exc,InputError):
                code=exc.code
            elif isinstance(exc,FileNotFoundError):
                code='model_missing'
            elif 'FFmpeg' in str(exc) or 'Tesseract' in str(exc):
                code='tools_missing'
            elif 'two seconds' in str(exc):
                code='audio_short'
            elif 'silent' in str(exc):
                code='silent_audio'
            elif 'face' in str(exc).lower():
                code='face_required'
            else:
                code='analysis_failed'
            with self.lock:
                LOGGER.warning('Analysis failed: stage=%s code=%s exception=%s',
                    self.jobs[key]['stage'], code, type(exc).__name__)
                self.jobs[key].update(status='failed',stage='failed',error={'code':code},_updated=time.monotonic())
                self.jobs[key]['history'].append('failed')
        finally:
            if folder:shutil.rmtree(folder,ignore_errors=True)

    def get(self,key):
        with self.lock:
            self._prune()
            job=self.jobs.get(key)
            return deepcopy({k:v for k,v in job.items() if not k.startswith('_')}) if job else None

    def shutdown(self):
        self.closed.set()
        self.janitor.join(timeout=2)
        self.executor.shutdown(wait=True)
