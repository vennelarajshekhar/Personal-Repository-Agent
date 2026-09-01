from __future__ import annotations

from pathlib import Path

from repo_agent.skills.safety import run_allowed_command


def ensure_git_repository(root: Path) -> None:
    """Initialize a local git repo so git_status() works on a freshly copied sample."""
    git_dir = root / ".git"
    if git_dir.exists():
        return
    run_allowed_command(["git", "init"], cwd=root, timeout=15)
    run_allowed_command(["git", "add", "."], cwd=root, timeout=15)
    run_allowed_command(
        [
            "git",
            "-c",
            "user.email=agent@localhost",
            "-c",
            "user.name=Repository Agent",
            "commit",
            "-m",
            "Initial sample Python repository",
        ],
        cwd=root,
        timeout=15,
    )
