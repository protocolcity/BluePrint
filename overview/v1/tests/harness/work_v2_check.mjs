// Issue #158: Work representation v2 — seat-load chips only, hard caps,
// +N doors, never a 78-row flat backlog.
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
    this.style = {};
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
  click() {
    for (const fn of this.listeners.click || []) fn({preventDefault() {}, stopPropagation() {}});
  }
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
      if (sel === 'button' && node.tagName === 'BUTTON') return node;
      if (sel === 'summary' && node.tagName === 'SUMMARY') return node;
      if (sel === 'details' && node.tagName === 'DETAILS') return node;
      if (sel.startsWith('.') && node.hasClass(sel.slice(1))) return node;
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
      if (sel === 'button' && node.tagName === 'BUTTON') out.push(node);
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
  'timeline-view', 'connections-view', 'delivery-view', 'settings-view', 'overview-executions',
  'overview-exec-cue', 'metrics', 'overview-throughput', 'overview-unrouted', 'overview-source-line',
  'for-you-decide', 'overview-decide-more', 'overview-face-chips',
  'work-band-act-now', 'work-act-now', 'work-act-now-count', 'work-act-now-more',
  'work-band-my-todos', 'work-my-todos', 'work-my-todos-count', 'work-my-todos-more',
  'work-band-seat-backlog', 'work-seat-backlog', 'work-seat-backlog-count', 'work-seat-backlog-more',
  'work-flow', 'work-calendar-doors', 'mute-status',
  'projects-list', 'projects-summary', 'projects-compare', 'projects-compare-summary', 'projects-filter',
  'seat-list', 'job-list', 'agent-detail', 'supervisor-panel', 'coverage-list', 'agents-heartbeat',
  'agents-next-fire', 'agents-pulse', 'agents-floor-remainder', 'agents-floor-empty', 'agents-floor-spark',
  'agents-quiet', 'agents-quiet-summary', 'agents-quiet-list',
  'timeline-project', 'timeline-source', 'timeline-actor', 'timeline-list', 'timeline-sources',
  'timeline-more', 'timeline-new-events', 'timeline-activity', 'timeline-activity-chart',
  'timeline-activity-summary', 'timeline-period', 'calendar-project', 'calendar-today', 'calendar-next',
  'calendar-past', 'calendar-prev-week', 'calendar-next-week', 'calendar-today-btn',
  'calendar-today-heading', 'calendar-next-heading', 'calendar-past-summary', 'calendar-past-wrap',
  'calendar-range', 'calendar-load', 'calendar-load-chart', 'calendar-load-summary', 'calendar-doors',
  'schedule-list', 'event-list', 'connection-exceptions', 'connection-list',
  'capability-list', 'engine-list', 'excluded-store-list', 'remote-repositories', 'remote-status',
  'github-connection-status', 'refresh-description', 'build', 'workspace-path', 'settings-build',
  'settings-workspace',
];
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, new Element());
  return nodes.get(id);
};

function order(id, extras = {}) {
  return {
    id, project: 'blueprint', project_name: 'BluePrint', title: extras.title || `Order ${id}`,
    status: extras.status || 'backlog', status_word: extras.status_word || 'Open',
    attention: Boolean(extras.attention_face), attention_face: extras.attention_face || '',
    owner: extras.owner || extras.workers?.[0] || 'You',
    assigned_you: extras.assigned_you !== undefined ? extras.assigned_you : (extras.workers || []).includes('you'),
    workers: extras.workers || [],
    needs_routing: false, kind: extras.kind || 'work',
    updated_at: extras.updated_at || '2026-09-16T12:00:00Z',
    gate_type: extras.gate_type || '',
    gate_note: extras.gate_note || '',
    last_note: '', blocked_on: 'clear', blockers: [], parent: '', persona: '',
    ready_for: extras.ready_for || '',
    live_with: extras.live_with || null, parked_by: extras.parked_by || null, since: null,
    ...extras,
  };
}

