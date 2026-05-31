"""Tests for Notion-backed memory + embedding search (all offline)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel import (  # noqa: E402
    Kernel, MemoryManager, HashEmbedder, NotionStorage,
    InMemoryNotionTransport, cosine,
)
from kernel.embeddings import VoyageEmbedder  # noqa: E402
from monarch.llm import MockLLM  # noqa: E402
from shadow_os import Monarch  # noqa: E402


# --- Embeddings ------------------------------------------------------------

def test_hash_embedder_is_deterministic_and_normalized():
    e = HashEmbedder(dim=64)
    a, b = e.embed("retention dropped"), e.embed("retention dropped")
    assert a == b
    assert abs(cosine(a, a) - 1.0) < 1e-6


def test_cosine_identical_vs_disjoint():
    e = HashEmbedder(dim=128)
    same = cosine(e.embed("billing migration"), e.embed("billing migration"))
    disjoint = cosine(e.embed("alpha beta"), e.embed("gamma delta"))
    assert same > disjoint


def test_memory_embedding_search_ranks_by_similarity():
    mem = MemoryManager(capacity=8, embedder=HashEmbedder(dim=128))
    mem.write("a", "retention dropped after onboarding friction")
    mem.write("b", "billing migration evidence chain")
    hits = mem.search("retention onboarding", k=2)
    assert hits[0][0] == "a"
    assert hits[0][2] > 0


def test_embeddings_persist_on_record():
    mem = MemoryManager(capacity=8, embedder=HashEmbedder(dim=32))
    mem.write("a", "hello world")
    assert "embedding" in mem.read("a")
    assert len(mem.read("a")["embedding"]) == 32


def test_voyage_embedder_uses_injected_transport():
    # No network: inject a fake transport returning a fixed embedding.
    def fake(url, headers, body):
        assert "voyageai" in url
        return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    e = VoyageEmbedder(api_key="test", transport=fake)
    assert e.embed("anything") == [0.1, 0.2, 0.3]


# --- Notion storage backend ------------------------------------------------

def test_notion_storage_roundtrip_via_fake_transport():
    t = InMemoryNotionTransport()
    s = NotionStorage(database_id="db", transport=t)
    s.put("k", {"v": 1, "text": "hi"})
    assert s.get("k") == {"v": 1, "text": "hi"}
    assert "k" in s.keys()
    s.delete("k")
    assert s.get("k") is None


def test_notion_storage_rehydrates_from_database():
    t = InMemoryNotionTransport()
    s1 = NotionStorage(database_id="db", transport=t)
    s1.put("note:0", {"text": "durable in notion"})

    # New storage instance on the same (shared) transport = same database.
    s2 = NotionStorage(database_id="db", transport=t)
    assert s2.get("note:0") == {"text": "durable in notion"}


def test_memory_on_notion_backend_rehydrates():
    t = InMemoryNotionTransport()
    mem = MemoryManager(capacity=8, storage=NotionStorage("db", t))
    mem.write("commercial:0", "retention dipped after the v2 change")

    mem2 = MemoryManager(capacity=8, storage=NotionStorage("db", t))
    assert len(mem2) == 1
    assert mem2.read("commercial:0")["text"].startswith("retention dipped")


def test_kernel_with_notion_and_embedder_persists_and_searches():
    t = InMemoryNotionTransport()
    kernel = Kernel(
        llm=MockLLM(handler=lambda s, u: "Retention dropped after onboarding friction."),
        storage=NotionStorage("db", t),
        embedder=HashEmbedder(dim=128),
    )
    Monarch(kernel=kernel).run("research why retention dropped after onboarding")
    assert len(kernel.memory) == 1

    # Fresh kernel on the same Notion database rehydrates the memory.
    kernel2 = Kernel(
        llm=MockLLM(handler=lambda s, u: "x"),
        storage=NotionStorage("db", t),
        embedder=HashEmbedder(dim=128),
    )
    assert len(kernel2.memory) == 1
    hits = kernel2.memory.search("retention drop")
    assert hits and hits[0][2] > 0
