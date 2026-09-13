// view-state.js — the single MapViewState store.
//
// Glass §Dig grammar and §Paint stack rules:
//   - Dig state has ONE owner. No sibling `mapDigIn` global.
//   - Two consumers only: #dig-in-layer paint and the dig-trail chrome.
//   - Filters (managed / unmanaged / hidden) persist here, not in a second store.
//   - No `setProjection`, no custom-order layout API — those come back Later.
//
// FOCUSED_PROJECT (docs/specs/MAP_FOCUSED_PROJECT.md, pc-1492) adds a second,
// still single-owner slice: the focused project, its one expanded branch,
// and the selected item. `dig`/`trail` remain the Papers branch's nested
// folder browser — they only apply while `branch === 'papers'`.
//
// Public shape:
//   const state = createViewState();
//   state.subscribe(fn)           // fn(state) on any change; returns unsubscribe
//   state.setDig({relPath, name}) // nested dig — push onto trail (child of current)
//   state.replaceDig({...})       // root-level dig — REPLACE trail with [node]
//   state.clearDig()              // Reset — trail empty, dig null
//   state.popDig()                // Back — pop one trail entry (null if empty)
//   state.setFilter(k, v)         // one of: managed | unmanaged | hidden
//   state.selectProject({relPath, name}) // focus a project; clears branch/item/dig
//   state.clearProject()          // return to the workspace (no project in focus)
//   state.setBranch(key)          // expand a branch; same key again collapses it
//   state.setItem(item)           // select a detail item inside the open branch
//   state.clearItem()             // drop the selected detail, keep the branch open
//   state.snapshot()              // frozen plain object

export function createViewState(initial = {}) {
  const listeners = new Set();
  const state = {
    dig: null,             // { relPath, name } | null
    trail: [],             // array of { relPath, name }, deepest last
    filters: {
      managed: true,
      unmanaged: false,
      hidden: false,
      ...(initial.filters || {}),
    },
    project: null,         // { relPath, name } | null — the focused project
    branch: null,          // 'work' | 'agents' | 'papers' | 'delivery' | null
    item: null,            // { branch, id, label, href, ... } | null
  };

  function emit() {
    for (const fn of listeners) {
      try { fn(snapshot()); } catch (err) { console.error('[view-state] listener', err); }
    }
  }

  function snapshot() {
    return Object.freeze({
      dig: state.dig ? { ...state.dig } : null,
      trail: state.trail.map(t => ({ ...t })),
      filters: { ...state.filters },
      project: state.project ? { ...state.project } : null,
      branch: state.branch,
      item: state.item ? { ...state.item } : null,
    });
  }

  return {
    snapshot,
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    setDig(node) {
      if (!node || typeof node.relPath !== 'string') return;
      const top = state.trail[state.trail.length - 1];
      if (!top || top.relPath !== node.relPath) {
        state.trail.push({ relPath: node.relPath, name: node.name || node.relPath });
      }
      state.dig = { relPath: node.relPath, name: node.name || node.relPath };
      emit();
    },
    replaceDig(node) {
      if (!node || typeof node.relPath !== 'string') return;
      const entry = { relPath: node.relPath, name: node.name || node.relPath };
      state.trail = [entry];
      state.dig = { ...entry };
      emit();
    },
    clearDig() {
      state.dig = null;
      state.trail = [];
      emit();
    },
    popDig() {
      if (state.trail.length === 0) return null;
      state.trail.pop();
      const top = state.trail[state.trail.length - 1] || null;
      state.dig = top ? { ...top } : null;
      emit();
      return state.dig;
    },
    setFilter(key, value) {
      if (!(key in state.filters)) return;
      state.filters[key] = Boolean(value);
      emit();
    },
    selectProject(node) {
      if (!node || typeof node.relPath !== 'string') return;
      state.project = { relPath: node.relPath, name: node.name || node.relPath };
      state.branch = null;
      state.item = null;
      state.dig = null;
      state.trail = [];
      emit();
    },
    clearProject() {
      state.project = null;
      state.branch = null;
      state.item = null;
      state.dig = null;
      state.trail = [];
      emit();
    },
    setBranch(key) {
      if (!state.project) return;
      state.branch = state.branch === key ? null : key;
      state.item = null;
      if (state.branch !== 'papers') { state.dig = null; state.trail = []; }
      emit();
    },
    setItem(item) {
      if (!state.branch) return;
      state.item = item ? { branch: state.branch, ...item } : null;
      emit();
    },
    clearItem() {
      state.item = null;
      emit();
    },
    clearBranch() {
      state.branch = null;
      state.item = null;
      state.dig = null;
      state.trail = [];
      emit();
    },
  };
}
