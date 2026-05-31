"""Real Claude adapter for the engine's model-agnostic LLM interface.

``ClaudeLLM`` implements ``complete(system, user) -> str`` (the same interface as
``MockLLM``), so dropping it into ``Monarch(llm=ClaudeLLM())`` makes every shadow
reason against a live Claude model instead of canned text.

Design notes:
- Defaults to Claude Opus 4.8 (``claude-opus-4-8``) with adaptive thinking and
  ``effort: "high"`` — the recommended settings for intelligence-sensitive work.
- **Prompt caching**: each shadow's system prompt is stable across calls, so it
  is sent as a cached block (``cache_control: ephemeral``). Repeated calls with
  the same shadow reuse the cached prefix. (Caching only kicks in once the
  prefix exceeds the model's minimum cacheable size; the marker is harmless
  below that.)
- The ``anthropic`` SDK is imported lazily and the client is injectable, so the
  rest of the package stays dependency-free and offline-testable.

Requires ``pip install anthropic`` and ``ANTHROPIC_API_KEY`` to run for real.
"""

from __future__ import annotations

from typing import Any, List, Optional


class ClaudeLLM:
    def __init__(
        self,
        model: str = "claude-opus-4-8",
        effort: str = "high",
        max_tokens: int = 16000,
        cache_system: bool = True,
        client: Optional[Any] = None,
    ):
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.cache_system = cache_system
        self._client = client
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                      "cache_read_input_tokens": 0}

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

    def _system_blocks(self, system: str) -> List[dict]:
        block: dict = {"type": "text", "text": system}
        if self.cache_system:
            block["cache_control"] = {"type": "ephemeral"}
        return [block]

    def complete(self, system: str, user: str) -> str:
        client = self._ensure_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            system=self._system_blocks(system),
            messages=[{"role": "user", "content": user}],
        )
        self._record_usage(response)
        return _extract_text(response)

    def _record_usage(self, response: Any) -> None:
        self.usage["calls"] += 1
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
