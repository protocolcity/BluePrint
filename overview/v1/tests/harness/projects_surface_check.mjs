// Projects surface harness (pc-1486): comparison rows, quiet collapse,
// unavailable honesty, project-scoped links, and keyboard breakdown.
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
    this.style = {};
    this.ownerDocument = {createElement: tag => new Element(tag)};
    this.classList = {
      add: name => { this.className = `${this.className} ${name}`.trim(); },
      remove: name => { this.className = this.className.split(/\s+/).filter(x => x && x !== name).join(' '); },
    };
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
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
  setAttribute(name, value) { this.attributes[name] = String(value); }
  querySelector(sel) {
    const walk = node => {
      if (sel === 'details' && node.tagName === 'DETAILS') return node;
      if (sel === 'summary' && node.tagName === 'SUMMARY') return node;
      if (sel === '.bp-projects-spark' && node.className && node.className.includes('bp-projects-spark')) return node;
      if (sel === '.bp-projects-pulse' && node.className && node.className.includes('bp-projects-pulse')) return node;
      if (sel === '.bp-projects-stack' && node.className && node.className.includes('bp-projects-stack')) return node;
      if (sel.startsWith('a[href') && node.tagName === 'A') return node;
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
      if (sel === '.bp-projects-row' && node.className && node.className.includes('bp-projects-row') && !node.className.includes('bp-projects-head')) out.push(node);
      if (sel === '.bp-projects-compare-row' && node.className && node.className.includes('bp-projects-compare-row')) out.push(node);
      if (sel === '.bp-projects-spark' && node.className && node.className.includes('bp-projects-spark')) out.push(node);
      if (sel === '.bp-projects-pulse' && node.className && node.className.includes('bp-projects-pulse')) out.push(node);
      if (sel === '.bp-projects-stack' && node.className && node.className.includes('bp-projects-stack')) out.push(node);
      if (sel === 'details' && node.tagName === 'DETAILS') out.push(node);
      if (sel === 'a' && node.tagName === 'A') out.push(node);
      for (const child of node.children || []) walk(child);
    };
    walk(this);
    return out;
  }
  get textContent() {
    if (this._text && !this.children.length) return this._text;
    return this.children.map(c => c.textContent || c._text || '').join('');
  }
  set textContent(value) { this._text = String(value ?? ''); }
}

function syncNode(existing, rendered) {
  existing.className = rendered.className;
  existing.dataset = {...rendered.dataset};
  existing.hidden = rendered.hidden;
  existing.replaceChildren(...rendered.children);
}

