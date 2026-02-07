from __future__ import annotations

from ..config import resolve_config
from .app import VaultchefApp


def run_tui(cli_args: dict[str, object]) -> int:
    cfg = resolve_config(cli_args)
    app = VaultchefApp(cfg)
    app.run()
    return 0


__all__ = ["run_tui", "VaultchefApp"]
