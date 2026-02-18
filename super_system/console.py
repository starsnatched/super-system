from __future__ import annotations

import time
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

if TYPE_CHECKING:
    from super_system.message_board import Message

AGENT_STYLES: dict[str, str] = {
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

_SYSTEM_SUBTYPE_STYLES: dict[str, tuple[str, str]] = {
    "tool_use": ("🔧", "cyan"),
    "tool_result": ("📦", "green"),
    "model_request": ("🧠", "magenta"),
    "model_response": ("💬", "blue"),
    "error": ("✗", "bright_red"),
    "rate_limit": ("⏳", "yellow"),
    "retry": ("↻", "yellow"),
}

_MSG_KIND_ICONS: dict[str, tuple[str, str]] = {
    "question": ("?", "bold bright_yellow"),
    "answer": ("✓", "bold bright_green"),
    "info": ("i", "bold bright_cyan"),
    "request": ("!", "bold bright_magenta"),
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
    label = Text.assemble(
        (f"  {_ts()} ", "ts"),
        ("▸ ", f"bold {color}"),
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
        title = "[error]✗ Session failed[/error]"
        border_style = "red"
    else:
        title = "[success]✓ Session complete[/success]"
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


def print_message_activity(msg: Message) -> None:
    sender_color = AGENT_STYLES.get(msg.from_agent, "white")
    receiver_color = AGENT_STYLES.get(msg.to_agent, "white")
    icon, kind_style = _MSG_KIND_ICONS.get(msg.kind, ("•", "dim"))

    label = Text.assemble(
        (f"  {_ts()} ", "ts"),
        (f"  {icon} ", kind_style),
        (msg.from_agent, f"bold {sender_color}"),
        (" → ", "dim"),
        (msg.to_agent, f"bold {receiver_color}"),
        (f"  [{msg.kind}] ", kind_style),
        (msg.subject, "dim"),
    )
    err_console.print(label)


def print_artifact_shared(owner: str, key: str) -> None:
    owner_color = AGENT_STYLES.get(owner, "white")
    label = Text.assemble(
        (f"  {_ts()} ", "ts"),
        ("  ◆ ", "bold bright_cyan"),
        (owner, f"bold {owner_color}"),
        (" shared artifact ", "dim"),
        (key, "bold white"),
    )
    err_console.print(label)
