from repo_agent.cli import main


def test_tools_command(capsys):
    assert main(["tools"]) == 0
    out = capsys.readouterr().out
    assert "search_files" in out
    assert "run_tests" in out
    assert "git_status" in out
