---
name: Bug report
about: Something broke while using the installed suite
title: "[bug] "
labels: ["bug"]
---

## Versions

Paste output of:

```bash
blueprint feedback
# or:
brew list --versions blueprint 2>/dev/null
pip show protocolcity-blueprint protocolcity-worklane protocolcity-workforce 2>/dev/null | grep -E '^(Name|Version)'
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
(suite / worklane / workforce / citylens), or the block from `blueprint feedback`.

## Surface

- [ ] Suite shell (Overview / Map / Settings) — this BluePrint repo
- [ ] Work orders (Desk / wl_*) — WorkLane
- [ ] Agents (Roster / hire / daemon) — WorkForce
- [ ] Homebrew formula only — homebrew-tap
