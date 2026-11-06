# Detector reconstruction plan v9.2: run state

```yaml
task_file: hep-research-detector-reconstruction-plan-v9.2-en.md
task_file_sha256: 452b48a52c4d1bba28cabe7089e261030cc2a0d7500dbd7db7859ae72d0de708
base: {ref: origin/main, commit: 580dc79e83abbc33b27c69633d9e15658f4f90b6, plugin_version: 0.56.0, contracts_version: 3.19.0}
branch: feature/detector-reconstruction
private: "<private>, on the group file system with ACLs removed, mode 700 (decisions.md, Q2)"
worktree: <private>/worktree
checkout: <private>/checkout
workdir: "<workdir>, on the group file system, ACLs removed, mode 750 (decisions.md, Q3)"
job_interpreter: {path: <workdir>/env/py313/bin/python, version: 3.13.18, sha256: 32545eb5023762341770737253e9fd8a64e41f993e255561246f50d5c0ff4a53, deviation: "R29 option b"}
plugin_root: plugins/hep-research
main_checkout_t0: {head: 9bd365f0, porcelain_lines: 0}
git_identity: none configured; commits pass -c user.name=Claude -c user.email=noreply@anthropic.com
mode: M1, segmented
open_questions:
  Q1: answered, see decisions.md
  Q2: answered, see decisions.md
  Q3: answered, see decisions.md
  Q4: answered, see decisions.md
  Q5: answered, see decisions.md
  Q6: answered yes
  Q7: answered, see decisions.md
  Q8: answered, see decisions.md
  D1: answered, see decisions.md
  D2: answered, see decisions.md
jobs:
  tiny-1: {state: COMPLETED, exit: "0:0", elapsed: "00:00:51", node: hpa-wn28, result: "interpreter hash matches; core imports pass; no credential-like variable names in job or login environment; root.exe exit 0 with libxxhash from /lib64 on this node", job_id: 7470150, script: "<private>/jobs/tiny/tiny.sh", script_sha256: ea8217e77cd21d79fa67c7fe9d0d4beb29d8164c0cb55610ce08325a91305148, command: "sbatch --parsable <private>/jobs/tiny/tiny.sh", approval: "as suggested, approve the commands, kill the bfs search"}
  baseline-units-1: {state: submitted, job_id: 7470206, script: "<private>/jobs/baseline-units/units.sh", script_sha256: d3d448062ddc63290b166e709a2d81120b58d3050f7f5f694d420f532d7a9b44, command: "sbatch --parsable <private>/jobs/baseline-units/units.sh", approval: "approve the submission"}
baseline_static: {evidence: "<private>/evidence/20261106T044938Z", exit: 0, seconds: 327, note: "run on the login node, --jobs 2, under Q8; docs/dev/detector-reconstruction was present and untracked"}
tasks:
  T01: {state: in-progress, note: "awaiting checkpoint suite (R28); done-provisional for R24; K defaults used: K01 all F01-F38 kept"}
next_action: "T01; read baseline-units-1 receipt when it ends"
```

## Plan conflicts found

- R06 names `find_python.py --json`; the script at the baseline has no such flag and prints JSON by default. Its default search finds no interpreter on this host, so candidates are listed by folder.
- R27 Q1's default, "the newest local commit", would select an unreleased task branch on this host. The baseline was chosen by release instead.
- R09's yes/no/unprobed columns were kept: a coverage draft's `partial` became `no; partly`, the strict reading.
- R03 treats the group space as shared and R27 Q2 places `<private>` in home. The user placed `<private>` on the group file system; it is not shared, because its ACLs were removed (decisions.md, Q2).
