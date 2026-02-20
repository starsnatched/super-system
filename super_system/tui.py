from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, RichLog, Static

from super_system.console import AGENT_ICONS, AGENT_STYLES
from super_system.orchestrator import (
    OrchestratorError,
    OrchestratorInterrupted,
    RunCallbacks,
    run,
)
from super_system.sessions import SessionRecord, list_sessions, save_session

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


@dataclass
class LaunchConfig:
    prompt: str
    resume: str | None = None
    fork: bool = False


class WelcomeScreen(Screen):
    AUTO_FOCUS = "#prompt-input"

    BINDINGS = [
        Binding("escape", "quit_app", "Quit"),
    ]

    CSS = """
    WelcomeScreen {
        align: center middle;
    }

    #welcome-box {
        width: 72;
        height: auto;
        padding: 1 3;
        background: $surface;
        border: round $primary-darken-1;
    }

    #logo {
        width: 100%;
        text-align: center;
        padding: 1 0 0 0;
    }

    #tagline {
        width: 100%;
        text-align: center;
        color: $text-muted;
    }

    #prompt-input {
        margin: 1 0 0 0;
    }

    #prompt-input:focus {
        border: tall $accent;
    }

    #sessions-label {
        margin: 1 0 0 0;
        color: $text-muted;
    }

    #sessions-table {
        height: auto;
        max-height: 12;
        margin: 1 0 0 0;
    }

    #hint {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        try:
            self._sessions_list = list_sessions()
        except Exception:
            self._sessions_list = []
        self._sessions_map: dict[str, SessionRecord] = {
            s.session_id: s for s in self._sessions_list
        }

    def compose(self) -> ComposeResult:
        with Vertical(id="welcome-box"):
            yield Static(
                "[bold bright_cyan]⚡[/] [bold bright_white]super-system[/]",
                id="logo",
            )
            yield Static("multi-agent engineering team", id="tagline")
            yield Input(
                placeholder="What would you like to build?",
                id="prompt-input",
            )
            if self._sessions_list:
                yield Static("Recent sessions", id="sessions-label")
                yield DataTable(id="sessions-table", cursor_type="row")
            hint_parts = ["[white]enter[/] [dim]start[/]"]
            if self._sessions_list:
                hint_parts.append("[white]↑↓[/] [dim]select session[/]")
            hint_parts.append("[white]esc[/] [dim]quit[/]")
            yield Static("   ".join(hint_parts), id="hint")
        yield Footer()

    def on_mount(self) -> None:
        if not self._sessions_list:
            return
        table = self.query_one("#sessions-table", DataTable)
        table.add_columns("Session", "Prompt", "Status", "Cost", "Started")
        for s in reversed(self._sessions_list[-10:]):
            status_styles = {
                "completed": ("✓ done", "bright_green"),
                "running": ("● run", "bright_yellow"),
                "failed": ("✗ fail", "bright_red"),
                "interrupted": ("⚠ stop", "yellow"),
            }
            st_text, st_color = status_styles.get(s.status, (s.status, "white"))
            started = (
                datetime.fromtimestamp(s.started_at, tz=timezone.utc)
                .astimezone()
                .strftime("%m/%d %H:%M")
            )
            table.add_row(
                Text(s.session_id[:12], style="cyan"),
                Text(s.prompt_preview[:36], style="white"),
                Text(st_text, style=st_color),
                Text(f"${s.cost_usd:.4f}", style="dim"),
                Text(started, style="dim"),
                key=s.session_id,
            )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if value:
            self.dismiss(LaunchConfig(prompt=value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        session_id = str(event.row_key.value)
        session = self._sessions_map.get(session_id)
        if not session:
            return
        input_widget = self.query_one("#prompt-input", Input)
        prompt = input_widget.value.strip() or "Continue from where you left off."
        self.dismiss(LaunchConfig(prompt=prompt, resume=session.session_id))

    def action_quit_app(self) -> None:
        self.app.exit()


class InfoBar(Static):
    prompt_text: reactive[str] = reactive("")
    session_id: reactive[str] = reactive("")
    resumed: reactive[bool] = reactive(False)
    forked: reactive[bool] = reactive(False)

    def render(self) -> Text:
        line = Text()
        line.append("  ▸ ", style="bold bright_cyan")
        display = self.prompt_text
        if len(display) > 100:
            display = display[:100] + "…"
        line.append(display, style="white")
        if self.session_id:
            line.append("  │  ", style="dim")
            line.append(self.session_id[:12], style="cyan")
            if self.forked:
                line.append(" forked", style="dim yellow")
            elif self.resumed:
                line.append(" resumed", style="dim green")
        return line


class StatusBar(Static):
    turns: reactive[int] = reactive(0)
    cost_usd: reactive[float] = reactive(0.0)
    duration_s: reactive[float] = reactive(0.0)
    status: reactive[str] = reactive("idle")
    spinner_frame: reactive[int] = reactive(0)

    def render(self) -> Text:
        line = Text()
        status_map = {
            "idle": ("  ○ ready", "dim"),
            "running": (
                f"  {SPINNER_FRAMES[self.spinner_frame % len(SPINNER_FRAMES)]} running",
                "bold bright_cyan",
            ),
            "completed": ("  ✓ done", "bold bright_green"),
            "interrupted": ("  ⚠ stopped", "bold yellow"),
            "failed": ("  ✗ failed", "bold red"),
        }
        text, style = status_map.get(
            self.status, (f"  ✗ {self.status}", "bold red")
        )
        line.append(text, style=style)
        line.append("  │  ", style="dim")
        line.append("turns ", style="dim")
        line.append(str(self.turns), style="bold white")
        line.append("  │  ", style="dim")
        line.append("cost ", style="dim")
        line.append(f"${self.cost_usd:.4f}", style="bold white")
        line.append("  │  ", style="dim")
        mins, secs = divmod(int(self.duration_s), 60)
        line.append(f"{mins:02d}:{secs:02d}", style="dim green")
        return line


class SuperSystemApp(App):
    TITLE = "⚡ super-system"

    CSS = """
    #info-bar {
        width: 100%;
        height: 1;
        background: $boost;
    }

    #main {
        height: 1fr;
    }

    #output-log {
        width: 2fr;
        border: round $primary-darken-1;
        border-title-color: $primary;
    }

    #output-log:focus {
        border: round $primary;
    }

    #activity-log {
        width: 1fr;
        border: round $accent-darken-1;
        border-title-color: $accent;
    }

    #activity-log:focus {
        border: round $accent;
    }

    #status-bar {
        width: 100%;
        height: 1;
        background: $boost;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        prompt: str | None = None,
        *,
        cwd: Path | None = None,
        verbose: bool = False,
        resume: str | None = None,
        fork_session: bool = False,
    ) -> None:
        super().__init__()
        self._prompt = prompt
        self._cwd = cwd
        self._verbose = verbose
        self._resume = resume
        self._fork_session = fork_session
        self._session_id: str | None = None
        self._start_mono = time.monotonic()
        self._start_wall = time.time()

    def compose(self) -> ComposeResult:
        yield Header()
        yield InfoBar(id="info-bar")
        with Horizontal(id="main"):
            output_log = RichLog(
                id="output-log",
                wrap=True,
                highlight=True,
                markup=True,
                auto_scroll=True,
            )
            output_log.border_title = "Output"
            yield output_log
            activity_log = RichLog(
                id="activity-log",
                wrap=True,
                markup=True,
                auto_scroll=True,
            )
            activity_log.border_title = "Activity"
            yield activity_log
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        if self._prompt:
            self._begin_run()
        else:
            self.push_screen(WelcomeScreen(), self._on_welcome)

    def _on_welcome(self, config: LaunchConfig) -> None:
        self._prompt = config.prompt
        if config.resume:
            self._resume = config.resume
        self._fork_session = config.fork
        self._begin_run()

    def _begin_run(self) -> None:
        info_bar = self.query_one("#info-bar", InfoBar)
        info_bar.prompt_text = self._prompt or ""
        if self._resume:
            info_bar.resumed = True
            if self._fork_session:
                info_bar.forked = True

        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.status = "running"

        output = self.query_one("#output-log", RichLog)
        output.write(Text("  Starting session…", style="dim italic"))

        self._start_mono = time.monotonic()
        self._start_wall = time.time()
        self.set_interval(0.1, self._tick)
        self._run_orchestrator()

    def _tick(self) -> None:
        bar = self.query_one("#status-bar", StatusBar)
        if bar.status == "running":
            bar.duration_s = time.monotonic() - self._start_mono
            bar.spinner_frame += 1

    def _ts(self) -> str:
        elapsed = time.monotonic() - self._start_mono
        mins, secs = divmod(int(elapsed), 60)
        return f"{mins:02d}:{secs:02d}"

    def _save(
        self,
        status: str,
        cost: float = 0.0,
        turns: int = 0,
        duration: int = 0,
    ) -> None:
        if not self._session_id:
            return
        save_session(
            SessionRecord(
                session_id=self._session_id,
                prompt_preview=(self._prompt or "")[:100],
                started_at=self._start_wall,
                status=status,
                cost_usd=cost,
                num_turns=turns,
                duration_ms=duration,
            )
        )

    @work(thread=False)
    async def _run_orchestrator(self) -> None:
        prompt = self._prompt
        if not prompt:
            return

        output = self.query_one("#output-log", RichLog)
        activity = self.query_one("#activity-log", RichLog)
        info_bar = self.query_one("#info-bar", InfoBar)
        status_bar = self.query_one("#status-bar", StatusBar)

        def on_text(text: str) -> None:
            output.write(Markdown(text))

        def on_agent_dispatch(agent_name: str, description: str = "") -> None:
            color = AGENT_STYLES.get(agent_name, "white")
            icon = AGENT_ICONS.get(agent_name, "▸")
            line = Text()
            line.append(f"{self._ts()} ", style="dim green")
            line.append(f"{icon} ", style=f"bold {color}")
            line.append(agent_name, style=f"bold {color}")
            if description:
                line.append("  ")
                line.append(description, style="dim")
            activity.write(line)

        def on_result(
            num_turns: int,
            cost_usd: float,
            duration_ms: int,
            is_error: bool = False,
            error_text: str = "",
        ) -> None:
            status_bar.turns = num_turns
            status_bar.cost_usd = cost_usd
            status_bar.duration_s = duration_ms / 1000
            status_bar.status = "failed" if is_error else "completed"

            result_table = Table(show_header=False, box=None, padding=(0, 2))
            result_table.add_column(style="dim")
            result_table.add_column(style="bold white")
            result_table.add_row("Turns", str(num_turns))
            result_table.add_row("Cost", f"${cost_usd:.4f}")
            result_table.add_row("Duration", f"{duration_ms / 1000:.1f}s")

            if is_error:
                title = "[red]✗ Session failed[/red]"
                border = "red"
            else:
                title = "[green]✓ Session complete[/green]"
                border = "green"
            output.write(
                Panel(
                    result_table,
                    title=title,
                    border_style=border,
                    expand=False,
                )
            )

            if is_error and error_text:
                output.write(Text(f"  {error_text}", style="bold red"))

            self._save(
                "failed" if is_error else "completed",
                cost=cost_usd,
                turns=num_turns,
                duration=duration_ms,
            )

        def on_system(subtype: str, data: object) -> None:
            line = Text()
            line.append(f"{self._ts()} ", style="dim green")
            line.append(f"[{subtype}] ", style="dim cyan")
            line.append(str(data)[:200], style="dim")
            activity.write(line)

        def on_session_id(session_id: str) -> None:
            self._session_id = session_id
            info_bar.session_id = session_id

            line = Text()
            line.append(f"{self._ts()} ", style="dim green")
            line.append("● ", style="bold bright_green")
            if self._resume and not self._fork_session:
                line.append(f"Resumed {session_id[:16]}", style="bright_green")
            elif self._fork_session:
                line.append(f"Forked {session_id[:16]}", style="bright_yellow")
            else:
                line.append(f"Started {session_id[:16]}", style="bright_green")
            activity.write(line)
            self._save("running")

        def on_interrupted() -> None:
            status_bar.status = "interrupted"
            activity.write(
                Text(f"{self._ts()}  ⚠ Interrupted", style="bold yellow")
            )
            self._save("interrupted")

        def on_error(msg: str) -> None:
            output.write(Text(f"\n✗ {msg}", style="bold red"))
            status_bar.status = "failed"
            self._save("failed")

        callbacks = RunCallbacks(
            on_banner=lambda: None,
            on_text=on_text,
            on_agent_dispatch=on_agent_dispatch,
            on_result=on_result,
            on_system=on_system,
            on_session_id=on_session_id,
            on_interrupted=on_interrupted,
            on_error=on_error,
        )

        try:
            await run(
                prompt,
                cwd=self._cwd,
                verbose=self._verbose,
                resume=self._resume,
                fork_session=self._fork_session,
                callbacks=callbacks,
                handle_signals=False,
            )
        except OrchestratorInterrupted:
            status_bar.status = "interrupted"
        except OrchestratorError:
            status_bar.status = "failed"
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            status_bar.status = "failed"
            output.write(
                Text(f"\n✗ Unexpected error: {exc}", style="bold red")
            )
