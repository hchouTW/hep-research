# G3 plan: evaluation (T08) for hep-review

Spec v9 §18.1 (T08), §18.3 (G3), §15. Decided 2026-10-29:
- **Extensions: T05–T07 are not built**, and the support matrix lists them as unsupported. T06 needs enforcement the
  host does not provide, and T07 depends on T05/T06. T05 would widen the scope beyond what one suite can measure.
- **Evaluation**: a harder statistics suite, authored by Codex and held out by the user.
- **Hosts**: Claude Code on macOS only.
- **Release** (publishing) needs external authorization and is not part of G3.

G3 claims **evaluated-scope only for what is measured**.

## Work packages

| WP | Content | Done when |
|---|---|---|
| WP1 claim lifecycle | `evaluation.py` (see below) | Tests first; transitions refuse an upgrade that has no new evidence |
| WP2 regression suite | Committed pilot evidence (G2, g2h, g2x) re-scored by the frozen drivers. The 0.1.0 golden layer-1 bytes stay. The packet-text digest is pinned, so a changed packet text forces a fingerprint change | `tests/skills/hep_review/test_regression.py` reproduces every committed `score.json` byte for byte |
| WP3 support matrix | `skills/hep-review/references/support-matrix.md` and the capability-matrix row. One row per (domain, method, format, host, tier) | Evaluated / pilot-checked / not-run / unsupported, never more than measured. T05–T07 rows unsupported |
| WP4 g3 evaluation | Codex brief v3 and frozen protocol (below). Seal, encrypt, trials, decrypt, cross-family grading, report | Report with the three denominators, the miss rate with a 95% Clopper-Pearson interval, and the false-alarm rate with its interval |
| WP5 claim update and docs | A claim per measured scope, written through WP1 with its fingerprint; SKILL.md status, CHANGELOG, G3 report, independent review of the G3 diff | G3 declared at the measured scope |

WP1 consists of:
- **CapabilityClaim objects** with the spec 15.6 binding: domain / method / format, model / host / prompt / tool /
  reader / hash profile, policy / rubric / gold / suite, case distribution, trial plan, results and limitations.
- **A fingerprint** over the parts that change capability: the host-profile digest, the packet-text template digest,
  the kernel validator version, the reader and hash profiles, and the model alias with its date ("unknown" when it is
  not pinned).
- **A state machine**:
  - experimental → pilot-checked-scope → evaluated-scope;
  - any state → needs-reassessment on a fingerprint change or a new failure type;
  - → retired.
- **A claims registry**: `assets/claims.json`, a pure check that names the current claims.

## g3 suite design (brief v3)

| Item | Value |
|---|---|
| Instances | 20, opaque `g` + 8 hex. C01 12: 2–4 defects each; ≥ 6 interacting; ≥ 4 needing numerical or Monte Carlo reasoning, e.g. a toy-MC coverage claim, a convergence or binning artefact, an interpolation; ≥ 3 needing HEP conventions, e.g. luminosity units, prescales, pile-up, a cross-section times branching ratio, a trigger efficiency. C02 5 (≥ 3 unusual but correct). C03 2. C04 1 |
| Length | 800–2,000 words, 5–10 steps; data.json may hold arrays (histograms, toy results, scans) |
| Exposed families | All families of G2, g2h and g2x are listed and excluded |
| Trials | 3 per instance = 60 |
| Grading | Claude forward, Claude reversed, Codex; calibration on 12 Codex-written items; unanimous combination |
| Budget | Claude: 60 trials + 3 grader dispatches. Codex: 1 authoring run + 2 grading runs |

**Pre-registered outputs**:
- defect-level detection with its interval, split by single / multiple / interacting, numerical, and
  domain-knowledge;
- C02 false alarms with an interval;
- C03 gap kept;
- C04;
- findings outside the gold, unadjudicated and listed.

**Claim rule**: evaluated-scope is granted for the measured scope **if the engineering gate passes and the graders
are calibrated**. The claim states the measured rates and intervals. There is no pass threshold that hides a weak
result. A detection rate below 0.8 or a false-alarm rate above 0.2 is printed as a usage warning in the claim.
