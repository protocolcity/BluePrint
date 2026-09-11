/**
 * calendar.v1.js — Calendar lens host (Designer IA, Overview four-lens).
 *
 * Reads local desk events from /api/calendar/events and paints a quiet
 * week list. Honest empty by default (`No events`) — never shimmer, never
 * fake a busy schedule. Calendar is time on **this desk**; nothing else.
 *
 * Never speaks Map's verbs (dig, lot, hub, fan, trail, md-viewer, crumb).
 */

const ENDPOINTS = {
  events: "/api/calendar/events",
  pulse: "/api/overview/pulse",
};

const EVENT_SOURCES = new Set(["routine", "WO", "manual"]);
const EVENT_STATES = new Set(["scheduled", "due", "done"]);

async function fetchJson(url, fetcher) {
  const res = await fetcher(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`calendar: ${url} → ${res.status}`);
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

function formatWhen(iso) {
  if (!iso) return "";
  const s = String(iso);
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (!m) return s;
  const clock = m[4] ? ` · ${m[4]}:${m[5]}` : "";
  return `${m[1]}-${m[2]}-${m[3]}${clock}`;
}

export function paintEvents(root, events) {
  const list = root.querySelector('[data-role="cal-list"]');
  if (!list) return;
  const rows = Array.isArray(events) ? events : [];
  clear(list);
  if (rows.length === 0) {
    list.appendChild(makeEmpty("No events"));
    return;
  }
  const ul = document.createElement("ul");
  ul.className = "ov-cal-events";
  for (const row of rows) {
    const li = document.createElement("li");
    li.className = "ov-cal-event";
    const title = document.createElement("span");
    title.className = "ov-cal-event-title";
    title.textContent = row?.title || "";
    const when = document.createElement("span");
    when.className = "ov-cal-event-when";
    when.textContent = formatWhen(row?.at);
    const source = document.createElement("span");
    source.className = "ov-cal-event-source";
    const src = EVENT_SOURCES.has(row?.source) ? row.source : "manual";
    source.textContent = src;
    source.dataset.source = src;
    const state = document.createElement("span");
    state.className = "ov-cal-event-state";
    const st = EVENT_STATES.has(row?.state) ? row.state : "scheduled";
    state.textContent = st;
    state.dataset.state = st;
    li.append(title, when, source, state);
    ul.appendChild(li);
  }
  list.appendChild(ul);
}

export function paintRange(root, range) {
  const el = root.querySelector('[data-role="cal-range"]');
  if (!el) return;
  el.textContent = range || "";
}

export function paintFooter(root, pulse) {
  // Mirror the pulse tile's rule: only lit heartbeats surface as rows.
  // Permanent `off` rows are noise, not signal — they stay silent.
  const row = root.querySelector('[data-role="footer-row"]');
  if (!row) return;
  const heartbeats = Array.isArray(pulse?.heartbeats) ? pulse.heartbeats : [];
  const lit = heartbeats.filter(
    (hb) => String(hb?.state || "off").toLowerCase() !== "off",
  );
  clear(row);
  for (const hb of lit) {
    const cell = document.createElement("span");
    cell.className = "ov-footer-cell";
    const name = document.createElement("span");
    name.className = "ov-footer-name";
    name.textContent = hb?.name || "";
    const dot = document.createElement("span");
    dot.className = "ov-footer-dot";
    const st = String(hb?.state || "off").toLowerCase();
    dot.dataset.state = st;
    const state = document.createElement("span");
    state.className = "ov-footer-state";
    state.textContent = st;
    cell.append(name, dot, state);
    row.appendChild(cell);
  }
}

export async function boot(opts = {}) {
  const root = opts.root || document.getElementById("calendar-shell");
  if (!root) throw new Error("calendar: missing #calendar-shell");
  const endpoints = { ...ENDPOINTS, ...(opts.endpoints || {}) };
  const fetcher = opts.fetcher || window.fetch.bind(window);
  try {
    const data = await fetchJson(endpoints.events, fetcher);
    paintEvents(root, data?.events || []);
    paintRange(root, data?.range || "");
  } catch (err) {
    // Local-only honesty: on error keep the `No events` copy on screen.
    console.warn("calendar: events unavailable", err);
  }
  try {
    const pulse = await fetchJson(endpoints.pulse, fetcher);
    paintFooter(root, pulse || { heartbeats: [] });
  } catch (err) {
    console.warn("calendar: pulse unavailable", err);
  }
}

if (typeof window !== "undefined" && !window.__CALENDAR_V1_NO_AUTO_BOOT__) {
  boot();
}
