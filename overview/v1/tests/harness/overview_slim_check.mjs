// pc-1509 / pc-1511: Overview Decide is ≤5 one-line rows with an honest
// remainder door; Read/Watch/Due are chips to Work; Mute/More/Recent live
// on Work with the full For You faces.
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
  'work-flow', 'work-list', 'mute-status',
  'projects-list', 'projects-summary', 'projects-compare', 'projects-compare-summary', 'projects-filter',
  'seat-list', 'job-list', 'agent-detail', 'supervisor-panel', 'coverage-list', 'agents-heartbeat',
  'agents-next-fire', 'agents-pulse', 'agents-floor-remainder', 'agents-floor-empty', 'agents-floor-spark',
  'agents-quiet', 'agents-quiet-summary', 'agents-quiet-list', 'work-calendar-doors',
  'timeline-project', 'timeline-source', 'timeline-actor', 'timeline-list', 'timeline-sources',
  'timeline-more', 'timeline-new-events', 'timeline-activity', 'timeline-activity-chart',
  'timeline-activity-summary', 'timeline-period', 'calendar-project', 'calendar-today', 'calendar-next',
  'calendar-past', 'calendar-prev-week', 'calendar-next-week', 'calendar-today-btn',
  'calendar-today-heading', 'calendar-next-heading', 'calendar-past-summary', 'calendar-past-wrap',
  'calendar-range', 'schedule-list', 'event-list', 'connection-exceptions', 'connection-list',
  'capability-list', 'engine-list', 'excluded-store-list', 'remote-repositories', 'remote-status',
  'github-connection-status', 'refresh-description', 'build', 'workspace-path', 'settings-build',
  'settings-workspace',
];
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, new Element());
  return nodes.get(id);
};

function order(id, face, extra = {}) {
  return {
    id, project: 'blueprint', project_name: 'BluePrint', title: `Order ${id}`,
    status: extra.status || 'backlog', status_word: extra.status_word || 'Open',
    attention: Boolean(face), attention_face: face || '',
    owner: extra.owner || 'You', assigned_you: extra.assigned_you !== undefined ? extra.assigned_you : true,
    workers: extra.workers || ['you'], needs_routing: false, kind: extra.kind || 'work',
    updated_at: extra.updated_at || '2026-09-16T12:00:00Z',
    face_reason: extra.face_reason || (face ? `${face} reason` : ''),
    gate_type: face === 'decide' ? 'human' : (extra.gate_type || ''),
    gate_note: face === 'decide' ? `Approve ${id}` : '',
    last_note: extra.last_note || '',
    blocked_on: 'clear', blockers: [], parent: '', persona: '', ready_for: '',
    live_with: null, parked_by: null, since: null,
    ...extra,
  };
}

const fixture = {
  workspace: {name: 'Desk', path: '/tmp/desk'},
  build: '0.1.74',
  projects: [{id: 'blueprint', name: 'BluePrint', open: 12, attention: 10, state: 'available'}],
  agents: [
    {id: 'bp-cursor-implementer', name: 'Cursor', group: 'seat', state: 'working', badge: 'WORKING', project: 'blueprint', held: {id: 'pc-d1', project: 'blueprint'}, shift: {started_at: '2026-09-16T10:00:00Z', age_seconds: 120, budget_secs: 2100}},
    {id: 'loop-health', name: 'loop-health', group: 'job', state: 'idle', badge: 'IDLE', schedule: '5,35 * * * *', next_fire: new Date(Date.now() + 12 * 60 * 1000).toISOString()},
  ],
  work_dates: [
    {kind: 'deadline', product: 'blueprint', task_id: 'pc-due1', summary: 'Order pc-due1', dtstart: '2026-09-16', all_day: true, source: 'deadline:2026-09-16'},
  ],
  events: [],
  orders: [
    ...Array.from({length: 6}, (_, i) => order(`pc-d${i + 1}`, 'decide', {updated_at: `2026-09-16T1${i}:00:00Z`})),
    order('pc-r1', 'read'),
    order('pc-r2', 'read'),
    order('pc-w1', 'watch'),
    order('pc-due1', 'due', {kind: 'reminder', workers: ['you'], assigned_you: true}),
    order('pc-open', '', {attention: false, assigned_you: false, workers: ['agent'], ready_for: 'agent', owner: 'agent', updated_at: '2026-09-17T01:00:00Z', title: 'Newest open'}),
    order('pc-done', '', {status: 'done', status_word: 'Done', attention: false, updated_at: '2026-09-17T08:00:00Z'}),
  ],
  sources: [
    {name: 'WorkLane store', state: 'fresh'},
    {name: 'WorkForce heartbeat', state: 'fresh'},
  ],
  coverage: [],
  engines: {},
  excluded_stores: [],
  truncated: false,
  observed_at: new Date().toISOString(),
  throughput: {
    closes: 3,
    hours: [0,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1],
    href: '/timeline?period=1',
    state: 'healthy',
  },
};

