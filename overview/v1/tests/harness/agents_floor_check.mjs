// pc-1513: Agents live floor — pulse counts, claim cards, quiet Off, next fire.
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
    this.hidden = false;
    this.open = false;
    this.disabled = false;
    this._text = '';
    this.type = '';
    this.href = '';
    this.value = '';
    this.selectedOptions = [{text: ''}];
    this.ownerDocument = {createElement: t => new Element(t), createTextNode: t => Object.assign(new Element('#text'), {_text: String(t), textContent: String(t)})};
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
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  hasClass(name) {
    return String(this.className || '').split(/\s+/).includes(name);
  }
  querySelector(sel) {
    const walk = node => {
      if (sel === 'a' && node.tagName === 'A') return node;
      if (sel === 'strong' && node.tagName === 'STRONG') return node;
      if (sel.startsWith('.') && node.hasClass(sel.slice(1))) return node;
      if (sel.startsWith('[data-agent-id=') && node.dataset && node.dataset.agentId === sel.slice(16, -2)) return node;
      for (const child of node.children || []) {
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
      if (sel === 'a' && node.tagName === 'A') out.push(node);
      if (sel.startsWith('.') && node.hasClass(sel.slice(1))) out.push(node);
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
  'agents-hero', 'agents-coverage-door', 'agents-coverage-summary', 'agents-legend',
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
const fixture = {
  workspace: {name: 'Desk', path: '/tmp/desk'},
  build: '0.1.51',
  projects: [],
  orders: [{id: 'pc-9', project: 'blueprint', project_name: 'BluePrint', title: 'Live claim'}],
  agents: [
    agent('working-seat', 'working', {
      held: {id: 'pc-9', project: 'blueprint'},
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
  coverage: [
    {project:'blueprint', name:'BluePrint', present:['claude'], held:[], missing:['cursor'], not_configured:[], hire_commands:{cursor:'workforce hire cursor --project blueprint'}, install_hints:{}},
  ],
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
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {agents, applySnapshot(next){ snapshot = next; }}; })();`);
const runtime = await boot(...Object.values(context));

runtime.agents();
const pulse = get('agents-pulse').querySelectorAll('.bp-metric').map(n => n.textContent.replace(/\s+/g, ''));
assert.deepEqual(pulse, ['1Working', '2Idle', '1Error'], 'strip counts Working/Idle/Error from state; jobs count, Off does not');
assert.match(get('agents-floor-remainder').textContent, /1 off or unknown/);
assert.equal(get('agents-floor-empty').hidden, true);

const liveIds = get('seat-list').querySelectorAll('.bp-agent-select').map(n => n.dataset.agentId);
assert.deepEqual(liveIds, ['working-seat', 'idle-seat', 'failed-seat']);
assert.ok(!liveIds.includes('off-seat'), 'Off seats leave the live floor');
assert.equal(get('agents-quiet').hidden, false);
assert.match(get('agents-quiet-summary').textContent, /Quiet · 1 off or unknown/);
const quietIds = get('agents-quiet-list').querySelectorAll('.bp-agent-select').map(n => n.dataset.agentId);
assert.deepEqual(quietIds, ['off-seat']);

const working = get('seat-list').querySelectorAll('.bp-agent-row-live')[0];
assert.ok(working, 'working seat is a live card');
assert.match(working.textContent, /pc-9|Live claim/);
assert.ok(working.querySelector('.bp-shift-cue'), 'open in-budget shift keeps the live cue');
assert.match(get('agents-next-fire').textContent, /Next fire · loop-health/);

const sparkOf = (host, id) => {
  const select = host.querySelectorAll('.bp-agent-select').find(node => node.dataset.agentId === id);
  if (!select) return '';
  const label = select.querySelector('.bp-agent-spark-label');
  const fail = select.querySelector('.bp-agent-spark-fail');
  return [label ? label.textContent : '', fail ? fail.textContent : ''].filter(Boolean).join(' · ');
};
const sparkToneOf = (host, id) => {
  const select = host.querySelectorAll('.bp-agent-select').find(node => node.dataset.agentId === id);
  const line = select && select.querySelector('.bp-agent-spark-line');
  return line ? line.dataset.tone : '';
};
const workingSpark = sparkOf(get('seat-list'), 'working-seat');
const idleSpark = sparkOf(get('seat-list'), 'idle-seat');
const failedSpark = sparkOf(get('seat-list'), 'failed-seat');
const quietSpark = sparkOf(get('agents-quiet-list'), 'off-seat');
assert.equal(workingSpark, '2 runs');
assert.ok(get('seat-list').querySelector('.bp-agent-spark-line'), 'working seat paints a throughput spark');
assert.equal(idleSpark, '', 'idle with no ticks stays honest empty');
assert.equal(failedSpark, '1 run · 1 fail (100%)');
assert.equal(quietSpark, '', 'off seats do not invent spark motion');
assert.equal(sparkToneOf(get('seat-list'), 'working-seat'), 'working');
assert.equal(sparkToneOf(get('seat-list'), 'failed-seat'), 'error');
assert.match(get('agents-floor-spark').textContent, /4 runs · last 24h/);
assert.match(get('agents-floor-spark').textContent, /1 fail \(25%\)/);
assert.ok(get('agents-floor-spark').querySelector('.bp-agents-floor-fail'), 'strip fail rate is its own glanceable chip');
assert.equal(get('agents-floor-spark').querySelector('.bp-agents-floor-spark-line') && get('agents-floor-spark').querySelector('.bp-agents-floor-spark-line').dataset.tone, 'working', 'mixed fail does not paint the whole strip as error');
assert.equal(get('agents-floor-spark').querySelector('a') && get('agents-floor-spark').querySelector('a').href, '/timeline?period=1');

const idleRow = get('seat-list').querySelectorAll('.bp-agent-select').find(n => n.dataset.agentId === 'idle-seat');
const idleAction = idleRow && idleRow.parent && idleRow.parent.querySelector('.bp-quiet-action');
assert.ok(idleAction, 'Dispatch now stays on the row but as a quiet secondary control');
assert.equal(idleAction.textContent, 'Dispatch now');
assert.equal(get('agents-coverage-door').open, false, 'Coverage / Hire stay collapsed behind the door');
assert.equal(get('agents-coverage-summary').textContent, 'Coverage · 1 project');
const coverageSummary = get('agents-coverage-summary').textContent;
assert.ok(!/missing staff|hire/i.test(coverageSummary), 'closed door is not a staffing bulletin');
assert.equal(get('coverage-list').querySelectorAll('code').length, 0, 'hire commands stay closed until the inner Hire door opens');

const quietOnly = {
  ...fixture,
  agents: [agent('off-seat', 'off', {badge: 'OFF'}), agent('held-seat', 'not_configured', {badge: 'NOT CONFIGURED'})],
  agents_floor: {working: 0, idle: 0, error: 0, stale: 0, quiet: 2, sparks: {}},
  coverage: [],
  calendar_doors: {due_count: 0, due_href: '/calendar', items: [], next_fire: null, next_fire_line: 'Next fire · none reported'},
};
runtime.applySnapshot(quietOnly);
get('agents-pulse').replaceChildren();
get('seat-list').replaceChildren();
get('agents-quiet-list').replaceChildren();
runtime.agents();
assert.equal(get('agents-pulse').querySelectorAll('.bp-metric').map(n => n.textContent.replace(/\s+/g, '')).join('|'), '0Working|0Idle|0Error');
assert.equal(get('agents-floor-empty').hidden, false);
assert.equal(get('agents-floor-empty').textContent, 'No seats working right now.');
assert.match(get('seat-list').textContent, /quiet roster below/);
assert.equal(get('agents-next-fire').textContent, 'Next fire · none reported');
assert.equal(get('agents-floor-spark').textContent, '');
assert.equal(get('agents-coverage-summary').textContent, 'Coverage · none reported');

process.stdout.write(JSON.stringify({
  pulse,
  live_seats: liveIds.filter(id => id === 'working-seat'),
  quiet_seats: quietIds,
  working_has_claim: /pc-9|Live claim/.test(working.textContent),
  working_has_cue: Boolean(working.querySelector('.bp-shift-cue')),
  empty_when_quiet: get('agents-floor-empty').textContent,
  next_fire: 'Next fire · loop-health in 12m',
  working_spark: workingSpark,
  failed_spark: failedSpark,
  idle_spark: idleSpark,
  quiet_spark: quietSpark,
  floor_spark: '4 runs · last 24h · 1 fail (25%)',
  floor_spark_when_quiet: get('agents-floor-spark').textContent,
  dispatch_secondary: idleAction ? idleAction.textContent : '',
  coverage_door_open: get('agents-coverage-door').open,
  coverage_door: coverageSummary,
  coverage_door_empty: get('agents-coverage-summary').textContent,
  coverage_door_bulletin: /missing staff|hire/i.test(coverageSummary),
}));
