# DIRC: simulator-calibration specialization

Part B §11.1 items 1–8 for a DIRC (Cherenkov light trapped in a quartz bar by total internal reflection, imaged in
pixel and time), from §3.1 derivation basis (1), the DIRC row of §12 and the full optical tracking path of §11.4.
Folder rules: [index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object |
|---|---|---|---|
| `source` | 0 | tracks of known momentum, species and polar angle | `simulation-request/1` source |
| `bar` | 1 | quartz-bar traversal, Cherenkov emission | `g4sim_run` |
| `tir` | 3 | total internal reflection, path ambiguity | `g4sim_run` (full optical tracking) |
| `pde` | 4a | MCP-PMT PDE, TTS | sensor surface `efficiency` (applied in Geant4) |
| `sensor` | 4b | gain | response stage 3 |
| `tdc` | 5 | TDC, threshold | response stage 4 |
| `reco` | 6–7 | pixels and time; likelihood of angle and time | reconstruction |

The refractive index acts on `bar` (emission angle) and `tir` (propagation, group velocity): one parameter on two
nodes (§12). In g4sim both are `g4sim_run`; no injection edge between them or before stage 3 exists (§11.4).

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| refractive index | physics process / 1 and 3 | n(E) table | detector-spec `optical/rindex` (optical row) |
| bar-surface reflectivity | transport / 3 | reflectivity spectrum | `optical_surfaces/<s>/reflectivity` (optical row) |
| PDE | yield / 4a | surface `efficiency` spectrum | `optical_surfaces/<s>/efficiency` (optical row) |
| TTS | time / 4a | width | no field in `response-pipeline/1`: not bindable |
| time offset | time / 5–7 | offset | reconstruction (rerun) |

## 3. Kernel properties

`bar` and `tir` samplable black boxes; `pde` binomial density; 4b and 5 densities; 6–7 deterministic. The time
response is a two-dimensional shape functional in (pixel, time) (§12).

## 4. Storage recommendations

`photons.csv` with photon energy and time for any post-transport PDE(E) thinning; hits for re-digitization of the
sensor and TDC; simreco columns for the likelihood.

## 5. Reference catalog

Tracks of known momentum at several polar angles (known input: the number of reflections changes with polar angle,
which breaks PDE × reflectivity, §12); momentum from the tracker (internal constraint); a laser pulse into the
photodetector plane would be a mid-chain injection after node 1 and needs a conversion relation (*Inferred*; not
declarable on g4sim's optical path).

## 6. Special functionals and link functions

Hit pattern in (pixel, time) per polar-angle bin: normalized two-dimensional shape, alr/ilr on the prediction side
(§3.3). Photon yield per track: multiplicity, log. Single-photon time resolution: core width, log. Time offset:
location, identity.

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C | ℓ |
|---|---|---|---|
| shape (pixel, time), alr/ilr in clr coordinates | no literature value | no literature value | no literature value |
| multiplicity, log | no literature value | no literature value | no literature value |
| core width, log | no literature value | no literature value | no literature value |

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| rough bar surface (unified model, `sigma_alpha_deg`) instead of polished | photon yield versus polar angle |
| absorption in the glue joints added | photon yield versus path length |
| chromatic dispersion removed (constant index) | single-photon time width versus path length (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/dirc.binding.example.json`: refractive index (on `bar` and `tir`), reflectivity and
surface efficiency resimulation or surrogate model; time offset rerun. Degeneracies (§12): PDE × reflectivity
(broken by polar angle); time offset and group velocity.
