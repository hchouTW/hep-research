# Model: massless QCD corrections to R in e+e- annihilation

R(Q) = sigma(e+e- -> hadrons) / sigma(e+e- -> mu+mu-) = R_EW (1 + delta_QCD(Q)), with R_EW = N_c sum_q e_q^2 for
photon exchange [qcdr:C01] and delta_QCD = sum_n c_n (alpha_s/pi)^n through n = 4 at mu = Q, MS-bar [qcdr:C02].

## Assumptions

- Photon exchange only; Z exchange and gamma-Z interference are neglected.
- n_f = 5 active quarks (u, d, s, c, b), all massless; the top quark is decoupled.
- alpha_s(m_Z) = 0.1180 +- 0.0009 [qcdr:C04], run to mu with the three-loop beta function [qcdr:C03] at fixed
  n_f = 5. No flavour threshold is crossed, so no matching is needed.
- No QED corrections to the hadronic or the muonic cross section.

## Validity domain

Q well above the b-quark pair threshold and well below m_Z: the code refuses scales below 5 GeV and Q above m_Z/3.
Near 2 m_b, quark masses and resonances dominate; near m_Z, Z exchange does. Inside the domain the neglected effects
are not estimated here, so the prediction is not a statement about measured R.

## What each uncertainty object can and cannot claim

| Object | Prescription | Can claim | Cannot claim |
|---|---|---|---|
| Scale envelope | min and max over mu in [Q/2, 2Q] | how strongly the truncated series depends on an unphysical scale | coverage of the true value; a Gaussian width; anything about missing higher orders beyond this choice of range |
| Truncation estimate | size of the last included term at mu = Q | the series' local convergence pattern | a bound on the remainder (asymptotic series, coefficient growth) |
| Parametric alpha_s | re-evaluation at alpha_s(m_Z) +- 0.0009 | sensitivity to the input coupling | correlation with other inputs (none modelled) |

They are reported side by side and never added in quadrature without a stated prescription.

## Excluded

Quark-mass corrections, Z exchange, QED corrections, the n_f = 4 to 5 matching, resummation, non-perturbative
(power) corrections and any comparison with measured R.
