local in_recipe = false
local page_open = false
local first_recipe = true

local function is_recipe_start(el)
  return el.format == "html" and el.text:match("vaultchef:recipe:start")
end

local function header_text(el)
  return pandoc.utils.stringify(el.content)
end

function RawBlock(el)
  if is_recipe_start(el) then
    in_recipe = true
    local blocks = {}
    if page_open then
      table.insert(blocks, pandoc.RawBlock("latex", "\\VaultChefPageEnd\n"))
    end
    if first_recipe then
      table.insert(blocks, pandoc.RawBlock("latex", "\\VaultChefPageStart\n"))
      first_recipe = false
    else
      table.insert(blocks, pandoc.RawBlock("latex", "\\clearpage\n\\VaultChefPageStart\n"))
    end
    page_open = true
    return blocks
  end
end

function Header(el)
  if el.level == 1 then
    in_recipe = false
    return nil
  end
  if in_recipe and header_text(el):lower() == "method" then
    local blocks = {
      pandoc.RawBlock("latex", "\\VaultChefPageEnd\n\\clearpage\n\\VaultChefPageStart\n"),
      el,
    }
    page_open = true
    return blocks
  end
  return nil
end

function Pandoc(doc)
  if page_open then
    table.insert(doc.blocks, pandoc.RawBlock("latex", "\\VaultChefPageEnd\n"))
  end
  return doc
end

return {
  RawBlock = RawBlock,
  Header = Header,
  Pandoc = Pandoc,
}
