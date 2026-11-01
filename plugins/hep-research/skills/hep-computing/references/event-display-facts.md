# Event display facts and pitfalls

Each entry says how it was established: **run** (exercised by the templates on 2026-10-30) or **source** (read in
the library's source on 2026-10-29/30: Phoenix at commit `2329146`, JSROOT 7.11.0, ROOT `TH1.cxx`). Versions move;
before relying on an entry with a different version, recheck it as the last column says. When an entry is wrong
for the version in use, fix the template and this file together.

## 1. Tested toolchain (run, 2026-10-30)

| Component | Version | Note |
|---|---|---|
| Python | 3.13.18 | numpy 2.5.4, uproot 5.7.7, awkward 2.14.0, Playwright for Python 1.63.0 with its bundled Chromium |
| Node / npm | 22.23.4 / 10.9.9 | `npm ci` from `web/package-lock.json` (≈ 93 KB) |
| phoenix-event-display | 4.2.3 | pulls three 0.184.0 (nested), jsroot ^7.11.0, dat.gui, jszip, html2canvas, tween.js |
| jsroot | 7.12.0 | one copy, shared by Phoenix and the JSROOT panel (`npm ls jsroot` shows "deduped"); brings its own three 0.162.0 |
| @angular/core, rxjs | 20.3.30, 7.8.2 | needed even without the Angular UI (see §2) |
| plotly.js-basic-dist-min | 4.1.2 | bar and scatter only |
| echarts | 6.1.0 | `echarts/core` with only BarChart, Grid, Legend, Title, Tooltip, Canvas registered |
| vite | 7.3.7 | `base: './'`; build ≈ 30 s; bundle ≈ 9 MB, largest chunks: Phoenix+three+JSROOT core 3.5 MB, three addons 2.5 MB, Plotly 1.2 MB (lazy), ECharts 0.5 MB (lazy) |

## 2. Building

| Fact | How known | Consequence / recheck |
|---|---|---|
| `phoenix-event-display` 4.2.3 imports `EventEmitter` from `@angular/core` in `dist/managers/three-manager/index.js` but does not declare Angular as a dependency; a plain Vite build fails with "failed to resolve import @angular/core". | run | Install `@angular/core` 20.x and `rxjs` explicitly. Recheck: `grep -rn "@angular" node_modules/phoenix-event-display/dist --include=*.js` (ignore `dist/bundle/`). |
| The package also ships `dist/bundle/phoenix.min.js`, a webpack bundle that contains its own JSROOT. | source | Import `phoenix-event-display` (resolves to `dist/index`, ESM), never the bundle, or JSROOT is loaded twice. |
| `phoenix-ui-components` pins Angular packages at `^20` as dependencies. | source | Keep Angular at 20.x. Angular 20's support window ends around the end of 2026: check angular.dev and whether Phoenix moved to 21 before upgrading. |
| Two copies of three.js end up in the build (0.184 for Phoenix, 0.162 for JSROOT). | run | Expected; size only. Do not force one version: JSROOT's geometry builder and Phoenix were tested with their own. |
| A lockfile created on one platform can miss native optional packages (esbuild/rollup binaries) for another. | source (npm issue) | Run `npm ci` on each platform you build on; or build once and copy `web/dist`, which is platform independent. |
| Playwright for Python only works with the browser build of the same Playwright version. | run | After `pip install playwright`, run `python -m playwright install chromium`, or use a Chromium path via `--chromium` / `HEP_CHROMIUM`. |
| The packaging check of hep-research (`check_packaging` in `tools/`) rejects any single file over 2 MiB. | source | Never put `node_modules`, `dist` or large data into the plugin; the lockfile is far below the limit. |

## 3. Phoenix behaviour

| Fact | How known | Consequence / recheck |
|---|---|---|
| `buildEventDataFromJSON(event)` builds synchronously and fires `onDisplayedEventChange` synchronously, but builds nothing unless `configuration.eventDataLoader` is set (only `parsePhoenixEvents` sets it by default). | source, run | Pass `eventDataLoader: new PhoenixLoader()` to `init`. |
| `loadEvent(key)` silently does nothing for an unknown key once events were parsed, and throws before any parse. | source | Never call it; the controller checks the key and calls `buildEventDataFromJSON`. |
| URL options (loading files, configs from the query string) are on unless `allowUrlOptions === false`. | source | Always pass `allowUrlOptions: false`. |
| `init()` exposes `window.EventDisplay` (`loadGLTFGeometry`, `emit`, `scene`, …) for the console. | source, run | `delete window.EventDisplay` after `init`; the browser test checks it. |
| Calling `init()` again calls `cleanup()`, which empties the `onDisplayedEventChange` listeners. | source | Reattach the controller's listener after every `init`. |
| Phoenix writes `uuid` and other fields into the event object it is given. | source | Pass `structuredClone(event)`; keep the fetched object pristine. |
| Keyboard previous/next event use `eventsData`, which stays unset when events are never parsed. | source | With the controller pattern they do nothing; keep it that way. |
| `Tracks`: Phoenix fills phi/eta/d0/z0/dca/angle from the first points when missing (a provided 0 is overwritten: `!track.phi`), redraws the track as a `CatmullRomCurve3` spline, and writes `tid`/`uuid` back. | source | Do not emit `Tracks`; draw sampled trajectories as `Hits` `Line` segments. If fitted tracks are ever needed, label the derived values as Phoenix's. |
| `Hits`: an array of `{pos, type, color}`; `type` is read from the first item: `Point` (3 numbers), `Line` or `Box` (6 numbers); one colour per collection (the first item's); `Point` size is fixed (10 world units). Positions go into a `Float32Array`. | source | One collection per style. Expect float32 rounding of drawn coordinates; compare positions with float32 tolerance, never bit for bit. Large detectors make points tiny: use `Box` or collection colour for emphasis. |
| `enableDatGUIMenu: true` gives geometry and collection toggles without Angular. | run | The minimal template uses it. |
| Object types registered: Tracks, Jets, Hits, CaloClusters, CaloCells, PlanarCaloCells, IrregularCaloCells, Muons, Photons, Electrons, Vertices, MissingEnergy. Loaders exist for EDM4hep JSON, JiveXML, TrackML and several experiment-specific formats. | source | Before using another type, read what its builder computes in `loaders/objects/phoenix-objects.ts`. The other loaders were not tested here. |
| Geometry: `loadOBJGeometry`, `parseOBJGeometry`, `loadGLTFGeometry`, `loadJSONGeometry`, `loadRootJSONGeometry`, `loadRootGeometry` (the last two read TGeo through JSROOT and set JSROOT's global `settings.UseStamp=false`). | source | The template uses `parseOBJGeometry` on digest-checked text. TGeo is possible but untested here: check cm→mm, node limits and the global setting first. |

## 4. JSROOT

| Fact | How known | Consequence / recheck |
|---|---|---|
| `createHistogram('TH1D', n)` makes a TH1D with `fArray` of n+2 cells; copying members into it and calling `draw(el, h, opt)` renders it. | run | The JSROOT panel copies members only. |
| JSROOT computes error bars in the browser: `sqrt(fSumw2[bin])`, or `sqrt(abs(content))` without Sumw2 (as ROOT `GetBinError` does for `kNormal`). Bin positions come from `fXaxis`. | source | Unweighted without Sumw2 is fine; weighted without Sumw2 draws wrong errors: refuse or draw without errors (`hist`). |
| ROOT's `"title;x title;y title"` convention is not parsed when members are copied: the whole string shows as the title. | run | Split it in the exporter (done in `export_histogram.py`). |
| The painter may change `fXaxis.fFirst`/`fLast` while drawing. | source | Leave them out of readback comparisons. |
| A TH1 filled with `SetBinContent` and no Sumw2 has `fTsumw == fTsumw2 == 0` while `fEntries > 0`; ROOT and JSROOT then draw sqrt(\|content\|), which is meaningless for a ratio, rate or cross section. | source | `export_histogram.py` draws sqrt errors without Sumw2 only for `fTsumw == fTsumw2 > 0` (unit-weight fills), and for a `binned-1d` JSON only with `"weighted": false`; anything else is refused unless `--errors disabled`. |
| Members that change what is shown: `fBinStatErrOpt` (Poisson errors), `fNormFactor`, `fFunctions` (drawn fits), `fMaximum`/`fMinimum`, axis range, `fOption`; an unflushed `fBuffer` means the contents are incomplete. | source | The exporter refuses non-default values; extend deliberately if needed. |
| `draw` option `nostat` turns the statistics box off. | run | Keep it off unless the box's numbers are checked against the source. |

## 5. Plotly and ECharts

| Fact | How known | Consequence / recheck |
|---|---|---|
| Plotly traces of type `histogram*`, attributes `histfunc`, `histnorm`, `cumulative`, `barnorm`, `error_y.type` `sqrt`/`percent`/`constant`, and `barmode` `stack`/`relative` compute in the browser. | source (docs) | The Plotly validator allows `bar` with `error_y.type: "data"` only. |
| After `Plotly.react`, the element's `data` holds the arrays Plotly uses. | run | Readback compares `x`, `y`, `width`, `error_y.array` with the payload. |
| Plotly and ECharts have no place for underflow/overflow. | — | The payload carries them; the panel note shows them when non-zero. |
| ECharts dataset transforms (`filter`, `sort`, registered transforms) and series `stack` compute in the browser. | source (docs) | The ECharts validator allows title, tooltip, legend, xAxis, yAxis and bar series with name and data only. |
| `chart.getOption()` returns the option ECharts holds. | run | Readback compares categories and series data. |
| ROOT LaTeX-like titles (`p_{T}`) render in JSROOT, not in Plotly or ECharts. | run | Write plain titles for those panels. |

## 6. Serving and data

| Fact | How known | Consequence / recheck |
|---|---|---|
| Chromium blocks `fetch` and dynamic `import()` under `file://`. | source | Serve over HTTP (loopback is fine); never promise double-click opening. |
| `crypto.subtle` (used for digest checks) needs a secure context: `https` or `http://127.0.0.1`/`localhost`. | source (web platform); loopback run | On a remote plain-HTTP server the digest check fails: serve over HTTPS, or accept that the page stops with an error. |
| uproot: `tree.arrays()` regroups dotted branch names (`hit.x`) into records. | run | Read branch by branch (`tree[name].array()`), as `export_events.py` does. |
| uproot reads TH1 members exactly as stored; PyROOT `TH1::GetStats` can recompute statistics (`fTsumw == 0 && fEntries > 0`, or with an axis range). | source | Identity and sidecars use uproot's stored members. |
| JSON floats written by Python's `json` (shortest repr) round-trip exactly into JavaScript numbers; NaN and Infinity are not JSON. | run | Bit-exact payload/readback comparisons are valid; exporters refuse non-finite values. |
