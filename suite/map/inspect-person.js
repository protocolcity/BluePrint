/*! inspect-person.js — Person / hand inspect panel renderer (pc-1401)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4).
 * Hand / job dig-in (inspectPerson + paintPersonDigIn + person-dig helpers)
 * live here only — host keeps thin wrappers so existing call sites stay put.
 *
 * Browser: window.InspectPerson
 * Public: { init, show, paint }
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    actorIsJob: null,
    actorShortName: null,
    bindPlacePulse: null,
    citizenActivityLine: null,
    citizenShiftLabel: null,
    digShiftTicketId: null,
    escHtml: null,
    flashHudNote: null,
    formatRemain: null,
    goHref: null,
    heldClaimLineFromParts: null,
    inspectIsProseNote: null,
    inspectItemIconHtml: null,
    inspectProseNoteHtml: null,
    inspectYou: null,
    instructionDepthLabel: null,
    instructionReadRel: null,
    instructionSectionLabel: null,
    isEmptyCheckShift: null,
    isFailShift: null,
    nextFireMs: null,
    openInspect: null,
    openPaperInSuite: null,
    paperPathFromHref: null,
    paperRelPath: null,
    papersForWorker: null,
    partitionShiftHistory: null,
    personHomeLabel: null,
    personInspectMeta: null,
    placePulseStripHtml: null,
    pulseAgentRailCard: null,
    refreshDeskOwnerIndex: null,
    renderedActivityCopy: null,
    scrollInspectSection: null,
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  function actorIsJob() {
    var fn = H('actorIsJob');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function actorShortName() {
    var fn = H('actorShortName');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function bindPlacePulse() {
    var fn = H('bindPlacePulse');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function citizenActivityLine() {
    var fn = H('citizenActivityLine');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function citizenShiftLabel() {
    var fn = H('citizenShiftLabel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function digShiftTicketId() {
    var fn = H('digShiftTicketId');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function escHtml() {
    var fn = H('escHtml');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function flashHudNote() {
    var fn = H('flashHudNote');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function formatRemain() {
    var fn = H('formatRemain');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function goHref() {
    var fn = H('goHref');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function heldClaimLineFromParts() {
    var fn = H('heldClaimLineFromParts');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function inspectIsProseNote() {
    var fn = H('inspectIsProseNote');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function inspectItemIconHtml() {
    var fn = H('inspectItemIconHtml');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function inspectProseNoteHtml() {
    var fn = H('inspectProseNoteHtml');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function inspectYou() {
    var fn = H('inspectYou');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function instructionDepthLabel() {
    var fn = H('instructionDepthLabel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function instructionReadRel() {
    var fn = H('instructionReadRel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function instructionSectionLabel() {
    var fn = H('instructionSectionLabel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function isEmptyCheckShift() {
    var fn = H('isEmptyCheckShift');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function isFailShift() {
    var fn = H('isFailShift');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function nextFireMs() {
    var fn = H('nextFireMs');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openInspect() {
    var fn = H('openInspect');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openPaperInSuite() {
    var fn = H('openPaperInSuite');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paperPathFromHref() {
    var fn = H('paperPathFromHref');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function paperRelPath() {
    var fn = H('paperRelPath');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function papersForWorker() {
    var fn = H('papersForWorker');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function partitionShiftHistory() {
    var fn = H('partitionShiftHistory');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function personHomeLabel() {
    var fn = H('personHomeLabel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function personInspectMeta() {
    var fn = H('personInspectMeta');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function placePulseStripHtml() {
    var fn = H('placePulseStripHtml');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function pulseAgentRailCard() {
    var fn = H('pulseAgentRailCard');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function refreshDeskOwnerIndex() {
    var fn = H('refreshDeskOwnerIndex');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function renderedActivityCopy() {
    var fn = H('renderedActivityCopy');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function scrollInspectSection() {
    var fn = H('scrollInspectSection');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  /**
   * Hand / job dig-in → map inspect rail only (same sidebar as jobs/papers).
   * One chrome: page header stays visible; ← Previous panel uses inspect history.
   * SuitePersonSheet overlay is not used on Map (two-sidebar drift).
   */
  function inspectPerson(w) {
    if (!w) return;
    if (w.kind === "citizen") {
      inspectYou();
      return;
    }
    /* Close floating person sheet if it was left open */
    try {
      if (
        window.SuitePersonSheet &&
        SuitePersonSheet.isOpen &&
        SuitePersonSheet.isOpen()
      ) {
        SuitePersonSheet.close();
      }
    } catch (eClose) {}

    const name = w.name || "";
    const isJob = actorIsJob(w);
    const lawLocal = papersForWorker(w);
    const nf = nextFireMs(w);
    const short =
      (typeof actorShortName === "function" ? actorShortName(w) : null) ||
      w.display ||
      name;

    const healthLow0 = String(w.health || "").toLowerCase();
    const needsAtt0 =
      healthLow0 === "err" ||
      healthLow0 === "error" ||
      healthLow0 === "fault" ||
      healthLow0 === "failed" ||
      healthLow0 === "wedged" ||
      healthLow0 === "amber";
    /*
     * pc-1203: person dig status — Holding when off-shift held IP/IR claim
     * (WF holding[] or Desk Owner join), not plain Idle.
     */
    let heldClaimId = "";
    let heldClaimLine0 = "";
    try {
      const ownerBy =
        typeof AgentsPanel !== "undefined" &&
        AgentsPanel.getDeskOwnerByHand
          ? AgentsPanel.getDeskOwnerByHand()
          : null;
      heldClaimLine0 = heldClaimLineFromParts(w, ownerBy || {});
      if (heldClaimLine0) {
        const mHold = String(heldClaimLine0).match(/^Holding\s+(\S+)/i);
        if (mHold) heldClaimId = mHold[1];
      }
    } catch (eHold0) {
      heldClaimLine0 = "";
    }
    if (!heldClaimId && w.holding && w.holding.length) {
      const h0 = w.holding[0];
      heldClaimId =
        (h0 && (h0.id || h0.task_id)) ||
        (typeof digTicketId === "function" ? digTicketId(h0) : "") ||
        "";
    }
    const isHoldingClaim = !w.working && !!(heldClaimLine0 || heldClaimId);
    let statusVal = "Idle";
    if (w.working) statusVal = "Working";
    else if (isHoldingClaim) statusVal = "Holding";
    else if (needsAtt0) statusVal = "Attention";
    const statusMeta =
      w.working
        ? "running now"
        : isHoldingClaim
          ? "holding"
          : "idle";
    const stats = [
      {
        label: "status",
        value: statusVal,
        live: !!w.working,
        muted: !w.working && !needsAtt0 && !isHoldingClaim,
        title: "Scroll to Now",
        action: function () {
          scrollInspectSection("now");
        },
      },
      {
        label: "next fire",
        value: isFinite(nf) ? formatRemain(nf - Date.now()) : "—",
        hero: true,
        muted: !isFinite(nf),
        title: "Scheduled next execute",
      },
    ];
    if (w.health && needsAtt0) {
      stats.push({
        label: "health",
        value: String(w.health),
        muted: true,
        hero: false,
      });
    }

    openInspect({
      kind: isJob ? "Job" : "Hand",
      title: short,
      meta: personInspectMeta(w, statusMeta, heldClaimId || undefined),
      stats: stats,
      formHtml: '<p class="meta" id="person-dig-load">Loading dig-in…</p>',
      doors: [],
      afterOpen: function (formHost) {
        paintPersonDigIn(formHost, w, lawLocal);
        /* pc-813: warm Desk owner index so last real / live claim can surface */
        try {
          refreshDeskOwnerIndex(false, function (_by, changed) {
            if (!formHost || !formHost.isConnected) return;
            if (changed) paintPersonDigIn(formHost, w, lawLocal);
          });
        } catch (eOwn) {}
        fetch("/api/worker/" + encodeURIComponent(name), {
          cache: "no-store",
          credentials: "same-origin",
        })
          .then(function (r) {
            return r.json().then(function (d) {
              if (!r.ok) throw new Error((d && d.error) || r.statusText);
              return d;
            });
          })
          .then(function (apiW) {
            if (!formHost || !formHost.isConnected) return;
            const mergedW = Object.assign({}, w, apiW);
            paintPersonDigIn(formHost, mergedW, lawLocal);
            try {
              const st = document.getElementById("inspect-meta");
              if (st && apiW) {
                /* pc-1203: Holding status when claim held and not working */
                let claimed =
                  apiW.holding && apiW.holding.length
                    ? apiW.holding[0].id ||
                      apiW.holding[0].task_id ||
                      "work order"
                    : "";
                let digStatus = "idle";
                if (apiW.working) digStatus = "on shift";
                else {
                  try {
                    const ownerBy2 =
                      AgentsPanel.getDeskOwnerByHand &&
                      AgentsPanel.getDeskOwnerByHand();
                    const held2 = heldClaimLineFromParts(
                      mergedW,
                      ownerBy2 || {}
                    );
                    if (held2) {
                      digStatus = "holding";
                      if (!claimed) {
                        const m2 = String(held2).match(/^Holding\s+(\S+)/i);
                        if (m2) claimed = m2[1];
                      }
                    } else if (claimed) {
                      digStatus = "holding";
                    }
                  } catch (eH2) {
                    if (claimed) digStatus = "holding";
                  }
                }
                st.textContent = personInspectMeta(
                  mergedW,
                  digStatus,
                  claimed
                );
                /* Refresh status KPI tile if present */
                try {
                  const kpi = document.querySelector(
                    '.inspect-kpi[data-label="status"] .v, .inspect .stats .v'
                  );
                  /* Prefer first stats value which is status */
                  const statsRoot = document.querySelector(".inspect .stats");
                  if (statsRoot) {
                    const firstV = statsRoot.querySelector(".inspect-kpi .v");
                    if (firstV) {
                      let sv = "Idle";
                      if (apiW.working) sv = "Working";
                      else if (digStatus === "holding") sv = "Holding";
                      else if (needsAtt0) sv = "Attention";
                      if (firstV.textContent !== sv) firstV.textContent = sv;
                    }
                  }
                } catch (eKpi) {}
              }
            } catch (eM) {}
          })
          .catch(function () {
            /* keep local paint */
          });
      },
    });
  }

  function digTicketId(t) {
    if (t == null) return "";
    if (typeof t === "string") return t;
    return t.id || t.task_id || "";
  }
  function digTicketTitle(t) {
    if (!t || typeof t !== "object") return "";
    return t.title || "";
  }
  function digNiceTs(ts) {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return String(ts);
    }
  }
  function digRelativeTs(ts) {
    if (!ts) return "—";
    try {
      const diff = Date.now() - new Date(ts).getTime();
      if (diff < 60000) return "just now";
      const h = Math.round(diff / 3600000);
      if (h < 24) return h + "h ago";
      const d = Math.round(diff / 86400000);
      if (d <= 14) return d + "d ago";
      return digNiceTs(ts);
    } catch (e) {
      return digNiceTs(ts);
    }
  }
  function digRunVerb(s) {
    if (!s) return "—";
    const oc = String(s.outcome || "").toLowerCase();
    const passes = s.passes != null ? s.passes | 0 : null;
    if (oc === "ok" || oc === "success" || oc === "done") {
      return passes > 0
        ? "Done · " + passes + " task" + (passes === 1 ? "" : "s")
        : "Done";
    }
    if (oc === "vendor_limit") return "Vendor limit";
    if (
      oc === "error" ||
      oc === "err" ||
      oc === "fault" ||
      oc === "failed" ||
      oc === "crashed"
    )
      return "Failed";
    if (oc === "skip" || oc === "skipped") {
      const r = String(s.reason || "").toLowerCase();
      return r.indexOf("queue empty") >= 0 || r.indexOf("no ready") >= 0
        ? "Checked · empty"
        : "Skipped";
    }
    return String(s.outcome || "?");
  }
  function digRunDetail(s) {
    if (!s) return "";
    const r = renderedActivityCopy(s.reason || "").trim();
    return r ? r.slice(0, 24) + (r.length > 24 ? "…" : "") : "";
  }
  function isSkipShift(s) {
    if (!s) return false;
    const oc = String(s.outcome || "").toLowerCase();
    return oc === "skip" || oc === "skipped";
  }

  /**
   * Person dig-in body inside map inspect rail — same list grammar as
   * jobs/papers (card rows), not a second overlay sheet.
   */
  function paintPersonDigIn(formHost, w, lawLocal) {
    if (!formHost) return;
    w = w || {};
    const isJob =
      actorIsJob(w) || String(w.kind || "").toLowerCase() === "job";
    const held = w.holding || [];
    const ready = w.ready || [];
    /* Prefer full shifts[]; fall back to last_shift as a one-row history */
    let rawShifts = Array.isArray(w.shifts) ? w.shifts.slice() : [];
    if (!rawShifts.length && w.last_shift) rawShifts = [w.last_shift];
    if (
      !rawShifts.length &&
      w.last_real_shift &&
      typeof w.last_real_shift === "object"
    ) {
      rawShifts = [w.last_real_shift];
    }
    const hist = partitionShiftHistory(rawShifts, 6);
    /* pc-964 BFF: empty_checks when deep ledger re-partitioned */
    const ecMeta =
      w.empty_checks && typeof w.empty_checks === "object"
        ? w.empty_checks
        : null;
    if (ecMeta && (ecMeta.count | 0) > hist.emptyN) {
      hist.emptyN = ecMeta.count | 0;
      if (ecMeta.last_ts || ecMeta.since) {
        hist.lastEmpty = hist.lastEmpty || {
          ts: ecMeta.last_ts || ecMeta.since,
        };
        hist.firstEmpty = hist.firstEmpty || {
          ts: ecMeta.since || ecMeta.last_ts,
        };
      }
    }
    const lastReal =
      hist.meaningful[0] ||
      (w.last_real_shift && typeof w.last_real_shift === "object"
        ? w.last_real_shift
        : null);
    /* pc-813: desk owner join when holding[] empty but IP/IR owned */
    let deskOwned = null;
    try {
      const handKey = String(w.name || "")
        .trim()
        .toLowerCase();
      if (handKey && AgentsPanel.getDeskOwnerByHand() && AgentsPanel.getDeskOwnerByHand()[handKey]) {
        deskOwned = AgentsPanel.getDeskOwnerByHand()[handKey];
      }
    } catch (eOwn) {}
    const lrtMeta =
      w.last_real_ticket && typeof w.last_real_ticket === "object"
        ? w.last_real_ticket
        : null;
    const lastRealTid =
      (lrtMeta && lrtMeta.id) ||
      hist.lastRealTicket ||
      (lastReal ? digShiftTicketId(lastReal) : "") ||
      (deskOwned && deskOwned.id) ||
      "";
    const lastRealTitle =
      (lrtMeta && lrtMeta.title) ||
      (deskOwned && deskOwned.id === lastRealTid && deskOwned.title
        ? deskOwned.title
        : "") ||
      "";
    /* pc-567: never "Project · ops" product folder for workspace ops jobs */
    const home = personHomeLabel(w);

    let nowBody = "Idle · nothing claimed";
    let nowSub = "Hands empty right now";
    let nowHref = null;
    if (held.length) {
      const h0 = held[0];
      const hid = digTicketId(h0);
      const hti = digTicketTitle(h0);
      nowBody =
        "Working on " +
        (hid || "a work order") +
        (hti ? " · " + String(hti).slice(0, 48) : "") +
        (held.length > 1 ? " (+" + (held.length - 1) + ")" : "");
      nowSub = isJob ? "Running now" : "On shift";
      if (hid) nowHref = "/ticket?id=" + encodeURIComponent(hid);
    } else if (w.working && deskOwned && deskOwned.id) {
      /* Live but WF holding empty — Desk owner is the real claim */
      nowBody =
        "Working on " +
        deskOwned.id +
        (deskOwned.title ? " · " + String(deskOwned.title).slice(0, 42) : "");
      nowSub = "On shift · from Desk owner";
      nowHref = "/ticket?id=" + encodeURIComponent(deskOwned.id);
    } else if (w.working) {
      nowBody = isJob ? "Running now" : "On shift · no work order id yet";
      nowSub =
        citizenActivityLine(w.why || w.activity || "") || "Live this tick";
      if (lastRealTid) {
        nowSub =
          "Last real · " +
          lastRealTid +
          (lastReal ? " · " + digNiceTs(lastReal.ts) : "");
        nowHref = "/ticket?id=" + encodeURIComponent(lastRealTid);
      }
    } else if (lastReal) {
      nowBody = isFailShift(lastReal)
        ? "Last real · " +
          lastRealTid +
          (lastReal ? " · " + digNiceTs(lastReal.ts) : "")
        : "Last real · " +
          (lastRealTid ? lastRealTid + " · " : "") +
          citizenShiftLabel(lastReal);
      nowSub =
        digNiceTs(lastReal.ts) +
        (lastReal.reason && !isEmptyCheckShift(lastReal)
          ? " · " + renderedActivityCopy(lastReal.reason).slice(0, 40)
          : "");
      if (lastRealTid)
        nowHref = "/ticket?id=" + encodeURIComponent(lastRealTid);
    } else if (hist.emptyN > 0) {
      nowBody = "Idle · checks only · no real work lately";
      const sinceTs =
        (hist.firstEmpty && hist.firstEmpty.ts) ||
        (hist.lastEmpty && hist.lastEmpty.ts) ||
        "";
      nowSub =
        hist.emptyN +
        " empty check" +
        (hist.emptyN === 1 ? "" : "s") +
        " since " +
        (sinceTs ? digNiceTs(sinceTs) : "—");
    } else {
      const citizenWhy = citizenActivityLine(w.why || "");
      if (citizenWhy) {
        nowBody = "Idle";
        nowSub = citizenWhy;
      }
    }

    const items = [];
    /* Now status → place-pulse tile (not a list section); claim/last-real as inventory */
    let nowSev = "quiet";
    let nowVal = "Idle";
    if (held.length || (w.working && deskOwned) || w.working) {
      nowSev = "live";
      nowVal = held.length
        ? digTicketId(held[0]) || "Working"
        : deskOwned && deskOwned.id
          ? deskOwned.id
          : "On shift";
    } else if (lastReal) {
      nowSev = "queued";
      nowVal = lastRealTid || "Last real";
    } else if (hist.emptyN > 0) {
      nowSev = "starved";
      nowVal = "Checks only";
    }
    const nowPulseHtml = placePulseStripHtml(
      [
        {
          id: "now",
          label: "Now",
          value: nowVal,
          reason: nowBody + (nowSub ? " · " + nowSub : ""),
          severity: nowSev,
          clickable: !!nowHref,
          title: nowHref ? "Open work order" : "Current status",
          action: !!nowHref,
        },
      ],
      { label: "Status", aria: "Agent status now" }
    );
    /* pc-813/pc-964: hero — last real ticket id + title + when */
    if ((lastRealTid || lastReal) && !held.length) {
      const whenTs =
        (lrtMeta && lrtMeta.ts) ||
        (lastReal && lastReal.ts) ||
        "";
      items.push({
        label: lastRealTid
          ? "Last real · " + lastRealTid
          : "Last real work",
        sub:
          (lastRealTitle
            ? String(lastRealTitle).slice(0, 52)
            : lastReal
              ? citizenShiftLabel(lastReal)
              : "Last real work order") +
          (whenTs ? " · " + digNiceTs(whenTs) : ""),
        href: lastRealTid
          ? nowHref || "/ticket?id=" + encodeURIComponent(lastRealTid)
          : null,
        attention: !!(lastReal && isFailShift(lastReal)),
      });
    }
    if (w.schedule || w.next_fire) {
      items.push({
        label: "Schedule · " + (w.schedule || "—"),
        sub: w.next_fire
          ? "Next fire · " + digNiceTs(w.next_fire)
          : "",
        note: true,
        inert: true,
      });
    }
    const healthLow = String(w.health || "").toLowerCase();
    const needsAtt0 =
      healthLow === "err" ||
      healthLow === "error" ||
      healthLow === "fault" ||
      healthLow === "failed" ||
      healthLow === "wedged" ||
      healthLow === "amber";
    const failAlreadySurfaced = isFailShift(lastReal) && needsAtt0;
    if (
      w.health &&
      healthLow !== "ok" &&
      healthLow !== "healthy" &&
      healthLow !== "good" &&
      !failAlreadySurfaced
    ) {
      items.push({
        label: "Needs attention",
        sub:
          String(w.health) +
          (w.why ? " · " + (citizenActivityLine(w.why) || renderedActivityCopy(w.why).slice(0, 48)) : ""),
        note: true,
        inert: true,
      });
    }

    let law = Array.isArray(w.law) ? w.law.slice() : [];
    if (!law.length && lawLocal && lawLocal.length) {
      law = lawLocal.map(function (ap) {
        const rel = paperRelPath(ap);
        const isC = String(ap.kind || "").toLowerCase() === "contract";
        const isP = String(ap.kind || "").toLowerCase() === "prompt";
        return {
          level: isC ? "L2" : isP ? "L3" : ap.kind || "instructions",
          file: ap.file || ap.name || "paper",
          path: rel,
          label: isC ? "contract" : isP ? "prompt" : ap.kind || "",
          readable: !!rel,
        };
      });
    }
    if (
      w.contract_path &&
      !law.some(function (e) {
        return e && String(e.level || "").toUpperCase() === "L2";
      })
    ) {
      law.push({
        level: "L2",
        file: "CONTRACT.md",
        path: w.contract_path,
        label: "contract",
        readable: true,
      });
    }
    if (
      w.prompt_path &&
      !law.some(function (e) {
        return e && String(e.level || "").toUpperCase() === "L3";
      })
    ) {
      law.push({
        level: "L3",
        file: "prompt.md",
        path: w.prompt_path,
        label: "prompt",
        readable: true,
      });
    }

    items.push({
      label: "Lane",
      section: true,
      inert: true,
    });
    held.slice(0, 8).forEach(function (t) {
      const id = digTicketId(t);
      const title = digTicketTitle(t);
      items.push({
        label: id || "work order",
        sub: title ? String(title).slice(0, 52) : "claimed",
        href: id ? "/ticket?id=" + encodeURIComponent(id) : null,
      });
    });
    ready.slice(0, 6).forEach(function (t) {
      const id = digTicketId(t);
      const title = digTicketTitle(t);
      items.push({
        label: id || "work order",
        sub: title ? String(title).slice(0, 48) : "ready",
        href: id ? "/ticket?id=" + encodeURIComponent(id) : null,
      });
    });
    if (!held.length && !ready.length) {
      items.push({
        label: "Lane empty",
        sub: "nothing claimed or ready",
        empty: true,
        inert: true,
      });
    }

    items.push({
      label: (isJob ? "Recent runs" : "Recent work") +
        (hist.meaningful.length ? " · " + hist.meaningful.length : ""),
      section: true,
      inert: true,
    });
    if (!hist.meaningful.length && !hist.emptyN) {
      items.push({
        label: "No runs recorded yet",
        sub: "Nothing in the shift ledger",
        empty: true,
        inert: true,
      });
    } else {
      /* Meaningful first — empty checks collapsed to one footer row (pc-813/964) */
      hist.meaningful.forEach(function (s) {
        const tidS = digShiftTicketId(s);
        items.push({
          label: (tidS ? tidS + " · " : "") + digRunVerb(s),
          sub:
            digRelativeTs(s.ts) +
            (isFailShift(s) || isSkipShift(s) ? " · " + digRunDetail(s) : ""),
          href: tidS ? "/ticket?id=" + encodeURIComponent(tidS) : null,
          note: !tidS,
          inert: !tidS,
          attention: isFailShift(s),
        });
      });
      if (hist.emptyN > 0) {
        const sinceTs =
          (hist.firstEmpty && hist.firstEmpty.ts) ||
          (hist.lastEmpty && hist.lastEmpty.ts) ||
          "";
        items.push({
          label:
            hist.emptyN +
            " empty check" +
            (hist.emptyN === 1 ? "" : "s") +
            " since " +
            (sinceTs ? digNiceTs(sinceTs) : "—"),
          sub: "Queue-empty skips · not real throughput",
          empty: true,
          inert: true,
        });
      }
    }

    items.push({
      label: "Reference",
      section: true,
      ref: true,
      inert: true,
    });
    items.push({
      label: home.isOps
        ? "Home · " + home.label
        : "Project · " + home.label,
      sub: home.isOps
        ? "Workspace ops · not a product folder"
        : w.workdir || (isJob ? "job · automation" : "hand · work-order lane"),
      note: true,
      inert: true,
    });
    items.push({
      label: instructionSectionLabel("hand", law.length),
      section: true,
      ref: true,
      inert: true,
    });
    if (!law.length) {
      items.push({
        label: "No instruction stack published",
        sub: isJob ? "workers/<id>/ papers" : "Lane papers missing",
        empty: true,
        inert: true,
      });
    } else {
      law.forEach(function (e) {
        if (!e) return;
        const rawPath = e.path || "";
        const file =
          e.file || (rawPath ? String(rawPath).split("/").pop() : "paper");
        /* P4: always city-rel for /read — abs WorkForce paths open too */
        const rel = instructionReadRel(rawPath);
        const depth = instructionDepthLabel(
          Object.assign({}, e, { file: file })
        );
        const lv = String(e.level || "").toUpperCase();
        items.push({
          label: file,
          sub: depth + (rel ? " · open" : " · path not in workspace"),
          href: rel ? "/read?path=" + encodeURIComponent(rel) : null,
          kind: "paper",
          law: lv === "L0" || lv === "L1" || lv === "L2" || lv === "L3",
        });
      });
    }

    formHost.innerHTML =
      nowPulseHtml +
      '<div class="inspect-list" role="list" id="person-dig-list">' +
      items
        .map(function (it, i) {
          if (inspectIsProseNote(it)) {
            return inspectProseNoteHtml(it);
          }
          const icon = it.section
            ? ""
            : it.kind === "paper" ||
                (it.href && String(it.href).indexOf("/read") >= 0)
              ? inspectItemIconHtml(it)
              : it.href && String(it.href).indexOf("/ticket") >= 0
                ? '<span class="card-ic is-paper" aria-hidden="true"><span class="glyph">🎫</span></span>'
                : "";
          return (
            '<button type="button" class="inspect-list-item' +
            (it.section || it.inert ? " is-inert" : "") +
            (it.section ? " is-section" : "") +
            (it.ref ? " is-section-ref" : "") +
            (it.attention ? " is-attention" : "") +
            (it.empty ? " is-empty" : "") +
            '" data-i="' +
            i +
            '">' +
            icon +
            '<span class="card-body"><span class="card-title">' +
            escHtml(it.label) +
            "</span>" +
            (it.sub
              ? '<span class="sub">' + escHtml(it.sub) + "</span>"
              : "") +
            "</span></button>"
          );
        })
        .join("") +
      "</div>";

    formHost.querySelectorAll(".inspect-list-item").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        const i = parseInt(btn.getAttribute("data-i"), 10);
        const it = items[i];
        if (!it || it.inert || it.section || !it.href) return;
        const paper = paperPathFromHref(it.href);
        if (paper) openPaperInSuite(paper);
        else if (
          it.href.indexOf("/ticket") >= 0 &&
          window.SuitePaper &&
          typeof SuitePaper.openTicket === "function"
        ) {
          const tid = (it.href.match(/[?&]id=([^&]+)/) || [])[1];
          if (tid) SuitePaper.openTicket(decodeURIComponent(tid));
          else goHref(it.href);
        } else goHref(it.href);
      });
    });
    bindPlacePulse(formHost, {
      now: function () {
        if (!nowHref) return;
        if (
          nowHref.indexOf("/ticket") >= 0 &&
          window.SuitePaper &&
          typeof SuitePaper.openTicket === "function"
        ) {
          const tid = (nowHref.match(/[?&]id=([^&]+)/) || [])[1];
          if (tid) SuitePaper.openTicket(decodeURIComponent(tid));
          else goHref(nowHref);
        } else goHref(nowHref);
      },
    });

    try {
      const doors = document.getElementById("inspect-doors");
      if (doors) {
        doors.innerHTML = "";
        const b = document.createElement("button");
        b.type = "button";
        b.className = "primary";
        b.setAttribute("data-person-dispatch", "1");
        b.textContent = w.working
          ? isJob
            ? "Running"
            : "On shift"
          : "Dispatch now";
        b.disabled = !!w.working;
        b.addEventListener("click", function () {
          if (b.disabled) return;
          b.disabled = true;
          b.textContent = "Dispatching…";
          /* pc-1243 Phase 1: pulse Activities card + stage toast immediately */
          try { pulseAgentRailCard(w.name, "live"); } catch (ePr1) {}
          try { flashHudNote("Dispatching · " + (w.display || w.name), 3500); } catch (eFH1) {}
          /* Engine route is path-param: POST /api/dispatch/<name> (pc-243) */
          fetch("/api/dispatch/" + encodeURIComponent(w.name || ""), {
            method: "POST",
            credentials: "same-origin",
          })
            .then(function (r) {
              /* Non-JSON bodies (405/502 fallthrough pages) must not mask
                 the HTTP status behind a parse error */
              return r
                .json()
                .catch(function () {
                  return null;
                })
                .then(function (d) {
                  if (!r.ok) {
                    throw new Error(
                      (d && (d.msg || d.error)) || r.statusText || "HTTP " + r.status
                    );
                  }
                  return d;
                });
            })
            .then(function (d) {
              b.textContent = "Dispatched";
              /* pc-1243 Phase 2: re-pulse rail, write sprint signal, dispatched toast */
              try { pulseAgentRailCard(w.name, "live"); } catch (ePr2) {}
              try {
                localStorage.setItem(
                  "pc-map-dispatch",
                  JSON.stringify({
                    name: w.name,
                    project: w.homeKey || w.home || "",
                    at: Date.now(),
                  })
                );
              } catch (eLs) {}
              try {
                flashHudNote(
                  "Dispatched · " + (w.display || w.name) + " · checking queue",
                  4500
                );
              } catch (eFH2) {}
              /* pc-1242: delay re-fetch so a sync CLI skip has time to land
                 in WorkForce ledger before we inspect last_shift */
              var dispatchAt = Date.now();
              setTimeout(function () {
                fetch("/api/worker/" + encodeURIComponent(w.name || ""), {
                  cache: "no-store",
                  credentials: "same-origin",
                })
                  .then(function (r) {
                    return r.ok ? r.json() : null;
                  })
                  .then(function (apiW) {
                    if (!formHost || !formHost.isConnected) return;
                    var merged = apiW ? Object.assign({}, w, apiW) : w;
                    paintPersonDigIn(formHost, merged, lawLocal);
                    /* pc-1242: detect CLI-missing skip; surface prominently */
                    var ls = apiW && apiW.last_shift;
                    var lsOc = ls ? String(ls.outcome || "").toLowerCase() : "";
                    var lsReason = ls ? String(ls.reason || "") : "";
                    var lsTsMs = ls && ls.ts ? Date.parse(ls.ts) : 0;
                    var isCliSkip =
                      (lsOc === "skip" || lsOc === "skipped") &&
                      (lsReason.toLowerCase().indexOf("cli") >= 0 ||
                        lsReason.toLowerCase().indexOf("not installed") >= 0 ||
                        lsReason.toLowerCase().indexOf("not found") >= 0);
                    var isRecent = !lsTsMs || lsTsMs >= dispatchAt - 8000;
                    if (isCliSkip && isRecent) {
                      var skipMsg =
                        "Dispatch skipped — " +
                        (lsReason || "runtime CLI not installed");
                      try {
                        flashHudNote(skipMsg, 10000);
                      } catch (eFHSk) {}
                      try {
                        var banner = document.createElement("p");
                        banner.className = "pc-dispatch-err";
                        banner.textContent = skipMsg;
                        banner.style.cssText =
                          "margin:6px 8px 0;font-size:var(--type-label);color:#c0392b;";
                        formHost.appendChild(banner);
                      } catch (eBann) {}
                    }
                  })
                  .catch(function () {});
              }, 1500);
            })
            .catch(function (err) {
              b.disabled = false;
              b.textContent = "Dispatch now";
              /* pc-1243: no alert — in-panel error line + stage toast */
              const msg = (err && err.message) || String(err);
              try {
                const errEl = document.createElement("p");
                errEl.className = "pc-dispatch-err";
                errEl.textContent = "Failed · " + msg;
                errEl.style.cssText =
                  "margin:6px 0 0;font-size:var(--type-label);color:#c0392b;";
                doors.appendChild(errEl);
              } catch (eBann) {}
              try { flashHudNote("Dispatch failed · " + msg, 6000); } catch (eFHE) {}
            });
        });
        doors.appendChild(b);
      }
    } catch (eD) {}
  }


  var InspectPerson = {
    init: init,
    show: inspectPerson,
    paint: paintPersonDigIn,
  };

  function init(host) {
    if (!host || typeof host !== "object") return InspectPerson;
    Object.keys(host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return InspectPerson;
  }

  global.InspectPerson = InspectPerson;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = InspectPerson;
  }
})(typeof window !== "undefined" ? window : globalThis);
