from __future__ import annotations

from fnmatch import fnmatch

from repo_agent.config import Settings
from repo_agent.skills.safety import iter_files, resolve_under_root


def search_files(
    settings: Settings,
    pattern: str = "*",
    query: str | None = None,
    path: str = ".",
    max_results: int = 50,
) -> dict:
    """Find files by glob pattern and optionally by file-content substring."""
    start = resolve_under_root(settings.repo_root, path)
    matches: list[dict] = []
    query_l = query.lower() if query else None
    for file_path in iter_files(settings.repo_root, start if start.is_dir() else start.parent):
        if start.is_file() and file_path != start:
            continue
        rel = file_path.relative_to(settings.repo_root).as_posix()
        if not fnmatch(rel, pattern) and not fnmatch(file_path.name, pattern):
            continue
        item: dict = {"path": rel}
        if query_l is not None:
            try:
                text = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            hits = []
            for i, line in enumerate(text.splitlines(), start=1):
                if query_l in line.lower():
                    hits.append({"line": i, "text": line.strip()})
                    if len(hits) >= 5:
                        break
            if not hits:
                continue
            item["matches"] = hits
        matches.append(item)
        if len(matches) >= max_results:
            break
    return {
        "root": str(settings.repo_root),
        "pattern": pattern,
        "query": query,
        "count": len(matches),
        "files": matches,
        "truncated": len(matches) >= max_results,
    }


def tool_spec(settings: Settings):
    from repo_agent.tools.base import ToolSpec

    def handler(
        pattern: str = "*",
        query: str | None = None,
        path: str = ".",
        max_results: int = 50,
    ) -> dict:
        return search_files(settings, pattern, query, path, max_results)

    return ToolSpec(
        name="search_files",
        description=(
            "Search the repository for files. Use glob `pattern` (e.g. '*.py', 'tests/**') "
            "and optional case-insensitive content `query`. Paths are relative to the repo root."
        ),
        parameters={
            "pattern": {
                "type": "string",
                "description": "Glob pattern matched against relative paths and filenames.",
            },
            "query": {
                "type": "string",
                "description": "Optional substring to find inside file contents.",
            },
            "path": {
                "type": "string",
                "description": "Subdirectory or file to search under, relative to the repo root.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of files to return (default 50).",
            },
        },
        handler=handler,
        risk="read",
        required=[],
    )
