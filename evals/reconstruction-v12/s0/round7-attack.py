import importlib.util, os, sys
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("m", os.path.join(here, "model.py"))
m = importlib.util.module_from_spec(sp); sys.modules["m"] = m; sp.loader.exec_module(m)

def setup():
    log = m.new_log(m.base_steps())
    m.run(log, "a1", "raw", "R1"); m.run(log, "a2", "reco", "X1")
    m.check(log, "X1", "chkA", "crit1", "pass", "c1")
    return log

# A1: draw left unknown (output seen out of band), then revert program -> old draw binds without a pin
log = setup()
m.recontract(log, reco=m.reco_spec(program="pReco_v2"))
m.admit(log, log.head, "a3", "reco"); log.append("start", "B", attempt="a3")
log.append("receipt", "B", attempt="a3", end="success", termination="unknown", outputs=())
m.recontract(log, reco=m.reco_spec(program="pReco"))     # revert (content change, auto-effective)
print("A1 unknown: exec a3 =", m.exec_status(log, "a3"), "label X1 =", m.label(log, "X1"),
      "met =", m.deliverable_status(log, "D")["met"])
p = m.publish(log, log.head, "D")
print("A1 published:", p.get("digest"), "failed_draws", p.get("failed_draws"))

# A2: same, abandoned by a human and later reconciled with the output digest recorded
log = setup()
m.recontract(log, reco=m.reco_spec(program="pReco_v2"))
m.admit(log, log.head, "a3", "reco"); log.append("start", "B", attempt="a3")
log.append("receipt", "B", attempt="a3", end="success", termination="unknown", outputs=())
log.append("decision", "human", action="abandon", attempt="a3")
log.append("reconcile", "B", attempt="a3", end="success", termination="confirmed", outputs=("Y",))
print("A2 Y in candidates_raw:", "Y" in m.candidates_raw(log, "reco"))
m.recontract(log, reco=m.reco_spec(program="pReco"))
print("A2 abandoned+reconciled: label X1 =", m.label(log, "X1"), "overtaken =", m.overtaken(log, "X1"),
      "met =", m.deliverable_status(log, "D")["met"])
p = m.publish(log, log.head, "D")
print("A2 published:", p.get("digest"))
# control: same with a confirmed receipt -> overtaken
log = setup()
m.recontract(log, reco=m.reco_spec(program="pReco_v2"))
m.run(log, "a3", "reco", "Y"); m.check(log, "Y", "chkA", "crit1", "pass", "c3")
m.recontract(log, reco=m.reco_spec(program="pReco"))
print("control (confirmed Y): label X1 =", m.label(log, "X1"))

# B1: confirmation check attempt aborted after its result was seen -> no result, retry on another sample
smp = {"S1": "confirmation", "S2": "confirmation", "S3": "confirmation"}
log = m.new_log(m.t3c_steps(), target="T3C", samples=smp)
log.append("freeze", "agent", step="reco", samples=("S1", "S2", "S3"), required=m.C1)
m.run(log, "a1", "raw", "R1"); m.run(log, "a2", "reco", "X1")
for att, s in (("c1", "S1"), ("c2", "S2")):
    m.admit(log, log.head, att, "__check__", cost=0.0, reads=(s,), check=("chkA", "crit1", "X1"))
    log.append("start", "B", attempt=att)
    log.append("receipt", "B", attempt=att, end="failure", termination="confirmed", outputs=())
m.check(log, "X1", "chkA", "crit1", "pass", "c3", sample="S3")
st = m.report_status(log, "D")
print("B1 achieved", st["achieved"], "met", st["met"], "failed_draws", st["failed_draws"],
      "conf_results", st["confirmation_results"], "task failed draws", st["task_history"]["failed_draws"])
p = m.publish(log, log.head, "D")
print("B1 published:", {k: p.get(k) for k in ("digest", "achieved", "prior_failures", "failed_draws", "confirmation_results")})

# B2: non-confirmation, non-deterministic check: aborted attempt then rerun of the same check identity
log = setup.__wrapped__() if hasattr(setup, "__wrapped__") else None
log = m.new_log(m.base_steps())
m.run(log, "a1", "raw", "R1"); m.run(log, "a2", "reco", "X1")
m.admit(log, log.head, "c1", "__check__", cost=0.0, check=("chkA", "crit1", "X1"))
log.append("start", "B", attempt="c1")
m.admit(log, log.head, "cx", "__check__", cost=0.0, check=("chkA", "crit1", "X1")) if False else None
log.append("cancel_request", "C", attempt="c1")
log.append("receipt", "B", attempt="c1", end="cancelled", termination="confirmed", outputs=())
m.check(log, "X1", "chkA", "crit1", "pass", "c2")
p = m.publish(log, log.head, "D")
print("B2 published after cancelled same-identity check:", p.get("digest"), "failed_draws", p.get("failed_draws"))
