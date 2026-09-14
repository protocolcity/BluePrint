// project-focus.js — pure data composition for the focused exploded project
// view (docs/specs/MAP_FOCUSED_PROJECT.md, pc-1492).
//
// Every function here is pure: given the already-fetched snapshots (map
// tree lots, the shared operations projection, the remote-activity cache)
// it returns the four virtual branches — Work, Agents, Papers, Delivery —
// as named facts, never bare number triplets. No fetch, no DOM, no store.
//
// Papers keeps the real filesystem tree (map-tree.js / server/map_tree.py);
// this module only reports whether the project folder has any Markdown to
// browse, matching FOCUSED_PROJECT §Sources ("Papers keeps the real
// folder/file tree with exact names").

export const BRANCH_KEYS = Object.freeze(['work', 'agents', 'papers', 'delivery']);

const BRANCH_LABELS = Object.freeze({
  work: 'Work', agents: 'Agents', papers: 'Papers', delivery: 'Delivery',
});

export function branchLabel(key) { return BRANCH_LABELS[key] || key; }

// Bounded-navigation guidance for large levels applies to the sidebar list
// too, not only the canvas fan (map-paint.js's own, smaller
// BRANCH_ITEM_MAX_SHOWN cap) — an open-ended project (thousands of orders)
// must not turn #map-branch-items into an unbounded scroll list. Each
// branch's `summary` already reports the true totals from operations'
// server-side counts, independent of how many items this array carries.
export const BRANCH_ITEM_LIMIT = 20;

// The sidebar itself (the existing map-tree-driven project/paper browser)
// keeps every project reachable while one is in focus (FOCUSED_PROJECT rule:
// "the other projects stay reachable in a stable sidebar"); this module only
// composes the branches for whichever project is currently focused.

function findOpsProject(operations, projectRelPath) {
  if (!operations || !Array.isArray(operations.projects)) return null;
  return operations.projects.find(p => p && p.folder === projectRelPath) || null;
}

function sourceAvailable(operations, name) {
  if (!operations || !Array.isArray(operations.sources)) return true;
  const source = operations.sources.find(s => s && s.name === name);
  return !source || source.state === 'available';
}

// Matches operations.js/work-order.js: a claimed in-progress order is named
// by its owning seat ("Live · <seat>"), never by status_word alone — a
// stored claim is not the same fact as a running agent (STATES_AND_TERMS §5).
function lifecycleDetail(o) {
  if (o.status === 'in_progress' && o.live_with) return `Live · ${o.live_with}`;
  return o.status_word || o.status;
}

// Work: STATES_AND_TERMS §5 — "All open" already includes every gate; the
// server-side count (operations.py) is the single source, this module never
// recomputes it. A WorkLane claim is reported as "claimed", never "working".
export function workBranch(project, operations) {
  const key = 'work';
  const label = branchLabel(key);
  if (!operations || !sourceAvailable(operations, 'WorkLane')) {
    return { key, label, state: 'unavailable', summary: 'Work source unavailable', items: [] };
  }
  const opProject = findOpsProject(operations, project && project.relPath);
  if (!opProject) {
    return { key, label, state: 'empty', summary: 'No linked work-order project', items: [] };
  }
  if (opProject.state && opProject.state !== 'available') {
    return { key, label, state: 'unavailable', summary: 'read-only', items: [] };
  }
  const open = Number(opProject.open) || 0;
  const attention = Number(opProject.attention) || 0;
  const claimed = Number(opProject.claimed) || 0;
  const running = Number(opProject.running) || 0;
  const orders = (operations.orders || []).filter(o => o && o.project === opProject.id);
  // itemsAll is the full mapped list (never sliced) — a deep-linked ?item=
  // must be findable even when it falls outside the sidebar/canvas display
  // cap (BRANCH_ITEM_LIMIT); `items` stays the capped, sorted preview.
  const itemsAll = orders
    .slice()
    .sort((a, b) => (Number(a.priority) || 9) - (Number(b.priority) || 9))
    .map(o => ({
      id: o.id,
      label: o.title || o.id,
      detail: o.attention ? `${lifecycleDetail(o)} · For You` : lifecycleDetail(o),
      href: `/work-order?project=${encodeURIComponent(opProject.id)}&id=${encodeURIComponent(o.id)}`,
    }));
  return {
    key, label,
    state: open === 0 ? 'empty' : 'available',
    summary: `${open} open · ${attention} For You · ${claimed} claimed · ${running} working`,
    items: itemsAll.slice(0, BRANCH_ITEM_LIMIT),
    itemsAll,
    itemCount: orders.length,
  };
}

