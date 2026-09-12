/**
 * suite-paper.js — Summary for city papers (.md) and Desk tickets (pc-272)
 *
 * Click /read?path=… or /ticket?id=… → in-room Summary over the current room.
 * Map modal chrome (pc-449): Full page + close only (Rail / Source retired).
 * Modal always uses stage-readable layout; density keyboard (.) is a no-op.
 * Full page (`/read` · `/ticket`) is a one-shot escape (pc-495) — soft-nav via
 * suite-nav; does not sticky-prefer full for later dig-ins. Cmd-click still
 * hard-navigates. Viewer chrome leads with Full page + × above content
 * identity (pc-483). Esc · backdrop · × close.
 *
 * Playlist: all paper/ticket links on the page, in DOM order.
 * Prev/next: buttons · ←/→ · [/] · j/k (when Summary open).
 */
(function (global) {
  /* pc-1396: HTML escape lives in /esc.js */
  var esc = function (s) { return global.__bp.esc(s); };

  /** Resolve dotdot segments; strip leading slash. */
  function normalizeCityPath(p) {
    var parts = String(p || "").replace(/^\/+/, "").split("/");
    var out = [];
    for (var pi = 0; pi < parts.length; pi++) {
      if (parts[pi] === "..") out.pop();
      else if (parts[pi] !== ".") out.push(parts[pi]);
    }
    return out.join("/");
  }

  /**
   * Lightweight markdown → HTML (demo-grade; offline, no CDN).
   * Large papers (ledgers, dumps): cap initial paint so full-page / overlay
   * stay responsive; pass { full: true } to force complete render.
   */
  var MD_FAST_CHAR_CAP = 120000;

  function renderMd(src, basePath, opts) {
    opts = opts || {};
    var raw = String(src || "").replace(/\r\n/g, "\n");
    var truncated = false;
    if (!opts.full && raw.length > MD_FAST_CHAR_CAP) {
      truncated = true;
      /* Prefer a line boundary so we don't split mid-code-fence badly. */
      var cut = raw.lastIndexOf("\n", MD_FAST_CHAR_CAP);
      if (cut < MD_FAST_CHAR_CAP * 0.5) cut = MD_FAST_CHAR_CAP;
      raw = raw.slice(0, cut);
    }
    const lines = raw.split("\n");
    const out = [];
    let i = 0;
    let inCode = false,
      codeBuf = [];
    let inUl = false,
      inOl = false,
      inTable = false,
      tableBuf = [];
    let para = [];

    function closeLists() {
      if (inUl) {
        out.push("</ul>");
        inUl = false;
      }
      if (inOl) {
        out.push("</ol>");
        inOl = false;
      }
    }
    function flushPara() {
      if (!para.length) return;
      const t = para.join(" ").trim();
      if (t) out.push("<p>" + inline(t) + "</p>");
      para = [];
    }
    function flushTable() {
      if (!tableBuf.length) return;
      closeLists();
      flushPara();
      const rows = tableBuf.filter(
        (r) => !/^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(r)
      );
      out.push("<table>");
      rows.forEach((row, ri) => {
        const cells = row.replace(/^\|/, "").replace(/\|$/, "").split("|");
        const tag = ri === 0 ? "th" : "td";
        out.push(
          "<tr>" +
            cells
              .map((c) => `<${tag}>` + inline(c.trim()) + `</${tag}>`)
              .join("") +
            "</tr>"
        );
      });
      out.push("</table>");
      tableBuf = [];
      inTable = false;
    }
    function inline(t) {
      t = esc(t);
      t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
      t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      t = t.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, text, href) {
        if (/^https?:\/\//i.test(href)) {
          return '<a href="' + href + '" target="_blank" rel="noopener">' + text + "</a>";
        }
        if (/\.md(#[^)]*)?$/.test(href)) {
          var bare = href.replace(/#.*$/, "");
          var frag = (href.match(/#(.*)$/) || [])[1] || "";
          var dir =
            basePath && basePath.indexOf("/") !== -1
              ? basePath.slice(0, basePath.lastIndexOf("/") + 1)
              : "";
          var resolved = normalizeCityPath(dir + bare);
          var readHref =
            "/read?path=" +
            encodeURIComponent(resolved) +
            (frag ? "#" + frag : "");
          return (
            '<a href="' +
            readHref +
            '" data-paper-link="' +
            esc(resolved) +
            '">' +
            text +
            "</a>"
          );
        }
        return '<a href="' + href + '" target="_blank" rel="noopener">' + text + "</a>";
      });
      return t;
    }

    while (i < lines.length) {
      const line = lines[i];
      if (line.startsWith("```")) {
        flushTable();
        closeLists();
        flushPara();
        if (!inCode) {
          inCode = true;
          codeBuf = [];
        } else {
          out.push("<pre><code>" + esc(codeBuf.join("\n")) + "</code></pre>");
          inCode = false;
          codeBuf = [];
        }
        i++;
        continue;
      }
      if (inCode) {
        codeBuf.push(line);
        i++;
        continue;
      }
      if (/^\|/.test(line) && line.includes("|", 1)) {
        closeLists();
        flushPara();
        inTable = true;
        tableBuf.push(line);
        i++;
        continue;
      } else if (inTable) {
        flushTable();
      }
      if (/^---+\s*$/.test(line) || /^\*\*\*+\s*$/.test(line)) {
        closeLists();
        flushPara();
        out.push("<hr>");
        i++;
        continue;
      }
      const hm = /^(#{1,4})\s+(.*)$/.exec(line);
      if (hm) {
        closeLists();
        flushPara();
        out.push(`<h${hm[1].length}>` + inline(hm[2]) + `</h${hm[1].length}>`);
        i++;
        continue;
      }
      if (/^>\s?/.test(line)) {
        closeLists();
        flushPara();
        const q = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) {
          q.push(lines[i].replace(/^>\s?/, ""));
          i++;
        }
        out.push(
          "<blockquote><p>" + inline(q.join(" ")) + "</p></blockquote>"
        );
        continue;
      }
      if (/^\s*[-*+]\s+/.test(line)) {
        flushPara();
        if (inOl) {
          out.push("</ol>");
          inOl = false;
        }
        if (!inUl) {
          out.push("<ul>");
          inUl = true;
        }
        out.push(
          "<li>" + inline(line.replace(/^\s*[-*+]\s+/, "")) + "</li>"
        );
        i++;
        continue;
      }
      if (/^\s*\d+\.\s+/.test(line)) {
        flushPara();
        if (inUl) {
          out.push("</ul>");
          inUl = false;
        }
        if (!inOl) {
          out.push("<ol>");
          inOl = true;
        }
        out.push(
          "<li>" + inline(line.replace(/^\s*\d+\.\s+/, "")) + "</li>"
        );
        i++;
        continue;
      }
      if (!line.trim()) {
        closeLists();
        flushPara();
        i++;
        continue;
      }
      closeLists();
      para.push(line.trim());
      i++;
    }
    if (inCode)
      out.push("<pre><code>" + esc(codeBuf.join("\n")) + "</code></pre>");
    flushTable();
    closeLists();
    flushPara();
    if (truncated) {
      out.push(
        '<p class="suite-paper-truncate" data-paper-truncate="1">' +
          "<em>Showing first ~" +
          Math.round(MD_FAST_CHAR_CAP / 1000) +
          "k characters for speed.</em> " +
          '<button type="button" class="suite-paper-render-full">Render full paper</button>' +
          " · use <strong>view source</strong> for the raw file." +
          "</p>"
      );
    }
    return out.join("\n");
  }

  /** Wire "Render full paper" after a truncated renderMd paint. */
  function wireTruncateExpand(bodyEl, fullContent, basePath) {
    if (!bodyEl) return;
    var btn = bodyEl.querySelector(".suite-paper-render-full");
    if (!btn) return;
    btn.addEventListener("click", function () {
      bodyEl.innerHTML = renderMd(fullContent, basePath, { full: true });
      wireRelativeLinks(bodyEl);
      bodyEl.scrollTop = 0;
    });
  }

  function pathFromHref(href) {
    if (!href) return null;
    try {
      const u = new URL(href, global.location.origin);
      if (u.pathname !== "/read" && u.pathname !== "/read_v1.html") return null;
      const p = (u.searchParams.get("path") || "").replace(/^\/+/, "");
      return p || null;
    } catch (e) {
      return null;
    }
  }

  function ticketIdFromHref(href) {
    if (!href) return null;
    try {
      const u = new URL(href, global.location.origin);
      if (u.pathname !== "/ticket" && u.pathname !== "/ticket_v1.html")
        return null;
      const id = (u.searchParams.get("id") || "").trim();
      return id || null;
    } catch (e) {
      return null;
    }
  }

  function itemKey(it) {
    return it.type + ":" + it.id;
  }

  function fullHref(it) {
    if (it.type === "ticket")
      return "/ticket?id=" + encodeURIComponent(it.id);
    return "/read?path=" + encodeURIComponent(it.id);
  }

  function niceTs(ts) {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return String(ts);
    }
  }

  /**
   * pc-1187: compact open/touch age (no "ago") for dig-in foot.
   * Returns "" | "just now" | "12m" | "3h" | "9d".
   */
  function ageCompact(ts) {
    if (!ts) return "";
    let ms = 0;
    if (typeof ts === "number" && isFinite(ts)) {
      ms = ts < 1e12 ? ts * 1000 : ts;
    } else {
      ms = Date.parse(String(ts));
    }
    if (!isFinite(ms) || ms <= 0) return "";
    const ago = Date.now() - ms;
    if (ago < 45 * 1000) return "just now";
    if (ago < 60 * 60 * 1000)
      return Math.max(1, Math.round(ago / 60000)) + "m";
    if (ago < 24 * 60 * 60 * 1000)
      return Math.max(1, Math.round(ago / 3600000)) + "h";
    return Math.max(1, Math.round(ago / 86400000)) + "d";
  }

  function productSlug(task) {
    let p = (task.product || task.project || "").toLowerCase();
    if (p === "ticketingprotocol") p = "worklane";
    if (p) return p;
    const id = (task.id || "").toLowerCase();
    const pref = id.split("-")[0];
    return (
      {
        ts: "tradeos",
        t: "tradeos",
        tp: "worklane",
        wl: "worklane",
        pc: "protocolcity",
        wf: "workforce",
        oc: "workforce",
        so: "socials",
        gf: "gridfinity",
        conn: "connector",
        osp: "oneseo-pos",
        regi: "oneseo-pos",
        career: "career",
        reci: "recipes",
      }[pref] || ""
    );
  }

  var MAP_PROJECT_SLUGS = {
    protocolcity: 1,
    tradeos: 1,
    worklane: 1,
    ticketingprotocol: 1,
    workforce: 1,
    "oneseo-pos": 1,
    oneseopos: 1,
    socials: 1,
    gridfinity: 1,
    connector: 1,
    davinci: 1,
    career: 1,
    recipes: 1,
    presentations: 1,
  };

  function isMapProjectSlug(s) {
    const n = String(s || "")
      .toLowerCase()
      .replace(/_/g, "-");
    return !!MAP_PROJECT_SLUGS[n];
  }

  /** Top folder / slug → Map project key (city-relative path first segment). */
  function mapSlugFromPath(pathOrSlug) {
    const raw = String(pathOrSlug || "")
      .replace(/^\/+/, "")
      .split("/")[0];
    if (!raw) return "";
    const low = raw.toLowerCase();
    const aliases = {
      tradeos: "tradeos",
      protocolcity: "protocolcity",
      ticketingprotocol: "worklane",
      worklane: "worklane",
      workforce: "workforce",
      orchestrator: "workforce",
    };
    return aliases[low] || low;
  }

  function rowHtml(k, v) {
    return (
      '<div class="suite-ticket-row"><span class="k">' +
      esc(k) +
      '</span><span class="v">' +
      v +
      "</span></div>"
    );
  }

  /** Seat face for You — suite.youLabel, never engine "human". */
  function youFaceLabel() {
    try {
      const v = String(localStorage.getItem("suite.youLabel") || "").trim();
      if (v && v.toLowerCase() !== "you") return v;
    } catch (e) {}
    return "You";
  }

  /**
   * Parse PROCESS Glance intake from description.
   * Returns { glance, where, doneWhen, detail, rest } — rest = body when no ## sections.
   */
  function parseWorkOrderSections(desc) {
    const text = String(desc || "").replace(/\r\n/g, "\n").trim();
    const empty = { glance: "", where: "", doneWhen: "", detail: "", rest: "" };
    if (!text) return empty;
    if (!/^##\s+/m.test(text)) {
      return { glance: "", where: "", doneWhen: "", detail: "", rest: text };
    }
    const parts = text.split(/^##\s+/m);
    const out = { glance: "", where: "", doneWhen: "", detail: "", rest: "" };
    const other = [];
    for (let i = 0; i < parts.length; i++) {
      const chunk = parts[i];
      if (!chunk || !chunk.trim()) continue;
      const nl = chunk.indexOf("\n");
      const title = (nl === -1 ? chunk : chunk.slice(0, nl)).trim().toLowerCase();
      const body = (nl === -1 ? "" : chunk.slice(nl + 1)).trim();
      if (title === "glance") out.glance = body;
      else if (title === "where" || title === "location" || title === "surface")
        out.where = body;
      else if (title === "done when" || title === "donewhen") out.doneWhen = body;
      else if (title === "detail" || title === "details") out.detail = body;
      else other.push("## " + (nl === -1 ? chunk : chunk.slice(0, nl)).trim() +
        (body ? "\n" + body : ""));
    }
    if (other.length) out.rest = other.join("\n\n");
    return out;
  }

  /**
   * Parse ## Where lines into {kind, value, label}.
   * kind: path | url | note
   */
  function parseWhereLines(whereBody) {
    const lines = String(whereBody || "").replace(/\r\n/g, "\n").split("\n");
    const items = [];
    for (let i = 0; i < lines.length; i++) {
      let s = lines[i]
        .replace(/^\s*[-*+]\s+/, "")
        .replace(/^\s*\d+\.\s+/, "")
        .trim();
      if (!s) continue;
      const md = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(s);
      if (md) {
        const href = String(md[2] || "").trim();
        const lab = String(md[1] || href).trim();
        if (/^https?:\/\//i.test(href)) {
          items.push({ kind: "url", value: href, label: lab });
        } else {
          items.push({
            kind: "path",
            value: href.replace(/^\.\//, "").replace(/^\/+/, ""),
            label: lab,
          });
        }
        continue;
      }
      if (/^https?:\/\//i.test(s)) {
        let host = s;
        try {
          host = new URL(s).hostname + new URL(s).pathname.slice(0, 28);
        } catch (eU) {}
        items.push({ kind: "url", value: s, label: host });
        continue;
      }
      s = s.replace(/^`+|`+$/g, "").trim();
      /* city-relative path or project leaf */
      if (
        /^[A-Za-z0-9_./@+-]+$/.test(s) &&
        (s.indexOf("/") >= 0 ||
          /\.(md|py|js|html?|tsx?|css|json|sql|sh|rhai)$/i.test(s) ||
          /^[A-Za-z0-9_-]+$/.test(s))
      ) {
        items.push({
          kind: "path",
          value: s.replace(/^\.\//, "").replace(/^\/+/, ""),
          label: s,
        });
        continue;
      }
      items.push({ kind: "note", value: s, label: s });
    }
    return items;
  }

  /**
   * Resolve pivot targets for a work order.
   * Always has mapSlug/product when known; paths/urls from ## Where or body hints.
   */
  function resolveWhere(task) {
    const product = productSlug(task);
    const sec = parseWorkOrderSections(task.description || "");
    const fromSec = parseWhereLines(sec.where);
    const paths = [];
    const urls = [];
    const notes = [];
    for (let i = 0; i < fromSec.length; i++) {
      const it = fromSec[i];
      if (it.kind === "path") paths.push(it);
      else if (it.kind === "url") urls.push(it);
      else notes.push(it);
    }
    /* Fallback: backtick paths in description when ## Where empty */
    if (!paths.length) {
      const desc = String(task.description || "");
      const re =
        /`([A-Za-z0-9_./-]+\.(?:md|py|js|html?|tsx?|css|json|sql))`/g;
      let m;
      const seen = {};
      while ((m = re.exec(desc)) && paths.length < 4) {
        const v = m[1];
        if (seen[v]) continue;
        seen[v] = 1;
        paths.push({ kind: "path", value: v, label: v });
      }
    }
    let mapSlug = product || "";
    if (paths.length) {
      const fromPath = mapSlugFromPath(paths[0].value);
      /* Project-relative WHERE (docs/design/…) is not a Map folder. */
      if (fromPath && isMapProjectSlug(fromPath)) mapSlug = fromPath;
    }
    if (!mapSlug && product) mapSlug = product;
    /* Finder / open: prefer first concrete path, else project root slug */
    let finderPath = "";
    if (paths.length) finderPath = paths[0].value;
    else if (mapSlug) finderPath = mapSlug;
    const papers = paths.filter(function (p) {
      return /\.md$/i.test(p.value);
    });
    const targetLabel =
      (paths.length
        ? paths
            .slice(0, 2)
            .map(function (p) {
              return p.label;
            })
            .join(" · ")
        : "") ||
      (notes.length ? notes[0].label : "") ||
      mapSlug ||
      product ||
      "—";
    return {
      product: product,
      mapSlug: mapSlug,
      finderPath: finderPath,
      paths: paths,
      urls: urls,
      papers: papers,
      notes: notes,
      targetLabel: targetLabel,
    };
  }

  function isWorkspaceMapHere() {
    try {
      const path = String(
        (global.location && global.location.pathname) || ""
      );
      if (
        window.SuiteNav &&
        typeof SuiteNav.isWorkspaceMapPath === "function"
      ) {
        return !!SuiteNav.isWorkspaceMapPath(path);
      }
      return (
        path === "/workspace-map" ||
        path.indexOf("/workspace-map") === 0
      );
    } catch (e) {
      return false;
    }
  }

  function workspaceMapProjectHref(slug, paperPath) {
    const s = String(slug || "").trim();
    let base = "/workspace-map";
    try {
      if (
        window.SuiteNav &&
        typeof SuiteNav.workspaceMapHref === "function"
      ) {
        base = SuiteNav.workspaceMapHref() || base;
      }
    } catch (e) {}
    let href = base + "?project=" + encodeURIComponent(s);
    const paper = String(paperPath || "").trim();
    if (paper) href += "&paper=" + encodeURIComponent(paper);
    return href;
  }

  function goWhereMap(slug, paperPath) {
    const s = String(slug || "").trim();
    if (!s) return;
    const paper = String(paperPath || "").trim();
    /* Prefer live Map hook (in-place dig-in) when the room provides it. */
    try {
      if (
        window.SuiteMap &&
        typeof SuiteMap.focusProject === "function"
      ) {
        SuiteMap.focusProject(s, paper || "");
        return;
      }
    } catch (eMap) {}
    if (isWorkspaceMapHere()) {
      let handled = false;
      try {
        document.dispatchEvent(
          new CustomEvent("suite-where-map", {
            detail: { slug: s, path: paper },
            cancelable: true,
          })
        );
        handled = true;
      } catch (eEv) {}
      /* Same-document deep link so ?project= dig-in still runs if no listener */
      try {
        const u = new URL(global.location.href);
        u.searchParams.set("project", s);
        history.replaceState({}, "", u.pathname + u.search + u.hash);
        if (!handled) {
          global.location.href = workspaceMapProjectHref(s, paper);
        }
      } catch (eHist) {
        global.location.href = workspaceMapProjectHref(s, paper);
      }
      return;
    }
    const href = workspaceMapProjectHref(s, paper);
    try {
      if (
        window.SuiteNav &&
        typeof SuiteNav.softNavTo === "function"
      ) {
        SuiteNav.softNavTo(href);
        return;
      }
    } catch (eNav) {}
    global.location.href = href;
  }

  function renderWhereHtml(task) {
    const w = resolveWhere(task);
    if (!w.mapSlug && !w.finderPath && !w.urls.length && !w.paths.length) {
      return "";
    }
    const actions = [];
    if (w.mapSlug) {
      const paperHint =
        w.papers.length > 0 ? w.papers[0].value : "";
      actions.push(
        '<button type="button" class="suite-ticket-where-btn" data-where-map="' +
          esc(w.mapSlug) +
          '"' +
          (paperHint
            ? ' data-where-path="' + esc(paperHint) + '"'
            : "") +
          ">On Map</button>"
      );
    }
    /* pc-1209: WHERE paths are usually project-relative — stamp the project
     * so open/probe calls can fall back to <project-folder>/<path>. */
    const projAttr = w.product
      ? ' data-where-project="' + esc(w.product) + '"'
      : "";
    if (w.finderPath) {
      actions.push(
        '<button type="button" class="suite-ticket-where-btn" data-open-path="' +
          esc(w.finderPath) +
          '"' +
          projAttr +
          ">Finder</button>"
      );
    }
    for (let i = 0; i < Math.min(w.papers.length, 2); i++) {
      const p = w.papers[i];
      const short =
        p.label.length > 28
          ? p.label.replace(/^.*\//, "").slice(0, 28)
          : p.label;
      actions.push(
        '<button type="button" class="suite-ticket-where-btn" data-where-paper="' +
          esc(p.value) +
          '"' +
          projAttr +
          ">" +
          esc(short) +
          "</button>"
      );
    }
    /* Non-md path: still open in Finder via extra chip if different from primary */
    for (let j = 0; j < Math.min(w.paths.length, 2); j++) {
      const p = w.paths[j];
      if (/\.md$/i.test(p.value)) continue;
      if (p.value === w.finderPath && w.mapSlug) continue;
      const short =
        p.label.length > 24
          ? p.label.replace(/^.*\//, "").slice(0, 24)
          : p.label;
      actions.push(
        '<button type="button" class="suite-ticket-where-btn" data-open-path="' +
          esc(p.value) +
          '"' +
          projAttr +
          ' title="' +
          esc(p.value) +
          '">' +
          esc(short) +
          "</button>"
      );
    }
    for (let u = 0; u < Math.min(w.urls.length, 2); u++) {
      const link = w.urls[u];
      actions.push(
        '<a class="suite-ticket-where-btn suite-ticket-where-link" href="' +
          esc(link.value) +
          '" target="_blank" rel="noopener">' +
          esc(link.label.length > 22 ? link.label.slice(0, 22) + "…" : link.label) +
          "</a>"
      );
    }
    if (!actions.length) return "";
    return (
      '<div class="suite-ticket-where">' +
      '<div class="suite-ticket-where-label">Where</div>' +
      '<div class="suite-ticket-where-target">' +
      esc(w.targetLabel) +
      "</div>" +
      '<div class="suite-ticket-where-actions">' +
      actions.join("") +
      "</div></div>"
    );
  }

  /**
   * Wire relative .md links (data-paper-link) after renderMd HTML is injected.
   * Lazy on-click: probe /api/file; if 404 replace with dead span instead of navigating.
   */
  function wireRelativeLinks(container, project) {
    if (!container || !container.querySelectorAll) return;
    const proj = String(project || "");
    Array.prototype.forEach.call(
      container.querySelectorAll("a[data-paper-link]"),
      function (a) {
        if (a._paperLinkWired) return;
        a._paperLinkWired = true;
        a.addEventListener("click", function (e) {
          if (
            e.defaultPrevented ||
            e.metaKey ||
            e.ctrlKey ||
            e.shiftKey ||
            e.altKey ||
            e.button !== 0
          )
            return;
          var path = a.getAttribute("data-paper-link");
          if (!path) return;
          e.preventDefault();
          fetch(
            "/api/file?path=" +
              encodeURIComponent(path) +
              (proj ? "&project=" + encodeURIComponent(proj) : ""),
            { credentials: "same-origin", cache: "no-store" }
          )
            .then(function (r) {
              if (r.ok) {
                /* Open the canonical resolved path (post project fallback) */
                return r
                  .json()
                  .catch(function () {
                    return null;
                  })
                  .then(function (d) {
                    var canon = (d && d.path) || path;
                    if (root && !root.hidden) {
                      openItem({ type: "paper", id: canon, project: proj });
                    } else {
                      window.location.href =
                        "/read?path=" + encodeURIComponent(canon);
                    }
                  });
              } else {
                var sp = document.createElement("span");
                sp.className = "suite-paper-link-dead";
                sp.title = path + " — not found in workspace";
                sp.textContent = a.textContent;
                if (a.parentNode) a.parentNode.replaceChild(sp, a);
              }
            })
            .catch(function () {
              window.location.href =
                "/read?path=" + encodeURIComponent(path);
            });
        });
      }
    );
  }

  /** Wire Where buttons after HTML is injected into a container. */
  function wireWhereActions(scope) {
    const root = scope || document;
    const nodes = root.querySelectorAll
      ? root.querySelectorAll(
          "[data-where-map], [data-where-paper], [data-open-path]"
        )
      : [];
    Array.prototype.forEach.call(nodes, function (el) {
      if (el._whereWired) return;
      el._whereWired = true;
      if (el.hasAttribute("data-where-map")) {
        el.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          goWhereMap(
            el.getAttribute("data-where-map"),
            el.getAttribute("data-where-path") || ""
          );
        });
        return;
      }
      if (el.hasAttribute("data-where-paper")) {
        el.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          const path = el.getAttribute("data-where-paper");
          if (!path) return;
          const proj = el.getAttribute("data-where-project") || "";
          if (typeof open === "function") open(path, proj);
          else if (global.SuitePaper && SuitePaper.open)
            global.SuitePaper.open(path, proj);
        });
        return;
      }
      if (el.hasAttribute("data-open-path")) {
        el.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          const p = el.getAttribute("data-open-path");
          const proj = el.getAttribute("data-where-project") || "";
          try {
            if (
              window.SuiteNav &&
              typeof SuiteNav.openInFinder === "function"
            ) {
              SuiteNav.openInFinder(p == null ? "" : p, proj).catch(
                function (err) {
                  console.warn("openInFinder", err);
                }
              );
              return;
            }
          } catch (eF) {}
          fetch("/api/open", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: p || "", project: proj || "" }),
          }).catch(function () {});
        });
      }
    });
  }

  /** Hide engine-noise labels; keep a short human-readable set. */
  function citizenLabels(labels) {
    const arr = Array.isArray(labels) ? labels : [];
    const hide = /^(product:|gate_type:|blocks:|parent:|area:|sys:|size:|needs:)/i;
    const out = [];
    for (let i = 0; i < arr.length; i++) {
      const L = String(arr[i] || "").trim();
      if (!L || hide.test(L)) continue;
      if (/^worker:(you|founder|founder-terminal)$/i.test(L)) continue;
      if (/^worker:/i.test(L)) {
        out.push(L.replace(/^worker:/i, "hand "));
        continue;
      }
      out.push(L);
    }
    return out;
  }

  /** First worker:* hand id (citizen: hand name). */
  function ticketHandLabel(labels) {
    const arr = Array.isArray(labels) ? labels : [];
    for (let i = 0; i < arr.length; i++) {
      const L = String(arr[i] || "").trim();
      const m = /^worker:(.+)$/i.exec(L);
      if (!m) continue;
      const id = String(m[1] || "").trim();
      if (!id) continue;
      if (/^(you|founder|founder-terminal)$/i.test(id)) return "You";
      return id;
    }
    return "";
  }

  /**
   * Dual-read deferred (Map parity, pc-547 / wl-257 / pc-1084).
   * Canonical predicate: WoBuckets.isDeferredGate — no local marker list.
   */
  function isDeferredGateNote(gateType, gateNote) {
    if (
      global.WoBuckets &&
      typeof global.WoBuckets.isDeferredGate === "function"
    ) {
      return global.WoBuckets.isDeferredGate(gateType, gateNote);
    }
    /* Failsafe if wo-buckets.js failed to load */
    const gt = String(gateType || "")
      .toLowerCase()
      .trim();
    return gt === "deferred";
  }

  /**
   * Map-facing dispatch face for one work order (same register as dig KPI doors).
   * Returns { id, label, kind } — kind drives chip CSS.
   * pc-1084: deferred dual-read before human For You (ice parks must not gold).
   */
  function ticketDispatchFace(t) {
    t = t || {};
    const st = String(t.status || "")
      .toLowerCase()
      .replace(/\s+/g, "_");
    const gt = String(t.gate_type || t.gateType || "").toLowerCase();
    const note = t.gate_note != null ? t.gate_note : t.gateNote;
    if (st === "done") return { id: "done", label: "Done", kind: "done" };
    if (st === "canceled" || st === "cancelled")
      return { id: "canceled", label: "Canceled", kind: "muted" };
    if (st === "in_progress")
      return { id: "in_progress", label: "In progress", kind: "live" };
    if (st === "in_review")
      return { id: "in_review", label: "In review", kind: "muted" };
    /* Ice before For You — human + deferred: note is park, not gold */
    if (gt === "deferred" || isDeferredGateNote(gt, note))
      return { id: "deferred", label: "Deferred", kind: "deferred" };
    if (gt === "human")
      return { id: "for_you", label: "For You", kind: "you" };
    if (gt === "timer") return { id: "timed", label: "Timed", kind: "muted" };
    /* Ungated backlog = ready (claimable) — subset of live open on Map */
    if (st === "backlog" || !st)
      return { id: "ready", label: "Ready", kind: "ready" };
    return {
      id: "open",
      label: st.replace(/_/g, " ") || "Open",
      kind: "muted",
    };
  }

  /**
   * Place pulse one-liner when Map is live (MapPlaceState.exportSlug).
   * Matches dig: live · deferred · ready · for you · work signal · presence.
   */
  function placeContextHtml(product) {
    const slug = String(product || "")
      .toLowerCase()
      .trim();
    if (!slug) return "";
    let ex = null;
    try {
      if (
        global.MapPlaceState &&
        typeof global.MapPlaceState.exportSlug === "function"
      ) {
        ex = global.MapPlaceState.exportSlug(slug);
      }
    } catch (eEx) {
      ex = null;
    }
    if (!ex || !ex.wo) return "";
    const wo = ex.wo || {};
    const bits = [];
    bits.push("live " + (wo.liveOpen | 0));
    bits.push("deferred " + (wo.deferred | 0));
    bits.push("ready " + (wo.ready | 0));
    bits.push("for you " + (wo.forYou | 0));
    const workLab =
      (ex.work && ex.work.label) ||
      (wo.liveOpen === 0 && (wo.deferred | 0) > 0 ? "Starved" : "");
    const presLab = (ex.presence && ex.presence.label) || "";
    const title = String(ex.title || ex.id || slug).trim() || slug;
    /* pc-1135: count sentence ends at for-you; signal/presence labels rendered by dig KPIs */
    const line = title + " place · " + bits.join(" · ");
    return (
      '<div class="suite-ticket-place" data-place-slug="' +
      esc(slug) +
      '" title="Same counts as project dig place pulse">' +
      '<div class="suite-ticket-place-label">Place</div>' +
      '<div class="suite-ticket-place-body">' +
      esc(line) +
      "</div></div>"
    );
  }

  /**
   * Product slug → on-disk project folder under city root (BP boundaries).
   * Ticket product is lower-case; disk may be tradeOS / ProtocolCity / …
   */
  function productFolderName(slug) {
    const s = String(slug || "")
      .toLowerCase()
      .replace(/^product:/, "");
    const map = {
      tradeos: "tradeOS",
      protocolcity: "ProtocolCity",
      worklane: "worklane",
      ticketingprotocol: "worklane",
      workforce: "workforce",
      "oneseo-pos": "oneseo-pos",
      connector: "connector",
      gridfinity: "gridfinity",
      socials: "socials",
      career: "career",
      recipes: "recipes",
      presentations: "presentations",
    };
    return map[s] || (s ? s : "");
  }

  /** True if text looks like a city report path (md/html under reports). */
  function looksLikeReportPathBlob(text) {
    const s = String(text || "");
    if (/local\/reports\/[^\s`]+\.(?:md|html|json)/i.test(s)) return true;
    if (/(?:^|[\s`])[A-Za-z0-9_.-]+\/local\/reports\//i.test(s)) return true;
    if (/\*\*(?:Report|Visual):\*\*/i.test(s)) return true;
    return false;
  }

  /** Inbox report drops (Map For You) — not implement work orders. */
  function isInboxReport(t) {
    t = t || {};
    const labs = (t.labels || []).map(function (x) {
      return String(x || "").toLowerCase();
    });
    if (
      labs.some(function (l) {
        return l === "inbox-report" || l.indexOf("inbox-report:") === 0;
      })
    )
      return true;
    const title = String(t.title || "");
    if (/^Inbox\s*[·•\-–]/i.test(title)) return true;
    const hasReport = labs.indexOf("report") >= 0;
    const forYouSeat =
      labs.indexOf("you:todo") >= 0 ||
      labs.indexOf("you:host") >= 0 ||
      labs.indexOf("for-you") >= 0;
    if (hasReport && forYouSeat) return true;
    /* FOUNDER read packs + human-gated report drops with disk paths */
    if (
      hasReport &&
      looksLikeReportPathBlob(t.description) &&
      (String(t.gate_type || t.gateType || "").toLowerCase() === "human" ||
        /^FOUNDER\s*[·•\-–]/i.test(title))
    )
      return true;
    if (
      /^FOUNDER\s*[·•\-–]/i.test(title) &&
      looksLikeReportPathBlob(t.description)
    )
      return true;
    return false;
  }

  function reportKindFromTicket(t) {
    const labs = (t.labels || []).map(function (x) {
      return String(x || "").toLowerCase();
    });
    let key = "";
    for (let i = 0; i < labs.length; i++) {
      const m = /^inbox-report:[^:]+:([^:]+):/.exec(labs[i]);
      if (m) {
        key = m[1];
        break;
      }
    }
    /* Labels first (truth) — do not let optional RSU path mislabel a desk brief */
    if (
      labs.indexOf("desk-brief") >= 0 ||
      labs.indexOf("maru") >= 0 ||
      key === "desk-brief" ||
      key === "maru"
    )
      return { key: "desk-brief", label: "Desk brief" };
    if (labs.indexOf("rsu") >= 0 || key === "decision" || key === "rsu")
      return { key: "decision", label: "Decision pack" };
    if (labs.indexOf("efficiency") >= 0 || key === "efficiency")
      return { key: "efficiency", label: "Efficiency" };
    if (labs.indexOf("correspondent") >= 0 || key === "correspondent")
      return { key: "correspondent", label: "Correspondent" };
    if (
      labs.indexOf("glance") >= 0 ||
      key === "glance" ||
      key === "for-you-glance"
    )
      return { key: "glance", label: "Glance" };
    if (labs.indexOf("digest") >= 0 || key === "digest")
      return { key: "digest", label: "Digest" };
    if (
      labs.indexOf("board") >= 0 ||
      key === "board" ||
      key === "board-validation"
    )
      return { key: "board", label: "Board" };

    const title = String(t.title || "").toLowerCase();
    if (/desk.?brief|maru/.test(title))
      return { key: key || "desk-brief", label: "Desk brief" };
    if (/rsu|vest|decision.?pack|read pack/.test(title))
      return { key: key || "decision", label: "Decision pack" };
    if (/efficiency/.test(title))
      return { key: key || "efficiency", label: "Efficiency" };
    if (/correspondent/.test(title))
      return { key: key || "correspondent", label: "Correspondent" };
    if (/glance|for you pack/.test(title))
      return { key: key || "glance", label: "Glance" };
    if (/digest/.test(title))
      return { key: key || "digest", label: "Digest" };
    if (/board.?validation/.test(title))
      return { key: key || "board", label: "Board" };
    if (key)
      return {
        key: key,
        label: key
          .replace(/-/g, " ")
          .replace(/\b\w/g, function (c) {
            return c.toUpperCase();
          }),
      };
    return { key: "report", label: "Report" };
  }

  function reportDisplayTitle(t) {
    let s = String((t && t.title) || "").trim();
    s = s.replace(/^Inbox\s*[·•\-–]\s*/i, "");
    s = s.replace(/^FOUNDER\s*[·•\-–]\s*/i, "");
    s = s.replace(/^Report\s*[·•\-–]\s*/i, "");
    return s || "Report";
  }

  function normalizeReportPath(p) {
    let s = String(p || "").trim();
    if (!s) return "";
    s = s.replace(/^['"`]+|['"`]+$/g, "");
    s = s.replace(/^\.\/+/, "");
    /* Drop trailing punctuation from prose lines */
    s = s.replace(/[.,;:)\]]+$/, "");
    /* Ignore placeholder none markers */
    if (/^\(none\)$/i.test(s) || s === "—") return "";
    return s;
  }

  /**
   * Truth: city-root-relative path for suite /api/city-asset and /read.
   * Accepts repo-rel ``local/reports/…`` and prefixes product folder.
   */
  function resolveCityReportPath(path, product) {
    let p = normalizeReportPath(path);
    if (!p) return "";
    p = p.replace(/^\/+/, "");
    /* Already city-rel: tradeOS/local/… or ProtocolCity/local/… */
    if (/^[A-Za-z0-9_.-]+\/local\//.test(p)) return p;
    if (/^local\//i.test(p)) {
      const folder = productFolderName(product);
      if (folder) return folder + "/" + p.replace(/^local\//i, "local/");
    }
    return p;
  }

  function reportPathIsHtml(p) {
    return /\.html?$/i.test(String(p || ""));
  }

  function reportPathIsMd(p) {
    return /\.md$/i.test(String(p || ""));
  }

  /** Citizen label for a report path button. */
  function reportPathLabel(p) {
    const base = String(p || "").split("/").pop() || p;
    const low = String(p || "").toLowerCase();
    if (
      /for-you\/(?:latest|.*glance)\.html$/.test(low) ||
      /glance\.html$/.test(low)
    )
      return "Visual glance";
    if (/desk-brief/.test(low)) return "Desk brief";
    if (/rsu|vest/.test(low)) return "RSU pack";
    if (/board-validation|board_validation/.test(low)) return "Board validation";
    if (/efficiency/.test(low)) return "Efficiency";
    if (/digest/.test(low)) return "Digest";
    return base;
  }

  /**
   * Open target for a report path.
   * .md → SuitePaper /read · .html → raw city asset (full document paint).
   */
  function reportPathOpen(p, product) {
    const path = resolveCityReportPath(p, product);
    if (!path) return null;
    const html = reportPathIsHtml(path);
    const href = html
      ? "/api/city-asset?path=" +
        encodeURIComponent(path) +
        (product ? "&project=" + encodeURIComponent(product) : "")
      : "/read?path=" + encodeURIComponent(path);
    return {
      path: path,
      href: href,
      label: reportPathLabel(path),
      isHtml: html,
      isMd: reportPathIsMd(path),
      primary: html || /for-you\/(?:latest|.*glance)\.html$/i.test(path),
    };
  }

  /** Extract short glance bullets for cream strip / iframe fallback. */
  function reportGlanceBullets(desc) {
    const d = String(desc || "");
    let block = "";
    const m1 = d.match(
      /\*\*Glance bullets?:\*\*\s*\n([\s\S]*?)(?=\n\*\*[A-Za-z]|\n##\s|$)/i
    );
    if (m1) block = m1[1];
    if (!block) {
      const m2 = d.match(
        /##\s*Glance\s*\n([\s\S]*?)(?=\n##\s|\n#\s[^#]|$)/i
      );
      if (m2) block = m2[1];
    }
    if (!block) return [];
    const out = [];
    const lines = block.split("\n");
    for (let i = 0; i < lines.length; i++) {
      let line = String(lines[i] || "").trim();
      if (!line) continue;
      line = line.replace(/^[-*•]\s+/, "").replace(/^\d+\.\s+/, "");
      if (!line || line.length < 8) continue;
      if (/^`[^`]+`$/.test(line)) continue;
      out.push(line);
      if (out.length >= 6) break;
    }
    return out;
  }

  /**
   * Body for report dig-in: strip ticket scaffolding + path dumps.
   * Prefer ## Glance / Glance bullets prose only.
   */
  function reportBodyMarkdown(desc, paths) {
    let d = String(desc || "").trim();
    if (!d) return "";
    d = d.replace(
      /^BluePrint\s+\*\*For You\*\*\s+inbox item[^\n]*\n+/gim,
      ""
    );
    d = d.replace(/^BluePrint For You inbox item[^\n]*\n+/gim, "");
    d = d.replace(/^## How to use[\s\S]*?(?=\n## |\n# |$)/gim, "");
    d = d.replace(/^_Label `[^`]+`[^\n]*_\n*/gim, "");
    /* Whole Paths (open these) blocks — CTAs own those */
    d = d.replace(
      /\*\*Paths(?:\s*\([^)]*\))?:\*\*[\s\S]*?(?=\n\*\*[A-Za-z]|\n##\s|$)/gi,
      ""
    );
    d = d.replace(
      /^Open these[^\n]*\n(?:(?:\d+\.|[-*])[^\n]*\n(?:[ \t]+[^\n]+\n)*)+/gim,
      ""
    );
    d = d.replace(/^\*\*Report:\*\*[^\n]*\n+/gim, "");
    d = d.replace(/^\*\*Visual:\*\*[^\n]*\n+/gim, "");
    d = d.replace(/^\*\*Date:\*\*[^\n]*\n+/gim, "");
    /* Prefer Glance bullets / ## Glance as the body */
    const bullets = reportGlanceBullets(desc);
    if (bullets.length) {
      return (
        "### At a glance\n\n" +
        bullets
          .map(function (b) {
            return "- " + b;
          })
          .join("\n")
      );
    }
    const glanceM = d.match(
      /##\s*Glance\s*\n([\s\S]*?)(?=\n##\s|\n#\s[^#]|$)/i
    );
    if (glanceM && String(glanceM[1] || "").trim().length > 40) {
      return String(glanceM[1]).trim();
    }
    d = d.replace(/^#\s+[^\n]+\n+/, "");
    d = d.replace(/^##\s*Glance\s*\n+/im, "");
    d = d.replace(/\*\*What clears this gate:\*\*[\s\S]*$/i, "");
    d = d.replace(/\*\*Not required:\*\*[\s\S]*$/i, "");
    if (paths && paths.length) {
      for (let i = 0; i < paths.length; i++) {
        const leaf = String(paths[i]).split("/").pop() || paths[i];
        d = d.replace(
          new RegExp(
            "`" +
              String(paths[i]).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
              "`",
            "g"
          ),
          ""
        );
        d = d.replace(
          new RegExp(
            "`[^`]*" +
              String(leaf).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
              "`",
            "g"
          ),
          ""
        );
      }
    }
    d = d.replace(/\n{3,}/g, "\n\n").trim();
    return d;
  }

  function reportPathsFromTicket(t) {
    const product = productSlug(t);
    const paths = [];
    const seen = {};
    const desc = String((t && t.description) || "");
    function push(raw) {
      const resolved = resolveCityReportPath(raw, product);
      if (!resolved) return;
      if (!/\.(?:md|html?|json)$/i.test(resolved)) return;
      const key = resolved.toLowerCase();
      if (seen[key]) return;
      seen[key] = true;
      paths.push(resolved);
    }
    const re = /(?:\*\*Report:\*\*|\*\*Visual:\*\*|Path:)\s*`([^`]+)`/gi;
    let m;
    while ((m = re.exec(desc))) push(m[1]);
    const re2 = /`([^`]+\.(?:md|html?|json))`/gi;
    while ((m = re2.exec(desc))) push(m[1]);
    const re3 =
      /(?:^|[\s(])((?:[A-Za-z0-9_.-]+\/)+local\/reports\/[^\s`"'<>]+\.(?:md|html?|json))/gim;
    while ((m = re3.exec(desc))) push(m[1]);
    const re4 =
      /(?:^|[\s(])(local\/reports\/[^\s`"'<>]+\.(?:md|html?|json))/gim;
    while ((m = re4.exec(desc))) push(m[1]);

    /* Dedupe dated glance vs latest.html (same visual) */
    const hasLatest = paths.some(function (p) {
      return /for-you\/latest\.html$/i.test(p);
    });
    let out = paths;
    if (hasLatest) {
      out = paths.filter(function (p) {
        return !/for-you\/.+-glance\.html$/i.test(p);
      });
    }
    /* HTML first (prefer latest), then md */
    out.sort(function (a, b) {
      const ah = reportPathIsHtml(a) ? 0 : 1;
      const bh = reportPathIsHtml(b) ? 0 : 1;
      if (ah !== bh) return ah - bh;
      const ap = /latest\.html$/i.test(a)
        ? 0
        : /glance\.html$/i.test(a)
          ? 1
          : 2;
      const bp = /latest\.html$/i.test(b)
        ? 0
        : /glance\.html$/i.test(b)
          ? 1
          : 2;
      if (ap !== bp) return ap - bp;
      return a.localeCompare(b);
    });
    return out.slice(0, 8);
  }

  /** Primary escape href for report dig-in (open report / full page chrome). */
  function reportEscapeForTicket(t) {
    const product = productSlug(t);
    const paths = reportPathsFromTicket(t);
    if (!paths.length) return null;
    return reportPathOpen(paths[0], product);
  }

  /** Blob URLs for report glance iframes — revoke on close (pc-886). */
  let reportBlobUrls = [];

  function revokeReportBlobs() {
    for (let i = 0; i < reportBlobUrls.length; i++) {
      try {
        URL.revokeObjectURL(reportBlobUrls[i]);
      } catch (eR) {}
    }
    reportBlobUrls = [];
  }

  /**
   * Resolved suite appearance for report theming (pc-887).
   * Manual light/dark on <html data-theme>; system → prefers-color-scheme.
   */
  function suiteResolvedTheme() {
    try {
      const root = document.documentElement;
      if (root) {
        const attr = root.getAttribute("data-theme");
        if (attr === "light" || attr === "dark") return attr;
      }
    } catch (eT) {}
    try {
      if (
        global.matchMedia &&
        global.matchMedia("(prefers-color-scheme: dark)").matches
      ) {
        return "dark";
      }
    } catch (eM) {}
    return "light";
  }

  /**
   * Map common report CSS vars onto suite glass tokens (pc-887).
   * Generators may still bake a dark skin; dig-in frame re-skins without
   * re-authoring every drop.
   */
  function reportThemeOverrideCss(theme) {
    const dark = theme === "dark";
    /* Values mirror suite.css :root / [data-theme=dark] paper tokens. */
    const v = dark
      ? {
          bg: "#161410",
          bg2: "#1f1c16",
          bg3: "#2a251c",
          border: "#4a453c",
          text: "#f0e8d8",
          dim: "#a89f90",
          accent: "#5ecf8a",
          accent2: "#5a9a88",
          warn: "#e9c46a",
          danger: "#e07060",
          blue: "#64b5f6",
          scheme: "dark",
          pillPaper: "#3a5060",
          pillLive: "#5a3030",
        }
      : {
          bg: "#faf6ec",
          bg2: "#fffdf8",
          bg3: "#efe8d5",
          border: "#c4b8a4",
          text: "#2a241c",
          dim: "#6b6154",
          accent: "#2e7d4f",
          accent2: "#3d7a6a",
          warn: "#a33327",
          danger: "#a33327",
          blue: "#2a5a8a",
          scheme: "light",
          pillPaper: "#a8c4d8",
          pillLive: "#c4a0a0",
        };
    return (
      ":root{" +
      "--bg:" +
      v.bg +
      ";--bg2:" +
      v.bg2 +
      ";--bg3:" +
      v.bg3 +
      ";--border:" +
      v.border +
      ";--text:" +
      v.text +
      ";--dim:" +
      v.dim +
      ";--accent:" +
      v.accent +
      ";--accent2:" +
      v.accent2 +
      ";--warn:" +
      v.warn +
      ";--danger:" +
      v.danger +
      ";--blue:" +
      v.blue +
      ";color-scheme:" +
      v.scheme +
      ";}" +
      "html,body{background:var(--bg)!important;color:var(--text)!important;}" +
      ".pill.paper{border-color:" +
      v.pillPaper +
      ";}" +
      ".pill.live{border-color:" +
      v.pillLive +
      ";}"
    );
  }

  /** Inject/replace #suite-report-theme block so report vars follow suite. */
  function injectReportTheme(html, theme) {
    theme = theme === "dark" ? "dark" : "light";
    let src = String(html || "");
    src = src.replace(
      /<style\b[^>]*\bid=["']suite-report-theme["'][^>]*>[\s\S]*?<\/style>/gi,
      ""
    );
    const block =
      '<style id="suite-report-theme" data-suite-theme="' +
      theme +
      '">' +
      reportThemeOverrideCss(theme) +
      "</style>";
    if (/<\/head>/i.test(src)) {
      return src.replace(/<\/head>/i, block + "</head>");
    }
    if (/<html\b[^>]*>/i.test(src)) {
      return src.replace(/<html\b[^>]*>/i, function (m) {
        return m + block;
      });
    }
    if (/<body\b[^>]*>/i.test(src)) {
      return src.replace(/<body\b[^>]*>/i, function (m) {
        return m + block;
      });
    }
    return block + src;
  }

  /**
   * Paint themed HTML into the dig-in iframe (blob). Keeps raw source on the
   * wrap so Settings light↔dark can re-skin without re-fetch (pc-887).
   */
  function paintReportFrameBlob(wrap, rawHtml) {
    const frame = wrap.querySelector(".suite-ticket-report-frame");
    if (!frame || rawHtml == null) return null;
    const theme = suiteResolvedTheme();
    wrap.setAttribute("data-report-theme", theme);
    const themed = injectReportTheme(rawHtml, theme);
    const blob = new Blob([themed], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    if (wrap._reportBlobUrl) {
      try {
        URL.revokeObjectURL(wrap._reportBlobUrl);
      } catch (eRev) {}
      const ix = reportBlobUrls.indexOf(wrap._reportBlobUrl);
      if (ix >= 0) reportBlobUrls.splice(ix, 1);
    }
    reportBlobUrls.push(url);
    wrap._reportBlobUrl = url;
    wrap._reportRawHtml = rawHtml;
    wrap._reportTheme = theme;
    frame.src = url;
    return url;
  }

  /** Re-skin already-loaded previews when suite theme flips. */
  function rethemeReadyReportFrames() {
    if (typeof document === "undefined") return;
    const theme = suiteResolvedTheme();
    const wraps = document.querySelectorAll
      ? document.querySelectorAll(".suite-ticket-report-frame-wrap.is-ready")
      : [];
    Array.prototype.forEach.call(wraps, function (wrap) {
      if (!wrap._reportRawHtml) return;
      if (wrap._reportTheme === theme) return;
      paintReportFrameBlob(wrap, wrap._reportRawHtml);
    });
  }

  function installReportThemeListener() {
    if (installReportThemeListener._done) return;
    installReportThemeListener._done = true;
    if (typeof document === "undefined") return;
    try {
      const mo = new MutationObserver(function () {
        rethemeReadyReportFrames();
      });
      mo.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    } catch (eMo) {}
    try {
      const mq =
        global.matchMedia &&
        global.matchMedia("(prefers-color-scheme: dark)");
      if (mq) {
        const onChange = function () {
          rethemeReadyReportFrames();
        };
        if (typeof mq.addEventListener === "function") {
          mq.addEventListener("change", onChange);
        } else if (typeof mq.addListener === "function") {
          mq.addListener(onChange);
        }
      }
    } catch (eMq) {}
    try {
      global.addEventListener("storage", function (ev) {
        if (ev && ev.key === "suite.theme") rethemeReadyReportFrames();
      });
    } catch (eSt) {}
  }

  /**
   * Load HTML glance into dig-in frame (fetch → themed blob). Never auto on
   * open — user opts in (pc-886 lag cycle: map cinema + iframe paint).
   * Theme: suite light/dark tokens injected into blob (pc-887).
   */
  function loadReportFrame(wrap) {
    if (!wrap || wrap._reportFrameLoading || wrap.classList.contains("is-ready"))
      return;
    const href = wrap.getAttribute("data-asset-href") || "";
    const path = wrap.getAttribute("data-report-path") || "";
    const frame = wrap.querySelector(".suite-ticket-report-frame");
    const status = wrap.querySelector(".suite-ticket-report-frame-status");
    const openA = wrap.querySelector(".suite-ticket-report-frame-open");
    const loadBtn = wrap.querySelector("[data-report-load-visual]");
    if (!href || !frame) return;
    wrap._reportFrameLoading = true;
    wrap.classList.remove("is-idle", "is-error");
    wrap.classList.add("is-loading");
    if (loadBtn) loadBtn.hidden = true;
    if (status) {
      status.hidden = false;
      status.textContent = "Loading visual…";
    }
    fetch(href, { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        const ct = (r.headers.get("content-type") || "").toLowerCase();
        return r.text().then(function (text) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          const trimmed = String(text || "").trim();
          if (
            ct.indexOf("json") >= 0 ||
            (trimmed.charAt(0) === "{" && /"error"\s*:/.test(trimmed))
          ) {
            throw new Error("not found");
          }
          if (!/<\s*html|<\s*body|<\s*div/i.test(trimmed)) {
            throw new Error("not html");
          }
          frame.onload = function () {
            wrap._reportFrameLoading = false;
            wrap.classList.remove("is-loading");
            wrap.classList.add("is-ready");
            if (status) status.hidden = true;
          };
          frame.hidden = false;
          const url = paintReportFrameBlob(wrap, text);
          if (openA) {
            /* Full-size uses themed blob when available; city-asset stays on primary CTA. */
            openA.href = url || href;
            openA.hidden = false;
          }
        });
      })
      .catch(function () {
        wrap._reportFrameLoading = false;
        wrap.classList.remove("is-loading");
        wrap.classList.add("is-error");
        if (frame) {
          frame.hidden = true;
          frame.removeAttribute("src");
        }
        if (status) {
          status.hidden = false;
          status.innerHTML =
            "Visual not found at <code>" +
            esc(path || href) +
            "</code> — use Open visual glance above (new tab).";
        }
        if (loadBtn) {
          loadBtn.hidden = false;
          loadBtn.textContent = "Retry preview";
        }
        if (openA) openA.hidden = true;
      });
  }

  /**
   * Wire report dig: auto-load HTML frames (data-auto-load) + optional manual.
   */
  function wireReportFrames(scope) {
    installReportThemeListener();
    const rootEl = scope || document;
    const wraps = rootEl.querySelectorAll
      ? rootEl.querySelectorAll(".suite-ticket-report-frame-wrap[data-asset-href]")
      : [];
    Array.prototype.forEach.call(wraps, function (wrap) {
      if (wrap._reportFrameWired) return;
      wrap._reportFrameWired = true;
      wrap.classList.add("is-idle");
      wrap.setAttribute("data-report-theme", suiteResolvedTheme());
      const loadBtn = wrap.querySelector("[data-report-load-visual]");
      if (loadBtn) {
        loadBtn.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          loadReportFrame(wrap);
        });
      }
      /* Auto-show HTML in dig — no second click for content (pc-894) */
      if (wrap.getAttribute("data-auto-load") === "1") {
        loadReportFrame(wrap);
      }
    });
  }

  /**
   * Fetch disk report into dig panel (MD → renderMd; HTML frames via loadReportFrame).
   * Ticket body is only an index — truth is the file on disk (pc-894).
   * @param {Element} scope
   * @param {object} [ticket] optional — fallback prose if file fetch fails
   */
  function hydrateReportInline(scope, ticket) {
    const rootEl = scope || document;
    if (!rootEl || !rootEl.querySelectorAll) return;
    const mounts = rootEl.querySelectorAll("[data-report-inline]");
    const t = ticket || null;
    Array.prototype.forEach.call(mounts, function (el) {
      if (el._reportInlineHydrated) return;
      el._reportInlineHydrated = true;
      const kind = String(el.getAttribute("data-report-inline") || "md");
      const path = String(el.getAttribute("data-report-path") || "").trim();
      const product = String(el.getAttribute("data-product") || "").trim();
      const status = el.querySelector(".suite-ticket-report-inline-status");
      const body = el.querySelector(".suite-ticket-report-full");
      if (!path) {
        if (status) {
          status.textContent = "No report path on this inbox card.";
          status.classList.add("is-error");
        }
        return;
      }
      if (kind === "html") {
        /* Frame wrap handles load via wireReportFrames */
        return;
      }
      let url = "/api/file?path=" + encodeURIComponent(path);
      if (product) {
        url += "&project=" + encodeURIComponent(product);
      }
      if (status) {
        status.hidden = false;
        status.textContent = "Loading report…";
      }
      fetch(url, { cache: "no-store", credentials: "same-origin" })
        .then(function (r) {
          return r.json().then(function (data) {
            if (!r.ok) {
              throw new Error(
                (data && (data.error || data.message)) || "HTTP " + r.status
              );
            }
            return data;
          });
        })
        .then(function (data) {
          const content = String(
            (data && data.content != null ? data.content : "") || ""
          );
          if (!content.trim()) {
            throw new Error("empty report");
          }
          if (body) {
            body.innerHTML = renderMd(content, path);
            wireRelativeLinks(body, product);
            body.hidden = false;
          }
          if (status) status.hidden = true;
          try {
            const src = document.getElementById("suite-paper-source");
            if (src && content.length > String(src.textContent || "").length) {
              src.textContent = content;
            }
          } catch (eSrc) {}
        })
        .catch(function (err) {
          let fb = "";
          if (t) {
            fb = reportBodyMarkdown(
              t.description || "",
              reportPathsFromTicket(t)
            );
            /* Ticket may paste full report under ## Glance — use raw desc strip */
            if (!fb || fb.length < 80) {
              fb = String(t.description || "")
                .replace(/^BluePrint\s+\*\*For You\*\*[^\n]*\n+/gim, "")
                .replace(/^\*\*Report:\*\*[^\n]*\n+/gim, "")
                .replace(/^\*\*Date:\*\*[^\n]*\n+/gim, "")
                .replace(/^## How to use[\s\S]*?(?=\n## |\n# |$)/gim, "")
                .replace(/\*\*What clears this gate:\*\*[\s\S]*$/i, "")
                .trim();
            }
          }
          if (fb && body) {
            body.innerHTML = renderMd(fb);
            body.hidden = false;
            if (status) {
              status.hidden = false;
              status.classList.remove("is-error");
              status.textContent =
                "Showing inbox copy (could not load file). Open in paper if needed.";
            }
            return;
          }
          if (status) {
            status.hidden = false;
            status.classList.add("is-error");
            status.innerHTML =
              "Could not load report at <code>" +
              esc(path) +
              "</code>" +
              (err && err.message ? " — " + esc(String(err.message)) : "") +
              ". Use Open in paper below.";
          }
        });
    });
  }

  /**
   * Report inbox dig-in — not a work-order face (pc-884 · pc-894).
   * Full report renders inline from disk; path links are secondary escape.
   */
  function renderReportHtml(t) {
    const product = productSlug(t);
    const kind = reportKindFromTicket(t);
    const paths = reportPathsFromTicket(t);
    const opens = paths
      .map(function (p) {
        return reportPathOpen(p, product);
      })
      .filter(Boolean);
    const mdOpen = opens.filter(function (o) {
      return o.isMd;
    })[0];
    const htmlOpen = opens.filter(function (o) {
      return o.isHtml;
    })[0];
    /* Prefer MD for inline prose; HTML for themed glance frames */
    const primaryFile = mdOpen || htmlOpen || opens[0];

    const chips = [];
    /* pc-950: Read face on For You paper pile — still one product name For You */
    chips.push(
      '<span class="suite-ticket-chip face-pill st-report" data-chip="face" title="For You · Read paper">Read</span>'
    );
    chips.push(
      '<span class="suite-ticket-chip suite-ticket-chip-kind" data-chip="kind">' +
        esc(kind.label) +
        "</span>"
    );
    if (product) {
      chips.push(
        '<span class="suite-ticket-chip" data-chip="project">' +
          esc(product) +
          "</span>"
      );
    }
    chips.push(
      '<span class="suite-ticket-chip suite-ticket-chip-muted" data-chip="hint" title="Read-only report — not implement work">' +
        "Mark read" +
        "</span>"
    );
    const statusHtml =
      '<div class="suite-ticket-status suite-ticket-status-strip" role="status">' +
      chips.join("") +
      "</div>";

    /* Secondary escapes only — content is inline (pc-894) */
    let pathHtml = "";
    if (opens.length) {
      pathHtml =
        '<div class="suite-ticket-report-paths suite-ticket-report-paths-secondary">' +
        '<div class="suite-ticket-where-label">Also open</div>' +
        '<div class="suite-ticket-report-secondary">' +
        opens
          .map(function (o) {
            const hard = o.isHtml
              ? ' data-hard-nav="1" target="_blank" rel="noopener"'
              : "";
            const lab = o.isMd
              ? "Open in paper"
              : o.isHtml
                ? "Full size (new tab)"
                : o.label;
            return (
              '<a class="suite-ticket-report-sec-link" href="' +
              esc(o.href) +
              '" data-report-path="' +
              esc(o.path) +
              '"' +
              hard +
              ' title="' +
              esc(o.path) +
              '">' +
              esc(lab) +
              "</a>"
            );
          })
          .join('<span class="suite-ticket-report-sec-sep">·</span>') +
        "</div>" +
        (primaryFile
          ? '<p class="suite-ticket-report-path-meta"><code>' +
            esc(primaryFile.path) +
            "</code></p>"
          : "") +
        "</div>";
    }

    /* Inline body — hydrated after mount */
    let inlineHtml = "";
    if (mdOpen) {
      inlineHtml =
        '<div class="suite-ticket-report-inline" data-report-inline="md" data-report-path="' +
        esc(mdOpen.path) +
        '" data-product="' +
        esc(product) +
        '">' +
        '<div class="suite-ticket-where-label">Report</div>' +
        '<p class="suite-ticket-report-inline-status">Loading report…</p>' +
        '<div class="md suite-ticket-report-full" hidden></div>' +
        "</div>";
    } else if (htmlOpen) {
      inlineHtml =
        '<div class="suite-ticket-report-inline" data-report-inline="html" data-report-path="' +
        esc(htmlOpen.path) +
        '" data-product="' +
        esc(product) +
        '">' +
        '<div class="suite-ticket-report-frame-wrap is-idle" data-auto-load="1" data-asset-href="' +
        esc(htmlOpen.href) +
        '" data-report-path="' +
        esc(htmlOpen.path) +
        '">' +
        '<div class="suite-ticket-where-label">Report</div>' +
        '<p class="suite-ticket-report-frame-status">Loading visual…</p>' +
        '<iframe class="suite-ticket-report-frame" title="Report" src="about:blank" hidden></iframe>' +
        '<a class="suite-ticket-report-frame-open" href="' +
        esc(htmlOpen.href) +
        '" data-hard-nav="1" target="_blank" rel="noopener" hidden>Open full size</a>' +
        "</div></div>";
    } else {
      /* No path — show whatever prose is on the card */
      const bodyMd = reportBodyMarkdown(t.description || "", paths);
      if (bodyMd) {
        inlineHtml =
          '<div class="md suite-ticket-report-body suite-ticket-report-full">' +
          renderMd(bodyMd) +
          "</div>";
      } else {
        inlineHtml =
          '<p class="suite-paper-muted">No report file on this card. Clear when read.</p>';
      }
    }

    const tid = String((t && t.id) || "").trim();
    const actionsHtml = tid
      ? '<div class="suite-ticket-report-inbox-actions" data-report-inbox-actions data-task-id="' +
        esc(tid) +
        '">' +
        '<button type="button" class="suite-ticket-report-act is-primary" data-report-act="read" title="Mark this inbox report read (done) and remove For You gold">' +
        "Mark read" +
        "</button>" +
        '<button type="button" class="suite-ticket-report-act" data-report-act="snooze1d" title="Hide For You gold for 1 day — does not clear the gate">' +
        "Snooze 1d" +
        "</button>" +
        '<span class="suite-ticket-report-act-status" data-report-act-status aria-live="polite"></span>' +
        "</div>"
      : "";

    const foot =
      "Mark read when done · not implement work" +
      (tid ? " · " + tid : "");
    return (
      '<div class="suite-ticket suite-ticket-report" data-face="report" data-report-kind="' +
      esc(kind.key) +
      '" data-product="' +
      esc(product) +
      '"' +
      (tid ? ' data-task-id="' + esc(tid) + '"' : "") +
      ">" +
      statusHtml +
      actionsHtml +
      inlineHtml +
      pathHtml +
      '<p class="suite-ticket-foot suite-ticket-report-foot">' +
      esc(foot) +
      "</p>" +
      "</div>"
    );
  }

  /**
   * Mark-read / snooze on report dig (pc-895). Report-class only.
   * Mark read → status done + close dig + refresh For You gold.
   */
  function wireReportInboxActions(scope, ticket) {
    const rootEl = scope || document;
    if (!rootEl || !rootEl.querySelector) return;
    const bar = rootEl.querySelector("[data-report-inbox-actions]");
    if (!bar || bar._reportActWired) return;
    bar._reportActWired = true;
    const tid = String(
      bar.getAttribute("data-task-id") || (ticket && ticket.id) || ""
    ).trim();
    if (!tid) return;
    if (ticket && !isInboxReport(ticket)) return;

    const statusEl = bar.querySelector("[data-report-act-status]");
    const setStatus = function (msg, isErr) {
      if (!statusEl) return;
      statusEl.textContent = msg || "";
      statusEl.classList.toggle("is-err", !!isErr);
    };
    const setBusy = function (on) {
      bar.querySelectorAll("button[data-report-act]").forEach(function (b) {
        b.disabled = !!on;
      });
    };
    const refreshForYou = function () {
      try {
        document.dispatchEvent(
          new CustomEvent("suite-for-you-refresh", {
            detail: { task_id: tid, source: "report-dig" },
          })
        );
      } catch (eEv) {}
    };

    bar.addEventListener("click", function (e) {
      const btn =
        e.target && e.target.closest && e.target.closest("[data-report-act]");
      if (!btn || !bar.contains(btn)) return;
      e.preventDefault();
      e.stopPropagation();
      const act = btn.getAttribute("data-report-act") || "";

      if (act === "read") {
        setBusy(true);
        setStatus("Marking read…", false);
        fetch("/api/task/" + encodeURIComponent(tid), {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ status: "done", author: "you" }),
          cache: "no-store",
          credentials: "same-origin",
        })
          .then(function (r) {
            return r.json().then(function (j) {
              return {
                ok: r.ok && !!(j && j.ok !== false),
                data: j,
              };
            });
          })
          .then(function (res) {
            if (!res || !res.ok) {
              setStatus(
                (res &&
                  res.data &&
                  (res.data.error || res.data.message || res.data.msg)) ||
                  "Could not mark read",
                true
              );
              setBusy(false);
              return;
            }
            setStatus("Marked read", false);
            refreshForYou();
            try {
              close();
            } catch (eCl) {}
          })
          .catch(function () {
            setStatus("Network error", true);
            setBusy(false);
          });
        return;
      }

      if (act === "snooze1d") {
        setBusy(true);
        setStatus("Snoozing…", false);
        fetch("/api/attention/snooze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            task_id: tid,
            until: "1d",
            reason: "Report dig snooze 1d",
          }),
          cache: "no-store",
          credentials: "same-origin",
        })
          .then(function (r) {
            return r.json().then(function (j) {
              return {
                ok: r.ok && !!(j && j.ok !== false),
                data: j,
              };
            });
          })
          .then(function (res) {
            if (!res || !res.ok) {
              setStatus(
                (res &&
                  res.data &&
                  (res.data.error || res.data.message || res.data.msg)) ||
                  "Snooze failed",
                true
              );
              setBusy(false);
              return;
            }
            setStatus("Snoozed 1 day · gold muted", false);
            setBusy(false);
            refreshForYou();
            try {
              close();
            } catch (eCl2) {}
          })
          .catch(function () {
            setStatus("Network error", true);
            setBusy(false);
          });
      }
    });
  }

  /** Build "Filed by You · Seat · {hand}" text for dual stamp (pc-929). */
  function buildDualStampText(t, hand) {
    const youFace = youFaceLabel();
    const rawAuthor = String((t && t.author) || "").trim();
    let filedBy = youFace;
    if (rawAuthor && !/^(you|founder|founder-terminal)$/i.test(rawAuthor)) {
      try {
        if (global.SuiteNav && typeof global.SuiteNav.displayAuthor === "function") {
          const mapped = global.SuiteNav.displayAuthor(rawAuthor);
          if (mapped) filedBy = mapped;
        } else {
          filedBy = rawAuthor;
        }
      } catch (eA) {}
    }
    if (!hand) return "Filed by " + filedBy + " · Seat · none — route a hand";
    return "Filed by " + filedBy + " · Seat · " + hand;
  }

  /**
   * Citizen work-order dig-in (2026-07-30 / pc-752 · pc-753; faces 2026-08):
   * Full body always open — no More/Detail folds. Where pivot above Glance.
   * Order: face badge · status strip · dual stamp · place · Where · gate note · Glance · …
   * Faces match Map dig KPI doors (Done / Ready / Deferred / For You / …).
   * Inbox reports use renderReportHtml (not this WO chrome).
   */
  function renderTicketHtml(t) {
    if (isInboxReport(t)) return renderReportHtml(t);
    const product = productSlug(t);
    const gt = String(t.gate_type || t.gateType || "").toLowerCase();
    const gateNote = String(
      t.gate_note != null
        ? t.gate_note
        : t.gateNote != null
          ? t.gateNote
          : ""
    ).trim();
    const face = ticketDispatchFace(t);
    const youFace = youFaceLabel();
    const sec = parseWorkOrderSections(t.description || "");
    const hand = ticketHandLabel(t.labels || []);
    /* pc-1084: use face (dual-read), not raw gate_type alone — human+deferred: is ice */
    const isHuman = face.id === "for_you";
    const isDeferred = face.id === "deferred";
    const isTimer = face.id === "timed" || (gt === "timer" && !isDeferred);

    /* Map slip-pill stamp classes — one paint system with left-rail tape */
    const faceStamp =
      face.id === "for_you"
        ? "st-you"
        : face.id === "deferred"
          ? "st-deferred"
          : face.id === "ready"
            ? "st-ready"
            : face.id === "in_progress"
              ? "st-live"
              : face.id === "done"
                ? "st-done"
                : face.id === "canceled"
                  ? "st-canceled"
                  : face.id === "in_review" || face.id === "timed"
                    ? "st-review"
                    : "st-open";

    /* Status strip only (no double face badge) — Map register chips */
    const chips = [];
    chips.push(
      '<span class="suite-ticket-chip face-pill ' +
        faceStamp +
        '" data-chip="face" data-face="' +
        esc(face.id) +
        '">' +
        esc(face.label) +
        "</span>"
    );
    if (t.priority != null && t.priority !== "") {
      chips.push(
        '<span class="suite-ticket-chip" data-chip="priority">p' +
          esc(String(t.priority)) +
          "</span>"
      );
    }
    if (product) {
      chips.push(
        '<span class="suite-ticket-chip" data-chip="project">' +
          esc(product) +
          "</span>"
      );
    }
    if (isTimer && t.gate_until) {
      chips.push(
        '<span class="suite-ticket-chip" data-chip="until">until ' +
          esc(niceTs(t.gate_until)) +
          "</span>"
      );
    }
    const statusHtml =
      '<div class="suite-ticket-status suite-ticket-status-strip" role="status">' +
      chips.join("") +
      "</div>";

    /* Dual stamp: Filed by · Seat · hand (pc-929) */
    let dualStampText = buildDualStampText(t, hand);
    const stNorm = String(t.status || "").toLowerCase().replace(/\s+/g, "_");
    const ownerVal = String(t.owner || "").trim();
    if (ownerVal && (stNorm === "in_progress" || stNorm === "in_review")) {
      const ownerDisplay = /^(you|founder|founder-terminal)$/i.test(ownerVal)
        ? youFace : ownerVal;
      dualStampText += " · Claim · " + ownerDisplay;
    }
    const dualStampHtml =
      '<div class="suite-ticket-dual-stamp' +
      (!hand ? " is-unrouted" : "") +
      '">' +
      esc(dualStampText) +
      "</div>";

    /* Gate note — For You / Deferred thaw / Timed (not human-only) */
    let gateNoteHtml = "";
    if (gateNote) {
      let noteLabel = "Note";
      let noteCls = "suite-ticket-gate-note";
      if (isHuman) {
        noteLabel = "For You";
        noteCls += " suite-ticket-needs-you";
      } else if (isDeferred) {
        noteLabel = "Deferred · why parked";
        noteCls += " suite-ticket-deferred-note";
      } else if (isTimer) {
        noteLabel = "Timed";
        noteCls += " suite-ticket-timed-note";
      }
      gateNoteHtml =
        '<div class="' +
        noteCls +
        '">' +
        '<div class="suite-ticket-needs-you-label">' +
        esc(noteLabel) +
        "</div>" +
        '<div class="suite-ticket-needs-you-body">' +
        esc(gateNote).replace(/\n/g, "<br>") +
        "</div></div>";
    } else if (isHuman) {
      gateNoteHtml =
        '<div class="suite-ticket-needs-you">' +
        '<div class="suite-ticket-needs-you-label">For You</div>' +
        '<div class="suite-ticket-needs-you-body">Waiting on ' +
        esc(youFace) +
        " — open when you can act.</div></div>";
    }

    const placeHtml = placeContextHtml(product);
    const whereHtml = renderWhereHtml(t);

    /* Full ticket body — always expanded (founder 2026-07-30: no More hide). */
    let bodyHtml = "";
    if (sec.glance) {
      bodyHtml +=
        '<div class="suite-ticket-glance md">' + renderMd(sec.glance) + "</div>";
    }
    if (sec.doneWhen) {
      bodyHtml +=
        '<h3 class="suite-ticket-h">Done when</h3>' +
        '<div class="md suite-ticket-done">' +
        renderMd(sec.doneWhen) +
        "</div>";
    }
    if (sec.detail) {
      bodyHtml +=
        '<h3 class="suite-ticket-h">Detail</h3>' +
        '<div class="md suite-ticket-detail-open">' +
        renderMd(sec.detail) +
        "</div>";
    }
    if (sec.rest) {
      bodyHtml +=
        '<div class="md suite-ticket-desc">' +
        renderMd(sec.rest) +
        "</div>";
    }
    if (!bodyHtml && !whereHtml) {
      bodyHtml = '<p class="suite-paper-muted">(no description)</p>';
    }

    /* pc-1148: Remind me on… — convert Decide/Note gold → timer (Watch/calendar) */
    const stOpen =
      stNorm !== "done" && stNorm !== "canceled" && stNorm !== "cancelled";
    const tidCitizen = String((t && t.id) || "").trim();
    const showRemind =
      stOpen &&
      tidCitizen &&
      !isTimer &&
      (isHuman || face.id === "ready" || face.id === "open");
    let remindHtml = "";
    if (showRemind) {
      const ymd = function (d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return y + "-" + m + "-" + day;
      };
      let todayYmd = "";
      let defDate = "";
      try {
        const now = new Date();
        todayYmd = ymd(now);
        const tmr = new Date(now.getTime());
        tmr.setDate(tmr.getDate() + 1);
        defDate = ymd(tmr);
      } catch (eDef) {
        todayYmd = "";
        defDate = "";
      }
      remindHtml =
        '<div class="suite-ticket-remind suite-ticket-report-inbox-actions" data-remind-me data-task-id="' +
        esc(tidCitizen) +
        '">' +
        '<label class="suite-ticket-remind-label" for="suite-remind-date-' +
        esc(tidCitizen) +
        '">Remind me on</label>' +
        '<input type="date" class="suite-ticket-remind-date" id="suite-remind-date-' +
        esc(tidCitizen) +
        '" data-remind-date value="' +
        esc(defDate) +
        '"' +
        (todayYmd ? ' min="' + esc(todayYmd) + '"' : "") +
        ' title="Opens on this date · sets timer gate (not human gold)">' +
        '<button type="button" class="suite-ticket-report-act is-primary" data-remind-submit title="Set gate_type=timer · leaves Decide gold · appears on Watch + calendar">' +
        "Set reminder" +
        "</button>" +
        '<span class="suite-ticket-report-act-status" data-remind-status aria-live="polite"></span>' +
        "</div>";
    }

    const footParts = [];
    if (t.id) footParts.push(String(t.id));
    if (product) footParts.push(product);
    if (t.priority != null) footParts.push("p" + String(t.priority));
    footParts.push(face.label);
    /* pc-1187: open age from created_at primary; last-touch secondary */
    const openAge = ageCompact(t.created_at || t.created);
    if (openAge) footParts.push("open " + openAge);
    const touchAge = ageCompact(t.updated_at || t.updated);
    if (
      touchAge &&
      touchAge !== openAge &&
      t.updated_at &&
      t.created_at &&
      Math.abs(Date.parse(String(t.updated_at)) - Date.parse(String(t.created_at))) >
        90 * 1000
    ) {
      footParts.push("touched " + touchAge);
    } else if (!openAge) {
      const upd = niceTs(t.updated_at);
      if (upd && upd !== "—") footParts.push("updated " + upd);
    }
    const lab = citizenLabels(t.labels || []);
    if (lab.length) footParts.push(lab.slice(0, 4).join(" · "));

    return (
      '<div class="suite-ticket suite-ticket-citizen" data-face="' +
      esc(face.id) +
      '">' +
      statusHtml +
      dualStampHtml +
      placeHtml +
      whereHtml +
      gateNoteHtml +
      remindHtml +
      bodyHtml +
      (footParts.length
        ? '<p class="suite-ticket-foot">' + esc(footParts.join(" · ")) + "</p>"
        : "") +
      "</div>"
    );
  }

  /**
   * pc-1148: wire Remind me on… → PATCH gate_type=timer + gate_until.
   * Leaves Decide gold; ticket surfaces on Watch band + /calendar.
   */
  function wireRemindMeAction(scope, ticket) {
    const rootEl = scope || document;
    if (!rootEl || !rootEl.querySelector) return;
    const bar = rootEl.querySelector("[data-remind-me]");
    if (!bar || bar._remindWired) return;
    bar._remindWired = true;
    const tid = String(
      bar.getAttribute("data-task-id") || (ticket && ticket.id) || ""
    ).trim();
    if (!tid) return;

    const statusEl = bar.querySelector("[data-remind-status]");
    const dateEl = bar.querySelector("[data-remind-date]");
    const setStatus = function (msg, isErr) {
      if (!statusEl) return;
      statusEl.textContent = msg || "";
      statusEl.classList.toggle("is-err", !!isErr);
    };
    const setBusy = function (on) {
      bar.querySelectorAll("button[data-remind-submit]").forEach(function (b) {
        b.disabled = !!on;
      });
      if (dateEl) dateEl.disabled = !!on;
    };
    const refreshForYou = function () {
      try {
        document.dispatchEvent(
          new CustomEvent("suite-for-you-refresh", {
            detail: { task_id: tid, source: "remind-me" },
          })
        );
      } catch (eEv) {}
    };

    const submit = function () {
      const raw = dateEl ? String(dateEl.value || "").trim() : "";
      if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        setStatus("Pick a date", true);
        return;
      }
      /* Noon UTC on that calendar day — stable Opens label + ICS day */
      const until = raw + "T12:00:00+00:00";
      const note = "Remind me on " + raw;
      setBusy(true);
      setStatus("Setting reminder…", false);
      fetch("/api/task/" + encodeURIComponent(tid), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          gate_type: "timer",
          gate_until: until,
          gate_note: note,
          author: "you",
        }),
        cache: "no-store",
        credentials: "same-origin",
      })
        .then(function (r) {
          return r.json().then(function (j) {
            return {
              ok: r.ok && !!(j && j.ok !== false),
              data: j,
            };
          });
        })
        .then(function (res) {
          if (!res || !res.ok) {
            setStatus(
              (res &&
                res.data &&
                (res.data.error || res.data.message || res.data.msg)) ||
                "Could not set reminder",
              true
            );
            setBusy(false);
            return;
          }
          setStatus("Reminder set · Opens " + raw + " · Watch + calendar", false);
          refreshForYou();
          /* Reload dig so face chip becomes Timed / until */
          try {
            if (typeof loadTicket === "function") {
              loadToken += 1;
              loadTicket(tid, loadToken);
            }
          } catch (eReload) {
            setBusy(false);
          }
        })
        .catch(function () {
          setStatus("Network error", true);
          setBusy(false);
        });
    };

    bar.addEventListener("click", function (e) {
      const btn =
        e.target &&
        e.target.closest &&
        e.target.closest("[data-remind-submit]");
      if (!btn || !bar.contains(btn)) return;
      e.preventDefault();
      e.stopPropagation();
      submit();
    });
    if (dateEl) {
      dateEl.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          submit();
        }
      });
    }
  }

  /* ── state ── */
  let root = null;
  let playlist = []; /* {type:'paper'|'ticket', id:string}[] */
  let current = null; /* item or null */
  let loadToken = 0;
  /* Attention densities: scan (edge rail) | stage (read surface). Not a depth. */
  let density = "scan";
  let densityUserOverride = false;

  /* Content-weight thresholds — promote Scan → Stage (pc-272). */
  const WEIGHT = {
    paperChars: 900,
    ticketChars: 400,
    bodyViewportRatio: 0.55,
  };

  function ensure() {
    if (root) return root;
    root = document.createElement("div");
    root.id = "suite-paper";
    root.className = "suite-paper";
    root.hidden = true;
    root.innerHTML =
      '<div class="suite-paper-bg" data-paper-close="1"></div>' +
      '<aside class="suite-paper-sheet" role="dialog" aria-modal="true" aria-labelledby="suite-paper-title">' +
      '  <header class="suite-paper-head">' +
      '    <div class="suite-paper-head-main">' +
      '      <div class="suite-paper-chrome" style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:4px">' +
      '        <div class="suite-paper-kicker" id="suite-paper-kicker" style="margin-bottom:0">Paper</div>' +
      '        <div class="suite-paper-actions">' +
      '          <div class="suite-paper-nav" id="suite-paper-nav" hidden>' +
      '            <button type="button" class="suite-paper-nav-btn" id="suite-paper-prev" title="Previous (← or j)" aria-label="Previous">‹</button>' +
      '            <span class="suite-paper-nav-pos" id="suite-paper-pos">—</span>' +
      '            <button type="button" class="suite-paper-nav-btn" id="suite-paper-next" title="Next (→ or k)" aria-label="Next">›</button>' +
      "          </div>" +
      /* pc-449: map modal = Full page + close only (Rail/Source retired) */
      '          <a class="suite-paper-full" id="suite-paper-full" href="#">full page</a>' +
      '          <button type="button" class="suite-paper-x" id="suite-paper-close" title="Close" aria-label="Close">×</button>' +
      "        </div>" +
      "      </div>" +
      '      <h2 id="suite-paper-title">—</h2>' +
      '      <div class="suite-paper-path" id="suite-paper-path"></div>' +
      "    </div>" +
      "  </header>" +
      '  <div class="suite-paper-body md" id="suite-paper-body"></div>' +
      '  <pre class="suite-paper-source" id="suite-paper-source" hidden></pre>' +
      "</aside>";
    document.body.appendChild(root);

    root.querySelector("[data-paper-close]").addEventListener("click", close);
    document
      .getElementById("suite-paper-close")
      .addEventListener("click", close);
    document.getElementById("suite-paper-prev").addEventListener("click", () =>
      step(-1)
    );
    document.getElementById("suite-paper-next").addEventListener("click", () =>
      step(1)
    );
    return root;
  }

  function setDensity(mode, opts) {
    /* Modal always uses stage-readable layout; no Rail toggle (pc-449). */
    opts = opts || {};
    density = "stage";
    if (opts.user) densityUserOverride = true;
    ensure();
    root.classList.add("is-stage");
    document.documentElement.classList.toggle(
      "suite-paper-stage",
      !!(root && !root.hidden)
    );
  }

  function toggleDensity() {
    /* no-op — density control retired from map modal (pc-449) */
  }

  function contentWantsStage(kind, text, task) {
    const body = String(text || "");
    if (kind === "ticket") {
      /* Inbox reports always need the wide stage (pc-895) */
      if (task && isInboxReport(task)) return true;
      if (body.length >= WEIGHT.ticketChars) return true;
      const gate = String(
        (task && (task.gate_type || task.gate || task.kind)) || ""
      ).toLowerCase();
      if (
        gate === "human" ||
        gate === "timer" ||
        gate === "embargo" ||
        gate.indexOf("founder") >= 0 ||
        gate.indexOf("human") >= 0
      )
        return true;
      if (task && String(task.gate_note || "").trim()) return true;
      const labs = (task && task.labels) || [];
      for (let i = 0; i < labs.length; i++) {
        const L = String(labs[i] || "").toLowerCase();
        if (
          L.indexOf("founder") >= 0 ||
          L.indexOf("human") >= 0 ||
          L.indexOf("embargo") >= 0
        )
          return true;
      }
      /* Priority 1–2 tickets default to stage for reading */
      const pr = task && task.priority;
      if (pr === 1 || pr === 2) return true;
      return false;
    }
    return body.length >= WEIGHT.paperChars;
  }

  function maybeAutoStage(kind, text, task) {
    if (densityUserOverride) return;
    if (contentWantsStage(kind, text, task)) {
      setDensity("stage");
      /* Second frame — forces layout so is-stage isn't stuck as rail paint */
      try {
        requestAnimationFrame(function () {
          setDensity("stage");
        });
      } catch (e) {}
      return;
    }
    /* Layout weight: tall rendered body needs Stage even when char count is low. */
    try {
      const el = document.getElementById("suite-paper-body");
      if (
        el &&
        el.scrollHeight > window.innerHeight * WEIGHT.bodyViewportRatio
      ) {
        setDensity("stage");
        return;
      }
    } catch (e) {}
    setDensity("stage");
  }

  function setOpen(on) {
    ensure();
    root.hidden = !on;
    root.classList.toggle("on", on);
    document.documentElement.classList.toggle("suite-paper-open", on);
    /* Modal always stage-readable when open (pc-449) */
    document.documentElement.classList.toggle("suite-paper-stage", !!on);
    if (root) root.classList.toggle("is-stage", !!on);
    if (!on && root) root.classList.remove("is-report-inbox");
  }

  function resetViewChrome() {
    const src = document.getElementById("suite-paper-source");
    const body = document.getElementById("suite-paper-body");
    if (src) src.hidden = true;
    if (body) body.hidden = false;
  }

  function updateNav() {
    const nav = document.getElementById("suite-paper-nav");
    const pos = document.getElementById("suite-paper-pos");
    const prev = document.getElementById("suite-paper-prev");
    const next = document.getElementById("suite-paper-next");
    if (!nav) return;
    if (!current || playlist.length < 2) {
      nav.hidden = true;
      return;
    }
    const idx = playlist.findIndex(
      (it) => itemKey(it) === itemKey(current)
    );
    if (idx < 0) {
      nav.hidden = true;
      return;
    }
    nav.hidden = false;
    pos.textContent = idx + 1 + " / " + playlist.length;
    prev.disabled = idx <= 0;
    next.disabled = idx >= playlist.length - 1;
  }

  function collectPlaylist() {
    const items = [];
    const seen = new Set();
    document.querySelectorAll("a[href]").forEach((a) => {
      if (a.closest(".suite-paper")) return;
      const href = a.getAttribute("href");
      const paper = pathFromHref(href);
      if (paper) {
        const k = "paper:" + paper;
        if (!seen.has(k)) {
          seen.add(k);
          items.push({ type: "paper", id: paper });
        }
        return;
      }
      const tid = ticketIdFromHref(href);
      if (tid) {
        const k = "ticket:" + tid;
        if (!seen.has(k)) {
          seen.add(k);
          items.push({ type: "ticket", id: tid });
        }
      }
    });
    return items;
  }

  function close() {
    const wasOpen = root && !root.hidden;
    const closedItem = current;
    revokeReportBlobs();
    setOpen(false);
    current = null;
    loadToken++;
    resetViewChrome();
    densityUserOverride = false;
    setDensity("scan");
    if (wasOpen && typeof document !== "undefined") {
      try {
        document.dispatchEvent(
          new CustomEvent("suite-paper-close", {
            detail: closedItem ? { type: closedItem.type, id: closedItem.id } : {},
          })
        );
      } catch (e) {}
    }
  }

  function step(dir) {
    if (!current || playlist.length < 2) return;
    const idx = playlist.findIndex(
      (it) => itemKey(it) === itemKey(current)
    );
    if (idx < 0) return;
    const next = playlist[idx + dir];
    if (!next) return;
    openItem(next, { keepPlaylist: true });
  }

  /**
   * SuitePaper head escape control.
   * Papers/tickets: "full page" → /read or /ticket.
   * Reports: "open report" → primary path (HTML asset or /read md).
   */
  function setFullPageChrome(it, reportOpen) {
    const fullEl = document.getElementById("suite-paper-full");
    if (!fullEl) return;
    if (reportOpen && reportOpen.href) {
      fullEl.textContent = "open report";
      fullEl.href = reportOpen.href;
      if (reportOpen.isHtml) {
        fullEl.setAttribute("data-hard-nav", "1");
        fullEl.setAttribute("target", "_blank");
        fullEl.setAttribute("rel", "noopener");
      } else {
        fullEl.removeAttribute("data-hard-nav");
        fullEl.removeAttribute("target");
        fullEl.removeAttribute("rel");
      }
      fullEl.title = reportOpen.path
        ? "Open " + reportOpen.path
        : "Open report";
      return;
    }
    fullEl.textContent = "full page";
    fullEl.href = fullHref(it);
    fullEl.removeAttribute("data-hard-nav");
    fullEl.removeAttribute("target");
    fullEl.removeAttribute("rel");
    fullEl.title = "Full page";
  }

  /**
   * pc-1305: ids from tape (pc-1302), search ("pc-1302 · title"), or bare 1302.
   */
  function ticketIdsMatch(a, b) {
    const na = String(a || "")
      .trim()
      .toLowerCase();
    const nb = String(b || "")
      .trim()
      .toLowerCase();
    if (!na || !nb) return false;
    if (na === nb) return true;
    try {
      if (global.SuiteNav && typeof SuiteNav.normalizeTicketId === "function") {
        const xa = String(SuiteNav.normalizeTicketId(na) || "").toLowerCase();
        const xb = String(SuiteNav.normalizeTicketId(nb) || "").toLowerCase();
        if (xa && xb && xa === xb) return true;
      }
    } catch (eN) {}
    return false;
  }

  function glanceFromDescription(desc) {
    const text = String(desc || "").trim();
    if (!text) return "";
    try {
      if (global.WoTape && typeof WoTape.extractGlanceText === "function") {
        return String(WoTape.extractGlanceText(text) || "").trim();
      }
    } catch (eW) {}
    const sec = parseWorkOrderSections(text);
    return String((sec && sec.glance) || "").trim();
  }

  function stripTicketIdPrefix(title, tid) {
    let t = String(title || "").trim();
    const id = String(tid || "").trim();
    if (!t || !id) return t;
    const pref = id + " · ";
    if (t.indexOf(pref) === 0) return t.slice(pref.length).trim();
    if (t.toLowerCase().indexOf(id.toLowerCase() + " · ") === 0) {
      const i = t.indexOf(" · ");
      return i > 0 ? t.slice(i + 3).trim() : t;
    }
    return t;
  }

  /**
   * pc-1305: title + Glance already on the tape / search row / slip meta.
   * Overlay first paint must not wait for GET /api/task.
   */
  function peekTicketPreview(id, hint) {
    const tid = String(id || "").trim();
    const out = { title: "", glance: "", status: "", source: "" };
    function take(obj, source) {
      if (!obj) return;
      let title = String(obj.title || obj.summary || "").trim();
      title = stripTicketIdPrefix(title, tid);
      let glance = String(obj.glance || "").trim();
      if (!glance) glance = glanceFromDescription(obj.description || obj.desc);
      const status = String(obj.status || obj.stamp || "").trim();
      if (title && !out.title) out.title = title;
      if (glance && !out.glance) out.glance = glance;
      if (status && !out.status) out.status = status;
      if ((title || glance) && source && !out.source) out.source = source;
    }
    take(hint, "hint");
    if (hint && typeof hint === "object") {
      take(hint.preview, "hint");
    }

    try {
      if (global.WoTape && typeof WoTape.getSlipMeta === "function") {
        const meta = WoTape.getSlipMeta() || {};
        const keys = Object.keys(meta);
        for (let i = 0; i < keys.length; i++) {
          if (ticketIdsMatch(keys[i], tid)) {
            take(meta[keys[i]], "slip");
            break;
          }
        }
      }
    } catch (eM) {}

    try {
      if (global.WoTape && typeof WoTape.getDeskCache === "function") {
        const cache = WoTape.getDeskCache() || {};
        const filters = Object.keys(cache);
        for (let fi = 0; fi < filters.length; fi++) {
          const rows = (cache[filters[fi]] && cache[filters[fi]].rows) || [];
          for (let ri = 0; ri < rows.length; ri++) {
            const row = rows[ri];
            if (ticketIdsMatch((row && (row.tid || row.id)) || "", tid)) {
              take(row, "desk");
              break;
            }
          }
          if (out.glance && out.title) break;
        }
      }
    } catch (eD) {}

    try {
      const nodes = document.querySelectorAll(
        "button.slip-row[data-tid], button.hy-ticket[data-tid], [data-tid].inspect-list-item, .map-sr-item"
      );
      for (let i = 0; i < nodes.length; i++) {
        const el = nodes[i];
        const dtid = el.getAttribute("data-tid") || "";
        if (dtid && ticketIdsMatch(dtid, tid)) {
          const titleEl = el.querySelector(
            ".slip-title, .card-title, .map-sr-title"
          );
          const glanceEl = el.querySelector(
            ".slip-glance:not(.is-skel):not([hidden])"
          );
          take(
            {
              title: titleEl ? titleEl.textContent : "",
              glance: glanceEl ? String(glanceEl.textContent || "").trim() : "",
            },
            "dom"
          );
          continue;
        }
        const titleEl = el.querySelector(".map-sr-title");
        if (!titleEl) continue;
        const raw = String(titleEl.textContent || "").trim();
        const low = raw.toLowerCase();
        const idLow = tid.toLowerCase();
        if (low === idLow || low.indexOf(idLow + " ·") === 0) {
          take({ title: raw }, "search");
        }
      }
    } catch (eDom) {}

    out.title = stripTicketIdPrefix(out.title, tid);
    return out;
  }

  function ticketPreviewBodyHtml(preview) {
    const glance = String((preview && preview.glance) || "").trim();
    let html =
      '<div class="suite-ticket suite-ticket-citizen" data-ticket-preview="1">';
    if (glance) {
      html +=
        '<div class="suite-ticket-glance md" data-ticket-preview-glance="1">' +
        renderMd(glance) +
        "</div>";
    }
    html +=
      '<p class="suite-paper-muted" data-ticket-hydrate="1">Loading description…</p>';
    html += "</div>";
    return html;
  }

  function showLoading(it) {
    ensure();
    const isTicket = it && it.type === "ticket";
    let preview = null;
    if (isTicket) {
      preview = peekTicketPreview(it.id, it);
      it._preview = preview;
    }
    document.getElementById("suite-paper-kicker").textContent = isTicket
      ? "Work order"
      : "Loading…";
    document.getElementById("suite-paper-title").textContent = isTicket
      ? (preview && preview.title) || it.id
      : it.id.split("/").pop() || it.id;
    document.getElementById("suite-paper-path").textContent = isTicket
      ? "work order · " + it.id
      : it.id;
    document.getElementById("suite-paper-body").innerHTML = isTicket
      ? ticketPreviewBodyHtml(preview)
      : '<p class="suite-paper-muted">Opening paper…</p>';
    document.getElementById("suite-paper-source").textContent = "";
    setFullPageChrome(it, null);
    resetViewChrome();
    /* Fresh open resets auto-promote unless keepDensity (nav step). */
    if (!it._keepDensity) {
      densityUserOverride = false;
      setDensity("scan");
    } else {
      setDensity(density);
    }
    updateNav();
    setOpen(true);
    if (isTicket) {
      const hydrateAt = Date.now();
      it._hydrateAt = hydrateAt;
      setTimeout(function () {
        if (!it || it._hydrateAt !== hydrateAt) return;
        const el = document.querySelector("[data-ticket-hydrate]");
        if (!el) return;
        el.textContent = "Still waiting on the desk…";
      }, 2500);
    }
  }

  /**
   * pc-568: never surface bare WebKit "Load failed" / "Failed to fetch".
   * Always attach kind + path/id (+ HTTP status / API body when known).
   */
  function formatOpenError(kind, ref, detail) {
    const tag = kind === "ticket" ? "ticket " + ref : "path " + ref;
    let msg = detail == null || detail === "" ? "unknown error" : String(detail);
    const low = msg.toLowerCase();
    if (
      low === "load failed" ||
      low === "failed to fetch" ||
      low.indexOf("networkerror") >= 0 ||
      low.indexOf("network request failed") >= 0 ||
      low.indexOf("the internet connection appears to be offline") >= 0
    ) {
      msg =
        "network error (" +
        msg +
        ") — is BluePrint suite still up on this origin?";
    }
    if (msg.indexOf(tag) >= 0) return msg;
    return msg + " · " + tag;
  }

  async function fetchSuiteJson(url, kind, ref, opts) {
    opts = opts || {};
    let r;
    let timer = null;
    let ctrl = null;
    try {
      const fetchOpts = { cache: "no-store", credentials: "same-origin" };
      const timeoutMs = opts.timeoutMs > 0 ? opts.timeoutMs : 0;
      if (timeoutMs && typeof AbortController === "function") {
        ctrl = new AbortController();
        fetchOpts.signal = ctrl.signal;
        timer = setTimeout(function () {
          try {
            ctrl.abort();
          } catch (eA) {}
        }, timeoutMs);
      }
      r = await fetch(url, fetchOpts);
    } catch (eNet) {
      const name = (eNet && eNet.name) || "";
      const raw = (eNet && eNet.message) || eNet;
      const timed =
        name === "AbortError" || /aborted|abort/i.test(String(raw));
      throw new Error(
        formatOpenError(
          kind,
          ref,
          timed
            ? "desk timed out — overlay kept the Glance already on the row"
            : raw
        )
      );
    } finally {
      if (timer) {
        try {
          clearTimeout(timer);
        } catch (eC) {}
      }
    }
    let text = "";
    try {
      text = await r.text();
    } catch (eBody) {
      throw new Error(
        formatOpenError(
          kind,
          ref,
          "HTTP " +
            r.status +
            " · body unreadable (" +
            ((eBody && eBody.message) || eBody) +
            ")"
        )
      );
    }
    let data = {};
    if (text && String(text).trim()) {
      try {
        data = JSON.parse(text);
      } catch (eParse) {
        const snippet = String(text)
          .replace(/\s+/g, " ")
          .trim()
          .slice(0, 96);
        throw new Error(
          formatOpenError(
            kind,
            ref,
            "HTTP " +
              r.status +
              " non-JSON" +
              (snippet ? " · " + snippet : "")
          )
        );
      }
    }
    if (!r.ok) {
      const err =
        (data &&
          (data.error ||
            data.detail ||
            data.message ||
            (data.ok === false && data.reason))) ||
        r.statusText ||
        "error";
      const errStr =
        typeof err === "string" ? err : JSON.stringify(err);
      throw new Error(
        formatOpenError(kind, ref, errStr + " · HTTP " + r.status)
      );
    }
    return data;
  }

  /** Paper id: keep abs paths (Unix / Windows); strip only accidental leading /. */
  function normalizePaperId(raw) {
    let s = String(raw == null ? "" : raw).trim();
    if (!s) return "";
    if (s.charAt(0) === "/" || /^[A-Za-z]:[\\/]/.test(s)) return s;
    return s.replace(/^\/+/, "");
  }

  async function loadPaper(path, token, project) {
    /* pc-1209: project hint → server falls back to <project-folder>/<path> */
    const data = await fetchSuiteJson(
      "/api/file?path=" +
        encodeURIComponent(path) +
        (project ? "&project=" + encodeURIComponent(project) : ""),
      "paper",
      path
    );
    if (token !== loadToken) return;
    /* Canonical city-relative path from the server (post project fallback) */
    const canon = data.path || path;
    document.getElementById("suite-paper-title").textContent =
      data.name || path.split("/").pop() || path;
    document.getElementById("suite-paper-path").textContent = canon;
    document.getElementById("suite-paper-kicker").textContent = data.rule
      ? "Rules · required"
      : "Document · read-only";
    const content = data.content || "";
    const bodyEl = document.getElementById("suite-paper-body");
    bodyEl.innerHTML = renderMd(content, canon);
    wireRelativeLinks(bodyEl, mapSlugFromPath(canon));
    wireTruncateExpand(bodyEl, content, path);
    document.getElementById("suite-paper-source").textContent = content;
    bodyEl.scrollTop = 0;
    maybeAutoStage("paper", content, null);
  }

  /**
   * Full-page paper room (shortest path): one /api/file hop, no HTML shell
   * re-fetch. Soft-nav and cold /read both use this when SuitePaper is live.
   */
  function paperRoomHtml() {
    return (
      '<div class="suite-read-room" data-suite-room="read">' +
      '  <div class="suite-read-pathbar" id="suite-read-pathbar"></div>' +
      '  <div class="suite-read-meta" id="suite-read-meta"></div>' +
      '  <div class="suite-read-sheet paper" id="suite-read-sheet">' +
      '    <div class="suite-read-toolbar">' +
      '      <button type="button" class="raw-toggle" id="suite-read-toggle-raw">view source</button>' +
      "    </div>" +
      '    <div class="md suite-paper-body" id="suite-read-view"></div>' +
      '    <pre id="suite-read-raw" class="suite-read-raw" hidden></pre>' +
      "  </div>" +
      '  <div class="err suite-read-err" id="suite-read-err" hidden></div>' +
      "</div>"
    );
  }

  function buildReadPathbar(relPath) {
    var parts = String(relPath || "")
      .split("/")
      .filter(Boolean);
    var file = parts.pop() || relPath;
    var bits = [];
    bits.push('<a href="/workspace-map">Map</a>');
    var acc = [];
    parts.forEach(function (p) {
      acc.push(p);
      bits.push('<span class="sep">/</span>');
      var href =
        global.SuiteNav && SuiteNav.placeHref
          ? SuiteNav.placeHref(acc[0], acc.slice(1).join("/"))
          : "/workspace-map";
      bits.push('<a href="' + href + '">' + esc(p) + "</a>");
    });
    bits.push('<span class="sep">/</span>');
    bits.push('<span class="here">' + esc(file) + "</span>");
    return bits.join("");
  }

  async function mountFullPagePaper(path, opts) {
    opts = opts || {};
    path = normalizePaperId(path);
    if (!path) return false;
    try {
      if (typeof close === "function") close();
    } catch (eC) {}
    ensureSuitePaperStyles();
    var body = document.getElementById("suite-body");
    if (!body) {
      body = document.createElement("div");
      body.id = "suite-body";
      document.body.appendChild(body);
    }
    body.setAttribute("data-suite-room", "read");
    body.innerHTML = paperRoomHtml();
    var pathbar = document.getElementById("suite-read-pathbar");
    var meta = document.getElementById("suite-read-meta");
    var viewEl = document.getElementById("suite-read-view");
    var rawEl = document.getElementById("suite-read-raw");
    var errEl = document.getElementById("suite-read-err");
    var sheet = document.getElementById("suite-read-sheet");
    if (pathbar) pathbar.innerHTML = buildReadPathbar(path);
    if (viewEl)
      viewEl.innerHTML =
        '<p class="suite-paper-muted">Opening paper…</p>';
    if (meta) meta.textContent = path;

    try {
      if (global.SuiteNav && typeof SuiteNav.apply === "function") {
        var project =
          (SuiteNav.projectFromCityPath &&
            SuiteNav.projectFromCityPath(path)) ||
          "";
        SuiteNav.apply({ room: "read", project: project });
      }
    } catch (eA) {}

    var data;
    try {
      data = await fetchSuiteJson(
        "/api/file?path=" + encodeURIComponent(path),
        "paper",
        path
      );
    } catch (e) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent =
          "Could not open paper: " + ((e && e.message) || e);
      }
      if (sheet) sheet.hidden = true;
      return false;
    }

    var content = data.content || "";
    var name = data.name || path.split("/").pop() || path;
    try {
      var mastEl =
        document.querySelector(".suite-title h1") ||
        document.getElementById("title");
      if (global.SuiteNav && typeof SuiteNav.setMastTitle === "function" && mastEl) {
        /* Keep dogfood / package version chip when opening papers on Map */
        var paperVer = null;
        try {
          paperVer =
            localStorage.getItem("suite.suiteVersion") ||
            sessionStorage.getItem("suite.suiteVersion") ||
            null;
        } catch (ePv) {
          paperVer = null;
        }
        SuiteNav.setMastTitle(mastEl, name, paperVer);
      } else if (mastEl) {
        mastEl.textContent = name;
      }
      document.title =
        global.SuiteNav && SuiteNav.docTitle
          ? SuiteNav.docTitle(name)
          : "BluePrint — " + name;
    } catch (eM) {}

    if (meta) {
      meta.innerHTML =
        (data.rule
          ? '<span class="badge">law / required</span>'
          : "<span>document</span>") +
        " <span>" +
        (data.bytes || content.length || 0) +
        " bytes</span>" +
        ' <a href="/workspace-map">← Map</a>';
    }
    if (viewEl) {
      viewEl.innerHTML = renderMd(content, path);
      wireRelativeLinks(viewEl);
      wireTruncateExpand(viewEl, content, path);
    }
    if (rawEl) rawEl.textContent = content;
    var tog = document.getElementById("suite-read-toggle-raw");
    if (tog && rawEl && viewEl) {
      tog.onclick = function () {
        var on = rawEl.hidden === false;
        rawEl.hidden = on;
        viewEl.hidden = !on;
        tog.textContent = on ? "view source" : "view rendered";
      };
    }
    if (opts.push !== false) {
      try {
        history.pushState(
          {},
          "",
          "/read?path=" + encodeURIComponent(path)
        );
      } catch (eH) {}
    }
    return true;
  }

  async function mountFullPageTicket(id, opts) {
    opts = opts || {};
    id = SuiteNav.normalizeTicketId(id);
    if (!id) return false;
    /* Full ticket page still uses soft HTML for richer chrome; open overlay is faster. */
    try {
      if (typeof close === "function") close();
    } catch (eC) {}
    openTicket(id);
    if (opts.push !== false) {
      try {
        history.pushState({}, "", "/ticket?id=" + encodeURIComponent(id));
      } catch (eH) {}
    }
    return true;
  }

  function ensureSuitePaperStyles() {
    /* Full-page room styles live in suite.css (.suite-read-*). No-op hook. */
  }

  async function loadTicket(id, token) {
    /* pc-1305: first paint already showed Glance; bound hydrate so LIVE BUSY
       cannot leave the overlay on Opening… for the 12s desk proxy. */
    const data = await fetchSuiteJson(
      "/api/task/" + encodeURIComponent(id),
      "ticket",
      id,
      { timeoutMs: 5000 }
    );
    if (token !== loadToken) return;
    const t = data.task || data;
    const report = isInboxReport(t);
    const reportOpen = report ? reportEscapeForTicket(t) : null;
    ensure();
    if (report) {
      const kind = reportKindFromTicket(t);
      document.getElementById("suite-paper-title").textContent =
        reportDisplayTitle(t);
      document.getElementById("suite-paper-path").textContent =
        (t.id || id) + " · For You · Read";
      document.getElementById("suite-paper-kicker").textContent =
        "Read · " + kind.label;
      setFullPageChrome({ type: "ticket", id: id }, reportOpen);
      root.classList.add("is-report-inbox");
    } else {
      document.getElementById("suite-paper-title").textContent =
        t.title || t.id || id;
      document.getElementById("suite-paper-path").textContent = t.id || id;
      /* Kicker uses Map face (Done / Deferred / For You…), not bare engine status */
      const kFace = ticketDispatchFace(t);
      document.getElementById("suite-paper-kicker").textContent =
        "Work order · " + (kFace.label || String(t.status || "open"));
      setFullPageChrome({ type: "ticket", id: id }, null);
      root.classList.remove("is-report-inbox");
    }
    const bodyEl = document.getElementById("suite-paper-body");
    bodyEl.innerHTML = renderTicketHtml(t);
    wireWhereActions(bodyEl);
    wireRelativeLinks(bodyEl, productSlug(t));
    if (report) {
      wireReportFrames(bodyEl);
      hydrateReportInline(bodyEl, t);
      wireReportInboxActions(bodyEl, t);
    } else {
      wireRemindMeAction(bodyEl, t);
    }
    document.getElementById("suite-paper-source").textContent =
      t.description || JSON.stringify(t, null, 2);
    bodyEl.scrollTop = 0;
    /* Prefer full ticket body + description for weight; gates force Stage. */
    const weightText =
      (t.description || "") +
      "\n" +
      (t.title || "") +
      "\n" +
      (t.gate_note || "");
    maybeAutoStage("ticket", weightText, t);
    if (report) {
      /* Reports always stage + wide pane (pc-895) */
      setDensity("stage");
      root.classList.add("is-report-inbox");
    }
  }

  async function openItem(it, opts) {
    /* Map cinema: law/paper open glow (pc-398) */
    try {
      document.dispatchEvent(
        new CustomEvent("suite-paper-open", {
          detail: it
            ? { type: it.type, id: it.id, path: it.path || it.id || "" }
            : {},
        })
      );
    } catch (eOpen) {}
    opts = opts || {};
    if (!it || !it.id) return;
    const kind = it.type || "paper";
    const nid =
      kind === "ticket"
        ? SuiteNav.normalizeTicketId(it.id)
        : normalizePaperId(it.id);
    if (!nid) return;
    /* pc-1209: keep project hint so project-relative paths resolve */
    it = {
      type: kind,
      id: nid,
      project: it.project || "",
      preview: it.preview || null,
      title: it.title || "",
      glance: it.glance || "",
    };
    if (!opts.keepPlaylist) {
      playlist = collectPlaylist();
      /* ensure opened item is in the list even if not linked (API-driven) */
      if (!playlist.some((x) => itemKey(x) === itemKey(it))) {
        playlist = [it].concat(playlist);
      }
    }
    /* Playlist step: keep current density / user override. */
    if (opts.keepPlaylist) it._keepDensity = true;
    current = it;
    const token = ++loadToken;
    showLoading(it);
    try {
      if (it.type === "ticket") await loadTicket(it.id, token);
      else await loadPaper(it.id, token, it.project || "");
    } catch (e) {
      if (token !== loadToken) return;
      const detail = formatOpenError(
        it.type === "ticket" ? "ticket" : "paper",
        it.id,
        (e && e.message) || e
      );
      const bodyEl = document.getElementById("suite-paper-body");
      const hyd =
        bodyEl && bodyEl.querySelector("[data-ticket-hydrate]");
      if (it.type === "ticket" && hyd) {
        /* Keep title + Glance; do not wipe first paint on a slow/failing desk. */
        hyd.className = "suite-paper-err";
        hyd.removeAttribute("data-ticket-hydrate");
        hyd.textContent = "Could not load the rest: " + detail;
      } else {
        document.getElementById("suite-paper-kicker").textContent = "Error";
        if (bodyEl) {
          bodyEl.innerHTML =
            '<p class="suite-paper-err">Could not open: ' +
            esc(detail) +
            "</p>";
        }
      }
    }
  }

  function open(path, project) {
    return openItem({ type: "paper", id: path, project: project || "" });
  }

  function openTicket(id, preview) {
    return openItem({
      type: "ticket",
      id: id,
      preview: preview || null,
    });
  }

  function onDocClick(e) {
    if (e.defaultPrevented) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0)
      return;
    const a = e.target.closest("a[href]");
    if (!a) return;
    if (a.closest(".suite-paper-sheet")) return;
    const href = a.getAttribute("href");
    const paper = pathFromHref(href);
    if (paper) {
      e.preventDefault();
      openItem({ type: "paper", id: paper });
      return;
    }
    const tid = ticketIdFromHref(href);
    if (tid) {
      e.preventDefault();
      openItem({ type: "ticket", id: tid });
    }
  }

  function typingTarget(el) {
    if (!el || !el.tagName) return false;
    const t = el.tagName.toLowerCase();
    if (t === "input" || t === "textarea" || t === "select") return true;
    if (el.isContentEditable) return true;
    return false;
  }

  function onKey(e) {
    if (!root || root.hidden) return;
    if (typingTarget(e.target)) return;
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      return;
    }
    /* density toggle (.) retired with Rail control — pc-449 */
    const prevKeys = ["ArrowLeft", "ArrowUp", "[", "j", "J"];
    const nextKeys = ["ArrowRight", "ArrowDown", "]", "k", "K"];
    if (prevKeys.indexOf(e.key) !== -1) {
      e.preventDefault();
      step(-1);
    } else if (nextKeys.indexOf(e.key) !== -1) {
      e.preventDefault();
      step(1);
    }
  }

  let installed = false;
  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener("click", onDocClick);
    document.addEventListener("keydown", onKey);
  }

  global.SuitePaper = {
    install: install,
    open: open,
    openTicket: openTicket,
    peekTicketPreview: peekTicketPreview,
    mountFullPagePaper: mountFullPagePaper,
    mountFullPageTicket: mountFullPageTicket,
    isInboxReport: isInboxReport,
    reportKindFromTicket: reportKindFromTicket,
    reportPathsFromTicket: reportPathsFromTicket,
    reportEscapeForTicket: reportEscapeForTicket,
    resolveCityReportPath: resolveCityReportPath,
    productFolderName: productFolderName,
    wireReportFrames: wireReportFrames,
    hydrateReportInline: hydrateReportInline,
    wireReportInboxActions: wireReportInboxActions,
    wireRemindMeAction: wireRemindMeAction,
    wireRelativeLinks: wireRelativeLinks,
    suiteResolvedTheme: suiteResolvedTheme,
    injectReportTheme: injectReportTheme,
    rethemeReadyReportFrames: rethemeReadyReportFrames,
    openItem: openItem,
    close: close,
    isOpen: function () {
      return !!(root && !root.hidden);
    },
    setDensity: setDensity,
    toggleDensity: toggleDensity,
    getDensity: function () {
      return density;
    },
    next: function () {
      step(1);
    },
    prev: function () {
      step(-1);
    },
    renderMd: renderMd,
    renderTicketHtml: renderTicketHtml,
    ticketDispatchFace: ticketDispatchFace,
    isDeferredGateNote: isDeferredGateNote,
    placeContextHtml: placeContextHtml,
    parseWorkOrderSections: parseWorkOrderSections,
    resolveWhere: resolveWhere,
    wireWhereActions: wireWhereActions,
    goWhereMap: goWhereMap,
    youFaceLabel: youFaceLabel,
    ticketDualStampText: function (t) {
      return buildDualStampText(t, ticketHandLabel((t && t.labels) || []));
    },
    pathFromHref: pathFromHref,
    ticketIdFromHref: ticketIdFromHref,
  };
})(typeof window !== "undefined" ? window : globalThis);
