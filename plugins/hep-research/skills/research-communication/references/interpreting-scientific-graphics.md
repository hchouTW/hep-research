# Interpreting scientific graphics

Use when reading and critically interpreting a figure already in someone
else's paper — not designing one. Use `figures-and-tables.md` for the
design side (what makes a figure publication-ready, how to caption and
build one); use `manuscript-consistency-auditing.md` and
`claim-evidence-mapping.md` once a figure-reading problem needs to be
tracked as a finding against the paper's claims.

## Reading common plot types correctly

Each plot type has a specific thing readers most often misread:

- **Log-log spectra** (energy/mass/flux spectra common in HEP and
  astroparticle papers): read the local slope, not the absolute height, for
  a power-law claim — a "steep" or "flat" region is about slope, and a
  visually small gap between curves near the top of a log axis can still be
  an order-of-magnitude difference. Check where a stated deviation from a
  power law actually starts on the axis, not just that "there's a bump."
- **Exclusion contours / Brazil-band limit plots**: the solid line is the
  observed limit; the dashed line and shaded bands are the *expected* limit
  under the background-only hypothesis and its ±1σ/±2σ spread. An observed
  line outside the green/yellow bands is itself worth noting (excess or
  deficit relative to expectation), not just "was this mass excluded."
  Check which confidence level (90%, 95%, CLs) the exclusion is quoted at —
  this changes the reach substantially and is easy to skip past.
- **ROC and precision-recall curves**: a curve that's higher everywhere
  dominates, but curves that cross mean neither dominates — a single AUC
  number can hide that one method is better only in an operating regime
  the paper doesn't actually use. Check where on the curve the paper's
  actual working point sits, not just the summary statistic.
- **Corner/posterior plots**: diagonal panels are marginal (1D) posteriors;
  off-diagonal panels are joint (2D) constraints. A tilted ellipse or banana
  shape in an off-diagonal panel means the two parameters are correlated —
  reading only the marginals misses that a value near the edge of one
  parameter's range may still be perfectly consistent once the correlation
  is accounted for.
- **Skymaps**: check the projection (Mollweide, Aitoff, orthographic) before
  comparing angular sizes across the map — most all-sky projections distort
  area or shape away from the center. Check whether the color scale encodes
  significance, flux, or counts — these are easy to conflate and change
  what a "hot spot" actually means.
- **Cutflow/efficiency plots and tables**: check whether values are
  absolute (fraction of the original sample) or relative to the previous
  cut — a sequence of relative efficiencies close to 100% can still
  represent a small absolute surviving fraction after many cuts.
- **Learning curves and ablation plots**: check for train/validation
  divergence (overfitting) rather than reading only the final-epoch value,
  and check whether the x-axis is linear or log-scale epochs — a log-x axis
  compresses early, fast-changing training dynamics that a linear axis
  would show as the most dramatic part of the curve.

## Extracting approximate values when no data table is given

- Prefer a linked data table, HEPData record, or supplemental file over
  reading pixels off a figure whenever one exists — check for it first (see
  `citations-and-bibliography.md`'s supplemental-material-linking guidance,
  and the AMS-02 case study in `astroparticle-and-cosmic-ray-papers.md`,
  where the underlying flux tables are often published as a separate
  collaboration-site link rather than in the paper's own figure).
- If reading from an image is the only option, read against the plot's own
  gridlines/tick marks rather than eyeballing a fraction of the panel, and
  state the result as an approximate value with its precision made
  explicit ("approximately 45 GeV, read from the plot") — never report a
  pixel-read value with more precision than the reading method supports.
  This is the same discipline `manuscript-consistency-auditing.md` requires
  when comparing a pixel-read value against a stated one.
- For a log-scale axis, remember that visually equal distances are not
  equal differences — interpolate in log space, not linear space, when
  estimating a value between gridlines.

## Spotting misleading visualization techniques

- **Truncated or non-zero-origin axes** that exaggerate an apparent
  difference between bars or points — check the axis range before judging
  the size of an effect, especially in a bar chart.
- **Inconsistent bin widths** across histograms being compared in the same
  panel or across panels — a fair comparison needs matched binning, not
  just matched axis ranges.
- **Dual-axis tricks**: two different y-axes plotted together can be scaled
  to visually align two curves that have no real relationship — check
  whether both axes start at a meaningful reference point (often zero) and
  whether their relative scaling was chosen to produce visual overlap.
- **Log-scale compression hiding effect size**: an axis that is log-scaled
  specifically to make a large relative difference look small (or vice
  versa when linear) — ask whether the field's convention actually calls
  for a log axis here (e.g., spectra do) or whether the choice flatters the
  result.
- **Cherry-picked axis ranges** that crop out an inconvenient region (a
  competing method's better regime, a discrepant data point) — check
  whether the visible range covers the full range the underlying data or
  claim spans.
- **Mismatched color scales between compared panels** (different min/max
  or different colormaps) that make two panels look more or less similar
  than the actual values warrant.
- **Absent uncertainty bands/error bars** on a curve or points where the
  paper's own claim depends on the difference being significant — no
  visible uncertainty is not evidence of high precision; check the caption
  and Methods for whether uncertainty was computed and simply omitted from
  the plot.

## Visual impression vs. statistical significance

- Overlapping error bars are not proof of no difference, and separated
  error bars are not a significance test by themselves — check whether the
  paper reports an actual test (p-value, confidence interval on the
  difference, Bayes factor) rather than relying on the reader's visual
  impression of separation.
- A "clear trend" read off a scatter plot is not a fit — check whether a
  quoted trend has an actual regression/correlation statistic behind it, or
  is asserted from the plot alone.
- Check the caption/Methods for which uncertainty convention is plotted
  (statistical only, or statistical+systematic combined) and at what
  confidence level — a claim in the prose can quietly assume a stronger
  convention than what the figure actually shows. This feeds directly into
  `claim-evidence-mapping.md`'s evidence-strength check once a mismatch is
  found.

## Fair-comparison checks specific to figures

When a figure compares multiple methods, datasets, or conditions in one
panel: check that binning, normalization, and axis range are matched across
the compared series; check that the same baseline/control conditions apply
to all of them; and check whether the apparent winner would still be the
winner under a different, equally valid axis choice (linear vs. log,
zero-origin vs. not) — a comparison that only looks decisive under one
specific axis choice is worth flagging rather than taking at face value.

Deliver findings the same way as the skill's other reading checks: the
figure's locator, the specific concern, why it matters to the paper's
claim, and what wasn't verified (e.g., no underlying data file was
available, so any extracted value is approximate only).
