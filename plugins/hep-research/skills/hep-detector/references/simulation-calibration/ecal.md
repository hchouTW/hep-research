# ECAL: simulator-calibration specialization

Part B §11.1 items 1–8 for an electromagnetic calorimeter (scintillating crystal or sampling, light read out by a
photosensor), from §3.1 derivation basis (1), the ECAL row of §12 and the g4sim binding of §11.4. Folder rules and the
literature search record: [index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object (§11.4 Table 1) |
|---|---|---|---|
| `source` | 0 | beam or generator | source of `simulation-request/1`, `analytic` only |
| `shower` | 1 | electromagnetic shower deposition; dead material | `g4sim_run`; Birks applied per step, `edep_by_dedx_class` |
| `quanta` | 2 | photon generation (Birks quenching) | response stage 1 (`scintillation`) |
| `collection` | 3 | light collection, attenuation | response stage 2 (efficiency map) |
| `pde` | 4a | photoelectric conversion | sensor surface `efficiency`, folded into ε_c |
| `sensor` | 4b | gain | response stage 3 (`sensor`) |
| `electronics` | 5 | noise, ADC, saturation | response stage 4 |
| `readout` | 5 | zero suppression, clustering | response stage 5 |
| `reco` | 6–7 | crystal energy, shower energy | simreco or the user's reconstruction |

Splits: a light source with a known photon count needs an edge between `collection` and `pde` (the 3/4a edge, the
binomial thinning chain of §3.5); single-photoelectron injection needs the edge `pde` → `sensor` (§3.1). On g4sim's
efficiency-map path the 3/4a edge exists only under the PDE split of §6.7, and the 4a/4b edge has no hand-off, so a
single-photoelectron reference cannot be declared (§11.4).

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| light yield | yield / 2 | multiplicative, photons per MeV | `response-pipeline` scintillation `light_yield_per_MeV` (LY row) |
| Birks k_B | nonlinearity / 2 | quenching 1/(1 + k_B·dE/dx) | detector-spec `ionisation/birks_mm_per_MeV` (Birks row) |
| collection efficiency | transport / 3 | reflectivity, absorption length | optical tables and surfaces (optical row) |
| PDE | yield / 4a | probability, or PDE(E) | surface `efficiency`; a θ of its own only under the §6.7 split |
| gain | 4b | multiplicative, with ENF | `sensor` stage `gain` (response row) |
| noise | 5 | width | `electronics` stage `noise_sigma` |
| dead material | geometry / 1 | thickness | detector-spec `params` (geometry row) |

## 3. Kernel properties

Nodes 0, 2, 3, 4a, 4b and 5 (electronics) are densities, node 1 a samplable black box, readout and reconstruction
deterministic. `log_density`: Poisson and binomial pmf; the multinomial of the map as successive binomials; for a bin
with μ_b > 10 the pmf of g4sim's rounded Gaussian (width √(v_b − 1/12), cut at 0), not the normal density (§11.4).
`run`: readout and reconstruction. `resample`: the full `g4sim_run` plus response, as used by P0 at the extreme points
of k_B and r (§5.4).

## 4. Storage recommendations

Record as `column` or `event_file` (moments forbid reweighting and rerun, §6.1): `edep_by_dedx_class` (k_B rerun),
`edep_visible_ly_split` (LY and r re-digitization), the hit file (re-digitization of stages 2–5), simreco columns
(reconstruction rerun). Keep the mapping run's `photons.csv` when a PDE(E) is applied under the split (§11.4 Table 2).

## 5. Reference catalog

| Reference | Type | Edge | g4sim |
|---|---|---|---|
| beam energy | known input | into `source` | yes; its uncertainty is φ |
| MIP peak, cosmic rays | population feature | out of the observation | yes |
| E/p with tracker momentum | internal constraint | merging branch (§3.4) | yes, upstream result by hash |
| laser or LED monitoring | mid-chain injection | 3/4a, with conversion S/S₀ = (R/R₀)^α, α as φ | only under the §6.7 split |
| single photoelectron | mid-chain injection | `pde` → `sensor` | refused (`binding.injection_single_pe`) |

## 6. Special functionals and link functions

Energy scale: location, log link. Resolution: core width, log link. Leakage and tail fractions: tail, logit (the
determining region of tail functionals is open, D41: P5/G4 decisions on them are rejected until defined). Longitudinal
or lateral shower shape: normalized shape with alr/ilr, never logit per bin (§3.3). Scale and response shape: the
functional form r(E; b) is declared (§3.5).

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C (to other groups) | ℓ (control variable) |
|---|---|---|---|
| location, log | no literature value | no literature value | no literature value |
| core width, log | no literature value | no literature value | no literature value |
| shape, alr/ilr (clr coordinates) | no literature value | no literature value | no literature value |

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| full optical tracking instead of the efficiency map (§5.4) | core width versus energy |
| another EM option (run card `em_option`) | longitudinal and lateral shower shapes |
| Cherenkov light in the crystal as a separate node-1 term (§5.4 last row) | energy scale of electrons versus MIPs (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/ecal.binding.example.json`: candidates beam energy (φ) analytic reweighting; dead
material and wrap reflectivity resimulation or surrogate model; k_B, light yield, gain and noise rerun. Degeneracies
to expect (§12): the binomial thinning chain yield × collection × PDE (on the efficiency-map path LY and ε_c scale
together), addition in quadrature, scale and response shape.
