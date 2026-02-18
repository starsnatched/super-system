import logging
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from super_system import prompts
from super_system.agents import build_agents

logger = logging.getLogger(__name__)


async def run(
    prompt: str,
    *,
    cwd: Path | None = None,
    verbose: bool = False,
) -> None:
    agents = build_agents()

    orchestrator_prompt = f"{prompts.ORCHESTRATOR}\n\nUSER REQUEST:\n{prompt}"

    options = ClaudeAgentOptions(
        allowed_tools=["Task", "Read", "Grep", "Glob"],
        agents=agents,
        permission_mode="bypassPermissions",
        model="claude-opus-4-20250514",
    )

    if cwd is not None:
        options.cwd = cwd

    if verbose:
        options.debug_stderr = sys.stderr

    async for message in query(prompt=orchestrator_prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, flush=True)
                elif isinstance(block, ToolUseBlock):
                    logger.info("Agent dispatch: %s", block.name)
                    if verbose and isinstance(block.input, dict):
                        desc = block.input.get("description", "")
                        if desc:
                            logger.info("  -> %s", desc)
        elif isinstance(message, ResultMessage):
            logger.info(
                "Session complete | turns=%d cost=$%.4f duration=%dms",
                message.num_turns,
                message.total_cost_usd or 0,
                message.duration_ms,
            )
            if message.is_error:
                logger.error("Session ended with error: %s", message.result)
        elif isinstance(message, SystemMessage):
            logger.debug("System [%s]: %s", message.subtype, message.data)
