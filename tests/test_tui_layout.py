from __future__ import annotations

from vaultchef.tui.layout import (
    build_progress_bar_width,
    centered_card_width,
    normalize_density,
    normalize_layout_mode,
    resolve_layout_mode,
    use_create_wizard,
)


# Purpose: verify normalize layout mode.
def test_normalize_layout_mode() -> None:
    assert normalize_layout_mode("WIDE") == "wide"
    assert normalize_layout_mode(" bad ") == "auto"


# Purpose: verify normalize density.
def test_normalize_density() -> None:
    assert normalize_density("COMPACT") == "compact"
    assert normalize_density("dense") == "cozy"


# Purpose: verify resolve layout mode auto thresholds.
def test_resolve_layout_mode_auto_thresholds() -> None:
    assert resolve_layout_mode(160, 40, "auto") == "wide"
    assert resolve_layout_mode(120, 30, "auto") == "normal"
    assert resolve_layout_mode(90, 24, "auto") == "compact"


# Purpose: verify resolve layout mode explicit override.
def test_resolve_layout_mode_explicit_override() -> None:
    assert resolve_layout_mode(80, 20, "wide") == "wide"
    assert resolve_layout_mode(160, 40, "compact") == "compact"


# Purpose: verify create wizard mode trigger.
def test_use_create_wizard() -> None:
    assert use_create_wizard("compact", 50) is True
    assert use_create_wizard("normal", 24) is True
    assert use_create_wizard("normal", 36) is False


# Purpose: verify centered card width bounds.
def test_centered_card_width_bounds() -> None:
    assert centered_card_width(200, "wide") == 120
    assert centered_card_width(90, "normal") <= 88
    assert centered_card_width(38, "compact") == 36


# Purpose: verify build progress bar width bounds.
def test_build_progress_bar_width_bounds() -> None:
    assert build_progress_bar_width(200, "wide") == 52
    assert build_progress_bar_width(120, "normal") == 40
    assert build_progress_bar_width(70, "compact") <= 28
    assert build_progress_bar_width(20, "compact") == 16
