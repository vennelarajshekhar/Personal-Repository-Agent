from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().strip('"').strip("'")


@lru_cache(maxsize=1)
def _dotenv_map() -> dict[str, str]:
    path = _project_root() / ".env"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for key, raw in dotenv_values(path).items():
        if key and raw is not None and _clean(raw):
            values[key] = _clean(raw)
    return values


def _env(name: str, default: str = "") -> str:
    live = _clean(os.environ.get(name))
    if live:
        return live
    return _dotenv_map().get(name, default)


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    allow_tests: bool
    read_only: bool
    max_steps: int
    command_timeout: int
    max_file_bytes: int
    max_output_chars: int

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip())


def _default_repo_root() -> Path:
    raw = _env("REPO_ROOT")
    if raw:
        candidate = Path(raw).expanduser()
        if candidate.exists():
            return candidate.resolve()
    return (_project_root() / "sample_repo").resolve()


def load_settings(repo_root: str | Path | None = None) -> Settings:
    root = Path(repo_root).expanduser().resolve() if repo_root else _default_repo_root()
    return Settings(
        repo_root=root,
        llm_api_key=_env("LLM_API_KEY") or _env("OPENAI_API_KEY"),
        llm_base_url=_env("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_model=_env("LLM_MODEL", "gpt-4o-mini"),
        allow_tests=_as_bool(_env("AGENT_ALLOW_TESTS"), True),
        read_only=_as_bool(_env("AGENT_READ_ONLY"), False),
        max_steps=int(_env("AGENT_MAX_STEPS", "12")),
        command_timeout=int(_env("AGENT_COMMAND_TIMEOUT", "30")),
        max_file_bytes=int(_env("AGENT_MAX_FILE_BYTES", str(256 * 1024))),
        max_output_chars=int(_env("AGENT_MAX_OUTPUT_CHARS", "8000")),
    )
