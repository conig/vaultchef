# vaultchef

vaultchef is a terminal-only cookbook builder that turns an Obsidian vault of Markdown recipe notes into a polished PDF that reads somewhere between a restaurant menu and a recipe book.

The vault stays user-managed and clean.
All build tooling, LaTeX templates, filters, and caches live outside the vault in a separate project directory. Intermediate build outputs live in the project build dir, while the final PDF is copied to the current working directory.

## Core promise

- Write recipes as plain `.md` notes in an Obsidian vault.
- Curate a cookbook using a single “Cookbook note” that embeds recipes with `![[...]]`.
- Run one command in a terminal to generate a beautiful PDF.
- Never write generated artifacts into the vault.

## Non-goals

- No GUI dependencies for authoring or building.
- No proprietary formats.
- No requirement for Obsidian plugins.
- No attempt to fully parse nutrition, units, or do ingredient scaling in v1.

Scaling and shopping lists can be added later without changing the authoring format.

## Concepts

### Vault (user-managed)

A folder containing the user’s Markdown notes.
The user edits content here via Obsidian, obsidian.nvim, or any editor.

### Project (tool-managed)

A folder containing vaultchef templates, filters, build outputs, and cache.
A single vault can be rendered by multiple projects (different styles or audiences).

### Intermediates

All intermediate files should be written into /tmp. Only the resultant PDF should appear in the working directory.

### Cookbook note

A Markdown note that acts as the table of contents.
It contains chapters and Obsidian embeds that reference recipe notes.

### Recipe note

A Markdown note with YAML frontmatter plus standard sections for ingredients and method.

## Directory structure

### Example vault

```
Vault/
  Recipes/
    116 Lemon Tart.md
    118 Anzac Biscuits.md
    205 Saag Paneer.md
  Cookbooks/
    Family Cookbook.md
```

### Example project

```
CookbookProject/
  vaultchef.toml
  templates/
    cookbook.tex
    recipe.sty
  filters/
    recipe.lua
  build/
    Family Cookbook.baked.md
    Family Cookbook.tex
    Family Cookbook.pdf
  cache/
    ...
```

## Configuration

vaultchef uses a global user config that points to the vault location and default settings.
Per-project configuration controls style, templates, and build outputs.

### Global config

Path:

- `~/.config/vaultchef/config.toml`

Example:

```toml
vault = "/home/james/Obsidian/Vault"
recipes_dir = "Recipes"
cookbooks_dir = "Cookbooks"

default_project = "/home/james/CookbookProject"

editor = "nvim"
pdf_viewer = "zathura"

[pandoc]
# Optional override if you store templates in user config
template = "cookbook.tex"
style_dir = "~/.config/vaultchef/templates"
```

### Per-project config

Path:

- `<project>/vaultchef.toml`

Example:

```toml
build_dir = "build"
cache_dir = "cache"

[pandoc]
pdf_engine = "lualatex"
template = "templates/cookbook.tex"
lua_filter = "filters/recipe.lua"
style_dir = "templates"

[style]
theme = "menu-card"
```

### User-owned LaTeX templates (optional)

vaultchef supports user-owned templates stored under the user config directory, for example:

```
~/.config/vaultchef/templates/
  cookbook.tex
  recipe.sty
```

This is optional. Defaults live in the project (or bundled with vaultchef).

Guidelines:

- Do not store templates in the vault.
- Prefer user templates for fonts and typography that are specific to the machine.
- Keep macro names and the macro contract stable to avoid breaking the Lua filter.

### Theme vs template

- Theme: semantic layout contract (menu-card, minimal, gift-book). Themes are app-owned and define which macros are required.
- Template: LaTeX presentation (fonts, margins, title page). Templates can be project-owned or user-owned.

The Lua filter should emit semantic macros, and the template should implement their visual appearance.

### Precedence rules

Highest wins:

1. CLI flags
2. Per-project `vaultchef.toml`
3. Global `~/.config/vaultchef/config.toml`
4. Built-in defaults

### Suggested profiles (optional)

If multiple projects exist, optional profiles can be stored at:

- `~/.config/vaultchef/projects.d/*.toml`

Example:
`~/.config/vaultchef/projects.d/gift.toml`

```toml
project = "/home/james/CookbookGiftProject"
```

Usage:

```bash
vaultchef build "Family Cookbook" --profile gift
```

## Authoring format

### Recipe note format

Recipe notes are plain Markdown with YAML frontmatter.

Required frontmatter keys:

- `recipe_id` (string or integer)
- `title` (string)

Recommended frontmatter keys:

