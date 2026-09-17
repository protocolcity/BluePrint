// pc-1534: Agents Floor | Canvas toggle — read-only spatial twin.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {reconcileList} from '../../static/js/dom-reconcile.mjs';

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
    this.style = {};
    this.hidden = false;
    this.open = false;
    this.disabled = false;
    this._text = '';
    this.type = '';
    this.href = '';
    this.value = '';
    this.selectedOptions = [{text: ''}];
    this.ownerDocument = {
      createElement: t => new Element(t),
      createElementNS: (_ns, t) => new Element(t),
      createTextNode: t => Object.assign(new Element('#text'), {_text: String(t), textContent: String(t)}),
    };
    this.classList = {
      add: name => { this.className = `${this.className} ${name}`.trim(); },
      remove: name => { this.className = this.className.split(/\s+/).filter(x => x && x !== name).join(' '); },
      contains: name => this.className.split(/\s+/).includes(name),
      toggle: (name, on) => { if (on === false) this.classList.remove(name); else this.classList.add(name); },
    };
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  append(...nodes) {
    for (const node of nodes) {
      const child = typeof node === 'string' ? Object.assign(new Element('#text'), {_text: node, textContent: node}) : node;
      child.parent = this;
      child.parentElement = this;
      this.children.push(child);
    }
  }
  appendChild(node) { this.append(node); return node; }
  insertBefore(node, ref) {
    const idx = ref ? this.children.indexOf(ref) : this.children.length;
    node.parent = this;
    node.parentElement = this;
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
  replaceChildren(...nodes) { this.children.length = 0; this.childNodes = this.children; this.append(...nodes); }
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === 'class') this.className = String(value);
  }
  hasClass(name) {
    return String(this.className || '').split(/\s+/).includes(name);
  }
  querySelector(sel) {
    return this.querySelectorAll(sel)[0] || null;
  }
  querySelectorAll(sel) {
    const out = [];
    const walk = node => {
      if (sel === 'a' && node.tagName === 'A') out.push(node);
      if (sel.startsWith('.') && node.hasClass(sel.slice(1))) out.push(node);
      if (sel.startsWith('[data-kind=') && node.dataset && node.dataset.kind === sel.slice(12, -2)) out.push(node);
      if (sel.startsWith('[data-id=') && node.dataset && node.dataset.id === sel.slice(10, -2)) out.push(node);
      if (sel.startsWith('[data-agent-id=') && node.dataset && node.dataset.agentId === sel.slice(16, -2)) out.push(node);
      for (const child of node.children || []) walk(child);
    };
    walk(this);
    return out;
  }
  get textContent() {
    if (this._text && !this.children.length) return this._text;
    return this.children.map(c => c.textContent || c._text || '').join('');
  }
  set textContent(value) { this._text = String(value ?? ''); this.children.length = 0; }
}

const IDS = [
  'page-title', 'page-description', 'eyebrow', 'freshness', 'source-warning', 'footer-status',
  'refresh', 'desk-scope', 'desk-name', 'scope-path', 'restore-muted', 'refresh-preference',
  'motion-preference', 'preferences', 'preference-status', 'search', 'project-filter',
  'assignment-filter', 'status-filter', 'gate-filter', 'kind-filter', 'attention-filter',
  'filters', 'work-list', 'results', 'page-count', 'previous', 'next', 'clear-filters',
  'active-filters', 'overview-view', 'work-view', 'agents-view', 'calendar-view',
  'seat-list', 'job-list', 'agent-detail', 'supervisor-panel', 'coverage-list',
  'agents-heartbeat', 'agents-next-fire', 'agents-pulse', 'agents-floor-remainder',
  'agents-floor-empty', 'agents-floor-spark', 'agents-quiet', 'agents-quiet-summary', 'agents-quiet-list',
  'agents-face', 'agents-face-floor', 'agents-face-canvas', 'agents-floor-lists',
  'agents-canvas-wrap', 'agents-canvas', 'agents-canvas-empty',
  'timeline-project', 'timeline-source',
];
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, new Element());
  return nodes.get(id);
};

