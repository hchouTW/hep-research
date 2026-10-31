import importlib.util, sys
spec_ = importlib.util.spec_from_file_location("m", sys.argv[1]); m = importlib.util.module_from_spec(spec_)
sys.modules["m"] = m; spec_.loader.exec_module(m)
from m import *
print("=== Check C: a required check attempt of this artifact reads S1 but ends in execution failure; rerun passes")
log = new_log(t3c_steps(), target="T3C", samples={"S1": "confirmation"})
log.append("freeze", "agent", step="reco", samples=("S1",), required=C1)
run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
admit(log, log.head, "c1", "__check__", cost=0.0, reads=("S1",), check=("chkA", "crit1", "X1"))
log.append("receipt", "B", attempt="c1", end="failure", termination="confirmed", outputs=())
check(log, "X1", "chkA", "crit1", "pass", "c2", sample="S1")
print(" checks ok:", checks_state(log, "X1"), "freeze_ok:", freeze_ok(log, "X1"), "status:", deliverable_status(log, "D"))
