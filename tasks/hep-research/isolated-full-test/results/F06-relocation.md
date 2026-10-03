# F06 relocation (E2, dd9b940)

| Run | File | Result |
|---|---|---|
| 1 | `relocation-20261003T194714Z.json` | fail: `packaging_scan` failed in the copy. Cause (reproduced): the INSTALL order's `plugins/hep-research/.venv-hep` (294 MB, git-ignored) was still in the tree; `check_relocation.py` copies everything except `__pycache__`, `*.pyc`, `.pytest_cache`, `output-*`, and all 94 packaging findings are inside `.venv-hep`. The unit failure for Mermaid and the DDP error are the same as F02 |
| 2 | `relocation-20261003T200705Z.json` | `.venv-hep` moved out of the tree (not deleted): packaging passes. Unit tests 1241 run, 1230 pass, 0 fail, 1 error (DDP, as F02), 10 skip; profile suites pass; `ams_ledger_preservation` and traceability skip. The extra unit skip is `test_lint_task` (needs the legacy checkout), the same cause as the two check skips: the copy is outside the repository and has no `.legacy/` next to it |

Copy properties (both runs): path with spaces, outside the repository, no symlinks, no file names the source path.
