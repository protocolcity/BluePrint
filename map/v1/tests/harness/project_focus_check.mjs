/* project-focus.js is pure data composition — no DOM needed, so this harness
   just imports the real module and asserts against realistic fixtures
   (busy, empty, unavailable, stale project data). */
import assert from 'node:assert/strict';
import {
  workBranch, agentsBranch, papersBranch, deliveryBranch, buildBranches, branchLabel,
} from '../../static/js/project-focus.js';

const project = { relPath: 'blueprint', name: 'BluePrint', hasMd: true };

// --- Work -------------------------------------------------------------
{
  const operations = {
    sources: [{ name: 'WorkLane', state: 'available' }],
    projects: [{ id: 'pc', folder: 'blueprint', open: 4, attention: 1, claimed: 2, running: 1, state: 'available' }],
    orders: [
      { id: 'pc-1', project: 'pc', title: 'Fix map', status: 'in_progress', status_word: 'In progress', priority: 2, attention: false },
      { id: 'pc-2', project: 'pc', title: 'Add tests', status: 'in_review', status_word: 'In review', priority: 1, attention: true },
      { id: 'pc-9', project: 'other', title: 'Not this project', status: 'backlog', status_word: 'Backlog', priority: 3 },
    ],
  };
  const branch = workBranch(project, operations);
  assert.equal(branch.state, 'available');
  assert.equal(branch.summary, '4 open · 1 For You · 2 claimed · 1 working');
  assert.equal(branch.items.length, 2, 'only items for the focused project');
  assert.equal(branch.items[0].id, 'pc-2', 'higher-priority order sorts first');
  assert.ok(branch.items[0].detail.includes('For You'));
  assert.equal(branch.items[0].href, '/work-order?project=pc&id=pc-2');
}

// Work — no linked project (empty, not silently zero-with-no-explanation).
{
  const operations = { sources: [{ name: 'WorkLane', state: 'available' }], projects: [], orders: [] };
  const branch = workBranch(project, operations);
  assert.equal(branch.state, 'empty');
  assert.match(branch.summary, /No linked work-order project/);
}

// Work — source unavailable is explicit, not an empty branch.
{
  const branch = workBranch(project, { sources: [{ name: 'WorkLane', state: 'unavailable' }], projects: [], orders: [] });
  assert.equal(branch.state, 'unavailable');
  assert.equal(branch.summary, 'Work source unavailable');
}
assert.equal(workBranch(project, null).state, 'unavailable');

// --- Agents -------------------------------------------------------------
{
  const operations = {
    projects: [{ id: 'pc', folder: 'blueprint' }],
    agents: [
      { id: 'bp-claude-implementer', project: 'pc', name: 'bp-claude-implementer', state: 'working' },
      { id: 'bp-grok-implementer', project: 'pc', name: 'bp-grok-implementer', state: 'idle', held: { id: 'pc-1' } },
      { id: 'other-seat', project: 'other', name: 'other-seat', state: 'working' },
    ],
  };
  const branch = agentsBranch(project, operations);
  assert.equal(branch.state, 'available');
  assert.equal(branch.summary, '2 seats · 1 working');
  assert.equal(branch.items.length, 2);
  assert.equal(branch.items[0].detail, 'working');
}
assert.equal(agentsBranch(project, { agents: [] , projects: [{id:'pc', folder:'blueprint'}]}).state, 'empty');
assert.equal(agentsBranch(project, {}).state, 'unavailable');

// --- Papers ---------------------------------------------------------------
assert.equal(papersBranch({ ...project, hasMd: true }).state, 'available');
assert.equal(papersBranch({ ...project, hasMd: false }).state, 'empty');
assert.equal(papersBranch(null).state, 'unavailable');

// --- Delivery ---------------------------------------------------------------
{
  const operations = { projects: [{ id: 'pc', folder: 'blueprint' }] };
  const remote = {
    state: 'connected',
    repositories: [{
      repo: 'org/repo', project: 'pc', state: 'connected', observed_at: '2026-09-13T00:00:00Z',
      items: [
        { kind: 'pull_request', title: 'Add branch chips', state: 'opened', url: 'https://github.com/org/repo/pull/1', updated_at: '2026-09-13T00:00:00Z' },
      ],
    }],
  };
  const branch = deliveryBranch(project, operations, remote);
  assert.equal(branch.state, 'available');
  assert.match(branch.summary, /1 item.*observed 2026-09-13T00:00:00Z/);
  assert.equal(branch.items[0].href, 'https://github.com/org/repo/pull/1');
}
// Delivery — not configured is explicit, not empty.
assert.equal(deliveryBranch(project, {}, { state: 'not_configured', repositories: [] }).state, 'unavailable');
assert.equal(deliveryBranch(project, {}, null).state, 'unavailable');
// Delivery — a stale (partially unreadable) repo is flagged, not silently dropped.
{
  const operations = { projects: [{ id: 'pc', folder: 'blueprint' }] };
  const remote = { state: 'partial', repositories: [
    { repo: 'org/a', project: 'pc', state: 'connected', observed_at: 't1', items: [{ kind: 'release', title: 'v1' }] },
    { repo: 'org/b', project: 'pc', state: 'unavailable', observed_at: 't2', items: [] },
  ] };
  assert.equal(deliveryBranch(project, operations, remote).state, 'stale');
}

// --- buildBranches — fixed order, always four ------------------------------
{
  const branches = buildBranches(project, null, null);
  assert.deepEqual(branches.map(b => b.key), ['work', 'agents', 'papers', 'delivery']);
  assert.ok(branches.every(b => typeof b.summary === 'string' && b.summary.length > 0));
}
assert.equal(branchLabel('agents'), 'Agents');

console.log('project-focus: work/agents/papers/delivery composition passed.');
