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
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
    Switch,
)

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
    cwd: Path | None = None
    verbose: bool = False
    resume: str | None = None
    fork: bool = False


class SessionActionScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    SessionActionScreen {
        align: center middle;
    }

    #action-box {
        width: 52;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: tall $primary;
    }

    #action-title {
        width: 100%;
        text-align: center;
        margin: 0 0 1 0;
    }

    #action-detail {
        width: 100%;
        text-align: center;
        color: $text-muted;
    }

    #action-meta {
        width: 100%;
        text-align: center;
        color: $text-disabled;
        margin: 0 0 1 0;
    }

    #action-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #action-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, session: SessionRecord) -> None:
        super().__init__()
        self._session = session

    def compose(self) -> ComposeResult:
        s = self._session
        status_map = {
            "completed": "[bright_green]done[/]",
            "running": "[bright_yellow]running[/]",
            "failed": "[bright_red]failed[/]",
            "interrupted": "[yellow]interrupted[/]",
        }
        status_txt = status_map.get(s.status, s.status)
        with Vertical(id="action-box"):
            yield Static(
                f"[bold cyan]{s.session_id[:16]}[/]",
                id="action-title",
            )
            yield Static(s.prompt_preview[:48], id="action-detail")
            yield Static(
                f"{status_txt}  [dim]${s.cost_usd:.4f}  {s.num_turns} turns[/]",
                id="action-meta",
            )
            with Horizontal(id="action-buttons"):
                yield Button("Resume", id="btn-resume", variant="primary")
                yield Button("Fork", id="btn-fork", variant="warning")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id or "btn-cancel")

    def action_cancel(self) -> None:
        self.dismiss("btn-cancel")


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-box {
        width: 56;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: tall $accent;
    }

    #help-title {
        width: 100%;
        text-align: center;
        margin: 0 0 1 0;
    }

    #help-content {
        width: 100%;
        height: auto;
    }

    #help-hint {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Static("[bold]Keyboard Shortcuts[/bold]", id="help-title")
            yield Static(id="help-content")
            yield Static(
                "[dim]Press [white]esc[/white] to close[/dim]",
                id="help-hint",
            )

    def on_mount(self) -> None:
        tbl = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        tbl.add_column(style="bold white", width=16)
        tbl.add_column(style="dim")
        tbl.add_row("tab / shift+tab", "Switch panel focus")
        tbl.add_row("q", "Quit application")
        tbl.add_row("n", "Start new session")
        tbl.add_row("?", "Show this help")
        tbl.add_row("↑ / ↓", "Scroll focused panel")
        tbl.add_row("page up / down", "Scroll faster")
        tbl.add_row("home / end", "Jump to top / bottom")
        self.query_one("#help-content", Static).update(tbl)


