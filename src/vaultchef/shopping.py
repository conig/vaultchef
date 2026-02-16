from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re

from .domain import extract_sections, split_frontmatter
from .errors import ShoppingParseError


BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
QUANTITY_RE = re.compile(r"^(?P<qty>\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\b\s*(?P<rest>.*)$")
PARENS_RE = re.compile(r"\s*\([^)]*\)\s*")
SPACE_RE = re.compile(r"\s+")

UNIT_ALIASES = {
    "tsp": "tsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tbsp": "tbsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "l": "l",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "cup": "cup",
    "cups": "cup",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "clove": "clove",
    "cloves": "clove",
    "can": "can",
    "cans": "can",
    "tin": "can",
    "tins": "can",
    "packet": "packet",
    "packets": "packet",
}


@dataclass
class ShoppingItem:
    quantity: Fraction | None
    unit: str | None
    name: str
    key: str
    source_path: str
    line_number: int


def build_shopping_list(recipe_documents: list[tuple[str, str]]) -> list[str]:
    items: list[ShoppingItem] = []
    for source_path, recipe_md in recipe_documents:
        items.extend(_extract_ingredient_items(recipe_md, source_path))
    lines = _aggregate_items(items)
    _assert_item_representation(items, lines)
    return lines


def _extract_ingredient_items(recipe_md: str, source_path: str) -> list[ShoppingItem]:
    doc = split_frontmatter(recipe_md)
    sections = extract_sections(doc.body)
    ingredients = sections.get("Ingredients", "")
    items: list[ShoppingItem] = []
    for idx, line in enumerate(ingredients.splitlines(), start=1):
        match = BULLET_RE.match(line)
        if not match:
            if line.strip():
                raise ShoppingParseError(
                    f"{source_path}: ingredients line {idx} is not a bullet: {line.strip()!r}"
                )
            continue
        parsed = _parse_ingredient_line(match.group(1), source_path, idx)
        if parsed:
            items.append(parsed)
    return items


def _parse_ingredient_line(line: str, source_path: str, line_number: int) -> ShoppingItem | None:
    text = line.strip()
    if not text:
        raise ShoppingParseError(f"{source_path}: ingredients line {line_number} is empty")

    qty: Fraction | None = None
    unit: str | None = None
    name = text

    match = QUANTITY_RE.match(text)
    if match:
        qty = _parse_quantity(match.group("qty"))
        rest = match.group("rest").strip()
        if rest:
            token, _, tail = rest.partition(" ")
            candidate = _normalize_unit(token)
            if candidate and tail.strip():
                unit = candidate
                name = tail.strip()
            else:
                name = rest

    name_key = _normalize_name(name)
    if not name_key:
        raise ShoppingParseError(
            f"{source_path}: ingredients line {line_number} has no parseable ingredient name: {text!r}"
        )
    return ShoppingItem(
        quantity=qty,
        unit=unit,
        name=_display_name(name),
        key=name_key,
        source_path=source_path,
        line_number=line_number,
    )


def _aggregate_items(items: list[ShoppingItem]) -> list[str]:
    merged: dict[tuple[str, str, bool], ShoppingItem] = {}
    for item in items:
        bucket = (item.key, item.unit or "", item.quantity is None)

        if bucket not in merged:
            merged[bucket] = ShoppingItem(
                quantity=item.quantity,
                unit=item.unit,
                name=item.name,
                key=item.key,
                source_path=item.source_path,
                line_number=item.line_number,
            )
            continue

        existing = merged[bucket]
        if existing.quantity is not None and item.quantity is not None:
            existing.quantity += item.quantity

    lines: list[str] = []
    sorted_items = sorted(
        merged.values(),
        key=lambda item: (item.key, item.unit or "", item.name.lower()),
    )
    for item in sorted_items:
        lines.append(_format_item(item))
    return lines


def _format_item(item: ShoppingItem) -> str:
    if item.quantity is None:
        return item.name
    qty = _format_quantity(item.quantity)
    if item.unit:
        return f"{qty} {item.unit} {item.name}"
    return f"{qty} {item.name}"


def _format_quantity(quantity: Fraction) -> str:
    if quantity.denominator == 1:
        return str(quantity.numerator)

    whole = quantity.numerator // quantity.denominator
    remainder = quantity - whole
    if whole == 0:
        return f"{remainder.numerator}/{remainder.denominator}"
    return f"{whole} {remainder.numerator}/{remainder.denominator}"


def _parse_quantity(text: str) -> Fraction | None:
    text = text.strip()
    if not text:
        return None

    if " " in text and "/" in text:
        whole_text, frac_text = text.split(" ", 1)
        whole = _parse_quantity(whole_text)
        frac = _parse_quantity(frac_text)
        if whole is None or frac is None:
            return None
        return whole + frac

    if "/" in text:
        num_text, den_text = text.split("/", 1)
        try:
            return Fraction(int(num_text), int(den_text))
        except (ValueError, ZeroDivisionError):
            return None

    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return Fraction(number).limit_denominator(16)


def _normalize_unit(token: str) -> str | None:
    cleaned = token.strip().lower().rstrip(".,")
    return UNIT_ALIASES.get(cleaned)


def _normalize_name(text: str) -> str:
    lowered = text.strip().lower()
    lowered = PARENS_RE.sub(" ", lowered)
    lowered = lowered.strip(" ,.;:")
    return SPACE_RE.sub(" ", lowered).strip()


def _display_name(text: str) -> str:
    clean = PARENS_RE.sub(" ", text).strip(" ,.;:")
    return SPACE_RE.sub(" ", clean).strip()


def _assert_item_representation(items: list[ShoppingItem], lines: list[str]) -> None:
    output_keys = {_shopping_line_key(line) for line in lines}
    for item in items:
        if item.key not in output_keys:
            raise ShoppingParseError(
                f"{item.source_path}: ingredients line {item.line_number} not represented in shopping list: {item.name!r}"
            )


def _shopping_line_key(line: str) -> str:
    text = line.strip()
    if not text:
        return ""

    match = QUANTITY_RE.match(text)
    if match:
        rest = match.group("rest").strip()
        if rest:
            token, _, tail = rest.partition(" ")
            candidate = _normalize_unit(token)
            if candidate and tail.strip():
                return _normalize_name(tail.strip())
            return _normalize_name(rest)
    return _normalize_name(text)
