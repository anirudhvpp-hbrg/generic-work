"""Tests for the AIOS-style kernel and its integration with the engine."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarch.llm import MockLLM  # noqa: E402
from kernel import (  # noqa: E402
    Kernel, Scheduler, ContextManager, MemoryManager, StorageManager,
    AccessManager, AccessDenied, ToolManager,
)
from shadow_os import Monarch  # noqa: E402


# --- Scheduler -------------------------------------------------------------

def test_scheduler_runs_in_priority_order():
    s = Scheduler()
    s.submit("low", lambda: "l", priority=9)
    s.submit("high", lambda: "h", priority=1)
    s.submit("mid", lambda: "m", priority=5)
    results = s.run()
    assert s.history == ["high", "mid", "low"]
    assert results == {"low": "l", "high": "h", "mid": "m"}


def test_scheduler_fifo_within_priority():
    s = Scheduler()
    s.submit("a", lambda: 1, priority=5)
    s.submit("b", lambda: 2, priority=5)
    s.run()
    assert s.history == ["a", "b"]


# --- Context Manager -------------------------------------------------------

def test_context_snapshot_restore_is_deep():
    c = ContextManager()
    state = {"steps": [1, 2]}
    c.snapshot("agent", state)
    state["steps"].append(3)            # mutate after snapshot
    restored = c.restore("agent")
    assert restored == {"steps": [1, 2]}  # snapshot unaffected
    assert c.has("agent")
    assert c.restore("missing") is None


# --- Storage + Memory ------------------------------------------------------

def test_storage_persists_to_disk(tmp_path):
    path = str(tmp_path / "store.json")
    s = StorageManager(path)
    s.put("k", {"v": 1})
    s.persist()
    reloaded = StorageManager(path)
    assert reloaded.get("k") == {"v": 1}


def test_storage_auto_persists_on_write(tmp_path):
    path = str(tmp_path / "auto.json")
    s = StorageManager(path)          # auto_persist defaults on
    s.put("k", {"v": 1})              # no explicit persist() call
    assert StorageManager(path).get("k") == {"v": 1}
    s.delete("k")                     # delete is durable too
    assert StorageManager(path).get("k") is None


def test_storage_write_is_atomic(tmp_path):
    # A real file is left after replace; no leftover .tmp files in the dir.
    path = str(tmp_path / "atomic.json")
    s = StorageManager(path)
    s.put("a", 1)
    leftovers = [p for p in os.listdir(tmp_path) if p.endswith(".tmp")]
    assert leftovers == []
    assert os.path.exists(path)


def test_memory_durable_across_restart(tmp_path):
    path = str(tmp_path / "mem.json")
    storage = StorageManager(path)
    mem = MemoryManager(capacity=8, storage=storage)
    mem.write("commercial:0", "retention dipped after the v2 onboarding change")
    mem.write("research:0", "evidence chain for the billing migration")

    # Simulate a fresh process: new managers on the same path rehydrate.
    mem2 = MemoryManager(capacity=8, storage=StorageManager(path))
    assert len(mem2) == 2
    assert mem2.read("commercial:0")["text"].startswith("retention dipped")


def test_memory_search_ranks_by_overlap():
    mem = MemoryManager(capacity=8)
    mem.write("a", "retention dropped after onboarding friction")
    mem.write("b", "billing migration evidence chain")
    hits = mem.search("why did retention drop", k=2)
    assert hits
    assert hits[0][0] == "a"          # most relevant first
    assert hits[0][2] > 0


def test_kernel_durable_storage_survives_new_instance(tmp_path):
    path = str(tmp_path / "kernel.json")
    k1 = Kernel(llm=MockLLM(handler=lambda s, u: "x"), storage_path=path)
    k1.access.grant("agent", "memory:write")
    k1.syscall("agent", "mem.write", key="note:0", text="durable fact stored")

    k2 = Kernel(llm=MockLLM(handler=lambda s, u: "x"), storage_path=path)
    assert len(k2.memory) == 1
    assert k2.memory.read("note:0")["text"] == "durable fact stored"


def test_memory_manager_evicts_lru():
    m = MemoryManager(capacity=2)
    m.write("a", "A")
    m.write("b", "B")
    m.read("a")              # touch a -> b is now least-recently-used
    m.write("c", "C")        # over capacity -> evict b
    assert m.read("b") is None
    assert m.read("a") is not None
    assert m.read("c") is not None
    assert "b" in m.evicted


# --- Access + Tools --------------------------------------------------------

def test_access_grant_check_require():
    a = AccessManager()
    a.grant("aegis", "data:pipeline")
    assert a.check("aegis", "data:pipeline")
    assert not a.check("ira", "data:pipeline")
    a.require("aegis", "data:pipeline")     # no raise
    with pytest.raises(AccessDenied):
        a.require("ira", "data:pipeline")


def test_tool_manager_enforces_permission():
    a = AccessManager()
    t = ToolManager()
    t.register("pipeline", lambda: "data", permission="data:pipeline")
    a.grant("aegis", "data:pipeline")
    assert t.call("aegis", "pipeline", a) == "data"
    with pytest.raises(AccessDenied):
        t.call("ira", "pipeline", a)


# --- Kernel syscall surface ------------------------------------------------

def test_kernel_syscall_llm_requires_permission():
    k = Kernel(llm=MockLLM(handler=lambda s, u: "ok"))
    with pytest.raises(AccessDenied):
        k.syscall("nobody", "llm.complete", system="s", user="u")
    k.access.grant("agent", "llm")
    assert k.syscall("agent", "llm.complete", system="s", user="u") == "ok"
    assert k.llm_core.usage()["calls"] == 1


# --- Integration: engine on the kernel -------------------------------------

def test_monarch_boots_on_kernel_and_persists():
    k = Kernel(llm=MockLLM(handler=lambda s, u: "Clean grounded answer."))
    m = Monarch(kernel=k)
    task = m.run("draft the proposal summary")
    assert task.shipped is True
    # llm calls were accounted by the shared core
    assert k.llm_core.usage()["calls"] >= 1
    # shipped output persisted to kernel memory
    assert len(k.memory) >= 1
    # each shadow that ran has a context snapshot
    for sid in task.shadow_loadout:
        assert k.context.has(sid)


def test_kernel_access_example_aegis_yes_ira_no():
    k = Kernel(llm=MockLLM(handler=lambda s, u: "x"))
    Monarch(kernel=k)  # boots default grants + pipeline_data tool
    assert k.syscall("aegis", "tool.call", tool="pipeline_data")
    with pytest.raises(AccessDenied):
        k.syscall("ira", "tool.call", tool="pipeline_data")
