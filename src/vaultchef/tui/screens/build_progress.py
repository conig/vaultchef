from __future__ import annotations

import threading
from pathlib import Path

from ...build import build_cookbook
from ...config import EffectiveConfig
from ...errors import VaultchefError
from ..common import apply_centered_card_width, current_layout_mode, header_icon, sync_screen_layout
from ..layout import build_progress_bar_width
from ..state import CookbookInfo
from ..textual import ComposeResult, Footer, Header, Screen, Static, Vertical


class BuildProgressScreen(Screen):
    def __init__(self, cookbook: CookbookInfo, cfg: EffectiveConfig) -> None:
        super().__init__()
        self.cookbook = cookbook
        self.cfg = cfg
        self._frame_idx = 0
        self._bar_pos = 0
        self._bar_dir = 1
        self._timer = None
        self._failed = False

    def compose(self) -> ComposeResult:
        yield Header(icon=header_icon(self))
        with Vertical(id="build-progress-shell", classes="screen-shell"):
            with Vertical(id="build-progress-card", classes="screen-card"):
                yield Static(f"Cooking up {self.cookbook.display()}", id="build-title")
                yield Static("", id="build-animation")
                yield Static("", id="build-bar")
                yield Static("Building...", id="build-status")
        yield Footer()

    def on_mount(self) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#build-progress-card")
        self._update_animation()
        self._timer = self.set_interval(0.12, self._update_animation)
        thread = threading.Thread(target=self._run_build, daemon=True)
        thread.start()

    def on_resize(self, event) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#build-progress-card")

    def on_key(self, event) -> None:
        if self._failed and event.key in ("enter", "escape", "q"):
            self.app.pop_screen()
            event.stop()

    def _run_build(self) -> None:
        try:
            result = build_cookbook(self.cookbook.stem, self.cfg, dry_run=False, verbose=False)
        except VaultchefError as exc:
            self.app.call_from_thread(self._on_build_error, str(exc))
            return
        except Exception as exc:  # pragma: no cover
            self.app.call_from_thread(self._on_build_error, f"Build failed: {exc}")
            return
        self.app.call_from_thread(self._on_build_success, result.pdf)

    def _update_animation(self) -> None:
        frames = [
            "Simmering .  ",
            "Simmering .. ",
            "Simmering ...",
            "Simmering ....",
            "Simmering ...",
            "Simmering .. ",
        ]
        self._frame_idx = (self._frame_idx + 1) % len(frames)
        self.query_one("#build-animation", Static).update(frames[self._frame_idx])

        bar_width = build_progress_bar_width(
            int(getattr(getattr(self, "size", None), "width", 0) or 0),
            current_layout_mode(self),
        )
        self._bar_pos += self._bar_dir
        if self._bar_pos >= bar_width:
            self._bar_pos = bar_width
            self._bar_dir = -1
        elif self._bar_pos <= 0:
            self._bar_pos = 0
            self._bar_dir = 1

        filled = self._bar_pos
        bar = f"[{'#' * filled}{'-' * (bar_width - filled)}]"
        self.query_one("#build-bar", Static).update(bar)

    def _stop_animation(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _on_build_success(self, pdf_path: Path) -> None:
        self._stop_animation()
        self.query_one("#build-status", Static).update(f"Built {pdf_path}")
        self.set_timer(0.6, self.app.exit)

    def _on_build_error(self, message: str) -> None:
        self._stop_animation()
        self._failed = True
        self.query_one("#build-status", Static).update(message)
        self.query_one("#build-animation", Static).update("Build failed.")
        self.query_one("#build-bar", Static).update("Press Enter, Esc, or q to return.")
