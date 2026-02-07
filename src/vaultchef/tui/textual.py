from __future__ import annotations

from ..errors import ConfigError

try:  # Textual is optional at import time for non-TUI usage.
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.screen import Screen
    from textual.theme import Theme
    from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static
except Exception as exc:  # pragma: no cover
    raise ConfigError(
        "Textual is required for --tui. Install vaultchef with TUI dependencies."
    ) from exc

__all__ = [
    "App",
    "Button",
    "ComposeResult",
    "Footer",
    "Header",
    "Horizontal",
    "Input",
    "Label",
    "ListItem",
    "ListView",
    "Screen",
    "Static",
    "Theme",
    "Vertical",
]
