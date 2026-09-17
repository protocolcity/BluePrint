# protocolcity (compat alias)

**Preferred install name:** [`protocolcity-blueprint`](https://pypi.org/project/protocolcity-blueprint/)

This package is a **forever-compat alias**. Installing it pulls the full
BluePrint suite (`protocolcity-blueprint`) at the same version. The taught
CLI is **`blueprint` only**.

```bash
# preferred
pip install --upgrade 'protocolcity-blueprint[engines]'

# still works (this package)
pip install --upgrade 'protocolcity[engines]'
```

Import package is always `import protocolcity` (never renamed).
