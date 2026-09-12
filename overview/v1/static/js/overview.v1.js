/**
 * overview.v1.js — Mission Control glass host (full glass ext-01c/02c/03d).
 *
 * Paints three peer tiles (agents · jobs · pulse), an optional project card,
 * an optional Charter drawer, and a quiet footer strip — all from local-only
 * JSON against the /api/overview/* contract. Honest empty by default: if the
 * desk returns zero rows, the Writer copy (`No agents` / `No open jobs` /
 * silent pulse) stays on the tile — no shimmer, no synthesized activity.
 *
 * Invariants (see docs/specs/OVERVIEW_INTENT.md · OVERVIEW_THEME.md ·
 * OVERVIEW_MC_EXT.md):
 *   - Never speak Map's verbs (dig, lot, hub, fan, trail, md-viewer, crumb).
 *   - Never say `workspace` — the banner says `Local desk`.
 *   - Cloud / remote builders are outbound links — never agent rows.
 *   - Pulse is discrete — draw ticks on load, never animate.
 *   - Charter drawer sits alongside the peer tiles, never replaces them.
 *   - Missing heartbeat → `off` state (muted), never working green.
 *   - No live loop, no SSE, no polling — one fetch on boot per surface.
 */

const AGENT_STATES = new Set(["idle", "working", "error", "off"]);

const DEFAULT_ENDPOINTS = {
  agents: "/api/overview/agents",
  jobs: "/api/overview/jobs",
  pulse: "/api/overview/pulse",
  project: "/api/overview/project",
  charter: "/api/overview/charter",
};

const BADGE_META = [
  { key: "local_write", label: "Local write", litSuffix: "lit", glyph: "♁" },
  { key: "consume", label: "Consume", litSuffix: null, offSuffix: "off", glyph: "↓" },
  { key: "upstream", label: "Upstream", litSuffix: null, glyph: "↑" },
  { key: "local_only", label: "Local-only", litSuffix: null, glyph: "⌂" },
];

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

