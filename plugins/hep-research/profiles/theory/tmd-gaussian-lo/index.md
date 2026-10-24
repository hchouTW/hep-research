# Gaussian TMD profile: routing map

Profile `theory:tmd-gaussian-lo` covers Gaussian-ansatz TMDs at leading order, without evolution. Its topics are
SIDIS F_UU,T, the Cahn cos(phi_h) term, the Sivers asymmetry, the Drell-Yan q_T shape, and the change of sign of the
Sivers function between SIDIS and Drell-Yan. It needs no experiment profile. Paths are relative to this folder.

| Request | Read |
|---|---|
| Model, conventions of the two papers, validity domain, what each output can claim | `models/tmd-gaussian-lo.md` |
| Derivations, status per step, checks, versions | `derivations/derivation-record.md` (run `scripts/derive.py`, about 50 s) |
| F_UU,T, Cahn ratio, Sivers asymmetry, Sivers function in SIDIS and Drell-Yan, q_T shape | `scripts/predict.py --help`; stored outputs `predictions/*.prediction.json` |
| Theory spec (contract artifact) | `derivations/theory-spec.json` (written by `scripts/make_artifacts.py`) |
| Published closed-form benchmark (Anselmino et al. Eqs. 38-39, 64-67) | `benchmarks/anselmino-closed-forms.json` |
| Inputs (synthetic collinear values; the paper's fitted widths as illustrative settings) | `benchmarks/toy-inputs.json` |
| References read and what they state | `evidence/sources.json`, `evidence/claims.json` |

Conventions are in `conventions.json`. Two points need care:
- The fragmentation width differs between the two papers. Anselmino's <p_perp^2> is the hadron relative to the quark;
  Bacchetta's D_1(z, k_T^2) uses the quark relative to the hadron and carries a z^2 normalization, so
  <p_perp^2> = z^2 <k_T^2>.
- The Sivers sign is SIDIS f_1T^perp = -(Drell-Yan f_1T^perp).
- Anselmino et al. and the Trento conventions use the same phi_h and phi_S. The incoming lepton has l_x > 0 and the
  photon points along +z (see derivation step 5).
- Key differences from `theory:drell-yan-lo`, all intentional:
  - This profile adds `target_normalization`, `polarization_convention` and `target_mass_treatment`, because SIDIS
    has a (polarized) nucleon target.
  - It uses `tmdg:*` keys for the Gaussian ansatz and the fragmentation normalization.
  - It has no `dylo:angular_distribution` or `dylo:channel_mixture`, because no lepton angular coefficients are
    modelled.
  - `em_coupling` means the same in both: alpha enters only prefactors.

Keep these limits in view:
- The physics status is `heuristic-argument`, because the Gaussian ansatz is a model.
- The Sivers sign change is cited, not derived.
- No Drell-Yan Sivers asymmetry formula is provided, only the sign of the Sivers function.

Out of scope (say so): TMD evolution, b-space fits, Collins and Boer-Mulders effects, and any extraction from data.