function reconcileList(container, items, keyFn, buildRow, {emptyText = ''} = {}) {
  const existing = new Map();
  for (const child of [...container.children]) existing.set(child.dataset.key, child);
  let cursor = container.firstChild;
  if (!items.length) {
    container.replaceChildren(Object.assign(new Element('p'), {className: 'bp-empty', textContent: emptyText}));
    return;
  }
  if (container.firstChild && container.firstChild.className === 'bp-empty') container.replaceChildren();
  const seen = new Set();
  for (const item of items) {
    const key = keyFn(item);
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
  'projects-view', 'projects-summary', 'projects-compare', 'projects-compare-summary', 'projects-filter', 'projects-list', 'projects-filters',
  'refresh', 'desk-scope', 'desk-name', 'scope-path', 'restore-muted', 'refresh-preference',
  'motion-preference', 'preferences', 'preference-status', 'search', 'project-filter',
  'assignment-filter', 'status-filter', 'gate-filter', 'kind-filter', 'attention-filter',
  'filters', 'work-list', 'results', 'page-count', 'previous', 'next', 'clear-filters',
  'active-filters', 'overview-view', 'work-view', 'agents-view', 'calendar-view',
  'timeline-view', 'connections-view', 'delivery-view', 'settings-view', 'overview-executions',
  'metrics', 'for-you-decide', 'overview-decide-more', 'overview-face-chips', 'overview-throughput', 'overview-unrouted', 'overview-source-line',
  'work-flow',
  'work-band-act-now', 'work-act-now', 'work-act-now-count', 'work-act-now-more',
  'work-band-my-todos', 'work-my-todos', 'work-my-todos-count', 'work-my-todos-more',
  'work-band-seat-backlog', 'work-seat-backlog', 'work-seat-backlog-count', 'work-seat-backlog-more',
  'mute-status',
  'project-summary', 'source-list', 'seat-list', 'job-list', 'agent-detail', 'supervisor-panel',
  'coverage-list', 'agents-heartbeat', 'timeline-project', 'timeline-source', 'timeline-actor',
  'timeline-list', 'timeline-sources', 'timeline-more', 'timeline-new-events', 'timeline-filters',
  'timeline-hero', 'timeline-doors', 'timeline-activity', 'timeline-activity-chart', 'timeline-activity-summary', 'timeline-period',
  'calendar-project', 'calendar-today', 'calendar-next', 'calendar-past', 'calendar-prev-week',
  'calendar-next-week', 'calendar-today-btn', 'calendar-filters', 'calendar-today-heading',
  'calendar-next-heading', 'calendar-past-summary', 'calendar-past-wrap', 'calendar-range',
  'calendar-load', 'calendar-load-chart', 'calendar-load-summary', 'calendar-doors',
  'schedule-list', 'event-list', 'connection-exceptions', 'connection-list', 'capability-list',
  'engine-list', 'excluded-store-list', 'remote-repositories', 'remote-status',
  'github-connection-status', 'refresh-description', 'build', 'workspace-path', 'settings-build',
  'settings-workspace',
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
    {id: 'blueprint', name: 'BluePrint', folder: 'blueprint', open: 31, attention: 4, deferred: 9,
      claimed: 2, parked: 1, running: 1, state: 'available', partial: false,
      last_change: {at: '2026-09-13T14:58:00Z', actor: 'bp-cursor-implementer', order_id: 'pc-1480', verb: 'claim', text: 'claim pc-1480'}},
    {id: 'workforce', name: 'WorkForce', folder: 'workforce', open: 6, attention: 1, deferred: 2,
      claimed: 0, parked: 0, running: 0, state: 'available', partial: false, last_change: null},
    {id: 'worklane', name: 'WorkLane', folder: 'worklane', open: 3, attention: 0, deferred: 0,
      claimed: 0, parked: 0, running: 0, state: 'available', partial: false, last_change: null},
    {id: 'comms', name: 'Comms', folder: 'comms', open: 7, attention: 5, deferred: 1,
      claimed: 1, parked: 0, running: 0, state: 'available', partial: true, last_change: null},
    {id: 'tradeos', name: 'tradeOS', folder: 'tradeos', open: 0, attention: 0, deferred: 0,
      claimed: 0, parked: 0, running: 0, state: 'unavailable', partial: false, last_change: null},
    {id: 'gridfinity', name: 'Gridfinity', folder: 'gridfinity', open: 0, attention: 0, deferred: 0,
      claimed: 0, parked: 0, running: 0, state: 'available', partial: false, last_change: null},
    {id: 'recipes', name: 'Recipes', folder: 'recipes', open: 0, attention: 0, deferred: 0,
      claimed: 0, parked: 0, running: 0, state: 'available', partial: false, last_change: null},
  ],
  agents: [
    {id: 'bp-cursor-implementer', name: 'Cursor implementer', group: 'seat', state: 'working', badge: 'WORKING',
      project: 'blueprint', last_run: null, shift: null},
    {id: 'bp-claude-implementer', name: 'Claude implementer', group: 'seat', state: 'idle', badge: 'IDLE',
      project: 'workforce', last_run: null, shift: null},
  ],
  orders: [
    {id: 'pc-1480', project: 'blueprint', status_word: 'Live', status: 'in_progress', gate_type: '', updated_at: '2026-09-13T14:58:00Z',
      live_with: 'bp-cursor-implementer', parked_by: null},
    {id: 'comms-28', project: 'comms', status_word: 'Live', status: 'in_progress', gate_type: '', updated_at: '2026-09-13T07:24:00Z',
      live_with: 'you', parked_by: null},
  ],
  sources: [{name: 'WorkForce heartbeat', state: 'fresh', last_at: new Date().toISOString()}],
  coverage: [
    {project: 'blueprint', name: 'BluePrint', present: ['Claude', 'Cursor'], held: [], missing: [], not_configured: [],
      text: 'BluePrint: Claude, Cursor', sources: {}, install_hints: {}, hire_commands: {}},
    {project: 'workforce', name: 'WorkForce', present: ['Claude'], held: [], missing: ['Cursor'], not_configured: ['Grok', 'Codex'],
      text: 'WorkForce: Claude · missing Cursor · not configured: Grok, Codex', sources: {}, install_hints: {}, hire_commands: {}},
    {project: 'worklane', name: 'WorkLane', present: [], held: [], missing: [], not_configured: ['Claude', 'Cursor', 'Grok', 'Codex'],
      text: 'WorkLane: none staffed · not configured: Claude, Cursor, Grok, Codex', sources: {}, install_hints: {}, hire_commands: {}},
    {project: 'comms', name: 'Comms', present: [], held: [], missing: [], not_configured: ['Claude', 'Cursor', 'Grok', 'Codex'],
      text: 'Comms: none staffed · not configured: Claude, Cursor, Grok, Codex', sources: {}, install_hints: {}, hire_commands: {}},
    {project: 'gridfinity', name: 'Gridfinity', present: [], held: [], missing: [], not_configured: ['Claude', 'Cursor', 'Grok', 'Codex'],
      text: 'Gridfinity: none staffed · not configured: Claude, Cursor, Grok, Codex', sources: {}, install_hints: {}, hire_commands: {}},
    {project: 'recipes', name: 'Recipes', present: [], held: [], missing: [], not_configured: ['Claude', 'Cursor', 'Grok', 'Codex'],
      text: 'Recipes: none staffed · not configured: Claude, Cursor, Grok, Codex', sources: {}, install_hints: {}, hire_commands: {}},
  ],
  truncated: false,
  observed_at: new Date().toISOString(),
  portfolio: {
    state: 'healthy',
    peak_open: 31,
    hot: 4,
    quiet: 2,
    blocked: 0,
    projects: [
      {id: 'blueprint', name: 'BluePrint', open: 31, attention: 4, deferred: 9,
        hours: [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2], motion: 3, pulse: 'hot',
        href: '/work?project=blueprint', attention_href: '/work?project=blueprint&attention=any',
        map_href: '/map?project=blueprint', state: 'healthy'},
      {id: 'workforce', name: 'WorkForce', open: 6, attention: 1, deferred: 2,
        hours: Array(24).fill(0), motion: 0, pulse: 'hot',
        href: '/work?project=workforce', attention_href: '/work?project=workforce&attention=any',
        map_href: '/map?project=workforce', state: 'empty'},
      {id: 'worklane', name: 'WorkLane', open: 3, attention: 0, deferred: 0,
        hours: Array(24).fill(0), motion: 0, pulse: 'hot',
        href: '/work?project=worklane', attention_href: '/work?project=worklane&attention=any',
        map_href: '/map?project=worklane', state: 'empty'},
      {id: 'comms', name: 'Comms', open: 7, attention: 5, deferred: 1,
        hours: Array(24).fill(0), motion: 0, pulse: 'hot',
        href: '/work?project=comms', attention_href: '/work?project=comms&attention=any',
        map_href: '/map?project=comms', state: 'empty'},
      {id: 'tradeos', name: 'tradeOS', open: 0, attention: 0, deferred: 0,
        hours: Array(24).fill(0), motion: 0, pulse: 'unavailable',
        href: '/work?project=tradeos', attention_href: '/work?project=tradeos&attention=any',
        map_href: '/map?project=tradeos', state: 'unavailable'},
      {id: 'gridfinity', name: 'Gridfinity', open: 0, attention: 0, deferred: 0,
        hours: Array(24).fill(0), motion: 0, pulse: 'quiet',
        href: '/work?project=gridfinity', attention_href: '/work?project=gridfinity&attention=any',
        map_href: '/map?project=gridfinity', state: 'empty'},
      {id: 'recipes', name: 'Recipes', open: 0, attention: 0, deferred: 0,
        hours: Array(24).fill(0), motion: 0, pulse: 'quiet',
        href: '/work?project=recipes', attention_href: '/work?project=recipes&attention=any',
        map_href: '/map?project=recipes', state: 'empty'},
    ],
  },
};

