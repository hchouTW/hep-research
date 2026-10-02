# M0 Baseline Summary

- Date: 2026-10-02 (UTC 13:2x; Asia/Taipei 21:2x)
- Commit: `3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9` (matches Section 4 baseline), clean tree before branch creation
- Environment: Linux 6.18.44 x86_64 (Claude Code cloud container, not the user's workstation), Python 3.11.15,
  `.venv-hep` created empty (`pip-freeze.txt` is empty). numpy/scipy/matplotlib/sympy NOT installed (D5 install needs approval: network).
- Command: `tasks/hep-research/baseline/run_baseline.sh` (Section 8 M0 step 4 script, verbatim) with `.venv-hep` active.
- Raw results: `summary.csv`, per-skill `*.bundle.log` and `*.unittest.log`.

| Skill | Bundle validator | Tests run | Pass | Fail | Error | Skip |
|---|---|---|---|---|---|---|
| ams-analysis | exit 0 | 462 | 462 | 0 | 0 | 0 |
| hep-analysis | exit 0 | 223 | 200 | 0 | 0 | 23 |
| deep-learning | exit 0 | 118 | 104 | 0 | 0 | 14 |
| academic-papers | exit 0 | 48 | 47 | 0 | 0 | 1 |
| academic-diagrams | exit 0 | 28 | 24 | 0 | 0 | 4 |
| agile-development | exit 0 | 44 | 44 | 0 | 0 | 0 |
| task-authoring | exit 0 | 104 | 104 | 0 | 0 | 0 |
| **Total** | 7/7 exit 0 | **1027** | **985** | **0** | **0** | **42** |

Baseline failures: none.

## Skip reasons (all optional-dependency skips, none network-related)

| Count | Reason |
|---|---|
| 7 | numpy, awkward and uproot are required |
| 7 | PyTorch not installed |
| 7 | PyROOT not importable (set HEP_ROOT_PYTHON) |
| 4 | numpy/pyhf not importable (set HEP_PYHF_PYTHON) |
| 4 | PyTorch is required to build datasets |
| 3 | scipy not installed |
| 3 | PyTorch is required to measure real allocations |
| 2 | Graphviz not installed |
| 1 each | tectonic, awkward, PlantUML, Mermaid CLI, Combine (HEP_COMBINE_WRAPPER) |

The 42 skipped tests are **unverified** in this environment, not passed. Several (scipy, numpy) become runnable once D5's mandatory environment is installed.

## Network-use scan (M0 step 3)

`grep -rnE "urllib|requests|http.client|socket|API_KEY|api_key|subprocess"` over `*.py`:
- `ams-analysis/scripts/fetch_papers.py`, `crdb_query.py` use `urllib`. Their tests (`test_fetch_papers.py`, `test_crdb_query.py`) inject a `FakeHttp` object; no real requests. Not skipped.
- `*/tests/run_prompts.py`, `behavior_eval.py`, `prompts_eval.py`, `routing_eval.py` invoke model CLIs (paid). They are not matched by `unittest discover` (`test*.py` pattern) and were not run.
- No API keys found.
