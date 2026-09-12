/**
 * map-fast.js — guaranteed usable Map (pc-895…pc-898, pc-973)
 *
 * workspace_map_app.js is ~1.1MB. This layer is the failsafe usable Map.
 * pc-898/973: paint ring UNDER the skeleton only — do not reveal early.
 * Skeleton holds until full hierarchy handoff (finishFirstPaint). A visible
 * ring→radial re-layout is a fail (pc-973). REVEAL_MS is last-resort only
 * when the engine is late so Map is never permanently blank.
 */
(function () {
  "use strict";
  if (window.__mapFastBooted) return;
  window.__mapFastBooted = true;

  /*
   * pc-973: hold skeleton through normal boot. Engine load is no longer gated
   * 800ms; hierarchy should hand off before this failsafe. Late reveal only.
   */
  var REVEAL_MS = 4000;
  var label = document.getElementById("map-first-paint-label");
  var paint = document.getElementById("map-first-paint");
  var shell = document.getElementById("map-shell");
  var stage = document.getElementById("stage");
  var world = document.getElementById("world");
  var bootAt = Date.now();
  var revealTimer = null;

  function setMsg(m) {
    if (label) label.textContent = m;
  }

  function hideSkeleton() {
    if (paint) {
      paint.hidden = true;
      paint.setAttribute("hidden", "");
      paint.classList.add("is-done");
      try {
        paint.style.cssText =
          "display:none!important;visibility:hidden!important;pointer-events:none!important;opacity:0!important";
      } catch (e) {}
    }
    if (shell) {
      shell.classList.remove("is-first-paint");
      shell.setAttribute("aria-busy", "false");
    }
    window.__mapFastPainted = true;
    try {
      document.documentElement.setAttribute("data-map-fast", "1");
    } catch (e2) {}
  }

  /**
   * Paint under the skeleton; only reveal when full map is late or already gone.
   * Avoids the "grid then explode into ring" first-second flash (pc-898).
   */
  function maybeRevealFast() {
    if (window.__mapAppReady) return;
    var hasLots = false;
    try {
      hasLots = !!(
        document.querySelector("#lots .hier-project") ||
        document.querySelector(".hier-project")
      );
    } catch (eQ) {}
    if (hasLots) return;
    if (!window.__mapFastHasLayer) return;
    hideSkeleton();
  }

  function scheduleReveal() {
    if (revealTimer) return;
    revealTimer = setTimeout(function () {
      revealTimer = null;
      maybeRevealFast();
    }, Math.max(0, REVEAL_MS - (Date.now() - bootAt)));
  }

  function hoodsFromCity(city) {
    if (!city || typeof city !== "object") return [];
    var list = city.neighborhoods || city.folders || [];
    return Array.isArray(list) ? list : [];
  }

  function hoodsFromDetect(det) {
    if (!det || typeof det !== "object") return [];
    var projs = det.managed_projects || [];
    if (!Array.isArray(projs)) return [];
    return projs.map(function (p) {
      var name = String((p && (p.name || p.slug)) || "project");
      var slug = String((p && (p.slug || p.name)) || name)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      return {
        name: name,
        slug: slug || name.toLowerCase(),
        path: (p && p.path) || name,
        managed: true,
        store: null,
      };
    });
  }

  /**
   * pc-1001: fast ring must only show managed projects (detect set).
   * City light lists export trees / local / scripts as unmanaged folders —
   * never paint those on the failsafe layer (founder ~19-node flash).
   */
  function managedHoodsForFast(city, detect) {
    var cityHoods = hoodsFromCity(city);
    var fromDetect = hoodsFromDetect(detect);
    if (fromDetect.length) {
      var keys = {};
      fromDetect.forEach(function (m) {
        if (!m) return;
        keys[normKey(m.slug)] = true;
        keys[normKey(m.name)] = true;
      });
      var fromCity = cityHoods.filter(function (h) {
        if (!h) return false;
        return (
          keys[normKey(h.slug)] ||
          keys[normKey(h.name)] ||
          keys[normKey(h.product)]
        );
      });
      /* Prefer city rows (store badges); fall back to detect stubs. */
      return fromCity.length ? fromCity : fromDetect;
    }
    return cityHoods.filter(function (h) {
      return h && h.managed === true;
    });
  }

  /**
   * pc-1084: gate-aware live open — prefer store.ready+ip+ir (excludes ice).
   * Pre-pc-1084 used backlog+ip+ir and counted deferred parks as open.
   */
  function openCount(h) {
    if (window.WoBuckets && typeof window.WoBuckets.storeLiveOpen === "function") {
      return window.WoBuckets.storeLiveOpen((h && h.store) || {});
    }
    var st = (h && h.store) || {};
    if (Object.prototype.hasOwnProperty.call(st, "ready")) {
      return (st.ready | 0) + (st.in_progress | 0) + (st.in_review | 0);
    }
    return (st.backlog | 0) + (st.in_progress | 0) + (st.in_review | 0);
  }

  /**
   * pc-933: overlay tpScene store counts onto folder rows before open badges.
   * Server merge in map-bootstrap is primary; this is belt for detect-shell
   * paint and older Cellar builds that ship unmerged city light.
   */
  function normKey(k) {
    return String(k || "")
      .trim()
      .toLowerCase()
      .replace(/_/g, "-")
      .replace(/\s+/g, "-");
  }

  function overlayHoodStoresFromTp(hoods, tp) {
    if (!hoods || !hoods.length || !tp) return hoods;
    var stores = tp.stores;
    if (!Array.isArray(stores) && stores && typeof stores === "object") {
      stores = Object.keys(stores).map(function (k) {
        var s = stores[k] || {};
        return Object.assign({ slug: k }, s);
      });
    }
    if (!Array.isArray(stores) || !stores.length) return hoods;
    var by = {};
    stores.forEach(function (s) {
      if (!s || !s.slug) return;
      by[normKey(s.slug)] = s;
    });
    return hoods.map(function (h) {
      if (!h) return h;
      var keys = [h.product, h.slug, h.name].filter(Boolean).map(normKey);
      var s = null;
      for (var i = 0; i < keys.length; i++) {
        if (by[keys[i]]) {
          s = by[keys[i]];
          break;
        }
      }
      if (!s) return h;
      var next = Object.assign({}, h);
      next.store = {
        backlog: s.backlog | 0,
        in_progress: s.in_progress | 0,
        in_review: s.in_review | 0,
        done: s.done_total != null ? s.done_total | 0 : s.done | 0,
        urgent_backlog: s.urgent_backlog | 0,
        ready: s.ready | 0,
      };
      return next;
    });
  }

  function paintFolders(hoods, source) {
    hoods = (hoods || []).filter(function (h) {
      return h && (h.name || h.slug);
    });
    if (!hoods.length || !world) {
      setMsg("No projects found — waiting for full map…");
      return false;
    }

    /* Clear previous fast paint only */
    var old = world.querySelector("#map-fast-layer");
    if (old) old.remove();

    var NS = "http://www.w3.org/2000/svg";
    var g = document.createElementNS(NS, "g");
    g.setAttribute("id", "map-fast-layer");
    g.setAttribute("data-source", source || "fast");
    g.setAttribute("opacity", "1");

    var n = hoods.length;
    /* Ring layout — same visual language as hierarchy (not a grid) */
    var vbW = 1200;
    var vbH = 780;
    var cx = vbW / 2;
    var cy = vbH / 2;
    var folderW = 88;
    var folderH = 72;
    var half = Math.max(folderW, folderH) * 0.55;
    var stemR = n <= 1 ? 0 : Math.max(220, (half + 28) / Math.sin(Math.PI / n));
    try {
      world.setAttribute("viewBox", "0 0 " + vbW + " " + vbH);
    } catch (eV) {}

    /* Center YOU stand-in (quiet) so ring reads as Map, not a list */
    var you = document.createElementNS(NS, "g");
    you.setAttribute("class", "map-fast-you");
    you.setAttribute("transform", "translate(" + cx + "," + cy + ")");
    var youDisc = document.createElementNS(NS, "circle");
    youDisc.setAttribute("r", "22");
    youDisc.setAttribute("fill", "#e9c46a");
    youDisc.setAttribute("stroke", "#2a241c");
    youDisc.setAttribute("stroke-width", "1.5");
    you.appendChild(youDisc);
    var youLab = document.createElementNS(NS, "text");
    youLab.setAttribute("text-anchor", "middle");
    youLab.setAttribute("y", "5");
    youLab.setAttribute("font-size", "11");
    youLab.setAttribute("font-family", "system-ui, -apple-system, sans-serif");
    youLab.setAttribute("fill", "#2a241c");
    youLab.textContent = "You";
    you.appendChild(youLab);
    g.appendChild(you);

    hoods.forEach(function (h, i) {
      var ang = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(n, 1);
      var x = cx + stemR * Math.cos(ang) - folderW / 2;
      var y = cy + stemR * Math.sin(ang) - folderH / 2;
      var name = String(h.name || h.slug || "project");
      var slug = String(h.slug || name).toLowerCase();
      var open = openCount(h);
      var managed = h.managed !== false;

      var node = document.createElementNS(NS, "g");
      node.setAttribute("class", "map-fast-folder");
      node.setAttribute("data-slug", slug);
      node.setAttribute("transform", "translate(" + x + "," + y + ")");
      node.style.cursor = "pointer";

      /* Tab */
      var tab = document.createElementNS(NS, "rect");
      tab.setAttribute("x", "8");
      tab.setAttribute("y", "4");
      tab.setAttribute("width", "36");
      tab.setAttribute("height", "14");
      tab.setAttribute("rx", "3");
      tab.setAttribute(
        "fill",
        managed ? "#e9c46a" : "#c4b8a4"
      );
      tab.setAttribute("stroke", "#2a241c");
      tab.setAttribute("stroke-width", "1.2");
      node.appendChild(tab);

      /* Body */
      var body = document.createElementNS(NS, "rect");
      body.setAttribute("x", "0");
      body.setAttribute("y", "14");
      body.setAttribute("width", "88");
      body.setAttribute("height", "58");
      body.setAttribute("rx", "6");
      body.setAttribute("fill", "#fffdf8");
      body.setAttribute("stroke", "#2a241c");
      body.setAttribute("stroke-width", "1.5");
      node.appendChild(body);

      var tlab = document.createElementNS(NS, "text");
      tlab.setAttribute("x", "44");
      tlab.setAttribute("y", "48");
      tlab.setAttribute("text-anchor", "middle");
      tlab.setAttribute("font-size", "11");
      tlab.setAttribute("font-family", "system-ui, -apple-system, sans-serif");
      tlab.setAttribute("fill", "#2a241c");
      tlab.textContent =
        name.length > 12 ? name.slice(0, 11) + "…" : name;
      node.appendChild(tlab);

      if (open > 0) {
        var badge = document.createElementNS(NS, "circle");
        badge.setAttribute("cx", "76");
        badge.setAttribute("cy", "22");
        badge.setAttribute("r", "10");
        badge.setAttribute("fill", "#c0392b");
        node.appendChild(badge);
        var bt = document.createElementNS(NS, "text");
        bt.setAttribute("x", "76");
        bt.setAttribute("y", "26");
        bt.setAttribute("text-anchor", "middle");
        bt.setAttribute("font-size", "9");
        bt.setAttribute("fill", "#fff");
        bt.setAttribute("font-family", "system-ui, sans-serif");
        bt.textContent = open > 99 ? "99+" : String(open);
        node.appendChild(bt);
      }

      node.addEventListener("click", function () {
        /* When full app is ready it owns dig-in; until then show note */
        if (window.MapFast && typeof window.MapFast.onFolderClick === "function") {
          window.MapFast.onFolderClick(h);
          return;
        }
        var tip = document.getElementById("tip");
        if (tip) {
          tip.hidden = false;
          tip.textContent =
            name + " — full map still loading; click again in a moment";
          setTimeout(function () {
            tip.hidden = true;
          }, 2500);
        }
      });

      g.appendChild(node);
    });

    world.appendChild(g);
    window.__mapFastHasLayer = true;
    try {
      window.__mapFastRingAt = Date.now();
      if (typeof console !== "undefined" && console.info) {
        console.info(
          "[pc-1292] map-fast ring",
          (window.__mapFastRingAt - bootAt) + "ms",
          "source=" + (source || "fast")
        );
      }
    } catch (eMark) {}
    /*
     * pc-973: paint under skeleton; do NOT hideSkeleton here.
     * Revealing the ring before hierarchy handoff is the wrong-layout flash.
     * scheduleReveal only as failsafe if engine is late (REVEAL_MS).
     */
    setMsg("Building workspace map…");

    var err = document.getElementById("err");
    if (err) {
      err.hidden = true;
      err.textContent = "";
    }
    var badge = document.getElementById("map-live-label");
    if (badge && !window.__mapAppReady) {
      badge.textContent = "FAST · " + hoods.length;
    }
    scheduleReveal(); /* failsafe only — hierarchy handoff is the happy path */
    return true;
  }

  function takeBoot(d) {
    if (!d) return false;
    var city = d.city || d;
    /* pc-1001: managed set only — detect.managed_projects or city.managed */
    var hoods = managedHoodsForFast(city, d.detect || d);
    if (!hoods.length) return false;
    /* pc-933: folder open badges from tpScene when city light still zeros */
    hoods = overlayHoodStoresFromTp(hoods, d.tpScene);
    return paintFolders(hoods, d.detect_shell ? "detect" : "bootstrap");
  }

  /* ── pc-932: left-rail first paint from map-bootstrap (before 1.1MB app) ── */

  /* pc-1396: HTML escape lives in /esc.js */
  var escHtml = function (s) { return window.__bp.esc(s); };
  var escAttr = function (s) { return window.__bp.escAttr(s); };

  function shortWhen(ts) {
    if (!ts) return "";
    var t = Date.parse(ts);
    if (!isFinite(t)) return "";
    var sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (sec < 60) return "just now";
    if (sec < 3600) return Math.floor(sec / 60) + "m";
    if (sec < 86400) return Math.floor(sec / 3600) + "h";
    return Math.floor(sec / 86400) + "d";
  }

  function statusVerb(from, to) {
    var t = String(to || "").toLowerCase();
    var f = String(from || "").toLowerCase();
    if (t === "done" || t === "canceled" || t === "cancelled") return "closed";
    if (t === "in_progress" && (!f || f === "backlog" || f === "in_review"))
      return "claimed";
    if (t === "backlog" && !f) return "filed";
    if (t === "in_review") return "parked";
    if (t === "backlog" && f === "in_progress") return "released";
    return t ? t.replace(/_/g, " ") : "update";
  }

  function slipPillCls(to) {
    var t = String(to || "").toLowerCase();
    if (t === "done") return "st-done";
    if (t === "in_progress") return "st-live";
    if (t === "in_review") return "st-review";
    if (t === "backlog") return "st-filed";
    if (t === "canceled" || t === "cancelled") return "st-done";
    return "st-filed";
  }

  /**
   * Paint Agents + Work orders rails from bootstrap payload so left rails are
   * truthful within ~bootstrap RTT — not stuck on HTML defaults until the
   * full app parses. Full app refines via paintMapInsights + railsHandoff.
   */
  function paintRailsFromBoot(d) {
    if (!d || window.__mapAppReady) return false;
    /* Once full app has owned rails, never re-stomp */
    if (window.__mapRailAppOwned) return false;

    var people = d.people || {};
    var tp = d.tpScene || {};
    var att = d.attention || {};
    var sectors = people.sectors || [];
    var inflight = people.in_flight || [];
    var inflightSet = {};
    (Array.isArray(inflight) ? inflight : []).forEach(function (n) {
      if (n) inflightSet[String(n)] = true;
    });

    var liveN = 0;
    var dueN = 0;
    var idleN = 0;
    var roster = [];
    var seen = {};
    var now = Date.now();
    var DUE_MS = 15 * 60 * 1000;

    sectors.forEach(function (sec) {
      if (!sec) return;
      var home = String(
        ((sec.workdir || "").split("/").pop() || sec.workplace || "") || ""
      );
      (sec.workers || []).forEach(function (w) {
        if (!w || !w.name || w.kind === "citizen") return;
        if (seen[w.name]) return;
        seen[w.name] = true;
        var isLive = !!(w.working || inflightSet[w.name]);
        var kind = "idle";
        var pill = "Idle";
        var pillCls = "hand-pill st-idle";
        if (isLive) {
          kind = "live";
          pill = "Working";
          pillCls = "hand-pill st-live";
          liveN++;
        } else {
          var nf = w.next_fire ? Date.parse(w.next_fire) : NaN;
          if (isFinite(nf) && nf - now >= 0 && nf - now <= DUE_MS) {
            kind = "due";
            pill = "Due";
            pillCls = "hand-pill st-due";
            dueN++;
          } else {
            idleN++;
          }
        }
        roster.push({
          name: w.name,
          display: w.display || w.name,
          home: home,
          kind: kind,
          pill: pill,
          pillCls: pillCls,
          role: String(w.skill || w.role || (w.kind === "job" ? "job" : "") || "").trim(),
          isJob: w.kind === "job",
          health: String(w.health || "").trim(),
        });
      });
    });
    /* in_flight not yet listed under sectors */
    Object.keys(inflightSet).forEach(function (name) {
      if (seen[name]) return;
      seen[name] = true;
      liveN++;
      roster.push({
        name: name,
        display: name,
        home: "",
        kind: "live",
        pill: "Working",
        pillCls: "hand-pill st-live",
        role: "",
        isJob: false,
        health: "",
      });
    });
    /* Heat order matches agents-panel rowRank (peek/walk before due). */
    roster.sort(function (a, b) {
      var rank = { live: 0, peek: 1, walk: 2, due: 3, idle: 4 };
      var ra = rank[a.kind] != null ? rank[a.kind] : 9;
      var rb = rank[b.kind] != null ? rank[b.kind] : 9;
      if (ra !== rb) return ra - rb;
      return String(a.display || a.name).localeCompare(String(b.display || b.name));
    });

    var liveList = document.getElementById("map-live-list");
    var liveEmpty = document.getElementById("map-live-empty");
    var agentsSub = document.getElementById("map-agents-sub");
    var agentsTot = document.getElementById("map-agents-total");
    var agentsCap = document.getElementById("map-agents-cap");
    var ROSTER_CAP = 40;

    if (agentsSub) {
      agentsSub.textContent =
        liveN + " live · " + dueN + " due · " + idleN + " idle";
    }
    if (agentsTot) {
      agentsTot.textContent = String(roster.length);
      agentsTot.hidden = false;
    }

    /* pc-995: same guard as chips — never re-stomp after full app owns rails */
    if (liveList && liveEmpty && !window.__mapAppReady && !window.__mapRailAppOwned) {
      if (!roster.length) {
        liveList.hidden = true;
        liveList.innerHTML = "";
        liveEmpty.hidden = false;
        liveEmpty.textContent = "No hands or jobs yet";
        if (agentsCap) {
          agentsCap.hidden = true;
          agentsCap.textContent = "";
        }
      } else {
        liveEmpty.hidden = true;
        liveList.hidden = false;
        var slice = roster.slice(0, ROSTER_CAP);
        var html = "";
        slice.forEach(function (r) {
          var dens =
            r.kind === "live"
              ? "is-live"
              : r.kind === "due"
                ? "is-due"
                : "is-idle";
          var short = String(r.display || r.name || "");
          if (short.length > 28) short = short.slice(0, 27) + "…";
          var role = r.role || (r.home ? r.home.slice(0, 18) : "");
          html +=
            '<li class="hand-li ' +
            dens +
            '" data-worker="' +
            escAttr(r.name) +
            '" data-fast-rail="1">' +
            '<div class="hand-card-wrap hand-card ' +
            dens +
            '" data-agent="' +
            escAttr(r.name) +
            '" data-entity-slug="' +
            escAttr(r.home || "__you__") +
            '" data-entity-seat="' +
            (r.isJob ? "jobs" : "hands") +
            '" role="button" tabindex="0">' +
            '<span class="hand-av" title="' +
            (r.isJob ? "job" : "hand") +
            '"><span class="glyph">' +
            (r.isJob ? "⏱" : "◆") +
            "</span></span>" +
            '<span class="hand-body">' +
            '<span class="hand-top">' +
            '<span class="hand-nm">' +
            escHtml(short) +
            "</span>" +
            '<span class="' +
            r.pillCls +
            '">' +
            escHtml(r.pill) +
            "</span></span>" +
            (role
              ? '<span class="hand-role">' + escHtml(role) + "</span>"
              : "") +
            (r.kind === "live"
              ? '<span class="hand-work">On shift</span>'
              : "") +
            "</span></div></li>";
        });
        liveList.innerHTML = html;
        if (agentsCap) {
          if (roster.length > ROSTER_CAP) {
            agentsCap.hidden = false;
            agentsCap.textContent =
              "Showing " + ROSTER_CAP + " of " + roster.length + " on roster";
          } else {
            agentsCap.hidden = true;
            agentsCap.textContent = "";
          }
        }
      }
    }

    /* Work-order header from tpScene.stores + attention For You */
    var storesRaw = tp.stores;
    /* pc-1001: missing stores = feed still pending — do not assert "0 WOs" */
    var storesKnown =
      Array.isArray(storesRaw) ||
      (storesRaw && typeof storesRaw === "object");
    var stores = storesRaw;
    if (!Array.isArray(stores) && stores && typeof stores === "object") {
      stores = Object.keys(stores).map(function (k) {
        var s = stores[k] || {};
        return Object.assign({ slug: k }, s);
      });
    }
    stores = Array.isArray(stores) ? stores : [];
    var openSum = 0;
    var doneSum = 0;
    var readySum = 0;
    if (storesKnown) {
      stores.forEach(function (s) {
        if (!s) return;
        openSum +=
          (s.backlog | 0) + (s.in_progress | 0) + (s.in_review | 0);
        doneSum += s.done_total != null ? s.done_total | 0 : s.done | 0;
        readySum += s.ready | 0;
      });
    }
    var deskTotal = openSum + doneSum;
    var woFeedsPending = !storesKnown;

    var attItems =
      (att && Array.isArray(att.items) && att.items) ||
      (Array.isArray(tp.attention) && tp.attention) ||
      [];
    /* Fail-open empty attention is ok; "pending" flag reserved if suite adds it */
    var attPending = !!(att && att.pending);
    var forYouN = attItems.filter(function (it) {
      if (!it) return false;
      var k = String(it.kind || "").toLowerCase().replace(/ /g, "_");
      return k !== "stalled" && k !== "embargo";
    }).length;

    var woTot = document.getElementById("map-wo-total");
    var woSub = document.getElementById("map-wo-total-sub");
    if (woTot) {
      if (woFeedsPending) {
        woTot.textContent = "…";
        woTot.title = "Loading work-order counts…";
      } else {
        woTot.textContent = String(deskTotal);
        woTot.title =
          deskTotal +
          " work orders across projects (" +
          openSum +
          " open · " +
          doneSum +
          " done; open = live, deferred excluded)";
      }
    }
    if (woSub) {
      woSub.textContent = woFeedsPending
        ? "Loading work orders…"
        : openSum + " open · " + doneSum + " done";
    }

    var youMeta = document.getElementById("map-you-meta");
    var youPill = document.getElementById("map-you-pill");
    var youCard = document.getElementById("map-you-card");
    if (youMeta) {
      if (attPending) {
        youMeta.textContent = "Checking For You…";
      } else {
        youMeta.textContent =
          forYouN > 0
            ? forYouN === 1
              ? "1 For You"
              : forYouN + " For You"
            : "Nothing For You";
      }
    }
    if (youPill) {
      if (attPending) {
        youPill.textContent = "…";
        youPill.classList.add("is-zero");
      } else {
        youPill.textContent = forYouN > 99 ? "99+" : String(forYouN);
        youPill.classList.toggle("is-zero", forYouN <= 0);
      }
    }
    if (youCard) {
      /* class id stays is-need-you (CSS); citizen meta above is For You only (pc-949) */
      youCard.classList.toggle("is-need-you", !attPending && forYouN > 0);
    }

    /* Filter count sentence (live · ready · deferred · for you) */
    var woFilters = document.getElementById("map-wo-filters");
    /* pc-995: also respect railsHandoff — __mapAppReady alone can lag */
    if (
      woFilters &&
      !window.__mapAppReady &&
      !window.__mapRailAppOwned
    ) {
      function door(id, label, value) {
        return (
          '<button type="button" class="wo-count-link" data-wo-filter="' +
          id +
          '" data-fast-rail="1" aria-pressed="false" title="' +
          escAttr(label + " " + value) +
          '"><span class="v">' +
          value +
          '</span><span class="l">' +
          escHtml(label) +
          "</span></button>"
        );
      }
      if (woFeedsPending) {
        /* Holding line — not "0 live · 0 ready" as truth while Desk is slow */
        woFilters.innerHTML =
          '<span class="wo-count-line" role="status" data-fast-rail="1">' +
          "Loading counts…</span>";
      } else {
        /* deferred unknown from stores alone — show 0 honestly until full app */
        woFilters.innerHTML =
          '<span class="wo-count-line" role="group" aria-label="Work-order counts">' +
          door("live", "live", openSum) +
          '<span class="wo-count-sep" aria-hidden="true">·</span>' +
          door("ready", "ready", readySum) +
          '<span class="wo-count-sep" aria-hidden="true">·</span>' +
          door("deferred", "deferred", 0) +
          '<span class="wo-count-sep" aria-hidden="true">·</span>' +
          door("for_you", "for you", forYouN) +
          "</span>";
      }
    }

    /* Tape: recent_transitions (+ title join from filed) — not multi-minute Loading */
    var tapeList = document.getElementById("map-tape-list");
    var tapeEmpty = document.getElementById("map-tape-empty");
    var titleById = {};
    ((tp.filed || []) || []).forEach(function (f) {
      if (f && f.id) titleById[String(f.id)] = f.title || "";
    });
    var transitions = Array.isArray(tp.recent_transitions)
      ? tp.recent_transitions.slice()
      : [];
    /* pc-995: guard tape like chips — was unguarded and re-stamped data-fast-rail */
    if (
      tapeList &&
      tapeEmpty &&
      !window.__mapAppReady &&
      !window.__mapRailAppOwned
    ) {
      if (!transitions.length && !attItems.length) {
        tapeEmpty.hidden = false;
        /* pc-1001: pending feeds keep holding copy, not "No activity yet" */
        tapeEmpty.textContent = woFeedsPending
          ? "Loading live activity…"
          : deskTotal > 0
            ? "Activity will appear as work moves"
            : "No work-order activity yet";
        tapeList.hidden = true;
        tapeList.innerHTML = "";
      } else {
        tapeEmpty.hidden = true;
        tapeList.hidden = false;
        var rows = transitions.slice(0, 24);
        /* If transitions empty but attention exists, skeleton For You as honesty */
        if (!rows.length && attItems.length) {
          rows = attItems.slice(0, 12).map(function (it) {
            return {
              task_id: it.id,
              to_status: it.kind || "for_you",
              from_status: "",
              author: "",
              ts: it.waiting_since || "",
              store: it.product || "",
              _title: it.title || "",
              _fromAtt: true,
            };
          });
        }
        var th = "";
        rows.forEach(function (tr) {
          if (!tr) return;
          var tid = String(tr.task_id || tr.id || "");
          if (!tid) return;
          var title =
            tr._title ||
            titleById[tid] ||
            (tr.to_status
              ? statusVerb(tr.from_status, tr.to_status)
              : "update");
          var pill = tr._fromAtt
            ? "For You"
            : statusVerb(tr.from_status, tr.to_status);
          var pcls = tr._fromAtt ? "st-you" : slipPillCls(tr.to_status);
          var focus = String(tr.store || tr.product || "");
          var when = shortWhen(tr.ts || tr.closed_at || tr.waiting_since);
          th +=
            '<li class="slip-li" data-fast-rail="1"><button type="button" class="slip-row" data-tid="' +
            escAttr(tid) +
            '" data-focus="' +
            escAttr(focus) +
            '" data-entity-slug="' +
            escAttr(focus) +
            '">' +
            '<span class="slip-top">' +
            '<span class="slip-id">' +
            escHtml(tid) +
            "</span>" +
            '<span class="slip-pill ' +
            pcls +
            '">' +
            escHtml(pill) +
            "</span></span>" +
            '<span class="slip-title">' +
            escHtml(String(title).slice(0, 96)) +
            "</span>" +
            '<span class="slip-glance is-skel" aria-hidden="true"></span>' +
            (when
              ? '<span class="slip-when">' + escHtml(when) + "</span>"
              : '<span class="slip-when" hidden></span>') +
            "</button></li>";
        });
        tapeList.innerHTML = th;
      }
    }

    window.__mapRailFastPainted = true;
    try {
      document.documentElement.setAttribute("data-map-rail-fast", "1");
      var railLive = document.getElementById("map-rail-live");
      var tape = document.getElementById("map-tape");
      if (railLive) railLive.setAttribute("data-map-rail-fast", "1");
      if (tape) tape.setAttribute("data-map-rail-fast", "1");
    } catch (eMark) {}
    return true;
  }

  function railsHandoff() {
    window.__mapRailAppOwned = true;
    window.__mapRailFastPainted = false;
    try {
      document.documentElement.removeAttribute("data-map-rail-fast");
      var railLive = document.getElementById("map-rail-live");
      var tape = document.getElementById("map-tape");
      if (railLive) railLive.removeAttribute("data-map-rail-fast");
      if (tape) tape.removeAttribute("data-map-rail-fast");
      /* pc-995: strip residual fast markers so soft-patch cannot leave
       * unwired map-fast chips / frozen tape after handoff. */
      var roots = [railLive, tape, document.getElementById("map-wo-filters")];
      for (var i = 0; i < roots.length; i++) {
        var root = roots[i];
        if (!root || !root.querySelectorAll) continue;
        var marks = root.querySelectorAll("[data-fast-rail]");
        for (var j = 0; j < marks.length; j++) {
          marks[j].removeAttribute("data-fast-rail");
        }
      }
    } catch (e) {}
    return true;
  }

  function fetchJson(url, ms) {
    var ctrl =
      typeof AbortController !== "undefined" ? new AbortController() : null;
    var t =
      ctrl &&
      setTimeout(function () {
        try {
          ctrl.abort();
        } catch (e) {}
      }, ms || 4000);
    return fetch(url, {
      credentials: "same-origin",
      cache: "no-store",
      signal: ctrl ? ctrl.signal : undefined,
    })
      .then(function (r) {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .finally(function () {
        if (t) clearTimeout(t);
      });
  }

  function boot() {
    setMsg("Loading projects…");
    /*
     * pc-901: SHARE __mapBootPrefetch — do not null it. Full app / SuiteData
     * also consume the same promise; stealing forced a second 4s bootstrap.
     */
    var pref =
      window.__mapBootPrefetch &&
      typeof window.__mapBootPrefetch.then === "function"
        ? window.__mapBootPrefetch
        : null;

    var bootP = pref
      ? pref
      : fetchJson("/api/map/snapshot", 5000).catch(function () {
          return null;
        });
    var detP = fetchJson("/api/detect", 2500).catch(function () {
      return null;
    });

    /*
     * pc-902: one fast paint only. Detect is a short-wait fallback so we do
     * not re-layout (detect → bootstrap) and flash the ring twice before
     * the full hierarchy lands.
     */
    var painted = false;
    var bootDone = false;
    bootP.then(function (d) {
      bootDone = true;
      if (window.__mapAppReady) return;
      if (d && d.city) {
        try {
          if (window.SuiteData && typeof SuiteData.put === "function") {
            SuiteData.put("mapBootstrap", d);
            if (d.city) SuiteData.put("city", d.city);
            if (d.people) SuiteData.put("people", d.people);
            if (d.tpScene) SuiteData.put("tpScene", d.tpScene);
            if (d.attention) SuiteData.put("attention", d.attention);
          }
        } catch (ePut) {}
        painted = takeBoot(d) || painted;
        /* pc-932: rails from bootstrap before 1.1MB app parses */
        try {
          paintRailsFromBoot(d);
        } catch (eRails) {
          try {
            console.warn("[map-fast] paintRailsFromBoot", eRails);
          } catch (eC) {}
        }
      }
      if (!painted) {
        setMsg("Waiting for full map engine…");
      }
    });
    /* Detect only if bootstrap still empty after 280ms */
    detP.then(function (det) {
      if (window.__mapAppReady) return;
      function tryDetect() {
        if (painted || bootDone || window.__mapAppReady) return;
        var hoods = hoodsFromDetect(det);
        if (hoods.length) {
          painted = paintFolders(hoods, "detect") || painted;
        }
      }
      if (painted || bootDone) return;
      setTimeout(tryDetect, 280);
    });

    /* Absolute failsafe: never leave skeleton past 8s without trying detect again */
    setTimeout(function () {
      if (window.__mapAppReady || window.__mapFastPainted) return;
      setMsg("Still loading — drawing what we can…");
      fetchJson("/api/detect", 2000)
        .then(function (det) {
          if (!window.__mapFastPainted) paintFolders(hoodsFromDetect(det), "detect-retry");
        })
        .catch(function () {
          hideSkeleton();
          setMsg("Map engine slow — refresh if empty");
        });
    }, 8000);
  }

  window.MapFast = {
    painted: function () {
      return !!window.__mapFastPainted || !!window.__mapFastHasLayer;
    },
    hasLayer: function () {
      return !!window.__mapFastHasLayer;
    },
    railsPainted: function () {
      return !!window.__mapRailFastPainted;
    },
    /** Full app paintMapInsights finished — stop fast rail ownership. */
    railsHandoff: railsHandoff,
    /**
     * Full app calls only after finishFirstPaint — never on script load.
     * If the hierarchy has not completed its seats/camera pass, keep the fast
     * layer. Lots alone are not a readiness signal: a thrown build used to
     * leave partial lots hidden under data-map-building forever (pc-904).
     */
    handoff: function () {
      if (revealTimer) {
        try {
          clearTimeout(revealTimer);
        } catch (eT) {}
        revealTimer = null;
      }
      if (window.__mapHierarchyReady !== true) {
        window.__mapAppReady = false;
        maybeRevealFast();
        return false;
      }
      /* Only remove fast layer if full map actually built lots */
      var hasLots = false;
      try {
        hasLots = !!(
          document.querySelector("#lots .hier-project") ||
          document.querySelector("#lots .hier-folder") ||
          document.querySelector(".hier-project")
        );
      } catch (eQ) {}
      var layer = document.getElementById("map-fast-layer");
      if (!hasLots && layer) {
        /* Full app not ready — keep folders, reveal them if still under skeleton */
        try {
          console.warn("[map-fast] handoff deferred — full map has no lots yet");
        } catch (eC) {}
        window.__mapAppReady = false;
        maybeRevealFast();
        return false;
      }
      window.__mapAppReady = true;
      try {
        document.documentElement.removeAttribute("data-map-building");
      } catch (eB) {}
      if (layer) {
        try {
          /* Short fade — hierarchy already painted underneath (opacity 0→1) */
          var reduceMotion = false;
          try {
            reduceMotion = !!(
              window.matchMedia &&
              window.matchMedia("(prefers-reduced-motion: reduce)").matches
            );
          } catch (eM) {}
          layer.setAttribute(
            "class",
            (layer.getAttribute("class") || "") + " is-handoff"
          );
          layer.style.transition = reduceMotion
            ? "none"
            : "opacity 0.12s ease";
          layer.style.opacity = "0";
          setTimeout(function () {
            try {
              layer.remove();
            } catch (eR) {}
          }, reduceMotion ? 0 : 140);
        } catch (e) {
          try {
            layer.remove();
          } catch (e2) {}
        }
      }
      window.__mapFastHasLayer = false;
      try {
        document.documentElement.removeAttribute("data-map-fast");
      } catch (e3) {}
      hideSkeleton();
      return true;
    },
  };

  /* Script is at end of body — DOM is ready. Do not wait on DOMContentLoaded
   * (deferred/async full-app load must not gate this). */
  try {
    boot();
  } catch (eBoot) {
    try {
      setMsg("Fast paint error — " + (eBoot && eBoot.message ? eBoot.message : eBoot));
    } catch (e2) {}
  }
})();
