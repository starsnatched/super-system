from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
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
from super_system.config import load_api_key, save_api_key

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


@dataclass
class LaunchConfig:
    prompt: str
    cwd: Path | None = None
    verbose: bool = False
    api_key: str | None = None


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
        tbl.add_row("n", "Start new run")
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

    #api-key-row {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    #api-key-input {
        width: 1fr;
    }

    #api-key-input:focus {
        border: tall $accent;
    }

    #api-key-summary {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    #api-key-summary-label {
        width: 16;
        padding: 0 1 0 0;
        text-align: right;
        color: $text-muted;
    }

    #api-key-summary-status {
        width: auto;
        padding: 0 1 0 0;
    }

    #btn-change-key {
        min-width: 10;
        height: 1;
        margin: 0 0 0 1;
        background: transparent;
        border: none;
        color: $accent;
    }

    #btn-change-key:hover {
        text-style: underline;
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
        default_api_key: str | None = None,
    ) -> None:
        super().__init__()
        self._default_cwd = default_cwd or Path.cwd()
        self._default_verbose = default_verbose
        self._default_api_key = (
            default_api_key
            or os.environ.get("ANTHROPIC_API_KEY", "")
            or load_api_key()
        )

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
                with Horizontal(id="api-key-summary"):
                    yield Static("API Key", id="api-key-summary-label")
                    yield Static(
                        "[bright_green]✓ configured[/]",
                        id="api-key-summary-status",
                    )
                    yield Button("Change", id="btn-change-key", variant="default")
                with Horizontal(id="api-key-row"):
                    yield Static("API Key", classes="field-label")
                    yield Input(
                        value=self._default_api_key,
                        placeholder="sk-ant-…",
                        id="api-key-input",
                        password=True,
                    )
                with Horizontal(classes="switch-row"):
                    yield Static("Verbose", classes="switch-label")
                    yield Switch(id="verbose-switch", value=self._default_verbose)

            yield Input(
                placeholder="What would you like to build?",
                id="prompt-input",
            )

            yield Static(
                "[white]enter[/] [dim]start[/]   [white]esc[/] [dim]quit[/]",
                id="hint",
            )

        yield Footer()

    def on_mount(self) -> None:
        has_key = bool(self._default_api_key)
        self.query_one("#api-key-summary").display = has_key
        self.query_one("#api-key-row").display = not has_key

    def _build_config(self, prompt: str) -> LaunchConfig:
        cwd_raw = self.query_one("#cwd-input", Input).value.strip()
        cwd = Path(cwd_raw).resolve() if cwd_raw else None
        verbose = self.query_one("#verbose-switch", Switch).value
        api_key = self.query_one("#api-key-input", Input).value.strip() or None
        return LaunchConfig(
            prompt=prompt,
            cwd=cwd,
            verbose=verbose,
            api_key=api_key,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-change-key":
            self.query_one("#api-key-summary").display = False
            self.query_one("#api-key-row").display = True
            self.query_one("#api-key-input", Input).value = ""
            self.query_one("#api-key-input", Input).focus()

    def _validate_config(self, config: LaunchConfig) -> bool:
        if config.cwd and not config.cwd.is_dir():
            self.notify(
                f"Directory not found: {config.cwd}",
                severity="error",
                title="Invalid Path",
            )
            self.query_one("#cwd-input", Input).focus()
            return False
        if not config.api_key:
            self.notify(
                "An Anthropic API key is required.",
                severity="error",
                title="Missing API Key",
            )
            self.query_one("#api-key-summary").display = False
            self.query_one("#api-key-row").display = True
            self.query_one("#api-key-input", Input).focus()
            return False
        return True

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "cwd-input":
            if self.query_one("#api-key-row").display:
                self.query_one("#api-key-input", Input).focus()
            else:
                self.query_one("#prompt-input", Input).focus()
            return
        if event.input.id == "api-key-input":
            key = event.value.strip()
            if key:
                save_api_key(key)
                os.environ["ANTHROPIC_API_KEY"] = key
                self._default_api_key = key
                self.query_one("#api-key-row").display = False
                self.query_one("#api-key-summary").display = True
                self.notify("API key saved.", severity="information")
            self.query_one("#prompt-input", Input).focus()
            return
        prompt = event.value.strip()
        if not prompt:
            return
        config = self._build_config(prompt)
        if not self._validate_config(config):
            return
        self.dismiss(config)

    def action_quit_app(self) -> None:
        self.app.exit()


class InfoBar(Static):
    prompt_text: reactive[str] = reactive("")
    working_dir: reactive[str] = reactive("")

    def render(self) -> Text:
        line = Text()
        line.append("  ⚡ ", style="bold bright_cyan")
        display = self.prompt_text
        if len(display) > 60:
            display = display[:60] + "…"
        line.append(display, style="white")
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
        Binding("n", "new_run", "New Run"),
    ]

    def __init__(
        self,
        prompt: str | None = None,
        *,
        cwd: Path | None = None,
        verbose: bool = False,
    ) -> None:
        super().__init__()
        self._prompt = prompt
        self._cwd = cwd
        self._verbose = verbose
        self._api_key: str | None = None
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
                    default_api_key=self._api_key,
                ),
                self._on_welcome,
            )

    def _on_welcome(self, config: LaunchConfig) -> None:
        self._prompt = config.prompt
        self._cwd = config.cwd
        self._verbose = config.verbose
        self._api_key = config.api_key
        self._begin_run()

    def _begin_run(self) -> None:
        if self._api_key:
            os.environ["ANTHROPIC_API_KEY"] = self._api_key
        self._run_active = True
        info_bar = self.query_one("#info-bar", InfoBar)
        info_bar.prompt_text = self._prompt or ""
        info_bar.working_dir = str(self._cwd) if self._cwd else str(Path.cwd())

        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.status = "running"

        output = self.query_one("#output-log", RichLog)
        output.write(Text("  Starting…", style="dim italic"))

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

    def _reset_ui(self) -> None:
        self._prompt = None
        self._stop_tick()

        info_bar = self.query_one("#info-bar", InfoBar)
        info_bar.prompt_text = ""
        info_bar.working_dir = ""

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

    def action_new_run(self) -> None:
        if self._run_active:
            self.notify("Run still active.", severity="warning")
            return
        self._reset_ui()
        self.push_screen(
            WelcomeScreen(
                default_cwd=self._cwd,
                default_verbose=self._verbose,
                default_api_key=self._api_key,
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
                title = "[red]✗ Run failed[/red]"
                border = "red"
            else:
                title = "[green]✓ Run complete[/green]"
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

        def on_system(subtype: str, data: object) -> None:
            line = Text()
            line.append(f"{self._ts()} ", style="dim green")
            line.append(f"[{subtype}] ", style="dim cyan")
            line.append(str(data)[:200], style="dim")
            activity.write(line)

        def on_interrupted() -> None:
            status_bar.status = "interrupted"
            activity.write(
                Text(f"{self._ts()}  ⚠ Interrupted", style="bold yellow")
            )

        def on_error(msg: str) -> None:
            output.write(Text(f"\n✗ {msg}", style="bold red"))
            status_bar.status = "failed"

        callbacks = RunCallbacks(
            on_banner=lambda: None,
            on_text=on_text,
            on_agent_dispatch=on_agent_dispatch,
            on_result=on_result,
            on_system=on_system,
            on_interrupted=on_interrupted,
            on_error=on_error,
        )

        try:
            await run(
                prompt,
                cwd=self._cwd,
                verbose=self._verbose,
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
