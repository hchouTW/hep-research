# PDF, nPDF and FF fits: chi2 forms, uncertainties, reweighting and profiling

Purpose: the statistics of global parton-distribution fits (proton PDFs, nuclear PDFs, fragmentation functions): chi2
with correlated and multiplicative uncertainties, tolerance criteria, Hessian and Monte Carlo replica uncertainties,
closure tests, and updating a published set with new data by Bayesian reweighting or Hessian profiling. The theory
inputs of a fit (parametrization, constraints, theory settings, cuts) are hep-theory's
(`skills/hep-theory/references/global-fits-theory-inputs.md`). Executing a complete global fit is not provided: it
needs evolution codes and fast interpolation grids (a separate software plan); this page covers specification,
reweighting, profiling and review.

Status: guidance and two tools (S12, S13), sources read in full text on 2026-10-23 (see "Sources read").

## Contents

- chi2 and multiplicative uncertainties
- Uncertainties: Hessian with tolerance, Monte Carlo replicas
- Bayesian reweighting
- Hessian profiling
- Impact studies with pseudo-data
- Review checklist for an existing fit
- Scripts
- Sources read

## chi2 and multiplicative uncertainties

- The covariance form and the nuisance-parameter form of chi2 with correlated systematics agree for additive Gaussian
  systematics; use `covariance_fit.py` (and `build_covariance.py` to assemble the covariance).
