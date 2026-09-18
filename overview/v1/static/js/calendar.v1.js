/**
 * calendar.v1.js — Calendar lens host (Designer IA, Overview four-lens).
 *
 * Reads local desk events from /api/calendar/events and paints the
 * One Agenda factory clock: weighted doors, week/day spine, Hybrid
 * source honesty. Honest empty by default (`No events`) — never shimmer,
 * never fake Google/MCP. Calendar is time on **this desk**; nothing else.
 *
 * Load-by-day bars (issue #153) count dated clocks, local events, and
 * WorkForce next_fire onto a Monday–Sunday week. Open WO dumps and the
 * Agents floor stay off this host.
 *
 * Never speaks Map's verbs (dig, lot, hub, fan, trail, md-viewer, crumb).
 */

const ENDPOINTS = {
  events: "/api/calendar/events",
  pulse: "/api/overview/pulse",
  operations: "/api/operations",
};

const EVENT_SOURCES = new Set(["routine", "WO", "manual"]);
const EVENT_STATES = new Set(["scheduled", "due", "done"]);
const SCHEDULE_KINDS = new Set(["deadline", "reminder", "timer"]);
const LOAD_DAYS = 7;
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const NONE_FIRE_LINE = "Next fire · none reported";

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

function eventRecord(row) {
  const src = EVENT_SOURCES.has(row?.source) ? row.source : "manual";
  const st = EVENT_STATES.has(row?.state) ? row.state : "scheduled";
  return {
    title: row?.title || "",
    at: row?.at || "",
    source: src,
    state: st,
    notes: typeof row?.notes === "string" ? row.notes : "",
  };
}

export function dayKey(from) {
  const d = from instanceof Date ? from : new Date();
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

export function shiftDay(key, days) {
  const [y, m, d] = String(key).split("-").map(Number);
  return dayKey(new Date(y, m - 1, d + days));
}

export function weekMonday(key) {
  const [y, m, d] = String(key).split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  return dayKey(new Date(y, m - 1, d - ((dt.getDay() + 6) % 7)));
}

export function localDayKey(value, allDay) {
  if (!value) return "";
  const raw = String(value);
  if (allDay || /^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw.slice(0, 10);
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.valueOf())) return raw.slice(0, 10);
  return dayKey(parsed);
}

export function emptyLoad(state = "empty") {
  return { state, origin: "", days: [], total: 0 };
}

export function emptyDoors() {
  return {
    due_count: 0,
    due_href: "/calendar",
    items: [],
    next_fire: null,
    next_fire_line: NONE_FIRE_LINE,
  };
}

export function buildLoadByDay(opts = {}) {
  if (opts.readable === false) return emptyLoad("unavailable");
  const origin = opts.origin || dayKey(opts.now || new Date());
  const start = weekMonday(origin);
  const project = opts.project || "";
  const today = opts.today || dayKey(opts.now || new Date());
  const selected = opts.selected || opts.origin || today;
  const days = [];
  for (let i = 0; i < LOAD_DAYS; i += 1) {
    const day = shiftDay(start, i);
    days.push({
      day,
      label: WEEKDAYS[i],
      count: 0,
      today: day === today,
      selected: day === selected,
    });
  }
  const index = Object.fromEntries(days.map((row) => [row.day, row]));

  for (const row of opts.workDates || []) {
    if (!SCHEDULE_KINDS.has(String(row?.kind || "").trim())) continue;
    if (project && String(row.product || "") !== project) continue;
    const key = localDayKey(row.dtstart, row.all_day);
    if (index[key]) index[key].count += 1;
  }
  for (const event of opts.events || []) {
    const key = localDayKey(event?.at, false);
    if (index[key]) index[key].count += 1;
  }
  for (const agent of opts.agents || []) {
    const key = localDayKey(agent?.next_fire, false);
    if (index[key]) index[key].count += 1;
  }

  const total = days.reduce((sum, row) => sum + row.count, 0);
  return {
    state: total ? "healthy" : "empty",
    origin: start,
    days,
    total,
  };
}

