/**
 * Pathbar — shared breadcrumb (Explorer/Desk/Agents hosts) (pc-294).
 * props: { crumbs: [{ label, href? }] }  — last crumb = current (no link)
 */
import { esc, escAttr, ensureSuiteUiCss } from "./util.js";

export function mountPathbar(el, props) {
  ensureSuiteUiCss();
  props = props || {};
  var crumbs = Array.isArray(props.crumbs) ? props.crumbs : [];

  el.className = (el.className || "").replace(/\bpathbar\b/g, "").trim();
  el.classList.add("pathbar", "suite-pathbar");
  el.setAttribute("aria-label", "Breadcrumb");
  // nav landmark when used as primary path; stay a div-friendly host
  if (el.tagName === "NAV") {
    /* already nav */
  }

  if (!crumbs.length) {
    el.innerHTML = "";
  } else {
    var parts = crumbs.map(function (c, i) {
      var last = i === crumbs.length - 1;
      var label = c && c.label != null ? String(c.label) : "";
      if (last || !c || !c.href) {
        return (
          '<span class="suite-pathbar__cur" aria-current="page">' +
          esc(label) +
          "</span>"
        );
      }
      return (
        '<a class="suite-pathbar__link" href="' +
        escAttr(c.href) +
        '">' +
        esc(label) +
        "</a>"
      );
    });
    el.innerHTML = parts.join(
      ' <span class="path-sep suite-pathbar__sep" aria-hidden="true">/</span> '
    );
  }

  return {
    update: function (next) {
      return mountPathbar(el, next);
    },
    destroy: function () {
      el.innerHTML = "";
      el.removeAttribute("aria-label");
      el.classList.remove("suite-pathbar");
    },
  };
}
