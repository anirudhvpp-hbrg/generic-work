"""Notion-backed storage — durable memory that lives in your Notion workspace.

``NotionStorage`` is a drop-in for ``StorageManager``: it implements the same
``put / get / delete / keys / items / persist / load`` contract, so
``MemoryManager`` can rehydrate from a Notion database with no change to callers.
Each key becomes one page in the database; the record (text, meta, seq, optional
embedding) is stored as a JSON payload property, chunked to respect Notion's
per-field size limit.

Why Notion instead of an opaque vector DB: the memory is browsable and editable
in the same workspace as the Shadow OS specs. The trade-off is no native vector
search — semantic ranking is done in-process (see ``MemoryManager`` + embeddings).

The Notion API is reached through a ``transport`` so this is fully testable
offline: ``InMemoryNotionTransport`` simulates the database;
``HttpNotionTransport`` talks to the real API with only the standard library.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional, Protocol, Tuple

_CHUNK = 1900  # Notion rich_text hard cap is 2000 chars per segment.


class NotionTransport(Protocol):
    def query(self, database_id: str) -> List[dict]: ...
    def create(self, database_id: str, key: str, payload: str) -> str: ...
    def update(self, page_id: str, key: str, payload: str) -> None: ...
    def archive(self, page_id: str) -> None: ...


def _chunk(text: str) -> List[dict]:
    return [{"text": {"content": text[i:i + _CHUNK]}} for i in range(0, len(text) or 1, _CHUNK)] or [{"text": {"content": ""}}]


def _join(rich_text: List[dict]) -> str:
    return "".join(seg.get("text", {}).get("content", "") for seg in rich_text)


class HttpNotionTransport:
    """Talks to the real Notion API. Standard-library HTTP only.

    Needs an integration token (``NOTION_TOKEN``) and a database with a title
    property ``Key`` and a rich_text property ``Payload``.
    """

    API = "https://api.notion.com/v1"
    VERSION = "2022-06-28"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("NOTION_TOKEN")

    def _req(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        if not self.token:
            raise RuntimeError("HttpNotionTransport needs NOTION_TOKEN.")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.API}{path}", data=data, method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": self.VERSION,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def query(self, database_id: str) -> List[dict]:
        results, cursor = [], None
        while True:
            body = {"start_cursor": cursor} if cursor else {}
            out = self._req("POST", f"/databases/{database_id}/query", body)
            for page in out.get("results", []):
                props = page.get("properties", {})
                key = _join(props.get("Key", {}).get("title", []))
                payload = _join(props.get("Payload", {}).get("rich_text", []))
                results.append({"id": page["id"], "key": key, "payload": payload})
            if not out.get("has_more"):
                return results
            cursor = out.get("next_cursor")

    def create(self, database_id: str, key: str, payload: str) -> str:
        out = self._req("POST", "/pages", {
            "parent": {"database_id": database_id},
            "properties": {
                "Key": {"title": [{"text": {"content": key}}]},
                "Payload": {"rich_text": _chunk(payload)},
            },
        })
        return out["id"]

    def update(self, page_id: str, key: str, payload: str) -> None:
        self._req("PATCH", f"/pages/{page_id}", {
            "properties": {"Payload": {"rich_text": _chunk(payload)}},
        })

    def archive(self, page_id: str) -> None:
        self._req("PATCH", f"/pages/{page_id}", {"archived": True})


class InMemoryNotionTransport:
    """Offline simulation of a Notion database for tests and dry runs."""

    def __init__(self) -> None:
        self.pages: Dict[str, Dict[str, str]] = {}   # page_id -> {key, payload}
        self._n = 0

    def query(self, database_id: str) -> List[dict]:
        return [{"id": pid, **rec} for pid, rec in self.pages.items()]

    def create(self, database_id: str, key: str, payload: str) -> str:
        pid = f"page-{self._n}"
        self._n += 1
        self.pages[pid] = {"key": key, "payload": payload}
        return pid

    def update(self, page_id: str, key: str, payload: str) -> None:
        self.pages[page_id] = {"key": key, "payload": payload}

    def archive(self, page_id: str) -> None:
        self.pages.pop(page_id, None)


class NotionStorage:
    """StorageManager-compatible backend persisting to a Notion database."""

    def __init__(self, database_id: str, transport: Optional[NotionTransport] = None):
        self.database_id = database_id
        self.transport = transport or HttpNotionTransport()
        self._index: Dict[str, str] = {}   # key -> page_id
        self._cache: Dict[str, Any] = {}    # key -> value
        self.load()

    # --- StorageManager contract ------------------------------------------

    def put(self, key: str, value: Any) -> None:
        payload = json.dumps(value)
        if key in self._index:
            self.transport.update(self._index[key], key, payload)
        else:
            self._index[key] = self.transport.create(self.database_id, key, payload)
        self._cache[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def delete(self, key: str) -> None:
        pid = self._index.pop(key, None)
        self._cache.pop(key, None)
        if pid:
            self.transport.archive(pid)

    def keys(self) -> List[str]:
        return list(self._cache.keys())

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._cache.items())

    def persist(self) -> None:
        # Writes are synchronous through the transport; nothing to flush.
        pass

    def load(self) -> None:
        self._index.clear()
        self._cache.clear()
        for page in self.transport.query(self.database_id):
            key = page["key"]
            if not key:
                continue
            self._index[key] = page["id"]
            try:
                self._cache[key] = json.loads(page["payload"])
            except (json.JSONDecodeError, TypeError):
                self._cache[key] = page["payload"]
