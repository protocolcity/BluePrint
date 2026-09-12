/*! inspect-you.js — You / For You inspect panel renderer (pc-1405)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4).
 * You tray prefs + inspectYou + fill/list/snooze/toolbar live here only —
 * host keeps thin wrappers so existing call sites stay put.
 *
 * Browser: window.InspectYou
 * Public: { init, show, fill, bindSnooze, applyFaceQuery, faceFromQuery,
 *          setClassPref, formatSnoozeUntil, productSnoozeActive,
 *          youSnoozeBarHtml, watchRowModel }
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    buildScene: null,
    escHtml: null,
    fetchJsonTimeout: null,
    forYouAgeLabel: null,
    forYouAskLine: null,
    forYouAttItems: null,
    forYouCountsByProduct: null,
    forYouFocusTitle: null,
    forYouInboxCategory: null,
    forYouProductLabel: null,
    forYouRowModel: null,
    goHref: null,
    normalizeStoreSlug: null,
    openInspect: null,
    paintInspectKpis: null,
    paintMapInsights: null,
    setMapWoFilterFromInspect: null,
    sortForYouByGroupThenUrgency: null,
    sortForYouByProjectThenUrgency: null,
    stalledAttItems: null,
    storeSlugEquivalents: null,
    youIdentityBits: null,
    getLastAtt: null,
    setLastAtt: null,
    getLastTpScene: null,
    getLastCityData: null,
    getLastPeople: null,
    getModel: null,
    getAttentionByProduct: null,
    setAttentionByProduct: null,
    setPrevAttentionByProduct: null,
    setAttStickyPending: null
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  function buildScene() {
    var fn = H('buildScene');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function escHtml() {
    var fn = H('escHtml');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function fetchJsonTimeout() {
    var fn = H('fetchJsonTimeout');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouAgeLabel() {
    var fn = H('forYouAgeLabel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouAskLine() {
    var fn = H('forYouAskLine');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouAttItems() {
    var fn = H('forYouAttItems');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouCountsByProduct() {
    var fn = H('forYouCountsByProduct');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouFocusTitle() {
    var fn = H('forYouFocusTitle');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouInboxCategory() {
    var fn = H('forYouInboxCategory');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouProductLabel() {
    var fn = H('forYouProductLabel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouRowModel() {
    var fn = H('forYouRowModel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function goHref() {
    var fn = H('goHref');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function normalizeStoreSlug() {
    var fn = H('normalizeStoreSlug');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openInspect() {
    var fn = H('openInspect');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paintInspectKpis() {
    var fn = H('paintInspectKpis');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paintMapInsights() {
    var fn = H('paintMapInsights');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function setMapWoFilterFromInspect() {
    var fn = H('setMapWoFilterFromInspect');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function sortForYouByGroupThenUrgency() {
    var fn = H('sortForYouByGroupThenUrgency');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function sortForYouByProjectThenUrgency() {
    var fn = H('sortForYouByProjectThenUrgency');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function stalledAttItems() {
    var fn = H('stalledAttItems');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function storeSlugEquivalents() {
    var fn = H('storeSlugEquivalents');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function youIdentityBits() {
    var fn = H('youIdentityBits');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function lastAtt() {
    var fn = H('getLastAtt');
    return typeof fn === "function" ? fn() : null;
  }
  function setLastAtt(v) {
    var fn = H('setLastAtt');
    if (typeof fn === "function") fn(v);
  }
  function lastTpScene() {
    var fn = H('getLastTpScene');
    return typeof fn === "function" ? fn() : null;
  }
  function lastCityData() {
    var fn = H('getLastCityData');
    return typeof fn === "function" ? fn() : null;
  }
  function lastPeople() {
    var fn = H('getLastPeople');
    return typeof fn === "function" ? fn() : null;
  }
  function getModel() {
    var fn = H('getModel');
    return typeof fn === "function" ? fn() : null;
  }
  function attentionByProduct() {
    var fn = H('getAttentionByProduct');
    return typeof fn === "function" ? fn() : null;
  }
  function setAttentionByProduct(v) {
    var fn = H('setAttentionByProduct');
    if (typeof fn === "function") fn(v);
  }
  function setPrevAttentionByProduct(v) {
    var fn = H('setPrevAttentionByProduct');
    if (typeof fn === "function") fn(v);
  }
  function setAttStickyPending(v) {
    var fn = H('setAttStickyPending');
    if (typeof fn === "function") fn(v);
  }

  /* pc-888: You tray filter prefs (class · group · project). Gold count stays unfiltered. */
  var LS_YOU_FY_CLASS = "suite.youFyClass";
  var LS_YOU_FY_GROUP = "suite.youFyGroup";
  var LS_YOU_FY_PROJECT = "suite.youFyProject";

  function youFyClassPref() {
    try {
      const raw = localStorage.getItem(LS_YOU_FY_CLASS);
      /* pc-1201: default pulse = Decide (one body slice), not All dump */
      if (raw == null || String(raw).trim() === "") return "needs_you";
      let v = String(raw || "needs_you")
        .toLowerCase()
        .trim();
      /* pc-950: Read/Decide aliases → filter keys reports | needs_you | watch */
      if (v === "read") v = "reports";
      if (v === "decide") v = "needs_you";
      if (
        v === "reports" ||
        v === "needs_you" ||
        v === "all" ||
        v === "watch"
      )
        return v;
    } catch (e) {}
    return "needs_you";
  }

  function youFyGroupPref() {
    try {
      const v = String(localStorage.getItem(LS_YOU_FY_GROUP) || "category")
        .toLowerCase()
        .trim();
      if (v === "project" || v === "category") return v;
    } catch (e) {}
    return "category";
  }

  function youFyProjectPref() {
    try {
      const v = String(localStorage.getItem(LS_YOU_FY_PROJECT) || "all")
        .toLowerCase()
        .trim();
      return v || "all";
    } catch (e) {
      return "all";
    }
  }

  function setYouFyClassPref(v) {
    let n = String(v || "needs_you").toLowerCase().trim();
    if (n === "read") n = "reports";
    if (n === "decide") n = "needs_you";
    const ok =
      n === "reports" || n === "needs_you" || n === "all" || n === "watch"
        ? n
        : "needs_you";
    try {
      localStorage.setItem(LS_YOU_FY_CLASS, ok);
    } catch (e) {}
    return ok;
  }

  /** pc-1279 / pc-1304: Overview hops — `/workspace-map?you=read|watch|decide|note`. */
  function youFaceFromQuery() {
    try {
      const raw = String(
        new URLSearchParams(window.location.search || "").get("you") || ""
      )
        .toLowerCase()
        .trim();
      if (!raw) return "";
      if (raw === "read" || raw === "reports") return "reports";
      if (raw === "watch") return "watch";
      if (raw === "decide" || raw === "needs_you") return "needs_you";
      if (raw === "note" || raw === "yours" || raw === "list") return "note";
      if (raw === "all") return "all";
    } catch (e) {}
    return "";
  }

  function applyYouFaceQuery() {
    const face = youFaceFromQuery();
    if (!face) return false;
    /* pc-1304: Note is the quiet worker:you list — not For You gold. */
    if (face === "note") {
      try {
        if (global.WoTape) WoTape.setProjectKey("");
        if (typeof setMapWoFilterFromInspect === "function") {
          setMapWoFilterFromInspect("yours");
        } else if (global.WoTape) {
          WoTape.setFilter("yours");
        }
        var tape =
          document.getElementById("map-wo-filters") ||
          document.getElementById("map-wo-cap") ||
          document.querySelector(".map-wo-tape");
        if (tape && tape.scrollIntoView) {
          tape.scrollIntoView({ block: "nearest" });
        }
      } catch (eNote) {}
      return true;
    }
    setYouFyClassPref(face);
    try {
      if (global.WoTape) WoTape.setProjectKey("");
      if (typeof setMapWoFilterFromInspect === "function") {
        setMapWoFilterFromInspect("for_you");
      } else if (global.WoTape) {
        WoTape.setFilter("for_you");
      }
    } catch (eFilt) {}
    if (typeof inspectYou === "function") inspectYou();
    return true;
  }

  function setYouFyGroupPref(v) {
    const n = String(v || "category").toLowerCase().trim();
    const ok = n === "project" ? "project" : "category";
    try {
      localStorage.setItem(LS_YOU_FY_GROUP, ok);
    } catch (e) {}
    return ok;
  }

  function setYouFyProjectPref(v) {
    const n = String(v || "all").toLowerCase().trim() || "all";
    try {
      localStorage.setItem(LS_YOU_FY_PROJECT, n);
    } catch (e) {}
    return n;
  }

  /**
   * Effective project filter for the For You list. Canonicalizes the saved
   * pref and self-heals when it's stale: a slug with zero gold in the current
   * membership can't be picked from the select (options only list products
   * with gold), so it silently zeroed the list while the select displayed
   * "All projects". Stale → reset to all.
   */
  function youFyEffectiveProject(allItems) {
    const pref = youFyProjectPref();
    if (!pref || pref === "all") return "all";
    const canon = normalizeStoreSlug(pref);
    const by = forYouCountsByProduct(allItems || []);
    if (!canon || !by[canon]) {
      setYouFyProjectPref("all");
      return "all";
    }
    return canon;
  }

  /** Report-class only (bulk-safe). Aligns with forYouInboxCategory reports. */
  function isForYouReportItem(it) {
    return forYouInboxCategory(it || {}).key === "reports";
  }

  /**
   * pc-888 / pc-950: filter For You list without changing gold membership.
   * classFilter: all | reports|read | needs_you|decide
   * projectFilter: product slug or all
   */
  function filterForYouListItems(items, classFilter, projectFilter) {
    let cls = String(classFilter || "needs_you").toLowerCase();
    if (cls === "read") cls = "reports";
    if (cls === "decide") cls = "needs_you";
    const proj = String(projectFilter || "all").toLowerCase().trim();
    /* pc-1090 grammar: canonical-slug match, never raw string (alias-safe) */
    const want = proj && proj !== "all" ? storeSlugEquivalents(proj) : null;
    return (items || []).filter(function (it) {
      if (!it) return false;
      if (want) {
        const p = normalizeStoreSlug(it.product || it.project || it.store || "");
        if (want.indexOf(p) < 0) return false;
      }
      /* watch slice: gold list empty (Watch band only) */
      if (cls === "watch") return false;
      if (cls === "reports") return isForYouReportItem(it);
      if (cls === "needs_you") return !isForYouReportItem(it);
      return true;
    });
  }

  function youForYouReportIds(items) {
    return (items || [])
      .filter(isForYouReportItem)
      .map(function (it) {
        return String(it.id || "").trim();
      })
      .filter(Boolean);
  }

  function youFyToolbarHtml(allItems, filteredN, watchN) {
    const cls = youFyClassPref();
    const group = youFyGroupPref();
    const projPref = youFyEffectiveProject(allItems || []);
    const total = (allItems || []).length;
    const nRep = (allItems || []).filter(isForYouReportItem).length;
    const nNeed = total - nRep;
    const nWatch = watchN | 0;
    const byProd = forYouCountsByProduct(allItems || []);
    const prods = Object.keys(byProd).sort(function (a, b) {
      return forYouProductLabel(a).localeCompare(forYouProductLabel(b));
    });
    /* pc-1201 / pc-1210: face pulse = FULL place-dig grammar —
     * label + count + reason line + severity accent, selected drives body slice.
     * Same anatomy as PLACE PULSE so You dig and place digs read as one chrome. */
    function pulseCell(val, lab, n, sev, reason) {
      const on = cls === val;
      const quiet = !(n > 0) && val !== "all";
      return (
        /* pc-1210: pure place-pulse cell — no pill-chip class, severity accents live */
        '<button type="button" class="inspect-pulse-cell' +
        (on ? " is-selected is-on" : "") +
        (n > 0 && sev ? " " + sev : "") +
        (quiet ? " is-quiet" : "") +
        '" data-you-fy="class" data-val="' +
        escHtml(val) +
        '" aria-pressed="' +
        (on ? "true" : "false") +
        '">' +
        '<span class="pulse-lab">' +
        escHtml(lab) +
        "</span>" +
        '<span class="pulse-val">' +
        escHtml(String(n)) +
        "</span>" +
        (reason
          ? '<span class="pulse-reason">' + escHtml(reason) + "</span>"
          : "") +
        "</button>"
      );
    }
    let html =
      '<div class="you-fy-toolbar you-fy-pulse-toolbar" id="map-you-fy-toolbar" role="toolbar" aria-label="For You face pulse">';
    html +=
      '<div class="inspect-pulse you-fy-seg" role="group" aria-label="Face">' +
      pulseCell(
        "needs_you",
        "Decide",
        nNeed,
        "is-gold",
        nNeed > 0
          ? "Rulings · gates waiting on You — open to act"
          : "No decisions waiting"
      ) +
      pulseCell(
        "reports",
        "Read",
        nRep,
        "is-gold",
        nRep > 0
          ? "Reports · briefs — mark read when skimmed"
          : "No unread papers"
      ) +
      pulseCell(
        "watch",
        "Watch",
        nWatch,
        "is-queued",
        nWatch > 0
          ? "Timers · stalled — not counted in gold"
          : "No timers or stalled work"
      ) +
      pulseCell(
        "all",
        "All",
        total,
        "is-gold",
        "Gold together · Watch band underneath"
      ) +
      "</div>";
    /* pc-1213 polish: ONE control line — group toggle + project filter.
     * "By project / By urgency" = ordering; "Show:" select = filter.
     * Distinct captions so the two stop reading as overlapping functions. */
    html += '<div class="you-fy-controls-row">';
    html +=
      '<div class="you-fy-seg you-fy-sort-seg" role="group" aria-label="Group order">' +
      '<button type="button" class="you-fy-chip' +
      (group === "project" ? " is-on" : "") +
      '" data-you-fy="group" data-val="project" aria-pressed="' +
      (group === "project" ? "true" : "false") +
      '">By project</button>' +
      '<button type="button" class="you-fy-chip' +
      (group === "category" ? " is-on" : "") +
      '" data-you-fy="group" data-val="category" aria-pressed="' +
      (group === "category" ? "true" : "false") +
      '">By urgency</button>' +
      "</div>";
    if (prods.length > 1) {
      html +=
        '<div class="you-fy-seg you-fy-show-seg" role="group" aria-label="Project filter">' +
        '<span class="you-fy-seg-cap" aria-hidden="true">show</span>' +
        '<select class="you-fy-proj-sel" id="map-you-fy-proj" aria-label="Project">' +
        '<option value="all"' +
        (projPref === "all" ? " selected" : "") +
        ">All projects</option>";
      prods.forEach(function (p) {
        html +=
          '<option value="' +
          escHtml(p) +
          '"' +
          (projPref === p ? " selected" : "") +
          ">" +
          escHtml(forYouProductLabel(p)) +
          " · " +
          (byProd[p] || 0) +
          "</option>";
      });
      html += "</select></div>";
    }
    html += "</div>";
    html += "</div>";
    return html;
  }

  function youFyBulkBarHtml(reportIds) {
    const n = (reportIds || []).length;
    if (!n) return "";
    return (
      '<div class="you-fy-bulk" id="map-you-fy-bulk" data-report-ids="' +
      escHtml(reportIds.join(",")) +
      '">' +
      '<span class="you-fy-bulk-label" title="Bulk acts on Read papers only — never touches Decide gold or gates">Read in view · ' +
      n +
      "</span>" +
      '<button type="button" class="you-fy-bulk-btn" data-bulk="snooze1d" title="Mute gold notification only — does not clear gates">Mute 1d</button>' +
      '<button type="button" class="you-fy-bulk-btn" data-bulk="clear" title="Marks these Read papers read — never touches Decide gold">Mark read</button>' +
      '<p class="you-fy-bulk-status" id="map-you-fy-bulk-status" aria-live="polite"></p>' +
      "</div>"
    );
  }

  /**
   * pc-484: active product-scope snoozes from Desk attention prefs.
   * Snooze mutes For You / gold fill only — never clears ticket gates.
   */
  function attentionSnoozes() {
    const raw = (lastAtt() && lastAtt().snoozes) || [];
    return Array.isArray(raw) ? raw : [];
  }

  function productSnoozeActive(product) {
    const p = String(product || "")
      .toLowerCase()
      .trim();
    if (!p) return null;
    const hits = attentionSnoozes().filter(function (s) {
      if (!s) return false;
      const scope = String(s.scope || "product").toLowerCase();
      if (scope === "all") return true;
      if (scope !== "product") return false;
      return String(s.product || "")
        .toLowerCase()
        .trim() === p;
    });
    return hits.length ? hits[0] : null;
  }

  function citywideSnoozeActive() {
    return (
      attentionSnoozes().find(function (s) {
        return s && String(s.scope || "").toLowerCase() === "all";
      }) || null
    );
  }

  function formatSnoozeUntil(until) {
    if (!until) return "";
    try {
      const d = new Date(until);
      if (isNaN(d.getTime())) return String(until).slice(0, 16);
      return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (e) {
      return String(until).slice(0, 16);
    }
  }

  /**
   * pc-1146: timer/embargo citizen line — "Opens Aug 17" (not missing from gold).
   * gate_until may be ISO string; also accept attention note "gated until …".
   */
  function forYouOpensLabel(it) {
    if (!it) return "";
    let raw = it.gate_until || it.until || null;
    if (!raw && it.note) {
      const m = String(it.note).match(
        /gated until\s+(\d{4}-\d{2}-\d{2}[T\s]?\d{0,2}:?\d{0,2}:?\d{0,2}Z?)/i
      );
      if (m) raw = m[1];
    }
    if (!raw) return "";
    try {
      let s = String(raw).trim();
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) s = s + "T12:00:00Z";
      if (s.indexOf("T") < 0 && s.indexOf(" ") > 0) s = s.replace(" ", "T");
      if (/Z$/i.test(s) === false && /[+-]\d{2}:\d{2}$/.test(s) === false && s.indexOf("T") >= 0)
        s = s + "Z";
      const d = new Date(s);
      if (isNaN(d.getTime())) return "Opens " + String(raw).slice(0, 16);
      const now = Date.now();
      const when = d.getTime();
      const dayLab = d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
      if (when <= now) return "Due " + dayLab;
      return "Opens " + dayLab;
    } catch (e) {
      return "";
    }
  }

  /** Watch-face row model (stalled / embargo) — not gold; dig + You tray band. */
  function forYouWatchRowModel(it) {
    const tid = String((it && it.id) || "").trim();
    const k = String((it && it.kind) || "")
      .toLowerCase()
      .replace(/ /g, "_");
    const isEmbargo = k === "embargo";
    const prodRaw = String(
      (it && (it.product || it.project || it.store)) || ""
    ).trim();
    const prod = forYouProductLabel(prodRaw);
    const focus = forYouFocusTitle(it || {});
    const opens = forYouOpensLabel(it || {});
    const stamp = isEmbargo ? "timer" : "stalled";
    const verb = isEmbargo
      ? opens || "Timed · not gold yet"
      : "Watch · no recent update";
    /* pc-1201: same anatomy as gold rows — title = focus; meta = id · … */
    return {
      ask: forYouAskLine(it, focus),
      tid: tid,
      prod: prodRaw,
      prodLabel: prod,
      catKey: "watch",
      catLabel: "Watch",
      face: "watch",
      glyph: isEmbargo ? "⏱" : "👁",
      catOrder: 3,
      verb: verb,
      sectionSub:
        "timers · stalled — not counted in For You gold · calendar when timed",
      focus: focus,
      headline: focus,
      focusLine: focus,
      meta: [tid, verb, stamp, opens, prod].filter(Boolean).join(" · "),
      age: forYouAgeLabel(it || {}),
      opens: opens,
      stamp: stamp,
    };
  }

  function youSnoozeBarHtml(opts) {
    opts = opts || {};
    const compact = !!opts.compact;
    const product = String(opts.product || "").trim();
    const products = Array.isArray(opts.products)
      ? opts.products.filter(Boolean)
      : product
        ? [product]
        : [];
    const uniq = [];
    const seen = {};
    products.forEach(function (pr) {
      const k = String(pr).toLowerCase().trim();
      if (!k || seen[k]) return;
      seen[k] = true;
      uniq.push(String(pr).trim());
    });
    const id = String(opts.id || "map-you-snooze");
    const active =
      (uniq.length === 1 && productSnoozeActive(uniq[0])) ||
      (uniq.length === 0 && citywideSnoozeActive());
    const snoozedN =
      (lastAtt() && typeof lastAtt().snoozed_count === "number"
        ? lastAtt().snoozed_count
        : 0) | 0;
    let status = "";
    if (active) {
      status =
        "Muted until " +
        (formatSnoozeUntil(active.until) || "later") +
        " · gates stay set";
    } else if (snoozedN > 0 && !uniq.length) {
      status = snoozedN + " muted elsewhere · not cleared";
    }
    const scopeLabel =
      uniq.length === 1
        ? uniq[0]
        : uniq.length > 1
          ? uniq.length + " products in tray"
          : "all products";
    const dataProducts = uniq.join(",");
    let actionsHtml = '<div class="you-snooze-actions">';
    if (active && uniq.length <= 1) {
      actionsHtml +=
        '<button type="button" class="you-snooze-btn is-unsnooze" data-snooze-act="unsnooze">Unsnooze</button>';
    } else {
      ["today", "1d", "1w"].forEach(function (u) {
        const lab = u === "today" ? "Today" : u === "1d" ? "1 day" : "1 week";
        actionsHtml +=
          '<button type="button" class="you-snooze-btn" data-snooze-act="snooze" data-until="' +
          u +
          '">' +
          lab +
          "</button>";
      });
      if (uniq.length === 0) {
        actionsHtml +=
          '<button type="button" class="you-snooze-btn" data-snooze-act="snooze" data-until="1d" data-scope="all" title="Mute every product">All · 1 day</button>';
      }
    }
    actionsHtml += "</div>";
    const statusHtml =
      '<p class="you-snooze-status" id="' +
      escHtml(id) +
      '-status">' +
      escHtml(status) +
      "</p>";
    if (compact) {
      const untilTip = active
        ? "Gold muted until " +
          (formatSnoozeUntil(active.until) || "later") +
          " · server · gates unchanged · not a calendar reminder"
        : "Mute For You gold · " +
          scopeLabel +
          " · notification only (not timer, not clear gate)";
      return (
        '<div class="you-snooze is-compact' +
        (active ? " is-active" : "") +
        '" id="' +
        escHtml(id) +
        '" data-products="' +
        escHtml(dataProducts) +
        '" data-compact="1">' +
        '<button type="button" class="you-snooze-toggle" aria-expanded="false" aria-haspopup="true" title="' +
        escHtml(untilTip) +
        '" aria-label="' +
        escHtml(untilTip) +
        '"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M8 3.2a4.8 4.8 0 1 0 0 9.6 4.8 4.8 0 0 0 0-9.6zm0 1.4a3.4 3.4 0 1 1 0 6.8 3.4 3.4 0 0 1 0-6.8zM7.3 5.5h1.4v2.6l1.9 1.1-.7 1.2-2.6-1.5V5.5zM3.2 2.1l1.5 1.2-.8 1L2.4 3.1l.8-1zm9.6 0 .8 1-1.5 1.2-.8-1 1.5-1.2z"/></svg></button>' +
        '<div class="you-snooze-popover" hidden>' +
        '<div class="you-snooze-label">Mute gold · ' +
        escHtml(scopeLabel) +
        "</div>" +
        '<p class="you-snooze-note">Mutes notification only · does not set a calendar date · map pin hide is Notices.</p>' +
        actionsHtml +
        statusHtml +
        "</div></div>"
      );
    }
    return (
      '<div class="you-snooze" id="' +
      escHtml(id) +
      '" data-products="' +
      escHtml(dataProducts) +
      '">' +
      '<div class="you-snooze-label">Mute For You gold · ' +
      escHtml(scopeLabel) +
      "</div>" +
      '<p class="you-snooze-note">Mutes gold notifications for a while (server). ' +
      "Does not clear human gates, cancel work orders, set a timer/calendar date, hide map pins, or dismiss work forever. " +
      "Timed reminders use gate_type=timer (Watch · Opens date). Map pin mute is Notices · Hide notice.</p>" +
      actionsHtml +
      statusHtml +
      "</div>"
    );
  }

  function postAttentionSnooze(body) {
    return fetch("/api/attention/snooze", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body || {}),
      cache: "no-store",
    }).then(function (r) {
      return r.json().then(function (j) {
        return { ok: r.ok && !!(j && j.ok !== false), status: r.status, data: j };
      });
    });
  }

  function postAttentionUnsnooze(body) {
    return fetch("/api/attention/unsnooze", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body || {}),
      cache: "no-store",
    }).then(function (r) {
      return r.json().then(function (j) {
        return { ok: r.ok && !!(j && j.ok !== false), status: r.status, data: j };
      });
    });
  }

  function refreshAttentionAfterSnooze(done) {
    fetchJsonTimeout("/api/attention", 5000)
      .then(function (d) {
        if (d && typeof d === "object") {
          /* Authoritative desk payload — accept empty items after mute */
          setLastAtt(d);
          /* pc-558: for-you-only rollup (stalled never inflates gold) */
          const by = forYouCountsByProduct(d.items || []);
          /* Snooze is intentional — force-commit, skip sticky lag (pc-550) */
          setAttentionByProduct(Object.assign({}, by));
          setPrevAttentionByProduct(Object.assign({}, by));
          setAttStickyPending(Object.create(null));
        }
        try {
          const city = lastCityData() || (getModel() && getModel().city);
          const people =
            lastPeople() || { sectors: [], in_flight: [] };
          if (city && typeof buildScene === "function") {
            buildScene(city, people);
          }
          if (typeof paintMapInsights === "function" && city) {
            paintMapInsights(
              city,
              people,
              lastAtt(),
              lastTpScene()
            );
          }
        } catch (ePaint) {}
        if (typeof done === "function") done(d);
      })
      .catch(function () {
        if (typeof done === "function") done(null);
      });
  }

  function bindYouSnoozeBar(root) {
    const bar =
      (root && root.querySelector && root.querySelector(".you-snooze")) ||
      document.querySelector("#inspect-form .you-snooze");
    if (!bar || bar._snoozeBound) return;
    bar._snoozeBound = true;
    const isCompact = bar.classList.contains("is-compact");
    if (isCompact) {
      const toggle = bar.querySelector(".you-snooze-toggle");
      const pop = bar.querySelector(".you-snooze-popover");
      if (toggle && pop) {
        toggle.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          const open = !bar.classList.contains("is-open");
          bar.classList.toggle("is-open", open);
          pop.hidden = !open;
          toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });
        if (!bar._snoozeDocClose) {
          bar._snoozeDocClose = function (ev) {
            if (!bar.classList.contains("is-open")) return;
            if (bar.contains(ev.target)) return;
            bar.classList.remove("is-open");
            pop.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
          };
          document.addEventListener("click", bar._snoozeDocClose);
        }
      }
    }
    bar.addEventListener("click", function (e) {
      const btn = e.target && e.target.closest && e.target.closest("button[data-snooze-act]");
      if (!btn || !bar.contains(btn)) return;
      e.preventDefault();
      e.stopPropagation();
      const act = btn.getAttribute("data-snooze-act") || "";
      const until = btn.getAttribute("data-until") || "1d";
      const scopeAttr = btn.getAttribute("data-scope") || "";
      const products = String(bar.getAttribute("data-products") || "")
        .split(",")
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
      const statusEl =
        bar.querySelector(".you-snooze-status") ||
        document.getElementById(bar.id + "-status");
      const setStatus = function (msg, isErr) {
        if (!statusEl) return;
        statusEl.textContent = msg || "";
        statusEl.classList.toggle("is-err", !!isErr);
      };
      const disable = function (on) {
        bar.querySelectorAll("button.you-snooze-btn").forEach(function (b) {
          b.disabled = !!on;
        });
      };
      disable(true);
      setStatus(act === "unsnooze" ? "Restoring…" : "Snoozing…", false);

      const finish = function (res, label) {
        if (!res || !res.ok) {
          const err =
            (res && res.data && (res.data.error || res.data.msg)) ||
            "Snooze failed";
          setStatus(String(err), true);
          disable(false);
          return;
        }
        if (res.data && Array.isArray(res.data.snoozes)) {
          setLastAtt(Object.assign({}, lastAtt() || {}, {
            snoozes: res.data.snoozes,
            snoozed_count: res.data.snoozed_count,
            visible_count: res.data.visible_count,
            count:
              res.data.visible_count != null
                ? res.data.visible_count
                : res.data.count,
          }));
        }
        refreshAttentionAfterSnooze(function () {
          setStatus(label || "Updated", false);
          /* Re-paint open inspect panels that host the bar */
          try {
            const form = document.getElementById("inspect-form");
            if (form && form.querySelector("#map-you-for-you-h")) {
              fillYouForYouPanel(
                forYouAttItems((lastAtt() && lastAtt().items) || [])
              );
            } else if (form && form.querySelector(".you-snooze")) {
              /* Project overview: rebuild compact snooze control (pc-703) */
              const old = form.querySelector(".you-snooze");
              const prod =
                (products[0] ||
                  (old &&
                    old.getAttribute &&
                    old.getAttribute("data-products")) ||
                  "") + "";
              const html = youSnoozeBarHtml({
                id: "map-project-snooze",
                product: String(prod).split(",")[0] || "",
                compact: !!(old && old.classList.contains("is-compact")),
              });
              const tmp = document.createElement("div");
              tmp.innerHTML = html;
              const neu = tmp.querySelector(".you-snooze");
              if (old && neu) {
                old.replaceWith(neu);
                bindYouSnoozeBar(form);
              }
            }
          } catch (eFill) {}
        });
      };

      if (act === "unsnooze") {
        const body =
          products.length === 1
            ? { scope: "product", product: products[0] }
            : citywideSnoozeActive()
              ? { scope: "all" }
              : products[0]
                ? { scope: "product", product: products[0] }
                : { scope: "all" };
        postAttentionUnsnooze(body)
          .then(function (res) {
            finish(res, "Unsnoozed — gold returns if gates remain");
          })
          .catch(function () {
            setStatus("Network error", true);
            disable(false);
          });
        return;
      }

      /* Snooze: one product, multi-product sequential, or all */
      if (scopeAttr === "all" || products.length === 0) {
        postAttentionSnooze({
          scope: "all",
          until: until,
          reason: "Map For You snooze",
        })
          .then(function (res) {
            finish(res, "Snoozed all products · gates unchanged");
          })
          .catch(function () {
            setStatus("Network error", true);
            disable(false);
          });
        return;
      }

      let chain = Promise.resolve({ ok: true, data: {} });
      products.forEach(function (pr) {
        chain = chain.then(function () {
          return postAttentionSnooze({
            scope: "product",
            product: pr,
            until: until,
            reason: "Map For You snooze · " + pr,
          });
        });
      });
      chain
        .then(function (res) {
          finish(
            res,
            "Snoozed " +
              (products.length === 1 ? products[0] : products.length + " products") +
              " · gates unchanged"
          );
        })
        .catch(function () {
          setStatus("Network error", true);
          disable(false);
        });
    });
  }

  /**
   * Ensure attention tray items are loaded (first click often races poll).
   * Updates _lastAtt + attentionByProduct when fetched.
   */
  function ensureAttentionItems(done) {
    const cur = (lastAtt() && lastAtt().items) || [];
    if (cur.length) {
      done(cur);
      return;
    }
    const nRollup = Object.keys(attentionByProduct() || {}).reduce(function (
      s,
      k
    ) {
      return s + (attentionByProduct()[k] || 0);
    },
    0);
    fetchJsonTimeout("/api/attention", 5000)
      .then(function (d) {
        if (d && Array.isArray(d.items)) {
          setLastAtt(d);
          /* pc-558: for-you-only rollup */
          const by = forYouCountsByProduct(d.items);
          setAttentionByProduct(Object.assign({}, by));
          done(d.items);
          return;
        }
        done(cur);
      })
      .catch(function () {
        done(cur);
      });
    /* If rollup already knows count, keep waiting on fetch; else done([]) soon */
    if (!nRollup && !cur.length) {
      /* still waiting on fetch above */
    }
  }

  function youForYouListHtml(forYou) {
    const all = forYou || [];
    const goldN = all.length;
    const cls = youFyClassPref();
    const group = youFyGroupPref();
    const proj = youFyEffectiveProject(all);
    const filtered = filterForYouListItems(all, cls, proj);
    const ordered =
      group === "project"
        ? sortForYouByProjectThenUrgency(filtered)
        : sortForYouByGroupThenUrgency(filtered);
    const listItems = ordered.map(function (it) {
      const row = forYouRowModel(it);
      return {
        tid: row.tid,
        headline: row.headline,
        focus: row.focusLine,
        ask: row.ask,
        meta: row.meta,
        glyph: row.glyph,
        catKey: row.catKey,
        catLabel: row.catLabel,
        face: row.face,
        verb: row.verb,
        sectionSub: row.sectionSub,
        prod: row.prod,
        prodLabel: row.prodLabel,
        dateBadge: row.dateBadge,
      };
    });
    /* pc-1146 / pc-1201: Watch band — All stacks under gold; Watch pulse = only Watch */
    let watchRaw = stalledAttItems(proj === "all" ? null : proj);
    if (cls === "reports" || cls === "needs_you") {
      watchRaw = [];
    }
    const watchItems = watchRaw.map(forYouWatchRowModel);
    const reportIds = youForYouReportIds(filtered);
    const prods = [];
    all.forEach(function (it) {
      const p = String((it && (it.product || it.project || it.store)) || "").trim();
      if (p) prods.push(p);
    });
    /* Also surface products already product-snoozed so Unsnooze stays reachable */
    attentionSnoozes().forEach(function (s) {
      if (s && String(s.scope || "").toLowerCase() === "product" && s.product) {
        prods.push(String(s.product));
      }
    });
    const headN =
      listItems.length === goldN
        ? String(goldN)
        : listItems.length + " of " + goldN;
    let html =
      '<div class="you-for-you-h" id="map-you-for-you-h">' +
      '<span class="you-for-you-h-title">For You · ' +
      headN +
      " gold</span>" +
      '<span class="you-for-you-h-links">' +
      '<a class="you-fy-cal-link" href="/calendar" target="_blank" rel="noopener" title="Timers and deadlines (pc-1125)">Calendar</a>' +
      '<a class="you-fy-cal-link" href="/calendar.ics" target="_blank" rel="noopener" title="Subscribe in Apple/Google Calendar">ICS</a>' +
      "</span>" +
      /* pc-703/pc-715 bell, pc-1213: now a flex child of the header row —
       * the old float + negative-margin overlay ate link clicks (302px box). */
      youSnoozeBarHtml({
        id: "map-you-snooze",
        products: prods,
        compact: true,
      }) +
      "</div>";
    /* pc-888: class filter + group + project · report bulk (reports only) */
    html += youFyToolbarHtml(all, listItems.length, watchItems.length);
    /* Bulk Mark read only on Read pulse (never Decide) */
    if (cls === "reports" || cls === "all") {
      html += youFyBulkBarHtml(reportIds);
    }
    if (!goldN && !watchItems.length) {
      const snoozedN =
        (lastAtt() && typeof lastAtt().snoozed_count === "number"
          ? lastAtt().snoozed_count
          : 0) | 0;
      html +=
        '<p class="you-form-note" id="map-you-for-you-empty">' +
        (snoozedN > 0
          ? "Nothing visible — " +
            snoozedN +
            " muted by snooze (gates unchanged). Unsnooze above to restore gold."
          : "Loading For You…") +
        "</p>";
    } else if (!listItems.length && !watchItems.length) {
      html +=
        '<p class="you-form-note" id="map-you-for-you-empty">' +
        "No items match this filter. Try All or another project — gold count above is unchanged." +
        "</p>";
    } else {
      let lastSection = "";
      const chunks = [];
      /* pc-1201: single-face pulse → omit nested DECIDE/READ kicker (pulse owns it) */
      const oneFace =
        cls === "needs_you" || cls === "reports" || cls === "watch";
      listItems.forEach(function (it, i) {
        const sectionKey =
          group === "project" ? "p:" + it.prodLabel : "c:" + it.catKey;
        if (!oneFace && sectionKey !== lastSection) {
          lastSection = sectionKey;
          const nIn =
            group === "project"
              ? listItems.filter(function (x) {
                  return x.prodLabel === it.prodLabel;
                }).length
              : listItems.filter(function (x) {
                  return x.catKey === it.catKey;
                }).length;
          const sectionLabel =
            group === "project" ? it.prodLabel : it.catLabel;
          const sectionHint =
            group === "project"
              ? "id · verb · age — open to act"
              : it.sectionSub ||
                (it.face === "read"
                  ? "mark read · mute gold — not implement work"
                  : "open work order · clear gate when decided");
          chunks.push(
            '<div class="inspect-list-item is-section is-inert you-fy-group you-fy-face-' +
              escHtml(it.face || "decide") +
              '" role="presentation" data-face="' +
              escHtml(it.face || "decide") +
              '">' +
              '<span class="card-body"><span class="card-title">' +
              escHtml(sectionLabel) +
              " · " +
              nIn +
              "</span>" +
              '<span class="sub you-fy-section-sub">' +
              escHtml(sectionHint) +
              "</span></span></div>"
          );
        }
        /* pc-1201: title = focus; meta = id · verb · age · product */
        const titleLine = it.focus || it.headline || it.tid || "For You";
        const isRead = it.face === "read" || it.catKey === "reports";
        chunks.push(
          '<button type="button" class="inspect-list-item you-fy-row you-fy-face-' +
            escHtml(it.face || "decide") +
            (isRead ? " is-read-paper" : " is-decide-paper") +
            '" data-i="' +
            i +
            '" data-tid="' +
            escHtml(it.tid) +
            '" data-cat="' +
            escHtml(it.catKey) +
            '" data-face="' +
            escHtml(it.face || "decide") +
            '" data-prod="' +
            escHtml(it.prod || "") +
            '" role="listitem">' +
            '<span class="card-ic is-paper" aria-hidden="true"><span class="glyph">' +
            escHtml(it.glyph || "⭐") +
            "</span></span>" +
            '<span class="card-body"><span class="card-title">' +
            escHtml(titleLine) +
            "</span>" +
            (it.dateBadge
              ? '<span class="you-fy-date" title="Scheduled — same date the calendar shows">' +
                escHtml(it.dateBadge) +
                "</span>"
              : "") +
            (it.ask
              ? '<span class="sub you-fy-ask">' + escHtml(it.ask) + "</span>"
              : "") +
            (it.meta
              ? '<span class="sub you-fy-meta">' + escHtml(it.meta) + "</span>"
              : "") +
            "</span></button>"
        );
      });
      /* Watch band: under All golds, or sole body when Watch pulse */
      if (watchItems.length) {
        if (cls === "all") {
          chunks.push(
            '<div class="inspect-list-item is-section is-inert you-fy-group you-fy-face-watch" role="presentation" data-face="watch">' +
              '<span class="card-body"><span class="card-title">Watch · ' +
              watchItems.length +
              "</span>" +
              '<span class="sub you-fy-section-sub">timers · stalled — not counted in gold · calendar for dates</span>' +
              "</span></div>"
          );
        }
        watchItems.forEach(function (it, wi) {
          chunks.push(
            '<button type="button" class="inspect-list-item you-fy-row you-fy-face-watch is-watch-paper" data-watch-i="' +
              wi +
              '" data-tid="' +
              escHtml(it.tid) +
              '" data-cat="watch" data-face="watch" data-prod="' +
              escHtml(it.prod || "") +
              '" role="listitem">' +
              '<span class="card-ic is-paper" aria-hidden="true"><span class="glyph">' +
              escHtml(it.glyph || "⏱") +
              "</span></span>" +
              '<span class="card-body"><span class="card-title">' +
              escHtml(it.headline || it.focus || it.tid) +
              "</span>" +
              (it.ask
                ? '<span class="sub you-fy-ask">' + escHtml(it.ask) + "</span>"
                : "") +
              (it.meta
                ? '<span class="sub you-fy-meta">' + escHtml(it.meta) + "</span>"
                : "") +
              "</span></button>"
          );
        });
      }
      html +=
        '<div class="inspect-list" role="list" id="map-you-for-you-list">' +
        chunks.join("") +
        "</div>";
    }
    return html;
  }

  function bindYouForYouClicks(root) {
    const listEl =
      (root && root.querySelector && root.querySelector("#map-you-for-you-list")) ||
      document.getElementById("map-you-for-you-list");
    if (!listEl) return;
    listEl.querySelectorAll(".inspect-list-item.you-fy-row").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const tid = btn.getAttribute("data-tid") || "";
        if (!tid) return;
        try {
          if (
            window.SuitePaper &&
            typeof SuitePaper.openTicket === "function"
          ) {
            SuitePaper.openTicket(tid);
            return;
          }
        } catch (err) {}
        goHref("/ticket?id=" + encodeURIComponent(tid));
      });
    });
  }

  /**
   * pc-1213: header Calendar/ICS anchors — default anchor navigation dies in
   * this panel while every JS-bound control works, so navigate explicitly.
   * Same-tab: /calendar is a suite page (Back returns to Map); .ics hands the
   * feed to the browser without leaving the page.
   */
  function bindYouFyCalLinks(root) {
    const host =
      (root && root.querySelector && root.querySelector("#map-you-for-you-h")) ||
      document.getElementById("map-you-for-you-h");
    if (!host) return;
    host.querySelectorAll("a.you-fy-cal-link").forEach(function (a) {
      if (a._calBound) return;
      a._calBound = true;
      a.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const href = a.getAttribute("href") || "/calendar";
        try {
          window.location.assign(href);
        } catch (eNav) {
          window.location.href = href;
        }
      });
    });
  }

  /** pc-888: re-paint You tray when filter chips change (gold membership untouched). */
  function repaintYouForYouFromPrefs() {
    const items = forYouAttItems((lastAtt() && lastAtt().items) || []);
    fillYouForYouPanel(items);
  }

  function bindYouFyToolbar(root) {
    const bar =
      (root && root.querySelector && root.querySelector("#map-you-fy-toolbar")) ||
      document.getElementById("map-you-fy-toolbar");
    if (!bar || bar._youFyBound) return;
    bar._youFyBound = true;
    bar.addEventListener("click", function (e) {
      const t = e.target;
      if (!t || !t.closest) return;
      /* pc-1210: pulse cells dropped the chip class — bind on data attr */
      const btn = t.closest("button[data-you-fy]");
      if (!btn || !bar.contains(btn)) return;
      e.preventDefault();
      e.stopPropagation();
      const kind = btn.getAttribute("data-you-fy") || "";
      const val = btn.getAttribute("data-val") || "";
      if (kind === "class") setYouFyClassPref(val);
      else if (kind === "group") setYouFyGroupPref(val);
      else return;
      repaintYouForYouFromPrefs();
    });
    const sel =
      (root && root.querySelector && root.querySelector("#map-you-fy-proj")) ||
      document.getElementById("map-you-fy-proj");
    if (sel && !sel._youFyBound) {
      sel._youFyBound = true;
      sel.addEventListener("change", function () {
        setYouFyProjectPref(sel.value || "all");
        repaintYouForYouFromPrefs();
      });
    }
  }

  function postTaskStatusDone(tid) {
    return fetch("/api/task/" + encodeURIComponent(tid), {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ status: "done", author: "you" }),
      cache: "no-store",
    }).then(function (r) {
      return r.json().then(function (j) {
        return { ok: r.ok && !!(j && j.ok !== false), status: r.status, data: j };
      });
    });
  }

  /**
   * pc-888: bulk snooze / clear-read — report-class ids only.
   * Never mass-clears Publish / For You / FOUNDER decision gold.
   */
  function bindYouFyBulk(root) {
    const bar =
      (root && root.querySelector && root.querySelector("#map-you-fy-bulk")) ||
      document.getElementById("map-you-fy-bulk");
    if (!bar || bar._youFyBound) return;
    bar._youFyBound = true;
    bar.addEventListener("click", function (e) {
      const t = e.target;
      if (!t || !t.closest) return;
      const btn = t.closest("button.you-fy-bulk-btn");
      if (!btn || !bar.contains(btn)) return;
      e.preventDefault();
      e.stopPropagation();
      const act = btn.getAttribute("data-bulk") || "";
      const rawIds = String(bar.getAttribute("data-report-ids") || "")
        .split(",")
        .map(function (x) {
          return String(x || "").trim();
        })
        .filter(Boolean);
      /* Safety: re-filter against live attention + report classifier */
      const live = forYouAttItems((lastAtt() && lastAtt().items) || []);
      const byId = {};
      live.forEach(function (it) {
        const id = String((it && it.id) || "").trim();
        if (id) byId[id] = it;
      });
      const reportIds = rawIds.filter(function (id) {
        return byId[id] && isForYouReportItem(byId[id]);
      });
      if (!reportIds.length) return;
      const statusEl = bar.querySelector("#map-you-fy-bulk-status");
      const setStatus = function (msg, isErr) {
        if (!statusEl) return;
        statusEl.textContent = msg || "";
        statusEl.classList.toggle("is-err", !!isErr);
      };
      const disable = function (on) {
        bar.querySelectorAll("button.you-fy-bulk-btn").forEach(function (b) {
          b.disabled = !!on;
        });
      };

      if (act === "snooze1d") {
        disable(true);
        setStatus("Snoozing " + reportIds.length + " report(s)…", false);
        let chain = Promise.resolve({ ok: true, data: {} });
        reportIds.forEach(function (tid) {
          chain = chain.then(function () {
            return postAttentionSnooze({
              task_id: tid,
              until: "1d",
              reason: "Bulk report snooze (You tray)",
            });
          });
        });
        chain
          .then(function (res) {
            if (!res || !res.ok) {
              setStatus(
                (res && res.data && (res.data.error || res.data.msg)) ||
                  "Snooze failed",
                true
              );
              disable(false);
              return;
            }
            refreshAttentionAfterSnooze(function () {
              setStatus(
                "Muted " + reportIds.length + " report(s) · gates unchanged",
                false
              );
              repaintYouForYouFromPrefs();
            });
          })
          .catch(function () {
            setStatus("Network error", true);
            disable(false);
          });
        return;
      }

      if (act === "clear") {
        const ok = window.confirm(
          "Mark " +
            reportIds.length +
            " report card(s) as read (done)?\n\n" +
            "Only report-class inbox items. Publish / For You / FOUNDER decision gold is not touched."
        );
        if (!ok) return;
        disable(true);
        setStatus("Clearing " + reportIds.length + " report(s)…", false);
        let chain = Promise.resolve({ ok: true });
        let failed = 0;
        reportIds.forEach(function (tid) {
          chain = chain.then(function () {
            return postTaskStatusDone(tid).then(function (res) {
              if (!res || !res.ok) failed += 1;
              return res;
            });
          });
        });
        chain
          .then(function () {
            refreshAttentionAfterSnooze(function () {
              if (failed) {
                setStatus(
                  "Cleared with " + failed + " error(s) — check remaining cards",
                  true
                );
              } else {
                setStatus(
                  "Cleared " + reportIds.length + " report(s) as read",
                  false
                );
              }
              repaintYouForYouFromPrefs();
              disable(false);
            });
          })
          .catch(function () {
            setStatus("Network error", true);
            disable(false);
          });
      }
    });
  }

  function fillYouForYouPanel(forYou) {
    const form = document.getElementById("inspect-form");
    if (!form) return;
    const all = forYou || [];
    /* pc-558: NEED YOU KPI === list length (no sticky max inflation) */
    const n = all.length;
    const stats = document.getElementById("inspect-stats");
    if (stats) {
      /* pc-1210: KPI chip row retired on You dig (same as place digs, pc-1043) —
       * the face pulse owns every count with a reason line. */
      paintInspectKpis(stats, []);
    }
    /* Rebuild For You block + snooze + filters + bulk together */
    const html = youForYouListHtml(all);
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    const pairs = [
      ["#map-you-for-you-h", true],
      ["#map-you-snooze", true],
      ["#map-you-fy-toolbar", true],
      ["#map-you-fy-bulk", false],
      ["#map-you-for-you-list", false],
      ["#map-you-for-you-empty", false],
    ];
    pairs.forEach(function (pair) {
      const sel = pair[0];
      const keepIfMissing = pair[1];
      const neu = tmp.querySelector(sel);
      const old = form.querySelector(sel);
      /* pc-1213: skip identical swaps — a soft-poll replaceWith between the
       * user's mousedown and mouseup kills the click (header Calendar/ICS
       * links dying under board churn). Unchanged nodes stay in place. */
      if (neu && old) {
        if (old.outerHTML !== neu.outerHTML) old.replaceWith(neu);
      } else if (neu && !old) form.appendChild(neu);
      else if (!neu && old && !keepIfMissing) old.remove();
    });
    /* Empty-state message when gold is 0 or filter hides all */
    const empty = form.querySelector("#map-you-for-you-empty");
    const list = form.querySelector("#map-you-for-you-list");
    if (!n) {
      if (list) list.remove();
      const bulk = form.querySelector("#map-you-fy-bulk");
      if (bulk) bulk.remove();
      const emptyMsg =
        ((lastAtt() && lastAtt().snoozed_count) | 0) > 0
          ? "Nothing visible — " +
            ((lastAtt() && lastAtt().snoozed_count) | 0) +
            " muted by snooze (gates unchanged). Unsnooze above to restore gold."
          : "Nothing waiting on You right now. Human-gated work orders will land here and on the left rail.";
      if (empty) {
        empty.textContent = emptyMsg;
      } else {
        const p = document.createElement("p");
        p.className = "you-form-note";
        p.id = "map-you-for-you-empty";
        p.textContent = emptyMsg;
        form.appendChild(p);
      }
      bindYouSnoozeBar(form);
      bindYouFyToolbar(form);
      bindYouFyCalLinks(form);
      return;
    }
    bindYouForYouClicks(form);
    bindYouSnoozeBar(form);
    bindYouFyToolbar(form);
    bindYouFyBulk(form);
    bindYouFyCalLinks(form);
  }

  /**
   * YOU panel — For You work orders only (pc-882).
   * Seat name (suite.youLabel) edits live in Settings · Appearance.
   * Loads attention on open so the first click is not blank.
   */
  function inspectYou() {
    const id = youIdentityBits();
    const youEl = document.getElementById("map-you-card");
    const titleShow = id.isDefault ? "YOU" : id.label;
    const seedItems = forYouAttItems((lastAtt() && lastAtt().items) || []);

    /* Mirror left rail */
    try {
      if (global.WoTape) WoTape.setFilter("for_you");
      if (global.WoTape) WoTape.bustTape();
      if (global.WoTape) WoTape.bustChips();
    } catch (eFy) {}

    openInspect({
      el: youEl,
      kind: "YOU",
      title: titleShow,
      meta:
        "Work that waits on the human. Seat name is under Settings · Appearance. " +
        "Input stays chat / MCP / CLI — not this panel.",
      /* pc-1210: KPI chips retired on You dig — face pulse owns the counts */
      stats: [],
      formHtml: youForYouListHtml(seedItems),
      doors: [],
      afterOpen: function (host) {
        bindYouForYouClicks(host);
        bindYouSnoozeBar(host);
        bindYouFyToolbar(host);
        bindYouFyBulk(host);
        bindYouFyCalLinks(host);

        function applyAtt(items) {
          const forYou = forYouAttItems(items);
          fillYouForYouPanel(forYou);
          /* Refresh left rail with real attention */
          try {
            if (typeof paintMapInsights === "function" && getModel()) {
              paintMapInsights(
                getModel().city,
                {
                  in_flight: (getModel().workers || [])
                    .filter(function (w) {
                      return w && w.working;
                    })
                    .map(function (w) {
                      return w.name;
                    }),
                  sectors: [],
                },
                lastAtt() || { items: items || [] },
                lastTpScene()
              );
            }
          } catch (eP) {}
        }

        if (seedItems.length) {
          applyAtt((lastAtt() && lastAtt().items) || seedItems);
        } else {
          ensureAttentionItems(function (items) {
            /* Only patch if YOU panel still open */
            const kind = document.getElementById("inspect-kind");
            if (
              !kind ||
              String(kind.textContent || "").indexOf("YOU") < 0
            ) {
              return;
            }
            applyAtt(items);
          });
        }
      },
    });
  }

  var InspectYou = {
    init: init,
    show: inspectYou,
    fill: fillYouForYouPanel,
    bindSnooze: bindYouSnoozeBar,
    applyFaceQuery: applyYouFaceQuery,
    faceFromQuery: youFaceFromQuery,
    setClassPref: setYouFyClassPref,
    formatSnoozeUntil: formatSnoozeUntil,
    productSnoozeActive: productSnoozeActive,
    youSnoozeBarHtml: youSnoozeBarHtml,
    watchRowModel: forYouWatchRowModel,
  };

  function init(host) {
    if (!host || typeof host !== "object") return InspectYou;
    Object.keys(host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return InspectYou;
  }

  global.InspectYou = InspectYou;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = InspectYou;
  }
})(typeof window !== "undefined" ? window : globalThis);
