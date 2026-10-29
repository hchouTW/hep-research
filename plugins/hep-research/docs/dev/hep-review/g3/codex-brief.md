# Authoring brief: the G3 held-out evaluation suite (for Codex)

You are writing the test cases for an evaluation of AI reviewers of physics analyses. The reviewers will never see
anything you write except the files under `public/`. Everything under `private/` is the answer key, and it will be
removed from this machine before any reviewer runs. Work only inside the current directory. Do not read other
directories for ideas.

## What a reviewer gets

Each instance is a short statistical analysis, as it might appear in a particle- or astroparticle-physics note. The
reviewer is asked two questions about it:
- **O-stat**: "Is the statistical treatment in analysis.md appropriate for the model and inputs stated there?"
  Criterion: "The statistical treatment is appropriate for the stated model and inputs and the stated results follow
  from it; a missing input needed to decide is named rather than assumed."
- **O-compute**: "Can every number in data.json 'stated_results' be recomputed from the inputs in data.json with the
  method described in analysis.md, within 0.1% relative?"

The reviewer answers each question as supported, violated (with findings that point at an element), undetermined
(naming the missing inputs) or not examined.

## What to write

Make **20 instances** with opaque ids: the letter `g` followed by 8 random hexadecimal digits, from a real random
source. The ids must not encode the type.

| Type | Count | Content |
|---|---|---|
| C01 | 12 | Two to four planted defects each. At least 6 have defects that interact (fixing one alone still leaves a stated number wrong). At least 4 have a defect that can only be found by numerical or Monte Carlo reasoning (for example a toy-MC coverage claim that the stated toys do not support, a binning or interpolation artefact, a convergence claim that a finer step refutes). At least 3 have a defect that needs particle-physics conventions (for example luminosity units, trigger prescales, pile-up, cross section times branching ratio, acceptance versus efficiency) |
| C02 | 5 | No defect. At least 3 use a correct method that is unusual or written differently from the textbook form, so that it looks suspicious but is right |
| C03 | 2 | No defect, but one input that the stated numbers depend on is missing from data.json (null or absent), and analysis.md says it comes from elsewhere. The stated numbers must be reachable for some admissible value of the missing input, and they must change for another admissible value |
| C04 | 1 | Correct material (like C02). Its intent has a second requirement that the review plan will not cover (see the files below) |

Mix the types in a random order. A reviewer must not be able to infer the type from length, style, file names or
field names.

### Difficulty

Three previous suites (141 trials) were too easy: reviewers found every planted defect, including multi-defect
single-page cases. This suite exists to measure a miss rate, so it must be clearly harder, while staying fair and
verifiable:
- **Length and steps.** analysis.md is 800 to 2,000 words and describes a multi-step analysis (5 to 10 steps, for
  example selection counts, a background estimate, an efficiency correction, a fit or a limit, a combination). Most
  steps are correct. data.json may hold arrays (histograms, toy-MC results, scans) of up to a few hundred numbers.
- **Plausible defects.** Each defect is a mistake a competent analyst could plausibly make: a wrong correlation
  assumption, a wrong degrees-of-freedom count, an inconsistent normalisation between steps, a unit or luminosity
  mismatch, double counting of an uncertainty, a wrong conditional probability, an approximation used outside its
  validity, and so on. No typos, no cosmetic issues, no defects announced by the text.
- **Material effect.** Every defect is non-cosmetic: it changes at least one value in `stated_results` by more than
  0.5% relative compared with the corrected analysis.
- **Honest controls.** C02 and C04 instances must be genuinely correct, including every number to 0.1%.
- **No reused families.** These were used before and are exposed: inverse-variance weights 1/sigma vs 1/sigma^2;
  binomial vs Poisson efficiency error; product of anticorrelated quantities; forward-backward asymmetry error;
  sqrt(sum w) vs sqrt(sum w^2); combining two measurements with a shared systematic; ndf of a straight-line fit;
  P(N < n) vs P(N <= n) in a Poisson limit; a missing transfer-calibration or reference-count variance term; event
  efficiency not squared for two required tracks, or branching fraction not squared for two parents; gamma
  posterior mode reported as the mean; a missing finite-population correction; a response matrix inverted as its
  transpose, or diagonal-only propagation through an unfolding; Neyman versus Pearson chi-square, or a fixed-total
  degrees-of-freedom count; a prescale left out of a control-region transfer factor, or a control count treated as
  fixed; a Bonferroni bound reported as an exact global p-value. Do not use any of them as a planted defect or as the
  main topic.
