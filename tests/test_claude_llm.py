"""Tests for the ClaudeLLM adapter — offline, via an injected fake client."""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarch.claude_llm import ClaudeLLM, _extract_text  # noqa: E402
from shadow_os import Monarch  # noqa: E402


def _block(text):
    return types.SimpleNamespace(type="text", text=text)


def _response(text, **usage):
    return types.SimpleNamespace(
        content=[_block(text)],
        usage=types.SimpleNamespace(**usage) if usage else None,
    )


class FakeMessages:
    def __init__(self, reply="grounded answer"):
        self.reply = reply
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _response(self.reply, input_tokens=10, output_tokens=5,
                         cache_read_input_tokens=8)


class FakeClient:
    def __init__(self, reply="grounded answer"):
        self.messages = FakeMessages(reply)


def test_complete_returns_text_and_records_usage():
    client = FakeClient("Cause: latency. Fix: cache.")
    llm = ClaudeLLM(client=client)
    out = llm.complete("system prompt", "user prompt")
    assert out == "Cause: latency. Fix: cache."
    assert llm.usage["calls"] == 1
    assert llm.usage["input_tokens"] == 10
    assert llm.usage["cache_read_input_tokens"] == 8


def test_request_uses_opus_adaptive_effort_and_cached_system():
    client = FakeClient()
    llm = ClaudeLLM(client=client)
    llm.complete("SYS", "USER")
    sent = client.messages.calls[0]
    assert sent["model"] == "claude-opus-4-8"
    assert sent["thinking"] == {"type": "adaptive"}
    assert sent["output_config"] == {"effort": "high"}
    # system is a cached text block
    assert sent["system"][0]["text"] == "SYS"
    assert sent["system"][0]["cache_control"] == {"type": "ephemeral"}
    # user message shape
    assert sent["messages"] == [{"role": "user", "content": "USER"}]


def test_caching_can_be_disabled():
    client = FakeClient()
    ClaudeLLM(client=client, cache_system=False).complete("SYS", "USER")
    assert "cache_control" not in client.messages.calls[0]["system"][0]


def test_custom_model_and_effort():
    client = FakeClient()
    ClaudeLLM(client=client, model="claude-sonnet-4-6", effort="medium").complete("s", "u")
    sent = client.messages.calls[0]
    assert sent["model"] == "claude-sonnet-4-6"
    assert sent["output_config"] == {"effort": "medium"}


def test_extract_text_skips_non_text_blocks():
    resp = types.SimpleNamespace(content=[
        types.SimpleNamespace(type="thinking", thinking="..."),
        types.SimpleNamespace(type="text", text="answer"),
    ])
    assert _extract_text(resp) == "answer"


def test_engine_runs_on_claude_adapter():
    # The whole engine drives the adapter just like any LLM.
    client = FakeClient("Compressed, grounded answer for the directive.")
    monarch = Monarch(llm=ClaudeLLM(client=client))
    task = monarch.run("tighten this proposal")
    assert task.shipped is True
    assert "grounded" in task.final_output
    assert client.messages.calls  # the model was actually called