class WelcomeScreen(Screen[LaunchConfig]):
    AUTO_FOCUS = "#prompt-input"

    BINDINGS = [
        Binding("escape", "quit_app", "Quit"),
    ]

    CSS = """
    WelcomeScreen {
        align: center middle;
    }

    #welcome-box {
        width: 80;
        height: auto;
        padding: 1 3;
        background: $surface;
        border: tall $primary-darken-1;
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
        margin: 0 0 1 0;
    }

    #config-section {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    .field-row {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    .field-label {
        width: 16;
        padding: 1 1 0 0;
        text-align: right;
        color: $text-muted;
    }

    #cwd-input {
        width: 1fr;
    }

    #cwd-input:focus {
        border: tall $accent;
    }

    .switch-row {
        width: 100%;
        height: auto;
    }

    .switch-label {
        width: 16;
        padding: 0 1 0 0;
        text-align: right;
        color: $text-muted;
    }

    #prompt-input {
        margin: 0 0 1 0;
    }

    #prompt-input:focus {
        border: tall $accent;
    }

    #sessions-label {
        color: $text-muted;
        margin: 1 0 0 0;
    }

    #sessions-table {
        height: auto;
        max-height: 14;
        margin: 0 0 1 0;
    }

    #hint {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    def __init__(
        self,
        *,
        default_cwd: Path | None = None,
        default_verbose: bool = False,
    ) -> None:
        super().__init__()
        self._default_cwd = default_cwd or Path.cwd()
        self._default_verbose = default_verbose
        self._selected_session: SessionRecord | None = None
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

            with Vertical(id="config-section"):
                with Horizontal(classes="field-row"):
                    yield Static("Working Dir", classes="field-label")
                    yield Input(
                        value=str(self._default_cwd),
                        placeholder="/path/to/project",
                        id="cwd-input",
                    )
                with Horizontal(classes="switch-row"):
                    yield Static("Verbose", classes="switch-label")
                    yield Switch(id="verbose-switch", value=self._default_verbose)

            yield Input(
                placeholder="What would you like to build?",
                id="prompt-input",
            )

            if self._sessions_list:
                yield Static("Recent sessions", id="sessions-label")
                yield DataTable(id="sessions-table", cursor_type="row")

            hints = ["[white]enter[/] [dim]start[/]"]
            if self._sessions_list:
                hints.append("[white]↑↓[/] [dim]select session[/]")
            hints.append("[white]esc[/] [dim]quit[/]")
            yield Static("   ".join(hints), id="hint")

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

    def _build_config(
        self,
        prompt: str,
        resume: str | None = None,
        fork: bool = False,
    ) -> LaunchConfig:
        cwd_raw = self.query_one("#cwd-input", Input).value.strip()
        cwd = Path(cwd_raw).resolve() if cwd_raw else None
        verbose = self.query_one("#verbose-switch", Switch).value
        return LaunchConfig(
            prompt=prompt,
            cwd=cwd,
            verbose=verbose,
            resume=resume,
            fork=fork,
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "cwd-input":
            self.query_one("#prompt-input", Input).focus()
            return
        prompt = event.value.strip()
        if not prompt:
            return
        config = self._build_config(prompt)
        if config.cwd and not config.cwd.is_dir():
            self.notify(
                f"Directory not found: {config.cwd}",
                severity="error",
                title="Invalid Path",
            )
            self.query_one("#cwd-input", Input).focus()
            return
        self.dismiss(config)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        session_id = str(event.row_key.value)
        session = self._sessions_map.get(session_id)
        if not session:
            return
        self._selected_session = session
        self.app.push_screen(
            SessionActionScreen(session),
            self._on_session_action,
        )

    def _on_session_action(self, action: str) -> None:
        session = self._selected_session
        if not session or action == "btn-cancel":
            return
        prompt_input = self.query_one("#prompt-input", Input)
        prompt = prompt_input.value.strip() or "Continue from where you left off."
        fork = action == "btn-fork"
        config = self._build_config(prompt, resume=session.session_id, fork=fork)
        if config.cwd and not config.cwd.is_dir():
            self.notify(
                f"Directory not found: {config.cwd}",
                severity="error",
                title="Invalid Path",
            )
            self.query_one("#cwd-input", Input).focus()
            return
        self.dismiss(config)

    def action_quit_app(self) -> None:
        self.app.exit()


class InfoBar(Static):
    prompt_text: reactive[str] = reactive("")
    session_id: reactive[str] = reactive("")
    working_dir: reactive[str] = reactive("")
    resumed: reactive[bool] = reactive(False)
    forked: reactive[bool] = reactive(False)

    def render(self) -> Text:
        line = Text()
        line.append("  ⚡ ", style="bold bright_cyan")
        display = self.prompt_text
        if len(display) > 60:
            display = display[:60] + "…"
        line.append(display, style="white")
        if self.session_id:
            line.append("  │  ", style="dim")
            line.append(self.session_id[:12], style="cyan")
            if self.forked:
                line.append(" forked", style="dim yellow")
            elif self.resumed:
                line.append(" resumed", style="dim green")
        if self.working_dir:
            line.append("  │  ", style="dim")
            wd = self.working_dir
            if len(wd) > 30:
                wd = "…" + wd[-29:]
            line.append(wd, style="dim italic")
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
        Binding("question_mark", "show_help", "Help"),
        Binding("n", "new_session", "New Session"),
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
        self._run_active = False
        self._tick_timer: object | None = None

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
            self.push_screen(
                WelcomeScreen(
                    default_cwd=self._cwd,
                    default_verbose=self._verbose,
                ),
                self._on_welcome,
            )

    def _on_welcome(self, config: LaunchConfig) -> None:
        self._prompt = config.prompt
        self._cwd = config.cwd
        self._verbose = config.verbose
        if config.resume:
            self._resume = config.resume
        self._fork_session = config.fork
        self._begin_run()

    def _begin_run(self) -> None:
        self._run_active = True
        info_bar = self.query_one("#info-bar", InfoBar)
        info_bar.prompt_text = self._prompt or ""
        info_bar.working_dir = str(self._cwd) if self._cwd else str(Path.cwd())
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
        self._stop_tick()
        self._tick_timer = self.set_interval(0.1, self._tick)
        self._run_orchestrator()

    def _stop_tick(self) -> None:
        if self._tick_timer is not None:
            self._tick_timer.stop()  # type: ignore[union-attr]
            self._tick_timer = None

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

    def _reset_ui(self) -> None:
        self._prompt = None
        self._resume = None
        self._fork_session = False
        self._session_id = None
        self._stop_tick()

        info_bar = self.query_one("#info-bar", InfoBar)
        info_bar.prompt_text = ""
        info_bar.session_id = ""
        info_bar.working_dir = ""
        info_bar.resumed = False
        info_bar.forked = False

        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.turns = 0
        status_bar.cost_usd = 0.0
        status_bar.duration_s = 0.0
        status_bar.status = "idle"
        status_bar.spinner_frame = 0

        self.query_one("#output-log", RichLog).clear()
        self.query_one("#activity-log", RichLog).clear()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_new_session(self) -> None:
        if self._run_active:
            self.notify("Session still running.", severity="warning")
            return
        self._reset_ui()
        self.push_screen(
            WelcomeScreen(
                default_cwd=self._cwd,
                default_verbose=self._verbose,
            ),
            self._on_welcome,
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
        finally:
            self._run_active = False
            self._stop_tick()
