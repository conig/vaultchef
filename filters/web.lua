local RESERVED_HEADERS = {
  ingredients = "vc-ingredients-heading",
  method = "vc-method-heading",
  notes = "vc-notes-heading",
}

local function is_recipe_start(block)
  return block.t == "RawBlock" and block.format == "html" and block.text:match("vaultchef:recipe:start")
end

local function is_image_marker(block)
  return block.t == "RawBlock" and block.format == "html" and block.text:match("vaultchef:image:")
end

local function html_escape(text)
  return (text:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

local function image_from_marker(block)
  local path = block.text:match("vaultchef:image:(.-)%s*%-%-%>")
  if not path then
    return nil
  end

  path = path:gsub("^%s+", ""):gsub("%s+$", "")
  if path == "" then
    return nil
  end

  local escaped = html_escape(path)
  return pandoc.RawBlock("html", '<figure class="vc-hero"><img src="' .. escaped .. '" alt="Recipe image" loading="lazy" decoding="async" /></figure>')
end

local function add_class(attr, class_name)
  for _, name in ipairs(attr.classes) do
    if name == class_name then
      return attr
    end
  end
  table.insert(attr.classes, class_name)
  return attr
end

local function slugify(text)
  local slug = text:lower()
  slug = slug:gsub("[^%w%s-]", "")
  slug = slug:gsub("%s+", "-")
  slug = slug:gsub("-+", "-")
  slug = slug:gsub("^-+", "")
  slug = slug:gsub("-+$", "")
  if slug == "" then
    return "section"
  end
  return slug
end

local function unique_id(base, used_ids)
  local candidate = base
  local i = 2
  while used_ids[candidate] do
    candidate = base .. "-" .. i
    i = i + 1
  end
  used_ids[candidate] = true
  return candidate
end

local function ensure_header_id(header, base, used_ids)
  local attr = header.attr
  local current = attr.identifier or ""

  if current == "" then
    current = unique_id(base, used_ids)
  elseif used_ids[current] then
    current = unique_id(base, used_ids)
  else
    used_ids[current] = true
  end

  attr.identifier = current
  header.attr = attr
  return header
end

local function mark_chapter_header(block, used_ids)
  local attr = add_class(block.attr, "vc-chapter-title")
  block.attr = attr
  local text = pandoc.utils.stringify(block.content)
  return ensure_header_id(block, slugify(text), used_ids)
end

local function process_recipe_blocks(blocks, recipe_index, used_ids)
  local processed = {}
  local saw_recipe_title = false
  local recipe_title_id = nil

  for _, block in ipairs(blocks) do
    if is_image_marker(block) then
      local figure = image_from_marker(block)
      if figure ~= nil then
        table.insert(processed, figure)
      end
    else
      if block.t == "Header" and block.level == 2 then
        local text = pandoc.utils.stringify(block.content)
        local lower = text:lower()

        if (not saw_recipe_title) and RESERVED_HEADERS[lower] == nil then
          local attr = add_class(block.attr, "vc-recipe-title")
          block.attr = attr
          block = ensure_header_id(block, slugify(text), used_ids)
          saw_recipe_title = true
          recipe_title_id = block.attr.identifier
        elseif RESERVED_HEADERS[lower] ~= nil then
          local attr = add_class(block.attr, RESERVED_HEADERS[lower])
          block.attr = attr
        end
      elseif block.t == "Header" and block.level == 3 then
        local attr = add_class(block.attr, "vc-subsection-heading")
        block.attr = attr
      end

      table.insert(processed, block)
    end
  end

  local card_base = recipe_title_id or ("recipe-" .. recipe_index)
  local card_id = unique_id(card_base .. "-card", used_ids)
  return pandoc.Div(processed, pandoc.Attr(card_id, { "vc-recipe-card" }))
end

function Pandoc(doc)
  local blocks_out = {}
  local recipe_blocks = {}
  local in_recipe = false
  local recipe_index = 0
  local used_ids = {}

  local function flush_recipe()
    if #recipe_blocks == 0 then
      return
    end

    recipe_index = recipe_index + 1
    table.insert(blocks_out, process_recipe_blocks(recipe_blocks, recipe_index, used_ids))
    recipe_blocks = {}
  end

  for _, block in ipairs(doc.blocks) do
    if is_recipe_start(block) then
      flush_recipe()
      in_recipe = true
    elseif in_recipe then
      if block.t == "Header" and block.level == 1 then
        flush_recipe()
        in_recipe = false
        table.insert(blocks_out, mark_chapter_header(block, used_ids))
      else
        table.insert(recipe_blocks, block)
      end
    else
      if block.t == "Header" and block.level == 1 then
        table.insert(blocks_out, mark_chapter_header(block, used_ids))
      elseif is_image_marker(block) then
        local figure = image_from_marker(block)
        if figure ~= nil then
          table.insert(blocks_out, figure)
        end
      else
        table.insert(blocks_out, block)
      end
    end
  end

  flush_recipe()
  doc.blocks = blocks_out
  return doc
end

return {
  Pandoc = Pandoc,
}
