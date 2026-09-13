// Agent inspector reconciliation + Escape + row-control-split harness
// (pc-1485 review recovery 1): three DOM-behavioral guards that a static
// source-string check cannot make honest:
//   1. Two paints with an identical selected agent leave the inspector's
//      own DOM nodes untouched (same node identity); a changed field
//      updates only that field's text, nothing else is torn down.
//   2. Escape, with a seat selected on the Agents view, clears the
//      selection, hides the inspector, and returns focus to the row.
//   3. The action cell is never inside the role=button selectable region
//      (no nested interactive controls); Enter on the selectable region
//      selects, Enter on the action button does not.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
const focusLog = [];

class Element {
  constructor(tag = 'div') {
    this.tagName = String(tag).toUpperCase();
    this.nodeType = tag === '#text' ? 3 : 1;
    this.nodeName = this.tagName;
    this.children = [];
    this.childNodes = this.children;
    this.listeners = {};
    this.attributes = {};
    this.className = '';
    this.dataset = {};
    this.hidden = false;
    this.open = false;
    this._text = '';
    this.type = '';
    this.href = '';
    this.value = '';
    this.disabled = false;
    this.ownerDocument = {createElement: tag => new Element(tag)};
  }
  append(...nodes) {
    for (const node of nodes) {
      const child = typeof node === 'string' ? Object.assign(new Element('#text'), {_text: node, textContent: node}) : node;
      child.parent = this;
      this.children.push(child);
    }
  }
  appendChild(node) { this.append(node); return node; }
  insertBefore(node, ref) {
    const idx = ref ? this.children.indexOf(ref) : this.children.length;
    node.parent = this;
    this.children.splice(idx < 0 ? this.children.length : idx, 0, node);
    return node;
  }
  removeChild(node) {
    this.children = this.children.filter(x => x !== node);
    return node;
  }
  get firstChild() { return this.children[0] || null; }
  get nextSibling() {
    if (!this.parent) return null;
    const idx = this.parent.children.indexOf(this);
    return this.parent.children[idx + 1] || null;
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatchEvent(event) {
    if (!event.preventDefault) event.preventDefault = () => {};
    for (const fn of this.listeners[event.type] || []) fn.call(this, event);
    return true;
  }
  focus() { focusLog.push(this); }
  closest(selector) {
    let node = this;
    while (node) {
      if (matchesSelector(node, selector)) return node;
      node = node.parent || null;
    }
    return null;
  }
  querySelector(selector) {
    const walk = node => {
      if (matchesSelector(node, selector)) return node;
      for (const child of node.children || []) { const hit = walk(child); if (hit) return hit; }
      return null;
    };
    for (const child of this.children) { const hit = walk(child); if (hit) return hit; }
    return null;
  }
  querySelectorAll(selector) {
    const out = [];
    const walk = node => {
      if (matchesSelector(node, selector)) out.push(node);
      for (const child of node.children || []) walk(child);
    };
    for (const child of this.children) walk(child);
    return out;
  }
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  get textContent() {
    if (this._text && !this.children.length) return this._text;
    return this.children.map(c => c.textContent || c._text || '').join('');
  }
  set textContent(value) { this._text = String(value ?? ''); this.children = []; }
}

function findByTag(node, tag) {
  if (node.tagName === tag) return node;
  for (const child of node.children || []) {
    const hit = findByTag(child, tag);
    if (hit) return hit;
  }
  return null;
}
function matchesSelector(node, selector) {
  const tagMatch = selector.match(/^([a-zA-Z]+)/);
  if (tagMatch && node.tagName !== tagMatch[1].toUpperCase()) return false;
  const classMatch = selector.match(/\.([\w-]+)/);
  if (classMatch && !(node.className || '').split(/\s+/).includes(classMatch[1])) return false;
  const attrRe = /\[([\w-]+)(?:="([^"]*)")?\]/g;
  let m;
  while ((m = attrRe.exec(selector))) {
    const [, attr, value] = m;
    const actual = attr.startsWith('data-')
      ? node.dataset[attr.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())]
      : node.getAttribute(attr);
    if (value === undefined) { if (actual === undefined || actual === null) return false; }
    else if ((actual || '') !== value) return false;
  }
  return true;
}