const actNow = [
  ...Array.from({length: 6}, (_, i) => order(`pc-d${i + 1}`, {
    attention_face: 'decide', gate_type: 'human', workers: ['you'], assigned_you: true,
    title: `Decide ${i + 1}`, updated_at: `2026-09-16T1${i}:00:00Z`,
  })),
  ...Array.from({length: 3}, (_, i) => order(`pc-r${i + 1}`, {
    attention_face: 'read', kind: 'report', workers: ['you'], assigned_you: true,
    title: `Read ${i + 1}`,
  })),
];
const myTodos = Array.from({length: 31}, (_, i) => order(`pc-t${i + 1}`, {
  kind: i % 3 === 0 ? 'note' : 'todo', workers: ['you'], assigned_you: true,
  title: `Todo ${i + 1}`, owner: 'You',
}));
const seatRows = [];
for (const [seat, count] of [['pepper', 40], ['lili', 20], ['oak', 18]]) {
  for (let i = 0; i < count; i += 1) {
    const extras = {
      workers: [seat], assigned_you: false, owner: seat, title: `${seat} ${i + 1}`,
      updated_at: `2026-09-15T${String((i % 20) + 1).padStart(2, '0')}:00:00Z`,
    };
    if (i % 7 === 0) {
      extras.status = 'in_progress';
      extras.attention_face = 'watch';
    } else if (i % 4 === 0) {
      extras.ready_for = seat;
    }
    seatRows.push(order(`pc-${seat}-${i + 1}`, extras));
  }
}

const fixture = {
  workspace: {name: 'Desk', path: '/tmp/desk-v2'},
  build: '0.1.47+consolidation.87',
  projects: [{id: 'blueprint', name: 'BluePrint', open: 118, attention: 9, state: 'available'}],
  agents: [
    {id: 'pepper', name: 'pepper', group: 'seat', state: 'working'},
    {id: 'lili', name: 'lili', group: 'seat', state: 'idle'},
    {id: 'oak', name: 'oak', group: 'seat', state: 'idle'},
  ],
  orders: [...actNow, ...myTodos, ...seatRows],
  sources: [{name: 'WorkLane store', state: 'fresh'}],
  coverage: [], engines: {}, excluded_stores: [], truncated: false,
  observed_at: new Date().toISOString(),
  work_dates: [], events: [],
};

