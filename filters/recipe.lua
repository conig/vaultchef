local in_recipe = false

local function is_recipe_start(el)
  return el.format == "html" and el.text:match("vaultchef:recipe:start")
end

local function header_text(el)
  return pandoc.utils.stringify(el.content)
end

function RawBlock(el)
  if is_recipe_start(el) then
    in_recipe = true
    return pandoc.RawBlock("latex", "\\clearpage\n")
  end
end

function Header(el)
  if el.level == 1 then
    in_recipe = false
    return nil
  end
  if in_recipe and header_text(el):lower() == "method" then
    return { pandoc.RawBlock("latex", "\\clearpage\n"), el }
  end
  return nil
end

return {
  RawBlock = RawBlock,
  Header = Header,
}
