from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from typing import Any, Callable


ToolHandler = Callable[..., Any]


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    risk: str = "read"  # read | execute
    required: list[str] = field(default_factory=list)

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                    "additionalProperties": False,
                },
            },
        }


def parse_call_arguments(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    raw = raw.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = ast.literal_eval(raw)
    if not isinstance(parsed, dict):
        raise ValueError("tool arguments must be a JSON object")
    return parsed
