/* Shared desk scope and navigation affordances for reader shells. */
(async () => {
  const {ensureActiveNavVisible} = await import('/js/nav-shell.mjs');
  const name = document.getElementById('desk-name');
  const path = document.getElementById('scope-path');
  const footer = document.getElementById('footer-status');
  const refresh = document.getElementById('refresh');
  try {
    document.body.classList.toggle(
      'bp-reduce-motion',
      JSON.parse(localStorage.getItem('bp-display') || '{}').motion === 'off',
    );
  } catch (_) { /* System preference applies when storage is unavailable. */ }
  refresh?.addEventListener('click', () => location.reload());
  ensureActiveNavVisible();
  try {
    const response = await fetch('/api/operations', {cache: 'no-store', signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('unavailable');
    const data = await response.json();
    if (name) name.textContent = data.workspace ? `${data.workspace.name} · Local` : 'No workspace';
    if (path) path.textContent = data.workspace?.path || 'No workspace selected.';
    if (footer) {
      const issues = (data.sources || []).filter(item => item.state && item.state !== 'available');
      footer.textContent = `${(data.projects || []).length} project stores · ${issues.length ? `${issues.length} source notices` : 'Local sources readable'} · Remote details in Delivery`;
    }
  } catch (_) {
    if (name) name.textContent = 'Workspace unavailable';
    if (path) path.textContent = 'Could not verify the selected workspace.';
    if (footer) footer.textContent = 'Workspace unavailable';
  }
})();
