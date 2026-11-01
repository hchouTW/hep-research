# Sensor and gas transport tools: Allpix Squared and Garfield++

Physics guide for choosing, and rightly refusing, the two charge-transport simulators that the optional
`detector-simulation` adapter wraps: Allpix Squared (semiconductor pixel and strip sensors, event by event) and
Garfield++ (gas and semiconductor media, transport tables, fields, signals). It covers tool selection, model, charge and
signal boundaries, the Garfield++ interpolation, extrapolation and temperature-pressure behaviour, the two first-batch
task cards, failure classes and limitations. Geant4 studies in general are in [detector simulation](detector-simulation.md);
how to obtain, build and run the tools and the `detsim` command is in the hep-computing
[operations guide](../../hep-computing/references/sensor-and-gas-simulation-operations.md).

**Status (2026-11-01).** Usable with no simulator installed: everything in this page is read from sources, nothing
from a run. Both backends have run their task cards' acceptance checks on one macOS arm64 environment (section 10);
every statement about another version, platform or configuration is **unverified**, and no example result is given. Source IDs in
brackets (`[GF-03]`) refer to the source index `docs/dev/detector-simulation/SOURCES.md` (plugin root), which gives
the commit, file, lines, retrieval time and content hash of each.

## 1. Problem and scope

A researcher asks for a sensor or gas-detector response that a parametrized model cannot give: charge collected per
pixel in a silicon sensor for a beam, or the electron drift velocity in a gas at a field. The two tools answer such
questions with their own native models; the plugin coordinates a pinned run, records sources and states what the
result does and does not establish. It never replaces upstream physics.

In scope here: when each tool applies, what its result means, which defaults silently decide the answer, and the two
pipeline-validation task cards. Out of scope (later task cards, Appendix A of the task specification [H-01]): gas-table
generation with Magboltz, microscopic tracking, avalanche, induced waveforms and electronics, TCAD conversion,
parameter scans, coupling the two tools.

## 2. Which tool, or neither

| Question | Use | Why |
|---|---|---|
| Charge deposited, drifted and collected per pixel or strip in a semiconductor sensor, event by event, with a Geant4 particle source and a detector model | **Allpix Squared** | Module chain from Geant4 deposition through propagation, transfer and digitization [AP-02, AP-11, AP-12] |
| Hit maps, cluster size, efficiency versus threshold in a pixel telescope or a device under test, with a stated field map | **Allpix Squared** (with its own detector model and field) | Same chain; the field and model are inputs that must be pinned |
| Electron drift velocity of a gas at a field, B = 0, read from a 1D gas table | **Garfield++** (`MediumMagboltz` + `LoadGasFile`) | The table is the model; Garfield++ interpolates it [GF-02, GF-03]. The only Garfield++ query of the first batch |
| Diffusion, Townsend or attachment coefficient from a gas table; any quantity at B ≠ 0 or from a 3D table | **Garfield++** natively | Not in the first batch: each needs its own storage and interpolation semantics (log-space Townsend and attachment, zero below threshold, √N scaling of diffusion) and a later task card |
| Signal induced on electrodes of a gaseous or semiconductor detector with a field solved elsewhere (TCAD, finite elements) | **Garfield++** components (`ComponentTcad2d/3d`, `ComponentComsol`, `ComponentElmer`, `ComponentAnsys…`) [GF-12] | Not in the first batch; a later task card |
| Avalanche gain, microscopic electron tracking, primary ionization clusters in gas | **Garfield++** (`AvalancheMicroscopic`, `AvalancheMC`, `TrackHeed`) [GF-12] | Not in the first batch |
| Electric field inside a sensor from its doping profile and bias | **Neither**: a TCAD device simulator produces it; Allpix Squared reads the map (`ElectricFieldReader` model `mesh`, `tools/mesh_converter`) [AP-23, AP-24] and Garfield++ imports it (`ComponentTcad2d/3d`) [GF-12] | Neither tool solves the semiconductor device equations from doping. Allpix Squared also offers simple analytic fields (constant, linear, parabolic, custom) [AP-24], and Garfield++ solves electrostatics for wires and electrodes (`ComponentAnalyticField`, neBEM) [GF-12]; neither of those is a doping-based device field |
| Front-end ASIC behaviour (shaper, comparator, ToT logic) at transistor level | **Neither**: a circuit simulator; both tools stop at a simplified electronics model | DefaultDigitizer is Gaussian noise + threshold + linear QDC/TDC [AP-12] |
| Shower development, material budget, physics-list choice | **Geant4 directly** ([detector simulation](detector-simulation.md), [Geant4 study protocol](geant4-study-protocol.md)) | Allpix Squared embeds Geant4 only for deposition |
| Gas properties at a temperature or pressure different from the table's | **Neither, through this plugin**: generate a new table (Magboltz, later task card) | Garfield++ density scaling is "very approximate" by its own tutorial [GW-02]; the adapter refuses it (section 6) |
| Front-end noise, threshold and timing from parameters, no transport | Neither: [front-end electronics](front-end-electronics-and-signal-processing.md) and its script | No transport simulation needed |

