"""Storage Manager + Memory Manager — the durable persistence tier.

This is infrastructure: where bytes live, how they persist, and what gets
evicted. It is distinct from the cognitive engine's semantic Memory (what
context matters) — the engine's Memory stage is *backed by* this.

- ``StorageManager`` — key-value store. When given a ``path`` it is durable:
  every write is flushed to disk atomically (temp file + ``os.replace``), so a
  new manager pointed at the same path resumes the prior state and a crash
  mid-write cannot corrupt the file.
- ``MemoryManager`` — capacity-bounded memory with LRU eviction, backed by the
  storage manager. It rehydrates from disk on startup and offers dependency-free
  semantic ``search`` (token-overlap) over stored text — a durable stand-in for
  a vector store that a real embedding backend can later replace.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

# Reserved key prefix so memory records never collide with arbitrary kv entries.
_MEM_PREFIX = "mem::"
_TOKEN = re.compile(r"[a-z0-9]+")


class StorageManager:
    def __init__(self, path: Optional[str] = None, auto_persist: bool = True) -> None:
        self.path = path
        self.auto_persist = auto_persist
        self._data: Dict[str, Any] = {}
        if path and os.path.exists(path):
            self.load()

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._maybe_persist()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._maybe_persist()

    def keys(self) -> List[str]:
        return list(self._data.keys())

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._data.items())

    def _maybe_persist(self) -> None:
        if self.auto_persist and self.path:
            self.persist()

    def persist(self) -> None:
        """Atomic write: serialize to a temp file in the same dir, then replace."""
        if not self.path:
            return
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(self._data, fh)
            os.replace(tmp, self.path)   # atomic on POSIX and Windows
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def load(self) -> None:
        if self.path and os.path.exists(self.path):
            with open(self.path) as fh:
                self._data = json.load(fh)


class MemoryManager:
    """Capacity-bounded, durable memory with LRU eviction and semantic search.

    Pass an ``embedder`` (anything with ``embed(text) -> list[float]``) to rank
    recall by cosine similarity over embeddings; without one, ``search`` falls
    back to token overlap. Embeddings are stored on each record, so they persist
    and rehydrate alongside the text.
    """

    def __init__(
        self,
        capacity: int = 128,
        storage: Optional[Any] = None,
        embedder: Optional[Any] = None,
    ) -> None:
        self.capacity = max(1, capacity)
        self.storage = storage or StorageManager()
        self.embedder = embedder
        self._lru: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self.evicted: List[str] = []
        self._seq = 0
        self._rehydrate()

    # --- durability --------------------------------------------------------

    def _rehydrate(self) -> None:
        """Rebuild the LRU from any memory records already in storage."""
        records = [
            (k[len(_MEM_PREFIX):], v)
            for k, v in self.storage.items()
            if k.startswith(_MEM_PREFIX)
        ]
        # Restore recency order via the persisted sequence number.
        records.sort(key=lambda kv: kv[1].get("seq", 0))
        for key, record in records:
            self._lru[key] = record
            self._seq = max(self._seq, record.get("seq", 0) + 1)
        self._enforce_capacity()

    def _enforce_capacity(self) -> None:
        while len(self._lru) > self.capacity:
            old_key, _ = self._lru.popitem(last=False)
            self.storage.delete(_MEM_PREFIX + old_key)
            self.evicted.append(old_key)

    # --- writes / reads ----------------------------------------------------

    def write(self, key: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        record = {"text": text, "meta": meta or {}, "seq": self._seq}
        if self.embedder is not None:
            record["embedding"] = self.embedder.embed(text)
        self._seq += 1
        if key in self._lru:
            self._lru.move_to_end(key)
        self._lru[key] = record
        self.storage.put(_MEM_PREFIX + key, record)   # durable when storage has a path
        self._enforce_capacity()

    def read(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self._lru:
            return None
        self._lru.move_to_end(key)
        return self._lru[key]

    # --- retrieval ---------------------------------------------------------

    def search(self, query: str, k: int = 3) -> List[Tuple[str, Dict[str, Any], float]]:
        """Relevance search. Returns up to ``k`` (key, record, score).

        With an ``embedder`` configured, ranks by cosine similarity over
        embeddings (true semantic recall). Otherwise falls back to token overlap.
        """
        if self.embedder is not None:
            return self._search_embeddings(query, k)
        return self._search_overlap(query, k)

    def _search_overlap(self, query: str, k: int) -> List[Tuple[str, Dict[str, Any], float]]:
        q = set(_TOKEN.findall(query.lower()))
        if not q:
            return []
        scored = []
        for key, record in self._lru.items():
            tokens = set(_TOKEN.findall(record["text"].lower()))
            if not tokens:
                continue
            overlap = len(q & tokens) / len(q)
            if overlap > 0:
                scored.append((key, record, round(overlap, 3)))
        scored.sort(key=lambda t: t[2], reverse=True)
        return scored[:k]

    def _search_embeddings(self, query: str, k: int) -> List[Tuple[str, Dict[str, Any], float]]:
        from kernel.embeddings import cosine

        qv = self.embedder.embed(query)
        scored = []
        for key, record in self._lru.items():
            ev = record.get("embedding")
            if ev is None:
                ev = self.embedder.embed(record["text"])
                record["embedding"] = ev
            score = cosine(qv, ev)
            if score > 0:
                scored.append((key, record, round(score, 4)))
        scored.sort(key=lambda t: t[2], reverse=True)
        return scored[:k]

    def __len__(self) -> int:
        return len(self._lru)
