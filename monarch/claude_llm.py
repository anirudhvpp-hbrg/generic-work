"""Real Claude adapter for the engine's model-agnostic LLM interface.

``ClaudeLLM`` implements ``complete(system, user) -> str`` (the same interface as
``MockLLM``), so dropping it into ``Monarch(llm=ClaudeLLM())`` makes every shadow
reason against a live Claude model instead of canned text.

Model tiering (default):
- **Sonnet 4.6** (``claude-sonnet-4-6``) for normal work — the best
  speed/intelligence balance — with adaptive thinking and ``effort: "high"``.
- **Haiku 4.5** (``claude-haiku-4-5``) for clear, simple tasks — fast and cheap.
  Haiku 4.5 does not accept the ``effort`` or adaptive-``thinking`` parameters,
  so they are omitted for it (sending them would 400).

Auto-tiering picks Haiku for short, low-stakes prompts and Sonnet otherwise; set
``auto_tier=False`` to always use ``model``.

Design notes:
- **Prompt caching**: each shadow's system prompt is stable across calls, so it
  is sent as a cached block (``cache_control: ephemeral``); repeated calls with
  the same shadow reuse the cached prefix (once it exceeds the model's minimum
  cacheable size — the marker is harmless below that).
- The ``anthropic`` SDK is imported lazily and the client is injectable, so the
  rest of the package stays dependency-free and offline-testable.

Requires ``pip install anthropic`` and ``ANTHROPIC_API_KEY`` to run for real.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Markers that make a task "not clear" — deliberate reasoning, route to Sonnet.
_COMPLEX = re.compile(
    r"\b(architect|design|system|strateg|analy[sz]e|evaluate|proposal|rfp|risk|"
    r"pre-?mortem|trade-?off|decide|decision|why|compare|first principles|"
    r"roadmap|migrat|refactor|invent|novel)\b",
    re.I,
)


def _is_clear_task(user: str) -> bool:
    """Heuristic: short, low-stakes prompts with no complexity markers."""
    if _COMPLEX.search(user):
        return False
    return len(user.split()) <= 30


def _supports_thinking_and_effort(model: str) -> bool:
    # Haiku 4.5 rejects `effort` and adaptive `thinking`; Sonnet/Opus accept them.
    return "haiku" not in model.lower()


class ClaudeLLM:
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        simple_model: str = "claude-haiku-4-5",
        auto_tier: bool = True,
        effort: str = "high",
        max_tokens: int = 16000,
        cache_system: bool = True,
        client: Optional[Any] = None,
    ):
        self.model = model
        self.simple_model = simple_model
        self.auto_tier = auto_tier
        self.effort = effort
        self.max_tokens = max_tokens
        self.cache_system = cache_system
        self._client = client
        self.usage: Dict[str, Any] = {
            "calls": 0, "input_tokens": 0, "output_tokens": 0,
            "cache_read_input_tokens": 0, "by_model": {},
        }

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "ClaudeLLM needs the Anthropic SDK: pip install anthropic, and "
                "set ANTHROPIC_API_KEY. For offline runs use MockLLM."
            ) from exc
        self._client = anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY from env
        return self._client

    def pick_model(self, user: str) -> str:
        """Sonnet by default; Haiku for clear, simple tasks (when auto_tier)."""
        if self.auto_tier and _is_clear_task(user):
            return self.simple_model
        return self.model

    def _system_blocks(self, system: str) -> List[dict]:
        block: dict = {"type": "text", "text": system}
        if self.cache_system:
            block["cache_control"] = {"type": "ephemeral"}
        return [block]

    def _build_request(self, model: str, system: str, user: str) -> Dict[str, Any]:
        request: Dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens,
            "system": self._system_blocks(system),
            "messages": [{"role": "user", "content": user}],
        }
        # Only the models that support these get adaptive thinking + effort.
        if _supports_thinking_and_effort(model):
            request["thinking"] = {"type": "adaptive"}
            request["output_config"] = {"effort": self.effort}
        return request

    def complete(self, system: str, user: str) -> str:
        client = self._ensure_client()
        model = self.pick_model(user)
        response = client.messages.create(**self._build_request(model, system, user))
        self._record_usage(model, response)
        return _extract_text(response)

    def _record_usage(self, model: str, response: Any) -> None:
        self.usage["calls"] += 1
        self.usage["by_model"][model] = self.usage["by_model"].get(model, 0) + 1
        u = getattr(response, "usage", None)
        if u is None:
            return
        for field in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
            value = getattr(u, field, None)
            if value:
                self.usage[field] = self.usage.get(field, 0) + value


def _extract_text(response: Any) -> str:
    """Concatenate the text blocks of a Messages API response."""
    parts = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)
