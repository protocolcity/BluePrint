// workspace_map_app.v1.js — thin V1 host.
//
// Wires: snapshot fetch (map-tree) → paint (map-paint) → hit routing
// (map-hit-router) → view state (view-state) → reader (md-viewer).
//
// Glass §Non-goals: host stays under ~2k LOC; no cinema, no store polling,
// no live loop, no second projection. If you find yourself importing an
// inspect-* rail, an agents-panel, or a WO tape module — you are outside V1.
//
// Load order: this file is the entry. All modules are loaded as ES modules.

import { createViewState } from './view-state.js';
import { createMapTree } from './map-tree.js';
import {
  ensureLayers, paintHub, paintLots, paintDigIn, clearDigIn, fitTransform,
} from './map-paint.js';
import { createHitRouter } from './map-hit-router.js';
import { createMdViewer } from './md-viewer.js';

const CONFIG = {
  worldId: 'world',
  stageId: 'map-stage',
  chromeIds: {
    trail: 'map-dig-trail',
    reset: 'map-reset',
    viewOptions: 'map-view-options',
    filterManaged: 'flt-managed',
    filterUnmanaged: 'flt-unmanaged',
    filterHidden: 'flt-hidden',
  },
  radius: 220,
  digRadius: 130,
  minZoom: 0.5,
  maxZoom: 4,
};

