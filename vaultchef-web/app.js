const DATA_PATH = "./content/index.json";

const FLAG_LABELS = {
  vegetarian: "Vegetarian",
  vegan: "Vegan",
  gluten_free: "Gluten Free",
  dairy_free: "Dairy Free",
};

const state = {
  tab: "recipes",
  recipeSlug: "",
  cookbookSlug: "",
  q: "",
  flags: new Set(),
  tags: new Set(),
};

const refs = {
  tabRecipes: document.getElementById("vc-tab-recipes"),
  tabCookbooks: document.getElementById("vc-tab-cookbooks"),
  searchInput: document.getElementById("vc-search-input"),
  filterRow: document.getElementById("vc-filter-row"),
  list: document.getElementById("vc-list"),
  detail: document.getElementById("vc-detail"),
  detailEmpty: document.getElementById("vc-detail-empty"),
  cardTemplate: document.getElementById("vc-card-template"),
};

let data = null;
let recipesBySlug = new Map();
let cookbooksBySlug = new Map();
let pendingMorphRect = null;
let activeRecipeList = [];
let activeCookbookList = [];

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const text = (value) => String(value || "").trim();
const escapeHtml = (value) =>
  text(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char] || char));

const normalize = (value) =>
  text(value)
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();

const parseHash = () => {
  const raw = window.location.hash || "#/recipes";
  const hash = raw.startsWith("#") ? raw.slice(1) : raw;
  const [pathRaw, queryRaw] = hash.split("?", 2);
  const path = pathRaw.replace(/^\/+/, "");
  const parts = path.split("/").filter(Boolean);
  const tab = parts[0] === "cookbooks" ? "cookbooks" : "recipes";
  const slug = decodeURIComponent(parts[1] || "");

  const params = new URLSearchParams(queryRaw || "");
  const flags = new Set(
    text(params.get("flags"))
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
  );
  const tags = new Set(
    text(params.get("tags"))
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
  );

  return {
    tab,
    recipeSlug: tab === "recipes" ? slug : "",
    cookbookSlug: tab === "cookbooks" ? slug : "",
    q: text(params.get("q")),
    flags,
    tags,
  };
};

const encodeHash = () => {
  const path = state.tab === "recipes" ? `/recipes/${encodeURIComponent(state.recipeSlug || "")}` : `/cookbooks/${encodeURIComponent(state.cookbookSlug || "")}`;
  const params = new URLSearchParams();

  if (state.q) {
    params.set("q", state.q);
  }
  if (state.flags.size > 0) {
    params.set("flags", Array.from(state.flags).sort().join(","));
  }
  if (state.tags.size > 0 && state.tab === "recipes") {
    params.set("tags", Array.from(state.tags).sort().join(","));
  }

  const query = params.toString();
  return `#${path}${query ? `?${query}` : ""}`;
};

const applyStateFromHash = () => {
  const parsed = parseHash();
  state.tab = parsed.tab;
  state.recipeSlug = parsed.recipeSlug;
  state.cookbookSlug = parsed.cookbookSlug;
  state.q = parsed.q;
  state.flags = parsed.flags;
  state.tags = parsed.tags;
  render();
};

const updateHash = (replace = false) => {
  const nextHash = encodeHash();
  if (replace) {
    const url = new URL(window.location.href);
    url.hash = nextHash.slice(1);
    history.replaceState(null, "", url);
    applyStateFromHash();
    return;
  }
  if (window.location.hash === nextHash) {
    render();
    return;
  }
  window.location.hash = nextHash;
};

const matchesRecipeFilters = (recipe) => {
  const needle = normalize(state.q);
  if (needle && !text(recipe.search_text).includes(needle)) {
    return false;
  }

  for (const flag of state.flags) {
    if (!recipe.flags || recipe.flags[flag] !== true) {
      return false;
    }
  }

  for (const tag of state.tags) {
    if (!recipe.tags.includes(tag)) {
      return false;
    }
  }

  return true;
};

const matchesCookbookFilters = (cookbook) => {
  const needle = normalize(state.q);
  if (!needle) {
    return true;
  }

  const haystack = normalize([
    cookbook.title,
    cookbook.subtitle,
    cookbook.author,
    cookbook.date,
  ].join(" "));

  return haystack.includes(needle);
};

const setTab = (tab) => {
  state.tab = tab;
  if (tab === "recipes") {
    state.cookbookSlug = "";
  } else {
    state.recipeSlug = "";
    state.flags = new Set();
    state.tags = new Set();
  }
  updateHash();
};

