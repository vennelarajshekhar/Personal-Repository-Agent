from __future__ import annotations

from dataclasses import dataclass, field

from repo_agent.tools.base import ToolSpec


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict
    fingerprint: str


class Orchestrator:
    """Track tool usage, stop duplicate loops, and hint at useful next steps."""

    def __init__(self, max_repeats: int = 2):
        self.max_repeats = max_repeats
        self.history: list[ToolCallRecord] = []

    def fingerprint(self, name: str, arguments: dict) -> str:
        items = tuple(sorted((str(k), repr(v)) for k, v in arguments.items()))
        return f"{name}:{items}"

    def before_call(self, spec: ToolSpec, arguments: dict) -> str | None:
        """Return a skip reason if this call should not run again."""
        fp = self.fingerprint(spec.name, arguments)
        repeats = sum(1 for record in self.history if record.fingerprint == fp)
        if repeats >= self.max_repeats:
            return (
                f"skipped duplicate {spec.name} call with the same arguments "
                f"(already ran {repeats} times)"
            )
        return None

    def after_call(self, spec: ToolSpec, arguments: dict) -> None:
        self.history.append(
            ToolCallRecord(
                name=spec.name,
                arguments=dict(arguments),
                fingerprint=self.fingerprint(spec.name, arguments),
            )
        )

    def suggest(self, question: str) -> list[str]:
        q = question.lower()
        suggestions: list[str] = []
        if any(word in q for word in ("test", "pytest", "fail", "coverage")):
            suggestions.extend(["search_files", "read_file", "run_tests"])
        if any(word in q for word in ("git", "branch", "commit", "status", "dirty")):
            suggestions.append("git_status")
        if any(word in q for word in ("function", "def ", "class", "method", "where is")):
            suggestions.append("search_functions")
        if not suggestions:
            suggestions.extend(["search_files", "search_functions", "read_file"])
        seen: set[str] = set()
        ordered: list[str] = []
        for name in suggestions:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    def called_names(self) -> list[str]:
        return [record.name for record in self.history]
