/*! chrome.js — fill/stroke/seats/law mark classifiers (pc-757)
 *
 * Pure: law-mark detection, paper role classification, project paper split.
 * No DOM. No global model. Every function is data-in → data-out.
 *
 * Host (workspace_map.html) delegates via MapChrome when available.
 * Spatial projection uses MapChrome directly.
 */
(function (global) {
  "use strict";

  /* BluePrint instruction basenames that earn a gold law mark. */
  var PC_LAW_MD = {
    "agents.md": 1,
    "boundaries.md": 1,
    "perimeter.md": 1,
    "office_perimeter.md": 1,
    "city_edges.md": 1,
    "atlas.md": 1,
    "claude.md": 1,
    "grok.md": 1,
    "codex.md": 1,
    "cursor.md": 1,
    "gemini.md": 1,
  };

  function isPcLawMd(name) {
    return !!PC_LAW_MD[String(name || "").toLowerCase()];
  }

  /**
   * Citizen list label for an instruction paper (foundation v2).
   * Filename may stay PERIMETER.md; glass says Boundaries.
   */
  function instructionPaperLabel(name) {
    var n = String(name || "").toLowerCase();
    if (
      n === "boundaries.md" ||
      n === "perimeter.md" ||
      n === "office_perimeter.md" ||
      n === "city_edges.md"
    ) {
      return "Boundaries";
    }
    if (n === "agents.md") return "AGENTS.md";
    /* pc-1095: product architecture law — own label beside AGENTS.md */
    if (n === "architecture.md") return "ARCHITECTURE.md";
    if (n === "claude.md" || n === "grok.md" || n === "codex.md" || n === "cursor.md" || n === "gemini.md") {
      return String(name || "");
    }
    return String(name || "");
  }

  function isBoundariesPaper(name) {
    var n = String(name || "").toLowerCase();
    return (
      n === "boundaries.md" ||
      n === "perimeter.md" ||
      n === "office_perimeter.md" ||
      n === "city_edges.md"
    );
  }

  /**
   * Collapse the Boundaries alias family to one instruction row.
   * Keep the family's first list position, but replace its row when a more
   * canonical filename appears so callers inherit the preferred href too.
   */
  function canonicalInstructionPapers(fileRows) {
    var out = [];
    var familyIndex = -1;
    var familyRank = Infinity;
    var rank = {
      "boundaries.md": 0,
      "perimeter.md": 1,
      "office_perimeter.md": 2,
      "city_edges.md": 3,
    };
    (fileRows || []).forEach(function (row) {
      var f = row && row.f ? row.f : row;
      var name = String((f && f.name) || "").toLowerCase();
      if (!isBoundariesPaper(name)) {
        out.push(row);
        return;
      }
      var nextRank = Object.prototype.hasOwnProperty.call(rank, name)
        ? rank[name]
        : 99;
      if (familyIndex < 0) {
        familyIndex = out.length;
        familyRank = nextRank;
        out.push(row);
      } else if (nextRank < familyRank) {
        out[familyIndex] = row;
        familyRank = nextRank;
      }
    });
    return out;
  }

  /**
   * Gold required paper = BluePrint instruction basenames + rule pointers + rule flag.
   * Generic "instruction" *spec*.md stays white handbook.
   */
  function isRequiredPaper(f) {
    if (!f) return false;
    return !!f.rule || !!f.pointer || isPcLawMd(String(f.name || ""));
  }

  /** Depth of an indexed paper (citylens depth or path segments). */
  function paperDepth(f) {
    if (!f) return 1;
    if (f.depth != null) {
      var d = parseInt(f.depth, 10);
      if (isFinite(d) && d >= 1) return d;
    }
    var rel = String(f.rel || "")
      .replace(/\\/g, "/")
      .replace(/^\//, "");
    if (rel) {
      var segs = rel.split("/").filter(Boolean);
      return Math.max(1, segs.length);
    }
    return 1;
  }

  /** Skills live under .claude/skills — capability, not L0/L1 law. */
  function isSkillPaper(f) {
    if (!f) return false;
    var rel = String(f.rel || f.path || "")
      .toLowerCase()
      .replace(/\\/g, "/");
    if (rel.indexOf(".claude/skills") >= 0) return true;
    if (rel.indexOf("/skills/") >= 0 && rel.indexOf("skill.md") >= 0)
      return true;
    var n = String(f.name || "").toLowerCase();
    return n === "skill.md" && rel.indexOf("skill") >= 0;
  }

  /** Architecture / structure papers (pc-423 class stack · pc-1095 root law). */
  function isArchitecturePaper(f) {
    if (!f) return false;
    var n = String(f.name || "").toLowerCase();
    if (
      n === "architecture.md" ||
      n === "truth-index.md" ||
      n === "folder_map.md" ||
      n === "structure.md"
    ) {
      return true;
    }
    var rel = String(f.rel || f.path || "")
      .toLowerCase()
      .replace(/\\/g, "/");
    return (
      rel.indexOf("/architecture/") >= 0 ||
      rel.indexOf("architecture.md") >= 0
    );
  }

  /**
   * Project-root ARCHITECTURE.md only (pc-1087 / pc-1095).
   * Role stays `architecture` (not gold PC_LAW_MD) so dig-in can seat it
   * beside AGENTS with its own label without collapsing into law.
   */
  function isRootArchitecturePaper(f) {
    if (!f) return false;
    var n = String(f.name || "").toLowerCase();
    if (n !== "architecture.md") return false;
    if (paperDepth(f) > 1) return false;
    var rel = String(f.rel || "")
      .replace(/\\/g, "/")
      .replace(/^\//, "");
    if (rel && rel.indexOf("/") >= 0) return false;
    return true;
  }

  /**
   * Dig-in role class (pc-423):
   *   law · skill · architecture · handbook
   * pc-1095: architecture checked before generic required so root
   * ARCHITECTURE.md keeps role `architecture` even if flagged rule.
   */
  function classifyPaperRole(f) {
    if (!f) return "handbook";
    if (isArchitecturePaper(f) && !isPcLawMd(String(f.name || "")))
      return "architecture";
    if (isRequiredPaper(f)) return "law";
    if (isSkillPaper(f)) return "skill";
    if (isArchitecturePaper(f)) return "architecture";
    return "handbook";
  }

  var PAPER_ROLE_ORDER = ["law", "skill", "architecture", "handbook"];
  /* Citizen register: one Instructions family (ADR-008 rules / instruction
   * files). Role id stays `law` internally; UI never says "Agent instructions"
   * for folder stacks — that title was scope-confused with hand digs.
   * Architecture is product structure law (pc-1087) — own section label. */
  var PAPER_ROLE_LABEL = {
    law: "Instructions",
    skill: "Skills",
    architecture: "Architecture",
    handbook: "Other papers",
  };
  var PAPER_ROLE_SUB = {
    law: "AGENTS · Boundaries · pointers",
    skill: "agent capability papers",
    architecture: "layers · SoTs · data flow · invariants",
    handbook: "README · docs · misc",
  };

  /**
   * Dig section title for the Instructions family (one phrase, scope suffix).
   * @param {string} scope  workspace | project | hand | role | (other → bare)
   * @param {number|string|null} [count] optional · N suffix
   */
  function instructionSectionLabel(scope, count) {
    var s = String(scope || "").toLowerCase();
    var base = "Instructions";
    if (s === "workspace" || s === "ws" || s === "l0" || s === "city") {
      base = "Instructions · workspace";
    } else if (s === "project" || s === "l1" || s === "neighborhood") {
      base = "Instructions · project";
    } else if (
      s === "hand" ||
      s === "job" ||
      s === "person" ||
      s === "they" ||
      s === "agent"
    ) {
      base = "Instructions they follow";
    } else if (s === "role" || s === "papers" || s === "law") {
      base = "Instructions";
    }
    if (count != null && count !== "" && isFinite(Number(count))) {
      return base + " · " + Number(count);
    }
    return base;
  }

  /**
   * Citizen depth line for one stack entry (hand dig / person sheet).
   * Glass never stamps L0–L3 (pc-1363). Level/file win over published
   * citizen_label so retired *law* captions stay off glass (pc-1382).
   */
  function instructionDepthLabel(e) {
    if (!e) return "rules";
    var lv = String(e.level || "").toUpperCase();
    var lab = String(e.label || "").toLowerCase();
    var fn = String(e.file || e.name || "").toLowerCase();
    if (
      lv === "L0" ||
      lab.indexOf("city") >= 0 ||
      lab.indexOf("workspace") >= 0
    ) {
      return "workspace";
    }
    if (
      lv === "L1" ||
      lab.indexOf("neighborhood") >= 0 ||
      lab.indexOf("project") >= 0
    ) {
      return "project";
    }
    if (lv === "L2" || fn === "contract.md" || lab.indexOf("contract") >= 0) {
      return "contract";
    }
    if (lv === "L3" || fn === "prompt.md" || lab.indexOf("prompt") >= 0) {
      return "this run";
    }
    if (e.citizen_label) {
      var cit = String(e.citizen_label);
      if (!/\bL[0-3]\b/.test(cit) && !/\blaw\b/i.test(cit)) return cit;
      var cl = cit.toLowerCase();
      if (cl.indexOf("workspace") >= 0 || cl.indexOf("city") >= 0) {
        return "workspace";
      }
      if (cl.indexOf("project") >= 0 || cl.indexOf("neighborhood") >= 0) {
        return "project";
      }
    }
    if (e.label) return String(e.label);
    if (lv === "L0" || lv === "L1" || lv === "L2" || lv === "L3") return "rules";
    if (lv) return lv;
    return "rules";
  }

  /**
   * City-root-relative path for /read?path= (abs or already-rel OK).
   * @param {string} path
   * @param {string} [cityRoot]
   */
  function instructionCityRel(path, cityRoot) {
    if (!path) return "";
    var p = String(path).replace(/\\/g, "/").trim();
    if (!p) return "";
    var root = String(cityRoot || "")
      .replace(/\\/g, "/")
      .replace(/\/+$/, "");
    /* Already relative (no unix/windows abs root) */
    if (p.charAt(0) !== "/" && !/^[A-Za-z]:\//.test(p)) {
      return p.replace(/^\.\//, "");
    }
    if (root) {
      if (p === root) return "";
      if (p.indexOf(root + "/") === 0) return p.slice(root.length + 1);
      var base = root.split("/").filter(Boolean).pop() || "";
      if (base) {
        var marker = "/" + base + "/";
        var i = p.lastIndexOf(marker);
        if (i >= 0) return p.slice(i + marker.length);
      }
    }
    return p.replace(/^\//, "");
  }

  /** Partition a file list into role stacks (order fixed). */
  function groupFilesByRole(fileRows) {
    var buckets = { law: [], skill: [], architecture: [], handbook: [] };
    canonicalInstructionPapers(fileRows).forEach(function (row) {
      var f = row && row.f ? row.f : row;
      var role = classifyPaperRole(f);
      var bucket = buckets[role] || buckets.handbook;
      bucket.push(row);
    });
    return PAPER_ROLE_ORDER.map(function (role) {
      return {
        role: role,
        label: PAPER_ROLE_LABEL[role],
        sub: PAPER_ROLE_SUB[role],
        files: buckets[role] || [],
      };
    }).filter(function (g) {
      return g.files.length > 0;
    });
  }

  /**
   * Classify project papers for rim stacks:
   *   law          — required L0/L1 at project root only
   *   architecture — root ARCHITECTURE.md (pc-1095 · beside AGENTS)
   *   handbook     — other root-only .md (README, CHANGELOG…)
   *   nested       — anything deeper (reached via folder bubbles, not rim stacks)
   */
  function classifyProjectPaper(f) {
    if (!f) return "nested";
    var atRoot = paperDepth(f) <= 1;
    if (isRootArchitecturePaper(f)) return atRoot ? "architecture" : "nested";
    if (isRequiredPaper(f)) return atRoot ? "law" : "nested";
    if (!atRoot) return "nested";
    return "handbook";
  }

  global.MapChrome = {
    PC_LAW_MD: PC_LAW_MD,
    isPcLawMd: isPcLawMd,
    isBoundariesPaper: isBoundariesPaper,
    canonicalInstructionPapers: canonicalInstructionPapers,
    instructionPaperLabel: instructionPaperLabel,
    isRequiredPaper: isRequiredPaper,
    paperDepth: paperDepth,
    isSkillPaper: isSkillPaper,
    isArchitecturePaper: isArchitecturePaper,
    isRootArchitecturePaper: isRootArchitecturePaper,
    classifyPaperRole: classifyPaperRole,
    PAPER_ROLE_ORDER: PAPER_ROLE_ORDER,
    PAPER_ROLE_LABEL: PAPER_ROLE_LABEL,
    PAPER_ROLE_SUB: PAPER_ROLE_SUB,
    groupFilesByRole: groupFilesByRole,
    classifyProjectPaper: classifyProjectPaper,
    instructionSectionLabel: instructionSectionLabel,
    instructionDepthLabel: instructionDepthLabel,
    instructionCityRel: instructionCityRel,
  };
})(typeof window !== "undefined" ? window : globalThis);
