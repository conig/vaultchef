from __future__ import annotations

import os
from dataclasses import replace

from ..common import apply_centered_card_width, header_icon, sync_screen_layout
from ..data_sources import fuzzy_filter
from ..state import CookbookInfo
from ..textual import (
    Button,
    ComposeResult,
    Footer,
    Header,
    Horizontal,
    Input,
    Label,
    ListItem,
    ListView,
    Screen,
    Static,
    Vertical,
)
from ..widgets.list_utils import current_highlight, current_index, highlighted_item, list_view_index
from .build_progress import BuildProgressScreen


class BuildCookbookScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.search_query: str = ""
        self.selected: CookbookInfo | None = None
        self.highlight_index: int = 0

    def compose(self) -> ComposeResult:
        yield Header(icon=header_icon(self))
        with Vertical(id="build-shell", classes="screen-shell"):
            with Vertical(id="build-card", classes="screen-card"):
                yield Label("Find a cookbook")
                yield Input(placeholder="Type to search", id="search-input")
                yield ListView(id="cookbook-list")
                with Horizontal(id="build-actions"):
                    yield Button("Build", id="build", variant="primary")
                    yield Button("Back", id="back")
                yield Static("", id="status")
        yield Footer()

    async def on_mount(self) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#build-card")
        await self._refresh_cookbooks()
        self.query_one("#search-input", Input).focus()

    def on_resize(self, event) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#build-card")

    async def on_input_changed(self, event: Input.Changed) -> None:
        widget = getattr(event, "input", event.control)
        if widget.id == "search-input":
            self.search_query = event.value
            await self._refresh_cookbooks()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "build":
            self._build_selected()
        elif event.button.id == "back":
            self.app.pop_screen()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        list_view = getattr(event, "list_view", event.control)
        if list_view.id == "cookbook-list":
            item = event.item
            self.selected = getattr(item, "cookbook", None)
            self.highlight_index = list_view_index(list_view, item)
            self._apply_cookbook_selection()
            self._build_selected()

    def on_key(self, event) -> None:
        focused = self.app.focused
        if event.key in ("tab",):
            self._cycle_focus(1)
            event.stop()
            return
        if event.key in ("shift+tab", "backtab"):
            self._cycle_focus(-1)
            event.stop()
            return
        if isinstance(focused, Input):
            if event.key in ("down", "up"):
                delta = 1 if event.key == "down" else -1
                self._move_highlight_in(self.query_one("#cookbook-list", ListView), delta)
                event.stop()
                return
            if event.key in ("enter",):
                self._build_selected()
                event.stop()
                return
            return
        if event.key in ("down", "j"):
            self._move_highlight(1)
            event.stop()
            return
        if event.key in ("up", "k"):
            self._move_highlight(-1)
            event.stop()
            return
        if event.key in ("h", "left"):
            self._cycle_focus(-1)
            event.stop()
            return
        if event.key in ("l", "right"):
            self._cycle_focus(1)
            event.stop()
            return
        if event.key in ("enter", "space"):
            self._activate_focused()
            event.stop()

    def _cycle_focus(self, direction: int) -> None:
        order = [
            self.query_one("#search-input", Input),
            self.query_one("#cookbook-list", ListView),
            self.query_one("#build", Button),
            self.query_one("#back", Button),
        ]
        focused = self.app.focused
        if focused in order:
            idx = order.index(focused)
            next_idx = (idx + direction) % len(order)
        else:
            next_idx = 0
        order[next_idx].focus()

    def _focused_list_view(self) -> ListView | None:
        focused = self.app.focused
        if isinstance(focused, ListView):
            return focused
        return None

    def _move_highlight(self, delta: int) -> None:
        list_view = self._focused_list_view()
        if not list_view:
            return
        self._move_highlight_in(list_view, delta)

    def _move_highlight_in(self, list_view: ListView, delta: int) -> None:
        try:
            if delta > 0:
                list_view.action_cursor_down()
            else:
                list_view.action_cursor_up()
        except Exception:
            pass

        self.highlight_index = current_index(list_view, self.highlight_index)
        self._apply_cookbook_selection()

    def _activate_focused(self) -> None:
        focused = self.app.focused
        if isinstance(focused, ListView):
            item = highlighted_item(focused)
            if item:
                self.selected = getattr(item, "cookbook", None)
                self._build_selected()
            return
        if isinstance(focused, Button) and hasattr(focused, "press"):
            focused.press()

    async def _refresh_cookbooks(self) -> None:
        cookbooks = self.app.cookbooks
        if self.search_query:
            cookbooks = fuzzy_filter(cookbooks, self.search_query, lambda c: c.display())

        list_view = self.query_one("#cookbook-list", ListView)
        if list_view.children:
            await list_view.clear()

        selected_stem = self.selected.stem if self.selected else None
        next_index = 0
        items: list[ListItem] = []
        for idx, book in enumerate(cookbooks):
            display_text = book.display()
            prefix = "> " if idx == next_index else "  "
            label = Label(f"{prefix}{display_text}")
            item = ListItem(label)
            item.cookbook = book
            item.display_text = display_text
            item.label_widget = label
            if selected_stem and book.stem == selected_stem:
                next_index = idx
            items.append(item)

        self.highlight_index = next_index
        if items:
            await list_view.extend(items)
        else:
            await list_view.extend([ListItem(Label("No cookbooks found"))])

        self._apply_cookbook_selection()

    def _apply_cookbook_selection(self) -> None:
        list_view = self.query_one("#cookbook-list", ListView)
        items = [item for item in list(list_view.children) if getattr(item, "cookbook", None)]
        if not items:
            self.selected = None
            return

        idx = max(0, min(self.highlight_index, len(items) - 1))
        for i, item in enumerate(items):
            if i == idx:
                if hasattr(item, "add_class"):
                    item.add_class("cookbook-selected")
                label = getattr(item, "label_widget", None)
                text = getattr(item, "display_text", None)
                if label is not None and text is not None:
                    label.update(f"> {text}")
            else:
                if hasattr(item, "remove_class"):
                    item.remove_class("cookbook-selected")
                label = getattr(item, "label_widget", None)
                text = getattr(item, "display_text", None)
                if label is not None and text is not None:
                    label.update(f"  {text}")

        self.highlight_index = idx
        self.selected = getattr(items[idx], "cookbook", None)
        try:
            if hasattr(list_view, "index"):
                list_view.index = idx
            elif hasattr(list_view, "highlighted"):
                list_view.highlighted = idx
        except Exception:
            pass

    def _build_selected(self) -> None:
        cookbook = self.selected or current_highlight(self.query_one("#cookbook-list", ListView))
        if not cookbook:
            self._set_status("Select a cookbook to build.")
            return

        cfg = replace(self.app.cfg, project_dir=os.getcwd())
        self.app.push_screen(BuildProgressScreen(cookbook, cfg))

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)
