from __future__ import annotations

AUTO_WIDE_MIN_WIDTH = 140
AUTO_WIDE_MIN_HEIGHT = 36
AUTO_NORMAL_MIN_WIDTH = 100
AUTO_NORMAL_MIN_HEIGHT = 28
CREATE_WIZARD_MIN_HEIGHT = 30

VALID_LAYOUTS = {"auto", "compact", "normal", "wide"}
VALID_DENSITIES = {"cozy", "compact"}


def normalize_layout_mode(mode: object) -> str:
    text = str(mode or "").strip().lower()
    if text in VALID_LAYOUTS:
        return text
    return "auto"


def normalize_density(density: object) -> str:
    text = str(density or "").strip().lower()
    if text in VALID_DENSITIES:
        return text
    return "cozy"


def resolve_layout_mode(width: int, height: int, requested_mode: object) -> str:
    mode = normalize_layout_mode(requested_mode)
    if mode != "auto":
        return mode
    if width >= AUTO_WIDE_MIN_WIDTH and height >= AUTO_WIDE_MIN_HEIGHT:
        return "wide"
    if width >= AUTO_NORMAL_MIN_WIDTH and height >= AUTO_NORMAL_MIN_HEIGHT:
        return "normal"
    return "compact"


def use_create_wizard(layout_mode: str, height: int) -> bool:
    return layout_mode == "compact" or height < CREATE_WIZARD_MIN_HEIGHT


def centered_card_width(viewport_width: int, layout_mode: str) -> int:
    width = max(40, viewport_width)
    if layout_mode == "wide":
        target = min(120, width - 20)
    elif layout_mode == "normal":
        target = min(104, width - 12)
    else:
        target = width - 4
    return max(36, min(target, width - 2))


def build_progress_bar_width(viewport_width: int, layout_mode: str) -> int:
    width = max(30, viewport_width)
    if layout_mode == "wide":
        limit = 52
    elif layout_mode == "normal":
        limit = 40
    else:
        limit = 28
    return max(16, min(limit, width - 24))
