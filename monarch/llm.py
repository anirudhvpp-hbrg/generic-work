"""Model-agnostic LLM interface (Invariant 11) used by the reasoning stage.

The reasoning stage (Vajra substrate) needs a model to think. Everything else
in the pipeline — intake routing, Caveman compression, QA — is deterministic
and needs no model. Provide any object with a ``complete(system, user)`` method;
``MockLLM`` is supplied for tests and offline runs.
"""

from __future__ import annotations

from typing import Callable, Optional, Protocol


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str:
        ...


class MockLLM:
    """Deterministic stand-in for a model.

    Defaults to echoing a structured stub so the pipeline can run end-to-end
    offline. Pass ``handler(system, user) -> str`` to script responses.
    """

    def __init__(self, handler: Optional[Callable[[str, str], str]] = None):
        self.handler = handler
        self.calls: list = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        if self.handler:
            return self.handler(system, user)
        return (
            "Claim: stub reasoning for the directive.\n"
            "Evidence: none (offline MockLLM).\n"
            "Implication: wire a real LLM via the `llm` argument.\n"
            "Kill condition: replace MockLLM with a model adapter."
        )


class CallableLLM:
    """Adapt any ``fn(system, user) -> str`` callable into an :class:`LLM`."""

    def __init__(self, fn: Callable[[str, str], str]):
        self._fn = fn

    def complete(self, system: str, user: str) -> str:
        return self._fn(system, user)
