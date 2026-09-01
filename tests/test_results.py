from repo_agent.skills.results import ToolResult


def test_for_llm_includes_error():
    result = ToolResult(ok=False, tool="read_file", error="path escapes repository root")
    text = result.for_llm()
    assert "read_file" in text
    assert "path escapes" in text


def test_for_llm_truncates_long_lists():
    result = ToolResult(ok=True, tool="search_files", data=["x" * 200] * 80)
    text = result.for_llm(max_chars=400)
    assert "truncated" in text.lower()
