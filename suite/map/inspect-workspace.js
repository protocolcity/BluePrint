/*! inspect-workspace.js — Workspace inspect panel renderer (pc-1408)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4).
 * Workspace overview (showWorkspaceDetail + For You section) lives here only —
 * host keeps a thin wrapper so existing call sites stay put.
 *
 * Browser: window.InspectWorkspace
 * Public: { init, show }
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    actorIsJob: null,
    actorIsLive: null,
    actorIsWalking: null,
    actorShortName: null,
    bindPlaceOpenSectionShared: null,
    bindPlacePulse: null,
    bodySliceToPulseId: null,
    buildPlaceOpenSectionHtml: null,
    canonicalInstructionPapers: null,
    computePlacePulseCells: null,
    ensurePlaceBodySurface: null,
    folderHasDeskStore: null,
    formatRemain: null,
    forYouAttItems: null,
    forYouRowModel: null,
    goldFor: null,
    inspectOrbitGroup: null,
    inspectPerson: null,
    isNonStoreZone: null,
    isPcLawMd: null,
    isProjectRootLayerLaw: null,
    isRootArchitecturePaper: null,
    isWorkspaceOpsWorker: null,
    nextFireMs: null,
    normalizeWoFilter: null,
    openCount: null,
    openFolderInFinder: null,
    openFolderInSuite: null,
    openMapPresenceSeatList: null,
    openProjectWorkOrders: null,
    placePulseStripHtml: null,
    readPlaceOpenUserPins: null,
    remountPlaceOverview: null,
    renderInstructionsSection: null,
    renderWorkingOnNowSection: null,
    repaintWoInsights: null,
    setPlaceBodySlice: null,
    sortForYouByGroupThenUrgency: null,
    workspacePlaceRollup: null,
    getModel: null,
    getLastAtt: null
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  function actorIsJob() {
    var fn = H('actorIsJob');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function actorIsLive() {
    var fn = H('actorIsLive');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function actorIsWalking() {
    var fn = H('actorIsWalking');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function actorShortName() {
    var fn = H('actorShortName');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function bindPlaceOpenSectionShared() {
    var fn = H('bindPlaceOpenSectionShared');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function bindPlacePulse() {
    var fn = H('bindPlacePulse');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function bodySliceToPulseId() {
    var fn = H('bodySliceToPulseId');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function buildPlaceOpenSectionHtml() {
    var fn = H('buildPlaceOpenSectionHtml');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function canonicalInstructionPapers() {
    var fn = H('canonicalInstructionPapers');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function computePlacePulseCells() {
    var fn = H('computePlacePulseCells');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function ensurePlaceBodySurface() {
    var fn = H('ensurePlaceBodySurface');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function folderHasDeskStore() {
    var fn = H('folderHasDeskStore');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function formatRemain() {
    var fn = H('formatRemain');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouAttItems() {
    var fn = H('forYouAttItems');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function forYouRowModel() {
    var fn = H('forYouRowModel');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function goldFor() {
    var fn = H('goldFor');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function inspectOrbitGroup() {
    var fn = H('inspectOrbitGroup');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function inspectPerson() {
    var fn = H('inspectPerson');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function isNonStoreZone() {
    var fn = H('isNonStoreZone');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function isPcLawMd() {
    var fn = H('isPcLawMd');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function isProjectRootLayerLaw() {
    var fn = H('isProjectRootLayerLaw');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function isRootArchitecturePaper() {
    var fn = H('isRootArchitecturePaper');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function isWorkspaceOpsWorker() {
    var fn = H('isWorkspaceOpsWorker');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function nextFireMs() {
    var fn = H('nextFireMs');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function normalizeWoFilter() {
    var fn = H('normalizeWoFilter');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openCount() {
    var fn = H('openCount');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openFolderInFinder() {
    var fn = H('openFolderInFinder');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openFolderInSuite() {
    var fn = H('openFolderInSuite');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openMapPresenceSeatList() {
    var fn = H('openMapPresenceSeatList');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function openProjectWorkOrders() {
    var fn = H('openProjectWorkOrders');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function placePulseStripHtml() {
    var fn = H('placePulseStripHtml');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function readPlaceOpenUserPins() {
    var fn = H('readPlaceOpenUserPins');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function remountPlaceOverview() {
    var fn = H('remountPlaceOverview');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function renderInstructionsSection() {
    var fn = H('renderInstructionsSection');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function renderWorkingOnNowSection() {
    var fn = H('renderWorkingOnNowSection');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function repaintWoInsights() {
    var fn = H('repaintWoInsights');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function setPlaceBodySlice() {
    var fn = H('setPlaceBodySlice');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function sortForYouByGroupThenUrgency() {
    var fn = H('sortForYouByGroupThenUrgency');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function workspacePlaceRollup() {
    var fn = H('workspacePlaceRollup');
    return typeof fn === "function" ? fn.apply(null, arguments) : undefined;
  }

  function getModel() {
    var fn = H('getModel');
    return typeof fn === "function" ? fn() : null;
  }
  function lastAtt() {
    var fn = H('getLastAtt');
    return typeof fn === "function" ? fn() : null;
  }

  /**
   * Append a workspace-flavored "For You" section (categorywise, all gates).
   * Project's For You section (per-WO rows) stays in buildItems — different source.
   */
  function renderWorkspaceForYouSection(forYouItems, gold, items) {
    if (!forYouItems.length) return;
    items.push({ label: "For You · " + gold, section: true, inert: true });
    var lastCat = "";
    forYouItems.forEach(function (it) {
      var row = forYouRowModel(it);
      if (row.catKey !== lastCat) {
        lastCat = row.catKey;
        items.push({
          label: row.catLabel,
          sub: row.sectionSub || "paper pile face",
          section: true,
          inert: true,
        });
      }
      /* pc-1201: title = focus; sub = id · verb · age · product */
      items.push({
        label: row.focus || row.headline,
        sub: row.meta || "",
        href: row.tid ? "/ticket?id=" + encodeURIComponent(row.tid) : null,
      });
    });
  }

  function showWorkspaceDetail() {
    var model = getModel();
    if (!model || !model.city) return;
    const city = model.city;
    const folders = (model.plots || []).filter(function (p) {
      return p && !isNonStoreZone(p); /* hide export/archive noise in list */
    });
    const root = String(city.city_root || "");
    const name =
      root.split("/").filter(Boolean).pop() || "Workspace";
    const roll = workspacePlaceRollup(folders);
    const openSum = roll.open;
    /* pc-558: workspace For You = citywide act-now (You card membership) */
    const gold = roll.forYou;
    /* Project-homed agents — excludes workspace-ops hands (hub ring) to match outlineWorkspaceStaffCounts */
    const handsList = (model.workers || []).filter(function (w) {
      return w && w.kind !== "citizen" && !actorIsJob(w) && !isWorkspaceOpsWorker(w);
    });
    /* pc-1022: split job roster into staff (kind=job+staff=true) and pure jobs */
    const staffList = (model.workers || []).filter(function (w) {
      return w && actorIsJob(w) && (w.staff === true || w.staff === "true" || w.staff === 1);
    });
    const jobsList = (model.workers || []).filter(function (w) {
      return w && actorIsJob(w) && !(w.staff === true || w.staff === "true" || w.staff === 1);
    });
    /* Workspace-ops hands live on hub ring — also count for presence (Working on now) */
    const wsOpsList = (model.workers || []).filter(function (w) {
      return w && w.kind !== "citizen" && !actorIsJob(w) && isWorkspaceOpsWorker(w);
    });
    const liveHands = handsList.concat(wsOpsList).filter(actorIsLive);
    const walkHands = handsList.concat(wsOpsList).filter(actorIsWalking);
    const laws = (city.root_files || city.root_mds || []).filter(function (f) {
      if (!f) return false;
      /* Workspace-root layer only — AGENTS / PERIMETER / rule pointers at workspace root */
      return isProjectRootLayerLaw(f, root) || isPcLawMd(f.name) || f.pointer;
    });
    /* Prefer unique names at root (no nested path) */
    const lawSeen = {};
    const lawsRoot = canonicalInstructionPapers(laws.filter(function (f) {
      const n = String(f.name || "").toLowerCase();
      if (lawSeen[n]) return false;
      const rel = String(f.rel || f.path || "")
        .replace(root, "")
        .replace(/^\//, "");
      if (rel.indexOf("/") >= 0) return false;
      lawSeen[n] = true;
      return true;
    }));
    /* pc-1095: workspace-root ARCHITECTURE.md on Instructions row */
    const archRoot = (city.root_files || city.root_mds || []).filter(function (f) {
      return isRootArchitecturePaper(f);
    });

    /*
     * ONE place overview (workspace + project share slice grammar).
     * Pulse = nav; body = one slice. No KPI chip row (pulse owns summary).
     * Full agent/WO streams stay on left rails.
     */
    const bodySlice = ensurePlaceBodySurface("workspace", {
      forYou: gold,
      stuck: roll.stuck | 0,
      liveN: liveHands.length,
      isWorkspace: true,
    });
    const items = [];

    function pushWorkspaceProjects() {
      items.push({
        label: "Projects · " + folders.length,
        section: true,
        inert: true,
      });
      if (!folders.length) {
        items.push({
          label: "No projects on map",
          sub: "Adopt a folder or show Managed / Unmanaged",
          empty: true,
          inert: true,
        });
        return;
      }
      folders
        .slice()
        .sort(function (a, b) {
          return openCount(b) - openCount(a);
        })
        .forEach(function (p) {
          const nOpen = openCount(p);
          const nGold = goldFor(p.slug, p.name);
          const hasStore = folderHasDeskStore(p);
          items.push({
            label: p.name || p.slug || "project",
            sub:
              (p.managed ? "" : "unmanaged · ") +
              (hasStore
                ? nOpen +
                  " open" +
                  (nGold ? " · " + nGold + " for You" : "")
                : "no WorkLane store"),
            kind: "folder",
            icon: "folder",
            action: function () {
              openFolderInSuite({ kind: "project", plot: p }, null);
            },
          });
        });
    }

    function pushWorkspaceRosterDoors() {
      items.push({
        label:
          "Roster doors · " +
          handsList.length +
          " · " +
          staffList.length +
          " · " +
          jobsList.length,
        section: true,
        inert: true,
      });
      items.push({
        label: "Full motion lives on left · Agent activities",
        sub: "These doors open one-kind lists · not a second live rail",
        note: true,
        inert: true,
      });
      if (handsList.length) {
        items.push({
          label: "All agents (" + handsList.length + ")",
          sub: "One-kind list · click a name for dig-in",
          icon: "agent",
          action: function () {
            openMapPresenceSeatList(handsList, {
              isJob: false,
              title: name + " · agents",
              meta: handsList.length + " agents workspace-wide",
            });
          },
        });
      }
      if (staffList.length) {
        items.push({
          label: "Staff (" + staffList.length + ")",
          sub: "Function ops seats",
          icon: "staff",
          action: function () {
            openMapPresenceSeatList(staffList, {
              isJob: true,
              title: name + " · staff",
              meta: staffList.length + " staff workspace-wide",
            });
          },
        });
      }
      if (jobsList.length) {
        items.push({
          label: "All jobs (" + jobsList.length + ")",
          sub: "Scheduled automation",
          icon: "job",
          action: function () {
            openMapPresenceSeatList(jobsList, {
              isJob: true,
              title: name + " · jobs",
              meta: jobsList.length + " jobs workspace-wide",
            });
          },
        });
      }
    }

    if (bodySlice === "act") {
      const attNow = lastAtt();
      const forYou = sortForYouByGroupThenUrgency(
        forYouAttItems((attNow && attNow.items) || [])
      ).slice(0, 12);
      renderWorkspaceForYouSection(forYou, gold, items);
      if (!gold && !(roll.stuck | 0)) {
        items.push({
          label: "Nothing to decide right now",
          sub: "Pulse → Projects or Structure · left rails for live work",
          note: true,
          inert: true,
        });
      }
    } else if (bodySlice === "presence") {
      renderWorkingOnNowSection(liveHands, walkHands, items, {
        subFn: function (w, st) {
          var hk = w.homeKey || "";
          var prefix =
            hk &&
            String(hk).indexOf("__") !== 0 &&
            String(hk).charAt(0) !== "/"
              ? String(hk) + " · "
              : "";
          return prefix + (st === "live" ? "live" : "on approach");
        },
      });
      if (!liveHands.length && !walkHands.length) {
        items.push({
          label: "Quiet · no one live",
          sub: "Full roster heat on left · Agent activities",
          note: true,
          inert: true,
        });
      }
      items.push({
        label: "Open Agent activities (left)",
        sub: "Heat-ordered hands · walk before due",
        action: function () {
          try {
            const list = document.getElementById("map-live-list");
            if (list) list.scrollIntoView({ block: "nearest", behavior: "smooth" });
          } catch (e) {}
        },
      });
    } else if (bodySlice === "work") {
      items.push({
        label: "Work orders · workspace",
        section: true,
        inert: true,
      });
      items.push({
        label: openSum + " live open · " + gold + " for You",
        sub:
          (roll.deferred | 0) +
          " deferred · full stream on left Work orders rail",
        note: true,
        inert: true,
      });
      items.push({
        label: "Open live pile (left rail)",
        sub: "Scopes Work orders · newest activity",
        action: function () {
          WoTape.setProjectKey("");
          WoTape.setFilter(normalizeWoFilter("live"));
          if (global.WoTape) WoTape.bustTape();
          if (typeof repaintWoInsights === "function") repaintWoInsights();
          openProjectWorkOrders("all", null, {
            scope: "workspace",
            title: name,
            expectedOpen: openSum,
            expectedGold: gold,
            filter: "live",
          });
        },
      });
      if (gold > 0) {
        items.push({
          label: "Open For You pile",
          sub: gold + " act-now · same as You card",
          action: function () {
            WoTape.setProjectKey("");
            WoTape.setFilter(normalizeWoFilter("for_you"));
            if (global.WoTape) WoTape.bustTape();
            if (typeof repaintWoInsights === "function") repaintWoInsights();
            openProjectWorkOrders("all", null, {
              scope: "workspace",
              title: name,
              expectedOpen: openSum,
              expectedGold: gold,
              filter: "for_you",
            });
          },
        });
      }
    } else if (bodySlice === "jobs") {
      items.push({
        label: "Jobs · " + jobsList.length,
        section: true,
        inert: true,
      });
      if (!jobsList.length) {
        items.push({
          label: "No scheduled jobs",
          sub: "Staff and jobs appear on left when hired",
          empty: true,
          inert: true,
        });
      } else {
        jobsList.slice(0, 12).forEach(function (w) {
          const nf = nextFireMs(w);
          items.push({
            label: actorShortName(w) || w.display || w.name,
            sub: isFinite(nf)
              ? "next " + formatRemain(nf - Date.now())
              : "job",
            icon: "job",
            isJob: true,
            name: w.name,
            action: function () {
              inspectPerson(w);
            },
          });
        });
      }
    } else if (bodySlice === "structure") {
      renderInstructionsSection(lawsRoot, items, "workspace", {
        architectureFiles: archRoot,
      });
    } else if (bodySlice === "roster") {
      pushWorkspaceRosterDoors();
    } else {
      /* projects (default quiet workspace) */
      pushWorkspaceProjects();
    }

    const lawN = lawsRoot.length + archRoot.length;
    const wsPulseHtml = placePulseStripHtml(
      computePlacePulseCells("workspace", null, {
        clickable: true,
        structureCount: lawN,
        projectsCount: folders.length,
      }),
      {
        label: "Place pulse",
        aria: "Workspace place pulse · dig nav",
        selectedId: bodySliceToPulseId(bodySlice),
      }
    );
    /* Same Open / Pin URL chrome as project dig (suite.placeOpen.workspace) */
    const wsOpenHtml = buildPlaceOpenSectionHtml(
      "workspace",
      readPlaceOpenUserPins("workspace"),
      [],
      { scopeLabel: "Workspace entry points" }
    );

    function wsPulseSelect(slice, thenFn) {
      setPlaceBodySlice(slice);
      if (typeof thenFn === "function") {
        try {
          thenFn();
        } catch (eT) {}
      }
      remountPlaceOverview();
    }

    inspectOrbitGroup({
      el: document.getElementById("workspace-badge"),
      kind: "Workspace · overview",
      surface: "workspace",
      title: name,
      meta:
        "pulse nav · one body slice · left rails = motion" +
        (roll.stuck ? " · " + roll.stuck + " stuck face" : "") +
        (roll.flowing ? " · " + roll.flowing + " flowing" : ""),
      skipPaperMeta: true,
      stats: [], /* pulse is the only summary strip */
      formPrefix: wsPulseHtml + wsOpenHtml,
      items: items,
      doors: [
        {
          label: "All work orders (" + openSum + ")",
          primary: true,
          action: function () {
            openProjectWorkOrders("all", null, {
              scope: "workspace",
              title: name,
              expectedOpen: openSum,
              expectedGold: gold,
              filter: "open",
            });
          },
        },
        {
          label: "Open in Finder",
          primary: false,
          action: function () {
            openFolderInFinder({ kind: "workspace" });
          },
        },
      ],
      afterOpen: function (host) {
        bindPlaceOpenSectionShared(host, "workspace", function () {
          remountPlaceOverview();
        });
        bindPlacePulse(host, {
          for_you: function () {
            wsPulseSelect("act", function () {
              WoTape.setProjectKey("");
              WoTape.setFilter(normalizeWoFilter("for_you"));
              if (global.WoTape) WoTape.bustTape();
              if (typeof repaintWoInsights === "function") repaintWoInsights();
            });
          },
          map_work: function () {
            wsPulseSelect("work", function () {
              WoTape.setProjectKey("");
              WoTape.setFilter(normalizeWoFilter("live"));
              if (global.WoTape) WoTape.bustTape();
              if (typeof repaintWoInsights === "function") repaintWoInsights();
            });
          },
          work_orders: function () {
            wsPulseSelect("work", function () {
              WoTape.setProjectKey("");
              WoTape.setFilter(normalizeWoFilter("live"));
              if (global.WoTape) WoTape.bustTape();
              if (typeof repaintWoInsights === "function") repaintWoInsights();
            });
          },
          presence: function () {
            wsPulseSelect("presence");
          },
          jobs: function () {
            wsPulseSelect("jobs");
          },
          structure: function () {
            wsPulseSelect("structure");
          },
          projects: function () {
            wsPulseSelect("projects");
          },
        });
      },
    });
  }

  var InspectWorkspace = {
    init: init,
    show: showWorkspaceDetail,
    renderForYou: renderWorkspaceForYouSection,
  };

  function init(host) {
    if (!host || typeof host !== "object") return InspectWorkspace;
    Object.keys(host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return InspectWorkspace;
  }

  global.InspectWorkspace = InspectWorkspace;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = InspectWorkspace;
  }
})(typeof window !== "undefined" ? window : globalThis);
