# Worked example: evidence-linked writing (synthetic)

One result artifact traced into a manuscript, changed, and tracked. Every file under `project/` is synthetic: the
input labeled `observed` simulates a measured result and is not real data; every number is a placeholder. Run
`python3 run.py` from this folder (it only reads the project and writes `output/`); `tests/skills/research_communication/test_worked_example.py`
regenerates the reports and compares them with the committed output.

| Step | Command (from `project/`) | Report | What it shows |
|---|---|---|---|
| Result artifact and claim map | `artifacts/comm.json`: claim `claim:C1` (observed, from `artifacts/obs.json` at `extension.results.ratio`) and the synthetic illustration `claim:C2` (from `artifacts/syn.json`); the envelope keeps the sticky caveats, each claim its own provenance | — | mixed provenance represented without putting `observed` beside `synthetic` |
| Paragraph and caption | `check_communication.py artifacts/comm.json --project-root . --checks manuscript` | `output/01-check-communication.json` | the abstract sentence, the body sentence and the caption of `claim:C1` are located in `paper/main.md`; coverage counts; whole-manuscript coverage not claimed |
| Claim audit and draft facts | `audit_claims.py artifacts/comm.json --project-root .` | `output/02-audit-claims.json` | the claim matrix, the draft-ready facts (value 1.02, stat 0.05, status observed; 0.98 synthetic), reporting completeness |
| Changed result | `track_revision_impact.py artifacts/comm.json artifacts/comm_v2.json --project-root .` | `output/03-revision-impact.json` | the authoritative result moved to `artifacts/obs_v2.json` (1.09) under a new source version while the abstract, body and caption did not: exactly those three occurrences are stale, the assessment of `claim:C1` is reopened (not called false), `claim:C2` keeps its provenance, the revision item stays pending |
| Response draft | `check_adaptation.py artifacts/comm_v2.json --project-root . --responses` | `output/04-responses.json` | the referee asked for the rerun; it has not happened, so the reply says "pending" and the authors' draft "We have rerun the fit" is a confirmed inconsistency (exit 1) |
| Unresolved evidence | `check_communication.py artifacts/comm_v3.json --project-root .` | `output/05-unresolved-source.json` | a literature source `lit:S01` is cited but its ledger file is not in the project: the run is incomplete (exit 3), never a pass |

What the reports do not say: that any claim is scientifically right. An assessment in the record is its assessor's
statement; the checks establish consistency between the record, the files and the manuscript.
