/* Shared source projection only: Map never owns work or dispatch. */
(async()=>{
  const {connectChanges} = await import('/js/change-feed.mjs');
  const name=document.getElementById('desk-name'), path=document.getElementById('scope-path');
  const context=document.getElementById('map-project-context');
  try { document.body.classList.toggle('bp-reduce-motion', JSON.parse(localStorage.getItem('bp-display') || '{}').motion === 'off'); } catch (_) { /* System preference applies when storage is unavailable. */ }
  let data=null, locationPath=new URLSearchParams(location.search).get('path') || '';
  document.getElementById('refresh')?.addEventListener('click',()=>location.reload());
  async function load() {
    try {
      const response=await fetch('/api/operations');if(!response.ok)throw new Error();
      data=await response.json();name.textContent=data.workspace ? data.workspace.name+' · Local' : 'No workspace';path.textContent=data.workspace?.path || 'No workspace selected.';render();
    } catch(error) {name.textContent='Workspace unavailable';path.textContent='Could not verify the selected workspace.';if(context)context.textContent='Work source unavailable.';}
  }
  function render() {
    if(!context || !data)return;
    context.replaceChildren();
    const project=data.projects.find(p=>locationPath===p.folder || locationPath.startsWith(p.folder+'/'));
    const heading=document.createElement('strong');heading.textContent=project?.name || 'Workspace work';context.append(heading);
    const orders=data.orders.filter(o=>!project || o.project===project.id);
    const unavailable=project ? project.state!=='available' : data.sources.some(s=>s.name==='WorkLane' && s.state!=='available');
    const summary=document.createElement('p');
    const count=project ? project.open : data.projects.reduce((n,p)=>n+p.open,0);
    summary.textContent=unavailable ? 'Work source unavailable; counts are incomplete.' : `${count} open · ${orders.filter(o=>['deferred','tracking'].includes(o.gate_type)).length} deferred/tracking · ${orders.filter(o=>o.status==='in_progress').length} in progress`;
    if(data.truncated)summary.textContent+=' · Partial detail';
    context.append(summary);
    const links=document.createElement('nav');links.setAttribute('aria-label','Project context');
    const query=project ? '?project='+encodeURIComponent(project.id) : '';
    const entries=[['Work','/work'+query],['Needs you','/work'+(query ? query+'&' : '?')+'status=attention'],['Agents and jobs','/agents'],['Papers',project ? '/documents'+query : '/projects']];
    if(project?.has_instructions)entries.push(['Instructions','/map?'+new URLSearchParams({path:project.folder,md:project.folder+'/AGENTS.md'})]);
    for(const [label,href] of entries){const a=document.createElement('a');a.textContent=label;a.href=href;links.append(a);}
    context.append(links);
    const note=document.createElement('small');note.textContent='Status is not agent liveness. Read '+new Date(data.observed_at).toLocaleTimeString();context.append(note);
  }
  document.addEventListener('bp:map-location',event=>{locationPath=event.detail.path;render();});
  connectChanges(()=>{if(!document.hidden)load();});
  await load();
})();
