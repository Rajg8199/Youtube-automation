"""Pure SEO helper tests (no DB/LLM)."""

from app.publishing.seo import _affiliate_links, _chapters_from_scenes


def test_affiliate_links_build_amazon_and_flipkart():
    links = _affiliate_links(["OnePlus 14", "Samsung Galaxy S26"])
    assert len(links) == 2
    a = links[0]
    assert a["device"] == "OnePlus 14"
    assert "amazon.in/s?k=OnePlus+14" in a["amazon_url"]
    assert "flipkart.com/search?q=OnePlus+14" in a["flipkart_url"]


def test_affiliate_links_empty():
    assert _affiliate_links([]) == []


def test_chapters_cumulative_timestamps():
    scenes = [
        {"template": "intro", "caption": "Hook", "duration": 15},
        {"template": "price-tracker", "caption": "Price", "duration": 50},
        {"template": "chart", "caption": "Specs", "duration": 20},
    ]
    chapters = _chapters_from_scenes(scenes)
    assert [c["time"] for c in chapters] == ["0:00", "0:15", "1:05"]
    assert chapters[1]["label"] == "Price"
