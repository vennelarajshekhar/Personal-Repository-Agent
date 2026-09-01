from repo_agent.skills.orchestration import Orchestrator
from repo_agent.tools.base import ToolSpec


def _spec(name: str = "search_files") -> ToolSpec:
    return ToolSpec(name=name, description="", parameters={}, handler=lambda: None)


def test_duplicate_calls_are_skipped():
    orch = Orchestrator(max_repeats=2)
    spec = _spec()
    args = {"query": "Task"}
    assert orch.before_call(spec, args) is None
    orch.after_call(spec, args)
    assert orch.before_call(spec, args) is None
    orch.after_call(spec, args)
    reason = orch.before_call(spec, args)
    assert reason is not None
    assert "duplicate" in reason


def test_suggests_tests_for_failing_question():
    orch = Orchestrator()
    assert "run_tests" in orch.suggest("why are the tests failing?")
    assert "git_status" in orch.suggest("is the git status clean?")
    assert "search_functions" in orch.suggest("where is the complete method?")
