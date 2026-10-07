# Parton distributions and LHAPDF

Choosing a PDF set, handling its members, and combining PDF uncertainties by the set's own rule. The combination
formulas are executable in `<plugin root>/skills/hep-theory/scripts/pdf_uncertainty.py` (tested on constructed
inputs). LHAPDF is not installed in the environments these checks ran in: API names below are given as a guide and
are `unverified` until run.

## Choosing a set

- Match the perturbative order of the PDF fit to the order of the calculation (an NLO matrix element with an NLO or
  NNLO set; state which and why).
- The set is fitted with a value of alpha_s(m_Z); use that value in the matrix element, or a set fitted at the value
  you use. Mixing a set fitted at 0.118 with a calculation at 0.120 is an inconsistency to report.
- Record the set name, version, the member used as central, and the number of members.
- A set built for a special purpose (fixed flavour number, photon content, nuclear PDFs, a small-x resummed fit) is
  appropriate only where that purpose applies.

## Members and error types

Member 0 is the central member. The error type is part of the set's metadata (`ErrorType` in the `.info` file):

| Error type | Members | Combination |
|---|---|---|
| `symmhessian` | 0, then N symmetric eigenvector members | delta = sqrt(sum_k (X_k - X_0)^2) |
| `hessian` | 0, then N/2 pairs (+, -) along each eigenvector | delta+ = sqrt(sum max(X_+ - X_0, X_- - X_0, 0)^2), delta- with min; asymmetric |
| `replicas` | 0 (average), then N Monte Carlo replicas | standard deviation over replicas, or the central 68% of replicas |

- Applying the Hessian formula to replicas inflates the uncertainty by about sqrt(N); applying the replica formula
  to a Hessian set shrinks it. The script refuses member counts that do not fit the declared type.
- The confidence level comes with the set (`ErrorConfLevel`). A 90% CL Hessian set is not rescaled to 68% silently;
  if a rescaling by 1.645 is used, it assumes a Gaussian and is stated.
- For replica sets, the observable evaluated on member 0 need not equal the mean over replicas for a nonlinear
  observable; report the replica mean when the replica prescription is used.

## alpha_s and PDF together

Sets with alpha_s variations (members or companion sets at alpha_s +- delta) let the alpha_s uncertainty be
evaluated with consistent PDFs. A combined PDF+alpha_s uncertainty is a prescription (commonly in quadrature for
Hessian sets); name it. Never vary alpha_s in the matrix element alone while keeping the PDF fixed.

## LHAPDF (guide, not run here)

Typical Python use: `pset = lhapdf.getPDFSet(name)`, `pdfs = pset.mkPDFs()`, evaluate the observable on every
member, then `pset.uncertainty(values, cl)` applies the set's own rule; compare it with `pdf_uncertainty.py` on the
same values. Record `lhapdf --version` and the data-file version of the set; sets are versioned and their members
change between versions.

## Deliverables

Set name and version, order, alpha_s(m_Z) of the fit and of the calculation, error type and CL, the combination
used (script output or LHAPDF), and whether alpha_s was varied with consistent PDFs.
