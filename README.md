# Developer Repository Agent

An agent that **understands and interacts with a software repository**. It answers questions by calling a small, permissioned toolset — never by guessing at files, functions, or test results.

## What it can do

| Tool | Purpose | Risk |
| --- | --- | --- |
| `search_files()` | Glob search, optional content query | read |
| `read_file()` | Bounded UTF-8 file read with line numbers | read |
| `search_functions()` | AST search for Python functions and classes | read |
| `run_tests()` | pytest only, no shell, timeout-bounded | execute |
| `git_status()` | Read-only branch / worktree snapshot | read |

## Skills

- **Tool permissions** — execute tools can be denied (`AGENT_READ_ONLY`, `AGENT_ALLOW_TESTS`).
- **Tool orchestration** — suggested tool order plus duplicate-call suppression.
- **Tool results** — structured JSON, truncation, errors returned to the model.
- **Safe execution** — path confinement to `REPO_ROOT`, no `shell=True`, no git mutations.

## Layout

```text
src/repo_agent/     the agent, tools, and skills
sample_repo/        sample Python package (tasklib) the agent inspects
tests/              tests for the agent itself
Dockerfile          container image
docker-compose.yml  one-command demo
```

`sample_repo` is a tiny task-tracker library (`TaskService`, `JsonTaskStore`, `priority_score`, …) with a passing pytest suite.

## Run locally

Python 3.11+ and git.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install -r requirements.txt
pytest
python -m repo_agent demo
python -m repo_agent tools
```

Live questions read `LLM_API_KEY` from `.env` in this folder (see `.env.example`):

```powershell
python -m repo_agent ask "How does TaskService order the backlog?"
python -m repo_agent chat
```

Point the agent at another repo with `--repo` or `REPO_ROOT`.

## Docker

```powershell
docker compose build
docker compose run --rm agent demo
docker compose run --rm agent tools
docker compose run --rm -e LLM_API_KEY=sk-... agent ask "Where is priority_score defined?"
```

Equivalent without Compose:

```powershell
docker build -t developer-repository-agent:local .
docker run --rm developer-repository-agent:local demo
```

The image includes git, pytest, the agent, and `sample_repo`. Paths cannot escape `/app/sample_repo` (or whatever you set as `REPO_ROOT`).

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `REPO_ROOT` | `./sample_repo` | Only directory tools may read or test |
| `LLM_API_KEY` | empty | Required for `ask` / `chat` |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model |
| `AGENT_ALLOW_TESTS` | `true` | Permit `run_tests()` |
| `AGENT_READ_ONLY` | `false` | Deny all execute tools |
| `AGENT_MAX_STEPS` | `12` | Max tool rounds per question |
| `AGENT_COMMAND_TIMEOUT` | `30` | pytest / git timeout (seconds) |

Copy `.env.example` to `.env` for Compose.
