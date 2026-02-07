from __future__ import annotations

from ..common import apply_centered_card_width, current_layout_mode, header_icon, set_hidden, sync_screen_layout
from ..layout import should_animate_mode_hero, show_mode_hero
from ..textual import Button, ComposeResult, Footer, Header, Horizontal, Screen, Static, Vertical
from .build import BuildCookbookScreen
from .create import CreateCookbookScreen

POT_FRAME_0 = [
    "            .-----.--,",
    "           (______(_. \\ _",
    "            /     /    | |",
    "           :     /     |_|",
    "           | .---------/ \\-.      _.-----,",
    "           | :'-------'- -':       |   = |-.",
    " ___.--------:___          : _  _  |   = |-'",
    "'--.)________).--'______.-' (_)(_) :_____: ",
]
POT_FRAME_1 = [
    "            .-----.--,",
    "           (______(_. \\ _",
    "            /     /    | |",
    "           :     /     |_|",
    "           | .--------- | -.      _.-----,",
    "           | :'------- -'- :       |   = |-.",
    " ___.--------:___          : _  _  |   = |-'",
    "'--.)________).--'______.-' (_)(_) :_____: ",
]
POT_FRAMES = [POT_FRAME_0, POT_FRAME_1]


class ModeScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self._hero_timer = None
        self._frame_idx = 0
        self._last_hero_width = 0

    def compose(self) -> ComposeResult:
        yield Header(icon=header_icon(self))
        with Vertical(id="mode-shell", classes="screen-shell"):
            with Vertical(id="mode-card", classes="screen-card"):
                yield Static("vaultchef", id="title")
                yield Static("Create a cookbook or build an existing one.", id="mode-subtitle")
                with Vertical(id="mode-hero"):
                    yield Static("", id="mode-pot")
                with Horizontal(id="mode-actions"):
                    yield Button("[underline]C[/underline]reate cookbook", id="create")
                    yield Button("[underline]B[/underline]uild cookbook", id="build")
        yield Footer()

    def on_mount(self) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#mode-card")
        self.set_timer(0, self._sync_animation_state)
        self.query_one("#create", Button).focus()

    def on_resize(self, event) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#mode-card")
        self._sync_animation_state()

    def on_unmount(self, event=None) -> None:
        self._stop_animation()

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

    def _sync_animation_state(self) -> None:
        hero = self.query_one("#mode-hero", Vertical)
        layout_mode = current_layout_mode(self)
        mode_animation = getattr(getattr(self.app.cfg, "tui", None), "mode_animation", "auto")

        visible = show_mode_hero(layout_mode, mode_animation)
        set_hidden(hero, not visible)
        if not visible:
            self._stop_animation()
            return

        if should_animate_mode_hero(layout_mode, mode_animation):
            self._start_animation()
            return

        self._stop_animation()
        self._render_hero(frame_idx=0)

    def _start_animation(self) -> None:
        if self._hero_timer is not None:
            return
        if not self._render_hero(frame_idx=self._frame_idx):
            return
        self._hero_timer = self.set_interval(0.14, self._tick_hero)

    def _stop_animation(self) -> None:
        if self._hero_timer is None:
            return
        self._hero_timer.stop()
        self._hero_timer = None

    def _tick_hero(self) -> None:
        self._frame_idx = (self._frame_idx + 1) % len(POT_FRAMES)
        self._render_hero(frame_idx=self._frame_idx)

    def _render_hero(self, frame_idx: int) -> bool:
        pot_lines = _normalize_art(POT_FRAMES[frame_idx % len(POT_FRAMES)])

        art_width = max(len(line) for line in pot_lines)
        hero = self.query_one("#mode-hero", Vertical)
        hero_width = int(getattr(hero.size, "width", 0) or 0)
        if hero_width > 0:
            self._last_hero_width = hero_width
        elif self._last_hero_width > 0:
            hero_width = self._last_hero_width
        else:
            self.query_one("#mode-pot", Static).update("")
            return False
        left_pad = max(0, (hero_width - art_width) // 2)
        prefix = " " * left_pad

        pot_text = "\n".join(f"{prefix}{line}" for line in pot_lines)
        self.query_one("#mode-pot", Static).update(pot_text)
        return True


def _normalize_art(lines) -> list[str]:
    trimmed = [str(line).rstrip() for line in lines]
    non_empty = [line for line in trimmed if line.strip()]
    if not non_empty:
        return trimmed
    common_indent = min(len(line) - len(line.lstrip(" ")) for line in non_empty)
    if common_indent <= 0:
        return trimmed
    return [line[common_indent:] if len(line) >= common_indent else line for line in trimmed]
