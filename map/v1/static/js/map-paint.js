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

// Split hub lots into folder + file rings so dense binders (30+ lots) don't
// pile all their labels onto a single arc. Widen the folder ring when dense,
// stash files on a tighter inner ring as smaller dots so folder labels
// breathe, and alternate labels above/below at the ring level a plain
// evenly-spaced arc can no longer clear.
//
// Returns { placed[], folderRadius, fileRadius, outerRadius } so the host
// can fit-to-screen against the effective outer radius instead of a fixed
// baseRadius that would clip a widened ring.
const HUB_DISC_R = 44;
const FOLDER_ARC_PX = 95;        // per-plate arc budget (~68px plate + gutter)
const FILE_ARC_PX = 34;          // per-dot arc budget on the inner ring
const FILE_RING_CLEAR = 90;      // min inner-ring radius (clears the hub disc)
const FILE_RING_GAP = 90;        // min gap between file ring and folder ring
const HUB_FOLDER_STAGGER_MIN = 8;
const HUB_FILE_STAGGER_MIN = 12;

export function computeHubLayout(lots, { baseRadius = 220 } = {}) {
  const items = Array.isArray(lots) ? lots : [];
  const folders = [];
  const files = [];
  items.forEach((lot, idx) => {
    const isFile = lot && lot.isDir === false;
    (isFile ? files : folders).push(idx);
  });

  const folderCount = folders.length;
  const fileCount = files.length;

  const folderMinRadius = folderCount > 0
    ? (folderCount * FOLDER_ARC_PX) / (2 * Math.PI)
    : 0;
  const folderRadius = Math.max(baseRadius, folderMinRadius);

  const fileMinRadius = fileCount > 0
    ? (fileCount * FILE_ARC_PX) / (2 * Math.PI)
    : 0;
  const fileRadius = fileCount > 0
    ? Math.max(
      FILE_RING_CLEAR,
      fileMinRadius,
      Math.min(folderRadius - FILE_RING_GAP, folderRadius * 0.55),
    )
    : 0;

  const folderStagger = folderCount > HUB_FOLDER_STAGGER_MIN;
  const fileStagger = fileCount > HUB_FILE_STAGGER_MIN;

  const placed = new Array(items.length);
  const folderPositions = ringPositions(folderCount, folderRadius);
  folders.forEach((idx, k) => {
    const { x, y } = folderPositions[k];
    const labelY = folderStagger ? (k % 2 === 0 ? 34 : -28) : 4;
    placed[idx] = { x, y, labelY, ring: 'folder' };
  });
  const filePositions = ringPositions(fileCount, fileRadius);
  files.forEach((idx, k) => {
    const { x, y } = filePositions[k];
    const labelY = fileStagger ? (k % 2 === 0 ? 22 : -16) : 22;
    placed[idx] = { x, y, labelY, ring: 'file' };
  });

  return {
    placed,
    folderRadius,
    fileRadius,
    outerRadius: Math.max(folderRadius, HUB_DISC_R),
  };
}

export function paintLots(world, lots, { radius = 220, selectedRelPath = null } = {}) {
  const layer = world.querySelector('#lots');
  layer.replaceChildren();
  const layout = computeHubLayout(lots, { baseRadius: radius });
  lots.forEach((lot, i) => {
    const pos = layout.placed[i];
    if (!pos) return;
    const kind = lot.isDir === false ? 'file' : 'folder';
    const isSelected = selectedRelPath && lot.relPath === selectedRelPath;
    const group = el('g', {
      class: `map-hit map-lot map-lot-${kind}${lot.hasMd ? ' map-lot-md' : ''}${isSelected ? ' is-selected' : ''}`,
      transform: `translate(${pos.x.toFixed(2)},${pos.y.toFixed(2)})`,
      'data-rel-path': lot.relPath,
      'data-name': lot.name,
      'data-has-md': lot.hasMd ? '1' : '0',
      'data-is-dir': lot.isDir === false ? '0' : '1',
      'data-ring': pos.ring,
    });
    if (kind === 'folder') {
      group.appendChild(el('rect', { x: -34, y: -22, width: 68, height: 44, rx: 6, class: 'map-lot-plate' }));
    } else {
      // Inner-ring files are small dots so the folder ring's labels breathe.
      group.appendChild(el('circle', { cx: 0, cy: 0, r: 12, class: 'map-lot-plate map-lot-file-plate' }));
    }
    const label = el('text', {
      x: 0, y: pos.labelY, class: 'map-lot-label', 'text-anchor': 'middle',
    }, lot.name || lot.relPath);
    if (kind === 'file') label.setAttribute('class', 'map-lot-label map-lot-file-label');
    group.appendChild(label);
    layer.appendChild(group);
  });
  return { outerRadius: layout.outerRadius, folderRadius: layout.folderRadius, fileRadius: layout.fileRadius };
}

// Truncate a name to fit inside a dig chip label. SVG has no native
// text-overflow, so we clip in JS and append U+2026.
const DIG_LABEL_MAX = 14;
function truncateLabel(name) {
  if (typeof name !== 'string') return '';
  if (name.length <= DIG_LABEL_MAX) return name;
  return `${name.slice(0, DIG_LABEL_MAX - 1)}…`;
}

export function paintDigIn(world, digNode, children, { radius = 140, origin } = {}) {
  const layer = world.querySelector('#dig-in-layer');
  layer.replaceChildren();
  if (!digNode || !children || children.length === 0) return;
  const positions = ringPositions(children.length, radius);
  const ox = (origin && Number.isFinite(origin.x)) ? origin.x : 0;
  const oy = (origin && Number.isFinite(origin.y)) ? origin.y : 0;
  // Dense fans (>8 children) get their labels staggered above/below the
  // plate so neighbor labels do not collide along the ring.
  const stagger = children.length > 8;
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
    // Alternate label position when the ring is dense: even indices sit
    // below the plate (y=+30), odd indices ride above (y=-22).
    const labelY = stagger ? (i % 2 === 0 ? 30 : -22) : 4;
    const label = el('text', {
      x: 0, y: labelY, class: 'map-dig-label', 'text-anchor': 'middle',
    }, truncateLabel(child.name));
    if (child.name && child.name.length > DIG_LABEL_MAX) {
      // Keep the full name reachable via native SVG tooltip.
      label.appendChild(el('title', {}, child.name));
    }
    group.appendChild(label);
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

export const _internal = {
  ringPositions,
  LAYER_IDS,
  truncateLabel,
  DIG_LABEL_MAX,
  HUB_FOLDER_STAGGER_MIN,
  HUB_FILE_STAGGER_MIN,
  FOLDER_ARC_PX,
  FILE_ARC_PX,
};
