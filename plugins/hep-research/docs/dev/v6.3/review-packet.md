# Review packet for G-ENFORCE step 2 (v6.3 analysis-check programme)

Status: prepared 2026-10-16 for the non-author reviewers the maintainer names (O04), in the roles that may accept
analysis-check reports as evidence (O14). The implementer prepared it and does not review it. A review recorded here
does not enable any rule; enabling one per purpose is a separate maintainer decision (`decision-enforce.md`).

## What to review

| Item | Files | The question for the reviewer |
| --- | --- | --- |
| Chain rules | `contracts/analysis_checks/rules.py`, `contracts/rules/registry.json` (rules `r-*`), `docs/dev/v6.3/m2a-design.md` | Does each rule return `satisfied` only on established evidence, and are its reason codes right for the five states? |
| Ratio rules | same files, rules `r-ratio.*` | Is "exact cancellation = same factor instance, selection, power, nonzero factor" the right bounded rule? Are validation records and scoped declarations the right evidence? |
| Coverage contract | `contracts/semantics/coverage/differential-flux.coverage.json` | The stages and covered efficiency members are proposals (O09). Does `correct_efficiency` cover only `selection_efficiency`? Should the effective-exposure members stay undefined? |
| Effect catalog | `contracts/vocab/effects.json` | Is the efficiency class and the exposure composition, with its conditions, correct? |
| Custodian requirement | `docs/dev/v6.3/custodian-gate-requirement.md` | Are the eight checks the right conditions before a report counts toward formal use? |
| `dependencies.py` row | `docs/dev/v6.3/refusal-matrix.md` (G-ENFORCE step 1) | Is "a file without inputs is consistent but not allowed" acceptable for a check-context file, or should the reader refuse non-envelopes? |
| crflux proposal | `docs/dev/v6.3/crflux-review.md` | Promote nothing; ask the AMS-02 profile owner to define or retire `crflux:local-interstellar`. |

## How to check the claims yourself

From the plugin root:

```text
python3 -m unittest discover -s tests/contracts -t . -p 'test_v63_*.py'
python3 contracts/rule_registry.py check
python3 tools/run_all_checks.py --out <dir>
```

The worked cases are built by `tests/contracts/v63_cases.py`: CASE-CHAIN (the public AMS example), the reduced
positive case and the ratio case. The shadow difference review is `docs/dev/v6.3/shadow-review.md`.

## Review record

One row per reviewer and item. A review by the implementer counts as `self-reviewed` (C15).

| Reviewer | Role | Date | Item | Conclusion (accepted / changes requested / rejected) | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
