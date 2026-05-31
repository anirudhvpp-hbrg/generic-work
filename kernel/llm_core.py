"""LLM Core — the model abstraction the kernel owns.

A single shared instance wraps the model so the scheduler can share one LLM
across many agents while accounting for usage. Agents never hold a model
directly; they request completions through the kernel.
"""

from __future__ import annotations

from monarch.llm import LLM, MockLLM


class LLMCore:
    def __init__(self, llm: LLM | None = None):
        self.llm = llm or MockLLM()
        self.calls = 0
        self.approx_tokens = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        out = self.llm.complete(system, user)
        self.approx_tokens += len((system + user + out).split())
        return out

    def usage(self) -> dict:
        return {"calls": self.calls, "approx_tokens": self.approx_tokens}
