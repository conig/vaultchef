# vaultchef

vaultchef is a terminal-only cookbook builder that turns an Obsidian vault of Markdown recipe notes into a polished PDF.

## Core promise

- Write recipes as plain `.md` notes in an Obsidian vault.
- Curate a cookbook using a single “Cookbook note” with `![[...]]` embeds.
- Run one command to generate a PDF.
- Never write generated files into the vault.

## Quick start (example vault)

This repo ships with a tiny example vault in `fixtures/VaultExample`.

```bash
vaultchef build "Family Cookbook" --vault fixtures/VaultExample --project . --dry-run
```

If you have pandoc and LaTeX installed, run a real build:

```bash
vaultchef build "Family Cookbook" --vault fixtures/VaultExample --project .
```

Outputs land in `./build/`.

## CLI

```bash
vaultchef --tui
vaultchef build "Family Cookbook" [--vault PATH] [--project PATH] [--profile NAME] [--open] [--dry-run]
vaultchef list [--vault PATH] [--tag TAG] [--category CATEGORY] [--json]
vaultchef watch "Family Cookbook" [--vault PATH] [--project PATH] [--profile NAME]
vaultchef new-recipe --id 116 --title "Lemon Tart"
vaultchef new-cookbook --title "Family Cookbook"
vaultchef init [PATH] [--force]
vaultchef config [--vault PATH] [--project PATH] [--profile NAME]
vaultchef tex-check [--pdf-engine ENGINE]
```

## Config

Global config lives at `~/.config/vaultchef/config.toml`.
Project config lives at `<project>/vaultchef.toml`.

Precedence:

1. CLI flags
2. Project config
3. Global config
4. Defaults

Example global config:

```toml
vault_path = "/home/james/Obsidian/Vault"
recipes_dir = "Recipes"
cookbooks_dir = "Cookbooks"
tex_check = true

default_project = "/home/james/CookbookProject"

[pandoc]
pdf_engine = "lualatex"
template = "templates/cookbook.tex"
lua_filter = "filters/recipe.lua"
style_dir = "templates"
```

## Authoring format

Recipe notes require frontmatter with `recipe_id` and `title`, and must include:

- `## Ingredients`
- `## Method`

Cookbook notes contain headings and embeds like:

```markdown
# Desserts
![[Recipes/116 Lemon Tart]]
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```
