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

## Added for 0.13.0 (2026-10-16): the complete suite set

Since the first version of this packet, the model part of M2b, V30 and M2c were built on synthetic cases (owner's
decision change in `decision-enforce.md`), so all 80 V parts pass. The crflux item above is decided:
`crflux:local-interstellar` was retired from `experiment:ams-02` (`crflux-review.md`, Decision). Further items for the
same reviewers:

| Item | Files | The question for the reviewer |
| --- | --- | --- |
| Model rules | `contracts/analysis_checks/model.py`, registry rules `r-model.*`, `r-aux.use`, `r-share.parameters`, `docs/dev/v6.3/m2b-model-design.md` | Within one evaluation, is "one observation enters through exactly one constraint term" the right R-AUX rule, with a shared parameter counting as one term? Is an unbound constraint correctly left unverified for the others? |
| Pairing contract | `contracts/semantics/model_pairings.json`, `docs/dev/v6.3/o03-model-pairings.md` | Do P1–P3 describe what the pyhf converter does, including "gaussian" meaning a constraint on α with `code4`? Should anything listed as unsupported be supported? |
| Run rules | `contracts/analysis_checks/runs.py`, registry rules `r-run.*`, `docs/dev/v6.3/m2c-design.md` | Are the closure sources (frozen item, external manifest entry, bound product) complete? Is a re-serialized JSON input correctly a derived input? Are the conditions for "campaign-recorded" right, and is its agent-writable limit stated clearly enough? |
| Result binding | `contracts/schemas/result_binding.json` | Does it bind enough (bundle, lock, runs, campaigns, per-root identity) and nothing that changes the bundle? Is treating it as a declaration (C12) right? |
| `allowed_outputs` rule | `docs/dev/v6.3/m2c-proposal.md` (approved), `r-run.blinding` | Is "prefixed exact entries only; unprefixed entries match nothing; a match is declaration-based" acceptable to the blinding policy owner? |
| Post-execution permit check | `contracts/permit.py` (`report_check`) | Are "cited results in the permit's artifacts" and "the same execution bundle" the right post-execution conditions for the custodian requirement? |
| Custody inventory | `contracts/custody.py` (V30) | At stage 1, is "plugin: public by origin; run-time --local: controlled, metadata missing; project-local: unknown" the right classification? |
| `dependencies.py`, result binding row | `docs/dev/v6.3/refusal-matrix.md` | The same question as for a check context: is accepting a binding as "consistent but not allowed" acceptable? |

The worked cases for these are in `tests/contracts/v63_cases.py` (CASE-MODEL, MODEL-USAGE, MODEL-SHARING) and
`tests/contracts/v63_runs.py` (RUN-CHAIN, RUN-CAMPAIGN). The tests are `test_v63_d07_model.py`, `test_v63_d12b.py`
and `test_v63_d05d.py`; the commands above run them.

## Review record

One row per reviewer and item. A review by the implementer counts as `self-reviewed` (C15).

| Reviewer | Role | Date | Item | Conclusion (accepted / changes requested / rejected) | Notes |
| --- | --- | --- | --- | --- | --- |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Chain rules | self-reviewed | C15: public and synthetic diagnostics only; owner accepted this status (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Ratio rules | self-reviewed | C15: public and synthetic diagnostics only; owner accepted this status (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Coverage contract | self-reviewed | C15: public and synthetic diagnostics only; owner accepted this status (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Effect catalog | self-reviewed | C15: public and synthetic diagnostics only; owner accepted this status (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Custodian requirement | self-reviewed | C15: public and synthetic diagnostics only; owner accepted this status (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | `dependencies.py` row | self-reviewed | C15: public and synthetic diagnostics only; owner accepted this status (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | crflux proposal | self-reviewed | C15: public and synthetic diagnostics only; owner accepted this status (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Model rules | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Pairing contract | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Run rules | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Result binding | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | `allowed_outputs` rule | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Post-execution permit check | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | Custody inventory | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
| implementer (Claude Code session) | none (author) | 2026-10-16 | `dependencies.py`, result binding row | self-reviewed | C15: public and synthetic diagnostics only (`decision-enforce.md`) |
