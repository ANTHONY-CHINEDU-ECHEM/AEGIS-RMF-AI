"""Embedding models exposed through the LlamaIndex embedding interface.

HashingEmbedding is a deterministic lexical embedding. It needs no model download, which keeps
tests, continuous integration and air gapped validation environments reproducible. A sentence
embedding model can be selected in the settings when semantic matching is wanted.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

import numpy as np
from llama_index.core.embeddings import BaseEmbedding

from aegis_rmf.settings import Settings

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be been by for from had has have in into is it its no not of on or so "
    "that the their then there these this to was were when which while with without that".split()
)
SUFFIXES = ("ing", "ed", "es", "s")
BIGRAM_WEIGHT = 0.5


def _stem(token: str) -> str:
    for suffix in SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: len(token) - len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    return [_stem(token) for token in TOKEN.findall(text.lower()) if token not in STOPWORDS and len(token) > 1]


def _bucket(feature: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    return value % dim, 1.0 if (value >> 63) == 0 else -1.0


class HashingEmbedding(BaseEmbedding):
    """Signed feature hashing of stemmed words and word pairs with sublinear term weighting."""

    dim: int = 1024

    def _embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        features = Counter(tokens)
        pairs = Counter(f"{left} {right}" for left, right in zip(tokens, tokens[1:], strict=False))
        vector = np.zeros(self.dim, dtype=np.float64)
        for feature, count in features.items():
            index, sign = _bucket(feature, self.dim)
            vector[index] += sign * (1.0 + math.log(count))
        for feature, count in pairs.items():
            index, sign = _bucket(feature, self.dim)
            vector[index] += sign * BIGRAM_WEIGHT * (1.0 + math.log(count))
        norm = float(np.linalg.norm(vector))
        return (vector / norm).tolist() if norm else vector.tolist()

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)


def build_embedding(settings: Settings) -> BaseEmbedding:
    backend = settings.embedding_backend.strip().lower()
    if backend == "hashing":
        return HashingEmbedding(model_name="aegis_hashing", dim=settings.embedding_dim, embed_batch_size=256)
    if backend == "huggingface":
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        return HuggingFaceEmbedding(model_name=settings.embedding_model)
    raise ValueError(f"Unsupported embedding_backend: {settings.embedding_backend!r}")
