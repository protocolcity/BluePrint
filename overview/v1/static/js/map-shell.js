/* Shared source projection only: Map never owns work or dispatch. */
(async()=>{
  const {connectChanges} = await import('/js/change-feed.mjs');
  const name=document.getElementById('desk-name'), path=document.getElementById('scope-path');
  const context=document.getElementById('map-project-context');
  try { document.body.classList.toggle('bp-reduce-motion', JSON.parse(localStorage.getItem('bp-display') || '{}').motion === 'off'); } catch (_) { /* System preference applies when storage is unavailable. */ }
  let data=null, locationPath=new URLSearchParams(location.search).get('path') || '', lastLoad=0, renderFingerprint='', noteEl=null;
  document.getElementById('refresh')?.addEventListener('click',()=>location.reload());
  async function load() {
    lastLoad=Date.now();
    try {
      const response=await fetch('/api/operations');if(!response.ok)throw new Error();
      data=await response.json();
      try { document.dispatchEvent(new CustomEvent('bp:map-operations',{detail:data})); } catch (_) { /* Map host subscribes when present. */ }
      name.textContent=data.workspace ? data.workspace.name+' · Local' : 'No workspace';path.textContent=data.workspace?.path || 'No workspace selected.';render();
    } catch(error) {name.textContent='Workspace unavailable';path.textContent='Could not verify the selected workspace.';if(context)context.textContent='Work source unavailable.';}
  }
  function noteText() { return 'Status is not agent liveness. Read '+new Date(data.observed_at).toLocaleTimeString(); }
  function render() {
    if(!context || !data)return;
    const project=data.projects.find(p=>locationPath===p.folder || locationPath.startsWith(p.folder+'/'));
    const unavailable=project ? project.state!=='available' : data.sources.some(s=>s.name==='WorkLane' && s.state!=='available');
    const count=project ? project.open : data.projects.reduce((n,p)=>n+p.open,0);
    const attention=project ? (project.attention||0) : data.projects.reduce((n,p)=>n+(p.attention||0),0);
    const claimed=project ? (project.claimed||0) : data.projects.reduce((n,p)=>n+(p.claimed||0),0);
    const running=project ? (project.running||0) : data.projects.reduce((n,p)=>n+(p.running||0),0);
    const key=JSON.stringify([project?.id,unavailable,count,attention,claimed,running,data.truncated,project?.has_instructions]);
    if(key===renderFingerprint) { if(noteEl)noteEl.textContent=noteText(); return; }
    try {
      context.replaceChildren();
      const heading=document.createElement('strong');heading.textContent=project?.name || 'Workspace work';context.append(heading);
      const summary=document.createElement('p');
      summary.textContent=unavailable ? 'Work source unavailable; counts are incomplete.' : `${count} open · ${attention} For You · ${running} running · ${claimed} claimed`;
      if(data.truncated)summary.textContent+=' · Partial detail';
      context.append(summary);
      const links=document.createElement('nav');links.setAttribute('aria-label','Project context');
      const query=project ? '?project='+encodeURIComponent(project.id) : '';
      const entries=[['Work','/work'+query],['Needs you','/work'+(query ? query+'&' : '?')+'attention=any'],['Agents and jobs','/agents'],['Papers',project ? '/documents'+query : '/projects']];
      if(project?.has_instructions)entries.push(['Instructions','/map?'+new URLSearchParams({path:project.folder,md:project.folder+'/AGENTS.md'})]);
      for(const [label,href] of entries){const a=document.createElement('a');a.textContent=label;a.href=href;links.append(a);}
      context.append(links);
      const note=document.createElement('small');note.textContent=noteText();context.append(note);
      noteEl=note;
      renderFingerprint=key;
    } catch(error) {
      renderFingerprint='';
      throw error;
    }
  }
  document.addEventListener('bp:map-location',event=>{locationPath=event.detail.path;render();});
  connectChanges(()=>{if(!document.hidden)load();});
  setInterval(()=>{if(!document.hidden && Date.now()-lastLoad>=60000)load();},1000);
  await load();
})();
