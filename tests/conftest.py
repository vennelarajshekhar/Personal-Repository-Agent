from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_agent.agent import RepositoryAgent
from repo_agent.config import Settings


SAMPLE_REPO = Path(__file__).resolve().parents[1] / "sample_repo"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def sample_repo() -> Path:
    return SAMPLE_REPO


@pytest.fixture
def git_sample_repo(sample_repo: Path) -> Path:
    git_dir = sample_repo / ".git"
    if not git_dir.exists():
        _git(sample_repo, "init")
        _git(sample_repo, "config", "user.email", "agent@test")
        _git(sample_repo, "config", "user.name", "Agent Test")
        _git(sample_repo, "add", ".")
        _git(sample_repo, "commit", "-m", "test fixture")
    return sample_repo


@pytest.fixture
def settings(git_sample_repo: Path) -> Settings:
    return Settings(
        repo_root=git_sample_repo,
        llm_api_key="",
        llm_base_url="https://api.openai.com/v1",
        llm_model="gpt-4o-mini",
        allow_tests=True,
        read_only=False,
        max_steps=8,
        command_timeout=30,
        max_file_bytes=256 * 1024,
        max_output_chars=8000,
    )


@pytest.fixture
def agent(settings: Settings) -> RepositoryAgent:
    return RepositoryAgent(settings)
