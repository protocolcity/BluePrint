// Agents coverage panel harness (pc-1480): seat cards before coverage, one
// collapsed unstaffed line, hire commands hidden until a disclosure opens,
// open Hire disclosures survive repaints, and unavailable stores stay active.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');

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
    this.checked = false;
    this.disabled = false;
    this.ownerDocument = {createElement: tag => new Element(tag)};
    this.classList = {
      add: name => { this.className = `${this.className} ${name}`.trim(); },
      remove: name => { this.className = this.className.split(/\s+/).filter(x => x && x !== name).join(' '); },
      toggle: () => {},
    };
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
  addEventListener(type, fn, options) {
    const capture = options === true || options?.capture;
    const key = capture ? `${type}:capture` : type;
    (this.listeners[key] ||= []).push(fn);
  }
  dispatchEvent(event) {
    const type = event?.type;
    const bubbles = event?.bubbles === true;
    const evt = {type, target: this, bubbles};
    const path = [];
    let node = this;
    while (node) {
      path.unshift(node);
      node = node.parent;
    }
    for (const n of path) {
      for (const fn of n.listeners[`${type}:capture`] || []) fn.call(n, evt);
    }
    for (const fn of this.listeners[type] || []) fn.call(this, evt);
    if (bubbles) {
      for (let i = path.length - 2; i >= 0; i--) {
        for (const fn of path[i].listeners[type] || []) fn.call(path[i], evt);
      }
    }
    return true;
  }
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  contains() { return false; }
  get textContent() {
    if (this.tagName === 'CODE') return this._text;
    if (this._text && !this.children.length) return this._text;
    return this.children.map(c => c.textContent || c._text || '').join('');
  }
  set textContent(value) { this._text = String(value ?? ''); }
  querySelector(sel) {
    const walk = node => {
      if (sel === 'details' && node.tagName === 'DETAILS') return node;
      if (sel === 'summary' && node.tagName === 'SUMMARY') return node;
      if (sel === 'code' && node.tagName === 'CODE') return node;
      if (sel === '.bp-coverage-hire' && node.className.includes('bp-coverage-hire')) return node;
      for (const child of node.children) {
        const hit = walk(child);
        if (hit) return hit;
      }
      return null;
    };
    return walk(this);
  }
  querySelectorAll(sel) {
    const out = [];
    const walk = node => {
      if (sel === 'details' && node.tagName === 'DETAILS') out.push(node);
      if (sel === 'details[data-coverage-project]' && node.tagName === 'DETAILS' && node.dataset.coverageProject) out.push(node);
      if (sel === 'code' && node.tagName === 'CODE') out.push(node);
      for (const child of node.children) walk(child);
    };
    walk(this);
    return out;
  }
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
    if (emptyText) {
      const p = new Element('p');
      p.className = 'bp-empty';
      p.textContent = emptyText;
      container.append(p);
    }
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
  'agents-next-fire', 'agents-pulse', 'agents-floor-remainder', 'agents-floor-empty', 'agents-floor-spark',
  'agents-hero', 'agents-coverage-door', 'agents-coverage-summary', 'agents-legend',
  'agents-quiet', 'agents-quiet-summary', 'agents-quiet-list',
  'restore-muted', 'refresh', 'desk-scope', 'desk-name', 'scope-path', 'preferences',
  'refresh-preference', 'motion-preference', 'preference-status', 'filters', 'search',
  'project-filter', 'assignment-filter', 'status-filter', 'deferred-toggle', 'show-deferred',
  'deferred-count', 'work-list', 'results', 'page-count', 'previous', 'next',
];
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, new Element());
  return nodes.get(id);
};

