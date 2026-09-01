from pathlib import Path

from repo_agent.config import _dotenv_map, load_settings


def test_load_settings_reads_dotenv(tmp_path: Path, monkeypatch):
    (tmp_path / "sample_repo").mkdir()
    (tmp_path / ".env").write_text(
        'LLM_API_KEY="sk-test-from-dotenv"\nLLM_MODEL=gpt-4o-mini\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("repo_agent.config._project_root", lambda: tmp_path)
    _dotenv_map.cache_clear()
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("REPO_ROOT", raising=False)
    try:
        settings = load_settings()
        assert settings.llm_api_key == "sk-test-from-dotenv"
        assert settings.llm_configured is True
        assert settings.repo_root == (tmp_path / "sample_repo").resolve()
    finally:
        _dotenv_map.cache_clear()


def test_missing_docker_repo_root_falls_back(tmp_path: Path, monkeypatch):
    (tmp_path / "sample_repo").mkdir()
    (tmp_path / ".env").write_text(
        "LLM_API_KEY=sk-test\nREPO_ROOT=/app/sample_repo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("repo_agent.config._project_root", lambda: tmp_path)
    _dotenv_map.cache_clear()
    monkeypatch.delenv("REPO_ROOT", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    try:
        settings = load_settings()
        assert settings.repo_root == (tmp_path / "sample_repo").resolve()
    finally:
        _dotenv_map.cache_clear()
