# super-system

Multi-agent software engineering team powered by Claude. Describe what you want built and a team of 12 specialist AI agents collaborates through a 10-phase development lifecycle -- including continuous autonomous improvement -- to produce exceptional, production-ready software.

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

An orchestrator agent acts as a demanding tech lead, driving 12 specialist subagents through a strict development lifecycle. The system does not stop after the first working version -- it keeps iterating autonomously, adding features, fixing issues, and polishing until the product is exceptional.

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
    └── prompts.py           # all prompt constants
```
