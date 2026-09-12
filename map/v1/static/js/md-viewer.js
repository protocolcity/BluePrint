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
  layerId = 'md-viewer-host',
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
  let returnFocus = null;

  function mount() {
    if (overlay) return;
    hostLayer = document.getElementById(layerId);
    if (!hostLayer) throw new Error(`md-viewer: #${layerId} missing`);
    hostLayer.setAttribute('data-hit-layer', 'md-viewer');
    hostLayer.style.visibility = 'hidden';
    hostLayer.replaceChildren();

    const backdrop = document.createElement('div');
    backdrop.className = 'map-md-backdrop';
    backdrop.setAttribute('data-hit-layer', 'md-viewer');

    const panel = document.createElement('div');
    panel.className = 'map-md-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-label', 'Document reader');
    panel.tabIndex = -1;

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

    // Prefer an HTML host on #map-stage (viewport-fixed, inset from chrome)
    // so pan/zoom/dig never clip the panel. SVG <g> hosts keep a foreignObject
    // so the Glass paint-stack id still works in tests.
    if (hostLayer.namespaceURI === 'http://www.w3.org/2000/svg') {
      const svgNs = 'http://www.w3.org/2000/svg';
      const fo = document.createElementNS(svgNs, 'foreignObject');
      fo.setAttribute('x', '0');
      fo.setAttribute('y', '0');
      fo.setAttribute('width', '100%');
      fo.setAttribute('height', '100%');
      fo.classList.add('map-md-fo');
      fo.appendChild(backdrop);
      hostLayer.appendChild(fo);
    } else {
      hostLayer.appendChild(backdrop);
    }
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
    if (ev.key === 'Tab') {
      const nodes = [...overlay.panel.querySelectorAll('button, a[href], input, select, textarea, [tabindex="0"]')];
      const first = nodes[0], last = nodes[nodes.length-1];
      if (ev.shiftKey && (document.activeElement === first || !overlay.panel.contains(document.activeElement))) {ev.preventDefault();last?.focus();}
      else if (!ev.shiftKey && (document.activeElement === last || !overlay.panel.contains(document.activeElement))) {ev.preventDefault();first?.focus();}
    }
  }

  async function open(path, { label } = {}) {
    if (!overlay) mount();
    if (!isOpen) returnFocus = document.activeElement;
    currentPath = path;
    isOpen = true;
    hostLayer.style.visibility = 'visible';
    hostLayer.classList.add('is-open');
    titleEl.textContent = label || path || '';
    contentEl.textContent = '';
    contentEl.classList.add('is-loading');
    overlay.panel.querySelector('button').focus();
    try {
      const url = `${endpoint}?path=${encodeURIComponent(path)}&render=html`;
      const res = await fetcher(url, { headers: { accept: 'text/html' } });
      if (!res || !res.ok) throw new Error(`md-viewer: ${res && res.status}`);
      const html = await res.text();
      if (!isOpen || currentPath !== path) return;
      contentEl.classList.remove('is-loading');
      contentEl.innerHTML = html;
    } catch (err) {
      if (!isOpen || currentPath !== path) return;
      contentEl.classList.remove('is-loading');
      contentEl.textContent = `Failed to load ${path}: ${err.message}`;
    }
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    currentPath = null;
    if (hostLayer) {
      hostLayer.style.visibility = 'hidden';
      hostLayer.classList.remove('is-open');
    }
    if (contentEl) contentEl.textContent = '';
    if (returnFocus?.isConnected) returnFocus.focus();
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
