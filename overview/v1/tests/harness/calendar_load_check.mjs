// Issue #153: Calendar load-by-day bars + Due/Next-fire doors on calendar.v1.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));

class El {
  constructor(tag) {
    this.tagName = String(tag || 'div').toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.className = '';
    this.textContent = '';
    this.hidden = false;
    this.href = '';
    this.style = {};
    this._role = null;
    this._id = null;
  }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter((x) => x !== c); return c; }
  append(...cs) { for (const c of cs) this.appendChild(c); }
  get firstChild() { return this.children[0] || null; }
  setAttribute(k, v) {
    this.attributes[k] = v;
    if (k === 'data-role') this._role = v;
    if (k === 'id') this._id = v;
    if (k === 'href') this.href = v;
  }
  getAttribute(k) { return this.attributes[k]; }
  _walk(pred) {
    if (pred(this)) return this;
    for (const c of this.children) {
      const r = c._walk ? c._walk(pred) : null;
      if (r) return r;
    }
    return null;
  }
  querySelector(sel) {
    const roleM = sel.match(/^\[data-role="([^"]+)"\]$/);
    if (roleM) return this._walk((n) => n._role === roleM[1]);
    const idM = sel.match(/^#(.+)$/);
    if (idM) return this._walk((n) => n._id === idM[1]);
    return null;
  }
  querySelectorAll(sel) {
    const results = [];
    const cls = sel.startsWith('.') ? sel.slice(1) : '';
    const walk = (n) => {
      if (cls && n.className === cls) results.push(n);
      for (const c of n.children) walk(c);
    };
    walk(this);
    return results;
  }
}

globalThis.document = { createElement(tag) { return new El(tag); } };
globalThis.window = { __CALENDAR_V1_NO_AUTO_BOOT__: true };

const cal = await import(join(HERE, '..', '..', 'static', 'js', 'calendar.v1.js'));

function makeRoot() {
  const root = new El('section');
  root.setAttribute('id', 'calendar-view');
  const doors = new El('nav');
  doors.setAttribute('data-role', 'cal-doors');
  doors.setAttribute('id', 'calendar-doors');
  const load = new El('div');
  load.setAttribute('data-role', 'cal-load');
  load.setAttribute('id', 'calendar-load');
  const summary = new El('p');
  summary.setAttribute('data-role', 'cal-load-summary');
  const chart = new El('div');
  chart.setAttribute('data-role', 'cal-load-chart');
  chart.hidden = true;
  load.append(summary, chart);
  root.append(doors, load);
  return root;
}

