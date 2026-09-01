from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from repo_agent.config import Settings
from repo_agent.llm import LLMClient
from repo_agent.prompts import SYSTEM_PROMPT
from repo_agent.skills.orchestration import Orchestrator
from repo_agent.skills.permissions import PermissionDenied, PermissionGate
from repo_agent.skills.results import ToolResult
from repo_agent.skills.safety import SafetyError
from repo_agent.tools import build_registry, openai_tools
from repo_agent.tools.base import ToolSpec, parse_call_arguments

Printer = Callable[[str], None]


@dataclass
class AgentTurn:
    final_answer: str
    steps: int
    tool_results: list[ToolResult] = field(default_factory=list)


class RepositoryAgent:
    def __init__(
        self,
        settings: Settings,
        llm: LLMClient | None = None,
        printer: Printer | None = None,
    ):
        self.settings = settings
        self.llm = llm or LLMClient(settings)
        self.printer = printer or (lambda _msg: None)
        self.registry = build_registry(settings)
        self.permissions = PermissionGate(settings)
        self.orchestrator = Orchestrator()

    def run(self, question: str) -> AgentTurn:
        suggestions = self.orchestrator.suggest(question)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    f"Repository root: {self.settings.repo_root}\n"
                    f"Suggested tool order: {', '.join(suggestions)}"
                ),
            },
            {"role": "user", "content": question},
        ]
        results: list[ToolResult] = []
        tools = openai_tools(self.registry)

        for step in range(1, self.settings.max_steps + 1):
            message = self.llm.chat(messages, tools)
            tool_calls = message.get("tool_calls") or []
            assistant_content = message.get("content") or ""
            if not tool_calls:
                answer = assistant_content.strip() or "I could not produce an answer."
                return AgentTurn(final_answer=answer, steps=step, tool_results=results)

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_content or None,
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                result = self._execute_tool_call(call)
                results.append(result)
                call_id = call.get("id") or call.get("function", {}).get("name", "tool")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": result.tool,
                        "content": result.for_llm(self.settings.max_output_chars),
                    }
                )

        return AgentTurn(
            final_answer=(
                "Stopped after the maximum number of tool steps without a final answer. "
                "Try a more specific question."
            ),
            steps=self.settings.max_steps,
            tool_results=results,
        )

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        spec = self.registry.get(name)
        if spec is None:
            return ToolResult(ok=False, tool=name, error=f"unknown tool: {name}")
        return self._invoke(spec, arguments)

    def _execute_tool_call(self, call: dict[str, Any]) -> ToolResult:
        function = call.get("function") or {}
        name = function.get("name") or "unknown"
        spec = self.registry.get(name)
        if spec is None:
            return ToolResult(ok=False, tool=name, error=f"unknown tool: {name}")
        try:
            arguments = parse_call_arguments(function.get("arguments"))
        except (ValueError, SyntaxError) as exc:
            return ToolResult(ok=False, tool=name, error=f"invalid arguments: {exc}")
        return self._invoke(spec, arguments)

    def _invoke(self, spec: ToolSpec, arguments: dict[str, Any]) -> ToolResult:
        self.printer(f"-> {spec.name}({_brief_args(arguments)})")
        try:
            self.permissions.check(spec)
        except PermissionDenied as exc:
            return ToolResult(ok=False, tool=spec.name, error=str(exc), denied=True)

        skip_reason = self.orchestrator.before_call(spec, arguments)
        if skip_reason:
            return ToolResult(
                ok=False,
                tool=spec.name,
                error=skip_reason,
                metadata={"skipped": True},
            )

        started = time.perf_counter()
        try:
            data = spec.handler(**arguments)
        except TypeError as exc:
            return ToolResult(ok=False, tool=spec.name, error=f"bad arguments: {exc}")
        except SafetyError as exc:
            return ToolResult(ok=False, tool=spec.name, error=str(exc))
        except Exception as exc:  # noqa: BLE001 — surface unexpected tool failures to the LLM
            return ToolResult(ok=False, tool=spec.name, error=f"{type(exc).__name__}: {exc}")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self.orchestrator.after_call(spec, arguments)
        result = ToolResult(ok=True, tool=spec.name, data=data, elapsed_ms=elapsed_ms)
        preview = result.for_llm(self.settings.max_output_chars)
        if len(preview) >= self.settings.max_output_chars:
            result.truncated = True
        return result


def _brief_args(arguments: dict[str, Any]) -> str:
    parts = []
    for key, value in arguments.items():
        text = repr(value)
        if len(text) > 40:
            text = text[:37] + "..."
        parts.append(f"{key}={text}")
    return ", ".join(parts)
