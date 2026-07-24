---
name: Bug report
about: Something broke while using the installed suite
title: "[bug] "
labels: ["bug"]
---

## Versions

Paste output of:

```bash
protocolcity feedback
# or:
brew list --versions protocolcity 2>/dev/null
pip show protocolcity protocolcity-worklane protocolcity-workforce 2>/dev/null | grep -E '^(Name|Version)'
```

- macOS version:
- Python version (if pip):

## What happened

Steps to reproduce:

1.
2.

Expected:

Actual:

## Logs

Paste the last ~30 lines from `<workspace>/.protocolcity/logs/` if present
(suite / worklane / workforce / citylens), or the block from `protocolcity feedback`.

## Surface

- [ ] Suite shell (Overview / Map / Settings) — this BluePrint repo
- [ ] Work orders (Desk / tk) — WorkLane
- [ ] Agents (Roster / hire / daemon) — WorkForce
- [ ] Homebrew formula only — homebrew-tap