- `course` (string, example `dessert`, `main`, `side`, `snack`)
- `category` (string)
- `cuisine` (string)
- `occasion` (string, example `weekday`, `weekend`, `special`)
- `serves` (string)
- `prep` (string, example `25m`)
- `cook` (string, example `35m`)
- `rest` (string, example `2h`)
- dietary flags (booleans): `vegetarian`, `vegan`, `gluten_free`, `dairy_free`
- ratings (numbers): `emma_rating`, `james_rating`
- `difficulty` (integer, example 1 to 5)
- `tags` (list)
- `menu` (one-sentence description for the menu-style header)
- `source` (string)

Notes:

- YAML frontmatter metadata is Obsidian-friendly and safe to add.
- Keep metadata flat and typed (booleans for flags, numbers for ratings).
- Unknown keys must not break the build. vaultchef should ignore what it does not understand.

Required sections:

- `## Ingredients`
- `## Method`

Optional sections:

- `## Notes`

Ingredient subsections can be created with headings under Ingredients:

- `### Filling`
- `### Sauce`

Example:

```markdown
---
recipe_id: 116
title: Lemon tart

course: dessert
cuisine: french
serves: 8
prep: 25m
cook: 35m
rest: 2h

vegetarian: true
vegan: false
gluten_free: false

emma_rating: 4.5
james_rating: 5
difficulty: 2

tags: [citrus, baking]
menu: Bright lemon curd in a buttery shortcrust.
source: Ottolenghi
---

## Ingredients

- 200 g plain flour
- 120 g unsalted butter, cold, cubed

### Filling

- 4 eggs
- 200 g caster sugar

## Method

1. Make the dough.
2. Blind bake the shell.
3. Bake filling until just set.

## Notes

- Serve with whipped cream.
```

### Cookbook note format

A cookbook note is a normal Markdown note in `Cookbooks/` with chapter headings and embeds.
Embeds use Obsidian transclusion syntax:

- `![[Recipes/116 Lemon Tart]]`

Example:

```markdown
---
title: Family Cookbook
subtitle: Weeknight staples and weekend favourites
author: James & Emma
style: menu-card
---

# Desserts

![[Recipes/116 Lemon Tart]]
![[Recipes/118 Anzac Biscuits]]

# Mains

![[Recipes/205 Saag Paneer]]
```

## CLI interface

### Common commands

Build a cookbook:

```bash
vaultchef build "Family Cookbook"
```

Build and open the PDF:

```bash
vaultchef build "Family Cookbook" --open
```

Watch for changes and rebuild:

```bash
vaultchef watch "Family Cookbook"
```

Create a new recipe note from a template:

```bash
vaultchef new --id 116 --title "Lemon Tart" --category Desserts
```

List recipes:

```bash
vaultchef list
vaultchef list --tag dessert
vaultchef list --category Desserts
```

Override locations:

```bash
vaultchef build "Family Cookbook" --vault ~/Obsidian/Vault --project ~/CookbookProject
```

### Outputs

Intermediate outputs go into the project build directory, and the final PDF is copied to the current working directory.

- `<build>/Family Cookbook.baked.md`
  - The cookbook note with embeds expanded into full Markdown.
- `<build>/Family Cookbook.tex`
  - Optional intermediate for debugging LaTeX output.
- `<build>/Family Cookbook.pdf`
  - Intermediate PDF artifact (before copy).
- `./Family Cookbook.pdf`
  - Final artifact in the current working directory.

No generated file should be written into the vault.

### Exit codes (recommended)

- `0` success
- `1` generic failure
- `2` config error
- `3` missing file (cookbook or recipe)
- `4` parse error (frontmatter or required sections)
- `5` pandoc/latex failure
- `6` watch error

## Build pipeline

### Stage 1: Resolve cookbook note

- Locate cookbook note in: `$vault/$cookbooks_dir/<name>.md`
- Parse YAML frontmatter if present.

### Stage 2: Expand embeds

- Replace every `![[...]]` with the embedded file content.
- Support both:
  - `![[Recipes/116 Lemon Tart]]`
  - `![[Recipes/116 Lemon Tart.md]]`
- Optional future support:
  - block references `![[note#^blockid]]`
  - heading embeds `![[note#Heading]]`

Embed expansion should:

- preserve chapter headings in the cookbook note
- ensure each embedded recipe starts at a predictable boundary

### Stage 3: Normalise and validate recipes

Recipe validation rules in v1:

- frontmatter includes `recipe_id` and `title`
- sections include `## Ingredients` and `## Method`
- ingredients contain at least one bullet item
- method contains at least one ordered item

Metadata rules in v1:

