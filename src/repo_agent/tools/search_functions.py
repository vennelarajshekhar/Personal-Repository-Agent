from __future__ import annotations

import ast
from pathlib import Path

from repo_agent.config import Settings
from repo_agent.skills.safety import iter_files, resolve_under_root


def _docstring(node: ast.AST) -> str | None:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return None
    body = node.body
    if not body:
        return None
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        if isinstance(first.value.value, str):
            return first.value.value.strip().splitlines()[0]
    return None


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = []
    for arg in node.args.args:
        args.append(arg.arg)
    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)
    for arg in node.args.kwonlyargs:
        args.append(arg.arg)
    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)})"


def _collect(path: Path, query: str) -> list[dict]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []
    query_l = query.lower()
    hits: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            kind = "class"
            name = node.name
            signature = f"class {node.name}"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            name = node.name
            signature = _signature(node)
        else:
            continue
        doc = _docstring(node) or ""
        haystack = f"{name} {signature} {doc}".lower()
        if query_l not in haystack:
            continue
        hits.append(
            {
                "name": name,
                "kind": kind,
                "line": getattr(node, "lineno", None),
                "signature": signature,
                "doc": doc or None,
            }
        )
    return hits


def search_functions(
    settings: Settings,
    query: str,
    path: str = ".",
    max_results: int = 40,
) -> dict:
    """Find Python functions and classes whose name, signature, or docstring matches query."""
    start = resolve_under_root(settings.repo_root, path)
    results: list[dict] = []
    files = [start] if start.is_file() else iter_files(settings.repo_root, start)
    for file_path in files:
        if file_path.suffix != ".py":
            continue
        rel = file_path.relative_to(settings.repo_root).as_posix()
        for hit in _collect(file_path, query):
            results.append({"path": rel, **hit})
            if len(results) >= max_results:
                return {
                    "query": query,
                    "count": len(results),
                    "symbols": results,
                    "truncated": True,
                }
    return {
        "query": query,
        "count": len(results),
        "symbols": results,
        "truncated": False,
    }


def tool_spec(settings: Settings):
    from repo_agent.tools.base import ToolSpec

    def handler(query: str, path: str = ".", max_results: int = 40) -> dict:
        return search_functions(settings, query, path, max_results)

    return ToolSpec(
        name="search_functions",
        description=(
            "Search Python function, async function, and class definitions using the AST. "
            "Matches against name, signature, and the first docstring line."
        ),
        parameters={
            "query": {
                "type": "string",
                "description": "Case-insensitive substring to match against symbol names and docs.",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search, relative to the repo root.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of symbols to return (default 40).",
            },
        },
        handler=handler,
        risk="read",
        required=["query"],
    )
