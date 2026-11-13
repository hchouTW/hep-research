# Tracker: simulator-calibration specialization

Part B §11.1 items 1–8 for a silicon or gas tracker, from §3.1 derivation basis (2), the Tracker row of §12 and
§11.4. Folder rules: [index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object |
|---|---|---|---|
| `source` | 0 | tracks of known momentum | `simulation-request/1` source |
| `material` | 1 | ionisation, multiple scattering in material | `g4sim_run` |
| `pairs` | 2 | electron-hole pairs, or primary electrons in gas | response stage `ionisation` |
| `sharing` | 3 | drift, Lorentz angle, diffusion, attachment, charge sharing | `charge_sharing` or `drift_table` stage (hashed table) |
| `preamp` | 4b | preamplifier (silicon) / gas gain (drift chamber, TPC) | `sensor` stage (gas gain: *Inferred* mapping) |
| `electronics` | 5 | noise, threshold, shaping | response stage 4 |
| `hits` | 5 | zero suppression, clustering | response stage 5 |
| `reco` | 6–7 | clusters or hits, tracks; alignment assumed by reconstruction | reconstruction |
| `residual_a`, `residual_b`, `overlap` | observations, comparison | residuals of two overlapping modules and their difference | — |

A charge-injection pulse into the preamplifier is a mid-chain injection on the edge `sharing` → `preamp`; it needs a
conversion relation and g4sim has no hand-off before stage 3, so it is not declared in the example.

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| charge sharing, gas diffusion, attachment | sharing, transport / 3 | table | hashed table: no stage parameter value, no Table 2 row |
| Lorentz angle (simulation) | transport / 3 | angle | inside the table: not bindable |
| Lorentz shift assumed by reconstruction | transport / 7 | offset | reconstruction (rerun) |
| gas gain | 4b | multiplicative | `sensor` stage `gain` |
| noise, threshold | 5 | width, level | `electronics` stage `noise_sigma`, `threshold` |
| residual smearing | noise / 5 | width | only when the microscopic mechanism is not modeled (§12) |
| alignment | geometry / 7 | offsets and rotations per module | reconstruction (rerun); simulation misalignment via overlay waits for D83 (7) |
| material thickness | geometry / 1 | length | detector-spec `params` (geometry row) |

## 3. Kernel properties

Node 1 samplable black box; `pairs`, `preamp`, `electronics` densities; `sharing` deterministic given its table;
readout and reconstruction deterministic. Redundant measurements use a comparison node with exactly two upstream
observation nodes (§3.4); common modes of the two modules are decided by P3/G5, not by the graph.

## 4. Storage recommendations

Hits for re-digitization; simreco columns (cluster positions, track parameters) for the alignment and Lorentz-shift
rerun; keep the incidence angle per hit so that "sum of two terms" can be broken (§3.5).

## 5. Reference catalog

| Reference | Type | Edge |
|---|---|---|
| beam or cosmic tracks of known momentum | known input | into `source` |
| overlapping modules | redundant measurement | out of the comparison node |
| known resonance mass | internal constraint | out of the observation |
| magnetic-field polarity flip, incidence-angle scan | control variables | conditioning (§3.5) |

## 6. Special functionals and link functions

Signed residual mean: location, identity (offsets are signed, so not log). Residual width: core width, log. Cluster
size: multiplicity, log; its distribution: normalized shape, alr/ilr. Hit efficiency: efficiency, logit.

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C | ℓ |
|---|---|---|---|
| location, identity | no literature value | no literature value | no literature value |
| core width, log | no literature value | no literature value | no literature value |
| efficiency, logit | no literature value | no literature value | no literature value |

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| PAI ionisation model in the sensor | cluster-charge spectrum, cluster size at normal incidence |
| charge-sharing table with versus without diffusion | cluster size versus incidence angle |
| delta-ray production cut lowered (run card) | residual tails at large cluster size (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/tracker.binding.example.json`: material thickness (φ) resimulation or surrogate
model; noise, threshold, Lorentz shift and module offset rerun; P4 is met by the known input and by the overlap
comparison node. Degeneracies (§12): addition in quadrature; Lorentz angle plus alignment; offset mixed into width.
