from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".eggs",
}


class SafetyError(RuntimeError):
    """Raised when a tool would escape the allowed repository or run unsafely."""


def ensure_repo_exists(repo_root: Path) -> Path:
    root = repo_root.resolve()
    if not root.exists():
        raise SafetyError(f"repository root does not exist: {root}")
    if not root.is_dir():
        raise SafetyError(f"repository root is not a directory: {root}")
    return root


def resolve_under_root(repo_root: Path, relative: str | os.PathLike[str] | None) -> Path:
    """Resolve a user-supplied path and require it to stay inside repo_root."""
    root = ensure_repo_exists(repo_root)
    candidate = Path(relative or ".")
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        # Normalize Windows and POSIX separators without allowing `..` escapes.
        normalized = str(PurePosixPath(candidate.as_posix()))
        resolved = (root / normalized).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SafetyError(f"path escapes repository root: {relative}") from exc
    if resolved.is_symlink():
        link_target = resolved.resolve()
        try:
            link_target.relative_to(root)
        except ValueError as exc:
            raise SafetyError(f"symlink escapes repository root: {relative}") from exc
    return resolved


def is_skipped_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES


def iter_files(root: Path, start: Path | None = None):
    start = start or root
    for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
        current = Path(dirpath)
        dirnames[:] = sorted(
            name for name in dirnames if name not in SKIP_DIR_NAMES
        )
        for name in sorted(filenames):
            path = current / name
            if path.is_symlink():
                continue
            yield path


def run_allowed_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a fixed argv list with no shell expansion."""
    if not argv:
        raise SafetyError("empty command")
    if any(not isinstance(part, str) or part == "" for part in argv):
        raise SafetyError("command arguments must be non-empty strings")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if extra_env:
        env.update(extra_env)
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise SafetyError(f"command timed out after {timeout}s: {' '.join(argv)}") from exc
    except FileNotFoundError as exc:
        raise SafetyError(f"executable not found: {argv[0]}") from exc


def read_text_file(path: Path, max_bytes: int) -> str:
    if not path.is_file():
        raise SafetyError(f"not a file: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise SafetyError(
            f"file exceeds size limit ({size} bytes > {max_bytes} bytes): {path}"
        )
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SafetyError(f"file is not valid UTF-8 text: {path}") from exc
