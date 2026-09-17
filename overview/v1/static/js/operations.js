/* All source content is rendered as text. No source value becomes HTML. */
(async () => {
'use strict';
const {readerHref} = await import('/js/reader-navigation.mjs');
const {connectChanges} = await import('/js/change-feed.mjs');
const {reconcileList} = await import('/js/dom-reconcile.mjs');
const {buildLoadByDay, paintLoad, paintDoors} = await import('/js/calendar.v1.js');
const $ = id => document.getElementById(id);
const route = location.pathname.replace(/\/$/, '') || '/';
const page = ({'/':'overview','/overview':'overview','/work':'work','/projects':'projects','/agents':'agents','/connections':'connections','/delivery':'delivery','/activity':'delivery','/timeline':'timeline','/calendar':'calendar','/settings':'settings'})[route] || 'overview';
const titles = {delivery:['Delivery','Pull requests, CI and releases reported by GitHub; not agent activity.'],timeline:['Timeline','WorkLane events, WorkForce shifts, supervisor passes and GitHub delivery in one labelled stream.'],calendar:['Calendar','Today, upcoming runs, and dated work, with each clock labelled by its source.'],settings:['Settings','Display preferences and the application you are actually running.'],overview:['Overview','What needs you, what is moving, and what this desk can verify.'],work:['Work','Find an open work order, see its context, and read the full history.'],projects:['Projects','Which stores are hot, quiet, or blocked — open work, For You, and last motion.'],agents:['Agents','What each seat and job is doing right now, from the engine\'s own evidence.'],connections:['Connections','Where the information comes from, whether it is reachable and usable, and how current it is.']};
let snapshot = null, pending = false, lastSuccess = null, lastAttempt = 0, lastError = false, pageIndex = 0, fingerprint = '';
let selectedAgentId = '';
let agentsView = 'floor';
const size = 25;
let muted={};try {muted=JSON.parse(localStorage.getItem('bp-attention-mutes') || '{}');}catch(error){}
function muteKey(order){return JSON.stringify([snapshot?.workspace?.path,order.project,order.id]);}
function saveMutes(){try{localStorage.setItem('bp-attention-mutes',JSON.stringify(muted));}catch(error){}}
if($('restore-muted')) $('restore-muted').addEventListener('click',()=>{for(const order of snapshot.orders)delete muted[muteKey(order)];saveMutes();work();});
let remotePending = false, remoteLast = 0, remoteData = null;
let deliveryRepo = '', deliveryType = '', deliveryPeriod = '';
let timelineData = null, timelinePending = false, timelineCursor = '', timelineMore = false, timelineFingerprint = '', timelineExpanded = false;
let timelineProject = '', timelineSource = '', timelineActor = '', timelinePeriod = '';
let streamState = 'connecting', everOpened = false, consecutiveErrors = 0, lastChangeAt = null;
let interval = 15, motion = 'system';
try { const saved=JSON.parse(localStorage.getItem('bp-display') || '{}');if([0,15,30].includes(saved.interval))interval=saved.interval;if(saved.motion==='off')motion='off'; } catch(error) { /* Unavailable storage uses defaults. */ }
$('refresh-preference').value=String(interval);$('motion-preference').value=motion;
document.body.classList.toggle('bp-reduce-motion',motion==='off');
const query = new URLSearchParams(location.search);
if(page==='agents' && query.get('view')==='canvas') agentsView='canvas';
timelineProject = query.get('project') || '';
timelineSource = query.get('source') || '';
timelineActor = query.get('actor') || '';
timelinePeriod = query.get('period') || '';
deliveryRepo = query.get('repo') || '';
deliveryType = query.get('type') || '';
deliveryPeriod = query.get('period') || '';
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
if (attentionParam === 'any') { attentionParam = ''; }
if (attentionParam === 'seat_only' || attentionParam === 'seat-only') { attentionParam = 'seat'; legacyParam = true; }
if (attentionParam === 'my-todos') { attentionParam = 'my_todos'; legacyParam = true; }
if (attentionParam === 'act-now') { attentionParam = 'act_now'; legacyParam = true; }
if (query.get('blocked') === '1') { gateParam = gateParam || 'blocked'; legacyParam = true; }
const statusLegacy={backlog:'Open',in_progress:'Live',in_review:'Review',done:'Done',canceled:'Done',cancelled:'Done'};
const statusSelectValue = statusLegacy[statusParam] || statusParam;
if (attentionParam && !Array.from($('attention-filter').options).some(option=>option.value===attentionParam)) {
  const attentionLabels={decide:'Decide',read:'Read',watch:'Watch',due:'Due'};
  $('attention-filter').add(new Option(attentionLabels[attentionParam] || attentionParam, attentionParam));
}
$('status-filter').value = statusSelectValue;
$('gate-filter').value = gateParam;
$('kind-filter').value = kindParam;
$('attention-filter').value = attentionParam;
let selectedProject = query.get('project') || '';
let selectedAssignment = query.get('assignment') || '';
let unroutedOnly = query.get('unrouted') === '1';
let calendarDay = query.get('day') || '';
let projectsFilter = query.get('q') || '';
try { const saved=JSON.parse(localStorage.getItem('bp-projects') || '{}'); if(saved.filter) projectsFilter=saved.filter; } catch(error) { /* Unavailable storage uses defaults. */ }
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
if(page==='projects' && $('projects-filter')) $('projects-filter').value=projectsFilter;
document.querySelector(`[data-page="${page}"]`).setAttribute('aria-current','page');
import('/js/nav-shell.mjs').then(m => m.ensureActiveNavVisible()).catch(() => {});
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
    const event=deliveryPullEvent(item);
    return `PR #${item.number} · ${item.title} · ${event}`;
  }
  if(item.kind==='release') return `Release · ${item.title}`;
  return `${item.kind.replaceAll('_',' ')} · ${item.title}`;
}
function deliveryPullEvent(item) {
  if(item.merged_at || item.merged) return 'merged';
  if(item.pr_event) return item.pr_event;
  if(item.state==='open') return 'opened';
  return item.state;
}
function deliveryBadgeState(group, deployment) {
  if(group.deploy_state==='deployed') {
    // Activated only with a real activation time; a receipt without one is
    // Installed (pc-1487 second pass: never overclaim activation).
    const when=deployment?.activated_at ? date(deployment.activated_at) : '';
    const version=deployment?.version ? ` · ${deployment.version}` : '';
    const label=when ? `Activated ${when}` : `Installed${version}`;
    return ['deployed', label];
  }
  if(group.deploy_state==='version_note') {
    const version=deployment?.version ? ` ${deployment.version}` : '';
    return ['version_note', `Version note${version}`];
  }
  return [group.badge || 'unknown', (group.badge || 'unknown').replaceAll('_',' ')];
}
function deliveryPeriodCutoff() {
  if(!deliveryPeriod) return null;
  const days=Number(deliveryPeriod);
  return Number.isFinite(days) && days>0 ? Date.now()-days*86400000 : null;
}
function deliveryVisibleGroups(repo) {
  const groups=repo.groups || [];
  const cutoff=deliveryPeriodCutoff();
  return groups.filter(group=>{
    if(deliveryType && group.kind!==deliveryType) return false;
    if(!cutoff) return true;
    const at=Date.parse(group.updated_at || '');
    return Number.isNaN(at) || at>=cutoff;
  });
}
function deliverySummaryLine(repo) {
  const summary=repo.summary || {};
  const parts=[];
  if(summary.open_prs) parts.push(`${summary.open_prs} open PR${summary.open_prs===1?'':'s'}`);
  if(summary.failed_checks) parts.push(`${summary.failed_checks} failed check${summary.failed_checks===1?'':'s'}`);
  if(summary.pending_checks) parts.push(`${summary.pending_checks} pending check${summary.pending_checks===1?'':'s'}`);
  if(summary.recent_merges) parts.push(`${summary.recent_merges} merged`);
  if(summary.recent_releases) parts.push(`${summary.recent_releases} release${summary.recent_releases===1?'':'s'}`);
  if(repo.deployment?.version) {
    // Same rule as the group badges: the receipt counts as running only when a
    // group carries the sha match (deploy_state deployed), and Activated only
    // with an activation time (pc-1487 second pass).
    const activated=repo.deployment.activated_at ? date(repo.deployment.activated_at) : '';
    const shaMatched=(repo.groups || []).some(g=>g.deploy_state==='deployed');
    if(shaMatched) {
      const bit=activated ? `Activated ${activated}` : 'Installed';
      parts.push(`${bit} · ${repo.deployment.version}`);
    } else parts.push(`Version note ${repo.deployment.version}`);
  }
  return parts.length ? parts.join(' · ') : (repo.quiet ? 'Quiet in the last 14 days.' : 'No verified delivery available.');
}
function deliveryEvidenceRow(item) {
  const url=new URL(item.url);
  const row=link('',url.href,'bp-order');row.target='_blank';row.rel='noopener noreferrer';
  const text=el('div');
  text.append(el('strong',deliveryRow(item)),el('span',`Event ${date(item.updated_at)}`,'bp-order-meta'));
  const badgeState=item.kind==='pull_request' ? deliveryPullEvent(item) : item.state;
  row.append(text,badge(badgeState));
  return row;
}
function deliveryGroupRow(group, deployment) {
  if(group.items.length===1) {
    const item=group.items[0];
    const url=item.url ? new URL(item.url) : null;
    const row=url ? link('',url.href,'bp-order') : el('div','', 'bp-order');
    if(url) { row.target='_blank'; row.rel='noopener noreferrer'; }
    const text=el('div');
    text.append(el('strong',group.headline || deliveryRow(item)),el('span',`Event ${date(group.updated_at || item.updated_at)}`,'bp-order-meta'));
    row.append(text);
    const [state,label]=deliveryBadgeState(group, deployment);
    row.append(badge(state,label));
    return row;
  }
  const wrap=el('details',undefined,'bp-delivery-group');
  const summary=el('summary');
  const head=el('div');
  head.append(el('strong',group.headline || 'Delivery group'),el('span',`${group.items.length} events · Event ${date(group.updated_at)}`,'bp-order-meta'));
  summary.append(head);
  const [state,label]=deliveryBadgeState(group, deployment);
  summary.append(badge(state,label));
  wrap.append(summary);
  for(const item of group.items) wrap.append(deliveryEvidenceRow(item));
  return wrap;
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
const YOU_KINDS=new Set(['todo','note','reminder']);
const WORK_BAND_LIMIT=8;
const SEAT_PREVIEW_SEATS=3;
const SEAT_PREVIEW_PER_SEAT=3;
const SEAT_CHIP_NAMED=2;
const BAND_VIRTUAL_WINDOW=50;
let bandWindow={act_now:BAND_VIRTUAL_WINDOW,my_todos:BAND_VIRTUAL_WINDOW,seat_backlog:BAND_VIRTUAL_WINDOW};
function hasWorkerYou(order) {
  return Boolean(order.assigned_you) || (order.workers || []).includes('you');
}
function hasSeatWorker(order) {
  return (order.workers || []).some(worker=>worker!=='you');
}
function isYouKind(order) {
  return YOU_KINDS.has(order.kind || '');
}
function isActNow(order) {
  if(isClosedOrder(order)) return false;
  if(order.attention_face==='decide' && order.gate_type==='human') return true;
  return order.attention_face==='read';
}
function isMyTodo(order) {
  if(isClosedOrder(order) || isActNow(order) || order.gate_type==='human') return false;
  return hasWorkerYou(order) && isYouKind(order);
}
function isSeatBacklog(order) {
  if(isClosedOrder(order) || isActNow(order) || isMyTodo(order)) return false;
  if(order.status!=='backlog' && order.status!=='in_progress' && order.status!=='in_review') return false;
  return order.gate_type!=='human';
}
function boardBand(order) {
  if(order.board_band) return order.board_band;
  if(isActNow(order)) return 'act_now';
  if(isMyTodo(order)) return 'my_todos';
  if(isSeatBacklog(order)) return 'seat_backlog';
  return '';
}
function rowFace(order) {
  if(order.row_face) return order.row_face;
  if(order.attention_face==='decide') return 'Decide';
  if(order.attention_face==='read') return 'Read';
  if(order.attention_face==='watch') return 'Watch';
  if(order.attention_face==='due' || isYouKind(order)) return 'Note';
  if(order.you_host) return 'Host';
  if((order.kind || 'work')==='work' && hasWorkerYou(order) && !hasSeatWorker(order)) return 'Host';
  return 'none';
}
function watchIsStalled(order) {
  return order.attention_face==='watch' && order.gate_type!=='timer';
}
function rowStatus(order) {
  if(order.row_status) return order.row_status;
  if(isClosedOrder(order)) return 'Done';
  if(order.status==='in_progress') return watchIsStalled(order) ? 'Stalled' : 'Live';
  if(order.status==='in_review') return watchIsStalled(order) ? 'Stalled' : 'Review';
  if(order.gate_type==='deferred') return 'Deferred';
  if(order.ready_for) return 'Ready';
  if(watchIsStalled(order)) return 'Stalled';
  return 'Open';
}
function matchesStatusFacet(order, value) {
  if(!value) return true;
  const mapped={backlog:'Open',in_progress:'Live',in_review:'Review',done:'Done',canceled:'Done',cancelled:'Done'}[value] || value;
  return rowStatus(order)===mapped;
}
function matchesAttentionFacet(order, value) {
  if(!value || value==='any') return true;
  if(value==='act_now' || value==='decide' || value==='read') {
    if(!isActNow(order)) return false;
    if(value==='decide') return order.attention_face==='decide';
    if(value==='read') return order.attention_face==='read';
    return true;
  }
  if(value==='my_todos') return isMyTodo(order);
  if(value==='seat' || value==='seat_only') return isSeatBacklog(order);
  if(value==='watch' || value==='due') return order.attention_face===value;
  return true;
}
function partitionBands(orders) {
  const bands={act_now:[],my_todos:[],seat_backlog:[]};
  for(const order of orders) {
    const band=boardBand(order);
    if(band && bands[band]) bands[band].push(order);
  }
  return bands;
}
function attentionShowsBand(attention, band) {
  if(!attention || attention==='any' || attention==='watch' || attention==='due') return true;
  if(band==='act_now') return attention==='act_now' || attention==='decide' || attention==='read';
  if(band==='my_todos') return attention==='my_todos';
  if(band==='seat_backlog') return attention==='seat' || attention==='seat_only';
  return true;
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
  const face=rowFace(order);
  const status=rowStatus(order);
  const faceBadge=badge(face.toLowerCase(), face);
  faceBadge.dataset.kind='face';
  const statusBadge=badge(status.toLowerCase(), status);
  statusBadge.dataset.kind='status';
  return [faceBadge, statusBadge];
}
function relativeAge(value) {
  const parsed=Date.parse(String(value || ''));
  if(Number.isNaN(parsed)) return '';
  const seconds=Math.max(0, Math.round((Date.now()-parsed)/1000));
  if(seconds<60) return seconds+'s ago';
  const minutes=Math.floor(seconds/60);
  if(minutes<60) return minutes+'m ago';
  const hours=Math.floor(minutes/60);
  if(hours<48) return hours+'h ago';
  return Math.floor(hours/24)+'d ago';
}
function seatDisplayName(id) {
  if(!id || id==='unassigned') return 'Unassigned';
  if(id==='you') return 'You';
  const agent=(snapshot && snapshot.agents || []).find(item=>item.id===id);
  return (agent && agent.name) || id;
}
function seatChipForOrder(order) {
  const hand=seatHand(order);
  const name=hand ? seatDisplayName(hand) : '';
  if(!name || name==='Unassigned') return null;
  const chip=el('button', name, 'bp-work-row-seat');
  chip.type='button';
  chip.addEventListener('click', event=>{
    event.preventDefault();
    event.stopPropagation();
    scopeSeatLoad({id:hand, name, kind:'seat'});
  });
  return chip;
}
function workBoardRow(order) {
  const row=el('div',undefined,'bp-order bp-order-compact bp-work-row');
  const badges=el('div',undefined,'bp-order-badges');
  badges.append(...orderBadges(order));
  const anchor=link('',workUrl(order),'bp-order-link');
  anchor.append(el('strong',order.title));
  row.append(badges, anchor);
  const seat=seatChipForOrder(order);
  if(seat) row.append(seat);
  const age=relativeAge(order.updated_at);
  if(age) row.append(el('span', age, 'bp-work-row-age'));
  return row;
}
function orderRow(order) {
  return workBoardRow(order);
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
  const faceBadge={decide:'Needs you',read:'Read',watch:'Watch',due:'Due',note:'Note'}[order.attention_face] || 'For You';
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
function overviewSourceLine() {
  const host=$('overview-source-line');
  if(!host) return;
  const rows=snapshot.sources || [];
  host.replaceChildren();
  if(!rows.length) {
    host.append(el('span','No data sources reported. '));
    host.append(link('Connections','/connections'));
    return;
  }
  const exceptions=rows.filter(isException);
  const bits=[`${rows.length} source${rows.length===1?'':'s'}`];
  if(exceptions.length) bits.push(`${exceptions.length} need attention`);
  host.append(el('span', bits.join(' · ') + '. '));
  host.append(link('Connections','/connections'));
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
function workforceHeartbeatState() {
  const heartbeat=(snapshot.sources || []).find(s=>s.name==='WorkForce heartbeat');
  if(!heartbeat || heartbeat.state==='unknown') return 'unknown';
  return heartbeat.state;
}
function projectCountCell(project, field) {
  if(project.state!=='available') return el('span','Store unavailable','bp-muted');
  if(project.partial) return el('span',`${project[field]} partial (limited to 2,000)`,'bp-muted');
  return el('span',String(project[field] ?? 0));
}
function projectLiveParkedText(project) {
  if(project.state!=='available') return '—';
  const live=project.claimed || 0, parked=project.parked || 0;
  const bits=[];
  if(live) bits.push(`${live} live`);
  if(parked) bits.push(`${parked} parked`);
  const base=bits.length ? bits.join(' · ') : '0';
  if(project.partial) return `${base} partial (limited to 2,000)`;
  return base;
}
function projectLiveSeats(project) {
  const seen=new Set(), seats=[];
  for(const order of (snapshot.orders || [])) {
    if(order.project!==project.id || order.status!=='in_progress' || !order.live_with || seen.has(order.live_with)) continue;
    seen.add(order.live_with);
    seats.push({id:order.live_with, agent:(snapshot.agents || []).find(a=>a.id===order.live_with)});
  }
  // A seat that is still finishing an order it parked in this project (shift
  // open, claim released) is live for this row too; Agents shows it as
  // "Finishing · parked …" and Projects must not read Quiet (pc-1486 second pass).
  for(const agent of (snapshot.agents || [])) {
    if(!agent.finishing || seen.has(agent.id)) continue;
    if(!(agent.parked || []).some(p=>p.project===project.id)) continue;
    seen.add(agent.id);
    seats.push({id:agent.id, agent, finishing:true});
  }
  return seats;
}
function projectCoverageRow(project) {
  return (snapshot.coverage || []).find(item=>item.project===project.id);
}
function projectCoverageLists(row) {
  const present=Array.isArray(row?.present) ? row.present : [];
  const held=Array.isArray(row?.held) ? row.held : [];
  return {present, held};
}
function projectHasRegisteredSeats(project) {
  const {present, held}=projectCoverageLists(projectCoverageRow(project));
  return present.length || held.length;
}
function seatProviderFromId(seatId) {
  if(seatId==='you') return null;
  const slug=seatId.replace(/^bp-/,'').replace(/-implementer$/,'');
  if(!slug) return null;
  return slug.charAt(0).toUpperCase()+slug.slice(1);
}
function projectCoverageStaffedText(project, {skipProviders=new Set()}={}) {
  const row=projectCoverageRow(project);
  const {present, held}=projectCoverageLists(row);
  if(!row || (!present.length && !held.length)) return '';
  const bits=[];
  const idlePresent=present.filter(provider=>!skipProviders.has(provider));
  if(idlePresent.length===1) bits.push(`${idlePresent[0]} idle`);
  else if(idlePresent.length>1) bits.push(`${idlePresent.join(', ')} idle`);
  for(const provider of held) bits.push(`${provider} off`);
  return bits.join(', ');
}
function projectAgentsNowText(project) {
  if(workforceHeartbeatState()==='unknown') return 'unknown';
  const live=projectLiveSeats(project);
  const liveBits=live.map(({id, agent, finishing})=>{
    const name=id==='you' ? 'you' : id.replace(/^bp-/,'').replace(/-implementer$/,'');
    const badge=agent ? (finishing ? 'finishing' : (agent.state==='working' ? 'working' : agent.badge.toLowerCase())) : 'live';
    return `${name} · ${badge}`;
  });
  const liveProviders=new Set(live.map(({id})=>seatProviderFromId(id)).filter(Boolean));
  const coverageBits=projectCoverageStaffedText(project, {skipProviders: liveProviders});
  const parts=[...liveBits];
  if(coverageBits) parts.push(coverageBits);
  if(parts.length) return parts.join(', ');
  return 'none staffed';
}
function projectReturnTo() {
  const params=new URLSearchParams();
  if(projectsFilter) params.set('q', projectsFilter);
  const qs=params.toString();
  return '/projects'+(qs ? '?'+qs : '');
}
function projectLastChangeText(project) {
  if(project.state!=='available') return 'Store unavailable';
  const change=project.last_change;
  if(!change || !change.at) return 'no activity recorded';
  const time=new Date(change.at);
  const clock=Number.isNaN(time.valueOf()) ? '' : time.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
  const detail=change.text || `${change.verb || 'update'} ${change.order_id || ''}`.trim();
  return clock ? `${clock} ${detail}` : detail;
}
function projectGoLinks(project) {
  const wrap=el('span',undefined,'bp-projects-go');
  const params=id=>new URLSearchParams({project:id});
  const retained=new URLSearchParams({project:project.id, return_to:projectReturnTo()});
  wrap.append(link('Work','/work?'+params(project.id)), link('For You','/work?'+new URLSearchParams({project:project.id,attention:'any'})),
    link('Agents','/agents?'+retained), link('Delivery','/delivery?'+retained),
    link('Papers','/documents?'+params(project.id)), link('Map','/map?project='+encodeURIComponent(project.id)));
  return wrap;
}
function projectBreakdown(project) {
  const orders=(snapshot.orders || []).filter(o=>o.project===project.id);
  const body=el('div',undefined,'bp-projects-breakdown');
  const statusCounts={}, gateCounts={};
  for(const order of orders) {
    statusCounts[order.status_word || order.status]=(statusCounts[order.status_word || order.status]||0)+1;
    const gate=order.gate_type || 'none';
    gateCounts[gate]=(gateCounts[gate]||0)+1;
  }
  body.append(el('p',`Open by status: ${Object.entries(statusCounts).map(([k,v])=>`${k} ${v}`).join(' · ') || 'none'}`,'bp-muted'));
  body.append(el('p',`Gate counts: ${Object.entries(gateCounts).map(([k,v])=>`${k} ${v}`).join(' · ') || 'none'}`,'bp-muted'));
  const held=orders.filter(o=>o.live_with || o.parked_by);
  if(held.length) {
    const list=el('ul');
    for(const order of held.slice(0,6)) list.append(el('li',`${order.id} · ${order.live_with ? 'live with '+order.live_with : 'parked by '+order.parked_by}`));
    body.append(el('p','Live / parked orders','bp-muted'), list);
  }
  const seats=(snapshot.agents || []).filter(a=>a.group==='seat' && a.project===project.id);
  if(seats.length) {
    const list=el('ul');
    for(const seat of seats) {
      const outcome=seat.last_run ? `${seat.last_run.outcome}` : 'no run recorded';
      list.append(el('li',`${seat.name} · ${seat.badge} · last ${outcome}`));
    }
    body.append(el('p','Registered seats','bp-muted'), list);
  }
  const recent=orders.filter(o=>o.updated_at).sort((a,b)=>new Date(b.updated_at)-new Date(a.updated_at)).slice(0,3);
  if(recent.length) {
    const list=el('ul');
    for(const order of recent) list.append(el('li',`${order.id} · ${order.status_word} · ${date(order.updated_at)}`));
    body.append(el('p','Recent changes','bp-muted'), list);
  }
  return body;
}
function emptyPortfolio() {
  return {state:'empty', peak_open:0, hot:0, quiet:0, blocked:0, projects:[]};
}
function portfolioFromSnapshot() {
  const data=snapshot && snapshot.portfolio;
  if(data && Array.isArray(data.projects)) return data;
  return emptyPortfolio();
}
function projectPulseFromSnapshot(id) {
  return (portfolioFromSnapshot().projects || []).find(row=>row.id===id) || null;
}
function stackedOpenBar(open, attention, peak) {
  const wrap=el('span',undefined,'bp-projects-stack');
  wrap.setAttribute('aria-hidden','true');
  const scale=Math.max(1, peak || open || 1);
  const bar=el('span',undefined,'bp-projects-stack-bar');
  bar.style.width=Math.max(4, Math.round((Math.max(0, open)/scale)*100))+'%';
  if(open>0) {
    const youPct=Math.round((Math.min(attention, open)/open)*100);
    const you=el('span',undefined,'bp-projects-stack-you');
    you.style.width=youPct+'%';
    const rest=el('span',undefined,'bp-projects-stack-open');
    rest.style.width=(100-youPct)+'%';
    bar.append(you, rest);
  }
  wrap.append(bar);
  return wrap;
}
function projectSparkCell(project) {
  const cell=el('div',undefined,'bp-projects-spark');
  const pulse=projectPulseFromSnapshot(project.id);
  if(project.state!=='available') {
    cell.append(el('span','Store unavailable','bp-muted'));
    return cell;
  }
  const data=pulse || {pulse:'quiet', open:project.open||0, attention:project.attention||0, hours:[], state:'empty'};
  const chip=el('span', data.pulse, 'bp-projects-pulse');
  chip.dataset.pulse=data.pulse;
  cell.append(chip);
  if(data.open) cell.append(stackedOpenBar(data.open, data.attention||0, portfolioFromSnapshot().peak_open));
  const glyphs=throughputSpark(data.hours);
  if(glyphs) {
    const spark=el('span', glyphs, 'bp-projects-spark-line');
    spark.setAttribute('aria-hidden','true');
    cell.append(spark);
  }
  return cell;
}
function paintProjectsCompare() {
  const host=$('projects-compare');
  const summary=$('projects-compare-summary');
  if(!host) return;
  const data=portfolioFromSnapshot();
  const filter=(projectsFilter || '').trim().toLowerCase();
  const rows=(data.projects || []).filter(row=>{
    if(filter && !(row.name||'').toLowerCase().includes(filter) && !(row.id||'').toLowerCase().includes(filter)) return false;
    return row.pulse!=='quiet';
  });
  const pulseRank={hot:0, blocked:1, unavailable:2};
  rows.sort((a,b)=>{
    const rank=(pulseRank[a.pulse] ?? 9)-(pulseRank[b.pulse] ?? 9);
    if(rank) return rank;
    if((b.open||0)!==(a.open||0)) return (b.open||0)-(a.open||0);
    if((b.attention||0)!==(a.attention||0)) return (b.attention||0)-(a.attention||0);
    return (a.name||'').localeCompare(b.name||'');
  });
  if(summary) {
    if(data.state==='unavailable') summary.textContent='Portfolio unavailable';
    else {
      const bits=[];
      if(data.hot) bits.push(data.hot===1 ? '1 hot' : `${data.hot} hot`);
      if(data.blocked) bits.push(data.blocked===1 ? '1 blocked' : `${data.blocked} blocked`);
      if(data.quiet) bits.push(data.quiet===1 ? '1 quiet' : `${data.quiet} quiet`);
      summary.textContent=bits.join(' · ');
    }
  }
  if(data.state==='unavailable') {
    host.hidden=false;
    host.replaceChildren(el('p','Portfolio unavailable','bp-muted'));
    return;
  }
  if(!rows.length) {
    host.hidden=true;
    host.replaceChildren();
    return;
  }
  host.hidden=false;
  reconcileList(host, rows, row=>row.id, row=>{
    const article=el('div',undefined,'bp-projects-compare-row');
    article.dataset.pulse=row.pulse;
    article.dataset.project=row.id;
    const name=link(row.name || row.id, row.href || ('/work?project='+row.id), 'bp-projects-compare-name');
    const meta=el('span',undefined,'bp-projects-compare-meta');
    if(row.state==='unavailable') {
      meta.append(el('span','Store unavailable','bp-muted'));
      article.append(name, el('span','','bp-projects-stack'), meta);
      return article;
    }
    const stack=row.open ? stackedOpenBar(row.open, row.attention||0, data.peak_open) : el('span',undefined,'bp-projects-stack');
    meta.append(link((row.open||0)+' open', row.href || ('/work?project='+row.id)));
    if(row.attention) meta.append(link(row.attention+' For You', row.attention_href || ('/work?project='+row.id+'&attention=any')));
    if(row.map_href) meta.append(link('Map', row.map_href));
    if(row.pulse==='blocked') meta.append(el('span','blocked','bp-muted'));
    const glyphs=throughputSpark(row.hours);
    if(glyphs) {
      const spark=el('span', glyphs, 'bp-projects-spark-line');
      spark.setAttribute('aria-hidden','true');
      meta.append(spark);
    }
    article.append(name, stack, meta);
    return article;
  });
}
function projectComparisonRow(project) {
  const row=el('article',undefined,'bp-projects-row');
  row.dataset.project=project.id;
  const name=el('div',undefined,'bp-projects-name');
  name.append(el('strong',project.name), el('span',project.id,'bp-muted'), projectSparkCell(project));
  row.append(name, projectCountCell(project,'open'), projectCountCell(project,'attention'),
    project.state==='available' ? projectCountCell(project,'deferred') : el('span','—','bp-muted'),
    el('span',projectLiveParkedText(project)), el('span',projectAgentsNowText(project),'bp-projects-agents'),
    el('span',projectLastChangeText(project),'bp-projects-change'), projectGoLinks(project));
  const detail=el('details',undefined,'bp-projects-detail');
  detail.append(el('summary','Breakdown'), projectBreakdown(project));
  row.append(detail);
  return row;
}
function projectIsQuiet(project) {
  if(project.state!=='available') return false;
  return !project.open && !project.running && !project.claimed && !project.attention
    && !projectLiveSeats(project).length && !projectHasRegisteredSeats(project);
}
function projectActivityRank(project) {
  if(project.running) return 0;
  if(project.claimed) return 1;
  if(project.attention) return 2;
  if(project.open) return 3;
  return 4;
}
function projectActivitySort(a,b) {
  const rank=projectActivityRank(a)-projectActivityRank(b);
  if(rank) return rank;
  if(b.attention!==a.attention) return b.attention-a.attention;
  if(b.open!==a.open) return b.open-a.open;
  return a.name.localeCompare(b.name);
}
function projectsQuietBundle(rows) {
  const bundle=el('details',undefined,'bp-projects-collapsed');
  bundle.append(el('summary',`Quiet projects (no open work, no seats): ${rows.map(r=>r.name).join(', ')}`));
  const inner=el('div',undefined,'bp-projects-collapsed-rows');
  for(const row of rows) inner.append(projectComparisonRow(row));
  bundle.append(inner);
  return bundle;
}
function projects() {
  const filter=(projectsFilter || '').trim().toLowerCase();
  const all=(snapshot.projects || []).filter(p=>!filter || p.name.toLowerCase().includes(filter) || p.id.toLowerCase().includes(filter));
  const active=[], quiet=[];
  for(const project of all.sort(projectActivitySort)) (projectIsQuiet(project) ? quiet : active).push(project);
  const unavailable=(snapshot.projects || []).filter(p=>p.state!=='available').length;
  const readable=(snapshot.projects || []).filter(p=>p.state==='available').length;
  const readAge=lastSuccess ? Math.max(0,Math.floor((Date.now()-lastSuccess)/1000)) : null;
  $('projects-summary').textContent=`${snapshot.projects.length} stores · ${unavailable ? `${unavailable} unavailable` : 'all readable'} · read ${readAge===null ? '…' : readAge+'s ago'}`;
  paintProjectsCompare();
  const items=[...active];
  if(quiet.length) items.push({id:'__quiet__', rows:quiet});
  reconcileList($('projects-list'), items, item=>item.id, item=>{
    if(item.id==='__quiet__') return projectsQuietBundle(item.rows);
    return projectComparisonRow(item);
  }, {emptyText:'No local project stores found. A folder needs .protocolcity/desk-join.json to register.'});
}
function overviewDecideRow(order) {
  const row=el('div',undefined,'bp-order bp-order-compact bp-overview-decide');
  const anchor=link('',workUrl(order),'bp-order-link');
  const content=el('div');
  content.append(el('strong',[order.title,order.project_name].filter(Boolean).join(' · ')));
  anchor.append(content);
  row.append(anchor,badge('attention','Needs you'));
  return row;
}
function overviewFaceChip(label, count, href, face) {
  const chip=link(`${label} · ${count}`, href, 'bp-filter-chip bp-face-chip');
  if(face) chip.dataset.face=face;
  return chip;
}
function faceHost(face, part) {
  return $(`work-for-you-${face}-${part}`) || $(`for-you-${face}-${part}`);
}
function faceEntry(order) {
  const entry=el('div',undefined,'bp-face-entry');entry.append(overviewFaceRow(order));
  const mute=el('button','Mute 24h');mute.type='button';mute.className='bp-face-mute';
  mute.addEventListener('click',()=>{muted[muteKey(order)]=Date.now()+86400000;saveMutes();work();});
  entry.append(mute);
  return entry;
}
function faceHeading(label, total, visible, href) {
  let text=`${label} · ${total}`;
  if(total > visible) text+=` · showing ${visible}`;
  const summary=faceHost(label.toLowerCase(), 'summary');
  if(summary) summary.textContent=text;
  const linkWrap=summary && summary.parentElement && summary.parentElement.querySelector('a');
  if(linkWrap && total > visible && href) linkWrap.textContent=`View all ${total}`;
}
function bindForYouFaceToggle(face) {
  const details=faceHost(face, 'details');
  if(!details || details.dataset.toggleBound) return;
  details.dataset.toggleBound='1';
  details.addEventListener('toggle',()=>{ details.dataset.userToggled='1'; });
}
function syncForYouFaceOpen(face, count) {
  const details=faceHost(face, 'details');
  if(!details) return;
  bindForYouFaceToggle(face);
  if(details.dataset.userToggled) return;
  if(face==='decide' || face==='read') details.open=true;
  else details.open=count > 0;
}
function overviewExecutionEmpty() {
  const heartbeat=(snapshot.sources || []).find(s=>s.name==='WorkForce heartbeat');
  if(!heartbeat || heartbeat.state==='unknown') return 'WorkForce daemon not reachable — no shift evidence to show.';
  if(heartbeat.state==='stale') return 'WorkForce heartbeat is stale; running seats may not be reported.';
  return 'No seats report an open shift right now.';
}
function noteLiveSource(change) {
  if (!change || !change.source) return;
  // Current execution is WorkForce shift evidence only — WorkLane claim
  // activity must not stamp or flash this panel (pc-1504).
  if (change.source !== 'workforce') return;
  const host=$('overview-executions');
  if (!host) return;
  host.dataset.liveSource=change.source;
  const observed=change.observed_at ? ` · ${change.source} ${change.observed_at}` : ` · ${change.source}`;
  const cue=$('overview-exec-cue');
  if (cue) cue.textContent=observed.replace(/^ · /,'');
  if (document.body.classList.contains('bp-reduce-motion')) return;
  host.classList.remove('bp-live-flash');
  void host.offsetWidth;
  host.classList.add('bp-live-flash');
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
  reconcileList($('overview-executions'), running, a=>a.id, executionRow, running.length ? {} : {emptyText:overviewExecutionEmpty()});
  const metrics=[['For You',forYou.length,'/work?attention=any'],['Running',running.length,'/agents'],['Claimed',live.length,'/work?status=in_progress'],['Open work',snapshot.projects.filter(x=>x.state==='available').reduce((sum,p)=>sum+p.open,0),'/work'],['Seats · Jobs',`${seats} · ${jobs}`,'/agents']];
  reconcileList($('metrics'), metrics, m=>m[0], ([label,count,href])=>{const a=link('',href,'bp-metric');a.append(el('strong',String(count)),el('span',label));return a;});
  paintOverviewThroughput();
  const unrouted=orders.filter(isUnrouted), unroutedHost=$('overview-unrouted');
  if(unroutedHost) {
    unroutedHost.replaceChildren();
    unroutedHost.append(document.createTextNode('Unrouted '), link(String(unrouted.length), UNROUTED_WORK_HREF));
    unroutedHost.append(el('span', unrouted.length ? ' — open, ungated orders with no seat' : ' — none right now'));
  }
  // Overview Act-now is the true Decide pile (Mute lives on Work). Cap the
  // visible rows and always paint the remainder door — never silent truncate
  // (pc-1511).
  const decide=forYou.filter(o=>o.attention_face==='decide');
  const decideVisible=decide.slice(0,OVERVIEW_DECIDE_LIMIT);
  reconcileList($('for-you-decide'), decideVisible, o=>o.project+':'+o.id, overviewDecideRow, {emptyText:'Nothing for You'});
  const decideMore=$('overview-decide-more');
  if(decideMore) {
    const remainder=decide.length-decideVisible.length;
    decideMore.replaceChildren();
    if(remainder>0) {
      decideMore.hidden=false;
      const door=link('+'+remainder+' more on Work', DECIDE_WORK_HREF, 'bp-filter-chip bp-face-chip');
      door.dataset.face='decide';
      decideMore.append(door);
    } else {
      decideMore.hidden=true;
    }
  }
  const chips=$('overview-face-chips');
  if(chips) {
    const doors=calendarDoorsFromSnapshot();
    const faces=[['Read','read'],['Watch','watch'],['Due','due']];
    reconcileList(chips, faces, face=>face[1], ([label,face])=>{
      if(face==='due') return overviewFaceChip(label, doors.due_count, doors.due_href || '/calendar', face);
      return overviewFaceChip(label, forYou.filter(o=>o.attention_face===face).length, '/work?attention='+face, face);
    });
  }
  overviewSourceLine();
}
function remainderLabel(remainder, key) {
  if(key==='act_now') return '+'+remainder+' more in Act now';
  if(key==='my_todos') return '+'+remainder+' more · My todos';
  if(key==='seat_backlog') return '+'+remainder+' more · filter by seat';
  return '+'+remainder+' more';
}
function openWorkDoor(key) {
  const attention=$('attention-filter');
  if(attention) {
    if(key==='act_now') attention.value='act_now';
    else if(key==='my_todos') attention.value='my_todos';
    else if(key==='seat_backlog') attention.value='seat';
  }
  updateWorkFilters();
}
function bandIsOpen(attention, bandKey) {
  if(bandKey==='act_now') return attention==='act_now' || attention==='decide' || attention==='read';
  if(bandKey==='my_todos') return attention==='my_todos';
  if(bandKey==='seat_backlog') return attention==='seat' || attention==='seat_only';
  return false;
}
function renderWorkMore(host, remainder, key, mode) {
  if(!host) return;
  host.replaceChildren();
  if(remainder>0) {
    host.hidden=false;
    const button=el('button', mode==='window' ? '+'+remainder+' more' : remainderLabel(remainder, key));
    button.type='button';
    button.addEventListener('click',()=>{
      if(mode==='window') {
        bandWindow[key]=(bandWindow[key] || BAND_VIRTUAL_WINDOW)+BAND_VIRTUAL_WINDOW;
        work();
        return;
      }
      openWorkDoor(key);
    });
    host.append(button);
  } else {
    host.hidden=true;
  }
}
function groupSeatOrders(orders) {
  const groups=new Map();
  const statusRank={Stalled:0,Ready:1,Live:2,Review:3,Open:4,Deferred:5};
  for(const order of orders) {
    const key=seatHand(order) || 'unassigned';
    if(!groups.has(key)) groups.set(key,{id:key,name:seatDisplayName(key),orders:[],ready:0,stalled:0});
    const group=groups.get(key);
    group.orders.push(order);
    const status=rowStatus(order);
    if(status==='Ready') group.ready+=1;
    if(status==='Stalled') group.stalled+=1;
  }
  for(const group of groups.values()) {
    group.orders.sort((a,b)=>orderUpdatedAt(b)-orderUpdatedAt(a));
    group.orders.sort((a,b)=>(statusRank[rowStatus(a)] ?? 9)-(statusRank[rowStatus(b)] ?? 9));
    group.total=group.orders.length;
  }
  return [...groups.values()].sort((a,b)=>(b.stalled-a.stalled)||(b.ready-a.ready)||String(a.name).localeCompare(String(b.name)));
}
function seatGroupRow(group) {
  const wrap=el('details',undefined,'bp-work-seat-group');
  wrap.open=true;
  wrap.dataset.seat=group.id;
  const summary=el('summary');
  summary.append(el('strong',group.name),el('span',String(group.total || group.orders.length),'bp-work-count'));
  wrap.append(summary);
  const list=el('div',undefined,'bp-work-seat-items');
  reconcileList(list, group.orders, o=>o.project+':'+o.id, orderRow, {});
  wrap.append(list);
  return wrap;
}
function renderSeatBacklog(orders) {
  const host=$('work-seat-backlog');
  if(!host) return;
  const attention=$('attention-filter') && $('attention-filter').value;
  const open=bandIsOpen(attention, 'seat_backlog');
  const groups=groupSeatOrders(orders);
  if(!open) {
    const preview=[];
    let painted=0;
    for(const group of groups.slice(0, SEAT_PREVIEW_SEATS)) {
      const rows=group.orders.slice(0, SEAT_PREVIEW_PER_SEAT);
      preview.push(Object.assign({}, group, {orders:rows}));
      painted+=rows.length;
    }
    reconcileList(host, preview, group=>group.id, seatGroupRow, {emptyText:'No seat backlog'});
    renderWorkMore($('work-seat-backlog-more'), orders.length-painted, 'seat_backlog');
    return;
  }
  const windowSize=bandWindow.seat_backlog || BAND_VIRTUAL_WINDOW;
  let remaining=windowSize;
  const visible=[];
  let painted=0;
  for(const group of groups) {
    if(remaining<=0) break;
    const rows=group.orders.slice(0, remaining);
    visible.push(Object.assign({}, group, {orders:rows}));
    remaining-=rows.length;
    painted+=rows.length;
  }
  reconcileList(host, visible, group=>group.id, seatGroupRow, {emptyText:'No seat backlog'});
  renderWorkMore($('work-seat-backlog-more'), orders.length-painted, 'seat_backlog', 'window');
}
function renderComfortBand(bandKey, orders, emptyText) {
  const hostId=bandKey==='act_now'?'work-act-now':'work-my-todos';
  const host=$(hostId);
  if(!host) return;
  const attention=$('attention-filter') && $('attention-filter').value;
  const open=bandIsOpen(attention, bandKey);
  const cap=open ? (bandWindow[bandKey] || BAND_VIRTUAL_WINDOW) : WORK_BAND_LIMIT;
  const visible=orders.slice(0, cap);
  reconcileList(host, visible, o=>o.project+':'+o.id, workBoardRow, {emptyText});
  renderWorkMore($(hostId+'-more'), orders.length-visible.length, bandKey, open ? 'window' : 'door');
}
function renderWorkInbox() {
  return;
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
const OVERVIEW_DECIDE_LIMIT = 5;
const DECIDE_WORK_HREF = '/work?attention=decide';
const UNROUTED_WORK_HREF = '/work?unrouted=1';
const THROUGHPUT_HREF = '/timeline?period=1';
const SPARK_BLOCKS = '▁▂▃▄▅▆▇█';
function emptyThroughput() {
  return {closes:0, hours:Array(24).fill(0), href:THROUGHPUT_HREF, state:'empty'};
}
function throughputFromSnapshot() {
  const data=snapshot && snapshot.throughput;
  if(data && Array.isArray(data.hours) && typeof data.closes==='number') return data;
  return emptyThroughput();
}
function throughputSpark(hours) {
  const values=Array.isArray(hours) ? hours.slice(0,24) : [];
  while(values.length<24) values.push(0);
  const peak=Math.max(0, ...values);
  if(!peak) return '';
  return values.map(n=>SPARK_BLOCKS[Math.min(7, Math.round((n/peak)*7))]).join('');
}
function paintOverviewThroughput() {
  const host=$('overview-throughput');
  if(!host) return;
  const data=throughputFromSnapshot();
  host.replaceChildren();
  if(data.state==='unavailable') {
    host.append(document.createTextNode('Throughput unavailable'));
    return;
  }
  if(!data.closes) {
    host.append(document.createTextNode('No closes in the last 24h'));
    return;
  }
  host.append(link(data.closes+' closes · last 24h', data.href || THROUGHPUT_HREF));
  const glyphs=throughputSpark(data.hours);
  if(glyphs) {
    const spark=el('span', glyphs, 'bp-overview-spark');
    spark.setAttribute('aria-hidden','true');
    host.append(spark);
  }
}
function seatHand(order) {
  for(const worker of (order.workers || [])) {
    if(worker && worker!=='you') return worker;
  }
  if(order.live_with) return order.live_with;
  if(order.parked_by) return order.parked_by;
  if(hasWorkerYou(order)) return 'you';
  return '';
}
function loadBucket(order) {
  const status=rowStatus(order);
  if(status==='Ready') return 'ready';
  if(status==='Live' || status==='Review') return 'claimed';
  if(status==='Stalled') return 'stalled';
  return '';
}
const FLOW_STAGES = ['Open','Ready','Live','Done'];
function emptyFlowCounts() {
  return {Open:0,Ready:0,Live:0,Done:0};
}
function emptyWorkFlow(state) {
  return {state:state || 'empty', flow:emptyFlowCounts(), seats:[], chips:[], total:0};
}
function flowStage(order) {
  const status=rowStatus(order);
  if(status==='Done') return 'Done';
  if(status==='Ready') return 'Ready';
  if(status==='Live' || status==='Review' || status==='Stalled') return 'Live';
  if(status==='Open' || status==='Deferred') return 'Open';
  return '';
}
function flowFromOrders(orders) {
  const flow=emptyFlowCounts();
  for(const order of orders || []) {
    const stage=flowStage(order);
    if(stage) flow[stage]+=1;
  }
  return flow;
}
function flowTotal(flow) {
  return FLOW_STAGES.reduce((n,stage)=>n+((flow && flow[stage]) || 0),0);
}
function matchingWorkOrders() {
  const q=$('search').value.trim().toLowerCase(), status=$('status-filter').value, gate=$('gate-filter').value, kind=$('kind-filter').value, attention=$('attention-filter').value;
  return (snapshot.orders || []).filter(o=>(!unroutedOnly || isUnrouted(o)) && (!selectedProject || o.project===selectedProject) && (!selectedAssignment || matchesAssignment(o,selectedAssignment)) && matchesStatusFacet(o,status) && (!gate || matchesGate(o,gate)) && (!kind || o.kind===kind) && matchesAttentionFacet(o,attention) && (!q || `${o.id} ${o.title} ${o.project_name} ${o.owner}`.toLowerCase().includes(q)));
}
function workHasMatchingFilter() {
  const q=$('search').value.trim(), status=$('status-filter').value, gate=$('gate-filter').value, kind=$('kind-filter').value, attention=$('attention-filter').value;
  return Boolean(unroutedOnly || selectedAssignment || status || gate || kind || attention || q);
}
function buildWorkFlow(orders, agents) {
  const flow=flowFromOrders(orders);
  const seats=new Map();
  const names={you:'You'};
  for(const agent of agents || []) {
    if(!agent || !agent.id) continue;
    if(agent.group==='seat' || agent.id==='you') names[agent.id]=agent.name || agent.id;
  }
  for(const order of orders || []) {
    const bucket=loadBucket(order);
    const hand=seatHand(order);
    if(!bucket || !hand) continue;
    if(!seats.has(hand)) seats.set(hand,{id:hand,name:names[hand] || hand,ready:0,claimed:0,stalled:0});
    seats.get(hand)[bucket]+=1;
  }
  const list=[...seats.values()].sort((a,b)=>{
    const load=(b.ready+b.claimed+b.stalled)-(a.ready+a.claimed+a.stalled);
    return load || String(a.name).localeCompare(String(b.name));
  });
  const loadTotal=list.reduce((n,seat)=>n+seat.ready+seat.claimed+seat.stalled,0);
  const total=flowTotal(flow);
  return {state:(total || loadTotal) ? 'healthy' : 'empty', flow, seats:list, chips:seatLoadChips(list), total};
}
function workFlowFromOrders() {
  if(snapshot && snapshot.work_flow && snapshot.work_flow.state==='unavailable') return snapshot.work_flow;
  const scoped=(snapshot.orders || []).filter(order=>!selectedProject || order.project===selectedProject);
  const data=buildWorkFlow(scoped, snapshot && snapshot.agents);
  const snapshotFlow=snapshot && snapshot.work_flow && snapshot.work_flow.flow;
  if(snapshotFlow && !selectedProject && !workHasMatchingFilter()) {
    data.flow=snapshotFlow;
    data.total=typeof snapshot.work_flow.total==='number' ? snapshot.work_flow.total : flowTotal(snapshotFlow);
  } else {
    data.flow=flowFromOrders(matchingWorkOrders());
    data.total=flowTotal(data.flow);
  }
  const loadTotal=(data.seats || []).reduce((n,seat)=>n+seat.ready+seat.claimed+seat.stalled,0);
  data.state=(data.total || loadTotal) ? 'healthy' : 'empty';
  return data;
}
function seatLoadChips(seats) {
  const ranked=[...seats].sort((a,b)=>(b.stalled-a.stalled)||(b.ready-a.ready)||String(a.name).localeCompare(String(b.name)));
  const chips=ranked.slice(0,SEAT_CHIP_NAMED).map(seat=>({id:seat.id,name:seat.name,ready:seat.ready,stalled:seat.stalled,kind:'seat'}));
  const rest=ranked.slice(SEAT_CHIP_NAMED);
  if(rest.length) chips.push({
    id:'others', name:'others', kind:'others', rolled:rest.length,
    ready:rest.reduce((n,seat)=>n+seat.ready,0),
    stalled:rest.reduce((n,seat)=>n+seat.stalled,0),
  });
  return chips;
}
function scopeSeatLoad(chip) {
  const attention=$('attention-filter');
  if(attention) attention.value='seat';
  const assignment=$('assignment-filter');
  if(assignment) {
    if(!chip || chip.kind==='others' || !chip.id) assignment.value='';
    else {
      const value=chip.id==='you' ? 'you' : 'worker:'+chip.id;
      if(!Array.from(assignment.options).some(option=>option.value===value)) assignment.add(new Option(chip.name || chip.id, value));
      assignment.value=value;
    }
  }
  updateWorkFilters();
}
function filterSeatLoad(seatId) {
  scopeSeatLoad({id:seatId, name:seatDisplayName(seatId), kind:'seat'});
}
function flowTickCount(count, peak) {
  if(!count) return 0;
  return Math.max(1, Math.min(12, Math.round((count / Math.max(peak, 1)) * 12)));
}
function paintWorkFlow() {
  const host=$('work-flow');
  if(!host) return;
  host.replaceChildren();
  const data=workFlowFromOrders();
  if(data.state==='unavailable') {
    host.append(document.createTextNode('Seat load unavailable'));
    return;
  }
  const seats=data.seats || [];
  const chips=(data.chips && data.chips.length) ? data.chips : seatLoadChips(seats);
  const flow=data.flow || emptyFlowCounts();
  const stages=flowTotal(flow);
  const peak=FLOW_STAGES.reduce((n,stage)=>Math.max(n, flow[stage] || 0),0);
  if(stages) {
    const strip=el('div',undefined,'bp-work-flow-strip');
    strip.setAttribute('aria-label','Flow');
    FLOW_STAGES.forEach((stage,index)=>{
      if(index) strip.append(el('span',' → ','bp-work-flow-arrow'));
      const count=flow[stage] || 0;
      const item=el('span',undefined,'bp-work-flow-stage');
      item.dataset.stage=stage;
      item.append(el('span',stage,'bp-work-flow-label'));
      item.append(document.createTextNode(' '));
      item.append(el('span',String(count),'bp-work-flow-count'));
      const ticks=flowTickCount(count, peak);
      if(ticks) {
        const spark=el('span',undefined,'bp-work-flow-ticks');
        spark.setAttribute('aria-hidden','true');
        for(let i=0;i<ticks;i+=1) spark.append(el('span',undefined,'bp-work-flow-tick'));
        item.append(spark);
      }
      strip.append(item);
    });
    host.append(strip);
  }
  if(seats.length) {
    const list=el('div',undefined,'bp-work-seat-load');
    list.setAttribute('aria-label','Seat load');
    for(const chip of chips) {
      const button=el('button',undefined,'bp-work-seat-chip');
      button.type='button';
      button.dataset.seat=chip.id;
      button.dataset.kind=chip.kind;
      button.append(el('span', chip.name, 'bp-work-seat-chip-name'));
      button.append(el('span', chip.ready+' ready', 'bp-work-seat-chip-ready'));
      button.append(el('span', chip.stalled+' stalled', 'bp-work-seat-chip-stalled'));
      button.setAttribute('aria-label', `${chip.name}: ${chip.ready} ready, ${chip.stalled} stalled`);
      button.addEventListener('click',()=>scopeSeatLoad(chip));
      list.append(button);
    }
    host.append(list);
  }
  if(!seats.length && !stages) {
    host.append(document.createTextNode('No seat drain right now'));
  }
}
function isUnrouted(order) {
  // Same slice as the per-row Needs routing chip: open backlog, ungated, no
  // routable seat (ONE_DESK_STORY §The fact: Unrouted).
  return order.status === 'backlog' && Boolean(order.needs_routing);
}
function clearUnroutedPreset() {
  unroutedOnly = false;
}
function matchesGate(order, value) {
  if(value==='none') return !order.gate_type && order.blocked_on==='clear';
  if(value==='blocked') return order.blocked_on==='open' || order.blocked_on==='unknown';
  return order.gate_type===value;
}
function filterChips() {
  const chips=[];
  if(unroutedOnly) chips.push(['Unrouted',()=>{unroutedOnly=false;updateFilters();}]);
  if($('search').value) chips.push(['Search: '+$('search').value,()=>{$('search').value='';}]);
  if(selectedProject) { const opt=Array.from($('project-filter').options).find(o=>o.value===selectedProject); chips.push(['Project: '+(opt?opt.text:selectedProject),()=>{$('project-filter').value='';}]); }
  if(selectedAssignment) { const opt=Array.from($('assignment-filter').options).find(o=>o.value===selectedAssignment); chips.push(['Assignment: '+(opt?opt.text:selectedAssignment),()=>{$('assignment-filter').value='';}]); }
  if($('status-filter').value) chips.push(['Status: '+$('status-filter').selectedOptions[0].text,()=>{$('status-filter').value='';}]);
  if($('gate-filter').value) chips.push(['Gate: '+$('gate-filter').selectedOptions[0].text,()=>{$('gate-filter').value='';}]);
  if($('kind-filter').value) chips.push(['Kind: '+$('kind-filter').selectedOptions[0].text,()=>{$('kind-filter').value='';}]);
  if($('attention-filter').value) chips.push(['Attention: '+$('attention-filter').selectedOptions[0].text,()=>{$('attention-filter').value='';}]);
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
  renderWorkInbox();
  const attention=$('attention-filter').value;
  const total=snapshot.orders.length;
  const orders=matchingWorkOrders();
  paintWorkFlow();
  const bands=partitionBands(orders);
  const act=$('work-band-act-now'), todos=$('work-band-my-todos'), seat=$('work-band-seat-backlog');
  if(act) act.hidden=!attentionShowsBand(attention,'act_now');
  if(todos) todos.hidden=!attentionShowsBand(attention,'my_todos');
  if(seat) seat.hidden=!attentionShowsBand(attention,'seat_backlog');
  if(act && !act.hidden) {
    $('work-act-now-count').textContent=String(bands.act_now.length);
    renderComfortBand('act_now', bands.act_now, 'Nothing for You');
  }
  if(todos && !todos.hidden) {
    $('work-my-todos-count').textContent=String(bands.my_todos.length);
    renderComfortBand('my_todos', bands.my_todos, 'Your list is clear');
  }
  if(seat && !seat.hidden) {
    $('work-seat-backlog-count').textContent=String(bands.seat_backlog.length);
    renderSeatBacklog(bands.seat_backlog);
  }
  const pages=Math.max(1,Math.ceil(orders.length/size));pageIndex=Math.min(pageIndex,pages-1);
  if($('work-list') && !$('work-list').hidden) {
    reconcileList($('work-list'), orders.slice(pageIndex*size,(pageIndex+1)*size), o=>o.project+':'+o.id, orderRow, {emptyText:'No matching open work. Try another project, assignment, status, gate, or search.'});
  }
  $('results').textContent=`${orders.length} of ${total} matching work order${orders.length===1?'':'s'}`;
  renderActiveFilters();
  if($('page-count')) $('page-count').textContent=`Page ${pageIndex+1} of ${pages}`;
  if($('previous')) $('previous').disabled=pageIndex===0;
  if($('next')) $('next').disabled=pageIndex>=pages-1;
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
// Timestamps arrive as ISO ("…T…Z") from WorkForce and as SQLite text
// ("YYYY-MM-DD HH:MM:SS") from WorkLane; compare them as instants, never as
// strings (pc-1495 second-pass finding).
function tsEpoch(value) {
  if(!value) return null;
  let text=String(value).trim().replace(' ','T');
  if(!/[zZ]$|[+-]\d\d:?\d\d$/.test(text)) text+='Z';
  const ms=Date.parse(text);
  return Number.isNaN(ms)?null:ms;
}
function currentShiftParkedIds(agent) {
  if(!agent.shift || !agent.parked) return [];
  const start=tsEpoch(agent.shift.started_at);
  if(start===null) return parkedOrderIds(agent);
  return agent.parked.filter(p=>{const s=tsEpoch(p.since); return s!==null && s>=start;}).map(p=>p.id);
}
function latestParkedSince(agent) {
  return (agent.parked || []).reduce((latest,p)=>{
    const s=tsEpoch(p.since);
    if(s===null) return latest;
    return (!latest || s>tsEpoch(latest)) ? p.since : latest;
  }, null);
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
function agentRowClass(agent) {
  const bucket=floorBucket(agent);
  if(bucket==='working') return 'bp-agent-row bp-agent-row-live';
  if(bucket==='error' || bucket==='stale') return 'bp-agent-row bp-agent-row-alert';
  if(bucket==='quiet') return 'bp-agent-row bp-agent-row-quiet';
  return 'bp-agent-row';
}
function agentRow(agent) {
  const row=el('div',undefined,agentRowClass(agent));
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
  if(agent.state==='working' && agent.shift && !agent.shift.stale) {
    const cue=el('span','','bp-shift-cue');
    cue.setAttribute('aria-hidden','true');
    nameCell.append(cue);
  }
  nameCell.append(el('strong',agent.name),el('span',` · ${agent.model}`,'bp-muted'));
  select.append(nameCell);
  const stateCell=el('span',undefined,'bp-agent-cell');stateCell.append(badge(agent.state,agent.badge));select.append(stateCell);
  const workCell=el('span',undefined,'bp-agent-cell bp-agent-work');workCell.append(heldLink(agent));select.append(workCell);
  select.append(el('span',elapsedText(agent),'bp-agent-cell bp-muted'));
  select.append(el('span',lastUpdateText(agent),'bp-agent-cell bp-muted'));
  select.append(seatSparkCell(agent));
  const activate=event=>{ if(event.target.closest('a')) return; event.preventDefault(); selectAgent(agent.id); };
  select.addEventListener('click',activate);
  select.addEventListener('keydown',event=>{ if((event.key==='Enter' || event.key===' ') && !event.target.closest('a')) { event.preventDefault(); selectAgent(agent.id); } });
  row.append(select);
  const actionCell=el('span',undefined,'bp-agent-cell bp-agent-action');actionCell.append(...agentAction(agent));row.append(actionCell);
  return row;
}
function jobRow(agent) {
  const row=el('div',undefined,agentRowClass(agent));
  const info=el('div',undefined,'bp-job-info');
  info.append(el('span',agent.name,'bp-agent-cell'));
  info.append(el('span',scheduleLabel(agent.schedule),'bp-agent-cell bp-muted'));
  info.append(el('span',agent.schedule==='manual'?'On demand':date(agent.next_fire),'bp-agent-cell bp-muted'));
  const stateCell=el('span',undefined,'bp-agent-cell');stateCell.append(badge(agent.state,agent.badge));info.append(stateCell);
  const reportText=agent.report ? `${agent.report.state} · ${agent.report.summary}` : (agent.last_run ? `${agent.last_run.outcome} · ${date(agent.last_run.at)}` : 'No report yet');
  info.append(el('span',reportText,'bp-agent-cell bp-muted'));
  info.append(seatSparkCell(agent));
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
function emptyAgentsFloor() {
  return {working:0, idle:0, error:0, stale:0, quiet:0};
}
function floorBucket(agent) {
  const state=agent && agent.state;
  if(state==='working') return 'working';
  if(state==='last_run_failed') return 'error';
  if(state==='stale_shift') return 'stale';
  if(state==='idle') return 'idle';
  return 'quiet';
}
function buildAgentsFloor(agents) {
  const counts=emptyAgentsFloor();
  for(const agent of agents || []) counts[floorBucket(agent)]++;
  return counts;
}
function agentsFloorFromSnapshot() {
  const floor=snapshot && snapshot.agents_floor;
  if(floor && typeof floor.working==='number') return floor;
  return buildAgentsFloor(snapshot?.agents || []);
}
function emptySeatSpark(state) {
  return {hours:Array(24).fill(0), fails:Array(24).fill(0), runs:0, errors:0, fail_rate:null, state:state||'empty'};
}
function seatSparkFromSnapshot(id) {
  const sparks=snapshot && snapshot.agents_floor && snapshot.agents_floor.sparks;
  if(sparks && sparks[id] && Array.isArray(sparks[id].hours)) return sparks[id];
  return emptySeatSpark();
}
function failRateText(rate) {
  if(rate==null || !Number.isFinite(Number(rate))) return '';
  const value=Number(rate);
  if(value<0) return '';
  const pct=Math.round(value*100);
  if(pct===0 && value>0) return '<1%';
  return pct+'%';
}
function failBits(errors, rate) {
  if(!errors) return '';
  const count=errors===1?'1 fail':`${errors} fails`;
  const pct=failRateText(rate);
  return pct ? `${count} (${pct})` : count;
}
function sparkTone(data, fallback) {
  if(data && data.runs && data.errors && data.errors>=data.runs) return 'error';
  return fallback || 'working';
}
function seatSparkLabel(data) {
  if(!data || !data.runs) return '';
  const runs=data.runs===1?'1 run':`${data.runs} runs`;
  const fail=failBits(data.errors, data.fail_rate);
  return fail ? `${runs} · ${fail}` : runs;
}
function seatSparkCell(agent) {
  const cell=el('span',undefined,'bp-agent-cell bp-agent-spark-cell');
  const bucket=floorBucket(agent);
  if(bucket==='quiet') return cell;
  const data=seatSparkFromSnapshot(agent.id);
  if(data.state==='unavailable') {
    cell.append(el('span','Runs unavailable','bp-muted'));
    return cell;
  }
  const glyphs=throughputSpark(data.hours);
  if(glyphs) {
    const line=el('span',glyphs,'bp-agent-spark-line');
    line.dataset.tone=sparkTone(data, bucket==='working'?'working':'idle');
    line.setAttribute('aria-hidden','true');
    cell.append(line);
  }
  if(data.runs) {
    cell.append(el('span', data.runs===1?'1 run':`${data.runs} runs`, 'bp-muted bp-agent-spark-label'));
    const fail=failBits(data.errors, data.fail_rate);
    if(fail) cell.append(el('span', fail, 'bp-agent-spark-fail'));
    cell.setAttribute('aria-label', seatSparkLabel(data)+' · last 24h');
  }
  return cell;
}
function floorThroughputFromSnapshot() {
  const floor=agentsFloorFromSnapshot();
  if(floor.throughput && typeof floor.throughput.runs==='number') return floor.throughput;
  const sparks=floor.sparks || {};
  const live=(snapshot.agents || []).filter(agent=>floorBucket(agent)!=='quiet');
  const hours=Array(24).fill(0);
  let runs=0, errors=0, readable=0, unavailable=0;
  for(const agent of live) {
    const spark=sparks[agent.id];
    if(!spark) continue;
    if(spark.state==='unavailable') { unavailable+=1; continue; }
    readable+=1;
    runs+=spark.runs || 0;
    errors+=spark.errors || 0;
    (spark.hours || []).forEach((n,index)=>{ if(index<24) hours[index]+=n || 0; });
  }
  if(!readable && unavailable) return emptySeatSpark('unavailable');
  return {hours, fails:[], runs, errors, fail_rate:runs?errors/runs:null, state:runs?'healthy':'empty'};
}
function paintAgentsFloorSpark() {
  const host=$('agents-floor-spark');
  if(!host) return;
  host.replaceChildren();
  const live=(snapshot.agents || []).filter(agent=>floorBucket(agent)!=='quiet');
  if(!live.length) return;
  const data=floorThroughputFromSnapshot();
  if(data.state==='unavailable') {
    host.textContent='Seat runs unavailable';
    return;
  }
  if(!data.runs) {
    host.textContent='No seat runs in the last 24h';
    return;
  }
  const count=data.runs===1?'1 run · last 24h':`${data.runs} runs · last 24h`;
  host.append(link(count, '/timeline?period=1'));
  const fail=failBits(data.errors, data.fail_rate);
  if(fail) host.append(el('span', fail, 'bp-agents-floor-fail'));
  const glyphs=throughputSpark(data.hours);
  if(glyphs) {
    const spark=el('span',glyphs,'bp-agents-floor-spark-line');
    spark.dataset.tone=sparkTone(data, 'working');
    spark.setAttribute('aria-hidden','true');
    host.append(spark);
  }
}
function paintAgentsPulse() {
  const host=$('agents-pulse');
  if(!host) return;
  const floor=agentsFloorFromSnapshot();
  const items=[['Working',floor.working,'working'],['Idle',floor.idle,'idle'],['Error',floor.error,'last_run_failed']];
  reconcileList(host, items, item=>item[0], ([label,count,state])=>{
    const tile=el('div',undefined,'bp-metric');
    tile.dataset.state=state;
    tile.append(el('strong',String(count)),el('span',label));
    return tile;
  });
  const remainder=$('agents-floor-remainder');
  if(remainder) {
    const bits=[];
    if(floor.stale) bits.push(floor.stale===1 ? '1 stale shift' : `${floor.stale} stale shifts`);
    if(floor.quiet) bits.push(floor.quiet===1 ? '1 off or unknown' : `${floor.quiet} off or unknown`);
    remainder.textContent=bits.join(' · ');
  }
  const empty=$('agents-floor-empty');
  if(empty) {
    const seats=(snapshot.agents || []).filter(a=>a.group==='seat');
    if(!seats.length && !(snapshot.agents || []).length) {
      empty.hidden=false;
      empty.textContent='No seats or jobs on this roster.';
    } else if(floor.working===0) {
      empty.hidden=false;
      empty.textContent='No seats working right now.';
    } else {
      empty.hidden=true;
      empty.textContent='';
    }
  }
}
function paintAgentsNextFire() {
  const host=$('agents-next-fire');
  if(!host) return;
  const doors=calendarDoorsFromSnapshot();
  host.replaceChildren();
  host.append(link(doors.next_fire_line || 'Next fire · none reported', '/calendar'));
}
function scheduleDoorRow(item) {
  const href=item.product && item.task_id
    ? readerHref('/work-order?'+new URLSearchParams({project:item.product,id:item.task_id}))
    : '/calendar';
  const row=link('',href,'bp-order');
  const details=el('div');
  details.append(el('strong',item.title || 'Dated work'));
  details.append(el('span',`${item.kind==='remind'?'Remind':'Due'} · ${item.source || 'Calendar'}`,'bp-order-meta'));
  row.append(details,badge(item.kind==='remind'?'scheduled':'all_day', item.kind==='remind'?'Remind':'Due'));
  return row;
}
function renderWorkCalendarDoors() {
  const host=$('work-calendar-doors');
  if(!host) return;
  const items=(calendarDoorsFromSnapshot().items || []).slice(0,4);
  host.hidden=!items.length;
  if(!items.length) { host.replaceChildren(); return; }
  reconcileList(host, items, item=>item.key, scheduleDoorRow);
}
function agents() {
  const seats=snapshot.agents.filter(a=>a.group==='seat'), jobs=snapshot.agents.filter(a=>a.group==='job');
  const liveSeats=seats.filter(a=>floorBucket(a)!=='quiet');
  const quietSeats=seats.filter(a=>floorBucket(a)==='quiet');
  $('agents-heartbeat').textContent=heartbeatLine();
  paintAgentsPulse();
  paintAgentsFloorSpark();
  paintAgentsNextFire();
  const liveEmpty=seats.length ? 'No seats working or idle — quiet roster below.' : 'No seats registered in the readable registry.';
  reconcileList($('seat-list'), liveSeats, a=>a.id, agentRow, liveSeats.length ? {} : {emptyText:liveEmpty});
  const quietWrap=$('agents-quiet'), quietSummary=$('agents-quiet-summary'), quietList=$('agents-quiet-list');
  if(quietWrap && quietList) {
    quietWrap.hidden=!quietSeats.length;
    if(quietSummary) quietSummary.textContent=quietSeats.length===1 ? 'Quiet · 1 off or unknown' : `Quiet · ${quietSeats.length} off or unknown`;
    if(quietSeats.some(a=>a.id===selectedAgentId)) quietWrap.open=true;
    reconcileList(quietList, quietSeats, a=>a.id, agentRow, {emptyText:'No quiet seats.'});
  }
  reconcileList($('job-list'), jobs, a=>a.id, jobRow, {emptyText:'No jobs registered in the readable registry.'});
  agentDetail();
  supervisorPanel();
  renderCoverage();
  syncAgentsFace();
  paintAgentsCanvas();
}
function emptyAgentsCanvas() {
  return {nodes:[], edges:[], width:0, height:0, empty:true, empty_reason:'No seats or jobs on this roster.'};
}
function futureFireAt(value, now) {
  const ms=Date.parse(String(value || ''));
  if(Number.isNaN(ms) || ms<=now) return null;
  return ms;
}
function buildAgentsCanvas(agents, now) {
  const stamp=now || Date.now();
  const seats=[], jobs=[];
  for(const agent of agents || []) {
    if(!agent || !agent.id) continue;
    if(agent.group==='seat') seats.push(agent);
    else if(agent.group==='job') jobs.push(agent);
  }
  if(!seats.length && !jobs.length) return emptyAgentsCanvas();
  const nodes=[], edges=[];
  const nodeW=188, nodeH=58, gapY=16, padX=24, padY=24, colActor=24, colTarget=268, stackGap=10;
  let y=padY;
  const bands=[seats, jobs];
  bands.forEach((rows, index)=>{
    if(index && rows.length && nodes.length) y+=12;
    for(const agent of rows) {
      const actor={
        id:agent.id, kind:agent.group, label:agent.name || agent.id,
        badge:agent.badge || agent.state, bucket:floorBucket(agent), group:agent.group,
        x:colActor, y, w:nodeW, h:nodeH, door:agent.group==='seat'?'person':'',
      };
      const held=agent.group==='seat' && agent.held && agent.held.id && agent.held.project ? agent.held : null;
      if(agent.group==='seat') {
        actor.work_href='/work?'+new URLSearchParams({assignment:'worker:'+agent.id});
        if(held) actor.claim={label:`${held.title || held.id} · ${held.id}`, href:'/work-order?'+new URLSearchParams({project:held.project,id:held.id})};
      }
      nodes.push(actor);
      const targets=[];
      if(held) {
        targets.push({
          kind:'claim',
          node:{
            id:`work:${held.project}:${held.id}`, kind:'work',
            label:`${held.title || held.id} · ${held.id}`, title:held.title || held.id,
            href:'/work-order?'+new URLSearchParams({project:held.project,id:held.id}),
            door:'ticket', bucket:'target',
          },
        });
      }
      const fireAt=futureFireAt(agent.next_fire, stamp);
      if(fireAt!=null) {
        targets.push({
          kind:'next_fire',
          node:{
            id:`fire:${agent.id}`, kind:'fire', label:'Next fire', title:agent.name || agent.id,
            href:'/calendar', door:'calendar', bucket:'target',
          },
        });
      }
      let targetY=y;
      for(const target of targets) {
        nodes.push({...target.node, x:colTarget, y:targetY, w:nodeW, h:nodeH});
        edges.push({from:actor.id, to:target.node.id, kind:target.kind});
        targetY+=nodeH+stackGap;
      }
      const rowBottom=targets.length ? targetY-stackGap : y+nodeH;
      y=Math.max(y+nodeH, rowBottom)+gapY;
    }
  });
  return {nodes, edges, width:colTarget+nodeW+padX, height:Math.max(y+padY-gapY, padY+nodeH), empty:false, empty_reason:''};
}
function agentsCanvasFromSnapshot() {
  const canvas=snapshot && snapshot.agents_canvas;
  if(canvas && Array.isArray(canvas.nodes)) return canvas;
  return buildAgentsCanvas(snapshot?.agents || []);
}
function syncAgentsFace() {
  const floorBtn=$('agents-face-floor'), canvasBtn=$('agents-face-canvas');
  if(floorBtn) floorBtn.setAttribute('aria-pressed', String(agentsView==='floor'));
  if(canvasBtn) canvasBtn.setAttribute('aria-pressed', String(agentsView==='canvas'));
  const lists=$('agents-floor-lists'), wrap=$('agents-canvas-wrap');
  if(lists) lists.hidden=agentsView==='canvas';
  if(wrap) wrap.hidden=agentsView!=='canvas';
}
function setAgentsView(next) {
  agentsView=next==='canvas'?'canvas':'floor';
  if(page==='agents') {
    const params=new URLSearchParams(location.search);
    if(agentsView==='canvas') params.set('view','canvas');
    else params.delete('view');
    history.replaceState(null,'',location.pathname+(params.size?'?'+params:'')+location.hash);
  }
  syncAgentsFace();
  if(snapshot) agents();
}
function paintAgentsCanvasNode(node) {
  const card=el('article',undefined,'bp-agents-canvas-node');
  card.dataset.kind=node.kind;
  card.dataset.bucket=node.bucket || '';
  card.dataset.id=node.id;
  card.style.left=`${node.x || 0}px`;
  card.style.top=`${node.y || 0}px`;
  card.style.width=`${node.w || 188}px`;
  card.style.minHeight=`${node.h || 58}px`;
  if(node.kind==='seat' || node.kind==='job') {
    if(node.kind==='seat') {
      const person=el('button',undefined,'bp-agents-canvas-person');
      person.type='button';
      person.dataset.agentId=node.id;
      person.setAttribute('aria-pressed', String(selectedAgentId===node.id));
      if(selectedAgentId===node.id) card.dataset.selected='true';
      const name=el('span',undefined,'bp-agents-canvas-label');
      if(node.bucket==='working') {
        const cue=el('span','','bp-shift-cue');
        cue.setAttribute('aria-hidden','true');
        name.append(cue);
      }
      name.append(node.label);
      person.append(name);
      person.addEventListener('click',()=>selectAgent(node.id));
      card.append(person);
    } else {
      card.append(el('span',node.label,'bp-agents-canvas-label'));
    }
    const meta=el('div',undefined,'bp-agents-canvas-meta');
    if(node.badge) meta.append(badge(node.bucket==='error'?'last_run_failed':(node.bucket || 'idle'), node.badge));
    if(node.claim) meta.append(link(node.claim.label, readerHref(node.claim.href), 'bp-agents-canvas-chip bp-agents-canvas-claim'));
    else if(node.work_href) meta.append(link('Work', node.work_href, 'bp-agents-canvas-chip'));
    card.append(meta);
    return card;
  }
  const href=node.door==='ticket' ? readerHref(node.href || '/') : (node.href || '/calendar');
  const door=link('', href, 'bp-agents-canvas-person');
  door.append(el('span',node.label,'bp-agents-canvas-label'));
  card.append(door);
  return card;
}
function paintAgentsCanvasEdges(svg, canvas) {
  const byId={};
  for(const node of canvas.nodes || []) byId[node.id]=node;
  for(const edge of canvas.edges || []) {
    const from=byId[edge.from], to=byId[edge.to];
    if(!from || !to) continue;
    const line=document.createElementNS('http://www.w3.org/2000/svg','path');
    const x1=(from.x || 0)+(from.w || 188);
    const y1=(from.y || 0)+((from.h || 58)/2);
    const x2=to.x || 0;
    const y2=(to.y || 0)+((to.h || 58)/2);
    const mid=(x1+x2)/2;
    line.setAttribute('d',`M${x1} ${y1} C${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`);
    line.setAttribute('class','bp-agents-canvas-edge');
    line.dataset.kind=edge.kind || '';
    svg.append(line);
  }
}
function paintAgentsCanvas() {
  const host=$('agents-canvas'), empty=$('agents-canvas-empty');
  if(!host) return;
  if(agentsView!=='canvas') return;
  const canvas=agentsCanvasFromSnapshot();
  host.replaceChildren();
  if(empty) {
    empty.hidden=!canvas.empty;
    empty.textContent=canvas.empty ? (canvas.empty_reason || 'No seats or jobs on this roster.') : '';
  }
  host.hidden=!!canvas.empty;
  if(canvas.empty) return;
  const scene=el('div',undefined,'bp-agents-canvas-scene');
  scene.style.width=`${canvas.width || 480}px`;
  scene.style.height=`${canvas.height || 160}px`;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('class','bp-agents-canvas-edges');
  svg.setAttribute('viewBox',`0 0 ${canvas.width || 480} ${canvas.height || 160}`);
  svg.setAttribute('aria-hidden','true');
  paintAgentsCanvasEdges(svg, canvas);
  const layer=el('div',undefined,'bp-agents-canvas-nodes');
  for(const node of canvas.nodes || []) layer.append(paintAgentsCanvasNode(node));
  scene.append(svg, layer);
  host.append(scene);
}
const SOURCE_LABEL = {worklane: 'WorkLane', workforce: 'WorkForce', supervisor: 'Supervisor', github: 'GitHub'};
function timelineActionLabel(row) {
  const raw = row.event === 'event' ? (row.event_title || 'event') : row.event;
  const text = String(raw).replaceAll('_', ' ').replaceAll('/', ' · ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}
function timelineHeadline(row) {
  return `${timelineActionLabel(row)} · ${row.title}`;
}
function timelineMeta(row) {
  return [row.project || 'desk', row.actor, date(row.at)].filter(Boolean).join(' · ');
}
// Headline (action + work/project/actor) carries the action word exactly
// once; the badge names the source instead of repeating it (pc-1488
// Done-when: avoid repeated status/badge words).
function timelineRow(row) {
  const node = el('article', undefined, 'bp-order');
  const content = el('div');
  content.append(el('strong', timelineHeadline(row)));
  content.append(el('span', timelineMeta(row), 'bp-order-meta'));
  // The full original comment is never clipped away: a short headline is
  // shown, and the complete text stays reachable behind this expansion.
  if (row.detail && row.detail !== row.title) {
    const detail = el('details', undefined, 'bp-timeline-detail');
    detail.append(el('summary', 'Full text'), el('p', row.detail));
    content.append(detail);
  }
  const sourceBadge = badge(row.source, SOURCE_LABEL[row.source] || row.source);
  if (row.event_title) sourceBadge.title = row.event_title;
  node.append(content, sourceBadge);
  if (row.link?.href) {
    const href = row.link.href;
    const linkNode = link(row.link.label || 'Open', row.link.external ? href : readerHref(href), 'bp-order-link');
    if (row.link.external) { linkNode.target = '_blank'; linkNode.rel = 'noopener noreferrer'; }
    node.append(linkNode);
  }
  return node;
}
// Consecutive rows sharing a verified correlation key (WorkForce
// identity+ticket, or a GitHub PR/CI run's shared head sha — never
// prose/time similarity alone) collapse into one expandable group; the
// raw per-row view stays reachable inside it (pc-1488 Done-when).
function buildTimelineGroups(rows) {
  const groups = [];
  let index = 0;
  while (index < rows.length) {
    const row = rows[index];
    let end = index + 1;
    if (row.group_key) { while (end < rows.length && rows[end].group_key === row.group_key) end++; }
    if (end - index > 1) { groups.push({id: 'group:' + row.group_key + ':' + row.id, rows: rows.slice(index, end)}); }
    else { groups.push({id: row.id, rows: [row]}); }
    index = end;
  }
  return groups;
}
function timelineGroupNode(group) {
  if (group.rows.length === 1) return timelineRow(group.rows[0]);
  const wrap = el('details', undefined, 'bp-timeline-group');
  const head = group.rows[0];
  const actions = group.rows.map(timelineActionLabel).join(' → ');
  wrap.append(el('summary', `${group.rows.length} events · ${head.title} · ${actions}`));
  for (const row of group.rows) wrap.append(timelineRow(row));
  return wrap;
}
function timelinePeriodCutoff() {
  if (!timelinePeriod) return null;
  const days = Number(timelinePeriod);
  return Number.isFinite(days) && days > 0 ? Date.now() - days * 86400000 : null;
}
function timelineVisibleRows() {
  const rows = timelineData?.rows || [];
  const cutoff = timelinePeriodCutoff();
  if (!cutoff) return rows;
  return rows.filter(row => { const at = Date.parse(row.at); return Number.isNaN(at) || at >= cutoff; });
}
function timelineSources() {
  const rows = sortBySeverity(timelineData?.sources || [], s => s.name);
  reconcileList($('timeline-sources'), rows, source => source.name,
    source => connectionRow(source.name, source, isException(source) ? 'exception' : 'compact'),
    {emptyText: 'No timeline sources reported.'});
  const exceptions = rows.filter(isException);
  $('timeline-source-summary').textContent = exceptions.length
    ? `Sources · ${exceptions.length} notice${exceptions.length === 1 ? '' : 's'}`
    : 'Sources';
  // Force-open on a real exception so observation/error detail is never
  // hidden by a stale collapse; otherwise leave the reader's own toggle
  // alone rather than fighting it on every repaint.
  if (exceptions.length) $('timeline-source-strip').open = true;
}
function timelineFilterChips() {
  const chips = [];
  if (timelineProject) { const opt = Array.from($('timeline-project').options).find(o => o.value === timelineProject); chips.push(opt ? opt.text : timelineProject); }
  if (timelineSource) chips.push($('timeline-source').selectedOptions[0].text);
  if (timelineActor) chips.push('Actor: ' + timelineActor);
  if (timelinePeriod) chips.push($('timeline-period').selectedOptions[0].text);
  return chips;
}
function timelineActivitySeries() {
  const activity = timelineData?.activity || {};
  if (timelinePeriod === '1') {
    return {label: 'last day', grain: 'hour', buckets: activity.day?.buckets || []};
  }
  if (timelinePeriod === '3') {
    const days = activity.window?.buckets || [];
    return {label: 'last 3 days', grain: 'day', buckets: days.slice(-3)};
  }
  if (timelinePeriod === '7') {
    return {label: 'last 7 days', grain: 'day', buckets: activity.week?.buckets || []};
  }
  return {label: 'last 14 days', grain: 'day', buckets: activity.window?.buckets || []};
}
function timelineActivityLabel(bucket, grain, index, total) {
  const stamp = Date.parse(bucket.start);
  if (Number.isNaN(stamp)) return '';
  const d = new Date(stamp);
  if (grain === 'hour') {
    if (index % 6 && index !== total - 1) return '';
    return d.toLocaleTimeString([], {hour: 'numeric'});
  }
  if (total > 7 && index % 2 && index !== total - 1) return '';
  return d.toLocaleDateString([], {month: 'short', day: 'numeric'});
}
function paintTimelineActivity() {
  const summary = $('timeline-activity-summary');
  const chart = $('timeline-activity-chart');
  if (!summary || !chart) return;
  if (!timelineData) {
    summary.textContent = 'Timeline is unavailable right now.';
    chart.hidden = true;
    chart.replaceChildren();
    return;
  }
  // Missing payload: do not claim quiet while the list may still have rows
  // (harnesses and older responses). Server activity is the spine.
  if (!timelineData.activity) {
    summary.textContent = '';
    chart.hidden = true;
    chart.replaceChildren();
    return;
  }
  const series = timelineActivitySeries();
  const buckets = series.buckets;
  const total = buckets.reduce((sum, bucket) => sum + (Number(bucket.count) || 0), 0);
  if (!buckets.length || !total) {
    summary.textContent = 'Quiet in this window.';
    chart.hidden = true;
    chart.replaceChildren();
    return;
  }
  const peak = Math.max(...buckets.map(bucket => Number(bucket.count) || 0), 1);
  summary.textContent = `${total} event${total === 1 ? '' : 's'} · ${series.label} · by ${series.grain}`;
  chart.hidden = false;
  chart.setAttribute('role', 'img');
  chart.setAttribute('aria-label', summary.textContent);
  chart.replaceChildren();
  buckets.forEach((bucket, index) => {
    const count = Number(bucket.count) || 0;
    const col = el('div', undefined, 'bp-timeline-hist-col');
    const track = el('div', undefined, 'bp-timeline-hist-track');
    const bar = el('div', undefined, 'bp-timeline-hist-bar');
    bar.style.height = `${Math.round((count / peak) * 100)}%`;
    bar.dataset.empty = count ? 'false' : 'true';
    bar.title = `${count} · ${date(bucket.start)}`;
    track.append(bar);
    col.append(track);
    const label = timelineActivityLabel(bucket, series.grain, index, buckets.length);
    if (label) col.append(el('span', label, 'bp-timeline-hist-label'));
    chart.append(col);
  });
}
function timeline() {
  const groups = buildTimelineGroups(timelineVisibleRows());
  reconcileList($('timeline-list'), groups, g => g.id, timelineGroupNode, {emptyText: 'No timeline rows in the readable window.'});
  timelineSources();
  paintTimelineActivity();
  $('timeline-more').hidden = !timelineMore;
  $('timeline-clear-filters').hidden = !timelineFilterChips().length;
}
function timelineFilterParams() {
  const params = new URLSearchParams();
  if (timelineProject) params.set('project', timelineProject);
  if (timelineSource) params.set('source', timelineSource);
  if (timelineActor) params.set('actor', timelineActor);
  if (timelinePeriod) params.set('period', timelinePeriod);
  return params;
}
function updateTimelineFilters() {
  timelineProject = $('timeline-project').value;
  timelineSource = $('timeline-source').value;
  timelineActor = $('timeline-actor').value.trim();
  timelineCursor = '';
  timelineExpanded = false;
  const params = timelineFilterParams();
  history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
  refreshTimeline(false, {force: true});
}
// Period narrows the already-fetched (server-bounded 14-day) window; it
// repaints in place and never triggers a refetch or moves the reading
// position (STATES_AND_TERMS.md pc-1483 pattern extended to this filter).
function updateTimelinePeriod() {
  timelinePeriod = $('timeline-period').value;
  const params = timelineFilterParams();
  history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
  if (timelineData) timeline();
}
function clearTimelineFilters() {
  $('timeline-project').value = '';
  $('timeline-source').value = '';
  $('timeline-actor').value = '';
  $('timeline-period').value = '';
  // The period is client-side state with its own URL parameter; a clear
  // reset must drop it from the address too (pc-1488 browser check on .58
  // left ?period=3 after Clear).
  timelinePeriod = '';
  updateTimelineFilters();
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
function countdownWords(seconds) {
  if(seconds<=0) return 'now';
  let minutes=Math.max(0,Math.floor(seconds/60));
  let hours=Math.floor(minutes/60); minutes=minutes%60;
  const days=Math.floor(hours/24); hours=hours%24;
  if(days && hours) return `in ${days}d ${hours}h`;
  if(days) return `in ${days}d`;
  if(hours && minutes) return `in ${hours}h ${minutes}m`;
  if(hours) return `in ${hours}h`;
  if(minutes) return `in ${minutes}m`;
  return 'in <1m';
}
function nextScheduleFire(agents, now) {
  const instant=now || new Date();
  const candidates=[];
  for(const agent of agents || []) {
    const ms=Date.parse(String(agent.next_fire || ''));
    if(Number.isNaN(ms) || ms<=instant.valueOf()) continue;
    candidates.push({
      name:agent.name || agent.id || 'Scheduled job',
      id:agent.id || '',
      at:new Date(ms).toISOString(),
      group:agent.group || '',
      seconds:(ms-instant.valueOf())/1000,
    });
  }
  candidates.sort((a,b)=>a.seconds-b.seconds);
  return candidates[0] || null;
}
function nextFireLine(fire) {
  if(!fire) return 'Next fire · none reported';
  const name=fire.name || 'Scheduled job';
  return Number.isFinite(fire.seconds) ? `Next fire · ${name} ${countdownWords(fire.seconds)}` : `Next fire · ${name}`;
}
function calendarDueItems(workDates, events, now) {
  const origin=todayKey(now);
  const items=new Map();
  for(const row of workDates || []) {
    if(row.kind!=='deadline' && row.kind!=='reminder') continue;
    const day=localDayKey(row.dtstart, row.all_day);
    if(!day || day>origin) continue;
    const product=row.product || '', taskId=row.task_id || '';
    const key=product || taskId ? `${product}:${taskId}` : `date:${row.dtstart}|${row.summary}`;
    const kind=row.kind==='deadline'?'due':'remind';
    const existing=items.get(key);
    if(existing && existing.kind==='due') continue;
    items.set(key,{key,kind,title:row.summary || 'Dated work',at:String(row.dtstart || ''),source:row.source || '',product,task_id:taskId});
  }
  for(const event of events || []) {
    if(String(event.state || '').toLowerCase()!=='due') continue;
    const title=event.title || 'Untitled event';
    const at=String(event.at || '');
    const key=`event:${title}|${at}`;
    items.set(key,{key,kind:'due',title,at,source:event.source || 'Local calendar',product:'',task_id:''});
  }
  return [...items.values()];
}
function calendarDueHref(items) {
  return items.some(item=>item.task_id) ? '/work?attention=due' : '/calendar';
}
function buildCalendarDoors(workDates, events, agents, now) {
  const items=calendarDueItems(workDates, events, now);
  const fire=nextScheduleFire(agents, now);
  return {due_count:items.length, due_href:calendarDueHref(items), items, next_fire:fire, next_fire_line:nextFireLine(fire)};
}
function calendarDoorsFromSnapshot(now) {
  const doors=snapshot && snapshot.calendar_doors;
  if(doors && typeof doors.due_count==='number') return doors;
  return buildCalendarDoors(snapshot?.work_dates || [], snapshot?.events || [], snapshot?.agents || [], now);
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
function paintCalendarSchedule() {
  const view=$('calendar-view');
  if(!view) return;
  paintDoors(view, calendarDoorsFromSnapshot());
  paintLoad(view, buildLoadByDay({
    workDates: snapshot?.work_dates || [],
    events: snapshot?.events || [],
    agents: snapshot?.agents || [],
    origin: calendarOrigin(),
    project: selectedProject,
    now: new Date(),
    readable: Boolean(snapshot?.workspace),
  }));
}
function calendar() {
  paintCalendarSchedule();
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
  $('footer-status').textContent=`${snapshot.projects.length} project stores · ${issues.length ? `${issues.length} source notices` : 'Local sources readable'} · Remote details in Delivery`;
  filterOptions();
  if(page==='overview') overview();
  if(page==='work') { work(); renderWorkCalendarDoors(); }
  if(page==='projects') projects();
  if(page==='agents') agents();
  if(page==='calendar') calendar();
  if(page==='timeline') timeline();
  if(page==='settings') { $('settings-build').textContent=snapshot.build;$('settings-workspace').textContent=snapshot.workspace?.path || 'Not selected'; if($('settings-updates')) $('settings-updates').textContent=liveIndicator(); }
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
  if(page==='settings' && $('settings-updates')) $('settings-updates').textContent=indicator;
}
async function refreshTimeline(append, opts = {}) {
  if (timelinePending || page !== 'timeline') return;
  // Once the reader has loaded older pages (timelineExpanded) or has simply
  // scrolled down the default first page, a quiet background poll (a
  // change-feed push, not the reader's own Load more or the explicit
  // Refresh button) must not move their reading position — it surfaces an
  // affordance instead (pc-1483/pc-1488 cursor-reviewer: gating this only
  // on timelineExpanded left a reader scrolled partway down the first page
  // jumped by every poll; anchor on the current top row / scroll depth).
  const scrolled = (document.scrollingElement?.scrollTop || 0) > 0;
  const hasReadingPosition = Boolean(timelineData?.rows?.length) && (timelineExpanded || scrolled);
  const background = !append && hasReadingPosition && !opts.force;
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
      const isNew = Boolean(data.rows.length && data.rows[0].id !== currentTop);
      const button = $('timeline-new-events');
      button.hidden = !isNew;
      if (isNew) {
        const seenIndex = data.rows.findIndex(row => row.id === currentTop);
        const count = seenIndex === -1 ? data.rows.length : seenIndex;
        button.textContent = count ? `${count} new event${count === 1 ? '' : 's'} — refresh to see them` : 'New events — refresh to see them';
      }
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
    if (!timelineData) {
      empty($('timeline-list'), 'Timeline is unavailable right now.');
      paintTimelineActivity();
    }
  } finally {
    timelinePending = false;
    freshness();
  }
}
function repoSection(repo) {
  const section=el('section',undefined,'bp-panel bp-delivery-repo');
  section.dataset.deliveryRepo=repo.repo;
  const heading=el('div',undefined,'bp-section-head');
  heading.append(el('h2',repo.repo),badge(repo.state));
  section.append(heading);
  section.append(el('p',deliverySummaryLine(repo),'bp-delivery-summary'));
  const meta=[repo.role || 'Repository', repo.private===true?'Private':repo.private===false?'Public':'Visibility unknown'];
  if(repo.deployment?.sha) meta.push(`Receipt commit ${String(repo.deployment.sha).slice(0,7)}`);
  meta.push(`Fetched ${date(repo.observed_at)}`);
  section.append(el('p',meta.join(' · '),'bp-muted'));
  if(repo.error) section.append(el('p',repo.error,'bp-warning'));
  if(repo.missing?.length) section.append(el('p','Unavailable evidence: '+repo.missing.join(', '),'bp-warning'));
  const groups=deliveryVisibleGroups(repo);
  if(!groups.length) empty(section,repo.quiet?'Quiet in the last 14 days.':'No verified delivery available.');
  else section.append(el('div',undefined,'bp-delivery-groups'));
  return section;
}
function deliveryBoundaryText(data) {
  const repos=(data.repositories || []).filter(repo=>!deliveryRepo || repo.repo===deliveryRepo);
  const loaded=repos.reduce((sum,repo)=>sum+deliveryVisibleGroups(repo).length,0);
  const total=repos.reduce((sum,repo)=>sum+(repo.summary?.loaded || (repo.groups || []).length),0);
  const truncated=repos.some(repo=>repo.summary?.truncated);
  if(!loaded && !total) return '';
  let text=`Showing ${loaded} of ${total} grouped event${total===1?'':'s'}`;
  if(truncated) text += ' · GitHub list truncated at 100 runs per repository';
  return text;
}
function deliveryFilterChips() {
  const chips=[];
  if(deliveryRepo) chips.push(deliveryRepo);
  if(deliveryType) chips.push($('delivery-type').selectedOptions[0].text);
  if(deliveryPeriod) chips.push($('delivery-period').selectedOptions[0].text);
  return chips;
}
function deliveryFilters() {
  const repos=remoteData?.repositories || [];
  const select=$('delivery-repo');
  const previous=deliveryRepo;
  const names=repos.map(repo=>repo.repo).sort();
  while(select.options.length>1) select.remove(1);
  for(const name of names) select.append(new Option(name,name));
  if(previous && names.includes(previous)) select.value=previous;
  else deliveryRepo=select.value;
  $('delivery-clear-filters').hidden=!deliveryFilterChips().length;
  const boundary=$('delivery-boundary');
  const text=remoteData ? deliveryBoundaryText(remoteData) : '';
  boundary.textContent=text;
  boundary.hidden=!text;
}
function updateDeliveryFilters() {
  deliveryRepo=$('delivery-repo').value;
  deliveryType=$('delivery-type').value;
  const params=new URLSearchParams();
  if(deliveryRepo) params.set('repo',deliveryRepo);
  if(deliveryType) params.set('type',deliveryType);
  if(deliveryPeriod) params.set('period',deliveryPeriod);
  history.replaceState(null,'',location.pathname+(params.size?'?'+params:'')+location.hash);
  deliveryFilters();
  if(remoteData) paintDelivery(remoteData);
}
function updateDeliveryPeriod() {
  deliveryPeriod=$('delivery-period').value;
  const params=new URLSearchParams();
  if(deliveryRepo) params.set('repo',deliveryRepo);
  if(deliveryType) params.set('type',deliveryType);
  if(deliveryPeriod) params.set('period',deliveryPeriod);
  history.replaceState(null,'',location.pathname+(params.size?'?'+params:'')+location.hash);
  deliveryFilters();
  if(remoteData) paintDelivery(remoteData);
}
function clearDeliveryFilters() {
  $('delivery-repo').value='';
  $('delivery-type').value='';
  $('delivery-period').value='';
  deliveryRepo='';deliveryType='';deliveryPeriod='';
  history.replaceState(null,'',location.pathname+location.hash);
  deliveryFilters();
  if(remoteData) paintDelivery(remoteData);
}
function emptyDeliverySpark() {
  return {days:Array(14).fill(0), fails:Array(14).fill(0), merges:Array(14).fill(0), checks:0, failures:0, merges_total:0, href:'/delivery?type=workflow', merge_href:'/delivery?type=pull_request', out_href:'', state:'empty'};
}
function deliverySparkWindowLabel() {
  if(deliveryPeriod==='1') return 'last day';
  if(deliveryPeriod==='3') return 'last 3 days';
  if(deliveryPeriod==='7') return 'last 7 days';
  return 'last 14 days';
}
function deliverySparkSlice(spark) {
  const days=Number(deliveryPeriod);
  const width=Number.isFinite(days) && days>0 ? Math.min(14, days) : 14;
  const series=(spark.days || []).slice(-width);
  const fails=(spark.fails || []).slice(-width);
  const merges=(spark.merges || []).slice(-width);
  const sum=values=>values.reduce((total,n)=>total+(Number(n)||0),0);
  return {
    ...spark,
    days:series,
    fails,
    merges,
    checks:sum(series),
    failures:sum(fails),
    merges_total:sum(merges),
  };
}
function deliverySparkFromRemote(data) {
  if(!data) return emptyDeliverySpark();
  if(deliveryRepo) {
    const repo=(data.repositories || []).find(row=>row.repo===deliveryRepo);
    if(repo && repo.ci_spark && Array.isArray(repo.ci_spark.days)) return deliverySparkSlice(repo.ci_spark);
  }
  if(data.ci_spark && Array.isArray(data.ci_spark.days)) return deliverySparkSlice(data.ci_spark);
  return deliverySparkSlice({...emptyDeliverySpark(), state:data.state==='not_configured'?'not_configured':(data.state==='unavailable'||data.state==='invalid_config'?'unavailable':'empty')});
}
function deliverySparkHref(kind) {
  const params=new URLSearchParams();
  params.set('type', kind==='pull_request' ? 'pull_request' : 'workflow');
  if(deliveryRepo) params.set('repo', deliveryRepo);
  if(deliveryPeriod) params.set('period', deliveryPeriod);
  return '/delivery?'+params;
}
function deliverySparkGlyphs(values) {
  const series=Array.isArray(values) ? values.slice() : [];
  const peak=Math.max(0, ...series);
  if(!peak) return '';
  return series.map(n=>SPARK_BLOCKS[Math.min(7, Math.round((n/peak)*7))]).join('');
}
function paintDeliverySpark(data) {
  const host=$('delivery-ci-spark');
  if(!host) return;
  host.replaceChildren();
  if(!data) {
    host.append(document.createTextNode('CI unavailable'));
    return;
  }
  if(data.state==='not_configured') {
    host.append(document.createTextNode('CI not configured'));
    return;
  }
  if(data.state==='unavailable' || data.state==='invalid_config') {
    host.append(document.createTextNode('CI unavailable'));
    return;
  }
  if(data.state==='loading' && !(data.repositories || []).length) return;
  const spark=deliverySparkFromRemote(data);
  if(spark.state==='unavailable') {
    host.append(document.createTextNode('CI unavailable'));
    return;
  }
  const window=deliverySparkWindowLabel();
  if(!spark.checks && !spark.merges_total) {
    host.append(document.createTextNode('No CI runs in the '+window));
    return;
  }
  if(spark.checks) {
    const count=spark.checks===1 ? '1 check · '+window : `${spark.checks} checks · ${window}`;
    host.append(link(count, deliverySparkHref('workflow')));
    if(spark.failures) host.append(el('span', spark.failures===1?' · 1 fail':` · ${spark.failures} fails`));
    const glyphs=deliverySparkGlyphs(spark.days);
    if(glyphs) {
      const line=el('span',glyphs,'bp-delivery-ci-spark-line');
      line.dataset.tone=spark.failures?'error':'working';
      line.setAttribute('aria-hidden','true');
      host.append(line);
    }
  } else {
    host.append(document.createTextNode('No CI runs in the '+window));
  }
  if(spark.merges_total) {
    const merges=spark.merges_total===1 ? '1 merge' : `${spark.merges_total} merges`;
    host.append(link(merges, deliverySparkHref('pull_request')));
  }
  if(spark.out_href) {
    const out=link(spark.failures?'Open failing check':'Open repository', spark.out_href);
    out.target='_blank';
    out.rel='noopener noreferrer';
    host.append(out);
  }
}
function paintDelivery(data) {
  const repos=(data.repositories || []).filter(repo=>!deliveryRepo || repo.repo===deliveryRepo);
  reconcileList($('remote-repositories'), repos, repo=>repo.repo, repoSection,
    {emptyText: data.refreshing ? '' : 'No repository delivery available. Check connection configuration or GitHub access.'});
  for(const repo of repos) {
    const container=document.querySelector(`[data-delivery-repo="${repo.repo}"] .bp-delivery-groups`);
    if(!container) continue;
    reconcileList(container, deliveryVisibleGroups(repo), group=>group.id, group=>deliveryGroupRow(group, repo.deployment),
      {emptyText: repo.quiet ? 'Quiet in the last 14 days.' : 'No verified delivery available.'});
  }
  deliveryFilters();
  paintDeliverySpark(data);
}
function remoteStatusText(data) {
  const parts=[];
  parts.push(data.refreshing ? 'Refreshing GitHub evidence…' : `GitHub: ${String(data.state || 'unknown').replaceAll('_',' ')}`);
  if(typeof data.cache_age_seconds==='number') parts.push(`cache ${data.cache_age_seconds}s old`);
  if(data.fetched_at) parts.push(`fetched ${date(data.fetched_at)}`);
  if(data.error) parts.push(data.error);
  return parts.join(' · ');
}
async function refreshRemote() {
  if(remotePending || !['delivery','connections'].includes(page)) return;
  remotePending=true;remoteLast=Date.now();
  try {
    const response=await fetch('/api/remote-activity',{cache:'no-store',signal:AbortSignal.timeout(10000)});
    if(!response.ok)throw new Error('Unavailable');
    const data=await response.json();
    remoteData=data;
    const status=remoteStatusText(data);
    $('github-connection-status').textContent=status;
    if(page==='delivery') {
      $('remote-status').textContent=status;
      paintDelivery(data);
    }
  } catch(error) {
    $('remote-status').textContent='GitHub refresh failed. Previously displayed evidence may be stale.';
    $('github-connection-status').textContent='GitHub unavailable';
  } finally { remotePending=false; }
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
  bandWindow={act_now:BAND_VIRTUAL_WINDOW,my_todos:BAND_VIRTUAL_WINDOW,seat_backlog:BAND_VIRTUAL_WINDOW};
  const params=new URLSearchParams();if(unroutedOnly)params.set('unrouted','1');if(selectedProject)params.set('project',selectedProject);if(selectedAssignment)params.set('assignment',selectedAssignment);if($('status-filter').value)params.set('status',$('status-filter').value);if($('gate-filter').value)params.set('gate',$('gate-filter').value);if($('kind-filter').value)params.set('kind',$('kind-filter').value);if($('attention-filter').value)params.set('attention',$('attention-filter').value);if($('search').value)params.set('q',$('search').value);
  history.replaceState(null,'',location.pathname+(params.size?'?'+params:'')+location.hash);if(snapshot)work();
}
$('filters').addEventListener('submit',event=>event.preventDefault());
function updateWorkFilters() { clearUnroutedPreset(); updateFilters(); }
$('search').addEventListener('input',updateWorkFilters);$('project-filter').addEventListener('change',updateWorkFilters);$('status-filter').addEventListener('change',updateWorkFilters);$('gate-filter').addEventListener('change',updateWorkFilters);$('kind-filter').addEventListener('change',updateWorkFilters);$('attention-filter').addEventListener('change',updateWorkFilters);$('assignment-filter').addEventListener('change',updateWorkFilters);
if($('projects-filter')) $('projects-filter').addEventListener('input',()=>{projectsFilter=$('projects-filter').value;try{localStorage.setItem('bp-projects',JSON.stringify({filter:projectsFilter}));}catch(error){}projects();});
$('clear-filters').addEventListener('click',()=>{unroutedOnly=false;$('search').value='';$('project-filter').value='';$('assignment-filter').value='';$('status-filter').value='';$('gate-filter').value='';$('kind-filter').value='';$('attention-filter').value='';updateFilters();});
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
  $('timeline-period').value = timelinePeriod;
  $('timeline-filters').addEventListener('submit', event => event.preventDefault());
  $('timeline-project').addEventListener('change', updateTimelineFilters);
  $('timeline-source').addEventListener('change', updateTimelineFilters);
  $('timeline-actor').addEventListener('change', updateTimelineFilters);
  $('timeline-actor').addEventListener('input', updateTimelineFilters);
  $('timeline-period').addEventListener('change', updateTimelinePeriod);
  $('timeline-clear-filters').addEventListener('click', clearTimelineFilters);
  $('timeline-more').addEventListener('click', () => { timelineExpanded = true; refreshTimeline(true); });
  $('timeline-new-events').addEventListener('click', () => { timelineExpanded = false; refreshTimeline(false, {force: true}); });
}
if ($('delivery-filters')) {
  $('delivery-type').value = deliveryType;
  $('delivery-period').value = deliveryPeriod;
  $('delivery-filters').addEventListener('submit', event => event.preventDefault());
  $('delivery-repo').addEventListener('change', updateDeliveryFilters);
  $('delivery-type').addEventListener('change', updateDeliveryFilters);
  $('delivery-period').addEventListener('change', updateDeliveryPeriod);
  $('delivery-clear-filters').addEventListener('click', clearDeliveryFilters);
}
if($('agents-face-floor')) $('agents-face-floor').addEventListener('click',()=>setAgentsView('floor'));
if($('agents-face-canvas')) $('agents-face-canvas').addEventListener('click',()=>setAgentsView('canvas'));
syncAgentsFace();
$('refresh').addEventListener('click',()=>{refresh(true);refreshRemote();if(page==='timeline')refreshTimeline(false, {force: true});});
document.addEventListener('keydown',event=>{
  if(event.key!=='Escape') return;
  if(page==='agents' && selectedAgentId) {
    const closedId=selectedAgentId;
    selectAgent(closedId);
    const row=document.querySelector(`.bp-agent-select[data-agent-id="${CSS.escape(closedId)}"]`)
      || document.querySelector(`.bp-agents-canvas-person[data-agent-id="${CSS.escape(closedId)}"]`);
    if(row) row.focus();
    return;
  }
  $('desk-scope').open=false;
});
document.addEventListener('click',event=>{if(!$('desk-scope').contains(event.target))$('desk-scope').open=false;});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();freshness();});
document.addEventListener('bp:desk-changed',event=>{noteLiveSource(event.detail);});
$('preferences').addEventListener('submit',event=>event.preventDefault());
$('preferences').addEventListener('change',()=>{interval=Number($('refresh-preference').value);motion=$('motion-preference').value;document.body.classList.toggle('bp-reduce-motion',motion==='off');try{localStorage.setItem('bp-display',JSON.stringify({interval,motion}));$('preference-status').textContent='Saved in this browser.';}catch(error){$('preference-status').textContent='Applied for this page; browser storage is unavailable.';}});
connectChanges(()=>{if(!document.hidden){refresh();if(page==='timeline')refreshTimeline(false);}},state=>{streamState=state;if(state==='open'){everOpened=true;consecutiveErrors=0;}else if(state==='error'){consecutiveErrors++;}freshness();});
setInterval(()=>{const effective=streamState==='open'?60:interval;if(effective && !document.hidden && Date.now()-lastAttempt>=effective*1000)refresh();},1000);setInterval(freshness,1000);setInterval(()=>{if(!document.hidden && Date.now()-remoteLast>15000)refreshRemote();},1000);refresh();refreshRemote();if(page==='timeline')refreshTimeline(false);
})();