const PRESERVED_ATTRS = new Set(['open']);
function syncNode(oldEl, newEl) {
  let changed = false;
  for (const name of Object.keys(oldEl.attributes || {})) {
    if (PRESERVED_ATTRS.has(name)) continue;
    if (!newEl.hasAttribute(name)) { oldEl.removeAttribute(name); changed = true; }
  }
  for (const name of Object.keys(newEl.attributes || {})) {
    if (PRESERVED_ATTRS.has(name)) continue;
    if (oldEl.getAttribute(name) !== newEl.getAttribute(name)) { oldEl.setAttribute(name, newEl.getAttribute(name)); changed = true; }
  }
  if (oldEl.className !== newEl.className) { oldEl.className = newEl.className; changed = true; }
  if (oldEl.dataset && newEl.dataset) {
    for (const key of new Set([...Object.keys(oldEl.dataset), ...Object.keys(newEl.dataset)])) {
      if ((oldEl.dataset[key] || '') !== (newEl.dataset[key] || '')) {
        if (newEl.dataset[key] === undefined) delete oldEl.dataset[key];
        else oldEl.dataset[key] = newEl.dataset[key];
        changed = true;
      }
    }
  }
  oldEl.listeners = newEl.listeners;
  if (syncChildren(oldEl, newEl)) changed = true;
  return changed;
}
function syncChildren(oldParent, newParent) {
  let changed = false;
  const newNodes = newParent.children;
  for (let i = 0; i < newNodes.length; i++) {
    const newNode = newNodes[i];
    const oldNode = oldParent.children[i];
    if (!oldNode) { oldParent.appendChild(newNode); changed = true; continue; }
    if (oldNode.nodeType !== newNode.nodeType || oldNode.tagName !== newNode.tagName) {
      oldParent.insertBefore(newNode, oldNode);
      oldParent.removeChild(oldNode);
      changed = true;
      continue;
    }
    if (newNode.nodeType === 3) {
      if (oldNode.textContent !== newNode.textContent) { oldNode.textContent = newNode.textContent; changed = true; }
      continue;
    }
    if (syncNode(oldNode, newNode)) changed = true;
  }
  while (oldParent.children.length > newNodes.length) {
    oldParent.removeChild(oldParent.children[oldParent.children.length - 1]);
    changed = true;
  }
  return changed;
}
function reconcileList(container, items, keyOf, buildRow, options = {}) {
  const {emptyText} = options;
  if (!items.length) {
    container.replaceChildren();
    if (emptyText) { const p = new Element('p'); p.className = 'bp-empty'; p.textContent = emptyText; container.append(p); }
    return;
  }
  const existing = new Map();
  for (const node of [...container.children]) {
    if (!node.dataset || node.dataset.key === undefined) continue;
    if (existing.has(node.dataset.key)) { container.removeChild(node); continue; }
    existing.set(node.dataset.key, node);
  }
  const seen = new Set();
  let cursor = container.firstChild;
  for (const item of items) {
    const key = String(keyOf(item));
    if (seen.has(key)) continue;
    seen.add(key);
    const rendered = buildRow(item);
    rendered.dataset.key = key;
    const node = existing.get(key);
    if (node) {
      existing.delete(key);
      if (node !== cursor) container.insertBefore(node, cursor);
      syncNode(node, rendered);
      cursor = node.nextSibling;
    } else {
      container.insertBefore(rendered, cursor);
      cursor = rendered.nextSibling;
    }
  }
  for (const leftover of existing.values()) container.removeChild(leftover);
}

const IDS = [
  'page-title', 'page-description', 'eyebrow', 'freshness', 'source-warning', 'footer-status',
  'agents-view', 'agents-heartbeat', 'seat-list', 'job-list', 'supervisor-panel', 'coverage-list',
  'agent-detail', 'restore-muted', 'refresh', 'desk-scope', 'desk-name', 'scope-path', 'preferences',
  'refresh-preference', 'motion-preference', 'preference-status', 'filters', 'search',
  'project-filter', 'assignment-filter', 'status-filter', 'deferred-toggle', 'show-deferred',
  'deferred-count', 'work-list', 'results', 'page-count', 'previous', 'next',
];
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, new Element());
  return nodes.get(id);
};

