# Model: Gaussian-ansatz TMDs at leading order, no evolution

**Physics status: `heuristic-argument`.** The Gaussian ansatz with constant, flavour-independent widths is a model.
Each derivation step is exact within that model (`analytic-derivation` per step in `derivations/derivation.json`),
but the model itself is not derived from QCD, and there is no TMD evolution.

## Ingredients

- f_q(x, k) = f_q(x) exp(-k^2/<k_perp^2>)/(pi <k_perp^2>) and D_q(z, p) = D_q(z) exp(-p^2/<p_perp^2>)/(pi <p_perp^2>).
  Here p is the hadron transverse momentum relative to the fragmenting quark [tmdg:C02].
- P_hT = z k + p, x = x_B and z = z_h at O(k/Q) [tmdg:C01].
- Bacchetta et al. instead write D_1(z, k_T^2), with k_T the quark relative to the hadron and
  D_1(z) = z^2 int d^2k_T D_1(z, k_T^2) [tmdg:C06]. The hadron relative to the quark is -z k_T, so
  <p_perp^2> = z^2 <k_T^2>, and both conventions give the same F_UU,T.
- Sivers function (SIDIS convention): Delta^N f = 2 N_q(x) h'(k) f(x, k), with h' = sqrt(2e) (k/M') exp(-k^2/M'^2)
  [tmdg:C04]. Trento relation: Delta^N f = -(2|k_T|/M) f_1T^perp. Drell-Yan: f_1T^perp,DY = -f_1T^perp,SIDIS, cited
  from time reversal, not derived [tmdg:C08].

## Results

| Quantity | Closed form | Source |
|---|---|---|
| F_UU,T(x, z, P_hT) | x sum e_q^2 f_q D_q exp(-P_hT^2/<P_T^2>)/(pi <P_T^2>), <P_T^2> = <p_perp^2> + z^2 <k_perp^2> | Anselmino et al. Eqs. 38-39; Bacchetta et al. Eq. 4.2, re-derived |
| int d^2P_hT F_UU,T | x sum e_q^2 f_q D_q | Bacchetta et al. Eq. 4.21 |
| Cahn term | -4 (2-y) sqrt(1-y) <k_perp^2> z P_hT cos(phi_h)/(<P_T^2> Q), relative to 1 + (1-y)^2 | Anselmino et al. Eq. 38; Bacchetta Eq. 4.20 |
| A_UT^sin(phi_h - phi_S) | Delta sigma_Siv/sigma_0 with <k^2>hat = M'^2 <k_perp^2>/(M'^2 + <k_perp^2>), <P_T^2>hat = <p_perp^2> + z^2 <k^2>hat | Anselmino et al. Eqs. 64-67; Bacchetta Eq. 4.11 + Trento Eq. 4 |
| Drell-Yan q_T shape | exp(-q_T^2/<q_T^2>)/(pi <q_T^2>), <q_T^2> = <k1^2> + <k2^2> | derived here |
| Sivers in Drell-Yan | -(Sivers in SIDIS) | Trento Eq. 14 (cited) |

## Inputs

The collinear values f_q(x), D_q(z), the Sivers normalizations N_q and the Drell-Yan widths are SYNTHETIC. The SIDIS
widths <k_perp^2> = 0.25 GeV^2 and <p_perp^2> = 0.20 GeV^2 (Anselmino et al. Eq. 47) and M'^2 = 0.36 GeV^2 (their
Table I) are fitted values of that paper. They serve only as ILLUSTRATIVE settings, not as current determinations.

## Validity domain

The model applies at small P_hT, of order k_perp and well below Q. Corrections of O(k_perp^2/Q^2) are dropped and the
Cahn term is kept at O(k_perp/Q). The widths are constant in x, z, Q^2 and flavour. There is no matching to the
collinear large-P_hT region. The Sivers sign change holds for TMDs with the SIDIS and Drell-Yan Wilson lines.

## What the outputs can and cannot claim

| Output | Can claim | Cannot claim |
|---|---|---|
| F_UU,T, Cahn ratio | exact within the Gaussian model; matches the published closed form | physical P_hT spectra; any evolution |
| Sivers asymmetry | the published Gaussian-model closed form, re-derived in two conventions | a fit or an extraction of the Sivers function |
| Drell-Yan q_T shape | the convolution result | soft-factor or evolution effects |
| Sivers sign change | the sign of the Drell-Yan Sivers function given the SIDIS one | a Drell-Yan asymmetry formula (none read) |

## Excluded

TMD evolution, b-space, Collins and Boer-Mulders effects, flavour-dependent widths, fits, and data comparisons.
