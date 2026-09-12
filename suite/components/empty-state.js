/**
 * EmptyState — placard when a tray/list has nothing (pc-294).
 * props: { title, hint?, action?: { label, href? | onClick? } }
 */
import { esc, escAttr, ensureSuiteUiCss } from "./util.js";

export function mountEmptyState(el, props) {
  ensureSuiteUiCss();
  props = props || {};
  var title = props.title ? String(props.title) : "Nothing here";
  var hint = props.hint ? String(props.hint) : "";
  var action = props.action || null;
  var onClick =
    action && typeof action.onClick === "function" ? action.onClick : null;

  el.className = "suite-empty";
  el.setAttribute("role", "region");
  el.setAttribute("aria-label", title);

  var actionHtml = "";
  if (action && action.label) {
    if (action.href) {
      actionHtml =
        '<p class="suite-empty__action"><a class="suite-empty__btn" href="' +
        escAttr(action.href) +
        '">' +
        esc(action.label) +
        "</a></p>";
    } else if (onClick) {
      actionHtml =
        '<p class="suite-empty__action"><button type="button" class="suite-empty__btn">' +
        esc(action.label) +
        "</button></p>";
    }
  }

  el.innerHTML =
    '<p class="suite-empty__title">' +
    esc(title) +
    "</p>" +
    (hint ? '<p class="suite-empty__hint dim">' + esc(hint) + "</p>" : "") +
    actionHtml;

  var btn = el.querySelector("button.suite-empty__btn");
  function handleClick(ev) {
    if (onClick) onClick(ev);
  }
  if (btn && onClick) btn.addEventListener("click", handleClick);

  return {
    update: function (next) {
      if (btn && onClick) btn.removeEventListener("click", handleClick);
      return mountEmptyState(el, next);
    },
    destroy: function () {
      if (btn && onClick) btn.removeEventListener("click", handleClick);
      el.innerHTML = "";
      el.className = "suite-empty";
      el.removeAttribute("role");
      el.removeAttribute("aria-label");
    },
  };
}
