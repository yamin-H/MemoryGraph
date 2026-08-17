"""Data models for MemoryGraph Python SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class Message:
    """A conversational turn in a session."""
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }


@dataclass
class MemoryResult:
    """The result of querying MemoryGraph."""
    answer: str
    confidence: float
    abstained: bool = False
    abstention_reason: str | None = None

    source_sessions: list[str] = field(default_factory=list)
    facts_examined: int = 0
    query_time_ms: int = 0
    reasoning: str | None = None
    user_id: str = "anonymous"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryResult:
        return cls(
            answer=data.get("answer", ""),
            confidence=float(data.get("confidence", 0.0)),
            abstained=bool(data.get("abstained", False)),
            abstention_reason=data.get("abstention_reason"),
            source_sessions=data.get("source_sessions", []),
            facts_examined=int(data.get("facts_examined", 0)),
            query_time_ms=int(data.get("query_time_ms", 0)),
            reasoning=data.get("reasoning"),
            user_id=data.get("user_id", "anonymous"),
        )
