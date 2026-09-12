/* All source content is rendered as text. No source value becomes HTML. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const route = location.pathname.replace(/\/$/, '') || '/';
const page = ({'/':'overview','/overview':'overview','/work':'work','/projects':'projects','/agents':'agents','/connections':'connections','/activity':'activity','/calendar':'calendar','/settings':'settings'})[route] || 'overview';
const titles = {activity:['Activity','Verified repository activity across your projects.'],calendar:['Calendar','Agent schedules and local events, with their sources visible.'],settings:['Settings','Display preferences and the application you are actually running.'],overview:['Overview','What needs you, what is moving, and what this desk can verify.'],work:['Work','Find an open work order, see its context, and read the full history.'],projects:['Projects','Project stores connected to this workspace.'],agents:['Agents','Registered local agents, schedules, and reported runtime state.'],connections:['Connections','Where the information comes from and how current it is.']};
let snapshot = null, pending = false, lastSuccess = null, lastAttempt = 0, lastError = false, pageIndex = 0, fingerprint = '';
const size = 25;
let remotePending = false, remoteLast = 0;
let interval = 15, motion = 'system';
try { const saved=JSON.parse(localStorage.getItem('bp-display') || '{}');if([0,15,30].includes(saved.interval))interval=saved.interval;if(saved.motion==='off')motion='off'; } catch(error) { /* Unavailable storage uses defaults. */ }
$('refresh-preference').value=String(interval);$('motion-preference').value=motion;
document.body.classList.toggle('bp-reduce-motion',motion==='off');
const query = new URLSearchParams(location.search);
$('search').value = query.get('q') || '';
for(const [gate,label] of Object.entries({deferred:'Deferred',timer:'Timer gate',tracking:'Tracking'})) {
  const existing=Array.from($('status-filter').options).find(option=>option.value===gate);
  if(existing) existing.value='gate:'+gate;
  else $('status-filter').add(new Option(label,'gate:'+gate));
}
$('status-filter').value = query.get('status')==='deferred' ? 'gate:deferred' : query.get('status') || '';
let selectedProject = query.get('project') || '';
$('page-title').textContent = titles[page][0];
$('page-description').textContent = titles[page][1];
document.title = `BluePrint · ${titles[page][0]}`;
$(page + '-view').hidden = false;
document.querySelector(`[data-page="${page}"]`).setAttribute('aria-current','page');
function el(tag, text, cls) { const node = document.createElement(tag); if(text !== undefined) node.textContent = text; if(cls) node.className = cls; return node; }
function link(text, href, cls) { const node = el('a',text,cls); node.href=href; return node; }
function badge(state, text) { const node=el('span',text || state.replaceAll('_',' '),'bp-badge'); node.dataset.state=state; return node; }
function date(value) { if(!value) return 'Not reported'; const d=new Date(value); return Number.isNaN(d.valueOf()) ? 'Not reported' : d.toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}); }
function empty(parent, text) { parent.append(el('p',text,'bp-empty')); }
function scheduleLabel(value) { if(value==='manual')return 'Manual';if(!value || value==='Not scheduled')return 'Not scheduled';return 'Automatic schedule'; }
function workUrl(order) { return '/work-order?' + new URLSearchParams({project:order.project,id:order.id}); }
function orderRow(order) {
  const row=link('',workUrl(order),'bp-order');
  const content=el('div'); content.append(el('strong',order.title));
  content.append(el('span',`${order.project_name} · ${order.id} · ${order.owner} · ${date(order.updated_at)}`,'bp-order-meta'));
  if(order.gate_note) content.append(el('span',order.gate_note.length > 160 ? order.gate_note.slice(0,157) + '…' : order.gate_note,'bp-order-note'));
  const gateLabel={deferred:'Deferred',timer:'Timer gate',tracking:'Tracking'}[order.gate_type];
  row.append(content,badge(order.attention ? 'attention' : order.status, order.attention ? 'Needs you' : undefined));
  if(gateLabel) row.append(badge(order.gate_type,gateLabel));
  return row;
}
function sources(parent, details) {
  parent.replaceChildren();
  for(const source of snapshot.sources) {
    const row=el('div',undefined,'bp-source'); row.append(el('span',source.name),badge(source.state));
    if(details) row.append(el('p',source.detail + (source.last_at ? ` Last tick: ${date(source.last_at)}` : ''),'bp-muted'));
    parent.append(row);
  }
}
function projectCard(project) {
  const card=el('article',undefined,'bp-project');
  card.append(el('strong',project.name));
  card.append(el('p',project.state==='available' ? `${project.open} open · ${project.attention} need you` : 'Store unavailable'));
  card.append(el('span',project.folder || 'Folder mapping not found','bp-muted'));
  const actions=el('div',undefined,'bp-project-actions');actions.append(link('Open work','/work?'+new URLSearchParams({project:project.id})),link('Project papers','/documents?'+new URLSearchParams({project:project.id})));card.append(actions);
  return card;
}
function overview() {
  const orders=snapshot.orders, attention=orders.filter(x=>x.attention);
  const metrics=[['Needs you',attention.length,'/work?status=attention'],['In progress',orders.filter(x=>x.status==='in_progress').length,'/work?status=in_progress'],['Open work',snapshot.projects.filter(x=>x.state==='available').reduce((sum,p)=>sum+p.open,0),'/work'],['Agents & jobs',snapshot.agents.length,'/agents']];
  $('metrics').replaceChildren(...metrics.map(([label,count,href])=>{const a=link('',href,'bp-metric');a.append(el('strong',String(count)),el('span',label));return a;}));
  const list=$('attention-list');list.replaceChildren(...attention.slice(0,6).map(orderRow));
  if(!attention.length) empty(list,'No work orders explicitly waiting on you in the readable stores.');
  sources($('source-list'),false);
  const projects=[...snapshot.projects].sort((a,b)=>b.attention-a.attention || b.open-a.open);
  $('project-summary').replaceChildren(...projects.slice(0,6).map(projectCard));
  if(!projects.length) empty($('project-summary'),'No project stores found. Inspect Connections for source details.');
}
function filterOptions() {
  const select=$('project-filter');
  select.replaceChildren(new Option('All projects',''));
  for(const project of snapshot.projects) select.add(new Option(project.name,project.id));
  if(selectedProject && !snapshot.projects.some(p=>p.id===selectedProject)) select.add(new Option(selectedProject + ' (unavailable)', selectedProject));
  select.value=selectedProject;
  const status=$('status-filter'), current=status.value;
  for(const name of new Set(snapshot.orders.map(o=>o.status))) {
    if(!Array.from(status.options).some(option=>option.value===name)) status.add(new Option(name.replaceAll('_',' '),name));
  }
  status.value=current;
}
function work() {
  const q=$('search').value.trim().toLowerCase(), status=$('status-filter').value;
  const orders=snapshot.orders.filter(o=>(!selectedProject || o.project===selectedProject) && (!status || (status==='attention'?o.attention:status.startsWith('gate:')?o.gate_type===status.slice(5):o.status===status)) && (!q || `${o.id} ${o.title} ${o.project_name} ${o.owner}`.toLowerCase().includes(q)));
  const pages=Math.max(1,Math.ceil(orders.length/size));pageIndex=Math.min(pageIndex,pages-1);
  $('work-list').replaceChildren(...orders.slice(pageIndex*size,(pageIndex+1)*size).map(orderRow));
  if(!orders.length) empty($('work-list'),'No matching open work. Try another project, status, or search.');
  $('results').textContent=`${orders.length} matching work order${orders.length===1?'':'s'}`;
  $('page-count').textContent=`Page ${pageIndex+1} of ${pages}`;
  $('previous').disabled=pageIndex===0;$('next').disabled=pageIndex>=pages-1;
}
function agents() {
  $('agent-list').replaceChildren();
  for(const agent of snapshot.agents) {
    const card=el('article',undefined,'bp-panel');const heading=el('div',undefined,'bp-section-head');heading.append(el('h2',agent.name),badge(agent.state));card.append(heading);
    const facts=el('dl',undefined,'bp-facts');
    for(const [name,value] of [['Identity',agent.id],['Type',agent.kind],['Configuration',agent.configuration],['Schedule',scheduleLabel(agent.schedule)],['Next run',agent.schedule==='manual'?'On demand':date(agent.next_fire)],['Model',agent.model],['Scheduler heartbeat',date(agent.last_at)]]) facts.append(el('dt',name),el('dd',value));
    card.append(facts,link('Find assigned work','/work?'+new URLSearchParams({q:agent.id}),'bp-order-meta'));
    const dispatch=el('button',agent.state==='working'?'Running':'Dispatch now');
    dispatch.type='button';dispatch.disabled=!agent.configured || ['working','unknown','off'].includes(agent.state);
    const feedback=el('p','','bp-muted');feedback.setAttribute('role','status');
    dispatch.addEventListener('click',async()=>{
      dispatch.disabled=true;dispatch.textContent='Dispatching…';feedback.textContent='';
      try {
        const response=await fetch('/api/agents/dispatch',{method:'POST',headers:{'Content-Type':'application/json','X-BluePrint-Action':'agent-dispatch'},body:JSON.stringify({identity:agent.id})});
        const result=await response.json();
        if(!response.ok || !result.ok) throw new Error(result.error || 'Dispatch was not confirmed. Refresh before retrying.');
        feedback.textContent=result.message || 'Dispatch accepted. Refresh to see progress.';dispatch.textContent='Dispatched';
      } catch(error) {feedback.textContent=error.message;dispatch.textContent='Refresh to retry';}
    });
    card.append(dispatch,feedback);
    if(agent.last_run) card.append(el('p',`Last run: ${agent.last_run.outcome} · ${date(agent.last_run.at)} · ${agent.last_run.reason}`,'bp-note bp-muted'));
    if(agent.report) {
      const report=el('div',undefined,'bp-note');report.append(badge(agent.report.state),el('p',agent.report.summary),el('p',`${date(agent.report.observed_at)} · ${agent.report.mode}`,'bp-muted'),el('p',agent.report.detail,'bp-muted'));card.append(report);
    }
    $('agent-list').append(card);
  }
  if(!snapshot.agents.length) empty($('agent-list'),'No local agents found in the readable registry.');
}
function calendar() {
  const dated=$('dated-work');dated.replaceChildren();
  for(const event of [...(snapshot.work_dates || [])].sort((a,b)=>a.dtstart.localeCompare(b.dtstart))) {
    const row=link('', '/work-order?'+new URLSearchParams({project:event.product,id:event.task_id}),'bp-order');
    const details=el('div');details.append(el('strong',event.summary),el('span',`${event.all_day?event.dtstart+' · All day':date(event.dtstart)} · ${event.product} · ${event.kind==='timer'?'Hold until':'Due'}`,'bp-order-meta'));
    row.append(details,badge(event.attention?'attention':'scheduled',event.attention?'Needs you':'Dated work'));dated.append(row);
  }
  if(!dated.children.length)empty(dated,'No dated work orders in the readable stores.');
  const schedules=$('schedule-list');schedules.replaceChildren();
  for(const agent of [...snapshot.agents].sort((a,b)=>String(a.next_fire || 'z').localeCompare(String(b.next_fire || 'z')))) {
    const row=el('div',undefined,'bp-source');row.append(el('strong',agent.name),badge(agent.state==='unknown'?'unknown':(agent.state==='off'?'off':(agent.next_fire?'scheduled':'not_scheduled'))));
    row.append(el('p',`${date(agent.next_fire)} · ${scheduleLabel(agent.schedule)}`,'bp-muted'));schedules.append(row);
  }
  if(!snapshot.agents.length)empty(schedules,'No agent schedules available.');
  const events=$('event-list');events.replaceChildren();
  for(const event of [...snapshot.events].sort((a,b)=>String(a.at).localeCompare(String(b.at)))) {
    const row=el('details',undefined,'bp-event');const summary=el('summary');summary.append(el('strong',event.title || 'Untitled event'),el('span',`${date(event.at)} · ${event.source || 'Local calendar'} · ${event.state || 'State not specified'}`,'bp-order-meta'));row.append(summary,el('p',event.notes || 'No additional notes.','bp-note bp-muted'));events.append(row);
  }
  if(!snapshot.events.length)empty(events,'No local calendar events. Agent schedules above are independent of the calendar file.');
}
function paint() {
  const workspace=snapshot.workspace;
  $('desk-name').textContent=workspace ? `${workspace.name} · Local` : 'No workspace';
  $('scope-path').textContent=workspace?.path || 'Start BluePrint with a workspace selected.';
  const issues=snapshot.sources.filter(s=>!['available','fresh','not_configured'].includes(s.state));
  $('source-warning').hidden=!issues.length && !snapshot.truncated;
  $('source-warning').textContent=issues.length ? `Some sources need attention: ${issues.map(s=>`${s.name} (${s.state})`).join(', ')}. Counts may be incomplete.` : 'Large stores are limited to 2,000 open records each. Filtered counts may be incomplete.';
  $('footer-status').textContent=`${snapshot.projects.length} project stores · ${issues.length ? `${issues.length} source notices` : 'Local sources readable'} · Remote details in Activity`;
  filterOptions();
  if(page==='overview') overview();
  if(page==='work') work();
  if(page==='projects') { $('projects-view').replaceChildren(...snapshot.projects.map(projectCard));if(!snapshot.projects.length) empty($('projects-view'),'No local project stores found.'); }
  if(page==='agents') agents();
  if(page==='calendar') calendar();
  if(page==='settings') { $('settings-build').textContent=snapshot.build;$('settings-workspace').textContent=snapshot.workspace?.path || 'Not selected'; }
  if(page==='connections') { sources($('connection-list'),true);const excluded=snapshot.excluded_stores || []; if(excluded.length) $('connection-list').append(el('p','Excluded unregistered databases: ' + excluded.join(', ') + '. These are not counted as active projects.','bp-note bp-muted'));$('refresh-description').textContent=interval ? `Every ${interval} seconds while this page is visible` : 'Manual refresh only';$('build').textContent=snapshot.build;$('workspace-path').textContent=workspace?.path || 'Not selected'; }
}
function freshness() {
  const status=$('freshness');
  status.dataset.state=lastError?'error':'ok';
  status.textContent=lastSuccess ? `${lastError?'Refresh failed · showing last read':'Updated'} ${Math.floor((Date.now()-lastSuccess)/1000)}s ago${document.hidden?' · paused':''}` : (lastError?'Unable to read workspace. Retry with Refresh.':'Connecting…');
}
async function refreshRemote() {
  if(remotePending || !['activity','connections'].includes(page)) return;
  remotePending=true;remoteLast=Date.now();
  try {
    const response=await fetch('/api/remote-activity',{cache:'no-store',signal:AbortSignal.timeout(10000)});
    if(!response.ok)throw new Error('Unavailable');
    const data=await response.json();
    const status=data.refreshing ? 'Refreshing GitHub evidence…' : `GitHub: ${data.state.replaceAll('_',' ')}`;
    $('github-connection-status').textContent=status;
    $('remote-status').textContent=status + (data.error ? ' · '+data.error : '');
    const container=$('remote-repositories');
    container.replaceChildren();
    for(const repo of data.repositories || []) {
      const section=el('section',undefined,'bp-panel');const heading=el('div',undefined,'bp-section-head');
      heading.append(el('h2',repo.repo),badge(repo.state));section.append(heading);
      section.append(el('p',`${repo.role || 'Repository'} · ${repo.private===true?'Private':repo.private===false?'Public':'Visibility unknown'} · Observed ${date(repo.observed_at)}`,'bp-muted'));
      if(repo.error)section.append(el('p',repo.error,'bp-warning'));
      if(repo.missing?.length)section.append(el('p','Unavailable evidence: '+repo.missing.join(', '),'bp-warning'));
      for(const item of repo.items || []) {
        let url;try{url=new URL(item.url);}catch(error){continue;}
        if(url.protocol!=='https:' || url.hostname!=='github.com')continue;
        const row=link('',url.href,'bp-order');row.target='_blank';row.rel='noopener noreferrer';const text=el('div');
        text.append(el('strong',item.title),el('span',`${item.kind.replaceAll('_',' ')} · ${date(item.updated_at)}${item.sha?' · '+item.sha.slice(0,7):''}`,'bp-order-meta'));
        row.append(text,badge(item.state));section.append(row);
      }
      if(!(repo.items || []).length)empty(section,repo.state==='connected'?'No open pull requests, recent workflow runs, or published releases returned.':'No verified activity available.');
      container.append(section);
    }
    if(!data.repositories?.length && !data.refreshing)empty(container,'No repository activity available. Check connection configuration or GitHub access.');
  } catch(error) { $('remote-status').textContent='GitHub refresh failed. Previously displayed evidence may be stale.';$('github-connection-status').textContent='GitHub unavailable'; }
  finally { remotePending=false; }
}
async function refresh() {
  if(pending) return;
  lastAttempt=Date.now();pending=true;$('refresh').disabled=true;$('refresh').textContent='Refreshing…';
  try {
    const response=await fetch('/api/operations',{cache:'no-store',signal:AbortSignal.timeout(10000)});
    if(!response.ok) throw new Error('Source request failed');
    const next=await response.json();
    const key=JSON.stringify(page==='work' ? {orders:next.orders,projects:next.projects,workspace:next.workspace,sources:next.sources.map(s=>({name:s.name,state:s.state})),truncated:next.truncated} : {...next,observed_at:null});
    snapshot=next;lastSuccess=Date.now();lastError=false;
    if(key!==fingerprint) { paint();fingerprint=key;const view=$(page+'-view');view.classList.remove('bp-updated');void view.offsetWidth;view.classList.add('bp-updated'); }
  } catch(error) { lastError=true; }
  finally { pending=false;$('refresh').disabled=false;$('refresh').textContent='Refresh';freshness(); }
}
function updateFilters() {
  selectedProject=$('project-filter').value;pageIndex=0;
  const params=new URLSearchParams();if(selectedProject)params.set('project',selectedProject);if($('status-filter').value)params.set('status',$('status-filter').value);if($('search').value)params.set('q',$('search').value);
  history.replaceState(null,'',location.pathname+(params.size?'?'+params:''));if(snapshot)work();
}
$('filters').addEventListener('submit',event=>event.preventDefault());
$('search').addEventListener('input',updateFilters);$('project-filter').addEventListener('change',updateFilters);$('status-filter').addEventListener('change',updateFilters);
$('previous').addEventListener('click',()=>{pageIndex--;work();});$('next').addEventListener('click',()=>{pageIndex++;work();});$('refresh').addEventListener('click',()=>{refresh();refreshRemote();});
document.addEventListener('keydown',event=>{if(event.key==='Escape')$('desk-scope').open=false;});
document.addEventListener('click',event=>{if(!$('desk-scope').contains(event.target))$('desk-scope').open=false;});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();freshness();});
$('preferences').addEventListener('submit',event=>event.preventDefault());
$('preferences').addEventListener('change',()=>{interval=Number($('refresh-preference').value);motion=$('motion-preference').value;document.body.classList.toggle('bp-reduce-motion',motion==='off');try{localStorage.setItem('bp-display',JSON.stringify({interval,motion}));$('preference-status').textContent='Saved in this browser.';}catch(error){$('preference-status').textContent='Applied for this page; browser storage is unavailable.';}});
setInterval(()=>{if(interval && !document.hidden && Date.now()-lastAttempt>=interval*1000)refresh();},1000);setInterval(freshness,1000);setInterval(()=>{if(!document.hidden && Date.now()-remoteLast>15000)refreshRemote();},1000);refresh();refreshRemote();
})();
