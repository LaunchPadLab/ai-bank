"""The streaming agentic loop.

A manual loop over the Anthropic streaming API (not the SDK tool runner, which returns whole
messages -- we need per-token streaming, live tool-activity, and server-synthesized citations).

Per iteration: open a streaming request, forward text deltas as they arrive, then inspect the
final message. On ``stop_reason == "tool_use"`` we execute each tool against the in-process
catalog, append the assistant turn (with its thinking/tool_use blocks, signatures intact) and a
user turn of ``tool_result`` blocks, and loop. On ``end_turn`` we emit the citation set (derived
from the tools actually run -- the model cannot cite a source it never retrieved) and finish.

Opus 4.7 specifics: ``thinking={"type":"adaptive"}`` (off by default, so set it explicitly),
effort via ``output_config``, and NO ``temperature``/``top_p``/``budget_tokens`` (all 400).
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable

import anthropic

from aibank_mcp.catalog import Catalog

from .config import ChatSettings
from .events import (
    ChatEvent,
    CitationsEvent,
    DoneEvent,
    ErrorEvent,
    Source,
    StatusEvent,
    TextDeltaEvent,
    ToolCallEvent,
    UsageEvent,
)
from .tools import ANTHROPIC_TOOLS, execute_tool, tool_label

logger = logging.getLogger("aibank_web")

DisconnectCheck = Callable[[], Awaitable[bool]]


class AgentLoop:
    """Drives one chat turn: prior messages in, a stream of :class:`ChatEvent`s out."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        catalog: Catalog,
        settings: ChatSettings,
        system_blocks: list[dict],
    ) -> None:
        self._client = client
        self._catalog = catalog
        self._settings = settings
        self._system = system_blocks  # built once at startup; byte-stable for cache hits

    async def run(
        self,
        messages: list[dict],
        *,
        is_disconnected: DisconnectCheck | None = None,
    ) -> AsyncIterator[ChatEvent]:
        """Yield events for one user turn. ``messages`` is the full prior+new history."""
        convo = list(messages)
        sources: list[Source] = []
        seen_source_keys: set[tuple[str, str, str]] = set()
        usage = {"in": 0, "out": 0, "cache_read": 0, "cache_create": 0}
        deadline = time.monotonic() + self._settings.request_timeout

        for iteration in range(self._settings.max_iterations):
            if is_disconnected and await is_disconnected():
                return
            if time.monotonic() > deadline:
                yield ErrorEvent("timeout", "The request took too long and was stopped.")
                yield DoneEvent()
                return

            try:
                final = None
                async with self._client.messages.stream(
                    model=self._settings.model,
                    max_tokens=self._settings.max_tokens,
                    system=self._system,
                    tools=ANTHROPIC_TOOLS,
                    thinking={"type": "adaptive"},
                    output_config={"effort": self._settings.effort},
                    messages=convo,
                ) as stream:
                    async for event in stream:
                        ev = _translate_stream_event(event)
                        if ev is not None:
                            yield ev
                    final = await stream.get_final_message()
            except anthropic.APIError as exc:
                logger.warning("Anthropic API error: %s", exc)
                yield ErrorEvent(*_classify_api_error(exc))
                yield DoneEvent()
                return

            _accumulate_usage(usage, final)
            convo.append({"role": "assistant", "content": final.content})

            if final.stop_reason == "tool_use":
                async for ev in self._run_tools(final, convo, sources, seen_source_keys):
                    yield ev
                continue

            if final.stop_reason == "refusal":
                detail = getattr(final, "stop_details", None)
                msg = getattr(detail, "explanation", None) or "The request was declined."
                yield ErrorEvent("refusal", msg)
                yield DoneEvent()
                return

            if final.stop_reason == "max_tokens":
                yield ErrorEvent(
                    "truncated",
                    "The answer was cut off (token limit). Try a more specific question.",
                )
                # fall through to emit whatever citations/usage we have, then done.

            # end_turn (or truncated): finish.
            if sources:
                yield CitationsEvent(sources)
            yield UsageEvent(
                usage["in"], usage["out"], usage["cache_read"], usage["cache_create"]
            )
            yield DoneEvent()
            return

        # Exhausted max_iterations without a natural end.
        if sources:
            yield CitationsEvent(sources)
        yield ErrorEvent(
            "max_iterations",
            "The assistant kept calling tools without finishing. Please rephrase or narrow the "
            "question.",
        )
        yield DoneEvent()

    async def _run_tools(
        self,
        final,
        convo: list[dict],
        sources: list[Source],
        seen_source_keys: set[tuple[str, str, str]],
    ) -> AsyncIterator[ChatEvent]:
        """Execute the tool_use blocks in ``final`` and append the tool_result turn to ``convo``."""
        tool_results: list[dict] = []
        for block in final.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            arguments = dict(block.input or {})
            yield ToolCallEvent(block.name, tool_label(block.name, arguments), arguments)

            outcome = execute_tool(self._catalog, block.name, arguments)
            for src in outcome.sources:
                if src.key() not in seen_source_keys:
                    seen_source_keys.add(src.key())
                    sources.append(src)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": outcome.content,
                    "is_error": outcome.is_error,
                }
            )
        convo.append({"role": "user", "content": tool_results})


def _translate_stream_event(event) -> ChatEvent | None:
    """Map a raw Anthropic stream event to a ChatEvent, or None to ignore it."""
    etype = getattr(event, "type", None)
    if etype == "content_block_start":
        if getattr(event.content_block, "type", None) == "thinking":
            return StatusEvent("thinking")
        return None
    if etype == "content_block_delta":
        delta = event.delta
        if getattr(delta, "type", None) == "text_delta":
            return TextDeltaEvent(delta.text)
    return None


def _accumulate_usage(usage: dict, message) -> None:
    u = getattr(message, "usage", None)
    if u is None:
        return
    usage["in"] += getattr(u, "input_tokens", 0) or 0
    usage["out"] += getattr(u, "output_tokens", 0) or 0
    usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
    usage["cache_create"] += getattr(u, "cache_creation_input_tokens", 0) or 0


def _classify_api_error(exc: anthropic.APIError) -> tuple[str, str]:
    """Map a typed Anthropic exception to a (code, user-facing message) pair."""
    if isinstance(exc, anthropic.RateLimitError):
        return "rate_limited", "The assistant is rate limited right now. Please try again shortly."
    if isinstance(exc, anthropic.AuthenticationError):
        return "auth", "The assistant is misconfigured (authentication failed)."
    if isinstance(exc, anthropic.APIConnectionError):
        return "connection", "Could not reach the model. Please try again."
    status = getattr(exc, "status_code", None)
    if status and status >= 500:
        return "server", "The model service had an error. Please try again."
    return "error", "Something went wrong handling the request."