const openRecipe = (slug, sourceCard = null) => {
  if (sourceCard instanceof HTMLElement) {
    pendingMorphRect = sourceCard.getBoundingClientRect();
  }
  state.tab = "recipes";
  state.recipeSlug = slug;
  updateHash();
};

const openCookbook = (slug, sourceCard = null) => {
  if (sourceCard instanceof HTMLElement) {
    pendingMorphRect = sourceCard.getBoundingClientRect();
  }
  state.tab = "cookbooks";
  state.cookbookSlug = slug;
  updateHash();
};

const clearNode = (node) => {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
};

const renderTabs = () => {
  const recipeSelected = state.tab === "recipes";
  refs.tabRecipes.setAttribute("aria-selected", recipeSelected ? "true" : "false");
  refs.tabCookbooks.setAttribute("aria-selected", recipeSelected ? "false" : "true");
};

const buildMetaPills = (values) => {
  const row = document.createElement("div");
  row.className = "vc-meta-row";
  values.filter(Boolean).forEach((value) => {
    const pill = document.createElement("span");
    pill.className = "vc-pill";
    pill.textContent = value;
    row.appendChild(pill);
  });
  return row;
};

const makeCard = ({ title, body, pills, onOpen }) => {
  const card = refs.cardTemplate.content.firstElementChild.cloneNode(true);
  const heading = document.createElement("h2");
  heading.textContent = title;
  card.appendChild(heading);

  if (body) {
    const paragraph = document.createElement("p");
    paragraph.textContent = body;
    card.appendChild(paragraph);
  }

  if (pills && pills.length > 0) {
    card.appendChild(buildMetaPills(pills));
  }

  card.addEventListener("click", () => onOpen(card));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(card);
    }
  });

  return card;
};

const renderFilters = () => {
  clearNode(refs.filterRow);

  if (state.tab !== "recipes") {
    return;
  }

  const activeFlags = data.facets.flags || [];
  activeFlags.forEach((flag) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "vc-chip";
    chip.textContent = FLAG_LABELS[flag] || flag;
    chip.setAttribute("aria-pressed", state.flags.has(flag) ? "true" : "false");
    chip.addEventListener("click", () => {
      if (state.flags.has(flag)) {
        state.flags.delete(flag);
      } else {
        state.flags.add(flag);
      }
      state.recipeSlug = "";
      updateHash(true);
    });
    refs.filterRow.appendChild(chip);
  });

  const tagLimit = 12;
  (data.facets.tags || []).slice(0, tagLimit).forEach((tag) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "vc-chip";
    chip.textContent = `#${tag}`;
    chip.setAttribute("aria-pressed", state.tags.has(tag) ? "true" : "false");
    chip.addEventListener("click", () => {
      if (state.tags.has(tag)) {
        state.tags.delete(tag);
      } else {
        state.tags.add(tag);
      }
      state.recipeSlug = "";
      updateHash(true);
    });
    refs.filterRow.appendChild(chip);
  });
};

const renderRecipesList = () => {
  activeRecipeList = data.recipes.filter(matchesRecipeFilters);

  clearNode(refs.list);
  if (activeRecipeList.length === 0) {
    const empty = document.createElement("div");
    empty.className = "vc-empty";
    empty.textContent = "No recipes match your search and filters.";
    refs.list.appendChild(empty);
    return;
  }

  activeRecipeList.forEach((recipe) => {
    const pills = [];
    if (recipe.course) pills.push(recipe.course);
    if (recipe.category) pills.push(recipe.category);
    if (recipe.prep) pills.push(`Prep ${recipe.prep}`);
    if (recipe.cook) pills.push(`Cook ${recipe.cook}`);
    if (recipe.tags.length > 0) pills.push(`#${recipe.tags[0]}`);

    const card = makeCard({
      title: recipe.title,
      body: recipe.menu,
      pills,
      onOpen: (node) => openRecipe(recipe.slug, node),
    });
    refs.list.appendChild(card);
  });
};

const renderCookbooksList = () => {
  activeCookbookList = data.cookbooks.filter(matchesCookbookFilters);

  clearNode(refs.list);
  if (activeCookbookList.length === 0) {
    const empty = document.createElement("div");
    empty.className = "vc-empty";
    empty.textContent = "No cookbooks match your search.";
    refs.list.appendChild(empty);
    return;
  }

  activeCookbookList.forEach((cookbook) => {
    const pills = [];
    if (cookbook.author) pills.push(cookbook.author);
    if (cookbook.date) pills.push(cookbook.date);
    pills.push(`${cookbook.recipe_slugs.length} recipes`);

    const card = makeCard({
      title: cookbook.title,
      body: cookbook.subtitle || cookbook.description,
      pills,
      onOpen: (node) => openCookbook(cookbook.slug, node),
    });
    refs.list.appendChild(card);
  });
};

