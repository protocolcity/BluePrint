(async () => {
  const {safeReturnTo} = await import('/js/reader-navigation.mjs');
  const {backLabel, paintOutline, setTrustedHtml} = await import('/js/nav-shell.mjs');

  const $ = id => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const project = params.get('project') || '';
  let papers = [];
  let catalogScroll = 0;
  const back = $('reader-back');
  const defaultReturn = project ? `/projects?project=${encodeURIComponent(project)}` : '/projects';
  back.href = safeReturnTo(params.get('return_to') || defaultReturn);
  back.textContent = backLabel(new URL(back.href, location.href).pathname);

  async function openPaper(path, focus = true) {
    try {
      const response = await fetch('/api/document?' + new URLSearchParams({project, path}));
      const paper = await response.json();
      if (!response.ok) throw new Error(paper.error);
      $('paper-title').textContent = paper.title;
      $('paper-source').textContent = `${paper.path} · ${paper.exposure}`;
      if (paper.content_html) setTrustedHtml($('paper-content'), paper.content_html);
      else $('paper-content').textContent = paper.content || '';
      paintOutline($('paper-outline'), paper.content_outline);
      $('paper-reader').hidden = false;
      history.replaceState(null, '', '/documents?' + new URLSearchParams({
        project,
        path,
        ...(params.get('return_to') ? {return_to: params.get('return_to')} : {}),
      }));
      if (focus) {
        $('paper-title').focus();
        $('paper-reader').scrollIntoView({block: 'start'});
      }
    } catch (error) {
      $('document-status').textContent = error.message || 'Document could not be loaded.';
    }
  }

  function paint() {
    const q = $('document-search').value.toLowerCase();
    const container = $('paper-catalog');
    container.replaceChildren();
    for (const layer of ['Product', 'System', 'Operations', 'Development']) {
      const matches = papers.filter(p => p.layer === layer && `${p.title} ${p.path}`.toLowerCase().includes(q));
      if (!matches.length) continue;
      const section = document.createElement('section');
      const heading = document.createElement('h2');
      heading.textContent = layer;
      section.append(heading);
      for (const paper of matches) {
        const link = document.createElement('a');
        link.className = 'bp-paper-row';
        link.href = '/documents?' + new URLSearchParams({project, path: paper.path});
        link.textContent = paper.path;
        link.addEventListener('click', event => {
          if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
          event.preventDefault();
          catalogScroll = document.scrollingElement?.scrollTop || 0;
          openPaper(paper.path);
        });
        section.append(link);
      }
      container.append(section);
    }
    if (!container.children.length) container.textContent = 'No matching papers.';
  }

  $('document-search').addEventListener('input', paint);
  $('paper-back').addEventListener('click', event => {
    event.preventDefault();
    $('paper-reader').hidden = true;
    history.replaceState(null, '', '/documents?' + new URLSearchParams({
      project,
      ...(params.get('return_to') ? {return_to: params.get('return_to')} : {}),
    }));
    window.scrollTo({top: catalogScroll, behavior: document.body.classList.contains('bp-reduce-motion') ? 'auto' : 'smooth'});
    $('document-search').focus({preventScroll: true});
  });

  try {
    const response = await fetch('/api/documents?' + new URLSearchParams({project}));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    papers = data.papers;
    $('document-project').textContent = `${data.name} · Papers`;
    $('document-status').textContent = `${papers.length} existing documents${data.truncated ? ' · first 500 shown' : ''}`;
    paint();
    if (params.get('path')) await openPaper(params.get('path'), false);
  } catch (error) {
    $('document-status').textContent = error.message || 'Project papers unavailable.';
  }
})();
