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
def google_news(language, query):
    return 'https://news.google.com/rss/search?' + urllib.parse.urlencode(
        {'q': query + ' when:365d', 'hl': language, 'gl': 'IN', 'ceid': 'IN:' + language})

FEEDS = {
    'en': {
        'BleepingComputer': ('https://www.bleepingcomputer.com/feed/', 'www.bleepingcomputer.com'),
        'The Hacker News': ('https://feeds.feedburner.com/TheHackersNews', 'thehackernews.com'),
    },
    'hi': {
        'Google News — हिन्दी': (google_news('hi', '(एआई OR डीपफेक OR वॉइस क्लोन) (ठगी OR साइबर OR स्कैम)'), 'news.google.com'),
        'Live Hindustan — Cyber Crime': ('https://api.livehindustan.com/feeds/rss/crime/cyber-crime/rssfeed.xml', 'www.livehindustan.com'),
    },
    'te': {
        'Google News — తెలుగు': (google_news('te', '(ఏఐ OR డీప్‌ఫేక్ OR వాయిస్ క్లోన్) (మోసం OR సైబర్ OR స్కామ్)'), 'news.google.com'),
        'TV9 Telugu': ('https://tv9telugu.com/feed', 'tv9telugu.com'),
        'ABP Desam': ('https://telugu.abplive.com/home/feed', 'telugu.abplive.com'),
        'Sakshi': ('https://www.sakshi.com/rss.xml', 'www.sakshi.com'),
    },
}
AI = re.compile(r'\b(?:ai|artificial intelligence|deepfake|deepfakes|voice clon\w*|synthetic voice|generative)\b', re.I)
FRAUD = re.compile(r'\b(?:scam\w*|fraud\w*|phish\w*|impersonat\w*|clon\w*|deceiv\w*|fake|deepfake\w*)\b', re.I)
REGIONAL_AI = {
    'hi': re.compile(r'(?:एआई|आर्टिफिशियल इंटेलिजेंस|डीपफेक|वॉइस क्लोन|आवाज़ की नकल)', re.I),
    'te': re.compile(r'(?:ఏఐ|కృత్రిమ మేధ|డీప్‌?ఫేక్|వాయిస్ క్లోన్|గొంతు నకలు)', re.I),
}
REGIONAL_FRAUD = {
    'hi': re.compile(r'(?:फर्जी|ठगी|धोखाधड़ी|साइबर अपराध|स्कैम|फ्रॉड|नकली|जालसाज)', re.I),
    'te': re.compile(r'(?:నకిలీ|మోసం|సైబర్ నేరం|స్కామ్|ఫ్రాడ్|మోసగాళ్లు)', re.I),
}
REGIONAL_CYBER = {
    'hi': re.compile(r'(?:साइबर|ऑनलाइन|डिजिटल|व्हाट्सऐप|बैंक खाता)', re.I),
    'te': re.compile(r'(?:సైబర్|ఆన్‌లైన్|డిజిటల్|వాట్సాప్|బ్యాంక్ ఖాతా)', re.I),
}
GOOGLE_PUBLISHERS = {
    'hi': {'ABP News', 'AajTak', 'Prabhat Khabar', 'Live Hindustan', 'Dainik Jagran', 'Amar Ujala', 'NDTV India'},
    'te': {'Eenadu', 'Sakshi', 'TV9 Telugu', 'Samayam Telugu', 'ABP Desam', 'NTV Telugu', 'V6 News Telugu', 'Andhra Jyothy'},
}

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

def parse_feed(payload, publisher, allowed_host, now, language='en', max_age_days=365):
    if len(payload) > 2_000_000 or b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
        raise ValueError('Feed is too large or contains an XML declaration we do not accept')
    root = ET.fromstring(payload)
    articles = []
    for item in root.findall('.//item')[:100]:
        title = clean(item.findtext('title'))
        description = clean(item.findtext('description'))
        url = (item.findtext('link') or '').strip()
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in {allowed_host, allowed_host.removeprefix('www.'), 'www.' + allowed_host} or parsed.username or parsed.password:
            continue
        try:
            published = parsedate_to_datetime(item.findtext('pubDate'))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
        if not (now - timedelta(days=max_age_days) <= published <= now + timedelta(minutes=10)):
            continue
        content = title + ' ' + description
        item_publisher = clean(item.findtext('source')) if allowed_host == 'news.google.com' else publisher
        if allowed_host == 'news.google.com' and item_publisher not in GOOGLE_PUBLISHERS[language]:
            continue
        relevant = AI.search(content) and FRAUD.search(content) if language == 'en' else REGIONAL_FRAUD[language].search(content) and (REGIONAL_AI[language].search(content) or REGIONAL_CYBER[language].search(content))
        if not relevant or title.lower().startswith('threatsday:'):
            continue
        # The compact local classifier ranks selected reports. It is not a
        # fact-checker or a probability that the article is true.
        score = assess_message(content[:3000], 'en').get('score') or 0 if language == 'en' else (2 if REGIONAL_AI[language].search(content) else 0) + len(REGIONAL_FRAUD[language].findall(content)) / 10
        # Source's first sentence is an extract, not an invented model summary.
        sentences = [s for s in re.split(r'(?<=[.!?।])\s+', description) if len(s) >= 25][:4]
        matching = [s for s in sentences if (AI.search(s) or FRAUD.search(s))] if language == 'en' else [s for s in sentences if REGIONAL_FRAUD[language].search(s)]
        sentence = max(matching, key=lambda s: assess_message(s, 'en').get('score') or 0, default=(sentences[0] if sentences else description if len(description) >= 25 else ''))
        if len(sentence) > 180:
            sentence = sentence[:177].rsplit(' ', 1)[0] + '…'
        articles.append({'title': title[:200], 'url': url, 'publisher': item_publisher, 'language': language,
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
    target = ROOT / 'static' / 'cautions.json'
    try:
        previous = json.loads(target.read_text())
    except (OSError, ValueError):
        previous = {}
    languages, any_success = {}, False
    for language, feeds in FEEDS.items():
        articles, failures, succeeded = [], [], []
        for publisher, (url, host) in feeds.items():
            try:
                articles.extend(parse_feed(fetch(url), publisher, host, now, language))
                succeeded.append(publisher)
                any_success = True
            except Exception as exc:
                failures.append(publisher)
                print(f'{publisher}: {type(exc).__name__}', file=sys.stderr)
        unique = {article['url']: article for article in articles}
        ranked = sorted(unique.values(), key=lambda a: (a['_score'], a['published_at']), reverse=True)[:6]
        for article in ranked:
            del article['_score']
        carried = False
        if not ranked:
            ranked = previous.get('languages', {}).get(language, {}).get('articles', [])[:6]
            carried = bool(ranked)
        languages[language] = {'sources_checked': succeeded, 'sources_unavailable': failures,
                               'using_previous': carried, 'articles': ranked}
    # Preserve the last known good snapshot if every source fails.
    if not any_success:
        raise SystemExit('All feeds failed. Existing snapshot retained.')
    result = {'updated_at': now.isoformat(), 'max_age_days': 365, 'languages': languages}
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(target)
    print('Updated regional feeds: ' + ', '.join(f'{key}={len(value["articles"])}' for key, value in languages.items()))

if __name__ == '__main__':
    update()
