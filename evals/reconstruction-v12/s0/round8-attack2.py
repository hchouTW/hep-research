"""Attack a4: draws left in flight are invisible and do not overtake (loaded by path; model.py unchanged)."""
import importlib.util, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("m", os.path.join(HERE, "model.py"))
m = importlib.util.module_from_spec(s); sys.modules["m"] = m; s.loader.exec_module(m)


def a4_in_flight_draws_hide_a_selection():
    log = m.new_log(m.base_steps(), target="T2")
    m.run(log, "a1", "raw", "R1")
    for i in range(3):                       # three variants admitted in parallel (cosmetic content changes)
        m.recontract(log, reco=m.reco_spec(external=(f"p{i}",)))
        m.admit(log, log.head, f"p{i}", "reco")
        log.append("start", "B", attempt=f"p{i}")
    # the Agent has looked at the outputs the three running jobs wrote; it likes variant p1
    m.recontract(log, reco=m.reco_spec(external=("p1",)))       # revert the content to p1 (no output seen yet by C)
    log.append("receipt", "B", attempt="p1", end="success", termination="confirmed", outputs=("X1",))
    m.check(log, "X1", "chkA", "crit1", "pass", "c1")
    st = m.report_status(log, "D")
    p = m.publish(log, log.head, "D")
    return dict(bound=m.bound(log, "reco"), overtaken=m.overtaken(log, "X1"), met=st["met"],
                states={a: m.exec_status(log, a) for a in ("p0", "p1", "p2")},
                report_failed_draws=st["failed_draws"], task_failed_draws=st["task_history"]["failed_draws"],
                publish=dict((k, v) for k, v in p.data if k in ("failed_draws", "chain_artifacts", "prior_failures")))


def a4b_late_finish_after_publish():
    """Same as a4, then the held-back draw finishes after the publish: the publish already stands."""
    log = m.new_log(m.base_steps())
    m.run(log, "a1", "raw", "R1")
    for i in range(2):
        m.recontract(log, reco=m.reco_spec(external=(f"p{i}",)))
        m.admit(log, log.head, f"p{i}", "reco"); log.append("start", "B", attempt=f"p{i}")
    log.append("receipt", "B", attempt="p1", end="success", termination="confirmed", outputs=("X1",))
    m.check(log, "X1", "chkA", "crit1", "pass", "c1")
    p = m.publish(log, log.head, "D")
    return dict(published=p.get("digest"), in_flight=m.exec_status(log, "p0"))


if __name__ == "__main__":
    for f in (a4_in_flight_draws_hide_a_selection, a4b_late_finish_after_publish):
        try:
            print(f.__name__, "->", f())
        except Exception as e:
            print(f.__name__, "-> EXC", type(e).__name__, e)
