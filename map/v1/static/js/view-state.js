// view-state.js — the single MapViewState store.
//
// Glass §Dig grammar and §Paint stack rules:
//   - Dig state has ONE owner. No sibling `mapDigIn` global.
//   - Two consumers only: #dig-in-layer paint and the dig-trail chrome.
//   - Filters (managed / unmanaged / hidden) persist here, not in a second store.
//   - No `setProjection`, no custom-order layout API — those come back Later.
//
// Public shape:
//   const state = createViewState();
//   state.subscribe(fn)           // fn(state) on any change; returns unsubscribe
//   state.setDig({relPath, name}) // dig into a lot; pushes trail
//   state.clearDig()              // Reset — trail empty, dig null
//   state.popDig()                // Back — pop one trail entry (null if empty)
//   state.setFilter(k, v)         // one of: managed | unmanaged | hidden
//   state.snapshot()              // frozen plain object

export function createViewState(initial = {}) {
  const listeners = new Set();
  const state = {
    dig: null,             // { relPath, name } | null
    trail: [],             // array of { relPath, name }, deepest last
    filters: {
      managed: true,
      unmanaged: true,
      hidden: false,
      ...(initial.filters || {}),
    },
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
  };
}
