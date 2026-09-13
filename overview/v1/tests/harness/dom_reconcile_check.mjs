// Minimal but DOM-spec-faithful harness for dom-reconcile.mjs: implements
// insertBefore/removeChild/appendChild/attributes/classList/dataset well
// enough to prove node identity survives a reconcile (the whole point of
// the module — see test_dom_reconcile.py).
import { reconcileList, syncNote } from "../../static/js/dom-reconcile.mjs";

let nextId = 0;

class ClassList {
  constructor(node) { this.node = node; this.set = new Set(); }
  add(name) { this.set.add(name); this.node._syncClassName(); }
  remove(name) { this.set.delete(name); this.node._syncClassName(); }
  contains(name) { return this.set.has(name); }
}

class Node {
  constructor(nodeType, nodeName) {
    this.uid = ++nextId;
    this.nodeType = nodeType;
    this.nodeName = nodeName;
    this.parentNode = null;
    this.childNodes = [];
    this.attrs = new Map();
    this.dataset = new Proxy({}, {
      get: (t, k) => t[k],
      set: (t, k, v) => { t[k] = String(v); this.setAttribute("data-" + kebab(k), String(v)); return true; },
      deleteProperty: (t, k) => { delete t[k]; this.removeAttribute("data-" + kebab(k)); return true; },
      has: (t, k) => k in t,
      ownKeys: (t) => Reflect.ownKeys(t),
      getOwnPropertyDescriptor: (t, k) => Object.getOwnPropertyDescriptor(t, k),
    });
    this.classList = new ClassList(this);
    this.className = "";
    this._textContent = "";
    this.offsetWidth = 0;
    this.ownerDocument = fakeDocument;
  }
  _syncClassName() { this.className = Array.from(this.classList.set).join(" "); }
  get attributes() {
    return Array.from(this.attrs.entries()).map(([name, value]) => ({ name, value }));
  }
  hasAttribute(name) { return this.attrs.has(name); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  removeAttribute(name) { this.attrs.delete(name); }
  get firstChild() { return this.childNodes[0] || null; }
  get nextSibling() {
    if (!this.parentNode) return null;
    const i = this.parentNode.childNodes.indexOf(this);
    return this.parentNode.childNodes[i + 1] || null;
  }
  get textContent() {
    if (this.nodeType === 3) return this._textContent;
    return this.childNodes.map((c) => c.textContent).join("");
  }
  set textContent(value) {
    if (this.nodeType === 3) { this._textContent = value; return; }
    for (const c of this.childNodes.slice()) this.removeChild(c);
    if (value) this.appendChild(fakeDocument.createTextNode(value));
  }
  appendChild(child) {
    if (child.parentNode) child.parentNode.removeChild(child);
    this.childNodes.push(child);
    child.parentNode = this;
    return child;
  }
  insertBefore(child, ref) {
    if (child.parentNode) child.parentNode.removeChild(child);
    if (ref == null) { this.childNodes.push(child); }
    else {
      const i = this.childNodes.indexOf(ref);
      this.childNodes.splice(i === -1 ? this.childNodes.length : i, 0, child);
    }
    child.parentNode = this;
    return child;
  }
  removeChild(child) {
    this.childNodes = this.childNodes.filter((c) => c !== child);
    child.parentNode = null;
    return child;
  }
}

function kebab(k) { return k.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase()); }

class Element extends Node {
  constructor(tag) { super(1, String(tag).toUpperCase()); this.tagName = this.nodeName; }
}

class TextNode extends Node {
  constructor(text) { super(3, "#text"); this._textContent = text; }
}

const fakeDocument = {
  createElement: (tag) => new Element(tag),
  createTextNode: (text) => new TextNode(text),
};

