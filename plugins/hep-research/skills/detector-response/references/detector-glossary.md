# Detector Glossary: Symbols, Acronyms, and Adopted Conventions

Symbols and terms used across the detector-response references, from the
[measurement framework](detector-measurement-framework.md) to the [comparison tables](detector-comparison-tables.md).
Where communities differ, one convention is adopted here and stated.

## Symbols

| Symbol | Meaning | Units |
|---|---|---|
| `x`, `y`, `theta`, `epsilon` | latent properties, observables, nuisance parameters, noise | - |
| `p`, `q`, `R = p/q` | momentum, charge, rigidity (`R` also denotes the response ratio, the response matrix `R_ij`, the noise autocorrelation matrix in front-end electronics, and resistances `R_s`, `R_p`; context fixes the meaning) | GeV/c, e, GV |
| `rho` | bending radius (E2); density in `xi` (signal formation); noise correlation coefficient (front-end electronics) | m; g/cm^3; - |
| `z`; `Z`, `A` | projectile charge number; atomic number and atomic mass (g/mol) of the traversed material (cosmic-ray texts also write a nucleus's own charge as `Z`; then `z = Z` of the projectile, so say which is meant) | e; -, g/mol |
| `pT`, `eta`, `phi` | transverse momentum, pseudorapidity, azimuth | GeV/c, -, rad |
| `B`, `E` | magnetic, electric field | T, V/cm |
| `X_0`, `lambda_I`, `R_M`, `E_c` | radiation length, interaction length, Moliere radius, critical energy | g/cm^2 or cm, MeV |
| `beta`, `gamma` | `v/c`, Lorentz factor | - |
| `n`, `theta_C` | refractive index, Cherenkov angle | -, rad |
| `v_d`, `D`, `C_D`, `tau_e` | drift velocity, diffusion coefficient, diffusion constant `C_D = sqrt(2D/v_d)` (longitudinal and transverse values differ), electron lifetime | cm/us, cm^2/s, um/sqrt(cm), us |
| `W_max`, `I`, `delta` | maximum energy transfer, mean excitation energy, density correction | MeV, eV, - |
| `xi`, `kappa` | Landau scale `(K/2)(Z/A) z^2 rho x/beta^2`, `xi/W_max` | MeV, - |
| `t_p`, `tau`, `tau_d` | peaking time, shaper constant, dead time | ns |
| `E_w`, `phi_w` | weighting field, weighting potential | 1/cm, - |
| `alpha` | Townsend coefficient (gas) or current-damage constant (silicon) | 1/cm; A/cm |
| `n` | refractive index, shaper order, dynode count, or true rate (context) | - |
| `F` | excess-noise factor (`F_Fano` for the Fano factor) | - |
| residual sign | `r = x_meas - x_pred` in the signed track coordinate (convention of these references): a drift-chamber `t0` offset gives opposite-sign residuals for passages left and right of the wire, a wire-position offset the same sign; in the unsigned drift radius the two patterns swap | - |
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
- **Response** = `<x_reco>/x_true` at fixed truth (in a finite truth bin, state mean of ratio or
ratio of means); **bias** = `<x_reco - x_true>`; **scale** = the multiplicative part of the
response; **calibration** = the procedure that corrects them; **alignment** = element positions,
  distinct from timing/drift calibration.
- **Unbiased residual** = prediction excludes the measurement; **biased** = includes it.
- **Muon types**: standalone, combined, segment-tagged, calorimeter-tagged, trigger-level
  ([muon systems](muon-systems.md)).
- **Electron-equivalent** vs **nuclear-recoil** energy scales are distinct
  ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md)).
- Relations are labeled *exact*, *approximate*, *asymptotic*, *empirical*, or
  *detector-specific* where they appear.
