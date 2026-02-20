# super-system

Multi-agent software engineering team powered by Claude. Describe what you want built and a team of 12 specialist AI agents collaborates through a dynamic, non-linear development workflow -- navigating freely between research, architecture, implementation, review, testing, security, and improvement activities -- to produce exceptional, production-ready software.

## Quick install

One command — installs `uv` if needed, clones the repo, and puts `super-system` on your PATH:

```bash
curl -fsSL https://raw.githubusercontent.com/starsnatched/super-system/main/install.sh | bash
```

Your API key will be prompted on first launch and saved to `~/.config/super-system/config.json`.

### Prerequisites

- macOS or Linux
- git
- Python 3.13+ (managed automatically by uv)
- A valid Anthropic API key

### Manual install

```bash
git clone https://github.com/starsnatched/super-system.git
uv tool install --editable ./super-system
```

## Usage

Launch the interactive TUI from any directory:

```bash
super-system
```

Pass a project description directly:

```bash
super-system "Build a REST API for a todo app with SQLite persistence"
```

Build into a specific directory:

```bash
super-system -C /path/to/project "Build a CLI tool that converts CSV to JSON"
```

Pipe a prompt from a file:

```bash
cat spec.txt | super-system
```

Enable verbose logging to see agent dispatch details:

```bash
super-system -v "Build a markdown blog generator"
```

### Options

| Flag | Description |
|---|---|
| `prompt` | Project description (positional, or piped via stdin) |
| `-C`, `--cwd` | Working directory for the agents (defaults to current directory) |
| `-v`, `--verbose` | Enable debug-level logging with agent dispatch details |
| `-h`, `--help` | Show help |

### Alternative entry points

If running from the repo directory without a global install:

```bash
uv run super-system "Build something"
uv run python main.py "Build something"
```

## How it works

An orchestrator agent acts as a demanding tech lead, driving 12 specialist subagents through a dynamic development workflow. Rather than following a rigid pipeline, the orchestrator navigates freely between activities -- jumping back to architecture when implementation reveals a design flaw, re-running tests after security fixes, or looping through research when encountering unfamiliar APIs. The system does not stop after the first working version -- it keeps iterating autonomously, adding features, fixing issues, and polishing until the product is exceptional.

### Inter-agent communication

Agents communicate through a shared **BOARD.md** file in the working directory. Every agent reads this file at the start of its task and writes its outputs (specs, reports, findings, messages) to labeled `##` sections. This is the primary mechanism for cross-agent context sharing -- no MCP server or custom tooling required, just standard file read/write operations.

The researcher writes its brief to `## research-brief`, the architect writes its spec to `## architecture-spec`, the reviewer writes feedback to `## review-feedback` -- and downstream agents read exactly the sections they need. Agents can also post questions, flag blockers, and coordinate dependencies through a `## Messages` section.

The orchestrator still coordinates the overall lifecycle and routes unanswered questions, but BOARD.md reduces context loss and enables richer collaboration.

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

### Development activities

The orchestrator has a set of development activities it can invoke in any order, revisit at any time, and interleave as needed. It decides what to do next based on the current state of the project.

| Activity | Agent(s) | What happens |
|---|---|---|
| Research | `researcher` | Gathers latest docs, libraries, best practices |
| Architecture | `architect` | Produces detailed technical spec and feature plan |
| Implementation | `backend-coder`, `frontend-coder`, `infra-coder` | Writes code one feature at a time following the spec |
| Code Review | `reviewer` | Reviews code per-feature and holistically, loops until APPROVE |
| Testing | `tester` | Writes and runs tests, loops until 100% pass |
| Security Audit | `security-auditor` | Scans for vulnerabilities, loops until clean |
| Documentation | `doc-writer` | Produces README and API docs |
| Ship-Ready Gate | `architect` + `reviewer` | Holistic sign-off, jumps back to any activity if issues found |
| Improvement | `product-manager`, `performance-optimizer`, `ux-analyst` | Evaluates product, generates backlog, implements improvements in cycles |
| Delivery | `doc-writer` + `tester` | Updates docs, runs final test suite, prints summary |

The typical first-pass order is Research -> Architecture -> Implementation -> Review -> Testing -> Security -> Documentation -> Ship-Ready Gate -> Improvement -> Delivery, but the orchestrator navigates non-linearly: a test failure sends it back to implementation, a code review finding might trigger re-architecture, a security issue during improvement loops back through implementation and testing. Each activity has retry limits to prevent infinite loops, and the orchestrator tracks its navigation to detect and break out of unproductive cycles.

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
    └── prompts.py           # all prompt constants
```