When the answer is "neither", say so and name what is needed (field solution, new gas table, circuit model) instead of
running the nearest tool.

## 3. Preconditions, sources and versions

- **Version basis.** Name the commit or release whose documentation you cite, and run that same version. Allpix
  Squared master and its latest release are on different branches: tag `v3.3.0` (2026-09-30) is not an ancestor of
  master `df69a6a4` (2026-10-30), and they differ in 473 files [AP-01]. Example: master's build script requires spdlog >= 1.9.2,
  which its own prerequisites page does not list, and `v3.3.0` does not require it [AP-16, AP-20, AP-21]; the `log_level` values differ [AP-08]. Garfield++ is cited at master
  `e2e58ea7` = tag `2026.10` + 4 commits [GF-01]; the online User Guide is "Version 2026.1, July 2026" [GW-01].
  A statement read at one version is re-read at the version the task card pins.
- **Inputs exist and are legitimate.** Allpix: configuration, detector setup, model, field map, each hashed
  [AP-02 … AP-05]. Garfield++: one gas table with its source, conditions and licence. The Garfield++ repository has no
  licence file, so its example tables have unstated terms [GF-01]; the user allowed one example table for pipeline
  validation only, by an explicit decision recorded in the task specification [H-01]. The first batch uses only public or synthetic inputs; gas tables, field maps
  and other large inputs are never committed to the plugin or its test fixtures, and the project's protected-data
  policy applies unchanged.
- **Environment.** How to obtain it and what it needs: the [operations guide](../../hep-computing/references/sensor-and-gas-simulation-operations.md).
  Allpix Squared requires every Geant4 data set [AP-16].

## 4. Inputs and steps

Inputs, per tool: Allpix Squared takes a main configuration, a detector setup, detector models and field maps (all
files, all hashed); Garfield++ table queries take one gas table plus the query points (field vector, B = 0) and the
pinned interpolation and extrapolation settings. The research workflow is the same for both:

1. **Select** the tool, or refuse, with section 2; state the observable and why a parametrized model is not enough.
2. **Fix the version basis** (section 3): the commit or release, and the documentation of that same version.
3. **Check the native inputs**: Allpix Squared configuration keys and their defaults (section 5); Garfield++ table
   dimension, conditions, stored quantities and interpolation lines (section 6).
4. **Pin the plan**: inputs, environment identity, overrides, seeds or the deterministic query, tolerances written
   before running. The command that pins and runs it is in the [operations guide](../../hep-computing/references/sensor-and-gas-simulation-operations.md)
   (unverified: not yet built).
5. **Execute and store** through that command, never by editing results afterwards.
6. **Check the results** against the card's independent checks (section 7) and classify any failure (section 9).

## 5. Allpix Squared: model, charge and signal boundaries