const fixture = {
  workspace: {name: 'OneSeo', path: '/tmp/oneseo'},
  build: '0.1.47',
  projects: [
    {id: 'blueprint', name: 'BluePrint', open: 3, attention: 0, working: 1, state: 'available'},
    {id: 'workforce', name: 'WorkForce', open: 2, attention: 0, working: 0, state: 'available'},
    {id: 'tradeos', name: 'tradeOS', open: 0, attention: 0, working: 0, state: 'unavailable'},
    {id: 'career', name: 'Career', open: 0, attention: 0, working: 0, state: 'available'},
    {id: 'comms', name: 'Comms', open: 0, attention: 0, working: 0, state: 'available'},
    {id: 'connector', name: 'Connector', open: 0, attention: 0, working: 0, state: 'available'},
    {id: 'gridfinity', name: 'Gridfinity', open: 0, attention: 0, working: 0, state: 'available'},
    {id: 'presentations', name: 'Presentations', open: 0, attention: 0, working: 0, state: 'available'},
    {id: 'socials', name: 'Socials', open: 0, attention: 0, working: 0, state: 'available'},
  ],
  agents: [
    {id: 'bp-cursor-implementer', name: 'Cursor implementer', group: 'seat', state: 'idle', badge: 'IDLE',
      badge_source: 'daemon', configured: true, action: 'dispatch', project_name: 'BluePrint', model: 'Cursor',
      schedule: 'manual', kind: 'lane', source: 'Local WorkForce', held: null, last_run: null, shift: null,
      report: null, configuration: 'Command configured', next_fire: null, held_verified: false,
      recovery_attempts: 0, preserved_reservation: false},
    {id: 'chief-of-staff', name: 'Chief of staff', group: 'job', state: 'idle', badge: 'IDLE',
      badge_source: 'daemon', configured: true, action: 'dispatch', project_name: null, model: 'Local job',
      schedule: '0 9 * * 1-5', kind: 'job', source: 'Local WorkForce', held: null, last_run: null, shift: null,
      report: null, configuration: 'Command configured', next_fire: null, held_verified: false,
      recovery_attempts: 0, preserved_reservation: false},
  ],
  coverage: [
    {project: 'blueprint', name: 'BluePrint', present: ['Claude', 'Cursor', 'Codex'], held: ['Grok'],
      missing: [], not_configured: [], text: 'BluePrint: Claude, Cursor, Codex OFF · missing Grok',
      hire_commands: {}, install_hints: {}, sources: {}},
    {project: 'workforce', name: 'WorkForce', present: [], held: [], missing: ['Claude', 'Cursor'],
      not_configured: ['Grok', 'Codex'], text: 'WorkForce: none staffed · missing Claude, Cursor · not configured: Grok, Codex',
      hire_commands: {
        Claude: 'workforce hire wf-claude-implementer --provider claude --project workforce --repository /tmp/oneseo/workforce --schedule manual',
        Cursor: 'workforce hire wf-cursor-implementer --provider cursor --project workforce --repository /tmp/oneseo/workforce --schedule manual',
      },
      install_hints: {Grok: 'Install Grok CLI', Codex: 'Install Codex CLI'}, sources: {}},
    {project: 'tradeos', name: 'tradeOS', present: [], held: [], missing: ['Claude'], not_configured: ['Cursor', 'Grok', 'Codex'],
      text: 'tradeOS: none staffed · missing Claude', hire_commands: {Claude: 'workforce hire ts-claude-implementer --provider claude --project tradeos --repository /tmp/oneseo/tradeos --schedule manual'},
      install_hints: {}, sources: {}},
    {project: 'career', name: 'Career', present: [], held: [], missing: ['Claude'], not_configured: ['Cursor', 'Grok', 'Codex'],
      text: 'Career: none staffed · missing Claude', hire_commands: {Claude: 'workforce hire career-claude-implementer --provider claude --project career --repository /tmp/oneseo/career --schedule manual'},
      install_hints: {}, sources: {}},
    {project: 'comms', name: 'Comms', present: [], held: [], missing: ['Claude'], not_configured: ['Cursor', 'Grok', 'Codex'],
      text: 'Comms: none staffed · missing Claude', hire_commands: {Claude: 'workforce hire comms-claude-implementer --provider claude --project comms --repository /tmp/oneseo/comms --schedule manual'},
      install_hints: {}, sources: {}},
    {project: 'connector', name: 'Connector', present: [], held: [], missing: ['Claude'], not_configured: ['Cursor', 'Grok', 'Codex'],
      text: 'Connector: none staffed · missing Claude', hire_commands: {Claude: 'workforce hire conn-claude-implementer --provider claude --project connector --repository /tmp/oneseo/connector --schedule manual'},
      install_hints: {}, sources: {}},
    {project: 'gridfinity', name: 'Gridfinity', present: [], held: [], missing: ['Claude'], not_configured: ['Cursor', 'Grok', 'Codex'],
      text: 'Gridfinity: none staffed · missing Claude', hire_commands: {Claude: 'workforce hire gf-claude-implementer --provider claude --project gridfinity --repository /tmp/oneseo/gridfinity --schedule manual'},
      install_hints: {}, sources: {}},
    {project: 'presentations', name: 'Presentations', present: [], held: [], missing: ['Claude'], not_configured: ['Cursor', 'Grok', 'Codex'],
      text: 'Presentations: none staffed · missing Claude', hire_commands: {Claude: 'workforce hire pr-claude-implementer --provider claude --project presentations --repository /tmp/oneseo/presentations --schedule manual'},
      install_hints: {}, sources: {}},
    {project: 'socials', name: 'Socials', present: [], held: [], missing: ['Claude'], not_configured: ['Cursor', 'Grok', 'Codex'],
      text: 'Socials: none staffed · missing Claude', hire_commands: {Claude: 'workforce hire so-claude-implementer --provider claude --project socials --repository /tmp/oneseo/socials --schedule manual'},
      install_hints: {}, sources: {}},
  ],
  supervisor: null,
  sources: [{name: 'WorkForce heartbeat', state: 'fresh', last_at: new Date().toISOString()}],
  orders: [],
  truncated: false,
  observed_at: new Date().toISOString(),
};

