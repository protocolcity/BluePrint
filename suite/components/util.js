/**
 * Shared helpers for suite/components (pc-294).
 * Pages own data; components own DOM. No global state here.
 *
 * pc-1396: esc / escAttr stay the ESM export. Classic scripts load /esc.js
 * (same algorithm) onto window.__bp before map-fast and other non-modules.
 */

/** Escape text for safe insertion into HTML text/attribute contexts. */
export function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Escape for double-quoted attribute values (href, title, aria-*). */
export function escAttr(s) {
  return esc(s).replace(/`/g, "&#96;");
}

if (typeof globalThis !== "undefined") {
  globalThis.__bp = globalThis.__bp || {};
  globalThis.__bp.esc = esc;
  globalThis.__bp.escAttr = escAttr;
}

var CSS_HREF = "/components/suite-ui.css";
var cssLinked = false;

/**
 * Ensure suite-ui.css is linked once (idempotent).
 * Call from each mount so hosts need only load index.js.
 */
export function ensureSuiteUiCss() {
  if (cssLinked || typeof document === "undefined") return;
  try {
    var existing = document.querySelector('link[data-suite-ui-css="1"]');
    if (existing) {
      cssLinked = true;
      return;
    }
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = CSS_HREF;
    link.setAttribute("data-suite-ui-css", "1");
    document.head.appendChild(link);
    cssLinked = true;
  } catch (e) {
    /* head missing / non-browser */
  }
}

/** Whether the user prefers reduced motion (live query each call). */
export function prefersReducedMotion() {
  try {
    return (
      typeof matchMedia === "function" &&
      matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  } catch (e) {
    return false;
  }
}