**Chain.** Geometry (`GeometryBuilderGeant4`) → energy deposition (`DepositionGeant4`, a Geant4 physics list) → field
(`ElectricFieldReader`) → propagation (`GenericPropagation`, or `TransientPropagation` for induced charge) → transfer
to pixels (`PulseTransfer`) → digitization (`DefaultDigitizer`) → output (`ROOTObjectWriter`) [AP-02].

**Defaults that decide the answer** (at `df69a6a4`; re-read at the pinned commit):

| Setting | Default | Consequence | Source |
|---|---|---|---|
| `multithreading` | `true` | Must be written explicitly when a run is compared with another; never compare runs made in different threading modes | [AP-08] |
| `random_seed` | random from entropy if unset | An unpinned run is not reproducible; `random_seed_core` defaults to `random_seed + 1` | [AP-08] |
| Seeds per event | from a central generator in event order | Same seed gives the same per-event seeds for any number of workers | [AP-09] |
| `GenericPropagation` carriers | electrons propagated, holes not | Collected charge is that of one carrier type unless configured | [AP-11] |
| `GenericPropagation` `temperature`, `mobility_model` | 293.15 K, `jacoboni` | Mobility and diffusion follow these unless set; record them as upstream defaults | [AP-11] |
| `DefaultDigitizer` noise and threshold spread | 110 e, 30 e (threshold has no default) | The seed path matters even for a fixed deposit | [AP-12] |
| `DefaultDigitizer` `qdc_resolution`, `tdc_resolution` | 0 bit | `PixelHit` signal is charge in electrons and time in ns only at these defaults; with a QDC/TDC set, they are counts | [AP-12] |

**Charge sign.** `PixelCharge::getCharge()` is signed; `getAbsoluteCharge()` is its absolute value [AP-13]. With
electrons propagated the charge is negative. An observable must name which one it uses; summing `getCharge()` and
comparing it with a positive expectation is a sign error, not a physics result.

**Empty events versus missing output.** `ROOTObjectWriter` creates a tree for an object type when the first object of
that type arrives, then stores an empty vector for every event without one; a type that never appears has no tree;
the `Event` tree holds event numbers and seeds; `include` and `exclude` cannot be combined [AP-10]. So: an empty vector
is a real "no objects in this event"; a missing tree is either "never any object" (only if the run is otherwise
complete) or "excluded by configuration" (then never reported missing); never fill a missing tree with zeros.

**Signal boundary.** Without pulse information from propagation, `PulseTransfer` builds a pulse from carrier arrival
times near the collecting surface (`max_depth_distance`, default 5 µm) and upstream states this "does not represent a
time-resolved simulation of the signal formation" [AP-14]. An induced signal from a weighting potential needs
`TransientPropagation` (Shockley-Ramo) [AP-15]. The two have different validity domains even though both pass through
`PulseTransfer`; a total collected charge does not determine a waveform.

**Field boundary.** The field is an input to the chain: either a map read from file (the example uses a mesh file
[AP-04]) or one of `ElectricFieldReader`'s simple analytic models (constant, linear, parabolic, custom) [AP-24]. Its
source, units and mapping are part of the result. Allpix Squared does not solve for the field of a doped device; that
comes from a TCAD simulator.

## 6. Garfield++: table interpolation, extrapolation, temperature and pressure

Read at `e2e58ea7` [GF-02 … GF-08]; re-read at the pinned commit.

- **Table dimension.** The header line `Dimension : F` marks a 1D table (E only); `T` marks a 3D table with B and
  angle grids [GF-02 line 671]. The first batch accepts 1D tables only.
- **Stored forms.** The E grid is stored as E/p in V/(cm·Torr) and multiplied by the table pressure in Torr on load
  (line 560); a 1D table is read record by record by `ReadRecord1D` (dispatch at lines 477-483; reader lines 837-850), in which
  most quantities are followed by a column that is read and discarded (`ve, waste, vb, waste, vx, waste`, then
  `dl, waste, dt, waste`, then `alpha, waste, alpha0, eta, waste` — `alpha0` has none, line 852 — …), so the drift velocity along E is the first value of each record, not every second
  column; drift velocities are stored in cm/µs and converted to cm/ns (× 1e-3, lines 848-850; the 3D reader
  `ReadRecord3D` does the same at line 796); Townsend and
  attachment coefficients are stored as logarithms and shifted by ln p on load (lines 563-577) [GF-02]. The user
  guide confirms the logarithmic storage of α and η [GF-08].
