from __future__ import annotations

from repo_agent.config import Settings
from repo_agent.skills.safety import read_text_file, resolve_under_root


def read_file(
    settings: Settings,
    path: str,
    start_line: int = 1,
    line_count: int | None = None,
) -> dict:
    """Read a UTF-8 text file from the repository with optional line slicing."""
    target = resolve_under_root(settings.repo_root, path)
    text = read_text_file(target, settings.max_file_bytes)
    lines = text.splitlines()
    if start_line < 1:
        start_line = 1
    start_idx = start_line - 1
    if start_idx >= len(lines):
        selected: list[str] = []
    elif line_count is None:
        selected = lines[start_idx:]
    else:
        selected = lines[start_idx : start_idx + max(0, line_count)]
    numbered = [f"{start_line + i:>4}| {line}" for i, line in enumerate(selected)]
    return {
        "path": target.relative_to(settings.repo_root).as_posix(),
        "start_line": start_line,
        "end_line": start_line + len(selected) - 1 if selected else start_line - 1,
        "total_lines": len(lines),
        "content": "\n".join(numbered),
    }


def tool_spec(settings: Settings):
    from repo_agent.tools.base import ToolSpec

    def handler(path: str, start_line: int = 1, line_count: int | None = None) -> dict:
        return read_file(settings, path, start_line, line_count)

    return ToolSpec(
        name="read_file",
        description=(
            "Read a UTF-8 text file from the repository. `path` is relative to the repo root. "
            "Use start_line and line_count to read a slice instead of the whole file."
        ),
        parameters={
            "path": {
                "type": "string",
                "description": "File path relative to the repository root.",
            },
            "start_line": {
                "type": "integer",
                "description": "1-based line number to start reading from (default 1).",
            },
            "line_count": {
                "type": "integer",
                "description": "Maximum number of lines to return. Omit to read through EOF.",
            },
        },
        handler=handler,
        risk="read",
        required=["path"],
    )
