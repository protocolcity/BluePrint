# Vendor pointers

The canonical law file is always `AGENTS.md` — one law, every vendor reads
it. Vendor-specific files are pointers, never content. Set them up once per
folder that has an `AGENTS.md`:

**Claude Code** — create `CLAUDE.md` containing exactly one line:

```
@AGENTS.md
```

**Cursor / Codex** — nothing to do: both read `AGENTS.md` natively.

**Grok CLI** — symlink it:

```
ln -s AGENTS.md GROK.md
```

**Anything else** — same idea: find where the tool looks for instructions
and point it at `AGENTS.md`. If a tool forces you to copy content instead of
pointing, treat that copy as generated: regenerate it from `AGENTS.md`,
never edit it directly.

The rule this preserves: when the law changes, it changes in one file.
