/**
 * pc-1396 — classic-script HTML-escape boot.
 *
 * ESM components import { esc, escAttr } from /components/util.js (same
 * algorithm). Classic suite files cannot import modules, so this file
 * publishes window.__bp.esc / window.__bp.escAttr and must load as a
 * synchronous <script> before map-fast and other non-module consumers.
 */
(function (root) {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escAttr(s) {
    return esc(s).replace(/`/g, "&#96;");
  }

  var bp = root.__bp || (root.__bp = {});
  bp.esc = esc;
  bp.escAttr = escAttr;
})(typeof window !== "undefined" ? window : globalThis);
