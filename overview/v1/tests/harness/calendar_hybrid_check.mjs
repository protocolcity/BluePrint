// pc-1563: Calendar Hybrid soft-conflict marks + outbound honesty weight.
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
      if (cls && String(n.className || '').split(/\s+/).includes(cls)) results.push(n);
      for (const c of n.children) walk(c);
    };
    walk(this);
    return results;
  }
}

globalThis.document = { createElement(tag) { return new El(tag); } };
globalThis.window = { __CALENDAR_V1_NO_AUTO_BOOT__: true };

const cal = await import(join(HERE, '..', '..', 'static', 'js', 'calendar.v1.js'));

assert.deepEqual(cal.HYBRID_SCENES, ['A', 'B2', 'C1', 'D1']);
assert.equal(cal.AGENDA_DAY_LIMIT, 8);

const scenes = cal.lockedHybridScenes('2026-09-18');
assert.equal(scenes.length, 4);
assert.deepEqual(scenes.map((row) => row.hybrid.scene), ['A', 'B2', 'C1', 'D1']);
assert.equal(scenes.filter((row) => row.hybrid.bp_event_id === 'bp_evt_d1').length, 1);
assert.equal(new Set(scenes.map((row) => row.hybrid.bp_event_id).filter(Boolean)).size, 1);

const chips = Object.fromEntries(scenes.map((row) => [row.hybrid.scene, row.hybrid.chips.map((c) => c.label)]));
assert.deepEqual(chips.A, ['also on Apple', 'app precedes']);
assert.deepEqual(chips.B2, ['You win']);
assert.deepEqual(chips.C1, ['rejected', 'proposes']);
assert.deepEqual(chips.D1, ['also on Apple']);
assert.equal(scenes[0].hybrid.dimTwin, true);
assert.equal(scenes[0].hybrid.twin, 'Apple copy · hosted 09:00');
assert.equal(scenes[2].hybrid.app, 'Outlook');
assert.equal(scenes[3].hybrid.bp_event_id, 'bp_evt_d1');

const host = new El('div');
for (const row of scenes) cal.paintHybridMark(host, row.hybrid);
const painted = host.querySelectorAll('.bp-cal-soft');
assert.equal(painted.length, 4);
assert.deepEqual(painted.map((n) => n.dataset.scene), ['A', 'B2', 'C1', 'D1']);
const labels = painted.flatMap((n) => n.querySelectorAll('.bp-cal-soft-chip').map((c) => c.textContent));
assert.deepEqual(labels, [
  'also on Apple', 'app precedes',
  'You win',
  'rejected', 'proposes',
  'also on Apple',
]);
assert.equal(host.querySelectorAll('.bp-cal-twin').length, 2);
assert.equal(painted[3].dataset.bpEventId, 'bp_evt_d1');

const dated = [
  {product: 'product', task_id: 'pc-1', summary: 'Real due', dtstart: '2026-09-18', due: '2026-09-18'},
];
const unmarked = cal.applyHybridMarks(dated, {scenes: false, origin: '2026-09-18'});
assert.equal(unmarked.length, 1);
assert.equal(unmarked[0].hybrid, undefined);

const marked = cal.applyHybridMarks(dated, {
  marks: [{task_id: 'pc-1', scene: 'B2'}],
  scenes: false,
});
assert.equal(marked[0].hybrid.scene, 'B2');
assert.deepEqual(marked[0].hybrid.chips.map((c) => c.label), ['You win']);

const dogfood = cal.applyHybridMarks(dated, {scenes: true, origin: '2026-09-18'});
assert.equal(dogfood.length, 5);
assert.deepEqual(dogfood.slice(0, 4).map((row) => row.hybrid.scene), ['A', 'B2', 'C1', 'D1']);
assert.equal(dogfood.filter((row) => row.hybrid?.bp_event_id === 'bp_evt_d1').length, 1);

const already = cal.applyHybridMarks(
  [{...dated[0], hybrid: {scene: 'A'}}],
  {scenes: true, origin: '2026-09-18'},
);
assert.equal(already.filter((row) => row.hybrid?.scene === 'A').length, 1);

const capped = cal.capAgendaDay(Array.from({length: 10}, (_, i) => ({id: i})));
assert.equal(capped.shown.length, 8);
assert.equal(capped.remainder, 2);
assert.equal(capped.total, 10);
assert.equal(cal.capAgendaDay([1, 2, 3]).remainder, 0);

const outboundRoot = new El('section');
const outboundHost = new El('div');
outboundHost.setAttribute('data-role', 'cal-outbound');
outboundRoot.append(outboundHost);
cal.paintOutboundStrip(outboundRoot);
assert.deepEqual(
  outboundHost.children.map((c) => c.textContent),
  [
    'Apple · reader · honesty',
    'Apple · publish · honesty',
    'Outlook · reader · honesty',
    'Outlook · publish · honesty',
  ],
);
assert.deepEqual(outboundHost.children.map((c) => c.dataset.state), ['honesty', 'honesty', 'honesty', 'honesty']);

const html = readFileSync(join(HERE, '..', '..', 'static', 'operations.html'), 'utf8');
const calendar = html.split('id="calendar-view"')[1].split('id="settings-view"')[0];
assert.ok(calendar.includes('id="calendar-today-more"'));
assert.ok(calendar.includes('id="calendar-hero"'));
assert.ok(calendar.includes('id="calendar-doors"'));
assert.ok(calendar.includes('data-role="cal-sources"'));
assert.ok(calendar.includes('data-role="cal-outbound"'));
assert.ok(calendar.includes('id="calendar-app-facet"'));
assert.ok(calendar.includes('BluePrint · SoT'));
assert.ok(calendar.includes('One Agenda'));
assert.equal(calendar.split('id="dated-work"').length - 1, 1);
assert.ok(!calendar.includes('id="reconcile"'));
assert.ok(!calendar.includes('Google'));
assert.ok(!calendar.includes('wo-tile'));
assert.ok(!calendar.includes('id="overview-throughput"'));
assert.ok(!calendar.includes('id="work-flow"'));
assert.ok(!calendar.includes('POS'));

console.log(JSON.stringify({
  scenes: scenes.map((row) => row.hybrid.scene),
  chips,
  outbound: outboundHost.children.map((c) => c.textContent),
  day_cap: capped,
  dogfood_rows: dogfood.length,
}));
