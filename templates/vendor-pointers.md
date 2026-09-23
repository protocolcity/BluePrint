# Provider instruction pointers

Keep instructions in canonical `AGENTS.md` files. Codex, Claude, Grok, Cursor and
other clients can participate through their supported instruction mechanisms;
verify those mechanisms for the installed client/version.

When a client supports an import file, point it to `AGENTS.md`. For example, a
supported `CLAUDE.md` import can contain:

```
@AGENTS.md
```

A client may instead read `AGENTS.md` directly, follow an explicitly configured
path, or need a generated copy. Do not assume a file named `GROK.md` or a symlink
is loaded by every client. Verify with a bounded run before enabling dispatch.
Keep provider-only connection settings separate from shared product rules.

BP founding tools may create pointer files; the current Doctor can report
missing or divergent pointers and add supported missing pointers with explicit
repair. Existing files are preserved. Read the installed command's help for the
exact repair option. A generated pointer does not establish provider access,
model availability, quota, tools or permission to run.
