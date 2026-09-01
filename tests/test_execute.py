from repo_agent.tools.git_status import git_status
from repo_agent.tools.run_tests import run_tests


def test_git_status_reports_branch(settings):
    result = git_status(settings)
    assert result["branch"]
    assert "head" in result
    assert result["clean"] in {True, False}


def test_run_tests_passes_sample_repo(settings):
    result = run_tests(settings, target="tests")
    assert result["passed"] is True
    assert result["exit_code"] == 0


def test_unknown_tool_is_safe(agent):
    result = agent.execute("rm_rf", {"path": "/"})
    assert result.ok is False
    assert "unknown tool" in (result.error or "")
