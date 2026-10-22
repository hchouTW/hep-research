# Sci-fix ledger: sources read for locators

Sources and locators behind the `locator` basis of the oracle-independence records in `sci-fixes.json`
(docs/maintenance.md, oracle rules). An `independence` record with `basis: "locator"` names its source (`source_id`)
and its located claim (`locator_id`) here; `tests/tools/test_scifix_ledger.py` checks that both exist and that the
source was read at `page` level or better. The two tables are **generated** from `scifix-sources.json` and
`scifix-claims.json`: edit those files, then from the plugin root run
`python3 core/evidence/ledger.py --sources docs/evidence/scifix-sources.json --claims docs/evidence/scifix-claims.json --namespace scifix --strict`
and `python3 core/evidence/render_index.py --sources docs/evidence/scifix-sources.json --claims docs/evidence/scifix-claims.json --index docs/evidence/scifix-index.md --write`.
Each source row carries its own verification date; a claim's strength never exceeds its source's level.

## Source table

<!-- BEGIN GENERATED: source-table (edit scifix-sources.json, then run core/evidence/render_index.py --write) -->
| ID | Title | Authors | Year | DOI / URL | Tier | Level |
|---|---|---|---|---|---|---|
| scifix:S01 | Review of Particle Physics 2024, 34. Passage of Particles Through Matter (rev. August 2023) | Particle Data Group | 2024 | https://pdg.lbl.gov/2024/reviews/rpp2024-rev-passage-particles-matter.pdf | 1 | page |
| scifix:S02 | Review of Particle Physics 2024, 35. Particle Detectors at Accelerators | Particle Data Group | 2024 | https://pdg.lbl.gov/2024/reviews/rpp2024-rev-particle-detectors-accel.pdf | 1 | page |
| scifix:S03 | Review of Particle Physics 2025, 35. Particle Detectors at Accelerators | Particle Data Group | 2025 | https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf | 1 | page |
| scifix:S04 | Atomic and Nuclear Properties of Materials: water (liquid) | Particle Data Group | 2024 | https://pdg.lbl.gov/2024/AtomicNuclearProperties/HTML/water_liquid.html | 1 | page |
| scifix:S05 | Rank-normalization, folding, and localization: an improved R-hat for assessing convergence of MCMC | A. Vehtari, A. Gelman, D. Simpson, B. Carpenter, P.-C. Buerkner | 2021 | 10.1214/20-BA1221 | 1 | full-text |
| scifix:S06 | Unified approach to the classical statistical analysis of small signals | G. J. Feldman, R. D. Cousins | 1998 | 10.1103/PhysRevD.57.3873 | 1 | full-text |
| scifix:S07 | Pierre Auger Collaboration, JCAP 03 (2019) 018 | Pierre Auger Collaboration | 2019 | https://arxiv.org/abs/1811.04660v2 | 1 | full-text |
| scifix:S08 | A Comparison of Methods for Computing Autocorrelation Time | M. B. Thompson | 2010 | https://arxiv.org/abs/1011.0175v1 | 1 | full-text |
| scifix:S09 | Review of Particle Physics 2024, 30. Cosmic Rays | Particle Data Group | 2024 | https://pdg.lbl.gov/2024/reviews/rpp2024-rev-cosmic-rays.pdf | 1 | full-text |
| scifix:S10 | Gaisser, Hillas, Proc. 15th ICRC 8 (1977) 353 | T. K. Gaisser, A. M. Hillas | 1977 | https://ui.adsabs.harvard.edu/abs/1977ICRC....8..353G | 1 | not-opened |
| scifix:S11 | Unbiased Elimination of Negative Weights in Monte Carlo Samples | J. R. Andersen, A. Maier | 2021 | 10.1140/epjc/s10052-022-10372-3 | 1 | page |
| scifix:S12 | Bootstrap Inference in the Presence of Bias | G. Cavaliere, S. Gonçalves, M. Ø. Nielsen | 2022 | https://arxiv.org/abs/2208.02028v1 | 1 | page |
| scifix:S13 | Review of Particle Physics 2024, 40. Statistics (rev. August 2023) | G. Cowan (Particle Data Group) | 2024 | https://pdg.lbl.gov/2024/reviews/rpp2024-rev-statistics.pdf | 1 | page |
<!-- END GENERATED: source-table -->

## Claim ledger

