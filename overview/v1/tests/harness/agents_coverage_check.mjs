// Agents coverage panel harness (pc-1480): seat cards before coverage, one
// collapsed unstaffed line, hire commands hidden until a disclosure opens,
// and no classifier jargon in the DOM.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');

class Element {
  constructor(tag = 'div') {
    this.tagName = String(tag).toUpperCase();
    this.children = [];
    this.listeners = {};
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
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  setAttribute() {}
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
      for (const child of node.children) walk(child);
    };
    walk(this);
    return out;
  }
}

const IDS = [
  'page-title', 'page-description', 'eyebrow', 'freshness', 'source-warning', 'footer-status',
  'agents-view', 'agents-heartbeat', 'seat-list', 'job-list', 'supervisor-panel', 'coverage-list',
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
const reconcileList = (parent, items, keyFn, render, opts = {}) => {
  parent.replaceChildren();
  if (!items.length) {
    const empty = new Element('p');
    empty.textContent = opts.emptyText || 'Empty';
    parent.append(empty);
    return;
  }
  for (const item of items) parent.append(render(item));
};
context.readerNav = {readerHref: path => path};
context.changeFeed = {connectChanges() { return {stop() {}}; }};
context.reconcileListFn = reconcileList;
let raw = read('../../static/js/operations.js');
raw = raw.slice(raw.indexOf("'use strict';"), raw.lastIndexOf('})();'));
raw = raw
  .replace("const {readerHref} = await import('/js/reader-navigation.mjs');", 'const {readerHref} = readerNav;')
  .replace("const {connectChanges} = await import('/js/change-feed.mjs');", 'const {connectChanges} = changeFeed;')
  .replace("const {reconcileList} = await import('/js/dom-reconcile.mjs');", 'const {reconcileList} = {reconcileList: reconcileListFn};')
;
const bootMarker = 'connectChanges(()=>{if(!document.hidden){refresh();';
const bootAt = raw.indexOf(bootMarker);
if (bootAt === -1) throw new Error('operations.js boot marker missing');
raw = raw.slice(0, bootAt) + `snapshot = ${JSON.stringify(fixture)}; agents();`;
const scopeKeys = Object.keys(context);
const scopeVals = Object.values(context);
const boot = new Function(...scopeKeys, `return (async () => { ${raw} })();`);
await boot(...scopeVals);

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

const closedText = domText(coverageList);
assert.ok(!/workforce hire/i.test(closedText), 'hire commands must stay hidden until disclosure opens');
assert.ok(!/classifier/i.test(closedText), 'classifier jargon must not appear');

const hireDisclosure = coverageList.querySelectorAll('details').find(d => {
  const summary = d.children.find(c => c.tagName === 'SUMMARY');
  return summary && summary.textContent === 'Hire…';
});
assert.ok(hireDisclosure, 'an active row must expose a Hire disclosure');
hireDisclosure.open = true;
const openText = domText(coverageList);
assert.ok(/workforce hire/i.test(openText), 'opening disclosure must reveal hire commands');

process.stdout.write(JSON.stringify({
  seat_count: seatList.children.length,
  coverage_active_rows: coverageList.children.filter(c => c.className.includes('bp-coverage-row')).length,
  collapsed_summary: collapsed.querySelector('summary').textContent,
  hire_hidden_until_open: !/workforce hire/i.test(closedText),
  no_classifier: !/classifier/i.test(closedText),
}));
