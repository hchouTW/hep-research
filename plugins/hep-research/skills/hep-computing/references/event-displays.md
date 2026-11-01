# Event displays and result panels: how to build one, accurately

Use this when a user wants to see events in 3D (Phoenix) and/or already-computed results as charts (JSROOT,
Plotly, ECharts) in a web page. The plugin ships **knowledge and templates**, not a finished tool: you build the
page in the user's project from the templates in `<plugin root>/skills/hep-computing/assets/event-display/`,
adapt them to the request, and prove the result with the checks below. Read
[event-display-facts.md](event-display-facts.md) before changing any template; it records why each rule exists.
Close with [event-display-checklist.md](event-display-checklist.md).

## 1. What you build

```text
project data (ROOT/Parquet)          project results (TH1, binned JSON, tables) — computed by the project, once
        │ export_events.py (mapping)          │ export_histogram.py (serialise only) → payload + sidecar
        ▼                                     ▼
  events/<run>_<subrun>_<event>.json   results/<name>.<integration>.json, <name>.sidecar.json
        └──────────────┬──────────────────────┘
                       ▼ build_bundle.py (+ web/dist from `npm run build`)
  bundle/  index.html  assets/  bundle.json  objects/<sha256>.<ext>     ← static, self-contained, content-addressed
                       ▼ check_bundle.py (no browser) → test_page.py (headless Chromium)
  serve over HTTPS, or plain HTTP on loopback only (never file://, never plain HTTP to another host)
```

The page reads only `bundle.json` and the objects it lists. Every data file is named by its SHA-256, and the page
checks the digest before use.

## 2. Rules that are not negotiable

| # | Rule | Why |
|---|---|---|
| 1 | Results are computed by the project once; the page and the exporters only serialise. Never bin, fit, normalise or accumulate in JavaScript or in an exporter. | The plot must show the analysis result, not a second, unreviewed analysis. |
| 2 | Display numbers (bin centres, widths, error bars, unit factors) come only from the named functions in `export_histogram.py`, checked by its self-test, and every payload has a sidecar. | One place to be wrong, and an oracle that can catch it. |
| 3 | JSROOT is the only library that derives numbers in the browser (positions from the axis, errors from `fSumw2`), because that is ROOT's own semantics. Its input members must equal the source; the stats box stays off. | Copy, do not recompute. |
| 4 | Events are drawn only with the Phoenix-safe subset: `Hits` of type `Point` and `Line`. Never emit `Tracks`. | Phoenix recomputes track parameters in the browser and resamples tracks as smooth curves. |
| 5 | One controller changes the displayed event: it fetches, checks the digest, ignores stale responses, deep-copies, then calls `buildEventDataFromJSON`. Never call `loadEvent`; keep `allowUrlOptions: false`; remove `window.EventDisplay`. | Every other path can show the wrong event without an error. |
| 6 | Refuse rather than guess: unknown units, non-finite values, weighted histograms without Sumw2 (unless errors are explicitly disabled), histogram members that change meaning, over-limit samples. Missing per-event results are "unavailable", never zero. | A silent fallback is a wrong plot that looks right. |
| 7 | Keep every status label (`synthetic`, `unvalidated`, `user-supplied`, …) on the page; never call a display scientifically validated. | Execution success is not scientific validity. |

## 3. Decide what the request needs

| The user wants | Do |
|---|---|
| A first page for a project | §4 in full |
| Other events | Rerun §4 step 2 into a new folder with `--entries` or `--events`, then steps 5–7; the web build is reused |
| Other panels, layout, camera, title | Edit the bundle spec and rerun §4 steps 5–7 |
| A new result as a chart | Have the project produce the result (TH1, `binned-1d` or `table` JSON), then §4 step 3 for it, add a panel to the spec |
| A collection or branch layout the mapping cannot express | Write a project exporter that outputs the same event JSON (Hits Point/Line); keep the export record |
| A chart type not in the templates | Add a panel module (§5); its validator, readback and test are part of the change |
| Phoenix's standard Angular UI (detector tree, collection info) | §6; larger build, more entry points to close |
| The page on a machine without Node (e.g. a cluster) | Build `web/dist` where Node exists; copy the built `dist` (platform independent) and run the Python steps there |
| TH2, TEfficiency, TGraph, fits drawn on top, glTF or TGeo geometry | Not covered by the templates: say so, then extend deliberately (§5) with its own checks |

If the request is ambiguous about which results to show, which events, or whether data may leave the project
(policy), ask first. For durable work, fill `assets/event-display/task.md` before building. Given a filled task
card, run §4 to the end without further questions unless one of the card's stop rules applies; then report with
the checklist.

## 4. Build, step by step

Copy `assets/event-display/` into the project (for example `display/`); edit the copies, never the plugin. Run
`bash run_demo.sh <work dir>` once to confirm the toolchain on this machine (needs Python with numpy, uproot,
awkward, playwright and its Chromium, plus Node and npm; pyarrow only for Parquet event input).

