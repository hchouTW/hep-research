"""Attack scripts against the v12.1 reference model (asg-1, N1). Run: python3 -I attacks.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import *  # noqa


def a1_cosmetic_revert_rebinds_seen_draw():
    """Spec Control 1.2 'content changes' and 4.2: after several artifacts of a step have been seen, only the newest
    current one binds without a human; a revert needs approval. Attack: instead of reverting pReco_alt -> pReco
    (pending approval, t83), write a cosmetically different program pReco' that deterministically reproduces X1."""
    smp = {"S1": "confirmation", "S2": "confirmation"}
    log = new_log(t3c_steps(), target="T3C", samples=smp)
    log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S1")
    assert contract_status(log, recontract(log, reco=reco_spec(program="pReco_alt"))) == "effective"
    run(log, "a3", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S2")
    assert bound(log, "reco") == "X2"
    cf_revert = recontract(log, reco=reco_spec(program="pReco"))
    print("  literal revert:", contract_status(log, cf_revert))
    cf = recontract(log, reco=reco_spec(program="pReco  # whitespace"))   # cosmetic, same output bytes
    print("  cosmetic revert contract:", contract_status(log, cf))
    run(log, "a4", "reco", "X1")                                           # deterministic: same digest X1
    st = deliverable_status(log, "D")
    print("  bound:", bound(log, "reco"), "achieved:", st["achieved"], "met:", st["met"],
          "accepted(X1):", accepted(log, "X1"))
    p = publish(log, log.head, "D")
    print("  published:", p.get("digest"), p.get("achieved"), "human decisions:", len(log.of("decision")))
    return bound(log, "reco") == "X1" and st["met"] and not log.of("decision")


def a2_upstream_cosmetic_revert_rebinds_downstream():
    """Variant: the deliverable step is never recomputed. raw is unchecked; a cosmetic program of raw reproduces R1, so
    X1 (consumed R1, confirmed on S1) is current and bound again, although X2 was seen and confirmed later."""
    smp = {"S1": "confirmation", "S2": "confirmation"}
    log = new_log(t3c_steps(), target="T3C", samples=smp)
    log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S1")
    recontract(log, raw=StepSpec(program="pRaw2")); run(log, "a3", "raw", "R2")
    run(log, "a4", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S2")
    assert bound(log, "reco") == "X2"
    print("  literal revert of raw:", contract_status(log, recontract(log, raw=StepSpec(program="pRaw"))))
    cf = recontract(log, raw=StepSpec(program="pRaw "))
    print("  cosmetic revert of raw:", contract_status(log, cf))
    run(log, "a5", "raw", "R1")
    st = deliverable_status(log, "D")
    print("  bound(reco):", bound(log, "reco"), "label X2:", label(log, "X2"), "achieved:", st["achieved"])
    p = publish(log, log.head, "D")
    print("  published:", p.get("digest"), p.get("achieved"), "decisions:", len(log.of("decision")))
    return bound(log, "reco") == "X1" and st["met"] and not log.of("decision")


def a3_check_input_held_still_counts():
    """Control 5.2: a non-upstream check input resolves to the bound version or, without one, to the latest current
    artifact; nothing requires it to be ok. A checked reference step whose artifact FAILED its own check is held, so it
    has no bound version, and C resolves to that held artifact; the target's check passes against it and is counted."""
    st = base_steps()
    st["ref"] = StepSpec(program="pRef", checked=True, required=frozenset({("refchk", "rc")}))
    st["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "ref")}))
    log = new_log(st)
    run(log, "a1", "raw", "R1"); run(log, "f1", "ref", "F1")
    check(log, "F1", "refchk", "rc", "fail", "k1")                    # the reference fails its own check
    print("  ref F1 label:", label(log, "F1"), "bound(ref):", bound(log, "ref"))
    run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    print("  check input resolved:", inputs_of(intent_of(log, "c1")))
    print("  X1 label:", label(log, "X1"), "accepted:", accepted(log, "X1"))
    p = publish(log, log.head, "D")
    print("  published", p.get("digest"), p.get("achieved"))
    return accepted(log, "X1")


def a4_check_input_invalidated_still_counts():
    """Same, with an unchecked reference whose version used by the check is later invalidated by a content change."""
    st = base_steps()
    st["ref"] = StepSpec(program="pRefLenient")
    st["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "ref")}))
    log = new_log(st)
    run(log, "a1", "raw", "R1"); run(log, "f1", "ref", "F1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, ref=StepSpec(program="pRefStrict")); run(log, "f2", "ref", "F2")
    print("  F1 label:", label(log, "F1"), "bound(ref):", bound(log, "ref"))
    print("  X1 label:", label(log, "X1"), "accepted:", accepted(log, "X1"))
    return accepted(log, "X1") and label(log, "F1") == "invalidated"


def a5_unknown_check_attempt_side_effect():
    """Control 3: a check attempt's side effect is check x criterion x target. The model keys it on the full identity,
    which includes the resolved check inputs, so a second check attempt is admitted while the first is unknown."""
    st = base_steps()
    st["ref"] = StepSpec(program="pRef")
    st["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "ref")}))
    log = new_log(st)
    run(log, "a1", "raw", "R1"); run(log, "f1", "ref", "F1"); run(log, "a2", "reco", "X1")
    admit(log, log.head, "c1", "__check__", cost=0.0, check=("chkA", "crit1", "X1"))
    log.append("receipt", "B", attempt="c1", end="success", termination="unknown", outputs=())
    recontract(log, ref=StepSpec(program="pRef2")); run(log, "f2", "ref", "F2")
    try:
        admit(log, log.head, "c2", "__check__", cost=0.0, check=("chkA", "crit1", "X1"))
        print("  second check attempt admitted while c1 is unknown:", exec_status(log, "c1"))
        return True
    except Admission as e:
        print("  rejected:", e)
        return False


if __name__ == "__main__":
    for f in (a1_cosmetic_revert_rebinds_seen_draw, a2_upstream_cosmetic_revert_rebinds_downstream,
              a3_check_input_held_still_counts, a4_check_input_invalidated_still_counts,
              a5_unknown_check_attempt_side_effect):
        print(f.__name__)
        try:
            print("  ATTACK SUCCEEDS" if f() else "  attack fails")
        except Exception as e:  # noqa
            print("  attack fails with", type(e).__name__, e)
