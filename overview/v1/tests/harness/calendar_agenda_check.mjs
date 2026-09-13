import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const src = readFileSync(new URL('../../static/js/operations.js', import.meta.url), 'utf8');
const start = src.indexOf('function todayKey(from)');
const end = src.indexOf('function datedHref(event)');
assert.ok(start >= 0 && end > start, 'calendar helpers must stay as named functions in operations.js');
const helpers = src.slice(start, end);
const {
  todayKey, shiftDay, localDayKey, allDayStamp, datedStamp, holdExpired,
  mergeDatedWork, rowClocks, agendaGroup, clockLabel,
} = Function('"use strict";\n' + helpers + '\nreturn {todayKey,shiftDay,localDayKey,allDayStamp,datedStamp,holdExpired,mergeDatedWork,rowClocks,agendaGroup,clockLabel};')();

const origin = '2026-09-13';
const items = [
  {kind:'deadline', product:'product', task_id:'pc-1', summary:'Due and hold', dtstart:'2026-09-20', all_day:true, source:'deadline:2026-09-20', attention_face:''},
  {kind:'timer', product:'product', task_id:'pc-1', summary:'Due and hold', dtstart:'2026-09-22T12:00:00+00:00', all_day:false, source:'gate_until', attention_face:'watch', attention:false},
  {kind:'reminder', product:'product', task_id:'pc-1', summary:'Due and hold', dtstart:'2026-09-21', all_day:true, source:'reminder:2026-09-21', attention_face:'note'},
  {kind:'mentioned', product:'product', task_id:'pc-2', summary:'Ratify leftover', dtstart:'2026-09-13', all_day:true, source:'gate_note', attention_face:'decide', attention:true},
  {kind:'timer', product:'product', task_id:'pc-3', summary:'Expired hold', dtstart:'2026-08-10T12:00:00+00:00', all_day:false, source:'gate_until', attention_face:'watch'},
  {kind:'deadline', product:'other', task_id:'osp-1', summary:'Other project', dtstart:'2026-09-13', all_day:true, source:'deadline:2026-09-13', attention_face:''},
];
const merged = mergeDatedWork(items);
assert.equal(merged.length, 4);
const dual = merged.find(row => row.task_id === 'pc-1');
assert.equal(dual.due, '2026-09-20');
assert.equal(dual.reminder, '2026-09-21');
assert.equal(dual.hold, '2026-09-22T12:00:00+00:00');
assert.equal(dual.due_source, 'deadline:2026-09-20');
assert.equal(dual.hold_source, 'gate_until');
assert.equal(dual.reminder_source, 'reminder:2026-09-21');
assert.notEqual(dual.attention_face, 'decide');
assert.equal(agendaGroup(dual, origin), 'next');

const mentioned = merged.find(row => row.task_id === 'pc-2');
assert.equal(mentioned.mentioned, '2026-09-13');
assert.equal(mentioned.mentioned_source, 'gate_note');
assert.equal(mentioned.attention_face, 'decide');
assert.equal(agendaGroup(mentioned, origin), 'today');
const mentionedClock = rowClocks(mentioned).find(clock => clock.kind === 'mentioned');
assert.equal(clockLabel(mentionedClock), 'Mentioned date');

const expired = merged.find(row => row.task_id === 'pc-3');
assert.equal(agendaGroup(expired, origin), 'past');
const hold = rowClocks(expired).find(clock => clock.kind === 'hold');
assert.equal(hold.expired, true);
assert.equal(clockLabel(hold), 'Expired hold');
assert.equal(holdExpired('2026-08-10T12:00:00+00:00', false, new Date('2026-09-13T12:00:00Z')), true);
assert.equal(holdExpired('2026-10-12T14:00:00+00:00', false, new Date('2026-09-13T12:00:00Z')), false);

assert.equal(localDayKey('2026-09-13', true), '2026-09-13');
assert.equal(allDayStamp('2026-09-13').includes('13'), true);
assert.ok(datedStamp('2026-09-13', true).includes('All day'));
assert.equal(shiftDay('2026-09-13', 7), '2026-09-20');
assert.equal(shiftDay('2026-09-13', -7), '2026-09-06');
assert.match(todayKey(new Date(2026, 8, 13)), /^2026-09-13$/);

console.log('Calendar agenda: merge, today/next/past, expired hold, mentioned date, all-day key passed.');
