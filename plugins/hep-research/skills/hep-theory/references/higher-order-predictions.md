# Higher-order predictions: scales, envelopes and truncation

How to report a fixed-order prediction beyond leading order so that each uncertainty object says only what it can.
`[General method]` unless a profile says otherwise. A shipped theory-domain profile (`<plugin root>/profiles/registry.json`)
carries a checkable worked example:

<!-- example: worked example -->
- The R-ratio profile (R in e+e- annihilation through alpha_s^4): its `scripts/derive.py` derives the scale
  dependence from the renormalization group equation and its `scripts/predict.py` reports the three objects below
  side by side.
<!-- /example -->

## The order and what it means

- State the order of the **observable**, not of the matrix element: "NLO QCD" for a cross section means
  O(alpha_s) relative to the leading order, and for a ratio or a normalized distribution the orders of numerator and
  denominator may differ.
- State the scheme (MS-bar, on-shell), the number of active flavours, the coupling at its reference scale and how it
  was run (loop order of the beta function, thresholds crossed and the matching used, or that none is crossed).
- A K-factor is a ratio of two predictions at stated scales and PDFs; applying an inclusive K-factor to a
  differential distribution is an assumption to be stated.

## Scale variation prescriptions

- **Single scale** (for example mu_R in R or in a decay width): vary mu in [mu_0/2, 2 mu_0]. Report the minimum and
  maximum over the range (or the three points mu_0/2, mu_0, 2 mu_0), and say which.
- **Two scales** (mu_R and mu_F in hadron collisions): the 7-point envelope varies both by factors of 2 and drops the
  two opposite-direction combinations (1/2, 2) and (2, 1/2); the 9-point envelope keeps them. They are different
  prescriptions and are not interchangeable; name the one used.
- The central scale is a choice (Q, a transverse mass, H_T/2); a dynamic scale changes both the central value and the
  envelope, so record it with the prediction.
- Correlations: an envelope taken bin by bin has no defined correlation between bins. If a downstream fit needs one,
  the analysis states a prescription (for example fully correlated within one scale choice) and labels it as such.

## Reporting an envelope

An envelope is a prescription, not a confidence interval. Report it as `[min, max]` with the prescription, never as
a Gaussian standard deviation, and never add it in quadrature to a PDF or parametric uncertainty without a stated
rule (the plugin's invariant). If a statistics tool needs a nuisance parameter, the mapping (for example a flat or
a two-point nuisance) is a hep-statistics decision recorded with the fit, not part of the prediction.

## Truncation uncertainty

- **Last-term estimate:** the size of the last included term. Cheap, but it is zero when a coefficient happens to
  vanish and it says nothing about coefficient growth.
- **Scale envelope as a proxy:** conventional, but at low orders it can underestimate the next correction. In the R
  example each envelope contains the next order's central value at the Q values scanned (10-30 GeV); that is one
  observable, not a rule.
- **Series-based models** (assume a distribution for the unknown coefficients from the known ones) give a
  degree-of-belief interval whose meaning depends on the assumed prior; report the model with the number.
- Perturbative series in QCD are asymptotic. Agreement between successive orders is evidence about the truncation,
  not convergence.

## What each object cannot claim

| Object | Cannot claim |
|---|---|
| Scale envelope | coverage of the true value; independence of the central-scale choice |
| Truncation estimate | a bound on the remainder |
| PDF uncertainty | anything about scales or missing orders; its CL is that of the PDF set |
| Parametric (alpha_s, masses) | correlation with other inputs unless modelled |

## Deliverables

Order of the observable, scheme, coupling input and running, central scale, scale prescription and its result,
truncation estimate and its method, parametric and PDF uncertainties as separate objects, and the derivation status
of each formula used.
