/**
 * suite-nav.js — peer door law: Overview · Map first-user (+ deep pages)
 * pc-1266: four-lens spine (Overview · Map · Calendar · Settings) is the
 * shell chrome. Work orders / Agents / Files stay absorbed, not spine items.
 * pc-1267: /settings is the Settings spine view.
 * pc-1274: Map corner Settings FAB retired; Calendar plants the same spine.
 * pc-376: Desk / Agents are deep-link only — not mast peers.
 *
 * Axes (two-axis wayfinding — view doors ≠ place path):
 *   Place = Explorer (workspace only) | Home (project / folder)
 *   View  = place | desk | roster  (internal place id stays "map" for APIs;
 *           "home" is accepted as an alias; chrome label for roster = Agents)
 *   Scope = workspace (no project) | project (?project=slug)
 *   Seat  = You (default Desk) | agent (?worker=) | person file
 *   Path  = place-only drill (&path=…) — NEVER on Desk/Agents peer doors
 * Peer doors change VIEW and preserve SCOPE.
 * Climbing out of a project is breadcrumb / workspace name, not the place door.
 * Context strip (#suite-context) always shows Workspace › Project › View › Seat.
 *
 * Law (2026-07-24): ship dig-in is **Workspace map** only (`/workspace-map`).
 * Retired peer URLs 302 → Map: /skin /map /explorer /desk /roster /agents /ported /home.
 * Project Files (`/home?project=`) is absorbed — Map is the door (pc-1278).
 */