function agentFixture(overrides = {}) {
  return {
    id: 'bp-claude-implementer', name: 'Claude implementer', group: 'seat', state: 'working',
    badge: 'WORKING', badge_source: 'daemon', configured: true, action: 'recover',
    project_name: 'BluePrint', model: 'Claude',
    held: {id: 'pc-1485', project: 'protocolcity'}, held_verified: true,
    last_candidates: ['bp-claude-implementer'],
    shift: {started_at: '2026-09-13T20:07:58Z', age_seconds: 60, budget_secs: 5400, stale: false, lock_held: true, source: 'ledger'},
    last_run: null, recovery_attempts: 0, preserved_reservation: false, report: null,
    schedule: 'manual', next_fire: null,
    ...overrides,
  };
}
const fixture = {
  workspace: {name: 'OneSeo', path: '/tmp/oneseo'},
  build: '0.1.50',
  projects: [],
  agents: [agentFixture()],
  coverage: [],
  supervisor: null,
  sources: [{name: 'WorkForce heartbeat', state: 'fresh', last_at: new Date().toISOString()}],
  orders: [],
  truncated: false,
  observed_at: new Date().toISOString(),
};

class Option { constructor(text, value) { this.text = text; this.value = value; } }
const keydownListeners = [];
const context = {
  URL, URLSearchParams, console, JSON, Option, AbortSignal: {timeout: () => ({})},
  location: new URL('/agents', 'https://desk.example'),
  localStorage: {getItem() { return null; }, setItem() {}},
  navigator: {clipboard: {writeText() {}}},
  CSS: {escape: s => s},
  fetch: async url => {
    if (String(url).includes('/api/operations')) return {ok: true, json: async () => fixture};
    return {ok: true, json: async () => ({repositories: []})};
  },
  setInterval() { return 1; }, clearInterval() {}, setTimeout() {}, Date,
  history: {replaceState() {}},
};
context.document = {
  getElementById: get,
  createElement: tag => new Element(tag),
  addEventListener(type, fn) { if (type === 'keydown') keydownListeners.push(fn); },
  dispatchEvent() { return true; },
  body: {classList: {add() {}, remove() {}, toggle() {}}},
  hidden: false,
  querySelector: selector => {
    if (selector === '[data-page="agents"]') { const a = new Element('a'); return a; }
    for (const root of nodes.values()) {
      const stack = [root];
      while (stack.length) {
        const node = stack.pop();
        if (matchesSelector(node, selector)) return node;
        stack.push(...(node.children || []));
      }
    }
    return null;
  },
};
function wireSelect(id) {
  const node = get(id);
  node.options = []; node.value = '';
  node.replaceChildren = (...opts) => { node.options = [...opts]; node.children = [...opts]; };
  node.add = option => { node.options.push(option); node.children.push(option); };
  return node;
}
for (const id of IDS) get(id);
for (const id of ['project-filter', 'assignment-filter', 'status-filter', 'timeline-project', 'timeline-source', 'refresh-preference', 'motion-preference']) wireSelect(id);
get('agents-view').hidden = false;
get('refresh-preference').value = '15';
get('motion-preference').value = 'system';
context.readerNav = {readerHref: path => path};
context.changeFeed = {connectChanges() { return {stop() {}}; }};
context.reconcileListFn = reconcileList;

let raw = read('../../static/js/operations.js');
raw = raw.slice(raw.indexOf("'use strict';"), raw.lastIndexOf('})();'));
raw = raw
  .replace("const {readerHref} = await import('/js/reader-navigation.mjs');", 'const {readerHref} = readerNav;')
  .replace("const {connectChanges} = await import('/js/change-feed.mjs');", 'const {connectChanges} = changeFeed;')
  .replace("const {reconcileList} = await import('/js/dom-reconcile.mjs');", 'const {reconcileList} = {reconcileList: reconcileListFn};');
