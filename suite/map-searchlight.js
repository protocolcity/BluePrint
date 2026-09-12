/**
 * map-searchlight.js — shared Map/Home searchlight.
 *
 * Pages own the corpus and navigation actions. This module owns the search
 * field, result grouping, keyboard behavior, and the `/` focus shortcut.
 */
(function (global) {
  "use strict";

  const STYLE_ID = "map-searchlight-style";
  let nextId = 1;

  function installStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .map-searchlight {
        position: relative;
        flex: 0 1 280px;
        width: min(280px, 30vw);
        min-width: 170px;
        max-width: 340px;
        z-index: 80;
      }
      .map-searchlight input {
        width: 100%;
        box-sizing: border-box;
        padding: 6px 11px 6px 30px;
        border: 1px solid var(--line-faint, rgba(42, 36, 28, 0.18));
        border-radius: 8px;
        background:
          var(--card, var(--paper-deep, #fffdf8))
          url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 13 13'%3E%3Ccircle cx='5.4' cy='5.4' r='3.7' fill='none' stroke='%236b6154' stroke-width='1.25'/%3E%3Cpath d='M8.2 8.2L11.5 11.5' stroke='%236b6154' stroke-width='1.25' stroke-linecap='round'/%3E%3C/svg%3E")
          10px 50% no-repeat;
        color: var(--ink, var(--line, #2a241c));
        font-weight: var(--weight-medium); font-size: var(--type-body); line-height: 1.25; font-family: "Avenir Next", system-ui, sans-serif;
        letter-spacing: 0.01em;
        outline: none;
      }
      .map-searchlight input::placeholder {
        color: var(--dim, var(--line, #6b6154));
        opacity: 0.62;
      }
      .map-searchlight input:focus {
        border-color: var(--finder-blue, #007aff);
        box-shadow: 0 0 0 2px color-mix(in srgb, var(--finder-blue, #007aff) 18%, transparent);
      }
      .map-search-results {
        position: absolute;
        top: calc(100% + 7px);
        left: 0;
        width: max(100%, 330px);
        max-width: min(440px, calc(100vw - 24px));
        max-height: min(430px, 62vh);
        overflow: auto;
        padding: 4px 0 7px;
        background: var(--card, var(--paper-deep, #fffdf8));
        color: var(--ink, var(--line, #2a241c));
        border: 1px solid var(--border, var(--line-faint, #c4b8a4));
        border-radius: 10px;
        box-shadow: 0 14px 38px rgba(42, 36, 28, 0.2);
        z-index: 90;
      }
      .map-searchlight.is-end .map-search-results {
        right: 0;
        left: auto;
      }
      .map-search-results[hidden] {
        display: none !important;
      }
      .map-search-results .map-sr-group {
        padding: 9px 12px 3px;
        color: var(--dim, var(--line, #6b6154));
        font-weight: var(--weight-medium); font-size: var(--type-caption); line-height: 1.2; font-family: "Avenir Next", system-ui, sans-serif;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        opacity: 0.72;
      }
      .map-search-results .map-sr-item {
        display: flex;
        align-items: flex-start;
        gap: 9px;
        width: 100%;
        padding: 8px 12px;
        border: 0;
        background: transparent;
        color: inherit;
        text-align: left;
        cursor: pointer;
        font-weight: var(--weight-medium); font-size: var(--type-body); line-height: 1.3; font-family: "Avenir Next", system-ui, sans-serif;
      }
      .map-search-results .map-sr-item:hover,
      .map-search-results .map-sr-item.is-active {
        background: color-mix(in srgb, var(--finder-blue, #007aff) 10%, transparent);
      }
      .map-search-results .map-sr-chip {
        flex: 0 0 23px;
        width: 23px;
        height: 23px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: 1px solid var(--line-faint, rgba(42, 36, 28, 0.16));
        border-radius: 6px;
        font-size: var(--type-label);
        line-height: 1;
        opacity: 0.9;
      }
      .map-search-results .map-sr-body {
        min-width: 0;
        flex: 1 1 auto;
      }
      .map-search-results .map-sr-title,
      .map-search-results .map-sr-meta {
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .map-search-results .map-sr-title {
        font-weight: var(--weight-medium);
      }
      .map-search-results .map-sr-meta {
        margin-top: 2px;
        color: var(--dim, var(--line, #6b6154));
        font-size: var(--type-label);
        opacity: 0.78;
      }
      .map-search-results .map-sr-empty {
        padding: 14px;
        color: var(--dim, var(--line, #6b6154));
        font-size: var(--type-body);
        font-style: italic;
        opacity: 0.8;
      }
      html.suite-map-city .suite-head-meta {
        gap: 9px;
      }
      html.suite-map-city .map-searchlight {
        width: clamp(180px, 24vw, 320px);
      }
      @media (max-width: 760px) {
        .map-searchlight {
          width: min(220px, 42vw);
          min-width: 145px;
        }
        .map-search-results {
          width: min(360px, calc(100vw - 20px));
        }
      }
    `;
    document.head.appendChild(style);
  }

  /* pc-1396: HTML escape lives in /esc.js */
  var esc = function (s) { return global.__bp.esc(s); };

  function itemScore(item, query) {
    const q = String(query || "").trim().toLowerCase();
    if (!q) return -1;
    const keys = [item.title, item.meta].concat(item.keys || []).map(function (v) {
      return String(v == null ? "" : v).toLowerCase();
    });
    for (let i = 0; i < keys.length; i++) {
      if (keys[i] === q) return 0;
    }
    for (let i = 0; i < keys.length; i++) {
      if (keys[i].indexOf(q) === 0) return 1;
    }
    const hay = keys.join(" \u0001 ");
    const tokens = q.split(/\s+/).filter(Boolean);
    for (let i = 0; i < tokens.length; i++) {
      if (hay.indexOf(tokens[i]) < 0) return -1;
    }
    return 2;
  }

  function mount(host, options) {
    const root =
      typeof host === "string" ? document.querySelector(host) : host;
    if (!root) return null;
    if (root._mapSearchlight) return root._mapSearchlight;

    installStyles();
    const opts = Object.assign(
      {
        placeholder: "Search…",
        ariaLabel: "Search",
        resultsLabel: "Search results",
        emptyLabel: "Nothing matching",
        maxResults: 36,
        maxPerKind: 10,
        kindOrder: [],
        groupLabels: {},
        slashShortcut: true,
      },
      options || {}
    );
    const idBase =
      String(opts.idBase || root.id || "map-searchlight") + "-" + nextId++;
    const inputId = idBase + "-input";
    const resultsId = idBase + "-results";

    root.classList.add("map-searchlight");
    if (opts.align === "end") root.classList.add("is-end");
    root.innerHTML =
      '<input type="search" id="' +
      esc(inputId) +
      '" autocomplete="off" spellcheck="false" enterkeyhint="search" ' +
      'role="combobox" aria-autocomplete="list" aria-expanded="false" ' +
      'aria-controls="' +
      esc(resultsId) +
      '">' +
      '<div class="map-search-results" id="' +
      esc(resultsId) +
      '" role="listbox" hidden></div>';

    const input = root.querySelector("input");
    const results = root.querySelector(".map-search-results");
    const state = {
      items: [],
      hits: [],
      query: "",
      active: -1,
      timer: null,
      open: false,
    };

    function setContext(context) {
      Object.assign(opts, context || {});
      input.placeholder = opts.placeholder || "Search…";
      input.setAttribute("aria-label", opts.ariaLabel || "Search");
      if (opts.title) input.setAttribute("title", opts.title);
      else input.removeAttribute("title");
      results.setAttribute(
        "aria-label",
        opts.resultsLabel || "Search results"
      );
    }

    function close(closeOptions) {
      const keepQuery = !!(closeOptions && closeOptions.keepQuery);
      if (state.timer) {
        clearTimeout(state.timer);
        state.timer = null;
      }
      state.open = false;
      state.active = -1;
      state.hits = [];
      results.hidden = true;
      results.innerHTML = "";
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      if (!keepQuery) {
        input.value = "";
        state.query = "";
      }
    }

    function groupedHits(query) {
      const groups = Object.create(null);
      const order = (opts.kindOrder || []).slice();
      state.items.forEach(function (item) {
        if (!item) return;
        const score = itemScore(item, query);
        if (score < 0) return;
        const kind = String(item.kind || "result");
        if (!groups[kind]) {
          groups[kind] = [];
          if (order.indexOf(kind) < 0) order.push(kind);
        }
        groups[kind].push(Object.assign({}, item, { _score: score }));
      });

      const hits = [];
      order.forEach(function (kind) {
        const rows = groups[kind] || [];
        rows.sort(function (a, b) {
          if (a._score !== b._score) return a._score - b._score;
          return String(a.title || "").localeCompare(String(b.title || ""));
        });
        rows.slice(0, opts.maxPerKind).forEach(function (item) {
          if (hits.length < opts.maxResults) hits.push(item);
        });
      });
      return hits;
    }

    function paintActive() {
      results.querySelectorAll(".map-sr-item").forEach(function (el) {
        const index = Number(el.getAttribute("data-index"));
        const active = index === state.active;
        el.classList.toggle("is-active", active);
        el.setAttribute("aria-selected", active ? "true" : "false");
      });
      const activeEl = results.querySelector(".map-sr-item.is-active");
      if (activeEl) {
        input.setAttribute("aria-activedescendant", activeEl.id);
        if (activeEl.scrollIntoView) {
          activeEl.scrollIntoView({ block: "nearest" });
        }
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }

    function activate(item) {
      if (!item) return;
      close({ keepQuery: true });
      input.blur();
      if (typeof opts.onActivate === "function") {
        opts.onActivate(item);
        return;
      }
      if (typeof item.action === "function") {
        item.action(item);
        return;
      }
      if (item.href) {
        if (typeof opts.onNavigate === "function") opts.onNavigate(item.href, item);
        else global.location.href = item.href;
      }
    }

    function render() {
      const query = state.query;
      if (!query) {
        close({ keepQuery: true });
        return;
      }
      state.hits = groupedHits(query);
      state.active = state.hits.length ? 0 : -1;
      state.open = true;
      results.hidden = false;
      input.setAttribute("aria-expanded", "true");

      if (!state.hits.length) {
        results.innerHTML =
          '<div class="map-sr-empty">' +
          esc(opts.emptyLabel || "Nothing matching") +
          " “" +
          esc(query) +
          "”</div>";
        input.removeAttribute("aria-activedescendant");
        return;
      }

      let html = "";
      let lastKind = "";
      state.hits.forEach(function (item, index) {
        const kind = String(item.kind || "result");
        if (kind !== lastKind) {
          lastKind = kind;
          html +=
            '<div class="map-sr-group">' +
            esc(opts.groupLabels[kind] || kind) +
            "</div>";
        }
        html +=
          '<button type="button" class="map-sr-item' +
          (index === state.active ? " is-active" : "") +
          '" id="' +
          esc(idBase + "-option-" + index) +
          '" data-index="' +
          index +
          '" role="option" aria-selected="' +
          (index === state.active ? "true" : "false") +
          '">' +
          '<span class="map-sr-chip" aria-hidden="true">' +
          esc(item.glyph || "·") +
          "</span>" +
          '<span class="map-sr-body"><span class="map-sr-title">' +
          esc(item.title || "") +
          '</span><span class="map-sr-meta">' +
          esc(item.meta || "") +
          "</span></span></button>";
      });
      results.innerHTML = html;
      results.querySelectorAll(".map-sr-item").forEach(function (el) {
        el.addEventListener("click", function () {
          activate(state.hits[Number(el.getAttribute("data-index"))]);
        });
        el.addEventListener("mouseenter", function () {
          state.active = Number(el.getAttribute("data-index"));
          paintActive();
        });
      });
      paintActive();
    }

    function run(query) {
      state.query = String(query || "").trim();
      /* pc-1170: page may dig tickets / expand corpus from the live query */
      if (typeof opts.onQuery === "function") {
        try {
          opts.onQuery(state.query, {
            setItems: setItems,
            getItems: function () {
              return state.items.slice();
            },
            render: function () {
              if (state.query) render();
            },
          });
        } catch (eOn) {}
      }
      render();
    }

    function schedule(query) {
      if (state.timer) clearTimeout(state.timer);
      state.timer = setTimeout(function () {
        state.timer = null;
        run(query);
      }, 100);
    }

    function setItems(items) {
      state.items = Array.isArray(items) ? items.filter(Boolean) : [];
      if (state.query) render();
    }

    function focus() {
      input.focus();
      if (input.select) input.select();
    }

    input.addEventListener("input", function () {
      schedule(input.value);
    });
    input.addEventListener("focus", function () {
      if (String(input.value || "").trim()) run(input.value);
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        if (!state.hits.length) return;
        event.preventDefault();
        const delta = event.key === "ArrowDown" ? 1 : -1;
        state.active = Math.max(
          0,
          Math.min(
            state.hits.length - 1,
            state.active < 0 ? 0 : state.active + delta
          )
        );
        paintActive();
        return;
      }
      if (event.key === "Enter") {
        if (state.active >= 0 && state.hits[state.active]) {
          event.preventDefault();
          activate(state.hits[state.active]);
        }
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        close();
        input.blur();
      }
    });

    const onPointerDown = function (event) {
      if (!state.open || root.contains(event.target)) return;
      close({ keepQuery: true });
    };
    document.addEventListener("pointerdown", onPointerDown);

    const onShortcut = function (event) {
      if (
        !opts.slashShortcut ||
        event.key !== "/" ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      ) {
        return;
      }
      const target = event.target;
      const tag =
        target && target.tagName ? String(target.tagName).toUpperCase() : "";
      if (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        (target && target.isContentEditable)
      ) {
        return;
      }
      if (
        typeof opts.shouldFocus === "function" &&
        opts.shouldFocus(event) === false
      ) {
        return;
      }
      event.preventDefault();
      focus();
    };
    document.addEventListener("keydown", onShortcut);

    const api = {
      close: close,
      focus: focus,
      input: input,
      results: results,
      setContext: setContext,
      setItems: setItems,
      getItems: function () {
        return state.items.slice();
      },
      getQuery: function () {
        return state.query;
      },
      destroy: function () {
        if (state.timer) clearTimeout(state.timer);
        document.removeEventListener("pointerdown", onPointerDown);
        document.removeEventListener("keydown", onShortcut);
        root.innerHTML = "";
        delete root._mapSearchlight;
      },
    };
    root._mapSearchlight = api;
    setContext(opts);
    return api;
  }

  /*
   * pc-1389: shared GET /api/find helper so Overview and Map share one
   * paper/folder/file corpus. Name-substring over the citylens survey
   * (pc-94 / pc-1225) — not full-text body search. Cold/empty survey
   * surfaces an honest "Surveying…" row instead of silently dropping
   * to work-orders-only.
   */
  const FIND_MIN_CHARS = 2;
  const FIND_LIMIT = 30;
  let _findCache = Object.create(null);
  let _findCacheCount = 0;
  const _findInflight = Object.create(null);

  function openFinder(path) {
    try {
      if (global.SuiteNav && typeof global.SuiteNav.openInFinder === "function") {
        global.SuiteNav.openInFinder(path == null ? "" : String(path)).catch(
          function () {}
        );
        return;
      }
    } catch (eNav) {}
    try {
      fetch("/api/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path == null ? "" : String(path) }),
      }).catch(function () {});
    } catch (eOpen) {}
  }

  function openPaper(path) {
    const rel = String(path || "").trim();
    if (!rel) return;
    try {
      if (global.SuitePaper && typeof global.SuitePaper.open === "function") {
        global.SuitePaper.open(rel);
        return;
      }
    } catch (ePaper) {}
    global.location.href = "/read?path=" + encodeURIComponent(rel);
  }

  function itemFromFindHit(hit, options) {
    if (!hit) return null;
    const opts = options || {};
    const projectNames = opts.projectNames || {};
    const path = String(hit.path || "").trim();
    const name = String(hit.name || path.split("/").pop() || "").trim();
    if (!path || !name) return null;
    const isDir = String(hit.kind || "file") === "dir";
    const isMd = !isDir && /\.md$/i.test(name);
    if (isDir && path.indexOf("/") < 0 && projectNames[name.toLowerCase()]) {
      return null;
    }
    const parent =
      path.indexOf("/") >= 0
        ? path.slice(0, path.lastIndexOf("/"))
        : "workspace";
    if (isDir) {
      const projectHref =
        "/workspace-map?project=" + encodeURIComponent(name);
      const nested = path.indexOf("/") >= 0;
      return {
        kind: "folder",
        title: name,
        meta: "folder · " + parent,
        keys: [path, name],
        glyph: "▸",
        href: nested ? "/workspace-map" : projectHref,
        action: function () {
          if (nested) {
            openFinder(path);
            return;
          }
          global.location.href = projectHref;
        },
      };
    }
    if (isMd) {
      return {
        kind: "paper",
        title: name,
        meta: "paper · " + parent,
        keys: [path, name],
        glyph: "▤",
        href: "/read?path=" + encodeURIComponent(path),
        action: function () {
          openPaper(path);
        },
      };
    }
    return {
      kind: "file",
      title: name,
      meta: String(hit.ftype || "file") + " · " + parent,
      keys: [path, name],
      glyph: "▢",
      action: function () {
        openFinder(path);
      },
    };
  }

  function heapItemFromHint(hint) {
    if (!hint || !hint.path) return null;
    const path = String(hint.path);
    return {
      kind: "folder",
      title: path.split("/").pop() || path,
      meta: String(hint.label || "not surveyed"),
      keys: [path],
      glyph: "⊘",
      action: function () {
        openFinder(path);
      },
    };
  }

  function surveyingItem(query) {
    const q = String(query || "").trim();
    return {
      kind: "folder",
      title: "Surveying workspace…",
      meta: "Papers and folders appear when the index is ready",
      keys: [q, "surveying"],
      glyph: "…",
      href: "/workspace-map",
    };
  }

  function itemsFromFindPack(pack, options) {
    const items = [];
    const seen = Object.create(null);
    ((pack && pack.hits) || []).forEach(function (hit) {
      const item = itemFromFindHit(hit, options);
      if (!item) return;
      const key = String(item.kind || "") + ":" + String(item.keys && item.keys[0] || item.title);
      if (seen[key]) return;
      seen[key] = 1;
      items.push(item);
    });
    const heap = heapItemFromHint(pack && pack.skipped_hint);
    if (heap) items.push(heap);
    if (pack && pack.cold) items.push(surveyingItem(pack.q));
    return items;
  }

  function emptyFindPack(q) {
    return {
      q: q,
      hits: [],
      skipped_hint: null,
      survey: null,
      cold: false,
    };
  }

  function loadFindPack(q, limit) {
    const cached = _findCache[q];
    if (cached) return Promise.resolve(cached);
    if (_findInflight[q]) return _findInflight[q];
    const pending = fetch(
      "/api/find?q=" + encodeURIComponent(q) + "&limit=" + limit,
      { cache: "no-store" }
    )
      .then(function (r) {
        if (!r.ok) throw new Error("find HTTP " + r.status);
        return r.json();
      })
      .then(function (d) {
        const survey = (d && d.survey) || null;
        const entries = survey && survey.entries != null ? Number(survey.entries) : 0;
        const pack = {
          q: q,
          hits: (d && d.hits) || [],
          skipped_hint: (d && d.skipped_hint) || null,
          survey: survey,
          cold: !(entries > 0),
        };
        if (_findCacheCount > 400) {
          _findCache = Object.create(null);
          _findCacheCount = 0;
        }
        _findCache[q] = pack;
        _findCacheCount++;
        return pack;
      })
      .catch(function () {
        return {
          q: q,
          hits: [],
          skipped_hint: null,
          survey: { status: "error", entries: 0 },
          cold: true,
        };
      })
      .finally(function () {
        delete _findInflight[q];
      });
    _findInflight[q] = pending;
    return pending;
  }

  function fetchFind(query, options) {
    const opts = options || {};
    const minChars = opts.minChars != null ? opts.minChars : FIND_MIN_CHARS;
    const limit = opts.limit != null ? opts.limit : FIND_LIMIT;
    const q = String(query || "").trim().toLowerCase();
    if (q.length < minChars) {
      const empty = emptyFindPack(q);
      empty.items = [];
      return Promise.resolve(empty);
    }
    return loadFindPack(q, limit).then(function (pack) {
      return Object.assign({}, pack, {
        items: itemsFromFindPack(pack, opts),
      });
    });
  }

  /*
   * pc-1403: shared WO id-dig so Overview and Map share one /api/task/{id}
   * query path. Rooms own item shape (href vs action) and inject/drop;
   * this module owns the composite-id regex, cache, inflight, and fetch.
   */
  let _digCache = Object.create(null);
  const _digInflight = Object.create(null);

  function looksLikeWorkOrderId(q) {
    const s = String(q || "").trim();
    if (!/^[a-z][a-z0-9]*-\d+$/i.test(s)) return "";
    return s.toLowerCase();
  }

  function injectTicketItem(api, item, rawId) {
    if (!item || !api || typeof api.setItems !== "function") return;
    const prev = typeof api.getItems === "function" ? api.getItems() : [];
    const id = String(rawId || (item.keys && item.keys[0]) || "").toLowerCase();
    const next = [];
    let had = false;
    prev.forEach(function (it) {
      if (!it) return;
      const keys = (it.keys || []).map(function (k) {
        return String(k || "").toLowerCase();
      });
      if (
        it.kind === "ticket" &&
        (keys.indexOf(id) >= 0 ||
          String(it.title || "")
            .toLowerCase()
            .indexOf(id) === 0)
      ) {
        next.push(item);
        had = true;
      } else {
        next.push(it);
      }
    });
    if (!had) next.unshift(item);
    api.setItems(next);
  }

  function dropTicketById(api, rawId) {
    if (!api || typeof api.setItems !== "function") return;
    const id = String(rawId || "").toLowerCase();
    const prev = typeof api.getItems === "function" ? api.getItems() : [];
    api.setItems(
      prev.filter(function (it) {
        if (!it || it.kind !== "ticket") return true;
        const keys = (it.keys || []).map(function (k) {
          return String(k || "").toLowerCase();
        });
        return keys.indexOf(id) < 0;
      })
    );
  }

  function defaultPendingDigItem(id) {
    return {
      kind: "ticket",
      title: id + " · looking up…",
      meta: "closed work orders · dig by id",
      href: "/ticket?id=" + encodeURIComponent(id),
      keys: [id, "looking up dig work order"],
      glyph: "…",
    };
  }

  function applyDigPack(pack, id, hooks) {
    const d = (pack && pack.body) || {};
    const task = d.task || (d.id ? d : null);
    if (!pack || !pack.ok || !task || !task.id) {
      if (hooks && typeof hooks.drop === "function") hooks.drop(id);
      return;
    }
    _digCache[String(task.id).toLowerCase()] = task;
    if (typeof hooks.onHit === "function") hooks.onHit(task);
    if (typeof hooks.itemFromTask === "function") {
      const item = hooks.itemFromTask(task);
      if (item && typeof hooks.inject === "function") {
        hooks.inject(item, String(task.id));
      }
    }
  }

  function digWorkOrder(rawId, hooks) {
    const id = looksLikeWorkOrderId(rawId);
    if (!id) return false;
    const opts = hooks || {};
    const inject = opts.inject;
    if (typeof inject !== "function") return false;
    if (_digCache[id]) {
      applyDigPack(
        { ok: true, body: _digCache[id] },
        id,
        opts
      );
      return true;
    }
    const pendingItem =
      typeof opts.pendingItem === "function"
        ? opts.pendingItem(id)
        : defaultPendingDigItem(id);
    if (pendingItem) inject(pendingItem, id);

    function settle(pack) {
      applyDigPack(pack, id, opts);
    }
    function fail() {
      if (typeof opts.drop === "function") opts.drop(id);
    }

    if (_digInflight[id]) {
      _digInflight[id].then(settle).catch(fail);
      return true;
    }
    const pending = fetch("/api/task/" + encodeURIComponent(id), {
      cache: "no-store",
      credentials: "same-origin",
    }).then(function (r) {
      return r.json().then(function (d) {
        return { ok: r.ok, body: d };
      });
    });
    _digInflight[id] = pending;
    pending
      .then(settle)
      .catch(fail)
      .finally(function () {
        delete _digInflight[id];
      });
    return true;
  }

  /*
   * pc-1404: query-time WO title search via suite GET /api/tasks?q=
   * (Desk wl-493). Id-shaped queries stay on digWorkOrder; recency
   * preload is not title search. project=all = whole workspace;
   * a named store prefers that chip (id-dig still cross-store).
   */
  const TITLE_MIN_CHARS = 2;
  const TITLE_LIMIT = 20;
  let _titleCache = Object.create(null);
  let _titleCacheCount = 0;
  const _titleInflight = Object.create(null);

  function titleSearchKey(q, project) {
    return String(project || "all").toLowerCase() + "\u0001" + String(q || "").toLowerCase();
  }

  function titleSearchUrl(q, project, limit) {
    const params = [
      "q=" + encodeURIComponent(q),
      "limit=" + encodeURIComponent(String(limit)),
      "preview=0",
      "project=" + encodeURIComponent(project),
    ];
    return "/api/tasks?" + params.join("&");
  }

  function searchWorkOrders(query, hooks) {
    const opts = hooks || {};
    const q = String(query || "").trim();
    const projectRaw = String(opts.project || "all").trim() || "all";
    const project = projectRaw.toLowerCase() === "all" ? "all" : projectRaw;
    const limit = opts.limit != null ? opts.limit : TITLE_LIMIT;

    function deliver(tasks, qHit) {
      const rows = Array.isArray(tasks) ? tasks : [];
      const items = [];
      if (typeof opts.itemFromTask === "function") {
        rows.forEach(function (task) {
          const item = opts.itemFromTask(task);
          if (item) items.push(item);
        });
      }
      if (typeof opts.onTasks === "function") opts.onTasks(rows, qHit);
      if (typeof opts.setHits === "function") opts.setHits(items, qHit);
    }

    if (looksLikeWorkOrderId(q) || q.length < TITLE_MIN_CHARS) {
      deliver([], q);
      return false;
    }

    const key = titleSearchKey(q, project);
    if (_titleCache[key]) {
      deliver(_titleCache[key], q);
      return true;
    }

    function fail() {
      deliver([], q);
    }

    if (_titleInflight[key]) {
      _titleInflight[key].then(function (rows) {
        deliver(rows, q);
      }).catch(fail);
      return true;
    }

    const pending = fetch(titleSearchUrl(q, project, limit), {
      cache: "no-store",
      credentials: "same-origin",
    }).then(function (r) {
      return r.json().then(function (d) {
        return { ok: r.ok, body: d };
      });
    }).then(function (pack) {
      const d = pack.body || {};
      const tasks = pack.ok && Array.isArray(d.tasks) ? d.tasks : [];
      if (_titleCacheCount > 200) {
        _titleCache = Object.create(null);
        _titleCacheCount = 0;
      }
      _titleCache[key] = tasks;
      _titleCacheCount++;
      return tasks;
    });
    _titleInflight[key] = pending;
    pending
      .then(function (rows) {
        deliver(rows, q);
      })
      .catch(fail)
      .finally(function () {
        delete _titleInflight[key];
      });
    return true;
  }

  global.MapSearchlight = {
    mount: mount,
    fetchFind: fetchFind,
    itemsFromFindPack: itemsFromFindPack,
    looksLikeWorkOrderId: looksLikeWorkOrderId,
    digWorkOrder: digWorkOrder,
    searchWorkOrders: searchWorkOrders,
    injectTicketItem: injectTicketItem,
    dropTicketById: dropTicketById,
    FIND_MIN_CHARS: FIND_MIN_CHARS,
    FIND_LIMIT: FIND_LIMIT,
    TITLE_MIN_CHARS: TITLE_MIN_CHARS,
    TITLE_LIMIT: TITLE_LIMIT,
  };
})(window);
