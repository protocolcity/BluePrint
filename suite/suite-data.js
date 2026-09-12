/**
 * suite-data.js — shared first-paint / soft-nav data bus (SUITE_SHELL S3 · pc-405)
 *
 * One long-lived document reuses bootstrap across Map loads so soft-nav
 * does not cold-fetch the world every time. Truth still comes from engines;
 * this is a short-TTL memory, not a second store.
 *
 * API:
 *   SuiteData.getMapBootstrap({ force })
 *   SuiteData.getCity({ force })
 *   SuiteData.peek()
 *   SuiteData.put(key, value)
 *   SuiteData.invalidate(key|null)
 *   SuiteData.age(key) → ms since put, or -1
 *   SuiteData.notePulse(pulse)   — token diff → invalidate + listeners
 *   SuiteData.watchPulse(opts)   — optional standalone poller (do not dual-arm)
 *   SuiteData.stopPulseWatch()
 *
 * Pulse ownership (pc-1092): SuiteLive / SuitePulse own /api/pulse polling.
 * This module does not auto-arm a second loop. Rooms without SuiteLive may
 * call watchPulse() explicitly; SuiteLive calls notePulse + stopPulseWatch.
 */
(function (global) {
  var TTL_MS = 12000; /* soft; force=true always network */
  var store = Object.create(null);
  var stamps = Object.create(null);
  var inflight = Object.create(null);

  function now() {
    return Date.now();
  }

  function age(key) {
    if (!stamps[key]) return -1;
    return now() - stamps[key];
  }

  function fresh(key, ttl) {
    var a = age(key);
    if (a < 0) return false;
    return a < (ttl == null ? TTL_MS : ttl);
  }

  function put(key, value) {
    store[key] = value;
    stamps[key] = now();
    return value;
  }

  function peek(key) {
    if (key == null || key === "") {
      return {
        keys: Object.keys(store),
        store: store,
        stamps: stamps,
        ttlMs: TTL_MS,
      };
    }
    return store[key];
  }

  function invalidate(key) {
    if (key == null || key === "") {
      store = Object.create(null);
      stamps = Object.create(null);
      inflight = Object.create(null);
      return;
    }
    delete store[key];
    delete stamps[key];
    delete inflight[key];
  }

  function fetchJson(url, timeoutMs) {
    var ms = timeoutMs || 20000;
    var ctrl =
      typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;
    if (ctrl) {
      timer = setTimeout(function () {
        try {
          ctrl.abort();
        } catch (e) {}
      }, ms);
    }
    return fetch(url, {
      credentials: "same-origin",
      cache: "no-store",
      signal: ctrl ? ctrl.signal : undefined,
    })
      .then(function (r) {
        if (!r.ok) throw new Error(url + " " + r.status);
        return r.json();
      })
      .finally(function () {
        if (timer) clearTimeout(timer);
      });
  }

  /**
   * Dedupe concurrent callers for the same key.
   */
  function once(key, loader) {
    if (inflight[key]) return inflight[key];
    inflight[key] = Promise.resolve()
      .then(loader)
      .then(function (v) {
        put(key, v);
        return v;
      })
      .finally(function () {
        delete inflight[key];
      });
    return inflight[key];
  }

  function seedBootstrapPayload(d) {
    if (!d || typeof d !== "object") return d;
    if (d.city) put("city", d.city);
    if (d.people) put("people", d.people);
    if (d.attention) {
      var nextItems =
        d.attention && Array.isArray(d.attention.items)
          ? d.attention.items
          : null;
      var prev = store.attention;
      var prevItems =
        prev && Array.isArray(prev.items) ? prev.items : null;
      if (nextItems && nextItems.length > 0) {
        put("attention", d.attention);
      } else if (!prevItems || !prevItems.length) {
        put("attention", d.attention);
      }
    }
    if (d.tpScene) put("tpScene", d.tpScene);
    put("mapBootstrap", d);
    return d;
  }

  function getMapBootstrap(opts) {
    opts = opts || {};
    var force = !!opts.force;
    if (!force && fresh("mapBootstrap") && store.mapBootstrap) {
      return Promise.resolve(store.mapBootstrap);
    }
    /*
     * pc-893 / pc-901: head of workspace_map starts __mapBootPrefetch while
     * the 1MB map app downloads. Always prefer it when store is empty —
     * even if force=true (cold poll used to force and ignore a live race,
     * burning 4s+ on a duplicate /api/map-bootstrap).
     */
    if (
      global.__mapBootPrefetch &&
      typeof global.__mapBootPrefetch.then === "function" &&
      (!store.mapBootstrap || !store.mapBootstrap.city)
    ) {
      var pref = global.__mapBootPrefetch;
      global.__mapBootPrefetch = null;
      return pref.then(function (d) {
        if (d && d.city) return seedBootstrapPayload(d);
        /* Prefetch failed — fall through to network */
        return getMapBootstrap({
          force: true,
          timeout: opts.timeout,
          _skipPrefetch: true,
        });
      });
    }
    if (opts._skipPrefetch) {
      /* already consumed prefetch */
    }
    /*
     * pc-891: force must not join a stuck inflight (aborted soft-nav / hung
     * fetch). Drop the slot so a new loader can run.
     */
    if (force && inflight.mapBootstrap) {
      try {
        delete inflight.mapBootstrap;
      } catch (eInf) {}
    }
    return once("mapBootstrap", function () {
      return fetchJson("/api/map-bootstrap", opts.timeout || 8000).then(
        function (d) {
          return seedBootstrapPayload(d);
        }
      );
    });
  }

  function getCity(opts) {
    opts = opts || {};
    var force = !!opts.force;
    if (!force && fresh("city") && store.city) {
      return Promise.resolve(store.city);
    }
    /* Prefer warm map bootstrap city over a second round-trip */
    if (!force && fresh("mapBootstrap") && store.mapBootstrap && store.mapBootstrap.city) {
      put("city", store.mapBootstrap.city);
      return Promise.resolve(store.mapBootstrap.city);
    }
    return once("city", function () {
      /* light=1: folders + counts; never founder brief (Map / soft-nav) */
      return fetchJson("/api/city?light=1", opts.timeout || 5000);
    });
  }

  var _pulseLast = Object.create(null);
  var _pulseTimer = null;
  var _pulseListeners = [];

  /**
   * Poll /api/pulse; invalidate SuiteData keys when generation tokens move.
   * Rooms keep SuiteLive for UI; this keeps the shared cache honest.
   */
  function notePulse(pulse) {
    put("pulse", pulse);
    var sources = (pulse && pulse.sources) || {};
    var changed = [];
    Object.keys(sources).forEach(function (k) {
      var tok = sources[k] && sources[k].token;
      if (tok == null) tok = "?";
      if (_pulseLast[k] === undefined) {
        _pulseLast[k] = tok;
        return;
      }
      if (_pulseLast[k] !== tok) {
        _pulseLast[k] = tok;
        changed.push(k);
      }
    });
    /*
     * pc-943: when WF generation (via suite pulse people) carries
     * recent_failures, keep a short-lived copy for Map Agents strip.
     * Tokens-only pulse is fine — this is optional payload passthrough.
     */
    try {
      var pe = sources.people || null;
      if (pe && Array.isArray(pe.recent_failures)) {
        put("recent_failures", pe.recent_failures);
      }
    } catch (eRf) {}
    if (changed.length) {
      /* Token moved → drop related bootstrap so next get* refetches */
      if (changed.indexOf("city") >= 0) {
        delete store.mapBootstrap;
        delete stamps.mapBootstrap;
        delete store.city;
        delete stamps.city;
      }
      _pulseListeners.slice().forEach(function (fn) {
        try {
          fn(changed, pulse);
        } catch (e) {}
      });
    }
    return changed;
  }

  function watchPulse(opts) {
    opts = opts || {};
    var interval = opts.interval || 2000;
    if (typeof opts.onChange === "function") {
      _pulseListeners.push(opts.onChange);
    }
    if (_pulseTimer) return;
    function tick() {
      fetchJson("/api/pulse", 5000)
        .then(function (pulse) {
          notePulse(pulse);
        })
        .catch(function () {})
        .then(function () {
          _pulseTimer = setTimeout(tick, interval);
        });
    }
    tick();
  }

  function stopPulseWatch() {
    if (_pulseTimer) clearTimeout(_pulseTimer);
    _pulseTimer = null;
    _pulseListeners = [];
  }

  global.SuiteData = {
    TTL_MS: TTL_MS,
    getMapBootstrap: getMapBootstrap,
    getCity: getCity,
    notePulse: notePulse,
    watchPulse: watchPulse,
    stopPulseWatch: stopPulseWatch,
    peek: peek,
    put: put,
    invalidate: invalidate,
    age: age,
    fresh: fresh,
  };

  /* pc-1092: no module-scope auto-arm. SuiteLive owns /api/pulse and feeds
   * notePulse so SuiteData cache stays honest without a second poller. */
})(typeof window !== "undefined" ? window : globalThis);
