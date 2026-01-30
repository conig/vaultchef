from __future__ import annotations

from pathlib import Path
import pytest

from vaultchef.templates import (
    render_recipe_template,
    render_cookbook_template,
    render_cookbook_note,
    write_template_file,
)


def test_render_recipe_template() -> None:
    text = render_recipe_template("1", "Test", course="dessert")
    assert "recipe_id" in text
    assert "## Ingredients" in text
    assert "course: dessert" in text


def test_render_cookbook_template() -> None:
    text = render_cookbook_template("My Book", subtitle="Sub", author="A", style="menu-card")
    assert "title: My Book" in text
    assert "subtitle: Sub" in text
    assert "![[Recipes/Example Recipe]]" in text


def test_render_cookbook_note() -> None:
    text = render_cookbook_note("My Book", ["Recipes/One", "Recipes/Two"])
    assert "title: My Book" in text
    assert "![[Recipes/One]]" in text


def test_write_template_file(tmp_path: Path) -> None:
    path = write_template_file("content", "file.md", str(tmp_path))
    assert Path(path).exists()
    with pytest.raises(FileExistsError):
        write_template_file("content", "file.md", str(tmp_path))