function agent(id, state, extra = {}) {
  return {
    id, name: id, group: extra.group || 'seat', state, badge: extra.badge || state.toUpperCase(),
    badge_source: 'engine ledger', configured: true, action: state === 'idle' ? 'dispatch' : null,
    project_name: extra.project_name || 'BluePrint', model: 'Claude',
    held: extra.held || null, held_verified: Boolean(extra.held), finishing: false, parked: null,
    shift: extra.shift || null, last_run: extra.last_run || null, schedule: extra.schedule || 'manual',
    next_fire: extra.next_fire || null, report: null, last_candidates: [], recovery_attempts: 0,
    preserved_reservation: false,
  };
}

const later = new Date(Date.now() + 12 * 60 * 1000).toISOString();
const canvas = {
  empty: false,
  empty_reason: '',
  width: 480,
  height: 320,
  nodes: [
    {id: 'working-seat', kind: 'seat', label: 'working-seat', badge: 'WORKING', bucket: 'working', group: 'seat', x: 24, y: 24, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:working-seat', claim: {label: 'Live claim · pc-9', href: '/work-order?project=blueprint&id=pc-9'}},
    {id: 'work:blueprint:pc-9', kind: 'work', label: 'Live claim · pc-9', href: '/work-order?project=blueprint&id=pc-9', door: 'ticket', bucket: 'target', x: 268, y: 24, w: 188, h: 58},
    {id: 'idle-seat', kind: 'seat', label: 'idle-seat', badge: 'IDLE', bucket: 'idle', group: 'seat', x: 24, y: 98, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:idle-seat'},
    {id: 'failed-seat', kind: 'seat', label: 'failed-seat', badge: 'LAST RUN FAILED', bucket: 'error', group: 'seat', x: 24, y: 172, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:failed-seat'},
    {id: 'off-seat', kind: 'seat', label: 'off-seat', badge: 'OFF', bucket: 'quiet', group: 'seat', x: 24, y: 246, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:off-seat'},
    {id: 'loop-health', kind: 'job', label: 'loop-health', badge: 'IDLE', bucket: 'idle', group: 'job', x: 24, y: 332, w: 188, h: 58, door: ''},
    {id: 'fire:loop-health', kind: 'fire', label: 'Next fire · in 12m', href: '/calendar', door: 'calendar', bucket: 'target', x: 268, y: 332, w: 188, h: 58},
  ],
  edges: [
    {from: 'working-seat', to: 'work:blueprint:pc-9', kind: 'claim'},
    {from: 'loop-health', to: 'fire:loop-health', kind: 'next_fire'},
  ],
};
const fixture = {
  workspace: {name: 'Desk', path: '/tmp/desk'},
  build: '0.1.51',
  projects: [],
  orders: [{id: 'pc-9', project: 'blueprint', project_name: 'BluePrint', title: 'Live claim'}],
  agents: [
    agent('working-seat', 'working', {
      held: {id: 'pc-9', project: 'blueprint', title: 'Live claim'},
      shift: {started_at: '2026-09-17T03:00:00Z', age_seconds: 120, budget_secs: 1500, stale: false, lock_held: true, source: 'ledger'},
    }),
    agent('idle-seat', 'idle'),
    agent('failed-seat', 'last_run_failed', {badge: 'LAST RUN FAILED', last_run: {outcome: 'ERROR', reason: 'agent exit', at: '2026-09-17T02:00:00Z'}}),
    agent('off-seat', 'off', {badge: 'OFF'}),
    agent('loop-health', 'idle', {group: 'job', schedule: '5,35 * * * *', next_fire: later, badge: 'IDLE'}),
  ],
  agents_floor: {
    working: 1, idle: 2, error: 1, stale: 0, quiet: 1,
    sparks: {
      'working-seat': {hours: Array.from({length: 24}, (_, i) => i === 4 || i === 23 ? 1 : 0), fails: Array(24).fill(0), runs: 2, errors: 0, fail_rate: 0, state: 'healthy'},
      'idle-seat': {hours: Array(24).fill(0), fails: Array(24).fill(0), runs: 0, errors: 0, fail_rate: null, state: 'empty'},
      'failed-seat': {hours: Array.from({length: 24}, (_, i) => i === 22 ? 1 : 0), fails: Array.from({length: 24}, (_, i) => i === 22 ? 1 : 0), runs: 1, errors: 1, fail_rate: 1, state: 'healthy'},
      'off-seat': {hours: Array(24).fill(0), fails: Array(24).fill(0), runs: 0, errors: 0, fail_rate: null, state: 'empty'},
      'loop-health': {hours: Array.from({length: 24}, (_, i) => i === 10 ? 1 : 0), fails: Array(24).fill(0), runs: 1, errors: 0, fail_rate: 0, state: 'healthy'},
    },
    throughput: {
      hours: Array.from({length: 24}, (_, i) => (i === 4 || i === 10 || i === 22 || i === 23) ? 1 : 0),
      fails: Array.from({length: 24}, (_, i) => i === 22 ? 1 : 0),
      runs: 4, errors: 1, fail_rate: 0.25, state: 'healthy',
    },
  },
  agents_canvas: canvas,
  coverage: [],
  supervisor: null,
  sources: [{name: 'WorkForce heartbeat', state: 'fresh', last_at: new Date().toISOString()}],
  calendar_doors: {due_count: 0, due_href: '/calendar', items: [], next_fire: {name: 'loop-health', seconds: 12 * 60}, next_fire_line: 'Next fire · loop-health in 12m'},
  events: [],
  work_dates: [],
  truncated: false,
  observed_at: new Date().toISOString(),
};

const context = {
  URL, URLSearchParams, console, JSON,
  Option: class { constructor(text, value) { this.text = text; this.value = value; } },
  location: new URL('/agents', 'https://desk.example'),
  localStorage: {getItem() { return null; }, setItem() {}},
  fetch: async () => ({ok: true, json: async () => fixture}),
  setInterval() { return 1; },
  clearInterval() {},
  setTimeout() {},
  Date,
  history: {replaceState() {}},
};
context.document = {
  getElementById: get,
  createElement: tag => new Element(tag),
  createElementNS: (_ns, tag) => new Element(tag),
  createTextNode: text => Object.assign(new Element('#text'), {_text: String(text), textContent: String(text)}),
  addEventListener() {},
  hidden: false,
  querySelector: sel => {
    if (String(sel).includes('data-page')) {
      const a = new Element('a');
      a.setAttribute = () => {};
      return a;
    }
    return null;
  },
  body: new Element('body'),
};
context.document.body.classList = {toggle() {}, contains() { return false; }};
function wireSelect(id) {
  const node = get(id);
  node.options = [];
  node.value = '';
  node.replaceChildren = (...opts) => { node.options = [...opts]; node.children = [...opts]; };
  node.add = option => { node.options.push(option); node.children.push(option); };
  return node;
}
for (const id of IDS) get(id);
for (const id of ['project-filter', 'assignment-filter', 'status-filter', 'gate-filter', 'kind-filter',
  'attention-filter', 'timeline-project', 'timeline-source', 'refresh-preference', 'motion-preference']) wireSelect(id);
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
  .replace("const {buildLoadByDay, paintLoad, paintDoors} = await import('/js/calendar.v1.js');", 'const {buildLoadByDay, paintLoad, paintDoors} = {buildLoadByDay(){return {state:"empty",origin:"",days:[],total:0};},paintLoad(){},paintDoors(){}};');
const bootMarker = 'connectChanges(()=>{if(!document.hidden){refresh();';
const bootAt = raw.indexOf(bootMarker);
if (bootAt === -1) throw new Error('operations.js boot marker missing');
raw = raw.slice(0, bootAt) + `snapshot = ${JSON.stringify(fixture)}; lastSuccess = Date.now();`;
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {agents, setAgentsView, applySnapshot(next){ snapshot = next; }}; })();`);
const runtime = await boot(...Object.values(context));

runtime.agents();
const pulse = get('agents-pulse').querySelectorAll('.bp-metric').map(n => n.textContent.replace(/\s+/g, ''));
assert.deepEqual(pulse, ['1Working', '2Idle', '1Error']);
assert.equal(get('agents-floor-lists').hidden, false);
assert.equal(get('agents-canvas-wrap').hidden, true);
assert.match(get('agents-floor-spark').textContent, /4 runs · last 24h/);

runtime.setAgentsView('canvas');
assert.equal(get('agents-face-canvas').attributes['aria-pressed'], 'true');
assert.equal(get('agents-face-floor').attributes['aria-pressed'], 'false');
assert.equal(get('agents-floor-lists').hidden, true);
assert.equal(get('agents-canvas-wrap').hidden, false);
assert.equal(get('agents-canvas').hidden, false);
assert.equal(get('agents-canvas-empty').hidden, true);
assert.match(get('agents-pulse').textContent.replace(/\s+/g, ''), /1Working/);
assert.match(get('agents-floor-spark').textContent, /4 runs · last 24h/);

const cards = get('agents-canvas').querySelectorAll('.bp-agents-canvas-node');
const seatIds = cards.filter(n => n.dataset.kind === 'seat').map(n => n.dataset.id);
const jobIds = cards.filter(n => n.dataset.kind === 'job').map(n => n.dataset.id);
const working = cards.find(n => n.dataset.id === 'working-seat');
assert.deepEqual(seatIds, ['working-seat', 'idle-seat', 'failed-seat', 'off-seat']);
assert.deepEqual(jobIds, ['loop-health']);
assert.equal(working.dataset.bucket, 'working');
assert.ok(working.querySelector('.bp-shift-cue'));

const edges = get('agents-canvas').querySelectorAll('.bp-agents-canvas-edge');
assert.ok(edges.some(edge => edge.dataset.kind === 'claim'));
assert.ok(edges.some(edge => edge.dataset.kind === 'next_fire'));

const links = get('agents-canvas').querySelectorAll('a');
assert.ok(links.some(a => String(a.href).includes('/work?assignment=worker:idle-seat')), 'seats without a held WO still get the generic Work link');
assert.ok(links.some(a => String(a.href).includes('/work-order?project=blueprint&id=pc-9')));
assert.ok(links.some(a => String(a.href) === '/calendar'));
assert.ok(!cards.some(n => n.draggable), 'canvas nodes are not an editor');

const claimChip = working.querySelectorAll('.bp-agents-canvas-claim')[0];
assert.ok(claimChip, 'claimed WO is visible directly on the seat node');
assert.match(claimChip.textContent, /Live claim.*pc-9/);
assert.equal(claimChip.href, '/work-order?project=blueprint&id=pc-9');
assert.ok(!working.querySelectorAll('.bp-agents-canvas-chip').some(a => a.textContent === 'Work'), 'claim chip replaces the generic Work link once a WO is held');

const emptyCanvas = {
  ...fixture,
  agents: [],
  agents_floor: {working: 0, idle: 0, error: 0, stale: 0, quiet: 0, sparks: {}},
  agents_canvas: {nodes: [], edges: [], width: 0, height: 0, empty: true, empty_reason: 'No seats or jobs on this roster.'},
};
runtime.applySnapshot(emptyCanvas);
runtime.agents();
assert.equal(get('agents-canvas-empty').hidden, false);
assert.equal(get('agents-canvas-empty').textContent, 'No seats or jobs on this roster.');
assert.equal(get('agents-canvas').hidden, true);

runtime.applySnapshot(fixture);
runtime.setAgentsView('floor');
assert.equal(get('agents-floor-lists').hidden, false);
assert.equal(get('agents-canvas-wrap').hidden, true);
assert.equal(get('agents-face-floor').attributes['aria-pressed'], 'true');

process.stdout.write(JSON.stringify({
  pulse,
  floor_lists_visible: true,
  canvas_hidden_on_floor: true,
  canvas_visible: true,
  floor_lists_hidden_on_canvas: true,
  seat_ids: seatIds,
  job_ids: jobIds,
  working_bucket: 'working',
  has_claim_edge: true,
  has_next_fire_edge: true,
  work_chip: true,
  ticket_door: true,
  empty_roster: 'No seats or jobs on this roster.',
  floor_back: true,
}));
