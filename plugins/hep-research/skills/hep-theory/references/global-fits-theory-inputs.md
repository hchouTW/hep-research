# Global PDF, nPDF and FF fits: the theory inputs

Purpose: what hep-theory supplies to a global fit of parton distributions (proton PDFs, nuclear PDFs, fragmentation
functions): the parametrization and flavour assumptions, the constraints, the theory settings, the kinematic cuts and
the theory uncertainty. The statistics (chi2 forms, tolerances, Hessian and replica uncertainties, reweighting,
profiling) are hep-statistics' (`skills/hep-statistics/references/pdf-fit-statistics.md`). Executing a complete fit
is not provided (it needs evolution codes and fast interpolation grids; a separate software plan): this page is for
writing a fit specification and reviewing an existing fit. Entry page: [hadron structure](hadron-structure-essentials.md).

Status: guidance (Th14-Th20 inputs to S13), sources read in full text on 2026-10-23 (see "Sources read").

## Division of work

| Item | hep-theory (this page) | hep-statistics |
|---|---|---|
| Parametrization | functional form or neural network, flavour assumptions, initial scale | number of parameters, over-fitting diagnostics |
| Constraints | momentum and valence sum rules, positivity choice, integrability | how they enter the minimization |
| Theory settings | order, scheme, alpha_s, heavy-quark scheme, nuclear and deuteron corrections | - |
| Data selection | kinematic cuts with reasons | consistency and tension diagnostics |
| Theory uncertainty | scale variations and their prescription | how a theory covariance enters chi2 |
| Updating a published set | the predictions and the members they depend on | reweighting, profiling, impact studies |

## Parametrization and flavour assumptions

Most groups use input forms x f = x^a (...) (1 - x)^b with 14-32 free parameters in total and start evolution at
Q_0^2 = 1-4 GeV^2; the NNPDF approach uses neural networks with a Monte Carlo representation (PDG 2026 Structure
Functions, Sec. 18.3). The form is a choice that biases the result where data are sparse: the uncertainty in
extrapolation regions (small x, large x) reflects the parametrization only. Flavour assumptions (s = sbar or not,
ubar versus dbar, the strange fraction, an intrinsic charm or not) are listed in `assumptions`. For nuclear PDFs the A
dependence of the parameters (for example nCTEQ's c_k(A) = p_k + a_k (1 - A^-b_k)) and the proton baseline are part of
the specification ([nuclear targets](nuclear-parton-effects.md)); for FFs the parametrization of their Eq. 19.12 and
the favoured/unfavoured assumptions ([fragmentation functions](fragmentation-functions.md)).

## Constraints

- Momentum and valence-number sum rules (`sum_rules.py`), the FF momentum sum rule over hadrons; whether they are
  imposed exactly or as penalties is stated.
- Positivity: of observables (cross sections) or of the MS-bar PDFs themselves; these are different choices (state
  which). Integrability at small x.

## Theory settings

Order of the coefficient functions and of the evolution, factorization and renormalization schemes (MS-bar almost
universally; PDG Sec. 18.2.2), alpha_s(M_Z) (fitted or fixed, with its value and source), the heavy-quark scheme (FFNS
or a named GM-VFNS variant; the choice changes alpha_s and the large-x gluon, PDG Sec. 18.3;
[DIS structure functions](dis-structure-functions.md)), target-mass and higher-twist treatment, nuclear and deuteron
corrections. These settings are one consistent set for every prediction in the fit.

## Data selection

Kinematic cuts in W^2 and Q^2 remove the region where higher twist and target-mass effects are not modelled (PDG
Sec. 18.2.2 mentions W^2 > 15 GeV^2 as a cut above which higher twist appears numerically unimportant for Q^2 above a
few GeV^2, except at very small x and near x = 1); state each cut and its reason. Isoscalar-corrected nuclear data
need predictions at Z = A/2 or beta applied ([nuclear targets](nuclear-parton-effects.md)).

## Theory uncertainty

Missing higher orders are estimated by scale variations ([higher orders](higher-order-predictions.md)); a theory
covariance built from them is a named prescription, and how it enters chi2 is hep-statistics'. No specific
prescription is given here: none was read for this page.

## Review checklist (theory side)

One order, scheme, alpha_s and heavy-quark scheme throughout; flavour assumptions listed; positivity choice stated;
cuts justified; nuclear and deuteron corrections declared; extrapolation regions flagged; the fit's own documentation
followed for its members.

## Sources read (full text, 2026-10-23)

- PDG 2026 "Structure Functions" ([DIS structure functions](dis-structure-functions.md)): Secs. 18.2.2, 18.3.
- The nPDF and FF sources of [nuclear targets](nuclear-parton-effects.md) and
  [fragmentation functions](fragmentation-functions.md).

Not verified and therefore not used: theory-covariance (MHOU) prescriptions; positivity-constraint implementations of
particular groups; intrinsic-charm parametrizations.
