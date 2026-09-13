// contentKey() harness (pc-1483 review finding, recovery 2): an agent's
// open-shift age_seconds is recomputed from the wall clock on every read,
// so two snapshots identical except that field must fingerprint the same;
// a snapshot that changes something real (started_at) must still differ.
import {readFileSync} from 'node:fs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');

let raw = read('../../static/js/operations.js');
raw = raw.slice(raw.indexOf("'use strict';"), raw.lastIndexOf('})();'));
const marker = 'function stripShiftAge(shift)';
const at = raw.indexOf(marker);
if (at === -1) throw new Error('operations.js stripShiftAge marker missing');
const end = raw.indexOf('async function refresh(manual)');
if (end === -1) throw new Error('operations.js refresh(manual) marker missing');
const body = raw.slice(at, end);

const context = {page: 'agents'};
const scopeKeys = Object.keys(context);
const scopeVals = Object.values(context);
const boot = new Function(...scopeKeys, `${body}\nreturn {contentKey};`);
const {contentKey} = boot(...scopeVals);

const base = {
  observed_at: '2026-09-13T20:00:00Z',
  orders: [], projects: [], workspace: {}, truncated: false,
  sources: [{name: 'WorkForce heartbeat', state: 'fresh', last_at: '2026-09-13T20:00:00Z'}],
  agents: [{
    id: 'agent', name: 'Agent', group: 'seat', state: 'working', last_at: '2026-09-13T20:00:00Z',
    shift: {started_at: '2026-09-13T19:00:00Z', budget_secs: 3600, candidates: [], age_seconds: 5, stale: false, source: 'engine ledger'},
  }],
  engines: {
    worklane_api: {state: 'available', reachable: true, usable: true, http_status: 200, observed_at: '2026-09-13T20:00:00Z', last_success_at: '2026-09-13T20:00:00Z'},
    supervisor: {state: 'available', reachable: true, usable: true, outcome: 'dispatched', observed_at: '2026-09-13T20:00:00Z', last_success_at: '2026-09-13T20:00:00Z'},
  },
  supervisor: null,
};

const sameAgeVariant = JSON.parse(JSON.stringify(base));
sameAgeVariant.observed_at = '2026-09-13T20:00:05Z';
sameAgeVariant.sources[0].last_at = '2026-09-13T20:00:05Z';
sameAgeVariant.agents[0].last_at = '2026-09-13T20:00:05Z';
sameAgeVariant.agents[0].shift.age_seconds = 400;

const differentStartVariant = JSON.parse(JSON.stringify(base));
differentStartVariant.agents[0].shift.started_at = '2026-09-13T18:00:00Z';

const laterProbeVariant = JSON.parse(JSON.stringify(base));
laterProbeVariant.engines.worklane_api.observed_at = '2026-09-13T20:00:15Z';
laterProbeVariant.engines.worklane_api.last_success_at = '2026-09-13T20:00:15Z';
laterProbeVariant.engines.supervisor.observed_at = '2026-09-13T20:00:15Z';
laterProbeVariant.engines.supervisor.last_success_at = '2026-09-13T20:00:15Z';

const capabilityChangedVariant = JSON.parse(JSON.stringify(base));
capabilityChangedVariant.engines.worklane_api.state = 'reachable';
capabilityChangedVariant.engines.worklane_api.usable = false;

const keyBase = contentKey(base);
const keySameAge = contentKey(sameAgeVariant);
const keyDifferentStart = contentKey(differentStartVariant);
const keyLaterProbe = contentKey(laterProbeVariant);
const keyCapabilityChanged = contentKey(capabilityChangedVariant);

process.stdout.write(JSON.stringify({
  same_key_for_different_age_seconds: keyBase === keySameAge,
  different_key_for_different_started_at: keyBase !== keyDifferentStart,
  same_key_for_probe_timestamps: keyBase === keyLaterProbe,
  different_key_for_capability_state: keyBase !== keyCapabilityChanged,
}));
