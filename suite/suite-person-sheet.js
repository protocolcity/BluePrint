/**
 * suite-person-sheet.js — Agent dig-in (SUITE_SHELL S4)
 *
 * Click an agent → in-glass sheet over Map/Overview. The sheet is the dig-in;
 * /person full page is not promoted (direct URL still works).
 * ← Back (top-left) · Esc · backdrop · × close. Tickets/papers via SuitePaper.
 */
(function (global) {
  "use strict";

  var root = null;
  var bodyEl = null;
  var titleEl = null;
  var stateEl = null;
  var fullEl = null;
  var backEl = null;
  var currentName = "";
  var onCloseCb = null;
  var sheetDispatchLive = false;
  var sheetDispatchTimer = null;

  /* pc-1396: HTML escape lives in /esc.js */
  var esc = function (s) { return global.__bp.esc(s); };

  function nice(ts) {
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

  function ticketId(t) {
    if (t == null) return "";
    if (typeof t === "string") return t;
    return t.id || t.task_id || "";
  }

  function ticketTitle(t) {
    if (!t || typeof t !== "object") return "";
    return t.title || "";
  }

  function injectCss() {
    if (document.getElementById("suite-person-sheet-css")) return;
    var s = document.createElement("style");
    s.id = "suite-person-sheet-css";
    s.textContent =
      "html.suite-person-open{overflow:hidden}" +
      ".suite-person-sheet{position:fixed;inset:0;z-index:9250;pointer-events:none}" +
      ".suite-person-sheet.on{pointer-events:auto}" +
      ".suite-person-sheet[hidden]{display:none!important}" +
      ".sps-bg{position:absolute;inset:0;background:rgba(20,18,14,.35);opacity:0;transition:opacity .18s}" +
      ".suite-person-sheet.on .sps-bg{opacity:1}" +
      ".sps-panel{position:absolute;top:0;right:0;bottom:0;width:min(26rem,100%);" +
      "background:var(--card,#fffdf8);color:var(--ink,#1a1814);border-left:1px solid var(--border,#c4b8a4);" +
      "box-shadow:-8px 0 32px rgba(0,0,0,.12);display:flex;flex-direction:column;" +
      "transform:translateX(10px);opacity:0;transition:transform .18s,opacity .18s}" +
      ".suite-person-sheet.on .sps-panel{transform:none;opacity:1}" +
      ".sps-head{padding:12px 14px 14px;border-bottom:1px solid var(--border,#c4b8a4)}" +
      /* Top chrome: ← Back (left) · × (right) — no full-page promo */
      ".sps-top{display:flex;align-items:center;gap:10px;margin:0 0 8px}" +
      ".sps-back{font:inherit;font-size: var(--type-label);letter-spacing:.06em;text-transform:uppercase;" +
      "border:0;background:transparent;cursor:pointer;color:var(--finder-blue,#007AFF);" +
      "padding:0;font-weight: var(--weight-medium);flex:0 0 auto}" +
      ".sps-back:hover{text-decoration:underline}" +
      ".sps-top-spacer{flex:1 1 auto;min-width:0}" +
      ".sps-x{font:inherit;font-size: var(--type-display);line-height:1;border:0;background:transparent;cursor:pointer;" +
      "color:inherit;opacity:.55;padding:0 2px;flex:0 0 auto}" +
      ".sps-x:hover{opacity:1}" +
      ".sps-title-row{display:flex;align-items:center;gap:10px}" +
      ".sps-title-row h2{margin:0;flex:1;font-size: var(--type-heading);font-weight: var(--weight-medium);min-width:0;" +
      "overflow:hidden;text-overflow:ellipsis;white-space:nowrap}" +
      ".sps-badge{font-size: var(--type-label);letter-spacing:.06em;text-transform:uppercase;" +
      "padding:3px 8px;border:1px solid var(--border,#c4b8a4);border-radius:3px;opacity:.75;flex:0 0 auto}" +
      ".sps-badge.working{color:var(--alive,#2e7d4f);border-color:var(--alive,#2e7d4f);opacity:1;font-weight: var(--weight-medium)}" +
      ".sps-full{font-size: var(--type-label);letter-spacing:.06em;text-transform:uppercase;color:var(--gold,#b8860b)}" +
      ".sps-body{flex:1;overflow:auto;padding:14px 16px 28px}" +
      ".sps-meta{font-size: var(--type-body);opacity:.7;line-height:1.45;margin:0 0 14px}" +
      ".sps-sec{margin:16px 0 8px;font-size: var(--type-label);letter-spacing:.12em;text-transform:uppercase;opacity:.5;font-weight: var(--weight-medium)}" +
      ".sps-row{display:flex;gap:8px;padding:6px 0;border-bottom:1px solid var(--line-faint,rgba(0,0,0,.06));" +
      "font-size: var(--type-body);align-items:baseline}" +
      ".sps-row a{color:var(--verd,var(--ink));font-weight: var(--weight-medium);text-decoration:none}" +
      ".sps-row a:hover{color:var(--gold,#b8860b)}" +
      ".sps-row .dim{opacity:.55;font-size: var(--type-label)}" +
      ".sps-btn{font:inherit;font-size: var(--type-label);letter-spacing:.08em;text-transform:uppercase;" +
      "padding:8px 14px;border:1px solid var(--border,#c4b8a4);background:var(--card,#fff);" +
      "cursor:pointer;color:inherit;margin-top:8px}" +
      ".sps-btn:hover{border-color:var(--gold,#b8860b)}" +
      ".sps-btn:disabled{opacity:.45;cursor:default}" +
      ".sps-muted{opacity:.55;font-size: var(--type-body);margin:0 0 8px;line-height:1.4}" +
      ".sps-err{color:#a33;font-size: var(--type-body)}" +
      ".sps-now{padding:10px 12px;margin:0 0 12px;border:1px solid var(--border,#c4b8a4);" +
      "background:color-mix(in srgb,var(--card,#fff) 88%,var(--alive,#2e7d4f));border-radius:4px}" +
      ".sps-now.idle{background:var(--card,#fff)}" +
      ".sps-now .n-label{font-size: var(--type-label);letter-spacing:.1em;text-transform:uppercase;opacity:.55;margin-bottom:4px}" +
      ".sps-now .n-body{font-size: var(--type-body);font-weight: var(--weight-medium);line-height:1.35}" +
      ".sps-now .n-sub{font-size: var(--type-label);opacity:.65;margin-top:4px}" +
      ".sps-kv{display:grid;grid-template-columns:5.5rem minmax(0,1fr);gap:4px 10px;font-size: var(--type-body);margin:0 0 12px}" +
      ".sps-kv .k{opacity:.5;font-size: var(--type-label);letter-spacing:.06em;text-transform:uppercase;padding-top:2px}" +
      ".sps-kv .v{min-width:0;word-break:break-word}" +
      ".sps-model-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:0 0 4px}" +
      ".sps-model-row input{flex:1 1 8rem;min-width:0;font:inherit;font-size: var(--type-body);padding:5px 8px;" +
      "border:1px solid var(--border,#c4b8a4);background:var(--card,#fff);color:inherit;border-radius:3px}" +
      ".sps-model-row .sps-btn{margin-top:0;padding:5px 10px}" +
      ".sps-model-hint{font-size: var(--type-label);opacity:.55;line-height:1.35}" +
      ".sps-paper{display:block;padding:8px 0;border-bottom:1px solid var(--line-faint,rgba(0,0,0,.06));" +
      "text-decoration:none;color:inherit}" +
      ".sps-paper:hover .fn{color:var(--gold,#b8860b)}" +
      ".sps-paper .lv{font-size: var(--type-label);letter-spacing:.08em;text-transform:uppercase;opacity:.55}" +
      ".sps-paper .fn{font-size: var(--type-body);font-weight: var(--weight-medium);color:var(--verd,var(--ink));margin-top:2px}" +
      ".sps-paper .sm{font-size: var(--type-label);opacity:.5;margin-top:2px}" +
      ".sps-shift{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 10px;padding:7px 0;" +
      "border-bottom:1px solid var(--line-faint,rgba(0,0,0,.06));font-size: var(--type-body)}" +
      ".sps-shift .out{font-size: var(--type-label);letter-spacing:.05em;text-transform:uppercase;font-weight: var(--weight-medium);" +
      "padding:2px 6px;border:1px solid var(--border,#c4b8a4);border-radius:3px;align-self:start}" +
      ".sps-shift .out.ok,.sps-shift .out.done,.sps-shift .out.success{color:var(--alive,#2e7d4f);border-color:var(--alive,#2e7d4f)}" +
      ".sps-shift .out.skip{opacity:.65}" +
      ".sps-shift .out.err,.sps-shift .out.error,.sps-shift .out.fail,.sps-shift .out.failed," +
      ".sps-shift .out.crashed,.sps-shift .out.vendor_limit{color:#a33;border-color:#a33}" +
      ".sps-shift.is-attention{border-left:3px solid #a33;padding-left:8px;" +
      "background:color-mix(in srgb,#a33 7%,var(--card,#fffdf8));margin:2px 0;border-radius:3px}" +
      ".sps-shift.is-empty .out{opacity:.55}" +
      ".sps-shift .when{font-size: var(--type-label);opacity:.55}" +
      ".sps-shift .reason{font-size: var(--type-body);line-height:1.35}";
    document.head.appendChild(s);
  }

  /** Queue-empty / no-ready skip noise — not real throughput (pc-964 / §9).
   *  Preflight skips (low disk, CLI missing) stay meaningful at 0 passes (pc-1378). */
  function isEmptyCheckShift(s) {
    if (!s) return true;
    var outcome = String(s.outcome || "").toLowerCase();
    var reason = String(s.reason || "").toLowerCase();
    var passes = s.passes != null ? s.passes | 0 : 0;
    if (outcome === "skip" || outcome === "skipped") {
      return reason.indexOf("queue empty") >= 0 || reason.indexOf("no ready") >= 0;
    }
    if (outcome === "ok" && passes <= 0 && reason.indexOf("queue empty") >= 0)
      return true;
    if (outcome === "warn" && reason.indexOf("empty") >= 0) return true;
    return false;
  }

  function isFailShift(s) {
    if (!s) return false;
    var oc = String(s.outcome || "").toLowerCase();
    return (
      oc === "error" ||
      oc === "err" ||
      oc === "fault" ||
      oc === "failed" ||
      oc === "crashed" ||
      oc === "vendor_limit"
    );
  }

  function shiftTicketId(s) {
    if (!s || typeof s !== "object") return "";
    var cands = [s.ticket_id, s.task_id, s.tid, s.work_order, s.wo];
    for (var i = 0; i < cands.length; i++) {
      var v = String(cands[i] || "").trim();
      if (v && /^[a-z]{1,12}-\d+/i.test(v)) return v;
    }
    var blob = String(s.reason || s.why || s.summary || "");
    var m = blob.match(/\b([a-z]{1,12}-\d+)\b/i);
    return m ? m[1] : "";
  }

  /**
   * Meaningful first; trailing empty streak collapsed (pc-964).
   * Prefer BFF empty_checks / last_real_* when present.
   */
  function partitionShiftHistory(shifts, maxMeaningful) {
    var list = Array.isArray(shifts) ? shifts : [];
    var meaningful = [];
    var emptyN = 0;
    var lastEmpty = null;
    var firstEmpty = null;
    var lastRealTicket = "";
    var seenReal = false;
    for (var i = 0; i < list.length; i++) {
      var s = list[i];
      if (isEmptyCheckShift(s)) {
        if (!seenReal) {
          emptyN++;
          if (!lastEmpty) lastEmpty = s;
          firstEmpty = s;
        }
        continue;
      }
      if (!s) continue;
      seenReal = true;
      if (meaningful.length < (maxMeaningful || 6)) meaningful.push(s);
      if (!lastRealTicket) lastRealTicket = shiftTicketId(s);
    }
    return {
      meaningful: meaningful,
      emptyN: emptyN,
      lastEmpty: lastEmpty,
      firstEmpty: firstEmpty,
      lastRealTicket: lastRealTicket,
    };
  }

  function citizenShiftLabel(s) {
    if (!s) return "—";
    var outcome = String(s.outcome || "").toLowerCase();
    var passes = s.passes != null ? s.passes | 0 : null;
    var reason = String(s.reason || "").trim();
    if (outcome === "ok" || outcome === "success" || outcome === "done") {
      if (passes != null && passes > 0)
        return "Finished · " + passes + " pass" + (passes === 1 ? "" : "es");
      return "Finished · ok";
    }
    if (outcome === "vendor_limit")
      return "Vendor limit" + (reason ? " · " + reason.slice(0, 32) : "");
    if (isFailShift(s))
      return "Failed" + (reason ? " · " + reason.slice(0, 36) : "");
    if (outcome === "skip" || outcome === "skipped") {
      if (reason.toLowerCase().indexOf("queue empty") >= 0)
        return "Checked · nothing ready";
      return "Skipped" + (reason ? " · " + reason.slice(0, 36) : "");
    }
    if (outcome === "running") return "On shift";
    return String(s.outcome || "?");
  }

  function ensure() {
    if (root) return root;
    injectCss();
    root = document.createElement("div");
    root.id = "suite-person-sheet";
    root.className = "suite-person-sheet";
    root.hidden = true;
    root.innerHTML =
      '<div class="sps-bg" data-sps-close="1"></div>' +
      '<aside class="sps-panel" role="dialog" aria-modal="true" aria-labelledby="sps-title">' +
      '  <header class="sps-head">' +
      '    <div class="sps-top">' +
      '      <button type="button" class="sps-back" id="sps-back" title="Back">← Back</button>' +
      '      <span class="sps-top-spacer" aria-hidden="true"></span>' +
      '      <button type="button" class="sps-x" id="sps-close" title="Close" aria-label="Close">×</button>' +
      "    </div>" +
      '    <div class="sps-title-row">' +
      '      <h2 id="sps-title">—</h2>' +
      '      <span class="sps-badge" id="sps-state">—</span>' +
      "    </div>" +
      "  </header>" +
      '  <div class="sps-body" id="sps-body"><p class="sps-muted">Loading…</p></div>' +
      "</aside>";
    document.body.appendChild(root);
    bodyEl = root.querySelector("#sps-body");
    titleEl = root.querySelector("#sps-title");
    stateEl = root.querySelector("#sps-state");
    fullEl = null; /* full page no longer in sheet chrome */
    backEl = root.querySelector("#sps-back");
    root.querySelector("#sps-close").addEventListener("click", close);
    root.querySelector(".sps-bg").addEventListener("click", close);
    if (backEl) {
      backEl.addEventListener("click", function (e) {
        e.preventDefault();
        close(); /* onClose restores previous map sidebar */
      });
    }
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
    document.documentElement.classList.toggle("suite-person-open", on);
  }

  function close() {
    stopSheetDispatchFollow();
    sheetDispatchLive = false;
    setOpen(false);
    currentName = "";
    var cb = onCloseCb;
    onCloseCb = null;
    if (typeof cb === "function") {
      try {
        cb();
      } catch (e) {}
    }
  }

  function isOpen() {
    return !!(root && !root.hidden);
  }

  function shouldGlassIntercept() {
    var body = document.getElementById("suite-body");
    var room = body && body.getAttribute("data-suite-room");
    if (room === "map") return true;
    var path = (global.location && global.location.pathname) || "";
    if (path === "/" || path === "/workspace-map") return true;
    if (
      global.SuiteNav &&
      SuiteNav.isWorkspaceMapPath &&
      SuiteNav.isWorkspaceMapPath(path)
    ) {
      return true;
    }
    /* Parked keep-alive still counts as glass app */
    if (document.getElementById("suite-body-park-map")) return true;
    return false;
  }

  function openTicket(id) {
    if (!id) return;
    if (global.SuitePaper && typeof SuitePaper.openTicket === "function") {
      SuitePaper.openTicket(id);
      return;
    }
    global.location.href = "/ticket?id=" + encodeURIComponent(id);
  }

  function openPaper(path) {
    if (!path) return;
    if (global.SuitePaper && typeof SuitePaper.open === "function") {
      SuitePaper.open(path);
      return;
    }
    global.location.href = "/read?path=" + encodeURIComponent(path);
  }

  function lastShiftOf(w) {
    if (!w) return null;
    if (w.shifts && w.shifts[0]) return w.shifts[0];
    if (w.last_real_shift && typeof w.last_real_shift === "object") {
      return w.last_real_shift;
    }
    return null;
  }

  function stdoutIsStale(shift, mtime) {
    if (!mtime || !shift || !shift.ts) return false;
    var shiftTs = Date.parse(shift.ts);
    var outTs = Date.parse(mtime);
    if (isNaN(shiftTs) || isNaN(outTs)) return true;
    return outTs < shiftTs - 2000;
  }

  function workerState(w, inflightSet) {
    var name = (w && w.name) || "";
    var health = String((w && w.health) || "").toLowerCase();
    if (health === "err" || health === "error" || health === "fault") {
      return { id: "fault", label: "Fault", cls: "fault" };
    }
    if (sheetDispatchLive && name && name === currentName) {
      return { id: "working", label: "On shift", cls: "working" };
    }
    if (inflightSet && inflightSet.has(name)) {
      return { id: "working", label: "On shift", cls: "working" };
    }
    if (w && w.holding && w.holding.length) {
      return { id: "working", label: "On shift", cls: "working" };
    }
    var oc = String((lastShiftOf(w) || {}).outcome || "").toLowerCase();
    if (oc === "running" || oc === "in_progress") {
      return { id: "working", label: "On shift", cls: "working" };
    }
    var nf = w && w.next_fire;
    if (nf) {
      try {
        var ms = Date.parse(nf) - Date.now();
        if (ms > 0 && ms < 120000) {
          return { id: "soon", label: "Due soon", cls: "soon" };
        }
      } catch (e) {}
    }
    return { id: "idle", label: "Idle", cls: "" };
  }

  function render(w, inflightSet) {
    var display = w.display || w.name || currentName;
    var project =
      w.project ||
      (w.workdir || "").split("/").filter(Boolean).pop() ||
      "";
    var kind = String(w.kind || "worker").toLowerCase();
    var isJob = kind === "job";
    var st = workerState(w, inflightSet);
    if (titleEl) titleEl.textContent = display;
    if (stateEl) {
      stateEl.textContent = st.label;
      stateEl.className = "sps-badge" + (st.cls ? " " + st.cls : "");
    }
    var pay = [];
    if (w.cli) pay.push(String(w.cli));
    /* Model pin always named (pc-428) — empty = vendor default */
    var modelPin =
      w.model && w.model !== "default" ? String(w.model) : "";
    var modelLabel = modelPin || "vendor default";

    var held = w.holding || [];
    var ready = w.ready || [];
    var rawShifts = Array.isArray(w.shifts) ? w.shifts.slice() : [];
    if (!rawShifts.length && w.last_shift) rawShifts = [w.last_shift];
    if (!rawShifts.length && w.last_real_shift) rawShifts = [w.last_real_shift];
    var hist = partitionShiftHistory(rawShifts, 6);
    var ecMeta =
      w.empty_checks && typeof w.empty_checks === "object" ? w.empty_checks : null;
    if (ecMeta && (ecMeta.count | 0) > hist.emptyN) {
      hist.emptyN = ecMeta.count | 0;
      if (ecMeta.since || ecMeta.last_ts) {
        hist.firstEmpty = hist.firstEmpty || { ts: ecMeta.since || ecMeta.last_ts };
        hist.lastEmpty = hist.lastEmpty || { ts: ecMeta.last_ts || ecMeta.since };
      }
    }
    var lastReal =
      hist.meaningful[0] ||
      (w.last_real_shift && typeof w.last_real_shift === "object"
        ? w.last_real_shift
        : null);
    var lrtMeta =
      w.last_real_ticket && typeof w.last_real_ticket === "object"
        ? w.last_real_ticket
        : null;
    var lastRealTid =
      (lrtMeta && lrtMeta.id) ||
      hist.lastRealTicket ||
      (lastReal ? shiftTicketId(lastReal) : "") ||
      "";
    var lastRealTitle = (lrtMeta && lrtMeta.title) || "";

    /* —— This wake (hero) — pc-1310: ready[0] lead, or Holding on shift —— */
    var nowCls = held.length || st.id === "working" ? "sps-now" : "sps-now idle";
    var nowBody = "";
    var nowSub = "";
    var r0 = ready[0];
    var rid = ticketId(r0);
    var rti = ticketTitle(r0);
    if (held.length) {
      var h0 = held[0];
      var hid = ticketId(h0);
      var hti = ticketTitle(h0);
      nowBody =
        "Claimed " +
        hid +
        (hti ? " · " + String(hti).slice(0, 56) : "") +
        (held.length > 1 ? " (+" + (held.length - 1) + " more)" : "");
      nowSub = isJob ? "Running now" : "On shift";
    } else if (st.id === "working") {
      var cid = lastRealTid || rid;
      var cti = lastRealTitle || rti;
      nowBody = isJob
        ? "Running now"
        : cid
          ? "On shift · claiming " +
            cid +
            (cti ? " · " + String(cti).slice(0, 56) : "")
          : "On shift · claiming…";
      nowSub = "This wake";
    } else if (rid && !isJob) {
      nowBody =
        "Dispatch will claim " +
        rid +
        (rti ? " · " + String(rti).slice(0, 56) : "");
      nowSub = "This wake";
    } else if (lastReal || lastRealTid) {
      nowBody =
        "Last real · " +
        (lastRealTid ? lastRealTid : citizenShiftLabel(lastReal));
      nowSub =
        (lastRealTitle
          ? String(lastRealTitle).slice(0, 48) + " · "
          : lastReal
            ? citizenShiftLabel(lastReal) + " · "
            : "") +
        nice((lrtMeta && lrtMeta.ts) || (lastReal && lastReal.ts) || "");
    } else if (hist.emptyN > 0) {
      var sinceTs =
        (hist.firstEmpty && hist.firstEmpty.ts) ||
        (hist.lastEmpty && hist.lastEmpty.ts) ||
        "";
      nowBody = "Ready queue empty";
      nowSub =
        hist.emptyN +
        " empty check" +
        (hist.emptyN === 1 ? "" : "s") +
        " since " +
        (sinceTs ? nice(sinceTs) : "—");
    } else {
      nowBody = isJob ? "Idle" : "Ready queue empty";
      nowSub = "";
    }

    var html = "";
    html +=
      '<div class="' +
      nowCls +
      '"><div class="n-label">This wake</div>' +
      '<div class="n-body">' +
      esc(nowBody) +
      "</div>" +
      (nowSub ? '<div class="n-sub">' + esc(nowSub) + "</div>" : "") +
      "</div>";

    /* —— Identity / project / schedule —— */
    html += '<div class="sps-kv">';
    html +=
      '<div class="k">Project</div><div class="v"><b>' +
      esc(project || "—") +
      "</b>" +
      (w.workdir
        ? '<div class="dim" style="font-size: var(--type-label);opacity:.5;margin-top:2px">' +
          esc(w.workdir) +
          "</div>"
        : "") +
      "</div>";
    html +=
      '<div class="k">Role</div><div class="v">' +
      esc(isJob ? "Job · automated task" : "Agent · work-order lane") +
      (w.identity ? " · signs as " + esc(w.identity) : "") +
      (w.cli ? " · " + esc(String(w.cli)) : "") +
      "</div>";
    html +=
      '<div class="k">Model</div><div class="v">' +
      '<div class="sps-model-row">' +
      '<input type="text" id="sps-model-input" spellcheck="false" ' +
      'placeholder="vendor default" value="' +
      esc(modelPin) +
      '" aria-label="Model pin" />' +
      '<button type="button" class="sps-btn" id="sps-model-save">Save pin</button>' +
      "</div>" +
      '<div class="sps-model-hint" id="sps-model-status">Current · ' +
      esc(modelLabel) +
      " · empty = vendor default · next shift uses new pin</div>" +
      "</div>";
    html +=
      '<div class="k">Schedule</div><div class="v">' +
      (w.schedule
        ? "<code style=\"font-size: var(--type-label)\">" + esc(w.schedule) + "</code>"
        : "—") +
      (w.next_fire
        ? '<div class="dim" style="margin-top:3px">Next fire · ' +
          esc(nice(w.next_fire)) +
          "</div>"
        : "") +
      "</div>";
    if (w.health || w.why) {
      html +=
        '<div class="k">Health</div><div class="v">' +
        esc(w.health || "—") +
        (w.why ? " · " + esc(w.why) : "") +
        "</div>";
    }
    html += "</div>";

    /* —— Instructions they follow (MapChrome register · same as Map digs) —— */
    var instrSec =
      window.MapChrome && MapChrome.instructionSectionLabel
        ? MapChrome.instructionSectionLabel("hand")
        : "Instructions they follow";
    html += '<div class="sps-sec">' + esc(instrSec) + "</div>";
    var law = Array.isArray(w.law) ? w.law.slice() : [];
    var seenPath = {};
    law.forEach(function (e) {
      if (e && e.path) seenPath[e.path] = true;
    });
    function pushLaw(e) {
      if (!e) return;
      var p = e.path || "";
      if (p && seenPath[p]) return;
      if (p) seenPath[p] = true;
      law.push(e);
    }
    /** Overlay instruction face. Glass never stamps L0–L3 or *law* (pc-1385).
     *  MapChrome.instructionDepthLabel is canonical when present. */
    function citizenLawLabel(e) {
      var chrome = window.MapChrome;
      if (chrome && chrome.instructionDepthLabel) {
        return chrome.instructionDepthLabel(e) || "rules";
      }
      if (!e) return "rules";
      var lv = String(e.level || "").toUpperCase();
      var lab = String(e.label || "").toLowerCase();
      var fn = String(e.file || e.name || "").toLowerCase();
      if (
        lv === "L0" ||
        lab.indexOf("city") >= 0 ||
        lab.indexOf("workspace") >= 0
      ) {
        return "workspace";
      }
      if (
        lv === "L1" ||
        lab.indexOf("neighborhood") >= 0 ||
        lab.indexOf("project") >= 0
      ) {
        return "project";
      }
      if (lv === "L2" || fn === "contract.md" || lab.indexOf("contract") >= 0) {
        return "contract";
      }
      if (lv === "L3" || fn === "prompt.md" || lab.indexOf("prompt") >= 0) {
        return "this run";
      }
      if (e.citizen_label) {
        var cit = String(e.citizen_label);
        if (!/\bL[0-3]\b/.test(cit) && !/\blaw\b/i.test(cit)) return cit;
        var cl = cit.toLowerCase();
        if (cl.indexOf("workspace") >= 0 || cl.indexOf("city") >= 0) {
          return "workspace";
        }
        if (cl.indexOf("project") >= 0 || cl.indexOf("neighborhood") >= 0) {
          return "project";
        }
      }
      if (e.label) return String(e.label);
      return "rules";
    }
    function lawReadRel(raw) {
      var cityRoot =
        (window.__suiteCityRoot ||
          (window.model && window.model.city && window.model.city.city_root) ||
          "") + "";
      if (window.MapChrome && MapChrome.instructionCityRel) {
        return MapChrome.instructionCityRel(raw, cityRoot) || "";
      }
      if (!raw) return "";
      var p = String(raw).replace(/\\/g, "/");
      var root = cityRoot.replace(/\\/g, "/").replace(/\/+$/, "");
      if (root && p.indexOf(root + "/") === 0) return p.slice(root.length + 1);
      if (p.charAt(0) !== "/") return p.replace(/^\.\//, "");
      return p.replace(/^\//, "");
    }
    /* Prefer API law[]; fill contract/prompt if missing from stack */
    var hasL2 = law.some(function (e) {
      return e && String(e.level || "").toUpperCase() === "L2";
    });
    var hasL3 = law.some(function (e) {
      return e && String(e.level || "").toUpperCase() === "L3";
    });
    if (!hasL2 && w.contract_path) {
      pushLaw({
        level: "L2",
        label: "contract",
        citizen_label: "Contract",
        file: "CONTRACT.md",
        path: w.contract_path,
        readable: true,
      });
    }
    if (!hasL3 && w.prompt_path) {
      pushLaw({
        level: "L3",
        label: "prompt",
        citizen_label: "This run",
        file: "prompt.md",
        path: w.prompt_path,
        readable: true,
      });
    }
    if (!law.length) {
      html +=
        '<p class="sps-muted">No instruction stack published for this agent</p>';
    } else {
      law.forEach(function (e) {
        if (!e) return;
        var p = e.path || "";
        var rel = lawReadRel(p);
        var file = e.file || (p ? String(p).split("/").pop() : "") || "—";
        var face = citizenLawLabel(e);
        var openable = !!(e.readable !== false && rel);
        if (openable) {
          html +=
            '<a class="sps-paper" href="/read?path=' +
            encodeURIComponent(rel) +
            '" data-sps-paper="' +
            esc(rel) +
            '">' +
            '<div class="lv">' +
            esc(face) +
            "</div>" +
            '<div class="fn">' +
            esc(file) +
            "</div>" +
            '<div class="sm">' +
            esc(rel) +
            (e.sha ? " · " + esc(e.sha) : "") +
            "</div></a>";
        } else {
          html +=
            '<div class="sps-paper" style="opacity:.55">' +
            '<div class="lv">' +
            esc(face) +
            "</div>" +
            '<div class="fn">' +
            esc(file) +
            "</div>" +
            '<div class="sm">not readable in workspace tree</div></div>';
        }
      });
    }

    /* —— Skills on disk (pc-411) —— */
    var skills = Array.isArray(w.skills) ? w.skills : [];
    html += '<div class="sps-sec">Skills</div>';
    if (!skills.length) {
      html +=
        '<p class="sps-muted">No skills folders found under this project or workspace ' +
        "(.claude/skills · .cursor/skills). Skills are capability papers chat AI maintains — " +
        "Map dig-in also groups them under Skills.</p>";
    } else {
      skills.slice(0, 24).forEach(function (s) {
        if (!s) return;
        var sp = s.path || "";
        var sid = s.id || s.name || (sp ? String(sp).split("/").pop() : "skill");
        if (!sp) return;
        html +=
          '<a class="sps-paper" href="/read?path=' +
          encodeURIComponent(sp) +
          '" data-sps-paper="' +
          esc(sp) +
          '">' +
          '<div class="lv">skill</div>' +
          '<div class="fn">' +
          esc(sid) +
          "</div>" +
          '<div class="sm">' +
          esc(sp) +
          "</div></a>";
      });
    }

    /* —— Ops/job report papers (pc-432) —— */
    var reports = Array.isArray(w.reports)
      ? w.reports
      : (w.outputs && w.outputs.reports) || [];
    if (isJob || (reports && reports.length)) {
      html += '<div class="sps-sec">Reports · job deliverables</div>';
      if (!reports.length) {
        html +=
          '<p class="sps-muted">No report files yet — after this job runs, dated ' +
          ".md land under ops reports (openable here).</p>";
      } else {
        reports.slice(0, 8).forEach(function (r) {
          var rp = (r && r.path) || "";
          var rn = (r && r.name) || (rp ? String(rp).split("/").pop() : "report");
          if (!rp) return;
          html +=
            '<a class="sps-paper" href="/read?path=' +
            encodeURIComponent(rp) +
            '" data-sps-paper="' +
            esc(rp) +
            '">' +
            '<div class="lv">report</div>' +
            '<div class="fn">' +
            esc(rn) +
            "</div>" +
            '<div class="sm">' +
            esc(rp) +
            (r.mtime ? " · " + esc(nice(r.mtime)) : "") +
            "</div></a>";
        });
      }
    }

    /* —— Tickets: holding only while on shift (idle lead already named ready[0]) —— */
    if (held.length || st.id === "working") {
      html += '<div class="sps-sec">Tickets · claimed now</div>';
      if (held.length) {
        held.slice(0, 10).forEach(function (t) {
          var id = ticketId(t);
          var title = ticketTitle(t);
          html +=
            '<div class="sps-row"><a href="/ticket?id=' +
            encodeURIComponent(id) +
            '" data-sps-ticket="' +
            esc(id) +
            '">' +
            esc(id) +
            "</a>" +
            (title
              ? '<span class="dim"> · ' +
                esc(String(title).slice(0, 52)) +
                (String(title).length > 52 ? "…" : "") +
                "</span>"
              : "") +
            "</div>";
        });
      } else {
        html +=
          '<p class="sps-muted">On shift · waiting for claim</p>';
      }
    }

    var claimedIds = {};
    held.forEach(function (t) {
      var id = ticketId(t);
      if (id) claimedIds[id] = true;
    });
    if (st.id === "working") {
      if (lastRealTid) claimedIds[lastRealTid] = true;
      if (rid) claimedIds[rid] = true;
    }
    var readyRest = (st.id === "working" ? ready : ready.slice(1)).filter(
      function (t) {
        var id = ticketId(t);
        return !id || !claimedIds[id];
      }
    );
    html += '<div class="sps-sec">Tickets · ready in lane</div>';
    if (readyRest.length) {
      readyRest.slice(0, 8).forEach(function (t) {
        var id = ticketId(t);
        var title = ticketTitle(t);
        html +=
          '<div class="sps-row"><a href="/ticket?id=' +
          encodeURIComponent(id) +
          '" data-sps-ticket="' +
          esc(id) +
          '">' +
          esc(id) +
          "</a>" +
          (title
            ? '<span class="dim"> · ' +
              esc(String(title).slice(0, 48)) +
              "</span>"
            : "") +
          "</div>";
      });
    } else if (ready.length && st.id !== "working") {
      html +=
        '<p class="sps-muted">Lead is this wake · no further ready</p>';
    } else {
      html +=
        '<p class="sps-muted">Ready queue empty or not published</p>';
    }

    var outputs = w.outputs || {};
    var lastShift = lastShiftOf(w);
    if (stdoutIsStale(lastShift, outputs.stdout_mtime)) {
      html +=
        '<p class="sps-muted">Last out is stale · file ' +
        esc(nice(outputs.stdout_mtime)) +
        (lastShift && lastShift.ts
          ? " · last shift " + esc(nice(lastShift.ts))
          : "") +
        "</p>";
    }

    /* —— Recent history (pc-964: last real first; empty checks collapsed) —— */
    html +=
      '<div class="sps-sec">' +
      (isJob ? "Recent runs" : "Recent work") +
      (hist.meaningful.length ? " · " + hist.meaningful.length : "") +
      "</div>";
    if (!hist.meaningful.length && !hist.emptyN) {
      html += '<p class="sps-muted">No shifts recorded yet</p>';
    } else {
      if (lastRealTid && !held.length) {
        html +=
          '<div class="sps-shift' +
          (lastReal && isFailShift(lastReal) ? " is-attention" : "") +
          '">' +
          '<span class="out ok">last</span>' +
          "<div>" +
          '<div class="reason"><a href="/ticket?id=' +
          encodeURIComponent(lastRealTid) +
          '" data-sps-ticket="' +
          esc(lastRealTid) +
          '">' +
          esc(lastRealTid) +
          "</a>" +
          (lastRealTitle
            ? '<span class="dim"> · ' +
              esc(String(lastRealTitle).slice(0, 48)) +
              "</span>"
            : "") +
          "</div>" +
          '<div class="when">' +
          esc(
            nice(
              (lrtMeta && lrtMeta.ts) || (lastReal && lastReal.ts) || ""
            )
          ) +
          (lastReal ? " · " + esc(citizenShiftLabel(lastReal)) : "") +
          "</div></div></div>";
      }
      hist.meaningful.forEach(function (s) {
        var out = String(s.outcome || "?").toLowerCase();
        var tidS = shiftTicketId(s);
        var fail = isFailShift(s);
        html +=
          '<div class="sps-shift' +
          (fail ? " is-attention" : "") +
          '">' +
          '<span class="out ' +
          esc(out) +
          '">' +
          esc(fail ? "fail" : s.outcome || "?") +
          "</span>" +
          "<div>" +
          '<div class="when">' +
          esc(nice(s.ts)) +
          (s.passes != null && s.passes > 0 ? " · " + s.passes + " pass" : "") +
          (s.dry_run ? " · dry-run" : "") +
          "</div>" +
          '<div class="reason">' +
          (tidS
            ? '<a href="/ticket?id=' +
              encodeURIComponent(tidS) +
              '" data-sps-ticket="' +
              esc(tidS) +
              '">' +
              esc(tidS) +
              "</a> · "
            : "") +
          esc(citizenShiftLabel(s)) +
          "</div>" +
          (s.reason && !isEmptyCheckShift(s) && citizenShiftLabel(s).indexOf(s.reason) < 0
            ? '<div class="when">' + esc(String(s.reason).slice(0, 80)) + "</div>"
            : "") +
          "</div></div>";
      });
      if (hist.emptyN > 0) {
        var sinceEmpty =
          (hist.firstEmpty && hist.firstEmpty.ts) ||
          (hist.lastEmpty && hist.lastEmpty.ts) ||
          "";
        html +=
          '<div class="sps-shift is-empty">' +
          '<span class="out skip">empty</span>' +
          "<div>" +
          '<div class="reason">' +
          esc(
            hist.emptyN +
              " empty check" +
              (hist.emptyN === 1 ? "" : "s") +
              " since " +
              (sinceEmpty ? nice(sinceEmpty) : "—")
          ) +
          "</div>" +
          '<div class="when">Queue-empty skips · not real throughput</div>' +
          "</div></div>";
      }
    }

    /* —— Actions —— */
    /* pc-555: Skip next queue-check while Approaching / due-soon only */
    var canSkipRound = st.id === "soon" && !(w && w.working);
    html +=
      '<div class="sps-sec">Actions</div>' +
      '<button type="button" class="sps-btn" id="sps-dispatch"' +
      (st.id === "working" ? " disabled" : "") +
      ">" +
      (st.id === "working"
        ? isJob
          ? "Running"
          : "On shift"
        : "Dispatch now") +
      "</button>" +
      (canSkipRound
        ? '<button type="button" class="sps-btn" id="sps-skip" style="margin-top:6px">Skip this round</button>'
        : "") +
      '<p class="sps-muted" id="sps-dispatch-status" style="margin-top:8px"></p>' +
      '<p class="sps-muted" style="margin-top:8px"><a href="/workspace-map?you=decide">For You on Map</a> · Esc or ← Back</p>';

    bodyEl.innerHTML = html;

    bodyEl.querySelectorAll("[data-sps-ticket]").forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey) return;
        e.preventDefault();
        openTicket(a.getAttribute("data-sps-ticket"));
      });
    });
    bodyEl.querySelectorAll("[data-sps-paper]").forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey) return;
        e.preventDefault();
        openPaper(a.getAttribute("data-sps-paper"));
      });
    });

    var dBtn = bodyEl.querySelector("#sps-dispatch");
    var dSt = bodyEl.querySelector("#sps-dispatch-status");
    if (dBtn && st.id !== "working") {
      dBtn.addEventListener("click", function () {
        var who = w.name || display;
        if (
          !confirm(
            "Dispatch " +
              who +
              " now?\n\nRuns a real " +
              (isJob ? "job" : "agent") +
              " shift under their contract (same path as the schedule)."
          )
        ) {
          return;
        }
        dBtn.disabled = true;
        dBtn.textContent = "Dispatching…";
        if (dSt) dSt.textContent = "Contacting WorkForce…";
        fetch("/api/dispatch/" + encodeURIComponent(w.name || currentName), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        })
          .then(function (r) {
            return r.json().then(function (d) {
              return { r: r, d: d || {} };
            });
          })
          .then(function (pack) {
            var r = pack.r;
            var d = pack.d;
            var why = d.msg || d.error || ("HTTP " + r.status);
            if (!r.ok || d.ok === false) {
              dBtn.disabled = false;
              dBtn.textContent = "Dispatch now";
              if (dSt) dSt.textContent = "Refused · " + why;
              alert((w.name || who) + ": " + why);
              return;
            }
            dBtn.textContent = isJob ? "Running" : "On shift";
            if (dSt) {
              dSt.textContent =
                "OK · " +
                (w.name || who) +
                " · " +
                (d.msg || "shift started") +
                " · following this wake";
            }
            try {
              localStorage.setItem(
                "pc-map-dispatch",
                JSON.stringify({
                  name: w.name || currentName,
                  project: project || "",
                  at: Date.now(),
                })
              );
            } catch (eSig) {}
            followSheetDispatch(w.name || currentName);
          })
          .catch(function (err) {
            dBtn.disabled = false;
            dBtn.textContent = "Dispatch now";
            var m = (err && err.message) || String(err);
            if (dSt) dSt.textContent = "Failed · " + m;
            alert("Dispatch failed: " + m);
          });
      });
    }
    var sBtn = bodyEl.querySelector("#sps-skip");
    if (sBtn) {
      sBtn.addEventListener("click", function () {
        var who = w.name || currentName;
        if (!who) return;
        sBtn.disabled = true;
        sBtn.textContent = "Skipping…";
        if (dSt) dSt.textContent = "Skipping this queue-check round…";
        fetch("/api/skip/" + encodeURIComponent(who), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        })
          .then(function (r) {
            return r.json().then(function (d) {
              return { r: r, d: d || {} };
            });
          })
          .then(function (pack) {
            var d = pack.d || {};
            var why = d.msg || d.error || ("HTTP " + pack.r.status);
            if (!pack.r.ok || d.ok === false) {
              sBtn.disabled = false;
              sBtn.textContent = "Skip this round";
              if (dSt) dSt.textContent = "Skip refused · " + why;
              alert((who || "agent") + ": " + why);
              return;
            }
            sBtn.textContent = "Skipped this round";
            if (dSt) {
              dSt.textContent =
                "OK · skipped " +
                (d.skipped_fire || "this fire") +
                " · next schedule still stands";
            }
            try {
              /* Notify Map soft-state if open in same origin tab family */
              localStorage.setItem(
                "pc-map-skip",
                JSON.stringify({
                  name: who,
                  next_fire: d.skipped_fire || w.next_fire || "",
                  at: Date.now(),
                })
              );
            } catch (eSk) {}
          })
          .catch(function (err) {
            sBtn.disabled = false;
            sBtn.textContent = "Skip this round";
            var m = (err && err.message) || String(err);
            if (dSt) dSt.textContent = "Skip failed · " + m;
            alert("Skip failed: " + m);
          });
      });
    }

    /* pc-428: save model pin to local roster */
    var mIn = bodyEl.querySelector("#sps-model-input");
    var mSave = bodyEl.querySelector("#sps-model-save");
    var mSt = bodyEl.querySelector("#sps-model-status");
    if (mSave && mIn) {
      mSave.addEventListener("click", function () {
        var pin = String(mIn.value || "").trim();
        mSave.disabled = true;
        if (mSt) mSt.textContent = "Saving…";
        fetch(
          "/api/worker/" + encodeURIComponent(w.name || currentName) + "/model",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model: pin }),
          }
        )
          .then(function (r) {
            return r.json().then(function (d) {
              if (!r.ok) throw new Error((d && d.error) || r.statusText);
              return d;
            });
          })
          .then(function (d) {
            w.model = (d && d.model) || pin;
            mSave.disabled = false;
            if (mSt) {
              mSt.textContent =
                "Saved · " +
                (w.model ? w.model : "vendor default") +
                " · next shift uses this pin";
            }
          })
          .catch(function (err) {
            mSave.disabled = false;
            if (mSt) {
              mSt.textContent =
                "Save failed: " + ((err && err.message) || err);
            }
          });
      });
    }
  }

  function peekInflight() {
    var set = new Set();
    try {
      var scene =
        global.SuiteData && typeof SuiteData.peek === "function"
          ? SuiteData.peek("people")
          : null;
      var list = (scene && scene.in_flight) || [];
      for (var i = 0; i < list.length; i++) set.add(list[i]);
    } catch (e) {}
    return set;
  }

  var lastWorker = null;

  function stopSheetDispatchFollow() {
    if (sheetDispatchTimer) {
      clearInterval(sheetDispatchTimer);
      sheetDispatchTimer = null;
    }
  }

  function fetchWorker(name) {
    return fetch("/api/worker/" + encodeURIComponent(name), {
      cache: "no-store",
      credentials: "same-origin",
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error((d && d.error) || r.statusText);
        return d;
      });
    });
  }

  /** pc-1310: follow Dispatch in-sheet — no reload hunt, no Loading flash. */
  function followSheetDispatch(name) {
    name = String(name || "").trim();
    if (!name) return;
    sheetDispatchLive = true;
    stopSheetDispatchFollow();
    var tries = 0;
    var inflightSet = peekInflight();
    inflightSet.add(name);
    if (lastWorker && lastWorker.name === name) {
      render(lastWorker, inflightSet);
    }
    function tick() {
      tries += 1;
      fetchWorker(name)
        .then(function (w) {
          if (currentName !== name) return;
          lastWorker = w;
          var oc = String((lastShiftOf(w) || {}).outcome || "").toLowerCase();
          var held = w.holding || [];
          var running =
            oc === "running" || oc === "in_progress" || held.length > 0;
          var skip = oc === "skip" || oc === "skipped" || oc === "error";
          if (running || skip || tries >= 16) {
            sheetDispatchLive = running && !skip;
            stopSheetDispatchFollow();
          }
          render(w, inflightSet);
        })
        .catch(function () {});
    }
    tick();
    sheetDispatchTimer = setInterval(tick, 900);
  }

  /**
   * open(name) or open(name, { onClose: fn })
   * ← Back is always top-left (closes sheet; onClose restores map sidebar).
   * onClose runs once when the sheet closes (Back, ×, Esc, backdrop).
   * pc-1309: paint from /api/worker; /api/people must not block first paint.
   */
  function open(name, opts) {
    opts = opts || {};
    name = String(name || "").trim();
    if (!name) return;
    currentName = name;
    onCloseCb = typeof opts.onClose === "function" ? opts.onClose : null;
    ensure();
    if (titleEl) titleEl.textContent = name;
    if (stateEl) {
      stateEl.textContent = "…";
      stateEl.className = "sps-badge";
    }
    bodyEl.innerHTML = '<p class="sps-muted">Loading agent…</p>';
    setOpen(true);

    var inflightSet = peekInflight();
    lastWorker = null;

    var workerP = fetch("/api/worker/" + encodeURIComponent(name), {
      cache: "no-store",
      credentials: "same-origin",
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error((d && d.error) || r.statusText);
        return d;
      });
    });

    workerP
      .then(function (w) {
        if (currentName !== name) return;
        lastWorker = w;
        render(w, inflightSet);
      })
      .catch(function (err) {
        if (currentName !== name) return;
        bodyEl.innerHTML =
          '<p class="sps-err">Could not load agent.</p>' +
          '<p class="sps-muted">' +
          esc((err && err.message) || err) +
          "</p>" +
          '<p><a class="sps-full" href="/person?name=' +
          encodeURIComponent(name) +
          '">Open full page</a></p>';
      });

    fetch("/api/people", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.ok ? r.json() : {};
      })
      .then(function (scene) {
        (scene.in_flight || []).forEach(function (n) {
          inflightSet.add(n);
        });
        if (global.SuiteData && SuiteData.put) {
          try {
            SuiteData.put("people", scene);
          } catch (e) {}
        }
        if (currentName !== name) return;
        if (lastWorker) render(lastWorker, inflightSet);
      })
      .catch(function () {});
  }

  function nameFromHref(href) {
    try {
      var u = new URL(href, global.location.origin);
      if (u.pathname !== "/person" && u.pathname !== "/person_v1.html") {
        return null;
      }
      return (u.searchParams.get("name") || "").trim() || null;
    } catch (e) {
      return null;
    }
  }

  function install() {
    if (install._done) return;
    install._done = true;
    document.addEventListener(
      "click",
      function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (e.defaultPrevented) return;
        var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
        if (!a) return;
        if (
          a.classList.contains("sps-full") ||
          a.getAttribute("data-suite-full") === "1"
        ) {
          return;
        }
        var href = a.getAttribute("href") || "";
        var name = nameFromHref(href);
        if (!name) return;
        if (!shouldGlassIntercept()) return;
        e.preventDefault();
        e.stopPropagation();
        open(name);
      },
      true
    );
  }

  global.SuitePersonSheet = {
    open: open,
    close: close,
    isOpen: isOpen,
    install: install,
  };

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", install);
    } else {
      install();
    }
  }
})(typeof window !== "undefined" ? window : globalThis);
