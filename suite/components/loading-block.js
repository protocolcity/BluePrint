/**
 * LoadingBlock — skeleton or pulse placeholder (pc-294).
 * props: { label?, variant?: "skeleton"|"pulse", rows?: number }
 * Host gets aria-busy=true while mounted with visible content.
 */
import { esc, ensureSuiteUiCss } from "./util.js";

export function mountLoadingBlock(el, props) {
  ensureSuiteUiCss();
  props = props || {};
  var label = props.label != null ? String(props.label) : "Loading…";
  var variant = props.variant === "pulse" ? "pulse" : "skeleton";
  var rows = Math.max(1, Math.min(8, Number(props.rows) || 4));

  el.className = "suite-loading suite-loading--" + variant;
  el.setAttribute("aria-busy", "true");
  el.setAttribute("aria-live", "polite");
  el.setAttribute("aria-label", label);

  var bars = "";
  if (variant === "skeleton") {
    for (var i = 0; i < rows; i++) {
      var w = 60 + ((i * 17) % 35);
      bars +=
        '<div class="suite-loading__bar" style="width:' +
        w +
        '%" aria-hidden="true"></div>';
    }
  } else {
    bars = '<div class="suite-loading__pulse" aria-hidden="true"></div>';
  }

  el.innerHTML =
    '<p class="suite-loading__label">' + esc(label) + "</p>" + bars;

  return {
    update: function (next) {
      return mountLoadingBlock(el, next);
    },
    destroy: function () {
      el.innerHTML = "";
      el.className = "suite-loading";
      el.removeAttribute("aria-busy");
      el.removeAttribute("aria-live");
      el.removeAttribute("aria-label");
    },
  };
}