const bootMarker = 'connectChanges(()=>{if(!document.hidden){refresh();';
const bootAt = raw.indexOf(bootMarker);
if (bootAt === -1) throw new Error('operations.js boot marker missing');
raw = raw.slice(0, bootAt) + `snapshot = ${JSON.stringify(fixture)};`;
const scopeKeys = Object.keys(context);
const scopeVals = Object.values(context);
const boot = new Function(...scopeKeys, `return (async () => { ${raw}
  return {agents, getSnapshot: () => snapshot, selectAgent, getSelected: () => selectedAgentId}; })();`);
const runtime = await boot(...scopeVals);
const {agents, getSnapshot, selectAgent, getSelected} = runtime;

// ── 1. Identical selected agent leaves inspector nodes untouched;
//      a changed field updates only that field. ─────────────────────────
selectAgent('bp-claude-implementer');
const detail = get('agent-detail');
assert.equal(detail.hidden, false, 'inspector must be visible once a seat is selected');
const refsBefore = [...detail.children];
assert.equal(refsBefore.length, 6, 'inspector renders heading/meta/shift/timeline/link/close');
const timelineWrap = refsBefore[3];
const ddBefore = timelineWrap.children.map(step => step.children[1]);
const recoveryDd = ddBefore[3];
assert.equal(recoveryDd.textContent, '0');

agents(); // identical repaint — same agent, same fields
assert.deepEqual([...detail.children], refsBefore, 'identical repaint must not replace any inspector node');
assert.deepEqual(timelineWrap.children.map(step => step.children[1]), ddBefore, 'identical repaint must not replace any timeline phase node');

getSnapshot().agents[0].recovery_attempts = 1; // one field actually changes
agents();
assert.deepEqual([...detail.children], refsBefore, 'a single changed field must not tear down the panel skeleton');
const ddAfterChange = timelineWrap.children.map(step => step.children[1]);
assert.deepEqual(ddAfterChange, ddBefore, 'a single changed field must reuse every timeline phase node');
assert.equal(recoveryDd.textContent, '1', 'the changed phase must update in place');
for (let i = 0; i < ddAfterChange.length; i++) {
  if (i === 3) continue;
  assert.equal(ddAfterChange[i].textContent, ddBefore[i].textContent, `unrelated phase ${i} must keep its text`);
}

// ── 2. Escape clears the seat selection and hides the inspector. ────────
assert.equal(getSelected(), 'bp-claude-implementer');
const selectableBefore = get('seat-list').children[0].children[0];
assert.ok(keydownListeners.length > 0, 'a global Escape handler must be registered');
for (const fn of keydownListeners) fn({key: 'Escape', target: selectableBefore});
assert.equal(getSelected(), '', 'Escape must clear the seat selection');
assert.equal(get('agent-detail').hidden, true, 'Escape must hide the inspector');
assert.equal(get('agent-detail').children.length, 0, 'Escape must clear the inspector body');
assert.ok(focusLog.includes(selectableBefore), 'Escape must return focus to the same selectable row');

// ── 3. The action cell is not nested inside the role=button region. ─────
const row = get('seat-list').children[0];
assert.equal(row.children.length, 2, 'row must have exactly two top-level children: select region + action cell');
const select = row.children[0];
const actionCell = row.children[1];
assert.equal(select.getAttribute('role'), 'button');
assert.notEqual(select, actionCell);
assert.ok(!select.children.includes(actionCell), 'the action cell must not be a child of the selectable region');
assert.ok(findByTag(actionCell, 'BUTTON'), 'the action button must live in the action cell');
assert.equal(findByTag(select, 'BUTTON'), null, 'the selectable region must contain no action button');

selectAgent(''); // deselect
select.dispatchEvent({type: 'keydown', key: 'Enter', target: select});
assert.equal(getSelected(), 'bp-claude-implementer', 'Enter on the selectable region must select the row');
selectAgent(''); // deselect again
const actionButton = findByTag(actionCell, 'BUTTON');
actionButton.dispatchEvent({type: 'keydown', key: 'Enter', target: actionButton});
assert.equal(getSelected(), '', 'Enter on the action button must not select the row');

process.stdout.write(JSON.stringify({
  identical_repaint_stable: true,
  changed_phase_isolated: true,
  escape_clears_selection: true,
  escape_hides_inspector: true,
  escape_returns_focus: focusLog.includes(selectableBefore),
  action_cell_outside_select_region: !select.children.includes(actionCell),
}));
