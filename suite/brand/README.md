# BluePrint mark (pc-1285)

Locked 2026-08-19. Inset T-house, door as a box, eaves past the walls.
Map folder silhouette (left tab). No swings, no dimension ticks.

| File | Paint | Where |
|---|---|---|
| `mark-cyanotype.svg` | Manila tab, Prussian body, cream drawing | Spine (default) |
| `mark-cream.svg` | Cream folder, Prussian drawing | Spine when `suite.spinePaint=cream`; Settings About |
| `favicon.svg` | Cyanotype on paper tile | Browser tab (cyanotype paint) |
| `lens-overview.svg` · `lens-map.svg` · `lens-calendar.svg` · `lens-settings.svg` | Black stroke (CSS-masked to ink) | Collapsed spine peek (pc-1298) |

Settings → About **Spine paint** (pc-1291) persists `suite.spinePaint` (`cyanotype` \| `cream`) in this browser and repaints `.suite-spine-mark` plus `link[rel=icon]`. Cyanotype remains the shipped default.

`--prussian: #1b4a73` in `suite.css`. Do **not** retint Finder-blue selection (`#007AFF`).
ProtocolCity foot lockup is unchanged.
