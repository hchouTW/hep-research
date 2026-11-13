# HCAL: simulator-calibration specialization

Part B §11.1 items 1–8 for a hadronic sampling calorimeter with scintillator tiles, wavelength-shifting readout and
SiPMs, from §3.1 derivation basis (1), the HCAL row of §12 and §11.4. Folder rules: [index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object |
|---|---|---|---|
| `source` | 0 | beam | `simulation-request/1` source |
| `shower` | 1 | hadronic shower; sampling | `g4sim_run` (physics list, cuts, absorber geometry) |
| `quanta` | 2 | scintillation photons (Birks) | response stage 1 |
| `wls` | 3 | WLS collection, attenuation | response stage 2 (efficiency map) |
| `pde` | 4a | SiPM PDE | surface `efficiency`, folded into ε_c |
| `sensor` | 4b | gain, saturation | response stage 3 (saturation not implemented) |
| `electronics` | 5 | noise, time window | response stage 4 |
| `reco` | 6–7 | tower energy, weighted energy | reconstruction |

Splits as for the [ECAL](ecal.md): 3/4a only under the §6.7 PDE split; no single-photoelectron reference on g4sim.

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| cross-section scaling, hadronic model parameters | physics process / 1 | scale factors, model-internal values | none in the run card: the model enters as a discrete model M |
| hadronic model | discrete model / 1 | enumeration (physics list) | run card `reference_list`, with the §5.2 confirmation record |
| production cut | physics process / 1 | length | run card `cuts_mm` (geometry row) |
| sampling fraction | geometry / 1 | absorber and active thickness | detector-spec `params` |
| light yield, Birks | yield, nonlinearity / 2 | as for the ECAL | LY row, Birks row |
| SiPM saturation | nonlinearity / 4b | pixel count | not implemented in g4sim (Table 1 row 4b) |
| gain | 4b | multiplicative, ENF | `sensor` stage `gain` |

## 3. Kernel properties

Node 1 is a samplable black box (resimulation or surrogate model only); nodes 2–5 as for the ECAL. Fluctuations at
the deposition level (§12 "abstraction it motivates") sit in node 1 and are reached only through resimulation.

## 4. Storage recommendations

As for the ECAL (`edep_by_dedx_class`, `edep_visible_ly_split`, hits, simreco columns as `column` or `event_file`).
Each enumerated physics list is its own run with its own identity (§5.1); events are never shared across lists.

## 5. Reference catalog

Beam energy at several energies and for e and π (known input, into `source`); MIP peak of muons (population
feature); E/p with tracker momentum (internal constraint). §3.5 "scale and response shape" needs at least three
control points spanning the range and e and π samples together.

## 6. Special functionals and link functions

Response ratio versus energy: location, log link, with the declared form of r(E; b) (non-compensation as a power law,
§12). Resolution: core width, log. Longitudinal profile: normalized shape, alr/ilr. e/π ratio: location of a ratio,
log link.

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C | ℓ |
|---|---|---|---|
| location, log | no literature value | no literature value | no literature value |
| core width, log | no literature value | no literature value | no literature value |
| shape, alr/ilr | no literature value | no literature value | no literature value |

The model-ensemble component of §5.4 (absorbed physics lists, d_a at θ_ref) is the usual alternative to a kernel for
hadronic-model differences; it needs no literature value.

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| a hadronic model neither enumerated nor absorbed (with its confirmation record) | e/π response ratio versus energy, longitudinal profile |
| SiPM saturation on (needs the instance's own digitization: no g4sim stage) | linearity at the highest energies |
| high-precision neutron transport (an `_HP` reference list) | response versus integration time window (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/hcal.binding.example.json` (two enumerated lists FTFP_BERT and QGSP_BIC with a
placeholder confirmation record): candidates beam energy (φ) analytic reweighting; absorber thickness and production
cut resimulation or surrogate model; k_B, light yield and gain rerun. Degeneracies (§12): Poisson × gain; scale and
response shape.
