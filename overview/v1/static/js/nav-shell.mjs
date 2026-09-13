export function ensureActiveNavVisible(root = document) {
  const nav = root.querySelector('.bp-nav');
  const current = root.querySelector('.bp-nav a[aria-current="page"]');
  if (!nav || !current) return;
  const reduce = root.body?.classList.contains('bp-reduce-motion');
  current.scrollIntoView({inline: 'center', block: 'nearest', behavior: reduce ? 'auto' : 'smooth'});
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
