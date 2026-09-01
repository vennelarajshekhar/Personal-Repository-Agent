from __future__ import annotations

import argparse
import json
import sys

from repo_agent.agent import RepositoryAgent
from repo_agent.bootstrap import ensure_git_repository
from repo_agent.config import load_settings
from repo_agent.llm import LLMError
from repo_agent.skills.safety import SafetyError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo-agent",
        description="Developer Repository Agent - inspect and reason about a software repository.",
    )
    parser.add_argument(
        "--repo",
        help="Repository root to inspect (default: REPO_ROOT or ./sample_repo).",
    )
    sub = parser.add_subparsers(dest="command")

    ask = sub.add_parser("ask", help="Ask a question using the LLM + tools.")
    ask.add_argument("question", nargs="+", help="Question about the repository.")

    sub.add_parser("demo", help="Run a scripted exploration without an LLM key.")
    sub.add_parser("tools", help="List available tools and permission status.")
    sub.add_parser("chat", help="Interactive multi-turn chat (requires LLM_API_KEY).")

    parser.set_defaults(command="demo")
    args = parser.parse_args(argv)
    settings = load_settings(args.repo)
    if args.command in {"ask", "chat"} and not settings.llm_configured:
        print(
            "error: LLM_API_KEY is missing. Put your OpenAI key in the .env file "
            "next to pyproject.toml, then rerun.",
            file=sys.stderr,
        )
        return 1
    try:
        ensure_git_repository(settings.repo_root)
    except SafetyError:
        pass
    agent = RepositoryAgent(settings, printer=_print)

    if args.command == "tools":
        return _cmd_tools(agent)
    if args.command == "demo":
        return _cmd_demo(agent)
    if args.command == "ask":
        return _cmd_ask(agent, " ".join(args.question))
    if args.command == "chat":
        return _cmd_chat(agent)
    parser.print_help()
    return 2


def _print(message: str) -> None:
    print(message, flush=True)


def _cmd_tools(agent: RepositoryAgent) -> int:
    print(f"Repository: {agent.settings.repo_root}")
    print(f"Read-only: {agent.settings.read_only}  Allow tests: {agent.settings.allow_tests}")
    print()
    for spec in agent.registry.values():
        decision = agent.permissions.decide(spec)
        status = "allow" if decision.allowed else f"deny ({decision.reason})"
        print(f"- {spec.name:18} risk={spec.risk:8} {status}")
        print(f"  {spec.description.splitlines()[0]}")
    return 0


def _cmd_demo(agent: RepositoryAgent) -> int:
    print("Developer Repository Agent - offline demo")
    print(f"Inspecting: {agent.settings.repo_root}")
    print()

    files = agent.execute("search_files", {"pattern": "*.py", "path": "."})
    functions = agent.execute("search_functions", {"query": "task", "path": "src"})
    readme = agent.execute("read_file", {"path": "README.md", "line_count": 40})
    tests = agent.execute("run_tests", {"target": "tests"})
    status = agent.execute("git_status", {})

    print("\n=== search_files(*.py) ===")
    _show(files)
    print("\n=== search_functions('task') ===")
    _show(functions)
    print("\n=== read_file(README.md) ===")
    _show(readme)
    print("\n=== run_tests(tests) ===")
    _show(tests)
    print("\n=== git_status() ===")
    _show(status)

    print("\n=== Summary ===")
    file_count = (files.data or {}).get("count") if files.ok else "unavailable"
    symbol_count = (functions.data or {}).get("count") if functions.ok else "unavailable"
    tests_ok = (tests.data or {}).get("passed") if tests.ok else None
    branch = (status.data or {}).get("branch") if status.ok else "n/a"
    print(f"Python files found: {file_count}")
    print(f"Task-related symbols: {symbol_count}")
    print(f"Tests passed: {tests_ok}")
    print(f"Git branch: {branch}")
    print("\nAsk a live question with: python -m repo_agent ask \"How does TaskService work?\"")
    return 0 if files.ok else 1


def _cmd_ask(agent: RepositoryAgent, question: str) -> int:
    print(
        f"LLM: {agent.settings.llm_model} @ {agent.settings.llm_base_url}",
        flush=True,
    )
    print(f"Repo: {agent.settings.repo_root}", flush=True)
    try:
        turn = agent.run(question)
    except LLMError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print()
    print(turn.final_answer)
    return 0


def _cmd_chat(agent: RepositoryAgent) -> int:
    print("Interactive mode. Empty line or Ctrl+C to exit.")
    print(f"Repository: {agent.settings.repo_root}")
    try:
        while True:
            try:
                question = input("\nrepo-agent> ").strip()
            except EOFError:
                print()
                return 0
            if not question:
                return 0
            try:
                turn = agent.run(question)
            except LLMError as exc:
                print(f"error: {exc}")
                return 1
            print()
            print(turn.final_answer)
    except KeyboardInterrupt:
        print()
        return 0


def _show(result) -> None:
    if not result.ok:
        print(f"[error] {result.error}")
        return
    print(json.dumps(result.data, indent=2, default=str)[:2000])


if __name__ == "__main__":
    raise SystemExit(main())