function el(tag, text, cls, key) {
  const node = new Element(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls, node.setAttribute("class", cls);
  if (key !== undefined) node.setAttribute("data-item", String(key));
  return node;
}

function root() { return new Element("div"); }

const cases = {};

// 1. Unchanged snapshot leaves the DOM identical (same node identities).
{
  const container = root();
  const items = [{ id: "a", label: "Alpha" }, { id: "b", label: "Beta" }];
  const build = (item) => el("div", item.label, "row");
  reconcileList(container, items, (i) => i.id, build, { emptyText: "None" });
  const before = container.childNodes.slice();
  reconcileList(container, items, (i) => i.id, build, { emptyText: "None" });
  const after = container.childNodes.slice();
  cases.unchanged_same_identity = {
    sameLength: before.length === after.length,
    sameNodes: before.every((n, i) => n === after[i]),
    noHighlight: after.every((n) => !n.classList.contains("bp-row-changed")),
  };
}

// 2. A changed row is patched (text differs) without rebuilding siblings.
{
  const container = root();
  const build = (item) => el("div", item.label, "row");
  const items1 = [{ id: "a", label: "Alpha" }, { id: "b", label: "Beta" }, { id: "c", label: "Gamma" }];
  reconcileList(container, items1, (i) => i.id, build);
  const nodeA = container.childNodes[0], nodeB = container.childNodes[1], nodeC = container.childNodes[2];
  const items2 = [{ id: "a", label: "Alpha" }, { id: "b", label: "Beta CHANGED" }, { id: "c", label: "Gamma" }];
  reconcileList(container, items2, (i) => i.id, build);
  cases.changed_row_patched = {
    siblingsUntouched: container.childNodes[0] === nodeA && container.childNodes[2] === nodeC,
    patchedInPlace: container.childNodes[1] === nodeB,
    newText: container.childNodes[1].textContent,
    highlighted: container.childNodes[1].classList.contains("bp-row-changed"),
    siblingsNotHighlighted: !nodeA.classList.contains("bp-row-changed") && !nodeC.classList.contains("bp-row-changed"),
  };
}

// 3. Added / removed keys.
{
  const container = root();
  const build = (item) => el("div", item.label, "row");
  reconcileList(container, [{ id: "a", label: "A" }, { id: "b", label: "B" }], (i) => i.id, build);
  reconcileList(container, [{ id: "b", label: "B" }, { id: "c", label: "C" }], (i) => i.id, build);
  cases.add_remove = {
    keys: container.childNodes.map((n) => n.getAttribute("data-key")),
    count: container.childNodes.length,
  };
}

// 4. Reordering moves nodes but preserves identity (and a node not moved
// stays exactly where it was, so an in-progress focus/scroll target on it
// is never disturbed).
{
  const container = root();
  const build = (item) => el("div", item.label, "row");
  reconcileList(container, [{ id: "a" }, { id: "b" }, { id: "c" }], (i) => i.id, build);
  const [a, b, c] = container.childNodes;
  reconcileList(container, [{ id: "c" }, { id: "a" }, { id: "b" }], (i) => i.id, build);
  cases.reorder_preserves_identity = {
    order: container.childNodes.map((n) => n.getAttribute("data-key")),
    sameNodes: container.childNodes[0] === c && container.childNodes[1] === a && container.childNodes[2] === b,
  };
}

// 5. A focused control inside an unchanged row is left completely alone.
{
  const container = root();
  const build = (item) => {
    const row = el("div", undefined, "row");
    const button = el("button", item.label);
    row.appendChild(button);
    return row;
  };
  reconcileList(container, [{ id: "a", label: "Dispatch" }], (i) => i.id, build);
  const button = container.childNodes[0].childNodes[0];
  let focused = false;
  button.focus = () => { focused = true; };
  button.focus();
  reconcileList(container, [{ id: "a", label: "Dispatch" }], (i) => i.id, build);
  cases.focus_preserved_on_unchanged_row = {
    sameButtonNode: container.childNodes[0].childNodes[0] === button,
    stillFocusedFlagUntouched: focused === true,
  };
}

// 6. `open` on a <details> row is never clobbered by a patch, even when
// the row's other data changed.
{
  const container = root();
  const build = (item) => {
    const row = el("details", undefined, "row");
    row.appendChild(el("summary", item.label));
    return row;
  };
  reconcileList(container, [{ id: "a", label: "Note" }], (i) => i.id, build);
  const details = container.childNodes[0];
  details.setAttribute("open", "");
  reconcileList(container, [{ id: "a", label: "Note changed" }], (i) => i.id, build);
  cases.open_state_preserved = {
    stillOpen: details.hasAttribute("open"),
    textUpdated: details.textContent,
  };
}

// 7. Empty state: no items paints one empty paragraph; calling again with
// the same empty text does not touch the DOM (no repeated appends).
{
  const container = root();
  const build = (item) => el("div", item.label);
  reconcileList(container, [], (i) => i.id, build, { emptyText: "Nothing here" });
  const firstEmptyNode = container.childNodes[0];
  reconcileList(container, [], (i) => i.id, build, { emptyText: "Nothing here" });
  cases.empty_state_stable = {
    childCount: container.childNodes.length,
    text: container.childNodes[0] ? container.childNodes[0].textContent : "",
    sameNode: container.childNodes[0] === firstEmptyNode,
  };
}

// 8. A duplicate key among the current children (should never happen from
// reconcileList itself, but must not compound if it does) is deduped down
// to one node, and a duplicate key in the incoming items list is patched
// once and the second occurrence skipped — never three nodes for two items.
{
  const container = root();
  const build = (item) => el("div", item.label, "row");
  const dupA = el("div", "stale A", "row");
  dupA.dataset.key = "p:1";
  const dupB = el("div", "stale B", "row");
  dupB.dataset.key = "p:1";
  container.appendChild(dupA);
  container.appendChild(dupB);
  reconcileList(container, [{ id: "p:1", label: "One" }, { id: "p:1", label: "One" }], (i) => i.id, build);
  const afterDedupe = container.childNodes.slice();
  reconcileList(container, [{ id: "p:1", label: "One" }, { id: "p:2", label: "Two" }], (i) => i.id, build);
  cases.duplicate_key_deduped = {
    countAfterDupeInput: afterDedupe.length,
    keysAfterDupeInput: afterDedupe.map((n) => n.getAttribute("data-key")),
    countAfterFollowUp: container.childNodes.length,
    order: container.childNodes.map((n) => n.getAttribute("data-key")),
    firstNodeReused: container.childNodes[0] === dupA,
  };
}

// 9. syncNote: a fixed-identity note sibling is created once and patched
// in place on repeated calls, never appended again; passing a falsy text
// removes it.
{
  const container = root();
  syncNote(container, "excluded", "Excluded: a, b.", "bp-note");
  const first = container.childNodes[0];
  syncNote(container, "excluded", "Excluded: a, b.", "bp-note");
  syncNote(container, "excluded", "Excluded: a, b, c.", "bp-note");
  const afterUpdate = container.childNodes[0];
  const countBeforeRemoval = container.childNodes.length;
  syncNote(container, "excluded", null);
  cases.sync_note_stable = {
    countBeforeRemoval,
    sameNodeAfterRepeat: first === afterUpdate,
    textAfterUpdate: afterUpdate.textContent,
    countAfterRemoval: container.childNodes.length,
  };
}

process.stdout.write(JSON.stringify(cases));