const context = {
  URL, URLSearchParams, console, JSON, Option: class { constructor(text, value) { this.text = text; this.value = value; } },
  location: new URL('/projects', 'https://desk.example'),
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
  addEventListener() {},
  hidden: false,
  querySelector: sel => {
    if (sel === '[data-page="projects"]') {
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
for (const id of ['project-filter', 'assignment-filter', 'status-filter', 'gate-filter', 'kind-filter',
  'attention-filter', 'timeline-project', 'timeline-source', 'refresh-preference', 'motion-preference',
  'calendar-project']) wireSelect(id);
get('projects-view').hidden = false;
get('refresh-preference').value = '15';
get('motion-preference').value = 'system';
context.document.body = new Element('body');
context.document.body.classList = {toggle() {}};
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
const scopeKeys = Object.keys(context);
const scopeVals = Object.values(context);
const boot = new Function(...scopeKeys, `return (async () => { ${raw} return {projects, snapshot}; })();`);
const runtime = await boot(...scopeVals);
runtime.projects();

const list = get('projects-list');
const domText = node => {
  const bits = [];
  const walk = n => {
    if (n.tagName === 'DETAILS' && !n.open) {
      const summary = n.children.find(c => c.tagName === 'SUMMARY');
      if (summary) walk(summary);
      return;
    }
    if (n._text) bits.push(n._text);
    for (const child of n.children || []) walk(child);
  };
  walk(node);
  return bits.join(' ');
};

const activeRows = list.children.filter(c => c.className.includes('bp-projects-row'));
const collapsed = list.children.find(c => c.className.includes('bp-projects-collapsed'));
assert.ok(activeRows.length >= 2, 'active projects must render as comparison rows');
assert.ok(collapsed, 'quiet projects must collapse into one disclosure');
assert.match(collapsed.querySelector('summary').textContent, /Quiet projects/);

const unavailableRow = [...list.querySelectorAll('.bp-projects-row')].find(row => domText(row).includes('tradeOS'));
assert.ok(unavailableRow, 'unavailable project must still render a row');
assert.ok(domText(unavailableRow).includes('Store unavailable'), 'unavailable store must not show zero open');
assert.ok(!domText(unavailableRow).includes('0 open'), 'unavailable store must not paint zero as open');

const blueprintRow = [...list.querySelectorAll('.bp-projects-row')].find(row => domText(row).includes('BluePrint'));
assert.ok(blueprintRow, 'active project row must exist');
assert.ok(domText(blueprintRow).includes('cursor · working'), 'live seat badge must show in Agents now');
assert.ok(domText(blueprintRow).includes('Claude idle'), 'idle hired providers must remain visible with a live claim');
const links = blueprintRow.querySelectorAll('a');
assert.ok(links.length >= 5, 'go links must include Agents and Delivery');
assert.ok(links.some(a => (a.href || '').includes('project=blueprint')), 'links must carry project id');
const agentsLink = links.find(a => a.textContent === 'Agents');
const deliveryLink = links.find(a => a.textContent === 'Delivery');
assert.ok(agentsLink && deliveryLink, 'Agents and Delivery go links must exist');
assert.ok((agentsLink.href || '').includes('return_to=%2Fprojects'), 'Agents link must reader-return to Projects');
assert.ok((deliveryLink.href || '').includes('return_to=%2Fprojects'), 'Delivery link must reader-return to Projects');
assert.ok(blueprintRow.querySelectorAll('details').length >= 1, 'breakdown disclosure must be present');

const workforceRow = [...list.querySelectorAll('.bp-projects-row')].find(row => domText(row).includes('WorkForce'));
assert.ok(workforceRow, 'WorkForce row must exist');
assert.ok(domText(workforceRow).includes('Claude idle'), 'registered seat without live order must read hired coverage');

const worklaneRow = [...list.querySelectorAll('.bp-projects-row')].find(row => domText(row).includes('WorkLane'));
assert.ok(worklaneRow, 'WorkLane row must exist');
assert.ok(domText(worklaneRow).includes('none staffed'), 'project with no registered seats must read none staffed');

const commsRow = [...list.querySelectorAll('.bp-projects-row')].find(row => domText(row).includes('Comms'));
assert.ok(commsRow, 'Comms row must exist');
assert.ok(domText(commsRow).includes('you · live'), 'human live claim must still show in Agents now');

assert.ok(domText(commsRow).includes('partial (limited to 2,000)'), 'partial scan-derived counts must carry the limit marker');

const spark = blueprintRow.querySelector('.bp-projects-spark');
assert.ok(spark, 'active project row must host a per-card spark');
assert.ok(domText(spark).includes('hot'), 'hot store must read as hot');
assert.ok(blueprintRow.querySelector('.bp-projects-stack'), 'open store must paint a stacked open/For You bar');
assert.ok(!domText(unavailableRow.querySelector('.bp-projects-spark') || unavailableRow).includes('0 open'), 'unavailable spark must not paint zero as open');
assert.ok(domText(unavailableRow.querySelector('.bp-projects-spark') || unavailableRow).includes('Store unavailable'), 'unavailable spark stays honest');

const compare = get('projects-compare');
assert.equal(compare.hidden, false, 'workspace compare bars must show for active stores');
const compareRows = compare.querySelectorAll('.bp-projects-compare-row');
assert.ok(compareRows.length >= 4, 'compare bars must list non-quiet stores');
assert.equal(compareRows[0] && compareRows[0].dataset.project, 'blueprint', 'compare bars must lead with the hottest store');
assert.ok(!compareRows.some(row => (row.dataset && row.dataset.project) === 'gridfinity'), 'quiet stores stay out of compare bars');
const compareText = domText(compare);
assert.ok(compareText.includes('open'), 'compare bars must door open work');
assert.ok(compareText.includes('For You'), 'compare bars must door For You');
assert.ok(compareText.includes('Map'), 'compare bars must door Map');
assert.ok(!compareText.includes('Delivery'), 'compare bars must not lead with git evidence');
assert.match(get('projects-compare-summary').textContent, /hot/);

console.log(JSON.stringify({
  active_row_count: activeRows.length,
  quiet_summary: collapsed.querySelector('summary').textContent,
  unavailable_honest: domText(unavailableRow).includes('Store unavailable'),
  links_carry_project: links.some(a => (a.href || '').includes('project=blueprint')),
  agents_delivery_return: Boolean(agentsLink && deliveryLink),
  live_merges_idle_coverage: domText(blueprintRow).includes('cursor · working') && domText(blueprintRow).includes('Claude idle'),
  roster_reads_coverage: domText(workforceRow).includes('Claude idle'),
  unregistered_none_staffed: domText(worklaneRow).includes('none staffed'),
  human_live_claim: domText(commsRow).includes('you · live'),
  partial_counts_marked: domText(commsRow).includes('partial (limited to 2,000)'),
  breakdown_present: blueprintRow.querySelectorAll('details').length >= 1,
  spark_hot: domText(spark).includes('hot'),
  compare_rows: compareRows.length,
  compare_has_work_door: compareText.includes('open'),
  compare_skips_quiet: !compareRows.some(row => (row.dataset && row.dataset.project) === 'gridfinity'),
}));
