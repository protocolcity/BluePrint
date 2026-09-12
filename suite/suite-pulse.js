/*! suite-pulse.js — LIVE-B4 (pc-278)
 * Cheap change bus: poll /api/pulse; full-refetch only when a source token moves.
 * Doctrine: disk+stores remain truth; pulse is projection freshness only.
 *
 * Usage:
 *   SuitePulse.start({
 *     keys: ["city", "tickets", "people"],  // which sources matter for this room
 *     pulseUrl: "/api/pulse?scope=city",     // optional; defaults to all sources
 *     interval: 1500,
 *     onChange: function (changedKeys, pulse) { ... full refetch ... },
 *     onPulse: function (pulse) { ... optional cheap UI ... }
 *   });
 *   SuitePulse.stop();
 */
(function (global) {
  "use strict";

  var _timer = null;
  var _busy = false;
  var _last = {}; // source -> token
  var _opts = null;

  function _visibleMs(ms) {
    if (document.visibilityState === "hidden") {
      return Math.max(ms * 4, 8000);
    }
    return ms;
  }

  function _fetchPulse() {
    var url = (_opts && _opts.pulseUrl) || "/api/pulse";
    return fetch(url, { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("pulse " + r.status);
        return r.json();
      });
  }

  function _tick() {
    if (_busy || !_opts) return;
    _busy = true;
    _fetchPulse()
      .then(function (pulse) {
        var sources = (pulse && pulse.sources) || {};
        var keys = _opts.keys || Object.keys(sources);
        var changed = [];
        keys.forEach(function (k) {
          var src = sources[k] || {};
          var tok = src.token;
          // Missing upstream → treat as always-stale (force change once, then hold "?")
          if (tok == null) tok = "?";
          if (_last[k] === undefined) {
            _last[k] = tok;
            return; // first sample: baseline only, no full refetch storm
          }
          if (_last[k] !== tok) {
            _last[k] = tok;
            changed.push(k);
          }
        });
        /*
         * onPulse always fires (pc-943): Map may read people.recent_failures
         * when WF generation exposes it — even if tokens did not change.
         */
        if (typeof _opts.onPulse === "function") {
          try {
            _opts.onPulse(pulse);
          } catch (e) {}
        }
        if (changed.length && typeof _opts.onChange === "function") {
          try {
            _opts.onChange(changed, pulse);
          } catch (e) {}
        }
      })
      .catch(function () {
        /* degrade: keep last tokens; rooms still have focus/heartbeat paths */
      })
      .then(function () {
        _busy = false;
      });
  }

  function _arm() {
    if (_timer) clearInterval(_timer);
    if (!_opts) return;
    var ms = _visibleMs(_opts.interval || 1500);
    _timer = setInterval(_tick, ms);
  }

  var SuitePulse = {
    start: function (opts) {
      _opts = opts || {};
      _last = {};
      _arm();
      document.addEventListener("visibilitychange", _arm);
      // Immediate first sample
      setTimeout(_tick, 50);
      return SuitePulse;
    },
    stop: function () {
      if (_timer) clearInterval(_timer);
      _timer = null;
      _opts = null;
      document.removeEventListener("visibilitychange", _arm);
    },
    force: function () {
      _tick();
    },
    /** Reset baselines so next token change still fires (e.g. after soft-nav). */
    reset: function () {
      _last = {};
    },
  };

  global.SuitePulse = SuitePulse;
})(typeof window !== "undefined" ? window : this);
