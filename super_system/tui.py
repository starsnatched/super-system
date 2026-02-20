from __future__ import annotations

import asyncio
import time
from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Header, RichLog, Static

from super_system.console import AGENT_STYLES
from super_system.orchestrator import (
    OrchestratorError,
    OrchestratorInterrupted,
    RunCallbacks,
    run,
)
from super_system.sessions import SessionRecord, save_session


class SessionBar(Static):
    session_id: reactive[str] = reactive("")
    resumed: reactive[bool] = reactive(False)
    forked: reactive[bool] = reactive(False)

    def render(self) -> Text:
        line = Text()
        line.append("  Session: ", style="dim")
        if self.session_id:
            line.append(self.session_id, style="bold cyan")
            if self.forked:
                line.append("  (forked)", style="dim yellow")
            elif self.resumed:
                line.append("  (resumed)", style="dim green")
        else:
            line.append("starting...", style="dim italic")
        return line


class StatusBar(Static):
    turns: reactive[int] = reactive(0)
    cost_usd: reactive[float] = reactive(0.0)
    duration_s: reactive[float] = reactive(0.0)
    status: reactive[str] = reactive("running")

    def render(self) -> Text:
        line = Text()
        line.append("  Turns: ", style="dim")
        line.append(str(self.turns), style="bold")
        line.append("  │  ", style="dim")
        line.append("Cost: ", style="dim")
        line.append(f"${self.cost_usd:.4f}", style="bold")
        line.append("  │  ", style="dim")
        mins, secs = divmod(int(self.duration_s), 60)
        line.append(f"⏱ {mins:02d}:{secs:02d}", style="dim green")
        line.append("  │  ", style="dim")

        status_map = {
            "running": ("● running", "bold green"),
            "completed": ("✓ completed", "bold bright_green"),
            "interrupted": ("⚠ interrupted", "bold yellow"),
            "failed": ("✗ failed", "bold red"),
        }
        text, style = status_map.get(self.status, (f"✗ {self.status}", "bold red"))
        line.append(text, style=style)
        return line


class SuperSystemApp(App):
    TITLE = "⚡ super-system"
    SUB_TITLE = "multi-agent engineering team"

    CSS = """
    #session-bar {
        width: 100%;
        height: 1;
        background: $primary-background-darken-2;
    }

    #main {
        height: 1fr;
    }

    #output-log {
        width: 2fr;
        border: round $primary;
        border-title-color: $primary;
    }

    #activity-log {
        width: 1fr;
        border: round $accent;
        border-title-color: $accent;
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
        prompt: str,
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
        yield SessionBar(id="session-bar")
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
        self._start_mono = time.monotonic()
        self._start_wall = time.time()
        self.set_interval(1, self._tick)
        self._run_orchestrator()

    def _tick(self) -> None:
        status_bar = self.query_one("#status-bar", StatusBar)
        if status_bar.status == "running":
            status_bar.duration_s = time.monotonic() - self._start_mono

    def _ts(self) -> str:
        elapsed = time.monotonic() - self._start_mono
        mins, secs = divmod(int(elapsed), 60)
        return f"{mins:02d}:{secs:02d}"

    def _save(self, status: str, cost: float = 0.0, turns: int = 0, duration: int = 0) -> None:
        if not self._session_id:
            return
        save_session(
            SessionRecord(
                session_id=self._session_id,
                prompt_preview=self._prompt[:100],
                started_at=self._start_wall,
                status=status,
                cost_usd=cost,
                num_turns=turns,
                duration_ms=duration,
            )
        )

    @work(thread=False)
    async def _run_orchestrator(self) -> None:
        output = self.query_one("#output-log", RichLog)
        activity = self.query_one("#activity-log", RichLog)
        session_bar = self.query_one("#session-bar", SessionBar)
        status_bar = self.query_one("#status-bar", StatusBar)

        if self._resume:
            session_bar.resumed = True
            if self._fork_session:
                session_bar.forked = True

        def on_text(text: str) -> None:
            output.write(Markdown(text))

        def on_agent_dispatch(agent_name: str, description: str = "") -> None:
            color = AGENT_STYLES.get(agent_name, "white")
            line = Text()
            line.append(f"{self._ts()} ", style="dim green")
            line.append("▸ ", style=f"bold {color}")
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
            output.write(Panel(result_table, title=title, border_style=border, expand=False))

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
            session_bar.session_id = session_id

            line = Text()
            line.append(f"{self._ts()} ", style="dim green")
            line.append("● ", style="bold bright_green")
            if self._resume and not self._fork_session:
                line.append(f"Session resumed: {session_id}", style="bright_green")
            elif self._fork_session:
                line.append(f"Session forked: {session_id}", style="bright_yellow")
            else:
                line.append(f"Session started: {session_id}", style="bright_green")
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
                self._prompt,
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
            output.write(Text(f"\n✗ Unexpected error: {exc}", style="bold red"))
