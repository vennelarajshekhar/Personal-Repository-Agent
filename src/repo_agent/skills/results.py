from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    tool: str
    data: Any = None
    error: str | None = None
    truncated: bool = False
    elapsed_ms: int = 0
    denied: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def for_llm(self, max_chars: int = 8000) -> str:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "tool": self.tool,
            "elapsed_ms": self.elapsed_ms,
        }
        if self.denied:
            payload["denied"] = True
        if self.error:
            payload["error"] = self.error
        if self.data is not None:
            payload["data"] = self.data
        if self.truncated:
            payload["truncated"] = True
        if self.metadata:
            payload["metadata"] = self.metadata
        text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
        if len(text) <= max_chars:
            return text
        payload["data"] = _truncate_data(self.data, max_chars)
        payload["truncated"] = True
        return json.dumps(payload, indent=2, default=str, ensure_ascii=False)


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str, ensure_ascii=False)


def _truncate_data(data: Any, max_chars: int) -> Any:
    if isinstance(data, str):
        return data[: max(0, max_chars - 80)] + "\n...[truncated]..."
    if isinstance(data, list):
        kept: list[Any] = []
        for item in data:
            candidate = kept + [item]
            encoded = json_dumps(candidate)
            if len(encoded) > max_chars - 80 and kept:
                break
            kept = candidate
        return kept + [f"...[{len(data) - len(kept)} more items truncated]..."]
    encoded = json_dumps(data)
    if len(encoded) <= max_chars:
        return data
    return encoded[: max(0, max_chars - 80)] + "\n...[truncated]..."
