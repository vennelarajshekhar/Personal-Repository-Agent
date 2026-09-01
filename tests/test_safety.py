from pathlib import Path

from repo_agent.skills.safety import SafetyError, resolve_under_root, run_allowed_command


def test_empty_command_rejected(tmp_path: Path):
    try:
        run_allowed_command([], cwd=tmp_path, timeout=1)
        raised = False
    except SafetyError:
        raised = True
    assert raised


def test_relative_escape_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.txt").write_text("hi", encoding="utf-8")
    try:
        resolve_under_root(repo, "..")
        raised = False
    except SafetyError:
        raised = True
    assert raised


def test_nested_file_allowed(tmp_path: Path):
    repo = tmp_path / "repo"
    nested = repo / "src" / "app.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("print(1)\n", encoding="utf-8")
    resolved = resolve_under_root(repo, "src/app.py")
    assert resolved == nested.resolve()
