from repo_agent.skills.safety import SafetyError, resolve_under_root
from repo_agent.tools.read_file import read_file
from repo_agent.tools.search_files import search_files
from repo_agent.tools.search_functions import search_functions


def test_search_files_finds_python_modules(settings):
    result = search_files(settings, pattern="*.py", path="src")
    paths = {item["path"] for item in result["files"]}
    assert "src/tasklib/service.py" in paths
    assert result["count"] >= 4


def test_search_files_content_query(settings):
    result = search_files(settings, pattern="*.py", query="priority_score")
    assert result["count"] >= 1
    assert any("priority_score" in hit["text"] for item in result["files"] for hit in item["matches"])


def test_read_file_numbers_lines(settings):
    result = read_file(settings, "src/tasklib/service.py", start_line=1, line_count=8)
    assert result["path"] == "src/tasklib/service.py"
    assert "1|" in result["content"].splitlines()[0]


def test_search_functions_finds_task_service(settings):
    result = search_functions(settings, query="TaskService")
    names = {item["name"] for item in result["symbols"]}
    assert "TaskService" in names


def test_search_functions_finds_priority_score(settings):
    result = search_functions(settings, query="priority_score")
    match = next(item for item in result["symbols"] if item["name"] == "priority_score")
    assert match["kind"] == "function"
    assert match["path"].endswith("utils.py")


def test_read_file_rejects_escape(settings):
    try:
        read_file(settings, "../pyproject.toml")
        raised = False
    except SafetyError:
        raised = True
    assert raised


def test_resolve_under_root_blocks_absolute_escape(settings, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("nope", encoding="utf-8")
    try:
        resolve_under_root(settings.repo_root, str(outside))
        raised = False
    except SafetyError:
        raised = True
    assert raised
