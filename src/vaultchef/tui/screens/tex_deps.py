from __future__ import annotations

from ...errors import ConfigError
from ...tex import format_tex_report, install_tex_packages
from ..common import apply_centered_card_width, header_icon, sync_screen_layout
from ..textual import Button, ComposeResult, Footer, Header, Horizontal, Screen, Static, Vertical


class TexDepsScreen(Screen):
    def __init__(self, result) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        yield Header(icon=header_icon(self))
        with Vertical(id="tex-shell", classes="screen-shell"):
            with Vertical(id="tex-card", classes="screen-card"):
                yield Static("TeX dependencies missing", id="title")
                for line in format_tex_report(self.result):
                    yield Static(line, classes="tex-report-line")
                yield Static(
                    "Run `vaultchef tex-check` for details or set tex_check = false to disable this warning."
                )
                with Horizontal(id="tex-actions"):
                    yield Button("Install packages", id="install", variant="primary")
                    yield Button("Continue", id="continue")
                    yield Button("Quit", id="quit")
                yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#tex-card")
        self.query_one("#install", Button).focus()

    def on_resize(self, event) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#tex-card")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
            return
        if event.button.id == "continue":
            self.app.pop_screen()
            return
        if event.button.id == "install":
            missing = self.result.missing_required + self.result.missing_optional
            if not missing:
                self._set_status("No missing packages to install.")
                return
            try:
                install_tex_packages(missing)
            except ConfigError as exc:
                self._set_status(str(exc))
                return
            self._set_status("Installation complete.")
            self.app.pop_screen()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)