- **Temperature and pressure.** `LoadGasFile` sets the medium's pressure and temperature to the table's (lines
  555-556). The density ratio is (p_table/T_table)·(T/p) (line 156), and the field used for the lookup is the query
  field times that ratio [GF-06]. While the table's p and T are kept the ratio is exactly 1 and the lookup field is
  the query field. Changing p or T afterwards scales the table by laws the tutorial calls "very approximate" and does
  not recommend [GW-02]. The adapter therefore refuses any temperature or pressure other than the table's
  (`condition-mismatch`) [H-01 §11.3].
- **Interpolation and extrapolation come from the file.** The compiled defaults are order 2 and extrapolation
  constant below, linear above [GF-05 lines 770, 779], which the user guide also states as the default [GF-08, GW-01].
  But `LoadGasFile` overwrites them with the file's `Interp`, `L Extr`, `H Extr` lines [GF-02 lines 590-612]
  (file codes: 0 constant, 1 linear, 2 exponential). The setter `SetExtrapolationMethodVelocity(low, high)` takes
  **strings** only: `"const"`/`"constant"`, `"lin"`/`"linear"`, `"exp"`/`"exponential"`, case-insensitive; an
  unknown string prints an error and leaves that side unchanged [GF-03 lines 1291, 1321-1356]. The example table `ar_80_co2_20_0T.gas` has `Interp 2`, `L Extr 0`, `H Extr 1` [GF-07]. A pinned query
  therefore records the values read from the file and sets them explicitly with `SetInterpolationMethodVelocity` and
  `SetExtrapolationMethodVelocity`; note that `SetInterpolationMethodVelocity(0)` is ignored [GF-03 line 1381].
- **Code path.** `Medium::Interpolate` uses `Numerics::Boxin3` for a 3D table and `Interpolate1D` otherwise
  [GF-03 lines 1419-1437]. In `Interpolate1D` (lines 1439-1542): a negative field returns 0; below the first node
  the low-side method is applied (constant `ytab[0]`, linear through the first two nodes, exponential); above the
  last node the same with the last two; inside, order 1 uses `LinearInterpolation` and order >= 2 uses `Divdif`.
  For 3D tables extrapolation is a polynomial of the interpolation order, not the 1D methods [GF-08].
- **`Divdif` stencil** [GF-04 lines 1658-1754]. Effective order m = min(order, 10, n−1). With ix the 1-based index
  of the last node <= x, nodes are taken in the order ix, ix+1, ix−1, ix+2, …; for even m it uses m+2 nodes and
  averages the two highest divided differences, but as soon as an index falls outside the table it uses m+1 nodes.
  For m = 2 inside the table (2 <= ix <= n−2) the result is the average of the quadratics through (ix−1, ix, ix+1)
  and (ix, ix+1, ix+2); next to the ends a single quadratic through the first or last three nodes. At the first and
  last node (within 1e-6 of the end spacing) the stored value is returned directly; at an interior node the Newton
  form also returns the stored value exactly, because its first coefficient is that value and every further term is
  multiplied by (x − x_ix) = 0. The user guide calls orders above 2 "not
  recommended" [GF-08]. A reimplementation that uses a different stencil differs by O(h³ f‴) and is wrong.
- **Velocity vector at B = 0.** `ElectronVelocity` uses charge q = −1 [GF-03 lines 490-495]; for B below `Small`
  the velocity is (q·v_E/|E|)·E component by component (lines 232-238): electrons drift opposite to E, components
  perpendicular to E are exactly zero (possibly `-0.0`), and |v| equals the interpolated v_E up to one division and
  one multiplication.
- **Units.** E in V/cm, B in T, angles in rad, velocity in cm/ns [GF-08].

