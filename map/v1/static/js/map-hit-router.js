// map-hit-router.js — Hit-Layer Single Source of Truth.
//
// Glass §Hit-Layer SoT: exactly one classifier returns {kind, layer, root}
// for every pointer event. V1 has six rows in strict order:
//
//   1. md-viewer   → overlay open, owns hits alone (reader-only; Esc closes)
//   2. chrome      → HTML corner panels; DOM listeners own hits
//   3. dig-in      → pointer over #dig-in-layer child; verb = dig
//   4. hub         → pointer over hub; verb = dig (open) or reset (already open)
//   5. lots        → pointer over #lots child; verb = dig
//   6. empty       → none of the above; verb = pan
//
// No dual routers. If someone wires a second classifier V1 has drifted.

export const HIT_LAYERS = Object.freeze([
  'md-viewer',
  'chrome',
  'dig-in',
  'hub',
  'lots',
  'empty',
]);

const KIND_BY_LAYER = Object.freeze({
  'md-viewer': 'reader',
  chrome: 'chrome',
  'dig-in': 'dig',
  hub: 'hub',
  lots: 'dig',
  empty: 'pan',
});

// A layer id map so the router can be built once and reused across pointer
// events without re-querying the DOM.
export function createHitRouter({
  ids = {
    world: 'world',
    lots: 'lots',
    hub: 'hub',
    digIn: 'dig-in-layer',
    mdViewer: 'md-viewer-layer',
    chrome: 'chrome-layer',
  },
  isMdViewerOpen = () => false,
} = {}) {
  function findAncestor(el, matches) {
    let cur = el;
    while (cur && cur !== document && cur !== null) {
      if (matches(cur)) return cur;
      cur = cur.parentNode;
    }
    return null;
  }

  function classify(target) {
    // Row 1 — md-viewer owns every hit while overlay open.
    if (isMdViewerOpen()) {
      return { kind: 'reader', layer: 'md-viewer', root: null, target };
    }
    if (!target || target.nodeType !== 1) {
      return { kind: 'pan', layer: 'empty', root: null, target };
    }

    // Row 2 — chrome (HTML corner panels with pointer-events: auto).
    const chromeEl = findAncestor(target, el =>
      el.dataset && el.dataset.hitLayer === 'chrome'
      || (el.classList && el.classList.contains('map-chrome-hit'))
    );
    if (chromeEl) return { kind: 'chrome', layer: 'chrome', root: chromeEl, target };

    // Row 3 — #dig-in-layer child.
    const digIn = findAncestor(target, el =>
      el.id === ids.digIn || (el.parentNode && el.parentNode.id === ids.digIn)
    );
    if (digIn && digIn.id !== ids.digIn) {
      return { kind: 'dig', layer: 'dig-in', root: digIn, target };
    }

    // Row 4 — hub.
    const hub = findAncestor(target, el =>
      el.id === ids.hub || (el.dataset && el.dataset.hitLayer === 'hub')
    );
    if (hub) return { kind: 'hub', layer: 'hub', root: hub, target };

    // Row 5 — #lots child.
    const lot = findAncestor(target, el =>
      el.parentNode && el.parentNode.id === ids.lots
    );
    if (lot) return { kind: 'dig', layer: 'lots', root: lot, target };

    // Row 6 — empty; pan verb.
    return { kind: 'pan', layer: 'empty', root: null, target };
  }

  return { classify, layers: HIT_LAYERS, kindFor: (layer) => KIND_BY_LAYER[layer] || 'pan' };
}

// Pure classifier used by tests: takes a synthetic hit descriptor and
// returns the row it lands on. Kept separate so the browser DOM walk in
// createHitRouter isn't required for unit coverage.
export function classifyDescriptor(desc) {
  if (!desc) return { kind: 'pan', layer: 'empty' };
  if (desc.mdViewerOpen) return { kind: 'reader', layer: 'md-viewer' };
  if (desc.overChrome) return { kind: 'chrome', layer: 'chrome' };
  if (desc.overDigIn) return { kind: 'dig', layer: 'dig-in' };
  if (desc.overHub) return { kind: 'hub', layer: 'hub' };
  if (desc.overLot) return { kind: 'dig', layer: 'lots' };
  return { kind: 'pan', layer: 'empty' };
}
