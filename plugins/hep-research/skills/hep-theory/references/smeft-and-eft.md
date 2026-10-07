# SMEFT and other effective field theories: conventions and limits

What the plugin can check for an EFT prediction, the conventions that must travel with it, and what stays outside
v1. Global EFT fits are not supported: a request for one gets the "no validated domain profile" notice. The
truncation bookkeeping is executable in `<plugin root>/skills/hep-theory/scripts/eft_truncation.py`.

## Conventions every EFT prediction states

- **Basis** (for SMEFT, for example the Warsaw basis) and any field redefinitions or equations of motion used.
- **Operator normalization:** the coefficient multiplies O_i / Lambda^2 (C_i dimensionless) or O_i / v^2 or comes
  with an extra coupling factor; translating between them rescales the coefficient by (v/Lambda)^2 or by a coupling.
- **Input scheme** for the electroweak parameters ({alpha, m_Z, G_F} or {m_W, m_Z, G_F}): the same coefficient
  shifts different observables in different schemes.
- **Flavour assumption** (for example U(3)^5 universality, top-specific, or general).
- **Scale** at which the coefficients are defined and whether renormalization-group running between that scale and
  the process scale was included.
- **Truncation:** linear in 1/Lambda^2 (interference with the SM only), or linear plus the squared dimension-6
  amplitudes at 1/Lambda^4. The second is not "more accurate": dimension-8 interference enters at the same order.
- **Order** of the SM and EFT parts (QCD order of each term) and the generator or calculation that produced them.

## What the plugin can check

- That the convention block above is complete before a prediction is compared or combined (`eft_truncation.py`
  refuses missing basis, normalization or input scheme, and undeclared operators).
- That only C/Lambda^2 enters a linear prediction (rescaling C and Lambda together leaves it unchanged).
- The size of the quadratic part relative to the linear part at the points used, with a flag when it exceeds a
  stated fraction: there the truncation, not the data, drives the conclusion.
- Unit and convention consistency when two EFT predictions are compared (the comparison gate in `contracts/`).

## What it cannot validate (outside v1)

Global fits and their likelihoods; RG evolution of Wilson coefficients (no anomalous-dimension implementation ships);
positivity or unitarity bounds; matching to a specific UV model; translations between bases. A result that needs one
of these names the tool used and its status, and the plugin does not upgrade that status.

## Reporting

Report linear and linear+quadratic predictions as two truncations, not as an uncertainty band. A limit on C_i
depends on Lambda only through C_i/Lambda^2; quote both or the ratio. Coefficients fitted one at a time and in a
joint fit are different results; say which.
