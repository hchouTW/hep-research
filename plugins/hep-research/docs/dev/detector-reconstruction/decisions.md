# Detector reconstruction plan v9.2: decisions

User's answer, 2026-11-06, verbatim: "Q2, Q3, please choose ceph space. Q6 yes, Q7 try with best setting. other questions, please give me suggestion."

Earlier, 2026-11-06, verbatim: "choose best version for this task"; "go ahead with the R27 first reply".

| ID | Decision | Basis |
| --- | --- | --- |
| Q1 | Baseline `580dc79e` (plugin 0.56.0, contracts 3.19.0), by clone without network | Latest release; differs from the tag only by a custodian record |
| Q2 | `<private>` is a dedicated folder on the group file system, ACLs removed, mode 700 | User chose ceph. The parent's default ACLs would have shared a plain folder, so they were removed and the result checked with `getfacl` |
| Q3 | `<workdir>` is a separate folder in the group space; not yet created. Every write there is asked each time (R03) | User chose ceph |
| Q6 | Tiny confirmation job: yes, as the first job, after Q4 and Q5 | User |
| Q7 | Delegated to the agent ("try with best setting"). Tiny job: account ams, `edr2-al9_short_serial`, no QoS, 1 CPU, 2000 MB, 10 min. Unit-suite job: same partition, 6 CPUs, default memory per CPU, 2 h. Re-checked live before each submission | Partition on a node set the running g4sim array does not use; unit-suite size from the recorded 25 min at `--jobs 6` |
| Q4 | Option (b): environment `<workdir>/env/py313`, built from `requirements-ci.lock`, recorded as a deviation; also ask the site for Python >= 3.13 (option a) | Agent's suggestion, accepted by the user |
| Q5 | Yes: this account counts as a disposable test environment for agent-written jobs, on synthetic data only, each job approved by SHA-256. Known exposure: SSH key and GitHub token are reachable from any job | Agent's suggestion, accepted by the user |
| Q8 | Login node allowed: `freeze`, `verify-bundle`, dry-run `submit`/`resubmit`, `report`; short single test modules; `run_all_checks.py --part static` with `--jobs 2`. Not allowed for now: `executor_capabilities.py qualify` | Agent's suggestion, accepted by the user |
| D1 | Re-baseline onto 0.57.0 before T06, once it is released | Agent's suggestion, accepted by the user |
| D2 | Reconstruction defines conditions and alignment payloads and reuses g4sim's `geometry_id`; if g4sim S9 is triggered it uses those payloads, which changes a g4sim card and needs the user's approval then | Agent's suggestion, accepted by the user |

User's answer, 2026-11-06, verbatim: "as suggested, approve the commands, kill the bfs search". The approval covers the five commands listed in that reply, and no others.
