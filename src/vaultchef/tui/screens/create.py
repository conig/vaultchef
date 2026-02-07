from __future__ import annotations

from ...templates import render_cookbook_note
from ..common import (
    apply_centered_card_width,
    current_layout_mode,
    header_icon,
    set_hidden,
    sync_screen_layout,
)
from ..data_sources import embed_path_for_recipe, fuzzy_filter
from ..layout import use_create_wizard
from ..state import RecipeInfo
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
from ..widgets.list_utils import clear_list, highlighted_item


class CreateCookbookScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.selected: list[RecipeInfo] = []
        self.tag_filter: str | None = None
        self.search_query: str = ""
        self._wizard_mode = False
        self._wizard_step = 0

    def compose(self) -> ComposeResult:
        yield Header(icon=header_icon(self))
        with Vertical(id="create-shell", classes="screen-shell"):
            with Vertical(id="create-card", classes="screen-card"):
                with Vertical(id="create-name-group"):
                    yield Label("Cookbook name")
                    yield Input(placeholder="Family Cookbook", id="name-input")

                with Horizontal(id="create-lists"):
                    with Vertical(id="picker-panel"):
                        yield Label("Filter tags")
                        yield ListView(id="tag-list")
                        yield Label("Recipes")
                        yield Input(placeholder="Search recipes", id="search-input")
                        yield ListView(id="recipe-list")
                    with Vertical(id="selected-panel"):
                        yield Label("Selected")
                        yield ListView(id="selected-list")

                with Horizontal(id="wizard-nav"):
                    yield Button("Previous", id="step-prev")
                    yield Static("", id="step-indicator")
                    yield Button("Next", id="step-next", variant="primary")

                with Horizontal(id="create-actions"):
                    yield Button("Create cookbook", id="create", variant="primary")
                    yield Button("Back", id="back")
                yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_tags()
        self._refresh_recipes()
        self._refresh_selected()
        self._refresh_layout_mode(force=True)
        self.query_one("#name-input", Input).focus()

    def on_resize(self, event) -> None:
        self._refresh_layout_mode()

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
        elif event.button.id == "step-next":
            self._next_step()
        elif event.button.id == "step-prev":
            self._prev_step()

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
        if self._wizard_mode and event.key in ("n", "N"):
            self._next_step()
            event.stop()
            return
        if self._wizard_mode and event.key in ("p", "P"):
            self._prev_step()
            event.stop()
            return
        if isinstance(focused, Input):
            if focused.id == "search-input" and event.key in ("down", "up"):
                delta = 1 if event.key == "down" else -1
                self._move_highlight_in(self.query_one("#recipe-list", ListView), delta)
                event.stop()
                return
            if self._wizard_mode and focused.id == "name-input" and event.key in ("enter",):
                self._next_step()
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
        order = self._focus_order()
        if not order:
            return
        focused = self.app.focused
        if focused in order:
            idx = order.index(focused)
            next_idx = (idx + direction) % len(order)
        else:
            next_idx = 0
        order[next_idx].focus()

    def _focus_order(self) -> list[object]:
        if self._wizard_mode:
            if self._wizard_step == 0:
                return [
                    self.query_one("#name-input", Input),
                    self.query_one("#step-next", Button),
                    self.query_one("#back", Button),
                ]
            if self._wizard_step == 1:
                return [
                    self.query_one("#tag-list", ListView),
                    self.query_one("#search-input", Input),
                    self.query_one("#recipe-list", ListView),
                    self.query_one("#step-prev", Button),
                    self.query_one("#step-next", Button),
                    self.query_one("#back", Button),
                ]
            return [
                self.query_one("#selected-list", ListView),
                self.query_one("#step-prev", Button),
                self.query_one("#create", Button),
                self.query_one("#back", Button),
            ]

        return [
            self.query_one("#name-input", Input),
            self.query_one("#tag-list", ListView),
            self.query_one("#search-input", Input),
            self.query_one("#recipe-list", ListView),
            self.query_one("#selected-list", ListView),
            self.query_one("#create", Button),
            self.query_one("#back", Button),
        ]

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

    def _activate_focused(self) -> None:
        focused = self.app.focused
        if isinstance(focused, ListView):
            item = highlighted_item(focused)
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
        clear_list(tag_list)
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
            recipes = fuzzy_filter(recipes, self.search_query, lambda r: r.title)

        recipe_list = self.query_one("#recipe-list", ListView)
        clear_list(recipe_list)

        if not recipes:
            recipe_list.append(ListItem(Label("No recipes found")))
            return

        for recipe in recipes:
            item = ListItem(Label(recipe.display(recipe in self.selected)))
            item.recipe = recipe
            recipe_list.append(item)

    def _refresh_selected(self) -> None:
        selected_list = self.query_one("#selected-list", ListView)
        clear_list(selected_list)
        if not self.selected:
            selected_list.append(ListItem(Label("No recipes selected yet")))
            return
        for recipe in self.selected:
            selected_list.append(ListItem(Label(f"- {recipe.title}")))

    def _refresh_layout_mode(self, *, force: bool = False) -> None:
        sync_screen_layout(self)
        apply_centered_card_width(self, "#create-card")

        mode = current_layout_mode(self)
        height = int(getattr(getattr(self, "size", None), "height", 0) or 0)
        wizard = use_create_wizard(mode, height)
        changed = force or wizard != self._wizard_mode
        if changed:
            self._wizard_mode = wizard
            self._wizard_step = 0
        self._apply_wizard_state()
        if changed:
            self._focus_for_wizard_step()

    def _apply_wizard_state(self) -> None:
        wizard_nav = self.query_one("#wizard-nav", Horizontal)
        create_lists = self.query_one("#create-lists", Horizontal)
        name_group = self.query_one("#create-name-group", Vertical)
        picker_panel = self.query_one("#picker-panel", Vertical)
        selected_panel = self.query_one("#selected-panel", Vertical)
        step_indicator = self.query_one("#step-indicator", Static)
        prev_button = self.query_one("#step-prev", Button)
        next_button = self.query_one("#step-next", Button)
        create_button = self.query_one("#create", Button)

        if not self._wizard_mode:
            set_hidden(wizard_nav, True)
            set_hidden(name_group, False)
            set_hidden(create_lists, False)
            set_hidden(picker_panel, False)
            set_hidden(selected_panel, False)
            set_hidden(create_button, False)
            step_indicator.update("")
            return

        set_hidden(wizard_nav, False)
        if self._wizard_step == 0:
            set_hidden(name_group, False)
            set_hidden(create_lists, True)
            set_hidden(picker_panel, True)
            set_hidden(selected_panel, True)
            set_hidden(create_button, True)
            set_hidden(prev_button, True)
            set_hidden(next_button, False)
            step_indicator.update("Step 1/3  Name")
            return

        if self._wizard_step == 1:
            set_hidden(name_group, True)
            set_hidden(create_lists, False)
            set_hidden(picker_panel, False)
            set_hidden(selected_panel, True)
            set_hidden(create_button, True)
            set_hidden(prev_button, False)
            set_hidden(next_button, False)
            step_indicator.update("Step 2/3  Pick recipes")
            return

        set_hidden(name_group, True)
        set_hidden(create_lists, False)
        set_hidden(picker_panel, True)
        set_hidden(selected_panel, False)
        set_hidden(create_button, False)
        set_hidden(prev_button, False)
        set_hidden(next_button, True)
        step_indicator.update("Step 3/3  Review")

    def _next_step(self) -> None:
        if not self._wizard_mode:
            return
        self._wizard_step = min(2, self._wizard_step + 1)
        self._apply_wizard_state()
        self._focus_for_wizard_step()

    def _prev_step(self) -> None:
        if not self._wizard_mode:
            return
        self._wizard_step = max(0, self._wizard_step - 1)
        self._apply_wizard_state()
        self._focus_for_wizard_step()

    def _focus_for_wizard_step(self) -> None:
        if not self._wizard_mode:
            return
        if self._wizard_step == 0:
            self.query_one("#name-input", Input).focus()
            return
        if self._wizard_step == 1:
            self.query_one("#recipe-list", ListView).focus()
            return
        selected_list = self.query_one("#selected-list", ListView)
        if selected_list.children:
            selected_list.focus()
            return
        self.query_one("#create", Button).focus()

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
