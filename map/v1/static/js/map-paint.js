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

import { motionAriaSuffix, motionClassName } from './map-motion.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

// Reduce-motion check for the branch-item fan entrance (FOCUSED_PROJECT
// §Rules: "honor reduced motion"). The CSS opacity-0 start is scoped to
// `@media (prefers-reduced-motion: no-preference)`, so the app's own
// `body.bp-reduce-motion` toggle (Reduce motion "off" in Preferences) only
// disables the transition, not that opacity — it never becomes visible
// again on its own. Skip the entrance class here instead, under either
// signal, so the content itself is never hidden, only its animation.
function prefersReducedMotion() {
  if (typeof document !== 'undefined' && document.body && document.body.classList.contains('bp-reduce-motion')) return true;
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (_) { return false; }
  }
  return false;
}

const LAYER_IDS = Object.freeze([
  'lots', 'hub', 'dig-in-layer', 'project-focus-layer', 'md-viewer-layer', 'chrome-layer',
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
function ringPositions(count, radius, offset = 0) {
  const out = [];
  if (count <= 0) return out;
  const step = (Math.PI * 2) / count;
  for (let i = 0; i < count; i += 1) {
    const angle = -Math.PI / 2 + i * step + offset;
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

// Hub crowding (Design MAP_HUB_CROWDING_GUIDE — prefer order):
//   1) density-aware orbit (+~30% when folderCount ≥ 12)
//   2) multi-orbit lots (R1/R2) when still crowded; files stay inner
//   3) hide-until-hover labels at density (paintLots + CSS)
//   4) longer stagger / higher arc budget
//   5) plate shrink at dense hubs (paintLots)
// Dig REPLACE / focus / md-viewer must stay PASS.
//
// Returns { placed[], folderRadius, fileRadius, outerRadius, dense, … }
// so the host can fit-to-screen against the effective outer radius.
const HUB_DISC_R = 44;
const HUB_DENSE_MIN = 12;         // Design: density tools kick in here
const HUB_DENSITY_SCALE = 1.30;   // +30% lot orbit when dense
const FOLDER_ARC_PX = 128;        // per-plate arc (~plate chord + gutter)
const FOLDER_ARC_PX_DENSE = 140;  // extra chord when dense + multi-orbit
const FILE_ARC_PX = 36;
const FILE_RING_CLEAR = 90;
const FILE_RING_GAP = 100;        // more clearance file↔folder when dense
const HUB_FOLDER_STAGGER_MIN = 6;
const HUB_FILE_STAGGER_MIN = 8;
// Design: split lots across two outer orbits when still crowded after grow.
const HUB_MULTI_ORBIT_MIN = 12;
const HUB_INNER_ORBIT_RATIO = 0.78;

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
  const dense = folderCount >= HUB_DENSE_MIN;
  const multiOrbit = folderCount >= HUB_MULTI_ORBIT_MIN;
  const perOrbitCount = multiOrbit ? Math.ceil(folderCount / 2) : folderCount;
  const arcPx = dense ? FOLDER_ARC_PX_DENSE : FOLDER_ARC_PX;
  const densityScale = dense ? HUB_DENSITY_SCALE : 1;

  const folderMinRadius = folderCount > 0
    ? (perOrbitCount * arcPx) / (2 * Math.PI)
    : 0;
  // Design §1 — grow past baseRadius when dense, then honor arc budget.
  const folderRadius = Math.max(baseRadius * densityScale, folderMinRadius);
  const folderInnerRadius = multiOrbit
    ? Math.max(HUB_DISC_R + FILE_RING_GAP, folderRadius * HUB_INNER_ORBIT_RATIO)
    : folderRadius;

  const fileMinRadius = fileCount > 0
    ? (fileCount * FILE_ARC_PX) / (2 * Math.PI)
    : 0;
  const fileClearanceRef = multiOrbit ? folderInnerRadius : folderRadius;
  const fileGap = dense ? FILE_RING_GAP : 90;
  const fileRadius = fileCount > 0
    ? Math.max(
      FILE_RING_CLEAR,
      fileMinRadius,
      Math.min(fileClearanceRef - fileGap, fileClearanceRef * 0.52),
    )
    : 0;

  const folderStagger = folderCount > HUB_FOLDER_STAGGER_MIN;
  const fileStagger = fileCount > HUB_FILE_STAGGER_MIN;
  // Design §4 — farther radial label offsets when dense (labels outside plate).
  const folderLabelFar = dense ? 48 : 34;
  const folderLabelNear = dense ? -40 : -28;
  const fileLabelFar = dense ? 26 : 22;
  const fileLabelNear = dense ? -20 : -16;

  const placed = new Array(items.length);
  if (multiOrbit) {
    const outerIdxs = folders.filter((_, k) => k % 2 === 0);
    const innerIdxs = folders.filter((_, k) => k % 2 === 1);
    const outerPositions = ringPositions(outerIdxs.length, folderRadius);
    const innerPositions = ringPositions(innerIdxs.length, folderInnerRadius, Math.PI / Math.max(1, innerIdxs.length));
    outerIdxs.forEach((idx, k) => {
      const { x, y } = outerPositions[k];
      const labelY = folderStagger ? (k % 2 === 0 ? folderLabelFar : folderLabelNear) : folderLabelFar;
      placed[idx] = { x, y, labelY, ring: 'folder', orbit: 'outer' };
    });
    innerIdxs.forEach((idx, k) => {
      const { x, y } = innerPositions[k];
      const labelY = folderStagger ? (k % 2 === 0 ? folderLabelFar : folderLabelNear) : folderLabelFar;
      placed[idx] = { x, y, labelY, ring: 'folder', orbit: 'inner' };
    });
  } else {
    const folderPositions = ringPositions(folderCount, folderRadius);
    folders.forEach((idx, k) => {
      const { x, y } = folderPositions[k];
      const labelY = folderStagger ? (k % 2 === 0 ? folderLabelFar : folderLabelNear) : 4;
      placed[idx] = { x, y, labelY, ring: 'folder', orbit: 'outer' };
    });
  }
  const filePositions = ringPositions(fileCount, fileRadius);
  files.forEach((idx, k) => {
    const { x, y } = filePositions[k];
    const labelY = fileStagger ? (k % 2 === 0 ? fileLabelFar : fileLabelNear) : fileLabelFar;
    placed[idx] = { x, y, labelY, ring: 'file', orbit: 'file' };
  });

  return {
    placed,
    folderRadius,
    folderInnerRadius,
    fileRadius,
    multiOrbit,
    dense,
    outerRadius: Math.max(folderRadius, HUB_DISC_R),
  };
}

// Hub-lot label cap. SVG has no native text-overflow, so we clip the long
// tail and stash the full name on an SVG <title> tooltip. Files are dots
// with a shorter cap; folder plates are wider and can carry more glyphs.
const LOT_FOLDER_LABEL_MAX = 16;
const LOT_FILE_LABEL_MAX = 12;
function truncateLotLabel(name, max) {
  if (typeof name !== 'string') return '';
  if (name.length <= max) return name;
  return `${name.slice(0, max - 1)}…`;
}

function lotNodeState(lot, nodeState) {
  const fromOps = nodeState && lot && lot.relPath ? nodeState[lot.relPath] : null;
  if (fromOps) return fromOps;
  if (!lot) return null;
  if (lot.open == null && lot.attention == null && lot.working == null && !lot.storeState && !lot.motion) return null;
  return {
    open: lot.open || 0,
    attention: lot.attention || 0,
    working: lot.working || 0,
    state: lot.storeState || 'available',
    motion: lot.motion || null,
  };
}

export function paintLots(world, lots, { radius = 220, selectedRelPath = null, nodeState = null } = {}) {
  const layer = world.querySelector('#lots');
  layer.replaceChildren();
  const layout = computeHubLayout(lots, { baseRadius: radius });
  const dense = !!layout.dense;
  // Design §5 — shrink plates ~15% at dense hubs only (hit targets stay usable).
  const plateW = 116;
  const plateH = dense ? 38 : 44;
  const plateRx = dense ? 5 : 6;
  lots.forEach((lot, i) => {
    const pos = layout.placed[i];
    if (!pos) return;
    const kind = lot.isDir === false ? 'file' : 'folder';
    const isSelected = selectedRelPath && lot.relPath === selectedRelPath;
    const denseClass = dense ? ' map-lot-dense' : '';
    const state = kind === 'folder' ? lotNodeState(lot, nodeState) : null;
    const countsLabel = state
      ? (state.state && state.state !== 'available'
        ? 'read-only'
        : `${Number(state.open) || 0} · ${Number(state.attention) || 0} · ${Number(state.working) || 0}`)
      : '';
    const motion = state && state.motion ? state.motion : null;
    const motionClass = motionClassName(motion);
    const aria = countsLabel
      ? (countsLabel === 'read-only'
        ? `${lot.name}, read-only`
        : `${lot.name}, ${Number(state.open) || 0} open, ${Number(state.attention) || 0} For You, ${Number(state.working) || 0} working${motionAriaSuffix(motion)}`)
      : `${lot.name}${motionAriaSuffix(motion)}`;
    const group = el('g', {
      class: `map-hit map-lot map-lot-${kind}${lot.hasMd ? ' map-lot-md' : ''}${isSelected ? ' is-selected' : ''}${denseClass}${motionClass}`,
      transform: `translate(${pos.x.toFixed(2)},${pos.y.toFixed(2)})`,
      tabindex: '0',
      role: 'button',
      'aria-label': aria,
      'data-rel-path': lot.relPath,
      'data-name': lot.name,
      'data-has-md': lot.hasMd ? '1' : '0',
      'data-is-dir': lot.isDir === false ? '0' : '1',
      'data-ring': pos.ring,
      'data-motion': (motion && motion.stroke && motion.stroke !== 'none') ? motion.stroke : null,
    });
    if (kind === 'folder') {
      group.appendChild(el('rect', {
        x: -plateW / 2, y: -plateH / 2, width: plateW, height: plateH, rx: plateRx,
        class: 'map-lot-plate',
      }));
    } else {
      // Inner-ring files are small dots so the folder ring's labels breathe.
      group.appendChild(el('circle', { cx: 0, cy: 0, r: dense ? 10 : 12, class: 'map-lot-plate map-lot-file-plate' }));
    }
    const rawName = lot.name || lot.relPath || '';
    const max = kind === 'file' ? LOT_FILE_LABEL_MAX : LOT_FOLDER_LABEL_MAX;
    // Design §3 — at density, truncated rest labels hide until hover/focus;
    // full name stays on <title> + data-name for a11y.
    const labelClass = kind === 'file'
      ? 'map-lot-label map-lot-file-label'
      : 'map-lot-label';
    const label = el('text', {
      x: 0, y: kind === 'folder' ? 4 : pos.labelY, class: labelClass, 'text-anchor': 'middle',
    }, truncateLotLabel(rawName, max));
    label.appendChild(el('title', {}, rawName));
    group.appendChild(label);
    if (countsLabel) {
      group.appendChild(el('text', {
        x: 0, y: plateH / 2 + 12, class: 'map-lot-counts', 'text-anchor': 'middle',
      }, countsLabel));
    }
    layer.appendChild(group);
  });
  return {
    outerRadius: layout.outerRadius,
    folderRadius: layout.folderRadius,
    fileRadius: layout.fileRadius,
    dense,
  };
}

// Truncate a name to fit inside a dig chip label. SVG has no native
// text-overflow, so we clip in JS and append U+2026.
const DIG_LABEL_MAX = 14;
function truncateLabel(name) {
  if (typeof name !== 'string') return '';
  if (name.length <= DIG_LABEL_MAX) return name;
  return `${name.slice(0, DIG_LABEL_MAX - 1)}…`;
}

export function paintDigIn(world, digNode, children, { radius = 140, origin, nodeState = null } = {}) {
  const layer = world.querySelector('#dig-in-layer');
  layer.replaceChildren();
  if (!digNode || !children || children.length === 0) return;
  // Fat dig fans — same density tools as hub: grow radius, stagger, hide
  // labels until hover/focus. Hide kicks in with stagger (>8), not only ≥12.
  const fat = children.length >= 12;
  const stagger = children.length > 8;
  const digRadius = fat ? radius * 1.28 : (stagger ? radius * 1.12 : radius);
  const positions = ringPositions(children.length, digRadius);
  const ox = (origin && Number.isFinite(origin.x)) ? origin.x : 0;
  const oy = (origin && Number.isFinite(origin.y)) ? origin.y : 0;
  children.forEach((child, i) => {
    const { x, y } = positions[i];
    const kind = child.isDir === false ? 'file' : 'folder';
    const relPath = child.relPath || `${digNode.relPath}/${child.name}`;
    const childState = nodeState && relPath ? nodeState[relPath] : null;
    const motion = childState && childState.motion ? childState.motion : (child.motion || null);
    const motionClass = motionClassName(motion);
    const group = el('g', {
      class: `map-hit map-dig-child map-dig-${kind}${child.hasMd ? ' map-dig-md' : ''}${stagger ? ' map-dig-dense' : ''}${motionClass}`,
      tabindex: '0',
      role: 'button',
      'aria-label': `${child.name}${motionAriaSuffix(motion)}`,
      transform: `translate(${(ox + x).toFixed(2)},${(oy + y).toFixed(2)})`,
      'data-rel-path': relPath,
      'data-name': child.name,
      'data-has-md': child.hasMd ? '1' : '0',
      'data-is-dir': child.isDir === false ? '0' : '1',
      'data-motion': (motion && motion.stroke && motion.stroke !== 'none') ? motion.stroke : null,
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

// paintProjectFocus — the approved direction (FOCUSED_PROJECT, pc-1492):
// one project centered, its four virtual branches (Work, Agents, Papers,
// Delivery) around it, and — for exactly one expanded branch — its items
// fanned out from that branch's own position (Rule: "a short expansion
// from the parent node, stable positions for everything else"). Branch
// order never changes so the other three chips stay put when one expands.
const BRANCH_RADIUS = 150;
const BRANCH_ITEM_RADIUS = 130;
const BRANCH_ITEM_MAX_SHOWN = 8;
const BRANCH_ANGLE_SPAN = Math.PI / 2.4; // items fan within this arc of the chip

export function paintProjectFocus(world, { project, branches = [], expandedBranch = null, selectedItem = null, flashBranches = [], tickBranches = [], motion = null } = {}) {
  const layer = world.querySelector('#project-focus-layer');
  if (!layer) return;
  layer.replaceChildren();
  if (!project) return;

  // `.map-branch-item-enter` only sets the *starting* opacity:0 frame (CSS,
  // scoped to `no-preference`) — nothing ever removed the class, so with
  // motion enabled the chip stayed at its start state forever. Collect the
  // just-appended enter nodes and drop the class on the next frame so the
  // transition it declares actually runs to the base (opacity: 1) state.
  const enterNodes = [];

  const motionClass = motionClassName(motion);
  const center = el('g', {
    id: 'project-focus-node',
    class: `map-hit map-project-node${motionClass}`,
    'data-hit-layer': 'hub',
    'data-rel-path': project.relPath,
    'data-motion': (motion && motion.stroke && motion.stroke !== 'none') ? motion.stroke : null,
  });
  center.appendChild(el('circle', { cx: 0, cy: 0, r: 50, class: 'map-hub-disc' }));
  center.appendChild(el('text', { x: 0, y: 6, class: 'map-hub-label', 'text-anchor': 'middle' }, truncateLotLabel(project.name || project.relPath, 18)));
  layer.appendChild(center);

  const reduceMotion = prefersReducedMotion();
  const positions = ringPositions(branches.length, BRANCH_RADIUS);
  branches.forEach((branch, i) => {
    const { x, y } = positions[i];
    const angle = Math.atan2(y, x);
    const isExpanded = expandedBranch === branch.key;
    const flashing = !reduceMotion && flashBranches.includes(branch.key);
    const ticking = !reduceMotion && tickBranches.includes(branch.key);
    const chip = el('g', {
      class: `map-hit map-branch-chip map-branch-${branch.key}${isExpanded ? ' is-expanded' : ''} is-${branch.state}${flashing ? ' is-flash' : ''}`,
      transform: `translate(${x.toFixed(2)},${y.toFixed(2)})`,
      tabindex: '0', role: 'button',
      'aria-label': `${branch.label}, ${branch.summary}${isExpanded ? ', expanded' : ''}`,
      'aria-expanded': isExpanded ? 'true' : 'false',
      'data-hit-layer': 'branch', 'data-branch': branch.key,
      id: `map-branch-${branch.key}`,
    });
    chip.appendChild(el('rect', { x: -60, y: -22, width: 120, height: 44, rx: 8, class: 'map-branch-plate' }));
    chip.appendChild(el('text', { x: 0, y: -3, class: 'map-branch-label', 'text-anchor': 'middle' }, branch.label));
    chip.appendChild(el('text', { x: 0, y: 14, class: `map-branch-summary${ticking ? ' is-tick' : ''}`, 'text-anchor': 'middle' }, truncateLotLabel(branch.summary, 22)));
    layer.appendChild(chip);

    if (isExpanded && branch.items && branch.items.length > 0) {
      const shown = branch.items.slice(0, BRANCH_ITEM_MAX_SHOWN);
      const extra = branch.items.length - shown.length;
      const count = shown.length + (extra > 0 ? 1 : 0);
      const start = angle - BRANCH_ANGLE_SPAN / 2;
      const step = count > 1 ? BRANCH_ANGLE_SPAN / (count - 1) : 0;
      shown.forEach((item, idx) => {
        const a = count > 1 ? start + step * idx : angle;
        const ix = Math.cos(a) * (BRANCH_RADIUS + BRANCH_ITEM_RADIUS);
        const iy = Math.sin(a) * (BRANCH_RADIUS + BRANCH_ITEM_RADIUS);
        // Canvas and sidebar share one selection (FOCUSED_PROJECT §Rules) —
        // the chip for the item named by MapViewState.item carries the same
        // is-selected/aria-current the sidebar list marks it with.
        const isSelected = Boolean(selectedItem) && selectedItem.branch === branch.key && String(selectedItem.id) === String(item.id);
        const node = el('g', {
          class: `map-hit map-branch-item${isSelected ? ' is-selected' : ''}${reduceMotion ? '' : ' map-branch-item-enter'}`,
          transform: `translate(${ix.toFixed(2)},${iy.toFixed(2)})`,
          tabindex: '0', role: 'button',
          'aria-label': `${item.label}${item.detail ? ', ' + item.detail : ''}${isSelected ? ', selected' : ''}`,
          'aria-current': isSelected ? 'true' : null,
          'data-hit-layer': 'branch-item', 'data-branch': branch.key, 'data-item-id': String(item.id),
        });
        node.appendChild(el('rect', { x: -50, y: -16, width: 100, height: 32, rx: 6, class: 'map-branch-item-plate' }));
        node.appendChild(el('text', { x: 0, y: 4, class: 'map-branch-item-label', 'text-anchor': 'middle' }, truncateLotLabel(item.label, 16)));
        layer.appendChild(node);
        if (!reduceMotion) enterNodes.push(node);
      });
      if (extra > 0) {
        const a = count > 1 ? start + step * (count - 1) : angle;
        const ix = Math.cos(a) * (BRANCH_RADIUS + BRANCH_ITEM_RADIUS);
        const iy = Math.sin(a) * (BRANCH_RADIUS + BRANCH_ITEM_RADIUS);
        const node = el('g', {
          class: `map-hit map-branch-item map-branch-item-more${reduceMotion ? '' : ' map-branch-item-enter'}`,
          transform: `translate(${ix.toFixed(2)},${iy.toFixed(2)})`,
          tabindex: '0', role: 'button',
          'aria-label': `${extra} more in ${branch.label} — see the sidebar list`,
          'data-hit-layer': 'branch-more', 'data-branch': branch.key,
        });
        node.appendChild(el('rect', { x: -50, y: -16, width: 100, height: 32, rx: 6, class: 'map-branch-item-plate' }));
        node.appendChild(el('text', { x: 0, y: 4, class: 'map-branch-item-label', 'text-anchor': 'middle' }, `+${extra} more`));
        layer.appendChild(node);
        if (!reduceMotion) enterNodes.push(node);
      }
    }
  });

  if (enterNodes.length > 0) {
    requestAnimationFrame(() => {
      enterNodes.forEach(node => node.classList.remove('map-branch-item-enter'));
    });
  }
}

export function clearProjectFocus(world) {
  const layer = world.querySelector('#project-focus-layer');
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
  truncateLotLabel,
  DIG_LABEL_MAX,
  LOT_FOLDER_LABEL_MAX,
  LOT_FILE_LABEL_MAX,
  HUB_FOLDER_STAGGER_MIN,
  HUB_FILE_STAGGER_MIN,
  HUB_MULTI_ORBIT_MIN,
  HUB_INNER_ORBIT_RATIO,
  FOLDER_ARC_PX,
  FILE_ARC_PX,
};
