from __future__ import annotations

import os
import sys

from repo_agent.config import Settings
from repo_agent.skills.safety import run_allowed_command, resolve_under_root


def _pytest_argv(target: str | None) -> list[str]:
    args = [sys.executable, "-m", "pytest", "-q", "--tb=short"]
    if target:
        args.append(target)
    return args


def run_tests(settings: Settings, target: str | None = None) -> dict:
    """Run pytest inside the repository. `target` must stay under the repo root."""
    cwd = settings.repo_root
    pytest_target = None
    if target:
        resolved = resolve_under_root(cwd, target)
        pytest_target = resolved.relative_to(cwd).as_posix()
    extra_env: dict[str, str] = {}
    src = cwd / "src"
    if src.is_dir():
        existing = os.environ.get("PYTHONPATH", "")
        extra_env["PYTHONPATH"] = str(src) if not existing else f"{src}{os.pathsep}{existing}"
    argv = _pytest_argv(pytest_target)
    completed = run_allowed_command(
        argv,
        cwd=cwd,
        timeout=settings.command_timeout,
        extra_env=extra_env or None,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    return {
        "command": " ".join(argv),
        "target": pytest_target or ".",
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": stdout[-4000:],
        "stderr": stderr[-2000:],
    }


def tool_spec(settings: Settings):
    from repo_agent.tools.base import ToolSpec

    def handler(target: str | None = None) -> dict:
        return run_tests(settings, target)

    return ToolSpec(
        name="run_tests",
        description=(
            "Run pytest for this repository in a subprocess (no shell). "
            "Optionally pass a relative test path such as tests/test_service.py. "
            "Does not execute arbitrary commands."
        ),
        parameters={
            "target": {
                "type": "string",
                "description": "Optional test file or directory relative to the repo root.",
            },
        },
        handler=handler,
        risk="execute",
        required=[],
    )
