# RICH: simulator-calibration specialization

Part B §11.1 items 1–8 for a ring-imaging Cherenkov detector (radiator, optional mirrors, pixelated photodetector),
from §3.1 derivation basis (1), the RICH row of §12 and the full optical tracking path of §11.4. Folder rules:
[index](index.md).

## 1. Stage mapping and injection-point splits

| Node | Abstract node | Content (§3.1) | g4sim object |
|---|---|---|---|
| `source` | 0 | tracks of known momentum and species | `simulation-request/1` source |
| `radiator` | 1 (with 2, 3, 4a) | radiator traversal, Cherenkov emission (n, dispersion), optical propagation, mirrors, PDE at the surface | `g4sim_run`, full optical tracking |
| `sensor` | 4b | photodetector gain (MaPMT, HPD, SiPM, MCP-PMT) | response stage 3 |
| `electronics` | 5 | threshold, time | response stage 4 |
| `reco` | 6–7 | light spots, ring and angle | reconstruction |

On the full optical tracking path Cherenkov photons, their transport and the surface PDE are all node 1: there is no
hand-off before stage 3, and neither injection reference (known photon count, single photoelectron) can be declared
unless the surface `efficiency` is set to 1 and the workflow thins `photons.csv` by photon energy itself (§11.4).
The semantic graph may still keep nodes 2, 3 and 4a separate; they then bind to `g4sim_run` together.

## 2. Mechanisms and parameterization

| Parameter (§12) | Mechanism / node | Parameterization | g4sim field (Table 2 row) |
|---|---|---|---|
| refractive index and dispersion | physics process / 1 | n(E) table, or a scale of it | detector-spec `optical/rindex` (optical row) |
| mirror alignment | geometry / 3, light path | tilt and shift | detector-spec `params` (geometry row); an overlay θ waits for D83 (7) |
| PDE | yield / 4a | surface `efficiency` spectrum | detector-spec `optical_surfaces/<s>/efficiency` (optical row) |
| gain | 4b | multiplicative, ENF | `sensor` stage `gain` |

Every node-1 parameter changes the light path and needs resimulation, and for the optical row the production run is
resimulated with it (§11.4 Table 2).

## 3. Kernel properties

Node 1 samplable black box; 4b and 5 densities (Poisson photoelectrons, gain with ENF); 6–7 deterministic (ring
association is an association mechanism, §3.2).

## 4. Storage recommendations

Keep `photons.csv` (photon energy per detected photon) when a PDE(E) is to be applied after transport; record the hit
file for re-digitization of stages 3–5 and simreco columns for the ring fit.

## 5. Reference catalog

Tracks of known momentum and species (known input: several β break "refractive index and geometric scale", §3.5);
saturated rings of β ≈ 1 particles (population feature, *Inferred*); momentum from the tracker (internal
constraint, by hash).

## 6. Special functionals and link functions

Cherenkov angle: location, identity link (signed residual) or log. Angle resolution per photon and per ring: core
width, log. Photon count per ring: multiplicity, log. Ring-hit background: tail or efficiency, logit.

## 7. V_model correlation kernel (advisory)

| Observable group (functional, link) | f | C | ℓ |
|---|---|---|---|
| location (angle), identity or log | no literature value | no literature value | no literature value |
| core width, log | no literature value | no literature value | no literature value |
| multiplicity, log | no literature value | no literature value | no literature value |

## 8. Alternative hypotheses (advisory)

| Simulation setting | Observable expected to see it |
|---|---|
| Rayleigh scattering in the radiator off versus on (run card optical switch) | photon count per ring, hits off the ring |
| measured rindex dispersion table instead of a constant index | angle width versus β |
| absorption in the radiator added (`absorption_length_mm` table) | photon count versus path length in the radiator (*Inferred*) |

## Node-binding example

`assets/simulation-calibration/rich.binding.example.json`: refractive index, mirror tilt and surface efficiency
resimulation or surrogate model; gain rerun. Degeneracies (§12): refractive index and geometric scale; photon count ×
per-photon resolution.
