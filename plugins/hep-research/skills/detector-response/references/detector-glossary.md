# Detector Glossary: Symbols, Acronyms, and Adopted Conventions

Symbols and terms used across the detector-response references, from the
[measurement framework](detector-measurement-framework.md) to the [comparison tables](detector-comparison-tables.md).
Where communities differ, one convention is adopted here and stated.

## Symbols

| Symbol | Meaning | Units |
|---|---|---|
| `x`, `y`, `theta`, `epsilon` | latent properties, observables, nuisance parameters, noise | - |
| `p`, `q`, `R = p/q` | momentum, charge, rigidity (`R` is used for rigidity only) | GeV/c, e, GV |
| `rho` | bending radius of a track in a magnetic field | m |
| `z`; `Z`, `A` | projectile charge number; atomic number and mass number of the traversed material (cosmic-ray texts also write a nucleus's own charge as `Z`; then `z = Z` of the projectile, so say which is meant) | e; -, g/mol |
| `pT`, `eta`, `phi` | transverse momentum, pseudorapidity, azimuth | GeV/c, -, rad |
| `B`, `E` | magnetic, electric field | T, V/cm |
| `X_0`, `lambda_I`, `R_M`, `E_c` | radiation length, interaction length, Moliere radius, critical energy | g/cm^2 or cm, MeV |
| `beta`, `gamma` | `v/c`, Lorentz factor | - |
| `n`, `theta_C` | refractive index, Cherenkov angle | -, rad |
| `v_d`, `D`, `C_D`, `tau_e` | drift velocity, diffusion, diffusion coefficient, electron lifetime | cm/us, cm^2/s, um/sqrt(cm), us |
| `theta_L` | Lorentz angle | rad |
| `N_pe`, `F`, `QE` | photoelectrons, excess-noise factor, quantum efficiency | -, -, - |
| `A`, `eps`, `P` | acceptance, efficiency, purity (`A` alone, in metric context) | - |
| `e/h` | calorimeter compensation ratio: response to the electromagnetic over the non-electromagnetic hadronic component | - |
| `e/pi` | electron-pion separation (TRD, calorimeter PID), quoted as pion rejection at fixed electron efficiency | - |
| `r`, `p` (pull), `V_r`, `chi^2` | residual, pull, residual covariance, `chi^2` | as measured |
| `SF` | efficiency scale factor `eps_data/eps_MC` | - |
| `J`, `V_x`, `V_f` | Jacobian, input covariance, propagated covariance | - |
| `R_ij`, `n^reco`, `n^truth`, `b` | response matrix, reconstructed/truth spectra, background | - |
| `N_sigma` | separation of two species' means in resolution units; conventions in [performance metrics](performance-metrics-and-residual-diagnostics.md) | - |

## Acronyms

ADC/TDC analog/time-to-digital converter; APD avalanche photodiode; CFD constant-fraction
discriminator; CCD charge-coupled device; DEPFET depleted field-effect transistor;
DIRC detection of internally reflected Cherenkov light; ECAL/HCAL electromagnetic/hadronic
calorimeter; ENC equivalent noise charge; GEM gas electron multiplier; IACT imaging
atmospheric Cherenkov telescope; LGAD low-gain avalanche detector; MAPS monolithic
active pixel sensor; MC Monte Carlo; MCP microchannel plate; MIP minimum-ionizing
particle; MPGD micro-pattern gaseous detector; MPV most probable value; MRPC/RPC
(multi-gap) resistive plate chamber; MWPC multi-wire proportional chamber; PID particle
identification; PMT photomultiplier tube; RICH ring-imaging Cherenkov; SiPM silicon
photomultiplier; SPE single photoelectron; TOF time of flight; TOP time of propagation;
TPC time projection chamber; TRD transition radiation detector; WLS wavelength shifter.

## Adopted conventions

- **Resolution** = width of `x_reco - x_true` (or the relative form) for a population
  binned in *truth*, with estimator (core `sigma`, `sigma_68`, `IQR/1.349`,
  `1.4826 MAD`, RMS or std; defined in [performance metrics](performance-metrics-and-residual-diagnostics.md)) stated, and the
  tail fraction quoted separately.
- **Efficiency** = successes / eligible with the eligible population and matching rule
  named; **acceptance** is truth-only.
- **Fake** = selected object with no truth match; **mis-ID** = real particle with the
  wrong species; **duplicate** = truth matched by more than one object (rates and
  denominators in [performance metrics](performance-metrics-and-residual-diagnostics.md)).
- **Response** = `<x_reco/x_true>` at fixed truth; **calibration** = the procedure that
  corrects it; **scale** = central offset (bias); **alignment** = element positions,
  distinct from timing/drift calibration.
- **Unbiased residual** = prediction excludes the measurement; **biased** = includes it.
- **Muon types**: standalone, combined, segment-tagged, calorimeter-tagged, trigger-level
  ([muon systems](muon-systems.md)).
- **Electron-equivalent** vs **nuclear-recoil** energy scales are distinct
  ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md)).
- Relations are labeled *exact*, *approximate*, *asymptotic*, *empirical*, or
  *detector-specific* where they appear.
