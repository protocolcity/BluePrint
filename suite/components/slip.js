/**
 * Slip — ticket row / paper card for Desk trays (pc-294).
 * props: {
 *   id: string,
 *   title: string,
 *   status?: string,
 *   age?: string,
 *   forYou?: bool,
 *   loading?: bool,
 *   href?: string,          // when set, root is <a>
 *   tags?: string[],
 *   kind?: string,          // chip label (e.g. FOR YOU)
 * }
 */
import { esc, escAttr, ensureSuiteUiCss } from "./util.js";

var STATUS_CLASS = {
  backlog: "is-backlog",
  ready: "is-ready",
  in_progress: "is-motion",
  in_review: "is-motion",
  done: "is-done",
  canceled: "is-canceled",
  blocked: "is-blocked",
};

export function mountSlip(el, props) {
  ensureSuiteUiCss();
  props = props || {};
  var id = props.id != null ? String(props.id) : "";
  var title = props.title != null ? String(props.title) : "";
  var status = props.status != null ? String(props.status) : "";
  var age = props.age != null ? String(props.age) : "";
  var forYou = !!props.forYou;
  var loading = !!props.loading;
  var href = props.href ? String(props.href) : "";
  var kind = props.kind != null ? String(props.kind) : forYou ? "for You" : "";
  var tags = Array.isArray(props.tags) ? props.tags : [];

  var statusClass = STATUS_CLASS[status] || (status ? "is-other" : "");
  var classes = ["slip", "suite-slip"];
  if (forYou) classes.push("suite-slip--for-you", "fresh");
  if (loading) classes.push("suite-slip--loading");
  if (statusClass) classes.push(statusClass);

  var aria = id + (title ? " — " + title : "");
  if (forYou) aria += " (for You)";
  if (status) aria += ", " + status;

  if (loading) {
    el.className = classes.join(" ");
    el.setAttribute("aria-busy", "true");
    el.setAttribute("aria-label", "Loading slip");
    el.removeAttribute("href");
    el.innerHTML =
      '<div class="suite-slip__skel" aria-hidden="true">' +
      '<div class="suite-loading__bar" style="width:40%"></div>' +
      '<div class="suite-loading__bar" style="width:85%"></div>' +
      '<div class="suite-loading__bar" style="width:55%"></div>' +
      "</div>";
  } else {
    el.className = classes.join(" ");
    el.removeAttribute("aria-busy");
    el.setAttribute("aria-label", aria);
    if (title) el.setAttribute("title", title);

    var kindHtml = kind
      ? '<span class="kind' +
        (forYou ? "" : " muted") +
        '">' +
        esc(kind) +
        "</span>"
      : "";
    var tagsHtml = tags.length
      ? '<div class="tags">' +
        tags
          .map(function (t) {
            return '<span class="tag">' + esc(String(t)) + "</span>";
          })
          .join("") +
        "</div>"
      : "";

    el.innerHTML =
      '<div class="top">' +
      '<span class="id">' +
      esc(id) +
      "</span>" +
      '<span class="top-right">' +
      kindHtml +
      (age ? '<span class="when">' + esc(age) + "</span>" : "") +
      "</span></div>" +
      (title ? '<span class="t">' + esc(title) + "</span>" : "") +
      tagsHtml +
      (status
        ? '<span class="meta suite-slip__status">' + esc(status) + "</span>"
        : "");

    if (href) {
      if (el.tagName === "A") {
        el.setAttribute("href", href);
      } else {
        // Host is not an <a>; wrap content is left as-is — callers should
        // prefer mount into <a class="slip">. Still set data-href for paint.
        el.setAttribute("data-href", href);
      }
    }
  }

  return {
    update: function (next) {
      return mountSlip(el, next);
    },
    destroy: function () {
      el.innerHTML = "";
      el.className = "slip suite-slip";
      el.removeAttribute("aria-busy");
      el.removeAttribute("aria-label");
      el.removeAttribute("title");
      el.removeAttribute("data-href");
      if (el.tagName === "A") el.removeAttribute("href");
    },
  };
}
