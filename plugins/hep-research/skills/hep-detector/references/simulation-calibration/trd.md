# TRD: simulator-calibration specialization

Part B §11.1 items 1–8 for a transition-radiation detector (radiator plus gas drift chambers), from §3.1 derivation
basis (2), the TRD row of §12 and §11.4. Folder rules: [index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object |
|---|---|---|---|
| `source` | 0 | electrons and pions of known momentum | `simulation-request/1` source |
| `radiator_gas` | 1 | dE/dx plus TR photons | `g4sim_run` (XTR radiator in the run card, PAI optional) |
| `ionisation` | 2 | ionisation electrons | response stage `ionisation` (W value, Fano) |
| `drift` | 3 | drift, diffusion | `drift_table` stage (hashed table) |
| `gas_gain` | 4b | gas gain | `sensor` stage gain (*Inferred* mapping: no avalanche stage kind) |
| `adc` | 5 | shaping, ADC | response stage 4 |
| `reco` | 6–7 | clusters, likelihood | reconstruction |

There is no 4a node. An ⁵⁵Fe-type source in the gas would be a mid-chain injection on the edge into `ionisation`
(*Inferred*); g4sim has no hand-off there, so it is not declared in the example.

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| TR yield | yield / 1 | §12 writes a yield factor; g4sim has none | radiator geometry in detector-spec `params` (geometry row) as the node-1 handle |
| dE/dx model | discrete choice / 1 | enumeration | run card `/physics/pai`: enter as a discrete model M |
| gas gain | 4b | multiplicative | `sensor` stage `gain` |
| ADC noise | 5 | width | `electronics` stage `noise_sigma` |

## 3. Kernel properties

Node 1 samplable black box; `ionisation` density (g4sim's `response.ionisation_quanta` draws a Poisson count when
the mean E/W is at most 10, `POISSON_LIMIT`, and otherwise a Gaussian of width √(F·mean), rounded and cut at 0, read
from the plugin source; its `log_density` is the Poisson pmf on the first branch and the discrete rounded-Gaussian
pmf on the second, as in §11.4's rule for the photon count; the Poisson branch has variance mean, not F·mean);
`drift` deterministic given its table; 4b and 5 densities; reconstruction deterministic.

## 4. Storage recommendations

Hits for re-digitization of stages 2–5; the reconstruction's output columns for the likelihood (the user's
reconstruction: simreco has no TRD reconstruction); the cluster-charge spectrum must keep its
tail (the tail functional needs local ESS, §3.3).

## 5. Reference catalog

Pions and electrons of known momentum (known input). §12: the width alone cannot separate TR yield and gas gain;
samples of the heavier species below the TR onset (γ ≲ 10³: about 140 GeV/c for pions and 940 GeV/c for protons,
[particle identification](../particle-identification.md); PDG RPP 2025 sec. 35.6.5) and known momentum are needed;
above the onset the hadron sample carries TR itself and no longer fixes the gain. Electron samples from photon
conversions (tag and probe, *Inferred*).

## 6. Special functionals and link functions

Mean cluster charge: location, log. Cluster-charge tail above a threshold: tail, logit (D41 open: P5/G4 decisions on
tail functionals are rejected until the determining region is defined). Hadron (pion or proton) efficiency at
fixed electron efficiency, the inverse of the rejection factor: efficiency, logit. Cluster-charge spectrum: normalized shape, alr/ilr.

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C | ℓ |
|---|---|---|---|
| location, log | no literature value | no literature value | no literature value |
| tail, logit | no literature value | no literature value | no literature value |
| shape, alr/ilr | no literature value | no literature value | no literature value |

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| another XTR radiator class (regular versus irregular foils) | electron cluster-charge tail at fixed momentum |
| dE/dx without the PAI model in the gas | pion cluster-charge width (Landau tail) |
| a drift table from another gas computation | cluster-time distribution (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/trd.binding.example.json` (two enumerated models that differ in the PAI entry):
foil thickness resimulation or surrogate model; gas gain and ADC noise rerun. Degeneracies (§12): mean TR yield ×
gas gain; width from Landau fluctuations and the TR spectrum.