- **Fair difficulty.** A defect must be decidable from the material alone, by careful reading and computation. No
  hidden data or private convention is needed: a particle-physics convention defect relies on a standard convention
  that is stated or standard in the field.

## Files

```
public/instances/<id>/intent.json
public/instances/<id>/material/analysis.md
public/instances/<id>/material/data.json
private/gold/<id>.json
private/oracles/<id>.py
private/calibration/items.json
private/calibration/labels.json
private/AUTHOR_NOTES.md
```

**intent.json**, exactly this shape:

```json
{"id": "intent-<id>", "target_tier": "R2", "minimum_requirements": [
  {"id": "REQ-1", "text": "The derived result and its uncertainty are statistically sound and reproducible from the supplied inputs."}]}
```

For C04, add exactly this second requirement:
`{"id": "REQ-2", "text": "The inputs are tested for mutual consistency before they are used."}`

**data.json**: inputs plus a `stated_results` object with the reported numbers (enough significant digits for a 0.1%
check). No comments, and no field that hints at a defect or at the type.

**private/gold/<id>.json**:

```json
{"id": "<id>", "type": "C01|C02|C03|C04",
 "defects": [{"defect_id": "D1", "statement": "<one or two sentences: the mechanism and the affected step>",
              "affected_results": ["<stated_results key>"], "corrected_values": {"<key>": 0.0},
              "tags": ["<any of: interacting, numerical, convention>"]}],
 "missing_input": "<C03 only: what is missing>", "keywords": ["<C03 only: 2-4 lowercase substrings a reviewer naming the missing input would use>"],
 "unplanned_requirement": "<C04 only: REQ-2>", "notes": "<free text>"}
```

`defects` is empty for C02, C03 and C04. Tag a defect `interacting` when fixing it alone leaves another stated
number wrong because of a second defect, `numerical` when finding it needs numerical or Monte Carlo reasoning beyond
closed-form algebra, and `convention` when it needs a particle-physics convention. A defect may carry several tags or
none.

**private/oracles/<id>.py**: a standalone Python 3 script (standard library, plus numpy/scipy if needed) that
recomputes the instance from its public files and checks the gold. It runs as
`python3 <id>.py <path to public/instances/<id>>`, prints a JSON line `{"id": ..., "ok": true|false, "checks": [...]}`
and exits 0 only if every check passes:
- **C01**: the stated results follow from the method as written. For each defect, correcting that defect alone
  changes at least one affected result by more than 0.5%. The fully corrected values match `corrected_values` to
  0.1%.
- **C02 and C04**: every stated result matches an independent correct computation to 0.1%.
- **C03**: the stated results are reachable for the true (hidden) value of the missing input, and differ by more
  than 0.5% for another admissible value.

Run every oracle yourself and make sure all 16 pass. Fix the instance, never the oracle check.

**private/calibration/**: write 12 calibration items for a grader that decides whether a reviewer's finding matches a
planted defect. Each item has `{"item": "K01".., "defect": "<statement>", "finding": {"claim": ..., "element": ...,
"evidence_text": ...}}`, and `labels.json` maps each item to `accept` or `reject`. Cover at least: a correct finding
(several), a correct finding worded or derived differently, a finding about a different and wrong issue, and a vague
finding with no mechanism. Base the items on defects like yours, but not on your actual instances.

**private/AUTHOR_NOTES.md**: a short list of what you planted where, and anything a scorer should know.

When you finish, print only: the number of instances per type, and whether all oracles passed. Do not print any
defect, type assignment or gold content to the terminal.
