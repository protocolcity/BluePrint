// Issue #152: Delivery CI pass/fail spark — honest empty/unavailable and
// repo/PR doors. Not WorkLane triage, For You, or seat shifts.
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
  'timeline-view', 'connections-view', 'delivery-view', 'settings-view',
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
  .replace("const {reconcileList} = await import('/js/dom-reconcile.mjs');", 'const {reconcileList} = {reconcileList: reconcileListFn};');
const bootMarker = 'connectChanges(()=>{if(!document.hidden){refresh();';
const bootAt = raw.indexOf(bootMarker);
if (bootAt === -1) throw new Error('operations.js boot marker missing');
raw = raw.slice(0, bootAt) + `snapshot = ${JSON.stringify(fixture)}; lastSuccess = Date.now();`;
const boot = new Function(...Object.keys(context), `return (async () => { ${raw} return {paintDeliverySpark}; })();`);
const runtime = await boot(...Object.values(context));

const days = Array(14).fill(0);
const fails = Array(14).fill(0);
const merges = Array(14).fill(0);
days[2] = 3;
days[10] = 3;
days[13] = 2;
fails[13] = 2;
merges[8] = 3;
const healthy = {
  state: 'connected',
  repositories: [{repo: 'org/repo', state: 'connected', items: [], groups: [], ci_spark: {
    days, fails, merges, checks: 8, failures: 2, merges_total: 3,
    href: '/delivery?type=workflow', merge_href: '/delivery?type=pull_request',
    out_href: 'https://github.com/org/repo/actions/runs/9', state: 'healthy',
  }}],
  ci_spark: {
    days, fails, merges, checks: 8, failures: 2, merges_total: 3,
    href: '/delivery?type=workflow', merge_href: '/delivery?type=pull_request',
    out_href: 'https://github.com/org/repo/actions/runs/9', state: 'healthy',
  },
};

runtime.paintDeliverySpark(healthy);
const host = get('delivery-ci-spark');
const healthyText = host.textContent;
assert.match(healthyText, /8 checks · last 14 days/);
assert.match(healthyText, /2 fails/);
assert.match(healthyText, /3 merges/);
const links = host.querySelectorAll('a');
assert.equal(links[0].href, '/delivery?type=workflow');
assert.equal(links[1].href, '/delivery?type=pull_request');
assert.equal(links[2].href, 'https://github.com/org/repo/actions/runs/9');
assert.equal(links[2].target, '_blank');
assert.equal(links[2].textContent, 'Open failing check');
assert.ok(host.querySelector('.bp-delivery-ci-spark-line'), 'healthy paints glyphs');
assert.equal(host.querySelector('.bp-delivery-ci-spark-line').dataset.tone, 'error');

runtime.paintDeliverySpark({state: 'connected', repositories: [], ci_spark: {
  days: Array(14).fill(0), fails: Array(14).fill(0), merges: Array(14).fill(0),
  checks: 0, failures: 0, merges_total: 0, href: '/delivery?type=workflow',
  merge_href: '/delivery?type=pull_request', out_href: '', state: 'empty',
}});
const empty = get('delivery-ci-spark').textContent;
assert.equal(empty, 'No CI runs in the last 14 days');

runtime.paintDeliverySpark({state: 'unavailable', repositories: [], ci_spark: {
  days: Array(14).fill(0), fails: Array(14).fill(0), merges: Array(14).fill(0),
  checks: 0, failures: 0, merges_total: 0, href: '/delivery?type=workflow',
  merge_href: '/delivery?type=pull_request', out_href: '', state: 'unavailable',
}});
const unavailable = get('delivery-ci-spark').textContent;
assert.equal(unavailable, 'CI unavailable');

runtime.paintDeliverySpark({state: 'not_configured', repositories: [], ci_spark: {
  days: Array(14).fill(0), fails: Array(14).fill(0), merges: Array(14).fill(0),
  checks: 0, failures: 0, merges_total: 0, href: '/delivery?type=workflow',
  merge_href: '/delivery?type=pull_request', out_href: '', state: 'not_configured',
}});
const notConfigured = get('delivery-ci-spark').textContent;
assert.equal(notConfigured, 'CI not configured');

const mergeDays = Array(14).fill(0);
mergeDays[12] = 1;
runtime.paintDeliverySpark({state: 'connected', repositories: [], ci_spark: {
  days: Array(14).fill(0), fails: Array(14).fill(0), merges: mergeDays,
  checks: 0, failures: 0, merges_total: 1, href: '/delivery?type=workflow',
  merge_href: '/delivery?type=pull_request', out_href: 'https://github.com/org/repo/pull/9',
  state: 'healthy',
}});
const mergesOnly = get('delivery-ci-spark').textContent;
assert.match(mergesOnly, /No CI runs in the last 14 days/);
assert.match(mergesOnly, /1 merge/);

process.stdout.write(JSON.stringify({
  healthy: healthyText,
  healthy_href: links[0].href,
  merge_href: links[1].href,
  out_href: links[2].href,
  out_label: links[2].textContent,
  has_glyphs: true,
  empty,
  unavailable,
  not_configured: notConfigured,
  merges_only: mergesOnly,
}));
