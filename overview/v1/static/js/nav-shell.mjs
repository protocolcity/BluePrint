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
  if (reduce) nav.scrollLeft = next;
  else nav.scrollTo({left: next, behavior: 'smooth'});
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
