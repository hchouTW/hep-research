#!/bin/bash
# Session 1 of the C2 resumption case: run select, record it; run response, then "lose" the session before its receipt
# is recorded. Uses only the documented CLI of control_layer.py and run_workflow.py.
set -euo pipefail
P=$1; S=$2; PROJ=$3
mkdir -p $PROJ/data $PROJ/code $PROJ/caps $PROJ/runs $PROJ/receipts
cd $PROJ
$P - <<'PY'
import csv, numpy as np
rng = np.random.default_rng(20261030)
n = 50_000
e = rng.uniform(10, 100, n)
reco = 0.95 * e * (1 + rng.normal(0, 1, n) * 0.10 / np.sqrt(e))
bad = rng.random(n) < 0.01
reco[bad] = -999.0
with open("data/calo.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["event", "e_true_gev", "e_reco_gev"])
    for i in range(n):
        w.writerow([i, f"{e[i]:.5f}", f"{reco[i]:.5f}"])
PY
cat > code/select.py <<'PY'
import csv
rows = [r for r in csv.DictReader(open("calo.csv")) if float(r["e_reco_gev"]) > 0]
with open("selected.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["event", "e_true_gev", "e_reco_gev"]); w.writeheader(); w.writerows(rows)
PY
cat > code/response.py <<'PY'
import csv, json
rows = [r for r in csv.DictReader(open("selected.csv")) if int(r["event"]) % 2 == 0]   # half A: derive
ratio = [float(r["e_reco_gev"]) / float(r["e_true_gev"]) for r in rows]
mean = sum(ratio) / len(ratio)
sd = (sum((x - mean) ** 2 for x in ratio) / (len(ratio) - 1)) ** 0.5
json.dump({"response": mean, "stat_unc": sd / len(ratio) ** 0.5, "n": len(ratio)}, open("response.json", "w"))
PY
cat > code/closure_check.py <<'PY'
import csv, json, sys
crit = json.load(open("closure_criteria.json"))
resp = json.load(open("response.json"))["response"]
rows = [r for r in csv.DictReader(open("selected.csv")) if int(r["event"]) % 2 == 1]   # half B: closure
corr = sum(float(r["e_reco_gev"]) / resp / resp / float(r["e_true_gev"]) for r in rows) / len(rows)
res = "pass" if abs(corr - 1.0) < crit["tolerance"] else "fail"
json.dump({"check_digest": sys.argv[1], "criterion_digest": sys.argv[2], "target_artifact_digest": sys.argv[3],
           "result": res, "reason": f"corrected mean on half B {corr:.5f}, |x-1| vs {crit['tolerance']}",
           "samples": []}, open("closure_result.json", "w"))
PY
echo '{"tolerance": 0.005}' > code/closure_criteria.json
sha() { sha256sum "$1" | cut -d' ' -f1; }
$P $S/executor_capabilities.py qualify --out caps/qual.json > /dev/null
$P $S/executor_capabilities.py declare --qualification caps/qual.json --out caps/decl.json > /dev/null
TL=hep-research-artifacts/calo-response/task-log/task-log.jsonl
mkdir -p $(dirname $TL)
cat > contract.json <<JS
{"steps": {"select": {"program": "$(sha code/select.py)", "environment": "python3.13+numpy"},
           "response": {"program": "$(sha code/response.py)", "environment": "python3.13+numpy", "upstream": ["select"],
                        "checked": true, "required_checks": [["$(sha code/closure_check.py)", "$(sha code/closure_criteria.json)"]]}},
 "deliverables": {"D": {"step": "response", "target": "T2", "required": true}},
 "families": {}, "samples": {}, "budget": null}
JS
CL="$P $S/control_layer.py"
head_of() { $P -c "import json,sys;print(json.load(sys.stdin)['head'])"; }
$CL init --task-log $TL --mode M1 > /dev/null
H=$($CL status --task-log $TL | head_of); $CL contract --task-log $TL --file contract.json --expect-head $H > /dev/null
CAPS="--declaration caps/decl.json --qualification caps/qual.json"
# select
H=$($CL status --task-log $TL | head_of); $CL admit --task-log $TL --attempt s1/select --step select --cost 1 $CAPS --expect-head $H > /dev/null
mkdir -p runs/s1-select && cp data/calo.csv code/select.py runs/s1-select/
cat > runs/wf-select.json <<'JS'
{"workflow": "calo-select", "steps": [{"id": "select", "argv": ["{python}", "select.py"], "inputs": ["calo.csv", "select.py"], "outputs": ["selected.csv"]}]}
JS
$P $S/run_workflow.py runs/wf-select.json --work runs/s1-select --receipt-dir receipts --attempt-prefix s1/ > /dev/null
H=$($CL status --task-log $TL | head_of); $CL receipt --task-log $TL --receipt receipts/s1/select.receipt.json --work runs/s1-select --expect-head $H > /dev/null
# response: admitted and run, but the session ends before its receipt is recorded
H=$($CL status --task-log $TL | head_of); $CL admit --task-log $TL --attempt s1/response --step response --cost 1 $CAPS --expect-head $H > /dev/null
mkdir -p runs/s1-response && cp runs/s1-select/selected.csv code/response.py runs/s1-response/
cat > runs/wf-response.json <<'JS'
{"workflow": "calo-response", "steps": [{"id": "response", "argv": ["{python}", "response.py"], "inputs": ["selected.csv", "response.py"], "outputs": ["response.json"]}]}
JS
$P $S/run_workflow.py runs/wf-response.json --work runs/s1-response --receipt-dir receipts --attempt-prefix s1/ > /dev/null
H=$($CL status --task-log $TL | head_of); $CL receipt --task-log $TL --receipt receipts/s1/response.receipt.json --work runs/s1-response --expect-head $H > /dev/null; $CL status --task-log $TL | head -3
