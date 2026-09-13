export function ensureActiveNavVisible(root = document) {
  const nav = root.querySelector('.bp-nav');
  const current = root.querySelector('.bp-nav a[aria-current="page"]');
  if (!nav || !current) return;
  const reduce = root.body?.classList.contains('bp-reduce-motion');
  const navRect = nav.getBoundingClientRect();
  const linkRect = current.getBoundingClientRect();
  const target = linkRect.left - navRect.left + nav.scrollLeft - (nav.clientWidth - current.clientWidth) / 2;
  const maxScroll = Math.max(0, nav.scrollWidth - nav.clientWidth);
  const next = Math.min(maxScroll, Math.max(0, target));
  if (reduce) { nav.scrollLeft = next; return; }
  // Smooth scroll when the engine supports the options form; otherwise (or on
  // a throw) fall back to a direct assignment so the active tab is never left
  // off-screen (pc-1491 second pass).
  try {
    if (typeof nav.scrollTo === 'function') nav.scrollTo({left: next, behavior: 'smooth'});
    else nav.scrollLeft = next;
  } catch { nav.scrollLeft = next; }
}

// Outline links and fragment navigation target collapsed sections
// (<details class="bp-md-section" id="…">); a jump must open the target and
// its ancestors or the body stays hidden behind the summary (pc-1491 second
// pass).
export function revealHashSection(root = document, hash = null) {
  const raw = hash ?? root.location?.hash ?? '';
  const id = decodeURIComponent(String(raw).replace(/^#/, ''));
  if (!id) return null;
  let target = null;
  try { target = root.getElementById ? root.getElementById(id) : root.querySelector('#' + CSS.escape(id)); } catch { target = null; }
  if (!target) return null;
  let node = target;
  while (node) {
    if (node.tagName === 'DETAILS') node.open = true;
    node = node.parentElement;
  }
  return target;
}

export function bindHashReveal(root = document) {
  const win = root.defaultView || globalThis;
  if (!win || win.__bpHashRevealBound) return;
  win.__bpHashRevealBound = true;
  win.addEventListener?.('hashchange', () => revealHashSection(root));
  revealHashSection(root);
}

export function backLabel(pathname) {
  const path = (pathname || '').replace(/\/$/, '') || '/';
  if (path === '/map') return 'Back to Map';
  if (path === '/calendar') return 'Back to Calendar';
  if (path === '/timeline') return 'Back to Timeline';
  if (path === '/projects') return 'Back to Projects';
  if (path === '/work') return 'Back to Work';
  return 'Back to Work';
}

export function date(value) {
  if (!value) return 'Not reported';
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf())
    ? 'Not reported'
    : parsed.toLocaleString([], {month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'});
}

export function paintOutline(container, outline) {
  if (!container || !outline?.length) {
    if (container) container.hidden = true;
    return;
  }
  container.replaceChildren();
  for (const item of outline) {
    const link = document.createElement('a');
    link.href = `#${item.id}`;
    link.textContent = item.title;
    link.className = item.level === 3 ? 'bp-outline-h3' : 'bp-outline-h2';
    link.addEventListener('click', () => revealHashSection(container.ownerDocument || document, link.getAttribute('href')));
    container.append(link);
  }
  container.hidden = false;
}

export function setTrustedHtml(node, html) {
  if (!node) return;
  node.replaceChildren();
  const template = document.createElement('template');
  template.innerHTML = html || '';
  node.append(template.content);
}
