"""AIOS-style kernel — the resource layer beneath the cognitive engine.

The shadow fleet (orchestrated by Monarch) is the cognitive/agent layer: it
decides *which shadow reasons about what*. This kernel is the resource layer: it
decides *which request gets LLM, memory, tools* — and enforces per-agent access.

Managers:
- ``LLMCore``        one shared model the scheduler shares across agents
- ``Scheduler``      priority ordering of dispatched agent jobs
- ``ContextManager`` snapshot / restore an agent's loop state on context-switch
- ``StorageManager`` / ``MemoryManager``  persistence + LRU-bounded memory
- ``ToolManager``    a unified tool registry the Action stage calls into
- ``AccessManager``  per-agent permissions

``Kernel`` composes them and exposes a single ``syscall`` surface. ``boot_shadow_os``
wires an existing Monarch onto a Kernel with sensible default grants.
"""

from kernel.kernel import Kernel
from kernel.llm_core import LLMCore
from kernel.scheduler import Scheduler
from kernel.context import ContextManager
from kernel.storage import StorageManager, MemoryManager
from kernel.tools import ToolManager, Tool
from kernel.access import AccessManager, AccessDenied
from kernel.boot import boot_shadow_os
from kernel.embeddings import Embedder, HashEmbedder, VoyageEmbedder, cosine
from kernel.notion_storage import (
    NotionStorage, HttpNotionTransport, InMemoryNotionTransport,
)

__all__ = [
    "Kernel", "LLMCore", "Scheduler", "ContextManager",
    "StorageManager", "MemoryManager", "ToolManager", "Tool",
    "AccessManager", "AccessDenied", "boot_shadow_os",
    "Embedder", "HashEmbedder", "VoyageEmbedder", "cosine",
    "NotionStorage", "HttpNotionTransport", "InMemoryNotionTransport",
]

__version__ = "0.1.0"
