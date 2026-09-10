/**
 * overview.v1.js — Mission Control glass host.
 *
 * Paints three equal tiles (agents · jobs · pulse) from local-only JSON
 * against the /api/overview/* contract. Honest empty by default: if the
 * desk returns zero rows, the Writer copy (`No agents` / `No open jobs` /
 * silent pulse) stays on the tile — no shimmer, no synthesized activity.
 *
 * Invariants (see docs/specs/OVERVIEW_INTENT.md · OVERVIEW_THEME.md):
 *   - Never speak Map's verbs (dig, lot, hub, fan, trail, md-viewer, crumb).
 *   - Never say `workspace` — the banner says `Local desk`.
 *   - Pulse is discrete — draw ticks on load, never animate.
 *   - No live loop, no SSE, no polling — one fetch on boot per surface.
 */

const AGENT_STATES = new Set(["idle", "working", "error", "off"]);

const DEFAULT_ENDPOINTS = {
  agents: "/api/overview/agents",
  jobs: "/api/overview/jobs",
  pulse: "/api/overview/pulse",
};

async function fetchJson(url, fetcher) {
  const res = await fetcher(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`overview: ${url} → ${res.status}`);
  return res.json();
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function makeEmpty(text) {
  const p = document.createElement("p");
  p.className = "ov-empty";
  p.textContent = text;
  return p;
}

export function paintAgents(root, agents) {
  const body = root.querySelector('[data-role="agents-body"]');
  if (!body) return;
  clear(body);
  const rows = Array.isArray(agents) ? agents : [];
  if (rows.length === 0) {
    body.appendChild(makeEmpty("No agents"));
    return;
  }
  const list = document.createElement("ul");
  list.className = "ov-agent-list";
  for (const row of rows) {
    const li = document.createElement("li");
    li.className = "ov-agent-row";
    const dot = document.createElement("span");
    dot.className = "ov-agent-dot";
    const state = AGENT_STATES.has(row?.state) ? row.state : "idle";
    dot.dataset.state = state;
    dot.setAttribute("aria-label", state);
    const name = document.createElement("span");
    name.className = "ov-agent-name";
    name.textContent = row?.name || "";
    li.append(dot, name);
    list.appendChild(li);
  }
  body.appendChild(list);
}

export function paintJobs(root, jobs) {
  const body = root.querySelector('[data-role="jobs-body"]');
  if (!body) return;
  clear(body);
  const rows = Array.isArray(jobs) ? jobs : [];
  if (rows.length === 0) {
    body.appendChild(makeEmpty("No open jobs"));
    return;
  }
  const list = document.createElement("ul");
  list.className = "ov-job-list";
  for (const row of rows) {
    const li = document.createElement("li");
    li.className = "ov-job-row";
    const name = document.createElement("span");
    name.className = "ov-job-name";
    name.textContent = row?.name || "";
    const state = document.createElement("span");
    state.className = "ov-job-state";
    state.textContent = row?.state || "";
    li.append(name, state);
    list.appendChild(li);
  }
  body.appendChild(list);
}

export function paintPulse(root, pulse) {
  const body = root.querySelector('[data-role="pulse-body"]');
  if (!body) return;
  clear(body);
  const ticks = Array.isArray(pulse?.ticks) ? pulse.ticks : [];
  const track = document.createElement("div");
  track.className = "ov-pulse-track";
  track.setAttribute("aria-hidden", "true");
  if (ticks.length > 0) {
    // One quiet mark per tick, evenly spaced left-to-right. No animation,
    // no easing — ticks paint once when the fetch resolves.
    const n = ticks.length;
    for (let i = 0; i < n; i += 1) {
      const mark = document.createElement("span");
      mark.className = "ov-pulse-tick";
      const pct = n === 1 ? 50 : (i / (n - 1)) * 100;
      mark.style.left = `${pct}%`;
      track.appendChild(mark);
    }
  }
  body.appendChild(track);
  if (!pulse?.last_at && ticks.length === 0) {
    // Silent is allowed per THEME §Writer copy. Nothing to append.
    return;
  }
  if (pulse?.last_at) {
    const last = document.createElement("p");
    last.className = "ov-pulse-last";
    last.textContent = `Last: ${pulse.last_at}`;
    body.appendChild(last);
  }
}

export async function boot(opts = {}) {
  const root = opts.root || document.getElementById("overview-shell");
  if (!root) throw new Error("overview: missing #overview-shell");
  const endpoints = { ...DEFAULT_ENDPOINTS, ...(opts.endpoints || {}) };
  const fetcher = opts.fetcher || window.fetch.bind(window);

  const surfaces = [
    ["agents", (data) => paintAgents(root, data?.agents || [])],
    ["jobs", (data) => paintJobs(root, data?.jobs || [])],
    ["pulse", (data) => paintPulse(root, data || { ticks: [], last_at: null })],
  ];

  for (const [key, paint] of surfaces) {
    try {
      const data = await fetchJson(endpoints[key], fetcher);
      paint(data);
    } catch (err) {
      // Local-only honesty: on error, keep the honest-empty copy that
      // already sits in the tile. Never invent a fake row to compensate.
      console.warn(`overview: ${key} unavailable`, err);
    }
  }
}

if (typeof window !== "undefined" && !window.__OVERVIEW_V1_NO_AUTO_BOOT__) {
  boot();
}
