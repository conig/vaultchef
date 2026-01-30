from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import os
import re
from typing import Iterable, Optional
from difflib import SequenceMatcher

from .build import build_cookbook
from .config import EffectiveConfig, resolve_config
from .errors import VaultchefError, ConfigError
from .listing import list_recipes
from .paths import resolve_vault_paths
from .templates import render_cookbook_note

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
    CSS = """
    Screen {
        padding: 1 2;
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
        border: round $surface;
    }

    #status {
        height: auto;
        padding: 1 0 0 0;
        color: $text-muted;
    }

    #name-input, #search-input {
        margin: 0 0 1 0;
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


class ModeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Vaultchef TUI", id="title")
        yield Static("Create a cookbook or build an existing one.")
        with Horizontal(id="mode-actions"):
            yield Button("Create cookbook", id="create", variant="primary")
            yield Button("Build cookbook", id="build")
        yield Footer()

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
        yield Header()
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

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Find a cookbook")
        yield Input(placeholder="Type to search", id="search-input")
        yield ListView(id="cookbook-list")
        with Horizontal():
            yield Button("Build", id="build", variant="primary")
            yield Button("Back", id="back")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_cookbooks()

    def on_input_changed(self, event: Input.Changed) -> None:
        widget = getattr(event, "input", event.control)
        if widget.id == "search-input":
            self.search_query = event.value
            self._refresh_cookbooks()

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
            self._build_selected()

    def _refresh_cookbooks(self) -> None:
        cookbooks = self.app.cookbooks
        if self.search_query:
            cookbooks = _fuzzy_filter(cookbooks, self.search_query, lambda c: c.display())
        list_view = self.query_one("#cookbook-list", ListView)
        _clear_list(list_view)
        for book in cookbooks:
            item = ListItem(Label(book.display()))
            item.cookbook = book
            list_view.append(item)

    def _build_selected(self) -> None:
        cookbook = self.selected or _current_highlight(self.query_one("#cookbook-list", ListView))
        if not cookbook:
            self._set_status("Select a cookbook to build.")
            return
        try:
            cfg = replace(self.app.cfg, project_dir=os.getcwd())
            result = build_cookbook(cookbook.stem, cfg, dry_run=False, verbose=False)
        except VaultchefError as exc:
            self._set_status(str(exc))
            return
        self._set_status(f"Built {result.pdf}")
        self.app.exit()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)


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
