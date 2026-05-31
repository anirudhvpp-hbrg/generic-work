"""Embedders for semantic memory search.

The memory store ranks recall by cosine similarity over embeddings. Embedding is
pluggable:

- ``HashEmbedder`` — deterministic, offline, dependency-free (hashed bag-of-words).
  It is lexical, not truly semantic, but gives a working vector pipeline with no
  key or network, so tests and local runs need nothing.
- ``VoyageEmbedder`` — real semantic embeddings via Voyage AI (Anthropic's
  recommended embeddings partner; Anthropic itself has no embeddings endpoint).
  Activated when an API key is present; uses only the standard library.

Any object with ``embed(text) -> list[float]`` works, so other providers
(OpenAI, a local model) can drop in without touching callers.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.request
from typing import Callable, List, Optional, Protocol

_TOKEN = re.compile(r"[a-z0-9]+")


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class Embedder(Protocol):
    def embed(self, text: str) -> List[float]:
        ...


class HashEmbedder:
    """Deterministic offline embedder: hashed bag-of-words, L2-normalized.

    Lexical only (no synonym understanding) but real vectors — a no-dependency
    default and the fallback when no provider key is configured.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in _TOKEN.findall(text.lower()):
            vec[hash(tok) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm:
            vec = [round(v / norm, 4) for v in vec]
        return vec


class VoyageEmbedder:
    """Real semantic embeddings via Voyage AI. Standard-library HTTP only.

    Set ``VOYAGE_API_KEY`` (or pass ``api_key``). ``transport`` is injectable for
    testing; by default it POSTs to the Voyage embeddings endpoint.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "voyage-3",
        transport: Optional[Callable[[str, dict, dict], dict]] = None,
    ):
        self.api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        self.model = model
        self._transport = transport or self._http

    def _http(self, url: str, headers: dict, body: dict) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def embed(self, text: str) -> List[float]:
        if not self.api_key:
            raise RuntimeError(
                "VoyageEmbedder needs an API key (VOYAGE_API_KEY). Use HashEmbedder "
                "for offline runs."
            )
        out = self._transport(
            "https://api.voyageai.com/v1/embeddings",
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            {"input": [text], "model": self.model},
        )
        return out["data"][0]["embedding"]
