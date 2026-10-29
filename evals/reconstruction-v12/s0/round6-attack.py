import importlib.util, sys
from dataclasses import replace
spec_ = importlib.util.spec_from_file_location("m", sys.argv[1]); m = importlib.util.module_from_spec(spec_)
sys.modules["m"] = m; spec_.loader.exec_module(m)
from m import *

print("=== Attack A: peek draw made unattested by under-declared cost, then reproduced by a cosmetic change")
smp = {"S1": "confirmation", "S2": "confirmation"}
log = new_log(t3c_steps(), target="T3C", samples=smp)
log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
run(log, "a1", "raw", "R1")
admit(log, log.head, "a2", "reco", cost=0.0)              # agent declares cost 0 -> usage 0.5 makes it unattested
log.append("start", "B", attempt="a2")
log.append("receipt", "B", attempt="a2", end="success", termination="confirmed", outputs=("X1",), usage=0.5)
print(" X1 after peek: usable", usable(log, "X1"), "label", label(log, "X1"), "unchecked_artifacts", unchecked_artifacts(log, "reco"))
cf = recontract(log, reco=reco_spec(program="pReco_alt")); print(" content change:", contract_status(log, cf))
run(log, "a3", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S2")
print(" X2 confirmed:", deliverable_status(log, "D"))
cf = recontract(log, reco=reco_spec(program="pReco")); print(" direct revert to pReco:", contract_status(log, cf), "(revives sees unattested a2)")
cf = recontract(log, reco=reco_spec(program="pReco ")); print(" cosmetic change:", contract_status(log, cf))
run(log, "a4", "reco", "X1")                               # reproduces the peeked digest
print(" reproduced(X1):", reproduced(log, "X1"), "label", label(log, "X1"))
check(log, "X1", "chkA", "crit1", "pass", "c4", sample="S1")
print(" status:", deliverable_status(log, "D"))
p = publish(log, log.head, "D")
print(" PUBLISHED:", dict(p.data))

print("=== Attack B: a step removed by an approved contract is re-added by the agent with an old program (revert not detected)")
st = base_steps()
st["alt"] = StepSpec(program="pAlt1", upstream=("raw",), checked=True, required=C1)
log = new_log(st)
run(log, "a1", "raw", "R1")
run(log, "b1", "alt", "A1"); check(log, "A1", "chkA", "crit1", "pass", "k1")
recontract(log, alt=replace(st["alt"], program="pAlt2"))
run(log, "b2", "alt", "A2"); check(log, "A2", "chkA", "crit1", "pass", "k2")
print(" bound(alt) before removal:", bound(log, "alt"))
c = contract(log); steps = {k: v for k, v in c["steps"].items() if k != "alt"}
cf = log.append("contract", "agent", spec=spec(steps, dict(c["deliverables"]), {}, {}, None))
print(" removal:", contract_status(log, cf)); approve(log, cf); print(" after approval:", contract_status(log, cf))
c = contract(log); steps = dict(c["steps"]); steps["alt"] = st["alt"]          # program pAlt1 again = revert of A2
dels = dict(c["deliverables"]); dels["D2"] = Deliverable("alt", "T2")
cf = log.append("contract", "agent", spec=spec(steps, dels, {}, {}, None))
print(" re-add with pAlt1 (no human):", contract_status(log, cf))
print(" bound(alt):", bound(log, "alt"), "label A2:", label(log, "A2"), "status D2:", deliverable_status(log, "D2"))
p = publish(log, log.head, "D2"); print(" PUBLISHED:", dict(p.data)["deliverable"], dict(p.data)["digest"])
# variant: re-add with a pin to A1 under program pAlt2
log2 = new_log(st)
run(log2, "a1", "raw", "R1")
run(log2, "b1", "alt", "A1"); check(log2, "A1", "chkA", "crit1", "pass", "k1")
recontract(log2, alt=replace(st["alt"], program="pAlt2"))
run(log2, "b2", "alt", "A2"); check(log2, "A2", "chkA", "crit1", "pass", "k2")
c = contract(log2); steps = {k: v for k, v in c["steps"].items() if k != "alt"}
cf = log2.append("contract", "agent", spec=spec(steps, dict(c["deliverables"]), {}, {}, None)); approve(log2, cf)
c = contract(log2); steps = dict(c["steps"]); steps["alt"] = replace(st["alt"], program="pAlt1", pin="A1")
dels = dict(c["deliverables"]); dels["D2"] = Deliverable("alt", "T2")
cf = log2.append("contract", "agent", spec=spec(steps, dels, {}, {}, None))
print(" pin variant re-add:", contract_status(log2, cf), "bound", bound(log2, "alt"))
