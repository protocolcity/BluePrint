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
import { buildBranches, branchLabel, BRANCH_ITEM_LIMIT } from './project-focus.js';

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
let lastNodeStateJson = null;
let paintNodeState = null;
document.addEventListener('bp:map-operations', event => {
  const next = indexNodeState(event.detail && event.detail.projects);
  const json = JSON.stringify(next);
  // Identical reads must not repaint (Done-when: "Only actual evidence
  // changes receive brief feedback") — a poll that reports the same sibling
  // badges is a no-op, not a fresh repaint + re-triggered enter animation.
  if (json === lastNodeStateJson) return;
  lastNodeStateJson = json;
  nodeState = next;
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
  // A deep-linked ?item= can arrive before the branch it names has real
  // data (operations/remote snapshots load async, independently of the
  // boot sequence) — applyDeepLinkItem() re-tries against the always-fresh
  // currentBranches() (never the stale, repaint-only `lastBranches`) each
  // time either source updates, instead of only once at boot.
  let pendingDeepLinkItem = null;
  function applyDeepLinkItem(branch, itemId) {
    const found = currentBranches(viewState.snapshot()).find(b => b.key === branch);
    // Search the branch's full uncapped list (itemsAll), not the
    // BRANCH_ITEM_LIMIT-capped preview (items) — a shared/refreshed/back-
    // forward URL naming an item outside the sidebar/canvas preview must
    // still resolve, or pendingDeepLinkItem retries forever against the same
    // truncated slice.
    const item = found && (found.itemsAll || found.items).find(it => String(it.id) === itemId);
    if (item) {
      viewState.setItem(item);
      pendingDeepLinkItem = null;
      scheduleRepaint();
      return true;
    }
    pendingDeepLinkItem = { branch, itemId };
    return false;
  }
  function retryPendingDeepLinkItem() {
    if (!pendingDeepLinkItem) return;
    const snap = viewState.snapshot();
    if (snap.branch !== pendingDeepLinkItem.branch || snap.item) { pendingDeepLinkItem = null; return; }
    applyDeepLinkItem(pendingDeepLinkItem.branch, pendingDeepLinkItem.itemId);
  }
  // Both `latestOperations` and `latestRemote` are read-only external
  // snapshots, not a per-event trigger — a poll that reports the exact same
  // payload must not repaint (Done-when: "Only actual evidence changes
  // receive brief feedback"; identical reads must not re-run
  // repaintInner()/paintProjectFocus() or re-trigger the branch-item enter
  // animation). Gate scheduleRepaint() on a fingerprint of the combined data.
  let lastAppliedDataKey = null;
  function applyDataUpdate() {
    const key = JSON.stringify([latestOperations, latestRemote]);
    if (key === lastAppliedDataKey) return;
    lastAppliedDataKey = key;
    scheduleRepaint();
  }
  async function refreshRemote() {
    try {
      const res = await fetchImpl(remoteEndpoint, { headers: { accept: 'application/json' } });
      latestRemote = res && res.ok ? await res.json() : null;
    } catch (_) { latestRemote = null; }
    retryPendingDeepLinkItem();
    applyDataUpdate();
  }
  document.addEventListener('bp:map-operations', event => {
    latestOperations = event.detail || null;
    retryPendingDeepLinkItem();
    refreshRemote();
  });
  const viewer = createMdViewer({
    fetcher: opts.fetcher || fetch,
    endpoint: (opts.endpoints && opts.endpoints.file) || '/api/file',
    onClose: () => { syncUrl(); scheduleRepaint(); },
  });
  viewer.mount();

  // FOCUSED_PROJECT §Rules — "browser back/forward … restore it": a change
  // to the focused project/branch/item is a real navigation and needs its
  // own history entry; everything else syncUrl also carries (dig path, the
  // reader) keeps using replaceState as before, so paging/panning doesn't
  // spam the history stack.
  function projectNavKey(snap) {
    // Papers keeps digging deeper while the project stays focused/branch
    // stays 'papers' — without the dig path here each nested folder step
    // would only ever replaceState (nav key unchanged), so Back/Forward
    // would jump straight past every intermediate folder depth instead of
    // walking back up one segment at a time.
    const papersPath = snap.branch === 'papers' ? (snap.dig?.relPath || null) : null;
    return JSON.stringify([snap.project ? snap.project.relPath : null, snap.branch || null, snap.item ? String(snap.item.id) : null, papersPath]);
  }
  let lastNavKey = null;
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
    const dest = '/map' + url.search + url.hash;
    const navKey = projectNavKey(snap);
    if (navKey !== lastNavKey) {
      history.pushState(history.state, '', dest);
    } else {
      history.replaceState(history.state, '', dest);
    }
    lastNavKey = navKey;
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
  // keyboard focus") even though paint*() and renderBrowser() replaceChildren()
  // the groups/list they own — capture the focused hit's identity, rebuild,
  // then find and refocus its successor node. Shared by the SVG repaint and
  // the (possibly async) browser-list rebuild so a keyboard user browsing the
  // 400px list doesn't lose focus when badges or the dig scope change it.
  function captureFocusKey() {
    const active = document.activeElement;
    const ds = active && active.dataset;
    // The branch-item chip/button and the detail box's Open link share the
    // same branch+item-id (they name the same item); data-role disambiguates
    // which of them was actually focused so restoreFocus doesn't snap focus
    // from the Open link back onto the item chip/button after a repaint.
    if (ds && ds.itemId) {
      const role = ds.role ? `[data-role="${ds.role}"]` : '';
      return `[data-branch="${ds.branch}"][data-item-id="${ds.itemId}"]${role}`;
    }
    if (ds && ds.branch) return `[data-branch="${ds.branch}"]`;
    if (ds && ds.relPath) return `[data-rel-path="${ds.relPath}"]`;
    if (active && active.getAttribute) {
      const label = active.getAttribute('aria-label');
      if (label) return `[aria-label="${label.replace(/"/g, '\\"')}"]`;
    }
    return null;
  }
  function restoreFocus(selector, root) {
    if (!selector) return;
    try {
      const match = root.querySelector(selector);
      if (match && typeof match.focus === 'function') match.focus();
    } catch (_) { /* selector built from live data; a mismatch is a no-op */ }
  }
  function withFocusPreserved(fn) {
    const key = captureFocusKey();
    fn();
    // repaintInner() rebuilds both the SVG canvas (#world) and the
    // project-focus sidebar panel (#map-project-panel, outside #world) in
    // the same pass — restore against the whole document so keyboard focus
    // on a branch/item button survives an operations-driven repaint too,
    // not only a canvas hit (primary at ≤400px where the canvas is hidden).
    restoreFocus(key, document);
  }

  function currentBranches(snap) {
    return snap.project ? buildBranches(snap.project, latestOperations, latestRemote) : [];
  }

  // A refresh (operations/remote poll) re-sorts and re-slices each branch's
  // preview independently of the current selection — a selected work/agent/
  // delivery item can fall outside the new BRANCH_ITEM_LIMIT/BRANCH_ITEM_MAX_
  // SHOWN cap even though it is still the selected item (viewState.item is
  // untouched by a repaint). Pin it back into its branch's preview list so
  // the sidebar/canvas fan keep showing the same selection the detail box
  // and breadcrumb already show (Rule: "share one selection").
  function ensureSelectedItemVisible(branches, item) {
    if (!item) return branches;
    return branches.map(branch => {
      if (branch.key !== item.branch) return branch;
      const items = branch.items || [];
      if (items.some(it => String(it.id) === String(item.id))) return branch;
      const full = branch.itemsAll || items;
      const match = full.find(it => String(it.id) === String(item.id));
      if (!match) return branch;
      return { ...branch, items: [match, ...items].slice(0, BRANCH_ITEM_LIMIT) };
    });
  }

  function repaint() { withFocusPreserved(repaintInner); }

  function repaintInner() {
    const snap = viewState.snapshot();
    if (snap.project) {
      lastBranches = ensureSelectedItemVisible(currentBranches(snap), snap.item);
      world.querySelector('#hub').style.display = 'none';
      world.querySelector('#lots').style.display = 'none';
      if (snap.branch !== 'papers') clearDigIn(world);
      paintProjectFocus(world, { project: snap.project, branches: lastBranches, expandedBranch: snap.branch, selectedItem: snap.item });
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

  // Sidebar-only progressive reveal for a branch's item list — the canvas
  // fan is fixed-size (map-paint.js BRANCH_ITEM_MAX_SHOWN) so "large levels
  // disclose counts and offer bounded navigation" (FOCUSED_PROJECT §Rules)
  // has to happen here: "+N more" grows this by another page instead of
  // being static, unreachable text. Resets whenever the expanded branch
  // changes so a fresh branch always opens on the same first page. Starts
  // null (set the first time a branch is expanded) rather than reading
  // BRANCH_ITEM_LIMIT eagerly here — some test harnesses run this module
  // with its imports stripped and never focus a project, so the constant
  // must only ever be touched from project-focus code paths.
  let sidebarRevealCount = null;

  // One branch open at a time (FOCUSED_PROJECT §Rules: "Opening a branch
  // collapses the previously open one"). Papers keeps the real folder tree,
  // so opening it reuses the existing dig machinery scoped to the project's
  // own folder; the other three branches are flat, already-fetched lists.
  async function toggleBranchView(key) {
    const wasExpanded = viewState.snapshot().branch === key;
    sidebarRevealCount = BRANCH_ITEM_LIMIT;
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
        btn.dataset.branch = branch.key;
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
        // Reveal beyond the base BRANCH_ITEM_LIMIT preview as sidebarRevealCount
        // grows (the "+N more" button below) — itemsAll is the full, never-
        // sliced list (project-focus.js); the sidebar is the one surface with
        // room to page through it (the canvas fan stays fixed-size).
        const full = (branch && (branch.itemsAll || branch.items)) || [];
        const items = full.slice(0, sidebarRevealCount);
        if (snap.item && snap.item.branch === snap.branch && !items.some(it => String(it.id) === String(snap.item.id))) {
          const selected = full.find(it => String(it.id) === String(snap.item.id));
          if (selected) items.push(selected);
        }
        if (items.length === 0) {
          itemsHost.textContent = branch ? branch.summary : '';
        } else {
          for (const item of items) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.dataset.branch = snap.branch;
            btn.dataset.itemId = String(item.id);
            const isSelected = Boolean(snap.item) && snap.item.branch === snap.branch && String(snap.item.id) === String(item.id);
            if (isSelected) { btn.setAttribute('aria-current', 'true'); btn.classList.add('is-selected'); }
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
          // The canvas fan already caps at BRANCH_ITEM_MAX_SHOWN with a "+N
          // more" chip (map-paint.js) — the sidebar list is wider than that
          // but still bounded (project-focus.js's BRANCH_ITEM_LIMIT), so a
          // large project (thousands of open orders) gets the same labelled
          // count here. A real button — not static text — grows
          // sidebarRevealCount by another page, so "large levels … offer
          // bounded navigation" (FOCUSED_PROJECT §Rules) is an actual verb,
          // not just a truncation note.
          if (branch && Number(branch.itemCount) > items.length) {
            const more = document.createElement('button');
            more.type = 'button';
            more.className = 'map-branch-items-more';
            more.textContent = `+${branch.itemCount - items.length} more`;
            more.addEventListener('click', () => { sidebarRevealCount += BRANCH_ITEM_LIMIT; scheduleRepaint(); });
            itemsHost.appendChild(more);
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
      // captureFocusKey()/withFocusPreserved() need dataset identity to
      // restore focus here across an operations-driven repaint (every poll
      // replaceChildren()s this box) — data-role distinguishes this link
      // from the branch-item chip/button that names the same item.
      a.dataset.branch = snap.item.branch;
      a.dataset.itemId = String(snap.item.id);
      a.dataset.role = 'open-link';
      a.setAttribute('aria-label', `Open ${snap.item.label}`);
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
    // map-shell.js's #map-project-context strip matches this path against
    // operations.projects[].folder — while a project is focused it must
    // always name that project, even with dig cleared (Work/Agents/Delivery
    // branches carry no dig path), or the legacy strip keeps showing
    // workspace-wide totals next to a sidebar/canvas that already switched
    // to a specific project.
    const locationPath = snap.project ? snap.project.relPath : (snap.dig?.relPath || '');
    document.dispatchEvent(new CustomEvent('bp:map-location', {detail:{path:locationPath}}));
    // Sibling badges (open/attention/working) only ever render for top-level
    // lots (see `state` below), and refresh on every 'bp:map-operations'
    // poll — fold nodeState into the key so a poll during focus (dig
    // cleared, project still selected) repaints the list instead of
    // silently going stale for the whole focus session.
    const stateFingerprint = snap.dig ? '' : JSON.stringify(nodeState);
    // snap.project must be in the key: focusing a project from the canvas can
    // leave the dig path unchanged (usually empty), so without it the click
    // handlers below would keep closing over a stale snap with project:null
    // and dig into a sibling's children instead of switching focus to it.
    const key = JSON.stringify([snap.dig?.relPath || '', snap.project?.relPath || '', snap.filters, page, stateFingerprint]);
    if (key === browserKey) return;
    const focusKey = captureFocusKey();
    const version = ++browseVersion;
    // While a project is focused with dig cleared (Work/Agents/Delivery),
    // the sidebar list still shows the top-level lots — but the primary path
    // label at ≤400px (where the canvas is hidden) must name the focused
    // project, matching the bp:map-location dispatch above, not fall back to
    // the workspace-wide binder label.
    document.getElementById('map-browser-path').textContent = snap.dig?.relPath || (snap.project ? snap.project.name : null) || tree.binder?.name || 'Workspace';
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
      // The legacy dig-in fan (#dig-in-layer) is the top-level workspace's
      // folder browser — while a project is focused the exploded canvas
      // (#project-focus-layer) already owns the visual, and Papers browses
      // via the sidebar list only; painting the fan underneath would leave
      // stray, clickable folder chips in the gaps around the branch layout.
      if (snap.dig && !snap.project) { clearDigIn(world); paintDigIn(world, snap.dig, nodes.slice(page * pageSize, (page + 1) * pageSize), {radius:220}); }
      else if (snap.project) { clearDigIn(world); }
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
        button.dataset.relPath = node.relPath;
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
            if (node.isDir) {
              // A project is focused and this is a top-level lot (dig is
              // cleared) — tapping a sibling must switch focus to it, not
              // dig into its children behind the still-focused canvas/
              // breadcrumb (that leaves canvas/breadcrumb on the old
              // project while the list shows the new one's children).
              if (snap.project && !snap.dig) {
                selectProjectView({ relPath: node.relPath, name: node.name, hasMd: Boolean(node.hasMd) });
                return;
              }
              await digInto(node, {mode:snap.dig ? 'nest' : 'root'});
            }
            else await openPaper(node.relPath, {label:node.name});
          } catch (error) { document.getElementById('map-browser-path').textContent = 'Unable to open this folder.'; }
        });
        list.append(button);
      }
      if (!list.children.length) list.textContent = 'No folders or readable Markdown papers here.';
      restoreFocus(focusKey, list);
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
    // second click cannot leave A's ring layered under B's. While a project
    // is focused (Papers folder navigation reuses this same dig machinery),
    // the exploded canvas already owns the visual and the sidebar list is
    // the only way to browse — painting the legacy fan here too would leave
    // stray, clickable folder chips in the gaps around it, and the hit
    // router ranks dig-in above branch items so they could steal input.
    clearDigIn(world);
    if (!viewState.snapshot().project) {
      paintDigIn(world, node, kids.slice(0, pageSize), { radius: 220 });
    }
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

  // Shared by every crumb model below (plain workspace dig, focused-project
  // branch/item, and focused-project Papers) so the DOM building/attachment
  // rules — home styling, separators, disabled = current position — live in
  // one place.
  function renderCrumbs(el, crumbs) {
    el.hidden = false;
    el.replaceChildren();
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
  }

  // Papers reuses the plain dig/trail machinery while a project is focused
  // (toggleBranchView), so trail[0] is always the project root itself —
  // "nested" is only the folder depth beyond that root. Collapsing the
  // crumb at `depth` pops back to that many nested segments (0 = project
  // root). No paintDigIn here: the exploded canvas owns the visual while a
  // project is focused (see digInto()'s matching guard); renderBrowser()
  // picks up the new dig path on its own key change.
  function collapsePapersTrailTo(depth) {
    page = 0;
    while (viewState.snapshot().trail.length > depth + 1) viewState.popDig();
    clearDigIn(world);
    renderTrail();
    scheduleRepaint();
  }

  function renderTrail() {
    syncUrl();
    const el = document.getElementById(cfg.chromeIds.trail);
    if (!el) return;
    const snap = viewState.snapshot();
    // FOCUSED_PROJECT §Rules — "Sidebar, canvas and breadcrumb share one
    // selection." A focused project always shows Home › Project › … — the
    // raw Papers dig trail never appears on its own; once Papers is the
    // expanded branch its nested folder depth extends this same crumb model
    // instead of replacing it, so the focused project/branch is never
    // dropped from the breadcrumb during the primary Papers browse flow.
    if (snap.project && snap.branch !== 'papers') {
      const crumbs = [
        { label: tree.binder?.name || 'hub', onClick: clearProjectFocusView },
        { label: snap.project.name, onClick: () => { viewState.clearBranch(); scheduleRepaint(); } },
      ];
      if (snap.branch) crumbs.push({ label: branchLabel(snap.branch), onClick: () => { viewState.clearItem(); scheduleRepaint(); } });
      if (snap.item) crumbs.push({ label: snap.item.label, onClick: null });
      renderCrumbs(el, crumbs);
      return;
    }
    if (snap.project && snap.branch === 'papers') {
      const nested = snap.trail.slice(1); // trail[0] is the project root itself
      const crumbs = [
        { label: tree.binder?.name || 'hub', onClick: clearProjectFocusView },
        { label: snap.project.name, onClick: () => { viewState.clearBranch(); scheduleRepaint(); } },
        { label: branchLabel('papers'), onClick: nested.length > 0 ? () => collapsePapersTrailTo(0) : null },
      ];
      nested.forEach((entry, idx) => {
        crumbs.push({ label: entry.name, onClick: idx < nested.length - 1 ? () => collapsePapersTrailTo(idx + 1) : null });
      });
      renderCrumbs(el, crumbs);
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
        if (!itemId) {
          // The canvas "+N more" chip: the fan is fixed-size (map-paint.js
          // BRANCH_ITEM_MAX_SHOWN), so bounded navigation for the rest of a
          // large branch happens in the sidebar — grow its revealed page and
          // bring it into view instead of leaving the chip a dead click.
          sidebarRevealCount += BRANCH_ITEM_LIMIT;
          scheduleRepaint();
          document.getElementById('map-branch-items')?.scrollIntoView({ block: 'nearest' });
          return;
        }
        const branch = lastBranches.find(b => b.key === key);
        const item = branch ? (branch.itemsAll || branch.items).find(it => String(it.id) === itemId) : null;
        if (item) { viewState.setItem(item); scheduleRepaint(); }
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

  // Reset button — "Workspace" must always return to the workspace hub,
  // including out of a focused project (mirrors the hub-click handler
  // above); resetView() alone only clears a Papers dig, leaving the
  // focused canvas/breadcrumb/panel active.
  const resetBtn = document.getElementById(cfg.chromeIds.reset);
  if (resetBtn) resetBtn.addEventListener('click', () => {
    if (viewState.snapshot().project) { clearProjectFocusView(); return; }
    resetView();
  });

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
    // Same fan-under-focused-canvas guard as digInto() — Papers folder
    // navigation shares this dig machinery while a project is focused, and
    // the legacy fan must never paint over/under the exploded canvas.
    if (popped && !viewState.snapshot().project) {
      const kids = visibleChildren(await tree.childrenAt(popped.relPath));
      clearDigIn(world);
      paintDigIn(world, popped, kids.slice(0, pageSize), { radius: 220 });
    }
    renderTrail();
    // Trail root may have changed (or gone empty) → refresh the focus ring.
    scheduleRepaint();
  });

  // Escape unwinds the focused-project selection one level at a time
  // (item → branch → project), same order as the breadcrumb crumbs'
  // onClick — and returns to the workspace level once nothing is left to
  // unwind. md-viewer.js already owns Escape while the reader is open (it
  // only closes the reader), so this never fires alongside that.
  document.addEventListener('keydown', (ev) => {
    if (viewer.isOpen()) return;
    if (ev.key !== 'Escape') return;
    if (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA')) return;
    const snap = viewState.snapshot();
    if (!snap.project) return;
    ev.preventDefault();
    if (snap.item) { viewState.clearItem(); scheduleRepaint(); return; }
    if (snap.branch) { viewState.clearBranch(); scheduleRepaint(); return; }
    clearProjectFocusView();
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
  // Shared by boot and the popstate handler below — walks a `path` (project-
  // relative folder chain) one segment at a time via the existing dig
  // machinery, exactly like a person clicking down through the browser list.
  async function digToPath(path) {
    let relative = '';
    for (const part of path.split('/').filter(Boolean)) {
      relative = relative ? relative + '/' + part : part;
      await digInto({ relPath: relative, name: part }, { mode: relative.includes('/') ? 'nest' : 'root' });
    }
  }

  // Deep-link boot only carries the project relPath in the URL — resolve
  // hasMd from the already-loaded tree so papersBranch reports correctly on
  // first paint instead of always reading "empty" (no state.project.hasMd).
  // Shared with the popstate handler below so back/forward across a focused
  // project restores the same way a fresh deep link does, including the
  // `path` query param — Papers can be dug into a nested folder (the sidebar
  // list still nests further while a project is focused), and that depth
  // must match the address bar on Back/Forward, not just reset to the
  // project root.
  async function applyProjectParams(initial) {
    const projectPath = initial.get('project');
    const path = initial.get('path');
    if (!projectPath) {
      if (viewState.snapshot().project) clearProjectFocusView();
      if (path) await digToPath(path);
      else if (viewState.snapshot().dig) resetView();
      return;
    }
    // A popstate can re-apply the exact same project/branch/item/path already
    // in view (e.g. a Back/Forward step that only added or dropped `md`) —
    // selectProjectView()/toggleBranchView() always reset branch/item/dig, so
    // calling them unconditionally would collapse and re-expand the whole
    // focused view (and re-trigger the branch-item enter animation) for a
    // navigation that never actually changed the project-focus selection.
    const projectChanged = !viewState.snapshot().project || viewState.snapshot().project.relPath !== projectPath;
    if (projectChanged) {
      const treeLot = tree.snapshot().lots.find(lot => lot.relPath === projectPath);
      selectProjectView({
        relPath: projectPath,
        name: (treeLot && treeLot.name) || projectPath.split('/').pop(),
        hasMd: treeLot ? treeLot.hasMd : false,
      });
    }
    // `path` with no `branch` still names a Papers folder depth — a shared/
    // restored URL like `?project=…&path=docs/specs` must reopen Papers at
    // that depth rather than being silently ignored for lacking `branch`.
    const branch = initial.get('branch') || (path ? 'papers' : null);
    if (branch) {
      if (projectChanged || viewState.snapshot().branch !== branch) await toggleBranchView(branch);
      if (branch === 'papers') {
        if (path && path !== viewState.snapshot().dig?.relPath) await digToPath(path);
      }
      const itemId = initial.get('item');
      if (itemId) {
        const currentItem = viewState.snapshot().item;
        if (!currentItem || currentItem.branch !== branch || String(currentItem.id) !== itemId) {
          applyDeepLinkItem(branch, itemId);
        }
      } else if (!projectChanged && viewState.snapshot().item) {
        viewState.clearItem();
      }
    } else if (!projectChanged && viewState.snapshot().branch) {
      viewState.clearBranch();
    }
  }

  // The reader is independent of project/branch/item/path selection (Rule:
  // md-viewer "does NOT touch MapViewState.dig") but still needs its own
  // restore on Back/Forward — a popped `md` param must (re)open that paper,
  // and a popped state that dropped `md` must close whatever is open, or the
  // reader stays open/closed out of step with the address bar.
  async function applyMdParam(params) {
    const md = params.get('md');
    if (md) {
      if (viewer.currentPath() !== md) await openPaper(md, { label: md.split('/').pop() });
    } else if (viewer.isOpen()) {
      viewer.close();
    }
  }

  window.addEventListener('resize', applyCamera);
  window.addEventListener('popstate', async () => {
    restoring = true;
    const params = new URLSearchParams(location.search);
    await applyProjectParams(params);
    await applyMdParam(params);
    restoring = false;
    lastNavKey = projectNavKey(viewState.snapshot());
  });
  await tree.load();
  await refreshRemote();
  repaint();
  await applyProjectParams(initial);
  await applyMdParam(initial);
  // The restored state is not a fresh navigation — sync it with
  // replaceState (matching pre-existing boot behavior) rather than pushing
  // a duplicate history entry on top of the page load.
  lastNavKey = projectNavKey(viewState.snapshot());
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
