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
                    yield Button("[underline]I[/underline]nstall packages", id="install", variant="primary")
                    yield Button("[underline]C[/underline]ontinue (Esc)", id="continue")
                    yield Button("[underline]Q[/underline]uit", id="quit")
                yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#tex-card")
        self.query_one("#install", Button).focus()

    def on_resize(self, event) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#tex-card")

    def on_key(self, event) -> None:
        if event.key in ("i", "I"):
            self.query_one("#install", Button).press()
            event.stop()
            return
        if event.key in ("c", "C", "escape"):
            self.query_one("#continue", Button).press()
            event.stop()
            return
        if event.key in ("q", "Q"):
            self.query_one("#quit", Button).press()
            event.stop()
            return
        if event.key in ("h", "left"):
            self._cycle_focus(-1)
            event.stop()
            return
        if event.key in ("l", "right"):
            self._cycle_focus(1)
            event.stop()
            return
        if event.key in ("enter", "space"):
            focused = self.app.focused
            if isinstance(focused, Button) and hasattr(focused, "press"):
                focused.press()
                event.stop()

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

    def _cycle_focus(self, direction: int) -> None:
        order = [
            self.query_one("#install", Button),
            self.query_one("#continue", Button),
            self.query_one("#quit", Button),
        ]
        focused = self.app.focused
        if focused in order:
            idx = order.index(focused)
            next_idx = (idx + direction) % len(order)
        else:
            next_idx = 0
        order[next_idx].focus()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)
