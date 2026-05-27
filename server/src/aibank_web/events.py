"""Wire model for streaming chat events.

The agent loop yields :class:`ChatEvent`s; the HTTP layer serializes each with :func:`to_sse`.
Keeping the event model separate from the transport means the loop never touches SSE framing
and can be unit-tested directly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Source:
    """A catalog asset the agent actually retrieved -- the ground truth for a citation.

    ``name`` is the canonical asset slug; ``reference`` is set only for a skill reference doc.
    The frontend links these to the in-app viewer at ``/a/{kind}/{name}``.
    """

    kind: str  # "skill" | "agent" | "rule"
    name: str
    reference: str | None = None

    def key(self) -> tuple[str, str, str]:
        """De-dup key (case-insensitive)."""
        return (self.kind, self.name.lower(), (self.reference or "").lower())


# --------------------------------------------------------------------------- #
# Events (each becomes one SSE frame: `event: <type>` + `data: <json>`)
# --------------------------------------------------------------------------- #


@dataclass
class ChatEvent:
    """Base event. Subclasses set ``event`` and provide ``payload()``."""

    event: str = field(init=False, default="message")

    def payload(self) -> dict:
        return {}


@dataclass
class ToolCallEvent(ChatEvent):
    """The agent is invoking a tool; carries a human-readable label for the activity chip."""

    name: str
    label: str
    arguments: dict

    def __post_init__(self) -> None:
        self.event = "tool_call"

    def payload(self) -> dict:
        return {"name": self.name, "label": self.label, "arguments": self.arguments}


@dataclass
class TextDeltaEvent(ChatEvent):
    """An incremental chunk of the assistant's answer text."""

    text: str

    def __post_init__(self) -> None:
        self.event = "text"

    def payload(self) -> dict:
        return {"text": self.text}


@dataclass
class StatusEvent(ChatEvent):
    """A coarse progress signal (e.g. the model is thinking before answering)."""

    phase: str

    def __post_init__(self) -> None:
        self.event = "status"

    def payload(self) -> dict:
        return {"phase": self.phase}


@dataclass
class CitationsEvent(ChatEvent):
    """The de-duplicated set of sources the answer is grounded in."""

    sources: list[Source]

    def __post_init__(self) -> None:
        self.event = "citations"

    def payload(self) -> dict:
        return {"sources": [asdict(s) for s in self.sources]}


@dataclass
class UsageEvent(ChatEvent):
    """Token accounting for observability (includes cache hit counters)."""

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int

    def __post_init__(self) -> None:
        self.event = "usage"

    def payload(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
        }


@dataclass
class ErrorEvent(ChatEvent):
    """A terminal error; the client should surface ``message`` and stop."""

    code: str
    message: str

    def __post_init__(self) -> None:
        self.event = "error"

    def payload(self) -> dict:
        return {"code": self.code, "message": self.message}


@dataclass
class DoneEvent(ChatEvent):
    """End of stream. Always emitted last so the client has a clean terminus."""

    def __post_init__(self) -> None:
        self.event = "done"


def to_sse(event: ChatEvent) -> dict:
    """Render a ChatEvent as an sse-starlette message dict (``event`` + ``data``)."""
    return {"event": event.event, "data": json.dumps(event.payload(), ensure_ascii=False)}