<!-- BEGIN GENERATED: claim-ledger (edit scifix-claims.json, then run core/evidence/render_index.py --write) -->
| claim_id | claim (paraphrased) | type | source | location | supported scope | limitation |
|---|---|---|---|---|---|---|
| scifix:C01 | The Bethe equation gives the mean rate of energy loss of a moderately relativistic heavy charged particle. | general_method | scifix:S01 | RPP 2024 eq. (34.5), p. 4 | pid_separation_power.py dE/dx (DR-WP2-06-PID) | |
| scifix:C02 | The maximum energy transfer to an electron in a single collision, W_max, enters the Bethe equation. | general_method | scifix:S01 | RPP 2024 eq. (34.4), p. 3 | pid_separation_power.py dE/dx (DR-WP2-06-PID) | |
| scifix:C03 | The coefficient K of the Bethe equation and the other constants are listed in Table 34.1. | general_method | scifix:S01 | RPP 2024 Table 34.1, p. 2 | pid_separation_power.py dE/dx (DR-WP2-06-PID) | |
| scifix:C04 | The Highland formula gives the width theta_0 of the projected multiple-scattering angle distribution. | general_method | scifix:S01 | RPP 2024 eq. (34.16), p. 16 | multiple_scattering.py, Highland leading term (DR-WP2-06-MS) | |
| scifix:C05 | The Cherenkov angle satisfies cos theta_C = 1/(n beta). | general_method | scifix:S01 | RPP 2024 eq. (34.41), p. 33 | cherenkov_angle.py (TH9-MASSES, DR-WP1-01) | |
| scifix:C06 | The number of Cherenkov photons per unit length scales as z^2 sin^2 theta_C (N = N0 L z^2 sin^2 theta_C for a detector of response N0). | general_method | scifix:S01 | RPP 2024 eq. (34.43), p. 34 | cherenkov_angle.py yield (TH9-MASSES, DR-WP1-01) | |
| scifix:C07 | The Frank-Tamm photon spectrum per unit length and wavelength, integrated over wavelength, gives the Cherenkov yield. | general_method | scifix:S01 | RPP 2024 eq. (34.44), p. 34 | cherenkov_angle.py yield (DR-WP1-01) | |
| scifix:C08 | The calorimeter energy resolution is parametrized as stochastic, noise and constant terms added in quadrature. | general_method | scifix:S02 | RPP 2024 eq. (35.43), p. 82 | calorimeter_resolution.py fit (DR-WP2-06-CALO) | |
| scifix:C09 | The 2025 edition gives the same calorimeter energy resolution parametrization (stochastic, noise and constant terms in quadrature) under a new equation number. | general_method | scifix:S03 | RPP 2025 eq. (35.50), p. 92 | calorimeter_resolution.py fit (DR-WP2-06-CALO) | |
| scifix:C10 | The Gluckstern formula gives the momentum resolution from the position measurement error of N equally spaced points. | general_method | scifix:S03 | RPP 2025 eq. (35.68), p. 112 | multiple_scattering.py crossover and MDR (DR-WP2-06-MS) | |
| scifix:C11 | The multiple-scattering contribution to the momentum resolution (with the 0.016 coefficient). | general_method | scifix:S03 | RPP 2025 eq. (35.70), p. 112 | multiple_scattering.py; the script uses the Highland leading term (scifix:C04) instead, as tracking-and-vertexing.md states | |
| scifix:C12 | The mean excitation energy of liquid water is I = 79.7 eV. | general_method | scifix:S04 | PDG Atomic and Nuclear Properties, water (liquid) page | pid_separation_power.py water (DR-WP2-06-PID) | |
| scifix:C13 | The split R-hat compares between- and within-chain variances of split chains. | general_method | scifix:S05 | arXiv:1903.08008v5 eqs. (1)-(4) | bayes_diagnostics.py (BAYES-T24) | |
| scifix:C14 | The combined autocorrelation estimate over chains. | general_method | scifix:S05 | arXiv:1903.08008v5 eq. (10) | bayes_diagnostics.py (BAYES-T24) | as printed, the lag term is scaled by N/(N-1); the code follows Stan/ArviZ (biased autocovariance) |
| scifix:C15 | The effective sample size is ESS = NM/tau with tau = 1 + 2 sum of the autocorrelations, truncated as stated. | general_method | scifix:S05 | arXiv:1903.08008v5 eqs. (12)-(13) | bayes_diagnostics.py (BAYES-T24) | |
| scifix:C16 | Rank normalization of the draws before R-hat and ESS. | general_method | scifix:S05 | arXiv:1903.08008v5 eq. (14) | bayes_diagnostics.py (BAYES-T24) | |
| scifix:C17 | Folding of the draws about the median for the folded R-hat. | general_method | scifix:S05 | arXiv:1903.08008v5 eq. (15) | bayes_diagnostics.py (BAYES-T24) | |
| scifix:C18 | Tail ESS from the 5% and 95% quantile indicators. | general_method | scifix:S05 | arXiv:1903.08008v5 eq. (16) | bayes_diagnostics.py (BAYES-T24) | the code takes the 95% indicator as x >= q95 (equal unless draws tie at q95) |
| scifix:C19 | The Monte Carlo standard error of a quantile. | general_method | scifix:S05 | arXiv:1903.08008v5 eq. (20) | bayes_diagnostics.py (BAYES-T24) | |
| scifix:C20 | The Feldman-Cousins ordering ratio R = P(n\|mu)/P(n\|mu_best) and the adjustment that makes the upper end non-increasing in the background. | general_method | scifix:S06 | Phys. Rev. D 57 (1998) 3873, eq. (4.1) and Sec. IV.A, p. 8 | core/stats/poisson_diagnostics.py (FC-MONOTONE) | |
| scifix:C21 | Table IV gives the 90% C.L. intervals for the Poisson signal mean with known background, which the repository fixture transcribes. | general_method | scifix:S06 | Phys. Rev. D 57 (1998) 3873, Table IV, p. 37 | tests/core/fixtures/fc1998_tables.json (FC-MONOTONE) | |
| scifix:C22 | The Gaisser-Hillas form of the longitudinal shower profile. | general_method | scifix:S07 | arXiv:1811.04660v2 eq. (2.1), p. 3 | xmax_gaisser_hillas.py (DR-WP1-02) | |
| scifix:C23 | The integrated autocorrelation time is tau = 1 + 2 sum_k rho_k. | general_method | scifix:S08 | arXiv:1011.0175v1 eq. (4) | bayes_diagnostics.py (BAYES-T24) | |
| scifix:C24 | The autocorrelation time of an AR(p) process, which gives (1 + rho)/(1 - rho) for AR(1). | general_method | scifix:S08 | arXiv:1011.0175v1 eq. (7), p. 2 | test_bayes_diagnostics.py AR(1) ESS (BAYES-T24) | |
| scifix:C25 | For AR(1) with rho = 0.98 the autocorrelation time is 99. | general_method | scifix:S08 | arXiv:1011.0175v1 p. 3 | test_bayes_diagnostics.py AR(1) ESS (BAYES-T24) | |
| scifix:C26 | The PDG cosmic-ray review does not state the Gaisser-Hillas form. | general_method | scifix:S09 | RPP 2024 30. Cosmic Rays (whole review) | where the Gaisser-Hillas form was looked for (DR-WP1-02) | |
| scifix:C27 | Cell resampling: around a negative-weight event (the seed) a cell grows until the summed weight of the events inside is non-negative, then every weight in the cell is replaced by \|w_i\| sum_C w_j / sum_C \|w_j\|, which preserves the cell's summed weight; the steps are applied successively to each negative-weight event. | general_method | scifix:S11 | arXiv:2109.07851v2 Sec. 2, eq. (2.2), p. 3 (successive application, p. 4) | skills/hep-ml/assets/hep_metrics.py cell_resample (ML-NEGWEIGHTS) | the paper's distance is a phase-space distance on physics objects (Sec. 2.1); cell_resample uses Euclidean distance in the model's input features; the seed order is discussed in Appendix A (not read) |
| scifix:C28 | With H_n(u) = P(p_n <= u) the distribution function of the bootstrap p-value p_n, a test that rejects H0 whenever H_n(p_n) <= alpha is exact (prepivoting, Beran 1987). | general_method | scifix:S12 | arXiv:2208.02028v1 Sec. 2, p. 8 (H_n defined p. 7) | skills/hep-statistics/scripts/periodicity_scan.py red-noise global p (PERIODICITY-REFIT) | |
| scifix:C29 | Double bootstrap: the second-level bootstrap p-value is p*_n = P**(T**_n <= T*_n), computed on a further bootstrap sample drawn from the first-level one, and the double bootstrap modified p-value is p~_n = H^_n(p_n) = P*(p*_n <= p_n). | general_method | scifix:S12 | arXiv:2208.02028v1 Sec. 3.2.2, pp. 14-15 | skills/hep-statistics/scripts/periodicity_scan.py red-noise global p (PERIODICITY-REFIT) | |
| scifix:C30 | Theorem 3.2: under Assumptions 1, 2 and 3 the double bootstrap modified p-value p~_n = H^_n(p_n) converges in distribution to U[0,1], whether or not the original bootstrap p-value is asymptotically uniform. | general_method | scifix:S12 | arXiv:2208.02028v1 Sec. 3.2.2, Theorem 3.2, p. 15 | skills/hep-statistics/scripts/periodicity_scan.py red-noise global p (PERIODICITY-REFIT) | |
| scifix:C31 | Written with R = sqrt(lambda/\|X0'\|), L = sqrt(\|X0'\| lambda) and X0' = X0 - Xmax, the Gaisser-Hillas function is a Gaussian with standard deviation L multiplied by a term that distorts it, with the asymmetry governed by R. | general_method | scifix:S07 | arXiv:1811.04660v2 eq. (3.1) and the sentence below it, p. 5 | xmax_gaisser_hillas.py Gaussian limit at large x_max (DR-WP1-02) | |
| scifix:C32 | An estimator is consistent if its estimate converges in probability to the true value as the amount of data increases; its bias b = E[theta_hat] - theta is zero for an unbiased estimator, and the bias depends on the metric (theta_hat^2 is not in general unbiased for theta^2). | general_method | scifix:S13 | RPP 2024 sec. 40.2 items (a) and (b), p. 2 | calorimeter_resolution.py toy truth recovery (DR-WP2-06-CALO) | |
<!-- END GENERATED: claim-ledger -->
