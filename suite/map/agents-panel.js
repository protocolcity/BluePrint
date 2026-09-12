/*! agents-panel.js — Agent activities left-rail state + paint (pc-1130 Phase 3-A)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4 Phase 3).
 * Module-scope state lives here only — host calls the public API.
 *
 * Browser: window.AgentsPanel
 * Public: { init, paint, setStale } plus bridge accessors used by Map host
 * during the strangler (desk-owner index, shift truth, poll freshness).
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    fetchLiveStrip: null,
    fetchJsonTimeout: null,
    getModel: null,
    getMapDigIn: null,
    getPeople: null,
    actorRoleTitle: null,
    actorIsJob: null,
    tierOf: null,
    workerColor: null,
    nextFireMs: null,
    handPeekProgress: null,
    dispatchWalkProgress: null,
    isSkippedRound: null,
    fmtCountdown: null,
    getHandGlyph: null,
    getStaffGlyph: null,
    getJobGlyph: null,
    applyMapNodeStageFlag: null,
    paintMapMast: null,
    requestSkipRound: null,
    selectMapEntity: null,
    inspectPerson: null,
    wireMapEntityPreview: null,
    clearMapEntityPreviewKind: null,
    syncMapEntitySelection: null,
    isDigFocusSlug: null,
    getLastCity: null,
    getLastPeople: null,
    getLastAtt: null,
    getLastTpScene: null,
    onOwnerIndexChanged: null,
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  function model() {
    var g = H("getModel");
    return g ? g() : null;
  }

  function mapDigIn() {
    var g = H("getMapDigIn");
    return g ? g() : null;
  }

  /* Activity beat memory for soft-patch (was late in map app). */
  const _agentActivityAt = {};
  const _agentActivitySig = {};
  /* Soft-patch signature for #map-live-list */
  let _liveSig = "";
  let _ownerRepaint = false;

  /*
   * pc-526: Desk Owner claim index for LIVE work lines.
   * WorkForce holding[] is often empty for the whole shift; in_progress /
   * in_review tickets with latest Owner: <hand> are the board truth.
   * hand (lowercase) → { id, title, _u }
   * pc-1067: also tid → seat hand for CLAIMED chip attribution.
   */
  let _deskOwnerByHand = {};
  let _deskHolderByTid = {};
  let _deskOwnerAt = 0;
  let _deskOwnerLoading = false;
  /* pc-1204: force refresh requested while a strip hop was already in flight */
  let _deskOwnerForceQueued = false;
  /*
   * pc-1204: short-lived event truth so an in-flight / lagging live-strip hop
   * cannot re-poison Holding/CLAIMED after close, or drop a just-warmed claim.
   * tid → expiresMs · hand → { id, title, _u, until }
   */
  let _deskOwnerTombstone = {};
  let _deskOwnerWarm = {};
  const DESK_OWNER_TTL_MS = 12000;
  const DESK_OWNER_EVENT_HOLD_MS = 15000;
  /* pc-705 / pc-1067: last successful Map poll — freshness for LIVE badge + agent lines */
  let _lastMapPollOkAt = 0;
  /* pc-1106: suppress false-STALE on hidden-tab / refocus race.
   * Failsafe timer lives in workspace_map_app.js (pc-1157) — only the
   * boolean hold is owned here via setPendingRefocus / noteMapPollOk. */
  let _pendingRefocusPoll = false;

  /** Host / personal seat labels — not claim-holder names on glass. */
  function isYouishSeat(name) {
    return /^(you|founder|founder-terminal)$/i.test(String(name || "").trim());
  }

  /**
   * pc-1067: preferred claim seat from worker:* labels (skip you/founder).
   * Pure — labels array or space-joined string.
   */
  function seatHandFromLabels(labels) {
    const list = Array.isArray(labels)
      ? labels
      : String(labels || "")
          .split(/\s+/)
          .filter(Boolean);
    let fallback = "";
    for (let i = 0; i < list.length; i++) {
      const lab = String(list[i] || "")
        .trim()
        .toLowerCase();
      if (lab.indexOf("worker:") !== 0) continue;
      const hand = lab.slice("worker:".length).trim();
      if (!hand) continue;
      if (isYouishSeat(hand)) {
        if (!fallback) fallback = hand;
        continue;
      }
      return hand;
    }
    return fallback;
  }

  /**
   * pc-1067: seat hand for a desk task — worker:* first, then Owner if not youish.
   */
  function seatHandFromTask(t) {
    if (!t) return "";
    const fromLabs = seatHandFromLabels(t.labels || t.tags || []);
    if (fromLabs && !isYouishSeat(fromLabs)) return fromLabs;
    const own = String(t.owner || "")
      .trim()
      .toLowerCase();
    if (own && !isYouishSeat(own)) return own;
    return fromLabs || "";
  }

  /**
   * pc-1067: Map data freshness — same 12s window as LIVE/STALE badge.
   * When suite/polls die, last-known agent lines must not assert live truth.
   */
  function mapLastRefreshAt() {
    return typeof _lastMapPollOkAt === "number" ? _lastMapPollOkAt : 0;
  }

  function isMapDataStale() {
    const last = mapLastRefreshAt();
    if (!last) return true;
    /* pc-1106: hidden-tab poll throttle (≥8s) races the fixed 12s window.
     * Nobody can see a hidden badge; suppress until visible + first poll lands. */
    try {
      if (typeof document !== "undefined" && document.hidden) return false;
    } catch (eH) {}
    if (_pendingRefocusPoll) return false;
    return Date.now() - last > 12000;
  }

  function renderedActivityCopy(value) {
    return String(value || "")
      .replace(/\bdesk run\b/gi, "queue run")
      .replace(/\btickets\b/gi, "work orders")
      .replace(/\bticket\b/gi, "work order");
  }

  /**
   * pc-689: WF scene queue string → ready depth (0 when unknown / em-dash).
   * Pure — mirrored in tests/test_map_agent_queue_hint.py.
   */
  function parseReadyQueueDepth(w) {
    if (!w) return 0;
    const q = w.queue;
    if (q == null || q === "" || q === "—" || q === "-" || q === "–") return 0;
    const n = parseInt(q, 10);
    return isFinite(n) && n > 0 ? n : 0;
  }

  /**
   * pc-943: sticky shift truth for Agents strip.
   * Light /api/people strips last_shift (null every poll) and pulse may carry
   * recent_failures (wf-118) after WF bounce. Without sticky glass, fail rows
   * vanish within one light cycle even when full scene / ledger knew the fail.
   * Never invents WorkLane Owner comments — only WF last_shift / recent_failures.
   */
  let _shiftTruthByName = Object.create(null);
  let _shiftTruthFetchedAt = 0;
  let _shiftTruthInflight = null;
  const SHIFT_TRUTH_MIN_MS = 4000;

  function shiftTsRank(ts) {
    if (!ts) return 0;
    try {
      const t = new Date(ts).getTime();
      return isFinite(t) ? t : 0;
    } catch (eR) {
      return 0;
    }
  }

  function noteShiftTruth(name, ls, src) {
    if (!name || !ls || typeof ls !== "object") return;
    const outcome = String(ls.outcome || "").trim();
    const ts = String(ls.ts || ls.end_ts || "").trim();
    if (!outcome && !ts) return;
    const prev = _shiftTruthByName[name];
    if (prev) {
      const pt = shiftTsRank(prev.ts);
      const nt = shiftTsRank(ts);
      if (pt && nt && pt > nt) return;
      if (pt && !nt) return;
    }
    const tid = digShiftTicketId(ls) || (prev && prev.ticket_id) || "";
    _shiftTruthByName[name] = {
      ts: ts,
      outcome: outcome || (prev && prev.outcome) || "",
      reason: String(ls.reason || "").trim(),
      passes: ls.passes != null ? ls.passes | 0 : 0,
      ticket_id: tid,
      ticket_title: String(
        ls.ticket_title || (prev && prev.ticket_title) || ""
      ).trim(),
      _src: src || "last_shift",
    };
  }

  /**
   * pc-1174: sticky last *real* work (not empty SKIP) for Agents face.
   * Separate from last_shift truth so queue-empty thrash cannot wipe the id.
   */
  let _lastRealByName = Object.create(null);

  function noteLastRealTruth(name, pack) {
    if (!name || !pack || typeof pack !== "object") return;
    const ls =
      pack.last_real_shift && typeof pack.last_real_shift === "object"
        ? pack.last_real_shift
        : pack;
    const lrt =
      pack.last_real_ticket && typeof pack.last_real_ticket === "object"
        ? pack.last_real_ticket
        : null;
    const tid =
      (lrt && lrt.id) ||
      digShiftTicketId(ls) ||
      String(pack.id || pack.ticket_id || "").trim() ||
      "";
    const ts = String(
      (lrt && lrt.ts) || (ls && (ls.ts || ls.end_ts)) || pack.ts || ""
    ).trim();
    const outcome = String((ls && ls.outcome) || "").trim();
    /* Need at least a ticket id or a meaningful shift outcome */
    if (!tid && (!ls || isEmptyCheckShift(ls))) return;
    if (!tid && !outcome && !ts) return;
    const prev = _lastRealByName[name];
    if (prev) {
      const pt = shiftTsRank(prev.ts);
      const nt = shiftTsRank(ts);
      if (pt && nt && pt > nt) return;
      if (pt && !nt) return;
    }
    _lastRealByName[name] = {
      ts: ts,
      outcome: outcome || (prev && prev.outcome) || "",
      reason: String((ls && ls.reason) || "").trim(),
      passes: ls && ls.passes != null ? ls.passes | 0 : 0,
      ticket_id: tid || (prev && prev.ticket_id) || "",
      ticket_title: String(
        (lrt && lrt.title) ||
          (ls && ls.ticket_title) ||
          (prev && prev.ticket_title) ||
          ""
      ).trim(),
      _src: "last_real",
    };
  }

  function workerLastReal(w) {
    if (!w || typeof w !== "object") return null;
    const lrt =
      w.last_real_ticket && typeof w.last_real_ticket === "object"
        ? w.last_real_ticket
        : null;
    const lrs =
      w.last_real_shift && typeof w.last_real_shift === "object"
        ? w.last_real_shift
        : null;
    if (lrt || lrs) {
      noteLastRealTruth(w.name, {
        last_real_ticket: lrt,
        last_real_shift: lrs,
      });
    }
    const sticky = w.name ? _lastRealByName[w.name] : null;
    if (sticky && (sticky.ticket_id || sticky.outcome || sticky.ts)) {
      return {
        ts: sticky.ts || "",
        outcome: sticky.outcome || "",
        reason: sticky.reason || "",
        passes: sticky.passes | 0,
        ticket_id: sticky.ticket_id || "",
        ticket_title: sticky.ticket_title || "",
      };
    }
    /* Fall back: last_shift when it is real work (not empty check) */
    const ls = workerLastShift(w);
    if (ls && !isEmptyCheckShift(ls) && isMeaningfulShift(ls)) {
      return ls;
    }
    return null;
  }

  /**
   * pc-1174 / pc-1184 · ALWAYS_WORK §9: citizen line for last real ticket on
   * Agents face. Empty / SKIP / capacity exits never masquerade as last work.
   * When empty thrash trails real work, append streak so empty-shift lies are
   * visible without gold spam (empty vs real signal).
   */
  function emptyChecksTail(w) {
    if (!w || typeof w !== "object") return "";
    const ec =
      w.empty_checks && typeof w.empty_checks === "object" ? w.empty_checks : null;
    if (!ec) return "";
    const n = parseInt(ec.count, 10) || 0;
    if (n < 1) return "";
    let tail = n + " empty";
    const since = shortShiftWhen(ec.since || ec.last_ts || "");
    if (since) tail += " since " + since;
    return tail;
  }

  function lastRealWorkLine(w) {
    const real = workerLastReal(w);
    if (!real) return "";
    if (isEmptyCheckShift(real)) return "";
    const tid = digShiftTicketId(real) || String(real.ticket_id || "").trim();
    const title = String(real.ticket_title || "").trim();
    const when = shortShiftWhen(real.ts);
    const emptyTail = emptyChecksTail(w);
    if (tid) {
      let line = "Last real · " + tid;
      if (title) line += " · " + title.slice(0, 36);
      else if (when) line += " · " + when;
      if (emptyTail) line += " · " + emptyTail;
      return line;
    }
    /* Real shift without published id — outcome only (never empty-check copy) */
    if (isMeaningfulShift(real)) {
      const lab = citizenShiftLabel(real);
      if (!lab || lab === "—") return "";
      let line = "Last real · " + lab + (when ? " · " + when : "");
      if (emptyTail) line += " · " + emptyTail;
      return line;
    }
    return "";
  }

  /** wf-118 generation recent_failures → sticky fail rows (pc-943). */
  function noteRecentFailures(list) {
    if (!Array.isArray(list) || !list.length) return;
    list.forEach(function (f) {
      if (!f || typeof f !== "object") return;
      const name = String(f.worker || f.name || "").trim();
      if (!name) return;
      noteShiftTruth(
        name,
        {
          ts: f.ts || f.end_ts || "",
          outcome: f.outcome || "error",
          reason: f.reason || "",
          passes: 0,
        },
        "recent_failures"
      );
    });
  }

  function ingestPeopleShiftTruth(people) {
    if (!people || typeof people !== "object") return;
    if (Array.isArray(people.recent_failures)) {
      noteRecentFailures(people.recent_failures);
    }
    (people.sectors || []).forEach(function (sec) {
      (sec.workers || []).forEach(function (w) {
        if (!w || !w.name) return;
        const ls = w.last_shift;
        if (ls && typeof ls === "object" && (ls.outcome || ls.ts)) {
          noteShiftTruth(w.name, ls, "people");
        }
        /* pc-1174: last real past empty thrash (Agents face) */
        if (
          (w.last_real_ticket && typeof w.last_real_ticket === "object") ||
          (w.last_real_shift && typeof w.last_real_shift === "object")
        ) {
          noteLastRealTruth(w.name, w);
        }
      });
    });
  }

  /**
   * Background full-scene last_shift refresh (pc-943).
   * Light polls stay cheap; full=1 carries ledger outcomes when suite enrich
   * is stale or light nulls last_shift. Debounced; never blocks rail paint.
   */
  function refreshShiftTruthFromFull(force) {
    const now = Date.now();
    if (!force && now - _shiftTruthFetchedAt < SHIFT_TRUTH_MIN_MS) {
      return _shiftTruthInflight || Promise.resolve(false);
    }
    if (_shiftTruthInflight) return _shiftTruthInflight;
    _shiftTruthFetchedAt = now;
    _shiftTruthInflight = Promise.resolve()
      .then(function () {
        var fj = H("fetchJsonTimeout");
        if (typeof fj !== "function") {
          return fetch("/api/people?full=1", {
            cache: "no-store",
            credentials: "same-origin",
          }).then(function (r) {
            if (!r.ok) throw new Error("people full " + r.status);
            return r.json();
          });
        }
        return fj("/api/people?full=1", 6000);
      })
      .then(function (d) {
        if (d && typeof d === "object") ingestPeopleShiftTruth(d);
        return true;
      })
      .catch(function () {
        return false;
      })
      .then(function (ok) {
        _shiftTruthInflight = null;
        return ok;
      });
    return _shiftTruthInflight;
  }

  function applyPulsePeopleFailures(pulse) {
    if (!pulse || typeof pulse !== "object") return;
    const pe = (pulse.sources && pulse.sources.people) || pulse.people || null;
    if (!pe || typeof pe !== "object") return;
    if (Array.isArray(pe.recent_failures)) {
      noteRecentFailures(pe.recent_failures);
    }
  }

  /**
   * pc-922: last_shift from WF full scene or suite ledger enrich.
   * pc-943: sticky merge so light polls / missing enrich cannot wipe fail rows.
   */
  function workerLastShift(w) {
    if (!w || typeof w !== "object") return null;
    const ls = w.last_shift;
    if (ls && typeof ls === "object" && (ls.outcome || ls.ts)) {
      if (w.name) noteShiftTruth(w.name, ls, "worker");
      return ls;
    }
    const sticky = w.name ? _shiftTruthByName[w.name] : null;
    if (sticky && (sticky.outcome || sticky.ts)) {
      return {
        ts: sticky.ts || "",
        outcome: sticky.outcome || "",
        reason: sticky.reason || "",
        passes: sticky.passes | 0,
        ticket_id: sticky.ticket_id || "",
        ticket_title: sticky.ticket_title || "",
      };
    }
    return null;
  }

  /**
   * pc-922: short relative/absolute stamp for rail outcome rows.
   */
  function shortShiftWhen(ts) {
    if (!ts) return "";
    try {
      const t = new Date(ts).getTime();
      if (!isFinite(t)) return String(ts).slice(0, 16);
      const sec = Math.round((Date.now() - t) / 1000);
      if (sec < 0) return "just now";
      if (sec < 60) return sec + "s ago";
      if (sec < 3600) return Math.round(sec / 60) + "m ago";
      if (sec < 86400) return Math.round(sec / 3600) + "h ago";
      return new Date(t).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (eTs) {
      return String(ts).slice(0, 16);
    }
  }

  /**
   * Drop relative-clock tails ("· 2m ago" / "just now") from a status string.
   * State-change signatures must hash facts, not the ticking clock — otherwise
   * every minute rollover reads as "new state" and re-floats the row.
   */
  function stripRelWhen(s) {
    return String(s || "")
      .replace(/\s*·\s*(?:just now|\d+[smh] ago)\b/g, "")
      .replace(/^\s*(?:just now|\d+[smh] ago)\s*$/, "")
      .trim();
  }

  /**
   * pc-689: citizen amber/skip line from WF health + why.
   * pc-922: also last_shift outcome (error / vendor_limit / SKIP) so light
   * scene + ledger bridge paints fails even when health was still "ok".
   * Prefer short register: waiting on lock · no ready work · last fire skipped.
   * Pure — mirrored in tests/test_map_agent_queue_hint.py.
   */
  function citizenHandStatusHint(w) {
    if (!w) return "";
    const health = String(w.health || w.status || "")
      .toLowerCase()
      .trim();
    const whyRaw = renderedActivityCopy(
      w.why || w.status_detail || w.activity || ""
    ).trim();
    const why = whyRaw.toLowerCase();
    if (why.indexOf("lock") >= 0) return "waiting on lock";
    if (health === "amber" || health === "wedged") {
      if (why.indexOf("skip") >= 0) return "last fire skipped";
      if (
        why.indexOf("no-progress") >= 0 ||
        why.indexOf("no progress") >= 0
      )
        return "queue waiting · no claim";
      if (why.indexOf("vendor") >= 0) return "vendor limit";
      return whyRaw ? whyRaw.slice(0, 42) : "needs attention";
    }
    if (
      health === "err" ||
      health === "error" ||
      health === "fault" ||
      health === "failed"
    ) {
      return whyRaw ? whyRaw.slice(0, 42) : "last run failed";
    }
    if (why.indexOf("skip") >= 0) {
      const qn = parseReadyQueueDepth(w);
      return qn > 0 ? "last fire skipped" : "no ready work";
    }
    /* pc-922: last_shift when health/why silent (light scene) */
    const ls = workerLastShift(w);
    if (ls) {
      const oc = String(ls.outcome || "").toLowerCase();
      const reason = renderedActivityCopy(ls.reason || "").trim();
      const when = shortShiftWhen(ls.ts);
      if (oc === "vendor_limit") {
        return (
          "vendor limit" +
          (reason ? " · " + reason.replace(/^vendor limit:\s*/i, "").slice(0, 28) : "") +
          (when ? " · " + when : "")
        ).slice(0, 64);
      }
      if (oc === "error" || oc === "err" || oc === "fault" || oc === "failed" || oc === "crashed") {
        return (
          (reason ? reason.slice(0, 36) : "last run failed") +
          (when ? " · " + when : "")
        ).slice(0, 64);
      }
      if (oc === "skip" || oc === "skipped") {
        const qn = parseReadyQueueDepth(w);
        if (reason.toLowerCase().indexOf("queue empty") >= 0 || qn <= 0)
          return ("no ready work" + (when ? " · " + when : "")).slice(0, 64);
        return (
          "last fire skipped" +
          (reason ? " · " + reason.slice(0, 28) : "") +
          (when ? " · " + when : "")
        ).slice(0, 64);
      }
    }
    return "";
  }

  /**
   * pc-689: idle/due meta — ready · N and/or amber/skip hint (never empty-as-idle lie).
   * Pure — mirrored in tests/test_map_agent_queue_hint.py.
   */
  function composeIdleAgentMeta(queueReady, statusHint, skipped) {
    if (skipped) return "Skipped this check only";
    const bits = [];
    const n = queueReady | 0;
    if (n > 0) bits.push(n + " ready in lane");
    const hint = String(statusHint || "").trim();
    if (hint) bits.push(hint);
    return bits.join(" · ");
  }

  /**
   * Engine noise that must never paint as a citizen "work line"
   * (e.g. bare "light", single-token effort tags, empty markers).
   */
  function isJunkActivityCopy(s) {
    const t = String(s || "")
      .trim()
      .toLowerCase();
    if (!t) return true;
    if (t.length <= 8 && !/\s/.test(t)) {
      /* bare tokens: light · dark · ok · err · skip · run · job … */
      if (
        /^(light|dark|ok|err|error|skip|run|job|idle|live|busy|dim|none|n\/a|na|—|-)$/.test(
          t
        )
      )
        return true;
    }
    if (/^(model|cli|vendor)\b/.test(t)) return true;
    return false;
  }

  /** Citizen rewrite of last-run / activity engine copy. */
  function citizenActivityLine(raw) {
    const why = renderedActivityCopy(raw || "").trim();
    if (!why || isJunkActivityCopy(why)) return "";
    const low = why.toLowerCase();
    if (low.indexOf("queue empty") >= 0) return "Nothing ready in lane";
    if (low.indexOf("no ready") >= 0) return "Nothing ready in lane";
    if (low.indexOf("last desk run skip") >= 0 || low.indexOf("last queue run skip") >= 0)
      return "Last check · nothing ready";
    if (low.indexOf("last desk run ok") >= 0 || low.indexOf("last queue run ok") >= 0)
      return "Last check · ok";
    if (low.indexOf("error") >= 0 || low.indexOf("agent exit") >= 0)
      return "Last run failed · " + why.replace(/^last (desk|queue) run\s*/i, "").slice(0, 40);
    if (low.indexOf("skip") >= 0) return "Last check skipped";
    if (low.indexOf("claim") >= 0) return why.slice(0, 64);
    if (low.indexOf("close") >= 0 || low.indexOf("done") >= 0) return why.slice(0, 64);
    if (low.indexOf("check") >= 0 || low.indexOf("queue") >= 0) return why.slice(0, 64);
    /* Prefer known action phrases; drop opaque one-word leftovers */
    if (why.length < 12 && why.indexOf(" ") < 0) return "";
    return why.slice(0, 64);
  }

  /**
   * pc-1067: off-shift held claim line (idle hand still owns IP/IR).
   * Distinct from live "Working on …" — useful for stranded-claim triage.
   * Pure join: WF holding[] first, then Desk Owner map.
   */
  function heldClaimLineFromParts(w, ownerByHand) {
    if (!w) return "";
    const held = w.holding || [];
    if (held.length) {
      const h0 = held[0];
      const id =
        typeof digTicketId === "function"
          ? digTicketId(h0)
          : (h0 && (h0.id || h0.task_id)) || "";
      if (id) return "Holding " + id + " · resumes next shift";
    }
    const hand = String(w.name || "")
      .trim()
      .toLowerCase();
    const owned =
      hand && ownerByHand && typeof ownerByHand === "object"
        ? ownerByHand[hand]
        : null;
    if (owned && owned.id) {
      return "Holding " + owned.id + " · resumes next shift";
    }
    return "";
  }

  /** Pure join used by liveWorkLine + tests — holding first, then owner map. */
  function liveWorkLineFromParts(w, ownerByHand, opts) {
    if (!w) return "On shift";
    opts = opts || {};
    const stale = !!opts.stale;
    const held = w.holding || [];
    if (held.length) {
      const h0 = held[0];
      const id =
        typeof digTicketId === "function" ? digTicketId(h0) : h0 && h0.id;
      const title =
        typeof digTicketTitle === "function"
          ? digTicketTitle(h0)
          : (h0 && h0.title) || "";
      const more = held.length > 1 ? " (+" + (held.length - 1) + ")" : "";
      if (id && title) {
        return (
          "Working on " +
          id +
          " · " +
          String(title).slice(0, 42) +
          more
        );
      }
      if (id) return "Working on " + id + more;
      if (title) return "Working on " + String(title).slice(0, 48) + more;
      return "Working on a work order" + more;
    }
    const hand = String(w.name || "")
      .trim()
      .toLowerCase();
    const owned =
      hand && ownerByHand && typeof ownerByHand === "object"
        ? ownerByHand[hand]
        : null;
    if (owned && owned.id) {
      const ot = String(owned.title || "").trim();
      if (ot) return "Working on " + owned.id + " · " + ot.slice(0, 42);
      return "Working on " + owned.id;
    }
    /* pc-1067: stale tab must not invent "no work order yet" from dead data */
    if (stale) return "Stale · last known";
    const citizen = citizenActivityLine(
      w.why || w.status_detail || w.activity || ""
    );
    if (citizen) return citizen;
    if (w.kind === "job" || (typeof actorIsJob === "function" && actorIsJob(w)))
      return "Running scheduled job";
    return "On shift · no work order yet";
  }

  /**
   * Empty-check shift? queue-empty / no-ready skips — noise, not "real work".
   * Preflight skips (low disk, CLI missing) stay meaningful at 0 passes (pc-1378).
   */
  function isEmptyCheckShift(s) {
    if (!s) return true;
    const outcome = String(s.outcome || "").toLowerCase();
    const reason = String(s.reason || "").toLowerCase();
    const passes = s.passes != null ? s.passes | 0 : 0;
    if (outcome === "skip" || outcome === "skipped") {
      return reason.indexOf("queue empty") >= 0 || reason.indexOf("no ready") >= 0;
    }
    if (outcome === "ok" && passes <= 0 && reason.indexOf("queue empty") >= 0)
      return true;
    return false;
  }

  function isMeaningfulShift(s) {
    if (!s) return false;
    if (isEmptyCheckShift(s)) return false;
    const outcome = String(s.outcome || "").toLowerCase();
    if (!outcome || outcome === "?" || outcome === "running") return false;
    return true;
  }

  /** Citizen label for a shift row. */
  function citizenShiftLabel(s) {
    if (!s) return "—";
    const outcome = String(s.outcome || "").toLowerCase();
    const passes = s.passes != null ? s.passes | 0 : null;
    const reason = renderedActivityCopy(s.reason || "").trim();
    if (outcome === "ok" || outcome === "success" || outcome === "done") {
      if (passes != null && passes > 0)
        return "Finished · " + passes + " pass" + (passes === 1 ? "" : "es");
      return "Finished · ok";
    }
    if (outcome === "vendor_limit") {
      const short = reason
        ? reason.replace(/^vendor limit:\s*/i, "").slice(0, 32)
        : "";
      return "Vendor limit" + (short ? " · " + short : "");
    }
    if (
      outcome === "error" ||
      outcome === "err" ||
      outcome === "fault" ||
      outcome === "failed" ||
      outcome === "crashed"
    ) {
      return "Failed" + (reason ? " · " + reason.slice(0, 36) : "");
    }
    if (outcome === "skip" || outcome === "skipped") {
      if (reason.toLowerCase().indexOf("queue empty") >= 0)
        return "Checked · nothing ready";
      return "Skipped" + (reason ? " · " + reason.slice(0, 36) : "");
    }
    if (outcome === "running") return "On shift";
    return (
      String(s.outcome || "?") +
      (passes != null ? " · " + passes + " pass" : "")
    );
  }

  /**
   * pc-922: terminal fail/skip last_shift that should rise on Agent activities.
   * Not empty-check noise only — vendor_limit / agent exit / lock skip count.
   */
  function lastShiftRailKind(ls) {
    if (!ls) return "";
    const oc = String(ls.outcome || "").toLowerCase();
    if (oc === "vendor_limit") return "fail";
    if (
      oc === "error" ||
      oc === "err" ||
      oc === "fault" ||
      oc === "failed" ||
      oc === "crashed"
    )
      return "fail";
    if (oc === "skip" || oc === "skipped") {
      const reason = String(ls.reason || "").toLowerCase();
      /* queue-empty skip is still first-class (honest idle), lower heat */
      if (reason.indexOf("queue empty") >= 0 || reason.indexOf("no ready") >= 0)
        return "skip_empty";
      return "skip";
    }
    return "";
  }

  /**
   * Extract a ticket id from a shift / activity record when present.
   * Used so "last real work" can show Working on pc-xxx, not only outcome.
   */
  function digShiftTicketId(s) {
    if (!s || typeof s !== "object") return "";
    const cands = [
      s.ticket_id,
      s.task_id,
      s.tid,
      s.work_order,
      s.wo,
      s.holding_id,
      s.claimed,
    ];
    for (let i = 0; i < cands.length; i++) {
      const v = String(cands[i] || "").trim();
      if (v && /^[a-z]{1,12}-\d+/i.test(v)) return v;
    }
    const blob = String(
      s.reason || s.why || s.activity || s.summary || s.note || ""
    );
    const m = blob.match(/\b([a-z]{1,12}-\d+)\b/i);
    return m ? m[1] : "";
  }

  /**
   * Partition shifts: meaningful first, empty checks collapsed to a count.
   * Pure — dig person panel + idle "last real work" hero (pc-813 / pc-964).
   * Trailing empty streak only (newest until first real) for "since" line.
   */
  function partitionShiftHistory(shifts, maxMeaningful) {
    const list = Array.isArray(shifts) ? shifts : [];
    const meaningful = [];
    let emptyN = 0;
    let lastEmpty = null;
    let firstEmpty = null;
    let lastRealTicket = "";
    let seenReal = false;
    for (let i = 0; i < list.length; i++) {
      const s = list[i];
      if (isMeaningfulShift(s)) {
        seenReal = true;
        if (meaningful.length < (maxMeaningful || 6)) meaningful.push(s);
        if (!lastRealTicket) {
          lastRealTicket = digShiftTicketId(s);
        }
      } else if (s && isEmptyCheckShift(s)) {
        if (!seenReal) {
          emptyN++;
          if (!lastEmpty) lastEmpty = s;
          firstEmpty = s;
        }
      } else if (s) {
        /* non-empty unknown — treat as meaningful (fail-safe visibility) */
        seenReal = true;
        if (meaningful.length < (maxMeaningful || 6)) meaningful.push(s);
      }
    }
    return {
      meaningful: meaningful,
      emptyN: emptyN,
      lastEmpty: lastEmpty,
      firstEmpty: firstEmpty,
      lastRealTicket: lastRealTicket,
    };
  }

  /** Failed / vendor / crash — dig attention class (pc-964; never collapse). */
  function isFailShift(s) {
    if (!s) return false;
    const oc = String(s.outcome || "").toLowerCase();
    return (
      oc === "error" ||
      oc === "err" ||
      oc === "fault" ||
      oc === "failed" ||
      oc === "crashed" ||
      oc === "vendor_limit"
    );
  }

  /**
   * Build hand → claim index from IP/IR task lists (pc-526 / pc-1054).
   * Pure — hand (lowercase) → { id, title, _u }.
   */
  function indexDeskOwnersFromTasks(taskLists) {
    const by = {};
    const lists = taskLists || [];
    for (let li = 0; li < lists.length; li++) {
      const tasks = lists[li] || [];
      for (let i = 0; i < tasks.length; i++) {
        const t = tasks[i];
        if (!t) continue;
        const id = String(t.id || t.task_id || "").trim();
        if (!id) continue;
        const u = Date.parse(t.updated_at || t.updated || "") || 0;
        const title = String(t.title || "").trim();
        /* Keys: desk Owner: (with_preview) + worker:<hand> labels (pc-1054).
           Labels stay on the light wire; Owner alone misses hand seats when
           claim signed as host/you. */
        const keys = [];
        const own = String(t.owner || "")
          .trim()
          .toLowerCase();
        if (own) keys.push(own);
        const labs = t.labels || [];
        for (let j = 0; j < labs.length; j++) {
          const lab = String(labs[j] || "")
            .trim()
            .toLowerCase();
          if (lab.indexOf("worker:") !== 0) continue;
          const hand = lab.slice("worker:".length);
          if (hand && keys.indexOf(hand) < 0) keys.push(hand);
        }
        if (!keys.length) continue;
        for (let k = 0; k < keys.length; k++) {
          const key = keys[k];
          const prev = by[key];
          if (!prev || u >= (prev._u || 0)) {
            by[key] = { id: id, title: title, _u: u };
          }
        }
      }
    }
    return by;
  }

  /**
   * pc-1067: tid → preferred seat hand (worker:* over youish Owner).
   * Pure — used for CLAIMED chip attribution on WO slips.
   */
  function indexDeskHoldersByTid(taskLists) {
    const byTid = {};
    const lists = taskLists || [];
    for (let li = 0; li < lists.length; li++) {
      const tasks = lists[li] || [];
      for (let i = 0; i < tasks.length; i++) {
        const t = tasks[i];
        if (!t) continue;
        const id = String(t.id || t.task_id || "").trim();
        if (!id) continue;
        const u = Date.parse(t.updated_at || t.updated || "") || 0;
        const seat = seatHandFromTask(t);
        if (!seat || isYouishSeat(seat)) continue;
        const prev = byTid[id];
        if (!prev || u >= (prev._u || 0)) {
          byTid[id] = { hand: seat, _u: u };
        }
      }
    }
    return byTid;
  }

  /**
   * pc-1204: apply event holds onto a fresh strip index so lagging hops cannot
   * re-poison close drops or erase a just-warmed claim seat.
   */
  function applyDeskOwnerEventHolds(byHand, byTid) {
    const now = Date.now();
    const hand = byHand || {};
    const tidMap = byTid || {};
    Object.keys(_deskOwnerTombstone).forEach(function (id) {
      if (now > (_deskOwnerTombstone[id] || 0)) {
        delete _deskOwnerTombstone[id];
        return;
      }
      /* Strip still lists tid → keep tombstone and suppress; gone → release */
      if (tidMap[id]) {
        delete tidMap[id];
      } else {
        delete _deskOwnerTombstone[id];
      }
      Object.keys(hand).forEach(function (h) {
        const row = hand[h];
        if (row && String(row.id) === id) delete hand[h];
      });
    });
    Object.keys(_deskOwnerWarm).forEach(function (h) {
      const w = _deskOwnerWarm[h];
      if (!w || now > (w.until || 0)) {
        delete _deskOwnerWarm[h];
        return;
      }
      const id = String(w.id || "").trim();
      if (!id) {
        delete _deskOwnerWarm[h];
        return;
      }
      /* Closed wins over warm for same tid */
      if (_deskOwnerTombstone[id] && now <= _deskOwnerTombstone[id]) {
        delete _deskOwnerWarm[h];
        return;
      }
      const stripHas = tidMap[id] && tidMap[id].hand === h;
      if (stripHas) {
        /* Board caught up — release warm hold */
        delete _deskOwnerWarm[h];
        return;
      }
      hand[h] = {
        id: id,
        title: String(w.title || id).trim().slice(0, 96),
        _u: w._u || now,
      };
      tidMap[id] = { hand: h, _u: w._u || now };
    });
    return { byHand: hand, byTid: tidMap };
  }

  /**
   * pc-1204: optimistic claim warm — CLAIMED · hand + Holding join before
   * the next live-strip hop / 12s TTL alone.
   * @returns {boolean} whether maps changed
   */
  function warmDeskOwnerClaim(hand, tid, title) {
    const h = String(hand || "")
      .trim()
      .toLowerCase();
    const id = String(tid || "").trim();
    if (!h || isYouishSeat(h) || !id) return false;
    /* A close for this tid must win */
    delete _deskOwnerTombstone[id];
    const u = Date.now();
    _deskOwnerWarm[h] = {
      id: id,
      title: String(title || id).trim().slice(0, 96),
      _u: u,
      until: u + DESK_OWNER_EVENT_HOLD_MS,
    };
    let changed = false;
    const prev = _deskOwnerByHand[h];
    if (!prev || String(prev.id) !== id) {
      _deskOwnerByHand[h] = {
        id: id,
        title: String(title || id).trim().slice(0, 96),
        _u: u,
      };
      changed = true;
    } else if (title && prev.title !== String(title).trim().slice(0, 96)) {
      prev.title = String(title).trim().slice(0, 96);
      prev._u = u;
      changed = true;
    }
    const prevT = _deskHolderByTid[id];
    if (!prevT || prevT.hand !== h) {
      _deskHolderByTid[id] = { hand: h, _u: u };
      changed = true;
    }
    /* Do not advance _deskOwnerAt — force strip still needed for full truth */
    return changed;
  }

  /**
   * pc-1204: drop closed/canceled tid so Holding face + CLAIMED holder do not
   * stick until Desk Owner TTL alone.
   * @returns {boolean} whether maps changed
   */
  function dropDeskOwnerTid(tid) {
    const id = String(tid || "").trim();
    if (!id) return false;
    const now = Date.now();
    _deskOwnerTombstone[id] = now + DESK_OWNER_EVENT_HOLD_MS;
    /* Cancel any warm that points at this tid */
    Object.keys(_deskOwnerWarm).forEach(function (h) {
      const w = _deskOwnerWarm[h];
      if (w && String(w.id) === id) delete _deskOwnerWarm[h];
    });
    let changed = false;
    if (_deskHolderByTid[id]) {
      delete _deskHolderByTid[id];
      changed = true;
    }
    Object.keys(_deskOwnerByHand).forEach(function (h) {
      const row = _deskOwnerByHand[h];
      if (row && String(row.id) === id) {
        delete _deskOwnerByHand[h];
        changed = true;
      }
    });
    /* Invalidate TTL so next paint / force path re-fetches strip truth */
    _deskOwnerAt = 0;
    return changed;
  }

  function refreshDeskOwnerIndex(force, onDone) {
    const now = Date.now();
    if (
      !force &&
      now - _deskOwnerAt < DESK_OWNER_TTL_MS &&
      _deskOwnerAt > 0
    ) {
      /* Cache warm — no fetch; onDone(by, changed=false) so callers skip re-paint */
      if (typeof onDone === "function") onDone(_deskOwnerByHand, false);
      return;
    }
    if (_deskOwnerLoading) {
      /* pc-1204: claim/close force must not lose to an in-flight pre-event hop */
      if (force) _deskOwnerForceQueued = true;
      if (typeof onDone === "function") onDone(_deskOwnerByHand, false);
      return;
    }
    _deskOwnerLoading = true;
    /* pc-934: one live-strip hop (not parallel status fan-out) */
    (H("fetchLiveStrip") || function () { return Promise.reject(new Error("no fetchLiveStrip")); })("open", 100)
      .then(function (strip) {
        const by = (strip && strip.by_status) || {};
        const parts = [by.in_progress || [], by.in_review || []];
        let next = indexDeskOwnersFromTasks(parts);
        let nextTid = indexDeskHoldersByTid(parts);
        /* pc-1204: merge event holds after strip so lag cannot re-poison */
        const held = applyDeskOwnerEventHolds(next, nextTid);
        next = held.byHand;
        nextTid = held.byTid;
        const prevSig =
          JSON.stringify(_deskOwnerByHand) +
          "|" +
          JSON.stringify(_deskHolderByTid);
        const nextSig = JSON.stringify(next) + "|" + JSON.stringify(nextTid);
        _deskOwnerByHand = next;
        _deskHolderByTid = nextTid;
        _deskOwnerAt = Date.now();
        _deskOwnerLoading = false;
        const changed = prevSig !== nextSig;
        if (typeof onDone === "function") onDone(_deskOwnerByHand, changed);
        /* Drain force queued while this hop was in flight (pc-1204) */
        if (_deskOwnerForceQueued) {
          _deskOwnerForceQueued = false;
          refreshDeskOwnerIndex(true);
        }
      })
      .catch(function () {
        _deskOwnerLoading = false;
        if (typeof onDone === "function") onDone(_deskOwnerByHand, false);
        if (_deskOwnerForceQueued) {
          _deskOwnerForceQueued = false;
          refreshDeskOwnerIndex(true);
        }
      });
  }


  /**
   * paint — Agent activities rail (roster + cards).
   * @param {object} ctx city/people/att/tpScene (+ optional repaint hooks)
   */
  function paint(ctx) {
    ctx = ctx || {};
    const city = ctx.city;
    const people = ctx.people;
    const att = ctx.att;
    const tpScene = ctx.tpScene;
    const liveList = document.getElementById("map-live-list");
    const liveEmpty = document.getElementById("map-live-empty");
    const inflight = (people && people.in_flight) || [];
    const inflightSet = {};
    inflight.forEach(function (n) {
      if (n) inflightSet[n] = true;
    });
    // Local aliases so extracted paint body can call host helpers
    const actorRoleTitle = function (w) {
      var f = H("actorRoleTitle");
      return f ? f(w) : String((w && (w.role || w.title)) || "");
    };
    const actorIsJob = function (w) {
      var f = H("actorIsJob");
      return f ? !!f(w) : !!(w && w.kind === "job");
    };
    const tierOf = function (w) {
      var f = H("tierOf");
      return f ? f(w) : actorIsJob(w) ? "job" : "agent";
    };
    const workerColor = function (name) {
      var f = H("workerColor");
      return f ? f(name) : "#6b6154";
    };
    const nextFireMs = function (w) {
      var f = H("nextFireMs");
      return f ? f(w) : NaN;
    };
    const handPeekProgress = function (w) {
      var f = H("handPeekProgress");
      return f ? f(w) : 0;
    };
    const dispatchWalkProgress = function (w) {
      var f = H("dispatchWalkProgress");
      return f ? f(w) : 0;
    };
    const isSkippedRound = function (w) {
      var f = H("isSkippedRound");
      return f ? !!f(w) : false;
    };
    const fmtCountdown = function (ms) {
      var f = H("fmtCountdown");
      return f ? f(ms) : "";
    };
    const getHandGlyph = function (id) {
      var f = H("getHandGlyph");
      return f ? f(id) : "✋";
    };
    const getStaffGlyph = function (id) {
      var f = H("getStaffGlyph");
      return f ? f(id) : "👔";
    };
    const getJobGlyph = function (id) {
      var f = H("getJobGlyph");
      return f ? f(id) : "⏰";
    };
    const applyMapNodeStageFlag = function () {
      var f = H("applyMapNodeStageFlag");
      if (f) f();
    };
    const paintMapMast = function (c) {
      var f = H("paintMapMast");
      if (f) f(c);
    };
    const requestSkipRound = function (name, nf, btn) {
      var f = H("requestSkipRound");
      if (f) f(name, nf, btn);
    };
    const selectMapEntity = function (ent) {
      var f = H("selectMapEntity");
      if (f) f(ent);
    };
    const inspectPerson = function (w) {
      var f = H("inspectPerson");
      if (f) f(w);
    };
    const wireMapEntityPreview = function (el, fn) {
      var f = H("wireMapEntityPreview");
      if (f) f(el, fn);
    };
    const clearMapEntityPreviewKind = function (k) {
      var f = H("clearMapEntityPreviewKind");
      if (f) f(k);
    };
    const syncMapEntitySelection = function () {
      var f = H("syncMapEntitySelection");
      if (f) f();
    };
    const isDigFocusSlug = function (s) {
      var f = H("isDigFocusSlug");
      return f ? !!f(s) : false;
    };
    const mapDigIn = (function () { var g = H("getMapDigIn"); return g ? g() : null; })();
    const model = (function () { var g = H("getModel"); return g ? g() : null; })();
    /*
     * pc-526 / pc-1067: always refresh Desk Owner index (TTL-gated).
     * Needed for LIVE work lines when WF holding[] is empty AND for off-shift
     * held claims (idle hand still owns IP/IR) + CLAIMED chip holder map.
     * Re-paint once when the index lands (async) so the rail updates in-poll.
     */
    refreshDeskOwnerIndex(false, function (_by, changed) {
      if (!changed) return;
      try {
        if (_ownerRepaint) return;
        _ownerRepaint = true;
        paintMapInsights(
          _lastCityData || city,
          _lastPeople || people,
          _lastAtt || att,
          _lastTpScene || tpScene
        );
        _ownerRepaint = false;
      } catch (eOwn) {
        _ownerRepaint = false;
      }
    });

    /*
     * Agent activities — full roster, three densities:
     *   idle (S) · approach/due (M) · live (L + work line)
     * Citizen copy: never teach “walk”; motion stays on the stage.
     */
    const ROSTER_CAP = 100;
    const motionRows = [];
    const seenMotion = {};
    function homeLabel(w) {
      const hk = String((w && w.homeKey) || "");
      if (!hk || hk.indexOf("__") === 0) return "";
      if (hk.charAt(0) === "/" || hk.charAt(0) === "~") return "";
      return hk.slice(0, 14);
    }
    /**
     * What a live hand/job is doing — ticket id/title, why, or plain status.
     * pc-526: holding → Desk Owner IP/IR join → useful why → unclaimed copy.
     */
    function liveWorkLine(w) {
      return liveWorkLineFromParts(w, _deskOwnerByHand, {
        stale: isMapDataStale(),
      });
    }
    /** pc-1067: idle/off-shift held claim (not live Working on). */
    function heldClaimLine(w) {
      return heldClaimLineFromParts(w, _deskOwnerByHand);
    }
    function pushRoster(w, kind, meta, rank, opts) {
      if (!w || !w.name || seenMotion[w.name]) return;
      seenMotion[w.name] = true;
      opts = opts || {};
      const role =
        typeof actorRoleTitle === "function"
          ? actorRoleTitle(w)
          : String(
              w.role ||
                w.title ||
                w.job_title ||
                w.skill ||
                (w.kind === "job" ? "job" : "") ||
                ""
            ).trim();
      const nf = opts.nextFire != null ? opts.nextFire : w.next_fire || "";
      let remainMs = opts.remainMs;
      if (remainMs == null || !isFinite(remainMs)) {
        const t = nextFireMs(w);
        remainMs = isFinite(t) ? t - Date.now() : NaN;
      }
      const home = homeLabel(w);
      /* density: idle | med | live */
      let density = "med";
      if (kind === "idle") density = "idle";
      else if (kind === "live") density = "live";
      else density = "med"; /* walk, peek, due */
      /* pc-497: model pin + CLI for rail payroll line (roster grammar) */
      let modelPin = String(w.model || "").trim();
      if (modelPin === "default") modelPin = "";
      const cliPin = String(w.cli || "").trim();
      const workLine = opts.work || "";
      const ls = opts.lastShift || null;
      const lsKey = ls
        ? String(ls.ts || "") + "|" + String(ls.outcome || "") + "|" + String(ls.reason || "")
        : "";
      /* pc-696/pc-922: hash facts only — relative "Xm ago" tails tick every
       * minute and must not read as a state change (idle rows re-floating). */
      const stateSig =
        kind +
        "|" +
        stripRelWhen(workLine) +
        "|" +
        stripRelWhen(opts.statusHint || "") +
        "|" +
        String(opts.health || "") +
        "|" +
        (opts.skipped ? "1" : "0") +
        "|" +
        lsKey; /* pc-922: fail/skip pulse when ledger advances */
      const nm = String(w.name || "");
      let lastAt = _agentActivityAt[nm] || 0;
      let isStateNew = false;
      if (_agentActivitySig[nm] !== stateSig) {
        isStateNew = !!_agentActivitySig[nm]; /* first paint: no beat */
        /* First sighting is not a change — a boot-hot roster scrambles the
         * within-band countdown order for the first 45s. */
        lastAt = isStateNew ? Date.now() : 0;
        _agentActivitySig[nm] = stateSig;
        _agentActivityAt[nm] = lastAt;
      }
      motionRows.push({
        name: w.name,
        display: w.display || w.name,
        home: w.homeKey || "",
        homeShort: home,
        entitySlug:
          w.workspaceOps ||
          w.homeKey === "__staff__" ||
          String(w.homeKey || "").indexOf("__") === 0
            ? "__you__"
            : w.homeKey || "",
        kind: kind,
        density: density,
        meta: meta,
        work: workLine,
        rank: rank,
        remainMs: remainMs,
        progress: opts.progress != null ? opts.progress : 0,
        nextFire: nf,
        role: role,
        model: modelPin,
        cli: cliPin,
        idle: kind === "idle",
        skipped: !!opts.skipped,
        canSkip: kind === "walk" || kind === "peek",
        queueReady: opts.queueReady != null ? opts.queueReady | 0 : 0,
        statusHint: opts.statusHint || "",
        health: opts.health || "",
        lastShift: ls,
        shiftRail: opts.shiftRail || "",
        lastChangeAt: lastAt,
        isStateNew: isStateNew,
        isJob: !!(
          w.kind === "job" ||
          (typeof actorIsJob === "function" && actorIsJob(w))
        ),
        isStaff: !!(w.staff === true || w.staff === "true" || w.staff === 1),
        tier: typeof tierOf === "function" ? tierOf(w) : (actorIsJob(w) ? "job" : "agent"),
        color:
          w.color ||
          (typeof workerColor === "function" ? workerColor(w.name) : "#6b6154"),
      });
    }
    const pool =
      model && model.workers && model.workers.length
        ? model.workers
        : [];
    pool.forEach(function (w) {
      if (!w || w.kind === "citizen") return;
      const home = homeLabel(w);
      const working = !!(w.working || inflightSet[w.name]);
      const queueReady = parseReadyQueueDepth(w);
      const statusHint = citizenHandStatusHint(w);
      const healthStr = String(w.health || "").trim();
      const ls = workerLastShift(w);
      const shiftRail = lastShiftRailKind(ls);
      const lsOpts = {
        lastShift: ls,
        shiftRail: shiftRail,
        queueReady: queueReady,
        statusHint: statusHint,
        health: healthStr,
      };
      if (working) {
        /* live: project on role line; work line carries action (not project) */
        pushRoster(w, "live", "", 0, Object.assign({ progress: 1, work: liveWorkLine(w) }, lsOpts));
        return;
      }
      /* pc-555: Skip this round — suppress Approaching until fire advances */
      if (isSkippedRound(w)) {
        pushRoster(
          w,
          "idle",
          "Skipped this round",
          4,
          Object.assign(
            {
              progress: 0,
              nextFire: w.next_fire,
              work: "",
              skipped: true,
            },
            lsOpts
          )
        );
        return;
      }
      /*
       * pc-922: terminal fail/skip is first-class on the rail (not silent idle).
       * Fail rises above due/approach so away-session honesty wins.
       */
      if (shiftRail === "fail" && ls) {
        const lab = citizenShiftLabel(ls);
        const when = shortShiftWhen(ls.ts);
        const heldFail = heldClaimLine(w);
        pushRoster(
          w,
          "idle",
          lab,
          0.25,
          Object.assign(
            {
              progress: 0,
              nextFire: w.next_fire,
              /* pc-1067: stranded claim beats last-fail alone */
              work: heldFail || lab + (when ? " · " + when : ""),
            },
            lsOpts
          )
        );
        return;
      }
      if (shiftRail === "skip" && ls) {
        const lab = citizenShiftLabel(ls);
        const when = shortShiftWhen(ls.ts);
        const heldSkip = heldClaimLine(w);
        pushRoster(
          w,
          "idle",
          lab,
          1.5,
          Object.assign(
            {
              progress: 0,
              nextFire: w.next_fire,
              work: heldSkip || lab + (when ? " · " + when : ""),
            },
            lsOpts
          )
        );
        return;
      }
      const peekP = handPeekProgress(w);
      if (peekP > 0) {
        const nf = nextFireMs(w);
        const remain = isFinite(nf) ? nf - Date.now() : NaN;
        /* meta = status only — project is .hand-role (pc-474) */
        pushRoster(
          w,
          "peek",
          "Checking queue",
          0.5,
          Object.assign(
            {
              progress: 1,
              remainMs: remain,
              nextFire: w.next_fire,
              work: "Checking queue for ready work",
            },
            lsOpts
          )
        );
        return;
      }
      const walkP = dispatchWalkProgress(w);
      if (walkP > 0) {
        const nf = nextFireMs(w);
        const remain = isFinite(nf) ? nf - Date.now() : NaN;
        const pct = Math.round(Math.min(1, Math.max(0, walkP)) * 100);
        /* Approaching · N% — never repeat project slug in meta */
        pushRoster(
          w,
          "walk",
          "Approaching · " + pct + "%",
          1,
          Object.assign(
            {
              progress: walkP,
              remainMs: remain,
              nextFire: w.next_fire,
            },
            lsOpts
          )
        );
        return;
      }
      const nf = nextFireMs(w);
      if (isFinite(nf)) {
        const remain = nf - Date.now();
        if (remain > 0 && remain <= 15 * 60 * 1000) {
          /* Due: project once on role; pill = countdown; no meta project */
          pushRoster(
            w,
            "due",
            "",
            2,
            Object.assign(
              {
                progress: 0,
                remainMs: remain,
                nextFire: w.next_fire,
              },
              lsOpts
            )
          );
          return;
        }
      }
      /* Idle — ready · N / last outcome in meta (pc-689/pc-922); pill idle or fail.
       * pc-1067: off-shift held IP/IR claim is primary ("Holding pc-… · resumes next shift").
       * pc-1174 / §9: last real ticket next (never let empty SKIP masquerade as last work).
       * pc-1203: Holding rank above true idle / last-real (not grey idle pile). */
      let idleWork = heldClaimLine(w);
      if (!idleWork) {
        idleWork = lastRealWorkLine(w);
      }
      if (!idleWork && shiftRail === "skip_empty" && ls) {
        /* Honest empty-check only when no real work is known */
        idleWork = citizenShiftLabel(ls);
        if (ls.ts) idleWork += " · " + shortShiftWhen(ls.ts);
      }
      const holdingIdle =
        !!(idleWork && /^Holding\b/i.test(String(idleWork)));
      pushRoster(
        w,
        "idle",
        home || (w.kind === "job" ? "job" : "on roster"),
        holdingIdle ? 3.5 : 5,
        Object.assign(
          {
            progress: 0,
            nextFire: w.next_fire,
            work: idleWork,
          },
          lsOpts
        )
      );
    });
    /* Fallback: in_flight names not yet on model.workers */
    inflight.forEach(function (name) {
      if (!name || seenMotion[name]) return;
      let display = name;
      let home = "";
      ((people && people.sectors) || []).forEach(function (sec) {
        (sec.workers || []).forEach(function (w) {
          if (w.name !== name) return;
          display = w.display || w.name || name;
          home =
            ((sec.workdir || "").split("/").pop() || sec.workplace || "") ||
            "";
        });
      });
      motionRows.push({
        name: name,
        display: display,
        home: home,
        kind: "live",
        meta: home ? "live · " + String(home).slice(0, 10) : "live",
        rank: 0,
        progress: 1,
        role: "",
        idle: false,
        isJob: false,
        color: typeof workerColor === "function" ? workerColor(name) : "#6b6154",
      });
    });
    /*
     * Live activity rank: recent status change first, then density rank.
     * pc-696: bucket remainMs (15s) so continuous countdown ticks do not
     * re-order the roster every poll (full list remount → left-rail flash).
     */
    function remainBucket(ms) {
      if (typeof ms !== "number" || !isFinite(ms) || ms <= 0) {
        return Number.POSITIVE_INFINITY;
      }
      return Math.floor(ms / 15000);
    }
    motionRows.sort(function (a, b) {
      /* Hierarchy first: live · fail · peek/walk · due · Holding · idle.
       * The hot pulse (recent state change) only re-orders within a band —
       * an idle row must never leapfrog live/approaching just because its
       * label refreshed. pc-1203: Holding rank (3.5) sits above true idle. */
      const ra = +a.rank || 0;
      const rb = +b.rank || 0;
      if (ra !== rb) return ra - rb;
      const now = Date.now();
      const aHot = now - (a.lastChangeAt || 0) < 45000 ? 1 : 0;
      const bHot = now - (b.lastChangeAt || 0) < 45000 ? 1 : 0;
      if (bHot !== aHot) return bHot - aHot;
      if (bHot && aHot) {
        const d = (b.lastChangeAt || 0) - (a.lastChangeAt || 0);
        if (d) return d;
      }
      /* pc-1203: within same rank, Holding work line before last-real / bare idle */
      const aHold = a.work && /^Holding\b/i.test(String(a.work)) ? 1 : 0;
      const bHold = b.work && /^Holding\b/i.test(String(b.work)) ? 1 : 0;
      if (bHold !== aHold) return bHold - aHold;
      /* pc-1027: idle band groups by tier (Agents · Staff · Jobs) so the
       * three-type split reads at a glance — tier BEFORE the countdown
       * bucket, else next_fire spread interleaves tiers (dup headers).
       * Activity bands (live/due) keep pure recency. */
      if (a.kind === "idle" && b.kind === "idle") {
        const tord = { agent: 0, staff: 1, job: 2 };
        const ta = tord[a.tier] !== undefined ? tord[a.tier] : 0;
        const tb = tord[b.tier] !== undefined ? tord[b.tier] : 0;
        if (ta !== tb) return ta - tb;
      }
      const ar = remainBucket(a.remainMs);
      const br = remainBucket(b.remainMs);
      if (ar !== br) return ar - br;
      return String(a.display || a.name || "").localeCompare(
        String(b.display || b.name || "")
      );
    });
    const liveN = motionRows.filter(function (r) {
      return r.kind === "live";
    }).length;
    const dueN = motionRows.filter(function (r) {
      return r.kind === "due" || r.kind === "walk" || r.kind === "peek";
    }).length;
    const idleN = motionRows.filter(function (r) {
      return r.kind === "idle";
    }).length;
    const motionN = motionRows.length;
    const rosterTotal = motionRows.length;
    /* Keep hierarchy stage class for bubble hands; never hide left-rail agents */
    try {
      const liveHost = document.getElementById("map-rail-live");
      if (liveHost) {
        liveHost.hidden = false;
        liveHost.removeAttribute("aria-hidden");
      }
      const agentsMod = document.getElementById("map-mod-agents");
      if (agentsMod) agentsMod.hidden = false;
      const stageEl = document.getElementById("stage");
      if (stageEl) {
        stageEl.classList.add("map-layout-hierarchy");
      }
      /* pc-540: suite.mapNode stage flag (no paint fork in Phase 1) */
      applyMapNodeStageFlag();
    } catch (eHide) {}

    /* Header: [FOLDER] workspace + quiet version chip · brand left · LIVE right */
    try {
      paintMapMast(city);
    } catch (eHead) {}

    /*
     * Dig / heat helpers used by census header + list paint (same scope).
     * pc-771: dig groups by home; workspace groups by heat + idle tier.
     */
    function handOnDigFocus(r) {
      if (!mapDigIn || !mapDigIn.plot) return true;
      const home = String(
        (r && (r.entitySlug || r.home || r.homeShort)) || ""
      ).trim();
      if (!home || home.indexOf("__") === 0) return false;
      if (typeof isDigFocusSlug === "function" && isDigFocusSlug(home)) {
        return true;
      }
      const leaf = home.split(/[/\\]/).filter(Boolean).pop() || home;
      return typeof isDigFocusSlug === "function"
        ? isDigFocusSlug(leaf)
        : false;
    }
    /**
     * Heat band for a row — Approaching (peek/walk) is hotter than Due.
     * fail → live → peek → walk → due → idle. Never let due rank above walk.
     */
    function heatBand(r) {
      if (!r) return "idle";
      if (r.shiftRail === "fail") return "fail";
      var k = String(r.kind || "idle");
      if (k === "live" || k === "peek" || k === "walk" || k === "due") return k;
      return "idle";
    }
    function rowRank(r) {
      var band = heatBand(r);
      var rmap = { fail: -1, live: 0, peek: 1, walk: 2, due: 3, idle: 4 };
      return rmap[band] != null ? rmap[band] : 9;
    }
    function withinBandSort(a, b) {
      var ar = remainBucket(a && a.remainMs);
      var br = remainBucket(b && b.remainMs);
      if (ar !== br) return ar - br;
      return String((a && (a.display || a.name)) || "").localeCompare(
        String((b && (b.display || b.name)) || "")
      );
    }
    /**
     * Hard partition — never hope-sort across bands. Guarantees:
     *   fail → live → peek → walk → due → idle(agent) → idle(staff) → idle(job)
     * Approaching (walk/peek) always above gold Due. Idle headers once per tier.
     */
    function partitionRoster(rows) {
      var fail = [];
      var live = [];
      var peek = [];
      var walk = [];
      var due = [];
      var idleAgent = [];
      var idleStaff = [];
      var idleJob = [];
      (rows || []).forEach(function (r) {
        if (!r) return;
        var band = heatBand(r);
        if (band === "fail") fail.push(r);
        else if (band === "live") live.push(r);
        else if (band === "peek") peek.push(r);
        else if (band === "walk") walk.push(r);
        else if (band === "due") due.push(r);
        else {
          var t = r.tier || "agent";
          if (t === "staff") idleStaff.push(r);
          else if (t === "job") idleJob.push(r);
          else idleAgent.push(r);
        }
      });
      fail.sort(withinBandSort);
      live.sort(withinBandSort);
      peek.sort(withinBandSort);
      walk.sort(withinBandSort);
      due.sort(withinBandSort);
      idleAgent.sort(withinBandSort);
      idleStaff.sort(withinBandSort);
      idleJob.sort(withinBandSort);
      return {
        fail: fail,
        live: live,
        peek: peek,
        walk: walk,
        due: due,
        idleAgent: idleAgent,
        idleStaff: idleStaff,
        idleJob: idleJob,
        onShift: live.concat(peek, walk, due),
        idleAll: idleAgent.concat(idleStaff, idleJob),
        ordered: fail
          .concat(live, peek, walk, due, idleAgent, idleStaff, idleJob),
      };
    }
    function sortByRowRank(rows) {
      return partitionRoster(rows).ordered;
    }
    /** Fingerprint of name order by heat band — remount if shells would drift. */
    function bandOrderSig(rows) {
      return partitionRoster(rows)
        .ordered.map(function (r) {
          return String(r.name || "") + ":" + heatBand(r);
        })
        .join(",");
    }
    function clearTierFoldClasses(listEl) {
      if (!listEl || !listEl.classList) return;
      listEl.classList.remove(
        "is-tier-collapsed-agent",
        "is-tier-collapsed-staff",
        "is-tier-collapsed-job"
      );
    }
    function setAgentRosterMode(listEl, digOpen) {
      if (!listEl || !listEl.classList) return;
      listEl.classList.toggle("is-dig-roster", !!digOpen);
      if (digOpen) {
        /* Workspace idle-fold CSS must not hide on-project idle seats. */
        clearTierFoldClasses(listEl);
      }
    }
    /** DOM card shells in list order (skip headers / empty placeholders). */
    function listAgentShells(listEl) {
      var out = [];
      if (!listEl) return out;
      Array.from(listEl.children).forEach(function (child) {
        if (
          child.dataset &&
          (child.dataset.separator ||
            (child.classList && child.classList.contains("rail-group-hd")))
        ) {
          return;
        }
        var wrap =
          child.querySelector && child.querySelector("[data-agent]");
        if (!wrap) return;
        out.push({ li: child, wrap: wrap, name: wrap.getAttribute("data-agent") || "" });
      });
      return out;
    }
    const digOpenCensus = !!(mapDigIn && mapDigIn.plot);
    const focusCensusRows = digOpenCensus
      ? motionRows.filter(handOnDigFocus)
      : motionRows;
    const elseCensusN = digOpenCensus
      ? motionRows.length - focusCensusRows.length
      : 0;

    /* Title total + shared summary line (mirrors Work orders open · done) */
    try {
      const subEl = document.getElementById("map-agents-sub");
      const totEl = document.getElementById("map-agents-total");
      function focusAgentActivitiesList() {
        const list = document.getElementById("map-live-list");
        if (!list) return;
        try {
          list.scrollIntoView({ block: "nearest", behavior: "smooth" });
        } catch (eList) {
          try {
            list.scrollIntoView(true);
          } catch (eListFallback) {}
        }
      }
      if (subEl) {
        /* pc-1027: tier counts lead — the three-type split at a glance;
         * status counts move to the tooltip.
         * Dig open: census is *this project* (same scope as On this project),
         * not the full workspace — otherwise header lies vs place groups. */
        const census = digOpenCensus ? focusCensusRows : motionRows;
        const tierCount = function (t) {
          return census.filter(function (r) {
            return (r.tier || "agent") === t;
          }).length;
        };
        const summaryLine =
          tierCount("agent") + " agents · " +
          tierCount("staff") + " staff · " +
          tierCount("job") + " jobs";
        if (subEl.textContent !== summaryLine) subEl.textContent = summaryLine;
        if (digOpenCensus) {
          const fLive = focusCensusRows.filter(function (r) {
            return r.kind === "live";
          }).length;
          const fDue = focusCensusRows.filter(function (r) {
            return r.kind === "due" || r.kind === "walk" || r.kind === "peek";
          }).length;
          const fIdle = focusCensusRows.filter(function (r) {
            return r.kind === "idle";
          }).length;
          /* Dig filters the rail — no "elsewhere" (map selection is the filter). */
          subEl.title =
            focusCensusRows.length +
            " on this project · " +
            fLive +
            " live · " +
            fDue +
            " due · " +
            fIdle +
            " idle";
        } else {
          subEl.title =
            liveN + " live · " + dueN + " due · " + idleN + " idle";
        }
      }
      if (totEl) {
        /* Dig: badge = seats on this project (matches place group count).
         * Workspace: full roster. */
        const t = String(
          digOpenCensus ? focusCensusRows.length : rosterTotal
        );
        if (totEl.textContent !== t) totEl.textContent = t;
        totEl.hidden = false;
        if (!totEl._countDoorWired) {
          totEl._countDoorWired = true;
          totEl.addEventListener("click", focusAgentActivitiesList);
        }
      }
    } catch (eSub) {}

    if (liveList && liveEmpty) {
      const agentsCap = document.getElementById("map-agents-cap");
      /* pc-1067: dim agent cards when polls/suite are stale (not only LIVE badge) */
      try {
        const agentsRail =
          document.getElementById("map-rail-live") || liveList.parentElement;
        if (agentsRail) {
          agentsRail.classList.toggle("is-data-stale", isMapDataStale());
        }
        liveList.classList.toggle("is-data-stale", isMapDataStale());
      } catch (eStaleCls) {}
      if (!motionRows.length) {
        liveList.hidden = true;
        liveList.innerHTML = "";
        liveEmpty.hidden = false;
        liveEmpty.textContent =
          "No hands or jobs yet — seed ops jobs below (chief-of-staff · health-patrol · workspace-efficiency)";
        if (agentsCap) {
          agentsCap.hidden = true;
          agentsCap.textContent = "";
        }
        _liveSig = "";
      } else {
        liveEmpty.hidden = true;
        liveList.hidden = false;
        const slice = motionRows.slice(0, ROSTER_CAP);
        if (agentsCap) {
          if (motionRows.length > ROSTER_CAP) {
            agentsCap.hidden = false;
            agentsCap.textContent =
              "Showing " +
              ROSTER_CAP +
              " of " +
              motionRows.length +
              " on roster";
          } else {
            agentsCap.hidden = true;
            agentsCap.textContent = "";
          }
        }
        /*
         * Live activity sig: ordered identity + structural state.
         * Soft-patch when stable. pc-696: do NOT include lastChangeAt —
         * it changed every state tick and forced full list remounts
         * (left-rail flash) even when name/kind/work were unchanged.
         * Order still re-ranks hot rows via sort; remount only when the
         * ordered structural string actually changes.
         */
        const digFocusSig = mapDigIn
          ? (mapDigIn.plot ? (mapDigIn.plot.slug || mapDigIn.plot.name || "dig") : "dig")
          : "";
        /*
         * liveSig: ordered identity + structural state (pc-696).
         * pc-943: include shiftRail + last outcome so vendor_limit / agent exit
         * soft-patch pills without full remount thrash on timestamps alone.
         * Home + tier: dig place-split and idle tier headers must remount when
         * a seat is re-homed or re-tiered (not only when kind/work flips).
         * bandOrder: name:heatBand in render order — remount when Approaching
         * moves above Due or a seat crosses idle↔on-shift (soft-patch must not
         * freeze shells in the wrong band).
         */
        const dataStaleBit = isMapDataStale() ? "1" : "0";
        const bandSig = bandOrderSig(slice);
        const liveSig =
          "stale:" +
          dataStaleBit +
          "|band:" +
          bandSig +
          "|" +
          slice
            .map(function (r) {
              const oc = String(
                (r.lastShift && r.lastShift.outcome) || ""
              ).slice(0, 16);
              const homeBit = String(
                (r && (r.entitySlug || r.home || r.homeShort)) || ""
              ).slice(0, 24);
              return (
                r.name +
                ":" +
                r.kind +
                ":" +
                heatBand(r) +
                ":" +
                /* pc-996: strip "· Xm ago" tails — clock ticks are not state */
                stripRelWhen(r.work || "").slice(0, 40) +
                ":" +
                stripRelWhen(r.statusHint || "").slice(0, 24) +
                ":" +
                String(r.health || "").slice(0, 12) +
                ":" +
                String(r.shiftRail || "") +
                ":" +
                oc +
                ":" +
                homeBit +
                ":" +
                String((r && r.tier) || "")
              );
            })
            .join("|") +
          "|@dig:" +
          digFocusSig;
        function pillForRow(r) {
          /* Citizen status pills — what is happening now, not engine tokens */
          const health = String((r && r.health) || "").toLowerCase();
          const needsAtt =
            health === "err" ||
            health === "error" ||
            health === "fault" ||
            health === "failed" ||
            health === "wedged" ||
            health === "amber";
          if (r.kind === "live") {
            /* pc-1067: stale data — do not assert live Working from dead polls */
            if (isMapDataStale()) {
              return { lab: "Stale", cls: "hand-pill st-idle" };
            }
            return { lab: "Working", cls: "hand-pill st-live" };
          }
          /* pc-1067: off-shift claim — Holding pill when work line says so */
          if (
            (r.kind === "idle" || r.kind === "due") &&
            r.work &&
            /^Holding\b/i.test(String(r.work))
          ) {
            return { lab: "Holding", cls: "hand-pill st-due" };
          }
          if (r.kind === "walk" || r.kind === "peek") {
            return {
              lab:
                isFinite(r.remainMs) && r.remainMs > 0
                  ? fmtCountdown(r.remainMs)
                  : "Soon",
              cls: "hand-pill st-walk",
            };
          }
          if (r.skipped) {
            return { lab: "Skipped", cls: "hand-pill st-idle" };
          }
          /* pc-922: terminal ledger outcomes — first-class pills */
          if (r.shiftRail === "fail") {
            const oc = String((r.lastShift && r.lastShift.outcome) || "").toLowerCase();
            if (oc === "vendor_limit")
              return { lab: "Limit", cls: "hand-pill st-fail" };
            return { lab: "Failed", cls: "hand-pill st-fail" };
          }
          if (r.shiftRail === "skip") {
            return { lab: "Skipped", cls: "hand-pill st-due" };
          }
          if (needsAtt && (r.kind === "idle" || r.kind === "due")) {
            return { lab: "Attention", cls: "hand-pill st-due" };
          }
          /* idle never wears a countdown pill (that read as active work) */
          if (r.kind === "idle") {
            return { lab: "Idle", cls: "hand-pill st-idle" };
          }
          if (isFinite(r.remainMs) && r.remainMs > 0) {
            return {
              lab: fmtCountdown(r.remainMs),
              cls: "hand-pill st-due",
            };
          }
          return {
            lab: "Idle",
            cls: "hand-pill st-idle",
          };
        }
        function densityClass(r) {
          if (r.shiftRail === "fail") return "is-med is-fail";
          if (r.kind === "live") return "is-live";
          /* pc-1203: Holding ≠ grey idle — med + due lip (reuses due density) */
          if (
            (r.kind === "idle" || r.kind === "due") &&
            r.work &&
            /^Holding\b/i.test(String(r.work))
          ) {
            return "is-med is-due";
          }
          if (r.kind === "idle") return "is-idle";
          if (r.kind === "walk" || r.kind === "peek") return "is-med is-walk";
          return "is-med is-due";
        }
        /**
         * pc-1102 / pc-1203: scheduled wake on quiet rows.
         * Holding + next_fire → "Resumes HH:MM" (not bare Next = idle schedule).
         */
        function wakeTextForRow(r) {
          if (!r || r.kind !== "idle" || !r.nextFire) return "";
          let t = "";
          try {
            t = new Date(r.nextFire).toLocaleTimeString(undefined, {
              hour: "numeric",
              minute: "2-digit",
            });
          } catch (eT) {
            return "";
          }
          if (!t) return "";
          if (r.work && /^Holding\b/i.test(String(r.work))) {
            return "Resumes " + t;
          }
          return "Next " + t;
        }
        function projectLine(r) {
          if (r.homeShort) return r.homeShort;
          const rh = String(r.home || "");
          if (rh && rh.indexOf("__") !== 0 && rh.charAt(0) !== "/" && rh.charAt(0) !== "~")
            return rh.slice(0, 16);
          return "";
        }
        /**
         * Agent activities primary subtitle (pc-527): product/home first,
         * then role/title — scan by workplace before job epithet.
         * Ops jobs with no home: function role, else "workspace".
         */
        function cardRoleLine(r) {
          const role = String(r.role || "").trim();
          const project = projectLine(r);
          if (project && role && role.toLowerCase() !== project.toLowerCase()) {
            return project + " · " + role;
          }
          if (project) return project;
          if (role) return role;
          if (r.isJob) return "workspace";
          return "";
        }
        /** Status meta only — never restate product (lives on role line). */
        function cardMetaText(r) {
          if (r.skipped) return r.meta || "Skipped this check only";
          if (r.kind === "walk" || r.kind === "peek") {
            /* Approaching · N% lives in meta; countdown is the pill */
            return r.meta || "Approaching";
          }
          /* pc-922: work line owns fail/skip outcome; meta stays ready depth */
          if (r.shiftRail === "fail" || r.shiftRail === "skip") {
            const bits = [];
            const n = r.queueReady | 0;
            if (n > 0) bits.push(n + " ready in lane");
            if (r.work) bits.push(r.work);
            else if (r.statusHint) bits.push(r.statusHint);
            return bits.join(" · ");
          }
          if (r.kind === "idle" || r.kind === "due") {
            /* pc-1067: held claim is primary when off-shift (stranded triage) */
            if (r.work && /^Holding\b/i.test(String(r.work))) {
              return r.work; /* "Holding pc-… · resumes next shift" */
            }
            /* pc-1174: Last real · id is primary idle story when no ready/status */
            if (r.work && /^Last real\b/i.test(String(r.work))) {
              const bits = [];
              const n = r.queueReady | 0;
              if (n > 0) bits.push(n + " ready in lane");
              bits.push(r.work);
              return bits.join(" · ");
            }
            let meta = composeIdleAgentMeta(r.queueReady, r.statusHint, false);
            if (!meta && r.work) meta = r.work;
            return meta;
          }
          if (r.kind === "live") return ""; /* work line carries claim */
          return r.meta || "";
        }
        function cardMetaClass(r, metaWant) {
          const base = "hand-meta";
          if (!metaWant) return base;
          if (r.kind === "walk" || r.kind === "peek") return base + " is-walk";
          if (r.kind === "live") return base + " is-live";
          if (r.shiftRail === "fail") return base + " is-fail";
          /* pc-1203: Holding meta uses due tint (not quiet idle grey) */
          if (r.work && /^Holding\b/i.test(String(r.work))) {
            return base + " is-due";
          }
          const h = String(r.health || "").toLowerCase();
          if (
            h === "amber" ||
            h === "wedged" ||
            h === "err" ||
            h === "error" ||
            r.shiftRail === "skip" ||
            (r.statusHint &&
              (String(r.statusHint).indexOf("lock") >= 0 ||
                String(r.statusHint).indexOf("skip") >= 0 ||
                String(r.statusHint).indexOf("failed") >= 0 ||
                String(r.statusHint).indexOf("vendor") >= 0 ||
                String(r.statusHint).indexOf("attention") >= 0))
          )
            return base + " is-amber";
          if ((r.queueReady | 0) > 0) return base + " is-ready";
          if (r.kind === "due") return base + " is-due";
          return base;
        }
        /**
         * pc-529: quiet model pin only — never lead with bare CLI.
         * Hidden on live rows so the green work line is the only status story.
         */
        function handPayrollLine(r) {
          if (!r) return "";
          if (r.kind === "live") return ""; /* work line owns the slot */
          let model = String(r.model || "").trim();
          if (model === "default") model = "";
          if (!model) return "";
          return "model · " + model;
        }
        var HAND_PAY_TITLE = "payroll pin — not the worker's name";
        function patchHandCard(li, r) {
          if (!li || !r) return;
          const dens = densityClass(r);
          const wrapEl = li.querySelector(".hand-card-wrap");
          if (wrapEl) {
            wrapEl.className = "hand-card-wrap hand-card " + dens;
            wrapEl.setAttribute("data-agent", r.name);
            wrapEl.setAttribute(
              "data-entity-slug",
              r.entitySlug ||
                (r.home && String(r.home).indexOf("__") !== 0 ? r.home : "__you__")
            );
            wrapEl.setAttribute(
              "data-entity-seat",
              r.isJob ? "jobs" : "hands"
            );
          }
          const btn = li.querySelector("button.hand-card");
          if (btn) {
            btn.className = "hand-card " + dens;
          }
          /* pc-696: preserve/restart activity beat without full remount */
          li.className =
            "hand-li " +
            dens.split(" ")[0] +
            (r.isStateNew ? " is-activity-beat" : "");
          const meta = li.querySelector(".hand-meta");
          const metaWant = cardMetaText(r);
          if (meta) {
            if (!metaWant) {
              meta.remove();
            } else {
              if (meta.textContent !== metaWant) meta.textContent = metaWant;
              meta.className = cardMetaClass(r, metaWant);
            }
          } else if (metaWant) {
            /* soft-patch: meta may be missing after idle↔walk transitions */
            const body = li.querySelector(".hand-body");
            if (body) {
              const span = document.createElement("span");
              span.className = cardMetaClass(r, metaWant);
              span.textContent = metaWant;
              const pay = body.querySelector(".hand-pay");
              if (pay && pay.nextSibling) {
                body.insertBefore(span, pay.nextSibling);
              } else {
                body.appendChild(span);
              }
            }
          }
          const workEl = li.querySelector(".hand-work");
          if (workEl) {
            let wtxt = r.kind === "live" ? r.work || "On shift" : "";
            /* pc-1067: never paint live fallback from frozen stale tab */
            if (
              r.kind === "live" &&
              isMapDataStale() &&
              (!wtxt ||
                wtxt === "On shift" ||
                wtxt === "On shift · no work order yet")
            ) {
              wtxt = "Stale · last known";
            }
            if (workEl.textContent !== wtxt) workEl.textContent = wtxt;
            workEl.classList.toggle("is-stale", isMapDataStale() && r.kind === "live");
          }
          const roleEl = li.querySelector(".hand-role");
          if (roleEl) {
            const roleLine = cardRoleLine(r);
            if (roleEl.textContent !== roleLine) {
              roleEl.textContent = roleLine;
            }
          }
          /* pc-1102 / pc-1203: idle next-wake; Holding → Resumes HH:MM */
          const wakeWant = wakeTextForRow(r);
          const holdingWake =
            !!(r.work && /^Holding\b/i.test(String(r.work)));
          let wakeEl = li.querySelector(".hand-wake");
          if (wakeWant) {
            if (!wakeEl) {
              wakeEl = document.createElement("span");
              wakeEl.className = "hand-wake";
              const body = li.querySelector(".hand-body");
              if (body) {
                if (roleEl && roleEl.nextSibling) {
                  body.insertBefore(wakeEl, roleEl.nextSibling);
                } else if (roleEl) {
                  body.appendChild(wakeEl);
                }
              }
            }
            if (wakeEl.textContent !== wakeWant) wakeEl.textContent = wakeWant;
            /* Holding density is is-med is-due (not is-idle); CSS hides .hand-wake
             * off is-idle — force visible so Resumes still reads on Holding. */
            wakeEl.style.display = holdingWake ? "block" : "";
          } else if (wakeEl) {
            wakeEl.remove();
          }
          /* Per-hand / per-job face (overrides) with defaults from Settings */
          const avGlyph = li.querySelector(".hand-av .glyph");
          if (avGlyph) {
            const wid = String(r.name || r.id || r.worker || "").trim();
            const sTier = r.tier || (r.isStaff ? "staff" : r.isJob ? "job" : "agent");
            const wantG = sTier === "staff" ? getStaffGlyph(wid) : sTier === "job" ? getJobGlyph(wid) : getHandGlyph(wid);
            if (avGlyph.textContent !== wantG) avGlyph.textContent = wantG;
          }
          const payWant = handPayrollLine(r);
          let payEl = li.querySelector(".hand-pay");
          if (payWant) {
            if (!payEl) {
              const body = li.querySelector(".hand-body");
              if (body) {
                payEl = document.createElement("span");
                payEl.className = "hand-pay";
                const roleEl2 = body.querySelector(".hand-role");
                if (roleEl2 && roleEl2.nextSibling) {
                  body.insertBefore(payEl, roleEl2.nextSibling);
                } else if (roleEl2) {
                  body.appendChild(payEl);
                } else {
                  body.appendChild(payEl);
                }
              }
            }
            if (payEl) {
              if (payEl.textContent !== payWant) payEl.textContent = payWant;
              payEl.setAttribute("title", HAND_PAY_TITLE);
            }
          } else if (payEl) {
            payEl.remove();
          }
          const pill = li.querySelector(".hand-pill");
          if (pill) {
            const p = pillForRow(r);
            if (pill.textContent !== p.lab) pill.textContent = p.lab;
            pill.className = p.cls;
            if (r.nextFire) pill.setAttribute("data-nf", r.nextFire);
          }
          const barRow = li.querySelector(".hand-bar-row");
          const bar = li.querySelector(".hand-bar");
          const fill = bar && bar.querySelector("i");
          const showBar = r.kind === "walk" || r.kind === "peek";
          if (barRow || bar) {
            if (barRow) barRow.style.display = showBar ? "" : "none";
            if (bar && fill && showBar) {
              const pct = Math.round(
                Math.min(1, Math.max(0, r.progress || 0)) * 100
              );
              fill.style.width = pct + "%";
              bar.className = "hand-bar is-walk";
              const pctEl = li.querySelector(".hand-pct");
              if (pctEl && pctEl.textContent !== pct + "%") {
                pctEl.textContent = pct + "%";
              }
            }
          }
          /* Skip chip sits on the progress row (same bar height always) */
          let skipBtn = li.querySelector("button.hand-skip");
          const wantSkip = !!(r.canSkip && !r.skipped);
          const wantSkipSlot = wantSkip || !!r.skipped;
          if (wantSkipSlot && showBar && barRow && !skipBtn) {
            skipBtn = document.createElement("button");
            skipBtn.type = "button";
            skipBtn.className = "hand-skip";
            skipBtn.setAttribute("data-skip-agent", r.name);
            skipBtn.setAttribute(
              "title",
              "Skip this queue-check round only — does not pause hire"
            );
            skipBtn.textContent = wantSkip ? "Skip" : "Skipped";
            if (!wantSkip) skipBtn.disabled = true;
            skipBtn.addEventListener("click", function (ev) {
              ev.preventDefault();
              ev.stopPropagation();
              requestSkipRound(r.name, r.nextFire, skipBtn);
            });
            barRow.appendChild(skipBtn);
          } else if (skipBtn && !wantSkipSlot) {
            skipBtn.remove();
          } else if (skipBtn && wantSkip) {
            if (skipBtn.textContent !== "Skipping…" && !skipBtn.disabled) {
              skipBtn.textContent = "Skip";
              skipBtn.disabled = false;
            }
            skipBtn.setAttribute("data-skip-agent", r.name);
            if (barRow && skipBtn.parentNode !== barRow) {
              barRow.appendChild(skipBtn);
            }
          } else if (skipBtn && r.skipped) {
            skipBtn.textContent = "Skipped";
            skipBtn.disabled = true;
          }
        }
        /* pc-1396: HTML escape lives in /esc.js */
        var escAttr = function (s) { return global.__bp.escAttr(s); };
        var escHtmlLocal = function (s) { return global.__bp.esc(s); };
        /* pc-771: shared hand-li builder — used by both flat and grouped renders */
        function buildHandLiHtml(r, elsewhere) {
          const short = String(r.display || r.name).replace(/\s*·.*$/, "").slice(0, 18);
          const dens = densityClass(r);
          const metaText = cardMetaText(r);
          const metaCls = cardMetaClass(r, metaText);
          const p = pillForRow(r);
          const pct = Math.round(Math.min(1, Math.max(0, r.progress || 0)) * 100);
          const liCls =
            "hand-li " +
            dens.split(" ")[0] +
            (r.isStateNew ? " is-activity-beat" : "");
          const roleLine = cardRoleLine(r);
          const rTier = r.tier || (r.isStaff ? "staff" : r.isJob ? "job" : "agent");
          const avCls = "hand-av is-" + rTier;
          const handId = String(r.name || r.id || "").trim();
          const glyph = rTier === "staff" ? getStaffGlyph(handId) : rTier === "job" ? getJobGlyph(handId) : getHandGlyph(handId);
          /* pc-856: bare face — no inline plate color (row lip carries status) */
          const avStyle = "";
          const showBar = r.kind === "walk" || r.kind === "peek";
          const skipChip = showBar && r.canSkip && !r.skipped
            ? '<button type="button" class="hand-skip" data-skip-agent="' + escAttr(r.name) +
              '" title="Skip this queue-check round only — does not pause hire">Skip</button>'
            : showBar && r.skipped
              ? '<button type="button" class="hand-skip" disabled>Skipped</button>'
              : "";
          const barHtml = showBar
            ? '<div class="hand-bar-row"><div class="hand-bar is-walk" title="' + pct +
              '% to fire"><i style="width:' + pct + '%"></i></div>' +
              '<span class="hand-pct">' + pct + "%</span>" + skipChip + "</div>"
            : "";
          let workLineTxt =
            r.kind === "live" ? r.work || "On shift" : "";
          if (
            r.kind === "live" &&
            isMapDataStale() &&
            (!workLineTxt ||
              workLineTxt === "On shift" ||
              workLineTxt === "On shift · no work order yet")
          ) {
            workLineTxt = "Stale · last known";
          }
          const workHtml =
            r.kind === "live"
              ? '<span class="hand-work' +
                (isMapDataStale() ? " is-stale" : "") +
                '">' +
                escHtmlLocal(workLineTxt) +
                "</span>"
              : "";
          const payLine = handPayrollLine(r);
          const payHtml = payLine
            ? '<span class="hand-pay" title="' +
              escAttr(HAND_PAY_TITLE) +
              '">' +
              escHtmlLocal(payLine) +
              "</span>"
            : "";
          /* pc-1203: Holding → Resumes; force display when not is-idle density */
          const wakeWantBuild = wakeTextForRow(r);
          const holdingWakeBuild =
            !!(r.work && /^Holding\b/i.test(String(r.work)));
          const wakeHtml = wakeWantBuild
            ? '<span class="hand-wake"' +
              (holdingWakeBuild ? ' style="display:block"' : "") +
              ">" +
              escHtmlLocal(wakeWantBuild) +
              "</span>"
            : "";
          const wrapCls = "hand-card-wrap hand-card " + dens;
          const elseAttr = elsewhere ? ' data-elsewhere="1"' : "";
          const idleAttr = r.kind === "idle"
            ? ' data-idle="1" data-tier="' + escAttr(r.tier || "agent") + '"'
            : "";
          const kindAttr = rTier;
          return (
            '<li class="' +
            liCls +
            '"' +
            elseAttr +
            idleAttr +
            ' data-worker="' +
            escAttr(handId) +
            '" data-name="' +
            escAttr(handId) +
            '" data-kind="' +
            kindAttr +
            (r.isJob ? '" data-job="' + escAttr(handId) : "") +
            '">' +
            '<div class="' + wrapCls + '" data-agent="' + escAttr(r.name) +
            '" data-entity-slug="' +
            escAttr(r.entitySlug || (r.home && String(r.home).indexOf("__") !== 0 ? r.home : "__you__")) +
            '" data-entity-seat="' + (r.isJob ? "jobs" : "hands") + '" role="button" tabindex="0">' +
            '<span class="' + avCls + '"' + avStyle + ' title="' + rTier + '">' +
            '<span class="glyph">' + glyph + "</span></span>" +
            '<span class="hand-body">' +
            '<span class="hand-top">' +
            '<span class="hand-nm">' + escHtmlLocal(short) + "</span>" +
            '<span class="' + p.cls + '" data-nf="' + escAttr(r.nextFire || "") + '">' +
            escHtmlLocal(p.lab) + "</span></span>" +
            '<span class="hand-role">' + escHtmlLocal(roleLine) + "</span>" +
            wakeHtml +
            payHtml +
            (metaText ? '<span class="' + metaCls + '">' + escHtmlLocal(metaText) + "</span>" : "") +
            workHtml + barHtml +
            "</span></div></li>"
          );
        }
        const liveHasFastRail = !!(
          liveList.querySelector && liveList.querySelector("[data-fast-rail]")
        );
        /*
         * Patch order must match full-rebuild card order exactly (headers
         * skipped). Dig: focus-only heat order (map selection filters the rail).
         * Workspace: partitionRoster.ordered (walk before due).
         */
        function computePatchOrder() {
          if (mapDigIn && mapDigIn.plot) {
            var _fr = [];
            slice.forEach(function (r) {
              if (handOnDigFocus(r)) _fr.push(r);
            });
            return partitionRoster(_fr).ordered;
          }
          return partitionRoster(slice).ordered;
        }
        var patchOrderWanted = computePatchOrder();
        var shells = listAgentShells(liveList);
        var shellsMatch =
          shells.length === patchOrderWanted.length &&
          shells.every(function (s, i) {
            return (
              s.name === String((patchOrderWanted[i] && patchOrderWanted[i].name) || "")
            );
          });
        if (
          _liveSig === liveSig &&
          liveList.children.length &&
          !liveHasFastRail &&
          shellsMatch
        ) {
          /*
           * Soft-patch only when every shell is still the right agent in the
           * right band slot. Band moves (idle→walk, due↔approach) remount.
           * Dig: keep is-dig-roster + clear tier folds every tick.
           */
          if (mapDigIn && mapDigIn.plot) setAgentRosterMode(liveList, true);
          else setAgentRosterMode(liveList, false);
          shells.forEach(function (s, i) {
            patchHandCard(s.li, patchOrderWanted[i]);
          });
        } else {
          _liveSig = liveSig;
          clearMapEntityPreviewKind("agent");
          var digOpen = !!(mapDigIn && mapDigIn.plot);
          var digLabel = digOpen
            ? String(
                mapDigIn.plot.name || mapDigIn.plot.slug || "project"
              ).slice(0, 18)
            : "";
          var htmlParts = [];
          if (digOpen) {
            /*
             * Dig = filter. Only seats home on the dig project (map selection).
             * No "Elsewhere" fold — that fought the filtered left-rail story.
             * Heat order: fail → live → approach → due → idle.
             */
            setAgentRosterMode(liveList, true);
            liveList.classList.remove("is-elsewhere-collapsed");
            liveList.dataset.elsewhereOpen = "0";
            var focusRows = [];
            slice.forEach(function (r) {
              if (handOnDigFocus(r)) focusRows.push(r);
            });
            focusRows = partitionRoster(focusRows).ordered;
            if (focusRows.length) {
              htmlParts.push(
                '<li class="rail-group-hd" data-separator="1">' +
                  '<span class="rail-group-label">' +
                  escHtmlLocal(digLabel) +
                  " · " +
                  focusRows.length +
                  "</span></li>"
              );
              focusRows.forEach(function (r) {
                htmlParts.push(buildHandLiHtml(r, false));
              });
            } else {
              htmlParts.push(
                '<li class="hand-li is-idle" data-separator="1">' +
                  '<div class="hand-card-wrap hand-card is-idle" style="cursor:default;opacity:0.75">' +
                  '<span class="hand-body"><span class="hand-role">No hands or jobs home here</span>' +
                  '<span class="hand-meta">Reset dig or pick another project on the map</span></span>' +
                  "</div></li>"
              );
            }
            liveList.innerHTML = htmlParts.join("");
          } else {
            setAgentRosterMode(liveList, false);
            liveList.classList.remove("is-elsewhere-collapsed");
            liveList.dataset.elsewhereOpen = "0";
            /*
             * Hard partition (not lastIdleTier scan):
             *   Attention → live → peek → walk → due → Agents idle → Staff → Jobs
             * Approaching always above gold Due. Exactly one header per idle tier.
             */
            const tierLabel = { agent: "Agents", staff: "Staff", job: "Jobs" };
            const parts = partitionRoster(slice);
            const htmlOut = [];
            if (parts.fail.length) {
              htmlOut.push(
                '<li class="rail-group-hd" data-separator="1">' +
                  '<span class="rail-group-label">Attention · ' +
                  parts.fail.length +
                  "</span></li>"
              );
              parts.fail.forEach(function (r) {
                htmlOut.push(buildHandLiHtml(r, false));
              });
            }
            /* On-shift heat: live → peek → walk → due (never due before walk) */
            parts.onShift.forEach(function (r) {
              htmlOut.push(buildHandLiHtml(r, false));
            });
            function emitIdleTier(tierKey, rows) {
              if (!rows.length) return;
              htmlOut.push(
                '<li class="rail-group-hd" data-separator="1">' +
                  '<span class="rail-group-label">' +
                  (tierLabel[tierKey] || "Agents") +
                  " · " +
                  rows.length +
                  " idle</span>" +
                  '<button type="button" class="rail-group-toggle" data-tier-toggle="' +
                  escAttr(tierKey) +
                  '" aria-expanded="false">Show</button></li>'
              );
              rows.forEach(function (r) {
                htmlOut.push(buildHandLiHtml(r, false));
              });
            }
            emitIdleTier("agent", parts.idleAgent);
            emitIdleTier("staff", parts.idleStaff);
            emitIdleTier("job", parts.idleJob);
            liveList.innerHTML = htmlOut.join("");
            /* pc-1102: restore per-tier fold state; default collapsed */
            ["agent", "staff", "job"].forEach(function (t) {
              var n =
                t === "staff"
                  ? parts.idleStaff.length
                  : t === "job"
                    ? parts.idleJob.length
                    : parts.idleAgent.length;
              if (n > 0) {
                var wasOpen = liveList.dataset["tierOpen_" + t] === "1";
                liveList.classList.toggle("is-tier-collapsed-" + t, !wasOpen);
              } else {
                liveList.classList.remove("is-tier-collapsed-" + t);
              }
            });
            liveList.querySelectorAll("button[data-tier-toggle]").forEach(function (btn) {
              if (btn._wired) return;
              btn._wired = true;
              var tier = btn.getAttribute("data-tier-toggle");
              btn.addEventListener("click", function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                var collapsed = liveList.classList.contains("is-tier-collapsed-" + tier);
                liveList.classList.toggle("is-tier-collapsed-" + tier, !collapsed);
                liveList.dataset["tierOpen_" + tier] = collapsed ? "1" : "0";
                btn.setAttribute("aria-expanded", collapsed ? "true" : "false");
                btn.textContent = collapsed ? "Hide" : "Show";
              });
            });
          }
          function openAgentFromCard(el) {
            const nm = el && el.getAttribute("data-agent");
            if (!nm || !model || !model.workers) return;
            const entitySlug =
              (el && el.getAttribute("data-entity-slug")) || "";
            const w = model.workers.filter(function (x) {
              return x && x.name === nm;
            })[0];
            if (w) {
              try {
                const hk = String(w.homeKey || "");
                selectMapEntity({
                  kind: "agent",
                  agent: nm,
                  seat:
                    (el && el.getAttribute("data-entity-seat")) || "",
                  slug:
                    entitySlug ||
                    (hk && hk.indexOf("__") !== 0 ? hk : "__you__"),
                });
              } catch (eSel) {}
              inspectPerson(w);
            }
          }
          liveList.querySelectorAll(".hand-card-wrap[data-agent]").forEach(function (wrap) {
            wireMapEntityPreview(wrap, function () {
              return {
                kind: "agent",
                agent: wrap.getAttribute("data-agent") || "",
                seat: wrap.getAttribute("data-entity-seat") || "",
                slug: wrap.getAttribute("data-entity-slug") || "__you__",
              };
            });
            wrap.addEventListener("click", function (ev) {
              if (ev.target && ev.target.closest && ev.target.closest("button.hand-skip")) {
                return;
              }
              openAgentFromCard(wrap);
            });
            wrap.addEventListener("keydown", function (ev) {
              if (ev.key === "Enter" || ev.key === " ") {
                if (ev.target && ev.target.closest && ev.target.closest("button.hand-skip")) {
                  return;
                }
                ev.preventDefault();
                openAgentFromCard(wrap);
              }
            });
          });
          /* legacy button.hand-card if any */
          liveList.querySelectorAll("button.hand-card").forEach(function (btn) {
            btn.addEventListener("click", function () {
              openAgentFromCard(btn);
            });
          });
          liveList.querySelectorAll("button.hand-skip").forEach(function (btn) {
            if (btn.disabled) return;
            btn.addEventListener("click", function (ev) {
              ev.preventDefault();
              ev.stopPropagation();
              const nm = btn.getAttribute("data-skip-agent");
              if (!nm) return;
              let nf = "";
              const row = slice.filter(function (x) {
                return x && x.name === nm;
              })[0];
              if (row) nf = row.nextFire || "";
              requestSkipRound(nm, nf, btn);
            });
          });
        }
        syncMapEntitySelection();
      }
    }

  }


  function init(host) {
    if (!host || typeof host !== "object") return AgentsPanel;
    Object.keys(_host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return AgentsPanel;
  }

  /**
   * setStale — mark map poll freshness.
   * @param {boolean|number|object} flag
   *   true → force stale (clear last ok)
   *   false → note poll ok now
   *   number → set last ok to that epoch ms
   *   { pendingRefocus: bool } → hidden-tab race flag
   */
  function setStale(flag) {
    if (flag && typeof flag === "object") {
      if (Object.prototype.hasOwnProperty.call(flag, "pendingRefocus")) {
        _pendingRefocusPoll = !!flag.pendingRefocus;
      }
      if (Object.prototype.hasOwnProperty.call(flag, "lastOkAt")) {
        _lastMapPollOkAt = Number(flag.lastOkAt) || 0;
      }
      if (flag.noteOk) {
        _lastMapPollOkAt = Date.now();
        _pendingRefocusPoll = false;
      }
      return isMapDataStale();
    }
    if (typeof flag === "number") {
      _lastMapPollOkAt = flag;
      return isMapDataStale();
    }
    if (flag === false) {
      _lastMapPollOkAt = Date.now();
      _pendingRefocusPoll = false;
      return false;
    }
    if (flag === true) {
      _lastMapPollOkAt = 0;
      return true;
    }
    return isMapDataStale();
  }

  function noteMapPollOk() {
    _lastMapPollOkAt = Date.now();
    _pendingRefocusPoll = false;
  }

  function setPendingRefocus(v) {
    _pendingRefocusPoll = !!v;
  }

  function getPendingRefocus() {
    return !!_pendingRefocusPoll;
  }

  function getDeskOwnerByHand() {
    return _deskOwnerByHand;
  }

  function getDeskHolderByTid() {
    return _deskHolderByTid;
  }

  function getLiveSig() {
    return _liveSig;
  }

  function setLiveSig(s) {
    _liveSig = s || "";
  }

  var AgentsPanel = {
    init: init,
    paint: paint,
    setStale: setStale,
    /* bridge — strangler phase host needs these without reaching internals */
    noteMapPollOk: noteMapPollOk,
    setPendingRefocus: setPendingRefocus,
    getPendingRefocus: getPendingRefocus,
    mapLastRefreshAt: mapLastRefreshAt,
    isMapDataStale: isMapDataStale,
    getDeskOwnerByHand: getDeskOwnerByHand,
    getDeskHolderByTid: getDeskHolderByTid,
    refreshDeskOwnerIndex: refreshDeskOwnerIndex,
    /* pc-1204: claim/close soft-poll bust (optimistic + force strip) */
    warmDeskOwnerClaim: warmDeskOwnerClaim,
    dropDeskOwnerTid: dropDeskOwnerTid,
    ingestPeopleShiftTruth: ingestPeopleShiftTruth,
    applyPulsePeopleFailures: applyPulsePeopleFailures,
    refreshShiftTruthFromFull: refreshShiftTruthFromFull,
    noteShiftTruth: noteShiftTruth,
    noteRecentFailures: noteRecentFailures,
    workerLastShift: workerLastShift,
    workerLastReal: workerLastReal,
    lastRealWorkLine: lastRealWorkLine,
    noteLastRealTruth: noteLastRealTruth,
    seatHandFromLabels: seatHandFromLabels,
    seatHandFromTask: seatHandFromTask,
    isYouishSeat: isYouishSeat,
    liveWorkLineFromParts: liveWorkLineFromParts,
    heldClaimLineFromParts: heldClaimLineFromParts,
    indexDeskOwnersFromTasks: indexDeskOwnersFromTasks,
    indexDeskHoldersByTid: indexDeskHoldersByTid,
    citizenHandStatusHint: citizenHandStatusHint,
    citizenShiftLabel: citizenShiftLabel,
    partitionShiftHistory: partitionShiftHistory,
    isFailShift: isFailShift,
    isEmptyCheckShift: isEmptyCheckShift,
    digShiftTicketId: digShiftTicketId,
    lastShiftRailKind: lastShiftRailKind,
    parseReadyQueueDepth: parseReadyQueueDepth,
    stripRelWhen: stripRelWhen,
    renderedActivityCopy: renderedActivityCopy,
    citizenActivityLine: citizenActivityLine,
    composeIdleAgentMeta: composeIdleAgentMeta,
    shortShiftWhen: shortShiftWhen,
    getLiveSig: getLiveSig,
    setLiveSig: setLiveSig,
  };

  global.AgentsPanel = AgentsPanel;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = AgentsPanel;
  }
})(typeof window !== "undefined" ? window : globalThis);
