"""Shadow OS v4 — capability-first cognitive engine.

7 shadows orchestrated by Monarch, each running one loop:
Perception -> Memory -> Reasoning -> Action. Canonical spec:
``docs/shadow-os-v4.md``. Reuses the v1.1 primitives (``monarch.caveman`` for
compression, ``monarch.llm`` for the model-agnostic interface).

Example::

    from shadow_os import Monarch

    monarch = Monarch()                       # offline MockLLM by default
    task = monarch.run("tighten this bloated proposal deck")
    print(task.final_output)                  # ratified, shipped
    print(task.trace())                       # loadout, γ, RSI, governance
"""

from shadow_os.monarch import Monarch
from shadow_os.memory import Memory
from shadow_os.task import Task, ShadowResult, RSIArtifact, Gamma, DecisionType
from shadow_os.router import TaskClassifier, ShadowRouter
from shadow_os.shadows import build_fleet, Shadow

__all__ = [
    "Monarch", "Memory", "Task", "ShadowResult", "RSIArtifact",
    "Gamma", "DecisionType", "TaskClassifier", "ShadowRouter",
    "build_fleet", "Shadow",
]

__version__ = "4.0.0"
