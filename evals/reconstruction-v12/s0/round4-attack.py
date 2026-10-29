import importlib.util, sys, os
here = os.path.dirname(os.path.abspath(__file__))
spec_ = importlib.util.spec_from_file_location("model", os.path.join(here, "model.py"))
m = importlib.util.module_from_spec(spec_); sys.modules["model"] = m; spec_.loader.exec_module(m)
from model import *  # noqa

print("=== A1: confirmation shopping across two samples, then revert the program (content change) to pick ===")
log = new_log(t3c_steps(), target="T3C", samples={"S1": "confirmation", "S2": "confirmation", "CR": "control"})
log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")                 # program pReco
check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S1")               # look at X1 on S1
print("X1 after S1:", deliverable_status(log, "D"))
recontract(log, reco=reco_spec(program="pReco_alt"))                       # content change: automatic
run(log, "a3", "reco", "X2")                                               # allowed: X1 has a counted result
check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S2")               # look at X2 on S2
print("X2 after S2:", deliverable_status(log, "D"))
# both confirmation results seen; agent prefers X1's number -> revert the program (content change, automatic)
cf = recontract(log, reco=reco_spec(program="pReco"))
print("revert contract status:", contract_status(log, cf))
print("labels X1/X2:", label(log, "X1"), label(log, "X2"))
st = deliverable_status(log, "D"); print("D:", st)
p = publish(log, log.head, "D")
print("published:", dict(p.data))
print("report prior_failures:", report_status(log, "D")["prior_failures"])

print("\n=== A1b: same, picking X2 instead (no revert) also T3C; agent chose after seeing both ===")
log2 = new_log(t3c_steps(), target="T3C", samples={"S1": "confirmation", "S2": "confirmation"})
log2.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
run(log2, "a1", "raw", "R1"); run(log2, "a2", "reco", "X1")
check(log2, "X1", "chkA", "crit1", "pass", "c1", sample="S1")
recontract(log2, reco=reco_spec(program="pReco_alt"))
run(log2, "a3", "reco", "X2")
check(log2, "X2", "chkA", "crit1", "pass", "c2", sample="S2")
print("D (X2 bound):", deliverable_status(log2, "D"))

def check_u(log, target, chk, crit, result, attempt, sample=None):
    admit(log, log.head, attempt, "__check__", cost=1.0, reads=(sample,) if sample else (), check=(chk, crit, target))
    log.append("receipt", "B", attempt=attempt, end="success", termination="confirmed", outputs=(), usage=0.5)
    log.append("check_result", "B", target=target, check=chk, criteria=crit, result=result, check_attempt=attempt, sample=sample)

print("\n=== A2: M2, human confirms first contract with T2 deliverable on a step with confirmation_required=False;"
      " agent later adds a T3C deliverable on that step (automatic) ===")
log = new_log(t3c_steps(confirmation_required=False), target="T2", samples={"S": "confirmation", "CR": "control"},
              mode="M2")
approve(log, log.of("contract")[0])
dels = {"D": Deliverable("reco", "T2"), "D2": Deliverable("reco", "T3C")}
cf = recontract(log, deliverables=dels)
print("added-T3C contract status:", contract_status(log, cf))
log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
run(log, "a1", "raw", "R1", usage=0.5); run(log, "a2", "reco", "X1", usage=0.5)
check_u(log, "X1", "chkA", "crit1", "pass", "c1", sample="CR")              # control sample only; S never read
print("D2:", deliverable_status(log, "D2"), "accepted:", accepted(log, "X1"))
p = publish(log, log.head, "D2"); print("published:", dict(p.data))

print("\n=== A2b: same for independent confirmation (default no): later T3C deliverable on data needs no method-independent pass ===")
log = new_log(t3c_steps(), target="T2", samples={"S": "confirmation"}, mode="M2")
approve(log, log.of("contract")[0])
cf = recontract(log, deliverables={"D": Deliverable("reco", "T2"), "D2": Deliverable("reco", "T3C")})
print("status:", contract_status(log, cf))
log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
run(log, "a1", "raw", "R1", usage=0.5); run(log, "a2", "reco", "X1", usage=0.5)
check_u(log, "X1", "chkA", "crit1", "pass", "c1", sample="S")
print("D2:", deliverable_status(log, "D2"))

print("\n=== A3: agent-written exposure attributed to an admitted check attempt of the artifact ===")
log = new_log(t3c_steps(required=frozenset({("chkA", "crit1"), ("chkB", "crit2")})), target="T3C",
              samples={"S": "confirmation"})
req = frozenset({("chkA", "crit1"), ("chkB", "crit2")})
log.append("freeze", "agent", step="reco", samples=("S",), required=req)
run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S")
log.append("exposure", "agent", sample="S", attempt="c1")                 # an ad-hoc look at S, labelled as c1
check(log, "X1", "chkB", "crit2", "pass", "c2", sample="S")
print("D:", deliverable_status(log, "D"))
log = new_log(t3c_steps(required=req), target="T3C", samples={"S": "confirmation"})
log.append("freeze", "agent", step="reco", samples=("S",), required=req)
run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S")
log.append("exposure", "agent", sample="S", attempt="adhoc-look")         # honest label
check(log, "X1", "chkB", "crit2", "pass", "c2", sample="S")
print("D (honest label):", deliverable_status(log, "D"))

print("\n=== A4: unchecked side step that runs the check logic as a computation; draws invisible in task history ===")
log = new_log(base_steps(), samples={"CR": "control"})
run(log, "a1", "raw", "R1")
recontract(log, side=StepSpec(program="pVariant0", upstream=("raw",)))
for i in range(5):
    recontract(log, side=StepSpec(program=f"pVariant{i}", upstream=("raw",)))
    run(log, f"s{i}", "side", f"SV{i}", reads=("CR",))
recontract(log, sidecheck=StepSpec(program="pChkA-as-computation", upstream=("side",)))
run(log, "sc", "sidecheck", "SC")
recontract(log, reco=reco_spec(program="pReco_variant3"))                 # adopt the chosen variant
run(log, "a2", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "c1", sample="CR")
p = publish(log, log.head, "D")
print("published:", dict(p.data))
print("task_history:", task_history(log))
