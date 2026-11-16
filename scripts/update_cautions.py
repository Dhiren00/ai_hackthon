"""Build a small source-linked extractive AI scam brief. No paid services."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from detector.scam import assess_message

ROOT = Path(__file__).resolve().parents[1]
FEEDS = {
    'BleepingComputer': ('https://www.bleepingcomputer.com/feed/', 'www.bleepingcomputer.com'),
    'The Hacker News': ('https://feeds.feedburner.com/TheHackersNews', 'thehackernews.com'),
}
AI = re.compile(r'\b(?:ai|artificial intelligence|deepfake|deepfakes|voice clon\w*|synthetic voice|generative)\b', re.I)
FRAUD = re.compile(r'\b(?:scam\w*|fraud\w*|phish\w*|impersonat\w*|clon\w*|deceiv\w*|theft|stolen|fake|deepfake\w*)\b', re.I)

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def clean(value):
    parser = PlainText()
    parser.feed(value or '')
    return ' '.join(unescape(' '.join(parser.parts)).split())

def parse_feed(payload, publisher, allowed_host, now):
    if len(payload) > 2_000_000 or b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
        raise ValueError('Feed is too large or contains an XML declaration we do not accept')
    root = ET.fromstring(payload)
    articles = []
    for item in root.findall('.//item')[:100]:
        title = clean(item.findtext('title'))
        description = clean(item.findtext('description'))
        url = (item.findtext('link') or '').strip()
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname != allowed_host or parsed.username or parsed.password:
            continue
        try:
            published = parsedate_to_datetime(item.findtext('pubDate'))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
        if not (now - timedelta(days=14) <= published <= now + timedelta(minutes=10)):
            continue
        content = title + ' ' + description
        if not AI.search(content) or not FRAUD.search(content):
            continue
        # The compact local classifier ranks selected reports. It is not a
        # fact-checker or a probability that the article is true.
        score = assess_message(content[:3000], 'en').get('score') or 0
        # Source's first sentence is an extract, not an invented model summary.
        sentences = [s for s in re.split(r'(?<=[.!?])\s+', description) if len(s) >= 25][:4]
        sentence = max(sentences, key=lambda s: assess_message(s, 'en').get('score') or 0, default='')
        if len(sentence) > 180:
            sentence = sentence[:177].rsplit(' ', 1)[0] + '…'
        articles.append({'title': title[:200], 'url': url, 'publisher': publisher,
                         'published_at': published.astimezone(timezone.utc).isoformat(),
                         'summary': sentence, '_score': score})
    return articles

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'SHIELD-safety-brief/1.0 (source-linked non-commercial demo)'})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(2_000_001)
    return data

def update():
    now = datetime.now(timezone.utc)
    articles, failures, succeeded = [], [], []
    for publisher, (url, host) in FEEDS.items():
        try:
            articles.extend(parse_feed(fetch(url), publisher, host, now))
            succeeded.append(publisher)
        except Exception as exc:
            failures.append(publisher)
            print(f'{publisher}: {type(exc).__name__}', file=sys.stderr)
    # Preserve the last known good snapshot if every source fails.
    if not succeeded:
        raise SystemExit('All feeds failed. Existing snapshot retained.')
    unique = {article['url']: article for article in articles}
    ranked = sorted(unique.values(), key=lambda a: (a['_score'], a['published_at']), reverse=True)[:6]
    for article in ranked:
        del article['_score']
    result = {'updated_at': now.isoformat(), 'window_days': 14,
              'sources_checked': succeeded, 'sources_unavailable': failures, 'articles': ranked}
    target = ROOT / 'static' / 'cautions.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(target)
    print(f'Updated with {len(ranked)} reports from {len(succeeded)} sources.')

if __name__ == '__main__':
    update()
