# Hadron structure: entry page

Purpose: the entry to hadron-structure theory in hep-theory: inclusive and polarized DIS, Drell-Yan, nuclear effects
and nuclear PDFs, SIDIS, fragmentation and TMDs, small-x physics and saturation, exclusive processes and GPDs, and the
theory inputs of global PDF fits. It routes each request to its page, lists the convention fields every
hadron-structure prediction shares, and says what is computed and what is only stated as rules.

Status: hub (Th14 onward); the pages it links carry their own status lines and sources. Modules marked "planned" have
no page yet: say so and apply the general discipline of hep-theory.

## Routing

| Module | Topic | Page | Computed by the plugin | Rules only |
|---|---|---|---|---|
| A | Unpolarized inclusive DIS (NC, CC, neutrino) | [DIS structure functions](dis-structure-functions.md) (Th14) | LO structure functions and cross sections from user-supplied parton values (`structure_functions_lo.py`); sum-rule integrals (`sum_rules.py`) | coefficient functions beyond LO, heavy-quark schemes, target-mass corrections, higher twist |
| B | Polarized DIS (g_1, g_2, sum rules) | [polarized DIS](polarized-dis.md) (Th17) | LO g_1 first moments, the Bjorken integral at LO and the Ellis-Jaffe reference value from tabulated helicity densities (`sum_rules.py`) | asymmetries and depolarization factors (formulas), g_2 twist-3, scheme conversion of Delta Sigma, higher orders |
| C | Drell-Yan (cross sections, x_F, rapidity frames, angular coefficients) | [Drell-Yan](drell-yan.md) (Th15) | LO d2sigma/dM dy and dM dx_F (photon exchange), conversions between (M, y), (M, x_F), (x_1, x_2), (tau, y), CS <-> HX rotation with invariants, Lam-Tung combination (`drell_yan_lo.py`) | NLO, threshold resummation, Z exchange (refused by the script) |
| D | Nuclear effects and nuclear PDFs | [nuclear targets](nuclear-parton-effects.md) (Th16) | bound-nucleon (isospin) combination, per-nucleon <-> per-nucleus conversions, member-by-member nuclear ratios with the set's rule (`nuclear_combination.py`) | mechanism models (shadowing, EMC effect, energy loss), deuteron corrections, Coulomb corrections |
| E | SIDIS, fragmentation functions, TMDs, Drell-Yan q_T resummation | [SIDIS and TMDs](sidis-and-tmd.md), [fragmentation functions](fragmentation-functions.md) (Th18) | SIDIS invariants, Trento angles, leading-power q_T and region classification (`sidis_kinematics.py`); Gaussian-ansatz SIDIS and Drell-Yan shapes and the Sivers sign change (`tmd_gaussian.py`); FF momentum sum rule (`sum_rules.py`) | TMD evolution, matching, nonperturbative prescriptions, CSS resummation |
| F | Small-x physics and saturation (dipole picture) | [small x](small-x-and-saturation.md) (Th19) | LO photon wave functions and the GBW dipole model: sigma_T, sigma_L, F_2, F_L with a convergence report (`dipole_lo.py`) | BK/JIMWLK and BFKL evolution, small-x resummed DGLAP, other dipole models |
| G | Global PDF / nPDF / FF fits (theory inputs; statistics in hep-statistics) | [global-fit inputs](global-fits-theory-inputs.md); statistics: `skills/hep-statistics/references/pdf-fit-statistics.md` (S12, S13) | Bayesian reweighting of replicas and linear Hessian profiling (hep-statistics `pdf_reweighting.py`, `hessian_profiling.py`); t0 chi2 (`covariance_fit.py`) | executing a complete global fit (needs external codes) |
| H | Exclusive processes, GPDs, diffractive DIS | [exclusive and GPDs](exclusive-and-gpd.md) (Th20) | t_min, xi, the BMK and Trento azimuths, x_P and beta (`exclusive_kinematics.py`); GPD form-factor and Ji sum-rule integrals (`sum_rules.py`) | GPD extraction, Bethe-Heitler and DVCS amplitudes, Compton form factors |

Theory-domain profiles (in `<plugin root>/profiles/registry.json`): the DIS parton model (LO F_2 and O(alpha_s) F_L,
synthetic only), LO Drell-Yan (O(alpha_s) angular coefficients and Lam-Tung, with a published benchmark) and
Gaussian-ansatz TMDs (SIDIS, Cahn and Sivers terms, Drell-Yan q_T).

Kinematic invariants of DIS: [DIS kinematics](dis-kinematics.md). PDF sets, members and their uncertainty:
[PDFs](pdfs-and-lhapdf.md). Orders, scales and envelopes: [higher orders](higher-order-predictions.md).

## Shared required fields

Every hadron-structure prediction carries the core conventions plus those of its module, from the core vocabulary
(contracts 3.10.0): `target_normalization`, `exchanged_bosons`, `electroweak_scheme`, `em_coupling`,
`structure_function_signs`, `heavy_quark_scheme`, `factorization_scheme`, `target_mass_treatment`,
`polarization_convention`, `xF_definition`, `rapidity_frame`, `azimuth_convention`, `log_accuracy`. Each module page
names the ones it requires. A missing required field is a refusal, not a default. Model choices are not conventions:
widths, dipole-model parameters, nonperturbative prescriptions and the names of PDF, nPDF, FF or GPD sets go in
`parameters` and `assumptions`.

## Rules shared by the modules

- Inputs, not internals: the scripts take parton, FF and GPD values, widths and model parameters as inputs and embed
  no PDF set, coupling value or fit parameter.
- The validity domain (lower bounds on Q^2 and W^2, x ranges, q_T/Q, small-x limits) is the user's, written in the
  theory-spec; scripts classify against the bounds they are given and ship no default threshold.
- Scale envelopes, PDF-set uncertainties, alternative models and truncation estimates are separate uncertainty
  objects; none is turned into a Gaussian or added in quadrature without a named prescription.
- Facility settings (beam energies, targets, polarization) come from an experiment profile or the user, labelled
  `user-supplied`; never from memory.
- Comparison with data goes through `contracts/comparison/gate.py` first; chi2 and fits are hep-statistics.

## Boundaries

| Question | Owner |
|---|---|
| Reconstructing x, Q^2, y (electron, hadron, double-angle methods), hadron P_hT, recoil detection | hep-detector |
| Binning, selections, backgrounds, whether data are radiatively corrected | hep-measurement |
| chi2 of a prediction against data, PDF reweighting and profiling, fits | hep-statistics |
| Literature, equation locations, set versions | hep-citations |
| External codes (evolution, fast grids, fitting codes) and numerical convergence | hep-computing |

Outside v1, with the limited-support notice: lattice computations of PDFs and moments (`lattice-qcd`), the
quark-gluon plasma in nucleus-nucleus collisions (`heavy-ions`), model calculations of PDFs, TMDs or GPDs (quark
models, chiral soliton, AdS/QCD: `hadron-models`), quarkonium production and absorption (`quarkonium-production`), and
jets and resolved photons in lepton-hadron scattering (`jets-in-dis`). Their results may still be cited inputs with
source and status.