**Adapter policy, differing from native behaviour on purpose.** Garfield++ extrapolates silently outside the table.
The adapter refuses a query outside the table's E range by default (`out-of-domain`, with the valid range); with the
task parameter `allow_outside_validated_range` it evaluates natively and labels the row `outside-validated-range`
[H-01 §12.3; the same pattern as the plugin's bounded-model providers, `core/provider`]. The difference is a stated policy, not a failure.

## 7. The two first-batch task cards

Both are **pipeline-validation cases**: they show that identity, execution, commit and extraction work. They do not
produce research conclusions [H-01 §1.4]. Full cards: task specification §12.2 and §12.3 [H-01]; the pinned versions
are written when each card is pinned.

**AP-BOOT — rerun of the official pixel example** (capability `allpix.pixel-charge` 1.0.0, state `demonstrated-on-synthetic-data`: its checks passed on one macOS arm64
environment with Allpix Squared `df69a6a4`; see the adapter's capability-matrix row).

| Item | Content |
|---|---|
| Input | `examples/example.conf` with `example_detector.conf` and `example_electric_field.init`, unchanged [AP-02 … AP-04]: two `cmsp1` sensors (285 µm thick [AP-05]), 120 GeV π⁺ pencil beam, `FTFP_BERT_LIV`, 600 e threshold, `DepositedCharge` and `PropagatedCharge` excluded from output |
| Allowed changes | only `number_of_events = 10`, `multithreading = false` (written explicitly) and `random_seed = <integer>`, each passed once as `-o key=value` [AP-06, AP-07]; the whole command line is checked against this form; the output stays in Allpix's default folder of the run |
| Checks | (1) official file hash unchanged, overrides only from the allowed list; (2) same plan, two replicas in one environment: identical per-event objects and seeds (data members only, not file hashes); different seeds differ; (3) 10 events, every event has a PixelHit in each detector; (3b) median per-event Σ `getAbsoluteCharge()` over detector1 within [0.5, 2] × 75 e/µm × 285 µm, about 10.7-42.8 ke: a plausibility band for gross errors, not physics validation; also: every pixel charge negative (charge-sign; this example propagates electrons only) and the stored class versions as pinned |
| Counterexamples it must catch | missing dependency, wrong version, missing Geant4 data set, exit 0 with content missing, an event without hits, sign read wrongly, replaced input |
| Not claimed | 10 events are not statistics; no efficiency, waveform or scan |

**GF-QUERY — electron drift velocity on one pinned 1D table** (capability `garfield.gas-table-query` 1.0.0,
state `demonstrated-on-synthetic-data`: its checks passed on one macOS arm64 environment with Garfield++ `e2e58ea`; see
the adapter's capability-matrix row).

| Item | Content |
|---|---|
| Input | one 1D `.gas` table; candidate `Examples/GasFile/ar_80_co2_20_0T.gas`: Ar 80 % / CO₂ 20 %, 300 K, 760 Torr, 30 E points, E/p 0.1316 … 105.26 V/(cm·Torr) (100 V/cm to 80 kV/cm), B = 0, created 2012, format version 12 [GF-07]. Local input only, never committed; "example table, pipeline validation only", never reference physics data |
| Query | B = 0, E along +x; three nodes (first, middle, last), interior points including one in the first and one in the last interval; two out-of-range points in a separate task |
| Checks | (1) at nodes, the magnitude of v equals the independent parse (E = (E/p)·p, v = value × 1e-3) within 4 ulp, perpendicular components exactly 0; (2) electrons drift opposite to E, per component; (3) interior points equal an independent reimplementation of the pinned stencil within relative 1e-12 + 4 ulp; (4) out of range: refused by default, with the option equal to the reimplemented constant / linear / exponential extrapolation and labelled |
| Refused | a 3D table (B or angle grids), B ≠ 0, a temperature or pressure other than the table's, interpolation settings other than the table footer's, a missing velocity quantity, a malformed table, a field outside the table unless `allow_outside_validated_range` (`out-of-domain` with the valid range) |
| Not claimed | agreement with independent gas data; no seed (deterministic query) |

All tolerances are fixed before any query and never relaxed afterwards.

## 8. Outputs and what they establish

| Evidence | Establishes | Does not establish |
|---|---|---|
| Exit 0 and a run record | the program finished | that the required outputs exist (checked separately) |
| Same-seed replica identical | reproducibility of the pipeline in one environment | physical validity |
| Native run equals `detsim` run (same binary, same configuration) | almost a self-comparison: auxiliary only | independent correctness |
| AP-BOOT check 3b in band | no gross unit, material or field error | a validated charge scale |
| GF-QUERY checks 1-4 | the table was read and interpolated as pinned | that the table describes the gas (its generation record is incomplete) |
| Agreement between Allpix Squared and Garfield++ | consistency of two models | independent validation |

The levels are verification, numerical control, physics validation and research applicability [H-01 §16.2]; the
first batch reaches verification only. A capability state (`proposed`, `documented`,
`demonstrated-on-synthetic-data`, `tested-in-declared-environment`, `unavailable`) never implies physical validity
[H-01 §15.1].

## 9. Failure classification

| Class | Typical cause | Physics reading |
|---|---|---|
| Not run: missing dependency | backend, ROOT bindings, Geant4 data set or library absent | none: environment problem |
| Refused before running | stale plan, digest mismatch, out-of-domain point, temperature or pressure mismatch, 3D table, guarantee the platform cannot give | none: the request was outside what the card allows |
| Failed run | crash, timeout, interruption, exit 0 with outputs incomplete, commit conflict | none: no result; a failed run does not falsify the model |
| Semantic failure of a check | no hit in a detector, sign convention wrong, node value off by more than 4 ulp, wrong stencil | a pipeline or reading error to fix; never relax the tolerance |
| Physics disagreement (later cards) | model, field or table does not describe the device | a physics question for the owner; outside the first batch |

The status values and error codes behind these classes are in the [operations guide](../../hep-computing/references/sensor-and-gas-simulation-operations.md).

## 10. Limitations and untested scope

- Both capabilities ran their acceptance checks on one environment only (macOS 27.2 arm64; Allpix Squared `df69a6a4`
  with a C++20 Geant4 11.4.3, Garfield++ `e2e58ea`, ROOT 6.40.04); their state is `demonstrated-on-synthetic-data`
  until a non-author rerun and the performance measurement complete the checklist; any other version or environment
  is untested. The adapter's guarantees are measured on macOS only; on Linux they are
  declared unsupported until measured on a Linux host [H-02], so a capability that requires them is refused there.
- First batch only: no waveforms, gas-table generation, microscopic tracking, avalanche, TCAD field maps, user
  Allpix Squared configurations, scans or cross-tool coupling.
- Garfield++: only the electron drift velocity at B = 0 from a 1D table is queryable in the first batch; diffusion,
  Townsend and attachment coefficients, ion quantities and B ≠ 0 are not.
- Garfield++ 3D tables are refused: a B = 0 query on a table with B and angle grids still interpolates over the angle
  axis, whose convention at B = 0 is not pinned.
- Garfield++ temperature and pressure scaling is never used; a new condition needs a new table.
- Allpix Squared reproducibility across environments or platforms is an aim upstream (portable Boost.Random
  distributions [AP-16]) but not an acceptance criterion here.
- Example gas tables are not reference data: their licence is unstated and their generation record incomplete.

## 11. Citations

All sources, with commit, lines, retrieval time, content hash, licence and review status: `docs/dev/detector-simulation/SOURCES.md`.
Main ones: Allpix Squared master `df69a6a4` example, model, module documentation and manual sources [AP-02 … AP-16];
Garfield++ master `e2e58ea7` `MediumGas.cc`, `Medium.cc`, `Numerics.cc`, `Medium.hh`, `MediumGas.hh`, the example gas
table and the user guide source [GF-02 … GF-08]; Garfield++ User Guide 2026.1 [GW-01] and gas-files tutorial
[GW-02]; task specification 9.1 [H-01].
