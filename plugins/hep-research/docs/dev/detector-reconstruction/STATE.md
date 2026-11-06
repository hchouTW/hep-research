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
backend_env: {path: <workdir>/env/acts48, package: acts-core 48.2.0, size: 1.4 GB, approval: "approve the install commands", package_list: "<private>/evidence/acts48-explicit.txt"}
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
  baseline-units-1: {state: COMPLETED, slurm_exit: "0:0", suite_exit: 1, elapsed: "00:16:41", node: hpa-wn28, result: "see baseline.md, 2 failing IDs", job_id: 7470206, script: "<private>/jobs/baseline-units/units.sh", script_sha256: d3d448062ddc63290b166e709a2d81120b58d3050f7f5f694d420f532d7a9b44, command: "sbatch --parsable <private>/jobs/baseline-units/units.sh", approval: "approve the submission"}
  checkpoint-p0-1: {state: FAILED, slurm_exit: "1:0", elapsed: "00:17:22", result: "no new failure; 1 baseline error remains, see baseline.md", job_id: 7470679, tested_commit: 1d31ebd3, script: "<private>/jobs/checkpoint-p0/checkpoint.sh", script_sha256: 4f359e1719687390bcc26952cbab0853126ce788d73fcbb47054d0da6a9b08c8, approval: "approve both jobs and the read-only network queries"}
  cvmfs-probe-1: {state: COMPLETED, slurm_exit: "0:0", result: "lcg listed in 2 s; views and releases/acts stalled past 240 s", job_id: 7470680, script: "<private>/jobs/cvmfs-probe/cvmfs.sh", script_sha256: 8b4a0c66e43727b44744b0c67b67b0d753ba8a064dbd87de39a54aec11dec136, approval: "approve both jobs and the read-only network queries"}
  acts-confirm-1: {state: COMPLETED, slurm_exit: "0:0", elapsed: "00:00:27", node: hpa-wn28, result: "5 of 5 checks pass; backend-smoke level only", job_id: 7470886, script: "<private>/jobs/acts-confirm/confirm.sh", script_sha256: 3fe1402c5e0242b4d9cffdd51264f44f478930a039116f278a1d1adce6a091b1, approval: "approve the submission"}
baseline_static: {evidence: "<private>/evidence/20261106T044938Z", exit: 0, seconds: 327, note: "run on the login node, --jobs 2, under Q8; docs/dev/detector-reconstruction was present and untracked"}
tasks:
  T01: {state: done, note: "checkpoint 7470679 compared; K defaults used: K01"}
  T02: {state: done, note: "definitions and contract map; fixtures run in T06; provisional defaults K04, K05, K13"}
  T03: {state: in-progress, note: "done-provisional (R28), awaiting checkpoint suite; t03-selection.md, t07-t09-task-sheets.md; gaps stay recorded"}
  T04: {state: blocked-by-decision, record: blockers/T04.md, draft: t04-prereg.md, deciding: [K09, K12, K16]}
  T05: {state: done, note: "P1 sheets complete, P2 onward list blockers; record t05-task-sheets.md"}
  T11: {state: in-progress, note: "done-provisional (R28), awaiting checkpoint suite; every applicable cell is sourced or a recorded gap (R14); 10 citation uses unread; plugin defects in t11-citation-findings.md not applied"}
k_decisions: {state: drafted, provisional: true, record: decisions.md, contract_map: contract-map.md, needs_user: [K08, K09, K10, K11, K12, K16, K17, K18]}
next_action: "follow finish-plan.md, Phase A; user chooses the execution method"
```

## Plan conflicts found

- R06 names `find_python.py --json`; the script at the baseline has no such flag and prints JSON by default. Its default search finds no interpreter on this host, so candidates are listed by folder.
- R27 Q1's default, "the newest local commit", would select an unreleased task branch on this host. The baseline was chosen by release instead.
- R09's yes/no/unprobed columns were kept: a coverage draft's `partial` became `no; partly`, the strict reading.
- R03 treats the group space as shared and R27 Q2 places `<private>` in home. The user placed `<private>` on the group file system; it is not shared, because its ACLs were removed (decisions.md, Q2).
