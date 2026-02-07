from __future__ import annotations

from ..config import EffectiveConfig
from ..paths import resolve_vault_paths
from ..tex import check_tex_dependencies
from .common import apply_theme, resolve_tui_theme_name, sync_layout_classes
from .data_sources import load_cookbooks, load_recipes, unique_tags
from .layout import normalize_density, resolve_layout_mode
from .screens.mode import ModeScreen
from .screens.tex_deps import TexDepsScreen
from .textual import App
from .theme import APP_CSS


class VaultchefApp(App):
    TITLE = "vaultchef"
    CSS = APP_CSS
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, cfg: EffectiveConfig) -> None:
        super().__init__(ansi_color=True)
        self.cfg = cfg
        self._theme_name = resolve_tui_theme_name()
        self.tui_layout_mode = "normal"
        self.tui_density = normalize_density(cfg.tui.density)
        self.vault = resolve_vault_paths(cfg)
        self.recipes = load_recipes(cfg)
        self.tags = unique_tags(self.recipes)
        self.cookbooks = load_cookbooks(cfg)

    def on_mount(self) -> None:
        apply_theme(self, self._theme_name)
        self._refresh_layout_mode()
        self.push_screen(ModeScreen())
        if self.cfg.tex.check_on_startup:
            result = check_tex_dependencies(pdf_engine=self.cfg.pandoc.pdf_engine)
            if result.missing_binaries or result.missing_required or result.missing_optional:
                self.push_screen(TexDepsScreen(result))

    def on_resize(self, event) -> None:
        self._refresh_layout_mode()

    def _refresh_layout_mode(self) -> None:
        size = getattr(self, "size", None)
        width = int(getattr(size, "width", 0) or 0)
        height = int(getattr(size, "height", 0) or 0)
        self.tui_layout_mode = resolve_layout_mode(width, height, self.cfg.tui.layout)
        sync_layout_classes(self, self.tui_layout_mode, self.tui_density)
        for screen in tuple(getattr(self, "screen_stack", ())):
            sync_layout_classes(screen, self.tui_layout_mode, self.tui_density)
