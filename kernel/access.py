"""Access Manager — per-agent permissions.

Concrete example from the architecture analysis: the commercial/standards agent
may touch pipeline data; the personal-redirection agent may not. The kernel
enforces this at the resource boundary, independent of what the cognitive layer
decides to attempt.
"""

from __future__ import annotations

from typing import Dict, Set


class AccessDenied(Exception):
    pass


class AccessManager:
    def __init__(self) -> None:
        self._grants: Dict[str, Set[str]] = {}

    def grant(self, agent_id: str, permission: str) -> None:
        self._grants.setdefault(agent_id, set()).add(permission)

    def revoke(self, agent_id: str, permission: str) -> None:
        self._grants.get(agent_id, set()).discard(permission)

    def check(self, agent_id: str, permission: str) -> bool:
        return permission in self._grants.get(agent_id, set())

    def require(self, agent_id: str, permission: str) -> None:
        if not self.check(agent_id, permission):
            raise AccessDenied(f"{agent_id} lacks permission: {permission}")
