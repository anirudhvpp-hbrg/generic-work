"""Monarch OS — the local runtime that boots Shadow OS inside it.

This is the umbrella you run locally. ``boot()`` composes the whole stack:

    Monarch OS  (this runtime: local state, model selection)
      └─ kernel/        resource layer — durable memory, shared+metered model
           └─ shadow_os Monarch + 7 shadows   the cognitive engine

By default it persists memory to ``~/.monarchos/state.json`` (so runs accumulate
across sessions) and uses a real Claude model when ``ANTHROPIC_API_KEY`` is set,
falling back to the offline ``MockLLM`` otherwise. Nothing here needs the network
unless you opt into Claude.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from kernel import Kernel
from monarch.llm import MockLLM
from shadow_os import Monarch
from shadow_os.task import Task

DEFAULT_STATE = os.path.join(os.path.expanduser("~"), ".monarchos", "state.json")


@dataclass
class MonarchOS:
    """A booted runtime: the engine, the kernel it runs on, and the model."""

    monarch: Monarch
    kernel: Kernel
    llm: Any
    online: bool
    state_path: Optional[str]

    def run(self, directive: str, personal: bool = False) -> Task:
        """Run one directive through Shadow OS and return the full Task."""
        return self.monarch.run(directive, context={"personal": personal})

    def status(self) -> dict:
        return {
            "model": "claude" if self.online else "offline (MockLLM)",
            "state_path": self.state_path or "ephemeral (in-process)",
            "memory_units": len(self.kernel.memory),
            "shadows": list(self.monarch.fleet.keys()),
            "llm_usage": getattr(self.llm, "usage", None),
        }


def boot(
    state_path: Optional[str] = None,
    offline: bool = False,
    persist: bool = True,
    model: Optional[str] = None,
) -> MonarchOS:
    """Compose and start Monarch OS.

    Args:
        state_path: where durable memory lives. Defaults to ``~/.monarchos/state.json``.
        offline: force the offline MockLLM even if a Claude key is present.
        persist: when False, memory is in-process and resets each run.
        model: override the Claude model (e.g. ``"claude-opus-4-8"``).
    """
    use_claude = (not offline) and bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_claude:
        from monarch.claude_llm import ClaudeLLM
        llm = ClaudeLLM(model=model) if model else ClaudeLLM()
    else:
        llm = MockLLM()

    path: Optional[str]
    if not persist:
        path = None
    else:
        path = state_path or DEFAULT_STATE
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    kernel = Kernel(llm=llm, storage_path=path)   # durable when path is set
    monarch = Monarch(kernel=kernel)               # boots the fleet onto the kernel
    return MonarchOS(monarch=monarch, kernel=kernel, llm=llm, online=use_claude, state_path=path)
