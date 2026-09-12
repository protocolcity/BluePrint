/*! suite-live.js — shared live bus (pc-371) + continuous cinema (pc-392)
 * Composes SuitePulse (Layer B) + WorkLane transition SSE (Layer C)
 * + optional cinema heartbeat (always-on soft refresh while visible)
 * + slow reconcile + visibility re-arm.
 *
 * Disk+stores remain truth; this is projection freshness only.
 *
 * Continuous cinema is intentional: the map is the ops verification surface.
 * Pulse alone can miss a beat; heartbeat + SSE tail-from-now keep the stage live.
 *
 * Usage:
 *   SuiteLive.start({
 *     keys: ["city", "tickets", "people"],
 *     pulseUrl: "/api/pulse",
 *     pulseInterval: 900,
 *     reconcileMs: 60000,
 *     sse: true,
 *     sseTail: true,           // skip historical event dump (default true)
 *     cinema: true,            // always-on light heartbeat while visible
 *     heartbeatMs: 2200,
 *     debounceMs: 100,
 *     sseDebounceMs: 60,
 *     onRefresh: function (reason) {},
 *     onHeartbeat: function () {},  // optional; defaults to onRefresh("heartbeat")
 *     onTapeEvent: function (data) {}, // raw SSE JSON — same-tick theater
 *     onTransport: function (mode) {},
 *     forceOnVisible: true
 *   });
 */
