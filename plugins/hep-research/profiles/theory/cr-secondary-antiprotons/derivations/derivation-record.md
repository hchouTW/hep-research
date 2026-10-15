# Derivation record: the secondary antiproton source term with a toy cross section (theory:cr-secondary-antiprotons)

**Status: `analytic-derivation`** for the toy cross section below. SymPy checks the algebra (`scripts/derive.py`,
output `derivations/derivation.json`); the closed form is checked against the profile's own numerical quadrature
(`scripts/predict.py --benchmark`). Not a formal proof; no external program was run.

**Machine-readable header:** `derivations/theory-spec.json` (artifact type `theory-spec`, `model.family`
`cosmic-ray-secondary-source-term`), written by `scripts/make_artifacts.py`.

**References.** None was opened in this session (no network was approved for this work package). The source-term
definition, the threshold, the ISM composition, the channels and the antineutron/hyperon factor are taken from
`skills/hep-theory/references/cosmic-ray-propagation.md`, whose author read Korsmeier, Donato and Di Mauro (PRD 97
(2018) 103019, arXiv:1802.03030v2), di Mauro, Donato, Goudelis and Serpico (PRD 90 (2014) 085017, arXiv:1408.0288v3)
and Winkler (JCAP 02 (2017) 048, arXiv:1701.04866v1) on 2026-10-13 (claims `crpb:C01`-`C05`). The toy cross section
and every number in the shipped sets are this profile's own placeholders, not taken from those papers.

## Model and notation

Projectile i with flux phi_i(T_i) per kinetic energy per nucleon, target density n_j, antiproton kinetic energy T.
Toy prompt cross section: dsigma_pp/dT = (sigma0 / T_i) (1 - T/T_i)^n for T_i >= T_th and T < T_i; channel ij is
f_ij times this. T_th = (k_th - 1) m_p with k_th = 7.

## Result

For one power-law segment phi = C T_i^-gamma on [a, b) (b may be infinite), substitute x = T / T_i
(T_i = T/x, dT_i = -T/x^2 dx):

    int_{max(a, T_th, T)}^{b} C T_i^-gamma (sigma0 / T_i) (1 - T/T_i)^n dT_i
      = C sigma0 T^-gamma int_{T/b}^{x_hi} x^(gamma-1) (1 - x)^n dx,    x_hi = T / max(a, T_th, T),

an incomplete beta function difference B(x_hi; gamma, n+1) - B(T/b; gamma, n+1). For a pure power law above
threshold (T >= T_th) it is C sigma0 T^-gamma B(gamma, n + 1) = C sigma0 T^-gamma Gamma(gamma) Gamma(n+1) /
Gamma(gamma + n + 1): q_ij scales as T^-gamma there. Below threshold x_hi = T / T_th < 1. A sharp broken power law
is the sum of its segments. Then q_ij = 4 pi n_j f_ij x (the integral), and the total is
q = (sum_ij q_ij) [(1 + Delta_Lambda) + (1 + Delta_IS + Delta_Lambda)] = (sum_ij q_ij)(2 + Delta_IS + 2 Delta_Lambda).

## Checks run

| Check | How | Result |
|---|---|---|
| Substitution maps the integrand exactly | SymPy | pass |
| Beta function above threshold, symbolic gamma, n = 0, 1, 2, 3, 7 | SymPy | pass |
| Incomplete beta below threshold (n = 2), direct integral above threshold (n = 2) | SymPy | pass |
| Pieces of a broken power law add (n = 2) | SymPy | pass |
| Antineutron/hyperon bookkeeping equals 2 + Delta_IS + 2 Delta_Lambda | SymPy | pass |
| Numerical quadrature vs closed form: 4 channels x 9 energies x 2 flux shapes | `predict.py --benchmark` | max rel. dev. ~3e-15 (criterion 1e-8) |
| Hand-computed point (n = 0: B(gamma, 1) = 1/gamma) | `predict.py --benchmark` | pass (1e-10) |
| Discrimination: a wrong upper limit or a wrong Gamma-function ratio fails | `tests/test_derivation.py` | pass |

## Checks not run

- Published source-term values (open question B2: which table or figure, and whether digitizing a figure is
  acceptable). No published number is used anywhere in this profile.
- Any published cross-section parametrization (di Mauro et al., Winkler, Korsmeier et al.): none is reproduced.
- Propagation and comparison with measured antiproton fluxes (outside this profile).

## Not a propagation model

`model.family` is `cosmic-ray-secondary-source-term`. The contracts rule `theory.degeneracy_missing` applies to
`cosmic-ray-propagation` only, so this theory-spec has no `degenerate_directions`; `tests/test_artifacts.py` checks
that it validates, and that the same spec relabelled as a propagation family fails.