const origin = '2026-09-17';
const load = cal.buildLoadByDay({
  workDates: [
    {kind: 'deadline', product: 'blueprint', dtstart: '2026-09-16', all_day: true},
    {kind: 'reminder', product: 'blueprint', dtstart: '2026-09-17', all_day: true},
    {kind: 'mentioned', product: 'blueprint', dtstart: '2026-09-16', all_day: true},
    {kind: 'timer', product: 'other', dtstart: '2026-09-18', all_day: true},
  ],
  events: [{title: 'Standup', at: '2026-09-18'}],
  agents: [{name: 'loop-health', next_fire: '2026-09-18'}],
  origin,
});
assert.equal(load.origin, '2026-09-14');
assert.equal(load.state, 'healthy');
assert.equal(load.total, 5);
assert.deepEqual(load.days.map((row) => row.label), ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']);
assert.deepEqual(load.days.map((row) => row.count), [0, 0, 1, 1, 3, 0, 0]);

const filtered = cal.buildLoadByDay({
  workDates: [
    {kind: 'deadline', product: 'blueprint', dtstart: '2026-09-17', all_day: true},
    {kind: 'deadline', product: 'shop', dtstart: '2026-09-17', all_day: true},
  ],
  events: [],
  agents: [],
  origin,
  project: 'blueprint',
});
assert.equal(filtered.total, 1);

const quiet = cal.buildLoadByDay({workDates: [], events: [], agents: [], origin});
assert.equal(quiet.state, 'empty');
assert.equal(quiet.total, 0);

const unavailable = cal.buildLoadByDay({
  workDates: [{kind: 'deadline', dtstart: '2026-09-17', all_day: true}],
  origin,
  readable: false,
});
assert.equal(unavailable.state, 'unavailable');
assert.equal(unavailable.days.length, 0);

const root = makeRoot();
cal.paintLoad(root, load);
cal.paintDoors(root, {
  due_count: 2,
  next_fire_line: 'Next fire · loop-health in 12m',
});
const summary = root.querySelector('[data-role="cal-load-summary"]');
const chart = root.querySelector('[data-role="cal-load-chart"]');
assert.equal(summary.textContent, '5 scheduled · this week');
assert.equal(chart.hidden, false);
assert.equal(chart.querySelectorAll('.ov-cal-load-col').length, 7);
assert.equal(chart.getAttribute('aria-label'), '5 scheduled · this week');

const quietRoot = makeRoot();
cal.paintLoad(quietRoot, quiet);
assert.equal(quietRoot.querySelector('[data-role="cal-load-summary"]').textContent, 'Quiet this week.');
assert.equal(quietRoot.querySelector('[data-role="cal-load-chart"]').hidden, true);
assert.equal(quietRoot.querySelector('[data-role="cal-load-chart"]').children.length, 0);

const down = makeRoot();
cal.paintLoad(down, unavailable);
assert.equal(down.querySelector('[data-role="cal-load-summary"]').textContent, 'Schedule load unavailable');
assert.equal(down.querySelector('[data-role="cal-load-chart"]').hidden, true);

const doors = root.querySelector('[data-role="cal-doors"]');
assert.equal(doors.children.length, 4);
assert.equal(doors.children[0].textContent, 'Due · 2');
assert.equal(doors.children[0].href, '/');
assert.equal(doors.children[1].textContent, 'Due / Remind');
assert.equal(doors.children[1].href, '/work?attention=due');
assert.equal(doors.children[2].textContent, 'Next fire · loop-health in 12m');
assert.equal(doors.children[2].href, '/agents');
assert.equal(doors.children[3].textContent, 'Firings');
assert.equal(doors.children[3].href, '/timeline');

const html = readFileSync(join(HERE, '..', '..', 'static', 'operations.html'), 'utf8');
const calendar = html.split('id="calendar-view"')[1].split('id="settings-view"')[0];
assert.ok(calendar.includes('id="calendar-load"'));
assert.ok(calendar.includes('id="calendar-doors"'));
assert.ok(!calendar.includes('wo-tile'));
assert.ok(!calendar.includes('id="agents-pulse"'));
assert.ok(!calendar.includes('id="work-band-act-now"'));

// pc-1540 / Cap C2: reserved Hybrid source + outbound strips. WorkLane is
// only ever live when the workspace is actually readable; MCP/Connector
// are always reserved (never a fake live), matching Apple/Outlook outbound.
const sourcesRoot = new El('section');
const sourcesHost = new El('div');
sourcesHost.setAttribute('data-role', 'cal-sources');
const outboundHost = new El('div');
outboundHost.setAttribute('data-role', 'cal-outbound');
sourcesRoot.append(sourcesHost, outboundHost);

cal.paintSourceStrip(sourcesRoot, {workLane: true});
const sourceStates = sourcesHost.children.map((c) => c.dataset.state);
assert.deepEqual(sourceStates, ['live', 'live', 'reserved', 'reserved']);
assert.deepEqual(sourcesHost.children.map((c) => c.textContent), ['Local', 'WorkLane', 'MCP', 'Connector']);
assert.equal(sourcesHost.children[2].getAttribute('aria-disabled'), 'true');

cal.paintSourceStrip(sourcesRoot, {workLane: false});
const sourceStatesNoWorkLane = sourcesHost.children.map((c) => c.dataset.state);
assert.deepEqual(sourceStatesNoWorkLane, ['live', 'unavailable', 'reserved', 'reserved']);

cal.paintOutboundStrip(sourcesRoot);
const outboundStates = outboundHost.children.map((c) => c.dataset.state);
assert.deepEqual(outboundStates, ['reserved', 'reserved']);
assert.deepEqual(outboundHost.children.map((c) => c.textContent), ['Apple', 'Outlook']);
assert.equal(outboundHost.children[0].getAttribute('aria-disabled'), 'true');

console.log(JSON.stringify({
  origin: load.origin,
  total: load.total,
  counts: load.days.map((row) => row.count),
  summary: summary.textContent,
  bars: chart.querySelectorAll('.ov-cal-load-col').length,
  quiet_hidden: quietRoot.querySelector('[data-role="cal-load-chart"]').hidden,
  unavailable: down.querySelector('[data-role="cal-load-summary"]').textContent,
  due_door: doors.children[0].textContent,
  fire_door: doors.children[2].href,
  source_states: sourceStates,
  source_states_no_worklane: sourceStatesNoWorkLane,
  outbound_states: outboundStates,
}));
