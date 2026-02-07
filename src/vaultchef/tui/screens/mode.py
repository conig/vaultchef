from __future__ import annotations

from ..common import apply_centered_card_width, header_icon, sync_screen_layout
from ..textual import Button, ComposeResult, Footer, Header, Horizontal, Screen, Static, Vertical
from .build import BuildCookbookScreen
from .create import CreateCookbookScreen


class ModeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(icon=header_icon(self))
        with Vertical(id="mode-shell", classes="screen-shell"):
            with Vertical(id="mode-card", classes="screen-card"):
                yield Static("vaultchef", id="title")
                yield Static("Create a cookbook or build an existing one.", id="mode-subtitle")
                with Horizontal(id="mode-actions"):
                    yield Button("[underline]C[/underline]reate cookbook", id="create")
                    yield Button("[underline]B[/underline]uild cookbook", id="build")
        yield Footer()

    def on_mount(self) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#mode-card")
        self.query_one("#create", Button).focus()

    def on_resize(self, event) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#mode-card")

    def on_key(self, event) -> None:
        if event.key in ("c", "C"):
            self.query_one("#create", Button).press()
            event.stop()
            return
        if event.key in ("b", "B"):
            self.query_one("#build", Button).press()
            event.stop()
            return
        if event.key in ("h", "left"):
            self.query_one("#create", Button).focus()
            event.stop()
            return
        if event.key in ("l", "right"):
            self.query_one("#build", Button).focus()
            event.stop()
            return
        if event.key in ("enter", "space"):
            focused = self.app.focused
            if isinstance(focused, Button) and hasattr(focused, "press"):
                focused.press()
                event.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self.app.push_screen(CreateCookbookScreen())
        elif event.button.id == "build":
            self.app.push_screen(BuildCookbookScreen())