export function paintLoad(root, load) {
  const host = root.querySelector('[data-role="cal-load"]');
  if (!host) return;
  const summary =
    host.querySelector('[data-role="cal-load-summary"]') ||
    root.querySelector('[data-role="cal-load-summary"]');
  const chart =
    host.querySelector('[data-role="cal-load-chart"]') ||
    root.querySelector('[data-role="cal-load-chart"]');
  const payload = load && typeof load === "object" ? load : emptyLoad();
  if (summary) {
    if (payload.state === "unavailable") {
      summary.textContent = "Schedule load unavailable";
    } else if (!payload.total) {
      summary.textContent = "Quiet this week.";
    } else {
      const n = payload.total;
      summary.textContent = `${n} scheduled · this week`;
    }
  }
  if (!chart) return;
  if (payload.state === "unavailable" || !payload.total || !payload.days?.length) {
    chart.hidden = true;
    clear(chart);
    return;
  }
  const peak = Math.max(...payload.days.map((row) => Number(row.count) || 0), 1);
  chart.hidden = false;
  chart.setAttribute("role", "img");
  if (summary) chart.setAttribute("aria-label", summary.textContent);
  clear(chart);
  for (const row of payload.days) {
    const count = Number(row.count) || 0;
    const col = document.createElement("button");
    col.type = "button";
    col.className = "ov-cal-load-col";
    col.dataset.day = row.day || "";
    if (row.today) col.dataset.today = "true";
    if (row.selected) col.dataset.selected = "true";
    const countEl = document.createElement("span");
    countEl.className = "ov-cal-load-count";
    countEl.textContent = String(count);
    col.appendChild(countEl);
    const track = document.createElement("div");
    track.className = "ov-cal-load-track";
    const bar = document.createElement("div");
    bar.className = "ov-cal-load-bar";
    bar.style.height = `${Math.round((count / peak) * 100)}%`;
    bar.dataset.empty = count ? "false" : "true";
    bar.title = `${count} · ${row.day}`;
    track.appendChild(bar);
    col.appendChild(track);
    const label = document.createElement("span");
    label.className = "ov-cal-load-label";
    label.textContent = row.label || "";
    col.appendChild(label);
    chart.appendChild(col);
  }
}

export function paintDoors(root, doors) {
  const host = root.querySelector('[data-role="cal-doors"]');
  if (!host) return;
  const payload = doors && typeof doors === "object" ? doors : emptyDoors();
  const dueCount = Number(payload.due_count) || 0;
  const fireLine = payload.next_fire_line || NONE_FIRE_LINE;
  const firePrimary = fireLine.replace(/^Next fire · /, "") || "none reported";
  clear(host);
  const items = [
    {
      kind: "due",
      name: "Due",
      primary: dueCount ? String(dueCount) : "none",
      href: "/",
      tone: dueCount ? "open" : "muted",
    },
    {
      kind: "remind",
      name: "Due / Remind",
      primary: "My todos",
      href: "/work?attention=my_todos",
      tone: dueCount ? "open" : "muted",
    },
    {
      kind: "next-fire",
      name: "Next fire",
      primary: firePrimary,
      href: "/agents",
      tone: payload.next_fire ? "open" : "muted",
    },
    {
      kind: "firings",
      name: "Firings",
      primary: "Timeline",
      href: "/timeline",
      tone: "open",
    },
  ];
  for (const item of items) {
    const a = document.createElement("a");
    a.className = "ov-cal-door bp-cal-door";
    a.href = item.href;
    a.dataset.kind = item.kind;
    a.dataset.tone = item.tone;
    const name = document.createElement("span");
    name.className = "bp-cal-door-name";
    name.textContent = item.name;
    const primary = document.createElement("span");
    primary.className = "bp-cal-door-primary";
    primary.textContent = item.primary;
    a.append(name, primary);
    host.appendChild(a);
  }
}

// Hybrid honesty (CAP_ACQUAINTANCE_052 C2 / One Agenda): WorkLane is the
// live schedule spine. MCP and Connector stay dim / not-wired until that
// fabric exists. Local schedule is an honesty line, not a fourth live
// source. Apple/Outlook are reserved outbound readers — BluePrint stays
// the source of truth.
export function sourceStripChips(opts = {}) {
  return [
    { id: "worklane", label: "WorkLane", state: opts.workLane ? "live" : "unavailable" },
    { id: "mcp", label: "MCP", state: "reserved" },
    { id: "connector", label: "Connector", state: "reserved" },
  ];
}

export function outboundStripChips() {
  return [
    { id: "apple", label: "Apple · reader", state: "reserved" },
    { id: "outlook", label: "Outlook · reader", state: "reserved" },
  ];
}

const CHIP_STATE_LABELS = {
  live: "Live",
  unavailable: "Unavailable",
  reserved: "not wired",
};

function paintChipStrip(root, role, chips, reservedTitle) {
  const host = root.querySelector(`[data-role="${role}"]`);
  if (!host) return;
  clear(host);
  for (const chip of chips) {
    const span = document.createElement("span");
    span.className = "bp-cal-chip";
    span.dataset.state = chip.state;
    const stateLabel = CHIP_STATE_LABELS[chip.state] || chip.state;
    span.textContent = `${chip.label} · ${stateLabel}`;
    if (chip.state === "reserved") {
      span.title = reservedTitle || `${chip.label} — not wired yet`;
    } else if (chip.state === "unavailable") {
      span.title = `${chip.label} — unavailable`;
    }
    host.appendChild(span);
  }
}

