from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import os
import re
import threading
from typing import Iterable, Optional
from difflib import SequenceMatcher

from .build import build_cookbook
from .config import EffectiveConfig, resolve_config
from .errors import VaultchefError, ConfigError
from .listing import list_recipes
from .paths import resolve_vault_paths
from .templates import render_cookbook_note
from .tex import check_tex_dependencies, format_tex_report, install_tex_packages

try:  # Textual is optional at import time for non-TUI usage.
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static
    from textual.screen import Screen
except Exception as exc:  # pragma: no cover
    raise ConfigError(
        "Textual is required for --tui. Install vaultchef with TUI dependencies."
    ) from exc


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class RecipeInfo:
    recipe_id: Optional[str]
    title: str
    path: Path
    tags: list[str]

    def display(self, selected: bool) -> str:
        marker = "[x]" if selected else "[ ]"
        rid = f"{self.recipe_id}: " if self.recipe_id not in (None, "") else ""
        return f"{marker} {rid}{self.title}"


@dataclass(frozen=True)
class CookbookInfo:
    title: str
    stem: str
    path: Path

    def display(self) -> str:
        if self.title and self.title != self.stem:
            return f"{self.title} ({self.stem})"
        return self.stem


class VaultchefApp(App):
    TITLE = "vaultchef"
    CSS = """
    Screen {
        padding: 1 2;
        background: #F8F4EE;
        color: #1C1A17;
    }

    Header, Footer {
        background: #F2ECE3;
        color: #1C1A17;
    }

    Footer .footer--key,
    Footer .footer--description,
    Footer .footer--highlight,
    Footer .footer--binding,
    Footer Label,
    Footer * {
        color: #1C1A17;
    }

    #title {
        text-style: bold;
        color: #1C1A17;
    }

    #mode-actions {
        height: auto;
        align: center middle;
        padding: 1 0;
    }

    #mode-actions Button {
        margin: 0 2;
    }

    #lists {
        height: 1fr;
    }

    #tag-list, #recipe-list, #selected-list, #cookbook-list {
        height: 1fr;
        border: round #D8C9B6;
        background: #FDFBF7;
    }

    ListView,
    ListView > ListItem,
    ListView > .list-item,
    ListView Label {
        color: #1C1A17;
    }

    ListView > ListItem.--highlight,
    ListView > ListItem.-highlight,
    ListView > .list-item.--highlight,
    ListView > .list-item.-highlight,
    ListView > .list-item--highlight {
        background: #E8DDCF;
        color: #1C1A17;
        text-style: bold;
    }

    ListView:focus > ListItem.--highlight,
    ListView:focus > ListItem.-highlight,
    ListView:focus > .list-item.--highlight,
    ListView:focus > .list-item.-highlight,
    ListView:focus > .list-item--highlight {
        background: #9A7B4F;
        color: #F8F4EE;
    }

    ListView > ListItem.cookbook-selected {
        background: #9A7B4F;
        color: #F8F4EE;
        text-style: bold;
    }

    #status {
        height: auto;
        padding: 1 0 0 0;
        color: #5E4F42;
    }

    #name-input, #search-input {
        margin: 0 0 1 0;
        background: #FDFBF7;
        border: round #D8C9B6;
        color: #1C1A17;
    }

    Button {
        background: #F2ECE3;
        color: #1C1A17;
        border: round #D8C9B6;
    }

    Button.-primary {
        background: #9A7B4F;
        color: #F8F4EE;
        border: round #9A7B4F;
    }

    Button:hover {
        background: #E8DDCF;
    }

    Button.-primary:hover {
        background: #8C6F46;
    }

    Button:focus {
        background: #9A7B4F;
        color: #F8F4EE;
        border: round #9A7B4F;
        text-style: none;
    }

    Button:focus > .button--label {
        background: transparent;
        color: #F8F4EE;
        text-style: none;
    }

    Input {
        background: #FDFBF7;
        border: round #D8C9B6;
        color: #1C1A17;
    }

    #build-title {
        text-style: bold;
        padding: 1 0 0 0;
    }

    #build-animation {
        height: auto;
        padding: 1 0 0 0;
    }

    #build-bar {
        height: auto;
        padding: 0 0 1 0;
    }

    #build-status {
        height: auto;
        color: $text-muted;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, cfg: EffectiveConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.vault = resolve_vault_paths(cfg)
        self.recipes = _load_recipes(cfg)
        self.tags = _unique_tags(self.recipes)
        self.cookbooks = _load_cookbooks(cfg)

    def on_mount(self) -> None:
        self.push_screen(ModeScreen())
        if self.cfg.tex.check_on_startup:
            result = check_tex_dependencies(pdf_engine=self.cfg.pandoc.pdf_engine)
            if result.missing_binaries or result.missing_required or result.missing_optional:
                self.push_screen(TexDepsScreen(result))


def _header_icon(screen: Screen) -> str:
    app = getattr(screen, "app", None)
    cfg = getattr(app, "cfg", None) if app else None
    icon = getattr(getattr(cfg, "tui", None), "header_icon", None)
    if icon is None:
        return "🍳"
    text = str(icon).strip()
    return text or "🍳"


class ModeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(icon=_header_icon(self))
        yield Static("vaultchef", id="title")
        yield Static("Create a cookbook or build an existing one.")
        with Horizontal(id="mode-actions"):
            yield Button("[underline]C[/underline]reate cookbook", id="create")
            yield Button("[underline]B[/underline]uild cookbook", id="build")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#create", Button).focus()

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


class CreateCookbookScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.selected: list[RecipeInfo] = []
        self.tag_filter: Optional[str] = None
        self.search_query: str = ""

    def compose(self) -> ComposeResult:
        yield Header(icon=_header_icon(self))
        yield Label("Cookbook name")
        yield Input(placeholder="Family Cookbook", id="name-input")
        yield Label("Filter tags")
        with Horizontal(id="lists"):
            with Vertical():
                yield ListView(id="tag-list")
                yield Label("Recipes")
                yield Input(placeholder="Search recipes", id="search-input")
                yield ListView(id="recipe-list")
            with Vertical():
                yield Label("Selected")
                yield ListView(id="selected-list")
        with Horizontal():
            yield Button("Create cookbook", id="create", variant="primary")
            yield Button("Back", id="back")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_tags()
        self._refresh_recipes()
        self._refresh_selected()
        self.query_one("#name-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        widget = getattr(event, "input", event.control)
        if widget.id == "search-input":
            self.search_query = event.value
            self._refresh_recipes()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self._create_cookbook()
        elif event.button.id == "back":
            self.app.pop_screen()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        list_view = getattr(event, "list_view", event.control)
        if list_view.id == "tag-list":
            self._select_tag(event.item)
        elif list_view.id == "recipe-list":
            self._toggle_recipe(event.item)

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
            if focused.id == "search-input" and event.key in ("down", "up"):
                delta = 1 if event.key == "down" else -1
                self._move_highlight_in(self.query_one("#recipe-list", ListView), delta)
                event.stop()
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
            self.query_one("#name-input", Input),
            self.query_one("#tag-list", ListView),
            self.query_one("#search-input", Input),
            self.query_one("#recipe-list", ListView),
            self.query_one("#selected-list", ListView),
            self.query_one("#create", Button),
            self.query_one("#back", Button),
        ]
        focused = self.app.focused
        if focused in order:
            idx = order.index(focused)
            next_idx = (idx + direction) % len(order)
        else:
            next_idx = 0
        order[next_idx].focus()

    def _focused_list_view(self) -> Optional[ListView]:
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

    def _activate_focused(self) -> None:
        focused = self.app.focused
        if isinstance(focused, ListView):
            item = _highlighted_item(focused)
            if not item:
                return
            if focused.id == "tag-list":
                self._select_tag(item)
            elif focused.id == "recipe-list":
                self._toggle_recipe(item)
            return
        if isinstance(focused, Button) and hasattr(focused, "press"):
            focused.press()

    def _select_tag(self, item: ListItem) -> None:
        tag = getattr(item, "tag_value", None)
        self.tag_filter = tag if tag != "__all__" else None
        self._refresh_recipes()

    def _toggle_recipe(self, item: ListItem) -> None:
        recipe = getattr(item, "recipe", None)
        if not recipe:
            return
        if recipe in self.selected:
            self.selected = [r for r in self.selected if r != recipe]
        else:
            self.selected.append(recipe)
        self._refresh_recipes()
        self._refresh_selected()

    def _refresh_tags(self) -> None:
        tag_list = self.query_one("#tag-list", ListView)
        _clear_list(tag_list)
        all_item = ListItem(Label("All tags"))
        all_item.tag_value = "__all__"
        tag_list.append(all_item)
        for tag in self.app.tags:
            item = ListItem(Label(tag))
            item.tag_value = tag
            tag_list.append(item)

    def _refresh_recipes(self) -> None:
        recipes = self.app.recipes
        if self.tag_filter:
            recipes = [r for r in recipes if self.tag_filter in r.tags]
        if self.search_query:
            recipes = _fuzzy_filter(recipes, self.search_query, lambda r: r.title)
        recipe_list = self.query_one("#recipe-list", ListView)
        _clear_list(recipe_list)
        for recipe in recipes:
            item = ListItem(Label(recipe.display(recipe in self.selected)))
            item.recipe = recipe
            recipe_list.append(item)

    def _refresh_selected(self) -> None:
        selected_list = self.query_one("#selected-list", ListView)
        _clear_list(selected_list)
        for recipe in self.selected:
            selected_list.append(ListItem(Label(f"- {recipe.title}")))

    def _create_cookbook(self) -> None:
        name_input = self.query_one("#name-input", Input)
        name = name_input.value.strip()
        if not name:
            self._set_status("Cookbook name is required.")
            return
        if not self.selected:
            self._set_status("Select at least one recipe.")
            return
        cookbooks_dir = self.app.vault.cookbooks_dir
        cookbooks_dir.mkdir(parents=True, exist_ok=True)
        path = cookbooks_dir / f"{name}.md"
        if path.exists():
            self._set_status(f"Cookbook already exists: {path}")
            return
        embeds = [embed_path_for_recipe(r.path, self.app.vault.vault_root) for r in self.selected]
        content = render_cookbook_note(name, embeds)
        path.write_text(content, encoding="utf-8")
        self._set_status(f"Created cookbook: {path}")
        self.app.exit()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)


class BuildCookbookScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.search_query: str = ""
        self.selected: Optional[CookbookInfo] = None
        self.highlight_index: int = 0

    def compose(self) -> ComposeResult:
        yield Header(icon=_header_icon(self))
        yield Label("Find a cookbook")
        yield Input(placeholder="Type to search", id="search-input")
        yield ListView(id="cookbook-list")
        with Horizontal():
            yield Button("Build", id="build", variant="primary")
            yield Button("Back", id="back")
        yield Static("", id="status")
        yield Footer()

    async def on_mount(self) -> None:
        await self._refresh_cookbooks()
        self.query_one("#search-input", Input).focus()

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
            self.highlight_index = _list_view_index(list_view, item)
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

    def _focused_list_view(self) -> Optional[ListView]:
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
        self.highlight_index = _current_index(list_view, self.highlight_index)
        self._apply_cookbook_selection()

    def _activate_focused(self) -> None:
        focused = self.app.focused
        if isinstance(focused, ListView):
            item = _highlighted_item(focused)
            if item:
                self.selected = getattr(item, "cookbook", None)
                self._build_selected()
            return
        if isinstance(focused, Button) and hasattr(focused, "press"):
            focused.press()

    async def _refresh_cookbooks(self) -> None:
        cookbooks = self.app.cookbooks
        if self.search_query:
            cookbooks = _fuzzy_filter(cookbooks, self.search_query, lambda c: c.display())
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
        self._apply_cookbook_selection()

    def _apply_cookbook_selection(self) -> None:
        list_view = self.query_one("#cookbook-list", ListView)
        items = list(list_view.children)
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

    def _schedule_cookbook_selection(self) -> None:
        try:
            self.call_after_refresh(self._apply_cookbook_selection)
        except Exception:
            self.set_timer(0, self._apply_cookbook_selection)

    def _build_selected(self) -> None:
        cookbook = self.selected or _current_highlight(self.query_one("#cookbook-list", ListView))
        if not cookbook:
            self._set_status("Select a cookbook to build.")
            return
        cfg = replace(self.app.cfg, project_dir=os.getcwd())
        self.app.push_screen(BuildProgressScreen(cookbook, cfg))

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)


class TexDepsScreen(Screen):
    def __init__(self, result) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        yield Header(icon=_header_icon(self))
        yield Static("TeX dependencies missing", id="title")
        for line in format_tex_report(self.result):
            yield Static(line)
        yield Static("Run `vaultchef tex-check` for details or set tex_check = false to disable this warning.")
        with Horizontal():
            yield Button("Install packages", id="install", variant="primary")
            yield Button("Continue", id="continue")
            yield Button("Quit", id="quit")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#install", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
            return
        if event.button.id == "continue":
            self.app.pop_screen()
            return
        if event.button.id == "install":
            missing = self.result.missing_required + self.result.missing_optional
            if not missing:
                self._set_status("No missing packages to install.")
                return
            try:
                install_tex_packages(missing)
            except ConfigError as exc:
                self._set_status(str(exc))
                return
            self._set_status("Installation complete.")
            self.app.pop_screen()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)


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
        yield Header(icon=_header_icon(self))
        yield Static(f"Cooking up {self.cookbook.display()}", id="build-title")
        yield Static("", id="build-animation")
        yield Static("", id="build-bar")
        yield Static("Building...", id="build-status")
        yield Footer()

    def on_mount(self) -> None:
        self._update_animation()
        self._timer = self.set_interval(0.12, self._update_animation)
        thread = threading.Thread(target=self._run_build, daemon=True)
        thread.start()

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

        bar_width = 24
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
        self.query_one("#build-bar", Static).update("Press Enter to return.")


def run_tui(cli_args: dict[str, object]) -> int:
    cfg = resolve_config(cli_args)
    app = VaultchefApp(cfg)
    app.run()
    return 0


def _load_recipes(cfg: EffectiveConfig) -> list[RecipeInfo]:
    recipes: list[RecipeInfo] = []
    for rec in list_recipes(cfg, None, None):
        path = Path(rec.get("path", ""))
        tags = _normalize_tags(rec.get("tags"))
        recipes.append(
            RecipeInfo(
                recipe_id=None if rec.get("recipe_id") is None else str(rec.get("recipe_id")),
                title=str(rec.get("title") or path.stem),
                path=path,
                tags=tags,
            )
        )
    return recipes


def _load_cookbooks(cfg: EffectiveConfig) -> list[CookbookInfo]:
    vault = resolve_vault_paths(cfg)
    cookbooks: list[CookbookInfo] = []
    if not vault.cookbooks_dir.exists():
        return cookbooks
    for path in sorted(vault.cookbooks_dir.rglob("*.md")):
        title = _parse_frontmatter_title(path) or path.stem
        cookbooks.append(CookbookInfo(title=title, stem=path.stem, path=path))
    return cookbooks


def _parse_frontmatter_title(path: Path) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = FRONTMATTER_RE.search(text)
    if not match:
        return None
    try:
        import yaml

        data = yaml.safe_load(match.group(1)) or {}
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    title = data.get("title")
    if not title:
        return None
    return str(title)


def _normalize_tags(tags: object) -> list[str]:
    if isinstance(tags, list):
        return [str(t) for t in tags]
    if isinstance(tags, str):
        return [tags]
    return []


def _unique_tags(recipes: Iterable[RecipeInfo]) -> list[str]:
    found: set[str] = set()
    for rec in recipes:
        found.update(rec.tags)
    return sorted(t for t in found if t)


def _fuzzy_filter(items: list[object], query: str, key) -> list[object]:
    q = query.strip().lower()
    if not q:
        return items
    scored = []
    for item in items:
        text = str(key(item)).lower()
        if q in text:
            score = 1.0
        else:
            score = SequenceMatcher(None, q, text).ratio()
        if score >= 0.2:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


def embed_path_for_recipe(recipe_path: Path, vault_root: Path) -> str:
    rel = recipe_path.relative_to(vault_root)
    return rel.with_suffix("").as_posix()


def _clear_list(list_view: ListView) -> None:
    if hasattr(list_view, "clear"):
        list_view.clear()
    else:  # pragma: no cover - older Textual versions
        list_view.remove_children()


def _ensure_highlight(list_view: ListView) -> None:
    try:
        highlighted = getattr(list_view, "highlighted", None)
        if highlighted in (None, -1):
            if list_view.children:
                if hasattr(list_view, "index"):
                    list_view.index = 0
                elif hasattr(list_view, "highlighted"):
                    list_view.highlighted = 0
    except Exception:
        pass


def _list_view_index(list_view: ListView, item: ListItem) -> int:
    try:
        return list(list_view.children).index(item)
    except ValueError:
        return 0
    except Exception:
        return 0


def _current_index(list_view: ListView, fallback: int) -> int:
    highlighted = getattr(list_view, "highlighted", None)
    if isinstance(highlighted, int) and highlighted >= 0:
        return highlighted
    item = getattr(list_view, "highlighted_child", None)
    if item is not None:
        return _list_view_index(list_view, item)
    return fallback


def _current_highlight(list_view: ListView) -> Optional[CookbookInfo]:
    item = getattr(list_view, "highlighted_child", None)
    if item is None:
        highlighted = getattr(list_view, "highlighted", None)
        if isinstance(highlighted, int) and highlighted >= 0:
            try:
                item = list_view.children[highlighted]
            except Exception:
                item = None
    if not item:
        return None
    return getattr(item, "cookbook", None)


def _highlighted_item(list_view: ListView) -> Optional[ListItem]:
    item = getattr(list_view, "highlighted_child", None)
    if item is None:
        highlighted = getattr(list_view, "highlighted", None)
        if isinstance(highlighted, int) and highlighted >= 0:
            try:
                item = list_view.children[highlighted]
            except Exception:
                item = None
    return item
