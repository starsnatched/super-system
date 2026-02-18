# super-system

Multi-agent software engineering team powered by Claude. Describe what you want built and a team of 9 specialist AI agents collaborates through an 8-phase development lifecycle to produce production-ready code.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- A valid Anthropic API key (set `ANTHROPIC_API_KEY` in your environment)

## Install

```bash
git clone <repo-url> && cd super-system
uv sync
```

## Usage

Pass your project description as an argument:

```bash
uv run super-system "Build a REST API for a todo app with SQLite persistence"
```

Build into a specific directory:

```bash
uv run super-system -C /path/to/project "Build a CLI tool that converts CSV to JSON"
```

Pipe a prompt from a file:

```bash
cat spec.txt | uv run super-system
```

Enable verbose logging to see agent dispatch details:

```bash
uv run super-system -v "Build a markdown blog generator"
```

### Options

| Flag | Description |
|---|---|
| `prompt` | Project description (positional, or piped via stdin) |
| `-C`, `--cwd` | Working directory for the agents (defaults to current directory) |
| `-v`, `--verbose` | Enable debug-level logging with agent dispatch details |
| `-h`, `--help` | Show help |

### Alternative entry points

```bash
uv run python main.py "Build something"
uv run python -m super_system "Build something"
```

## How it works

An orchestrator agent acts as a demanding tech lead, driving 9 specialist subagents through a strict development lifecycle:

| Phase | Agent(s) | What happens |
|---|---|---|
| 1. Research | `researcher` | Gathers latest docs, libraries, best practices from the web |
| 2. Architecture | `architect` | Produces a detailed technical spec (file structure, data models, API contracts) |
| 3. Implementation | `backend-coder`, `frontend-coder`, `infra-coder` | Writes all code following the spec |
| 4. Code Review | `reviewer` | Reviews code, loops with coders until APPROVE |
| 5. Testing | `tester` | Writes and runs tests, loops until 100% pass rate |
| 6. Security Audit | `security-auditor` | Scans for vulnerabilities, loops until clean |
| 7. Documentation | `doc-writer` | Produces README and API docs |
| 8. Ship-Ready Gate | `architect` + `reviewer` | Final holistic sign-off, loops back if issues found |

Every phase has an inner retry loop. The entire lifecycle is wrapped in an outer loop that re-runs phases until both the architect and reviewer approve the final product.

## Project structure

```
super-system/
├── main.py                  # entry point shim
├── pyproject.toml
└── super_system/
    ├── __init__.py
    ├── __main__.py          # python -m super_system
    ├── cli.py               # argparse, logging, main()
    ├── orchestrator.py      # run(), message streaming
    ├── agents.py            # 9 agent definitions (tools, models)
    └── prompts.py           # all prompt constants
```