function formatClock(iso) {
  if (!iso) return "";
  const s = String(iso);
  const m = s.match(/(\d{2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return s;
  return m[3] ? `${m[1]}:${m[2]}:${m[3]}` : `${m[1]}:${m[2]}`;
}

export function paintAgents(root, agents, links) {
  const body = root.querySelector('[data-role="agents-body"]');
  const linksNode = root.querySelector('[data-role="agents-links"]');
  if (!body) return;

  const rows = Array.isArray(agents) ? agents : [];
  clear(body);
  if (rows.length === 0) {
    body.appendChild(makeEmpty("No agents"));
  } else {
    const list = document.createElement("ul");
    list.className = "ov-agent-list";
    for (const row of rows) {
      const li = document.createElement("li");
      li.className = "ov-agent-row";
      const name = document.createElement("span");
      name.className = "ov-agent-name";
      name.textContent = row?.name || "";
      const stateCell = document.createElement("span");
      stateCell.className = "ov-agent-state-cell";
      const state = AGENT_STATES.has(row?.state) ? row.state : "idle";
      const stateLabel = document.createElement("span");
      stateLabel.textContent = state;
      const dot = document.createElement("span");
      dot.className = "ov-agent-dot";
      dot.dataset.state = state;
      dot.setAttribute("aria-label", state);
      stateCell.append(stateLabel, dot);
      li.append(name, stateCell);
      list.appendChild(li);
    }
    body.appendChild(list);
  }

  if (!linksNode) return;
  clear(linksNode);
  const cloud = Array.isArray(links?.cloud_builders) ? links.cloud_builders : [];
  const remote = Array.isArray(links?.remote_builders) ? links.remote_builders : [];
  const cloudLink = buildBuilderLink("Cloud builders", "cloud", cloud);
  const remoteLink = buildBuilderLink("Remote builders", "remote", remote);
  if (cloudLink) linksNode.appendChild(cloudLink);
  if (remoteLink) linksNode.appendChild(remoteLink);
  linksNode.hidden = !cloudLink && !remoteLink;
}

function buildBuilderLink(label, kind, entries) {
  // A single "+ Cloud builders" / "+ Remote builders" line rendered as an
  // outbound link. Never painted as a local agent row. Only rendered when
  // an entry carries a real outbound url — never a `#hash` fallback. If
  // no outbound target exists, the group is silent (no anchor at all).
  const target = (entries || []).find((e) => e?.url);
  if (!target?.url) return null;
  const a = document.createElement("a");
  a.className = "ov-link-row";
  a.dataset.builder = kind;
  a.href = target.url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  const name = document.createElement("span");
  name.textContent = label;
  a.appendChild(name);
  const ext = document.createElement("span");
  ext.className = "ov-link-ext";
  ext.textContent = "↗";
  a.appendChild(ext);
  return a;
}

/** Cap for the Jobs MC tile — never wall the desk with full WorkLane. */
export const JOBS_TILE_CAP = 8;

const _JOB_STATE_RANK = { blocked: 0, ready: 1, waiting: 2 };

/**
 * Sort blocked → ready → waiting (unknown last), then take the first `cap`
 * rows. Returns `{ visible, more }` — buckets stay on the full API counts.
 */
export function rankAndCapJobs(jobs, cap = JOBS_TILE_CAP) {
  const rows = Array.isArray(jobs) ? jobs.slice() : [];
  rows.sort((a, b) => {
    const ra = _JOB_STATE_RANK[String(a?.state || "").toLowerCase()];
    const rb = _JOB_STATE_RANK[String(b?.state || "").toLowerCase()];
    const aa = ra === undefined ? 99 : ra;
    const bb = rb === undefined ? 99 : rb;
    return aa - bb;
  });
  const limit = Math.max(0, Number(cap) || JOBS_TILE_CAP);
  const visible = rows.slice(0, limit);
  const more = Math.max(0, rows.length - visible.length);
  return { visible, more };
}

export function paintJobs(root, jobs, buckets) {
  const body = root.querySelector('[data-role="jobs-body"]');
  const bucketNode = root.querySelector('[data-role="jobs-buckets"]');
  if (!body) return;

  const { visible, more } = rankAndCapJobs(jobs, JOBS_TILE_CAP);
  clear(body);
  if (visible.length === 0 && more === 0) {
    body.appendChild(makeEmpty("No open jobs"));
  } else {
    const list = document.createElement("ul");
    list.className = "ov-job-list";
    for (const row of visible) {
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
    if (more > 0) {
      const moreEl = document.createElement("p");
      moreEl.className = "ov-job-more";
      moreEl.textContent = `${more} more`;
      body.appendChild(moreEl);
    }
  }

  if (!bucketNode) return;
  clear(bucketNode);
  const b = buckets || { waiting: 0, ready: 0, blocked: 0 };
  const bucketRows = [
    ["waiting", "Waiting"],
    ["ready", "Ready"],
    ["blocked", "Blocked"],
  ];
  for (const [key, label] of bucketRows) {
    const row = document.createElement("div");
    row.className = "ov-bucket-row";
    const left = document.createElement("span");
    left.className = "ov-bucket-label";
    const dot = document.createElement("span");
    dot.className = "ov-bucket-dot";
    dot.dataset.bucket = key;
    const text = document.createElement("span");
    text.textContent = label;
    left.append(dot, text);
    const count = document.createElement("span");
    count.className = "ov-bucket-count";
    const n = Number(b[key] ?? 0);
    count.textContent = Number.isFinite(n) && n >= 0 ? String(n) : "0";
    row.append(left, count);
    bucketNode.appendChild(row);
  }
  bucketNode.hidden = false;
}

export function paintPulse(root, pulse) {
  const body = root.querySelector('[data-role="pulse-body"]');
  const metaNode = root.querySelector('[data-role="pulse-meta"]');
  if (!body) return;

  const heartbeats = Array.isArray(pulse?.heartbeats) ? pulse.heartbeats : [];
  const ticks = Array.isArray(pulse?.ticks) ? pulse.ticks : [];
  const cellarTip = pulse?.cellar_tip || "";
  const lastAt = pulse?.last_at || null;
  // All-off heartbeats read as silent pulse — a row list of five muted
  // ``off`` rows is not evidence of work. Only lit heartbeats surface as rows.
  const litHeartbeats = heartbeats.filter(
    (hb) => String(hb?.state || "off").toLowerCase() !== "off",
  );

  clear(body);
  if (litHeartbeats.length === 0 && ticks.length === 0 && !lastAt && !cellarTip) {
    // Honest empty: silent pulse (no orphan divider, per THEME §Writer copy).
    if (metaNode) {
      clear(metaNode);
      metaNode.hidden = true;
    }
    return;
  }

  if (litHeartbeats.length > 0) {
    const list = document.createElement("ul");
    list.className = "ov-pulse-list";
    for (const row of litHeartbeats) {
      const li = document.createElement("li");
      li.className = "ov-pulse-row";
      const glyph = document.createElement("span");
      glyph.className = "ov-pulse-glyph";
      glyph.setAttribute("aria-hidden", "true");
      glyph.textContent = "∿";
      const name = document.createElement("span");
      name.className = "ov-pulse-name";
      name.textContent = row?.name || "";
      const state = document.createElement("span");
      state.className = "ov-pulse-state";
      const st = String(row?.state || "off").toLowerCase();
      state.dataset.state = st;
      state.textContent = st;
      const time = document.createElement("span");
      time.className = "ov-pulse-time";
      time.textContent = formatClock(row?.last_at);
      li.append(glyph, name, state, time);
      list.appendChild(li);
    }
    body.appendChild(list);
  }

  if (ticks.length > 0) {
    const track = document.createElement("div");
    track.className = "ov-pulse-track";
    track.setAttribute("aria-hidden", "true");
    const n = ticks.length;
    for (let i = 0; i < n; i += 1) {
      const mark = document.createElement("span");
      mark.className = "ov-pulse-tick";
      const pct = n === 1 ? 50 : (i / (n - 1)) * 100;
      mark.style.left = `${pct}%`;
      track.appendChild(mark);
    }
    body.appendChild(track);
  }

  if (metaNode) {
    clear(metaNode);
    if (cellarTip) {
      const row = document.createElement("div");
      row.className = "ov-meta-row";
      const label = document.createElement("span");
      label.className = "ov-meta-label";
      label.textContent = "Cellar tip";
      const value = document.createElement("span");
      value.className = "ov-meta-value";
      value.textContent = cellarTip;
      row.append(label, value);
      metaNode.appendChild(row);
    }
    if (lastAt) {
      const row = document.createElement("div");
      row.className = "ov-meta-row";
      const label = document.createElement("span");
      label.className = "ov-meta-label";
      label.textContent = "Last tick";
      const value = document.createElement("span");
      value.className = "ov-meta-value ov-meta-value--muted";
      value.textContent = formatClock(lastAt);
      row.append(label, value);
      metaNode.appendChild(row);
    }
    metaNode.hidden = metaNode.childNodes.length === 0;
  }
}

export function paintProject(root, project) {
  const card = root.querySelector('[data-role="project-card"]');
  if (!card) return;
  if (!project || !project.title) {
    card.hidden = true;
    return;
  }
  const title = root.querySelector('[data-role="project-title"]');
  const path = root.querySelector('[data-role="project-path"]');
  const badges = root.querySelector('[data-role="project-badges"]');
  const excerptWrap = root.querySelector('[data-role="project-excerpt-wrap"]');
  const excerpt = root.querySelector('[data-role="project-excerpt"]');

  if (title) title.textContent = project.title;

  if (path) {
    clear(path);
    if (project.project) {
      const label = document.createElement("span");
      label.textContent = `Project: ${project.project} · `;
      path.appendChild(label);
    }
    const pathLabel = document.createElement("span");
    pathLabel.textContent = "Path: ";
    path.appendChild(pathLabel);
    // ``on this desk`` is the honesty voice — never `workspace`, never a
    // cloud path.
    const hint = document.createElement("strong");
    hint.textContent = project.path_hint || "on this desk";
    path.appendChild(hint);
  }

  if (badges) {
    clear(badges);
    const values = project.badges || {};
    for (const meta of BADGE_META) {
      const lit = Boolean(values[meta.key]);
      const badge = document.createElement("span");
      badge.className = "ov-badge";
      badge.dataset.lit = String(lit);
      badge.dataset.badge = meta.key;
      const glyph = document.createElement("span");
      glyph.className = "ov-badge-glyph";
      glyph.textContent = meta.glyph;
      badge.appendChild(glyph);
      const label = document.createElement("span");
      let tail = "";
      if (lit && meta.litSuffix) tail = ` ${meta.litSuffix}`;
      else if (!lit && meta.offSuffix) tail = ` ${meta.offSuffix}`;
      label.textContent = `${meta.label}${tail}`;
      badge.appendChild(label);
      if (lit && meta.key === "local_write") {
        const tailDot = document.createElement("span");
        tailDot.className = "ov-badge-tail";
        tailDot.textContent = "●";
        badge.appendChild(tailDot);
      }
      badges.appendChild(badge);
    }
  }

  if (excerpt && excerptWrap) {
    if (project.charter_excerpt) {
      excerpt.textContent = `“${project.charter_excerpt}”`;
      excerptWrap.hidden = false;
    } else {
      excerpt.textContent = "";
      excerptWrap.hidden = true;
    }
  }
  card.hidden = false;
}

export function paintCharter(root, charter) {
  const drawer = root.querySelector('[data-role="charter-drawer"]');
  if (!drawer) return;
  if (!charter || (!charter.title && !(charter.sections || []).length && !charter.footer)) {
    drawer.hidden = true;
    return;
  }
  const titleNode = root.querySelector("#ov-charter-title");
  const bodyNode = root.querySelector('[data-role="charter-body"]');
  const footerNode = root.querySelector('[data-role="charter-footer"]');
  if (titleNode) titleNode.textContent = charter.title || "Charter";
  if (bodyNode) {
    clear(bodyNode);
    for (const section of charter.sections || []) {
      const wrap = document.createElement("section");
      wrap.className = "ov-charter-section";
      if (section?.heading) {
        const h = document.createElement("h3");
        h.className = "ov-charter-heading";
        h.textContent = section.heading;
        wrap.appendChild(h);
      }
      if (section?.body) {
        const p = document.createElement("p");
        p.className = "ov-charter-text";
        p.textContent = section.body;
        wrap.appendChild(p);
      }
      bodyNode.appendChild(wrap);
    }
  }
  if (footerNode) {
    if (charter.footer) {
      footerNode.textContent = charter.footer;
      footerNode.hidden = false;
    } else {
      footerNode.textContent = "";
      footerNode.hidden = true;
    }
  }
  drawer.hidden = false;
}

export function paintNext(root, next) {
  const wrap = root.querySelector('[data-role="jobs-next"]');
  const link = root.querySelector('[data-role="jobs-next-link"]');
  if (!wrap || !link) return;
  const verb = next && next.verb ? String(next.verb) : "";
  const object = next && next.object ? String(next.object) : "";
  if (!verb || !object) {
    wrap.hidden = true;
    link.textContent = "";
    return;
  }
  link.textContent = `${verb} ${object}`;
  const href = next.href ? String(next.href) : "";
  if (href) {
    link.setAttribute("href", href);
  } else {
    link.removeAttribute("href");
  }
  wrap.hidden = false;
}

export function bindProjectActions(root) {
  const charterBtn = root.querySelector('[data-role="action-open-charter"]');
  if (charterBtn) {
    charterBtn.addEventListener("click", (ev) => {
      ev.preventDefault();
      const drawer = root.querySelector('[data-role="charter-drawer"]');
      if (drawer && !drawer.hidden) {
        drawer.scrollIntoView({ block: "nearest" });
      }
    });
  }
  const flagBtn = root.querySelector('[data-role="action-plant-flag"]');
  if (flagBtn) {
    flagBtn.setAttribute("href", "/map");
  }
  const agentsBtn = root.querySelector('[data-role="action-read-agents"]');
  if (agentsBtn) {
    agentsBtn.setAttribute("href", "/map?md=AGENTS.md");
  }
}

export function paintFooter(root, pulse) {
  // Mirror the pulse heartbeats in a single quiet footer line — but only
  // the lit ones. A permanent row of five `off` cells is noise, not
  // signal (spec: hide fake permanent Off footer rows until real signals
  // exist). The trailing "All systems quiet" label is a Writer string
  // that lives regardless.
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
  const root = opts.root || document.getElementById("overview-shell");
  if (!root) throw new Error("overview: missing #overview-shell");
  const endpoints = { ...DEFAULT_ENDPOINTS, ...(opts.endpoints || {}) };
  const fetcher = opts.fetcher || window.fetch.bind(window);

  const surfaces = [
    ["agents", (data) =>
      paintAgents(root, data?.agents || [], {
        cloud_builders: data?.cloud_builders || [],
        remote_builders: data?.remote_builders || [],
      }),
    ],
    ["jobs", (data) => {
      paintJobs(root, data?.jobs || [], data?.buckets || { waiting: 0, ready: 0, blocked: 0 });
      paintNext(root, data?.next || {});
    }],
    ["pulse", (data) => {
      const pulse = data || { heartbeats: [], ticks: [], last_at: null, cellar_tip: "" };
      paintPulse(root, pulse);
      paintFooter(root, pulse);
    }],
    ["project", (data) => paintProject(root, data || {})],
    ["charter", (data) => paintCharter(root, data || {})],
  ];

  bindProjectActions(root);

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
