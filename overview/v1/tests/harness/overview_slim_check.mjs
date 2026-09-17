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
  'overview-exec-cue', 'metrics', 'overview-unrouted', 'overview-source-line',
  'for-you-decide', 'overview-decide-more', 'overview-face-chips',
  'work-for-you-decide', 'work-for-you-read', 'work-for-you-watch', 'work-for-you-due',
  'work-for-you-decide-details', 'work-for-you-read-details', 'work-for-you-watch-details',
  'work-for-you-due-details', 'work-for-you-decide-summary', 'work-for-you-read-summary',
  'work-for-you-watch-summary', 'work-for-you-due-summary', 'work-recent', 'mute-status',
  'projects-list', 'projects-summary', 'projects-filter',
  'seat-list', 'job-list', 'agent-detail', 'supervisor-panel', 'coverage-list', 'agents-heartbeat',
  'agents-next-fire', 'work-calendar-doors',
  'timeline-project', 'timeline-source', 'timeline-actor', 'timeline-list', 'timeline-sources',
  'timeline-more', 'timeline-new-events', 'calendar-project', 'calendar-today', 'calendar-next',
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
    owner: 'You', assigned_you: true, workers: ['you'], needs_routing: false,
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
    order('pc-due1', 'due'),
    order('pc-open', '', {attention: false, updated_at: '2026-09-17T01:00:00Z', title: 'Newest open'}),
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
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {overview, work, renderWorkInbox, agents, applySnapshot(next){ snapshot = next; }, calendarDueItems, nextScheduleFire, nextFireLine, buildCalendarDoors}; })();`);
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

runtime.work();
const workDecide = get('work-for-you-decide').querySelectorAll('.bp-order');
const workRead = get('work-for-you-read').querySelectorAll('.bp-order');
const workWatch = get('work-for-you-watch').querySelectorAll('.bp-order');
const workDue = get('work-for-you-due').querySelectorAll('.bp-order');
const workMutes = get('work-for-you-decide').querySelectorAll('.bp-face-mute');
const workMore = get('work-for-you-decide').querySelectorAll('.bp-order-detail');
const recent = get('work-recent').querySelectorAll('.bp-order');
const recentIds = recent.map(row => row.textContent);

assert.equal(workDecide.length, 6, 'Work must show the full Decide face');
assert.equal(workRead.length, 2);
assert.equal(workWatch.length, 1);
assert.equal(workDue.length, 1);
assert.equal(workMutes.length, 6, 'Mute lives on Work For You rows');
assert.ok(workMore.length >= 1, 'More disclosure lives on Work face rows');
assert.ok(recent.length >= 1, 'Recent changes live on Work');
assert.ok(!recentIds.some(text => text.includes('pc-done') || text.includes('Order pc-done')), 'closed orders stay out of Recent');
assert.match(get('mute-status').textContent, /Mute only hides this inbox item/);
assert.match(get('work-for-you-decide-summary').textContent, /Decide · 6/);

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

process.stdout.write(JSON.stringify({
  decide_rows: decideRows.length,
  decide_more: sixMore && sixMore.textContent,
  decide_more_href: sixMore && sixMore.href,
  for_you_kpi: sixKpi,
  chips: chipText,
  chip_hrefs: chipHrefs,
  overview_has_mute: Boolean(overviewMute),
  overview_has_more: Boolean(overviewMore),
  work_decide: workDecide.length,
  work_read: workRead.length,
  work_mutes: workMutes.length,
  work_more: workMore.length,
  recent_count: recent.length,
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
}));
