# Statistical inference for physics

Use when evaluating or constructing a statistical inference — checking whether a
paper's likelihood, test, interval, or limit is set up and interpreted correctly,
or reasoning through one while drafting a Results/Systematic Uncertainties
section. This is inference *reasoning*; the fit, limit or toy campaign itself is
also `hep-statistics` work (`${CLAUDE_PLUGIN_ROOT}/core/stats` and the pyhf/Combine
adapter). Route the neighbouring steps by what is being done: deriving the model,
prediction or approximation is `hep-theory`
(`../../hep-theory/references/mathematical-reasoning-and-proof.md`); designing the
selection, cutflow or systematic variations is `hep-analysis`; an ML evaluation
harness is `physics-ml`; explaining or writing up the result is
`research-communication`.
Cross-references: `../../research-communication/references/claim-evidence-mapping.md` for whether the conclusion follows
from the result; `../../research-communication/references/equation-and-notation-auditing.md` for whether the likelihood's
algebra/dimensions are internally consistent; `../../research-communication/references/scientific-style.md` for how to
phrase the resulting claim once it's calibrated correctly.

## Table of contents
- [Entry questions](#entry-questions)
- [Likelihood-based inference](#likelihood-based-inference)
- [Frequentist inference](#frequentist-inference)
- [Bayesian inference](#bayesian-inference)
- [Systematic uncertainty](#systematic-uncertainty)
- [Common probability errors](#common-probability-errors)
- [Statistical claim calibration](#statistical-claim-calibration)
- [Sources](#sources)

## Entry questions

Before interpreting or accepting a statistical result, answer as many of these
as apply — skip a question only when it's genuinely inapplicable to the method,
not because the paper omitted the answer:

1. What is the estimand — the quantity the analysis is actually trying to learn?
2. What is the statistical model (the data-generating assumption)?
3. What is the likelihood, and does it actually correspond to that model?
4. What data enter the inference, and what was excluded or blinded?
5. What are the parameters of interest?
6. What are the nuisance parameters, and how are they constrained?
7. What assumptions justify the inference procedure (asymptotic regime,
   independence, correct model specification)?
8. What uncertainty is being reported — statistical only, or statistical +
   systematic, and combined how?

A paper that never lets you answer (1)-(3) has an inference that cannot yet be
evaluated — say so rather than assessing the reported number in isolation.

## Likelihood-based inference

- Confirm the likelihood's functional form matches the stated data-generating
  process — a Poisson-counting likelihood used where the described data are
  unbinned, or a Gaussian likelihood used for a small-count regime, is a mismatch
  worth flagging even if the fit converges.
- For maximum-likelihood estimation, check that the reported uncertainty comes
  from the actual curvature/profile of the likelihood (or a calibrated
  approximation to it), not a rule-of-thumb error propagation grafted on
  afterward.
- A likelihood ratio or profile likelihood is only as good as the nuisance-
  parameter treatment it profiles over — check that nuisance parameters
  relevant to the result are actually included, not fixed to their nominal
  value while being described elsewhere as "accounted for."
- For a covariance or correlation matrix used in the fit, check it is positive
  (semi-)definite and that off-diagonal terms have a stated physical origin
  (shared systematic source, shared calibration) — an unexplained correlation
  structure is a modeling assumption in disguise.

## Frequentist inference

Do not treat an asymptotic approximation as universally valid. Before accepting
one:

1. Identify the specific approximation used (Wilks' theorem for a likelihood-
   ratio test statistic, Wald for a Gaussian-limit interval).
2. Identify the assumptions it requires (large sample size, parameter not at a
   boundary, correct model, nested/regular hypotheses).
3. Check whether the analysis's actual sample size and parameter regime
   plausibly satisfy those assumptions — a search near a physical boundary
   (a non-negative signal strength, a cross-section at zero) is a standard case
   where Wilks' theorem [Wilks 1938] needs a corrected asymptotic form or doesn't
   apply: on a boundary the null distribution becomes a chi-squared mixture
   [Chernoff 1954], e.g. the half-chi-squared distribution of the discovery test
   statistic q0 [Cowan et al. 2011].
4. If the regime is boundary/non-regular/low-count, expect (or perform) a toy
   Monte Carlo calibration of the test statistic rather than accepting the
   asymptotic p-value at face value.
5. Calibrate the final claim to the validated method, not the convenient one.

Other checks:

- **Local vs. global significance**: for any reported local significance, check
  whether a look-elsewhere effect applies (the search scanned more than one
  place — a mass range, multiple channels, multiple sky positions) and whether
  a trials-corrected global significance is also given [Gross & Vitells 2010].
  A 3σ local excess scanned over dozens of independent bins is routinely well
  below 3σ globally.
  See `../../research-communication/references/reading-papers.md`'s look-elsewhere-effect check for where this surfaces
  during a first read.
- **Upper limits and exclusion**: identify the test statistic and confidence
  construction (e.g. CLs [Junk 1999; Read 2002], the Feldman-Cousins unified
  ordering [Feldman & Cousins 1998], or a plain Neyman construction), whether the limit is
  observed or expected (with its uncertainty band), and whether nuisance
  parameters are profiled or fixed at the limit-setting point.
- **Coverage**: a stated confidence level is a coverage property of the
  procedure across repeated experiments, not a probability statement about the
  single observed interval — do not let a paper's phrasing imply otherwise
  without flagging it.
- **Multiple testing**: when several hypotheses or channels are tested, check
  for a stated correction (Bonferroni, Holm, false-discovery-rate) or an
  explicit argument for why none is needed (e.g. a single pre-registered
  channel).

## Bayesian inference

- Identify the prior, the likelihood, and what marginalization was performed to
  obtain the reported posterior or credible interval.
- Check whether nuisance parameters were marginalized (integrated out) or
  profiled (optimized out) — these give numerically different intervals and the
  paper should say which.
- For a result that could plausibly be prior-sensitive (weak data, informative
  prior, a boundary-adjacent parameter), check whether a prior-sensitivity
  check or an alternative prior was reported; its absence is a gap, not
  automatically a flaw.
- A posterior predictive check (does the fitted model reproduce features of the
  data it wasn't directly fit to?) is evidence about model adequacy, not proof
  of it.
- **Never treat a confidence interval and a credible interval as
  interchangeable.** A 95% CI is a statement about the procedure's long-run
  coverage; a 95% credible interval is a posterior probability statement
  conditional on the prior. Reusing one's numeric value while calling it the
  other misstates what was computed. See `../../research-communication/references/scientific-style.md`'s statistical
  reporting section for how to phrase this once verified.

## Systematic uncertainty

For each material source of systematic uncertainty, require an answer to:
*how does it actually enter the final inference?* — a paper that lists sources
without explaining propagation has an inference gap, not just an incomplete
table.

- **Nuisance parameter modeling**: is each systematic represented as a
  constrained nuisance parameter (with a stated constraint term/prior), or
  folded in as a fixed additive/multiplicative shift? These propagate
  differently through a fit.
- **Correlated uncertainties**: when the same systematic source affects
  multiple bins, channels, or measurements, check that the correlation is
  actually modeled (a shared nuisance parameter, an off-diagonal covariance
  term) rather than treated as independent per bin, which understates the true
  uncertainty on any derived quantity.
- **Normalization vs. shape**: a systematic that only rescales a distribution
  behaves very differently in a fit from one that changes its shape — check
  which is claimed and whether the fit setup matches.
- **Uncertainty provenance**: is a given systematic data-driven (calibrated
  against a control sample) or simulation-based (relies on the accuracy of a
  Monte Carlo model)? A simulation-based systematic inherits the simulation's
  own validation status.
- Do not accept a total uncertainty that combines statistical and systematic
  components without stating whether they were added in quadrature under an
  independence assumption or combined with an explicit correlation model.

## Common probability errors

Guard against these specific unjustified leaps, which recur across otherwise
careful analyses:

- **Uncorrelated ⇒ independent.** Zero measured correlation rules out a linear
  relationship, not dependence in general — two variables can be uncorrelated
  and still statistically dependent (e.g. related by a symmetric nonlinear
  function). Flag this jump whenever "no correlation" is used to justify
  treating two quantities as independent in a likelihood or covariance
  structure.
- **Gaussian approximation ⇒ exact Gaussian distribution.** A large-sample or
  central-limit argument justifies treating an estimator as *approximately*
  Gaussian in some regime; it does not make the underlying distribution
  Gaussian, and the approximation can fail exactly where it matters most (tails,
  small samples, boundary parameters).
- **Monte Carlo estimate ⇒ exact probability.** A Monte Carlo integral, toy
  p-value, or sampled expectation carries its own stochastic uncertainty
  (finite sample size, finite number of toys) — report or ask for that
  uncertainty rather than presenting the estimate as an exact value.

## Statistical claim calibration

The written conclusion must match what the inference actually established —
no stronger. These pairs are not interchangeable; require the weaker,
literal reading unless the stronger one is separately justified:

| Reported result | Not the same as |
|---|---|
| "Not excluded at 95% CL" | "The data support the model" |
| "No statistically significant difference" | "The two effects are equivalent" |
| "Local significance of Nσ" | "Global/discovery-level significance of Nσ" |
| "95% confidence interval" | "95% credible interval" |
| "Correlated" | "One causes the other" |

When a paper's abstract or conclusion uses the stronger phrase, check the
Results section for the evidence needed to support it (a dedicated equivalence
test with a stated margin, a global-significance calculation, an actual
posterior) — if that evidence isn't there, the calibration gap is the finding.
See `../../research-communication/references/scientific-style.md`'s significance-language table for the physics σ-based
convention this pairs with, and `../../research-communication/references/claim-evidence-mapping.md` for recording the
gap against the paper's central claim.

## Sources

Checked 2026-09-26 against INSPIRE-HEP and Crossref records (the INSPIRE key is
given where one exists). For current conventions, the PDG "Statistics" review is
the standard summary.

- Wilks 1938 — S. S. Wilks, Ann. Math. Stat. 9, 60, doi:10.1214/aoms/1177732360
  (asymptotic chi-squared distribution of the likelihood-ratio statistic).
- Chernoff 1954 — H. Chernoff, Ann. Math. Stat. 25, 573, doi:10.1214/aoms/1177728725
  (the parameter-on-boundary case).
- Cowan et al. 2011 — G. Cowan, K. Cranmer, E. Gross, O. Vitells, Eur. Phys. J. C 71,
  1554, arXiv:1007.1727, `Cowan:2010js` (asymptotic formulae, Asimov dataset).
- Gross & Vitells 2010 — Eur. Phys. J. C 70, 525, arXiv:1005.1891, `Gross:2010qma`
  (look-elsewhere trials factors).
- Junk 1999 — T. Junk, Nucl. Instrum. Meth. A 434, 435, arXiv:hep-ex/9902006,
  `Junk:1999kv`; Read 2002 — A. L. Read, J. Phys. G 28, 2693,
  doi:10.1088/0954-3899/28/10/313 (CLs).
- Feldman & Cousins 1998 — Phys. Rev. D 57, 3873, arXiv:physics/9711021,
  `Feldman:1997qc` (unified intervals).
- PDG 2024 — S. Navas et al. (Particle Data Group), Phys. Rev. D 110, 030001,
  doi:10.1103/PhysRevD.110.030001, "Statistics" review.
