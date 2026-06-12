"""Mock embedding provider: determinism, dimension, and clustering behavior."""

from app.providers.embeddings import (
    EMBED_DIM,
    MockEmbeddingProvider,
    cosine,
    get_embedding_provider,
)


def test_dim_is_1024():
    p = MockEmbeddingProvider()
    assert p.dim == EMBED_DIM == 1024
    assert len(p.embed("Samsung Galaxy S26")) == 1024


def test_deterministic():
    p = MockEmbeddingProvider()
    assert p.embed("OnePlus 14 review") == p.embed("OnePlus 14 review")


def test_near_duplicates_cluster_above_threshold():
    p = MockEmbeddingProvider()
    a = p.embed("Samsung Galaxy S26 Ultra leaked specs surface online")
    b = p.embed("Leaked specs of Samsung Galaxy S26 Ultra surface online")
    assert cosine(a, b) > 0.85


def test_unrelated_topics_below_threshold():
    p = MockEmbeddingProvider()
    a = p.embed("Samsung Galaxy S26 Ultra leaked specs")
    b = p.embed("OnePlus 13R review midrange battery king")
    assert cosine(a, b) < 0.85


def test_hinglish_tokens_supported():
    p = MockEmbeddingProvider()
    v = p.embed("Samsung का नया फोन ₹30000 में")
    assert any(x != 0 for x in v)  # devanagari + latin tokens both counted


def test_resolver_mock():
    assert get_embedding_provider("mock").name == "mock:hash-1024"
