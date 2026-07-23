# Example — minimal workspace (Riverside)

A complete, minimal workspace: one root, one project, one agent — every
template from [`templates/`](../templates/) filled in for a fictional
operator ("Riv") who runs a recipe website and wants one agent working the
backlog. This is [FOUNDING.md](../FOUNDING.md) executed end to end.

```
riverside/                    ← workspace root
├── AGENTS.md                 ← workspace instructions
└── recipes-site/             ← the one project
    ├── AGENTS.md             ← project instructions
    ├── CLAUDE.md             ← vendor pointer (@AGENTS.md)
    └── workers/
        └── claude-recipes/
            ├── CONTRACT.md   ← agent job (standing role)
            └── prompt.md     ← this-run instructions
```

Set up well when: instructions exist ✓ (both AGENTS.md), work is tracked ✓
(work orders), agents sign ✓ (identity `claude-recipes`).

Start reading at [`AGENTS.md`](AGENTS.md) and follow the pointers down —
that's exactly what an agent would do. In the suite, the same tree appears
as the **workspace map**.