class Option {
  constructor(text, value) { this.text = text; this.value = value; }
}
const context = {
  URL, URLSearchParams, console, JSON, Option, AbortSignal: {timeout: () => ({})},
  location: new URL('/agents', 'https://desk.example'),
  localStorage: {getItem() { return null; }, setItem() {}},
  navigator: {clipboard: {writeText() {}}},
  fetch: async url => {
    if (String(url).includes('/api/operations')) return {ok: true, json: async () => fixture};
    return {ok: true, json: async () => ({repositories: []})};
  },
  setInterval() { return 1; },
  clearInterval() {},
  setTimeout() {},
  Date,
  history: {replaceState() {}},
};
context.document = {
  getElementById: get,
  createElement: tag => new Element(tag),
  addEventListener() {},
  dispatchEvent() { return true; },
  body: new Element('body'),
  hidden: false,
  querySelector: sel => {
    if (sel === '[data-page="agents"]') {
      const a = new Element('a');
      a.setAttribute = () => {};
      return a;
    }
    return null;
  },
};
function wireSelect(id) {
  const node = get(id);
  node.options = [];
  node.value = '';
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
  .replace("const {reconcileList} = await import('/js/dom-reconcile.mjs');", 'const {reconcileList} = {reconcileList: reconcileListFn};')
  .replace("const {buildLoadByDay, paintLoad, paintDoors, paintSourceStrip, paintOutboundStrip, applyHybridMarks, paintHybridMark, capAgendaDay} = await import('/js/calendar.v1.js');", 'const {buildLoadByDay, paintLoad, paintDoors, paintSourceStrip, paintOutboundStrip, applyHybridMarks, paintHybridMark, capAgendaDay} = {buildLoadByDay(){return {state:"empty",origin:"",days:[],total:0};},paintLoad(){},paintDoors(){},paintSourceStrip(){},paintOutboundStrip(){},applyHybridMarks(items){return items||[];},paintHybridMark(){},capAgendaDay(items){const rows=items||[];return {shown:rows,remainder:0,total:rows.length};}};');
;
const bootMarker = 'connectChanges(()=>{if(!document.hidden){refresh();';
const bootAt = raw.indexOf(bootMarker);
if (bootAt === -1) throw new Error('operations.js boot marker missing');
raw = raw.slice(0, bootAt) + `snapshot = ${JSON.stringify(fixture)};`;
const scopeKeys = Object.keys(context);
const scopeVals = Object.values(context);
const boot = new Function(...scopeKeys, `return (async () => { ${raw} return {agents, snapshot}; })();`);
const runtime = await boot(...scopeVals);
const {agents} = runtime;

agents();

const seatList = get('seat-list');
const coverageList = get('coverage-list');
const domText = node => {
  const bits = [];
  const walk = n => {
    if (n.tagName === 'DETAILS' && !n.open) {
      const summary = n.children.find(c => c.tagName === 'SUMMARY');
      if (summary) walk(summary);
      return;
    }
    if (n._text) bits.push(n._text);
    if (n.tagName === 'CODE') bits.push(n._text || '');
    for (const child of n.children || []) walk(child);
  };
  walk(node);
  return bits.join(' ');
};

assert.ok(seatList.children.length > 0, 'seat cards must render');
assert.ok(coverageList.children.length > 0, 'coverage panel must render');

const seatIndex = Array.from(nodes.values()).indexOf(seatList);
const coverageIndex = Array.from(nodes.values()).indexOf(coverageList);
assert.ok(seatIndex < coverageIndex, 'seat cards must render before coverage panel');

const collapsed = coverageList.children.find(c => c.className.includes('bp-coverage-collapsed'));
assert.ok(collapsed, 'unstaffed projects must collapse into one line');
assert.match(collapsed.querySelector('summary').textContent, /6 projects unstaffed/);
assert.equal(coverageList.children.filter(c => c.className.includes('bp-coverage-collapsed')).length, 1,
  'exactly one collapsed unstaffed line');

const unavailableRow = coverageList.children.find(c =>
  c.className.includes('bp-coverage-row') && domText(c).includes('tradeOS') && domText(c).includes('Store unavailable'));
assert.ok(unavailableRow, 'unavailable store must render as its own active row');
assert.ok(!domText(collapsed).includes('tradeOS'), 'unavailable store must not sit inside the collapsed line');

const closedText = domText(coverageList);
assert.ok(!/workforce hire/i.test(closedText), 'hire commands must stay hidden until disclosure opens');
assert.ok(!/classifier/i.test(closedText), 'classifier jargon must not appear');
assert.equal(coverageList.querySelectorAll('code').length, 0, 'closed rows must not contain hire command nodes');
const noHireNodesWhileClosed = coverageList.querySelectorAll('code').length === 0;

const hireDisclosure = coverageList.querySelectorAll('details[data-coverage-project]').find(d => {
  const summary = d.children.find(c => c.tagName === 'SUMMARY');
  return summary && summary.textContent === 'Hire…' && d.dataset.coverageProject === 'workforce';
});
assert.ok(hireDisclosure, 'an active row must expose a Hire disclosure');
hireDisclosure.open = true;
hireDisclosure.dispatchEvent({type: 'toggle', bubbles: false});
const openText = domText(coverageList);
assert.ok(/workforce hire/i.test(openText), 'opening disclosure must reveal hire commands');
assert.ok(coverageList.querySelectorAll('code').length > 0, 'opened disclosure must render hire command nodes');

agents();
assert.ok(hireDisclosure.open, 'opened Hire disclosure must stay open across repaint');
assert.ok(/workforce hire/i.test(domText(coverageList)), 'repaint must keep opened hire commands visible');

process.stdout.write(JSON.stringify({
  seat_count: seatList.children.length,
  coverage_active_rows: coverageList.children.filter(c => c.className.includes('bp-coverage-row')).length,
  collapsed_summary: collapsed.querySelector('summary').textContent,
  hire_hidden_until_open: !/workforce hire/i.test(closedText),
  no_classifier: !/classifier/i.test(closedText),
  hire_open_survives_repaint: hireDisclosure.open && /workforce hire/i.test(domText(coverageList)),
  unavailable_store_active: Boolean(unavailableRow),
  no_hire_nodes_while_closed: noHireNodesWhileClosed,
}));
