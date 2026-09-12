/*! inspect-orbit.js — Inspect orbit chrome (pc-1414)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4).
 * Orbit list (`inspectOrbitGroup`) + header KPIs + Previous-panel button
 * live here only — host keeps thin wrappers so existing call sites stay put.
 *
 * Browser: window.InspectOrbit
 * Public: { init, group, paintKpis, paintBackBtn, isProseNote,
 *          proseNoteHtml, itemIconHtml }
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    bindYouSnoozeBar: null,
    ensureInspectToolbar: null,
    escHtml: null,
    getHandGlyph: null,
    getInstrGlyph: null,
    getJobGlyph: null,
    getStaffGlyph: null,
    getWorkGlyph: null,
    goHref: null,
    inspectHistoryLength: null,
    openInspect: null,
    openPaperInSuite: null,
    openTicketInSuite: null,
    paperPathFromHref: null,
    ticketIdFromHref: null
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  function bindYouSnoozeBar() {
    var fn = H("bindYouSnoozeBar");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function ensureInspectToolbar() {
    var fn = H("ensureInspectToolbar");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function escHtml() {
    var fn = H("escHtml");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function getHandGlyph(name) {
    var fn = H("getHandGlyph");
    return typeof fn === "function" ? fn(name) : "✋";
  }

  function getInstrGlyph() {
    var fn = H("getInstrGlyph");
    return typeof fn === "function" ? fn.apply(null, arguments) : "📜";
  }

  function getJobGlyph(name) {
    var fn = H("getJobGlyph");
    return typeof fn === "function" ? fn(name) : "⏰";
  }

  function getStaffGlyph(name) {
    var fn = H("getStaffGlyph");
    return typeof fn === "function" ? fn(name) : "📋";
  }

  function getWorkGlyph() {
    var fn = H("getWorkGlyph");
    return typeof fn === "function" ? fn.apply(null, arguments) : "🎫";
  }

  function goHref() {
    var fn = H("goHref");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function inspectHistoryLength() {
    var fn = H("inspectHistoryLength");
    var n = typeof fn === "function" ? fn() : 0;
    return n | 0;
  }

  function openInspect() {
    var fn = H("openInspect");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openPaperInSuite() {
    var fn = H("openPaperInSuite");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openTicketInSuite() {
    var fn = H("openTicketInSuite");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paperPathFromHref() {
    var fn = H("paperPathFromHref");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function ticketIdFromHref() {
    var fn = H("ticketIdFromHref");
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paintInspectBackBtn() {
    ensureInspectToolbar();
    const btn = document.getElementById("inspect-back");
    if (!btn) return;
    const n = inspectHistoryLength();
    btn.hidden = n <= 0;
    btn.setAttribute("aria-hidden", n <= 0 ? "true" : "false");
    if (n > 0) {
      btn.textContent =
        n > 1 ? "← Previous (" + n + ")" : "← Previous";
      btn.title =
        n +
        " prior detail view" +
        (n === 1 ? "" : "s") +
        " · not map dig depth";
    } else {
      btn.textContent = "← Previous";
      btn.title =
        "Previous sidebar view (details only — Dig path ← Up / Reset for map dig)";
    }
  }

  /**
   * pc-452: paint inspect header KPIs.
   * stats entries may be:
   *   string HTML (legacy) → muted info chip
   *   { label, value, gold?, live?, muted?, info?, action? }
   */
  function paintInspectKpis(host, stats) {
    if (!host) return;
    host.innerHTML = "";
    host.classList.add("inspect-kpis");
    const rows = stats || [];
    if (!rows.length) {
      host.hidden = true;
      return;
    }
    host.hidden = false;
    rows.forEach(function (row) {
      if (row == null || row === "") return;
      if (typeof row === "string") {
        const span = document.createElement("span");
        span.className = "inspect-kpi is-info is-muted";
        /* Legacy HTML rows (may contain <b>) */
        span.innerHTML =
          '<span class="l">stat</span><span class="v">' + row + "</span>";
        host.appendChild(span);
        return;
      }
      const label = String(row.label != null ? row.label : "");
      const value =
        row.value != null
          ? String(row.value)
          : String(row.v != null ? row.v : "");
      const hasAction = typeof row.action === "function";
      const el = document.createElement(hasAction ? "button" : "span");
      if (hasAction) el.type = "button";
      let cls = "inspect-kpi";
      if (row.gold) cls += " is-gold";
      if (row.stuck) cls += " is-stuck";
      if (row.live) cls += " is-live";
      if (row.muted) cls += " is-muted";
      else if (!hasAction && !row.hero && !row.gold && !row.stuck && !row.live)
        cls += " is-muted";
      if (!hasAction) cls += " is-info";
      el.className = cls;
      if (row.id) el.dataset.kpiId = String(row.id);
      el.innerHTML =
        '<span class="l">' +
        escHtml(label) +
        '</span><span class="v">' +
        escHtml(value) +
        "</span>";
      if (row.title) el.title = String(row.title);
      if (hasAction) {
        el.setAttribute("aria-label", (label ? label + ": " : "") + value);
        el.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          try {
            row.action();
          } catch (errA) {
            console.warn("inspect kpi action", errA);
          }
        });
      }
      host.appendChild(el);
    });
  }

  /**
   * pc-451: quiet/empty/stub rows are prose notes — not inspect-list-item cards.
   * Real objects keep cards + icons (hand/job/folder/law/paper/ticket).
   */
  function inspectIsProseNote(it) {
    if (!it || it.section) return false;
    if (it.empty || it.note) return true;
    if (!it.inert) return false;
    if (typeof it.action === "function" || it.href) return false;
    if (it.icon || it.kind || it.isHand || it.isJob || it.law) return false;
    return true;
  }

  function inspectProseNoteHtml(it) {
    return (
      '<p class="you-form-note inspect-note" role="note">' +
      '<span class="note-title">' +
      escHtml((it && it.label) || "") +
      "</span>" +
      (it && it.sub
        ? '<span class="sub">' + escHtml(it.sub) + "</span>"
        : "") +
      "</p>"
    );
  }

  /**
   * Leading mark for list cards — bare emoji (pc-856 map seat DNA).
   */
  function inspectItemIconHtml(it) {
    if (!it) return "";
    if (inspectIsProseNote(it)) return "";
    /* Plain text section headers (no icon) — clickable folder sections keep chips */
    if (
      it.section &&
      !it.icon &&
      !it.kind &&
      typeof it.action !== "function"
    )
      return "";
    let kind = String(it.icon || it.kind || "").toLowerCase();
    if (!kind) {
      if (it.isJob || it.kind === "job") kind = "job";
      else if (it.isHand || it.kind === "agent" || it.kind === "hand")
        kind = "hand";
      else if (it.kind === "law" || it.law) kind = "law";
      else if (it.kind === "folder" || it.kind === "folder-here") kind = "folder";
      else if (it.href && String(it.href).indexOf("/read") >= 0) kind = "paper";
      else if (it.href && String(it.href).indexOf("/ticket") >= 0) kind = "paper";
      else if (it.href || typeof it.action === "function") kind = "paper";
      else return ""; /* pc-451: no silent paper default for inert empties */
    }
    if (kind === "folder-here" || it.here) kind = "folder-here";
    /* pc-856: bare glyphs only — map seat DNA (no plate fill) */
    let glyph = "📄";
    let cls = "card-ic is-paper";
    if (kind === "job") {
      glyph = getJobGlyph(it.name || it.id || "");
      cls = "card-ic is-job";
    } else if (kind === "staff") {
      glyph = getStaffGlyph(it.name || it.id || "");
      cls = "card-ic is-staff";
    } else if (kind === "hand" || kind === "agent") {
      glyph = getHandGlyph(it.name || it.id || "");
      cls = "card-ic is-agent";
    } else if (kind === "law") {
      glyph = getInstrGlyph();
      cls = "card-ic is-law";
    } else if (kind === "folder" || kind === "folder-here") {
      glyph = "📁";
      cls =
        "card-ic is-folder" +
        (kind === "folder-here" || it.here ? " is-folder-here" : "");
    } else if (kind === "ticket" || kind === "wo") {
      glyph = getWorkGlyph();
      cls = "card-ic is-paper";
    }
    return (
      '<span class="' +
      cls +
      '" aria-hidden="true"><span class="glyph">' +
      glyph +
      "</span></span>"
    );
  }

  function inspectOrbitGroup(spec) {
    spec = spec || {};
    const items = spec.items || [];
    /* Seat digs always replace so Map clicks retarget the rail (pc-826) */
    const forceReplace = spec.replace !== false;
    const openable = items.filter(function (it) {
      return it && !it.inert && !it.section && !inspectIsProseNote(it);
    }).length;
    const listHtml =
      items.length === 0
        ? '<p class="you-form-note inspect-note">Nothing in this group.</p>'
        : '<div class="inspect-list" role="list">' +
          items
            .map(function (it, i) {
              if (inspectIsProseNote(it)) {
                return inspectProseNoteHtml(it);
              }
              const isSec = !!it.section;
              const inertOnly = !!it.inert && !it.section && !it.action;
              const clickableSec =
                isSec && typeof it.action === "function";
              /* Folder section headers get manila chips; plain sections stay text-only */
              const showIcon =
                !isSec ||
                clickableSec ||
                it.icon ||
                it.kind === "folder" ||
                it.kind === "folder-here";
              const icon = showIcon ? inspectItemIconHtml(it) : "";
              return (
                '<button type="button" class="inspect-list-item' +
                (inertOnly ? " is-inert" : "") +
                (isSec ? " is-section" : "") +
                (clickableSec ? " is-section-link" : "") +
                (it.here ? " is-here" : "") +
                '" data-i="' +
                i +
                '" role="listitem"' +
                (inertOnly ? ' tabindex="-1"' : "") +
                (clickableSec
                  ? ' title="Open this folder in Finder"'
                  : "") +
                ">" +
                icon +
                '<span class="card-body">' +
                '<span class="card-title">' +
                escHtml(it.label || "?") +
                "</span>" +
                (it.sub
                  ? '<span class="sub">' + escHtml(it.sub) + "</span>"
                  : "") +
                "</span></button>"
              );
            })
            .join("") +
          "</div>";
    openInspect(
      {
        el: spec.el || null,
        kind: spec.kind || "Group",
        title: spec.title || "Group",
        panelKey: spec.panelKey || "",
        surface: spec.surface || undefined,
        meta:
          (spec.meta ||
            "Map position already shows where this sits · open items here") +
          (spec.skipPaperMeta
            ? ""
            : " · papers: click Summary · ⌘-click full page"),
        stats: spec.stats || [
          "<b>" +
            openable +
            "</b> item" +
            (openable === 1 ? "" : "s") +
            (items.length > openable ? " · grouped list" : ""),
        ],
        formHtml: (spec.formPrefix || "") + listHtml,
        doors: spec.doors || [],
        afterOpen: function (host) {
          if (!host) return;
          try {
            bindYouSnoozeBar(host);
          } catch (eSz) {}
          host.querySelectorAll(".inspect-list-item").forEach(function (btn) {
            btn.addEventListener("click", function (e) {
              e.preventDefault();
              e.stopPropagation();
              const i = parseInt(btn.getAttribute("data-i"), 10);
              const it = items[i];
              if (!it) return;
              if (typeof it.action === "function") {
                it.action();
                return;
              }
              if (it.inert || it.section) return;
              if (it.href) {
                const paper = paperPathFromHref(it.href);
                if (paper) {
                  if (e.metaKey || e.ctrlKey) {
                    goHref(it.href);
                    return;
                  }
                  openPaperInSuite(paper);
                  return;
                }
                /* pc-717: dig-in WO rows used goHref → full ticket page; glass first */
                const tid = ticketIdFromHref(it.href);
                if (tid) {
                  openTicketInSuite(tid, e);
                  return;
                }
                goHref(it.href);
              }
            });
          });
          if (typeof spec.afterOpen === "function") {
            try {
              spec.afterOpen(host, items);
            } catch (eA) {}
          }
        },
      },
      forceReplace || spec.replace ? { replace: true } : undefined
    );
  }

  var InspectOrbit = {
    init: init,
    group: inspectOrbitGroup,
    paintKpis: paintInspectKpis,
    paintBackBtn: paintInspectBackBtn,
    isProseNote: inspectIsProseNote,
    proseNoteHtml: inspectProseNoteHtml,
    itemIconHtml: inspectItemIconHtml,
  };

  function init(host) {
    if (!host || typeof host !== "object") return InspectOrbit;
    Object.keys(host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return InspectOrbit;
  }

  global.InspectOrbit = InspectOrbit;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = InspectOrbit;
  }
})(typeof window !== "undefined" ? window : globalThis);
