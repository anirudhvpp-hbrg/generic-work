"""Scheduler — ordering and LLM sharing when multiple agents are dispatched.

Agents submit jobs with a priority; the scheduler runs them in priority order
(lower number = higher priority, FIFO within a priority) against the shared LLM
Core. Execution order is recorded so callers can audit how the kernel sequenced
the fleet. This is the resource-layer counterpart to the cognitive layer's own
loadout sequencing — same idea, different concern (resources, not meaning).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple


@dataclass(order=True)
class _Job:
    priority: int
    seq: int
    agent_id: str = field(compare=False)
    fn: Callable[[], Any] = field(compare=False)


class Scheduler:
    def __init__(self) -> None:
        self._heap: List[_Job] = []
        self._seq = 0
        self.history: List[str] = []

    def submit(self, agent_id: str, fn: Callable[[], Any], priority: int = 5) -> None:
        heapq.heappush(self._heap, _Job(priority, self._seq, agent_id, fn))
        self._seq += 1

    def run(self) -> Dict[str, Any]:
        """Execute all submitted jobs in priority order; return agent_id->result."""
        results: Dict[str, Any] = {}
        while self._heap:
            job = heapq.heappop(self._heap)
            self.history.append(job.agent_id)
            results[job.agent_id] = job.fn()
        return results

    @property
    def pending(self) -> int:
        return len(self._heap)