const recipeLinksHtml = (slugs) =>
  slugs
    .map((slug) => {
      const recipe = recipesBySlug.get(slug);
      if (!recipe) {
        return "";
      }
      return `<button class="vc-chip" type="button" data-recipe-jump="${recipe.slug}">${escapeHtml(recipe.title)}</button>`;
    })
    .join(" ");

const cookbookLinksHtml = (slugs) =>
  slugs
    .map((slug) => {
      const cookbook = cookbooksBySlug.get(slug);
      if (!cookbook) {
        return "";
      }
      return `<button class="vc-chip" type="button" data-cookbook-jump="${cookbook.slug}">${escapeHtml(cookbook.title)}</button>`;
    })
    .join(" ");

const renderRecipeDetail = () => {
  const recipe = recipesBySlug.get(state.recipeSlug);
  if (!recipe) {
    refs.detail.hidden = true;
    refs.detailEmpty.hidden = false;
    refs.detailEmpty.textContent = "Choose a recipe from the list to see details.";
    return;
  }

  refs.detail.innerHTML = `
    <div class="vc-detail-card" id="vc-detail-card">
      <h2>${escapeHtml(recipe.title)}</h2>
      ${recipe.menu ? `<p>${escapeHtml(recipe.menu)}</p>` : ""}
      <div class="vc-meta-row">
        ${recipe.serves ? `<span class="vc-pill">Serves ${escapeHtml(recipe.serves)}</span>` : ""}
        ${recipe.prep ? `<span class="vc-pill">Prep ${escapeHtml(recipe.prep)}</span>` : ""}
        ${recipe.cook ? `<span class="vc-pill">Cook ${escapeHtml(recipe.cook)}</span>` : ""}
        ${recipe.rest ? `<span class="vc-pill">Rest ${escapeHtml(recipe.rest)}</span>` : ""}
      </div>
      <div class="vc-detail-grid">
        <section>
          <h3>Ingredients</h3>
          ${recipe.sections.ingredients_html || "<p>No ingredients section found.</p>"}
        </section>
        <section>
          <h3>Method</h3>
          ${recipe.sections.method_html || "<p>No method section found.</p>"}
          ${recipe.sections.notes_html ? `<h3>Notes</h3>${recipe.sections.notes_html}` : ""}
        </section>
      </div>
      ${recipe.cookbook_slugs.length > 0 ? `<section><h3>In Cookbooks</h3><div class="vc-meta-row">${cookbookLinksHtml(recipe.cookbook_slugs)}</div></section>` : ""}
    </div>
  `;

  refs.detail.querySelectorAll("[data-cookbook-jump]").forEach((button) => {
    button.addEventListener("click", () => openCookbook(button.dataset.cookbookJump || ""));
  });

  refs.detail.hidden = false;
  refs.detailEmpty.hidden = true;
  runMorphAnimation();
};

const renderCookbookDetail = () => {
  const cookbook = cookbooksBySlug.get(state.cookbookSlug);
  if (!cookbook) {
    refs.detail.hidden = true;
    refs.detailEmpty.hidden = false;
    refs.detailEmpty.textContent = "Choose a cookbook from the list to see details.";
    return;
  }

  refs.detail.innerHTML = `
    <div class="vc-detail-card" id="vc-detail-card">
      <h2>${escapeHtml(cookbook.title)}</h2>
      ${cookbook.subtitle ? `<p>${escapeHtml(cookbook.subtitle)}</p>` : ""}
      <div class="vc-meta-row">
        ${cookbook.author ? `<span class="vc-pill">${escapeHtml(cookbook.author)}</span>` : ""}
        ${cookbook.date ? `<span class="vc-pill">${escapeHtml(cookbook.date)}</span>` : ""}
        <span class="vc-pill">${cookbook.recipe_slugs.length} recipes</span>
      </div>
      ${cookbook.description ? `<section><h3>Description</h3><p>${escapeHtml(cookbook.description)}</p></section>` : ""}
      ${cookbook.album_title || cookbook.album_artist || cookbook.album_style ? `
      <section>
        <h3>Music Pairing</h3>
        <div class="vc-meta-row">
          ${cookbook.album_title ? `<span class="vc-pill">${escapeHtml(cookbook.album_title)}</span>` : ""}
          ${cookbook.album_artist ? `<span class="vc-pill">${escapeHtml(cookbook.album_artist)}</span>` : ""}
          ${cookbook.album_style ? `<span class="vc-pill">${escapeHtml(cookbook.album_style)}</span>` : ""}
        </div>
      </section>
      ` : ""}
      ${cookbook.recipe_slugs.length > 0 ? `<section><h3>Recipes</h3><div class="vc-meta-row">${recipeLinksHtml(cookbook.recipe_slugs)}</div></section>` : ""}
    </div>
  `;

  refs.detail.querySelectorAll("[data-recipe-jump]").forEach((button) => {
    button.addEventListener("click", () => openRecipe(button.dataset.recipeJump || ""));
  });

  refs.detail.hidden = false;
  refs.detailEmpty.hidden = true;
  runMorphAnimation();
};