export function paintSourceStrip(root, opts = {}) {
  paintChipStrip(root, "cal-sources", sourceStripChips(opts));
}

export function paintOutboundStrip(root) {
  paintChipStrip(
    root,
    "cal-outbound",
    outboundStripChips(),
    "Reserved outbound reader — BluePrint stays source of truth",
  );
}

export function openSheet(root, event) {
  const sheet = root.querySelector('[data-role="cal-sheet"]');
  if (!sheet) return;
  const rec = eventRecord(event || {});
  const title = root.querySelector('[data-role="cal-sheet-title"]');
  const when = root.querySelector('[data-role="cal-sheet-when"]');
  const notes = root.querySelector('[data-role="cal-sheet-notes"]');
  if (title) title.textContent = rec.title;
  if (when) when.textContent = formatWhen(rec.at);
  if (notes) notes.textContent = rec.notes;
  if (typeof sheet.showModal === "function") {
    if (!sheet.open) sheet.showModal();
  } else {
    sheet.hidden = false;
    sheet.open = true;
  }
}

export function closeSheet(root) {
  const sheet = root.querySelector('[data-role="cal-sheet"]');
  if (!sheet) return;
  if (typeof sheet.close === "function" && sheet.open) {
    sheet.close();
  } else {
    sheet.hidden = true;
    sheet.open = false;
  }
}

export function bindSheet(root) {
  const sheet = root.querySelector('[data-role="cal-sheet"]');
  if (!sheet || sheet.dataset.bound === "1") return;
  sheet.dataset.bound = "1";
  const closer = root.querySelector('[data-role="cal-sheet-close"]');
  if (closer) {
    closer.addEventListener("click", () => closeSheet(root));
  }
  sheet.addEventListener("click", (ev) => {
    if (ev.target === sheet) closeSheet(root);
  });
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
    const rec = eventRecord(row);
    const li = document.createElement("li");
    li.className = "ov-cal-event";
    li.setAttribute("role", "button");
    li.setAttribute("tabindex", "0");
    const title = document.createElement("span");
    title.className = "ov-cal-event-title";
    title.textContent = rec.title;
    const when = document.createElement("span");
    when.className = "ov-cal-event-when";
    when.textContent = formatWhen(rec.at);
    const source = document.createElement("span");
    source.className = "ov-cal-event-source";
    source.textContent = rec.source;
    source.dataset.source = rec.source;
    const state = document.createElement("span");
    state.className = "ov-cal-event-state";
    state.textContent = rec.state;
    state.dataset.state = rec.state;
    li.append(title, when, source, state);
    li.addEventListener("click", () => openSheet(root, rec));
    li.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        if (typeof ev.preventDefault === "function") ev.preventDefault();
        openSheet(root, rec);
      }
    });
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
  let events = [];
  try {
    const data = await fetchJson(endpoints.events, fetcher);
    events = data?.events || [];
    paintEvents(root, events);
    paintRange(root, data?.range || "");
  } catch (err) {
    // Local-only honesty: on error keep the `No events` copy on screen.
    console.warn("calendar: events unavailable", err);
  }
  let doors = emptyDoors();
  let load = buildLoadByDay({ events, origin: dayKey() });
  try {
    const ops = await fetchJson(endpoints.operations, fetcher);
    if (ops?.calendar_doors && typeof ops.calendar_doors.due_count === "number") {
      doors = ops.calendar_doors;
    }
    load = buildLoadByDay({
      workDates: ops?.work_dates || [],
      events: (ops?.events && ops.events.length ? ops.events : events),
      agents: ops?.agents || [],
      origin: dayKey(),
      readable: Boolean(ops?.workspace),
    });
  } catch (err) {
    console.warn("calendar: operations unavailable", err);
  }
  paintDoors(root, doors);
  paintLoad(root, load);
  bindSheet(root);
  try {
    const pulse = await fetchJson(endpoints.pulse, fetcher);
    paintFooter(root, pulse || { heartbeats: [] });
  } catch (err) {
    console.warn("calendar: pulse unavailable", err);
  }
}

if (typeof window !== "undefined" && !window.__CALENDAR_V1_NO_AUTO_BOOT__) {
  const shell = typeof document !== "undefined"
    ? document.getElementById("calendar-shell")
    : null;
  if (shell) boot({ root: shell });
}
