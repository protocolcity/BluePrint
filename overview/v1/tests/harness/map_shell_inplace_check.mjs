/* D2 live rendering (pc-1470): map-shell.js sidebar summary must not
   rebuild on a heartbeat-only re-fetch (identical payload) — only the
   "Read HH:MM:SS" note may change. A real data change (open count moves)
   does rebuild, and the note is still current afterwards. Drives the
   real script in a minimal sandbox — same technique as
   map_shell_fallback_check.mjs. */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');

class Element {
  constructor() { this.children = []; this.listeners = {}; this.classList = {add(){}, remove(){}, toggle(){}}; this.dataset = {}; this._text = ''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  setAttribute() {}
  get textContent() { return this._text; }
  set textContent(v) { this._text = v; }
}

let fetchCalls = 0, payload, fakeNow = 0, tick = null;
const RealDate = Date;
function FakeDate(...args) { return args.length ? new RealDate(...args) : new RealDate(fakeNow); }
FakeDate.now = () => fakeNow;
FakeDate.prototype = RealDate.prototype;
const basePayload = () => ({
  workspace: {name: 'Desk', path: '/tmp/desk'},
  projects: [{id: 'example', name: 'Example', folder: 'example', open: 3, attention: 1, working: 1, state: 'available', has_instructions: false}],
  orders: [{project: 'example', status: 'in_progress', gate_type: ''}],
  sources: [{name: 'WorkLane', state: 'available'}],
  truncated: false,
  observed_at: '2026-09-13T00:00:00Z',
});
payload = basePayload();

const nodes = new Map();
const get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
class FakeCustomEvent {
  constructor(type, init) { this.type = type; this.detail = init && init.detail; }
}
const context = {
  URL, URLSearchParams, console,
  location: new URL('/map', 'https://desk.example'),
  fetch: async () => { fetchCalls += 1; return {ok: true, json: async () => payload}; },
  localStorage: {getItem() { return null; }},
  JSON,
  Date: FakeDate,
  CustomEvent: FakeCustomEvent,
  setInterval: fn => { tick = fn; return 1; },
  clearInterval() {},
  setTimeout() {},
};
context.document = {
  getElementById: get,
  createElement: () => new Element(),
  addEventListener(type, fn) { (context.document.listeners ||= {})[type] = fn; },
  dispatchEvent() { return true; },
  body: new Element(),
  hidden: false,
};
vm.createContext(context);

const source = read('../../static/js/map-shell.js')
  .replace("await import('/js/change-feed.mjs')", "{connectChanges(){return {stop(){}};}}");
vm.runInContext(source, context);
const settle = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
await settle();

const summaryContainer = get('map-project-context');
assert.equal(fetchCalls, 1);
const [heading1, summary1, nav1, note1] = summaryContainer.children;
assert.equal(summary1.textContent, '3 open · 1 For You · 1 working');

// Re-fetch with an identical payload (a heartbeat-only tick, driven by
// the same 60s fallback poll as map_shell_fallback_check.mjs). The three
// structural children must be the exact same node instances — only the
// note's "Read" timestamp is allowed to change.
payload = {...basePayload(), observed_at: '2026-09-13T00:00:15Z'};
fakeNow += 60000;
tick();
await settle();
const [heading2, summary2, nav2, note2] = summaryContainer.children;

assert.equal(fetchCalls, 2, 'a second fetch happened');
assert.equal(heading2, heading1, 'heading node identity must survive an unchanged snapshot');
assert.equal(summary2, summary1, 'summary node identity must survive an unchanged snapshot');
assert.equal(nav2, nav1, 'nav node identity must survive an unchanged snapshot');
assert.equal(note2, note1, 'note node identity must survive an unchanged snapshot');
assert.ok(note2.textContent.includes('Read'), 'note still carries the read timestamp');

// A real change (open count moves) does rebuild the summary text.
payload = {...basePayload(), projects: [{...basePayload().projects[0], open: 9}]};
fakeNow += 60000;
tick();
await settle();
const [, summary3] = summaryContainer.children;
assert.equal(summary3.textContent, '9 open · 1 For You · 1 working', 'a real change updates the summary text');

// A throw mid-render (e.g. DOM construction fails partway) must not
// commit the new fingerprint — otherwise every later load with the same
// data silently skips and leaves the sidebar stuck on the partial write.
payload = {...basePayload(), projects: [{...basePayload().projects[0], open: 42}]};
fakeNow += 60000;
const realCreateElement = context.document.createElement;
let createCalls = 0;
context.document.createElement = () => {
  createCalls += 1;
  if (createCalls === 3) throw new Error('boom mid-render');
  return realCreateElement();
};
tick();
await settle();
context.document.createElement = realCreateElement;
const partial = summaryContainer.children.slice();
assert.ok(partial.length < 4, 'the failed attempt left a partial write (sanity check that the throw actually interrupted the render)');

// Retrying the same (previously failed) data must fully rebuild, not skip.
fakeNow += 60000;
tick();
await settle();
const [, summaryAfterRetry] = summaryContainer.children;
assert.equal(summaryContainer.children.length, 4, 'a retry after a failed render rebuilds all four nodes, not just the note');
assert.equal(summaryAfterRetry.textContent, '42 open · 1 For You · 1 working', 'the retried render reflects the data that failed to commit the first time');

console.log('ok');
