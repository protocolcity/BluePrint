// md-viewer.js — the in-shell markdown reader overlay.
//
// Glass §MD viewer: one overlay, mounted once, hidden by default. Opens on
// .md lot click; closes on × / Esc / backdrop; does NOT touch MapViewState.dig.
// Owns hits while up (see hit-router row 1).
//
// Content = server-rendered HTML from /api/file?path=…&render=html so the
// suite paints result. This module never runs a markdown parser itself.

const DEFAULT_ENDPOINT = '/api/file';

export function createMdViewer({
  layerId = 'md-viewer-layer',
  fetcher = fetch,
  endpoint = DEFAULT_ENDPOINT,
  onClose,
} = {}) {
  let hostLayer = null;
  let overlay = null;
  let contentEl = null;
  let titleEl = null;
  let isOpen = false;
  let currentPath = null;

  function mount() {
    if (overlay) return;
    hostLayer = document.getElementById(layerId);
    if (!hostLayer) throw new Error(`md-viewer: #${layerId} missing`);
    hostLayer.setAttribute('data-hit-layer', 'md-viewer');
    hostLayer.style.visibility = 'hidden';
    hostLayer.replaceChildren();

    // Use a foreignObject so the reader nests inside the SVG paint stack
    // (Glass §Paint stack) but hosts real HTML for content rendering.
    const svgNs = 'http://www.w3.org/2000/svg';
    const fo = document.createElementNS(svgNs, 'foreignObject');
    fo.setAttribute('x', '0');
    fo.setAttribute('y', '0');
    fo.setAttribute('width', '100%');
    fo.setAttribute('height', '100%');
    fo.classList.add('map-md-fo');

    const backdrop = document.createElement('div');
    backdrop.className = 'map-md-backdrop';
    backdrop.setAttribute('data-hit-layer', 'md-viewer');

    const panel = document.createElement('div');
    panel.className = 'map-md-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');

    const bar = document.createElement('div');
    bar.className = 'map-md-bar';
    titleEl = document.createElement('div');
    titleEl.className = 'map-md-title';
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'map-md-close';
    closeBtn.setAttribute('aria-label', 'Close reader');
    closeBtn.textContent = '×';
    bar.appendChild(titleEl);
    bar.appendChild(closeBtn);

    contentEl = document.createElement('div');
    contentEl.className = 'map-md-content';

    panel.appendChild(bar);
    panel.appendChild(contentEl);
    backdrop.appendChild(panel);
    fo.appendChild(backdrop);
    hostLayer.appendChild(fo);
    overlay = { backdrop, panel };

    backdrop.addEventListener('click', (ev) => {
      if (ev.target === backdrop) close();
    });
    closeBtn.addEventListener('click', close);
    document.addEventListener('keydown', onKeyDown);
  }

  function onKeyDown(ev) {
    if (!isOpen) return;
    if (ev.key === 'Escape') { ev.preventDefault(); close(); }
  }

  async function open(path, { label } = {}) {
    if (!overlay) mount();
    currentPath = path;
    isOpen = true;
    hostLayer.style.visibility = 'visible';
    titleEl.textContent = label || path || '';
    contentEl.textContent = '';
    contentEl.classList.add('is-loading');
    try {
      const url = `${endpoint}?path=${encodeURIComponent(path)}&render=html`;
      const res = await fetcher(url, { headers: { accept: 'text/html' } });
      if (!res || !res.ok) throw new Error(`md-viewer: ${res && res.status}`);
      const html = await res.text();
      contentEl.classList.remove('is-loading');
      contentEl.innerHTML = html;
    } catch (err) {
      contentEl.classList.remove('is-loading');
      contentEl.textContent = `Failed to load ${path}: ${err.message}`;
    }
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    currentPath = null;
    if (hostLayer) hostLayer.style.visibility = 'hidden';
    if (contentEl) contentEl.textContent = '';
    if (typeof onClose === 'function') onClose();
  }

  return {
    mount,
    open,
    close,
    isOpen: () => isOpen,
    currentPath: () => currentPath,
  };
}
