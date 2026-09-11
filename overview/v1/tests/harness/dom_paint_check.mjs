// Minimal DOM harness for the overview.v1.js paint functions.
//
// Renders paintAgents / paintProject / paintCharter against an empty
// wire payload and reports on the DOM shape via stdout JSON. Used by
// test_paint_dom.py to lock the honest-empty invariants that live
// on the JS side (no builder anchors, hidden shells).

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

process.stdout.write(JSON.stringify(cases));
