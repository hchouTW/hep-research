"""Attack scripts against the v12.2 reference model (loaded by path; model.py is not modified)."""
import importlib.util, sys, os
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
spec_ = importlib.util.spec_from_file_location("m", os.path.join(HERE, "model.py"))
m = importlib.util.module_from_spec(spec_)
sys.modules["m"] = m
spec_.loader.exec_module(m)


def a1_empty_output_draws_are_invisible():
    """Draws of the checked deliverable step that end 'success, confirmed, no outputs' are neither failed draws nor
    artifacts; each is a fresh content change, so check-before-recompute and the same-identity rule do not stop them."""
    log = m.new_log(m.base_steps())
    m.run(log, "a1", "raw", "R1")
    for i in range(4):                                   # four discarded draws, each a cosmetic content change
        m.recontract(log, reco=m.reco_spec(external=(f"note-{i}",)))
        m.admit(log, log.head, f"d{i}", "reco")
        log.append("start", "B", attempt=f"d{i}")
        log.append("receipt", "B", attempt=f"d{i}", end="success", termination="confirmed", outputs=())
        assert m.exec_status(log, f"d{i}") == "computed" and m.attested(log, f"d{i}")
    m.recontract(log, reco=m.reco_spec(external=("final",)))
    m.run(log, "a2", "reco", "X1")
    m.check(log, "X1", "chkA", "crit1", "pass", "c1")
    st = m.report_status(log, "D")
    p = m.publish(log, log.head, "D")
    th = st["task_history"]
    return dict(met=st["met"], failed_draws_report=len(st["failed_draws"]),
                task_failed_draws=len(th["failed_draws"]),
                publish_failed_draws=p.get("failed_draws"), publish_chain_artifacts=p.get("chain_artifacts"),
                reco_intents=len(m.step_intents(log, "reco")))


def a2_check_input_step_killed_draws_absent_from_publish():
    """A check input on an unchecked side step 'ref': disliked reference draws are turned into execution failures
    (kill after peek). They are off the deliverable's chain (chain = upstreams only) and publish carries no task-wide
    failed draws, so the published record shows none of them."""
    st = m.base_steps()
    st["ref"] = m.StepSpec(program="pRef")
    st["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "ref")}))
    log = m.new_log(st)
    m.run(log, "a1", "raw", "R1"); m.run(log, "a2", "reco", "X1")
    for i in range(5):                                   # five reference draws peeked at and killed
        m.recontract(log, ref=m.StepSpec(program="pRef", external=(f"v{i}",)))
        m.run(log, f"f{i}", "ref", f"F{i}", end="failure")
    m.recontract(log, ref=m.StepSpec(program="pRef", external=("kept",)))
    m.run(log, "f9", "ref", "FK")
    m.check(log, "X1", "chkA", "crit1", "pass", "c1")
    rs = m.report_status(log, "D")
    p = m.publish(log, log.head, "D")
    return dict(met=rs["met"], chain=m.chain_steps(log, "reco"), chain_failed_draws=len(rs["failed_draws"]),
                task_failed_draws=len(rs["task_history"]["failed_draws"]),
                publish_fields=sorted(k for k, _ in p.data))


def a3_parallel_draws_escape_check_before_recompute():
    """Several cosmetic variants admitted while the earlier ones are still in flight: check-before-recompute looks only
    at artifacts already produced, so draws X2 and X3 are never checked; only the last finisher binds."""
    log = m.new_log(m.base_steps())
    m.run(log, "a1", "raw", "R1")
    for i in range(3):
        m.recontract(log, reco=m.reco_spec(external=(f"p{i}",)))
        m.admit(log, log.head, f"p{i}", "reco")
    for i, out in ((0, "X2"), (1, "X3"), (2, "X4")):
        log.append("receipt", "B", attempt=f"p{i}", end="success", termination="confirmed", outputs=(out,))
    m.check(log, "X4", "chkA", "crit1", "pass", "c1")
    p = m.publish(log, log.head, "D")
    unchecked = [d for d in ("X2", "X3") if not m.counted_result(log, d, "chkA", "crit1")]
    return dict(published=p.get("digest"), unchecked_draws=unchecked, chain_artifacts=p.get("chain_artifacts"),
                prior_failures=p.get("prior_failures"))


if __name__ == "__main__":
    for f in (a1_empty_output_draws_are_invisible, a2_check_input_step_killed_draws_absent_from_publish,
              a3_parallel_draws_escape_check_before_recompute):
        try:
            print(f.__name__, "->", f())
        except Exception as e:
            print(f.__name__, "-> EXC", type(e).__name__, e)
