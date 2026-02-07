from __future__ import annotations

from .textual import Screen
from .layout import centered_card_width
from .theme import TUI_THEME_NAME, TUI_THEMES

DEFAULT_HEADER_ICON = "🔪"
LAYOUT_CLASSES = ("layout-compact", "layout-normal", "layout-wide")
DENSITY_CLASSES = ("density-cozy", "density-compact")


def header_icon(screen: Screen) -> str:
    app = getattr(screen, "app", None)
    cfg = getattr(app, "cfg", None) if app else None
    icon = getattr(getattr(cfg, "tui", None), "header_icon", None)
    if icon is None:
        return DEFAULT_HEADER_ICON
    text = str(icon).strip()
    return text or DEFAULT_HEADER_ICON


def resolve_tui_theme_name() -> str:
    return TUI_THEME_NAME


def apply_theme(app, theme_name: str) -> None:
    theme = TUI_THEMES.get(theme_name)
    if theme is not None and hasattr(app, "register_theme"):
        try:
            app.register_theme(theme)
        except Exception:
            pass
    if hasattr(app, "theme"):
        try:
            app.theme = theme_name
        except Exception:
            pass
    if hasattr(app, "ansi_color"):
        try:
            app.ansi_color = True
        except Exception:
            pass


def current_layout_mode(screen: Screen) -> str:
    app = getattr(screen, "app", None)
    mode = getattr(app, "tui_layout_mode", "normal") if app else "normal"
    return str(mode)


def sync_layout_classes(node, layout_mode: str, density: str) -> None:
    for class_name in LAYOUT_CLASSES:
        _toggle_class(node, class_name, class_name == f"layout-{layout_mode}")
    for class_name in DENSITY_CLASSES:
        _toggle_class(node, class_name, class_name == f"density-{density}")


def sync_screen_layout(screen: Screen) -> None:
    app = getattr(screen, "app", None)
    if app is None:
        return
    mode = str(getattr(app, "tui_layout_mode", "normal"))
    density = str(getattr(app, "tui_density", "cozy"))
    sync_layout_classes(screen, mode, density)


def apply_centered_card_width(screen: Screen, selector: str) -> None:
    try:
        card = screen.query_one(selector)
    except Exception:
        return

    width = getattr(getattr(screen, "size", None), "width", 0)
    mode = current_layout_mode(screen)
    if isinstance(width, int) and width > 0:
        try:
            card.styles.width = centered_card_width(width, mode)
        except Exception:
            pass


def set_hidden(widget, hidden: bool) -> None:
    _toggle_class(widget, "is-hidden", hidden)


def _toggle_class(node, class_name: str, enabled: bool) -> None:
    if node is None:
        return
    if enabled:
        if hasattr(node, "add_class"):
            try:
                node.add_class(class_name)
            except Exception:
                pass
        return
    if hasattr(node, "remove_class"):
        try:
            node.remove_class(class_name)
        except Exception:
            pass