| Step | Command (from the copied folder) | Done when |
|---|---|---|
| 1. Inputs | Identify the event file(s), the results to show, units and coordinate frame. Check the project's policy (`hep-research.project.json`, blinding) before exporting anything. | You can name every branch, its unit, and each result's producer. |
| 2. Events | Write a mapping like `mapping.example.json`, then `python3 export_events.py DATA.root --mapping mapping.json --out work/events --status <label> [--entries A:B or --events RUN_SUBRUN_EVENT,...]` (the output folder must be new or empty) | `status: ok`; `export-record.json` lists exactly the selected events with sha256; count ≤ `max_events` (checked before coordinates are read). |
| 3. Results | `python3 export_histogram.py --root FILE --object NAME --integration jsroot --out work/results` (or `--json RESULT.json --integration plotly` / `echarts`). Event-level results: one output folder per event key. A `binned-1d` JSON without `sumw2` must say `"weighted": false` to get sqrt(N) error bars; otherwise it is refused. | `status: ok`, or a refusal you resolve upstream (never by editing the payload). |
| 4. Web | `cd web && npm ci && npm run build` (`npm ci` installs exactly the shipped `package-lock.json`; use `npm install <pkg>` only to change a dependency, then commit the new lockfile and rerun steps 6–7). | `web/dist/index.html` exists; build log shows one lazy chunk per chart library used. |
| 5. Bundle | Edit `bundle-spec.json` (title, labels, default event, camera, geometry, panels, and each panel's `source`: `{"root": FILE, "object": NAME}` or `{"json": FILE}`, `{key}` allowed), then `python3 build_bundle.py bundle-spec.json` | `status: ok`; coverage shows any events without results. |
| 6. Check | `python3 check_bundle.py bundle --spec bundle-spec.json` and `python3 export_histogram.py --self-test` | Both `ok`: digests, no unlisted objects, relative paths only, every payload equals its sidecar's derivations, every sidecar equals a fresh read of its source; `unchecked_sources` is empty. |
| 7. Browser | `python3 test_page.py bundle` | All checks `ok` (default event, panels' readback = payload, rapid switching ends on the last event, tampered object refused, no external request, no page error). |
| 8. Deliver | Serve with `python3 -m http.server -d bundle --bind 127.0.0.1 8000` for one machine, or put `bundle/` on an HTTPS server for others (the digest check needs a secure context: plain HTTP to another host shows "failed to start"); package the `bundle/` folder as is. Record a `computational-run` (inputs with sha256, commands, tool versions, outputs). | The user can open the page; labels and coverage gaps are visible; the run record exists. |

Tested end to end with the versions in [event-display-facts.md §1](event-display-facts.md).

## 5. Extending the templates

**A new chart integration or panel type** (in `web/src/panels/<name>.js`, registered in `MODULES` in
`web/src/panels.js`). It must export:

- `validate(payload)`: an allowlist of keys and types; reject anything that computes in the browser (binning,
  stacking, normalisation, statistic error types, transforms).
- `mount(element, payload)` → `{ readback(), dispose() }`: `readback()` returns what the library actually holds
  for the values that matter; `dispose()` releases listeners, observers and the library's own state.
- optionally `note(payload)`: text for the panel (flow not drawn, errors disabled, …).

Add the payload builder and its derivation functions to `export_histogram.py` (or a sibling exporter) with
hand-written known-answer tests in `--self-test`, a `--verify-payload` branch, and the expected readback in
`test_page.py`. Only then add the panel to a spec.

**A new event collection**: keep to `Hits` `Point`/`Line` when you can (a ring is a closed polyline; a cell can
be drawn as its outline). Other Phoenix types (`CaloCells`, `Jets`, `Tracks`, …) need a deliberate check of what
Phoenix computes from them; see the facts file.

**Geometry**: the template loads OBJ in mm through `parseOBJGeometry` after a digest check. Convert units
upstream and label schematic geometry as such; a run name is not evidence of the right conditions.

## 6. Phoenix standard UI (optional)

`phoenix-ui-components` adds the Angular UI (detector tree, collection tables, menus). It pins Angular 20, so keep
`@angular/core` at 20.x everywhere. Its event selector calls `loadEvent`, and it has file-loading dialogs: replace
the selector with one driven by the controller, remove the dialogs, and extend `test_page.py` to prove no event
can change outside the controller. Budget for a much larger build; do not maintain two equivalent UIs.

## 7. What the checks prove, and what they do not

They prove: files are intact and are the ones exported; chart values equal the exported values, which equal the
source at the time of the check (with `--spec`); the page shows the selected event and refuses tampered data; nothing is fetched from outside. They do not
prove that the analysis, the mapping, the units or the geometry are physically right. That needs the project
owner's review; say so in the delivery.