(function (global) {
  /* pc-1396: /esc.js is the classic boot. Calendar HTML is rendered from an
   * imported Python module, so a live serve without kickstart can miss the
   * tag — publish the same algorithm onto __bp if the boot did not run. */
  if (!(global.__bp && typeof global.__bp.esc === "function")) {
    global.__bp = global.__bp || {};
    global.__bp.esc = function (s) {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    };
    global.__bp.escAttr = function (s) {
      return global.__bp.esc(s).replace(/`/g, "&#96;");
    };
  }

  /**
   * Suite appearance preference (pc-324).
   * Values: "system" | "light" | "dark". Default system → CSS prefers-color-scheme.
   * Manual light/dark sets html[data-theme]; system removes it so media query wins.
   * Soft-nav swaps #suite-body only — theme lives on <html>, so body swap cannot
   * leave mixed theme.
   *
   * Migration: legacy Office key protocolcity-theme (light|dark) is read once into
   * suite.theme and removed so the two keys never fight.
   */
  var THEME_KEY = "suite.theme";
  var LEGACY_THEME_KEY = "protocolcity-theme";
  var THEME_VALUES = { system: 1, light: 1, dark: 1 };

  function enc(s) {
    return encodeURIComponent(s || "");
  }

  /**
   * Suite package version from /api/city (suite_version | version).
   * Mast: strong folder title + quieter version chip (like Powered by label).
   */
  function suiteVersionLabel(cityOrVersion) {
    var v = "";
    if (cityOrVersion && typeof cityOrVersion === "object") {
      v = cityOrVersion.suite_version || cityOrVersion.version || "";
    } else if (cityOrVersion != null) {
      v = cityOrVersion;
    }
    v = String(v || "").trim();
    if (!v || v === "unknown" || v === "not-installed") return "";
    if (v.charAt(0) !== "v" && /^\d/.test(v)) v = "v" + v;
    return v;
  }

  /** Plain string for mast parking (version chip); not the browser tab brand. */
  function mastWithVersion(baseTitle, cityOrVersion) {
    var base = String(baseTitle || "").trim() || "Workspace";
    var ver = suiteVersionLabel(cityOrVersion);
    return ver ? base + " · " + ver : base;
  }

  /**
   * Browser tab title (pc-710): BluePrint — {Workspace} [· view gloss].
   * Mast may still credit ProtocolCity as the powering engine; tabs never
   * lead with bare ProtocolCity / PC.
   */
  function docTitle(workspace, viewGloss) {
    var ws = String(workspace == null ? "" : workspace).trim() || "Workspace";
    var gloss = viewGloss == null ? "" : String(viewGloss).trim();
    var base = "BluePrint — " + ws;
    return gloss ? base + " · " + gloss : base;
  }

  /**
   * Workspace folder for first paint (pc-1383). Map caches suite.cityName;
   * person/ticket hops reuse it so crumbs never flash civic "City".
   * Rejects empty, "developer", and the retired "City" fallback.
   */
  function workspaceFolderLabel(explicit) {
    var n = String(explicit == null ? "" : explicit).trim();
    if (n && !isRetiredWorkspaceFolder(n)) return n;
    try {
      n =
        (typeof sessionStorage !== "undefined" &&
          sessionStorage.getItem("suite.cityName")) ||
        (typeof localStorage !== "undefined" &&
          localStorage.getItem("suite.cityName")) ||
        "";
    } catch (e) {
      n = "";
    }
    n = String(n || "").trim();
    if (!n || isRetiredWorkspaceFolder(n)) return "Workspace";
    return n;
  }

  function isRetiredWorkspaceFolder(name) {
    var n = String(name || "").trim().toLowerCase();
    return n === "city" || n === "developer";
  }

  /**
   * Spine / tab paint (pc-1291). Cyanotype is the shipped default (pc-1285).
   * Cream is the paper-folder twin. Preference lives in this browser only.
   */
  var PAINT_KEY = "suite.spinePaint";
  var PAINT_VALUES = { cyanotype: 1, cream: 1 };
  var SPINE_MARK_VERSION = "pc-1291";
  var SPINE_MARK = {
    cyanotype: "/brand/mark-cyanotype.svg?v=" + SPINE_MARK_VERSION,
    cream: "/brand/mark-cream.svg?v=" + SPINE_MARK_VERSION,
  };
  var SPINE_FAVICON = {
    cyanotype: "/brand/favicon.svg?v=" + SPINE_MARK_VERSION,
    cream: "/brand/mark-cream.svg?v=" + SPINE_MARK_VERSION,
  };
  var SPINE_MARK_SRC = SPINE_MARK.cyanotype;

  function normalizePaintPref(v) {
    v = String(v || "").toLowerCase().trim();
    return PAINT_VALUES[v] ? v : "cyanotype";
  }

  function getSpinePaintPref() {
    try {
      if (global.localStorage) {
        return normalizePaintPref(global.localStorage.getItem(PAINT_KEY));
      }
    } catch (e) {
      /* private mode / denied */
    }
    return "cyanotype";
  }

  function spineMarkSrc(pref) {
    return SPINE_MARK[normalizePaintPref(pref)];
  }

  function spineFaviconSrc(pref) {
    return SPINE_FAVICON[normalizePaintPref(pref)];
  }

  function applySpinePaint(pref) {
    pref = normalizePaintPref(pref == null ? getSpinePaintPref() : pref);
    if (typeof document === "undefined") return pref;
    try {
      document.documentElement.setAttribute("data-spine-paint", pref);
    } catch (eRoot) {}
    var markSrc = spineMarkSrc(pref);
    var favSrc = spineFaviconSrc(pref);
    var marks = document.querySelectorAll(".suite-spine-mark");
    Array.prototype.forEach.call(marks, function (img) {
      if (img.getAttribute("src") !== markSrc) img.setAttribute("src", markSrc);
    });
    var icon = document.querySelector('link[rel="icon"]');
    if (icon && icon.getAttribute("href") !== favSrc) {
      icon.setAttribute("href", favSrc);
    }
    SPINE_MARK_SRC = markSrc;
    return pref;
  }

  function setSpinePaintPref(pref) {
    pref = normalizePaintPref(pref);
    try {
      if (global.localStorage) global.localStorage.setItem(PAINT_KEY, pref);
    } catch (e) {
      /* ignore */
    }
    return applySpinePaint(pref);
  }

  function spineLockupHTML() {
    return (
      '<a class="suite-spine-lockup" href="/" aria-label="BluePrint">' +
      '<img class="suite-spine-mark" src="' +
      spineMarkSrc() +
      '" width="64" height="52" alt="">' +
      '<span class="suite-spine-word">BluePrint</span></a>'
    );
  }

  function ensureSpineLockup(brand) {
    if (!brand) return;
    if (!brand.querySelector(".suite-spine-lockup")) {
      brand.innerHTML = spineLockupHTML();
    }
    applySpinePaint();
  }

  /**
   * pc-1285: spine is mark + BluePrint. Version lives in Settings → About
   * (was a pill on the brand seat that read as a build stamp).
   */
  function paintSpineVersion(cityOrVersion) {
    if (typeof document === "undefined") return;
    var brand = document.querySelector(".suite-spine-brand");
    if (brand) ensureSpineLockup(brand);
    var ver = suiteVersionLabel(cityOrVersion);
    if (!ver) {
      try {
        ver = suiteVersionLabel(
          localStorage.getItem("suite.suiteVersion") ||
            sessionStorage.getItem("suite.suiteVersion") ||
            ""
        );
      } catch (e) {
        ver = "";
      }
    }
    if (ver) {
      try {
        localStorage.setItem("suite.suiteVersion", ver);
        sessionStorage.setItem("suite.suiteVersion", ver);
      } catch (eStore) {}
    }
    if (brand) {
      var chip = brand.querySelector(".mast-version");
      if (chip && chip.parentNode) chip.parentNode.removeChild(chip);
    }
  }

  /**
   * Paint #mast with the page name only. Version → Settings About.
   */
  function setMastTitle(el, baseTitle, cityOrVersion) {
    var base = String(baseTitle || "").trim() || "Workspace";
    var ver = suiteVersionLabel(cityOrVersion);
    var plain = base;
    paintSpineVersion(cityOrVersion);
    if (!el) return plain;
    el.textContent = "";
    el.classList.remove("mast-has-version");
    var name = document.createElement("span");
    name.className = "mast-name";
    name.textContent = base;
    el.appendChild(name);
    try {
      el.setAttribute("data-mast-plain", plain);
    } catch (e) {}
    return plain;
  }

  /**
   * Open a workspace-relative path (or abs under city root) in Finder.
   * Empty path = workspace root. Folder viewer truth: audit real disk contents.
   */
  function openInFinder(relOrAbs, project) {
    var path = relOrAbs == null ? "" : String(relOrAbs);
    var payload = { path: path };
    /* pc-1209: project hint lets the server resolve project-relative paths */
    if (project) payload.project = String(project);
    return fetch("/api/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error((d && d.error) || r.statusText);
        return d;
      });
    });
  }

  function wireFinderOpens(root) {
    if (typeof document === "undefined") return;
    var scope = root || document;
    var nodes = scope.querySelectorAll
      ? scope.querySelectorAll("[data-open-path]")
      : [];
    Array.prototype.forEach.call(nodes, function (el) {
      if (el._finderWired) return;
      el._finderWired = true;
      el.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        var p = el.getAttribute("data-open-path");
        openInFinder(p == null ? "" : p).catch(function (err) {
          if (typeof console !== "undefined") {
            console.warn("openInFinder:", err && err.message ? err.message : err);
          }
        });
      });
    });
  }

  function normalizeThemePref(v) {
    v = String(v || "").toLowerCase().trim();
    return THEME_VALUES[v] ? v : "system";
  }

  function getThemePref() {
    try {
      if (global.localStorage) {
        var v = global.localStorage.getItem(THEME_KEY);
        if (v && THEME_VALUES[v]) return v;
        var legacy = global.localStorage.getItem(LEGACY_THEME_KEY);
        if (legacy === "light" || legacy === "dark") {
          try {
            global.localStorage.setItem(THEME_KEY, legacy);
            global.localStorage.removeItem(LEGACY_THEME_KEY);
          } catch (e2) {
            /* ignore write failures */
          }
          return legacy;
        }
      }
    } catch (e) {
      /* private mode / denied */
    }
    return "system";
  }

  /**
   * Apply preference to <html>. "system" clears data-theme so CSS media applies.
   * data-theme-pref always records the stored choice (for Settings UI).
   */
  function applyTheme(pref) {
    pref = normalizeThemePref(pref == null ? getThemePref() : pref);
    if (typeof document === "undefined" || !document.documentElement) return pref;
    var root = document.documentElement;
    root.setAttribute("data-theme-pref", pref);
    if (pref === "light" || pref === "dark") {
      root.setAttribute("data-theme", pref);
    } else {
      root.removeAttribute("data-theme");
    }
    return pref;
  }

  function setThemePref(pref) {
    pref = normalizeThemePref(pref);
    try {
      if (global.localStorage) global.localStorage.setItem(THEME_KEY, pref);
    } catch (e) {
      /* ignore */
    }
    return applyTheme(pref);
  }

  function installThemeListener() {
    if (typeof document === "undefined") return;
    if (installThemeListener._done) return;
    installThemeListener._done = true;
    applyTheme(getThemePref());
    try {
      var mq =
        global.matchMedia && global.matchMedia("(prefers-color-scheme: dark)");
      if (!mq) return;
      var onChange = function () {
        if (getThemePref() === "system") applyTheme("system");
      };
      if (typeof mq.addEventListener === "function") {
        mq.addEventListener("change", onChange);
      } else if (typeof mq.addListener === "function") {
        mq.addListener(onChange);
      }
    } catch (e) {
      /* ignore */
    }
  }

  /* Apply before paint when script is in <head> — avoids wrong-theme flash for overrides. */
  installThemeListener();
  if (typeof document !== "undefined") {
    var bootVer = function () {
      paintSpineVersion();
      applySpinePaint();
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bootVer);
    } else {
      bootVer();
    }
  }

  function projectFromSearch() {
    try {
      return new URLSearchParams(global.location.search).get("project") || "";
    } catch (e) {
      return "";
    }
  }

  /** First path segment under city root if it looks like a project folder. */
  function projectFromCityPath(relPath) {
    if (!relPath) return "";
    const parts = String(relPath).replace(/^\/+/, "").split("/").filter(Boolean);
    if (!parts.length) return "";
    const top = parts[0];
    if (top.indexOf(".") !== -1) return ""; // root file e.g. AGENTS.md
    return top;
  }

  function cityMapHref() {
    return "/workspace-map";
  }

  /**
   * Workspace map — hierarchy folder dig-in. Canonical URL: /workspace-map only.
   */
  function workspaceMapHref() {
    return "/workspace-map";
  }

  function normPath(path) {
    return String(path || "").split("?")[0] || "";
  }

  function isWorkspaceMapPath(path) {
    return normPath(path) === "/workspace-map";
  }

  /** User-facing place door: Map (Files / project Home absorbed, pc-1278). */
  function placeLabel(project) {
    return "Map";
  }

  /**
   * Canonical place URL — Map is the door (pc-1278 / pc-1377).
   * Workspace → `/workspace-map`.
   * Project → `/workspace-map?project=` (+ optional &path=).
   * Do not mint retired `/home?project=` (that route 302s here).
   */
  function placeHref(project, path) {
    project = (project || "").trim();
    path = (path || "").replace(/^\/+|\/+$/g, "");
    if (!project) return cityMapHref();
    let u = workspaceMapHref() + "?project=" + enc(project);
    if (path) u += "&path=" + enc(path);
    return u;
  }

  /**
   * Map dig-in with project focus (folder panel on hierarchy Map).
   * Use for “show on Map” — not for Overview project-table names.
   */
  function projectEntryHref(project) {
    project = (project || "").trim();
    if (!project) return workspaceMapHref();
    return workspaceMapHref() + "?project=" + enc(project);
  }

  /**
   * Project brief — Map with project focus (Overview URL retired)
   * Overview Projects table names use this (not projectEntryHref / Map).
   */
  function projectBriefHref(project) {
    project = (project || "").trim();
    if (!project) return workspaceMapHref();
    return workspaceMapHref() + "?project=" + enc(project);
  }

  /**
   * Scope URL inside the current room (pc-264): crumbs change city/project
   * without switching Explorer ↔ Desk ↔ Agents.
   */
  /**
   * Workspace Home — Overview landing (pc-1299). Map stays /workspace-map.
   */
  function workspaceHomeHref() {
    return spineOverviewHref();
  }

  /** Settings URL — Workspace spine view (pc-1267; scope arg ignored). */
  function settingsHref(scope, project) {
    let u = "/settings?scope=workspace";
    project = (project || "").trim();
    if (project) u += "&project=" + enc(project);
    return u;
  }

  function isSettingsPath(path) { return normPath(path) === "/settings"; }
  function isCalendarPath(path) { return normPath(path) === "/calendar"; }
  function isWallPath(path) {
    var p = normPath(path);
    return p === "/wall.html" || p === "/wall" || p === "/" || p === "/overview";
  }
  function isPersonPath(path) { return normPath(path) === "/person"; }
  function isTicketPath(path) { return normPath(path) === "/ticket"; }
  function isReadPath(path) { return normPath(path) === "/read"; }

  function isSpineDigPath(path) {
    return (
      isPersonPath(path) ||
      isTicketPath(path) ||
      isReadPath(path)
    );
  }

  /**
   * pc-1299: Overview is the landing. `/` and `/overview` serve Wall density.
   * `/wall.html` remains a file alias.
   */
  function spineOverviewHref() {
    return "/overview";
  }

  var SPINE_LENSES = [
    { id: "spine-overview", href: "/overview", label: "Overview", lens: "overview" },
    { id: "spine-map", href: "/workspace-map", label: "Map", lens: "map" },
    { id: "spine-calendar", href: "/calendar", label: "Calendar", lens: "calendar" },
    { id: "spine-settings", href: "/settings", label: "Settings", lens: "settings" },
  ];

  function spineLensFromLocation() {
    var path = "";
    var search = "";
    try {
      path = (global.location && global.location.pathname) || "";
      search = (global.location && global.location.search) || "";
    } catch (eLoc) {
      return "";
    }
    var p = String(path).split("?")[0] || "";
    if (p === "/calendar" || p === "/calendar.ics") return "calendar";
    if (p === "/settings") return "settings";
    if (/(?:^|[?&])open=settings(?:&|$)/.test(String(search))) return "settings";
    if (isWallPath(p)) return "overview";
    if (isWorkspaceMapPath(p)) return "map";
    return "";
  }

  function spineHrefLens(href) {
    var raw = String(href || "");
    var path = raw.split("?")[0] || "";
    if (path === "/calendar" || path === "/calendar.ics") return "calendar";
    if (path === "/settings") return "settings";
    if (isWallPath(path)) return "overview";
    if (isWorkspaceMapPath(path)) return "map";
    return "";
  }

  function markSpineHere(root) {
    if (!root) return;
    var here = spineLensFromLocation();
    var links = root.querySelectorAll("a");
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      var lens =
        a.getAttribute("data-spine-lens") || spineHrefLens(a.getAttribute("href"));
      var on = !!here && lens === here;
      a.classList.toggle("here", on);
      if (on) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    }
  }

  /**
   * Persistent four-lens spine. Wall already ships aside.spine (pc-1265);
   * Map paints #suite-spine in workspace_map.html; Settings plants the same
   * rail (pc-1267). Not a Desk/Roster revival.
   */
  function ensureSpine() {
    if (typeof document === "undefined" || !document.body) return null;
    var wallSpine = document.querySelector("aside.spine");
    if (wallSpine || (document.body.classList && document.body.classList.contains("wall"))) {
      try {
        document.documentElement.classList.add("suite-has-spine");
      } catch (eWall) {}
      markSpineHere(wallSpine);
      return wallSpine;
    }
    var aside = document.getElementById("suite-spine");
    var pathNow =
      typeof location !== "undefined" ? location.pathname : "";
    var onMap = isWorkspaceMapPath(pathNow);
    var onSettings = isSettingsPath(pathNow);
    var onCalendar = isCalendarPath(pathNow);
    var onWall = isWallPath(pathNow);
    var onPerson = isSpineDigPath(pathNow);
    if (!aside && !onMap && !onSettings && !onCalendar && !onWall && !onPerson) return null;
    if (!aside) {
      aside = document.createElement("aside");
      aside.id = "suite-spine";
      aside.className = "suite-spine";
      aside.setAttribute("aria-label", "BluePrint");
      var brand = document.createElement("div");
      brand.className = "suite-spine-brand";
      brand.innerHTML = spineLockupHTML();
      var nav = document.createElement("nav");
      nav.setAttribute("aria-label", "Lenses");
      for (var i = 0; i < SPINE_LENSES.length; i++) {
        var item = SPINE_LENSES[i];
        var a = document.createElement("a");
        a.id = item.id;
        a.href = item.href;
        a.textContent = item.label;
        a.setAttribute("data-spine-lens", item.lens);
        nav.appendChild(a);
      }
      var hint = document.createElement("p");
      hint.className = "suite-spine-hint";
      var hintA = document.createElement("a");
      hintA.href = "https://github.com/protocolcity/BluePrint";
      hintA.target = "_blank";
      hintA.rel = "noopener";
      var bolt = document.createElement("span");
      bolt.className = "suite-powered-bolt";
      bolt.setAttribute("aria-hidden", "true");
      bolt.textContent = "⚡";
      var lab = document.createElement("span");
      lab.className = "suite-powered-label";
      lab.textContent = "Powered by";
      var nam = document.createElement("span");
      nam.className = "suite-powered-name";
      nam.textContent = "ProtocolCity";
      hintA.appendChild(bolt);
      hintA.appendChild(lab);
      hintA.appendChild(nam);
      hint.appendChild(hintA);
      aside.appendChild(brand);
      aside.appendChild(nav);
      aside.appendChild(hint);
      document.body.insertBefore(aside, document.body.firstChild);
    }
    try {
      document.documentElement.classList.add("suite-has-spine");
    } catch (eCls) {}
    markSpineHere(aside);
    return aside;
  }

  /** @deprecated Overview killed — all paths land on Map */
  function overviewHref(room, project) {
    project = (project || "").trim();
    if (project) return workspaceMapHref() + "?project=" + enc(project);
    return workspaceMapHref();
  }

  function roomScopeHref(room, project, worker, onOverview) {
    project = (project || "").trim();
    worker = (worker || "").trim();
    /* On a view's Overview, crumbs stay on that Overview (not jump to operate). */
    if (onOverview) return overviewHref(room, project);
    if (room === "desk") return deskHrefFor(project, worker);
    if (room === "roster") {
      return project
        ? "/workspace-map?project=" + enc(project)
        : "/workspace-map";
    }
    if (isPlaceRoom(room)) return placeHref(project, "");
    if (room === "person" || room === "ticket" || room === "read") {
      return placeHref(project, "");
    }
    return placeHref(project, "");
  }

  function isPlaceRoom(room) {
    return room === "map" || room === "home" || room === "place";
  }

  function peerRoomLabel(room, project) {
    if (isPlaceRoom(room)) return placeLabel(project);
    if (room === "desk") return "Work orders";
    if (room === "roster") return "Agents";
    if (room === "settings") return "Settings";
    return room || "View";
  }

  function workerFromSearch() {
    try {
      return new URLSearchParams(global.location.search).get("worker") || "";
    } catch (e) {
      return "";
    }
  }

  /**
   * Work-orders entry — Map dig-in (peer /desk retired 2026-07-24).
   * Optional project= focuses the map; worker is ignored (open person detail).
   */
  function deskHrefFor(project, worker) {
    const p = new URLSearchParams();
    if (project) p.set("project", project);
    const qs = p.toString();
    return qs ? "/workspace-map?" + qs : "/workspace-map";
  }

  function roomWord(room) {
    if (isPlaceRoom(room)) return placeLabel(projectFromSearch()); // fallback
    if (room === "desk") return "Work orders";
    if (room === "roster") return "Agents";
    if (room === "person") return "Person";
    if (room === "ticket") return "Work order";
    if (room === "read") return "Paper";
    if (room === "overview") return "Overview";
    return room || "View";
  }

  /* pc-1396: HTML escape lives in /esc.js */
  var escHtml = function (s) { return global.__bp.esc(s); };

  /**
   * Ensure .suite-meta exists under header (person pages may lack it).
   */
  /** Ensure Home door exists left of peer doors (workspace front). */
  function ensureHomeDoor() {
    if (typeof document === "undefined") return;
    let a = document.getElementById("nav-home");
    if (a) return a;
    const doors = document.querySelector("nav.suite-doors");
    if (!doors || !doors.parentNode) return null;
    let homeNav = document.getElementById("suite-home-door");
    if (!homeNav) {
      homeNav = document.createElement("nav");
      homeNav.id = "suite-home-door";
      homeNav.className = "suite-home-door";
      homeNav.setAttribute("aria-label", "Workspace Home");
      doors.parentNode.insertBefore(homeNav, doors);
    }
    a = document.createElement("a");
    a.id = "nav-home";
    a.href = "/";
    a.textContent = "Overview";
    a.title = "Workspace overview — system summary";
    homeNav.appendChild(a);
    return a;
  }

  /**
   * Ensure surface furniture: Overview · Home · Settings (order fixed).
   * Peer Overviews are the entry point — Home is the live floor, never a
   * missing third mode. Workspace Home / Map dig-in hide this strip in apply().
   * Ship word is Home (not Operate) — SHIP_BOUNDARY / SUITE_VOCABULARY.
   */
  function ensureViewFurniture() {
    if (typeof document === "undefined") return;
    /*
     * Spine is the Settings door (pc-1274). Do not plant furniture Settings
     * on Map / Settings / Calendar.
     */
    const _path = typeof location !== "undefined" ? location.pathname : "";
    const onMap = isWorkspaceMapPath(_path);
    const onSettingsPage = isSettingsPath(_path);
    const onCalendarPage = isCalendarPath(_path);
    const onWallPage = isWallPath(_path);
    const onPersonPage = isSpineDigPath(_path);
    if (onMap || onSettingsPage || onCalendarPage || onWallPage || onPersonPage) {
      const furn = document.getElementById("suite-furniture");
      if (furn) {
        furn.hidden = true;
        furn.setAttribute("aria-hidden", "true");
      }
      return;
    }
    const meta = document.querySelector(".suite-meta") || ensureMeta();
    if (!meta) return;
    let strip =
      document.getElementById("suite-furniture") ||
      meta.querySelector(".suite-furniture");
    if (!strip) {
      strip = document.createElement("div");
      strip.id = "suite-furniture";
      strip.className = "suite-furniture";
      strip.setAttribute("aria-label", "View furniture");
      meta.appendChild(strip);
    }
    /* Migrate page-level Settings links into the strip (desk/roster legacy). */
    const loose = meta.querySelectorAll("#nav-settings");
    for (let i = 0; i < loose.length; i++) {
      const el = loose[i];
      if (el && !strip.contains(el)) strip.appendChild(el);
    }

    function ensureLink(id, className, text, href, title) {
      let el = document.getElementById(id);
      if (!el) {
        el = document.createElement("a");
        el.id = id;
        el.className = className;
        el.href = href;
        el.textContent = text;
        if (title) el.title = title;
        strip.appendChild(el);
      } else {
        if (!el.className || el.className.indexOf(className) < 0) {
          el.className = (el.className ? el.className + " " : "") + className;
        }
        if (title && !el.title) el.title = title;
        if (!strip.contains(el)) strip.appendChild(el);
      }
      return el;
    }

    const st = ensureLink(
      "nav-settings",
      "settings-link",
      "Settings",
      "/settings?scope=workspace",
      "Settings for this surface"
    );
    strip.appendChild(st);
  }

  function ensureMeta() {
    let meta = document.querySelector(".suite-meta");
    if (meta) return meta;
    const header =
      document.querySelector("header.suite-head") ||
      document.querySelector("header");
    meta = document.createElement("div");
    meta.className = "suite-meta";
    if (header && header.parentNode) {
      header.parentNode.insertBefore(meta, header.nextSibling);
    } else if (document.body) {
      document.body.insertBefore(meta, document.body.firstChild);
    }
    return meta;
  }

  /**
   * Place + seat context strip — Workspace › Project › View › Seat + law line.
   * Call after apply() or re-call when labels load (city name, worker display).
   *
   * @param {object} opts
   * @param {string} opts.room
   * @param {string} [opts.project]
   * @param {string} [opts.projectLabel]
   * @param {string} [opts.cityLabel]
   * @param {string} [opts.worker]
   * @param {string} [opts.workerLabel]
   * @param {string} [opts.person]     person file name
   * @param {string} [opts.personLabel]
   * @param {'you'|'worker'|'none'|string} [opts.seat]
   */
  function contextStrip(opts) {
    opts = opts || {};
    if (typeof document === "undefined") return null;
    const room = opts.room || "";
    const onOverview = !!opts.onOverview;
    const _path = typeof location !== "undefined" ? location.pathname : "";
    const onMapDig = isWorkspaceMapPath(_path);
    /* Map dig-in wins over onWorkspaceHome — same path must not say Overview */
    const onWorkspaceHome =
      !onMapDig &&
      (!!opts.onWorkspaceHome || opts.room === "workspace");
    const onSettings = !!opts.onSettings || isSettingsPath(_path);
    const onCalendar = !!opts.onCalendar || isCalendarPath(_path);
    const project = (opts.project || "").trim();
    const projectLabel = (opts.projectLabel || project || "").trim();
    const cityLabel = workspaceFolderLabel(opts.cityLabel);
    const worker = (opts.worker || "").trim();
    const workerLabel = (opts.workerLabel || worker || "").trim();
    const person = (opts.person || "").trim();
    const personLabel = (opts.personLabel || person || "").trim();
    /* Disk path for Show in Finder (project folder, agent workdir, …) */
    const openPath =
      opts.openPath != null && opts.openPath !== ""
        ? String(opts.openPath)
        : project || "";

    let seat = opts.seat;
    if (seat == null || seat === "") {
      if (worker || person) seat = "worker";
      else if (room === "desk" && !onOverview) seat = "you";
      else seat = "none";
    }

    const meta = ensureMeta();
    let strip = document.getElementById("suite-context");
    if (!strip) {
      strip = document.createElement("div");
      strip.id = "suite-context";
      strip.className = "suite-context";
      strip.setAttribute("aria-label", "Where you are");
      meta.insertBefore(strip, meta.firstChild);
    }

    const placeUrl = placeHref(project, "");
    /* pc-264: workspace/project crumbs stay in current peer (or its Overview) */
    const cityUrl = roomScopeHref(room, "", "", onOverview);
    const scopeUrl = roomScopeHref(
      room,
      project,
      room === "desk" ? worker || person : "",
      onOverview
    );
    const deskYou = deskHrefFor(project, "");
    const deskWorker = worker
      ? deskHrefFor(project, worker)
      : person
        ? deskHrefFor(project, person)
        : deskYou;
    const rosterUrl = project
      ? "/workspace-map?project=" + enc(project)
      : "/workspace-map";
    const operateUrl =
      room === "desk"
        ? deskHrefFor(project, worker)
        : room === "roster"
          ? rosterUrl
          : isPlaceRoom(room)
            ? placeUrl
            : room === "person" && (person || worker)
              ? "/person?name=" +
                enc(person || worker) +
                (project ? "&project=" + enc(project) : "")
              : placeUrl;
    /* Surface crumb always targets Operate floor (Overview is furniture mode). */
    const roomUrl = operateUrl;

    let roomLabel = peerRoomLabel(room, project);
    if (onMapDig) roomLabel = "Map";
    else if (onWorkspaceHome) roomLabel = "Home";
    else if (room === "person") roomLabel = "Person";
    else if (room === "ticket") roomLabel = "Work order";
    else if (room === "read") roomLabel = "Paper";

    const parts = [];
    if (
      onMapDig ||
      onSettings ||
      onCalendar ||
      isWallPath(_path) ||
      isSpineDigPath(_path)
    ) {
      /*
       * Spine lenses (Map / Settings / Calendar) — no Viewing pathbar.
       * The page mast + spine already say where you are.
       */
      strip.innerHTML = "";
      strip.hidden = true;
      strip.setAttribute("aria-hidden", "true");
      if (meta) {
        try {
          meta.hidden = true;
          meta.setAttribute("aria-hidden", "true");
        } catch (eM) {}
      }
      try {
        const furn = document.getElementById("suite-furniture");
        if (furn) {
          furn.hidden = true;
          furn.setAttribute("aria-hidden", "true");
        }
      } catch (eF) {}
      return strip;
    }
    if (onWorkspaceHome) {
      /*
       * Do NOT say "You are Workspace" — You is the human persona; Workspace
       * is a place. Mast already names the folder; this line is location only.
       */
      strip.innerHTML =
        '<div class="ctx-row"><span class="ctx-k">Viewing</span>' +
        '<span class="ctx-here" title="Workspace overview — system summary">' +
        "Overview</span>" +
        (cityLabel
          ? '<span class="ctx-sep">·</span><span class="ctx-place" title="Workspace folder">' +
            escHtml(cityLabel) +
            "</span>"
          : "") +
        '<button type="button" class="ctx-finder" data-open-path="" ' +
        'title="Open this workspace folder in Finder" aria-label="Open workspace folder in Finder">' +
        "Show in Finder</button></div>";
      wireFinderOpens(strip);
      return strip;
    }
    const cityTitle =
      room === "desk"
        ? "Workspace work orders"
        : room === "roster"
          ? "Workspace Agents"
          : "Workspace files";
    parts.push(
      '<a href="' +
        cityUrl +
        '" title="' +
        cityTitle +
        '">' +
        escHtml(cityLabel) +
        "</a>"
    );
    if (project) {
      parts.push('<span class="ctx-sep">›</span>');
      parts.push(
        '<a href="' +
          scopeUrl +
          '" title="Project scope — stay in this view">' +
          escHtml(projectLabel || project) +
          "</a>"
      );
    }
    parts.push('<span class="ctx-sep">›</span>');
    /* Surface crumb */
    if (onWorkspaceHome) {
      /* Workspace Home — do not show Explorer as current surface */
      parts.push('<span class="ctx-here">Home</span>');
    } else if (room === "desk" || room === "roster" || isPlaceRoom(room)) {
      parts.push(
        '<a href="' +
          roomUrl +
          '" class="' +
          (!onOverview && (seat === "none" || (!worker && !person))
            ? "ctx-here"
            : "") +
          '" title="' +
          (onOverview
            ? "Home · " + roomLabel + " floor"
            : roomLabel) +
          '">' +
          escHtml(roomLabel) +
          "</a>"
      );
      if (onOverview) {
        parts.push('<span class="ctx-sep">›</span>');
        parts.push('<span class="ctx-here">Overview</span>');
      }
    } else {
      parts.push(
        '<span class="ctx-here">' + escHtml(roomLabel) + "</span>"
      );
      if (onOverview) {
        parts.push('<span class="ctx-sep">›</span>');
        parts.push('<span class="ctx-here">Overview</span>');
      }
    }

    /* Finder: current level on disk (project folder / agent workdir) */
    const finderBtn =
      openPath || project
        ? '<button type="button" class="ctx-finder" data-open-path="' +
          escHtml(openPath || project) +
          '" title="Show this location in Finder" aria-label="Show this location in Finder">' +
          "Show in Finder</button>"
        : "";

    /* Seat chip */
    let seatHtml = "";
    if (seat === "you" || (room === "desk" && !worker && !person)) {
      seatHtml =
        '<span class="ctx-seat you" title="Your work orders — human gates and for-You tray">Seat · You</span>';
    } else if (worker || person || seat === "worker") {
      const who = workerLabel || personLabel || worker || person || "worker";
      const whoId = worker || person;
      const clear =
        room === "desk"
          ? ' <a class="clear" href="' +
            deskYou +
            '" title="Back to your work orders (for You)">× You</a>'
          : "";
      const whoLink =
        whoId
          ? '<a href="/person?name=' +
            enc(whoId) +
            (project ? "&project=" + enc(project) : "") +
            '" style="border:none;color:inherit">' +
            escHtml(who) +
            "</a>"
          : escHtml(who);
      seatHtml =
        '<span class="ctx-seat" title="Agent seat — their WorkLane queue">' +
        "Seat · " +
        whoLink +
        clear +
        "</span>";
    }

    /*
     * Rules · law-at-this-level (pc-250 / pc-330) — every operational paper is a
     * /read?path= link so suite-paper opens the Scan/Stage drawer. Never dead
     * labels for binding instruction files (SUITE_ARTIFACTS § In-suite paper).
     * Desk/Agents inherit city vs project depth from ?project=; Person opens
     * L2/L3 when paths are known (opts.lawPaths or workers/<id>/ convention).
     * Workspace Home skips this strip (body Instructions present panel).
     */
    let lawHtml = "";
    const lawPaths = opts.lawPaths || {};
    const folderSeg = (projectLabel || project || "").replace(/^\/+|\/+$/g, "");
    const agentId = (worker || person || "").trim();

    function paperHref(rel) {
      return "/read?path=" + enc(rel);
    }
    function paperA(label, rel, title) {
      if (!rel) return "";
      return (
        '<a class="ctx-paper" href="' +
        paperHref(rel) +
        '" title="' +
        escHtml(title || "Open in suite paper") +
        '">' +
        label +
        "</a>"
      );
    }

    const l0Agents = lawPaths.l0 || "AGENTS.md";
    const l0Perimeter =
      lawPaths.boundaries || lawPaths.perimeter || "BOUNDARIES.md";
    const l1Agents =
      lawPaths.l1 ||
      (folderSeg ? folderSeg + "/AGENTS.md" : "");
    /* Prefer API-resolved paths from person enrich; else project workers/ */
    let l2Contract = lawPaths.l2 || "";
    let l3Prompt = lawPaths.l3 || "";
    if (agentId && !l2Contract) {
      l2Contract = folderSeg
        ? folderSeg + "/workers/" + agentId + "/CONTRACT.md"
        : "workers/" + agentId + "/CONTRACT.md";
    }
    if (agentId && !l3Prompt) {
      l3Prompt = folderSeg
        ? folderSeg + "/workers/" + agentId + "/prompt.md"
        : "workers/" + agentId + "/prompt.md";
    }

    const showPlaceLaw =
      isPlaceRoom(room) ||
      room === "desk" ||
      room === "roster" ||
      room === "person";
    if (showPlaceLaw && !onSettings) {
      const bits = [];
      bits.push(
        paperA("AGENTS.md", l0Agents, "Workspace rules · open in suite paper")
      );
      if (!project) {
        bits.push(
          paperA(
            "BOUNDARIES.md",
            "PERIMETER.md",
            l0Perimeter,
            "Workspace boundaries · open in suite paper"
          )
        );
      }
      if (project && l1Agents) {
        bits.push(
          paperA(
            "AGENTS.md",
            l1Agents,
            "Project rules · open in suite paper"
          )
        );
      }
      if ((worker || person || room === "person") && agentId) {
        if (l2Contract) {
          bits.push(
            paperA(
              "CONTRACT.md",
              l2Contract,
              "Contract · open in suite paper"
            )
          );
        }
        if (l3Prompt) {
          bits.push(
            paperA(
              "prompt.md",
              l3Prompt,
              "This run · open in suite paper"
            )
          );
        }
      }
      if (bits.length) {
        lawHtml =
          '<div class="ctx-law" title="Rules at this level — open instruction papers in-suite">' +
          "Rules · " +
          bits.join(" · ") +
          "</div>";
      }
    }

    strip.innerHTML =
      '<div class="ctx-row"><span class="ctx-k">Viewing</span>' +
      parts.join("") +
      (seatHtml ? '<span class="ctx-sep">›</span>' + seatHtml : "") +
      (finderBtn || "") +
      "</div>" +
      lawHtml;
    wireFinderOpens(strip);
    return strip;
  }

  /**
   * @param {object} opts
   * @param {'map'|'home'|'place'|'desk'|'roster'|'person'|'ticket'|'read'} opts.room
   * @param {string} [opts.project]  project slug (empty = city)
   * @param {string} [opts.worker]   worker identity for Desk lane skim
   * @param {string} [opts.mapPath]  place-only subpath (only while on place room)
   * @param {string} [opts.cityLabel]
   * @param {string} [opts.projectLabel]
   * @param {string} [opts.workerLabel]
   * @param {string} [opts.person]
   * @param {string} [opts.personLabel]
   * @param {string} [opts.seat]
   */
  function apply(opts) {
    opts = opts || {};
    const room = opts.room || "";
    const onOverview = !!opts.onOverview;
    const onWorkspaceHome = !!opts.onWorkspaceHome || opts.room === "workspace";
    const onSettings =
      !!opts.onSettings ||
      (typeof location !== "undefined" && isSettingsPath(location.pathname));
    const onCalendar =
      !!opts.onCalendar ||
      room === "calendar" ||
      (typeof location !== "undefined" && isCalendarPath(location.pathname));
    const project = (opts.project || "").trim();
    const worker =
      (opts.worker != null ? String(opts.worker) : "").trim() ||
      (room === "desk" ? workerFromSearch() : "");
    const mapPath = (opts.mapPath || "").replace(/^\/+|\/+$/g, "");
    const onPlace = isPlaceRoom(room);
    const label = placeLabel(project);

    // Peer place: always list/Finder for Explorer operate (pc-327).
    let placeUrl;
    if (onPlace && !onOverview) {
      placeUrl = placeHref(project, mapPath);
    } else {
      placeUrl = placeHref(project, "");
    }

    const deskHref = deskHrefFor(project, worker);
    const rosterHref = project
      ? "/workspace-map?project=" + enc(project)
      : "/workspace-map";
    // Project Home root (no path) — climb from path drill
    const projectPlaceHref = placeHref(project, "");

    function set(id, href, here) {
      const el = document.getElementById(id);
      if (!el) return;
      if (href != null) el.setAttribute("href", href);
      if (here === true) {
        el.classList.add("here");
        el.classList.add("is-here");
      } else if (here === false) {
        el.classList.remove("here");
        el.classList.remove("is-here");
      }
    }

    function setLabel(id, text) {
      const el = document.getElementById(id);
      if (el && text != null) el.textContent = text;
    }

    /*
     * Overview lands (pc-1299). Map is the dig-in room. No Overview peer
     * door on the old mast — spine Overview lens is the hop.
     */
    const mapDigHref = workspaceMapHref();
    const onMapDig =
      typeof location !== "undefined" && isWorkspaceMapPath(location.pathname);
    /* nav-home was Overview — retarget to Map, hide as peer */
    set("nav-home", mapDigHref, false);
    setLabel("nav-home", "Map");
    if (typeof document !== "undefined") {
      const homeEl = document.getElementById("nav-home");
      if (homeEl) {
        homeEl.classList.add("suite-peer-demoted");
        homeEl.setAttribute("data-demoted", "1");
        homeEl.setAttribute("hidden", "hidden");
        homeEl.setAttribute("aria-hidden", "true");
        homeEl.title = "Use the spine Overview lens — old mast Overview door is gone";
      }
    }

    const deskPeerHref = deskHrefFor(project, worker);
    const agentsPeerHref = project
      ? "/workspace-map?project=" + enc(project)
      : "/workspace-map";
    const filesPeerHref = placeHref(project, "");
    const onDeskSurf = !onMapDig && !onSettings && room === "desk";
    const onAgentsSurf = !onMapDig && !onSettings && room === "roster";
    const onFilesSurf =
      !onMapDig &&
      !onSettings &&
      isPlaceRoom(room);

    /* nav-map = the only primary dig-in surface */
    set("nav-map", mapDigHref, onMapDig && !onSettings);
    setLabel("nav-map", "Map");
    if (typeof document !== "undefined") {
      const mapEl = document.getElementById("nav-map");
      if (mapEl) {
        mapEl.classList.remove("suite-peer-demoted");
        mapEl.removeAttribute("data-demoted");
        mapEl.title = "Workspace map — folders, agents, details";
        mapEl.hidden = false;
        mapEl.removeAttribute("aria-hidden");
      }
    }

    set("nav-desk", deskPeerHref, onDeskSurf);
    setLabel("nav-desk", "Work orders");
    set("nav-roster", agentsPeerHref, onAgentsSurf);
    setLabel("nav-roster", "Agents");

    /*
     * pc-376: first-user peer doors = Overview · Map only.
     * Desk/Roster stay routable for deep links (tape, person, pillars)
     * but never appear as equal peer rooms on the mast.
     */
    if (typeof document !== "undefined") {
      ["nav-desk", "nav-roster"].forEach(function (id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.add("suite-peer-demoted");
        el.setAttribute("data-demoted", "1");
        el.setAttribute("hidden", "hidden");
        el.setAttribute("aria-hidden", "true");
        el.title =
          id === "nav-desk"
            ? "Work orders — open from Map tape or Overview (deep link)"
            : "Agents — open from Map hands or Overview (deep link)";
      });
      const doors = document.querySelector(".suite-doors");
      if (doors) {
        doors.classList.remove("suite-doors-demoted");
        doors.classList.add("suite-doors-map-primary");
        /* pc-1290: spine rooms do not wear header peer doors. Calendar
         * keeps ICS in .suite-doors; Map/Overview/Settings hide the cluster. */
        var onCal =
          typeof location !== "undefined" &&
          isCalendarPath(location.pathname);
        if (onCal) {
          doors.removeAttribute("hidden");
          doors.setAttribute("aria-label", "Calendar tools");
        } else {
          doors.setAttribute("hidden", "hidden");
          doors.setAttribute("aria-hidden", "true");
        }
      }
      const filesEl = document.getElementById("nav-files");
      if (filesEl) {
        filesEl.setAttribute("href", filesPeerHref);
        filesEl.classList.toggle("is-here", onFilesSurf);
        filesEl.classList.add("suite-peer-demoted");
        filesEl.setAttribute("hidden", "hidden");
        filesEl.setAttribute("aria-hidden", "true");
      }
    }

    if (typeof document !== "undefined") {
      ensureHomeDoor();
      ensureViewFurniture();
      ensureSpine();
      paintSpineVersion();
      hideSpinePeerDoors();
    }

    let ovTarget = workspaceHomeHref();
    /* Operate on dig-in pages only — Overview/Map have no Operate furniture */
    let opTarget = "";
    if (room === "desk") opTarget = deskHref;
    else if (room === "roster") opTarget = rosterHref;
    else if (isPlaceRoom(room)) {
      opTarget = placeUrl;
    }
    if (onMapDig) opTarget = "";

    /* pc-666: Settings is one Workspace sheet from every room. */
    const setScope = "workspace";
    const setHref = settingsHref(setScope, project);

    const onOperate =
      !onOverview && !onMapDig && !onSettings && !!opTarget;

    set("nav-settings", setHref, onSettings);
    setLabel("nav-settings", "Settings");
    /* pc-1274: Map Settings FAB is gone — hide any leftover #nav-settings on Map. */
    if (typeof document !== "undefined") {
      const setEl = document.getElementById("nav-settings");
      if (setEl && onMapDig) {
        setEl.hidden = true;
        setEl.setAttribute("aria-hidden", "true");
      }
    }

    // Presence / hat / YOU secondary doors
    set("hat-map", placeUrl, false);
    setLabel("hat-map", label);
    set("hat-roster", rosterHref, false);
    setLabel("hat-roster", "Agents");
    set("you-map", placeUrl, false);
    setLabel("you-map", label);
    set("you-desk", deskHref, false);
    set("here-work-more", deskHref, false);
    set("here-who-more", rosterHref, false);
    set("here-compact-desk", deskHref, false);
    set("here-compact-roster", rosterHref, false);
    set("here-compact-up", projectPlaceHref, false);
    setLabel("here-compact-up", "↑ Project Home");

    contextStrip({
      room: room,
      onOverview: onOverview,
      onWorkspaceHome: onWorkspaceHome,
      onSettings: onSettings,
      onCalendar: onCalendar,
      project: project,
      projectLabel: opts.projectLabel || project,
      cityLabel: opts.cityLabel,
      worker: worker || opts.person || "",
      workerLabel: opts.workerLabel || opts.personLabel,
      person: opts.person || "",
      personLabel: opts.personLabel,
      seat: opts.seat,
      openPath: opts.openPath,
      lawPaths: opts.lawPaths,
    });

    if (typeof document !== "undefined") {
      try {
        var allowJump = shouldInstallJump(
          room,
          onOverview,
          onWorkspaceHome,
          onSettings
        );
        document.body.setAttribute("data-suite-jump", allowJump ? "1" : "0");
        document.body.setAttribute(
          "data-suite-surface",
          onWorkspaceHome
            ? "workspace"
            : onOverview
              ? "overview"
              : room || ""
        );
        /*
         * Full-bleed map paper chrome (html.suite-map-city). Soft-nav and
         * hard load both call apply() — keep class in sync with path so the
         * 48px grid fills the viewport like Overview.
         */
        var herePath =
          typeof location !== "undefined" ? location.pathname || "" : "";
        if (room === "map" || onWorkspaceHome) {
          applyMapCityChrome(herePath || "/workspace-map");
        } else {
          applyMapCityChrome(herePath);
        }
      } catch (e) {
        /* ignore */
      }
      installJump();
      installSoftNav();
      ensureSuitePaper();
    }

    return {
      map: placeUrl, // back-compat key
      place: placeUrl,
      desk: deskHref,
      roster: rosterHref,
      projectMap: projectPlaceHref, // back-compat
      projectPlace: projectPlaceHref,
      project: project,
      placeLabel: label,
      worker: worker,
      onOverview: onOverview,
    };
  }

  /**
   * Normalize a typed ticket id:
   *   "tp-207" | "TP-207" | "#tp-207" | "tp207" → "tp-207"
   */
  function normalizeTicketId(raw) {
    let s = String(raw || "").trim();
    if (!s) return "";
    if (s.charAt(0) === "#") s = s.slice(1).trim();
    const glued = /^([a-z]{1,6})(\d+)$/i.exec(s);
    if (glued) return glued[1].toLowerCase() + "-" + glued[2];
    const dashed = /^([a-z]{1,6})-(\d+)$/i.exec(s);
    if (dashed) return dashed[1].toLowerCase() + "-" + dashed[2];
    return s;
  }

  function ticketLooksLikeId(s) {
    return /^[a-z]{1,6}-\d+$/i.test(s);
  }

  /**
   * Suite-wide ticket jump box in .suite-meta.
   * Enter → open side drawer (SuitePaper) or /ticket full page.
   * "/" focuses the box when not typing in another field.
   */
  /** Ticket jump is Desk-only (work-order surface). Not on Home / Explorer / Agents. */
  function shouldInstallJump(room, onOverview, onWorkspaceHome, onSettings) {
    if (onWorkspaceHome || onOverview || onSettings) return false;
    return room === "desk";
  }

  function installJump() {
    const meta = document.querySelector(".suite-meta");
    if (!meta) return;
    /* Remove jump if we left Desk */
    const allow = document.body && document.body.getAttribute("data-suite-jump") === "1";
    if (!allow) {
      const old = document.getElementById("suite-jump");
      if (old) old.remove();
      return;
    }


    let form = document.getElementById("suite-jump");
    if (!form) {
      form = document.createElement("form");
      form.id = "suite-jump";
      form.className = "suite-jump";
      form.setAttribute("role", "search");
      form.setAttribute("aria-label", "Jump to work order");
      form.innerHTML =
        '<input type="search" id="suite-jump-q" name="q" ' +
        'placeholder="tp-207 · jump" autocomplete="off" spellcheck="false" />' +
        '<button type="submit" title="Open work order">Go</button>' +
        '<span class="suite-jump-msg" id="suite-jump-msg" hidden></span>';
      /* Overview lives inside #suite-furniture — insertBefore needs a direct child
         of meta. Prefer before the furniture strip; never pass a nested node. */
      const furniture =
        document.getElementById("suite-furniture") ||
        meta.querySelector(".suite-furniture");
      if (furniture && furniture.parentNode === meta) {
        meta.insertBefore(form, furniture);
      } else {
        const pathbar = meta.querySelector(".pathbar, #pathbar");
        if (pathbar && pathbar.parentNode === meta) {
          meta.insertBefore(form, pathbar.nextSibling);
        } else {
          meta.appendChild(form);
        }
      }
    } else if (form.dataset.suiteJumpBound === "1") {
      return;
    }
    form.dataset.suiteJumpBound = "1";

    const input = form.querySelector("#suite-jump-q");
    const msg = form.querySelector("#suite-jump-msg");

    function setErr(text) {
      form.classList.toggle("is-err", !!text);
      if (msg) {
        if (text) {
          msg.hidden = false;
          msg.textContent = text;
        } else {
          msg.hidden = true;
          msg.textContent = "";
        }
      }
    }

    async function jump(raw) {
      const id = normalizeTicketId(raw);
      if (!id) {
        setErr("type an id");
        return;
      }
      setErr("");
      form.classList.add("is-busy");
      try {
        const r = await fetch("/api/task/" + encodeURIComponent(id));
        const data = await r.json().catch(function () {
          return {};
        });
        if (!r.ok) {
          setErr(
            ticketLooksLikeId(id)
              ? "not found"
              : "use id · tp-207"
          );
          return;
        }
        const task = data.task || data;
        const tid = task.id || id;
        if (global.SuitePaper && SuitePaper.openTicket) {
          SuitePaper.openTicket(tid);
        } else {
          global.location.href =
            "/ticket?id=" +
            encodeURIComponent(tid) +
            "&back=" +
            encodeURIComponent(
              global.location.pathname + global.location.search
            );
        }
        if (input) input.select();
      } catch (e) {
        setErr("lookup failed");
      } finally {
        form.classList.remove("is-busy");
      }
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      jump(input && input.value);
    });
    if (input) {
      input.addEventListener("input", function () {
        setErr("");
      });
    }

    if (!installJump._keys) {
      installJump._keys = true;
      document.addEventListener("keydown", function (e) {
        if (e.key !== "/" && e.key !== "k" && e.key !== "K") return;
        if (e.key === "k" || e.key === "K") {
          if (!(e.metaKey || e.ctrlKey)) return;
        }
        const t = e.target;
        if (
          t &&
          (t.tagName === "INPUT" ||
            t.tagName === "TEXTAREA" ||
            t.tagName === "SELECT" ||
            t.isContentEditable)
        ) {
          return;
        }
        if (document.documentElement.classList.contains("suite-paper-open"))
          return;
        e.preventDefault();
        const live = document.querySelector("#suite-jump-q");
        if (live) {
          live.focus();
          live.select();
        }
      });
    }
  }

  /**
   * Page-owned CSS lives in <style id="suite-page-css"> (map paint, desk, …).
   * Soft-nav keeps header mounted and swaps this sheet with #suite-body so
   * City paint overrides (html.suite-map-city) do not leak across rooms.
   * Fallback: pages that still put CSS in bare <head><style> (settings, person)
   * — concatenate those so soft-nav does not land an unstyled empty shell.
   */
  function syncPageCss(doc) {
    if (typeof document === "undefined" || !doc) return;
    var incoming = doc.querySelector("style#suite-page-css");
    var cssText = incoming ? incoming.textContent || "" : "";
    if (!cssText) {
      var parts = [];
      var nodes = doc.querySelectorAll("head style");
      for (var i = 0; i < nodes.length; i++) {
        var t = nodes[i].textContent || "";
        if (t) parts.push(t);
      }
      cssText = parts.join("\n");
    }
    var live = document.querySelector("style#suite-page-css");
    if (cssText) {
      if (!live) {
        live = document.createElement("style");
        live.id = "suite-page-css";
        document.head.appendChild(live);
      }
      live.textContent = cssText;
    } else if (live && live.parentNode) {
      live.parentNode.removeChild(live);
    }
  }

  var MAP_CSS_HREF = "/map/workspace_map.css?v=20260819-pc1290";

  function ensureMapStylesheet() {
    if (typeof document === "undefined") return;
    if (document.querySelector('link[href*="workspace_map.css"]')) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = MAP_CSS_HREF;
    (document.head || document.documentElement).appendChild(l);
  }

  function hideSpinePeerDoors() {
    if (typeof document === "undefined") return;
    var home = document.getElementById("nav-home");
    if (home) {
      home.hidden = true;
      home.setAttribute("aria-hidden", "true");
      home.classList.add("suite-peer-demoted");
    }
    var homeNav = document.getElementById("suite-home-door");
    if (homeNav) {
      homeNav.hidden = true;
      homeNav.setAttribute("aria-hidden", "true");
    }
    var path =
      typeof location !== "undefined" ? location.pathname : "";
    var onCal = isCalendarPath(path);
    var cluster = document.querySelector(".suite-nav-cluster");
    var doors = document.querySelector("nav.suite-doors");
    if (!onCal) {
      if (cluster) {
        cluster.hidden = true;
        cluster.setAttribute("aria-hidden", "true");
      }
      if (doors) {
        doors.hidden = true;
        doors.setAttribute("aria-hidden", "true");
      }
    } else if (doors) {
      doors.removeAttribute("hidden");
      doors.removeAttribute("aria-hidden");
      if (cluster) {
        cluster.hidden = false;
        cluster.removeAttribute("aria-hidden");
      }
    }
  }

  /** Workspace map uses full-viewport stage chrome (pc-328). */
  function applyMapCityChrome(path) {
    if (typeof document === "undefined") return;
    var isCity = isWorkspaceMapPath(path);
    var isSettings = isSettingsPath(path);
    if (isCity) ensureMapStylesheet();
    try {
      document.documentElement.classList.toggle("suite-map-city", isCity);
      document.documentElement.classList.toggle("suite-settings-view", isSettings);
      document.documentElement.classList.toggle(
        "suite-calendar-view",
        isCalendarPath(path)
      );
      document.documentElement.classList.toggle(
        "suite-wall-view",
        isWallPath(path)
      );
      document.documentElement.classList.toggle(
        "suite-person-view",
        isPersonPath(path)
      );
      document.documentElement.classList.toggle(
        "suite-ticket-view",
        isTicketPath(path)
      );
      document.documentElement.classList.toggle(
        "suite-read-view",
        isReadPath(path)
      );
      if (
        isCity ||
        isSettings ||
        isCalendarPath(path) ||
        isWallPath(path) ||
        isSpineDigPath(path)
      ) {
        document.documentElement.classList.add("suite-has-spine");
      }
    } catch (e) {
      /* ignore */
    }
    hideSpinePeerDoors();
    var spine = document.getElementById("suite-spine");
    if (spine) {
      ensureSpineLockup(document.querySelector(".suite-spine-brand"));
      markSpineHere(spine);
    }
  }

  /**
   * pc-495: SuitePaper must survive soft-nav. Full-page rooms (ticket_v1) never
   * loaded suite-paper.js; soft-nav back to Map only re-execs inline scripts —
   * SuitePaper stayed undefined and every later /ticket|/read soft-nav'd full.
   * Ensure the script is present and install() once per document lifetime.
   */
  var SUITE_PAPER_SRC = "/suite-paper.js?v=20260830-pc1340";

  function ensureSuitePaper() {
    if (typeof document === "undefined") return;
    try {
      if (
        global.SuitePaper &&
        typeof global.SuitePaper.install === "function"
      ) {
        global.SuitePaper.install();
        return;
      }
    } catch (e0) {
      /* fall through to inject */
    }
    if (ensureSuitePaper._loading) return;
    var existing = document.querySelector(
      'script[data-suite-paper-ensure="1"], script[src*="suite-paper.js"]'
    );
    if (existing && global.SuitePaper) {
      try {
        global.SuitePaper.install();
      } catch (e1) {}
      return;
    }
    if (existing && !global.SuitePaper) {
      if (existing.getAttribute("data-suite-paper-wait") === "1") return;
      existing.setAttribute("data-suite-paper-wait", "1");
      existing.addEventListener("load", function () {
        try {
          if (global.SuitePaper) global.SuitePaper.install();
        } catch (e2) {}
      });
      return;
    }
    ensureSuitePaper._loading = true;
    var s = document.createElement("script");
    s.src = SUITE_PAPER_SRC;
    s.setAttribute("data-suite-paper-ensure", "1");
    s.onload = function () {
      ensureSuitePaper._loading = false;
      try {
        if (global.SuitePaper && global.SuitePaper.install) {
          global.SuitePaper.install();
        }
      } catch (e3) {}
    };
    s.onerror = function () {
      ensureSuitePaper._loading = false;
    };
    (document.head || document.documentElement).appendChild(s);
  }

  /**
   * Soft navigation — one pane of glass (SUITE_SHELL / pc-402).
   * Swap or restore views without full document load. Map keep-alive:
   * park #suite-body instead of teardown+re-exec when leaving Map.
   * Called from apply() after first install. Back/forward via popstate.
   */
  function installSoftNav() {
    if (installSoftNav._done) return;
    if (typeof document === "undefined") return;
    installSoftNav._done = true;

    var MAP_PARK_ID = "suite-body-park-map";
    var OV_PARK_ID = "suite-body-park-overview";

    function isOverviewShell(pathAndQuery) {
      var p = String(pathAndQuery || "").split("?")[0] || "";
      return isWallPath(p);
    }

    /** Paths the shell owns (same-origin soft-nav). */
    function isShellPath(path) {
      var p = String(path || "").split("?")[0] || "";
      if (
        p === "/" ||
        p === "/overview" ||
        p === "/wall.html" ||
        p === "/wall" ||
        p === "/calendar" ||
        p === "/settings" ||
        p === "/home" ||
        p === "/read" ||
        p === "/ticket" ||
        p === "/person" ||
        p === "/desk" ||
        p === "/roster" ||
        p === "/agents" ||
        p === "/skin" ||
        p === "/map" ||
        p === "/explorer" ||
        p === "/ported"
      ) {
        return true;
      }
      return isWorkspaceMapPath(p);
    }

    function pathOnly(pathAndQuery) {
      return String(pathAndQuery || "").split("?")[0] || "";
    }

    function syncMastFromDoc(doc) {
      if (!doc) return;
      var newTitle = doc.querySelector(".suite-title h1");
      var oldTitle = document.querySelector(".suite-title h1");
      if (newTitle && oldTitle) {
        oldTitle.textContent = newTitle.textContent;
        if (newTitle.id) oldTitle.id = newTitle.id;
      }
      var newSub = doc.querySelector(".suite-title .sub");
      var oldSub = document.querySelector(".suite-title .sub");
      if (newSub && oldSub) {
        oldSub.innerHTML = newSub.innerHTML;
        if (newSub.id) oldSub.id = newSub.id;
        if (newSub.hasAttribute("hidden")) oldSub.setAttribute("hidden", "");
        else oldSub.removeAttribute("hidden");
      }
      if (doc.title) document.title = doc.title;
    }

    function syncMastSimple(titleText, subHtml) {
      var oldTitle = document.querySelector(".suite-title h1");
      if (oldTitle && titleText) oldTitle.textContent = titleText;
      var oldSub = document.querySelector(".suite-title .sub");
      if (oldSub && subHtml != null) oldSub.innerHTML = subHtml;
    }

    /** True when the live #suite-body is the Map room (mounted, not parked). */
    function liveBodyIsMap() {
      var body = document.getElementById("suite-body");
      if (!body) return false;
      if (body.getAttribute("data-suite-room") === "map") return true;
      /* Heuristic: map stage lives on Workspace map dig-in */
      return !!(
        body.querySelector("#stage") &&
        body.querySelector("#map-kpis, #map-chrome, #stage svg, .map-chrome")
      );
    }

    function liveBodyIsOverview() {
      var body = document.getElementById("suite-body");
      if (!body) return false;
      if (body.getAttribute("data-suite-room") === "overview") return true;
      /* Heuristic: system brief (not map stage) */
      return !!(
        body.querySelector("#asof, .kpis, #floor-folders-wrap") &&
        !liveBodyIsMap()
      );
    }

    /** Keep-alive rooms: park instead of teardown+remount (glass bar). */
    function keepAliveKindFromPath(path) {
      if (isWorkspaceMapPath(path)) return "map";
      if (isOverviewShell(path)) return "overview";
      return null;
    }

    function parkIdFor(kind) {
      return kind === "map" ? MAP_PARK_ID : kind === "overview" ? OV_PARK_ID : null;
    }

    function liveKeepAliveKind() {
      if (liveBodyIsMap()) return "map";
      if (liveBodyIsOverview()) return "overview";
      var body = document.getElementById("suite-body");
      var r = body && body.getAttribute("data-suite-room");
      if (r === "map" || r === "overview") return r;
      return null;
    }

    function teardownDisposableRoom() {
      /* Tear down rooms that are NOT keep-alive parked (settings, person, …) */
      try {
        if (!global.SuiteRoomInit || !global.SuiteRoomInit.teardown) return;
        var n = global.SuiteRoomInit.name;
        if (n === "skin" || n === "overview") return;
        global.SuiteRoomInit.teardown();
        global.SuiteRoomInit = null;
      } catch (e) {
        /* ignore */
      }
    }

    /**
     * Park a keep-alive room body in DOM — do NOT teardown (Map RAF / Overview Live).
     */
    function parkLiveRoom(kind) {
      if (kind !== "map" && kind !== "overview") return false;
      var body = document.getElementById("suite-body");
      if (!body) return false;
      if (kind === "map" && !liveBodyIsMap()) return false;
      if (kind === "overview" && !liveBodyIsOverview()) return false;
      var parkId = parkIdFor(kind);
      if (document.getElementById(parkId)) {
        /* Already parked — drop duplicate live carefully */
        try {
          if (
            global.SuiteRoomInit &&
            ((kind === "map" && global.SuiteRoomInit.name === "skin") ||
              (kind === "overview" && global.SuiteRoomInit.name === "overview"))
          ) {
            global.SuiteRoomInit.teardown();
          }
        } catch (e) {}
        body.remove();
        return true;
      }
      body.id = parkId;
      body.setAttribute("data-suite-room", kind);
      body.setAttribute("hidden", "");
      body.setAttribute("aria-hidden", "true");
      body.style.display = "none";
      try {
        var liveCss = document.querySelector("style#suite-page-css");
        if (liveCss) {
          body.setAttribute("data-parked-page-css", liveCss.textContent || "");
        }
        var h1 = document.querySelector(".suite-title h1");
        var sub = document.querySelector(".suite-title .sub");
        if (h1) body.setAttribute("data-parked-title", h1.textContent || "");
        if (sub) body.setAttribute("data-parked-sub", sub.innerHTML || "");
        body.setAttribute(
          "data-parked-doc-title",
          document.title ||
            (kind === "map"
              ? docTitle("Workspace", "Map")
              : docTitle("Workspace", "Overview"))
        );
      } catch (e2) {}
      /* One SuiteLive owner at a time — stop while parked; resume re-arms */
      try {
        if (global.SuiteLive && typeof global.SuiteLive.stop === "function") {
          global.SuiteLive.stop();
        }
      } catch (eLive) {}
      if (kind === "map") {
        global._suiteMapRoomInit = global.SuiteRoomInit;
        if (global.SuiteRoomInit && global.SuiteRoomInit.name === "skin") {
          global.SuiteRoomInit = null;
        }
        applyMapCityChrome("/");
      } else {
        global._suiteOverviewRoomInit = global.SuiteRoomInit;
        if (global.SuiteRoomInit && global.SuiteRoomInit.name === "overview") {
          global.SuiteRoomInit = null;
        }
      }
      return true;
    }

    function parkLiveMap() {
      return parkLiveRoom("map");
    }

    /** Restore parked Map or Overview without re-fetch / re-exec. */
    function restoreParkedRoom(kind, push, target) {
      var parkId = parkIdFor(kind);
      if (!parkId) return false;
      var parked = document.getElementById(parkId);
      if (!parked) return false;
      /* Park the room we're leaving if it is keep-alive */
      var leaving = liveKeepAliveKind();
      if (leaving && leaving !== kind) {
        parkLiveRoom(leaving);
      } else {
        teardownDisposableRoom();
        var old = document.getElementById("suite-body");
        if (old && old !== parked) {
          /* Settings etc — remove (not keep-alive) */
          try {
            if (
              global.SuiteRoomInit &&
              global.SuiteRoomInit.teardown &&
              global.SuiteRoomInit.name !== "skin" &&
              global.SuiteRoomInit.name !== "overview"
            ) {
              global.SuiteRoomInit.teardown();
            }
          } catch (e0) {}
          old.remove();
        }
      }
      /* After parking leave, live suite-body may be gone */
      var still = document.getElementById("suite-body");
      if (still && still !== parked) still.remove();

      parked.id = "suite-body";
      parked.removeAttribute("hidden");
      parked.removeAttribute("aria-hidden");
      parked.style.display = "";
      try {
        var css = parked.getAttribute("data-parked-page-css");
        if (css != null) {
          var live = document.querySelector("style#suite-page-css");
          if (!live) {
            live = document.createElement("style");
            live.id = "suite-page-css";
            document.head.appendChild(live);
          }
          live.textContent = css;
        }
        var pt = parked.getAttribute("data-parked-title");
        var ps = parked.getAttribute("data-parked-sub");
        if (pt) syncMastSimple(pt, ps != null ? ps : undefined);
        var dt = parked.getAttribute("data-parked-doc-title");
        if (dt) document.title = dt;
      } catch (e) {}
      if (kind === "map" && global._suiteMapRoomInit) {
        global.SuiteRoomInit = global._suiteMapRoomInit;
      } else if (kind === "overview" && global._suiteOverviewRoomInit) {
        global.SuiteRoomInit = global._suiteOverviewRoomInit;
      }
      if (kind === "map") applyMapCityChrome("/workspace-map");
      else applyMapCityChrome("/");
      if (push !== false) {
        try {
          history.pushState(
            {},
            "",
            target || (kind === "map" ? workspaceMapHref() : "/")
          );
        } catch (e3) {}
      }
      try {
        installJump();
        if (typeof apply === "function") {
          if (kind === "map") {
            apply({
              room: "map",
              project: "",
              onWorkspaceHome: false,
              openPath: "",
            });
          } else {
            apply({
              room: "map",
              project: "",
              onWorkspaceHome: true,
              openPath: "",
            });
          }
        }
      } catch (e4) {}
      try {
        if (
          global.SuiteRoomInit &&
          typeof global.SuiteRoomInit.resume === "function"
        ) {
          global.SuiteRoomInit.resume();
        }
      } catch (e5) {}
      /* Overview: soft live refresh only (no blank Loading shell) */
      if (kind === "overview") {
        try {
          if (typeof global.SuiteOverviewReload === "function") {
            /* light path — prefer liveOnly via resume hook */
          }
          if (
            global.SuiteRoomInit &&
            global.SuiteRoomInit.name === "overview" &&
            typeof global.runMain === "function"
          ) {
            global.runMain({ liveOnly: true, reason: "park-restore" });
          } else if (typeof global.SuiteOverviewSoftResume === "function") {
            global.SuiteOverviewSoftResume();
          }
        } catch (e6) {}
      }
      /* pc-495: parked Map restore must keep dig-in default (SuitePaper) */
      try {
        ensureSuitePaper();
      } catch (e7) {}
      return true;
    }

    function restoreParkedMap(push, target) {
      return restoreParkedRoom("map", push, target);
    }

    async function softNavTo(href, push) {
      const cur = global.location.pathname + global.location.search;
      let target = String(href || "");
      if (!target) return;
      // Resolve relative hrefs against current location
      try {
        const u = new URL(target, global.location.origin);
        /* External → hard */
        if (u.origin !== global.location.origin) {
          global.location.href = target;
          return;
        }
        target = u.pathname + u.search;
      } catch (e) {
        /* keep raw */
      }
      if (target === cur) return;

      const tgtPath = pathOnly(target);
      const curPath = pathOnly(cur);

      /* pc-1267 / pc-1274: /settings is a spine view — fall through to soft-mount. */

      /*
       * / and /overview (and /wall.html) share the same Overview shell.
       * Skip full HTML fetch + script re-exec — only re-query + repaint.
       */
      if (isOverviewShell(cur) && isOverviewShell(target)) {
        if (push !== false) {
          try {
            history.pushState({}, "", target);
          } catch (e) {
            /* ignore */
          }
        }
        try {
          if (typeof global.SuiteOverviewReload === "function") {
            global.SuiteOverviewReload();
            return;
          }
        } catch (e) {
          /* fall through to full soft-nav */
        }
      }

      /*
       * Shortest ticket path (pc-1247): /ticket → one /api/task, no
       * ticket_v1.html re-fetch. Mirrors /read + mountFullPagePaper.
       */
      if (tgtPath === "/ticket") {
        var ticketParams = new URLSearchParams(
          target.indexOf("?") >= 0 ? target.split("?").slice(1).join("?") : ""
        );
        var ticketId = (ticketParams.get("id") || "").trim();
        if (ticketId) {
          ensureSuitePaper();
          var ticketReady = await new Promise(function (resolve) {
            if (
              global.SuitePaper &&
              typeof global.SuitePaper.mountFullPageTicket === "function"
            ) {
              resolve(true);
              return;
            }
            var tTicket = Date.now();
            var ivTicket = setInterval(function () {
              if (
                global.SuitePaper &&
                typeof global.SuitePaper.mountFullPageTicket === "function"
              ) {
                clearInterval(ivTicket);
                resolve(true);
              } else if (Date.now() - tTicket > 2500) {
                clearInterval(ivTicket);
                resolve(false);
              }
            }, 20);
          });
          if (ticketReady) {
            if (
              !document.getElementById("suite-body") &&
              !document.getElementById(MAP_PARK_ID) &&
              !document.getElementById(OV_PARK_ID)
            ) {
              global.location.href = target;
              return;
            }
            var curKeepTicket =
              keepAliveKindFromPath(curPath) || liveKeepAliveKind();
            if (curKeepTicket) parkLiveRoom(curKeepTicket);
            else {
              try {
                if (
                  global.SuiteRoomInit &&
                  global.SuiteRoomInit.teardown &&
                  global.SuiteRoomInit.name !== "skin" &&
                  global.SuiteRoomInit.name !== "overview"
                ) {
                  global.SuiteRoomInit.teardown();
                  global.SuiteRoomInit = null;
                }
              } catch (eTt) {}
            }
            document.documentElement.classList.add("suite-nav-busy");
            try {
              var okTicket = await global.SuitePaper.mountFullPageTicket(
                ticketId,
                { push: push !== false }
              );
              applyMapCityChrome(tgtPath);
              if (okTicket === false) {
                /* mount painted an error; stay on short path */
              }
            } catch (eTicket) {
              global.location.href = target;
              return;
            } finally {
              document.documentElement.classList.remove("suite-nav-busy");
            }
            return;
          }
        }
      }

      /*
       * Shortest paper path: /read → one /api/file, no HTML shell re-fetch.
       * (Full soft-nav was: fetch read_v1.html + re-exec + /api/file again.)
       */
      if (tgtPath === "/read") {
        var readParams = new URLSearchParams(
          target.indexOf("?") >= 0 ? target.split("?").slice(1).join("?") : ""
        );
        var paperPath = (readParams.get("path") || "").replace(/^\/+/, "");
        if (paperPath) {
          ensureSuitePaper();
          var paperReady = await new Promise(function (resolve) {
            if (
              global.SuitePaper &&
              typeof global.SuitePaper.mountFullPagePaper === "function"
            ) {
              resolve(true);
              return;
            }
            var t0 = Date.now();
            var iv = setInterval(function () {
              if (
                global.SuitePaper &&
                typeof global.SuitePaper.mountFullPagePaper === "function"
              ) {
                clearInterval(iv);
                resolve(true);
              } else if (Date.now() - t0 > 2500) {
                clearInterval(iv);
                resolve(false);
              }
            }, 20);
          });
          if (paperReady) {
            if (
              !document.getElementById("suite-body") &&
              !document.getElementById(MAP_PARK_ID) &&
              !document.getElementById(OV_PARK_ID)
            ) {
              global.location.href = target;
              return;
            }
            var curKeepRead =
              keepAliveKindFromPath(curPath) || liveKeepAliveKind();
            if (curKeepRead) parkLiveRoom(curKeepRead);
            else {
              try {
                if (
                  global.SuiteRoomInit &&
                  global.SuiteRoomInit.teardown &&
                  global.SuiteRoomInit.name !== "skin" &&
                  global.SuiteRoomInit.name !== "overview"
                ) {
                  global.SuiteRoomInit.teardown();
                  global.SuiteRoomInit = null;
                }
              } catch (eTr) {}
            }
            document.documentElement.classList.add("suite-nav-busy");
            try {
              var okMount = await global.SuitePaper.mountFullPagePaper(
                paperPath,
                { push: push !== false }
              );
              applyMapCityChrome(tgtPath);
              if (okMount === false) {
                /* mount painted an error; stay on short path */
              }
            } catch (eRead) {
              global.location.href = target;
              return;
            } finally {
              document.documentElement.classList.remove("suite-nav-busy");
            }
            return;
          }
        }
      }

      /* Need a live #suite-body or a parked keep-alive room */
      if (
        !document.getElementById("suite-body") &&
        !document.getElementById(MAP_PARK_ID) &&
        !document.getElementById(OV_PARK_ID)
      ) {
        global.location.href = target;
        return;
      }

      var tgtKeep = keepAliveKindFromPath(tgtPath);
      var curKeep =
        keepAliveKindFromPath(curPath) || liveKeepAliveKind();

      /*
       * Keep-alive restore (Map + Overview): no re-fetch, no blank Loading.
       * Map↔Settings was already fast; Map→Overview was remounting ~4–5s.
       */
      if (tgtKeep === "map" || tgtKeep === "overview") {
        if (restoreParkedRoom(tgtKeep, push, target)) {
          return;
        }
        /* First visit this session — fall through to mount */
      }

      /*
       * Leaving a keep-alive room: park instead of teardown.
       */
      if (curKeep && curKeep !== tgtKeep) {
        parkLiveRoom(curKeep);
      } else if (!curKeep) {
        /* Disposable room → somewhere: teardown current scripts */
        try {
          if (global.SuiteRoomInit && global.SuiteRoomInit.teardown) {
            var nm = global.SuiteRoomInit.name;
            if (nm !== "skin" && nm !== "overview") {
              global.SuiteRoomInit.teardown();
              global.SuiteRoomInit = null;
            } else if (
              nm === "skin" &&
              !document.getElementById(MAP_PARK_ID)
            ) {
              global.SuiteRoomInit.teardown();
              global.SuiteRoomInit = null;
            } else if (
              nm === "overview" &&
              !document.getElementById(OV_PARK_ID)
            ) {
              global.SuiteRoomInit.teardown();
              global.SuiteRoomInit = null;
            }
          }
        } catch (e) {
          /* ignore teardown errors */
        }
      }

      document.documentElement.classList.add("suite-nav-busy");
      /* Abort hung fetch so busy dim never sticks (pc-282 residual jank) */
      var ac =
        typeof AbortController !== "undefined" ? new AbortController() : null;
      var abortTimer = null;
      if (ac) {
        abortTimer = setTimeout(function () {
          try {
            ac.abort();
          } catch (e) {}
        }, 12000);
      }
      try {
        const res = await fetch(target, {
          credentials: "same-origin",
          signal: ac ? ac.signal : undefined,
          headers: { Accept: "text/html" },
        });
        if (!res.ok) {
          global.location.href = target;
          return;
        }
        const html = await res.text();
        const doc = new DOMParser().parseFromString(html, "text/html");
        const newBody = doc.getElementById("suite-body");
        if (!newBody) {
          global.location.href = target;
          return;
        }

        // Page CSS + City paint body chrome before body lands (avoids flash)
        syncPageCss(doc);
        applyMapCityChrome(tgtPath);
        syncMastFromDoc(doc);

        // Pull scripts out before DOM insertion (inline + src — neither auto-run on replaceWith)
        const scripts = Array.from(newBody.querySelectorAll("script:not([src])"));
        const extScripts = Array.from(newBody.querySelectorAll("script[src]"));
        scripts.forEach(function (s) {
          s.remove();
        });
        extScripts.forEach(function (s) {
          s.remove();
        });
        /*
         * Safety net: scripts left as siblings after #suite-body (legacy pages).
         * Prefer in-body scripts; append trailing only when body had none.
         */
        if (!scripts.length && doc.body) {
          var kids = doc.body.children;
          var after = false;
          for (var si = 0; si < kids.length; si++) {
            var eln = kids[si];
            if (eln.id === "suite-body") {
              after = true;
              continue;
            }
            if (
              after &&
              eln.tagName === "SCRIPT" &&
              !eln.getAttribute("src")
            ) {
              scripts.push(eln);
            }
          }
        }

        if (isWorkspaceMapPath(tgtPath)) {
          newBody.setAttribute("data-suite-room", "map");
        } else if (isOverviewShell(tgtPath)) {
          newBody.setAttribute("data-suite-room", "overview");
        } else if (isSettingsPath(tgtPath)) {
          newBody.setAttribute("data-suite-room", "settings");
        }

        const old = document.getElementById("suite-body");
        if (old) old.replaceWith(newBody);
        else document.body.appendChild(newBody);

        if (push !== false) history.pushState({}, "", target);
        document.title = doc.title || document.title;

        // Re-execute room init scripts in an IIFE (avoid const/let redeclare)
        scripts.forEach(function (s) {
          const el = document.createElement("script");
          el.textContent = "(function(){\n" + s.textContent + "\n})();";
          document.body.appendChild(el);
          el.remove();
        });
        /*
         * pc-893: Map app is external (/map/workspace_map_app.js). Soft-nav must
         * inject script[src] or Map never boots when not park-restored.
         */
        extScripts.forEach(function (s) {
          var src = s.getAttribute("src") || "";
          if (!src) return;
          /* Skip if already loaded same path (park soft-return shouldn't double) */
          var bare = src.split("?")[0];
          if (
            bare &&
            document.querySelector(
              'script[src^="' + bare.replace(/"/g, "") + '"]'
            )
          ) {
            /* Already present — Map park path; do not re-exec full app */
            return;
          }
          var el = document.createElement("script");
          el.src = src;
          document.body.appendChild(el);
        });

        // Jump box lives in suite-meta inside #suite-body — reinstall after swap
        installJump();
        /* pc-495: re-arm SuitePaper after body swap (script tags do not re-run) */
        ensureSuitePaper();
      } catch (e) {
        global.location.href = target;
      } finally {
        if (abortTimer) clearTimeout(abortTimer);
        document.documentElement.classList.remove("suite-nav-busy");
      }
    }

    // Intercept peer-door clicks (chrome stays mounted; listeners once)
    [
      "nav-map",
      "nav-desk",
      "nav-roster",
      "nav-home",
      "nav-settings",
    ].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el || el._suiteSoftNavBound) return;
      el._suiteSoftNavBound = true;
      el.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        const href = el.getAttribute("href") || "";
        softNavTo(href).catch(function () {
          global.location.href = href || workspaceMapHref();
        });
      });
    });

    /*
     * Shell-wide same-origin intercept (pc-403 / pc-495).
     * Cmd-click still hard-navigates. Explicit "full page" is a **one-shot**
     * soft-nav (Map parks; SuitePaper globals stay) — not a sticky mode and
     * not a hard reload that drops suite-paper.js.
     * /read + /ticket plain clicks default to SuitePaper when installed.
     */
    document.addEventListener(
      "click",
      function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (e.defaultPrevented) return;
        var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
        if (!a) return;
        if (a.target && a.target !== "" && a.target !== "_self") return;
        if (a.hasAttribute("download")) return;
        var href = a.getAttribute("href") || "";
        if (!href || href.charAt(0) === "#") return;
        if (/^(mailto:|tel:|javascript:)/i.test(href)) return;
        var path = "";
        var resolved = "";
        try {
          var u = new URL(href, global.location.origin);
          if (u.origin !== global.location.origin) return;
          path = u.pathname;
          resolved = u.pathname + u.search;
        } catch (err) {
          return;
        }
        /*
         * Explicit full-page escape (paper chrome, settings FULL PAGE, etc.).
         * One-shot soft-nav keeps SuitePaper installed so the next plain
         * /ticket|/read click is Scan again (pc-495). data-hard-nav opts out.
         */
        if (
          a.classList.contains("suite-paper-full") ||
          a.classList.contains("sss-full") ||
          a.getAttribute("data-suite-full") === "1"
        ) {
          if (a.getAttribute("data-hard-nav") === "1") return;
          if (!isShellPath(path) && a.id !== "workspace-map-entry") return;
          e.preventDefault();
          try {
            if (
              global.SuitePaper &&
              typeof global.SuitePaper.close === "function"
            ) {
              global.SuitePaper.close();
            }
          } catch (eClose) {}
          softNavTo(
            resolved.indexOf("/") === 0 ? resolved : workspaceMapHref()
          );
          return;
        }
        if (a.getAttribute("data-hard-nav") === "1") return;
        if (!isShellPath(path) && a.id !== "workspace-map-entry") return;
        /*
         * Paper overlay owns /read and /ticket when SuitePaper is live —
         * let its handler run (unless already handled).
         */
        if (
          (path === "/read" || path === "/ticket") &&
          global.SuitePaper &&
          typeof global.SuitePaper.open === "function"
        ) {
          return;
        }
        e.preventDefault();
        softNavTo(resolved.indexOf("/") === 0 ? resolved : workspaceMapHref());
      },
      false
    );

    global.addEventListener("popstate", function () {
      softNavTo(global.location.pathname + global.location.search, false);
    });

    global._suiteNavTo = softNavTo;
  }

  /* softNavTo is async — expose for Map/Overview callers */
  function softNavToPublic(href, push) {
    installSoftNav();
    if (typeof global._suiteNavTo === "function") {
      return global._suiteNavTo(href, push);
    }
    global.location.href = href;
    return Promise.resolve();
  }

  /* installJump only via apply() when surface is Desk */

  /**
   * Citizen display name for activity tape / Desk (pc-persona / You law).
   * Wire identity may still be founder-terminal or you; UI shows **You**.
   * Agents keep their persona ids.
   *   suite.youLabel = Map YOU dig-in display face (default "You" / seat YOU)
   * pc-664: suite.youAliases / suite.citizenId retired — aliases are the
   * built-in YOU_WIRE_DEFAULTS constant; browser wire id is always "you".
   */
  var YOU_WIRE_DEFAULTS = {
    you: true,
    "founder-terminal": true,
    founder: true,
    human: true,
    citizen: true,
    me: true,
    owner: true,
  };

  /* pc-664: clear retired identity knobs so old browsers land on law defaults. */
  try {
    if (global.localStorage) {
      localStorage.removeItem("suite.youAliases");
      localStorage.removeItem("suite.citizenId");
    }
  } catch (eClearYouId) {
    /* ignore */
  }

  function youLabel() {
    try {
      var L = (global.localStorage && localStorage.getItem("suite.youLabel")) || "";
      L = String(L).trim();
      if (L) return L;
    } catch (e) {
      /* ignore */
    }
    return "You";
  }

  function isYouAuthor(raw) {
    var a = String(raw || "")
      .trim()
      .toLowerCase();
    if (!a) return false;
    return !!YOU_WIRE_DEFAULTS[a];
  }

  /** Display form for a signed author id (tape, lists). Does not change storage. */
  function displayAuthor(raw) {
    if (raw == null || raw === "") return "—";
    if (isYouAuthor(raw)) return youLabel();
    return String(raw);
  }

  /** Wire id for new citizen writes from this browser — always you (pc-664). */
  function citizenAuthorId() {
    return "you";
  }

  global.SuiteNav = {
    projectFromSearch: projectFromSearch,
    workerFromSearch: workerFromSearch,
    projectFromCityPath: projectFromCityPath,
    placeLabel: placeLabel,
    placeHref: placeHref,
    overviewHref: overviewHref,
    workspaceHomeHref: workspaceHomeHref,
    workspaceMapHref: workspaceMapHref,
    isWorkspaceMapPath: isWorkspaceMapPath,
    isSettingsPath: isSettingsPath,
    isCalendarPath: isCalendarPath,
    projectEntryHref: projectEntryHref,
    projectBriefHref: projectBriefHref,
    softNavTo: softNavToPublic,
    settingsHref: settingsHref,
    displayAuthor: displayAuthor,
    isYouAuthor: isYouAuthor,
    youLabel: youLabel,
    citizenAuthorId: citizenAuthorId,
    peerRoomLabel: peerRoomLabel,
    cityMapHref: cityMapHref,
    getThemePref: getThemePref,
    setThemePref: setThemePref,
    applyTheme: applyTheme,
    getSpinePaintPref: getSpinePaintPref,
    setSpinePaintPref: setSpinePaintPref,
    applySpinePaint: applySpinePaint,
    roomScopeHref: roomScopeHref,
    deskHrefFor: deskHrefFor,
    isPlaceRoom: isPlaceRoom,
    apply: apply,
    ensureSpine: ensureSpine,
    spineOverviewHref: spineOverviewHref,
    contextStrip: contextStrip,
    ensureMeta: ensureMeta,
    installJump: installJump,
    installSoftNav: installSoftNav,
    ensureSuitePaper: ensureSuitePaper,
    normalizeTicketId: normalizeTicketId,
    openInFinder: openInFinder,
    wireFinderOpens: wireFinderOpens,
    suiteVersionLabel: suiteVersionLabel,
    mastWithVersion: mastWithVersion,
    setMastTitle: setMastTitle,
    paintSpineVersion: paintSpineVersion,
    docTitle: docTitle,
    workspaceFolderLabel: workspaceFolderLabel,
  };
})(typeof window !== "undefined" ? window : globalThis);
