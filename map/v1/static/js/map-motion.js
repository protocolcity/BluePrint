// map-motion.js — stroke = recent place activity (issue #156 / pc-1561).
//
// Pure classifier. Paint hosts apply the returned stroke; nothing here
// invents pulses for unmatched folders or paints a fake zero spark.
// No WO wall, Overview dump, or density overlay. Mirrors node_motion.py.

export const WINDOW_MS = 24 * 60 * 60 * 1000;
export const LIVE_MOTION = 3;

export function emptyMotion(state = 'quiet') {
  if (state === 'unavailable') {
    return { stroke: 'unavailable', motion: 0, last_at: null, state: 'unavailable' };
  }
  return { stroke: 'none', motion: 0, last_at: null, state: 'quiet' };
}

export function parseStamp(value) {
  if (value == null || value === '') return null;
  if (value instanceof Date) {
    const ms = value.getTime();
    return Number.isFinite(ms) ? ms : null;
  }
  const text = String(value).trim().replace(' ', 'T');
  const iso = /[zZ]|[+-]\d{2}:\d{2}$/.test(text) ? text : `${text}Z`;
  const ms = Date.parse(iso);
  return Number.isFinite(ms) ? ms : null;
}

function intCount(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.floor(n);
}

export function classifyNodeMotion(project, pulse, now) {
  if (!project || typeof project !== 'object') return emptyMotion('quiet');
  const storeState = project.state || project.storeState || '';
  if (!storeState && !project.folder && !project.id) return emptyMotion('quiet');
  if ((storeState || 'unavailable') !== 'available') return emptyMotion('unavailable');

  const clock = now instanceof Date ? now.getTime() : (Number.isFinite(now) ? now : Date.now());
  const running = intCount(project.running);
  const lastChange = project.last_change && typeof project.last_change === 'object'
    ? project.last_change
    : null;
  const lastAt = lastChange && lastChange.at ? lastChange.at : null;
  const lastMs = parseStamp(lastAt);
  const recentChange = lastMs != null && lastMs >= clock - WINDOW_MS && lastMs <= clock;

  let motionCount = 0;
  if (pulse && typeof pulse === 'object' && pulse.state !== 'unavailable') {
    motionCount = intCount(pulse.motion);
  }

  let state = 'quiet';
  let stroke = 'none';
  if (running > 0 || motionCount >= LIVE_MOTION) {
    state = 'live';
    stroke = 'live';
  } else if (motionCount > 0 || recentChange) {
    state = 'recent';
    stroke = 'recent';
  }

  return {
    stroke,
    motion: motionCount,
    last_at: lastAt ? String(lastAt) : null,
    state,
  };
}

export function motionClassName(motion) {
  const stroke = motion && motion.stroke;
  if (stroke === 'recent' || stroke === 'live' || stroke === 'unavailable') {
    return ` map-motion-${stroke}`;
  }
  return '';
}

export function motionAriaSuffix(motion) {
  const stroke = motion && motion.stroke;
  if (stroke === 'live') return ', live motion';
  if (stroke === 'recent') return ', recent motion';
  return '';
}

export function indexNodeState(projects, portfolio) {
  const pulses = {};
  for (const row of (portfolio && portfolio.projects) || []) {
    if (row && row.id) pulses[row.id] = row;
  }
  const map = {};
  for (const project of projects || []) {
    if (!project || !project.folder) continue;
    map[project.folder] = {
      open: project.open || 0,
      attention: project.attention || 0,
      working: project.working || project.running || 0,
      state: project.state || 'unavailable',
      motion: classifyNodeMotion(project, pulses[project.id] || null),
    };
  }
  return map;
}
