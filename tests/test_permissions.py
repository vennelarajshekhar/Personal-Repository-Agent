from repo_agent.agent import RepositoryAgent
from repo_agent.config import Settings


def test_run_tests_denied_when_disallowed(settings: Settings):
    locked = Settings(**{**settings.__dict__, "allow_tests": False})
    agent = RepositoryAgent(locked)
    result = agent.execute("run_tests", {})
    assert result.ok is False
    assert result.denied is True
    assert "AGENT_ALLOW_TESTS" in (result.error or "")


def test_run_tests_denied_in_read_only(settings: Settings):
    locked = Settings(**{**settings.__dict__, "read_only": True})
    agent = RepositoryAgent(locked)
    result = agent.execute("run_tests", {})
    assert result.denied is True


def test_read_tools_allowed_in_read_only(settings: Settings):
    locked = Settings(**{**settings.__dict__, "read_only": True})
    agent = RepositoryAgent(locked)
    result = agent.execute("search_files", {"pattern": "README.md"})
    assert result.ok is True
