# Model: Gamma(H -> b bbar) with the MS-bar running mass

Gamma(H -> b bbar) = 3 G_F M_H / (4 sqrt 2 pi) mbar_b(mu)^2 R(a(mu), L), a = alpha_s / pi, L = ln(mu^2 / M_H^2)
[hbb:C01]. At mu = M_H, R = 1 + s_1 a + s_2 a^2 + s_3 a^3 + s_4 a^4 with s_1..s_3 exact [hbb:C02] and s_4 = -825.7 at
n_f = 5 [hbb:C03]. Numerically s_1 = 5.6667, s_2 = 29.147, s_3 = 41.758 at n_f = 5 (derive.py, matching
hep-ph/0511063 eq. (3)).

## Why the running mass

With the pole (on-shell) mass the O(alpha_s) term carries log(m_b^2 / M_H^2) (Djouadi, hep-ph/0503172, eq. (2.9), read
2026-10-13), large at M_H / m_b of about 30. Evaluating mbar_b and alpha_s at mu of order M_H (eqs. (2.10)-(2.11)
there) absorbs these logarithms into mbar_b(M_H), which is about 2.79 GeV here instead of 4.186 GeV at mbar_b. The
mass and the coupling run with the four-loop gamma_m and beta [hbb:C04, C05]; the scheme background is in
`skills/hep-theory/references/regularization-and-schemes.md`.

## Assumptions

- n_f = 5 active massless quarks at leading power; the top quark is decoupled; no threshold matching. Above
  mu = m_t (part of the envelope range up to 2 M_H) this is an approximation that is not estimated here.
- alpha_s(m_Z) = 0.1180 +- 0.0009 and m_Z = 91.1879 GeV [hbb:C06]; mbar_b(mbar_b) = 4.186 +- 0.006 GeV (printed at CL
  90%) [hbb:C08]; M_H = 125.13 GeV [hbb:C07]; G_F = 1.1663785e-5 GeV^-2 [hbb:C06].
- alpha_s is run from m_Z down to mbar_b and (alpha_s, mbar_b) together from mbar_b to mu, at four loops for every
  order N of R (the running is not truncated with N).
- No top-induced (singlet) terms (Djouadi eq. (2.12) gives one at a^2), no electroweak and no QED corrections, no
  m_b^2 / M_H^2 power corrections.

## Validity domain

mu in [M_H/2, 2 M_H] with n_f = 5; the code refuses a configuration with n_f != 5 or a lowest scale below 2 mbar_b.
The prediction is conditional on the exclusions; it is not a statement about the measured width or branching ratio.

## Benchmark result (predictions/hbb_125.json)

Gamma in MeV at mu = M_H: 1.922 (a^0), 2.313 (a^1), 2.385 (a^2), 2.388 (a^3), 2.386 (a^4). The scale envelope
narrows from [1.727, 2.167] at a^0 to [2.384, 2.386] at a^4; the last-term truncation estimate is 0.0026 MeV at a^4;
the alpha_s(m_Z) variation moves the a^4 width by about -0.021 / +0.021 MeV and the mbar_b variation by about
+-0.008 MeV.

## What each uncertainty object can and cannot claim

| Object | Prescription | Can claim | Cannot claim |
|---|---|---|---|
| Scale envelope | `scan-min-max` over mu in [M_H/2, 2 M_H] (mass and coupling at the same mu) | how strongly the truncated series depends on an unphysical scale | coverage of the true value; a Gaussian width |
| Truncation estimate | `last-term` at mu = M_H | the local convergence pattern | a bound on the remainder (asymptotic series) |
| Parametric alpha_s, m_b | re-evaluation at the PDG +- values, one at a time | sensitivity to each input | correlations between inputs (none modelled); a 68% interval for m_b (input printed at 90% CL) |

They are reported side by side and never added in quadrature without a stated prescription.

## Excluded

Power corrections, top-induced and electroweak terms, threshold matching, the M_H uncertainty, any experiment field,
and any claim of formal proof or of envelope coverage.
