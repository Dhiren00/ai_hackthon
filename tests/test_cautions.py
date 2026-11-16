from datetime import datetime, timezone
from scripts.update_cautions import parse_feed

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)

def test_feed_selects_only_recent_ai_fraud_and_trusted_urls():
    xml = b'''<rss><channel>
    <item><title>AI voice scam targets families</title><description>A fake caller requested money.</description><link>https://www.bleepingcomputer.com/news/safety/example/</link><pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate></item>
    <item><title>AI fraud link</title><description>Fraud</description><link>https://bad.example/path</link><pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate></item>
    <item><title>AI voice scam</title><description>Fraud</description><link>https://www.bleepingcomputer.com/old</link><pubDate>Sun, 01 Nov 2026 00:00:00 GMT</pubDate></item>
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
