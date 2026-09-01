from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repo_agent.config import Settings
    from repo_agent.tools.base import ToolSpec


def build_registry(settings: "Settings") -> dict[str, "ToolSpec"]:
    from repo_agent.tools.git_status import tool_spec as git_status_spec
    from repo_agent.tools.read_file import tool_spec as read_file_spec
    from repo_agent.tools.run_tests import tool_spec as run_tests_spec
    from repo_agent.tools.search_files import tool_spec as search_files_spec
    from repo_agent.tools.search_functions import tool_spec as search_functions_spec

    specs = [
        search_files_spec(settings),
        read_file_spec(settings),
        search_functions_spec(settings),
        run_tests_spec(settings),
        git_status_spec(settings),
    ]
    return {spec.name: spec for spec in specs}


def openai_tools(registry: dict[str, "ToolSpec"]) -> list[dict]:
    return [spec.openai_schema() for spec in registry.values()]
