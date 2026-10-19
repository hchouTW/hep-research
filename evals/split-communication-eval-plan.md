# Live evals for the hep-communication split

**2026-10-19: round 1 ($74) and description round 1 ($8) fail criteria 3 and 5; the cause of the regressions outside the split was the skills' listing order ($6.60); description round 2 (rename to hep-citations / hep-authoring, $9.30) passes criteria 2, 3, 4, 6, 7 and fails criterion 5 on one case (`wp11-xexp-2`).** The names in the plan text below are the working names of round 1. Results and the per-criterion table are in
`plugins/hep-research/VALIDATION.md`, section SPLIT-LIVE-EVAL; result files are `routing/results/split-*`,
`research_communication/results/split-*` and `behavior/results/split-2026-10-19-*`. The text below is the plan as
prepared.

Prepared on branch `feat/split-communication` (2026-10-19) for the restructuring plan's section 8. Nothing here has
been run: every command below makes paid model calls and needs the maintainer's approval and budget. The plugin
side is offline-checked (`tools/run_all_checks.py --no-cli`, `tools/check_routing_static.py`: 404 cases).

## What changed in the eval inputs

| Eval | Change |
|---|---|
| `evals/routing/` | No file changed. The harness reads `plugins/hep-research/tests/routing/cases.json`, which now holds 404 cases: the 40 that expected hep-communication expect hep-literature (17) or hep-writing (23); `not`, `chain`, `turns` and `also_accept` follow; 10 new cases (`lit-*`, `j13`). The committed baseline `baselines/claude-2.1.293-claude-sonnet-5-5.json` keeps the old names; keep it and write a new baseline after the split run. |
| `evals/research_communication/` | `cases/cases.json` records the skill each of the 11 cases should load: hep-literature for 03, 05, 07, 11 (a source, a citation, a correction notice, a source's status); hep-writing for the other seven. Golden fixtures name hep-writing as producer. Scorer tests updated (16 pass). |
| `evals/behavior/` | `invariants.json` re-registered for both skills (COMM-01, -04, -05, -06 to hep-writing; COMM-02, -03 to hep-literature; new WRITE-01, LIT-01, LIT-02, LIT-04); `coverage` reports no unregistered or stale rule. Cases: `quick-ams-2`, `l2-comm-citation`, `l2-comm-newer-than-ledger` expect hep-literature; `l2-comm-status`, `l2-comm-internal` and the last hop of `l3-response-unfold-report` expect hep-writing; `quick-width-1` and `quick-ams-1` accept hep-literature. New G3 case `l2-write-cite-intro` (drafting with citations: loads hep-literature or marks citations unverified; no INSPIRE-style key typed from memory). Harness tests pass (55). |

## Order and criteria (plan section 8)

Run 1 on `main` (the base, `ee6b8b83`, 0.15.0) and runs 2 to 4 on the branch, with the same CLI version and
model. The branch must not be merged before they pass.

1. **Baseline on main** (criterion 1): every routing case, the research_communication eval, and the publication-record
   questions (`rc-ams-*`, `wp11-bound-bc-*`, `wp11-crdb-*`, `t19-quick-5`).
2. **Routing on the branch** (criteria 2, 5): strict pass rate of the 40 reassigned communication cases plus the new
   `lit-*` cases is not below the baseline's on the same 40; zero regressions in the other six skills' cases and the
   neighbouring cases; `wp11-xexp-3`, `eic-underspec-1` and `t19-turns-3` (plan 6.7) do not get worse.
3. **research_communication on the branch** (criterion 3): short requests that load no skill are at most 2 of 11
   (5 of 11 on 0.10.1; 1 of 11 on `b1f4d8e`).
4. **Behavior on the branch** (criteria 4, 6): the publication-record questions load no skill no more often than in
   run 1; `l2-write-cite-intro` passes WRITE-01 (loads hep-literature first or marks citations unverified).
5. **Always-on cost** (criterion 7): `tools/measure_entrypoints.py` with the CLI, growth at most 150 tokens over main;
   `/context` in a session shows the Skills listing untruncated.

Pass: proceed to the name comparison, then the migration of plan section 9. Fail: adjust descriptions or names and
rerun; after two failed rounds the split is abandoned (plan step 0 stays).

## Commands

```sh
# 1. baseline on main (a checkout of ee6b8b83)
python3 evals/routing/run_routing_eval.py run --model claude-sonnet-5-5 --jobs 4 --budget-usd 35
# writes baselines/claude-<CLI version>-claude-sonnet-5-5.json; the 2.1.293 baseline (old names) stays as it is
python3 evals/routing/run_routing_eval.py baseline evals/routing/results/<run 1>.json
python3 evals/research_communication/run_live_eval.py --model claude-sonnet-5-5 --budget-usd 2
# 2-4. the branch
python3 evals/routing/run_routing_eval.py run --model claude-sonnet-5-5 --jobs 4 --budget-usd 35
python3 evals/routing/run_routing_eval.py compare evals/routing/results/<branch run>.json \
  --baseline evals/routing/baselines/claude-<CLI version>-claude-sonnet-5-5.json
python3 evals/research_communication/run_live_eval.py --model claude-sonnet-5-5 --budget-usd 2
python3 evals/behavior/run.py plan --ids 'l2-comm|l2-write|quick-ams|quick-width-1|l3-response-unfold-report' --cost-per-run 0.15
python3 evals/behavior/run.py run --ids 'l2-comm|l2-write|quick-ams|quick-width-1|l3-response-unfold-report' --budget-usd 5
```

## Cost estimate

| Run | Cases | Basis | Estimate |
|---|---|---|---|
| Routing, full, per checkout | 394 (main) / 404 (branch) | $0.077 per case (2026-10-15, 241 cases, $18.55) | about $30 each, $61 for both |
| research_communication, per checkout | 11 | $0.73 for 11 (2026-10-17) | about $1 each |
| Behavior subset (9 cases, 1 repeat; 3 repeats triple it) | 9 | planner at $0.15 per run | $1.35 per repeat |
| Name comparison (plan 10.2: `hep-sources`/`hep-manuscript` against the working names) | the 63 cases that involve either skill | $0.077 per case | about $5 per name pair |

Total for one round with three behavior repeats: about $70; each name pair compared adds about $5.

## Name comparison (plan 10.2)

`evals/routing/make_name_variant.py` writes a renamed scratch copy of the plugin (skill folders, test folders and every
maintained text file; history files unchanged), runs the static routing check on it, and lists the ids of the cases
that involve either skill. `run_routing_eval.py run` now takes the skill names from the copy given in `--plugin-dir`.

```sh
python3 evals/routing/make_name_variant.py --literature hep-sources --writing hep-manuscript --out /tmp/hep-names-1
python3 evals/routing/run_routing_eval.py run --model claude-sonnet-5-5 --plugin-dir /tmp/hep-names-1 \
  --cases /tmp/hep-names-1/tests/routing/cases.json --ids "$(cat /tmp/hep-names-1/name-variant-ids.txt)" --budget-usd 6
# the same ids on the branch itself give the working-name arm
```

Checked offline on 2026-10-19: the `hep-sources`/`hep-manuscript` copy passes the static check (404 cases), stanzas,
host-neutral paths, ownership, layering, the capability map and the skill-name, link and routing-table tests; 63 cases
involve the two skills. No held-out suite was touched.
