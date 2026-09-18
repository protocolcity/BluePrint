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
    this.scrollIntoView = () => {};
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
  removeAttribute(name) {
    delete this.attributes[name];
    if (name === 'class') this.className = '';
    if (name.startsWith('data-') && this.dataset) {
      const key = name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      this.dataset[key] = '';
    }
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
  'agents-hero', 'agents-coverage-door', 'agents-coverage-summary', 'agents-legend',
  'agents-floor-empty', 'agents-floor-spark', 'agents-quiet', 'agents-quiet-summary', 'agents-quiet-list',
  'agents-face', 'agents-face-floor', 'agents-face-canvas', 'agents-floor-lists',
  'agents-canvas-wrap', 'agents-canvas', 'agents-canvas-empty', 'agents-canvas-legend',
  'agents-canvas-empty-teach', 'agents-canvas-tour', 'agents-canvas-tour-kicker',
  'agents-canvas-tour-copy', 'agents-canvas-tour-next', 'agents-canvas-tour-back',
  'agents-canvas-tour-skip', 'agents-canvas-tour-start',
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
    {id: 'working-seat', kind: 'seat', label: 'working-seat', shape: 'rounded', project: 'BluePrint', badge: 'WORKING', bucket: 'working', group: 'seat', x: 24, y: 24, w: 196, h: 92, door: 'person', work_href: '/work?assignment=worker:working-seat', claim: {label: 'Live claim · pc-9', href: '/work-order?project=blueprint&id=pc-9', order_id: 'pc-9'}},
    {id: 'work:blueprint:pc-9', kind: 'work', label: 'Live claim · pc-9', href: '/work-order?project=blueprint&id=pc-9', door: 'ticket', bucket: 'target', x: 268, y: 24, w: 188, h: 58},
    {id: 'idle-seat', kind: 'seat', label: 'idle-seat', badge: 'IDLE', bucket: 'idle', group: 'seat', x: 24, y: 98, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:idle-seat'},
    {id: 'failed-seat', kind: 'seat', label: 'failed-seat', badge: 'LAST RUN FAILED', bucket: 'error', group: 'seat', x: 24, y: 172, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:failed-seat'},
    {id: 'run:failed-seat', kind: 'last_run', label: 'Last run · failed', title: 'agent exit', outcome: 'error', href: '/timeline?actor=failed-seat', door: 'timeline', bucket: 'error', x: 268, y: 172, w: 188, h: 58},
    {id: 'off-seat', kind: 'seat', label: 'off-seat', badge: 'OFF', bucket: 'quiet', group: 'seat', x: 24, y: 246, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:off-seat'},
    {id: 'loop-health', kind: 'job', label: 'loop-health', shape: 'diamond', badge: 'IDLE', bucket: 'idle', group: 'job', x: 24, y: 332, w: 196, h: 92, door: '', fire: {label: 'Next fire · in 12m', href: '/calendar'}},
    {id: 'fire:loop-health', kind: 'fire', label: 'Next fire · in 12m', href: '/calendar', door: 'calendar', bucket: 'target', x: 268, y: 332, w: 188, h: 58},
  ],
  edges: [
    {from: 'working-seat', to: 'work:blueprint:pc-9', kind: 'claim', tone: 'working'},
    {from: 'failed-seat', to: 'run:failed-seat', kind: 'last_run', tone: 'error'},
    {from: 'loop-health', to: 'fire:loop-health', kind: 'next_fire', tone: 'next_fire'},
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
  localStorage: {
    _store: {},
    getItem(key) { return Object.prototype.hasOwnProperty.call(this._store, key) ? this._store[key] : null; },
    setItem(key, value) { this._store[key] = String(value); },
    removeItem(key) { delete this._store[key]; },
  },
  fetch: async () => ({ok: true, json: async () => fixture}),
  setInterval() { return 1; },
  clearInterval() {},
  setTimeout() {},
  Date,
  historyHref: '',
};
context.history = {replaceState(_state, _title, url) { context.historyHref = String(url || ''); }};
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
  .replace("const {buildLoadByDay, paintLoad, paintDoors, paintSourceStrip, paintOutboundStrip} = await import('/js/calendar.v1.js');", 'const {buildLoadByDay, paintLoad, paintDoors, paintSourceStrip, paintOutboundStrip} = {buildLoadByDay(){return {state:"empty",origin:"",days:[],total:0};},paintLoad(){},paintDoors(){},paintSourceStrip(){},paintOutboundStrip(){}};');
const bootMarker = 'connectChanges(()=>{if(!document.hidden){refresh();';
const bootAt = raw.indexOf(bootMarker);
if (bootAt === -1) throw new Error('operations.js boot marker missing');
raw = raw.slice(0, bootAt) + `snapshot = ${JSON.stringify(fixture)}; lastSuccess = Date.now();`;
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {agents, setAgentsView, startAgentsTour, advanceAgentsTour, retreatAgentsTour, endAgentsTour, applySnapshot(next){ snapshot = next; }}; })();`);
const runtime = await boot(...Object.values(context));

function fire(id) {
  for (const fn of get(id).listeners.click || []) fn({preventDefault() {}});
}

runtime.agents();
const pulse = get('agents-pulse').querySelectorAll('.bp-metric').map(n => n.textContent.replace(/\s+/g, ''));
assert.deepEqual(pulse, ['1Working', '2Idle', '1Error']);
assert.equal(get('agents-floor-lists').hidden, false);
assert.equal(get('agents-canvas-wrap').hidden, true);
assert.equal(get('agents-canvas-tour').hidden, true, 'tour stays off on Floor');
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
assert.match(context.historyHref, /face=canvas/);
assert.ok(!context.historyHref.includes('view=canvas'), 'canonical deep-link is face=canvas');
assert.equal(get('agents-view').dataset.face, 'canvas');
assert.ok(get('agents-canvas-legend'), 'canvas legend host stays on Agents');

const cards = get('agents-canvas').querySelectorAll('.bp-agents-canvas-node');
const seatIds = cards.filter(n => n.dataset.kind === 'seat').map(n => n.dataset.id);
const jobIds = cards.filter(n => n.dataset.kind === 'job').map(n => n.dataset.id);
const working = cards.find(n => n.dataset.id === 'working-seat');
assert.deepEqual(seatIds, ['working-seat', 'idle-seat', 'failed-seat', 'off-seat']);
assert.deepEqual(jobIds, ['loop-health']);
assert.equal(working.dataset.bucket, 'working');
assert.equal(working.dataset.shape, 'rounded');
assert.ok(working.querySelector('.bp-shift-cue'));
assert.match(working.textContent, /BluePrint/);
assert.ok(working.querySelector('.bp-agents-canvas-project'), 'seat shows project label');
assert.ok(working.querySelector('.bp-agents-canvas-spark'), 'optional spark paints when Floor has runs');

const edges = get('agents-canvas').querySelectorAll('.bp-agents-canvas-edge');
const claimEdge = edges.find(edge => edge.dataset.kind === 'claim');
const lastRunEdge = edges.find(edge => edge.dataset.kind === 'last_run');
assert.ok(claimEdge, 'claim edge is painted');
assert.equal(claimEdge.dataset.motion, 'pulse', 'claimed/active links pulse');
assert.equal(claimEdge.dataset.tone, 'working');
assert.ok(lastRunEdge, 'last-run edge is painted');
assert.equal(lastRunEdge.dataset.tone, 'error', 'failed last-run stays error on the edge');
assert.ok(edges.some(edge => edge.dataset.kind === 'next_fire'));

const links = get('agents-canvas').querySelectorAll('a');
assert.ok(links.some(a => String(a.href).includes('/work?assignment=worker:idle-seat')), 'seats without a held WO still get the generic Work link');
assert.ok(links.some(a => String(a.href).includes('/work-order?project=blueprint&id=pc-9')));
assert.ok(links.some(a => String(a.href) === '/calendar'));
assert.ok(links.some(a => String(a.href) === '/timeline?actor=failed-seat'), 'a failed last run opens a Timeline door scoped to that seat');
const failedRun = cards.find(n => n.dataset.id === 'run:failed-seat');
assert.ok(failedRun, 'last-run target node is painted');
assert.equal(failedRun.dataset.bucket, 'error', 'a failed last run stays error, not softened');
assert.ok(!cards.some(n => n.draggable), 'canvas nodes are not an editor');

const claimChip = working.querySelectorAll('.bp-agents-canvas-claim')[0];
assert.ok(claimChip, 'claimed WO is visible directly on the seat node');
assert.match(claimChip.textContent, /Live claim.*pc-9/);
assert.equal(claimChip.href, '/work-order?project=blueprint&id=pc-9');
assert.ok(!working.querySelectorAll('.bp-agents-canvas-chip').some(a => a.textContent === 'Work'), 'claim chip replaces the generic Work link once a WO is held');
const job = cards.find(n => n.dataset.id === 'loop-health');
assert.equal(job.dataset.shape, 'diamond');
const fireChip = job && job.querySelectorAll('.bp-agents-canvas-fire')[0];
assert.ok(fireChip, 'next-fire tick is visible on the job node');
assert.match(fireChip.textContent, /Next fire/);
assert.equal(fireChip.href, '/calendar');
assert.ok(job.querySelectorAll('.bp-agents-canvas-tick').length >= 5, 'calendar door paints ticks on the job');
const fireDoor = cards.find(n => n.dataset.id === 'fire:loop-health');
assert.ok(fireDoor && fireDoor.querySelectorAll('.bp-agents-canvas-tick').length >= 5, 'next-fire door keeps ticks');
assert.ok(get('agents-hero'), 'Floor scarcity hero host stays on Agents');
assert.equal(get('agents-coverage-door').open, false, 'Coverage door stays collapsed on Canvas');

assert.equal(get('agents-canvas-tour').hidden, false, 'unseen canvas starts the acquaintance tour');
assert.equal(get('agents-canvas-tour').dataset.step, 'strip');
assert.equal(get('agents-pulse').dataset.tourFocus, 'true');
assert.match(get('agents-canvas-tour-kicker').textContent, /1 of 3/);
assert.match(get('agents-canvas-tour-copy').textContent, /Working, Idle, and Error/);
assert.match(get('agents-canvas-tour-copy').textContent, /n8n-style factory/);
const tourFactory = get('agents-canvas-tour-copy').textContent;
assert.equal(get('agents-canvas-tour-next').textContent, 'Next');
assert.equal(get('agents-canvas-empty-teach').hidden, true);
fire('agents-canvas-tour-next');
assert.equal(get('agents-canvas-tour').dataset.step, 'node');
assert.equal(working.dataset.tourFocus, 'true', 'step 2 focuses a seat node');
assert.equal(get('agents-pulse').dataset.tourFocus, '');
assert.match(get('agents-canvas-tour-copy').textContent, /seat or a job/);
fire('agents-canvas-tour-next');
assert.equal(get('agents-canvas-tour').dataset.step, 'door');
assert.equal(failedRun.dataset.tourFocus, 'true', 'step 3 focuses the Timeline last-run door');
assert.equal(get('agents-canvas-tour-next').textContent, 'Done');
assert.match(get('agents-canvas-tour-copy').textContent, /Work for a claim, Timeline/);
fire('agents-canvas-tour-next');
assert.equal(get('agents-canvas-tour').hidden, true);
assert.equal(context.localStorage.getItem('bp-agents-canvas-tour'), 'seen');
const personDoor = get('agents-canvas').querySelectorAll('.bp-agents-canvas-node').find(n => n.dataset.id === 'working-seat');
const person = personDoor && personDoor.querySelector('.bp-agents-canvas-person');
assert.ok(person, 'seat node is a person door, not an edit handle');
for (const fn of person.listeners.click || []) fn({preventDefault() {}});
assert.equal(get('agent-detail').hidden, false, 'seat click opens the person sheet');
assert.match(get('agent-detail').textContent, /Inspect/);

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
assert.equal(get('agents-canvas-empty-teach').hidden, false, 'empty canvas teaches strip → node → door');
assert.equal(get('agents-canvas').hidden, true);
assert.equal(get('agents-canvas-tour').hidden, true, 'seen tour does not restart on the empty path');

runtime.applySnapshot(fixture);
runtime.setAgentsView('floor');
assert.equal(get('agents-floor-lists').hidden, false);
assert.equal(get('agents-canvas-wrap').hidden, true);
assert.equal(get('agents-face-floor').attributes['aria-pressed'], 'true');
assert.equal(get('agents-canvas-tour').hidden, true);

runtime.setAgentsView('canvas');
assert.equal(get('agents-canvas-wrap').hidden, false);
assert.equal(get('agents-canvas-tour').hidden, true, 'seen tour stays dismissed on Canvas');
fire('agents-canvas-tour-start');
assert.equal(get('agents-canvas-tour').hidden, false);
assert.equal(get('agents-canvas-tour').dataset.step, 'strip');
runtime.setAgentsView('floor');
assert.equal(get('agents-floor-lists').hidden, false);
assert.equal(get('agents-canvas-tour').hidden, true, 'switching to Floor hides an in-progress tour');

const idleOnly = {
  ...fixture,
  agents: [agent('idle-seat', 'idle')],
  agents_floor: {working: 0, idle: 1, error: 0, stale: 0, quiet: 0, sparks: {}},
  agents_canvas: {
    empty: false, empty_reason: '', width: 480, height: 120,
    nodes: [
      {id: 'idle-seat', kind: 'seat', label: 'idle-seat', badge: 'IDLE', bucket: 'idle', group: 'seat', x: 24, y: 24, w: 188, h: 58, door: 'person', work_href: '/work?assignment=worker:idle-seat'},
    ],
    edges: [],
  },
};
runtime.applySnapshot(idleOnly);
get('agents-pulse').replaceChildren();
runtime.setAgentsView('canvas');
runtime.agents();
const idlePulse = get('agents-pulse').querySelectorAll('.bp-metric').map(n => n.textContent.replace(/\s+/g, ''));
assert.deepEqual(idlePulse, ['0Working', '1Idle', '0Error'], 'soft-poll canvas reuses Floor Working/Idle/Error');
const idleCards = get('agents-canvas').querySelectorAll('.bp-agents-canvas-node');
assert.equal(idleCards.find(n => n.dataset.id === 'idle-seat').dataset.bucket, 'idle');
assert.ok(!idleCards.some(n => n.dataset.bucket === 'working'), 'canvas does not keep a stale Working seat after refresh');
assert.ok(!idleCards.some(n => n.querySelectorAll('.bp-agents-canvas-claim').length), 'no invented claim after Floor goes idle');
assert.ok(!idleCards.some(n => n.querySelectorAll('.bp-agents-canvas-fire').length), 'no invented next-fire when Calendar door is absent');

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
  empty_teaches_floor: true,
  tour_steps: ['strip', 'node', 'door'],
  tour_seen: 'seen',
  floor_back: true,
  claim_pulse: true,
  fire_on_job: true,
  last_run_error_tone: true,
  floor_hero: true,
  coverage_door_closed: true,
  soft_poll_pulse: idlePulse,
  working_shape: 'rounded',
  job_shape: 'diamond',
  has_legend: true,
  has_project_label: true,
  has_optional_spark: true,
  canvas_href: context.historyHref,
  person_sheet: true,
  tour_factory: tourFactory,
}));
