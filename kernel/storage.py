"""Storage Manager + Memory Manager — the persistence tier.

This is infrastructure: where bytes live, how they persist, and what gets
evicted. It is distinct from the cognitive engine's semantic Memory (what
context matters) — the engine's Memory stage would be *backed by* this.

- ``StorageManager`` is a key-value store with optional JSON persistence to disk.
- ``MemoryManager`` adds a capacity bound with LRU eviction, backed by storage.
"""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional


class StorageManager:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path
        self._data: Dict[str, Any] = {}
        if path and os.path.exists(path):
            self.load()

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys(self) -> List[str]:
        return list(self._data.keys())

    def persist(self) -> None:
        if not self.path:
            return
        with open(self.path, "w") as fh:
            json.dump(self._data, fh)

    def load(self) -> None:
        if self.path and os.path.exists(self.path):
            with open(self.path) as fh:
                self._data = json.load(fh)


class MemoryManager:
    """Capacity-bounded store with LRU eviction, backed by a StorageManager."""

    def __init__(self, capacity: int = 128, storage: Optional[StorageManager] = None) -> None:
        self.capacity = max(1, capacity)
        self.storage = storage or StorageManager()
        self._lru: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self.evicted: List[str] = []

    def write(self, key: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        record = {"text": text, "meta": meta or {}}
        if key in self._lru:
            self._lru.move_to_end(key)
        self._lru[key] = record
        self.storage.put(key, record)
        while len(self._lru) > self.capacity:
            old_key, _ = self._lru.popitem(last=False)
            self.storage.delete(old_key)
            self.evicted.append(old_key)

    def read(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self._lru:
            return None
        self._lru.move_to_end(key)
        return self._lru[key]

    def __len__(self) -> int:
        return len(self._lru)
