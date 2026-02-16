from __future__ import annotations

from fractions import Fraction
import pytest

from vaultchef.errors import ShoppingParseError
from vaultchef.shopping import (
    ShoppingItem,
    _aggregate_items,
    _assert_item_representation,
    _format_quantity,
    _parse_ingredient_line,
    _parse_quantity,
    _shopping_line_key,
    build_shopping_list,
)


# Purpose: verify shopping list merges compatible units.
def test_build_shopping_list_merges_compatible_units() -> None:
    recipes = [
        (
            "Recipes/One.md",
            """---
recipe_id: 1
title: One
---

## Ingredients
- 1 tbsp olive oil
- 120 g butter (80 g pastry, 40 g filling)

## Method
1. Cook.
""",
        ),
        (
            "Recipes/Two.md",
            """---
recipe_id: 2
title: Two
---

## Ingredients
- 2 tablespoons olive oil
- 80 g butter

## Method
1. Cook.
""",
        ),
    ]
    shopping = build_shopping_list(recipes)
    assert "3 tbsp olive oil" in shopping
    assert "200 g butter" in shopping


# Purpose: verify shopping list keeps incompatible units separate.
def test_build_shopping_list_keeps_incompatible_units() -> None:
    recipes = [
        (
            "Recipes/One.md",
            """---
recipe_id: 1
title: One
---

## Ingredients
- 100 g sugar

## Method
1. Mix.
""",
        ),
        (
            "Recipes/Two.md",
            """---
recipe_id: 2
title: Two
---

## Ingredients
- 1 cup sugar

## Method
1. Mix.
""",
        ),
    ]
    shopping = build_shopping_list(recipes)
    assert "100 g sugar" in shopping
    assert "1 cup sugar" in shopping


# Purpose: verify shopping parser rejects non-bullet ingredient lines.
def test_shopping_parser_rejects_non_bullet_lines() -> None:
    recipes = [
        (
            "Recipes/Bad.md",
            """---
recipe_id: 1
title: Bad
---

## Ingredients
- salt to taste
not-a-bullet

## Method
1. Mix.
""",
        ),
    ]
    with pytest.raises(ShoppingParseError, match="is not a bullet"):
        build_shopping_list(recipes)


# Purpose: verify shopping parser allows blank spacer lines in ingredients.
def test_shopping_parser_allows_blank_lines() -> None:
    recipes = [
        (
            "Recipes/Blank.md",
            """---
recipe_id: 1
title: Blank
---

## Ingredients
- 1 cup milk

- 2 tbsp sugar

## Method
1. Mix.
""",
        ),
    ]
    shopping = build_shopping_list(recipes)
    assert "1 cup milk" in shopping
    assert "2 tbsp sugar" in shopping


# Purpose: verify shopping parser rejects unparseable ingredient name.
def test_shopping_parser_rejects_unparseable_name() -> None:
    with pytest.raises(ShoppingParseError, match="no parseable ingredient name"):
        _parse_ingredient_line("(garnish)", "Recipes/Bad.md", 2)


# Purpose: verify shopping parser rejects empty ingredient line.
def test_shopping_parser_rejects_empty_line() -> None:
    with pytest.raises(ShoppingParseError, match="is empty"):
        _parse_ingredient_line("", "Recipes/Bad.md", 3)


# Purpose: verify shopping parser helper branches.
def test_shopping_parser_helpers() -> None:
    parsed = _parse_ingredient_line("1.5 sugar", "Recipes/One.md", 1)
    assert parsed is not None
    assert parsed.quantity == Fraction(3, 2)
    assert parsed.name == "sugar"

    assert _format_quantity(Fraction(1, 2)) == "1/2"
    assert _format_quantity(Fraction(3, 2)) == "1 1/2"

    assert _parse_quantity("") is None
    assert _parse_quantity("1 1/2") == Fraction(3, 2)
    assert _parse_quantity("x 1/2") is None
    assert _parse_quantity("1/2") == Fraction(1, 2)
    assert _parse_quantity("1/0") is None
    assert _parse_quantity("abc") is None

    lines = _aggregate_items(
        [
            ShoppingItem(
                quantity=None,
                unit=None,
                name="pinch salt",
                key="pinch salt",
                source_path="Recipes/A.md",
                line_number=1,
            ),
            ShoppingItem(
                quantity=None,
                unit=None,
                name="pinch salt",
                key="pinch salt",
                source_path="Recipes/A.md",
                line_number=2,
            ),
            ShoppingItem(
                quantity=Fraction(2, 1),
                unit=None,
                name="eggs",
                key="eggs",
                source_path="Recipes/A.md",
                line_number=3,
            ),
        ]
    )
    assert "pinch salt" in lines
    assert "2 eggs" in lines


# Purpose: verify item representation assertion fails when item key missing.
def test_shopping_item_representation_check() -> None:
    items = [
        ShoppingItem(
            quantity=Fraction(1, 1),
            unit="tbsp",
            name="olive oil",
            key="olive oil",
            source_path="Recipes/Test.md",
            line_number=4,
        )
    ]
    with pytest.raises(ShoppingParseError, match="not represented in shopping list"):
        _assert_item_representation(items, ["1 tbsp butter"])
    assert _shopping_line_key("3 tbsp olive oil") == "olive oil"
    assert _shopping_line_key("2 handful spinach") == "handful spinach"
    assert _shopping_line_key("olive oil") == "olive oil"
    assert _shopping_line_key("   ") == ""


# Purpose: verify shopping list is sorted alphabetically by ingredient key.
def test_shopping_list_alphabetical_order() -> None:
    recipes = [
        (
            "Recipes/R1.md",
            """---
recipe_id: 1
title: R1
---

## Ingredients
- 1 cup flour
- 1 tbsp olive oil

## Method
1. Mix.
""",
        ),
        (
            "Recipes/R2.md",
            """---
recipe_id: 2
title: R2
---

## Ingredients
- 230 g flour
- 2 tbsp basil

## Method
1. Mix.
""",
        ),
    ]
    shopping = build_shopping_list(recipes)
    assert shopping == [
        "2 tbsp basil",
        "1 cup flour",
        "230 g flour",
        "1 tbsp olive oil",
    ]
