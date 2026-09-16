/* Keyed list reconciliation: patch in place, never rebuild wholesale.
   A list container's children are matched to the new items by key
   (order id, agent id, project id, ...). A matched node is moved only
   when its position actually changed and patched in place — attributes
   and text are diffed and only the differences are written, so a row
   with identical data is never touched. An unmatched key is removed;
   a new key is inserted. A row whose rendered output differs gets a
   one-shot `changedClass` for a brief highlight. `open` is never
   touched by the patch — it is user-controlled state (a <details>
   the visitor opened), not data. */

const PRESERVED_ATTRS = new Set(['open']);

export function syncNode(oldEl, newEl) {
  let changed = false;
  for (const attr of Array.from(oldEl.attributes || [])) {
    if (PRESERVED_ATTRS.has(attr.name)) continue;
    if (!newEl.hasAttribute(attr.name)) { oldEl.removeAttribute(attr.name); changed = true; }
  }
  for (const attr of Array.from(newEl.attributes || [])) {
    if (PRESERVED_ATTRS.has(attr.name)) continue;
    if (oldEl.getAttribute(attr.name) !== attr.value) { oldEl.setAttribute(attr.name, attr.value); changed = true; }
  }
  if (syncChildren(oldEl, newEl)) changed = true;
  return changed;
}

function syncChildren(oldParent, newParent) {
  let changed = false;
  const newNodes = Array.from(newParent.childNodes);
  for (let i = 0; i < newNodes.length; i++) {
    const newNode = newNodes[i];
    const oldNode = oldParent.childNodes[i];
    if (!oldNode) { oldParent.appendChild(newNode); changed = true; continue; }
    if (oldNode.nodeType !== newNode.nodeType || oldNode.nodeName !== newNode.nodeName) {
      oldParent.insertBefore(newNode, oldNode);
      oldParent.removeChild(oldNode);
      changed = true;
      continue;
    }
    if (newNode.nodeType === 3) {
      if (oldNode.textContent !== newNode.textContent) { oldNode.textContent = newNode.textContent; changed = true; }
      continue;
    }
    if (syncNode(oldNode, newNode)) changed = true;
  }
  while (oldParent.childNodes.length > newNodes.length) {
    oldParent.removeChild(oldParent.childNodes[oldParent.childNodes.length - 1]);
    changed = true;
  }
  return changed;
}

function flash(node, highlightClass) {
  if (!node || !highlightClass || !node.classList) return;
  node.classList.remove(highlightClass);
  void node.offsetWidth;
  node.classList.add(highlightClass);
}

/* `buildRow(item)` must be pure — same item in, same node shape out —
   since it runs on every reconcile to know what the row should look
   like now, whether or not that node ends up touched. */
export function reconcileList(container, items, keyOf, buildRow, options = {}) {
  const { emptyText, highlightClass = 'bp-row-changed', enterClass = 'bp-row-enter' } = options;
  if (!items.length) {
    const alreadyEmpty = container.dataset.emptyText === (emptyText || '') && container.childNodes.length <= 1;
    if (alreadyEmpty) return;
    while (container.firstChild) container.removeChild(container.firstChild);
    container.dataset.emptyText = emptyText || '';
    if (emptyText) {
      const p = container.ownerDocument.createElement('p');
      p.className = 'bp-empty';
      p.textContent = emptyText;
      container.appendChild(p);
    }
    return;
  }
  if (container.dataset.emptyText !== undefined) delete container.dataset.emptyText;
  for (const node of Array.from(container.childNodes)) {
    if (!node.dataset || node.dataset.key === undefined) container.removeChild(node);
  }
  const existing = new Map();
  for (const node of Array.from(container.childNodes)) {
    if (!node.dataset || node.dataset.key === undefined) continue;
    if (existing.has(node.dataset.key)) { container.removeChild(node); continue; }
    existing.set(node.dataset.key, node);
  }
  const seen = new Set();
  let cursor = container.firstChild;
  for (const item of items) {
    const key = String(keyOf(item));
    if (seen.has(key)) continue;
    seen.add(key);
    const rendered = buildRow(item);
    rendered.dataset.key = key;
    const node = existing.get(key);
    if (node) {
      existing.delete(key);
      if (node !== cursor) container.insertBefore(node, cursor);
      if (syncNode(node, rendered)) flash(node, highlightClass);
      cursor = node.nextSibling;
    } else {
      container.insertBefore(rendered, cursor);
      flash(rendered, enterClass);
      cursor = rendered.nextSibling;
    }
  }
  for (const leftover of existing.values()) container.removeChild(leftover);
}

/* A single fixed-identity note sibling inside a `reconcileList` container
   (e.g. an "Excluded ..." footnote after the keyed rows): patched in
   place by a stable `key`, never appended again on the next paint. Pass
   `text` as null/undefined/empty to remove the note. */
export function syncNote(container, key, text, cls) {
  let node = null;
  for (const child of Array.from(container.childNodes)) {
    if (child.dataset && child.dataset.note === key) { node = child; break; }
  }
  if (!text) {
    if (node) container.removeChild(node);
    return null;
  }
  if (!node) {
    node = container.ownerDocument.createElement('p');
    node.dataset.note = key;
    container.appendChild(node);
  }
  if (cls !== undefined && node.className !== cls) node.className = cls;
  if (node.textContent !== text) node.textContent = text;
  return node;
}
