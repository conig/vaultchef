from __future__ import annotations

from ..state import CookbookInfo
from ..textual import ListItem, ListView


def clear_list(list_view: ListView) -> None:
    if hasattr(list_view, "clear"):
        list_view.clear()
    else:  # pragma: no cover - older Textual versions
        list_view.remove_children()


def list_view_index(list_view: ListView, item: ListItem) -> int:
    try:
        return list(list_view.children).index(item)
    except Exception:
        return 0


def current_index(list_view: ListView, fallback: int) -> int:
    highlighted = getattr(list_view, "highlighted", None)
    if isinstance(highlighted, int) and highlighted >= 0:
        return highlighted

    item = getattr(list_view, "highlighted_child", None)
    if item is not None:
        return list_view_index(list_view, item)
    return fallback


def highlighted_item(list_view: ListView) -> ListItem | None:
    item = getattr(list_view, "highlighted_child", None)
    if item is None:
        highlighted = getattr(list_view, "highlighted", None)
        if isinstance(highlighted, int) and highlighted >= 0:
            try:
                item = list_view.children[highlighted]
            except Exception:
                item = None
    return item


def current_highlight(list_view: ListView) -> CookbookInfo | None:
    item = highlighted_item(list_view)
    if not item:
        return None
    return getattr(item, "cookbook", None)
