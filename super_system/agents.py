from dataclasses import dataclass

from claude_agent_sdk import AgentDefinition

from super_system import prompts

BROWSER_TOOLS = ["mcp__claude-in-chrome"]


@dataclass
class _AgentDef(AgentDefinition):
    memory: str | None = None


_AGENT_DEFS: list[tuple[str, str, str, list[str]]] = [
    (
        "researcher",
        (
            "Technical researcher. Use to gather latest documentation, "
            "library info, best practices, and API references from the web."
        ),
        prompts.RESEARCHER,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob"],
    ),
    (
        "architect",
        (
            "Software architect. Use to design system architecture, produce "
            "technical specs, define file structures, data models, and API "
            "contracts. Also used for final sign-off during the ship-ready "
            "gate."
        ),
        prompts.ARCHITECT,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob"],
    ),
    (
        "backend-coder",
        (
            "Backend implementation specialist. Use to write Python backend "
            "code, APIs, database logic, and server-side features. Has full "
            "write access and can run commands."
        ),
        prompts.BACKEND_CODER,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    ),
    (
        "frontend-coder",
        (
            "Frontend implementation specialist using Next.js (App Router) and "
            "TypeScript. Use to write UI components, pages, styles, and "
            "client-side logic. Has full write access, can run commands, "
            "and has browser access to visually verify rendered UI."
        ),
        prompts.FRONTEND_CODER,
        [
            "WebSearch", "WebFetch", "Read", "Write", "Edit", "Bash",
            "Grep", "Glob",
        ] + BROWSER_TOOLS,
    ),
    (
        "infra-coder",
        (
            "Infrastructure and DevOps specialist. Use to write Dockerfiles, "
            "CI/CD pipelines, deployment configs, Makefiles, and environment "
            "setup. Has full write access and can run commands."
        ),
        prompts.INFRA_CODER,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    ),
    (
        "reviewer",
        (
            "Code reviewer. Use to conduct rigorous code review for quality, "
            "correctness, and adherence to the architectural spec. Returns "
            "APPROVE or REQUEST_CHANGES with specific issues. Also used for "
            "final sign-off during the ship-ready gate."
        ),
        prompts.REVIEWER,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob"],
    ),
    (
        "tester",
        (
            "QA and testing specialist. Use to write comprehensive test "
            "suites, run tests, stress test the application, and report "
            "failures with root cause analysis. Has write access to create "
            "test files and run commands, and browser access for visual "
            "and end-to-end UI testing."
        ),
        prompts.TESTER,
        [
            "WebSearch", "WebFetch", "Bash", "Read", "Write", "Edit",
            "Grep", "Glob",
        ] + BROWSER_TOOLS,
    ),
    (
        "security-auditor",
        (
            "Security auditor. Use to scan the codebase for vulnerabilities, "
            "check OWASP Top 10, audit dependencies, and verify secrets "
            "management. Returns a severity-rated report. Has Bash for "
            "running audit commands."
        ),
        prompts.SECURITY_AUDITOR,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob", "Bash"],
    ),
    (
        "doc-writer",
        (
            "Documentation writer. Use to produce README, API docs, setup "
            "instructions, and usage guides. Has write access to create and "
            "update documentation files."
        ),
        prompts.DOC_WRITER,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob"],
    ),
    (
        "product-manager",
        (
            "Product manager. Use to evaluate the built product against the "
            "original request and produce a prioritized improvement backlog. "
            "Returns SHIP_READY or IMPROVEMENTS_NEEDED with a ranked list "
            "of features, bugfixes, UX issues, and polish items. Use after "
            "the ship-ready gate to drive continuous improvement. Has Bash "
            "to run the application and browser access to interact with "
            "it as a real user."
        ),
        prompts.PRODUCT_MANAGER,
        [
            "WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob",
            "Bash",
        ] + BROWSER_TOOLS,
    ),
    (
        "performance-optimizer",
        (
            "Performance engineer. Use to profile code, run benchmarks, "
            "identify bottlenecks, and recommend optimizations. Reports "
            "issues ranked by impact with specific fix recommendations. "
            "Has Bash for running profiling and benchmarking tools."
        ),
        prompts.PERFORMANCE_OPTIMIZER,
        ["WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob", "Bash"],
    ),
    (
        "ux-analyst",
        (
            "UX and accessibility analyst. Use to review UI components for "
            "WCAG compliance, usability, responsive design, keyboard "
            "navigation, and visual polish. Returns CLEAN or ISSUES_FOUND "
            "with a severity-rated report. Has browser access to visually "
            "inspect the rendered application."
        ),
        prompts.UX_ANALYST,
        [
            "WebSearch", "WebFetch", "Read", "Write", "Edit", "Grep", "Glob",
        ] + BROWSER_TOOLS,
    ),
]


def build_agents() -> dict[str, AgentDefinition]:
    agents: dict[str, AgentDefinition] = {}
    for name, description, base_prompt, base_tools in _AGENT_DEFS:
        full_prompt = base_prompt + prompts.AGENT_COMMS_PROTOCOL.format(
            agent_name=name
        )
        agents[name] = _AgentDef(
            description=description,
            prompt=full_prompt,
            tools=base_tools,
            memory="project",
        )
    return agents
