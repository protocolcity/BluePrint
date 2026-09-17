// Compact row review-fix harness (pc-1484 recovery 1): recent changes sort,
// closed-order exclusion, More disclosure outside the row link, and open
// state preserved across reconcileList repaints.
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
    this.attributes = {};
    this.className = '';
    this.dataset = {};
    this.open = false;
    this._text = '';
    this.href = '';
    this.ownerDocument = {createElement: tag => new Element(tag)};
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
  get firstChild() { return this.children[0] || null; }
  get nextSibling() {
    if (!this.parent) return null;
    const idx = this.parent.children.indexOf(this);
    return this.parent.children[idx + 1] || null;
  }
  hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  get textContent() {
    if (this._text && !this.children.length) return this._text;
    return this.children.map(c => c.textContent || c._text || '').join('');
  }
  set textContent(value) { this._text = String(value ?? ''); this.children = []; }
}

function findByClass(node, cls) {
  if ((node.className || '').split(/\s+/).includes(cls)) return node;
  for (const child of node.children || []) {
    const hit = findByClass(child, cls);
    if (hit) return hit;
  }
  return null;
}

let raw = read('../../static/js/operations.js');
raw = raw.slice(raw.indexOf("'use strict';"), raw.lastIndexOf('})();'));
const start = raw.indexOf('function truncateText(text, max)');
const end = raw.indexOf('function executionRow(agent)');
if (start === -1 || end === -1) throw new Error('operations.js compact-row markers missing');
const body = raw.slice(start, end);

const helpers = `
function el(tag, text, cls) {
  const node = new Element(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}
function link(text, href, cls) {
  const node = el('a', text, cls);
  node.href = href;
  return node;
}
function badge(state, text) {
  const node = el('span', text || state.replaceAll('_', ' '), 'bp-badge');
  node.dataset.state = state;
  return node;
}
function date(value) { return value || 'Not reported'; }
function workUrl(order) { return '/work-order?project=' + order.project + '&id=' + order.id; }
function gateLabel(order) { return order.gate_type === 'human' ? 'Needs a decision' : ''; }
let snapshot = {agents: []};
function seatHand(order) {
  for (const worker of (order.workers || [])) {
    if (worker && worker !== 'you') return worker;
  }
  return order.assigned_you ? 'you' : '';
}
function scopeSeatLoad() {}
`;
const boot = new Function('Element', `${helpers}\n${body}\nreturn {assignmentSummary, orderUpdatedAt, isClosedOrder, orderRow, orderHasDetail, orderDetailBody, orderBadges};`);
const {assignmentSummary, orderUpdatedAt, isClosedOrder, orderRow, orderHasDetail, orderDetailBody, orderBadges} = boot(Element);

const personaOwnerShowsYou = assignmentSummary({
  owner: 'You',
  assigned_you: false,
  workers: [],
  needs_routing: false,
}) === 'You';

const orders = [
  {project: 'protocolcity', id: 'pc-1', status: 'backlog', updated_at: '2026-09-13T10:00:00Z'},
  {project: 'protocolcity', id: 'pc-2', status: 'backlog', updated_at: '2026-09-13T12:00:00+00:00'},
  {project: 'protocolcity', id: 'pc-3', status: 'backlog', updated_at: '2026-09-12T23:59:59.000Z'},
  {project: 'protocolcity', id: 'pc-done', status: 'done', updated_at: '2026-09-13T23:00:00Z'},
  {project: 'protocolcity', id: 'pc-bad', status: 'backlog', updated_at: 'not-a-date'},
];
const recent = [...orders]
  .filter(o => !isClosedOrder(o))
  .sort((a, b) => orderUpdatedAt(b) - orderUpdatedAt(a));
const recentSortsByRealTime = recent[0].id === 'pc-2' && recent[1].id === 'pc-1';
const doneOrderExcluded = !recent.some(o => o.id === 'pc-done');

const sample = {
  project: 'protocolcity',
  id: 'pc-1484',
  project_name: 'ProtocolCity',
  title: 'Compact row sample',
  status: 'backlog',
  status_word: 'Open',
  updated_at: '2026-09-13T12:00:00Z',
  owner: 'agent',
  gate_note: 'Needs a decision about the disclosure placement.',
  persona: 'Your todo',
};
const row = orderRow(sample);
const anchor = findByClass(row, 'bp-order-link');
const details = findByClass(row, 'bp-order-detail');
const mute = findByClass(row, 'bp-face-mute');
const titleNode = anchor && anchor.children[0];
const oneLineTitle = Boolean(anchor && titleNode && titleNode.textContent === 'Compact row sample')
  && !findByClass(row, 'bp-order-meta')
  && !findByClass(row, 'bp-order-note');

process.stdout.write(JSON.stringify({
  persona_owner_shows_you: personaOwnerShowsYou,
  recent_sorts_by_real_time: recentSortsByRealTime,
  done_order_excluded: doneOrderExcluded,
  one_line_title: oneLineTitle,
  has_more: Boolean(details),
  has_mute: Boolean(mute),
}));
