# TOF: simulator-calibration specialization

Part B §11.1 items 1–8 for a scintillator time-of-flight system read out at the counter ends, from §3.1 derivation
basis (2), the TOF row of §12 and §11.4. Folder rules: [index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object |
|---|---|---|---|
| `source` | 0 | particles of known momentum and species | `simulation-request/1` source |
| `scintillator` | 1 | scintillator deposition | `g4sim_run` |
| `quanta` | 2 | scintillation photons, emission time | response stage 1 |
| `light` | 3 | light propagation, attenuation, path dispersion | efficiency map with mapped transit times |
| `pde` | 4a | photoelectric conversion, TTS | surface `efficiency`; TTS as a digitization-job timing input |
| `sensor` | 4b | gain | response stage 3 |
| `tdc` | 5 | TDC, slewing | response stage 4 |
| `tracker_path` | control variable | track length and momentum from the tracker | another subsystem (upstream result) |
| `reco` | 6–7 | time points, β; T0 and slewing corrections | reconstruction |

Control variables come from another subsystem, so the graph is a DAG with a merging branch, not a chain (§12). A
laser into the counter would sit on the 2/3 or 3/4a edge and needs a conversion relation (§3.4).

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| emission time | time / 2 | decay and rise time | detector-spec scintillation component field: no Table 2 row |
| effective light speed, path dispersion | transport / 3 | velocity, spread | map transit times: no Table 2 row (resimulate the map with another rindex) |
| attenuation | transport / 3 | absorption length | detector-spec `optical/absorption_length_mm` (optical row) |
| TTS | time / 4a | width | digitization-job timing: no Table 2 row |
| T0, slewing | time / 5 | offset, coefficient | reconstruction (rerun) |
| light yield | yield / 2 | photons per MeV | LY row |

## 3. Kernel properties

Node 1 samplable black box; 2–5 densities (photon times per detected photon, `response.photon_times`); 6–7
deterministic. Common random numbers fall out of step when θ crosses an algorithm switch point (§11.4); this only
reduces variance reduction.

## 4. Storage recommendations

`edep_visible_ly_split` and hits (LY re-digitization); per-photon times when time observables are calibrated; simreco
columns for the T0 and slewing rerun; the event time per global event number for conditions IOVs (§11.4).

## 5. Reference catalog

| Reference | Type | Edge |
|---|---|---|
| momentum and species | known input | into `source` |
| track length from the tracker | internal constraint | `tracker_path` → `reco` |
| three-counter method | redundant measurement | out of a comparison node of two counter times |
| hit position along the counter | control variable | breaks T0 versus x/v_eff (§3.5) |

## 6. Special functionals and link functions

Time residual mean: location, identity. Time resolution: core width, log. β: location, log or identity. Non-Gaussian
time tails: tail, logit (D41 open). Time difference of the two ends versus position: correlation, Fisher z with
endpoints checked (§3.3).

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C | ℓ |
|---|---|---|---|
| location, identity | no literature value | no literature value | no literature value |
| core width, log | no literature value | no literature value | no literature value |

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| full optical tracking instead of the map and its mapped transit times | time residual versus hit position |
| a second scintillation component with its own decay time | slewing shape (time versus pulse height) |
| wrapping reflectivity changed to a diffuse surface | time resolution versus hit position (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/tof.binding.example.json`: light yield rerun; attenuation length resimulation or
surrogate model; T0 and slewing rerun; P4 met by the known input and by the tracker's internal constraint.
Degeneracies (§12): T0 plus x/v_eff; addition in quadrature.
