from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from .build import build_cookbook
from .config import resolve_config, config_to_toml
from .errors import (
    VaultchefError,
    ConfigError,
    MissingFileError,
    ValidationError,
    PandocError,
    WatchError,
)
from .listing import list_recipes
from .templates import (
    render_recipe_template,
    render_cookbook_template,
    write_template_file,
)
from .watch import watch_cookbook


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.tui:
        return _cmd_tui(args)
    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "build":
            return _cmd_build(args)
        if args.command == "list":
            return _cmd_list(args)
        if args.command == "watch":
            return _cmd_watch(args)
        if args.command == "new-recipe":
            return _cmd_new_recipe(args)
        if args.command == "new-cookbook":
            return _cmd_new_cookbook(args)
        if args.command == "init":
            return _cmd_init(args)
        if args.command == "config":
            return _cmd_config(args)
    except VaultchefError as exc:
        print(str(exc), file=sys.stderr)
        return _exit_code(exc)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(str(exc), file=sys.stderr)
        return 1
    return 0  # pragma: no cover


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", dest="vault_path")
    common.add_argument("--project")
    common.add_argument("--profile")
    common.add_argument("--pandoc", dest="pandoc_path")
    common.add_argument("--pdf-engine", dest="pdf_engine")
    common.add_argument("--template")
    common.add_argument("--lua-filter", dest="lua_filter")
    common.add_argument("--style-dir", dest="style_dir")
    common.add_argument("--theme")
    common.add_argument("--recipes-dir")
    common.add_argument("--cookbooks-dir")
    common.add_argument("--build-dir")
    common.add_argument("--cache-dir")

    parser = argparse.ArgumentParser(prog="vaultchef", parents=[common])
    parser.add_argument("--tui", action="store_true", help="Launch interactive TUI")
    sub = parser.add_subparsers(dest="command")

    build = sub.add_parser("build", parents=[common])
    build.add_argument("cookbook_name")
    build.add_argument("--open", action="store_true")
    build.add_argument("--dry-run", action="store_true")
    build.add_argument("--verbose", action="store_true")

    listing = sub.add_parser("list", parents=[common])
    listing.add_argument("--tag")
    listing.add_argument("--category")
    listing.add_argument("--json", action="store_true")

    watch = sub.add_parser("watch", parents=[common])
    watch.add_argument("cookbook_name")
    watch.add_argument("--debounce", type=int, default=400)
    watch.add_argument("--verbose", action="store_true")

    new_recipe = sub.add_parser("new-recipe")
    new_recipe.add_argument("--id", required=True)
    new_recipe.add_argument("--title", required=True)
    new_recipe.add_argument("--course")
    new_recipe.add_argument("--category")
    new_recipe.add_argument("--cuisine")
    new_recipe.add_argument("--serves")
    new_recipe.add_argument("--prep")
    new_recipe.add_argument("--cook")
    new_recipe.add_argument("--rest")
    new_recipe.add_argument("--menu")
    new_recipe.add_argument("--source")

    new_cookbook = sub.add_parser("new-cookbook")
    new_cookbook.add_argument("--title", required=True)
    new_cookbook.add_argument("--subtitle")
    new_cookbook.add_argument("--author")
    new_cookbook.add_argument("--style")

    init = sub.add_parser("init")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--force", action="store_true")

    config = sub.add_parser("config", parents=[common])

    return parser


def _cmd_build(args: argparse.Namespace) -> int:
    cfg = resolve_config(_cli_args_dict(args))
    result = build_cookbook(args.cookbook_name, cfg, dry_run=args.dry_run, verbose=args.verbose)
    if args.open and not args.dry_run:
        _open_file(str(result.pdf))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    cfg = resolve_config(_cli_args_dict(args))
    recipes = list_recipes(cfg, args.tag, args.category)
    if args.json:
        print(json.dumps(recipes, indent=2))
    else:
        for rec in recipes:
            print(f"{rec.get('recipe_id')}: {rec.get('title')}")
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    cfg = resolve_config(_cli_args_dict(args))
    watch_cookbook(args.cookbook_name, cfg, debounce_ms=args.debounce, verbose=args.verbose)
    return 0


def _cmd_new_recipe(args: argparse.Namespace) -> int:
    content = render_recipe_template(
        args.id,
        args.title,
        course=args.course,
        category=args.category,
        cuisine=args.cuisine,
        serves=args.serves,
        prep=args.prep,
        cook=args.cook,
        rest=args.rest,
        menu=args.menu,
        source=args.source,
    )
    filename = f"{args.title}.md"
    path = write_template_file(content, filename, os.getcwd())
    print(path)
    return 0


def _cmd_new_cookbook(args: argparse.Namespace) -> int:
    content = render_cookbook_template(
        args.title,
        subtitle=args.subtitle,
        author=args.author,
        style=args.style,
    )
    filename = f"{args.title}.md"
    path = write_template_file(content, filename, os.getcwd())
    print(path)
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.path)
    os.makedirs(root, exist_ok=True)
    _ensure_dir(root, "templates")
    _ensure_dir(root, "filters")
    _ensure_dir(root, "build")
    _ensure_dir(root, "cache")
    config_path = os.path.join(root, "vaultchef.toml")
    if os.path.exists(config_path) and not args.force:
        raise ConfigError(f"{config_path} already exists (use --force to overwrite)")
    with open(config_path, "w", encoding="utf-8") as fh:
        fh.write("""build_dir = \"build\"\ncache_dir = \"cache\"\n\n[pandoc]\n# template = \"templates/cookbook.tex\"\n# lua_filter = \"filters/recipe.lua\"\n# style_dir = \"templates\"\n\n[style]\n# theme = \"menu-card\"\n""")
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    cfg = resolve_config(_cli_args_dict(args))
    print(config_to_toml(cfg))
    return 0


def _cmd_tui(args: argparse.Namespace) -> int:
    from .tui import run_tui

    return run_tui(_cli_args_dict(args))


def _ensure_dir(root: str, name: str) -> None:
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)


def _cli_args_dict(args: argparse.Namespace) -> dict[str, object]:
    data = vars(args).copy()
    return data


def _open_file(path: str) -> None:
    try:
        subprocess.run(["xdg-open", path], check=False)
    except Exception as exc:
        raise ConfigError("Failed to open PDF") from exc


def _exit_code(exc: VaultchefError) -> int:
    if isinstance(exc, ConfigError):
        return 2
    if isinstance(exc, MissingFileError):
        return 3
    if isinstance(exc, ValidationError):
        return 4
    if isinstance(exc, PandocError):
        return 5
    if isinstance(exc, WatchError):
        return 6
    return 1