- accept arbitrary additional YAML keys
- ignore unknown keys (no failure)
- avoid strict typing enforcement (warn only in verbose mode)

### Stage 4: Convert with Pandoc

Pandoc runs on the baked Markdown.

Recommended approach:

- Use a Lua filter to identify recipe units and emit structured output for LaTeX macros.
- Use a LaTeX template and a style file that implement the menu-card aesthetic.

### Stage 5: LaTeX engine to PDF

Default engine: `lualatex`
Alternatives: `xelatex`

## Styling and semantics

The visual identity aims for:

- menu-style headers
- recipe cards
- dense but readable ingredient lists
- spacious method steps
- optional notes in a shaded panel
- no title page; page 1 must be the first recipe to preserve the two-page pattern per recipe

Recommended macro concepts in `recipe.sty`:

- `\RecipeCard{title}{menu}{meta}{ingredients}{method}{notes}`
- `\RecipeMeta{serves}{prep}{cook}{rest}{total}`
- two-column layout for ingredients and method where possible
- sensible page breaks to avoid splitting ingredients from method

The output cookbook PDF has the following requirements

- No title page unless specified in the cookbook yaml frontmatter (include_title_page :true)
- Each 2-sided page includes exactly one recipe. On the first page is the recipe title, ingredients, and when provided, a description.
- The second page includes the methods and notes.

This is important as it means that when printed, each recipe is on its own sheet of paper that can be handed to a cook who then does not need to search through the book for all relevant information.

## Caching and watch mode

Caching is allowed only in the project cache directory.
No cache files in the vault.

Watch mode should:

- watch the cookbook note
- watch all referenced recipes
- rebuild on changes
- debounce rebuilds (example: 250ms to 500ms)

## Implementation notes for agents

### Minimal viable implementation strategy

1. Implement config loading with precedence rules.
2. Implement cookbook note lookup and embed expansion.
3. Write baked Markdown to build dir.
4. Call pandoc with a working template.
5. Add the Lua filter only after basic PDF generation works.
6. Add watch mode.

### Suggested language choices

- Python is a good fit for fast iteration.
- Go is a good fit for a single static binary.

Either is fine.
The project should keep the authoring format stable.

### Parsing guidance

- Use a real YAML frontmatter parser.
- Keep Markdown parsing minimal until pandoc stage.
- Trust pandoc for most Markdown normalization.

### Logging guidance

- Print friendly errors that name the file and the failing rule.
- Provide a `--verbose` flag that prints command lines and pandoc output.

### Security and safety

- Treat vault files as untrusted input.
- Avoid shell injection by invoking pandoc with argument arrays.
- Never execute arbitrary code from notes.

## Testing

Recommended tests:

- embed expansion for simple paths
- embed expansion for nested embeds
- validation of required frontmatter and sections
- stable output naming and output locations
- pandoc invocation smoke test with a tiny sample vault in fixtures

## Developer experience

### Local development

- A `fixtures/` vault with 2 to 3 recipes and one cookbook note.
- A `make build` or `just build` command that runs the CLI locally.

### Release

- Versioned binary or package
- Keep templates versioned with the project, not the vault
- Support multiple projects for different cookbook styles

## Roadmap ideas (optional)

- Shopping list extraction
- Ingredient normalization and aggregation
- Tag and category index pages
- Multiple themes (menu-card, minimal, gift-book)
- Export to HTML for sharing
- Optional Cooklang import converter

## Invariants

- The vault is read-only from vaultchef’s perspective.
- All generated artifacts and caches live in the project directory.
- Authoring stays plain Markdown with YAML frontmatter.
- The cookbook note stays readable inside Obsidian and Neovim.

## Interactive mode

Vault chef includes an interactive mode for cookbook building and building.

# Features

trigger with --tui

User is given two options: create a cookbook or build a cookbook.

If they choose create they first choose a cookbook name, then are given the list of all recipes, they can /filter by all unique tags (e.g., gluten free, vegetarian, desert, drink, main, side).

Every time they press enter on a recipe it's added into a new cookbook.

When it's finalised vaultchef writes it into the cookbook dir of the vault.

Build mode is simpler, they just fuzzy find a cookbook from all possible cookbooks and then it builds it in the current working directory.

This mode is very pretty and snappy, an extremely polished TUI experience.

## Quick start

1. Create global config:
   `~/.config/vaultchef/config.toml`

2. Create a project folder:
   `~/CookbookProject/` with templates and filters.

3. Write recipes in:
   `$vault/Recipes/`

4. Write a cookbook note in:
   `$vault/Cookbooks/`

5. Build:
   ```bash
   vaultchef build "Family Cookbook" --open
   ```
