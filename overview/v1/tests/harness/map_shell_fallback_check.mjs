/* D2 review fix: map-shell.js must fall back to a 60s poll (paused while
   the tab is hidden) when the change feed is unavailable, same as
   operations.js. Drives the real script in a minimal sandbox with a fake
   clock and a captured setInterval tick — no live network or timers. */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');

class Element {
  constructor() { this.children = []; this.listeners = {}; this.classList = {add(){}, remove(){}, toggle(){}}; this.dataset = {}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  setAttribute() {}
}

const payload = {
  workspace: {name: 'Desk', path: '/tmp/desk'},
  projects: [{id: 'example', name: 'Example', folder: 'example', open: 1, attention: 0, working: 1, state: 'available', has_instructions: false}],
  orders: [{project: 'example', status: 'in_progress', gate_type: ''}],
  sources: [{name: 'WorkLane', state: 'available'}],
  truncated: false,
  observed_at: '2026-09-13T00:00:00Z',
};

let fetchCalls = 0, fakeNow = 0, tick = null;
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
  Date: {now: () => fakeNow},
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

assert.equal(fetchCalls, 1, 'initial load must fetch once');
assert.ok(typeof tick === 'function', 'map-shell.js must register a fallback poll interval');

// Not yet due — under 60s since the initial load.
fakeNow += 30000;
tick();
await settle();
assert.equal(fetchCalls, 1, 'fallback must not poll before 60s elapse');

// Due — 60s elapsed.
fakeNow += 30000;
tick();
await settle();
assert.equal(fetchCalls, 2, 'fallback must poll once 60s have elapsed');

// Hidden tab — fallback must pause even though 60s have elapsed again.
context.document.hidden = true;
fakeNow += 61000;
tick();
await settle();
assert.equal(fetchCalls, 2, 'fallback must not poll while the tab is hidden');

// Visible again — resumes.
context.document.hidden = false;
tick();
await settle();
assert.equal(fetchCalls, 3, 'fallback must resume once the tab is visible again');
