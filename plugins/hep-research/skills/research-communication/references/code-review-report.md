# Code review report

Use for a structured review of code that accompanies or backs a paper — a
supplementary repository, an analysis script, or a snippet quoted in the text —
producing a findings report a reader or referee could act on. This is a
different concern from `reproducibility-auditing.md`: that file
traces claims to execution evidence (does rerunning the code reproduce the
reported number); this one reviews the code itself (is it correct, does it
match what the paper says it does, is it legible to someone who did not write
it). Run both when the task calls for full reproducibility due diligence.

## Scope the review before reading code

State explicitly what is being reviewed: a single snippet reproduced in the
manuscript, one script, or a full repository. State the review's purpose —
pre-submission self-check, referee/reproducibility-committee review, or
post-publication scrutiny — since that changes how findings should be phrased
(a self-check can recommend fixes directly; a referee report should describe
impact on the paper's claims and let the authors decide the fix).

## Check paper-to-code alignment

Read the Methods/analysis description and the code side by side. Flag:

- **Undocumented deviations** — the code does something the paper doesn't
  mention (a different loss term, an extra selection cut, a preprocessing
  step, a hyperparameter or seed not stated in the text) or the text describes
  something the code doesn't actually do.
- **Ambiguity the code resolves one way** — where the paper's prose admits
  multiple readings, note which one the code implements, since that is
  effectively the paper's real specification.
- **Silent parameter drift** — hardcoded values, magic numbers, or config
  defaults that differ from the value quoted in the paper or its table/caption.

Do not assume a mismatch is a bug in the code; it may mean the manuscript text
is stale relative to the released version. Report the discrepancy and which
artifact (paper or code) is authoritative is for the authors/editors to
resolve, not something to silently pick.

## Delegate deep technical review to the domain skill

This file does not restate framework- or domain-specific correctness
guidance that already exists elsewhere. Once the paper-alignment pass above
is done, hand off:

- PyTorch code (models, training/eval loops, data pipelines) — invoke
  `physics-ml` for correctness, numerical stability, and performance
  issues.
- ROOT/PyROOT/RDataFrame or uproot/awkward columnar analysis code — invoke
  `hep-analysis` for cutflow logic, statistical treatment, and systematic
  propagation correctness.

Bring back only the findings that matter for the paper's claims — a code
review report is not a general linting pass on someone else's repository.

## General checks this skill still owns

Independent of language or domain, check whether the code is legible and
usable by someone other than the author:

- **Documentation matches behavior** — README/docstrings describe what the
  code actually does now, not an earlier version of the method.
- **Dependency and environment pinning** — versions specified precisely enough
  that a stated result is not silently dependent on an unpinned library
  update; see `artifact-packaging-for-release.md` for the
  release-readiness counterpart to this check.
- **License and reuse terms** — present and consistent with any data-use
  restrictions mentioned in the paper.
- **Runnability by a third party** — whether someone without the authors'
  local setup could execute the code from the released instructions alone
  (this is a documentation/completeness check, not an actual rerun — see
  `reproducibility-auditing.md` for execution).

## Report format

Deliver a findings table, one row per issue:

| Locator | Severity | Category | Finding | Suggested action |
|---|---|---|---|---|
| `file.py:120` or "Sec. 3.2 vs. `train.py`" | blocking / major / minor / note | alignment / correctness / documentation / packaging | one-sentence description | what would resolve it |

Order by severity, not by file. Lead the report with a one-paragraph summary
stating whether any *blocking* alignment or correctness issue affects a
specific reported claim or figure — that is the finding a reader most needs
before trusting the result. State explicitly which parts of the codebase were
out of scope for this pass.
