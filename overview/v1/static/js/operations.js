/* All source content is rendered as text. No source value becomes HTML. */
(async () => {
'use strict';
const {readerHref} = await import('/js/reader-navigation.mjs');
const {connectChanges} = await import('/js/change-feed.mjs');
const {reconcileList} = await import('/js/dom-reconcile.mjs');
const $ = id => document.getElementById(id);
const route = location.pathname.replace(/\/$/, '') || '/';
const page = ({'/':'overview','/overview':'overview','/work':'work','/projects':'projects','/agents':'agents','/connections':'connections','/delivery':'delivery','/activity':'delivery','/timeline':'timeline','/calendar':'calendar','/settings':'settings'})[route] || 'overview';
const titles = {delivery:['Delivery','Pull requests, CI and releases reported by GitHub; not agent activity.'],timeline:['Timeline','WorkLane events, WorkForce shifts, supervisor passes and GitHub delivery in one labelled stream.'],calendar:['Calendar','Today, upcoming runs, and dated work, with each clock labelled by its source.'],settings:['Settings','Display preferences and the application you are actually running.'],overview:['Overview','What needs you, what is moving, and what this desk can verify.'],work:['Work','Find an open work order, see its context, and read the full history.'],projects:['Projects','Project stores connected to this workspace.'],agents:['Agents',''],connections:['Connections','Where the information comes from, whether it is reachable and usable, and how current it is.']};
let snapshot = null, pending = false, lastSuccess = null, lastAttempt = 0, lastError = false, pageIndex = 0, fingerprint = '';
let selectedAgentId = '';
const size = 25;
let muted={};try {muted=JSON.parse(localStorage.getItem('bp-attention-mutes') || '{}');}catch(error){}
function muteKey(order){return JSON.stringify([snapshot?.workspace?.path,order.project,order.id]);}
function saveMutes(){try{localStorage.setItem('bp-attention-mutes',JSON.stringify(muted));}catch(error){}}
$('restore-muted').addEventListener('click',()=>{for(const order of snapshot.orders)delete muted[muteKey(order)];saveMutes();overview();});
let remotePending = false, remoteLast = 0;
let timelineData = null, timelinePending = false, timelineCursor = '', timelineMore = false, timelineFingerprint = '', timelineExpanded = false;
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
let kindParam = query.get('kind') || '';
let attentionParam = query.get('attention') || '';
let legacyParam = false;
if (statusParam.startsWith('gate:')) { gateParam = gateParam || statusParam.slice(5); statusParam = ''; legacyParam = true; }
else if (statusParam === 'deferred') { gateParam = gateParam || 'deferred'; statusParam = ''; legacyParam = true; }
else if (statusParam.startsWith('face:')) { attentionParam = attentionParam || statusParam.slice(5); statusParam = ''; legacyParam = true; }
else if (statusParam === 'attention') { attentionParam = attentionParam || 'any'; statusParam = ''; legacyParam = true; }
else if (statusParam === 'blocked') { gateParam = gateParam || 'blocked'; statusParam = ''; legacyParam = true; }
if (query.get('deferred') === '1') { gateParam = gateParam || 'deferred'; legacyParam = true; }
// Pre-D16 links used the retired Note face value; map it to Due (STATES_AND_TERMS.md §1.4).
if (attentionParam === 'note') { attentionParam = 'due'; legacyParam = true; }
if (query.get('blocked') === '1') { gateParam = gateParam || 'blocked'; legacyParam = true; }
$('status-filter').value = statusParam;
$('gate-filter').value = gateParam;
$('kind-filter').value = kindParam;
$('attention-filter').value = attentionParam;
let selectedProject = query.get('project') || '';
let selectedAssignment = query.get('assignment') || '';
let calendarDay = query.get('day') || '';
if (legacyParam) {
  const canonical = new URLSearchParams();
  if (selectedProject) canonical.set('project', selectedProject);
  if (selectedAssignment) canonical.set('assignment', selectedAssignment);
  if (statusParam) canonical.set('status', statusParam);
  if (gateParam) canonical.set('gate', gateParam);
  if (kindParam) canonical.set('kind', kindParam);
  if (attentionParam) canonical.set('attention', attentionParam);
  if (query.get('q')) canonical.set('q', query.get('q'));
  if (calendarDay) canonical.set('day', calendarDay);
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
function truncateText(text, max) {
  const value=(text || '').trim();
  if(!value || value.length <= max) return value;
  return value.slice(0, max - 1) + '…';
}
function isBoilerplateNote(note) {
  const value=(note || '').trim();
  if(!value) return true;
  return /^(Intake:|Owner:|Actor:|Evidence:|Plan:|\u0055pdated fields:)/.test(value);
}
function assignmentSummary(order) {
  const owner=(order.owner || '').trim();
  if(owner && owner!=='Unassigned') return owner;
  if(order.needs_routing) return 'Needs routing';
  return 'Unassigned';
}
function orderUpdatedAt(order) {
  const parsed=Date.parse(String(order.updated_at || ''));
  return Number.isNaN(parsed) ? Number.NEGATIVE_INFINITY : parsed;
}
function isClosedOrder(order) {
  const status=order.status || '';
  return status==='done' || status==='canceled' || status==='cancelled';
}
function lifecycleSummary(order) {
  if(order.status==='in_progress' && order.live_with) return `Live · ${order.live_with}`;
  if(order.status==='in_review' && order.parked_by) return `Parked · ${order.parked_by}`;
  return order.status_word || order.status;
}
function compactMetaLine(order) {
  return [order.project_name, order.id, lifecycleSummary(order), gateLabel(order), assignmentSummary(order), date(order.updated_at)].filter(Boolean).join(' · ');
}
function nextActionText(order) {
  if(order.attention_face==='decide' && order.gate_note) return truncateText(order.gate_note, 120);
  if(order.attention_face==='read') return 'Read the report, then clear or snooze';
  if(order.attention_face==='watch' && order.gate_type==='timer') return 'Review when the hold expires';
  if(order.attention_face==='watch') return 'Check for new evidence';
  if(order.ready_for) return `Ready for ${order.ready_for}`;
  if(order.blocked_on==='unknown' && order.blocked_note) return order.blocked_note;
  if(order.blocked_on==='open' && order.blockers && order.blockers.length) return `Blocked on ${order.blockers.join(', ')}`;
  if(!isBoilerplateNote(order.last_note)) return truncateText(order.last_note, 120);
  return '';
}
function orderDetailBody(order, content) {
  if(order.parent) content.append(el('p',`Part of ${order.parent}`,'bp-order-note'));
  if(order.blocked_on==='unknown' && order.blocked_note) content.append(el('p',order.blocked_note,'bp-order-note'));
  else if(order.blocked_on==='open' && order.blockers && order.blockers.length) content.append(el('p',`Blocked on ${order.blockers.join(', ')}`,'bp-order-note'));
  if(order.ready_for) content.append(el('p',`Ready for ${order.ready_for}`,'bp-order-note'));
  if(order.persona) content.append(el('p',order.persona,'bp-order-note'));
  else if(order.needs_routing) content.append(el('p','Needs routing','bp-order-note'));
  if(order.gate_note) content.append(el('p',order.gate_note,'bp-order-note'));
  if(!isBoilerplateNote(order.last_note)) content.append(el('p',`Last note: ${order.last_note}`,'bp-order-meta'));
  if(order.status==='in_progress' && order.live_with && order.since) content.append(el('p',`Claimed live with ${order.live_with} since ${date(order.since)}`,'bp-order-meta'));
  if(order.status==='in_review' && order.parked_by && order.since) content.append(el('p',`Parked by ${order.parked_by} since ${date(order.since)}`,'bp-order-meta'));
}
function orderHasDetail(order) {
  return Boolean(order.parent || order.blocked_on==='open' || order.blocked_on==='unknown' || order.ready_for || order.persona || order.needs_routing || order.gate_note || !isBoilerplateNote(order.last_note) || (order.since && (order.live_with || order.parked_by)));
}
function orderBadges(order) {
  const gateWord=gateLabel(order);
  const badges=[badge(order.attention_face==='decide' ? 'attention' : order.status, order.attention_face==='decide' ? 'Needs you' : (order.status_word || undefined))];
  if(gateWord) {
    const gateKind=order.gate_type || ((order.blocked_on==='open' || order.blocked_on==='unknown') ? 'blocked' : '');
    badges.push(badge(gateKind+(order.gate_expired?'-expired':''),gateWord));
  }
  return badges;
}
function orderRow(order) {
  const row=el('div',undefined,'bp-order bp-order-compact');
  const anchor=link('',workUrl(order),'bp-order-link');
  const content=el('div');
  content.append(el('strong',order.title));
  content.append(el('span',compactMetaLine(order),'bp-order-meta'));
  anchor.append(content);
  row.append(anchor,...orderBadges(order));
  if(orderHasDetail(order)) {
    const details=el('details',undefined,'bp-order-detail');
    details.append(el('summary','More'));
    orderDetailBody(order, details);
    row.append(details);
  }
  return row;
}
function gateLabel(order) {
  if(order.gate_type==='deferred') return 'Deferred';
  if(order.gate_type==='tracking') return 'Tracking';
  if(order.gate_type==='timer') return order.gate_expired ? 'Timer expired' : `Held until ${date(order.gate_until)}`;
  if(order.gate_type==='human') return 'Needs a decision';
  if(order.blocked_on==='open' || order.blocked_on==='unknown') return 'Blocked on another order';
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
function namedEngineRows(pairs) {
  const engines=snapshot.engines || {};
  return pairs.map(([name, key])=>[name, engines[key]]).filter(([,engine])=>engine);
}
function receiptEngineRows() {
  return namedEngineRows([['WorkLane engine','worklane'],['WorkForce engine','workforce']]);
}
function capabilityEngineRows() {
  return namedEngineRows([['WorkLane API','worklane_api'],['Supervisor last pass','supervisor']]);
}
function engineRows() {
  return receiptEngineRows().concat(capabilityEngineRows());
}
function overviewFaceRow(order) {
  const row=el('div',undefined,'bp-order bp-order-compact bp-face-row');
  const anchor=link('',workUrl(order),'bp-order-link');
  const content=el('div');
  content.append(el('strong',order.title));
  const why=truncateText(order.face_reason || '', 140);
  const meta=[order.project_name, order.id, why].filter(Boolean).join(' · ');
  content.append(el('span',meta,'bp-order-meta'));
  const action=nextActionText(order);
  if(action && action !== why) content.append(el('span',action,'bp-order-note'));
  anchor.append(content);
  const faceBadge={decide:'Needs you',read:'Read',watch:'Watch',note:'Note'}[order.attention_face] || 'For You';
  row.append(anchor,badge(order.attention_face==='decide' ? 'attention' : (order.attention_face || 'attention'), faceBadge));
  if(orderHasDetail(order)) {
    const details=el('details',undefined,'bp-order-detail');
    details.append(el('summary','More'));
    orderDetailBody(order, details);
    row.append(details);
  }
  return row;
}
function executionRow(agent) {
  const row=el('div',undefined,'bp-execution-row');
  const main=el('div');
  main.append(el('strong',agent.name));
  const bits=[agent.badge];
  if(agent.shift) bits.push(`since ${date(agent.shift.started_at)}`);
  if(agent.held) bits.push(agent.held.id);
  main.append(el('span',bits.join(' · '),'bp-order-meta'));
  row.append(main,badge(agent.state,agent.badge));
  const actions=el('div',undefined,'bp-execution-actions');
  actions.append(link('Inspect seat','/agents'));
  if(agent.held && agent.project) actions.append(link('Open order',workUrl({project:agent.project,id:agent.held.id,project_name:agent.project_name})));
  row.append(actions);
  return row;
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
  const entry=el('div',undefined,'bp-face-entry');entry.append(overviewFaceRow(order));
  const mute=el('button','Mute 24h');mute.type='button';mute.className='bp-face-mute';
  mute.addEventListener('click',()=>{muted[muteKey(order)]=Date.now()+86400000;saveMutes();overview();});
  entry.append(mute);
  return entry;
}
function faceHeading(label, total, visible, href) {
  let text=`${label} · ${total}`;
  if(total > visible) text+=` · showing ${visible}`;
  const heading=$(`for-you-${label.toLowerCase()}-heading`) || $(`for-you-${label.toLowerCase()}-summary`);
  if(heading) heading.textContent=text;
  const linkWrap=heading && heading.parentElement && heading.parentElement.querySelector('a');
  if(linkWrap && total > visible && href) linkWrap.textContent=`View all ${total}`;
}
function overviewExecutionEmpty() {
  const heartbeat=(snapshot.sources || []).find(s=>s.name==='WorkForce heartbeat');
  if(!heartbeat || heartbeat.state==='unknown') return 'WorkForce daemon not reachable — no shift evidence to show.';
  if(heartbeat.state==='stale') return 'WorkForce heartbeat is stale; running seats may not be reported.';
  return 'No seats report an open shift right now.';
}
function overview() {
  const orders=snapshot.orders, forYou=orders.filter(o=>o.attention_face);
  // Two independent facts, never merged into one 'Live': Claimed is a
  // WorkLane claim (a days-old human claim counts here); Running is
  // agent-evidence-only (fresh heartbeat plus an open shift or in-flight
  // ticket) and cannot be inflated by claim age (pc-1483).
  const live=orders.filter(o=>o.status==='in_progress' && o.live_with);
  const running=snapshot.agents.filter(a=>a.group==='seat' && a.state==='working');
  const seats=snapshot.agents.filter(a=>a.group==='seat').length, jobs=snapshot.agents.filter(a=>a.group==='job').length;
  reconcileList($('overview-executions'), running, a=>a.id, executionRow, {emptyText:overviewExecutionEmpty()});
  const metrics=[['For You',forYou.length,'/work?attention=any'],['Running',running.length,'/agents'],['Claimed',live.length,'/work?status=in_progress'],['Open work',snapshot.projects.filter(x=>x.state==='available').reduce((sum,p)=>sum+p.open,0),'/work'],['Seats · Jobs',`${seats} · ${jobs}`,'/agents']];
  reconcileList($('metrics'), metrics, m=>m[0], ([label,count,href])=>{const a=link('',href,'bp-metric');a.append(el('strong',String(count)),el('span',label));return a;});
  const faceLimit={decide:6,read:6,watch:4,note:4};
  let mutedCount=0;
  for(const face of ['decide','read','watch','due']) {
    const band=forYou.filter(o=>o.attention_face===face);
    const unmuted=band.filter(o=>!(Number(muted[muteKey(o)])>Date.now()));
    const visible=unmuted.slice(0,faceLimit[face]);
    mutedCount+=band.length-unmuted.length;
    reconcileList($('for-you-'+face), visible, o=>o.project+':'+o.id, faceEntry, {emptyText:'No '+face+' items visible in the readable stores.'});
    if(face==='decide' || face==='read') faceHeading(face.charAt(0).toUpperCase()+face.slice(1), band.length, visible.length, '/work?attention='+face);
    else {
      const summary=$(`for-you-${face}-summary`);
      if(summary) summary.textContent=`${face.charAt(0).toUpperCase()+face.slice(1)} · ${band.length}${band.length>visible.length?` · showing ${visible.length}`:''}`;
    }
  }
  $('mute-status').textContent=(mutedCount ? mutedCount+' muted. ' : '')+'Mute only hides this inbox item in this browser; it does not change gates, reminders, or assignments.';
  $('restore-muted').hidden=!orders.some(o=>Number(muted[muteKey(o)])>Date.now());
  const recent=[...orders].filter(o=>!isClosedOrder(o)).sort((a,b)=>orderUpdatedAt(b)-orderUpdatedAt(a)).slice(0,8);
  reconcileList($('overview-recent'), recent, o=>o.project+':'+o.id, orderRow, {emptyText:'No recent updates in the readable stores.'});
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
function matchesGate(order, value) {
  if(value==='none') return !order.gate_type && order.blocked_on==='clear';
  if(value==='blocked') return order.blocked_on==='open' || order.blocked_on==='unknown';
  return order.gate_type===value;
}
function filterChips() {
  const chips=[];
  if($('search').value) chips.push(['Search: '+$('search').value,()=>{$('search').value='';}]);
  if(selectedProject) { const opt=Array.from($('project-filter').options).find(o=>o.value===selectedProject); chips.push(['Project: '+(opt?opt.text:selectedProject),()=>{$('project-filter').value='';}]); }
  if(selectedAssignment) { const opt=Array.from($('assignment-filter').options).find(o=>o.value===selectedAssignment); chips.push(['Assignment: '+(opt?opt.text:selectedAssignment),()=>{$('assignment-filter').value='';}]); }
  if($('status-filter').value) chips.push(['Status: '+$('status-filter').selectedOptions[0].text,()=>{$('status-filter').value='';}]);
  if($('gate-filter').value) chips.push(['Gate: '+$('gate-filter').selectedOptions[0].text,()=>{$('gate-filter').value='';}]);
  if($('kind-filter').value) chips.push(['Kind: '+$('kind-filter').selectedOptions[0].text,()=>{$('kind-filter').value='';}]);
  if($('attention-filter').value) chips.push(['For You: '+$('attention-filter').selectedOptions[0].text,()=>{$('attention-filter').value='';}]);
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
  const q=$('search').value.trim().toLowerCase(), status=$('status-filter').value, gate=$('gate-filter').value, kind=$('kind-filter').value, attention=$('attention-filter').value;
  const total=snapshot.orders.length;
  const orders=snapshot.orders.filter(o=>(!selectedProject || o.project===selectedProject) && (!selectedAssignment || matchesAssignment(o,selectedAssignment)) && (!status || o.status===status) && (!gate || matchesGate(o,gate)) && (!kind || o.kind===kind) && (!attention || (attention==='any' ? o.attention : o.attention_face===attention)) && (!q || `${o.id} ${o.title} ${o.project_name} ${o.owner}`.toLowerCase().includes(q)));
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
function currentOrderFor(agent) {
  if(!agent.held) return null;
  return (snapshot.orders || []).find(o=>o.id===agent.held.id && o.project===agent.held.project) || null;
}
function parkedOrderIds(agent) {
  return (agent.parked || []).map(p=>p.id);
}
function currentShiftParkedIds(agent) {
  if(!agent.shift || !agent.parked) return [];
  const start=agent.shift.started_at;
  if(!start) return parkedOrderIds(agent);
  return agent.parked.filter(p=>p.since && p.since>=start).map(p=>p.id);
}
function latestParkedSince(agent) {
  return (agent.parked || []).reduce((latest,p)=>((!latest || (p.since && p.since>latest)) ? p.since : latest), null);
}
function heldLink(agent) {
  const order=currentOrderFor(agent);
  if(order) return link(`${order.title} · ${order.id}`,workUrl(order));
  if(agent.held) return link(agent.held.id,readerHref('/work-order?'+new URLSearchParams({project:agent.held.project,id:agent.held.id})));
  const finishingIds=currentShiftParkedIds(agent);
  if(agent.finishing && finishingIds.length) return el('span',`Finishing · parked ${finishingIds.join(', ')}`);
  const parkedIds=parkedOrderIds(agent);
  if(parkedIds.length) return el('span',`Parked: ${parkedIds.join(', ')} · awaiting integration`);
  return el('span','No current work','bp-muted');
}
function elapsedText(agent) {
  if(agent.shift && agent.shift.age_seconds!=null) {
    const mins=Math.floor(agent.shift.age_seconds/60);
    const elapsed=mins ? `${mins}m` : `${agent.shift.age_seconds}s`;
    return `${elapsed} of ${Math.round((agent.shift.budget_secs||0)/60)}m budget`;
  }
  return '—';
}
function lastUpdateText(agent) {
  if(agent.shift) return `Since ${date(agent.shift.started_at)}`;
  if(agent.last_run) return date(agent.last_run.at);
  return 'Not reported';
}
function selectAgent(id) {
  selectedAgentId=selectedAgentId===id ? '' : id;
  agents();
}
function agentRow(agent) {
  const row=el('div',undefined,'bp-agent-row');
  // Selection and action are two independent controls, never nested: the
  // selectable region (name, provider, badge, held, elapsed, last update)
  // carries role=button, and the action cell — a real <button>/<a> — is a
  // sibling outside it, not inside it (no nested interactive controls).
  const select=el('div',undefined,'bp-agent-select');
  select.setAttribute('role','button');select.tabIndex=0;
  select.dataset.agentId=agent.id;
  const selected=selectedAgentId===agent.id;
  select.dataset.selected=String(selected);
  select.setAttribute('aria-pressed',String(selected));
  select.append(el('span',agent.project_name || 'No project queue','bp-agent-cell'));
  const nameCell=el('span',undefined,'bp-agent-cell bp-agent-name');
  nameCell.append(el('strong',agent.name),el('span',` · ${agent.model}`,'bp-muted'));
  select.append(nameCell);
  const stateCell=el('span',undefined,'bp-agent-cell');stateCell.append(badge(agent.state,agent.badge));select.append(stateCell);
  const workCell=el('span',undefined,'bp-agent-cell bp-agent-work');workCell.append(heldLink(agent));select.append(workCell);
  select.append(el('span',elapsedText(agent),'bp-agent-cell bp-muted'));
  select.append(el('span',lastUpdateText(agent),'bp-agent-cell bp-muted'));
  const activate=event=>{ if(event.target.closest('a')) return; event.preventDefault(); selectAgent(agent.id); };
  select.addEventListener('click',activate);
  select.addEventListener('keydown',event=>{ if((event.key==='Enter' || event.key===' ') && !event.target.closest('a')) { event.preventDefault(); selectAgent(agent.id); } });
  row.append(select);
  const actionCell=el('span',undefined,'bp-agent-cell bp-agent-action');actionCell.append(...agentAction(agent));row.append(actionCell);
  return row;
}
function jobRow(agent) {
  const row=el('div',undefined,'bp-agent-row');
  const info=el('div',undefined,'bp-job-info');
  info.append(el('span',agent.name,'bp-agent-cell'));
  info.append(el('span',scheduleLabel(agent.schedule),'bp-agent-cell bp-muted'));
  info.append(el('span',agent.schedule==='manual'?'On demand':date(agent.next_fire),'bp-agent-cell bp-muted'));
  const stateCell=el('span',undefined,'bp-agent-cell');stateCell.append(badge(agent.state,agent.badge));info.append(stateCell);
  const reportText=agent.report ? `${agent.report.state} · ${agent.report.summary}` : (agent.last_run ? `${agent.last_run.outcome} · ${date(agent.last_run.at)}` : 'No report yet');
  info.append(el('span',reportText,'bp-agent-cell bp-muted'));
  row.append(info);
  const actionCell=el('span',undefined,'bp-agent-cell bp-agent-action');actionCell.append(...agentAction(agent));row.append(actionCell);
  return row;
}
function timelineStep(label, value) {
  const step=el('div',undefined,'bp-agent-timeline-step');
  step.append(el('dt',label),el('dd',value));
  return step;
}
function agentTimelineValues(agent) {
  let claim='Not reported';
  if(agent.held) claim=agent.held_verified ? `Verified: holds ${agent.held.id}` : `Holds ${agent.held.id} · not yet verified against the last dispatch candidates`;
  else if(agent.parked && agent.parked.length) {
    const detail=agent.parked.map(p=>p.verified ? `${p.id} (verified)` : `${p.id} (not yet verified)`).join(', ');
    const when=latestParkedSince(agent);
    claim=when ? `Parked ${detail} · ${date(when)}` : `Parked ${detail}`;
  }
  else if(agent.state==='last_run_failed') claim=agent.preserved_reservation ? 'No order currently held here; a preserved reservation is available to recover' : 'No order currently held here; the failed ticket may already be resolved by another provider';
  let terminal='Not reported';
  if(agent.shift) terminal='Open — no terminal row yet';
  else if(agent.last_run) terminal=`${agent.last_run.outcome} · ${agent.last_run.reason} · ${date(agent.last_run.at)}`;
  return [
    ['Dispatch candidate', agent.last_candidates && agent.last_candidates.length ? agent.last_candidates.join(', ') : 'Not reported'],
    ['Verified claim', claim],
    ['Observed run start', agent.shift ? date(agent.shift.started_at) : 'Not reported'],
    ['Recovery attempts', String(agent.recovery_attempts || 0)],
    ['Terminal outcome', terminal],
  ];
}
function agentTimeline(agent) {
  const wrap=el('dl',undefined,'bp-agent-timeline');
  for(const [label,value] of agentTimelineValues(agent)) wrap.append(timelineStep(label,value));
  return wrap;
}
function syncAgentTimeline(wrap, agent) {
  const steps=agentTimelineValues(agent), nodes=wrap.children;
  steps.forEach(([,value], index)=>{
    const dd=nodes[index] && nodes[index].querySelector('dd');
    if(dd && dd.textContent!==value) dd.textContent=value;
  });
}
function syncBadge(node, state, text) {
  const label=text || state.replaceAll('_',' ');
  if(node.textContent!==label) node.textContent=label;
  if(node.dataset.state!==state) node.dataset.state=state;
}
// The selected-run inspector is repainted on every meaningful snapshot
// change, but most of those changes belong to a different seat or a field
// this inspector doesn't show; rebuilding container.replaceChildren() on
// every call would tear down and recreate the panel (and lose focus/DOM
// identity) even when the selected agent's own displayed fields are
// unchanged. Keep the skeleton across repaints for the same agent id and
// only write the text/state that actually moved.
function agentDetail() {
  const container=$('agent-detail');
  const agent=snapshot.agents.find(a=>a.id===selectedAgentId && a.group==='seat');
  if(!agent) {
    if(!container.hidden || container._agentRefs) { container.hidden=true; container.replaceChildren(); container._agentRefs=null; }
    return;
  }
  container.hidden=false;
  const shiftText=agent.shift ? `${agent.shift.stale?'Shift open past its budget with no terminal row; verify the process before dispatching again':'Shift open'} · budget ${agent.shift.budget_secs}s${agent.shift.lock_held?' · lock held':''} · ${agent.shift.source}` : '';
  if(!container._agentRefs || container._agentRefs.id!==agent.id) {
    container.replaceChildren();
    const heading=el('div',undefined,'bp-section-head');
    const h2=el('h2',`Inspect · ${agent.name}`);
    const stateBadge=badge(agent.state,agent.badge);
    heading.append(h2,stateBadge);
    container.append(heading);
    const meta=el('p',`${agent.id} · source: ${agent.badge_source}`,'bp-muted bp-note');
    container.append(meta);
    const shiftLine=el('p',shiftText,agent.shift && agent.shift.stale?'bp-note':'bp-note bp-muted');
    shiftLine.hidden=!agent.shift;
    container.append(shiftLine);
    const timelineWrap=agentTimeline(agent);
    container.append(timelineWrap);
    container.append(link('Find assigned work','/work?'+new URLSearchParams({assignment:'worker:'+agent.id}),'bp-order-meta'));
    const closeBtn=el('button','Close');closeBtn.type='button';closeBtn.addEventListener('click',()=>selectAgent(agent.id));
    container.append(closeBtn);
    container._agentRefs={id:agent.id,h2,stateBadge,meta,shiftLine,timelineWrap};
    return;
  }
  const refs=container._agentRefs;
  if(refs.h2.textContent!==`Inspect · ${agent.name}`) refs.h2.textContent=`Inspect · ${agent.name}`;
  syncBadge(refs.stateBadge, agent.state, agent.badge);
  const metaText=`${agent.id} · source: ${agent.badge_source}`;
  if(refs.meta.textContent!==metaText) refs.meta.textContent=metaText;
  if(refs.shiftLine.hidden!==!agent.shift) refs.shiftLine.hidden=!agent.shift;
  if(refs.shiftLine.textContent!==shiftText) refs.shiftLine.textContent=shiftText;
  const shiftClass=agent.shift && agent.shift.stale?'bp-note':'bp-note bp-muted';
  if(refs.shiftLine.className!==shiftClass) refs.shiftLine.className=shiftClass;
  syncAgentTimeline(refs.timelineWrap, agent);
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
  reconcileList($('seat-list'), seats, a=>a.id, agentRow, {emptyText:'No seats registered in the readable registry.'});
  reconcileList($('job-list'), jobs, a=>a.id, jobRow, {emptyText:'No jobs registered in the readable registry.'});
  agentDetail();
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
  timelineExpanded = false;
  const params = new URLSearchParams();
  if (timelineProject) params.set('project', timelineProject);
  if (timelineSource) params.set('source', timelineSource);
  if (timelineActor) params.set('actor', timelineActor);
  history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
  refreshTimeline(false, {force: true});
}
function onDemandSeat(agent) {
  return agent.group==='seat' && (agent.schedule==='manual' || agent.schedule==='Not scheduled');
}
function todayKey(from) {
  const d=from || new Date();
  return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
}
function shiftDay(key, days) {
  const [y,m,d]=String(key).split('-').map(Number);
  return todayKey(new Date(y, m-1, d+days));
}
function calendarOrigin() {
  return calendarDay || todayKey();
}
function localDayKey(value, allDay) {
  if(!value) return '';
  const raw=String(value);
  if(allDay || /^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw.slice(0,10);
  const parsed=new Date(raw);
  if(Number.isNaN(parsed.valueOf())) return raw.slice(0,10);
  return todayKey(parsed);
}
function allDayStamp(value) {
  const [y,m,d]=String(value).slice(0,10).split('-').map(Number);
  if(!y || !m || !d) return String(value);
  return new Date(y, m-1, d).toLocaleDateString([], {month:'short', day:'numeric'});
}
function datedStamp(value, allDay) {
  return allDay || /^\d{4}-\d{2}-\d{2}$/.test(String(value||'')) ? allDayStamp(value)+' · All day' : date(value);
}
function holdExpired(value, allDay, now) {
  if(!value) return false;
  const instant=now || new Date();
  if(allDay || /^\d{4}-\d{2}-\d{2}$/.test(String(value))) return String(value).slice(0,10) < todayKey(instant);
  const parsed=new Date(value);
  return !Number.isNaN(parsed.valueOf()) && parsed < instant;
}
function mergeDatedWork(items) {
  const merged=new Map(), extras=[];
  for(const event of items) {
    if(event.kind!=='deadline' && event.kind!=='timer' && event.kind!=='reminder' && event.kind!=='mentioned') { extras.push(event); continue; }
    const key=event.product+':'+event.task_id;
    const row=merged.get(key) || {product:event.product,task_id:event.task_id,summary:event.summary,attention:false,attention_face:'',dtstart:event.dtstart,due:null,hold:null,reminder:null,mentioned:null,due_all_day:false,hold_all_day:false,reminder_all_day:false,mentioned_all_day:false,due_source:'',hold_source:'',reminder_source:'',mentioned_source:''};
    if(event.kind==='deadline') { row.due=event.dtstart; row.due_all_day=!!event.all_day; row.due_source=event.source || ('deadline:'+String(event.dtstart).slice(0,10)); }
    if(event.kind==='timer') { row.hold=event.dtstart; row.hold_all_day=!!event.all_day; row.hold_source=event.source || 'gate_until'; }
    if(event.kind==='reminder') { row.reminder=event.dtstart; row.reminder_all_day=!!event.all_day; row.reminder_source=event.source || ('reminder:'+String(event.dtstart).slice(0,10)); }
    if(event.kind==='mentioned') { row.mentioned=event.dtstart; row.mentioned_all_day=!!event.all_day; row.mentioned_source=event.source || 'gate_note'; }
    if(event.attention_face==='decide') { row.attention_face='decide'; row.attention=true; }
    else if(!row.attention_face && event.attention_face) row.attention_face=event.attention_face;
    if(event.summary) row.summary=event.summary;
    if(String(event.dtstart) < String(row.dtstart)) row.dtstart=event.dtstart;
    merged.set(key,row);
  }
  return [...merged.values(), ...extras];
}
function rowClocks(row) {
  const clocks=[];
  if(row.due) clocks.push({kind:'due', at:row.due, allDay:!!row.due_all_day, source:row.due_source});
  if(row.reminder) clocks.push({kind:'reminder', at:row.reminder, allDay:!!row.reminder_all_day, source:row.reminder_source});
  if(row.hold) clocks.push({kind:'hold', at:row.hold, allDay:!!row.hold_all_day, source:row.hold_source, expired:holdExpired(row.hold, row.hold_all_day)});
  if(row.mentioned) clocks.push({kind:'mentioned', at:row.mentioned, allDay:!!row.mentioned_all_day, source:row.mentioned_source});
  if(!clocks.length && row.dtstart) clocks.push({kind:row.kind==='timer'?'hold':(row.kind==='reminder'?'reminder':(row.kind==='mentioned'?'mentioned':'due')), at:row.dtstart, allDay:!!row.all_day, source:row.source||''});
  return clocks;
}
function agendaGroup(row, origin) {
  const days=rowClocks(row).map(clock=>localDayKey(clock.at, clock.allDay)).filter(Boolean);
  if(days.some(day=>day===origin)) return 'today';
  if(days.some(day=>day<origin)) return 'past';
  return 'next';
}
function clockLabel(clock) {
  if(clock.kind==='due') return 'Due';
  if(clock.kind==='reminder') return 'Reminder';
  if(clock.kind==='hold') return clock.expired ? 'Expired hold' : 'Hold until';
  return 'Mentioned date';
}
function datedHref(event) {
  return readerHref('/work-order?'+new URLSearchParams({project:event.product,id:event.task_id}));
}
function datedRow(event) {
  const row=link('', datedHref(event),'bp-order');
  const details=el('div');
  details.append(el('strong',event.summary || 'Untitled work'));
  const clocks=rowClocks(event);
  for(const clock of clocks) {
    const bits=[clockLabel(clock), datedStamp(clock.at, clock.allDay)];
    if(clock.source) bits.push(clock.source);
    details.append(el('span', bits.join(' · '),'bp-order-meta'));
  }
  details.append(el('span', event.product,'bp-order-meta'));
  const decide=event.attention_face==='decide';
  const hold=clocks.find(clock=>clock.kind==='hold');
  const state=decide?'attention':(hold && hold.expired?'expired':(event.due?'all_day':(event.reminder?'scheduled':'dated')));
  const label=decide?'Needs you':(hold && hold.expired?'Expired':(event.due?'Due':(event.reminder?'Reminder':(event.mentioned?'Mentioned':'Dated work'))));
  row.append(details,badge(state,label));
  return row;
}
function formatDayHeading(key) {
  const [y,m,d]=String(key).split('-').map(Number);
  return new Date(y, m-1, d).toLocaleDateString([], {weekday:'short', month:'short', day:'numeric'});
}
function updateCalendarContext() {
  if($('calendar-project')) selectedProject=$('calendar-project').value;
  if(calendarDay && calendarDay===todayKey()) calendarDay='';
  const params=new URLSearchParams();
  if(selectedProject) params.set('project', selectedProject);
  if(calendarDay) params.set('day', calendarDay);
  history.replaceState(null,'',location.pathname+(params.size?'?'+params:'')+location.hash);
  if(snapshot) calendar();
}
function calendar() {
  const origin=calendarOrigin();
  const actualToday=todayKey();
  const datedItems=mergeDatedWork(snapshot.work_dates || []).filter(event=>!selectedProject || event.product===selectedProject);
  const todayItems=datedItems.filter(event=>agendaGroup(event, origin)==='today').sort((a,b)=>String(a.dtstart).localeCompare(String(b.dtstart)));
  const nextItems=datedItems.filter(event=>agendaGroup(event, origin)==='next').sort((a,b)=>String(a.dtstart).localeCompare(String(b.dtstart)));
  const pastItems=datedItems.filter(event=>agendaGroup(event, origin)==='past').sort((a,b)=>String(b.dtstart).localeCompare(String(a.dtstart)));
  $('calendar-today-heading').textContent=origin===actualToday ? 'Today' : formatDayHeading(origin);
  $('calendar-next-heading').textContent='Next';
  $('calendar-past-summary').textContent=(origin===actualToday ? 'Past and overdue' : 'Before this day')+' · '+pastItems.length;
  $('calendar-past-wrap').hidden=!pastItems.length;
  $('calendar-range').textContent=origin===actualToday ? 'Agenda from today.' : 'Agenda centred on '+formatDayHeading(origin)+'.';
  if($('calendar-project')) {
    const select=$('calendar-project');
    const current=selectedProject;
    select.replaceChildren(new Option('All projects',''));
    for(const project of snapshot.projects) select.add(new Option(project.name, project.id));
    if(current && !snapshot.projects.some(project=>project.id===current)) select.add(new Option(current+' (unavailable)', current));
    select.value=current;
  }
  reconcileList($('calendar-today'), todayItems, event=>event.product+':'+event.task_id, datedRow, {emptyText:origin===actualToday ? 'Nothing dated today.' : 'Nothing dated on this day.'});
  reconcileList($('calendar-next'), nextItems, event=>event.product+':'+event.task_id, datedRow, {emptyText:'No upcoming dated work.'});
  reconcileList($('calendar-past'), pastItems, event=>event.product+':'+event.task_id, datedRow, {emptyText:'No past dated work.'});
  const demand=snapshot.agents.filter(onDemandSeat);
  const scheduled=[...snapshot.agents.filter(agent=>!onDemandSeat(agent))].sort((a,b)=>String(a.next_fire || 'z').localeCompare(String(b.next_fire || 'z')));
  const scheduleItems=demand.length ? scheduled.concat([{id:'_on-demand-seats', on_demand:demand.length}]) : scheduled;
  reconcileList($('schedule-list'), scheduleItems, agent=>agent.id, agent=>{
    if(agent.on_demand) {
      const row=el('div',undefined,'bp-source');
      row.append(el('strong','On demand seats: '+agent.on_demand));
      row.append(el('p','Manual seats have no next run.','bp-muted'));
      return row;
    }
    const manual=agent.schedule==='manual' || agent.schedule==='Not scheduled';
    const state=agent.state==='unknown'?'unknown':(agent.state==='off'?'off':(agent.next_fire?'scheduled':(manual?'manual':'not_scheduled')));
    const row=el('div',undefined,'bp-source');
    row.append(el('strong',agent.name),badge(state, manual?'Manual':(agent.next_fire?'Scheduled':'No next run')));
    const when=agent.next_fire ? date(agent.next_fire) : (manual ? 'No next run' : 'No next run reported');
    row.append(el('p',`${when} · ${scheduleLabel(agent.schedule)}`,'bp-muted'));
    if(agent.last_run) row.append(el('p',`Last run: ${agent.last_run.outcome} · ${date(agent.last_run.at)}${agent.last_run.reason?' · '+agent.last_run.reason:''}`,'bp-muted'));
    return row;
  }, {emptyText:'No agent schedules available.'});
  const calendarSource=(snapshot.sources || []).find(source=>source.name==='Calendar');
  const eventEmpty=calendarSource?.state==='not_configured' ? 'No local calendar file. Agent schedules above are independent of a calendar file.' : (calendarSource?.state==='unavailable' ? 'Local calendar file could not be read.' : 'No local calendar events. Agent schedules above are independent of the calendar file.');
  const eventItems=[...snapshot.events].sort((a,b)=>String(a.at).localeCompare(String(b.at)));
  reconcileList($('event-list'), eventItems, event=>`${event.title}|${event.at}`, event=>{
    const row=el('details',undefined,'bp-event');const summary=el('summary');summary.append(el('strong',event.title || 'Untitled event'),el('span',`${date(event.at)} · ${event.source || 'Local calendar'} · ${event.state || 'State not specified'}`,'bp-order-meta'));row.append(summary,el('p',event.notes || 'No additional notes.','bp-note bp-muted'));
    return row;
  }, {emptyText:eventEmpty});
}
function capabilities() {
  const rows=sortBySeverity(capabilityEngineRows().map(([name, engine])=>({...engine, name})), row=>row.name);
  reconcileList($('capability-list'), rows, row=>row.name, row=>connectionRow(row.name, row, 'details'), {emptyText:'No live engine probes reported.'});
}
function engines() {
  const rows=sortBySeverity(receiptEngineRows().map(([name, engine])=>({...engine, name})), row=>row.name);
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
  if(page==='connections') { connectionExceptions();sources($('connection-list'),true);capabilities();engines();excludedStores();$('refresh-description').textContent=(streamState==='open' ? 'Live updates when the desk changes; ' : '')+(interval ? `fallback poll every ${streamState==='open'?60:interval} seconds while this page is visible` : 'manual fallback only');$('build').textContent=snapshot.build;$('workspace-path').textContent=workspace?.path || 'Not selected'; }
}
// Three independent clocks, never collapsed into one ambiguous word
// (STATES_AND_TERMS.md, pc-1483): the transport (is the push connection
// up), the last successful read (a fetch returned, whether or not its
// content changed), and the last meaningful content change (only moves
// when refresh()/refreshTimeline() see their content fingerprint differ —
// never on a bare read-time or heartbeat-tick churn).
function liveIndicator() {
  if(!lastSuccess) return lastError ? 'Unable to read workspace. Retry with Refresh.' : 'Connecting…';
  const transport = document.hidden ? 'Updates paused'
    : streamState==='open' ? 'Updates connected'
    : !everOpened ? 'Updates connecting…'
    : consecutiveErrors>=3 ? 'Updates polling every 60 s' : 'Updates reconnecting';
  const readAge=Math.floor((Date.now()-lastSuccess)/1000);
  const changeText=lastChangeAt ? `last change ${Math.floor((Date.now()-lastChangeAt)/1000)}s ago` : 'no change observed yet';
  return `${transport} · last read ${readAge}s ago · ${changeText}`;
}
function freshness() {
  const status=$('freshness');
  status.dataset.state=lastError?'error':'ok';
  const indicator=liveIndicator();
  status.textContent=lastError && lastSuccess ? `Refresh failed · showing last read · ${indicator}` : indicator;
}
async function refreshTimeline(append, opts = {}) {
  if (timelinePending || page !== 'timeline') return;
  // Once the reader has loaded older pages (timelineExpanded), a quiet
  // background poll (a change-feed push, not the reader's own Load more or
  // the explicit Refresh button) must not move their reading position —
  // it surfaces an affordance instead (pc-1483: "While reading older
  // events show a new-events affordance instead of moving the reading
  // position").
  const background = !append && timelineExpanded && !opts.force;
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
    if (background) {
      const currentTop = timelineData?.rows?.[0]?.id;
      $('timeline-new-events').hidden = !(data.rows.length && data.rows[0].id !== currentTop);
      lastSuccess = Date.now();
      lastError = false;
      return;
    }
    if (append && timelineData) {
      const seen = new Set(timelineData.rows.map(row => row.id));
      timelineData = {...data, rows: [...timelineData.rows, ...data.rows.filter(row => !seen.has(row.id))]};
    } else {
      timelineData = data;
      timelineExpanded = false;
      $('timeline-new-events').hidden = true;
    }
    timelineCursor = data.next_cursor || '';
    timelineMore = Boolean(data.next_cursor);
    timeline();
    lastSuccess = Date.now();
    lastError = false;
    // A successful read that returns the same rows is not a meaningful
    // change (pc-1483): only row ids and their event content move this
    // clock, never a bare identical read.
    const timelineKey = JSON.stringify((timelineData.rows || []).map(row => [row.id, row.event, row.title]));
    if (timelineKey !== timelineFingerprint) { timelineFingerprint = timelineKey; lastChangeAt = Date.now(); }
  } catch (error) {
    lastError = true;
    if (!timelineData) empty($('timeline-list'), 'Timeline is unavailable right now.');
  } finally {
    timelinePending = false;
    freshness();
  }
}
function deliveryItemRow(item) {
  const url=new URL(item.url);
  const row=link('',url.href,'bp-order');row.target='_blank';row.rel='noopener noreferrer';const text=el('div');
  text.append(el('strong',deliveryRow(item)),el('span',`Observed ${date(item.updated_at)}`,'bp-order-meta'));
  row.append(text,badge(item.state));
  return row;
}
function repoSection(repo) {
  const section=el('section',undefined,'bp-panel');const heading=el('div',undefined,'bp-section-head');
  heading.append(el('h2',repo.repo),badge(repo.state));section.append(heading);
  section.append(el('p',`${repo.role || 'Repository'} · ${repo.private===true?'Private':repo.private===false?'Public':'Visibility unknown'} · Observed ${date(repo.observed_at)}`,'bp-muted'));
  if(repo.error)section.append(el('p',repo.error,'bp-warning'));
  if(repo.missing?.length)section.append(el('p','Unavailable evidence: '+repo.missing.join(', '),'bp-warning'));
  const items=(repo.items || []).filter(item=>{try{const url=new URL(item.url);return url.protocol==='https:' && url.hostname==='github.com';}catch(error){return false;}});
  if(!items.length) empty(section,repo.quiet?'Quiet in the last 14 days.':'No verified delivery available.');
  else for(const item of items) section.append(deliveryItemRow(item));
  return section;
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
    // Reconciled, not a wholesale replaceChildren: an unchanged repository
    // section keeps its node identity and does not flash (pc-1483).
    reconcileList($('remote-repositories'), data.repositories || [], repo=>repo.repo, repoSection,
      {emptyText: data.refreshing ? '' : 'No repository delivery available. Check connection configuration or GitHub access.'});
  } catch(error) { $('remote-status').textContent='GitHub refresh failed. Previously displayed evidence may be stale.';$('github-connection-status').textContent='GitHub unavailable'; }
  finally { remotePending=false; }
}
// The content-change fingerprint ignores read-time and heartbeat-tick
// churn: 'observed_at' is stamped fresh on every read, 'sources[].last_at'
// and 'agents[].last_at' mirror the same daemon heartbeat tick on every
// entry, 'agents[].shift.age_seconds' is recomputed from the wall clock on
// every read of an otherwise-unchanged open shift, and probed engine rows
// (worklane_api, supervisor) stamp observed_at and last_success_at on every
// poll — none of those are application content, so a snapshot that only
// differs in these fields must not read as a meaningful change (pc-1483:
// "Content-change fingerprints ignore read times/heartbeat tick churn").
function stripShiftAge(shift) {
  if(!shift) return shift;
  const {age_seconds, ...rest}=shift;
  return rest;
}
function stripProbeTimes(engine) {
  if(!engine) return engine;
  const {observed_at, last_success_at, ...rest}=engine;
  return rest;
}
function contentKey(next) {
  if(page==='work') return JSON.stringify({orders:next.orders,projects:next.projects,workspace:next.workspace,sources:next.sources.map(s=>({name:s.name,state:s.state})),truncated:next.truncated});
  const sources=(next.sources || []).map(({last_at, ...rest})=>rest);
  const agents=(next.agents || []).map(({last_at, shift, ...rest})=>({...rest,shift:stripShiftAge(shift)}));
  const supervisor=next.supervisor ? (({last_at, shift, ...rest})=>({...rest,shift:stripShiftAge(shift)}))(next.supervisor) : next.supervisor;
  const engines=next.engines ? {
    ...next.engines,
    worklane_api:stripProbeTimes(next.engines.worklane_api),
    supervisor:stripProbeTimes(next.engines.supervisor),
  } : next.engines;
  return JSON.stringify({...next,observed_at:null,sources,agents,supervisor,engines});
}
async function refresh(manual) {
  if(pending) return;
  lastAttempt=Date.now();pending=true;
  if(manual) { $('refresh').disabled=true;$('refresh').textContent='Refreshing…'; }
  try {
    const response=await fetch('/api/operations',{cache:'no-store',signal:AbortSignal.timeout(10000)});
    if(!response.ok) throw new Error('Source request failed');
    const next=await response.json();
    const key=contentKey(next);
    snapshot=next;lastSuccess=Date.now();lastError=false;
    if(key!==fingerprint) { paint();fingerprint=key;lastChangeAt=Date.now(); }
  } catch(error) { lastError=true; }
  finally { pending=false;if(manual) { $('refresh').disabled=false;$('refresh').textContent='Refresh'; }freshness(); }
}
function updateFilters() {
  selectedProject=$('project-filter').value;selectedAssignment=$('assignment-filter').value;pageIndex=0;
  const params=new URLSearchParams();if(selectedProject)params.set('project',selectedProject);if(selectedAssignment)params.set('assignment',selectedAssignment);if($('status-filter').value)params.set('status',$('status-filter').value);if($('gate-filter').value)params.set('gate',$('gate-filter').value);if($('kind-filter').value)params.set('kind',$('kind-filter').value);if($('attention-filter').value)params.set('attention',$('attention-filter').value);if($('search').value)params.set('q',$('search').value);
  history.replaceState(null,'',location.pathname+(params.size?'?'+params:'')+location.hash);if(snapshot)work();
}
$('filters').addEventListener('submit',event=>event.preventDefault());
$('search').addEventListener('input',updateFilters);$('project-filter').addEventListener('change',updateFilters);$('status-filter').addEventListener('change',updateFilters);$('gate-filter').addEventListener('change',updateFilters);$('kind-filter').addEventListener('change',updateFilters);$('attention-filter').addEventListener('change',updateFilters);$('assignment-filter').addEventListener('change',updateFilters);
$('clear-filters').addEventListener('click',()=>{$('search').value='';$('project-filter').value='';$('assignment-filter').value='';$('status-filter').value='';$('gate-filter').value='';$('kind-filter').value='';$('attention-filter').value='';updateFilters();});
$('previous').addEventListener('click',()=>{pageIndex--;work();});$('next').addEventListener('click',()=>{pageIndex++;work();});
if ($('calendar-filters')) {
  $('calendar-filters').addEventListener('submit', event => event.preventDefault());
  $('calendar-project').addEventListener('change', updateCalendarContext);
  $('calendar-prev-week').addEventListener('click', () => { calendarDay = shiftDay(calendarOrigin(), -7); updateCalendarContext(); });
  $('calendar-next-week').addEventListener('click', () => { calendarDay = shiftDay(calendarOrigin(), 7); updateCalendarContext(); });
  $('calendar-today-btn').addEventListener('click', () => { calendarDay = ''; updateCalendarContext(); });
}
if ($('timeline-filters')) {
  $('timeline-project').value = timelineProject;
  $('timeline-source').value = timelineSource;
  $('timeline-actor').value = timelineActor;
  $('timeline-filters').addEventListener('submit', event => event.preventDefault());
  $('timeline-project').addEventListener('change', updateTimelineFilters);
  $('timeline-source').addEventListener('change', updateTimelineFilters);
  $('timeline-actor').addEventListener('change', updateTimelineFilters);
  $('timeline-actor').addEventListener('input', updateTimelineFilters);
  $('timeline-more').addEventListener('click', () => { timelineExpanded = true; refreshTimeline(true); });
  $('timeline-new-events').addEventListener('click', () => { timelineExpanded = false; refreshTimeline(false, {force: true}); });
}
$('refresh').addEventListener('click',()=>{refresh(true);refreshRemote();if(page==='timeline')refreshTimeline(false, {force: true});});
document.addEventListener('keydown',event=>{
  if(event.key!=='Escape') return;
  if(page==='agents' && selectedAgentId) {
    const closedId=selectedAgentId;
    selectAgent(closedId);
    const row=document.querySelector(`.bp-agent-select[data-agent-id="${CSS.escape(closedId)}"]`);
    if(row) row.focus();
    return;
  }
  $('desk-scope').open=false;
});
document.addEventListener('click',event=>{if(!$('desk-scope').contains(event.target))$('desk-scope').open=false;});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();freshness();});
$('preferences').addEventListener('submit',event=>event.preventDefault());
$('preferences').addEventListener('change',()=>{interval=Number($('refresh-preference').value);motion=$('motion-preference').value;document.body.classList.toggle('bp-reduce-motion',motion==='off');try{localStorage.setItem('bp-display',JSON.stringify({interval,motion}));$('preference-status').textContent='Saved in this browser.';}catch(error){$('preference-status').textContent='Applied for this page; browser storage is unavailable.';}});
connectChanges(()=>{if(!document.hidden){refresh();if(page==='timeline')refreshTimeline(false);}},state=>{streamState=state;if(state==='open'){everOpened=true;consecutiveErrors=0;}else if(state==='error'){consecutiveErrors++;}freshness();});
setInterval(()=>{const effective=streamState==='open'?60:interval;if(effective && !document.hidden && Date.now()-lastAttempt>=effective*1000)refresh();},1000);setInterval(freshness,1000);setInterval(()=>{if(!document.hidden && Date.now()-remoteLast>15000)refreshRemote();},1000);refresh();refreshRemote();if(page==='timeline')refreshTimeline(false);
})();