- Multiplicative (normalization) uncertainties: scaling them with the measured values biases the fit low (D'Agostini
  bias; Ball et al., arXiv:0912.2276v2, Sec. 3); fitting the normalization as a constrained nuisance ("penalty
  trick") is unbiased for one experiment but biased when several experiments are combined (their Sec. 4); a
  self-consistent covariance built from the fitted prediction is also biased for several experiments (their Sec. 5).
  The t0 method builds the multiplicative part from a fixed prior prediction t0 and iterates t0 from the previous fit;
  it is unbiased (their Sec. 6). `covariance_fit.py` offers the modes `data`, `model` (fitted prediction, with ln det),
  `nuisance` and `t0` (`t0_prediction`, `t0_iterations`); its tests measure the biases on the Peelle setup.

## Uncertainties: Hessian with tolerance, Monte Carlo replicas

- Hessian: parameters expanded about the best fit; orthogonal eigenvector sets, the uncertainty the quadratic sum over
  eigenvectors (PDG 2026 Structure Functions, Sec. 18.3). Global fits use a tolerance Delta chi^2 > 1 (for example
  Delta chi^2 = 35 or about 33 from 90% criteria in nCTEQ15 and EPPS21; `skills/hep-theory/references/
  nuclear-parton-effects.md`), sometimes a dynamic tolerance per eigenvector (Paukkunen and Zurita, Sec. 2). The
  tolerance and its confidence level are properties of the set, never chosen by the user of the set.
- Monte Carlo replicas: fits to replica data sets; central value the mean, uncertainty the standard deviation over
  replicas (PDG Sec. 18.3); some sets prescribe the median and a central 68% interval (see the nuclear page).
- Converting Hessian sets to replicas is possible (Watt and Thorne, arXiv:1205.4024v2) and the reverse exists (PDG
  Sec. 18.3); a converted set is labelled as such.
- Closure tests (fitting pseudo-data generated from a known set) and the uncertainty in extrapolation regions (small x,
  large x), which reflects only the parametrization, belong in every review.

## Bayesian reweighting

For a replica set and new data with covariance C, chi2_k of each replica gives weights (Ball et al., arXiv:1012.0836v4,
Eqs. 8-10):

```
w_k proportional to (chi2_k)^((n-1)/2) exp(-chi2_k / 2)       (NNPDF form; n data points)
w_k proportional to exp(-chi2_k / 2)                          (Giele and Keller, arXiv:hep-ph/9803393v1)
sum_k w_k = N,   N_eff = exp( (1/N) sum_k w_k ln(N / w_k) )
```

The choice of weight form is debated (Ball et al. 1012.0836 call the Giele-Keller form an error; Paukkunen and
Zurita, Sec. 4, find the question open); `pdf_reweighting.py` reports both and records the other as an alternative-method
object. N_eff measures how many replicas still carry information; when it falls below the user's threshold, refit
rather than reweight further. N_eff is not the Kish effective sample size (sum w)^2/sum w^2 of
`bayes_diagnostics.py reweight`, which the script also reports. Replicas generated from a Hessian set may be reweighted
only when flagged, and then with Giele-Keller weights and chi2/Delta chi^2 (Paukkunen and Zurita, Sec. 5, Eq. 5.2;
the NNPDF form fails there, their Sec. 6).

## Hessian profiling

For a Hessian set (Paukkunen and Zurita, arXiv:1402.6623v3, Sec. 3): with D_ik = (y_i[S_k+] - y_i[S_k-])/2 and the
tolerance t (t^2 = Delta chi^2),

```
B = D^T C^-1 D + t^2 I,   a = D^T C^-1 (y[S_0] - y),   w_min = -B^-1 a
penalty P = sum_k (t w_k,min)^2:  P << Delta chi^2 consistent;  P >~ Delta chi^2 tension with the set
(with a dynamic tolerance this reading is lost; the script then gives no verdict and no profiled uncertainty)
new central prediction y[S_0] + D w_min;  new uncertainty t sqrt(D_O^T B^-1 D_O)
```

It is linear: `hessian_profiling.py` reports the asymmetry of the members as a linearity check, and the
non-linear extension of their Sec. 3 is not implemented. The profiled PDFs are linear combinations of the set's and
satisfy its sum rules (their Eq. 3.10).

## Impact studies with pseudo-data

Pseudo-data for a future facility carry the status label `synthetic`; the projected uncertainties carry `projection`,
which the publication gate fails. They are never phrased as "will be measured". Facility settings come from an
experiment profile or the user.

## Review checklist for an existing fit

Tolerance criterion, CL and error type stated; theory settings consistent (order, alpha_s, heavy-quark scheme;
`skills/hep-theory/references/global-fits-theory-inputs.md`); theory uncertainty (MHOU) included or not; nuclear and
deuteron data treatment; normalization uncertainties treated without D'Agostini bias (t0 or equivalent); closure tests
done; extrapolation regions flagged.

## Scripts

- `pdf_reweighting.py`: weights (both forms), N_eff, Kish ESS, reweighted means and standard deviations, unweighted
  indices; refuses Hessian sets, unflagged Hessian replicas, too few replicas, a covariance that is not positive
  definite. Tests: `tests/skills/hep_statistics/test_pdf_reweighting.py`.
- `hessian_profiling.py`: w_min, the penalty, chi2 before and after, profiled observables and uncertainties, the
  linearity check; refuses non-Hessian sets and asymmetric sets with an odd eigenvector-member count (central
  excluded). Tests: `tests/skills/hep_statistics/test_hessian_profiling.py` (exact weighted least squares on a linear
  toy, the no-information limit).
- `covariance_fit.py` `t0` mode. Tests: `tests/skills/hep_statistics/test_covariance_fit.py` (GLS oracle, bias toy).

## Sources read (full text, 2026-10-23)

- R.D. Ball et al. (NNPDF), arXiv:1012.0836v4 (Nucl. Phys. B 849 (2011) 112; errata B 854 (2012) 926, B 855 (2012) 927): Sec. 2, Eqs. 3-10.
- R.D. Ball et al. (NNPDF), arXiv:1108.1758v2 (Nucl. Phys. B 855 (2012) 608): Secs. 2-3 (N_eff, unweighting, Eq. 24).
- W.T. Giele, S. Keller, arXiv:hep-ph/9803393v1 (Phys. Rev. D 58 (1998) 094023).
- G. Watt, R.S. Thorne, arXiv:1205.4024v2 (JHEP 08 (2012) 052).
- H. Paukkunen, P. Zurita, arXiv:1402.6623v3 (JHEP 12 (2014) 100): Secs. 2-6, Eqs. 2.8, 3.1-3.12, 5.2.
- R.D. Ball et al. (NNPDF), arXiv:0912.2276v2 (JHEP 05 (2010) 075): Secs. 1, 3-6.
- PDG 2026 "Structure Functions", Sec. 18.3.

Not verified and therefore not used: theory-covariance (MHOU) prescriptions; specific tolerance values beyond those on
the nuclear page; closure-test statistics of particular groups.
