# Running Map V1 — dogfood steps

The V1 shell is dogfoodable stand-alone before it lands in the BluePrint
pip package. Two paths: **local dev tree** and **Cellar / brew install**.

## Local dev tree

Point the tiny server at any folder — your BluePrint checkout is a fine
first binder:

```bash
# from the BluePrint repo root
python3 map/v1/serve.py --binder . --port 8801
# → http://127.0.0.1:8801/  (workspace_map.html)
```

Then in the browser:

1. **DoD 1 — hub + lots paint.** The binder name shows in the center; each
   top-level folder + root `.md` becomes a lot around it.
2. **DoD 2 — pan · zoom · reset.** Drag on empty space to pan. Wheel to
   zoom (clamped 0.5×–4×). Click **Reset** in the top-right; camera and dig
   both snap back.
3. **DoD 3 — dig.** Click a folder lot. The `#dig-in-layer` fans children;
   the top chrome trail shows `<binder> › <lot>`. Click a child folder to
   dig deeper; **Backspace** pops one trail level.
4. **DoD 4 — MD reader.** Click a `.md` lot (root or dig-in). Overlay opens,
   server renders markdown → HTML. `Esc`, `×`, or backdrop click closes it.
   The reader does **not** touch dig state.
5. **DoD 5 — View Options.** Top-left `View` panel toggles
   Managed / Unmanaged / Hidden. Lots repaint immediately; state lives in
   `MapViewState`, not a second store.
6. **Hit SoT.** Only one classifier decides where hits land — verify by
   confirming panning does not fire while the reader is open, chrome
   buttons never eat lot clicks, and dig-in children win over the lot they
   were fanned from.

## Cellar / brew install path

BluePrint installs via `brew install protocolcity/tap/blueprint`, which
lays the pip package under a Homebrew Cellar prefix (e.g.
`$(brew --prefix)/Cellar/blueprint/<ver>/libexec`). Once the BluePrint BFF
serves the three V1 endpoints (see [`README.md`](./README.md)
§Consuming), the shell is reachable at:

```
blueprint serve --root ~/BluePrint --with-engines
# → http://127.0.0.1:8801/workspace-map
```

Until then, the stand-alone `map/v1/serve.py` above is the dogfood path.

### Manually vendoring into a Cellar checkout

If you need to preview the shell against a Cellar-installed BluePrint before
the BFF ships the endpoints:

```bash
BP=$(brew --prefix)/Cellar/blueprint/*/libexec
cp -R map/v1 "$BP/blueprint_map_v1"
python3 "$BP/blueprint_map_v1/serve.py" --binder ~/BluePrint --port 8802
```

This does not replace the installed `blueprint serve` command — it just
runs the V1 shell on a second port against the same binder folder.

## Tests

```bash
python3 -m unittest discover -s map/v1/tests -v
```

The suite runs in <1s and covers:

- Server projection (`build_tree`, `children_at`, `render_file`) — 12 tests.
- Hit-Layer SoT row order pinned in JS — 4 tests.
- DoD 1-4 smoke against the fixture binder — 3 tests.

If `test_hit_router_table` fails, the six-row order in
`static/js/map-hit-router.js` has drifted from the Glass spec — either fix
the code or amend the Glass and update the test.

## What to do when a peel breaks a row

1. Revert the peel; V1 rows are law until the shell is called done.
2. Open the row's DoD note in [`docs/specs/MAP_V1_GLASS.md`](../../docs/specs/MAP_V1_GLASS.md)
   §Definition of Done and confirm which row regressed.
3. Move the offending module back to the DEFERred list until the peel is
   redesigned.

## Non-goals when running

- Do **not** point the dogfood server at a workspace that hosts secrets —
  `/api/file` serves any readable file under the binder root by design.
  Use a scratch folder or a public repo checkout for demos.
- Do **not** wire in the pre-V1 `workspace_map_app.js` (the 28k-line host).
  That file is not in this repo; if you find yourself importing it you are
  in a different peel.
