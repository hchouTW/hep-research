# Code-to-methodology & technical-manual synthesis

Use when there is source code that implements a mathematical, statistical,
or algorithmic method — an analysis pipeline, a model, an optimization
routine, a numerical technique — but **no existing paper** describes it yet,
and the goal is to reverse-engineer the code into a written Methodology +
Technical Manual document. This is the inverse of this skill's other
code-facing files, which both assume a paper already exists:
`code-review-report.md` checks code *against* an already-written
paper's claims, and `reproducibility-auditing.md` traces an
already-*reported* result to execution evidence. Here, no paper text exists
yet — the output is new documentation, not a findings report.

The invariant that matters is *mathematical/algorithmic content to extract*,
not *whether a paper exists*. Code with no such content is out of scope —
see the last decision-rule bullet below.

## Decision rule

- No paper, code implements a method with real mathematical/algorithmic
  content, want a write-up describing what it does and how to use it →
  this file.
- A paper's Methods section already exists and needs checking against the
  code → `code-review-report.md`.
- A paper's reported result needs to be traced to execution evidence →
  `reproducibility-auditing.md`.
- The code needs packaging for public release (README, license, pinned
  environment) rather than a methodology write-up →
  `artifact-packaging-for-release.md`.
- Generic software with no mathematical/algorithmic content to extract (a
  CRUD API, a UI component library, build tooling) → out of scope for this
  file and for this skill. This skill's charter is the scientific-paper
  lifecycle, not general software documentation. If Part A below would end
  up entirely `[FORMULATION UNCERTAIN: no extractable method]`, that's a
  signal this file is the wrong tool for the code at hand, not a gap to
  force-fill.

## What this does not do

This produces a documented *reading* of the code — what it appears to
implement — not a certified-correct derivation. Once a candidate
mathematical formulation is reconstructed, hand off correctness
verification: PyTorch model/training/data-pipeline code to `deep-learning`;
ROOT/PyROOT/RDataFrame/uproot analysis code to `hep-analysis`. Never present
a reconstructed formula as verified correct in the output document itself.
For a formulation outside those two domains (classical numerical methods,
control theory, bespoke statistics code with no sibling skill in this
bundle to hand off to), say so explicitly in the output — an unverified
formulation with no owner is still unverified, not implicitly checked.

## Workflow

1. **Dissect the codebase.**
   - Map entry points, core logic components, and data structures by reading
     the code itself, not existing docstrings/comments/READMEs alone — those
     can be stale relative to the current implementation.
   - Trace the data flow and execution path from raw inputs to outputs.
   - Note implicit domain assumptions and constraints the code encodes but
     never states (an assumed input normalization, a hardcoded prior, an
     undocumented shape/units convention).
2. **Reconstruct the mathematics/algorithm.**
   - Extract the numerical algorithm, optimization target, or transformation
     the code implements, and formalize it in standard notation and LaTeX.
   - Where the code's intent is genuinely ambiguous — a variable name or
     control-flow branch doesn't disambiguate between two plausible
     formulations — write `[FORMULATION UNCERTAIN: <why>]` instead of
     picking the more common-looking one. This mirrors this skill's existing
     rule against inventing numbers or citations (see this file's "Working
     within this skill's discipline" below).
   - Name the methodology's category (e.g. statistical inference, graph
     optimization, probabilistic modeling) so a reader can place it before
     reading the derivation.
3. **Synthesize the two-part document.**
   - **Part A — Methodology & Theoretical Background.** A high-level
     theoretical summary with formal LaTeX equations; the algorithm workflow
     (initialization / iteration-or-processing / convergence-or-termination);
     the methodology's classification.
   - **Part B — Engineering User Manual & API Guide.** System architecture as
     a module/class responsibility table (primary responsibility, key
     inputs, key outputs); environment and dependency prerequisites read
     from the codebase's actual imports/lockfile/build config, not assumed;
     a minimal runnable quickstart snippet built from the code's own entry
     point, not invented usage.
   - `../assets/templates/code_to_methodology_manual_template.md` gives the
     fill-in-the-blank output shape for both parts.

## Working within this skill's existing discipline

- Never invent a mathematical form, dependency version, or example value the
  code doesn't actually support — mark it `[VALUE NEEDED: ...]` or
  `[FORMULATION UNCERTAIN: ...]`, matching `academic-papers-guide.md`'s "Working style within
  this skill" rule against inventing numbers, uncertainties, or citations.
- State explicitly which parts of the codebase were out of scope for the
  pass — a large repository rarely gets fully dissected in one session, and
  a manual that silently omits a module reads as more complete than it is.
- If the code is expected to change faster than the documentation could
  reasonably track, say so rather than presenting the manual as permanently
  current.
