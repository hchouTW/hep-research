# Preregistration and registered reports

Use when drafting a preregistration document (hypotheses and planned
analysis, filed before data collection or before looking at outcome data)
or a registered report's Stage 1 (introduction/method/analysis plan,
submitted for in-principle acceptance before results exist) and Stage 2
(the completed study, reporting exactly what Stage 1 committed to). Use
`statistics-and-ml-papers.md` for general reproducibility-checklist and
venue conventions, and `reproducibility-auditing.md` when the task is
checking whether an already-completed study matches its own preregistration
rather than writing one.

## Preregistration

1. State hypotheses and predicted direction/effect before any outcome data
   is examined — if the user has already seen results, say so explicitly
   rather than writing a preregistration that reads as if it preceded them;
   a preregistration written after seeing data is not a preregistration, it
   is a false record.
2. Specify the analysis plan concretely enough to be a real constraint: the
   primary outcome measure, sample-size/stopping rule, planned statistical
   test(s), covariates, and exclusion criteria decided in advance. Vague
   language here ("we will analyze the data appropriately") defeats the
   purpose — flag it back to the user rather than filling in a plausible-
   sounding default.
3. Distinguish confirmatory analyses (preregistered, hypothesis-testing) from
   exploratory ones (anything decided or adjusted after seeing data) and
   keep that label attached through to the eventual paper — an exploratory
   finding reported as confirmatory is the specific failure preregistration
   exists to prevent.
4. File on the registry the venue or field expects (OSF, AsPredicted,
   ClinicalTrials.gov-style registries for the relevant field) and record the
   registration ID/timestamp for later citation in the paper's methods.

## Registered reports

1. Stage 1 contains everything a normal paper has except results and
   discussion: motivation, hypotheses, full method, and the exact planned
   analysis — written so that a reviewer can grant in-principle acceptance
   based on the question and design alone. Do not include pilot-derived
   results dressed as motivation without disclosing they came from piloting.
2. Track committed elements (hypotheses, sample size, exclusion criteria,
   analysis pipeline) as a checklist to carry into Stage 2 verbatim. Use
   `revision-impact-tracking.md`'s change-ledger pattern if a Stage 1-
   accepted plan needs a justified deviation — registered-report venues
   generally require deviations disclosed and justified, not silently
   applied.
3. In Stage 2, report the preregistered analyses first and clearly labeled,
   then any exploratory analyses in a separate, clearly marked section — do
   not interleave them so a reader can't tell which is which.
4. If a result contradicts the preregistered hypothesis, report it as such;
   registered reports are accepted based on the question and method, not the
   outcome — do not reframe a null or contrary result as if it were the
   original hypothesis.

Deliver the preregistration/Stage-1 document plus a compact commitment
checklist (hypothesis, primary measure, sample-size rule, analysis, planned
exclusions) that the eventual paper or Stage-2 report can be checked
against.
