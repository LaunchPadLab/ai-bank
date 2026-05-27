"""Agent loop behavior, driven by a fake streaming Anthropic client.

The fake mimics the streaming SDK surface the loop touches: ``client.messages.stream(**kwargs)``
returns an async context manager that is async-iterable (yielding raw stream events) and exposes
``get_final_message()``. This lets us script tool-use turns and assert on the emitted ChatEvents
without any network calls. Tool execution itself runs for real against the in-process catalog.
"""

from __future__ import annotations

import dataclasses
import types

from aibank_mcp.catalog import build_catalog
from aibank_mcp.config import resolve_repo_root

from aibank_web.agent import AgentLoop
from aibank_web.config import ChatSettings
from aibank_web.events import (
    CitationsEvent,
    DoneEvent,
    ErrorEvent,
    TextDeltaEvent,
    ToolCallEvent,
)
from aibank_web.prompts import build_system_prompt


def _ns(**kw):
    return types.SimpleNamespace(**kw)


def _text_delta(text):
    return _ns(type="content_block_delta", delta=_ns(type="text_delta", text=text))


def _usage():
    return _ns(
        input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0
    )


class _FakeStream:
    def __init__(self, events, final):
        self._events = events
        self._final = final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        async def gen():
            for event in self._events:
                yield event

        return gen()

    async def get_final_message(self):
        return self._final


class _FakeMessages:
    def __init__(self, scripted):
        self._scripted = list(scripted)
        self._i = 0

    def stream(self, **kwargs):
        stream = self._scripted[min(self._i, len(self._scripted) - 1)]
        self._i += 1
        return stream


class _FakeClient:
    def __init__(self, scripted):
        self.messages = _FakeMessages(scripted)


def _harness():
    catalog = build_catalog(resolve_repo_root())
    settings = ChatSettings.from_env()
    system_blocks = build_system_prompt(catalog)
    return catalog, settings, system_blocks


async def _collect(loop, messages):
    return [event async for event in loop.run(messages)]


async def test_tool_use_then_answer_emits_citation():
    catalog, settings, system = _harness()
    skill = catalog.skill_names()[0]

    scripted = [
        # Turn 1: model calls get_skill.
        _FakeStream(
            [],
            _ns(
                stop_reason="tool_use",
                content=[_ns(type="tool_use", id="t1", name="get_skill", input={"name": skill})],
                usage=_usage(),
            ),
        ),
        # Turn 2: model answers and stops.
        _FakeStream(
            [_text_delta("Here is the answer.")],
            _ns(stop_reason="end_turn", content=[_ns(type="text", text="x")], usage=_usage()),
        ),
    ]
    loop = AgentLoop(_FakeClient(scripted), catalog, settings, system)
    events = await _collect(loop, [{"role": "user", "content": "tell me about a skill"}])

    tool_calls = [e for e in events if isinstance(e, ToolCallEvent)]
    assert tool_calls and tool_calls[0].name == "get_skill"

    text = "".join(e.text for e in events if isinstance(e, TextDeltaEvent))
    assert text == "Here is the answer."

    citations = [e for e in events if isinstance(e, CitationsEvent)]
    assert citations and any(s.kind == "skill" and s.name == skill for s in citations[0].sources)

    assert isinstance(events[-1], DoneEvent)


async def test_plain_answer_no_tools():
    catalog, settings, system = _harness()
    scripted = [
        _FakeStream(
            [_text_delta("Hello.")],
            _ns(stop_reason="end_turn", content=[_ns(type="text", text="Hello.")], usage=_usage()),
        )
    ]
    loop = AgentLoop(_FakeClient(scripted), catalog, settings, system)
    events = await _collect(loop, [{"role": "user", "content": "hi"}])
    assert not [e for e in events if isinstance(e, CitationsEvent)]  # no sources fetched
    assert isinstance(events[-1], DoneEvent)


async def test_max_iterations_guard():
    catalog, settings, system = _harness()
    settings = dataclasses.replace(settings, max_iterations=1)
    # Always asks for a tool -> never finishes within the cap.
    forever = _FakeStream(
        [],
        _ns(
            stop_reason="tool_use",
            content=[_ns(type="tool_use", id="t1", name="search", input={"query": "x"})],
            usage=_usage(),
        ),
    )
    loop = AgentLoop(_FakeClient([forever]), catalog, settings, system)
    events = await _collect(loop, [{"role": "user", "content": "loop forever"}])
    errors = [e for e in events if isinstance(e, ErrorEvent)]
    assert errors and errors[0].code == "max_iterations"
    assert isinstance(events[-1], DoneEvent)
