from claude_agent_sdk import AgentDefinition

from super_system import prompts


def build_agents() -> dict[str, AgentDefinition]:
    return {
        "researcher": AgentDefinition(
            description=(
                "Technical researcher. Use to gather latest documentation, "
                "library info, best practices, and API references from the web. "
                "Read-only -- cannot modify files."
            ),
            prompt=prompts.RESEARCHER,
            tools=["WebSearch", "WebFetch", "Read", "Grep", "Glob"],
            # model="sonnet",
        ),
        "architect": AgentDefinition(
            description=(
                "Software architect. Use to design system architecture, produce "
                "technical specs, define file structures, data models, and API "
                "contracts. Also used for final sign-off during the ship-ready "
                "gate. Read-only -- cannot modify files."
            ),
            prompt=prompts.ARCHITECT,
            tools=["Read", "Grep", "Glob"],
            # model="opus",
        ),
        "backend-coder": AgentDefinition(
            description=(
                "Backend implementation specialist. Use to write Python backend "
                "code, APIs, database logic, and server-side features. Has full "
                "write access and can run commands."
            ),
            prompt=prompts.BACKEND_CODER,
            tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            # model="sonnet",
        ),
        "frontend-coder": AgentDefinition(
            description=(
                "Frontend implementation specialist. Use to write UI components, "
                "pages, styles, and client-side logic. Has full write access and "
                "can run commands."
            ),
            prompt=prompts.FRONTEND_CODER,
            tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            # model="sonnet",
        ),
        "infra-coder": AgentDefinition(
            description=(
                "Infrastructure and DevOps specialist. Use to write Dockerfiles, "
                "CI/CD pipelines, deployment configs, Makefiles, and environment "
                "setup. Has full write access and can run commands."
            ),
            prompt=prompts.INFRA_CODER,
            tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            # model="sonnet",
        ),
        "reviewer": AgentDefinition(
            description=(
                "Code reviewer. Use to conduct rigorous code review for quality, "
                "correctness, and adherence to the architectural spec. Returns "
                "APPROVE or REQUEST_CHANGES with specific issues. Also used for "
                "final sign-off during the ship-ready gate. Read-only."
            ),
            prompt=prompts.REVIEWER,
            tools=["Read", "Grep", "Glob"],
            # model="opus",
        ),
        "tester": AgentDefinition(
            description=(
                "QA and testing specialist. Use to write comprehensive test "
                "suites, run tests, stress test the application, and report "
                "failures with root cause analysis. Has write access to create "
                "test files and run commands."
            ),
            prompt=prompts.TESTER,
            tools=["Bash", "Read", "Write", "Edit", "Grep", "Glob"],
            # model="sonnet",
        ),
        "security-auditor": AgentDefinition(
            description=(
                "Security auditor. Use to scan the codebase for vulnerabilities, "
                "check OWASP Top 10, audit dependencies, and verify secrets "
                "management. Returns a severity-rated report. Read-only with "
                "Bash for running audit commands."
            ),
            prompt=prompts.SECURITY_AUDITOR,
            tools=["Read", "Grep", "Glob", "Bash"],
            # model="opus",
        ),
        "doc-writer": AgentDefinition(
            description=(
                "Documentation writer. Use to produce README, API docs, setup "
                "instructions, and usage guides. Has write access to create and "
                "update documentation files."
            ),
            prompt=prompts.DOC_WRITER,
            tools=["Read", "Write", "Edit", "Grep", "Glob"],
            # model="sonnet",
        ),
    }
