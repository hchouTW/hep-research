# F00 environment (E2)

| Item | Value |
|---|---|
| Commit | `dd9b9405facbdce37acb183947dc7493c4bdf5bc` (`main`, PR #19 merged), run on branch `test/fulltest-e2` |
| OS / CPU | macOS 26.5 (Darwin 25.5.0), arm64, Apple M3 |
| Claude Code | 2.1.288 |
| Venv | `~/.venvs/hep-research-e2` (outside the plugin tree, R4), Python 3.13.2 |
| Core | numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, sympy 1.14.0 |
| Optional, venv (Q1) | pyhf 0.7.6, uproot 5.7.6, awkward 2.14.0, torch 2.14.1, torchvision 0.29.1 (CPU) |
| Optional, Homebrew (Q1) | mermaid-cli 12.0.0 (node 26.10.0), plantuml 1.2026.8 (with graphviz 16.1.0, openjdk) |
| Already present | ROOT 6.38.04 (Homebrew; PyROOT via `/opt/homebrew/bin/python3.14`), Graphviz `dot` 16.1.0, tectonic 0.17.0, cmake 4.3.2 |
| Absent | CMS Combine, Docker, Slurm (`sbatch`), HTCondor (`condor_submit`) |
| Legacy checkout (F01) | `.legacy/agentic-ai-skills` at `3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9` (git-ignored) |

Decisions: Q1 proposed tools installed; Q2 live routing **not run** (user: skip routing); Q3 host default model for F07;
Q4 not stated (results kept on local branch `test/fulltest-e2`).
