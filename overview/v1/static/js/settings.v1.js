/**
 * settings.v1.js — Settings lens host (Designer IA, Overview four-lens).
 *
 * Reads local desk config from /api/overview/pulse (Cellar tip) and
 * /api/settings/desk (binder path + desk label). Rows are label · value ·
 * quiet hint — same density as Overview tiles. No cloud-ops toggles that
 * lie; V1 dark theme only.
 */

const ENDPOINTS = {
  desk: "/api/settings/desk",
  pulse: "/api/overview/pulse",
};

async function fetchJson(url, fetcher) {
  const res = await fetcher(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`settings: ${url} → ${res.status}`);
  return res.json();
}

function setText(root, role, text) {
  const el = root.querySelector(`[data-role="${role}"]`);
  if (el && typeof text === "string" && text.length > 0) el.textContent = text;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function paintDesk(root, desk) {
  const path = desk?.binder_path || "on this desk";
  const label = desk?.desk_label || "Local desk";
  setText(root, "set-binder-path", path);
  setText(root, "set-desk-label", label);
}

export function paintCellarTip(root, pulse) {
  // Cold fallback is blank, not a pinned version string — the server's
  // DEFAULT_CELLAR_TIP is the single cold source when brew is missing.
  const tip = pulse?.cellar_tip || "";
  setText(root, "set-cellar-tip", tip);
}

export function paintFooter(root, pulse) {
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
  const root = opts.root || document.getElementById("settings-shell");
  if (!root) throw new Error("settings: missing #settings-shell");
  const endpoints = { ...ENDPOINTS, ...(opts.endpoints || {}) };
  const fetcher = opts.fetcher || window.fetch.bind(window);
  try {
    const desk = await fetchJson(endpoints.desk, fetcher);
    paintDesk(root, desk || {});
  } catch (err) {
    console.warn("settings: desk unavailable", err);
  }
  try {
    const pulse = await fetchJson(endpoints.pulse, fetcher);
    paintCellarTip(root, pulse || {});
    paintFooter(root, pulse || { heartbeats: [] });
  } catch (err) {
    console.warn("settings: pulse unavailable", err);
  }
}

if (typeof window !== "undefined" && !window.__SETTINGS_V1_NO_AUTO_BOOT__) {
  boot();
}
