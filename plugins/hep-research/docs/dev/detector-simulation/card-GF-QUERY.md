# Task card GF-QUERY — electron drift velocity on one pinned gas table (pinned in W2-GF)

Specification: `TASK.md` §12.3. Every tolerance and criterion below was fixed on 2026-11-01, before any query was
run, and is never relaxed afterwards. Pipeline validation only: the result is not physics validation and the table is
not reference data.

| Field | Pinned value |
|---|---|
| Capability | `garfield.gas-table-query`, version 1; state `proposed` until W4G |
| Backend | Garfield++ `master` commit `e2e58ea74ec8b20d347d78b7a769f40e3b156072` (2026-10-28, CMake project version 0.3), the commit the specification read; source `https://gitlab.cern.ch/garfield/garfieldpp.git`, blob-less clone in `WR/upstream/garfieldpp` |
| Environment | source build of that commit against Homebrew ROOT 6.40.04 and GSL on macOS 27.2 arm64 (`WR/env/build_garfield.sh`, install in `WR/env/garfield/install`); identity = the manifest digest recorded by `detsim check --probe` (§9.1): Garfield++ commit, ROOT version, build options, SHA-256 of the installed `libGarfield` and of the query script. See "Environment record" below (V-13) |
| Query method | Python query script loading Garfield++ through ROOT's Python bindings (`gSystem.Load` of the installed library, then `ROOT.Garfield.MediumMagboltz`), a rendered file in the plan (V-13) |
| Table | `Examples/GasFile/ar_80_co2_20_0T.gas` at the pinned commit; SHA-256 `ba4357348c211812b40f982b979df34bf02738855ee6a1ba58555c35d196b732`; 266 lines; header `Version : 12`, `Identifier: CO2 20%, Ar 80%, T=300 K, p=1 atm`, created 30/11/12; `Dimension : F 30 1 1 9 2` (1D: 30 E points, one angle, one B, 9 excitation and 2 ionisation rates); E/p grid 0.13157895 … 105.26316 V/(cm·Torr); B grid {0}; `PGAS = 760` Torr, `TGAS = 300` K; footer `Interp 2`, `L Extr 0` (constant), `H Extr 1` (linear) for the velocity (index 0). Used under H0 #13: local input only (never committed, never a test fixture; recorded by path, commit and hash) and pipeline validation only. Run records and observables carry the note "example table, pipeline validation only" |
| Licence | none stated (no licence file at the repository root; only `NeBem/Copyright.md`); use accepted by the H0 #13 default |
| Storage form (V-10) | E stored as E/p in V/(cm·Torr); `LoadGasFile` multiplies by `m_pressureTable` (Torr) (`MediumGas.cc:560`). Records: each 1D record is read by `ReadRecord1D` (`MediumGas.cc:837-876`): `ve, waste, vb, waste, vx, waste, dl, waste, dt, waste, alpha, waste, alpha0, eta, waste, mu, waste, lor, waste, dis, waste, 6 × (dif, waste), nexc × (rexc, waste), nion × (rion, waste)`, then the version ≥ 13 or GASOK-bit columns (absent here: version 12, bits 16–19 F); velocities × 1e-3 (cm/µs → cm/ns, lines 848-850; the 3D reader's lines 796-798 do the same). Numbers are fixed-width and may touch (`0.00000000E+00-0.30000000E+02`), so the independent parser tokenises with the regular expression `[-+]?\d+\.\d+E[-+]\d+`: 55 numbers per record, 1650 in all |
| Temperature and pressure (V-12) | `LoadGasFile` sets `m_pressure = m_pressureTable = PGAS` and `m_temperature = m_temperatureTable = TGAS` (`MediumGas.cc:555-556`); only T = 300 K and p = 760 Torr are allowed in a task, anything else is refused with `condition-mismatch`; after loading, the script asserts `GetPressure() == 760` and `GetTemperature() == 300` |
| Interpolation (V-11) | `Medium::Interpolate` → `Interpolate1D` for a 1D table (`Medium.cc:1419-1437`); `Interpolate1D` (`Medium.cc:1439-1545`): x < 0 → 0; one node → that value; x < first node → low extrapolation; x > last node → high extrapolation; else order 1 → `Numerics::LinearInterpolation` (`Numerics.cc:1756-1765`), order ≥ 2 → `Numerics::Divdif` (`Numerics.cc:1658-1754`, stencil as §12.3: m = min(order, 10, n−1); nodes ix, ix+1, ix−1, ix+2, …; even m averages the two highest differences when m+2 nodes exist, else m+1; returns the stored value within 1e-6 of the end spacing at the first and last node) |
| Pinned order and extrapolation | order **2**, low **constant**, high **linear** — the values read from this table's footer; the script sets them explicitly: `SetInterpolationMethodVelocity(2)`, `SetExtrapolationMethodVelocity("constant", "linear")` (`Medium.cc:1291-1294, 1341-1356, 1381-1383`) |
| Velocity vector (V-12) | `ElectronVelocity` → `Velocity(…, q = −1)` (`Medium.cc:490-495`); for B < Small: `mu = q·ve/e`, `v = mu·E` component-wise (`Medium.cc:205-238`); units: E in V/cm, B in T, v in cm/ns |
| Query points | B = 0, E = (E, 0, 0) along +x. In-range (task 1, must run): nodes k = 1 (E = 100.000002), k = 15 (middle, E = 2520.529056), k = 30 (E = 80000.0016) — decimal strings that parse to the same double as (E/p)ₖ × 760; interior points 112 (first interval, ix = 1: single quadratic through nodes 1, 2, 3), 2800 (interval 15–16, ix = 15: average of the quadratics through 14, 15, 16 and 15, 16, 17), 70000 (last interval, ix = 29 = n−1: single quadratic through 28, 29, 30). Out of range (task 2): 50 (below node 1) and 100000 (above node 30) |
| Acceptance tasks | task 1 = the six in-range points, must run; task 2 = task 1 plus the two out-of-range points, refused by `check`/`prepare` with `out-of-domain` and the valid range [100.000002, 80000.0016] V/cm by default; task 2 with `allow_outside_validated_range: true` must run and label those two rows `outside-validated-range` |
| Output | per point vx, vy, vz and |v| in cm/ns, printed with `repr` (round-trip exact); one process for all points |
| Check 1 — nodes | independent parser: node E = (E/p)ₖ × 760.0 in double, t = ve × 1e-3; `abs(abs(v) − t) ≤ 4·ulp(t)`; vy and vz exactly 0 (`-0.0` counts as 0) |
| Check 2 — sign | vx < 0 (electrons drift opposite to E along +x) at every point; vy = vz = 0 |
| Check 3 — interior | independent reimplementation of `Divdif` for order 2 with the stencil above; tolerance `abs(abs(v) − r) ≤ 1e-12·abs(r) + 4·ulp(r)` |
| Check 4 — out of range | default refusal (`out-of-domain`, valid range reported); with the option: below → constant (value of node 1), above → linear through nodes 29 and 30, same tolerance as check 3, rows labelled `outside-validated-range`; recorded as a known policy difference from native extrapolation |
| Counterexamples (must be caught) | missing quantity (velocity column absent → refused); table hash mismatch → `input-changed` / `plan-stale`; T or p mismatch → `condition-mismatch`; a table with `Dimension : T` (B or angle grid) → refused; wrong unit or sign (a reversed sign or a ×1e3 factor fails checks 1/2); missing query point → failed completeness; an out-of-range row without the label → failed |
| RNG | none: the query is deterministic; no seed is invented (`seeds` records the reason) |
| Budget | one query process ≤ 60 s; whole acceptance (tasks 1, 2, 2-with-option) ≤ 10 min |
| Required guarantees | G0 `macos-g0`: inputs not modified (hard), timeout (hard), output-size abort (soft); `no_network` not required |
| Not claimed | agreement with independent gas data; any physics validity of the example table |

## Environment record (V-13)

Pinned 2026-11-02 (V-13 concluded):

| Item | Value |
|---|---|
| Garfield++ | commit `e2e58ea74ec8b20d347d78b7a769f40e3b156072` (`git describe`: `2026.10-4-ge2e58ea`), built from source in `WR/env/garfield` (`WR/env/build_garfield.sh`): Release, `GARFIELD_WITH_GSL=ON` (libc++ has no `std::comp_ellint_1`, used by neBEM), `GARFIELD_WITH_EIGEN=OFF`, examples, tests, docs and CUDA off; `libGarfield.0.3.dylib` SHA-256 `29a501382d01cdca6e9f48c10370cb67c9d103f6d28c427df152556b7a21240c` |
| ROOT | Homebrew ROOT 6.40.04 (C++20) with its PyROOT; the login environment's ROOT variables (`ROOT_INCLUDE_PATH`, `ROOTSYS`, `LD_LIBRARY_PATH`, `PYTHONPATH`) are cleared (decision log: they break cling) |
| Python | Homebrew Python 3.15.2 (PyROOT is built for 3.15) |
| Environment root | a view folder `WR/env/gf-view` with `bin/python3 → python3.15`, `root → ROOT prefix`, `garfield → Garfield install`; the plan names only `ENV_ROOT/...` paths; identity is content-based (commit, library hash, ROOT and Python versions), never the path |
| Variables | `PYTHONPATH = ENV_ROOT/root/lib/root:ENV_ROOT/garfield/lib/python3.15/site-packages`, `DYLD_LIBRARY_PATH = ENV_ROOT/garfield/lib` |
| Query method | Python query script through PyROOT (`import ROOT, Garfield`; `ROOT.Garfield.MediumMagboltz`), a rendered file in the plan; no compiled driver |
| Pilot (allowed, no query of results) | `LoadGasFile` of the pinned table returns true and sets pressure 760 Torr and temperature 300 K (V-12 measured) |

## Amendments (recorded after W4G review round 1, 2026-11-02; none changes a tolerance or criterion)

- Environment identity: Garfield++ commit, build options, SHA-256 of the six Garfield++ libraries (libGarfield,
  libGarfieldRandom, libHeed, libMagboltz, libDegrade, libneBEM) and of ROOT's libCore and PyROOT binding library,
  ROOT and Python versions, platform. The query script's SHA-256 is in the plan's code hashes (and the run record's
  `script_sha256`), not in the environment identity.
- `PYTHONPATH = ENV_ROOT/root/lib/root` only; the script loads the Garfield++ libraries itself.
- Observables rows carry the note "example table, pipeline validation only" (optional row field `note` of
  detsim-observables/1, contracts 3.18.0) when the pinned example table is used.
- Interpolation order and extrapolation methods are task parameters and must equal the table footer.
- Query points must include the first node, the last node and an interior node of the table (rejected at `check`,
  partial at collect otherwise); at `check` the answer is `rejected` / `node-coverage` (exit 2).
