"""Embedding providers (1024-dim).

Default real backend: BGE-M3 (BAAI), self-hosted via sentence-transformers — 1024-dim
native, strong multilingual incl. Hindi, free per call (ADR-0007).

The mock backend is a deterministic token-hashing embedder: similar texts produce high
cosine similarity, so clustering logic (cosine > 0.85) is testable without the model.
Select via env EMBEDDINGS_BACKEND=mock|bge-m3 (tests force mock).
"""

from __future__ import annotations

import math
import re
from typing import Protocol, runtime_checkable

EMBED_DIM = 1024

_TOKEN_RE = re.compile(r"[a-z0-9ऀ-ॿ]+")  # latin + devanagari


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    dim: int

    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class MockEmbeddingProvider:
    """Deterministic token-hashing embedder. No model, no network."""

    name = "mock:hash-1024"
    dim = EMBED_DIM

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _tokenize(text)
        for tok in tokens:
            # Stable hash via Python's hash is salted per-process; use a fixed FNV-1a.
            idx = _fnv1a(tok) % self.dim
            vec[idx] += 1.0
        # L2 normalize so cosine == dot product and magnitudes don't dominate.
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


def _fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class BGEM3EmbeddingProvider:
    """BGE-M3 dense embeddings (1024-dim). Lazily loads the model on first use."""

    name = "bge-m3"
    dim = EMBED_DIM

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        self._model_name = model_name
        self._model = None  # loaded lazily

    def _ensure(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # heavy import

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure()
        vectors = model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        out = [v.tolist() for v in vectors]
        for v in out:
            if len(v) != self.dim:
                raise ValueError(
                    f"BGE-M3 returned {len(v)} dims, expected {self.dim}"
                )
        return out


def get_embedding_provider(backend: str) -> EmbeddingProvider:
    if backend == "bge-m3":
        return BGEM3EmbeddingProvider()
    if backend == "mock":
        return MockEmbeddingProvider()
    raise ValueError(f"unknown embeddings backend: {backend}")