(function (global) {
  "use strict";

  var _opts = null;
  var _timer = null; // reconcile
  var _heartbeat = null;
  var _refreshTimer = null;
  var _refreshBusy = false;
  var _tapeEs = null;
  var _transport = "pulse";
  var _visHandler = null;
  var _running = false;
  var _sseCatchupUntil = 0;
  var _lastRefreshAt = 0;

  /**
   * Dig-in overlays (paper / person / settings) own the glass — skip cinema
   * heartbeat + pulse-driven map thrash so reading a report does not lag.
   * pc-886.
   */
  function _overlayOpen() {
    try {
      if (typeof document === "undefined") return false;
      var cl = document.documentElement && document.documentElement.classList;
      if (!cl) return false;
      /* Dig-in sheets only. theater-paused freezes CSS/FX on Map but must
       * NOT kill pulse/data — otherwise first paint / LIVE go STALE forever. */
      return (
        cl.contains("suite-paper-open") ||
        cl.contains("suite-person-open") ||
        cl.contains("suite-settings-open")
      );
    } catch (e) {
      return false;
    }
  }

  function _setTransport(mode) {
    if (_transport === mode) return;
    _transport = mode;
    if (_opts && typeof _opts.onTransport === "function") {
      try {
        _opts.onTransport(mode);
      } catch (e) {}
    }
  }

  function _sseUrl() {
    var base = (_opts && _opts.sseUrl) || "/api/events/stream";
    var params = [];
    /* pc-1114: removed since=999999999 sentinel — it was higher than any real per-store
     * autoincrement id (WHERE id > 999999999 → empty forever). Age-check in onTape now
     * guards against historical catchup triggering theater for stale events. */
    if (_opts && _opts.project) {
      params.push("project=" + encodeURIComponent(_opts.project));
    }
    if (_opts && _opts.sseInterval) {
      params.push("interval=" + encodeURIComponent(String(_opts.sseInterval)));
    }
    if (!params.length) return base;
    var sep = base.indexOf("?") >= 0 ? "&" : "?";
    return base + sep + params.join("&");
  }

  function _closeTape() {
    if (!_tapeEs) return;
    try {
      _tapeEs.close();
    } catch (e) {}
    _tapeEs = null;
  }

  function _armTape() {
    _closeTape();
    if (!_opts || !_opts.sse) return;
    if (!global.EventSource) {
      _setTransport("pulse");
      return;
    }
    if (
      typeof document !== "undefined" &&
      document.visibilityState === "hidden"
    ) {
      _setTransport("pulse");
      return;
    }
    try {
      _tapeEs = new EventSource(_sseUrl());
    } catch (e) {
      _setTransport("pulse");
      return;
    }
    /* Catchup window: events during first 800ms trigger a debounced refresh only,
     * not theater — protects against replaying a burst of old events on connect. */
    _sseCatchupUntil = Date.now() + 800;
    _tapeEs.onopen = function () {
      var mode = _opts && _opts.cinema ? "cinema" : "sse+pulse";
      _setTransport(mode);
    };
    function onTape(ev) {
      /* Parse once at entry — shared by age-check and theater call. */
      var raw = ev && (ev.data != null ? ev.data : null);
      var parsed = null;
      if (raw && typeof raw === "string") {
        try { parsed = JSON.parse(raw); } catch (ep) {}
      } else if (raw && typeof raw === "object") {
        parsed = raw;
      }
      /* pc-1114: skip historical catchup events (older than 90s since SSE starts at
       * since=0 now). Prevents stale transitions from triggering theater/refresh after
       * the 800ms catchup window while the server replays old event ids. */
      if (parsed && parsed.created_at) {
        try {
          if (Date.now() - new Date(parsed.created_at).getTime() > 90000) return;
        } catch (eAge) {}
      }
      /* Same-tick theater before bootstrap poll (pc-397) */
      if (
        _opts &&
        typeof _opts.onTapeEvent === "function" &&
        parsed &&
        Date.now() >= _sseCatchupUntil &&
        !_overlayOpen()
      ) {
        try {
          _opts.onTapeEvent(parsed);
        } catch (eTape) {}
      }
      if (Date.now() < _sseCatchupUntil) {
        _scheduleRefresh("tape-catchup", true);
        return;
      }
      _scheduleRefresh("tape", true);
    }
    _tapeEs.addEventListener("status_change", onTape);
    _tapeEs.onmessage = onTape;
    _tapeEs.onerror = function () {
      _closeTape();
      /* Pulse + heartbeat remain; re-arm SSE later via visibility/reconcile */
      if (_opts && _opts.cinema) _setTransport("cinema");
      else _setTransport("pulse");
    };
  }

  function _debounceMs(reason, isSse) {
    if (isSse && _opts && _opts.sseDebounceMs != null) {
      return _opts.sseDebounceMs;
    }
    if (reason === "sse" || reason === "tape" || reason === "tape-catchup") {
      if (_opts && _opts.sseDebounceMs != null) return _opts.sseDebounceMs;
    }
    if (reason === "heartbeat") {
      return (_opts && _opts.heartbeatDebounceMs != null)
        ? _opts.heartbeatDebounceMs
        : 40;
    }
    return _opts && _opts.debounceMs != null ? _opts.debounceMs : 280;
  }

  function _scheduleRefresh(reason, isSse) {
    if (!_opts) return;
    if (_refreshTimer) clearTimeout(_refreshTimer);
    var ms = _debounceMs(reason, isSse);
    _refreshTimer = setTimeout(function () {
      _refreshTimer = null;
      if (_refreshBusy) return;
      _refreshBusy = true;
      _lastRefreshAt = Date.now();
      var done = function () {
        _refreshBusy = false;
      };
      try {
        var ret =
          typeof _opts.onRefresh === "function"
            ? _opts.onRefresh(reason || "live")
            : null;
        if (ret && typeof ret.then === "function") {
          ret.then(done, done);
        } else {
          done();
        }
      } catch (e) {
        done();
      }
    }, ms);
  }

  function _runReconcile() {
    if (!_opts) return;
    if (typeof _opts.onReconcile === "function") {
      try {
        _opts.onReconcile();
      } catch (e) {}
      return;
    }
    _scheduleRefresh("reconcile", false);
    /* Re-arm SSE if it dropped */
    if (_opts.sse && !_tapeEs) _armTape();
  }

  function _runHeartbeat() {
    if (!_opts || !_opts.cinema) return;
    if (
      typeof document !== "undefined" &&
      document.visibilityState === "hidden"
    ) {
      return;
    }
    /* Skip if a full refresh just ran (avoid double bootstrap) */
    if (Date.now() - _lastRefreshAt < 400) return;
    if (typeof _opts.onHeartbeat === "function") {
      try {
        var ret = _opts.onHeartbeat();
        if (ret && typeof ret.then === "function") {
          /* fire-and-forget */
        }
      } catch (e) {}
      return;
    }
    _scheduleRefresh("heartbeat", false);
  }

  function _onVisibility() {
    if (typeof document === "undefined") return;
    if (document.visibilityState === "visible") {
      _armTape();
      _armHeartbeat();
      if (_opts && _opts.forceOnVisible !== false && global.SuitePulse) {
        try {
          SuitePulse.force();
        } catch (e) {}
      }
      _scheduleRefresh("visible", false);
    } else {
      _closeTape();
      _disarmHeartbeat();
      _setTransport("pulse");
    }
  }

  function _armPulse() {
    if (!global.SuitePulse || !_opts) return;
    var keys = _opts.keys;
    if (!keys || !keys.length) return;
    /* pc-1092: one pulse loop — stop any SuiteData.watchPulse before SuitePulse */
    if (
      global.SuiteData &&
      typeof global.SuiteData.stopPulseWatch === "function"
    ) {
      try {
        global.SuiteData.stopPulseWatch();
      } catch (eStop) {}
    }
    SuitePulse.stop();
    var interval = _opts.pulseInterval;
    if (interval == null) {
      interval = _opts.cinema ? 900 : 1500;
    }
    SuitePulse.start({
      keys: keys,
      pulseUrl: _opts.pulseUrl,
      interval: interval,
      onChange: function (changed, pulse) {
        /* Keep SuiteData cache honest when rooms use SuiteLive not watchPulse */
        if (global.SuiteData && typeof global.SuiteData.notePulse === "function") {
          try {
            global.SuiteData.notePulse(pulse || { sources: {} });
          } catch (eNote) {}
        }
        var reason =
          "pulse:" +
          ((changed && changed.join && changed.join(",")) || "token");
        _scheduleRefresh(reason, false);
      },
      onPulse: function (pulse) {
        if (global.SuiteData && typeof global.SuiteData.notePulse === "function") {
          try {
            global.SuiteData.notePulse(pulse || { sources: {} });
          } catch (eNote2) {}
        }
        if (typeof _opts.onPulse === "function") _opts.onPulse(pulse);
      },
    });
  }

  function _armReconcile() {
    if (_timer) {
      clearInterval(_timer);
      _timer = null;
    }
    var ms = _opts && _opts.reconcileMs;
    if (ms == null) ms = _opts && _opts.cinema ? 60000 : 120000;
    if (!ms || ms <= 0) return;
    _timer = setInterval(_runReconcile, ms);
  }

  function _armHeartbeat() {
    _disarmHeartbeat();
    if (!_opts || !_opts.cinema) return;
    if (
      typeof document !== "undefined" &&
      document.visibilityState === "hidden"
    ) {
      return;
    }
    var ms = _opts.heartbeatMs != null ? _opts.heartbeatMs : 2200;
    if (ms <= 0) return;
    _heartbeat = setInterval(_runHeartbeat, ms);
    if (_opts.cinema) _setTransport("cinema");
  }

  function _disarmHeartbeat() {
    if (_heartbeat) {
      clearInterval(_heartbeat);
      _heartbeat = null;
    }
  }

  function _bindVisibility() {
    if (typeof document === "undefined") return;
    if (_visHandler) {
      document.removeEventListener("visibilitychange", _visHandler);
    }
    _visHandler = _onVisibility;
    document.addEventListener("visibilitychange", _visHandler);
  }

  function _unbindVisibility() {
    if (typeof document === "undefined" || !_visHandler) return;
    document.removeEventListener("visibilitychange", _visHandler);
    _visHandler = null;
  }

  var SuiteLive = {
    start: function (opts) {
      SuiteLive.stop();
      _opts = opts || {};
      _running = true;
      _transport = _opts.cinema ? "cinema" : "pulse";
      _refreshBusy = false;
      _lastRefreshAt = 0;
      _armPulse();
      if (_opts.sse) _armTape();
      _armReconcile();
      _armHeartbeat();
      _bindVisibility();
      return SuiteLive;
    },
    stop: function () {
      _running = false;
      if (_timer) {
        clearInterval(_timer);
        _timer = null;
      }
      _disarmHeartbeat();
      if (_refreshTimer) {
        clearTimeout(_refreshTimer);
        _refreshTimer = null;
      }
      _closeTape();
      _unbindVisibility();
      if (global.SuitePulse) {
        try {
          SuitePulse.stop();
        } catch (e) {}
      }
      _opts = null;
      _transport = "pulse";
      _refreshBusy = false;
      return SuiteLive;
    },
    force: function () {
      if (global.SuitePulse) {
        try {
          SuitePulse.force();
        } catch (e) {}
      }
      _scheduleRefresh("force", false);
      return SuiteLive;
    },
    refreshNow: function (reason) {
      if (_refreshTimer) {
        clearTimeout(_refreshTimer);
        _refreshTimer = null;
      }
      if (_refreshBusy || !_opts) return SuiteLive;
      _refreshBusy = true;
      _lastRefreshAt = Date.now();
      var done = function () {
        _refreshBusy = false;
      };
      try {
        var ret =
          typeof _opts.onRefresh === "function"
            ? _opts.onRefresh(reason || "now")
            : null;
        if (ret && typeof ret.then === "function") {
          ret.then(done, done);
        } else {
          done();
        }
      } catch (e) {
        done();
      }
      return SuiteLive;
    },
    transport: function () {
      return _transport;
    },
    running: function () {
      return _running;
    },
    lastRefreshAt: function () {
      return _lastRefreshAt;
    },
    reset: function () {
      if (global.SuitePulse) {
        try {
          SuitePulse.reset();
        } catch (e) {}
      }
      return SuiteLive;
    },
    schedule: function (reason, isSse) {
      _scheduleRefresh(reason || "manual", !!isSse);
      return SuiteLive;
    },
  };

  global.SuiteLive = SuiteLive;
})(typeof window !== "undefined" ? window : this);