const runMorphAnimation = () => {
  if (!pendingMorphRect) {
    return;
  }

  const target = document.getElementById("vc-detail-card");
  const startRect = pendingMorphRect;
  pendingMorphRect = null;

  if (!target || reducedMotion) {
    return;
  }

  const endRect = target.getBoundingClientRect();
  if (startRect.width < 2 || startRect.height < 2 || endRect.width < 2 || endRect.height < 2) {
    return;
  }

  const overlay = document.createElement("div");
  overlay.className = "vc-morph-overlay";
  overlay.style.left = `${startRect.left}px`;
  overlay.style.top = `${startRect.top}px`;
  overlay.style.width = `${startRect.width}px`;
  overlay.style.height = `${startRect.height}px`;
  document.body.appendChild(overlay);

  target.style.visibility = "hidden";

  requestAnimationFrame(() => {
    overlay.style.transition = "left 230ms cubic-bezier(0.2, 0, 0, 1), top 230ms cubic-bezier(0.2, 0, 0, 1), width 230ms cubic-bezier(0.2, 0, 0, 1), height 230ms cubic-bezier(0.2, 0, 0, 1), border-radius 230ms cubic-bezier(0.2, 0, 0, 1)";
    overlay.style.left = `${endRect.left}px`;
    overlay.style.top = `${endRect.top}px`;
    overlay.style.width = `${endRect.width}px`;
    overlay.style.height = `${endRect.height}px`;
    overlay.style.borderRadius = "22px";
  });

  overlay.addEventListener(
    "transitionend",
    () => {
      target.style.visibility = "visible";
      overlay.remove();
    },
    { once: true }
  );
};

const renderDetail = () => {
  if (state.tab === "recipes") {
    renderRecipeDetail();
    return;
  }
  renderCookbookDetail();
};

const render = () => {
  renderTabs();

  refs.searchInput.value = state.q;
  refs.searchInput.placeholder = state.tab === "recipes" ? "Search recipes" : "Search cookbooks";

  renderFilters();

  if (state.tab === "recipes") {
    renderRecipesList();

    if (state.recipeSlug && !recipesBySlug.has(state.recipeSlug)) {
      state.recipeSlug = "";
      updateHash(true);
      return;
    }

    if (!state.recipeSlug && activeRecipeList.length > 0 && normalize(state.q) === "" && state.flags.size === 0 && state.tags.size === 0) {
      state.recipeSlug = activeRecipeList[0].slug;
      updateHash(true);
      return;
    }
  } else {
    renderCookbooksList();

    if (state.cookbookSlug && !cookbooksBySlug.has(state.cookbookSlug)) {
      state.cookbookSlug = "";
      updateHash(true);
      return;
    }

    if (!state.cookbookSlug && activeCookbookList.length > 0 && normalize(state.q) === "") {
      state.cookbookSlug = activeCookbookList[0].slug;
      updateHash(true);
      return;
    }
  }

  renderDetail();
};

const setupEvents = () => {
  refs.tabRecipes.addEventListener("click", () => setTab("recipes"));
  refs.tabCookbooks.addEventListener("click", () => setTab("cookbooks"));

  refs.searchInput.addEventListener("input", (event) => {
    state.q = text(event.target.value);
    if (state.tab === "recipes") {
      state.recipeSlug = "";
    } else {
      state.cookbookSlug = "";
    }
    updateHash(true);
  });

  window.addEventListener("hashchange", applyStateFromHash);
};

const bootstrap = async () => {
  try {
    const response = await fetch(DATA_PATH, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Failed to fetch ${DATA_PATH}: ${response.status}`);
    }
    data = await response.json();
  } catch (error) {
    refs.list.innerHTML = `<div class="vc-empty">Unable to load cookbook content. ${error}</div>`;
    refs.detail.hidden = true;
    refs.detailEmpty.hidden = false;
    return;
  }

  recipesBySlug = new Map((data.recipes || []).map((recipe) => [recipe.slug, recipe]));
  cookbooksBySlug = new Map((data.cookbooks || []).map((cookbook) => [cookbook.slug, cookbook]));

  setupEvents();
  applyStateFromHash();
};

bootstrap();
