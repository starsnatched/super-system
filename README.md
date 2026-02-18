# super-system

Multi-agent software engineering team powered by Claude. Describe what you want built and a team of 12 specialist AI agents collaborates through a 10-phase development lifecycle -- including continuous autonomous improvement -- to produce exceptional, production-ready software.

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

An orchestrator agent acts as a demanding tech lead, driving 12 specialist subagents through a strict development lifecycle. The system does not stop after the first working version -- it keeps iterating autonomously, adding features, fixing issues, and polishing until the product is exceptional.

### Inter-agent communication

Agents communicate through a shared **message board** -- an in-process MCP server that provides six tools available to every agent:

| Tool | Purpose |
|---|---|
| `send_message` | Post a question, answer, info update, or action request to another agent (or broadcast to all) |
| `read_messages` | Read messages directed to you or broadcast -- agents check this at task startup |
| `read_thread` | Follow a conversation thread by ID |
| `share_artifact` | Store a named output (spec, report, findings) for other agents to pull on demand |
| `get_artifact` | Retrieve a shared artifact by name |
| `list_artifacts` | List all available artifacts |

This means agents don't rely solely on the orchestrator to relay context. The researcher shares its brief as an artifact, the architect shares its spec, the reviewer shares feedback -- and downstream agents pull exactly what they need. Agents can also ask each other direct questions, flag blockers, and coordinate dependencies through messages.

The orchestrator still coordinates the overall lifecycle and routes unanswered questions, but the message board reduces context loss and enables richer collaboration.

### Agents

| Agent | Role | Access |
|---|---|---|
| `researcher` | Gathers latest docs, libraries, best practices from the web | Read-only |
| `architect` | Designs system architecture, produces technical specs | Read-only |
| `product-manager` | Evaluates product, generates prioritized improvement backlog | Read-only + Bash |
| `backend-coder` | Writes Python backend code, APIs, server logic | Full write |
| `frontend-coder` | Writes UI components, pages, styles, client-side logic | Full write |
| `infra-coder` | Writes Dockerfiles, CI/CD, deployment configs, Makefiles | Full write |
| `reviewer` | Rigorous code review, returns APPROVE or REQUEST_CHANGES | Read-only |
| `tester` | Writes and runs comprehensive test suites | Full write |
| `security-auditor` | Scans for vulnerabilities, audits dependencies | Read-only + Bash |
| `performance-optimizer` | Profiles code, identifies bottlenecks, benchmarks | Read-only + Bash |
| `ux-analyst` | Reviews UI for accessibility, usability, responsive design | Read-only |
| `doc-writer` | Produces README, API docs, setup guides | Full write |

### Development lifecycle

| Phase | Agent(s) | What happens |
|---|---|---|
| 1. Research | `researcher` | Gathers latest docs, libraries, best practices |
| 2. Architecture | `architect` | Produces detailed technical spec |
| 3. Implementation | `backend-coder`, `frontend-coder`, `infra-coder` | Writes all code following the spec |
| 4. Code Review | `reviewer` | Reviews code, loops with coders until APPROVE |
| 5. Testing | `tester` | Writes and runs tests, loops until 100% pass |
| 6. Security Audit | `security-auditor` | Scans for vulnerabilities, loops until clean |
| 7. Documentation | `doc-writer` | Produces README and API docs |
| 8. Ship-Ready Gate | `architect` + `reviewer` | Holistic sign-off, loops back if issues found |
| 9. Continuous Improvement | `product-manager`, `performance-optimizer`, `ux-analyst` | Evaluates product, generates backlog, implements improvements in cycles |
| 10. Final Delivery | `doc-writer` + `tester` | Updates docs, runs final test suite, prints summary |

Every phase has an inner retry loop. Phase 8 wraps the initial build in an outer loop. Phase 9 is an autonomous improvement loop that keeps iterating -- the product manager evaluates, the performance optimizer profiles, the UX analyst reviews, and then coders implement improvements -- until the product manager declares the product ship-ready or 5 improvement cycles complete.

## Project structure

```
super-system/
├── main.py                  # entry point shim
├── pyproject.toml
└── super_system/
    ├── __init__.py
    ├── __main__.py          # python -m super_system
    ├── cli.py               # argparse, logging, main()
    ├── orchestrator.py      # run(), message streaming, board wiring
    ├── agents.py            # 12 agent definitions (tools, models)
    ├── prompts.py           # all prompt constants
    └── message_board.py     # shared message board + MCP tools
```
