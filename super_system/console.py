from __future__ import annotations

import asyncio
import time

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


AGENT_STYLES: dict[str, str] = {
    "intake": "bright_blue",
    "researcher": "bright_cyan",
    "architect": "bright_magenta",
    "backend-coder": "bright_green",
    "frontend-coder": "bright_yellow",
    "infra-coder": "orange3",
    "reviewer": "deep_sky_blue1",
    "tester": "medium_spring_green",
    "security-auditor": "bright_red",
    "doc-writer": "orchid1",
    "product-manager": "gold1",
    "performance-optimizer": "turquoise2",
    "ux-analyst": "plum2",
}

AGENT_ICONS: dict[str, str] = {
    "intake": "◈",
    "researcher": "◇",
    "architect": "△",
    "backend-coder": "◆",
    "frontend-coder": "●",
    "infra-coder": "■",
    "reviewer": "◎",
    "tester": "▲",
    "security-auditor": "◉",
    "doc-writer": "□",
    "product-manager": "▶",
    "performance-optimizer": "⚡",
    "ux-analyst": "○",
}

_SYSTEM_SUBTYPE_STYLES: dict[str, tuple[str, str]] = {
    "tool_use": ("🔧", "cyan"),
    "tool_result": ("📦", "green"),
    "model_request": ("🧠", "magenta"),
    "model_response": ("💬", "blue"),
    "error": ("✗", "bright_red"),
    "rate_limit": ("⏳", "yellow"),
    "retry": ("↻", "yellow"),
}

THEME = Theme(
    {
        "agent.name": "bold",
        "agent.desc": "dim",
        "info": "dim cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "metric.label": "dim",
        "metric.value": "bold white",
        "ts": "dim green",
    }
)

console = Console(theme=THEME, highlight=False)
err_console = Console(theme=THEME, stderr=True, highlight=False)

_t0 = time.monotonic()


def _ts() -> str:
    elapsed = time.monotonic() - _t0
    mins, secs = divmod(int(elapsed), 60)
    return f"{mins:02d}:{secs:02d}"


def print_banner() -> None:
    err_console.print()
    err_console.print(
        Panel(
            Text.assemble(
                ("⚡ ", "bright_yellow"),
                ("super-system", "bold bright_white"),
                ("  multi-agent engineering team", "dim"),
            ),
            border_style="bright_blue",
            expand=False,
            padding=(0, 2),
        )
    )
    err_console.print()


def print_agent_dispatch(agent_name: str, description: str = "") -> None:
    color = AGENT_STYLES.get(agent_name, "white")
    icon = AGENT_ICONS.get(agent_name, "▸")
    label = Text.assemble(
        (f"  {_ts()} ", "ts"),
        (f"{icon} ", f"bold {color}"),
        (agent_name, f"bold {color}"),
    )
    if description:
        label.append("  ")
        label.append(description, style="dim")
    err_console.print(label)


def print_text(text: str) -> None:
    md = Markdown(text)
    console.print(md)


def print_result(
    num_turns: int,
    cost_usd: float,
    duration_ms: int,
    is_error: bool = False,
    error_text: str = "",
) -> None:
    console.print()

    duration_s = duration_ms / 1000

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="metric.label")
    table.add_column(style="metric.value")
    table.add_row("Turns", str(num_turns))
    table.add_row("Cost", f"${cost_usd:.4f}")
    table.add_row("Duration", f"{duration_s:.1f}s")

    if is_error:
        title = "[error]✗ Run failed[/error]"
        border_style = "red"
    else:
        title = "[success]✓ Run complete[/success]"
        border_style = "green"

    console.print(Panel(table, title=title, border_style=border_style, expand=False))

    if is_error and error_text:
        console.print(f"[error]  {error_text}[/error]")


def print_system(subtype: str, data: object) -> None:
    icon, color = _SYSTEM_SUBTYPE_STYLES.get(subtype, ("•", "dim"))
    label = Text.assemble(
        (f"  {_ts()} ", "ts"),
        (f"{icon} ", color),
        (subtype, f"bold {color}"),
        ("  ", ""),
        (str(data), "dim"),
    )
    err_console.print(label)


def print_interrupted() -> None:
    err_console.print()
    err_console.print("[warning]⚠ Interrupted[/warning]")


def print_error(message: str) -> None:
    err_console.print()
    err_console.print(f"[error]✗ {message}[/error]")


def print_intake_banner() -> None:
    err_console.print()
    err_console.print(
        Panel(
            Text.assemble(
                ("◈ ", "bold bright_blue"),
                ("intake", "bold bright_white"),
                ("  gathering requirements", "dim"),
            ),
            border_style="bright_blue",
            expand=False,
            padding=(0, 2),
        )
    )
    err_console.print()


def print_intake_tool_use(tool_name: str, description: str = "") -> None:
    label = Text.assemble(
        (f"  {_ts()} ", "ts"),
        ("◈ ", "bold bright_blue"),
        (tool_name, "bold bright_blue"),
    )
    if description:
        label.append("  ")
        label.append(description, style="dim")
    err_console.print(label)


def print_intake_crafted(prompt: str) -> None:
    err_console.print()
    err_console.print(
        Panel(
            Text("Prompt crafted. Handing off to engineering team.", style="bold"),
            border_style="bright_green",
            title="[success]✓ Intake complete[/success]",
            expand=False,
            padding=(0, 2),
        )
    )
    err_console.print()


async def prompt_user_input() -> str | None:
    loop = asyncio.get_event_loop()
    err_console.print()
    err_console.print(
        Text.assemble(
            ("  ◈ ", "bold bright_blue"),
            ("Your turn", "bold bright_blue"),
            (" (empty line to let the agent decide):", "dim"),
        )
    )
    err_console.print()

    lines: list[str] = []
    try:
        while True:
            line = await loop.run_in_executor(
                None, lambda: input("  > ")
            )
            if line == "":
                if lines:
                    break
                return None
            lines.append(line)
    except EOFError:
        if lines:
            return "\n".join(lines)
        return None
    except KeyboardInterrupt:
        return None

    return "\n".join(lines)


