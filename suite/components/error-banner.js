/**
 * ErrorBanner — role=alert surface for engine-down / fetch failures (pc-294).
 * props: { message: string, onRetry?: () => void, upstream?: string }
 */
import { esc, ensureSuiteUiCss } from "./util.js";

export function mountErrorBanner(el, props) {
  ensureSuiteUiCss();
  props = props || {};
  var onRetry = typeof props.onRetry === "function" ? props.onRetry : null;
  var message = props.message ? String(props.message) : "";
  var upstream = props.upstream ? String(props.upstream) : "";

  el.setAttribute("role", "alert");
  el.className = "suite-error" + (message ? " is-visible" : "");
  if (!message) {
    el.innerHTML = "";
    el.hidden = true;
  } else {
    el.hidden = false;
    el.innerHTML =
      '<p class="suite-error__msg">' +
      esc(message) +
      "</p>" +
      (upstream
        ? '<p class="suite-error__up dim">' + esc(upstream) + "</p>"
        : "") +
      (onRetry
        ? '<button type="button" class="suite-error__retry">Retry</button>'
        : "");
  }

  var btn = el.querySelector(".suite-error__retry");
  function onClick(ev) {
    if (onRetry) onRetry(ev);
  }
  if (btn && onRetry) btn.addEventListener("click", onClick);

  return {
    update: function (next) {
      if (btn && onRetry) btn.removeEventListener("click", onClick);
      return mountErrorBanner(el, next);
    },
    destroy: function () {
      if (btn && onRetry) btn.removeEventListener("click", onClick);
      el.innerHTML = "";
      el.className = "suite-error";
      el.removeAttribute("role");
      el.hidden = true;
    },
  };
}