const context = {
  URL, URLSearchParams, console, JSON,
  Option: class { constructor(text, value) { this.text = text; this.value = value; } },
  location: new URL('/', 'https://desk.example'),
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
  .replace("const {reconcileList} = await import('/js/dom-reconcile.mjs');", 'const {reconcileList} = {reconcileList: reconcileListFn};');
const bootMarker = 'connectChanges(()=>{if(!document.hidden){refresh();';
const bootAt = raw.indexOf(bootMarker);
if (bootAt === -1) throw new Error('operations.js boot marker missing');
raw = raw.slice(0, bootAt) + `snapshot = ${JSON.stringify(fixture)}; lastSuccess = Date.now();`;
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {overview, work, renderWorkInbox, agents, applySnapshot(next){ snapshot = next; }, calendarDueItems, nextScheduleFire, nextFireLine, buildCalendarDoors, throughputSpark, emptyThroughput, buildWorkFlow, emptyWorkFlow, paintWorkFlow}; })();`);
const runtime = await boot(...Object.values(context));

function kpiForYouCount() {
  const tile = get('metrics').children[0];
  const strong = (tile.children || []).find(child => child.tagName === 'STRONG');
  return strong ? Number(strong.textContent) : NaN;
}
function decideMoreLink() {
  return get('overview-decide-more').querySelector('a');
}

runtime.overview();
const decideRows = get('for-you-decide').querySelectorAll('.bp-overview-decide');
const chips = get('overview-face-chips').querySelectorAll('.bp-face-chip');
const chipText = chips.map(c => c.textContent);
const chipHrefs = chips.map(c => c.href);
const overviewMute = get('for-you-decide').querySelector('.bp-face-mute');
const overviewMore = get('for-you-decide').querySelector('.bp-order-detail');
const sixMore = decideMoreLink();

assert.equal(decideRows.length, 5, 'Overview Decide must cap at five one-line rows');
assert.equal(overviewMute, null, 'Overview Decide must not paint Mute');
assert.equal(overviewMore, null, 'Overview Decide must not paint More');
assert.match(decideRows[0].textContent, /BluePrint/, 'Decide row shows project on the one line');
assert.match(decideRows[0].textContent, /Needs you/, 'Decide row keeps the face badge');
assert.equal(sixMore && sixMore.textContent, '+1 more on Work', '6 Decide must expose the remainder door');
assert.equal(sixMore && sixMore.href, '/work?attention=decide');
assert.equal(get('overview-decide-more').hidden, false);
const sixKpi = kpiForYouCount();
assert.equal(sixKpi, 10, 'For You KPI is the true pile, not the five-row cap');
assert.deepEqual(chipText, ['Read · 2', 'Watch · 1', 'Due · 1']);
assert.equal(chipHrefs[0], '/work?attention=read');
assert.equal(chipHrefs[1], '/work?attention=watch');
assert.equal(chipHrefs[2], '/work?attention=due', 'Calendar Due with a work-order clock routes to Work attention');
assert.equal(get('work-recent').children.length, 0, 'overview() must not paint Recent on Work');
assert.equal(get('mute-status').textContent, '', 'overview() must not write mute status');
assert.match(get('overview-unrouted').textContent, /Unrouted/);
assert.match(get('overview-source-line').textContent, /2 sources/);
assert.ok(get('metrics').children.length === 5, 'five KPI tiles');
const sparkHost = get('overview-throughput');
assert.match(sparkHost.textContent, /3 closes · last 24h/, 'healthy spark is a count door');
assert.equal(sparkHost.querySelector('a') && sparkHost.querySelector('a').href, '/timeline?period=1');
assert.ok(sparkHost.querySelector('.bp-overview-spark'), 'unicode spark sits beside the count');
assert.equal(runtime.throughputSpark([0,0,0,0]), '', 'all-zero hours paint no spark glyphs');
assert.ok(runtime.throughputSpark([0,2,0,1]).length > 0, 'nonzero hours paint a spark');

runtime.work();
const workAct = get('work-act-now').querySelectorAll('.bp-order');
const workTodos = get('work-my-todos').querySelectorAll('.bp-order');
const workSeat = get('work-seat-backlog').querySelectorAll('.bp-order');
const workMutes = get('work-act-now').querySelectorAll('.bp-face-mute');
const workMore = get('work-act-now').querySelectorAll('.bp-order-detail');
const workBadges = workAct[0] ? workAct[0].querySelectorAll('.bp-badge') : [];
const workBadgeText = workBadges.map(node => node.textContent);
const workNeedsYou = [...workAct, ...workTodos, ...workSeat].some(row => row.textContent.includes('Needs you'));

assert.equal(workAct.length, 8, 'Act now is Decide+Read at the comfortable cap');
assert.equal(get('work-act-now-count').textContent, '8');
assert.equal(workTodos.length, 1, 'Due reminder lands in My todos');
assert.ok(workSeat.length >= 1, 'Seat backlog shows agent-drainable open work');
assert.equal(workMutes.length, 8, 'Mute lives on Work Act now rows');
assert.ok(workMore.length >= 1, 'More disclosure lives on Work rows');
assert.equal(workBadges.length, 2, 'every Work row has dual Face + Status badges');
assert.ok(workBadgeText.includes('Decide'), 'Face badge is Decide, not Needs you');
assert.ok(workBadgeText.includes('Open'), 'Status badge stays on its own pill');
assert.equal(workNeedsYou, false, 'Work rows never paint a primary Needs you chip');
assert.match(get('mute-status').textContent, /Mute only hides this inbox item/);
assert.equal(get('work-recent') && get('work-recent').children.length, 0);
assert.match(get('work-flow').textContent, /Ready/, 'Work paints a flow strip above the bands');
assert.ok(get('work-flow').querySelector('.bp-work-flow-bar'), 'flow bar is present');

runtime.applySnapshot({
  ...fixture,
  orders: [
    order('pc-ready', '', {workers: ['pepper'], ready_for: 'pepper', assigned_you: false, owner: 'pepper'}),
    order('pc-live', '', {status: 'in_progress', workers: ['pepper'], assigned_you: false, owner: 'pepper', live_with: 'pepper'}),
    order('pc-stall', '', {status: 'in_progress', attention_face: 'watch', workers: ['lili'], assigned_you: false, owner: 'lili'}),
    order('pc-open2', '', {workers: ['lili'], assigned_you: false, owner: 'lili'}),
  ],
  agents: [
    {id: 'pepper', name: 'pepper', group: 'seat', state: 'working'},
    {id: 'lili', name: 'lili', group: 'seat', state: 'idle'},
  ],
});
get('work-flow').replaceChildren();
runtime.work();
const flowText = get('work-flow').textContent;
const seatRows = get('work-flow').querySelectorAll('.bp-work-seat-load-row');
const seatNames = seatRows.map(row => {
  const name = row.querySelector('.bp-work-seat-load-name');
  return name ? name.textContent : '';
});
assert.match(flowText, /Open 1 → Ready 1 → Live 2 → Done 0/);
assert.deepEqual(seatNames.sort(), ['lili', 'pepper']);
assert.equal(get('work-act-now').querySelectorAll('.bp-order').length, 0, 'flow fixture does not invent Act now');
assert.equal(get('work-band-act-now').hidden, false, 'empty Act now band stays visible');
assert.ok(get('work-flow').querySelector('.bp-work-seat-load'), 'per-seat ready/claimed/stalled rows paint');
runtime.applySnapshot({...fixture, orders: [], work_flow: runtime.emptyWorkFlow()});
get('work-flow').replaceChildren();
runtime.work();
assert.equal(get('work-flow').textContent, 'No seat drain right now');
runtime.applySnapshot({...fixture, work_flow: runtime.emptyWorkFlow('unavailable')});
get('work-flow').replaceChildren();
runtime.work();
assert.equal(get('work-flow').textContent, 'Seat load unavailable');
runtime.applySnapshot(fixture);
runtime.work();

get('for-you-decide').replaceChildren();
runtime.overview();
assert.equal(get('for-you-decide').querySelectorAll('.bp-overview-decide').length, 5, 'repaint keeps the five-row cap');
assert.equal(decideMoreLink() && decideMoreLink().textContent, '+1 more on Work', 'repaint keeps the remainder door');

const overflowOrders = [
  ...Array.from({length: 15}, (_, i) => order(`pc-d${i + 1}`, 'decide', {updated_at: `2026-09-16T${String(10 + i).padStart(2, '0')}:00:00Z`})),
  order('pc-r1', 'read'),
  order('pc-r2', 'read'),
  order('pc-w1', 'watch'),
  order('pc-due1', 'due'),
];
runtime.applySnapshot({...fixture, orders: overflowOrders});
get('metrics').replaceChildren();
get('for-you-decide').replaceChildren();
get('overview-decide-more').replaceChildren();
runtime.overview();
const overflowRows = get('for-you-decide').querySelectorAll('.bp-overview-decide');
const overflowMore = decideMoreLink();
const overflowChips = get('overview-face-chips').querySelectorAll('.bp-face-chip').map(c => c.textContent);
assert.equal(overflowRows.length, 5, '15 Decide still shows five Act-now rows');
assert.equal(overflowMore && overflowMore.textContent, '+10 more on Work');
assert.equal(overflowMore && overflowMore.href, '/work?attention=decide');
assert.equal(get('overview-decide-more').hidden, false);
const overflowKpi = kpiForYouCount();
assert.equal(overflowKpi, 19, 'For You KPI stays the true total when Decide overflows');
assert.deepEqual(overflowChips, ['Read · 2', 'Watch · 1', 'Due · 1']);

const emptyDecideOrders = [
  order('pc-r1', 'read'),
  order('pc-r2', 'read'),
  order('pc-w1', 'watch'),
  order('pc-due1', 'due'),
];
runtime.applySnapshot({...fixture, orders: emptyDecideOrders});
get('metrics').replaceChildren();
get('for-you-decide').replaceChildren();
get('overview-decide-more').replaceChildren();
get('overview-decide-more').hidden = false;
runtime.overview();
const emptyNode = get('for-you-decide').querySelector('.bp-empty');
const emptyMore = decideMoreLink();
const emptyChips = get('overview-face-chips').querySelectorAll('.bp-face-chip').map(c => c.textContent);
assert.equal(get('for-you-decide').querySelectorAll('.bp-overview-decide').length, 0);
assert.equal(emptyNode && emptyNode.textContent, 'Nothing for You');
assert.equal(emptyMore, null, 'no remainder door when Decide is empty');
assert.equal(get('overview-decide-more').hidden, true);
assert.equal(get('overview-decide-more').textContent, '');
const emptyKpi = kpiForYouCount();
assert.equal(emptyKpi, 4, 'For You KPI still counts Read/Watch/Due when Decide is 0');
assert.deepEqual(emptyChips, ['Read · 2', 'Watch · 1', 'Due · 1']);

runtime.applySnapshot({...fixture, work_dates: [], events: [{title: 'Standup', at: '2026-09-17T10:00:00Z', state: 'due', source: 'routine'}], calendar_doors: undefined});
get('overview-face-chips').replaceChildren();
runtime.overview();
const eventChips = get('overview-face-chips').querySelectorAll('.bp-face-chip');
assert.equal(eventChips[2] && eventChips[2].textContent, 'Due · 1');
assert.equal(eventChips[2] && eventChips[2].href, '/calendar', 'event-only Due routes to Calendar');

runtime.applySnapshot({...fixture, work_dates: [], events: [], calendar_doors: undefined});
get('overview-face-chips').replaceChildren();
runtime.overview();
const zeroDue = get('overview-face-chips').querySelectorAll('.bp-face-chip').map(c => c.textContent);
assert.deepEqual(zeroDue, ['Read · 2', 'Watch · 1', 'Due · 0']);

runtime.applySnapshot({...fixture, calendar_doors: undefined});
runtime.agents();
const nextFireText = get('agents-next-fire').textContent;
assert.match(nextFireText, /Next fire · loop-health in \d+m/);
assert.equal(get('agents-next-fire').querySelector('a') && get('agents-next-fire').querySelector('a').href, '/calendar');

const helperNow = new Date('2026-09-17T15:00:00Z');
const helperDoors = runtime.buildCalendarDoors(
  [{kind: 'deadline', product: 'blueprint', task_id: 'pc-due1', dtstart: '2026-09-16', all_day: true, summary: 'Order pc-due1'}],
  [],
  [{name: 'loop-health', id: 'loop-health', next_fire: '2026-09-17T15:12:00Z'}],
  helperNow,
);
assert.equal(helperDoors.due_count, 1);
assert.equal(helperDoors.due_href, '/work?attention=due');
assert.equal(helperDoors.next_fire_line, 'Next fire · loop-health in 12m');
assert.equal(runtime.nextFireLine(null), 'Next fire · none reported');
assert.equal(runtime.calendarDueItems([], [{title: 'Standup', at: '2026-09-17T10:00:00Z', state: 'due'}], helperNow).length, 1);

runtime.applySnapshot({...fixture, throughput: runtime.emptyThroughput()});
get('overview-throughput').replaceChildren();
runtime.overview();
assert.equal(get('overview-throughput').textContent, 'No closes in the last 24h');
assert.equal(get('overview-throughput').querySelector('a'), null, 'empty spark is not a fake door');
assert.equal(get('for-you-decide').querySelectorAll('.bp-overview-decide').length, 5, 'empty spark does not touch Option D');
runtime.applySnapshot({...fixture, throughput: {closes: 0, hours: Array(24).fill(0), href: '/timeline?period=1', state: 'unavailable'}});
get('overview-throughput').replaceChildren();
runtime.overview();
assert.equal(get('overview-throughput').textContent, 'Throughput unavailable');
assert.equal(get('metrics').children.length, 5, 'unavailable spark is not a sixth KPI');

process.stdout.write(JSON.stringify({
  decide_rows: decideRows.length,
  decide_more: sixMore && sixMore.textContent,
  decide_more_href: sixMore && sixMore.href,
  for_you_kpi: sixKpi,
  chips: chipText,
  chip_hrefs: chipHrefs,
  overview_has_mute: Boolean(overviewMute),
  overview_has_more: Boolean(overviewMore),
  work_act_now: workAct.length,
  work_my_todos: workTodos.length,
  work_seat: workSeat.length,
  work_mutes: workMutes.length,
  work_more: workMore.length,
  work_dual_badges: workBadges.length === 2,
  work_needs_you: workNeedsYou,
  unrouted: get('overview-unrouted').textContent,
  source_line: get('overview-source-line').textContent,
  kpis: get('metrics').children.length,
  overflow_rows: overflowRows.length,
  overflow_more: overflowMore && overflowMore.textContent,
  overflow_kpi: overflowKpi,
  overflow_chips: overflowChips,
  empty_decide_text: emptyNode && emptyNode.textContent,
  empty_decide_more: emptyMore && emptyMore.textContent,
  empty_kpi: emptyKpi,
  empty_chips: emptyChips,
  event_due_chip: eventChips[2] && eventChips[2].textContent,
  event_due_href: eventChips[2] && eventChips[2].href,
  zero_due_chips: zeroDue,
  next_fire: nextFireText,
  helper_due_count: helperDoors.due_count,
  helper_next_fire: helperDoors.next_fire_line,
  throughput: '3 closes · last 24h',
  throughput_href: '/timeline?period=1',
  throughput_empty: 'No closes in the last 24h',
  throughput_unavailable: 'Throughput unavailable',
  work_flow: flowText,
  work_flow_seats: seatNames.sort(),
  work_flow_empty: 'No seat drain right now',
  work_flow_unavailable: 'Seat load unavailable',
}));
