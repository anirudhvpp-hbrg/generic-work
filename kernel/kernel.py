"""Kernel — composes the resource managers and exposes a syscall interface.

This is the AIOS-style resource layer. The cognitive engine (the shadow fleet
orchestrated by Monarch) is an agent that runs *on* this kernel: it requests
LLM completions, memory, tools, and context-switches as syscalls, and the kernel
enforces access and accounts for usage.

    Cognitive layer:  Monarch + shadows  (which shadow reasons about what)
    Resource layer:   this Kernel        (which request gets LLM/memory/tools)
"""

from __future__ import annotations

from typing import Any, Optional

from monarch.llm import LLM
from kernel.access import AccessManager
from kernel.context import ContextManager
from kernel.llm_core import LLMCore
from kernel.scheduler import Scheduler
from kernel.storage import MemoryManager, StorageManager
from kernel.tools import ToolManager


class Kernel:
    def __init__(
        self,
        llm: Optional[LLM] = None,
        storage_path: Optional[str] = None,
        memory_capacity: int = 128,
        storage: Optional[Any] = None,
        embedder: Optional[Any] = None,
    ):
        self.llm_core = LLMCore(llm)
        self.scheduler = Scheduler()
        self.context = ContextManager()
        # A custom backend (e.g. NotionStorage) takes precedence over a path.
        self.storage = storage if storage is not None else StorageManager(storage_path)
        self.memory = MemoryManager(memory_capacity, self.storage, embedder=embedder)
        self.tools = ToolManager()
        self.access = AccessManager()

    # --- syscall surface ---------------------------------------------------

    def syscall(self, agent_id: str, name: str, **kw: Any) -> Any:
        """Single entry point. Access is enforced where the call needs it."""
        if name == "llm.complete":
            self.access.require(agent_id, "llm")
            return self.llm_core.complete(kw["system"], kw["user"])
        if name == "mem.write":
            self.access.require(agent_id, "memory:write")
            return self.memory.write(kw["key"], kw["text"], kw.get("meta"))
        if name == "mem.read":
            return self.memory.read(kw["key"])
        if name == "mem.search":
            return self.memory.search(kw["query"], kw.get("k", 3))
        if name == "tool.call":
            return self.tools.call(agent_id, kw["tool"], self.access, *kw.get("args", ()), **kw.get("kwargs", {}))
        if name == "ctx.snapshot":
            return self.context.snapshot(agent_id, kw["state"])
        if name == "ctx.restore":
            return self.context.restore(agent_id)
        raise KeyError(f"unknown syscall: {name}")
