/*! map-soft.js — structure sigs + soft lot patches (pc-370 / pc-372)
 * Pure helpers for Workspace map continuous live. Host page owns svg/model.
 *
 * Usage:
 *   MapSoft.handsStructureSig(workers)
 *   MapSoft.softPatchLiveLots(svg, model, normKey)
 */
(function (global) {
  "use strict";

  function handsStructureSig(workers) {
    return (workers || [])
      .map(function (w) {
        return [
          w.name || "",
          w.homeKey || "",
          w.kind || "",
          (w.kind || "").toLowerCase() === "job" ? "j" : "a",
        ].join("|");
      })
      .sort()
      .join(";");
  }

  function handsWorkingSig(workers) {
    return (workers || [])
      .map(function (w) {
        return (w.name || "") + ":" + (w.working ? "1" : "0");
      })
      .sort()
      .join(";");
  }

  /**
   * Plot *identity* only (sorted). Do NOT include managed/zone/open counts —
   * those flicker between API paints and forced full SVG wipes (dual-color
   * circle flash). Membership change = slug set change only.
   */
  function plotsStructureSig(plots) {
    return (plots || [])
      .map(function (p) {
        return String(p.slug || p.name || "")
          .toLowerCase()
          .trim();
      })
      .filter(Boolean)
      .sort()
      .join(";");
  }

  function plotsMembershipSig(plots) {
    return plotsStructureSig(plots);
  }

  /**
   * Folder work heat = live open (pc-546 / pc-552 / pc-875 / pc-1084).
   * Delegates to WoBuckets — single source for storeLiveOpen + heat sample.
   */
  function openCount(p, model) {
    if (global.WoBuckets && typeof global.WoBuckets.openCountFromPlot === "function") {
      return global.WoBuckets.openCountFromPlot(p, model);
    }
    /* Failsafe if wo-buckets.js failed to load */
    const st = (p && p.store) || {};
    if (Object.prototype.hasOwnProperty.call(st, "ready")) {
      return (st.ready | 0) + (st.in_progress | 0) + (st.in_review | 0);
    }
    return (st.backlog | 0) + (st.in_progress | 0) + (st.in_review | 0);
  }

  function deferredCount(p, model) {
    if (
      global.WoBuckets &&
      typeof global.WoBuckets.deferredCountFromPlot === "function"
    ) {
      return global.WoBuckets.deferredCountFromPlot(p, model);
    }
    return 0;
  }

  /**
   * Soft-patch open badges on bullseye .lot houses only.
   * Hierarchy map (default): host softPatchHierarchyBubbles redraws
   * manila folder badges + stem anchors (pc-439). Returns
   * [{slug, name, prev, open, el}] for lots whose count changed.
   */
  function softPatchLotOpenCounts(svg, model) {
    const changed = [];
    if (!svg || !model || !model.plots) return changed;
    /* Hierarchy owns its own open badges — do not no-op the host soft path */
    if (model._hierarchy) return changed;
    const lotsRoot = svg.querySelector("#lots");
    if (!lotsRoot) return changed;
    const byKey = Object.create(null);
    const iceByKey = Object.create(null);
    model.plots.forEach(function (p) {
      const open = openCount(p, model);
      const ice = deferredCount(p, model);
      const slug = String(p.slug || "").toLowerCase();
      const name = String(p.name || "").toLowerCase();
      if (slug) {
        byKey[slug] = open;
        iceByKey[slug] = ice;
      }
      if (name) {
        byKey[name] = open;
        iceByKey[name] = ice;
      }
    });
    Array.prototype.forEach.call(
      lotsRoot.querySelectorAll(".lot"),
      function (g) {
        const slug = String(g.getAttribute("data-slug") || "").toLowerCase();
        const name = String(g.getAttribute("data-name") || "").toLowerCase();
        const open =
          byKey[slug] != null
            ? byKey[slug]
            : byKey[name] != null
              ? byKey[name]
              : null;
        if (open == null) return;
        const ice =
          iceByKey[slug] != null
            ? iceByKey[slug]
            : iceByKey[name] != null
              ? iceByKey[name]
              : 0;
        const prevRaw = g.getAttribute("data-open");
        const prevIce = g.getAttribute("data-deferred");
        if (prevRaw === String(open) && prevIce === String(ice)) return;
        const prev = prevRaw != null ? parseInt(prevRaw, 10) : open;
        g.setAttribute("data-open", String(open));
        g.setAttribute("data-deferred", String(ice));
        try {
          g.setAttribute(
            "title",
            ice > 0
              ? open + " live · " + ice + " deferred"
              : open > 0
                ? open + " live open"
                : "No live open work"
          );
        } catch (eTip) {}
        const t = g.querySelector(".folder-open-count");
        if (t) {
          t.textContent = open > 0 ? String(open) : "0";
          /* Micro-pop on count change */
          t.setAttribute("data-bump", open > prev ? "up" : "down");
          try {
            t.classList.remove("count-bump");
            void t.getBoundingClientRect();
            t.classList.add("count-bump");
          } catch (eBump) {}
        }
        changed.push({
          slug: slug,
          name: name,
          prev: isFinite(prev) ? prev : open,
          open: open,
          el: g,
        });
      }
    );
    return changed;
  }

  function softPatchLiveLots(svg, model, normKeyFn) {
    if (!svg || !model || !model.plots) return;
    const lotsRoot = svg.querySelector("#lots");
    if (!lotsRoot) return;
    const nk =
      typeof normKeyFn === "function"
        ? normKeyFn
        : function (s) {
            return String(s || "")
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, "");
          };
    const liveKeys = Object.create(null);
    (model.workers || []).forEach(function (w) {
      if (!w || !w.working) return;
      const hk = String(w.homeKey || "").toLowerCase();
      if (!hk || hk.indexOf("__") === 0) return;
      liveKeys[hk] = true;
      liveKeys[nk(hk)] = true;
    });
    Array.prototype.forEach.call(
      lotsRoot.querySelectorAll(".lot"),
      function (g) {
        const slug = String(g.getAttribute("data-slug") || "").toLowerCase();
        const name = String(g.getAttribute("data-name") || "").toLowerCase();
        const live = !!(
          liveKeys[slug] ||
          liveKeys[name] ||
          liveKeys[nk(slug)] ||
          liveKeys[nk(name)]
        );
        const was = g.classList.contains("is-live");
        if (live === was) return;
        g.classList.toggle("is-live", live);
      }
    );
  }

  global.MapSoft = {
    handsStructureSig: handsStructureSig,
    handsWorkingSig: handsWorkingSig,
    plotsStructureSig: plotsStructureSig,
    plotsMembershipSig: plotsMembershipSig,
    openCount: openCount,
    deferredCount: deferredCount,
    softPatchLotOpenCounts: softPatchLotOpenCounts,
    softPatchLiveLots: softPatchLiveLots,
  };
})(typeof window !== "undefined" ? window : this);
