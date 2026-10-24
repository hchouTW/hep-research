# Model: LO Drell-Yan cross section and O(alpha_s) lepton angular coefficients

## Cross section (LO, photon exchange)

d^2 sigma / dM dy = (8 pi alpha^2 / (9 M s)) sum_q e_q^2 [q1(x1) qbar2(x2) + qbar1(x1) q2(x2)], with
x1,2 = (M/sqrt(s)) e^(+-y) and q1 denoting a quark in hadron 1. The formula is derived from
sigma(e+e- -> f fbar) = N_c Q_f^2 4 pi alpha^2/(3 s) [dylo:C01], a colour average, and the parton-model factorization
[dylo:C02] (`derivations/derivation-record.md`). Because PDG Eq. 51.3 gives 4 pi alpha^2/3 = 86.8 nb GeV^2, results
are kept in units of 4 pi alpha^2/3 and need no value of alpha.

## Angular coefficients (O(alpha_s))

d sigma/d Omega propto 1 + lambda cos^2 theta + mu sin 2theta cos phi + (nu/2) sin^2 theta cos 2phi, with the angles
taken in the Collins-Soper frame [dylo:C03]. Around the quark axis (theta1, phi1) the distribution is
1 + a cos theta0 + cos^2 theta0, which gives A_0..A_7 and lambda = (2 - 3 A0)/(2 + A0), nu = 2 A2/(2 + A0)
[dylo:C04]. At O(alpha_s):

| Channel | <sin^2 theta1> | lambda | nu | Status of the input |
|---|---|---|---|---|
| q qbar -> gamma* g | r^2/(1 + r^2) | (2 - r^2)/(2 + 3 r^2) | 2 r^2/(2 + 3 r^2) | exact at O(alpha_s) [dylo:C05] |
| q g -> gamma* q | 5 r^2/(1 + 5 r^2) | (2 - 5 r^2)/(2 + 15 r^2) | 10 r^2/(2 + 15 r^2) | approximation; the exact value depends on the PDFs [dylo:C05] |

Here r = qT/Q. With phi1 = 0, the coplanar case that Peng et al. state holds at O(alpha_s) [dylo:C06], A0 = A2 and
1 - lambda - 2 nu = 0 (Lam-Tung) in each channel and in any mixture.

## Assumptions

- Photon exchange only (a = 0); massless quarks and leptons; unpolarized hadrons; N_c = 3.
- One emitted parton, no intrinsic transverse momentum, no resummation.
- Channel mixture: f is the q g share of the angle-integrated cross section in the same (qT, Q) bin. That equals an
  event fraction only with full angular acceptance. The mixture is exact, with no choice of rule: every A_i term of
  Eq. 3 integrates to zero over the sphere and 1 + cos^2 theta to 16 pi/3, so A_i^mix = sum_c f_c A_i^c (derived in
  SymPy). Equivalently, lambda_mix = sum f_c lambda_c/(3 + lambda_c) / sum f_c/(3 + lambda_c), and nu likewise.
  Averaging lambda or nu linearly is wrong.

## Validity domain

The cross section holds at LO with photon exchange, i.e. for M well below the Z pole and away from resonances. The
angular coefficients hold at O(alpha_s). At small qT, intrinsic transverse momentum and soft-gluon resummation
matter (not included). Beyond O(alpha_s), non-coplanar emissions make 1 - lambda - 2 nu > 0. Only that sign is
derived here, and only within the quark-axis representation (Peng Eqs. 2-6: A0 - A2 = 2 sin^2 theta1 sin^2 phi1 >= 0),
not its size.

## What the outputs can and cannot claim

| Output | Can claim | Cannot claim |
|---|---|---|
| d2sigma/dM dy formula | exact LO algebra from the cited inputs; Jacobian checked numerically | NLO size; any number for a real collision (toy PDFs only) |
| lambda, nu per channel | agreement with the published closed form (Peng Eq. 10) | independent physics validation of Eq. 9 (same route as the paper) |
| Mixtures | the curve for a stated q g fraction | the fraction in any real process; a fit to data |
| Lam-Tung | exact at O(alpha_s) given the cited coplanarity | its validity beyond O(alpha_s) |

## Excluded

Z exchange, NLO cross sections, qT resummation, TMD effects, Lam-Tung violation beyond O(alpha_s), and comparisons
with measurements.
