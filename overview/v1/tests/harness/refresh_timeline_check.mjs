// Timeline poll-position harness (pc-1488 cursor-reviewer finding #2):
// a background poll on the default first page must keep the reader's
// position (and surface a new-events count) whenever they have scrolled
// down, not only after they have used Load more.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');

class Element {
  constructor(tag = 'div') {
    this.tagName = String(tag).toUpperCase();
    this.nodeType = tag === '#text' ? 3 : 1;
    this.children = [];
    this.childNodes = this.children;
    this.listeners = {};
    this.attributes = {};
    this.className = '';
    this.dataset = {};
    this.hidden = false;
    this.open = false;
    this._text = '';
    this.value = '';
    this.href = '';
    this.classList = {add() {}, remove() {}, toggle() {}};
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
    const idx = this.children.indexOf(node);
    if (idx >= 0) this.children.splice(idx, 1);
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
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  get textContent() {
    if (this._text && !this.children.length) return this._text;
    return this.children.map(c => c.textContent || c._text || '').join('');
  }
  set textContent(value) { this._text = String(value ?? ''); }
}

const PRESERVED_ATTRS = new Set(['open']);

function syncNode(oldEl, newEl) {
  for (const name of Object.keys(oldEl.attributes || {})) {
    if (PRESERVED_ATTRS.has(name)) continue;
    if (!newEl.hasAttribute(name)) oldEl.removeAttribute(name);
  }
  for (const name of Object.keys(newEl.attributes || {})) {
    if (PRESERVED_ATTRS.has(name)) continue;
    if (oldEl.getAttribute(name) !== newEl.getAttribute(name)) oldEl.setAttribute(name, newEl.getAttribute(name));
  }
  oldEl.className = newEl.className;
  syncChildren(oldEl, newEl);
}

function syncChildren(oldParent, newParent) {
  const newNodes = newParent.children;
  for (let i = 0; i < newNodes.length; i++) {
    const newNode = newNodes[i];
    const oldNode = oldParent.children[i];
    if (!oldNode) { oldParent.appendChild(newNode); continue; }
    if (oldNode.nodeType !== newNode.nodeType || oldNode.tagName !== newNode.tagName) {
      oldParent.insertBefore(newNode, oldNode);
      oldParent.removeChild(oldNode);
      continue;
    }
    if (newNode.nodeType === 3) { oldNode.textContent = newNode.textContent; continue; }
    syncNode(oldNode, newNode);
  }
  while (oldParent.children.length > newNodes.length) {
    oldParent.removeChild(oldParent.children[oldParent.children.length - 1]);
  }
}

function reconcileList(container, items, keyOf, buildRow, options = {}) {
  const {emptyText} = options;
  if (!items.length) {
    container.replaceChildren();
    if (emptyText) { const p = new Element('p'); p.textContent = emptyText; container.append(p); }
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

const nodes = new Map();
const get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };

function row(id, at, title) {
  return {id, at, source: 'worklane', project: 'blueprint', actor: 'you', event: 'commented', title, link: {}};
}

const firstPage = {rows: [row('r3', '2026-09-13T12:00:00Z', 'Third'), row('r2', '2026-09-13T11:00:00Z', 'Second'), row('r1', '2026-09-13T10:00:00Z', 'First')], sources: [], next_cursor: null};
const polledWhileScrolled = {rows: [row('r4', '2026-09-13T13:00:00Z', 'Fourth'), ...firstPage.rows], sources: [], next_cursor: null};
const polledAtTop = {rows: [row('r5', '2026-09-13T14:00:00Z', 'Fifth'), ...polledWhileScrolled.rows], sources: [], next_cursor: null};

let timelineCall = 0;
const timelineResponses = [firstPage, polledWhileScrolled, polledAtTop];
const operationsFixture = {workspace: {name: 'OneSeo', path: '/tmp/oneseo'}, build: '0.1.57', projects: [], agents: [], coverage: [], supervisor: null, sources: [], orders: [], truncated: false, observed_at: new Date().toISOString()};

const scrollingElement = {scrollTop: 0};
const context = {
  URL, URLSearchParams, console, JSON, Date,
  AbortSignal: {timeout: () => ({})},
  location: new URL('/timeline', 'https://desk.example'),
  localStorage: {getItem() { return null; }, setItem() {}},
  fetch: async url => {
    const target = String(url);
    if (target.includes('/api/timeline')) {
      const data = timelineResponses[Math.min(timelineCall, timelineResponses.length - 1)];
      timelineCall++;
      return {ok: true, json: async () => data};
    }
    if (target.includes('/api/operations')) return {ok: true, json: async () => operationsFixture};
    return {ok: true, json: async () => ({repositories: []})};
  },
  setInterval() { return 1; },
  clearInterval() {},
  setTimeout() {},
  history: {replaceState() {}},
};
context.document = {
  getElementById: get,
  createElement: tag => new Element(tag),
  addEventListener() {},
  dispatchEvent() { return true; },
  hidden: false,
  scrollingElement,
  body: new Element('body'),
  querySelector: () => new Element(),
};
for (const id of ['timeline-project', 'timeline-source']) { const node = get(id); node.options = []; node.value = ''; node.add = o => node.options.push(o); }
context.readerNav = {readerHref: path => path};
context.changeFeed = {connectChanges() { return {stop() {}}; }};
context.reconcileListFn = reconcileList;
context.Option = class { constructor(text, value) { this.text = text; this.value = value; } };

let raw = read('../../static/js/operations.js');
raw = raw.slice(raw.indexOf("'use strict';"), raw.lastIndexOf('})();'));
raw = raw
  .replace("const {readerHref} = await import('/js/reader-navigation.mjs');", 'const {readerHref} = readerNav;')
  .replace("const {connectChanges} = await import('/js/change-feed.mjs');", 'const {connectChanges} = changeFeed;')
  .replace("const {reconcileList} = await import('/js/dom-reconcile.mjs');", 'const {reconcileList} = {reconcileList: reconcileListFn};')
  .replace("const {buildLoadByDay, paintLoad, paintDoors, paintSourceStrip, paintOutboundStrip} = await import('/js/calendar.v1.js');", 'const {buildLoadByDay, paintLoad, paintDoors, paintSourceStrip, paintOutboundStrip} = {buildLoadByDay(){return {state:"empty",origin:"",days:[],total:0};},paintLoad(){},paintDoors(){},paintSourceStrip(){},paintOutboundStrip(){}};');

const scopeKeys = Object.keys(context);
const scopeVals = Object.values(context);
const boot = new Function(...scopeKeys, `return (async () => { ${raw}
return {refreshTimeline, getTimelineData: () => timelineData}; })();`);
const runtime = await boot(...scopeVals);
const {refreshTimeline} = runtime;

// Settle the automatic page-load refreshTimeline(false) call (populates the first page).
for (let i = 0; i < 10 && !runtime.getTimelineData(); i++) await Promise.resolve();
await Promise.resolve();
await Promise.resolve();

assert.deepEqual(runtime.getTimelineData().rows.map(r => r.id), ['r3', 'r2', 'r1'], 'first page load must populate timelineData');

// Reader has scrolled down the default first page (no Load more used).
scrollingElement.scrollTop = 400;
await refreshTimeline(false);
assert.deepEqual(runtime.getTimelineData().rows.map(r => r.id), ['r3', 'r2', 'r1'],
  'a poll while scrolled down the first page must not move the reading position');
const newEventsButton = get('timeline-new-events');
assert.equal(newEventsButton.hidden, false, 'new-events affordance must show on the default first page too, not only after Load more');
assert.match(newEventsButton.textContent, /1 new event/);

// Reader scrolls back to the top: the next poll may replace the page.
scrollingElement.scrollTop = 0;
await refreshTimeline(false);
assert.deepEqual(runtime.getTimelineData().rows.map(r => r.id), ['r5', 'r4', 'r3', 'r2', 'r1'],
  'a poll at the top of the page may safely bring in the newest rows');

process.stdout.write(JSON.stringify({
  kept_position_while_scrolled: true,
  new_events_count_shown_on_first_page: newEventsButton.textContent,
  replaced_rows_when_at_top: runtime.getTimelineData().rows.map(r => r.id),
}));
