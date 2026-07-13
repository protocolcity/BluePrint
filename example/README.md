# Example — the Riverside city

A complete, minimal city: one root, one neighborhood, one worker — every
template from [`templates/`](../templates/) filled in for a fictional
operator ("Riv") who runs a recipe website and wants one agent working the
backlog. This is [FOUNDING.md](../FOUNDING.md) executed end to end.

```
riverside/                    ← city root
├── AGENTS.md                 ← L0 city law (registry, rules, gates)
└── recipes-site/             ← the one neighborhood
    ├── AGENTS.md             ← L1 neighborhood law
    ├── CLAUDE.md             ← vendor pointer (@AGENTS.md)
    └── workers/
        └── claude-recipes/
            ├── CONTRACT.md   ← L2 employment contract
            └── prompt.md     ← L3 shift instructions
```

Compliance check (Charter §4): law written ✓ (both AGENTS.md), work
ticketed ✓ (store `recipes`, orders `rs-*`), workers sign ✓ (identity
`claude-recipes`). Riverside is a city.

Start reading at [`AGENTS.md`](AGENTS.md) and follow the pointers down —
that's exactly what an agent would do.
