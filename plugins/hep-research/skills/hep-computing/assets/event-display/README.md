# Event display templates

Working templates for a Phoenix event display with JSROOT, Plotly and ECharts panels. Copy this folder into the
project and adapt the copies; do not edit or run builds inside the plugin. Read
`../../references/event-displays.md` first. Tested end to end on 2026-10-30, rerun 2026-10-31, with the versions in
`../../references/event-display-facts.md` §1 (`bash run_demo.sh <work dir>`: all steps ok, browser test 9/9).

| File | What it is | Change it when |
|---|---|---|
| `task.md` | Task card to fill before building | Always (one per project) |
| `make_demo_data.py` | Synthetic inputs: a ROOT file with events and a weighted TH1D, per-event and dataset result JSON, a schematic OBJ | Never for real work; it is the demo's stand-in for the project's data and analysis |
| `mapping.example.json` | Branch → collection mapping with unit and limits | For every new ntuple layout |
| `export_events.py` | Events → one Phoenix JSON per event (Hits `Point`/`Line` only) + `export-record.json` | Only for layouts a mapping cannot express |
| `export_histogram.py` | Already-computed results → payloads (jsroot, plotly, echarts) + sidecar; `--self-test`; `--verify-payload` (oracle) | When adding a payload kind; add known-answer tests at the same time |
| `bundle-spec.example.json` | Title, labels, default event, camera, geometry, panels, paths | For every page |
| `build_bundle.py` | Assembles `bundle/`: `bundle.json`, `objects/<sha256>.<ext>`, web files | Rarely |
| `check_bundle.py` | Checks a bundle without a browser (digests, structure, payload oracle, sources with `--spec`, coverage) | Rarely |
| `test_page.py` | Browser test with headless Chromium on loopback | When adding a panel type (its expected readback) |
| `run_demo.sh` | The whole pipeline on synthetic data | Keep it passing; it is the templates' regression test |
| `web/` | Vite project: `index.html`, `src/main.js` (setup), `src/controller.js` (the only event-changing code), `src/panels.js` (panel manager), `src/panels/*.js` (one module per library), `src/objects.js` (digest-checked fetch), `package.json` + `package-lock.json` (pinned) | Layout and style freely; controller, objects and validators only with the facts file at hand |

Payload kinds accepted by `export_histogram.py`: a 1D ROOT histogram (TH1C/S/I/F/D) read with uproot; a
`binned-1d` JSON (`edges`, `contents`, `sumw2` or null, `weighted` (required as `false` for sqrt(N) errors when
`sumw2` is null), `underflow`, `overflow`, labels and units); a `table`
JSON (`categories`, `series` of `{name, unit, values}`) for ECharts. See `make_demo_data.py` for examples of both
JSON kinds.
