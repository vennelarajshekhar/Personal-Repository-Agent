from __future__ import annotations

from repo_agent.config import Settings
from repo_agent.skills.safety import SafetyError, run_allowed_command


def _git(settings: Settings, args: list[str]) -> str:
    completed = run_allowed_command(
        ["git", *args],
        cwd=settings.repo_root,
        timeout=min(settings.command_timeout, 15),
    )
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "git command failed").strip()
        raise SafetyError(err)
    return (completed.stdout or "").strip()


def git_status(settings: Settings) -> dict:
    """Read-only snapshot of the current git worktree."""
    inside = _git(settings, ["rev-parse", "--is-inside-work-tree"])
    if inside != "true":
        raise SafetyError("path is not a git work tree")
    branch = _git(settings, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = _git(settings, ["log", "-1", "--format=%h %s"])
    porcelain = _git(settings, ["status", "--porcelain=v1"])
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        index, worktree, path = line[0], line[1], line[3:]
        if path.startswith(" ") or " -> " in path:
            path = path.strip()
        if index == "?" and worktree == "?":
            untracked.append(path)
        else:
            if index != " ":
                staged.append(f"{index} {path}")
            if worktree != " ":
                unstaged.append(f"{worktree} {path}")
    return {
        "branch": branch,
        "head": head,
        "clean": not (staged or unstaged or untracked),
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
    }


def tool_spec(settings: Settings):
    from repo_agent.tools.base import ToolSpec

    def handler() -> dict:
        return git_status(settings)

    return ToolSpec(
        name="git_status",
        description=(
            "Return the current git branch, latest commit, and a read-only porcelain status. "
            "Never mutates the repository."
        ),
        parameters={},
        handler=handler,
        risk="read",
        required=[],
    )
