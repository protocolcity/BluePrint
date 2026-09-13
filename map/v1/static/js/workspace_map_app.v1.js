// workspace_map_app.v1.js — thin V1 host.
//
// Wires: snapshot fetch (map-tree) → paint (map-paint) → hit routing
// (map-hit-router) → view state (view-state) → reader (md-viewer).
//
// Project context consumes the shared operations projection. No scheduler or
// independent work-state cache belongs in this host.
//
// Load order: this file is the entry. All modules are loaded as ES modules.

import { createViewState } from './view-state.js';
import { createMapTree } from './map-tree.js';
import {
  ensureLayers, paintHub, paintLots, paintDigIn, clearDigIn, fitTransform,
  paintProjectFocus,
} from './map-paint.js';
import { createHitRouter } from './map-hit-router.js';
import { createMdViewer } from './md-viewer.js';
import { buildBranches, branchLabel } from './project-focus.js';

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
  // Fixed framing for the project-focus canvas (center + branch ring +
  // item fan) — the layout doesn't grow with content, so the camera never
  // has to re-fit while a project is in focus (Rule: "preserve camera").
  projectFocusRadius: 360,
  remoteEndpoint: '/api/remote-activity',
};

function indexNodeState(projects) {
  const map = {};
  for (const project of projects || []) {
    if (project && project.folder) {
      map[project.folder] = {
        open: project.open || 0,
        attention: project.attention || 0,
        working: project.working || 0,
        state: project.state || 'unavailable',
      };
    }
  }
  return map;
}

let nodeState = {};
let paintNodeState = null;
document.addEventListener('bp:map-operations', event => {
  nodeState = indexNodeState(event.detail && event.detail.projects);
  if (paintNodeState) paintNodeState();
});

