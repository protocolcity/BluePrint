/*! map-notices.js — hygiene notice / hide state (pc-780 / pc-860)
 *
 * Pure: localStorage read/write only. No DOM. No global model.
 * Extracted from workspace_map.html (pc-653 §4, pc-780).
 *
 * Browser: window.MapNotices + bare names on window for callers.
 * Node/test: globalThis.MapNotices; inject storage via MapNotices._setStorage().
 *
 * Key: suite.mapHygieneSnoozed.v1
 * Separate from attention / For You snooze (server-side /api/attention/snooze).
 *
 * Citizen UI (pc-860): call this "Hide notice" — never bare "Snooze".
 * "Snooze" / "Snooze For You" is reserved for the alarm / gold layer.
 * Internal API names keep *Snooze* for storage continuity.
 */
(function (global) {
  "use strict";

  var MAP_HYGIENE_SNOOZE_KEY = "suite.mapHygieneSnoozed.v1";

  /* Injected storage — browser uses real localStorage; tests supply a mock. */
  var _storage =
    typeof localStorage !== "undefined"
      ? localStorage
      : {
          _data: {},
          getItem: function (k) {
            return Object.prototype.hasOwnProperty.call(this._data, k)
              ? this._data[k]
              : null;
          },
          setItem: function (k, v) {
            this._data[k] = v;
          },
          removeItem: function (k) {
            delete this._data[k];
          },
        };

  /** Mirror WorkLane _parse_until_iso tokens used by For You snooze. */
  function mapHygieneSnoozeUntilIso(token) {
    var s = String(token || "today")
      .trim()
      .toLowerCase();
    var now = new Date();
    if (s === "today" || s === "eod" || s === "end-of-day") {
      var end = new Date(now.getTime());
      end.setHours(24, 0, 0, 0);
      if (end.getTime() <= now.getTime()) {
        return new Date(now.getTime() + 12 * 3600 * 1000).toISOString();
      }
      return end.toISOString();
    }
    if (s === "1d" || s === "day" || s === "24h") {
      return new Date(now.getTime() + 24 * 3600 * 1000).toISOString();
    }
    if (s === "1w" || s === "week" || s === "7d") {
      return new Date(now.getTime() + 7 * 24 * 3600 * 1000).toISOString();
    }
    try {
      var d = new Date(token);
      if (!isNaN(d.getTime())) return d.toISOString();
    } catch (e) {}
    return new Date(now.getTime() + 24 * 3600 * 1000).toISOString();
  }

  /* pc-653 §4: read + garbage-collect expired snoozes atomically. */
  function mapNoticeSnoozes() {
    var saved = {};
    try {
      var parsed = JSON.parse(_storage.getItem(MAP_HYGIENE_SNOOZE_KEY) || "{}");
      saved = parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
      saved = {};
    }
    var now = Date.now();
    var changed = false;
    var out = {};
    Object.keys(saved).forEach(function (kind) {
      var row = saved[kind];
      if (!row || typeof row !== "object") {
        changed = true;
        return;
      }
      var untilMs = Date.parse(String(row.until || ""));
      if (!row.signature || !isFinite(untilMs) || untilMs <= now) {
        changed = true;
        return;
      }
      out[kind] = {
        signature: String(row.signature),
        until: new Date(untilMs).toISOString(),
      };
    });
    if (changed) {
      try {
        _storage.setItem(MAP_HYGIENE_SNOOZE_KEY, JSON.stringify(out));
      } catch (eWrite) {}
    }
    return out;
  }

  /**
   * Active snooze only when kind+signature match and until is in the future.
   * Signature mismatch = set-change re-arm (unrouted genuine-stall variant).
   */
  function mapNoticeSnoozeActive(kind, signature) {
    if (!kind || !signature) return null;
    var row = mapNoticeSnoozes()[kind];
    if (!row) return null;
    if (String(row.signature) !== String(signature)) return null;
    return row;
  }

  function mapNoticeDismissed(kind, signature) {
    return !!mapNoticeSnoozeActive(kind, signature);
  }

  function snoozeMapNotice(kind, signature, untilToken) {
    if (!kind || !signature) return;
    var saved = mapNoticeSnoozes();
    saved[kind] = {
      signature: String(signature),
      until: mapHygieneSnoozeUntilIso(untilToken || "today"),
    };
    try {
      _storage.setItem(MAP_HYGIENE_SNOOZE_KEY, JSON.stringify(saved));
    } catch (e) {}
  }

  function unsnoozeMapNotice(kind) {
    if (!kind) return;
    var saved = mapNoticeSnoozes();
    if (!saved[kind]) return;
    delete saved[kind];
    try {
      _storage.setItem(MAP_HYGIENE_SNOOZE_KEY, JSON.stringify(saved));
    } catch (e) {}
  }

  var MapNotices = {
    MAP_HYGIENE_SNOOZE_KEY: MAP_HYGIENE_SNOOZE_KEY,
    mapHygieneSnoozeUntilIso: mapHygieneSnoozeUntilIso,
    mapNoticeSnoozes: mapNoticeSnoozes,
    mapNoticeSnoozeActive: mapNoticeSnoozeActive,
    mapNoticeDismissed: mapNoticeDismissed,
    snoozeMapNotice: snoozeMapNotice,
    unsnoozeMapNotice: unsnoozeMapNotice,
    _setStorage: function (s) {
      _storage = s;
    },
  };

  global.MapNotices = MapNotices;

  /* Re-export bare names so workspace_map.html callers need no change. */
  global.mapHygieneSnoozeUntilIso = mapHygieneSnoozeUntilIso;
  global.mapNoticeSnoozes = mapNoticeSnoozes;
  global.mapNoticeSnoozeActive = mapNoticeSnoozeActive;
  global.mapNoticeDismissed = mapNoticeDismissed;
  global.snoozeMapNotice = snoozeMapNotice;
  global.unsnoozeMapNotice = unsnoozeMapNotice;
})(typeof window !== "undefined" ? window : globalThis);
