# Settings INTENT — what this browser prefers, what this desk is running

Status: design record for pc-1481, 2026-09-13. Owning implementation order: pc-1491 (shared shell and readers). Companion to [OPERATIONS_EVOLUTION_2026_09.md](OPERATIONS_EVOLUTION_2026_09.md) and [SURFACES_REVIEW_2026_09.md](SURFACES_REVIEW_2026_09.md).

## One sentence

Settings holds the few things a person can change about how BluePrint behaves in this browser, and states plainly what build is running against which workspace and how it stays current; it never configures agents, engines or the host.

## Is / Is-not

| Settings IS | Settings IS NOT |
|---|---|
| Browser display preferences saved in this browser only: fallback refresh interval, motion | A roster editor, a scheduler, a place to set stop files or supervisor scope (host configuration, kept out on purpose) |
| The running-build statement: package version, workspace path, how updates arrive (live change feed with a fallback poll) and the current state of that connection | A second Connections page; source health lives on Connections and is linked |
| Honest about storage: "Saved in this browser" or "Applied for this page; browser storage is unavailable" | A cloud account, sync or profile surface |

## Primary hierarchy

```
SETTINGS
  Display preferences (this browser)
    Fallback refresh   [Every 15 s ▾]   used only while live updates are disconnected
    Motion             [Follow system ▾]   Reduce motion turns off transitions everywhere
    Saved in this browser.

  This desk
    Workspace        /path/to/workspace
    Running build    0.1.47+consolidation.47 · installed Sep 13 06:40
    Updates          Live · connected 12 min ago   (or: Disconnected · polling every 15 s)
    Data access      Local reads; work-order changes through WorkLane
    → Inspect connections and source freshness
```

## Sources

| Fact | Source |
|---|---|
| Preferences | `localStorage` key `bp-display`; system `prefers-reduced-motion` when Motion is "Follow system" |
| Running build | installed package metadata (`/api/operations` build) and the workspace deployment receipt for the install time; never a Homebrew formula version |
| Updates state | the change-feed connection state the page already tracks (open, reconnecting, polling) |

## Rules

- Keep the fallback interval preference: the live feed is the normal path and the interval is what the page uses when that connection is down. The copy must say so; the audit confirmed it does.
- Reduce motion here and the OS setting are the same switch for every surface (STATES_AND_TERMS motion contract).
- Settings shares the shell: at 400px the active Settings tab must be visible in the navigation without horizontal discovery (pc-1491 mobile navigation). Implemented via scroll-padding on `.bp-nav` and `ensureActiveNavVisible()` when a tab carries `aria-current="page"`.
- Nothing on this page sends a request that changes the workspace.

Held: appearance themes (BluePrint dark is the only register), account or profile, notification channels, host configuration.
