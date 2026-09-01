from __future__ import annotations

from dataclasses import dataclass

from repo_agent.config import Settings
from repo_agent.tools.base import ToolSpec


class PermissionDenied(PermissionError):
    """Raised when the current policy forbids a tool call."""


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    risk: str


class PermissionGate:
    """Allow or deny tools based on risk class and runtime policy."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def decide(self, spec: ToolSpec) -> PermissionDecision:
        if spec.risk == "execute" and self.settings.read_only:
            return PermissionDecision(
                allowed=False,
                reason="read-only mode forbids execute tools",
                risk=spec.risk,
            )
        if spec.name == "run_tests" and not self.settings.allow_tests:
            return PermissionDecision(
                allowed=False,
                reason="AGENT_ALLOW_TESTS is disabled",
                risk=spec.risk,
            )
        if spec.name == "git_status" and spec.risk != "read":
            return PermissionDecision(
                allowed=False,
                reason="git tools must be read-only",
                risk=spec.risk,
            )
        return PermissionDecision(allowed=True, reason="allowed", risk=spec.risk)

    def check(self, spec: ToolSpec) -> None:
        decision = self.decide(spec)
        if not decision.allowed:
            raise PermissionDenied(f"{spec.name}: {decision.reason}")
