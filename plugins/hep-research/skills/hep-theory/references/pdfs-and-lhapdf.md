# Parton distributions and LHAPDF

Choosing a PDF set, handling its members, and combining PDF uncertainties by the set's own rule. The combination
formulas are executable in `<plugin root>/skills/hep-theory/scripts/pdf_uncertainty.py` (tested on constructed
inputs; it refuses non-finite member values and confidence levels). LHAPDF is not installed in the environments
these checks ran in: API names below are given as a guide and are `unverified` until run.

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
  to a Hessian set shrinks it. The script refuses an odd number of `hessian` error members and fewer than 20
  replicas; the total member count is checked only when `num_members` (LHAPDF `NumMembers`, "Number of members in
  the set, including central (0)", LHAPDF 6 paper arXiv:1412.7420v2, Sec. 5.1, Table 1, read 2026-10-13) is passed.
  Pass it: a `symmhessian` set carrying two alpha_s members cannot be told apart from one with two more eigenvectors.
- The symmetric Hessian formula above is PDF4LHC21 Eq. (6.5), Sec. 6.3.2 (arXiv:2203.05506v2, read 2026-10-13).
- The confidence level comes with the set (`ErrorConfLevel`). A 90% CL Hessian set is not rescaled to 68% silently;
  if a rescaling by 1.645 is used, it assumes a Gaussian and is stated.
- For replica sets, the observable evaluated on member 0 need not equal the mean over replicas for a nonlinear
  observable; report the replica mean when the replica prescription is used.

## alpha_s and PDF together

Sets with alpha_s variations (members or companion sets at alpha_s +- delta) let the alpha_s uncertainty be
evaluated with consistent PDFs. A combined PDF+alpha_s uncertainty is a prescription; name it. Never vary alpha_s
in the matrix element alone while keeping the PDF fixed.

- **Error-type suffix.** LHAPDF marks combined sets with the `ErrorType` values `replicas+as`, `hessian+as` and
  `symmhessian+as` (LHAPDF ChangeLog, entry 2015-07-17, https://gitlab.com/hepcedar/lhapdf/-/raw/main/ChangeLog,
  read 2026-10-13). The LHAPDF source computes "the parameter variation uncertainties ... from the last 2*n members
  of the set, with n the number of parameters" (`include/LHAPDF/PDFSet.h`, `uncertainty()` documentation, main
  branch, read 2026-10-13).
- **Member order.** In PDF4LHC21_40_pdfas (`symmhessian+as`) members 0-40 are at alpha_s = 0.118, member 41 at
  0.117 and member 42 at 0.119; PDF4LHC21_mc_pdfas (`replicas+as`) has members 0-100, then 101 (0.117) and 102
  (0.119) (PDF4LHC21, Sec. 6.2, Table 6.1, read 2026-10-13). `pdf_uncertainty.py` with a `+as` type splits off the
  last two members as alpha_s down, then up; that order is the PDF4LHC21 one, check it in the `.info` file of any
  other set (the `.info` files themselves were not opened: `unverified` for sets other than PDF4LHC21).
- **alpha_s uncertainty.** PDF4LHC21 Eq. (6.7): delta_alphas = [X(alpha_s = 0.119) - X(alpha_s = 0.117)] / 2,
  corresponding to delta alpha_s = 0.001 at 68% CL, with alpha_s(m_Z^2) = 0.1180 +- 0.0010 (Eq. (6.6)); for another
  delta alpha_s the term is rescaled by r (Eq. (6.10)) (Sec. 6.3.3, read 2026-10-13). The script reports this half
  difference as a separate `alphas` object, and the alpha_s values when `alphas_values` is given.
- **Combination.** PDF4LHC21 Eq. (6.8) adds the two in quadrature, delta^(PDF+alphas) = sqrt((delta^pdf)^2 +
  (delta^alphas)^2); for the MC sets the PDF uncertainty is computed first (Sec. 6.3.3, read 2026-10-13).
  `--combine-alphas quadrature` applies it and labels the output `prescription: quadrature` with this citation.
- **LHAPDF differs.** `PDFSet::uncertainty` takes the min and max of the two variation members and combines
  asymmetric up and down errors in quadrature with the PDF ones (`src/PDFSet.cc`, main branch, read 2026-10-13); it
  agrees with the PDF4LHC21 half difference only for a response linear in alpha_s. State which one was used.
- **Symmetrized Hessian.** `--symmetrize` (`hessian` only) also reports 1/2 sqrt(sum_k (X_+ - X_-)^2), labelled an
  alternative prescription; it is not the set's own asymmetric rule (`unverified` as a recommendation of any
  collaboration: no source opened states it).

## LHAPDF (guide, not run here)

Typical Python use: `pset = lhapdf.getPDFSet(name)`, `pdfs = pset.mkPDFs()`, evaluate the observable on every
member, then `pset.uncertainty(values, cl)` applies the set's own rule; compare it with `pdf_uncertainty.py` on the
same values. Record `lhapdf --version` and the data-file version of the set; sets are versioned and their members
change between versions.

## Deliverables

Set name and version, order, alpha_s(m_Z) of the fit and of the calculation, error type and CL, the combination
used (script output or LHAPDF), and whether alpha_s was varied with consistent PDFs.
