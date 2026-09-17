// Issue 142: Timeline activity histogram paints day/week buckets from the
// firings spine and stays copy-only when the window is quiet.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {reconcileList} from '../../static/js/dom-reconcile.mjs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');

class Element {
  constructor(tag = 'div') {
    this.tagName = String(tag).toUpperCase();
    this.nodeType = tag === '#text' ? 3 : 1;
    this.children = [];
    this.childNodes = this.children;
    this.listeners = {};
    this.attributes = {};
    this.className = '';
    this.dataset = {};
    this.hidden = false;
    this.open = false;
    this._text = '';
    this.value = '';
    this.href = '';
    this.style = {};
    this.options = [];
    this.selectedOptions = [{text: ''}];
    this.ownerDocument = {createElement: t => new Element(t), createTextNode: t => Object.assign(new Element('#text'), {_text: String(t), textContent: String(t)})};
    this.classList = {
      add: name => { this.className = `${this.className} ${name}`.trim(); },
      remove: name => { this.className = this.className.split(/\s+/).filter(x => x && x !== name).join(' '); },
      contains: name => this.className.split(/\s+/).includes(name),
      toggle: (name, on) => { if (on === false) this.classList.remove(name); else this.classList.add(name); },
    };
  }
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
  get nextSibling() {
    if (!this.parent) return null;
    const idx = this.parent.children.indexOf(this);
    return this.parent.children[idx + 1] || null;
  }
  replaceChildren(...nodes) { this.children.length = 0; this.append(...nodes); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  hasClass(name) { return String(this.className || '').split(/\s+/).includes(name); }
  querySelector(sel) {
    const all = this.querySelectorAll(sel);
    return all[0] || null;
  }
  querySelectorAll(sel) {
    const out = [];
    const walk = node => {
      if (match(node, sel)) out.push(node);
      for (const child of node.children || []) walk(child);
    };
    for (const child of this.children) walk(child);
    return out;
  }
  get firstChild() { return this.children[0] || null; }
  get textContent() {
    if (this._text && !this.children.length) return this._text;
    return this.children.map(c => c.textContent || c._text || '').join('');
  }
  set textContent(value) { this._text = String(value ?? ''); this.children.length = 0; }
}

function match(node, sel) {
  if (!node || node.nodeType === 3) return false;
  if (sel.startsWith('.')) return node.hasClass(sel.slice(1));
  if (sel.startsWith('#')) return false;
  return node.tagName === sel.toUpperCase();
}

function series(grain, periods, counts) {
  const origin = grain === 'hour'
    ? Date.parse('2026-09-16T16:00:00Z')
    : Date.parse(periods === 7 ? '2026-09-11T00:00:00Z' : '2026-09-04T00:00:00Z');
  const step = grain === 'hour' ? 3600000 : 86400000;
  const buckets = Array.from({length: periods}, (_, index) => ({
    start: new Date(origin + index * step).toISOString().replace('.000Z', 'Z'),
    count: counts[index] || 0,
  }));
  return {grain, buckets, total: buckets.reduce((sum, bucket) => sum + bucket.count, 0)};
}

const hourCounts = Array(24).fill(0);
hourCounts[20] = 2;
hourCounts[22] = 1;
const weekCounts = Array(7).fill(0);
weekCounts[5] = 1;
weekCounts[6] = 2;
const windowCounts = Array(14).fill(0);
windowCounts[2] = 1;
windowCounts[4] = 1;
windowCounts[12] = 1;
windowCounts[13] = 2;

const busyActivity = {
  day: series('hour', 24, hourCounts),
  week: series('day', 7, weekCounts),
  window: series('day', 14, windowCounts),
};
const quietActivity = {
  day: series('hour', 24, []),
  week: series('day', 7, []),
  window: series('day', 14, []),
};

function row(id, at, title) {
  return {id, at, source: 'worklane', project: 'blueprint', actor: 'you', event: 'filed', title, link: {}};
}

const busyPage = {
  rows: [row('r1', '2026-09-17T14:10:00Z', 'Claim')],
  sources: [],
  next_cursor: null,
  activity: busyActivity,
};
const operationsFixture = {
  workspace: {name: 'OneSeo', path: '/tmp/oneseo'},
  build: '0.1.57',
  projects: [],
  agents: [],
  coverage: [],
  supervisor: null,
  sources: [],
  orders: [],
  truncated: false,
  observed_at: new Date().toISOString(),
};

const nodes = new Map();
const get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };

function wireSelect(id, options = [['', '']]) {
  const node = get(id);
  node.options = options.map(([text, value]) => ({text, value}));
  node.value = '';
  node.selectedOptions = [node.options[0]];
  node.add = option => { node.options.push(option); };
  return node;
}

