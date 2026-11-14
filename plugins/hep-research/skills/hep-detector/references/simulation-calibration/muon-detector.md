# μ detector: simulator-calibration specialization

Part B §11.1 items 1–8 for a muon system of gaseous chambers behind an absorber, matched to an inner tracker, from
§3.1 derivation basis (2), the μ detector row of §12 and §11.4. Folder rules: [index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object |
|---|---|---|---|
| `source` | 0 | muons of known momentum | `simulation-request/1` source |
| `absorber` | 1 | absorber traversal (multiple scattering), gas ionisation | `g4sim_run` |
| `gas` | 2 | primary electron clusters | response stage `ionisation` |
| `drift` | 3 | drift, diffusion | `drift_table` stage (hashed table) |
| `avalanche` | 4b | avalanche gain | `sensor` stage gain (*Inferred* mapping) |
| `discriminator` | 5 | threshold, time, dead time | response stage 4 |
| `readout` | 5 | clusters of strips or wires | response stage 5 |
| `segment` | 6–7 | hits and segments; t₀ and the r–t relation | reconstruction |
| `muon_segment`, `inner_track`, `matching` | observations, comparison | segment, extrapolated inner track, their difference | — |

The matching across branches is a comparison node whose two upstream observations belong to different subsystems
(§12 "matching functional across branches"). A test pulse into the front end would be a mid-chain injection before
stage 4; on g4sim only the 3→4 and 4→5 hand-offs exist.

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| gas gain | 4b | multiplicative | `sensor` stage `gain` |
| HV (as φ) | 4b | gain factor per IOV | `condition-snapshot/1` `gain_factor` row (D87; φ) |
| threshold | 5 | level | `electronics` stage `threshold` (or a snapshot row per cell and IOV) |
| cluster size | sharing / 3 | table | hashed table: no Table 2 row |
| multiple scattering in the absorber | physics process / 1 | absorber thickness, cut | detector-spec `params`, run card cuts (geometry row) |
| t₀ | time / 5 | offset | reconstruction (rerun) |

Dead time is a cross-event effect: only approximated by conditioning variables such as rate (§3.1, §19-6).

## 3. Kernel properties

Node 1 samplable black box; `gas`, `avalanche`, `discriminator` densities; `drift` deterministic given its table;
readout and reconstruction deterministic. Re-digitization at two condition values uses exact common random numbers;
`threshold` and `dead` change the code discontinuously (§11.4 "Conditions").

## 4. Storage recommendations

Hits (re-digitization in Python: `g4sim_digi` ignores conditions, C24); the event time per global event number for
the snapshot IOVs; simreco columns for t₀ and segment fits.

## 5. Reference catalog

| Reference | Type | Edge |
|---|---|---|
| muons of known momentum (beam or cosmic) | known input | into `source` |
| inner-tracker match | redundant measurement | out of the `matching` comparison node |
| Z → μμ tag and probe | tag and probe | out of the observation (tag-probe correlation biases, §3.4) |
| threshold scan, multiplicity | control variables | break efficiency, threshold and noise (§3.5) |

## 6. Special functionals and link functions

Chamber efficiency: efficiency, logit. Matching residual: location, identity; width: core width, log. Cluster size:
multiplicity, log. Drift-time spectrum: normalized shape, alr/ilr.

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C | ℓ |
|---|---|---|---|
| efficiency, logit | no literature value | no literature value | no literature value |
| location, identity | no literature value | no literature value | no literature value |
| core width, log | no literature value | no literature value | no literature value |

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| drift table from another gas-mixture computation | drift-time spectrum edges, r–t residual versus distance |
| multiple-scattering model of another EM option | matching residual width versus momentum |
| neutron and photon background added to the event (overlay of cavern background) | hit multiplicity and efficiency versus rate (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/muon.binding.example.json`: absorber thickness (φ) resimulation or surrogate model;
gas gain, HV gain factor (φ, snapshot row), threshold and t₀ rerun. Degeneracies (§12): efficiency, threshold and
noise; t₀ plus the r–t relation.