const context = {
  URL, URLSearchParams, console, JSON,
  Option: class { constructor(text, value) { this.text = text; this.value = value; } },
  location: new URL('/work', 'https://desk.example'),
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
  'attention-filter', 'timeline-project', 'timeline-source', 'refresh-preference', 'motion-preference',
  'calendar-project']) wireSelect(id);
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
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {work, applySnapshot(next){ snapshot = next; }, paintWorkFlow, filterOptions, updateWorkFilters}; })();`);
const runtime = await boot(...Object.values(context));

runtime.filterOptions();
runtime.work();

assert.equal(actNow.length, 9);
assert.equal(myTodos.length, 31);
assert.equal(seatRows.length, 78);

const actVisible = get('work-act-now').querySelectorAll('.bp-order');
const todoVisible = get('work-my-todos').querySelectorAll('.bp-order');
const seatVisible = get('work-seat-backlog').querySelectorAll('.bp-order');
const seatGroups = get('work-seat-backlog').querySelectorAll('.bp-work-seat-group');
const chips = get('work-flow').querySelectorAll('.bp-work-seat-chip');
const chipNames = chips.map(chip => {
  const name = chip.querySelector('.bp-work-seat-chip-name');
  return name ? name.textContent : chip.textContent;
});
const heroText = get('work-flow').textContent;
const actMore = get('work-act-now-more').textContent;
const todoMore = get('work-my-todos-more').textContent;
const seatMore = get('work-seat-backlog-more').textContent;
const firstRow = actVisible[0];

assert.equal(get('work-act-now-count').textContent, '9', 'Act now header is the true total');
assert.equal(actVisible.length, 8, 'Act now paints the 8-row cap');
assert.equal(actMore, '+1 more in Act now');
assert.equal(get('work-act-now-more').hidden, false);
assert.equal(get('work-my-todos-count').textContent, '31', 'My todos header is the true total');
assert.equal(todoVisible.length, 8, 'My todos paints the 8-row cap');
assert.equal(todoMore, '+23 more · My todos');
assert.equal(get('work-seat-backlog-count').textContent, '78', 'Seat backlog header is the true total');
assert.ok(seatVisible.length <= 9, 'Seat backlog never paints 78 flat');
assert.equal(seatVisible.length, 9, 'default paint is 3 seats × 3');
assert.ok(seatGroups.length <= 3);
assert.equal(seatMore, '+69 more · filter by seat');
assert.equal(get('work-flow').querySelector('.bp-work-flow-bar'), null, 'no flow-bar second hero');
assert.match(heroText, /Open \d+ → Ready \d+ → Live \d+ → Done \d+/);
assert.ok(get('work-flow').querySelector('.bp-work-flow-strip'), 'flow strip is the thin companion');
const flowStages = get('work-flow').querySelectorAll('.bp-work-flow-stage');
assert.deepEqual(flowStages.map(stage => stage.dataset.stage), ['Open', 'Ready', 'Live', 'Done']);
assert.ok(get('work-flow').querySelector('.bp-work-flow-ticks'), 'cheap stage ticks paint');
assert.ok(get('work-flow').querySelector('.bp-work-flow-count'), 'stage counts stay visible');
assert.ok(chips.length >= 2, 'seat-load chips stay the drain hero');
assert.ok(chipNames.includes('pepper'));
assert.ok(chipNames.includes('others') || chipNames.includes('lili') || chipNames.includes('oak'));
assert.match(heroText, /ready/);
assert.match(heroText, /stalled/);
assert.equal(firstRow.querySelectorAll('.bp-badge').length, 2, 'dual face+status badges');
assert.equal(firstRow.querySelector('.bp-order-detail'), null);
assert.equal(firstRow.querySelector('.bp-face-mute'), null);
assert.ok(firstRow.querySelector('.bp-order-link').textContent.includes('Decide'));
assert.ok(firstRow.querySelector('.bp-work-row-age'), 'dim age is present');

get('work-act-now-more').querySelector('button').click();
assert.equal(get('attention-filter').value, 'act_now', '+N opens the Act now facet');
assert.equal(get('work-act-now').querySelectorAll('.bp-order').length, 9, 'facet shows the full Act now list');
assert.equal(get('work-band-my-todos').hidden, true);
assert.equal(get('work-band-seat-backlog').hidden, true);
assert.match(get('work-flow').textContent, /Open 9 → Ready 0 → Live 0 → Done 0/, 'flow follows the Act now matching filter');
assert.ok(get('work-flow').querySelector('.bp-work-seat-chip'), 'seat-load chips stay while the facet is open');

get('attention-filter').value = '';
get('assignment-filter').value = '';
runtime.updateWorkFilters();
const pepper = chips.find(chip => chip.dataset.seat === 'pepper') || get('work-flow').querySelectorAll('.bp-work-seat-chip').find(chip => chip.dataset.seat === 'pepper');
assert.ok(pepper, 'pepper chip remains clickable');
pepper.click();
assert.equal(get('attention-filter').value, 'seat');
assert.equal(get('assignment-filter').value, 'worker:pepper');
const scoped = get('work-seat-backlog').querySelectorAll('.bp-order');
assert.ok(scoped.length > 0, 'seat chip scopes Seat backlog');
assert.ok(scoped.length < 78, 'scoped list is not the flat 78');
assert.equal(get('work-band-act-now').hidden, true);
assert.match(get('work-flow').textContent, /Open 26 → Ready 8 → Live 6 → Done 0/, 'flow follows the pepper matching filter');
assert.ok(get('work-flow').querySelectorAll('.bp-work-seat-chip').length >= 2, 'seat-load chips stay after a seat door');

get('attention-filter').value = '';
get('assignment-filter').value = '';
get('status-filter').value = 'Ready';
runtime.updateWorkFilters();
assert.match(get('work-flow').textContent, /Open 0 → Ready 16 → Live 0 → Done 0/, 'Ready facet recounts flow from matching work');
assert.ok(get('work-flow').querySelector('.bp-work-seat-chip'), 'seat-load chips are not removed by a status facet');
assert.equal(get('work-act-now').querySelectorAll('.bp-order').length, 0);
assert.ok(get('work-seat-backlog').querySelectorAll('.bp-order').length <= 9, 'Ready facet does not break the 3×3 backlog cap');

const result = {
  act_now_total: '9',
  act_now_visible_default: 8,
  act_now_more: '+1 more in Act now',
  my_todos_total: '31',
  my_todos_visible_default: 8,
  my_todos_more: '+23 more · My todos',
  seat_total: '78',
  seat_visible_default: 9,
  seat_more: '+69 more · filter by seat',
  hero_chips: chipNames,
  hero_flow: heroText,
  hero_has_flow_bar: false,
  hero_has_flow_strip: /Open \d+ → Ready/.test(heroText),
  mute_on_rows: 0,
  more_on_rows: 0,
  door_sets_attention: 'act_now',
  chip_sets_seat: 'worker:pepper',
};

get('status-filter').value = '';
get('attention-filter').value = '';
get('assignment-filter').value = '';
runtime.applySnapshot({
  ...fixture,
  orders: [],
  work_flow: {state: 'empty', flow: {Open: 0, Ready: 0, Live: 0, Done: 0}, seats: [], chips: [], total: 0},
});
runtime.updateWorkFilters();
assert.equal(get('work-flow').textContent, 'No seat drain right now');
assert.equal(get('work-flow').querySelector('.bp-work-flow-strip'), null, 'honest empty does not paint fake zeros');

process.stdout.write(JSON.stringify(result));