wireSelect('timeline-project', [['All projects', '']]);
wireSelect('timeline-source', [['All sources', '']]);
wireSelect('timeline-period', [
  ['Last 14 days', ''],
  ['Last day', '1'],
  ['Last 3 days', '3'],
  ['Last 7 days', '7'],
]);
wireSelect('attention-filter');
wireSelect('status-filter');
wireSelect('gate-filter');
wireSelect('kind-filter');
wireSelect('project-filter');
wireSelect('assignment-filter');
wireSelect('refresh-preference');
wireSelect('motion-preference');
get('refresh-preference').value = '15';
get('motion-preference').value = 'system';

const context = {
  URL, URLSearchParams, console, JSON, Date,
  AbortSignal: {timeout: () => ({})},
  location: new URL('/timeline', 'https://desk.example'),
  localStorage: {getItem() { return null; }, setItem() {}},
  fetch: async url => {
    const target = String(url);
    if (target.includes('/api/timeline')) return {ok: true, json: async () => busyPage};
    if (target.includes('/api/operations')) return {ok: true, json: async () => operationsFixture};
    return {ok: true, json: async () => ({repositories: []})};
  },
  setInterval() { return 1; },
  clearInterval() {},
  setTimeout() {},
  history: {replaceState() {}},
};
context.document = {
  getElementById: get,
  createElement: tag => new Element(tag),
  addEventListener() {},
  dispatchEvent() { return true; },
  hidden: false,
  scrollingElement: {scrollTop: 0},
  body: new Element('body'),
  querySelector: () => new Element(),
};
context.document.body.classList = {toggle() {}, contains() { return false; }};
context.readerNav = {readerHref: path => path};
context.changeFeed = {connectChanges() { return {stop() {}}; }};
context.reconcileListFn = reconcileList;
context.Option = class { constructor(text, value) { this.text = text; this.value = value; } };

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
raw = raw.slice(0, bootAt) + `timelineData = ${JSON.stringify(busyPage)}; lastSuccess = Date.now();`;

const boot = new Function(...Object.keys(context), `return (async () => { ${raw}
return {
  timeline,
  applyTimeline(data) { timelineData = data; },
  setPeriod(value) { timelinePeriod = value; },
}; })();`);
const runtime = await boot(...Object.values(context));
runtime.timeline();

const defaultSummary = get('timeline-activity-summary').textContent;
const defaultBars = get('timeline-activity-chart').querySelectorAll('.bp-timeline-hist-col').length;
assert.equal(defaultSummary, '5 events · last 14 days · by day');
assert.equal(defaultBars, 14);
assert.equal(get('timeline-activity-chart').hidden, false);

get('timeline-period').value = '1';
get('timeline-period').selectedOptions = [{text: 'Last day'}];
runtime.setPeriod('1');
runtime.timeline();
const daySummary = get('timeline-activity-summary').textContent;
const dayBars = get('timeline-activity-chart').querySelectorAll('.bp-timeline-hist-col').length;
assert.equal(daySummary, '3 events · last day · by hour');
assert.equal(dayBars, 24);

get('timeline-period').value = '7';
get('timeline-period').selectedOptions = [{text: 'Last 7 days'}];
runtime.setPeriod('7');
runtime.timeline();
const weekBars = get('timeline-activity-chart').querySelectorAll('.bp-timeline-hist-col').length;
assert.equal(get('timeline-activity-summary').textContent, '3 events · last 7 days · by day');
assert.equal(weekBars, 7);

get('timeline-period').value = '';
get('timeline-period').selectedOptions = [{text: 'Last 14 days'}];
runtime.setPeriod('');
runtime.applyTimeline({rows: [], sources: [], next_cursor: null, activity: quietActivity});
runtime.timeline();
assert.equal(get('timeline-activity-summary').textContent, 'Quiet in this window.');
assert.equal(get('timeline-activity-chart').hidden, true);
assert.equal(get('timeline-activity-chart').querySelectorAll('.bp-timeline-hist-col').length, 0);

runtime.applyTimeline(null);
runtime.timeline();
assert.equal(get('timeline-activity-summary').textContent, 'Timeline is unavailable right now.');
assert.equal(get('timeline-activity-chart').hidden, true);

process.stdout.write(JSON.stringify({
  default_summary: defaultSummary,
  default_bars: defaultBars,
  day_summary: daySummary,
  day_bars: dayBars,
  week_bars: weekBars,
  quiet_summary: 'Quiet in this window.',
  quiet_chart_hidden: true,
  unavailable_hidden: true,
}));
