/**
 * suite-settings-sheet.js — Settings dig-in (SUITE_SHELL S4 / pc-402 / pc-494)
 *
 * pc-779: On Map, Settings mounts in the **same dig rail** as project overview
 * (`#inspect` via `openMapSettingsDig`) — not a foreign overlay. Overlay sheet
 * remains fallback on Overview / rooms without Map dig.
 *
 * pc-1267: `/settings` is the spine Settings view. This sheet stays the
 * Map FAB / dig door (`#nav-settings`, `?open=settings`). Payload cloned
 * from `/settings_v1.html`. `?sheet=1` still 302s to Map (one-release fallback).
 *
 * pc-666: Workspace panel only — foreign `scope=` values coerce to workspace.
 *
 * pc-662: segmented-box CSS for Appearance / Pane sides.
 */
(function (global) {
  "use strict";

  var root = null;
  var bodyEl = null;
  var titleEl = null;
  var openHref = "/settings_v1.html?scope=workspace";
  var lastScope = "workspace";
  var lastProject = "";
  /* In-memory payload — short debounce only (double-open thrash).
   * Long TTL + cache:"default" caused dogfood regressions: dig kept painting
   * pre-land HTML while main already had Dig-in / Custom / faces (2026-08-09).
   * Always re-fetch with no-store; only skip network if same href within
   * PAYLOAD_CACHE_MS *and* we still have a body. */
  var _payloadCache = { href: "", html: "", at: 0 };
  var PAYLOAD_CACHE_MS = 8000; /* 8s debounce — not multi-minute glass freeze */

  function ensure() {
    if (root) return root;
    root = document.createElement("div");
    root.id = "suite-settings-sheet";
    root.className = "suite-settings-sheet";
    root.hidden = true;
    root.innerHTML =
      '<div class="sss-bg" data-sss-close="1"></div>' +
      '<aside class="sss-panel" role="dialog" aria-modal="true" aria-labelledby="sss-title">' +
      '  <header class="sss-head">' +
      '    <div class="sss-kicker">Settings · dig-in</div>' +
      '    <h2 id="sss-title">Workspace</h2>' +
      '    <div class="sss-actions">' +
      '      <button type="button" class="sss-x" id="sss-close" title="Close" aria-label="Close">×</button>' +
      "    </div>" +
      "  </header>" +
      '  <div class="sss-body" id="sss-body" tabindex="-1"><p class="sss-muted">Loading…</p></div>' +
      "</aside>";
    document.body.appendChild(root);
    bodyEl = root.querySelector("#sss-body");
    titleEl = root.querySelector("#sss-title");
    root.querySelector("#sss-close").addEventListener("click", close);
    root.querySelector(".sss-bg").addEventListener("click", close);
    document.addEventListener("keydown", function (e) {
      if (!root || root.hidden) return;
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      }
    });
    return root;
  }

  function setOpen(on) {
    ensure();
    root.hidden = !on;
    root.classList.toggle("on", on);
    document.documentElement.classList.toggle("suite-settings-open", on);
  }

  function close() {
    /* Map dig host first (pc-779) */
    if (
      typeof global.closeMapSettingsDig === "function" &&
      global.closeMapSettingsDig()
    ) {
      return;
    }
    setOpen(false);
  }

  function isOpen() {
    if (
      typeof global.isMapSettingsDigOpen === "function" &&
      global.isMapSettingsDigOpen()
    ) {
      return true;
    }
    return !!(root && !root.hidden);
  }

  /**
   * Mount already-fetched settings HTML into host (parse · clone · wire).
   */
  function applySettingsHtml(hostEl, html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var wrap =
      doc.querySelector("#suite-body .wrap") || doc.querySelector(".wrap");
    if (!wrap) throw new Error("no settings body");
    hostEl.innerHTML = "";
    var clone = document.importNode(wrap, true);
    clone.classList.add("sss-hosted");
    clone.classList.remove("box");
    if (clone.style) {
      clone.style.padding = "";
      clone.style.margin = "";
    }
    hostEl.appendChild(clone);

    var panel = hostEl.querySelector("#panel-workspace");
    if (panel) panel.hidden = false;

    hostEl
      .querySelectorAll(".settings-page-only, .back-row")
      .forEach(function (el) {
        el.hidden = true;
      });
    var sheetBlurb = hostEl.querySelector(".settings-sheet-blurb");
    var pageBlurbs = hostEl.querySelectorAll(
      "#blurb, #settings-apply-note, .settings-page-blurb"
    );
    if (sheetBlurb) {
      sheetBlurb.hidden = false;
      sheetBlurb.style.display = "block";
      pageBlurbs.forEach(function (el) {
        el.hidden = true;
      });
    }

    var scripts = Array.from(
      doc.querySelectorAll("#suite-body script:not([src])")
    );
    if (!scripts.length) {
      scripts = Array.from(doc.querySelectorAll("script:not([src])")).filter(
        function (s) {
          return (s.textContent || "").indexOf("panel-workspace") >= 0;
        }
      );
    }
    /* Defer script init one frame so dig rail paints first (feels instant) */
    var run = function () {
      scripts.forEach(function (s) {
        try {
          var el = document.createElement("script");
          el.textContent =
            "(function(){\ntry{\n" +
            s.textContent +
            "\n}catch(e){console.warn('settings dig',e)}\n})();";
          document.body.appendChild(el);
          el.remove();
        } catch (e) {}
      });
    };
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          run();
          /* After hosted scripts run: restore Map mast if they still touch it */
          try {
            if (
              document.documentElement &&
              document.documentElement.classList.contains("suite-map-city") &&
              global.SuiteNav &&
              typeof global.SuiteNav.setMastTitle === "function"
            ) {
              var mast = document.getElementById("mast");
              if (mast && !mast.querySelector(".mast-version")) {
                var folder =
                  localStorage.getItem("suite.cityName") ||
                  sessionStorage.getItem("suite.cityName") ||
                  "Workspace";
                var ver =
                  localStorage.getItem("suite.suiteVersion") ||
                  sessionStorage.getItem("suite.suiteVersion") ||
                  "";
                global.SuiteNav.setMastTitle(
                  mast,
                  String(folder).trim() + " workspace",
                  ver || null
                );
              }
            }
          } catch (eRestore) {}
        });
      });
    } else {
      setTimeout(run, 0);
    }
    try {
      hostEl.scrollTop = 0;
    } catch (eScr) {}
  }

  /**
   * Load settings_v1 payload into a host element (sheet body or Map dig form).
   * Shared by overlay + Map inspect so knobs stay one truth.
   *
   * Dogfood law: browser + memory must not pin stale settings HTML after a
   * suite land. Fetch always uses cache:"no-store". Memory is an 8s debounce
   * only (re-open thrash), not a multi-minute freeze of old knobs.
   */
  function loadSettingsInto(hostEl, href, onErr) {
    if (!hostEl) return;
    var url = href || openHref;
    var now = Date.now();
    if (
      _payloadCache.href === url &&
      _payloadCache.html &&
      now - _payloadCache.at < PAYLOAD_CACHE_MS
    ) {
      try {
        applySettingsHtml(hostEl, _payloadCache.html);
        return;
      } catch (eCache) {
        _payloadCache.html = "";
      }
    }
    hostEl.innerHTML =
      '<div class="sss-skel" aria-busy="true">' +
      '<div class="sss-skel-card"></div>' +
      '<div class="sss-skel-card"></div>' +
      '<div class="sss-skel-card short"></div>' +
      '<p class="sss-muted">Loading knobs…</p></div>';
    fetch(url, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("settings " + r.status);
        return r.text();
      })
      .then(function (html) {
        _payloadCache = { href: url, html: html, at: Date.now() };
        applySettingsHtml(hostEl, html);
      })
      .catch(function (err) {
        if (typeof onErr === "function") onErr(err);
        else {
          hostEl.innerHTML =
            '<p class="sss-err">Could not load settings.</p>' +
            '<p class="sss-muted">' +
            String((err && err.message) || err) +
            "</p>";
        }
      });
  }

  /** Test / hand hook — force next open to re-fetch (suite land, dogfood verify). */
  function bustSettingsPayloadCache() {
    _payloadCache = { href: "", html: "", at: 0 };
  }

  /**
   * scope arg kept for call-site back-compat; pc-666 coerces to workspace.
   * pc-779: Map dig rail preferred when openMapSettingsDig is registered.
   */
  function open(scope, project) {
    scope = "workspace";
    project = (project || "").trim();
    lastScope = scope;
    lastProject = project;
    openHref =
      "/settings_v1.html?scope=workspace" +
      (project ? "&project=" + encodeURIComponent(project) : "");

    /* Toggle: second Settings click closes map dig (do not reload) */
    if (
      typeof global.isMapSettingsDigOpen === "function" &&
      global.isMapSettingsDigOpen()
    ) {
      try {
        if (typeof global.closeMapSettingsDig === "function") {
          global.closeMapSettingsDig();
        }
      } catch (eClose) {}
      setOpen(false);
      return;
    }
    /* Overlay sheet already open → close */
    if (root && !root.hidden) {
      setOpen(false);
      return;
    }

    /* Map: same dig rail as project overview — not a second UI system */
    if (typeof global.openMapSettingsDig === "function") {
      try {
        setOpen(false); /* ensure overlay closed */
      } catch (eOff) {}
      try {
        global.openMapSettingsDig({
          project: project,
          href: openHref,
          load: loadSettingsInto,
        });
        return;
      } catch (eMap) {
        console.warn("settings map dig failed; overlay fallback", eMap);
      }
    }

    ensure();
    if (titleEl) {
      titleEl.textContent = "Workspace";
    }
    setOpen(true);
    loadSettingsInto(bodyEl, openHref, function (err) {
      bodyEl.innerHTML =
        '<p class="sss-err">Could not load settings. ' +
        '<button type="button" class="sss-retry" id="sss-retry">Retry</button></p>' +
        '<p class="sss-muted">' +
        String((err && err.message) || err) +
        "</p>";
      var retry = bodyEl.querySelector("#sss-retry");
      if (retry) {
        retry.addEventListener("click", function () {
          open(lastScope, lastProject);
        });
      }
    });
  }

  /** Cold URL / bookmark: /workspace-map?open=settings&scope=… (pc-661). */
  function consumeDeepLink() {
    try {
      var path = global.location.pathname || "";
      var onMap =
        path === "/workspace-map" ||
        (global.SuiteNav &&
          SuiteNav.isWorkspaceMapPath &&
          SuiteNav.isWorkspaceMapPath(path));
      if (!onMap) return;
      var params = new URLSearchParams(global.location.search || "");
      if ((params.get("open") || "").toLowerCase() !== "settings") return;
      var project = params.get("project") || "";
      open("workspace", project);
      params.delete("open");
      var next = path;
      var left = params.toString();
      if (left) next += "?" + left;
      try {
        history.replaceState(null, "", next + (global.location.hash || ""));
      } catch (eHist) {}
    } catch (e) {}
  }

  /** Map FAB opens the sheet. Spine /settings goes to the view (pc-1267). */
  function install() {
    if (install._done) return;
    install._done = true;
    document.addEventListener(
      "click",
      function (e) {
        if (e.defaultPrevented) return;
        var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
        if (!a) return;
        if (a.getAttribute("data-suite-full") === "1") return;
        /* Cmd-click FAB → /settings view */
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        var href = a.getAttribute("href") || "";
        if (!href) return;
        var path = "";
        var search = "";
        try {
          var u = new URL(href, global.location.origin);
          if (u.origin !== global.location.origin) return;
          path = u.pathname;
          search = u.search || "";
        } catch (err) {
          return;
        }
        if (path !== "/settings") return;
        var isFab =
          a.id === "nav-settings" ||
          (a.classList && a.classList.contains("map-settings-fab"));
        if (!isFab) return;
        e.preventDefault();
        e.stopPropagation();
        var params = new URLSearchParams(search);
        open(params.get("scope") || "workspace", params.get("project") || "");
      },
      true
    );
    consumeDeepLink();
  }

  /* CSS once — overlay shell + Map dig host (#inspect-form.inspect-settings-host) */
  function injectCss() {
    /* Bump id when glass tokens change so hard refresh isn't the only path */
    var cssId = "suite-settings-sheet-css-v7-dig-scroll";
    [
      "suite-settings-sheet-css",
      "suite-settings-sheet-css-v2-glass",
      "suite-settings-sheet-css-v3-cards",
      "suite-settings-sheet-css-v4-hand-glyph",
      "suite-settings-sheet-css-v5-glyph-preset",
      "suite-settings-sheet-css-v6-seat-name",
    ].forEach(
      function (id) {
        var old = document.getElementById(id);
        if (old && old.parentNode) old.parentNode.removeChild(old);
      }
    );
    if (document.getElementById(cssId)) return;
    var s = document.createElement("style");
    s.id = cssId;
    /* Host knobs: .sss-body (overlay) and .inspect-settings-host (Map dig) */
    var H = ".sss-body,.inspect-settings-host";
    s.textContent =
      "html.suite-settings-open{overflow:hidden}" +
      ".suite-settings-sheet{position:fixed;inset:0;z-index:9200;pointer-events:none}" +
      ".suite-settings-sheet.on{pointer-events:auto}" +
      ".suite-settings-sheet[hidden]{display:none!important}" +
      ".sss-bg{position:absolute;left:0;right:0;bottom:0;top:var(--suite-head-offset,52px);" +
      "background:rgba(20,18,14,.28);opacity:0;transition:opacity .18s}" +
      ".suite-settings-sheet.on .sss-bg{opacity:1}" +
      ".sss-panel{position:absolute;top:var(--suite-head-offset,52px);right:0;bottom:0;" +
      "width:min(28rem,100%);max-width:100%;" +
      "background:var(--card,#fffdf8);color:var(--ink,#1a1814);" +
      "border-left:1px solid var(--line-faint,var(--border,#c4b8a4));" +
      "box-shadow:-8px 0 28px rgba(0,0,0,.12);display:flex;flex-direction:column;" +
      "overflow:hidden;min-height:0;" +
      "font-family:inherit;font-size:var(--type-body);line-height:1.4;" +
      "transform:translateX(8px);opacity:0;transition:transform .18s,opacity .18s}" +
      ".suite-settings-sheet.on .sss-panel{transform:none;opacity:1}" +
      ".sss-head{flex:0 0 auto;display:flex;flex-wrap:wrap;align-items:flex-start;gap:8px 12px;" +
      "padding:14px 16px 10px;border-bottom:1px solid var(--line-faint,var(--border,#c4b8a4));" +
      "background:var(--card,#fffdf8);z-index:1}" +
      ".sss-kicker{width:100%;font-size:var(--type-caption);letter-spacing:.14em;text-transform:uppercase;opacity:.5;margin-bottom:2px}" +
      ".sss-head h2{margin:0;flex:1 1 auto;min-width:0;font-size:var(--type-heading);font-weight:var(--weight-medium);letter-spacing:.03em;line-height:1.25}" +
      ".sss-actions{display:flex;align-items:center;gap:10px;flex:0 0 auto;margin-left:auto}" +
      ".sss-x{font:inherit;font-size:var(--type-display);line-height:1;border:0;background:transparent;cursor:pointer;" +
      "color:inherit;opacity:.65;padding:0 4px}" +
      ".sss-x:hover{opacity:1}" +
      ".sss-body{flex:1 1 auto;min-height:0;overflow:auto;-webkit-overflow-scrolling:touch;padding:10px 12px 28px}" +
      /* Skeleton while first fetch */ +
      ".sss-skel{display:flex;flex-direction:column;gap:10px}" +
      ".sss-skel-card{height:72px;border-radius:10px;border:1px solid color-mix(in srgb,var(--ink,#2a241c) 10%,transparent);" +
      "background:linear-gradient(90deg,color-mix(in srgb,var(--ink,#2a241c) 4%,transparent) 0%," +
      "color-mix(in srgb,var(--finder-blue,#007AFF) 8%,transparent) 50%," +
      "color-mix(in srgb,var(--ink,#2a241c) 4%,transparent) 100%);background-size:200% 100%;" +
      "animation:sss-shimmer 1.1s ease-in-out infinite}" +
      ".sss-skel-card.short{height:48px;width:70%}" +
      "@keyframes sss-shimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}" +
      H +
      " .wrap," +
      H +
      " .wrap.sss-hosted{max-width:none;margin:0;padding:0;border:0;background:transparent;box-shadow:none}" +
      H +
      " .settings-page-only[hidden]," +
      H +
      " .back-row[hidden]{display:none!important}" +
      H +
      " .settings-sheet-blurb{font-size:var(--type-caption);opacity:.55;margin:0 0 10px;line-height:1.35}" +
      /* Section cards — map glass density */ +
      H +
      " .settings-card{margin:0 0 10px;padding:10px 12px 12px;" +
      "border:1px solid color-mix(in srgb,var(--ink,#2a241c) 12%,transparent);" +
      "border-radius:10px;background:color-mix(in srgb,var(--card,#fffdf8) 88%,#f0ebe0 12%);" +
      "box-shadow:0 1px 0 color-mix(in srgb,var(--ink,#2a241c) 4%,transparent)}" +
      H +
      " .settings-card>h3,.settings-card .settings-card-h{" +
      "margin:0 0 8px;padding:0 0 6px;border-bottom:1px solid color-mix(in srgb,var(--ink,#2a241c) 8%,transparent);" +
      "font-size:var(--type-caption);letter-spacing:.12em;text-transform:uppercase;" +
      "opacity:.72;color:var(--ink,#2a241c);font-weight:var(--weight-medium)}" +
      H +
      " .panel>h3{display:none}" + /* bare h3 retired when cards wrap sections */
      H +
      " .knob-block,.setting-row{margin:0 0 8px}" +
      H +
      " .setting-row{display:grid;justify-items:stretch;gap:4px}" +
      H +
      " .setting-row>.setting-control," +
      H +
      " .setting-row>select," +
      H +
      " .setting-row>input," +
      H +
      " .setting-row>button{justify-self:stretch}" +
      H +
      " .knob-lab,.setting-label{display:block;margin:0 0 3px;font-size:var(--type-label);" +
      "font-weight:var(--weight-medium);opacity:.88;letter-spacing:.02em}" +
      H +
      " .setting-help,.theme-note,.note{font-size:var(--type-caption);opacity:.52;line-height:1.35;margin:2px 0 0}" +
      H +
      " .state-chip, .status-pill{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;" +
      "border-radius:999px;font-size:var(--type-caption);letter-spacing:.04em;font-weight:var(--weight-medium);" +
      "border:1px solid color-mix(in srgb,var(--ink,#2a241c) 14%,transparent);" +
      "background:color-mix(in srgb,var(--card,#fffdf8) 92%,transparent)}" +
      H +
      " .status-pill.is-up,.state-chip.is-up{color:#1f6b3a;border-color:color-mix(in srgb,#2e7d4f 45%,transparent);" +
      "background:color-mix(in srgb,#2e7d4f 14%,var(--card,#fffdf8))}" +
      H +
      " .status-pill.is-down,.state-chip.is-down{color:#8a2e22;border-color:color-mix(in srgb,#a33327 45%,transparent);" +
      "background:color-mix(in srgb,#a33327 12%,var(--card,#fffdf8))}" +
      H +
      " .status-pill.is-checking,.state-chip.is-checking,.state-chip.is-loading{" +
      "color:#7a5a10;border-color:color-mix(in srgb,#c9a227 40%,transparent);" +
      "background:color-mix(in srgb,#c9a227 14%,var(--card,#fffdf8))}" +
      H +
      " .status-pill.is-ready,.state-chip.is-ready{color:#1f6b3a;border-color:color-mix(in srgb,#2e7d4f 40%,transparent);" +
      "background:color-mix(in srgb,#2e7d4f 12%,var(--card,#fffdf8))}" +
      H +
      " .engine-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px;margin:0 0 8px;" +
      "padding:8px 10px;border-radius:8px;" +
      "border:1px solid color-mix(in srgb,var(--ink,#2a241c) 10%,transparent);" +
      "background:color-mix(in srgb,var(--card,#fffdf8) 96%,transparent)}" +
      H +
      " .engine-row .engine-name{font-size:var(--type-label);font-weight:var(--weight-medium);min-width:5.5em}" +
      H +
      " .engine-row .mono{margin:0;flex:1 1 auto;min-width:0;padding:5px 8px;font-size:var(--type-caption)}" +
      H +
      " .theme-seg,.paint-seg{display:flex;flex-wrap:nowrap;width:100%;overflow:hidden;" +
      "border:1px solid color-mix(in srgb,var(--ink,#2a241c) 14%,transparent);" +
      "border-radius:8px;background:color-mix(in srgb,var(--card,#fffdf8) 96%,transparent)}" +
      H +
      " .theme-seg label,.paint-seg label{flex:1 1 0;min-width:0;margin:0;cursor:pointer}" +
      H +
      " .theme-seg input,.paint-seg input{position:absolute;opacity:0;pointer-events:none;width:0;height:0;margin:0}" +
      H +
      " .theme-seg span,.paint-seg span{display:block;text-align:center;padding:8px 8px;" +
      "font-size:var(--type-caption);letter-spacing:.06em;text-transform:uppercase;" +
      "color:color-mix(in srgb,var(--ink,#2a241c) 70%,transparent);" +
      "border-right:1px solid color-mix(in srgb,var(--ink,#2a241c) 10%,transparent);" +
      "background:transparent;transition:background .12s ease,color .12s ease}" +
      H +
      " .theme-seg label:last-child span,.paint-seg label:last-child span{border-right:none}" +
      H +
      " .theme-seg label:hover span,.paint-seg label:hover span{color:var(--finder-blue,#007AFF);" +
      "background:color-mix(in srgb,var(--finder-blue,#007AFF) 7%,transparent)}" +
      H +
      " .theme-seg input:checked + span,.paint-seg input:checked + span{" +
      "color:var(--ink,#2a241c);font-weight:var(--weight-medium);" +
      "background:color-mix(in srgb,var(--finder-blue,#007AFF) 16%,var(--card,#fffdf8));" +
      "box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--finder-blue,#007AFF) 40%,transparent)}" +
      H +
      /* pc-898: one chip size for You / agent / stack faces */
      " .glyph-presets,.hand-glyph-presets{display:flex;flex-wrap:wrap;gap:6px;margin:0}" +
      H +
      " .glyph-preset,.hand-glyph-preset,.you-glyph-preset{" +
      "width:2.25rem;height:2.25rem;min-width:2.25rem;min-height:2.25rem;box-sizing:border-box;" +
      "padding:0!important;font-size:var(--type-heading);letter-spacing:0;text-transform:none;" +
      "border-radius:8px!important;line-height:1;display:inline-flex!important;" +
      "align-items:center;justify-content:center}" +
      H +
      " .glyph-preset.is-on,.glyph-preset[aria-pressed=\"true\"]," +
      " .hand-glyph-preset.is-on,.hand-glyph-preset[aria-pressed=\"true\"]," +
      " .you-glyph-preset.is-on,.you-glyph-preset[aria-pressed=\"true\"]{" +
      "border-color:var(--finder-blue,#007AFF)!important;color:inherit!important;" +
      "box-shadow:0 0 0 2px color-mix(in srgb,var(--finder-blue,#007AFF) 28%,transparent)}" +
      H +
      /* pc-994: dashed outline marks the shipped default chip across all pickers */
      " .glyph-preset[data-is-default=\"true\"]{" +
      "outline:1.5px dashed color-mix(in srgb,var(--ink,#2a241c) 28%,transparent);outline-offset:2px}" +
      H +
      /* pc-1000: seat name is a normal themed text input, not an emoji chip input */
      " .seat-name-input{width:min(100%,11rem);padding:6px 10px;font:inherit;font-size:var(--type-body);" +
      "text-align:left;border:1px solid color-mix(in srgb,var(--ink,#2a241c) 14%,transparent);" +
      "border-radius:8px;background:color-mix(in srgb,var(--card,#fffdf8) 96%,transparent);color:var(--ink,#2a241c)}" +
      H +
      " .seat-name-input:focus{outline:none;border-color:var(--finder-blue,#007AFF);" +
      "box-shadow:0 0 0 2px color-mix(in srgb,var(--finder-blue,#007AFF) 22%,transparent)}" +
      H +
      " .glyph-custom,.hand-glyph-custom{display:flex;align-items:center;gap:8px;font-size:var(--type-caption)}" +
      H +
      " .glyph-custom .dim,.hand-glyph-custom .dim{opacity:.55}" +
      H +
      " .glyph-custom input,.hand-glyph-custom input{width:3.25rem;padding:6px 6px;font-size:var(--type-heading);text-align:center;" +
      "border:1px solid color-mix(in srgb,var(--ink,#2a241c) 14%,transparent);border-radius:8px;" +
      "background:color-mix(in srgb,var(--card,#fffdf8) 96%,transparent);color:var(--ink,#2a241c)}" +
      H +
      " .stack-glyph-rows{display:flex;flex-direction:column;gap:10px}" +
      H +
      " .stack-glyph-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px}" +
      H +
      " .stack-glyph-row>.stack-glyph-lab{min-width:5.75rem;font-size:var(--type-caption);opacity:.55}" +
      H +
      " .mono{display:block;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;" +
      "font-size:var(--type-caption);word-break:break-all;padding:7px 9px;" +
      "border:1px solid color-mix(in srgb,var(--ink,#2a241c) 12%,transparent);" +
      "border-radius:8px;background:color-mix(in srgb,var(--card,#fffdf8) 94%,transparent);margin:0}" +
      H +
      " .actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0}" +
      H +
      " button,.link-btn{font:inherit;font-size:var(--type-caption);letter-spacing:.05em;text-transform:uppercase;" +
      "padding:6px 12px;border:1px solid color-mix(in srgb,var(--ink,#2a241c) 16%,transparent);" +
      "border-radius:8px;background:color-mix(in srgb,var(--card,#fffdf8) 96%,transparent);" +
      "color:var(--ink,#2a241c);cursor:pointer;text-decoration:none;display:inline-block}" +
      H +
      " button:hover,.link-btn:hover{border-color:var(--finder-blue,#007AFF);color:var(--finder-blue,#007AFF)}" +
      H +
      " button.primary{background:color-mix(in srgb,var(--finder-blue,#007AFF) 14%,var(--card,#fffdf8));" +
      "color:var(--finder-blue,#007AFF);border-color:color-mix(in srgb,var(--finder-blue,#007AFF) 48%,transparent)}" +
      H +
      " ul.knob-list{list-style:none;padding:0;margin:0;border-radius:8px;overflow:hidden;" +
      "border:1px solid color-mix(in srgb,var(--ink,#2a241c) 12%,transparent)}" +
      H +
      " ul.knob-list li{display:flex;justify-content:space-between;align-items:center;gap:10px;" +
      "padding:7px 10px;border-bottom:1px solid color-mix(in srgb,var(--ink,#2a241c) 8%,transparent);" +
      "font-size:var(--type-label);background:color-mix(in srgb,var(--card,#fffdf8) 96%,transparent)}" +
      H +
      " ul.knob-list li:last-child{border-bottom:none}" +
      H +
      " .empty{font-size:var(--type-caption);opacity:.6;padding:8px 10px;" +
      "border:1px dashed color-mix(in srgb,var(--ink,#2a241c) 16%,transparent);border-radius:8px}" +
      /* pc-1013: dig host scrolls like .sss-body — lower knobs were clipped */
      ".inspect-settings-host{margin:0 0 8px;min-height:0;overflow-y:auto;" +
      "-webkit-overflow-scrolling:touch}" +
      ".sss-muted{opacity:.55;font-size:var(--type-caption)}" +
      ".sss-err{color:#a33;font-size:var(--type-body)}" +
      ".sss-retry{font:inherit;font-size:var(--type-body);margin-left:6px;cursor:pointer;" +
      "text-decoration:underline;background:transparent;border:0;color:inherit;padding:0}";
    document.head.appendChild(s);
  }

  injectCss();

  global.SuiteSettingsSheet = {
    open: open,
    close: close,
    isOpen: isOpen,
    install: install,
    consumeDeepLink: consumeDeepLink,
    loadSettingsInto: loadSettingsInto,
    bustSettingsPayloadCache: bustSettingsPayloadCache,
  };

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", install);
    } else {
      install();
    }
  }
})(typeof window !== "undefined" ? window : globalThis);
