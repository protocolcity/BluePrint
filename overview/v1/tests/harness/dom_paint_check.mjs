// Minimal DOM harness for Overview / Calendar / Settings paint functions.
//
// Renders paintAgents / paintProject / paintCharter against an empty
// wire payload and reports on the DOM shape via stdout JSON. Used by
// test_paint_dom.py to lock the honest-empty invariants that live
// on the JS side (no builder anchors, hidden shells).
//
// Also locks Calendar + Settings V1 glass DoD paint:
//   paintEvents empty → `No events`; populated → title · when · source · status
//   paintDesk / paintCellarTip → binder path + brew-face tip (never a fake SHA)

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

class El {
  constructor(tag) {
    this.tagName = String(tag || "div").toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.className = "";
    this.textContent = "";
    this.hidden = false;
    this.href = "";
    this.target = "";
    this.rel = "";
    this.style = {};
    this._role = null;
    this._id = null;
  }
  appendChild(c) {
    c.parent = this;
    this.children.push(c);
    return c;
  }
  removeChild(c) {
    this.children = this.children.filter((x) => x !== c);
    return c;
  }
  append(...cs) {
    for (const c of cs) this.appendChild(c);
  }
  get firstChild() {
    return this.children[0] || null;
  }
  get childNodes() {
    return this.children;
  }
  setAttribute(k, v) {
    this.attributes[k] = v;
    if (k === "data-role") this._role = v;
    if (k === "id") this._id = v;
  }
  getAttribute(k) {
    return this.attributes[k];
  }
  _walk(pred) {
    if (pred(this)) return this;
    for (const c of this.children) {
      const r = c._walk ? c._walk(pred) : null;
      if (r) return r;
    }
    return null;
  }
  querySelector(sel) {
    const roleM = sel.match(/^\[data-role="([^"]+)"\]$/);
    if (roleM) return this._walk((n) => n._role === roleM[1]);
    const idM = sel.match(/^#(.+)$/);
    if (idM) return this._walk((n) => n._id === idM[1]);
    return null;
  }
  querySelectorAll(sel) {
    const results = [];
    const tagM = sel.match(/^[a-zA-Z]+$/);
    const walk = (n) => {
      if (tagM && n.tagName === sel.toUpperCase()) results.push(n);
      for (const c of n.children) walk(c);
    };
    walk(this);
    return results;
  }
  countByTag(tag) {
    const t = tag.toUpperCase();
    let n = this.tagName === t ? 1 : 0;
    for (const c of this.children) n += c.countByTag ? c.countByTag(t) : 0;
    return n;
  }
}

globalThis.document = {
  createElement(tag) {
    return new El(tag);
  },
};

// Build the shell hosts the paint functions look up by data-role / id.
function makeShell() {
  const root = new El("main");
  root.setAttribute("id", "overview-shell");

  function child(tag, role, id) {
    const el = new El(tag);
    if (role) el.setAttribute("data-role", role);
    if (id) el.setAttribute("id", id);
    root.appendChild(el);
    return el;
  }

  child("div", "agents-body");
  child("div", "agents-links");
  child("div", "jobs-body");
  child("div", "jobs-buckets");
  child("div", "pulse-body");
  child("div", "pulse-meta");

  const projectCard = child("section", "project-card");
  projectCard.hidden = true;
  child("h2", "project-title", "ov-project-title");
  child("p", "project-path");
  child("div", "project-badges");
  child("div", "project-excerpt-wrap");
  child("blockquote", "project-excerpt");

  const drawer = child("aside", "charter-drawer");
  drawer.hidden = true;
  child("h2", null, "ov-charter-title");
  child("div", "charter-body");
  child("p", "charter-footer");

  child("div", "footer-row");
  return root;
}

const mod = await import(
  join(HERE, "..", "..", "static", "js", "overview.v1.js")
);

const cases = {};

// Case 1: paintAgents with empty payload → zero anchor children in links.
{
  const root = makeShell();
  mod.paintAgents(root, [], { cloud_builders: [], remote_builders: [] });
  const links = root.querySelector('[data-role="agents-links"]');
  cases.empty_agents_links = {
    anchor_count: links.countByTag("a"),
    hidden: links.hidden,
    child_count: links.children.length,
  };
}

// Case 2: paintAgents with only hash-only entries → still zero anchors.
{
  const root = makeShell();
  mod.paintAgents(root, [], {
    cloud_builders: [{ name: "No URL Builder" }],
    remote_builders: [{ name: "Also No URL" }],
  });
  const links = root.querySelector('[data-role="agents-links"]');
  cases.hashless_builders = {
    anchor_count: links.countByTag("a"),
    hidden: links.hidden,
  };
}

// Case 3: paintAgents with a real cloud url → exactly one anchor for that side.
{
  const root = makeShell();
  mod.paintAgents(root, [], {
    cloud_builders: [{ name: "Real", url: "https://example.test/x" }],
    remote_builders: [],
  });
  const links = root.querySelector('[data-role="agents-links"]');
  const anchors = links.children.filter((c) => c.tagName === "A");
  cases.real_cloud_only = {
    anchor_count: anchors.length,
    href: anchors[0]?.href || null,
    hidden: links.hidden,
  };
}

// Case 4: paintProject with empty payload → card stays hidden.
{
  const root = makeShell();
  mod.paintProject(root, {});
  cases.empty_project = {
    hidden: root.querySelector('[data-role="project-card"]').hidden,
  };
}

// Case 5: paintCharter with empty payload → drawer stays hidden.
{
  const root = makeShell();
  mod.paintCharter(root, {});
  cases.empty_charter = {
    hidden: root.querySelector('[data-role="charter-drawer"]').hidden,
  };
}

// Case 6: paintPulse with only all-off heartbeats → no row list is drawn.
{
  const root = makeShell();
  const heartbeats = [
    { name: "FS Watch", state: "off", last_at: null },
    { name: "Builder", state: "off", last_at: null },
    { name: "Cellar", state: "off", last_at: null },
    { name: "Index", state: "off", last_at: null },
    { name: "Sync", state: "off", last_at: null },
  ];
  mod.paintPulse(root, {
    heartbeats,
    ticks: [],
    last_at: null,
    cellar_tip: "",
  });
  const body = root.querySelector('[data-role="pulse-body"]');
  cases.all_off_pulse = {
    ul_count: body.countByTag("ul"),
    child_count: body.children.length,
  };
}


// Jobs tile: cap visible rows; quiet N more; buckets stay full counts.
{
  const root = makeShell();
  const many = [];
  for (let i = 0; i < 5; i++) many.push({ name: `w${i}`, state: "waiting" });
  for (let i = 0; i < 3; i++) many.push({ name: `r${i}`, state: "ready" });
  for (let i = 0; i < 4; i++) many.push({ name: `b${i}`, state: "blocked" });
  mod.paintJobs(root, many, { waiting: 100, ready: 3, blocked: 12 });
  const body = root.querySelector('[data-role="jobs-body"]');
  const buckets = root.querySelector('[data-role="jobs-buckets"]');
  const list = body.children.find((c) => c.tagName === "UL");
  const more = body.children.find((c) => c.tagName === "P" && c.className === "ov-job-more");
  const rows = list ? list.children : [];
  const states = rows.map((li) => {
    const st = li.children.find((c) => c.className === "ov-job-state");
    return st ? st.textContent : "";
  });
  cases.jobs_cap = {
    row_count: rows.length,
    more_text: more ? more.textContent : null,
    first_states: states.slice(0, 4),
    bucket_html: buckets.innerHTML || String(buckets.children.map((c) => c.textContent).join("|")),
  };
  // buckets: three rows with counts — collect count textContent
  const counts = buckets.children.map((row) => {
    const count = row.children.find((c) => c.className === "ov-bucket-count");
    return count ? count.textContent : "";
  });
  cases.jobs_cap.bucket_counts = counts;
  const ranked = mod.rankAndCapJobs(many, 8);
  cases.jobs_rank = {
    visible: ranked.visible.length,
    more: ranked.more,
    order: ranked.visible.map((r) => r.state),
  };
}

// ── Calendar + Settings V1 glass (OVERVIEW_CALENDAR_SETTINGS.md) ──────────

function makeCalendarShell() {
  const root = new El("main");
  root.setAttribute("id", "calendar-shell");
  const list = new El("div");
  list.setAttribute("data-role", "cal-list");
  const empty = new El("p");
  empty.className = "ov-empty";
  empty.textContent = "No events";
  list.appendChild(empty);
  root.appendChild(list);
  const range = new El("span");
  range.setAttribute("data-role", "cal-range");
  root.appendChild(range);
  return root;
}

function makeSettingsShell() {
  const root = new El("main");
  root.setAttribute("id", "settings-shell");
  const path = new El("span");
  path.setAttribute("data-role", "set-binder-path");
  path.textContent = "on this desk";
  const label = new El("span");
  label.setAttribute("data-role", "set-desk-label");
  label.textContent = "Local desk";
  const tip = new El("span");
  tip.setAttribute("data-role", "set-cellar-tip");
  tip.textContent = "";
  root.append(path, label, tip);
  return root;
}

function eventFields(li) {
  return li.children.map((c) => ({
    className: c.className,
    text: c.textContent,
    source: c.dataset.source || null,
    state: c.dataset.state || null,
  }));
}

const cal = await import(
  join(HERE, "..", "..", "static", "js", "calendar.v1.js")
);
const settings = await import(
  join(HERE, "..", "..", "static", "js", "settings.v1.js")
);

// Honest empty — Writer copy, no fabricated rows.
{
  const root = makeCalendarShell();
  cal.paintEvents(root, []);
  cal.paintRange(root, "");
  const list = root.querySelector('[data-role="cal-list"]');
  const range = root.querySelector('[data-role="cal-range"]');
  cases.calendar_empty = {
    child_count: list.children.length,
    empty_text: list.children[0] ? list.children[0].textContent : null,
    empty_class: list.children[0] ? list.children[0].className : null,
    ul_count: list.countByTag("ul"),
    range: range.textContent,
  };
}

// Populated rows — title · when · source · status (Glass DoD 3).
{
  const root = makeCalendarShell();
  cal.paintEvents(root, [
    { title: "Standup", at: "2026-09-11T09:00", source: "routine", state: "scheduled" },
    { title: "Ship peel", at: "2026-09-11T16:00", source: "WO", state: "due" },
    { title: "Filed note", at: "2026-09-12T11:30", source: "manual", state: "done" },
  ]);
  cal.paintRange(root, "2026-09-07 → 2026-09-13");
  const list = root.querySelector('[data-role="cal-list"]');
  const ul = list.children.find((c) => c.tagName === "UL");
  const rows = ul ? ul.children : [];
  cases.calendar_rows = {
    row_count: rows.length,
    fields: rows.map(eventFields),
    range: root.querySelector('[data-role="cal-range"]').textContent,
    empty_count: list.children.filter((c) => c.className === "ov-empty").length,
  };
}

// Unknown source/state fall back — never invent a fourth source or status.
{
  const root = makeCalendarShell();
  cal.paintEvents(root, [
    { title: "Odd", at: "2026-09-11T12:00", source: "cloud", state: "busy" },
  ]);
  const list = root.querySelector('[data-role="cal-list"]');
  const ul = list.children.find((c) => c.tagName === "UL");
  const fields = ul ? eventFields(ul.children[0]) : [];
  cases.calendar_fallback = { fields };
}

// Settings desk + Cellar brew face. Empty tip does not invent a version.
{
  const root = makeSettingsShell();
  settings.paintDesk(root, {
    binder_path: "/Users/eliefrainseo/OneSeo",
    desk_label: "Local desk",
  });
  settings.paintCellarTip(root, { cellar_tip: "blueprint 0.1.50_12" });
  cases.settings_desk = {
    binder_path: root.querySelector('[data-role="set-binder-path"]').textContent,
    desk_label: root.querySelector('[data-role="set-desk-label"]').textContent,
    cellar_tip: root.querySelector('[data-role="set-cellar-tip"]').textContent,
  };
}

{
  const root = makeSettingsShell();
  settings.paintCellarTip(root, { cellar_tip: "" });
  cases.settings_cellar_empty = {
    cellar_tip: root.querySelector('[data-role="set-cellar-tip"]').textContent,
  };
}


process.stdout.write(JSON.stringify(cases));
