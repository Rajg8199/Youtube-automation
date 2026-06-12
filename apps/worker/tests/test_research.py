"""Research adapters: offline RSS parsing + source factory mapping."""

import httpx

from app.providers.research import (
    RedditSource,
    RSSSource,
    build_source,
)

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Test Feed</title>
  <item>
    <title>Samsung Galaxy S26 Ultra leaked specs surface</title>
    <link>https://example.com/s26</link>
    <guid>guid-s26</guid>
    <pubDate>Tue, 10 Jun 2025 09:00:00 GMT</pubDate>
    <description>Leak details</description>
  </item>
  <item>
    <title>OnePlus 14 review</title>
    <link>https://example.com/op14</link>
    <guid>guid-op14</guid>
  </item>
</channel></rss>"""


def test_rss_parses_offline():
    # feedparser.parse accepts a raw XML string in place of a URL.
    src = RSSSource("Test", SAMPLE_RSS, user_agent="ua")
    signals = src.poll()
    assert len(signals) == 2
    first = signals[0]
    assert first.external_id == "guid-s26"
    assert first.title.startswith("Samsung Galaxy S26")
    assert first.url == "https://example.com/s26"
    assert first.published_at is not None


def test_rss_skips_titleless_entries():
    xml = SAMPLE_RSS.replace(
        "<title>OnePlus 14 review</title>", "<title></title>"
    )
    src = RSSSource("Test", xml, user_agent="ua")
    assert len(src.poll()) == 1


def test_build_source_maps_types():
    rss = build_source(
        {"name": "GSMArena", "type": "rss", "url": "https://x/feed"}, "ua"
    )
    reddit = build_source(
        {"name": "r/Android", "type": "reddit", "url": "https://x/r.json"}, "ua"
    )
    none_url = build_source({"name": "x", "type": "rss", "url": None}, "ua")
    unsupported = build_source(
        {"name": "yt", "type": "youtube_channel", "url": "https://x"}, "ua"
    )
    assert isinstance(rss, RSSSource)
    assert isinstance(reddit, RedditSource)
    assert none_url is None
    assert unsupported is None


def test_reddit_parses_with_mock_transport(monkeypatch):
    payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc123",
                        "title": "Best phone under 30000 INR?",
                        "permalink": "/r/PhoneIndia/comments/abc123/",
                        "selftext": "looking for camera",
                        "created_utc": 1739000000,
                    }
                }
            ]
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)
    src = RedditSource("r/PhoneIndia", "https://reddit/x.json", user_agent="ua")
    signals = src.poll()
    assert len(signals) == 1
    assert signals[0].external_id == "abc123"
    assert signals[0].url.endswith("/abc123/")