export async function boot(opts = {}) {
  const cfg = { ...CONFIG, ...opts };
  const stage = document.getElementById(cfg.stageId);
  const world = document.getElementById(cfg.worldId);
  if (!stage || !world) throw new Error('map-v1: stage/world elements missing');

  ensureLayers(world);

  const viewState = createViewState();
  const tree = createMapTree({ fetcher: opts.fetcher || fetch, endpoints: opts.endpoints });
  const viewer = createMdViewer({
    fetcher: opts.fetcher || fetch,
    endpoint: (opts.endpoints && opts.endpoints.file) || '/api/file',
    onClose: () => scheduleRepaint(),
  });
  viewer.mount();

  const hitRouter = createHitRouter({
    isMdViewerOpen: () => viewer.isOpen(),
  });

  // Camera state — snap only. No easing (Glass §Empty pan and zoom).
  const camera = { x: 0, y: 0, k: 1 };
  // Last outer radius reported by paintLots; the folder ring widens when
  // dense (see computeHubLayout), and applyCamera has to fit against the
  // actual outer radius or a dense hub gets clipped at the edges.
  let currentOuterRadius = cfg.radius;

  function applyCamera() {
    const rect = stage.getBoundingClientRect();
    const base = fitTransform(rect.width, rect.height, { radius: currentOuterRadius });
    world.setAttribute(
      'transform',
      `${base} translate(${camera.x.toFixed(2)},${camera.y.toFixed(2)}) scale(${camera.k.toFixed(3)})`,
    );
  }

  function repaint() {
    const snap = viewState.snapshot();
    // Selected top-level lot = the root of the current dig trail. Passing
    // its relPath into paintLots lights the 2px accent focus ring on the
    // matching lot so "digging into X" is visually anchored to X.
    const selectedRelPath = snap.trail.length > 0 ? snap.trail[0].relPath : null;
    paintHub(world, tree.binder);
    const layout = paintLots(world, tree.topLots(snap.filters), { radius: cfg.radius, selectedRelPath });
    currentOuterRadius = (layout && Number.isFinite(layout.outerRadius))
      ? Math.max(cfg.radius, layout.outerRadius)
      : cfg.radius;
    if (!snap.dig) { clearDigIn(world); }
    applyCamera();
    renderTrail();
    renderBrowser();
  }

  let repaintScheduled = false;
  let browseVersion = 0;
  let browserKey = null;
  async function renderBrowser() {
    const list = document.getElementById('map-browser-list');
    if (!list) return;
    const version = ++browseVersion;
    const snap = viewState.snapshot();
    const key = JSON.stringify([snap.dig?.relPath || '', snap.filters]);
    if (key === browserKey) return;
    document.getElementById('map-browser-path').textContent = snap.dig?.relPath || tree.binder?.name || 'Workspace';
    try {
      const nodes = snap.dig ? await tree.childrenAt(snap.dig.relPath) : tree.topLots(snap.filters);
      if (version !== browseVersion) return;
      browserKey = key;
      list.replaceChildren();
      for (const node of nodes) {
        if (!node.isDir && !node.hasMd) continue;
        const button = document.createElement('button');
        button.type = 'button'; button.textContent = (node.isDir ? 'Folder · ' : 'Paper · ') + node.name;
        button.addEventListener('click', async () => {
          try {
            if (node.isDir) await digInto(node, {mode:snap.dig ? 'nest' : 'root'});
            else await viewer.open(node.relPath, {label:node.name});
          } catch (error) { document.getElementById('map-browser-path').textContent = 'Unable to open this folder.'; }
        });
        list.append(button);
      }
      if (!list.children.length) list.textContent = 'No folders or readable Markdown papers here.';
    } catch (error) { if(version === browseVersion)list.textContent = 'Folder source unavailable.'; }
  }
  function scheduleRepaint() {
    if (repaintScheduled) return;
    repaintScheduled = true;
    Promise.resolve().then(() => { repaintScheduled = false; repaint(); });
  }

  async function digInto(node, { mode = 'root' } = {}) {
    if (!node || !node.relPath) return;
    // Root-level dig (sibling of hub / sibling of the current dig root) must
    // REPLACE the trail — clicking B after A should not nest B under A. Only
    // a nested click (verb from #dig-in-layer child) pushes onto the trail.
    if (mode === 'nest') {
      viewState.setDig(node);
    } else {
      viewState.replaceDig(node);
    }
    // Re-paint the lot ring so the top-level lot picks up the .is-selected
    // focus ring (paintLots reads selectedRelPath from the trail root).
    scheduleRepaint();
    const kids = await tree.childrenAt(node.relPath);
    if (viewState.snapshot().dig?.relPath !== node.relPath) return;
    // Belt-and-braces: clear the fan layer before every paint so a racing
    // second click cannot leave A's ring layered under B's.
    clearDigIn(world);
    paintDigIn(world, node, kids, { radius: cfg.digRadius });
    renderTrail();
  }

  function resetView() {
    viewState.clearDig();
    clearDigIn(world);
    camera.x = 0; camera.y = 0; camera.k = 1;
    applyCamera();
    renderTrail();
    // Trail cleared → drop the .is-selected ring on the previous top lot.
    scheduleRepaint();
  }

  function renderTrail() {
    const el = document.getElementById(cfg.chromeIds.trail);
    if (!el) return;
    const trail = viewState.snapshot().trail;
    if (trail.length === 0) { el.replaceChildren(); el.hidden = true; return; }
    el.hidden = false;
    el.replaceChildren();
    const home = document.createElement('button');
    home.type = 'button';
    home.className = 'map-trail-crumb map-trail-home';
    home.textContent = tree.binder?.name || 'hub';
    home.addEventListener('click', resetView);
    el.appendChild(home);
    trail.forEach((entry, i) => {
      const sep = document.createElement('span');
      sep.className = 'map-trail-sep';
      sep.textContent = '›';
      el.appendChild(sep);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'map-trail-crumb';
      btn.textContent = entry.name;
      btn.addEventListener('click', async () => {
        while (viewState.snapshot().trail.length > i + 1) viewState.popDig();
        const top = viewState.snapshot().dig;
        clearDigIn(world);
        if (top) {
          const kids = await tree.childrenAt(top.relPath);
          clearDigIn(world);
          paintDigIn(world, top, kids, { radius: cfg.digRadius });
        }
        renderTrail();
        scheduleRepaint();
      });
      el.appendChild(btn);
    });
  }

  // Pointer routing — all hits go through the SoT (Glass §Hit-Layer SoT).
  stage.addEventListener('click', (ev) => {
    const hit = hitRouter.classify(ev.target);
    switch (hit.layer) {
      case 'md-viewer':
      case 'chrome':
        return; // owned elsewhere
      case 'hub': {
        if (viewState.snapshot().dig) { resetView(); return; }
        // hub click on cold canvas = repaint anchor; no-op verb.
        return;
      }
      case 'lots':
      case 'dig-in': {
        const root = hit.root;
        const relPath = root.getAttribute('data-rel-path');
        const name = root.getAttribute('data-name') || relPath;
        const isDir = root.getAttribute('data-is-dir') !== '0';
        const hasMd = root.getAttribute('data-has-md') === '1';
        if (!isDir && hasMd) {
          viewer.open(relPath, { label: name });
          return;
        }
        if (!isDir) return; // non-md file: no verb in V1
        // hit.layer semantics pin the dig grammar:
        //   'lots'   → root-ring click; REPLACE trail (sibling swap)
        //   'dig-in' → child inside the current fan; PUSH trail (nested)
        const mode = hit.layer === 'dig-in' ? 'nest' : 'root';
        digInto({ relPath, name }, { mode });
        return;
      }
      default:
        return; // empty — handled by pan drag below
    }
  });

  // Pan on empty. Glass §Empty pan and zoom.
  let dragging = null;
  stage.addEventListener('pointerdown', (ev) => {
    const hit = hitRouter.classify(ev.target);
    if (hit.layer !== 'empty') return;
    dragging = { sx: ev.clientX, sy: ev.clientY, cx: camera.x, cy: camera.y, id: ev.pointerId };
    try { stage.setPointerCapture(ev.pointerId); } catch (_) { /* jsdom / non-DOM env */ }
  });
  stage.addEventListener('pointermove', (ev) => {
    if (!dragging || dragging.id !== ev.pointerId) return;
    camera.x = dragging.cx + (ev.clientX - dragging.sx);
    camera.y = dragging.cy + (ev.clientY - dragging.sy);
    applyCamera();
  });
  const endDrag = (ev) => {
    if (!dragging || dragging.id !== ev.pointerId) return;
    dragging = null;
    try { stage.releasePointerCapture(ev.pointerId); } catch (_) { /* fine */ }
  };
  stage.addEventListener('pointerup', endDrag);
  stage.addEventListener('pointercancel', endDrag);

  // Zoom on wheel; clamp per Glass §Empty pan and zoom.
  stage.addEventListener('wheel', (ev) => {
    const hit = hitRouter.classify(ev.target);
    if (hit.layer === 'md-viewer' || hit.layer === 'chrome') return;
    ev.preventDefault();
    const factor = ev.deltaY < 0 ? 1.1 : 1 / 1.1;
    camera.k = Math.max(cfg.minZoom, Math.min(cfg.maxZoom, camera.k * factor));
    applyCamera();
  }, { passive: false });

  // View Options filter checkboxes — thin wire, no second store.
  wireFilter(cfg.chromeIds.filterManaged, 'managed');
  wireFilter(cfg.chromeIds.filterUnmanaged, 'unmanaged');
  wireFilter(cfg.chromeIds.filterHidden, 'hidden');
  function wireFilter(id, key) {
    const box = document.getElementById(id);
    if (!box) return;
    box.checked = viewState.snapshot().filters[key];
    box.addEventListener('change', () => {
      viewState.setFilter(key, box.checked);
      scheduleRepaint();
    });
  }

  // Reset button.
  const resetBtn = document.getElementById(cfg.chromeIds.reset);
  if (resetBtn) resetBtn.addEventListener('click', resetView);

  // Back on Backspace.
  document.addEventListener('keydown', async (ev) => {
    if (viewer.isOpen()) return;
    if (ev.key !== 'Backspace') return;
    if (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA')) return;
    ev.preventDefault();
    const popped = viewState.popDig();
    clearDigIn(world);
    if (popped) {
      const kids = await tree.childrenAt(popped.relPath);
      clearDigIn(world);
      paintDigIn(world, popped, kids, { radius: cfg.digRadius });
    }
    renderTrail();
    // Trail root may have changed (or gone empty) → refresh the focus ring.
    scheduleRepaint();
  });

  await tree.load();
  repaint();

  return {
    // Exposed for smoke tests + dogfood introspection.
    viewState, tree, viewer, hitRouter,
    repaint, resetView, digInto,
  };
}

if (typeof window !== 'undefined' && window.__MAP_V1_AUTOBOOT__ !== false) {
  document.addEventListener('DOMContentLoaded', () => {
    boot().catch(err => {
      console.error('[map-v1] boot failed', err);
      const stage = document.getElementById('map-stage');
      if (stage) stage.dataset.mapV1Error = err.message;
    });
  });
}
