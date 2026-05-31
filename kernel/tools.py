"""Tool Manager — a unified registry the Action stage calls into.

Tools are registered with an optional required permission. Calls go through the
Access Manager first, so an agent can only invoke a tool it is permitted to use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from kernel.access import AccessManager


@dataclass
class Tool:
    name: str
    fn: Callable[..., Any]
    permission: Optional[str] = None


class ToolManager:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, fn: Callable[..., Any], permission: Optional[str] = None) -> None:
        self._tools[name] = Tool(name, fn, permission)

    def names(self) -> List[str]:
        return list(self._tools)

    def call(self, agent_id: str, name: str, access: AccessManager, *args: Any, **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"no such tool: {name}")
        if tool.permission:
            access.require(agent_id, tool.permission)  # raises AccessDenied if not granted
        return tool.fn(*args, **kwargs)
