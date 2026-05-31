"""Context Manager — snapshot and restore an agent's loop state.

When the scheduler context-switches away from an agent mid-loop, its state is
snapshotted here and restored when it resumes. Stores deep copies so later
mutation of the live state does not corrupt the snapshot.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional


class ContextManager:
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def snapshot(self, agent_id: str, state: Any) -> None:
        self._store[agent_id] = copy.deepcopy(state)

    def restore(self, agent_id: str) -> Optional[Any]:
        snap = self._store.get(agent_id)
        return copy.deepcopy(snap) if snap is not None else None

    def has(self, agent_id: str) -> bool:
        return agent_id in self._store

    def clear(self, agent_id: str) -> None:
        self._store.pop(agent_id, None)
