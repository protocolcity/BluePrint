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

  function applyCamera() {
    const rect = stage.getBoundingClientRect();
    const base = fitTransform(rect.width, rect.height, { radius: cfg.radius });
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
    paintLots(world, tree.topLots(snap.filters), { radius: cfg.radius, selectedRelPath });
    if (!snap.dig) { clearDigIn(world); }
    applyCamera();
    renderTrail();
  }

  let repaintScheduled = false;
  function scheduleRepaint() {
    if (repaintScheduled) return;
    repaintScheduled = true;
    Promise.resolve().then(() => { repaintScheduled = false; repaint(); });
  }

  async function digInto(node) {
    if (!node || !node.relPath) return;
    viewState.setDig(node);
    // Re-paint the lot ring so the top-level lot picks up the .is-selected
    // focus ring (paintLots reads selectedRelPath from the trail root).
    scheduleRepaint();
    const kids = await tree.childrenAt(node.relPath);
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
        if (top) {
          const kids = await tree.childrenAt(top.relPath);
          paintDigIn(world, top, kids, { radius: cfg.digRadius });
        } else {
          clearDigIn(world);
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
        digInto({ relPath, name });
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
    if (popped) {
      const kids = await tree.childrenAt(popped.relPath);
      paintDigIn(world, popped, kids, { radius: cfg.digRadius });
    } else {
      clearDigIn(world);
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
