# Vendor pointers (optional)

The canonical law file is always `AGENTS.md` — one law, every vendor reads
it. Vendor-specific files are **optional**: add them only when a vendor CLI
needs its own filename. When present, they must be thin pointers, never
content.

Missing a vendor file is fine — Office does not treat empty drawer wood as a
to-do. When a vendor file *is* present, it must be a thin pointer (or it is
**DIVERGED** and needs MERGE/CONVERT, never a second law body).
`protocolcity found` / `adopt` / `doctor --fix` do **not** plant these files.

**Claude Code** — create `CLAUDE.md` containing exactly one line:

```
@AGENTS.md
```

**Cursor / Codex** — nothing to do: both read `AGENTS.md` natively.

**Grok / xAI tooling** — either form is valid:

```
ln -s AGENTS.md GROK.md
```

or a one-line file containing only `@AGENTS.md`.

**Anything else** — same idea: find where the tool looks for instructions
and point it at `AGENTS.md`. If a tool forces you to copy content instead of
pointing, treat that copy as generated: regenerate it from `AGENTS.md`,
never edit it directly.

The rule this preserves: when the law changes, it changes in one file.
Personalized vendor instructions do not belong in `CLAUDE.md` / `GROK.md` —
fold them into `AGENTS.md` (or a worker `CONTRACT.md` / `prompt.md`), then
keep the vendor file as a pointer.
