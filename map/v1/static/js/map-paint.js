// map-paint.js — pure SVG paint helpers.
//
// Glass §Paint stack:
//   stage (#world)
//     ├─ #lots               folder silhouettes (base map)
//     ├─ #hub                binder root — depth-0
//     ├─ #dig-in-layer       dig fan / children (empty until dig fires)
//     ├─ #md-viewer-layer    overlay reader (visibility: hidden until open)
//     └─ #chrome-layer       HTML controls
//
// Nothing here polls or subscribes. The host wires state → paint.
// If a paint function reads MapViewState directly it has drifted.

const SVG_NS = 'http://www.w3.org/2000/svg';

const LAYER_IDS = Object.freeze([
  'lots', 'hub', 'dig-in-layer', 'md-viewer-layer', 'chrome-layer',
]);

export function ensureLayers(world) {
  for (const id of LAYER_IDS) {
    if (!world.querySelector(`#${id}`)) {
      const g = document.createElementNS(SVG_NS, 'g');
      g.id = id;
      world.appendChild(g);
    }
  }
}

function el(name, attrs = {}, textContent) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined) continue;
    node.setAttribute(k, String(v));
  }
  if (textContent !== undefined) node.textContent = textContent;
  return node;
}

// Ring-plot lots around the hub. No easing, no motion, no ornament — just
// the layout math a folder tree needs to be legible cold.
function ringPositions(count, radius) {
  const out = [];
  if (count <= 0) return out;
  const step = (Math.PI * 2) / count;
  for (let i = 0; i < count; i += 1) {
    const angle = -Math.PI / 2 + i * step;
    out.push({ x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
  }
  return out;
}

export function paintHub(world, binder) {
  const layer = world.querySelector('#hub');
  layer.replaceChildren();
  if (!binder) return;
  const group = el('g', {
    id: 'hub-node',
    class: 'map-hit map-hub',
    'data-hit-layer': 'hub',
    'data-rel-path': '',
  });
  group.appendChild(el('circle', { cx: 0, cy: 0, r: 44, class: 'map-hub-disc' }));
  group.appendChild(el('text', { x: 0, y: 6, class: 'map-hub-label', 'text-anchor': 'middle' }, binder.name || 'binder'));
  layer.appendChild(group);
}

export function paintLots(world, lots, { radius = 220 } = {}) {
  const layer = world.querySelector('#lots');
  layer.replaceChildren();
  const positions = ringPositions(lots.length, radius);
  lots.forEach((lot, i) => {
    const { x, y } = positions[i];
    const kind = lot.isDir === false ? 'file' : 'folder';
    const group = el('g', {
      class: `map-hit map-lot map-lot-${kind}${lot.hasMd ? ' map-lot-md' : ''}`,
      transform: `translate(${x.toFixed(2)},${y.toFixed(2)})`,
      'data-rel-path': lot.relPath,
      'data-name': lot.name,
      'data-has-md': lot.hasMd ? '1' : '0',
      'data-is-dir': lot.isDir === false ? '0' : '1',
    });
    if (kind === 'folder') {
      group.appendChild(el('rect', { x: -34, y: -22, width: 68, height: 44, rx: 6, class: 'map-lot-plate' }));
    } else {
      group.appendChild(el('circle', { cx: 0, cy: 0, r: 24, class: 'map-lot-plate map-lot-file-plate' }));
    }
    group.appendChild(el('text', { x: 0, y: 4, class: 'map-lot-label', 'text-anchor': 'middle' }, lot.name || lot.relPath));
    layer.appendChild(group);
  });
}

export function paintDigIn(world, digNode, children, { radius = 140, origin } = {}) {
  const layer = world.querySelector('#dig-in-layer');
  layer.replaceChildren();
  if (!digNode || !children || children.length === 0) return;
  const positions = ringPositions(children.length, radius);
  const ox = (origin && Number.isFinite(origin.x)) ? origin.x : 0;
  const oy = (origin && Number.isFinite(origin.y)) ? origin.y : 0;
  children.forEach((child, i) => {
    const { x, y } = positions[i];
    const kind = child.isDir === false ? 'file' : 'folder';
    const relPath = child.relPath || `${digNode.relPath}/${child.name}`;
    const group = el('g', {
      class: `map-hit map-dig-child map-dig-${kind}${child.hasMd ? ' map-dig-md' : ''}`,
      transform: `translate(${(ox + x).toFixed(2)},${(oy + y).toFixed(2)})`,
      'data-rel-path': relPath,
      'data-name': child.name,
      'data-has-md': child.hasMd ? '1' : '0',
      'data-is-dir': child.isDir === false ? '0' : '1',
    });
    if (kind === 'folder') {
      group.appendChild(el('rect', { x: -26, y: -18, width: 52, height: 36, rx: 4, class: 'map-dig-plate' }));
    } else {
      group.appendChild(el('circle', { cx: 0, cy: 0, r: 18, class: 'map-dig-plate map-dig-file-plate' }));
    }
    group.appendChild(el('text', { x: 0, y: 4, class: 'map-dig-label', 'text-anchor': 'middle' }, child.name));
    layer.appendChild(group);
  });
}

export function clearDigIn(world) {
  const layer = world.querySelector('#dig-in-layer');
  if (layer) layer.replaceChildren();
}

// fitToLots — snap camera transform to include hub + all lots at the given
// radius. No easing (V1 rule); the host applies the returned transform.
export function fitTransform(width, height, { radius = 220, margin = 60 } = {}) {
  const extent = radius + margin;
  const scale = Math.min(width / (extent * 2), height / (extent * 2), 1.5);
  const cx = width / 2;
  const cy = height / 2;
  return `translate(${cx.toFixed(2)},${cy.toFixed(2)}) scale(${scale.toFixed(3)})`;
}

export const _internal = { ringPositions, LAYER_IDS };
