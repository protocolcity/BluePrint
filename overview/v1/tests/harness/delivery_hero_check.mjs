// pc-1542 / C4: Delivery hero is PR · CI · Remote (git ledger).
// Optional CI spark stays on Delivery. Not WorkLane triage.
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
    this.target = '';
    this.rel = '';
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
      if (sel.startsWith('.') && node.hasClass(sel.slice(1))) return node;
      if (sel.startsWith('[data-kind=') && node.dataset.kind === sel.slice(12, -2)) return node;
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
      else if (sel.startsWith('.') && node.hasClass(sel.slice(1))) out.push(node);
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
  'timeline-view', 'connections-view', 'delivery-view', 'settings-view',
  'delivery-hero', 'delivery-hero-chips',
  'remote-status', 'delivery-ci-spark', 'delivery-filters', 'delivery-repo', 'delivery-type',
  'delivery-period', 'delivery-clear-filters', 'delivery-boundary', 'remote-repositories',
  'github-connection-status', 'timeline-project', 'timeline-source', 'timeline-actor',
  'timeline-period', 'timeline-filters', 'timeline-clear-filters', 'timeline-more',
  'timeline-new-events', 'calendar-filters', 'calendar-project', 'calendar-prev-week',
  'calendar-next-week', 'calendar-today-btn',
];
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, new Element());
  return nodes.get(id);
};

const fixture = {
  workspace: {name: 'Desk', path: '/tmp/desk'},
  build: '0.1.51',
  projects: [],
  orders: [],
  agents: [],
  sources: [],
  events: [],
  work_dates: [],
  truncated: false,
  observed_at: new Date().toISOString(),
};

const context = {
  URL, URLSearchParams, console, JSON,
  Option: class { constructor(text, value) { this.text = text; this.value = value; this.selected = false; } },
  location: new URL('/delivery', 'https://desk.example'),
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
  node.remove = index => { node.options.splice(index, 1); };
  return node;
}
for (const id of IDS) get(id);
for (const id of ['project-filter', 'assignment-filter', 'status-filter', 'gate-filter', 'kind-filter',
  'attention-filter', 'timeline-project', 'timeline-source', 'refresh-preference', 'motion-preference',
  'delivery-repo', 'delivery-type', 'delivery-period']) wireSelect(id);
get('refresh-preference').value = '15';
get('motion-preference').value = 'system';
get('delivery-type').selectedOptions = [{text: 'CI checks'}];
get('delivery-period').selectedOptions = [{text: 'Last 14 days'}];
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
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {paintDeliveryHero}; })();`);
const runtime = await boot(...Object.values(context));

const days = Array(14).fill(0);
const fails = Array(14).fill(0);
const merges = Array(14).fill(0);
days[13] = 8;
fails[13] = 2;
merges[8] = 3;
const healthy = {
  state: 'connected',
  repositories: [{
    repo: 'org/repo',
    state: 'connected',
    items: [],
    groups: [],
    summary: {open_prs: 2, recent_merges: 3, failed_checks: 2, pending_checks: 0},
    ci_spark: {
      days, fails, merges, checks: 8, failures: 2, merges_total: 3,
      href: '/delivery?type=workflow', merge_href: '/delivery?type=pull_request',
      out_href: 'https://github.com/org/repo/actions/runs/9', state: 'healthy',
    },
  }],
  ci_spark: {
    days, fails, merges, checks: 8, failures: 2, merges_total: 3,
    href: '/delivery?type=workflow', merge_href: '/delivery?type=pull_request',
    out_href: 'https://github.com/org/repo/actions/runs/9', state: 'healthy',
  },
};

runtime.paintDeliveryHero(healthy);
const host = get('delivery-hero-chips');
const chips = host.querySelectorAll('.bp-delivery-hero-chip');
assert.equal(chips.length, 3);
assert.deepEqual(chips.map(chip => chip.dataset.kind), ['pr', 'ci', 'remote']);
assert.equal(chips[0].textContent, 'PR2 open3 merged');
assert.equal(chips[1].textContent, 'CI8 checks2 fails');
assert.equal(chips[2].textContent, 'Remoteconnected1 remote');
assert.equal(chips[0].href, '/delivery?type=pull_request');
assert.equal(chips[1].href, '/delivery?type=workflow');
assert.equal(chips[2].href, '/connections');
assert.equal(chips[0].dataset.tone, 'open');
assert.equal(chips[1].dataset.tone, 'error');
assert.equal(chips[2].dataset.tone, 'working');
assert.ok(!host.textContent.includes('Needs you'));
assert.ok(!host.textContent.toLowerCase().includes('seat'));

runtime.paintDeliveryHero({
  state: 'connected',
  repositories: [],
  ci_spark: {
    days: Array(14).fill(0), fails: Array(14).fill(0), merges: Array(14).fill(0),
    checks: 0, failures: 0, merges_total: 0, href: '/delivery?type=workflow',
    merge_href: '/delivery?type=pull_request', out_href: '', state: 'empty',
  },
});
const emptyChips = get('delivery-hero-chips').querySelectorAll('.bp-delivery-hero-chip');
assert.equal(emptyChips[0].textContent, 'PRnone');
assert.equal(emptyChips[1].textContent, 'CIno runs');
assert.equal(emptyChips[2].textContent, 'Remoteconnected0 remotes');

runtime.paintDeliveryHero({state: 'unavailable', repositories: [], ci_spark: {
  days: Array(14).fill(0), fails: Array(14).fill(0), merges: Array(14).fill(0),
  checks: 0, failures: 0, merges_total: 0, href: '/delivery?type=workflow',
  merge_href: '/delivery?type=pull_request', out_href: '', state: 'unavailable',
}});
const down = get('delivery-hero-chips').querySelectorAll('.bp-delivery-hero-chip').map(chip => chip.textContent);

runtime.paintDeliveryHero({state: 'not_configured', repositories: [], ci_spark: {
  days: Array(14).fill(0), fails: Array(14).fill(0), merges: Array(14).fill(0),
  checks: 0, failures: 0, merges_total: 0, href: '/delivery?type=workflow',
  merge_href: '/delivery?type=pull_request', out_href: '', state: 'not_configured',
}});
const none = get('delivery-hero-chips').querySelectorAll('.bp-delivery-hero-chip').map(chip => chip.textContent);
assert.deepEqual(down, ['PRunavailable', 'CIunavailable', 'Remoteunavailable']);
assert.deepEqual(none, ['PRnot configured', 'CInot configured', 'Remotenot configured']);
assert.equal(none.every(text => !text.includes('0')), true);

process.stdout.write(JSON.stringify({
  kinds: chips.map(chip => chip.dataset.kind),
  healthy_pr: chips[0].textContent,
  healthy_ci: chips[1].textContent,
  healthy_remote: chips[2].textContent,
  pr_href: chips[0].href,
  ci_href: chips[1].href,
  remote_href: chips[2].href,
  empty_pr: emptyChips[0].textContent,
  unavailable: down,
  not_configured: none,
}));
