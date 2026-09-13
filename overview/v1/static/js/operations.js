/* All source content is rendered as text. No source value becomes HTML. */
(async () => {
'use strict';
const {readerHref} = await import('/js/reader-navigation.mjs');
const {connectChanges} = await import('/js/change-feed.mjs');
const {reconcileList} = await import('/js/dom-reconcile.mjs');
const $ = id => document.getElementById(id);
const route = location.pathname.replace(/\/$/, '') || '/';
const page = ({'/':'overview','/overview':'overview','/work':'work','/projects':'projects','/agents':'agents','/connections':'connections','/delivery':'delivery','/activity':'delivery','/timeline':'timeline','/calendar':'calendar','/settings':'settings'})[route] || 'overview';
const titles = {delivery:['Delivery','Pull requests, CI and releases reported by GitHub; not agent activity.'],timeline:['Timeline','WorkLane events, WorkForce shifts, supervisor passes and GitHub delivery in one labelled stream.'],calendar:['Calendar','Agent schedules and local events, with their sources visible.'],settings:['Settings','Display preferences and the application you are actually running.'],overview:['Overview','What needs you, what is moving, and what this desk can verify.'],work:['Work','Find an open work order, see its context, and read the full history.'],projects:['Projects','Project stores connected to this workspace.'],agents:['Agents',''],connections:['Connections','Where the information comes from, whether it is reachable and usable, and how current it is.']};
let snapshot = null, pending = false, lastSuccess = null, lastAttempt = 0, lastError = false, pageIndex = 0, fingerprint = '';
const size = 25;
let muted={};try {muted=JSON.parse(localStorage.getItem('bp-attention-mutes') || '{}');}catch(error){}
function muteKey(order){return JSON.stringify([snapshot?.workspace?.path,order.project,order.id]);}
function saveMutes(){try{localStorage.setItem('bp-attention-mutes',JSON.stringify(muted));}catch(error){}}
$('restore-muted').addEventListener('click',()=>{for(const order of snapshot.orders)delete muted[muteKey(order)];saveMutes();overview();});
let remotePending = false, remoteLast = 0;
let timelineData = null, timelinePending = false, timelineCursor = '', timelineMore = false;
let timelineProject = '', timelineSource = '', timelineActor = '';
let streamState = 'connecting', everOpened = false, consecutiveErrors = 0, lastChangeAt = null;
let interval = 15, motion = 'system';
try { const saved=JSON.parse(localStorage.getItem('bp-display') || '{}');if([0,15,30].includes(saved.interval))interval=saved.interval;if(saved.motion==='off')motion='off'; } catch(error) { /* Unavailable storage uses defaults. */ }
$('refresh-preference').value=String(interval);$('motion-preference').value=motion;
document.body.classList.toggle('bp-reduce-motion',motion==='off');
const query = new URLSearchParams(location.search);
timelineProject = query.get('project') || '';
timelineSource = query.get('source') || '';
timelineActor = query.get('actor') || '';
$('search').value = query.get('q') || '';
// Compatible mapping for pre-pc-1482 links: status carried gate/attention
// values and a deferred=1 toggle; those axes now have their own filters
// (STATES_AND_TERMS.md §5) and Status holds lifecycle words only.
let statusParam = query.get('status') || '';
let gateParam = query.get('gate') || '';
let attentionParam = query.get('attention') || '';
let blockedParam = query.get('blocked') === '1';
let legacyParam = false;
if (statusParam.startsWith('gate:')) { gateParam = gateParam || statusParam.slice(5); statusParam = ''; legacyParam = true; }
else if (statusParam === 'deferred') { gateParam = gateParam || 'deferred'; statusParam = ''; legacyParam = true; }
else if (statusParam.startsWith('face:')) { attentionParam = attentionParam || statusParam.slice(5); statusParam = ''; legacyParam = true; }
else if (statusParam === 'attention') { attentionParam = attentionParam || 'any'; statusParam = ''; legacyParam = true; }
else if (statusParam === 'blocked') { blockedParam = true; statusParam = ''; legacyParam = true; }
if (query.get('deferred') === '1') { gateParam = gateParam || 'deferred'; legacyParam = true; }
$('status-filter').value = statusParam;
$('gate-filter').value = gateParam;
$('attention-filter').value = attentionParam;
$('blocked-filter').checked = blockedParam;
let selectedProject = query.get('project') || '';
let selectedAssignment = query.get('assignment') || '';
if (legacyParam) {
  const canonical = new URLSearchParams();
  if (selectedProject) canonical.set('project', selectedProject);
  if (selectedAssignment) canonical.set('assignment', selectedAssignment);
  if (statusParam) canonical.set('status', statusParam);
  if (gateParam) canonical.set('gate', gateParam);
  if (attentionParam) canonical.set('attention', attentionParam);
  if (blockedParam) canonical.set('blocked', '1');
  if (query.get('q')) canonical.set('q', query.get('q'));
  history.replaceState(null, '', location.pathname + (canonical.size ? '?' + canonical : '') + location.hash);
}
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
function deliveryRow(item) {
  if(item.kind==='workflow') {
    const commit=item.sha?item.sha.slice(0,7):'no commit';
    const count=item.count>1?` · ×${item.count}`:'';
    return `CI · ${item.workflow_name || item.title} · ${item.state} · ${commit}${count}`;
  }
  if(item.kind==='pull_request') {
    const event=item.pr_event || (item.state==='open'?'opened':item.state);
    return `PR #${item.number} · ${item.title} · ${event} · ${date(item.updated_at)}`;
  }
  if(item.kind==='release') return `Release · ${item.title} · ${date(item.updated_at)}`;
  return `${item.kind.replaceAll('_',' ')} · ${item.title} · ${date(item.updated_at)}`;
}
function scheduleLabel(value) { if(value==='manual')return 'Manual';if(!value || value==='Not scheduled')return 'Not scheduled';return 'Automatic schedule'; }
function workUrl(order) { return readerHref('/work-order?' + new URLSearchParams({project:order.project,id:order.id})); }
function statusText(order) {
  if(order.status==='in_progress' && order.live_with) return `Live with ${order.live_with} since ${date(order.since)}`;
  if(order.status==='in_review' && order.parked_by) return `Parked by ${order.parked_by} since ${date(order.since)}`;
  return order.status_word || order.status;
}
function orderRow(order) {
  const row=link('',workUrl(order),'bp-order');
  const content=el('div'); content.append(el('strong',order.title));
  content.append(el('span',`${order.project_name} · ${order.id} · ${statusText(order)} · Assigned to ${order.owner} · ${date(order.updated_at)}`,'bp-order-meta'));
  if(order.parent) content.append(el('span',`Part of ${order.parent}`,'bp-order-meta'));
  if(order.blockers && order.blockers.length) content.append(el('span',`Blocked on ${order.blockers.join(', ')}`,'bp-order-note'));
  if(order.ready_for) content.append(el('span',`Ready for ${order.ready_for}`,'bp-order-note'));
  if(order.persona) content.append(el('span',order.persona,'bp-order-note'));
  else if(order.needs_routing) content.append(el('span','Needs routing','bp-order-note'));
  if(order.attention_face && order.face_reason) { const reason=el('span',order.face_reason,'bp-order-note'); reason.title=order.face_reason; content.append(reason); }
  if(order.gate_note) {
    const truncated=order.gate_note.length > 160;
    const details=el('details',undefined,'bp-order-note');
    details.append(el('summary',truncated ? order.gate_note.slice(0,157) + '…' : order.gate_note));
    if(truncated) details.append(el('p',order.gate_note));
    content.append(details);
  }
  if(order.last_note) content.append(el('span',`Last note: ${order.last_note}`,'bp-order-meta'));
  const gateWord=gateLabel(order);
  row.append(content,badge(order.attention_face==='decide' ? 'attention' : order.status, order.attention_face==='decide' ? 'Needs you' : (order.status_word || undefined)));
  if(gateWord) row.append(badge(order.gate_type+(order.gate_expired?'-expired':''),gateWord));
  return row;
}
function gateLabel(order) {
  if(order.gate_type==='deferred') return 'Deferred';
  if(order.gate_type==='tracking') return 'Tracking';
  if(order.gate_type==='timer') return order.gate_expired ? 'Timer expired' : `Held until ${date(order.gate_until)}`;
  if(order.gate_type==='human') return 'Needs a decision';
  return '';
}
const EXCEPTION_STATES = new Set(['unavailable','failed','partial','stale','reachable','unknown']);
function isException(item) {
  if(!item) return false;
  if(EXCEPTION_STATES.has(item.state)) return true;
  return item.reachable===true && item.usable===false && item.state!=='not_configured' && item.state!=='empty';
}
function sourceSeverity(item) {
  if(!item) return 9;
  if(item.state==='unavailable' || item.state==='failed') return 0;
  if(item.state==='partial' || item.state==='stale' || item.state==='reachable') return 1;
  if(item.state==='unknown') return 2;
  if(item.state==='empty') return 3;
  if(item.state==='not_configured') return 4;
  return 5;
}
function capabilityState(record) {
  if(record.reachable===true && record.usable===false && record.state!=='not_configured' && record.state!=='empty') {
    return record.state==='failed' ? 'failed' : (record.state || 'reachable');
  }
  return record.state || 'unavailable';
}
function capabilityText(state) {
  if(state==='not_configured') return 'not configured';
  if(state==='last_run_failed') return 'last run failed';
  return String(state || 'unavailable').replaceAll('_',' ');
}
function capabilityBits(record) {
  const bits=[];
  if(record.detail) bits.push(record.detail);
  if(record.outcome) {
    const outcome=String(record.outcome).replaceAll('_',' ');
    if(!(record.detail || '').toLowerCase().includes(outcome)) bits.push('Last outcome '+outcome);
  }
  if(record.activated_at) bits.push('Activated '+date(record.activated_at));
  else if(record.version) bits.push('Version '+record.version);
  if(record.observed_at) bits.push('Last observation '+date(record.observed_at));
  if(record.last_success_at && record.last_success_at!==record.observed_at) bits.push('Last successful observation '+date(record.last_success_at));
  if(record.last_at) bits.push('Last tick: '+date(record.last_at));
  return bits;
}
function rawDetails(record) {
  const bits=[];
  if(record.source) bits.push(record.source);
  if(record.version) bits.push('version '+record.version);
  if(record.http_status) bits.push('HTTP '+record.http_status);
  if(record.reachable===true) bits.push('reachable');
  else if(record.reachable===false) bits.push('not reachable');
  if(record.usable===true) bits.push('usable');
  else if(record.usable===false) bits.push('not usable');
  return bits.join(' · ');
}
function connectionRow(name, record, mode) {
  const state=capabilityState(record);
  const exception=isException(record);
  const compact=mode==='compact' && !exception;
  const row=el('div',undefined,'bp-source'+(compact?' bp-source-compact':''));
  row.append(el('span',name),badge(state, capabilityText(state)));
  const bits=capabilityBits(record);
  if(bits.length && (mode!=='compact' || exception)) row.append(el('p',bits.join(' · '),'bp-muted'));
  if((mode==='exception' || mode==='details') && exception && record.next_step) row.append(el('p','Next: '+record.next_step,'bp-source-next'));
  if(mode==='details' || mode==='exception') {
    const raw=rawDetails(record);
    if(raw) {
      const box=el('details',undefined,'bp-source-raw');
      box.append(el('summary','Endpoint, path and version'));
      box.append(el('p',raw,'bp-muted'));
      row.append(box);
    }
  }
  return row;
}
function sortBySeverity(items, nameOf) {
  return [...items].sort((a,b)=>sourceSeverity(a)-sourceSeverity(b) || String(nameOf(a)).localeCompare(String(nameOf(b))));
}
function engineRows() {
  const engines=snapshot.engines || {};
  return [['WorkLane engine',engines.worklane],['WorkForce engine',engines.workforce],['WorkLane API',engines.worklane_api],['Supervisor last pass',engines.supervisor]].filter(([,engine])=>engine);
}
function sources(parent, details) {
  const rows=sortBySeverity(snapshot.sources || [], s=>s.name);
  reconcileList(parent, rows, s=>s.name, source=>connectionRow(source.name, source, details?'details':'compact'), {emptyText:'No data sources reported.'});
}
function connectionExceptions() {
  const items=[];
  for(const source of snapshot.sources || []) if(isException(source)) items.push({id:'source:'+source.name, name:source.name, record:source});
  for(const [name, engine] of engineRows()) if(isException(engine)) items.push({id:'engine:'+name, name, record:engine});
  reconcileList($('connection-exceptions'), items, item=>item.id, item=>connectionRow(item.name, item.record, 'exception'), {emptyText:'No source exceptions.'});
}
function projectCard(project) {
  const card=el('article',undefined,'bp-project');
  card.append(el('strong',project.name));
  card.append(el('p',project.state==='available' ? `${project.open} open · ${project.attention} need you` : 'Store unavailable'));
  card.append(el('span',project.folder || 'Folder mapping not found','bp-muted'));
  const actions=el('div',undefined,'bp-project-actions');actions.append(link('Open work','/work?'+new URLSearchParams({project:project.id})));
  if(project.attention) actions.append(link('For you','/work?'+new URLSearchParams({project:project.id,attention:'any'})));
  actions.append(link('Project papers','/documents?'+new URLSearchParams({project:project.id})));card.append(actions);
  return card;
}
function faceEntry(order) {
  const entry=el('div');entry.append(orderRow(order));
  const mute=el('button','Mute here for 24 hours');mute.type='button';
  mute.addEventListener('click',()=>{muted[muteKey(order)]=Date.now()+86400000;saveMutes();overview();});
  entry.append(mute);
  return entry;
}
function overview() {
  const orders=snapshot.orders, forYou=orders.filter(o=>o.attention_face);
  const live=orders.filter(o=>o.status==='in_progress' && o.live_with);
  const seats=snapshot.agents.filter(a=>a.group==='seat').length, jobs=snapshot.agents.filter(a=>a.group==='job').length;
  const metrics=[['For You',forYou.length,'/work?attention=any'],['Live',live.length,'/work?status=in_progress'],['Open work',snapshot.projects.filter(x=>x.state==='available').reduce((sum,p)=>sum+p.open,0),'/work'],['Seats · Jobs',`${seats} · ${jobs}`,'/agents']];
  reconcileList($('metrics'), metrics, m=>m[0], ([label,count,href])=>{const a=link('',href,'bp-metric');a.append(el('strong',String(count)),el('span',label));return a;});
  let mutedCount=0;
  for(const face of ['decide','read','watch','note']) {
    const band=forYou.filter(o=>o.attention_face===face);
    const visible=band.filter(o=>!(Number(muted[muteKey(o)])>Date.now()));
    mutedCount+=band.length-visible.length;
    reconcileList($('for-you-'+face), visible.slice(0,6), o=>o.project+':'+o.id, faceEntry, {emptyText:'No '+face+' items visible in the readable stores.'});
  }
  $('for-you-decide-heading').textContent=`Decide · ${forYou.filter(o=>o.attention_face==='decide').length}`;
  $('for-you-read-heading').textContent=`Read · ${forYou.filter(o=>o.attention_face==='read').length}`;
  $('for-you-watch-summary').textContent=`Watch · ${forYou.filter(o=>o.attention_face==='watch').length}`;
  $('for-you-note-summary').textContent=`Note · ${forYou.filter(o=>o.attention_face==='note').length}`;
  $('mute-status').textContent=(mutedCount ? mutedCount+' muted. ' : '')+'Mute only hides this inbox item in this browser; it does not change gates, reminders, or assignments.';
  $('restore-muted').hidden=!orders.some(o=>Number(muted[muteKey(o)])>Date.now());

  sources($('source-list'),false);
  const projects=[...snapshot.projects].sort((a,b)=>b.attention-a.attention || b.open-a.open);
  reconcileList($('project-summary'), projects.slice(0,6), p=>p.id, projectCard, {emptyText:'No project stores found. Inspect Connections for source details.'});
}
function filterOptions() {
  const select=$('project-filter');
  select.replaceChildren(new Option('All projects',''));
  for(const project of snapshot.projects) select.add(new Option(project.name,project.id));
  if(selectedProject && !snapshot.projects.some(p=>p.id===selectedProject)) select.add(new Option(selectedProject + ' (unavailable)', selectedProject));
  select.value=selectedProject;
  const assignment=$('assignment-filter');
  assignment.replaceChildren(new Option('All assignments',''),new Option('You','you'));
  for(const seat of snapshot.agents.filter(a=>a.group==='seat')) assignment.add(new Option(seat.name,'worker:'+seat.id));
  assignment.add(new Option('Unassigned','unassigned'));
  if(selectedAssignment && !Array.from(assignment.options).some(o=>o.value===selectedAssignment)) assignment.add(new Option(selectedAssignment.replace(/^worker:/,''),selectedAssignment));
  assignment.value=selectedAssignment;
  const timelineSelect=$('timeline-project');
  if(timelineSelect) {
    const currentTimeline=timelineSelect.value;
    timelineSelect.replaceChildren(new Option('All projects',''));
    for(const project of snapshot.projects) timelineSelect.add(new Option(project.name,project.id));
    timelineSelect.value=currentTimeline || timelineProject;
  }
}
function matchesAssignment(order, value) {
  if(value==='you') return order.assigned_you;
  if(value==='unassigned') return !order.assigned_you && !order.workers.filter(w=>w!=='you').length;
  return order.workers.includes(value.slice(7));
}
function filterChips() {
  const chips=[];
  if($('search').value) chips.push(['Search: '+$('search').value,()=>{$('search').value='';}]);
  if(selectedProject) { const opt=Array.from($('project-filter').options).find(o=>o.value===selectedProject); chips.push(['Project: '+(opt?opt.text:selectedProject),()=>{$('project-filter').value='';}]); }
  if(selectedAssignment) { const opt=Array.from($('assignment-filter').options).find(o=>o.value===selectedAssignment); chips.push(['Assignment: '+(opt?opt.text:selectedAssignment),()=>{$('assignment-filter').value='';}]); }
  if($('status-filter').value) chips.push(['Status: '+$('status-filter').selectedOptions[0].text,()=>{$('status-filter').value='';}]);
  if($('gate-filter').value) chips.push(['Gate: '+$('gate-filter').selectedOptions[0].text,()=>{$('gate-filter').value='';}]);
  if($('attention-filter').value) chips.push(['For You: '+$('attention-filter').selectedOptions[0].text,()=>{$('attention-filter').value='';}]);
  if($('blocked-filter').checked) chips.push(['Blocked only',()=>{$('blocked-filter').checked=false;}]);
  return chips;
}
function renderActiveFilters() {
  const chips=filterChips(), container=$('active-filters');
  container.replaceChildren();
  for(const [label,clear] of chips) {
    const chip=el('button',label,'bp-filter-chip');chip.type='button';
    chip.addEventListener('click',()=>{clear();updateFilters();});
    container.append(chip);
  }
  $('clear-filters').hidden=!chips.length;
}
function work() {
  const q=$('search').value.trim().toLowerCase(), status=$('status-filter').value, gate=$('gate-filter').value, attention=$('attention-filter').value, blockedOnly=$('blocked-filter').checked;
  const total=snapshot.orders.length;
  const orders=snapshot.orders.filter(o=>(!selectedProject || o.project===selectedProject) && (!selectedAssignment || matchesAssignment(o,selectedAssignment)) && (!status || o.status===status) && (!gate || (gate==='none' ? !o.gate_type : o.gate_type===gate)) && (!attention || (attention==='any' ? o.attention : o.attention_face===attention)) && (!blockedOnly || (o.blockers && o.blockers.length)) && (!q || `${o.id} ${o.title} ${o.project_name} ${o.owner}`.toLowerCase().includes(q)));
  const pages=Math.max(1,Math.ceil(orders.length/size));pageIndex=Math.min(pageIndex,pages-1);
  reconcileList($('work-list'), orders.slice(pageIndex*size,(pageIndex+1)*size), o=>o.project+':'+o.id, orderRow, {emptyText:'No matching open work. Try another project, assignment, status, gate, or search.'});
  $('results').textContent=`${orders.length} of ${total} matching work order${orders.length===1?'':'s'}`;
  renderActiveFilters();
  $('page-count').textContent=`Page ${pageIndex+1} of ${pages}`;
  $('previous').disabled=pageIndex===0;$('next').disabled=pageIndex>=pages-1;
}
function agentAction(agent, dispatchLabel) {
  const nodes=[];
  if(agent.action==='inspect') {
    const button=el('button','Inspect');button.type='button';
    const feedback=el('p','','bp-muted');feedback.setAttribute('role','status');
    button.addEventListener('click',()=>{feedback.textContent=`Shift open past its budget with no terminal row. Inspect ledger/${agent.id}.log before dispatching again.`;});
    nodes.push(button,feedback);
    return nodes;
  }
  if(!agent.action) {
    nodes.push(el('p','No action needed.','bp-muted'));
    return nodes;
  }
  const button=el('button',agent.action==='recover' ? 'Recover' : (dispatchLabel || 'Dispatch now'));
  button.type='button';button.disabled=!agent.configured;
  const feedback=el('p','','bp-muted');feedback.setAttribute('role','status');
  button.addEventListener('click',async()=>{
    button.disabled=true;button.textContent=agent.action==='recover'?'Recovering…':'Dispatching…';feedback.textContent='';
    try {
      const response=await fetch('/api/agents/dispatch',{method:'POST',headers:{'Content-Type':'application/json','X-BluePrint-Action':'agent-dispatch'},body:JSON.stringify({identity:agent.id})});
      const result=await response.json();
      if(!response.ok || !result.ok) throw new Error(result.error || 'Dispatch was not confirmed. Refresh before retrying.');
      feedback.textContent=result.message || 'Dispatch accepted. Refresh to see progress.';button.textContent='Dispatched';
    } catch(error) {feedback.textContent=error.message;button.textContent='Refresh to retry';button.disabled=false;}
  });
  nodes.push(button,feedback);
  return nodes;
}
function agentCard(agent) {
  const card=el('article',undefined,'bp-panel');
  const heading=el('div',undefined,'bp-section-head');
  const title=el('div');title.append(el('h2',agent.name));
  if(agent.group==='seat') title.append(el('span',`${agent.project_name || 'No project queue'} · ${agent.model}`,'bp-muted'));
  title.append(el('p',agent.id,'bp-muted bp-note'));
  heading.append(title,badge(agent.state,agent.badge));
  card.append(heading,el('p',`Source: ${agent.badge_source}`,'bp-muted'));
  if(agent.group==='job') {
    const facts=el('dl',undefined,'bp-facts');
    facts.append(el('dt','Schedule'),el('dd',scheduleLabel(agent.schedule)));
    facts.append(el('dt','Next run'),el('dd',agent.schedule==='manual'?'On demand':date(agent.next_fire)));
    card.append(facts);
  }
  if(agent.group==='seat' && agent.held) card.append(el('p',`Holds ${agent.held.id}${agent.held_verified?' (owner verified)':' (not yet verified)'}${agent.shift && agent.shift.lock_held?' · lock held':''}`,'bp-note'));
  if(agent.shift) card.append(el('p',`${agent.shift.stale?'Shift open past its budget with no terminal row; verify the process before dispatching again':'Shift open'} · since ${date(agent.shift.started_at)} · budget ${agent.shift.budget_secs}s${agent.shift.candidates.length?' · candidates '+agent.shift.candidates.join(', '):''} · ${agent.shift.source}${agent.shift.lock_held?' · lock held':''}`,agent.shift.stale?'bp-note':'bp-note bp-muted'));
  if(agent.report) {
    const report=el('div',undefined,'bp-note');report.append(badge(agent.report.state),el('p',agent.report.summary),el('p',`${date(agent.report.observed_at)} · ${agent.report.mode}`,'bp-muted'),el('p',agent.report.detail,'bp-muted'));card.append(report);
  }
  if(agent.last_run) card.append(el('p',`Last run: ${agent.last_run.outcome} · ${date(agent.last_run.at)} · ${agent.last_run.reason} · ledger/${agent.id}.log`,'bp-note bp-muted'));
  if(agent.group==='seat' && agent.recovery_attempts) card.append(el('p',`Recovery attempts: ${agent.recovery_attempts}`,'bp-note bp-muted'));
  if(agent.group==='seat') card.append(link('Find assigned work','/work?'+new URLSearchParams({assignment:'worker:'+agent.id}),'bp-order-meta'));
  card.append(...agentAction(agent));
  return card;
}
function supervisorPanel() {
  const container=$('supervisor-panel');container.replaceChildren();
  const supervisor=snapshot.supervisor;
  if(!supervisor) { empty(container,'No supervisor registered on this roster.'); return; }
  const heading=el('div',undefined,'bp-section-head');heading.append(el('h2',supervisor.name),badge(supervisor.state,supervisor.badge));container.append(heading);
  container.append(el('p',`Schedule: ${scheduleLabel(supervisor.schedule)}`,'bp-muted'));
  const passList=el('div',undefined,'bp-pass-list');container.append(passList);
  const passes=supervisor.passes || {state:'unavailable',detail:'Supervisor pass record unavailable.',passes:[]};
  if(passes.state==='available') {
    if(!passes.passes.length) empty(passList,'No supervisor passes recorded yet.');
    for(const pass of passes.passes.slice(0,3)) {
      const row=el('div',undefined,'bp-note');
      row.append(el('strong',`${date(pass.generated_at)} · ${pass.mode || 'mode not reported'}`));
      row.append(el('p',`${pass.pass_outcome || 'outcome not reported'} · proposals ${pass.proposals_valid ?? '—'}/${pass.proposals_total ?? '—'} · dispatched ${pass.dispatch_completed ?? 0}/${pass.dispatch_attempted ?? 0}`,'bp-muted'));
      for(const item of pass.dispatched || []) row.append(el('p',`${item.worker} → ${item.project} · ${item.outcome}`,'bp-muted'));
      passList.append(row);
    }
  } else {
    empty(passList, passes.detail || 'Supervisor pass record unavailable.');
  }
  container.append(...agentAction(supervisor,'Run a pass'));
}
function heartbeatLine() {
  const heartbeat=(snapshot.sources || []).find(s=>s.name==='WorkForce heartbeat');
  if(!heartbeat || !heartbeat.last_at || heartbeat.state==='unknown') return 'WorkForce daemon: not reachable';
  const seconds=Math.max(0,Math.floor((Date.now()-new Date(heartbeat.last_at).getTime())/1000));
  const ago=seconds<60?`${seconds}s ago`:`${Math.floor(seconds/60)}m ago`;
  return `WorkForce daemon: seen ${ago}`;
}
function projectStoreState(slug) {
  const project=(snapshot.projects || []).find(p=>p.id===slug);
  if(!project) return 'unknown';
  return project.state==='available' ? 'available' : 'unavailable';
}
function projectOpenCount(slug) {
  if(projectStoreState(slug)!=='available') return null;
  return (snapshot.projects || []).find(p=>p.id===slug).open;
}
function coverageIsActive(row) {
  if(row.present.length || row.held.length) return true;
  if(projectStoreState(row.project)!=='available') return true;
  return projectOpenCount(row.project) > 0;
}
function coverageCompactLine(row) {
  const staffed=[...row.present, ...row.held.map(p=>`${p} off`)];
  let line=`${row.name} · ${staffed.length ? staffed.join(', ') : 'none staffed'}`;
  if(row.missing.length) line+=` · missing ${row.missing.join(', ')}`;
  if(row.not_configured.length) line+=` · not configured: ${row.not_configured.join(', ')}`;
  return line;
}
function paintCoverageHireBody(hire, row) {
  let body=hire.querySelector('.bp-coverage-hire');
  if(!body) { body=el('div',undefined,'bp-coverage-hire'); hire.append(body); }
  body.replaceChildren();
  if(!hire.open) return;
  for(const provider of row.missing) {
    const command=row.hire_commands[provider];
    const wrap=el('p',undefined,'bp-muted');
    const button=el('button','Copy');
    button.type='button';
    button.addEventListener('click',()=>navigator.clipboard.writeText(command));
    wrap.append(`Hire ${provider}: `,el('code',command),' ',button);
    body.append(wrap);
  }
  if(row.not_configured.length) body.append(el('p',row.not_configured.map(p=>`${p}: ${row.install_hints[p]}`).join(' · '),'bp-muted bp-note'));
}
function coverageRow(row) {
  const node=el('div',undefined,'bp-coverage-row');
  node.append(el('p',coverageCompactLine(row),'bp-muted'));
  if(projectStoreState(row.project)!=='available') node.append(el('p','Store unavailable','bp-muted bp-note'));
  if(row.missing.length || row.not_configured.length) {
    const hire=el('details');
    hire.dataset.coverageProject=row.project;
    hire.append(el('summary','Hire…'),el('div',undefined,'bp-coverage-hire'));
    node.append(hire);
  }
  return node;
}
function coverageCollapsedBundle(rows) {
  const bundle=el('details',undefined,'bp-coverage-collapsed');
  const names=rows.map(row=>row.project).join(', ');
  bundle.append(el('summary',`${rows.length} project${rows.length===1?'':'s'} unstaffed (${names})`));
  const inner=el('div',undefined,'bp-coverage-collapsed-rows');
  for(const row of rows) inner.append(coverageRow(row));
  bundle.append(inner);
  return bundle;
}
function refreshCoverageHireBodies(container) {
  for(const hire of container.querySelectorAll('details[data-coverage-project]')) {
    if(!hire.open) continue;
    const row=(snapshot.coverage || []).find(item=>item.project===hire.dataset.coverageProject);
    if(row) paintCoverageHireBody(hire, row);
  }
}
function ensureCoverageHireDelegation() {
  const container=$('coverage-list');
  if(container.dataset.hireBound) return;
  container.dataset.hireBound='1';
  container.addEventListener('toggle',event=>{
    const hire=event.target;
    if(hire.tagName!=='DETAILS' || !hire.dataset.coverageProject) return;
    const row=(snapshot.coverage || []).find(item=>item.project===hire.dataset.coverageProject);
    if(row) paintCoverageHireBody(hire, row);
  },true);
}
function renderCoverage() {
  ensureCoverageHireDelegation();
  const rows=snapshot.coverage || [], active=[], collapsed=[];
  for(const row of rows) {
    if(coverageIsActive(row)) active.push(row);
    else collapsed.push(row);
  }
  const items=[...active];
  if(collapsed.length) items.push({project:'__collapsed__', rows:collapsed});
  reconcileList($('coverage-list'), items, item=>item.project, item=>{
    if(item.project==='__collapsed__') return coverageCollapsedBundle(item.rows);
    return coverageRow(item);
  }, {emptyText:'No registered projects.'});
  refreshCoverageHireBodies($('coverage-list'));
}
function agents() {
  const seats=snapshot.agents.filter(a=>a.group==='seat'), jobs=snapshot.agents.filter(a=>a.group==='job');
  $('agents-heartbeat').textContent=heartbeatLine();
  reconcileList($('seat-list'), seats, a=>a.id, agentCard, {emptyText:'No seats registered in the readable registry.'});
  reconcileList($('job-list'), jobs, a=>a.id, agentCard, {emptyText:'No jobs registered in the readable registry.'});
  supervisorPanel();
  renderCoverage();
}
function timelineRow(row) {
  const node = el('article', undefined, 'bp-order');
  const content = el('div');
  content.append(el('strong', row.title));
  const local = date(row.at);
  content.append(el('span', `${row.source} · ${row.project || 'desk'} · ${row.actor} · ${row.event} · ${local}`, 'bp-order-meta'));
  const eventBadge = badge(row.source, row.event);
  if (row.event_title) eventBadge.title = row.event_title;
  node.append(content, eventBadge);
  if (row.link?.href) {
    const href = row.link.href;
    const linkNode = row.link.external ? link(row.link.label || 'Open', href, 'bp-order-link') : link(row.link.label || 'Open', href, 'bp-order-link');
    if (row.link.external) { linkNode.target = '_blank'; linkNode.rel = 'noopener noreferrer'; }
    node.append(linkNode);
  }
  return node;
}
function timelineSources() {
  reconcileList($('timeline-sources'), timelineData?.sources || [], source => source.name, source => {
    const row = el('div', undefined, 'bp-source');
    row.append(el('span', source.name), badge(source.state));
    const detail = [source.detail, source.observed_at ? `Observed ${date(source.observed_at)}` : ''].filter(Boolean).join(' · ');
    if (detail) row.append(el('p', detail, 'bp-muted'));
    return row;
  }, {emptyText: 'No timeline sources reported.'});
}
function timeline() {
  reconcileList($('timeline-list'), timelineData?.rows || [], row => row.id, timelineRow, {emptyText: 'No timeline rows in the readable window.'});
  timelineSources();
  $('timeline-more').hidden = !timelineMore;
}
function updateTimelineFilters() {
  timelineProject = $('timeline-project').value;
  timelineSource = $('timeline-source').value;
  timelineActor = $('timeline-actor').value.trim();
  timelineCursor = '';
  const params = new URLSearchParams();
  if (timelineProject) params.set('project', timelineProject);
  if (timelineSource) params.set('source', timelineSource);
  if (timelineActor) params.set('actor', timelineActor);
  history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
  refreshTimeline(false);
}
function onDemandSeat(agent) {
  return agent.group==='seat' && (agent.schedule==='manual' || agent.schedule==='Not scheduled');
}
function mergeDatedWork(items) {
  const merged=new Map(), extras=[];
  for(const event of items) {
    if(event.kind!=='deadline' && event.kind!=='timer') { extras.push(event); continue; }
    const key=event.product+':'+event.task_id;
    const row=merged.get(key) || {product:event.product,task_id:event.task_id,summary:event.summary,attention:false,dtstart:event.dtstart,due:null,hold:null,due_all_day:false};
    if(event.kind==='deadline') { row.due=event.dtstart; row.due_all_day=!!event.all_day; }
    if(event.kind==='timer') row.hold=event.dtstart;
    if(event.attention) row.attention=true;
    if(event.summary) row.summary=event.summary;
    if(event.dtstart < row.dtstart) row.dtstart=event.dtstart;
    merged.set(key,row);
  }
  return [...merged.values(), ...extras].sort((a,b)=>String(a.dtstart).localeCompare(String(b.dtstart)));
}
function datedStamp(value, allDay) {
  return allDay ? value+' · All day' : date(value);
}
function calendar() {
  const datedItems=mergeDatedWork(snapshot.work_dates || []);
  reconcileList($('dated-work'), datedItems, event=>event.due||event.hold ? event.product+':'+event.task_id+':dated' : event.product+':'+event.task_id+':'+event.kind+':'+event.dtstart, event=>{
    const row=link('', '/work-order?'+new URLSearchParams({project:event.product,id:event.task_id}),'bp-order');
    const parts=[];
    if(event.due) parts.push(datedStamp(event.due,event.due_all_day)+' · Due');
    if(event.hold) parts.push(date(event.hold)+' · Hold until');
    if(!parts.length) parts.push((event.all_day?event.dtstart+' · All day':date(event.dtstart))+' · '+(event.kind==='timer'?'Hold until':'Due'));
    const details=el('div');details.append(el('strong',event.summary),el('span',parts.join(' · ')+' · '+event.product,'bp-order-meta'));
    row.append(details,badge(event.attention?'attention':'scheduled',event.attention?'Needs you':'Dated work'));
    return row;
  }, {emptyText:'No dated work orders in the readable stores.'});
  const demand=snapshot.agents.filter(onDemandSeat);
  const scheduled=[...snapshot.agents.filter(agent=>!onDemandSeat(agent))].sort((a,b)=>String(a.next_fire || 'z').localeCompare(String(b.next_fire || 'z')));
  const scheduleItems=demand.length ? scheduled.concat([{id:'_on-demand-seats', on_demand:demand.length}]) : scheduled;
  reconcileList($('schedule-list'), scheduleItems, agent=>agent.id, agent=>{
    if(agent.on_demand) {
      const row=el('div',undefined,'bp-source');
      row.append(el('strong','On demand seats: '+agent.on_demand));
      return row;
    }
    const row=el('div',undefined,'bp-source');row.append(el('strong',agent.name),badge(agent.state==='unknown'?'unknown':(agent.state==='off'?'off':(agent.next_fire?'scheduled':'not_scheduled'))));
    row.append(el('p',`${date(agent.next_fire)} · ${scheduleLabel(agent.schedule)}`,'bp-muted'));
    return row;
  }, {emptyText:'No agent schedules available.'});
  const eventItems=[...snapshot.events].sort((a,b)=>String(a.at).localeCompare(String(b.at)));
  reconcileList($('event-list'), eventItems, event=>`${event.title}|${event.at}`, event=>{
    const row=el('details',undefined,'bp-event');const summary=el('summary');summary.append(el('strong',event.title || 'Untitled event'),el('span',`${date(event.at)} · ${event.source || 'Local calendar'} · ${event.state || 'State not specified'}`,'bp-order-meta'));row.append(summary,el('p',event.notes || 'No additional notes.','bp-note bp-muted'));
    return row;
  }, {emptyText:'No local calendar events. Agent schedules above are independent of the calendar file.'});
}
function engines() {
  const rows=sortBySeverity(engineRows().map(([name, engine])=>({...engine, name})), row=>row.name);
  reconcileList($('engine-list'), rows, row=>row.name, row=>connectionRow(row.name, row, 'details'), {emptyText:'Engine receipts are not available in this workspace.'});
}
function excludedStores() {
  const excluded=(snapshot.excluded_stores || []).map(name=>({name}));
  reconcileList($('excluded-store-list'), excluded, store=>store.name, store=>{
    const row=el('div',undefined,'bp-source');row.append(el('span',store.name));
    return row;
  }, {emptyText:'No unregistered databases in this workspace.'});
}
function paint() {
  const workspace=snapshot.workspace;
  $('desk-name').textContent=workspace ? `${workspace.name} · Local` : 'No workspace';
  $('scope-path').textContent=workspace?.path || 'Start BluePrint with a workspace selected.';
  const issues=[
    ...(snapshot.sources || []).filter(isException),
    ...engineRows().filter(([,engine])=>isException(engine)).map(([name, engine])=>({name, state:engine.state})),
  ];
  $('source-warning').hidden=!issues.length && !snapshot.truncated;
  $('source-warning').textContent=issues.length ? `Some sources need attention: ${issues.map(s=>`${s.name} (${s.state})`).join(', ')}. Counts may be incomplete.` : 'Large stores are limited to 2,000 open records each. Filtered counts may be incomplete.';
  $('footer-status').textContent=`${snapshot.projects.length} project stores · ${issues.length ? `${issues.length} source notices` : 'Local sources readable'} · Remote details in Activity`;
  filterOptions();
  if(page==='overview') overview();
  if(page==='work') work();
  if(page==='projects') { reconcileList($('projects-view'), snapshot.projects, p=>p.id, projectCard, {emptyText:'No local project stores found.'}); }
  if(page==='agents') agents();
  if(page==='calendar') calendar();
  if(page==='timeline') timeline();
  if(page==='settings') { $('settings-build').textContent=snapshot.build;$('settings-workspace').textContent=snapshot.workspace?.path || 'Not selected'; }
  if(page==='connections') { connectionExceptions();sources($('connection-list'),true);engines();excludedStores();$('refresh-description').textContent=(streamState==='open' ? 'Live updates when the desk changes; ' : '')+(interval ? `fallback poll every ${streamState==='open'?60:interval} seconds while this page is visible` : 'manual fallback only');$('build').textContent=snapshot.build;$('workspace-path').textContent=workspace?.path || 'Not selected'; }
}
function liveIndicator() {
  if(!lastSuccess) return lastError ? 'Unable to read workspace. Retry with Refresh.' : 'Connecting…';
  if(document.hidden) return 'Paused';
  if(streamState==='open') return lastChangeAt ? `Live · last change ${Math.floor((Date.now()-lastChangeAt)/1000)}s ago` : 'Live';
  if(!everOpened) return 'Connecting…';
  return consecutiveErrors>=3 ? 'Polling every 60 s' : 'Reconnecting';
}
function freshness() {
  const status=$('freshness');
  status.dataset.state=lastError?'error':'ok';
  const indicator=liveIndicator();
  status.textContent=lastError && lastSuccess ? `Refresh failed · showing last read · ${indicator}` : indicator;
}
async function refreshTimeline(append) {
  if (timelinePending || page !== 'timeline') return;
  timelinePending = true;
  try {
    const params = new URLSearchParams();
    if (timelineProject) params.set('project', timelineProject);
    if (timelineSource) params.set('source', timelineSource);
    if (timelineActor) params.set('actor', timelineActor);
    if (append && timelineCursor) params.set('cursor', timelineCursor);
    const response = await fetch('/api/timeline?' + params.toString(), {cache: 'no-store', signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('Unavailable');
    const data = await response.json();
    if (append && timelineData) {
      const seen = new Set(timelineData.rows.map(row => row.id));
      timelineData = {...data, rows: [...timelineData.rows, ...data.rows.filter(row => !seen.has(row.id))]};
    } else {
      timelineData = data;
    }
    timelineCursor = data.next_cursor || '';
    timelineMore = Boolean(data.next_cursor);
    timeline();
    lastSuccess = Date.now();
    lastError = false;
    lastChangeAt = Date.now();
  } catch (error) {
    lastError = true;
    if (!timelineData) empty($('timeline-list'), 'Timeline is unavailable right now.');
  } finally {
    timelinePending = false;
    freshness();
  }
}
async function refreshRemote() {
  if(remotePending || !['delivery','connections'].includes(page)) return;
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
        text.append(el('strong',deliveryRow(item)),el('span',`Observed ${date(item.updated_at)}`,'bp-order-meta'));
        row.append(text,badge(item.state));section.append(row);
      }
      if(!(repo.items || []).length)empty(section,repo.quiet?'Quiet in the last 14 days.':'No verified delivery available.');
      container.append(section);
    }
    if(!data.repositories?.length && !data.refreshing)empty(container,'No repository delivery available. Check connection configuration or GitHub access.');
  } catch(error) { $('remote-status').textContent='GitHub refresh failed. Previously displayed evidence may be stale.';$('github-connection-status').textContent='GitHub unavailable'; }
  finally { remotePending=false; }
}
async function refresh(manual) {
  if(pending) return;
  lastAttempt=Date.now();pending=true;
  if(manual) { $('refresh').disabled=true;$('refresh').textContent='Refreshing…'; }
  try {
    const response=await fetch('/api/operations',{cache:'no-store',signal:AbortSignal.timeout(10000)});
    if(!response.ok) throw new Error('Source request failed');
    const next=await response.json();
    const key=JSON.stringify(page==='work' ? {orders:next.orders,projects:next.projects,workspace:next.workspace,sources:next.sources.map(s=>({name:s.name,state:s.state})),truncated:next.truncated} : {...next,observed_at:null});
    snapshot=next;lastSuccess=Date.now();lastError=false;
    if(key!==fingerprint) { paint();fingerprint=key;lastChangeAt=Date.now(); }
  } catch(error) { lastError=true; }
  finally { pending=false;if(manual) { $('refresh').disabled=false;$('refresh').textContent='Refresh'; }freshness(); }
}
function updateFilters() {
  selectedProject=$('project-filter').value;selectedAssignment=$('assignment-filter').value;pageIndex=0;
  const params=new URLSearchParams();if(selectedProject)params.set('project',selectedProject);if(selectedAssignment)params.set('assignment',selectedAssignment);if($('status-filter').value)params.set('status',$('status-filter').value);if($('gate-filter').value)params.set('gate',$('gate-filter').value);if($('attention-filter').value)params.set('attention',$('attention-filter').value);if($('blocked-filter').checked)params.set('blocked','1');if($('search').value)params.set('q',$('search').value);
  history.replaceState(null,'',location.pathname+(params.size?'?'+params:'')+location.hash);if(snapshot)work();
}
$('filters').addEventListener('submit',event=>event.preventDefault());
$('search').addEventListener('input',updateFilters);$('project-filter').addEventListener('change',updateFilters);$('status-filter').addEventListener('change',updateFilters);$('gate-filter').addEventListener('change',updateFilters);$('attention-filter').addEventListener('change',updateFilters);$('assignment-filter').addEventListener('change',updateFilters);$('blocked-filter').addEventListener('change',updateFilters);
$('clear-filters').addEventListener('click',()=>{$('search').value='';$('project-filter').value='';$('assignment-filter').value='';$('status-filter').value='';$('gate-filter').value='';$('attention-filter').value='';$('blocked-filter').checked=false;updateFilters();});
$('previous').addEventListener('click',()=>{pageIndex--;work();});$('next').addEventListener('click',()=>{pageIndex++;work();});if ($('timeline-filters')) {
  $('timeline-project').value = timelineProject;
  $('timeline-source').value = timelineSource;
  $('timeline-actor').value = timelineActor;
  $('timeline-filters').addEventListener('submit', event => event.preventDefault());
  $('timeline-project').addEventListener('change', updateTimelineFilters);
  $('timeline-source').addEventListener('change', updateTimelineFilters);
  $('timeline-actor').addEventListener('change', updateTimelineFilters);
  $('timeline-actor').addEventListener('input', updateTimelineFilters);
  $('timeline-more').addEventListener('click', () => refreshTimeline(true));
}
$('refresh').addEventListener('click',()=>{refresh(true);refreshRemote();if(page==='timeline')refreshTimeline(false);});
document.addEventListener('keydown',event=>{if(event.key==='Escape')$('desk-scope').open=false;});
document.addEventListener('click',event=>{if(!$('desk-scope').contains(event.target))$('desk-scope').open=false;});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();freshness();});
$('preferences').addEventListener('submit',event=>event.preventDefault());
$('preferences').addEventListener('change',()=>{interval=Number($('refresh-preference').value);motion=$('motion-preference').value;document.body.classList.toggle('bp-reduce-motion',motion==='off');try{localStorage.setItem('bp-display',JSON.stringify({interval,motion}));$('preference-status').textContent='Saved in this browser.';}catch(error){$('preference-status').textContent='Applied for this page; browser storage is unavailable.';}});
connectChanges(()=>{if(!document.hidden){refresh();if(page==='timeline')refreshTimeline(false);}},state=>{streamState=state;if(state==='open'){everOpened=true;consecutiveErrors=0;}else if(state==='error'){consecutiveErrors++;}freshness();});
setInterval(()=>{const effective=streamState==='open'?60:interval;if(effective && !document.hidden && Date.now()-lastAttempt>=effective*1000)refresh();},1000);setInterval(freshness,1000);setInterval(()=>{if(!document.hidden && Date.now()-remoteLast>15000)refreshRemote();},1000);refresh();refreshRemote();if(page==='timeline')refreshTimeline(false);
})();
