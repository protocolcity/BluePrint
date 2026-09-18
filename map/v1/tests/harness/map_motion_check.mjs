/* map-motion.js is pure classification — no DOM. Fixtures match
   test_node_motion.py so Python and JS stay on the same honesty rules.
   pc-1561 verify: stroke stays the live pulse; no invented overlay. */
import assert from 'node:assert/strict';
import {
  LIVE_MOTION,
  WINDOW_MS,
  classifyNodeMotion,
  emptyMotion,
  indexNodeState,
  motionAriaSuffix,
  motionClassName,
} from '../../static/js/map-motion.js';

const NOW = Date.parse('2026-09-17T15:00:00Z');

function project(overrides = {}) {
  return {
    id: 'product',
    folder: 'recipes',
    name: 'Recipes',
    state: 'available',
    open: 4,
    attention: 1,
    running: 0,
    working: 0,
    last_change: null,
    ...overrides,
  };
}

{
  const quiet = emptyMotion();
  assert.equal(quiet.state, 'quiet');
  assert.equal(quiet.stroke, 'none');
  assert.equal(quiet.motion, 0);
  assert.equal(emptyMotion('unavailable').stroke, 'unavailable');
}

assert.equal(classifyNodeMotion(null, { motion: 4 }, NOW).stroke, 'none');

{
  const painted = classifyNodeMotion(
    project({ state: 'unavailable', running: 2, last_change: { at: '2026-09-17T14:00:00Z' } }),
    { motion: 9, state: 'healthy' },
    NOW,
  );
  assert.equal(painted.stroke, 'unavailable');
  assert.equal(painted.motion, 0);
}

{
  const pile = classifyNodeMotion(
    project({ open: 31, attention: 4, last_change: { at: '2026-09-13T15:00:00Z' } }),
    { motion: 0, state: 'empty' },
    NOW,
  );
  assert.equal(pile.stroke, 'none');
  assert.equal(pile.state, 'quiet');
}

{
  const recent = classifyNodeMotion(
    project({ last_change: { at: '2026-09-17T13:00:00Z' } }),
    { motion: 0, state: 'empty' },
    NOW,
  );
  assert.equal(recent.stroke, 'recent');
}

{
  const stale = classifyNodeMotion(
    project({ last_change: { at: new Date(NOW - WINDOW_MS - 3600000).toISOString() } }),
    null,
    NOW,
  );
  assert.equal(stale.stroke, 'none');
}

{
  const one = classifyNodeMotion(project(), { motion: 1, state: 'healthy' }, NOW);
  assert.equal(one.stroke, 'recent');
  const live = classifyNodeMotion(project(), { motion: LIVE_MOTION, state: 'healthy' }, NOW);
  assert.equal(live.stroke, 'live');
}

assert.equal(classifyNodeMotion(project({ running: 1 }), { motion: 0, state: 'empty' }, NOW).stroke, 'live');
assert.equal(classifyNodeMotion(project({ last_change: { at: '2026-09-17 14:00:00' } }), null, NOW).stroke, 'recent');
assert.equal(classifyNodeMotion(project(), { motion: 8, state: 'unavailable' }, NOW).stroke, 'none');

{
  const map = indexNodeState(
    [project({ running: 1 }), { id: 'notes', folder: 'notes', state: 'available', open: 0 }],
    { projects: [{ id: 'product', motion: 2, state: 'healthy' }] },
  );
  assert.equal(map.recipes.motion.stroke, 'live');
  assert.equal(map.recipes.working, 1);
  assert.equal(map.notes.motion.stroke, 'none');
  assert.equal(motionClassName(map.recipes.motion), ' map-motion-live');
  assert.equal(motionClassName(map.notes.motion), '');
  assert.equal(motionAriaSuffix(map.recipes.motion), ', live motion');
  assert.equal(motionAriaSuffix(map.notes.motion), '');
}

console.log(JSON.stringify({ ok: true, live_motion: LIVE_MOTION }));
