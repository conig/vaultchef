from __future__ import annotations

import pytest

from vaultchef.validate import validate_recipe, extract_sections
from vaultchef.errors import ValidationError


def test_validate_recipe_ok() -> None:
    md = """---
recipe_id: 1
title: Test
---

## Ingredients
- a

## Method
1. b
"""
    validate_recipe(md, "recipe.md")


def test_validate_missing_frontmatter() -> None:
    md = "## Ingredients\n- a\n\n## Method\n1. b\n"
    with pytest.raises(ValidationError):
        validate_recipe(md, "recipe.md")


def test_validate_invalid_yaml() -> None:
    md = "---\n[invalid\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n"
    with pytest.raises(ValidationError):
        validate_recipe(md, "recipe.md")


def test_validate_frontmatter_not_mapping() -> None:
    md = "---\n- a\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n"
    with pytest.raises(ValidationError):
        validate_recipe(md, "recipe.md")


def test_validate_missing_keys() -> None:
    md = "---\nrecipe_id: 1\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n"
    with pytest.raises(ValidationError):
        validate_recipe(md, "recipe.md")


def test_validate_missing_sections() -> None:
    md = "---\nrecipe_id: 1\ntitle: Test\n---\n\n## Ingredients\n- a\n"
    with pytest.raises(ValidationError):
        validate_recipe(md, "recipe.md")


def test_validate_missing_bullets() -> None:
    md = "---\nrecipe_id: 1\ntitle: Test\n---\n\n## Ingredients\nno bullets\n\n## Method\n1. b\n"
    with pytest.raises(ValidationError):
        validate_recipe(md, "recipe.md")


def test_validate_missing_method_steps() -> None:
    md = "---\nrecipe_id: 1\ntitle: Test\n---\n\n## Ingredients\n- a\n\n## Method\nno steps\n"
    with pytest.raises(ValidationError):
        validate_recipe(md, "recipe.md")


def test_extract_sections() -> None:
    md = "## Ingredients\n- a\n\n## Method\n1. b\n"
    sections = extract_sections(md)
    assert "Ingredients" in sections
    assert "Method" in sections
