# Core Detector Equations (E1-E17)

Seventeen cross-cutting relations used across the detector-response references; subsystem formulas (shower scales, Gluckstern, TOF separation, ENC, jitter, dead time) are in the subsystem and front-end files. For each: symbols and units,
assumptions and validity, which quantity is observable and which latent, and where its
parameters come from. Equations are numbered E1-E17.
Labels: *exact*, *approximate*, *asymptotic*, *empirical*, *detector-specific*.

| No. | Relation | Symbols, units, validity | Observable / latent | Parameter source |
|---|---|---|---|---|
| E1 | `y = f(x;theta) + epsilon`, `p(y|x,theta)` | `x` latent particle/event properties; `y` recorded observables; `theta` detector, geometry, field, material, electronics, environment, calibration; `epsilon` fluctuation and noise. Approximate when `epsilon` is Gaussian; Poisson and Landau-like noise violate it | `y` observed; `x`, `theta` inferred | `theta` from calibration, alignment, monitoring; `p(y|x,theta)` from simulation and test beam |
| E2 | `pT = 0.2998 |q| B rho` (usually rounded to 0.3) | `pT` in GeV/c, `B` in T, bending radius `rho` in m, `q` in units of `e`. Exact for a helix in a uniform field in these units; rigidity `R = p/q` is what a spectrometer measures | curvature observed; `pT`, `q` latent | field map from measurement; `rho` from the track fit |
| E3 | `chi^2 = r^T V^{-1} r` | `r` residual vector, `V` its covariance. Optimal for Gaussian errors; `V` must be the residual covariance, not the measurement covariance | hits observed; track parameters latent | `V` from hit resolutions, material, alignment |
| E4 | `theta_0 = (13.6 MeV/(beta c p)) z sqrt(x/X_0)[1 + 0.038 ln(x z^2/(X_0 beta^2))]` | Highland; `x/X_0` thickness in radiation lengths, `p` in MeV/c, `z` projectile charge. Approximate (about 11% for `1e-3 < x/X_0 < 100`); core only, tails are non-Gaussian. `theta_0` is the rms of the projected (plane) angle (`theta_space,rms = sqrt(2) theta_0`); for a stack use the total `x/X_0` once, not per-layer `theta_0` added in quadrature, which comes out too small (PDG) | scattering angle latent | `X_0` from tabulations |
| E5 | `-<dE/dx> = K z^2 (Z/A)(1/beta^2)[0.5 ln(2 m_e c^2 beta^2 gamma^2 W_max/I^2) - beta^2 - delta/2]`, `K = 0.307075 MeV mol^-1 cm^2` | Mean loss, heavy charged particles, intermediate energies (approximate). Fluctuations: highly skewed Landau-Vavilov for thin and moderate absorbers (PDG: moderate thickness means Vavilov's `kappa`, or Rossi's `G`, below about 0.05-0.1); for thin silicon use Bichsel's straggling functions, which include atomic binding; Gaussian only for thick absorbers | deposited charge/light observed; `beta gamma` latent | `I`, `delta` from tabulated fits |
| E6 | `v_d = mu E`; `sigma = sqrt(2 D L/v_d) = C_D sqrt(L)` | Drift velocity, mobility `mu`, diffusion `D`; low-field constant-mobility form is approximate; real gases need `v_d(E,B,T,P)` and `C_D` (um/sqrt(cm)) | arrival time/position observed; origin latent | measured in the operating gas or liquid |
| E7 | `cos theta_C = 1/(n beta)`; `p_th = m c/sqrt(n^2-1)`; `d^2N/(dx dE) ≈ 370 z^2 sin^2 theta_C eV^-1 cm^-1` (`z` projectile charge number) | Cherenkov angle, threshold, yield before detection efficiency; exact kinematics, approximate yield | photon hits observed; `beta` latent | `n(lambda,T,P)` from monitoring |
| E8 | `beta = L/(c t)`; `m^2 = p^2(1/beta^2 - 1)` | `L` track path length, `t` flight time; exact. Separation falls as `1/p^2` | `t` observed; `beta`, `m^2` inferred | `L` from the track fit; `t0`, clock from calibration |
| E9 | `sigma_E/E = a/sqrt(E) ⊕ b/E ⊕ c` | Quadrature sum: stochastic `a`, noise `b`, constant `c`; empirical decomposition | energy inferred | fit to test-beam or in-situ data |
| E10 | `sigma/N ≈ sqrt(F/N_pe)` | Photostatistics with excess-noise factor `F >= 1`; Poisson-limited | `N_pe` observed | `F` from single-photoelectron calibration |
| E11 | `A = N_fid/N_gen`, `eps = N_success/N_eligible`, `P = N_matched/N_selected`; `P(S) = P(A)P(R|A)P(S|R,A)` | Chain rule exact for consistent denominators; a naive product of separately measured efficiencies is not | `A` truth only; `eps` truth in simulation, proxies in data; `P` truth matching (simulation) | counts in simulation; proxies in data |
| E12 | `r = x_meas - x_pred`, `p = r/sigma_r`, `V_r = V_meas + V_pred - C - C^T` | Residual, pull, residual covariance with measurement-prediction correlation `C`; biased residual `V_r = V_meas - V_pred` | measured and predicted | fit covariance |
| E13 | `SF = eps_data/eps_MC` | Efficiency scale factor; both measured identically, in the analysis phase space | data and simulation | tag-and-probe or equivalent |
| E14 | `V_f ≃ J V_x J^T`, `J_ij = df_i/dx_j` | First-order propagation; fails for thresholds, migration, strongly nonlinear or asymmetric responses | nuisance covariance input | variations of the reconstruction |
| E15 | `n_i^reco = sum_j R_ij n_j^truth + b_i` | Response matrix, convention `R_ij = P(reco bin i | truth bin j)` (declare it; SKILL.md invariant 1): off-diagonal = migration (resolution and scale), truth-bin sums < 1 = inefficiency (and acceptance) when declared inside the matrix, `b_i` background, model dependence via the truth spectrum | reco observed; truth latent | simulation, validated on data |
| E16 | `N_sigma` (separation of two species' means in resolution units) | PID separation; single-measurement or quadrature convention, defined with the `sqrt(2)` conversion in [performance metrics](performance-metrics-and-residual-diagnostics.md); Gaussian approximation, unreliable with tails or few photons | discriminating variable | fitted distributions per species |
| E17 | Binomial/Poisson likelihoods; Clopper-Pearson or Wilson intervals | Efficiencies (binomial), counts (Poisson); Gaussian intervals fail near 0 or 1 | counts | counting |

**Reading the table.** Every relation has a domain of validity; using one outside it
(Bethe-Bloch at low `beta gamma`, Highland tails, Gaussian `N_sigma`, linear
propagation through a threshold) is a common source of quiet errors.

## Common misconceptions and failure modes

- **Equation used outside its validity range** without noticing.
- **Parameters treated as constants** when they are calibrated, time-dependent quantities.
- **Gaussian approximations applied to Poisson, Landau, or heavy-tailed quantities.**
- **The wrong covariance in `chi^2` or pulls** (measurement instead of residual covariance).
- **Symbols reused across detectors** with different meanings; check the [glossary](detector-glossary.md).

This file is the single home of these relations; the [detector principles summary](detector-principles-summary.md) points here. Sources: PDG RPP 2024, Passage of particles through matter (K, Highland and its use for a stack, Landau-Vavilov and Bichsel, Cherenkov yield), read 2026-10-14.
