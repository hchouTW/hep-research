# hep-authoring improvement items (added by the hep-authoring improvement task)

This folder is new: it was added by the hep-authoring improvement task (2026-10-29) and is not part of the T10
communication evaluation in `../cases/`. It reuses that evaluation's case format, runner (`../run_live_eval.py
--cases`) and replay scorer (`../score_replay.py`).

| Path | Content |
|---|---|
| `exploration/cases.json` | exploration cases (`spike`: one live run each at the base commit; exposed, support no claim) |
| `fixtures/` | synthetic inputs of those cases (no real data) |
| `results/` | scored summaries of the live runs (raw streams stay under `../runs/`, not committed) |
| `tools/` | per-item gold commitments (`commit_gold.py`, `verify_gold.py`) and the within-case permutation test (`permutation_test.py`) used by a frozen pilot comparison |
| `pilot/<target>/` | a frozen pilot protocol: `commitments.json`, the decision rule as frozen, pairing order and calibration items (gold files and nonces are kept outside the repository) |

What this task adds beyond the T10 evaluation: per-item gold grading (`held` / `not_held` / `undeterminable`) and the
decision rule of the frozen protocol. Evidence levels used here (`engineering`, `spike`, `authoring-pilot`,
`authoring-held-out`) are hep-authoring's own and are not hep-review claim states.
