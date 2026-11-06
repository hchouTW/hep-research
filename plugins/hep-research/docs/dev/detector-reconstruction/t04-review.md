# T04: independent review of the proposed values

Reviewer: a fresh agent with no access to the author's reasoning, 2026-11-06. **Verdict: redesign needed** for the shared pull design; the rest needs fixes. This is an unrecorded consultation, not a hep-review tier. The author recomputed findings 1-4 separately and they hold (`<private>/evidence/t04-oc/`).

| # | Severity | Finding | Number | Fix proposed |
| --- | --- | --- | --- | --- |
| 1 | Blocker | The 1 % family rate covers one parameter only | 0.49 % per parameter; 3.8 % for 8 parameters; 7.5 % over two fixtures; about 17 % with efficiency at the quoted true values | Count every test; about 7,100 per bin for pulls alone |
| 2 | Blocker | "Caught 100 %" holds only when all 12 bins shift, while Section 11.3.2 gates each bin | One bad bin: bias 0.06 caught 76 %, width 1.06 caught 83 %; 50 % at the tolerance | Test that the bound lies within tolerance, about 10,700 per bin; report single-bin power |
| 3 | Blocker | The width gate contradicts the 1 % wrong-minimum allowance | Two entries at pull 20 give sd 1.077; 38 give 2.01 | Core width (`sigma_68` or MAD) plus a separate tail gate; state the population |
| 4 | Blocker | Pull gates fail a correct fit at low counts | Poisson with Hessian sigma: mean -0.105 at mu = 25, -0.051 at mu = 100 | Declare a valid range; report only outside it |
| 5 | Major | A fixed 0.99 floor is a performance target, not closure | 0.995 fails 6.5 % | Compare with fixture-known efficiency; freeze fixture parameters |
| 6 | Major | "Too few events" has no number; denominators are not always 5,000 | Matched n below 4,979 when efficiency is below 0.9958 | Numeric minimum on actual denominators; bounds computed from n |
| 7 | Major | Objects in one event are not independent (11.3.1, 11.3.2) | ICC 0.05, 10 objects per event: 4 % pull-mean false failure, 7.5 % efficiency false pass | Define the statistical unit; bootstrap by event |
| 8 | Major | K16's "not resolved" has no interval or level; split, merge, mis-ID, vertex assignment ungated | | State the interval; add gates or justify |
| 9 | Major | "The code is correct for this fixture" overclaims; T07 also shares its geometry with its fixture | | Say "no discrepancy above X" |

Minor: 0.3 % was a 13-of-4,000 fluctuation (exact 0.49 %); Sidak control covers pulls only; bin in truth, not observed photon count; sum-to-1 gates may be tautological, and unclustered cells sum to 0; "K09 budgets" belongs to K10.

Reviewer found sound: Clopper-Pearson cutoffs, every-bin efficiency false pass 4.7 %, K12.

## Second review, of version 2

Reviewer: a second fresh agent, which judged the design before reading the first review. **Verdict: freeze-ready after fixes.** First-review findings 2, 8 and 9 closed; 1, 3, 4, 5, 6, 7 partly closed. The author recomputed the clustering, charge and binning claims; they hold, except that the charge-dependent bias passed the width gate 66 % of the time in the author's run, not always. Version 3 applies the fixes.

| # | Severity | Finding | Fix in version 3 |
| --- | --- | --- | --- |
| 1 | Blocker | T09 had no gate on failed fits | Fit-failure gate on the full population |
| 2 | Blocker | One design effect does not fit all statistics; count-based minimum unworkable | Bootstrap `se` per statistic; precision minimum instead of `n_eff` |
| 3 | Blocker | Clopper-Pearson on objects ignores clustering: a true 1 % passed up to 24.7 % | Effective-count bounds: 4.2-5.7 % simulated |
| 4 | Blocker | "Before any run" conflicted with development checks | Two-step freeze |
| 5 | Major | Truth bins undefined for fakes and vertices | Reconstructed and event-level bins |
| 6 | Major | The trimmed mean is not the mean; skew and outliers can pass | Renamed robust centre; mean and RMS reported; limit stated |
| 7 | Major | A charge-dependent bias cancels; prereg bins dropped | `q/p` gated per charge; one-dimensional diagnostics |
| 8 | Major | Noise reference treated as exact; fixed fake ceiling | Paired bootstrap; ceiling set at Freeze B |
| 9 | Major | Random binning leaves bins short | Stratified generation with margin |

Minor findings (test counts, `se` constant, wrong-minimum limit, photon toy value, overclaiming wording) are also applied.

## Third review and rechecks, on versions 3 and 4

Fresh agents, 2026-11-06, each with no access to the author's reasoning. Unrecorded consultations, not hep-review tiers. Full texts are in `<private>/evidence/20261106T102310Z-b3-review/` and `<private>/evidence/t04-v4/`.

| Review | Of | Verdict | Blocker, major, minor |
| --- | --- | --- | --- |
| Third review | Version 3 | Not freeze-ready | 5, 11, 6 |
| Recheck 1 | Version 4, round 1 | Not freeze-ready | 4, 14, 8 |
| Recheck 2 | Version 4, round 2 | Fixes needed, no further review | 3, 10, 8 |

The statistical core reproduced in the third review. Its blockers were missing fixture definitions, an unbounded Freeze B, a self-referential fake ceiling, no rule from bins to a workflow result, and undefined metrics. Recheck 1 found a failed evaluation could reopen valid ranges, and T08's clustering was unwritten with targets that failed by arithmetic. Recheck 2's blockers were in the section 18 rules.

Each blocker was checked by the coordinator against the document and the plan, with sample arithmetic recomputed by hand, before it was accepted. Findings and their handling: t04-v4-dispositions.md.

Round 3's changes were not reviewed, as recheck 2 ruled. `calc-t08-reference.py` gained code in that round, which the coordinator read once; it has not been run. The valid-range moves were removed by a coordinator ruling, listed in section 16 of version 4 for the user.

