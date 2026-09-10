// map-tree.js — client snapshot reader.
//
// Glass §Truth = filesystem + git: Map reads three things from the BFF
// snapshot, nothing else in V1. This module owns the fetch shape and hands
// paint code a small vocabulary:
//
//   const tree = createMapTree({ fetcher });
//   await tree.load();                       // GET /api/map/tree
//   tree.binder                              // { path, name }
//   tree.topLots()                           // depth-1 lots visible under hub
//   await tree.childrenAt(relPath)           // GET /api/map/children?relPath=…
//
// No stores, no roster, no scene — those are Later.

const DEFAULT_ENDPOINTS = {
  tree: '/api/map/tree',
  children: '/api/map/children',
};

export function createMapTree({ fetcher = fetch, endpoints = {} } = {}) {
  const eps = { ...DEFAULT_ENDPOINTS, ...endpoints };
  const state = {
    binder: null,
    lots: [],
    git: null,
    childrenCache: new Map(),
  };

  async function load() {
    const res = await fetcher(eps.tree, { headers: { accept: 'application/json' } });
    if (!res || !res.ok) throw new Error(`map-tree: /api/map/tree ${res && res.status}`);
    const data = await res.json();
    state.binder = data.binder || null;
    state.lots = Array.isArray(data.lots) ? data.lots : [];
    state.git = data.git || null;
    state.childrenCache.clear();
    return snapshot();
  }

  function topLots(filters = { managed: true, unmanaged: true, hidden: false }) {
    return state.lots.filter(lot => {
      if (!filters.hidden && lot.hidden) return false;
      if (!filters.managed && lot.managed) return false;
      if (!filters.unmanaged && !lot.managed && !lot.hidden) return false;
      return true;
    });
  }

  async function childrenAt(relPath) {
    if (typeof relPath !== 'string' || relPath === '') return [];
    if (state.childrenCache.has(relPath)) return state.childrenCache.get(relPath);
    const url = `${eps.children}?relPath=${encodeURIComponent(relPath)}`;
    const res = await fetcher(url, { headers: { accept: 'application/json' } });
    if (!res || !res.ok) throw new Error(`map-tree: /api/map/children ${res && res.status}`);
    const data = await res.json();
    const kids = Array.isArray(data.children) ? data.children : [];
    state.childrenCache.set(relPath, kids);
    return kids;
  }

  function snapshot() {
    return {
      binder: state.binder ? { ...state.binder } : null,
      lots: state.lots.slice(),
      git: state.git ? { ...state.git } : null,
    };
  }

  return {
    load,
    topLots,
    childrenAt,
    snapshot,
    get binder() { return state.binder; },
  };
}