export async function boot(opts = {}) {
  const cfg = { ...CONFIG, ...opts };
  const stage = document.getElementById(cfg.stageId);
  const world = document.getElementById(cfg.worldId);
  if (!stage || !world) throw new Error('map-v1: stage/world elements missing');

  ensureLayers(world);

  const initial = new URLSearchParams(location.search);
  let restoring = true;
  const viewState = createViewState();
  const tree = createMapTree({ fetcher: opts.fetcher || fetch, endpoints: opts.endpoints });
  const fetchImpl = opts.fetcher || fetch;
  const remoteEndpoint = (opts.endpoints && opts.endpoints.remote) || cfg.remoteEndpoint;

  // Work/Agents come from the shared operations projection (map-shell.js
  // dispatches `bp:map-operations` after its own /api/operations fetch);
  // Delivery comes from the remote-activity cache. Both are read-only
  // snapshots — project-focus.js composes the branches, never this host.
  let latestOperations = null;
  let latestRemote = null;
  let lastBranches = [];
  async function refreshRemote() {
    try {
      const res = await fetchImpl(remoteEndpoint, { headers: { accept: 'application/json' } });
      latestRemote = res && res.ok ? await res.json() : null;
    } catch (_) { latestRemote = null; }
    scheduleRepaint();
  }
  document.addEventListener('bp:map-operations', event => {
    latestOperations = event.detail || null;
    refreshRemote();
  });
  const viewer = createMdViewer({
    fetcher: opts.fetcher || fetch,
    endpoint: (opts.endpoints && opts.endpoints.file) || '/api/file',
    onClose: () => { syncUrl(); scheduleRepaint(); },
  });
  viewer.mount();

  function syncUrl() {
    if (restoring) return;
    const url = new URL(location.href);
    const snap = viewState.snapshot();
    const path = snap.dig?.relPath;
    const md = viewer.currentPath();
    if (path) url.searchParams.set('path', path); else url.searchParams.delete('path');
    if (md) url.searchParams.set('md', md); else url.searchParams.delete('md');
    // FOCUSED_PROJECT §Rules — "URL carries project, branch and item" so
    // back/forward, refresh and the reader's return restore the same view.
    if (snap.project) {
      url.searchParams.set('project', snap.project.relPath);
    } else {
      url.searchParams.delete('project');
    }
    if (snap.branch) url.searchParams.set('branch', snap.branch); else url.searchParams.delete('branch');
    if (snap.item) url.searchParams.set('item', String(snap.item.id)); else url.searchParams.delete('item');
    history.replaceState(history.state, '', '/map' + url.search + url.hash);
  }
  function currentMapUrl() { return '/map' + location.search; }
  function withReturnTo(href) {
    const sep = href.includes('?') ? '&' : '?';
    return href + sep + 'return_to=' + encodeURIComponent(currentMapUrl());
  }
  function openPaper(path, options) {
    const opening = viewer.open(path, options);
    syncUrl();
    return opening;
  }

  const hitRouter = createHitRouter({
    isMdViewerOpen: () => viewer.isOpen(),
  });

  // Camera state — snap only. No easing (Glass §Empty pan and zoom).
  const camera = { x: 0, y: 0, k: 1 };
  let page = 0;
  const pageSize = 12;
  let pageNodes = [];
  // Last outer radius reported by paintLots; the folder ring widens when
  // dense (see computeHubLayout), and applyCamera has to fit against the
  // actual outer radius or a dense hub gets clipped at the edges.
  let currentOuterRadius = cfg.radius;

  function applyCamera() {
    const rect = stage.getBoundingClientRect();
    const inset = rect.width > 700 ? 304 : 0;
    const sceneWidth = Math.max(1, rect.width - inset);
    const base = fitTransform(sceneWidth, rect.height - 110, { radius: currentOuterRadius });
    world.setAttribute(
      'transform',
      `translate(${inset},50) ${base} translate(${camera.x.toFixed(2)},${camera.y.toFixed(2)}) scale(${camera.k.toFixed(3)})`,
    );
  }

  // Keyboard focus survives a repaint (Rule: "Content updates preserve …
  // keyboard focus") even though paint*() functions replaceChildren() the
  // SVG groups they own — capture the focused hit's identity, repaint, then
  // find and refocus its successor node.
  function withFocusPreserved(fn) {
    const active = document.activeElement;
    const ds = active && active.dataset;
    const key = ds && (ds.branch || ds.relPath) ? { ...ds } : null;
    fn();
    if (!key) return;
    let selector = null;
    if (key.itemId) selector = `[data-branch="${key.branch}"][data-item-id="${key.itemId}"]`;
    else if (key.branch) selector = `[data-branch="${key.branch}"]`;
    else if (key.relPath) selector = `[data-rel-path="${key.relPath}"]`;
    if (!selector) return;
    try {
      const match = world.querySelector(selector);
      if (match && typeof match.focus === 'function') match.focus();
    } catch (_) { /* selector built from live data; a mismatch is a no-op */ }
  }

  function currentBranches(snap) {
    return snap.project ? buildBranches(snap.project, latestOperations, latestRemote) : [];
  }

  function repaint() { withFocusPreserved(repaintInner); }

  function repaintInner() {
    const snap = viewState.snapshot();
    if (snap.project) {
      lastBranches = currentBranches(snap);
      world.querySelector('#hub').style.display = 'none';
      world.querySelector('#lots').style.display = 'none';
      if (snap.branch !== 'papers') clearDigIn(world);
      paintProjectFocus(world, { project: snap.project, branches: lastBranches, expandedBranch: snap.branch });
      currentOuterRadius = cfg.projectFocusRadius;
      applyCamera();
      renderTrail();
      renderProjectPanel(snap);
      // The sidebar's folder browser (#map-browser-list) is also the only
      // surface at 400px where the canvas is hidden — keep it live while a
      // project is focused, especially once Papers reuses the dig machinery
      // (mode: 'root') so its contents actually reflect the expanded branch.
      renderBrowser();
      return;
    }
    lastBranches = [];
    world.querySelector('#project-focus-layer')?.replaceChildren();
    world.querySelector('#hub').style.display = '';
    // Selected top-level lot = the root of the current dig trail. Passing
    // its relPath into paintLots lights the 2px accent focus ring on the
    // matching lot so "digging into X" is visually anchored to X.
    const selectedRelPath = snap.trail.length > 0 ? snap.trail[0].relPath : null;
    paintHub(world, snap.dig || tree.binder);
    world.querySelector('#lots').style.display = snap.dig ? 'none' : '';
    const layout = paintLots(world, tree.topLots(snap.filters).slice(page * pageSize, (page + 1) * pageSize), { radius: cfg.radius, selectedRelPath, nodeState });
    currentOuterRadius = (layout && Number.isFinite(layout.outerRadius))
      ? Math.max(cfg.radius, layout.outerRadius)
      : cfg.radius;
    if (!snap.dig) { clearDigIn(world); }
    applyCamera();
    renderTrail();
    renderProjectPanel(snap);
    renderBrowser();
  }

  // Selecting a project focuses the canvas on it (FOCUSED_PROJECT §Rules:
  // "Selecting a project replaces the canvas; it never layers every
  // project behind its children"). A fresh focus always starts collapsed —
  // no branch open — so the four chips are the first thing the person sees.
  function selectProjectView(node) {
    page = 0; camera.x = 0; camera.y = 0; camera.k = 1;
    viewState.selectProject(node);
    scheduleRepaint();
  }

  function clearProjectFocusView() {
    camera.x = 0; camera.y = 0; camera.k = 1;
    viewState.clearProject();
    scheduleRepaint();
  }

  // One branch open at a time (FOCUSED_PROJECT §Rules: "Opening a branch
  // collapses the previously open one"). Papers keeps the real folder tree,
  // so opening it reuses the existing dig machinery scoped to the project's
  // own folder; the other three branches are flat, already-fetched lists.
  async function toggleBranchView(key) {
    const wasExpanded = viewState.snapshot().branch === key;
    viewState.setBranch(key);
    if (!wasExpanded && key === 'papers') {
      const project = viewState.snapshot().project;
      if (project) await digInto(project, { mode: 'root' });
      return;
    }
    if (wasExpanded && key === 'papers') clearDigIn(world);
    scheduleRepaint();
  }

  function renderProjectPanel(snap) {
    const panel = document.getElementById('map-project-panel');
    if (!panel) return;
    if (!snap.project) { panel.hidden = true; return; }
    panel.hidden = false;
    const nameEl = document.getElementById('map-project-name');
    if (nameEl) nameEl.textContent = snap.project.name;
    const buttonsHost = document.getElementById('map-branch-buttons');
    if (buttonsHost) {
      buttonsHost.replaceChildren();
      for (const branch of lastBranches) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.id = `map-branch-btn-${branch.key}`;
        btn.className = `is-${branch.state}`;
        btn.setAttribute('aria-expanded', snap.branch === branch.key ? 'true' : 'false');
        btn.textContent = `${branch.label} — ${branch.summary}`;
        btn.addEventListener('click', () => toggleBranchView(branch.key));
        buttonsHost.appendChild(btn);
      }
    }
    const itemsHost = document.getElementById('map-branch-items');
    if (itemsHost) {
      itemsHost.replaceChildren();
      if (snap.branch === 'papers') {
        itemsHost.textContent = 'Browse the folder list below.';
      } else if (snap.branch) {
        const branch = lastBranches.find(b => b.key === snap.branch);
        const items = (branch && branch.items) || [];
        if (items.length === 0) {
          itemsHost.textContent = branch ? branch.summary : '';
        } else {
          for (const item of items) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.dataset.branch = snap.branch;
            btn.dataset.itemId = String(item.id);
            const label = document.createElement('span');
            label.textContent = item.label;
            btn.appendChild(label);
            if (item.detail) {
              const detail = document.createElement('span');
              detail.className = 'map-branch-item-detail';
              detail.textContent = item.detail;
              btn.appendChild(detail);
            }
            btn.addEventListener('click', () => { viewState.setItem(item); scheduleRepaint(); });
            itemsHost.appendChild(btn);
          }
        }
      }
    }
    renderItemDetail(snap);
  }

  function renderItemDetail(snap) {
    const box = document.getElementById('map-item-detail');
    if (!box) return;
    if (!snap.item) { box.hidden = true; box.replaceChildren(); return; }
    box.hidden = false;
    box.replaceChildren();
    const heading = document.createElement('strong');
    heading.textContent = snap.item.label;
    box.append(heading);
    if (snap.item.detail) {
      const p = document.createElement('p');
      p.textContent = snap.item.detail;
      box.append(p);
    }
    if (snap.item.href) {
      const a = document.createElement('a');
      a.textContent = 'Open';
      const external = /^https?:\/\//.test(snap.item.href);
      a.href = external ? snap.item.href : withReturnTo(snap.item.href);
      if (external) { a.target = '_blank'; a.rel = 'noopener'; }
      box.append(a);
    }
  }

  let repaintScheduled = false;
  let browseVersion = 0;
  let browserKey = null;
  function visibleChildren(nodes) { return nodes.filter(node => (node.isDir || node.hasMd) && (viewState.snapshot().filters.hidden || !node.hidden)); }
  async function renderBrowser() {
    const list = document.getElementById('map-browser-list');
    if (!list) return;
    const snap = viewState.snapshot();
    document.dispatchEvent(new CustomEvent('bp:map-location', {detail:{path:snap.dig?.relPath || ''}}));
    const key = JSON.stringify([snap.dig?.relPath || '', snap.filters, page]);
    if (key === browserKey) return;
    const version = ++browseVersion;
    document.getElementById('map-browser-path').textContent = snap.dig?.relPath || tree.binder?.name || 'Workspace';
    try {
      const nodes = snap.dig ? visibleChildren(await tree.childrenAt(snap.dig.relPath)) : tree.topLots(snap.filters);
      if (version !== browseVersion) return;
      browserKey = key;
      pageNodes = nodes;
      const pageCount = Math.max(1, Math.ceil(nodes.length / pageSize));
      const controls = document.getElementById('map-page-controls');
      if (controls) {
        controls.hidden = pageCount <= 1;
        document.getElementById('map-page-status').textContent = `${page + 1} / ${pageCount}`;
        document.getElementById('map-page-prev').disabled = page === 0;
        document.getElementById('map-page-next').disabled = page >= pageCount - 1;
      }
      if (snap.dig) { clearDigIn(world); paintDigIn(world, snap.dig, nodes.slice(page * pageSize, (page + 1) * pageSize), {radius:220}); }
      list.replaceChildren();
      let lastGroup = '';
      const orderedNodes = [...nodes.filter(node => node.isDir), ...nodes.filter(node => !node.isDir && node.hasMd)];
      for (const node of orderedNodes) {
        const group = node.isDir ? (snap.dig ? 'Folders' : 'Projects') : 'Papers';
        if (group !== lastGroup) {
          const heading = document.createElement('h3');
          heading.className = 'map-browser-group'; heading.textContent = group; list.append(heading); lastGroup = group;
        }
        const button = document.createElement('button');
        button.type = 'button'; button.setAttribute('aria-label', (node.isDir ? 'Folder · ' : 'Paper · ') + node.name);
        const icon = document.createElement('span'); icon.className = 'map-browser-icon'; icon.setAttribute('aria-hidden', 'true');
        icon.innerHTML = node.isDir
          ? '<svg viewBox="0 0 20 20"><path d="M2 5h6l2 2h8v10H2z"/></svg>'
          : '<svg viewBox="0 0 20 20"><path d="M5 2h7l4 4v12H5zM12 2v5h4M8 10h5M8 13h5"/></svg>';
        const label = document.createElement('span'); label.textContent = node.name;
        button.append(icon, label);
        const state = node.isDir && !snap.dig ? nodeState[node.relPath] : null;
        if (state) {
          const counts = document.createElement('span');
          counts.className = 'map-browser-counts';
          counts.textContent = state.state && state.state !== 'available'
            ? 'read-only'
            : `${state.open} · ${state.attention} · ${state.working}`;
          button.append(counts);
        }
        button.addEventListener('click', async () => {
          try {
            if (node.isDir) await digInto(node, {mode:snap.dig ? 'nest' : 'root'});
            else await openPaper(node.relPath, {label:node.name});
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
  paintNodeState = scheduleRepaint;

  async function digInto(node, { mode = 'root' } = {}) {
    if (!node || !node.relPath) return;
    page = 0; camera.x = 0; camera.y = 0; camera.k = 1;
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
    const kids = visibleChildren(await tree.childrenAt(node.relPath));
    if (viewState.snapshot().dig?.relPath !== node.relPath) return;
    // Belt-and-braces: clear the fan layer before every paint so a racing
    // second click cannot leave A's ring layered under B's.
    clearDigIn(world);
    paintDigIn(world, node, kids.slice(0, pageSize), { radius: 220 });
    renderTrail();
  }

  function resetView() {
    page = 0;
    viewState.clearDig();
    clearDigIn(world);
    camera.x = 0; camera.y = 0; camera.k = 1;
    applyCamera();
    renderTrail();
    // Trail cleared → drop the .is-selected ring on the previous top lot.
    scheduleRepaint();
  }

  function renderTrail() {
    syncUrl();
    const el = document.getElementById(cfg.chromeIds.trail);
    if (!el) return;
    const snap = viewState.snapshot();
    // FOCUSED_PROJECT §Rules — "Sidebar, canvas and breadcrumb share one
    // selection." A focused project always shows Home › Project [› Branch
    // [› Item]], not the raw Papers dig trail (that only surfaces once the
    // Papers branch is the expanded one, as its own nested crumbs below).
    if (snap.project && snap.branch !== 'papers') {
      el.hidden = false;
      el.replaceChildren();
      const crumbs = [
        { label: tree.binder?.name || 'hub', onClick: clearProjectFocusView },
        { label: snap.project.name, onClick: () => { viewState.clearBranch(); scheduleRepaint(); } },
      ];
      if (snap.branch) crumbs.push({ label: branchLabel(snap.branch), onClick: () => { viewState.clearItem(); scheduleRepaint(); } });
      if (snap.item) crumbs.push({ label: snap.item.label, onClick: null });
      crumbs.forEach((crumb, i) => {
        if (i > 0) {
          const sep = document.createElement('span');
          sep.className = 'map-trail-sep';
          sep.textContent = '›';
          el.appendChild(sep);
        }
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'map-trail-crumb' + (i === 0 ? ' map-trail-home' : '');
        btn.textContent = crumb.label;
        if (crumb.onClick) btn.addEventListener('click', crumb.onClick); else btn.disabled = true;
        el.appendChild(btn);
      });
      return;
    }
    const trail = viewState.snapshot().trail;
    if (trail.length === 0) { el.replaceChildren(); el.hidden = true; return; }
    el.hidden = false;
    el.replaceChildren();
    const home = document.createElement('button');
    home.type = 'button';
    home.className = 'map-trail-crumb map-trail-home';
    home.textContent = tree.binder?.name || 'hub';
    home.addEventListener('click', snap.project ? clearProjectFocusView : resetView);
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
        page = 0;
        while (viewState.snapshot().trail.length > i + 1) viewState.popDig();
        const top = viewState.snapshot().dig;
        clearDigIn(world);
        if (top) {
          const kids = visibleChildren(await tree.childrenAt(top.relPath));
          clearDigIn(world);
          paintDigIn(world, top, kids.slice(0, pageSize), { radius: 220 });
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
        // The project-focus center node also reports layer 'hub' — clicking
        // it, like the old hub, always returns to the workspace.
        if (viewState.snapshot().project) { clearProjectFocusView(); return; }
        if (viewState.snapshot().dig) { resetView(); return; }
        // hub click on cold canvas = repaint anchor; no-op verb.
        return;
      }
      case 'branch': {
        toggleBranchView(hit.root.getAttribute('data-branch'));
        return;
      }
      case 'branch-item': {
        const key = hit.root.getAttribute('data-branch');
        const itemId = hit.root.getAttribute('data-item-id');
        const branch = lastBranches.find(b => b.key === key);
        const item = itemId && branch ? branch.items.find(it => String(it.id) === itemId) : null;
        if (item) { viewState.setItem(item); scheduleRepaint(); }
        // The "+N more" chip carries no item id — the sidebar already lists
        // every item, so there is nothing further to do here.
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
          openPaper(relPath, { label: name });
          return;
        }
        if (!isDir) return; // non-md file: no verb in V1
        // hit.layer semantics pin the dig grammar:
        //   'lots'   → root-ring click; focus this project (FOCUSED_PROJECT)
        //   'dig-in' → child inside the current fan; PUSH trail (nested)
        const mode = hit.layer === 'dig-in' ? 'nest' : 'root';
        if (mode === 'root') { selectProjectView({ relPath, name, hasMd }); return; }
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
      page = 0;
      viewState.setFilter(key, box.checked);
      scheduleRepaint();
    });
  }

  // Reset button.
  const resetBtn = document.getElementById(cfg.chromeIds.reset);
  if (resetBtn) resetBtn.addEventListener('click', resetView);

  const projectBackBtn = document.getElementById('map-project-back');
  if (projectBackBtn) projectBackBtn.addEventListener('click', clearProjectFocusView);

  // Back on Backspace.
  document.addEventListener('keydown', async (ev) => {
    if (viewer.isOpen()) return;
    if (ev.key !== 'Backspace') return;
    if (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA')) return;
    ev.preventDefault();
    page = 0;
    const popped = viewState.popDig();
    clearDigIn(world);
    if (popped) {
      const kids = visibleChildren(await tree.childrenAt(popped.relPath));
      clearDigIn(world);
      paintDigIn(world, popped, kids.slice(0, pageSize), { radius: 220 });
    }
    renderTrail();
    // Trail root may have changed (or gone empty) → refresh the focus ring.
    scheduleRepaint();
  });

  for (const [id, delta] of [['map-page-prev', -1], ['map-page-next', 1]]) {
    document.getElementById(id)?.addEventListener('click', () => {
      page = Math.max(0, Math.min(Math.ceil(pageNodes.length / pageSize) - 1, page + delta));
      scheduleRepaint();
    });
  }
  stage.addEventListener('keydown', ev => {
    if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches('.map-hit')) {
      ev.preventDefault(); ev.target.dispatchEvent(new MouseEvent('click', {bubbles:true}));
    }
  });
  window.addEventListener('resize', applyCamera);
  await tree.load();
  await refreshRemote();
  repaint();
  if (initial.get('project')) {
    const projectPath = initial.get('project');
    // Deep-link boot only carries the relPath in the URL — resolve hasMd
    // from the already-loaded tree so papersBranch reports correctly on
    // first paint instead of always reading "empty" (no state.project.hasMd).
    const treeLot = tree.snapshot().lots.find(lot => lot.relPath === projectPath);
    selectProjectView({
      relPath: projectPath,
      name: (treeLot && treeLot.name) || projectPath.split('/').pop(),
      hasMd: treeLot ? treeLot.hasMd : false,
    });
    const branch = initial.get('branch');
    if (branch) {
      await toggleBranchView(branch);
      const itemId = initial.get('item');
      if (itemId) {
        const found = lastBranches.find(b => b.key === branch);
        const item = found && found.items.find(it => String(it.id) === itemId);
        if (item) { viewState.setItem(item); scheduleRepaint(); }
      }
    }
  } else if(initial.get('path')) {
    let relative='';
    for(const part of initial.get('path').split('/').filter(Boolean)) {
      relative=relative ? relative+'/'+part : part;
      await digInto({relPath:relative,name:part},{mode:relative.includes('/')?'nest':'root'});
    }
  }
  if(initial.get('md'))await openPaper(initial.get('md'),{label:initial.get('md').split('/').pop()});
  restoring = false;
  syncUrl();

  return {
    // Exposed for smoke tests + dogfood introspection.
    viewState, tree, viewer, hitRouter,
    repaint, resetView, digInto,
    selectProjectView, clearProjectFocusView, toggleBranchView,
    get lastBranches() { return lastBranches; },
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