// Agents: only WorkForce shift evidence paints a seat as "working" — the
// upstream operations.agents rows already enforce that (pc-1483); this
// module just names the counts, never re-derives liveness.
export function agentsBranch(project, operations) {
  const key = 'agents';
  const label = branchLabel(key);
  if (!operations || !Array.isArray(operations.agents)) {
    return { key, label, state: 'unavailable', summary: 'Agents source unavailable', items: [] };
  }
  const opProject = findOpsProject(operations, project && project.relPath);
  const projectId = opProject ? opProject.id : null;
  const rows = operations.agents.filter(a => a && a.project === projectId);
  if (!projectId || rows.length === 0) {
    return { key, label, state: 'empty', summary: 'No seats hold this project', items: [] };
  }
  const working = rows.filter(a => a.state === 'working').length;
  const itemsAll = rows.map(a => ({
    id: a.id,
    label: a.name || a.id,
    detail: a.state === 'working' ? 'working' : (a.held ? `live with ${a.held.id}` : (a.badge || a.state)),
    href: '/agents',
  }));
  return {
    key, label, state: 'available',
    summary: `${rows.length} seat${rows.length === 1 ? '' : 's'} · ${working} working`,
    items: itemsAll.slice(0, BRANCH_ITEM_LIMIT),
    itemsAll,
    itemCount: rows.length,
  };
}

// Papers: the real folder/file tree is fetched separately (map-tree.js);
// this only reports whether there is anything to open, per Sources rule
// ("source folders are not exposed until the person asks to browse them").
export function papersBranch(project) {
  const key = 'papers';
  const label = branchLabel(key);
  if (!project) return { key, label, state: 'unavailable', summary: 'Papers source unavailable', items: [] };
  return {
    key, label,
    state: project.hasMd ? 'available' : 'empty',
    summary: project.hasMd ? 'Open the folder to browse' : 'No Markdown papers found',
    items: [],
  };
}

// Delivery: remote-activity cache; "unavailable" is explicit, never a
// silent empty branch (Sources rule).
export function deliveryBranch(project, operations, remote) {
  const key = 'delivery';
  const label = branchLabel(key);
  if (!remote || !['connected', 'partial'].includes(remote.state)) {
    const reason = remote && remote.state === 'not_configured' ? 'No repository connected'
      : remote && remote.state === 'unavailable' ? 'GitHub source unavailable'
        : 'Delivery source unavailable';
    return { key, label, state: 'unavailable', summary: reason, items: [] };
  }
  const opProject = findOpsProject(operations, project && project.relPath);
  const projectId = opProject ? opProject.id : null;
  const repos = (remote.repositories || []).filter(r => r && r.project === projectId);
  if (!projectId || repos.length === 0) {
    return { key, label, state: 'empty', summary: 'No repository linked to this project', items: [] };
  }
  const allItems = repos.flatMap(r => (r.items || []).map(item => ({ ...item, repo: r.repo, observedAt: r.observed_at })));
  const observedAt = repos.map(r => r.observed_at).filter(Boolean).sort().pop();
  // Stable across reorder/truncation of the remote-activity cache: keyed on
  // the item's own identity (PR number, commit sha, or URL) rather than its
  // position in the list — a list-index id breaks `?item=` deep links and
  // selection whenever the cache reorders or truncates between polls.
  const itemsAll = allItems.map(item => {
    const stableKey = item.number != null ? `n${item.number}`
      : item.sha ? `s${item.sha}`
        : item.url ? `u${item.url}`
          : `t${item.observedAt || ''}-${item.title || item.workflow_name || ''}`;
    return {
      id: `${item.repo}-${item.kind}-${stableKey}`,
      label: item.title || item.workflow_name || item.kind || 'activity',
      detail: `${item.state || 'unknown'}${item.updated_at ? ' · ' + item.updated_at : ''}`,
      href: item.url || `https://github.com/${item.repo}`,
    };
  });
  const anyUnavailable = repos.some(r => r.state === 'unavailable');
  return {
    key, label,
    state: allItems.length === 0 ? 'empty' : (anyUnavailable ? 'stale' : 'available'),
    summary: `${allItems.length} item${allItems.length === 1 ? '' : 's'}${observedAt ? ' · observed ' + observedAt : ''}`,
    items: itemsAll.slice(0, BRANCH_ITEM_LIMIT),
    itemsAll,
    itemCount: allItems.length,
  };
}

export function buildBranches(project, operations, remote) {
  return [
    workBranch(project, operations),
    agentsBranch(project, operations),
    papersBranch(project),
    deliveryBranch(project, operations, remote),
  ];
}
