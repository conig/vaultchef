# vaultchef

vaultchef is a terminal-only cookbook builder that turns an Obsidian vault of Markdown recipe notes into a polished PDF or publish-ready HTML.

## Core promise

- Write recipes as plain `.md` notes in an Obsidian vault.
- Curate a cookbook using a single “Cookbook note” with `![[...]]` embeds.
- Run one command to generate a PDF or web-ready HTML.
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

Build a web version suitable for a personal site:

```bash
vaultchef build "Family Cookbook" --vault fixtures/VaultExample --project . --format web
```

Intermediate outputs land in `./build/`, and the final `.pdf` or `.html` is copied to your current working directory.
The web template is responsive for desktop and phone screens (including Pixel 8 Pro-class widths).

## CLI

```bash
vaultchef            # launches TUI by default
vaultchef --tui
vaultchef --tui-layout auto|compact|normal|wide --tui-density cozy|compact --tui-mode-animation auto|on|off
vaultchef build "Family Cookbook" [--vault PATH] [--project PATH] [--profile NAME] [--format pdf|web] [--open] [--dry-run]
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
Optional profiles live at `~/.config/vaultchef/projects.d/<name>.toml`.

Precedence:

1. CLI flags
2. Project config
3. Global config
4. Defaults

### Options (all keys)

Top-level keys:

- `vault_path` (required): absolute path to your Obsidian vault.
- `recipes_dir` (default: `"Recipes"`): recipes folder inside the vault.
- `cookbooks_dir` (default: `"Cookbooks"`): cookbooks folder inside the vault.
- `default_project` (optional): project dir used when `--project` and `--profile` are not provided.
- `build_dir` (default: `"build"`): build output folder inside the project.
- `cache_dir` (default: `"cache"`): cache folder inside the project.
- `tex_check` (default: `true`): run TeX dependency check at startup.
- `tui_header_icon` (default: `"🔪"`): icon used in the TUI header.
- `tui_layout` (default: `"auto"`): `auto` or fixed `compact`/`normal`/`wide` TUI layout.
- `tui_density` (default: `"cozy"`): spacing density (`cozy` or `compact`).
- `tui_mode_animation` (default: `"auto"`): front-page hero animation behavior (`auto`, `on`, `off`).

`[pandoc]` table:

- `pdf_engine` (default: `"lualatex"`): LaTeX engine for PDF output.
- `template` (default: `"templates/cookbook.tex"`): LaTeX template path (relative to project).
- `lua_filter` (default: `"filters/recipe.lua"`): Lua filter path (relative to project).
- `style_dir` (default: `"templates"`): directory of LaTeX styles/macros (relative to project).
- `pandoc_path` (default: `"pandoc"`): pandoc binary name or full path.

`[style]` table:

- `theme` (default: `"menu-card"`): semantic theme name.

Profile file (optional):

- `project` (required): absolute path to the project directory for the profile.

### Example global config

Global config is a good place for your vault location and defaults that apply to all projects.

```toml
vault_path = "/home/user/Obsidian/Vault"
recipes_dir = "Recipes"
cookbooks_dir = "Cookbooks"
tex_check = true
tui_header_icon = "🔪"
tui_layout = "auto"
tui_density = "cozy"
tui_mode_animation = "auto"

default_project = "/home/user/CookbookProject"

[pandoc]
pdf_engine = "lualatex"
template = "templates/cookbook.tex"
lua_filter = "filters/recipe.lua"
style_dir = "templates"
pandoc_path = "pandoc"

[style]
theme = "menu-card"
```

### Example project config

Project config is a good place for build locations and template overrides.

```toml
build_dir = "build"
cache_dir = "cache"

[pandoc]
template = "templates/cookbook.tex"
lua_filter = "filters/recipe.lua"
style_dir = "templates"

[style]
theme = "menu-card"
```

### Example profile config

Profiles map a short name to a project directory.

```toml
project = "/home/user/CookbookProject"
```

## Authoring format

Recipe notes require frontmatter with `recipe_id` and `title`, and must include:

- `## Ingredients`
- `## Method`

Optional frontmatter:

- `image` (path to a hero image placed between the title and ingredients)

Cookbook notes contain headings and embeds like:

```markdown
# Desserts

![[Recipes/116 Lemon Tart]]
```

Cookbook frontmatter also supports intro/music metadata:

- `include_intro_page` (bool, opt-in intro page before recipes)
- `include_title_page` (legacy alias for `include_intro_page`)
- `album_title`, `album_artist`, `album_style` (music pairing metadata)
- `album_youtube_url` (optional YouTube/YouTube Music URL for a web play button)

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```
