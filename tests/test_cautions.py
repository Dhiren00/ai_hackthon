from datetime import datetime, timezone
from scripts.update_cautions import parse_feed

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)

def test_feed_selects_only_recent_ai_fraud_and_trusted_urls():
    xml = b'''<rss><channel>
    <item><title>AI voice scam targets families</title><description>A fake caller requested money.</description><link>https://www.bleepingcomputer.com/news/safety/example/</link><pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate></item>
    <item><title>AI fraud link</title><description>Fraud</description><link>https://bad.example/path</link><pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate></item>
    <item><title>AI voice scam</title><description>Fraud</description><link>https://www.bleepingcomputer.com/old</link><pubDate>Sat, 01 Nov 2025 00:00:00 GMT</pubDate></item>
    <item><title>New security update</title><description>Updates</description><link>https://www.bleepingcomputer.com/new</link><pubDate>Sun, 15 Nov 2026 00:00:00 GMT</pubDate></item>
    </channel></rss>'''
    result = parse_feed(xml, 'BleepingComputer', 'www.bleepingcomputer.com', NOW)
    assert len(result) == 1
    assert result[0]['summary'] == 'A fake caller requested money.'
    assert result[0]['published_at'].startswith('2026-11-15')

def test_xml_entity_declaration_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        parse_feed(b'<!DOCTYPE rss [<!ENTITY x "X">]><rss/>', 'Source', 'example.com', NOW)

def test_telugu_feed_keeps_regional_ai_scam_from_approved_publisher():
    xml = b'''<rss><channel><item>
    <title>AI voice scam</title><description>regional report</description>
    <link>https://news.google.com/rss/articles/example</link>
    <source>Sakshi</source><pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate>
    </item></channel></rss>'''.replace(b'AI voice scam', 'ఏఐ వాయిస్ మోసం'.encode())
    result = parse_feed(xml, 'Google News — తెలుగు', 'news.google.com', NOW, 'te')
    assert len(result) == 1
    assert result[0]['publisher'] == 'Sakshi'
    assert result[0]['language'] == 'te'

def test_google_feed_rejects_unapproved_regional_publisher():
    xml = '''<rss><channel><item><title>ఏఐ వాయిస్ మోసం</title><description>సైబర్ మోసం</description>
    <link>https://news.google.com/rss/articles/example</link><source>Unknown Blog</source>
    <pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>'''.encode()
    assert parse_feed(xml, 'Google News — తెలుగు', 'news.google.com', NOW, 'te') == []
