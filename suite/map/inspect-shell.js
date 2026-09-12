/*! inspect-shell.js — Inspect rail shell (pc-1415)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4).
 * openInspect / history stack / toolbar / closeInspect live here only —
 * host keeps thin wrappers so existing call sites stay put.
 *
 * Browser: window.InspectShell
 * Public: { init, open, close, back, panelId, ensureToolbar, setRailOpen,
 *          scrollSection, historyLength }
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    clearInspectSnippet: null,
    clearMapEntitySelection: null,
    fillAgentsSnippet: null,
    getInspectEl: null,
    onInspectClosed: null,
    paintInspectBackBtn: null,
    paintInspectKpis: null,
    paintSettingsFab: null,
    selectMapEntity: null,
    setInspectSurface: null
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  function getInspectEl() {
    var fn = H("getInspectEl");
    return typeof fn === "function" ? fn() : null;
  }

  function selectMapEntity() {
    var fn = H("selectMapEntity");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function setInspectSurface(s) {
    var fn = H("setInspectSurface");
    if (typeof fn === "function") fn(s);
  }

  function paintInspectKpis() {
    var fn = H("paintInspectKpis");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function fillAgentsSnippet() {
    var fn = H("fillAgentsSnippet");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function clearInspectSnippet() {
    var fn = H("clearInspectSnippet");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paintInspectBackBtn() {
    var fn = H("paintInspectBackBtn");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paintSettingsFab() {
    var fn = H("paintSettingsFab");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function clearMapEntitySelection() {
    var fn = H("clearMapEntitySelection");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function onInspectClosed() {
    var fn = H("onInspectClosed");
    if (typeof fn === "function") fn();
  }

  /*
   * Right-rail inspect history: stack previous panels so Previous panel returns
   * (jobs list → job dig-in → Previous panel → jobs list) without full reset.
   * NOT map dig / expand — that is Dig path (← Up) and Reset view (pc-776).
   *
   * pc-780: same kind+title remount (poll soft-refresh, dig overview re-paint,
   * desk fetch remount) must REPLACE not push — otherwise count climbs to 9+
   * for one place with no real navigation.
   */
  var _inspectHistory = [];
  var _inspectCurrent = null; /* { id, kind, title, reopen } */
  var INSPECT_HISTORY_MAX = 8;

  function inspectHistoryLength() {
    return (_inspectHistory || []).length;
  }

  /** Stable id for stack dedupe — not full formHtml (that changes every paint). */
  function inspectPanelId(opts) {
    opts = opts || {};
    const kind = String(opts.kind || "").trim().toLowerCase();
    const title = String(opts.title || "").trim().toLowerCase();
    const key = String(opts.panelKey || opts.seat || "").trim().toLowerCase();
    /* Settings is one panel; seat digs key by panelKey so selection always retargets */
    return kind + "::" + title + (key ? "::" + key : "");
  }

  function ensureInspectToolbar() {
    var inspectEl = getInspectEl();
    if (!inspectEl) return null;
    let bar = document.getElementById("inspect-toolbar");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "inspect-toolbar";
      bar.className = "inspect-toolbar";
      inspectEl.insertBefore(bar, inspectEl.firstChild);
    }
    let back = document.getElementById("inspect-back");
    if (!back) {
      back = document.createElement("button");
      back.type = "button";
      back.id = "inspect-back";
      back.className = "inspect-back";
      back.textContent = "← Previous";
      bar.insertBefore(back, bar.firstChild);
    }
    if (!back._wiredInspectBack) {
      back._wiredInspectBack = true;
      back.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        inspectBack();
      });
    }
    let spacer = bar.querySelector(".inspect-toolbar-spacer");
    if (!spacer) {
      spacer = document.createElement("span");
      spacer.className = "inspect-toolbar-spacer";
      spacer.setAttribute("aria-hidden", "true");
      bar.appendChild(spacer);
    }
    let closeBtn = document.getElementById("inspect-close");
    if (!closeBtn) {
      closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.id = "inspect-close";
      closeBtn.className = "inspect-close";
      closeBtn.setAttribute("aria-label", "Close details");
      closeBtn.title = "Close details";
      closeBtn.textContent = "×";
      bar.appendChild(closeBtn);
    }
    if (!closeBtn._wiredInspectClose) {
      closeBtn._wiredInspectClose = true;
      closeBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        closeInspect({ clearHistory: true, clearEntity: true });
        try {
          paintSettingsFab();
        } catch (eFab) {}
      });
    }
    return bar;
  }

  function inspectBack() {
    if (!_inspectHistory.length) {
      closeInspect({ clearHistory: true });
      return;
    }
    const prev = _inspectHistory.pop();
    paintInspectBackBtn();
    if (prev && typeof prev.reopen === "function") {
      prev.reopen();
    }
  }

  /**
   * pc-452: scroll inspect list to a section whose title contains match.
   * Returns true if a section was found.
   */
  function scrollInspectSection(match) {
    const form = document.getElementById("inspect-form");
    if (!form || !match) return false;
    const m = String(match).toLowerCase();
    /* Place pulse cells first (for you / map work / presence) */
    const pulseNodes = form.querySelectorAll("[data-pulse]");
    for (let pi = 0; pi < pulseNodes.length; pi++) {
      const pel = pulseNodes[pi];
      const pid = String(pel.getAttribute("data-pulse") || "").toLowerCase();
      const ptxt = String(pel.textContent || "").toLowerCase();
      if (pid.indexOf(m) < 0 && ptxt.indexOf(m) < 0) continue;
      try {
        pel.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } catch (eP) {
        try {
          pel.scrollIntoView(true);
        } catch (eP2) {}
      }
      pel.classList.add("is-kpi-flash");
      setTimeout(function () {
        try {
          pel.classList.remove("is-kpi-flash");
        } catch (eR) {}
      }, 900);
      return true;
    }
    const nodes = form.querySelectorAll(
      ".inspect-list-item.is-section, .inspect-list-item.is-section-link"
    );
    for (let i = 0; i < nodes.length; i++) {
      const btn = nodes[i];
      const titleEl = btn.querySelector(".card-title");
      const t = String(
        (titleEl && titleEl.textContent) || btn.textContent || ""
      ).toLowerCase();
      if (t.indexOf(m) < 0) continue;
      try {
        btn.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } catch (eScr) {
        try {
          btn.scrollIntoView(true);
        } catch (e2) {}
      }
      btn.classList.add("is-kpi-flash");
      setTimeout(function () {
        try {
          btn.classList.remove("is-kpi-flash");
        } catch (eR) {}
      }, 900);
      return true;
    }
    return false;
  }

  /**
   * openInspect(opts, flags?)
   * flags.replace — do not push current onto history (used when restoring)
   * flags.skipHistory — open without stacking (rare)
   * Same panel id while already open ⇒ auto-replace (pc-780).
   */
  function openInspect(opts, flags) {
    opts = opts || {};
    flags = flags || {};
    var inspectEl = getInspectEl();
    const wasOpen = !!(inspectEl && inspectEl.classList.contains("is-open"));
    const nextId = inspectPanelId(opts);
    const samePanel =
      wasOpen &&
      _inspectCurrent &&
      _inspectCurrent.id &&
      nextId &&
      _inspectCurrent.id === nextId;
    if (samePanel) {
      flags = Object.assign({}, flags, { replace: true });
    }
    if (
      wasOpen &&
      !flags.replace &&
      !flags.skipHistory &&
      _inspectCurrent &&
      typeof _inspectCurrent.reopen === "function"
    ) {
      /* Dedupe: don't push identical id twice in a row */
      const last = _inspectHistory[_inspectHistory.length - 1];
      if (!last || last.id !== _inspectCurrent.id) {
        _inspectHistory.push(_inspectCurrent);
      }
      if (_inspectHistory.length > INSPECT_HISTORY_MAX) {
        _inspectHistory.shift();
      }
    }
    if (opts.el) {
      const elClass = opts.el.classList;
      const isFolderEntity =
        !!(
          elClass &&
          (elClass.contains("hier-project") || elClass.contains("lot"))
        ) ||
        (opts.el.getAttribute &&
          opts.el.getAttribute("data-entity-kind") === "folder");
      const selectedSlug =
        isFolderEntity &&
        opts.el.getAttribute &&
        (opts.el.getAttribute("data-slug") ||
          opts.el.getAttribute("data-entity-slug") ||
          opts.el.getAttribute("data-name"));
      if (selectedSlug) {
        selectMapEntity({ kind: "folder", slug: selectedSlug });
      } else if (opts.el.id === "workspace-badge") {
        selectMapEntity({ kind: "folder", slug: "__you__" });
      }
    }
    document.getElementById("inspect-kind").textContent = opts.kind || "Inspect";
    document.getElementById("inspect-title").textContent = opts.title || "—";
    document.getElementById("inspect-meta").textContent = opts.meta || "";
    /* pc-1043: state-driven soft dispatch — set once at open, not from DOM text */
    if (opts.surface) {
      setInspectSurface(String(opts.surface));
    } else {
      const kl = String(opts.kind || "")
        .trim()
        .toLowerCase();
      if (kl.indexOf("you") === 0) setInspectSurface("you");
      else if (kl.indexOf("workspace") === 0) setInspectSurface("workspace");
      else if (kl.indexOf("project") === 0) setInspectSurface("project");
      else setInspectSurface(null);
    }
    const stats = document.getElementById("inspect-stats");
    paintInspectKpis(stats, opts.stats || []);
    /* Optional form body (You identity) — between stats and doors */
    let formHost = document.getElementById("inspect-form");
    if (!formHost) {
      formHost = document.createElement("div");
      formHost.id = "inspect-form";
      const snip = document.getElementById("inspect-snippet");
      if (snip && snip.parentNode) {
        snip.parentNode.insertBefore(formHost, snip);
      } else {
        stats.parentNode.insertBefore(formHost, stats.nextSibling);
      }
    }
    formHost.innerHTML = "";
    if (typeof opts.formHtml === "string" && opts.formHtml) {
      formHost.innerHTML = opts.formHtml;
    }
    /* pc-365: AGENTS snippet only when requested (project houses) */
    if (opts.agentsSnippetPath) {
      fillAgentsSnippet(opts.agentsSnippetPath, opts.agentsReadHref || "");
    } else {
      clearInspectSnippet();
    }
    if (typeof opts.afterOpen === "function") {
      try {
        opts.afterOpen(formHost);
      } catch (err) {
        console.warn("inspect afterOpen", err);
      }
    }
    const doors = document.getElementById("inspect-doors");
    doors.innerHTML = "";
    (opts.doors || []).forEach(function (d) {
      if (d && typeof d.action === "function") {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = d.label;
        b.className = (d.primary ? "primary " : "") + (d.className || "");
        b.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          d.action();
        });
        doors.appendChild(b);
        return;
      }
      if (!d || !d.href) return;
      /* Drop Overview peer hops — Map is the only room */
      if (
        d.href === "/" ||
        d.href === "/overview" ||
        /^\/overview(\?|$)/.test(d.href)
      ) {
        return;
      }
      const a = document.createElement("a");
      a.href = d.href;
      a.textContent = d.label;
      if (d.primary) a.className = "primary";
      doors.appendChild(a);
    });
    if (inspectEl) inspectEl.classList.add("is-open");
    setInspectRailOpen(true);
    _inspectCurrent = {
      id: nextId,
      kind: opts.kind || "",
      title: opts.title || "",
      reopen: function () {
        openInspect(opts, { replace: true });
      },
    };
    paintInspectBackBtn();
  }

  function setInspectRailOpen(on) {
    const shell = document.getElementById("map-shell");
    const rail = document.getElementById("map-right");
    if (shell) shell.classList.toggle("has-inspect", !!on);
    if (rail) {
      rail.hidden = !on;
      rail.setAttribute("aria-hidden", on ? "false" : "true");
    }
  }

  function closeInspect(flags) {
    flags = flags || {};
    var inspectEl = getInspectEl();
    if (!inspectEl) return;
    inspectEl.classList.remove("is-open");
    if (flags.clearEntity !== false) clearMapEntitySelection();
    clearInspectSnippet();
    setInspectRailOpen(false);
    if (flags.clearHistory !== false) {
      _inspectHistory = [];
      _inspectCurrent = null;
    }
    paintInspectBackBtn();
    try {
      paintSettingsFab();
    } catch (eFab) {}
    try {
      onInspectClosed();
    } catch (eClosed) {}
  }

  var InspectShell = {
    init: init,
    open: openInspect,
    close: closeInspect,
    back: inspectBack,
    panelId: inspectPanelId,
    ensureToolbar: ensureInspectToolbar,
    setRailOpen: setInspectRailOpen,
    scrollSection: scrollInspectSection,
    historyLength: inspectHistoryLength,
  };

  function init(host) {
    if (!host || typeof host !== "object") return InspectShell;
    Object.keys(host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return InspectShell;
  }

  global.InspectShell = InspectShell;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = InspectShell;
  }
})(typeof window !== "undefined" ? window : globalThis);
