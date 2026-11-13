"""core/calibration/deps (simulator calibration phase 0): hash references, cycle checks, roles derived from usage, and
acyclic version ids (Part B sections 5.2 clause 5, 10.2, 10.3, 10.4; sections 15.3.2, 15.3.17, 15.3a); phase 4:
upstream invalidation and the change of simulation identity (section 10.3) with the T2 carry-over of approval A21
(section 19-g7). Each negative test has a positive control."""
from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import deps  # noqa: E402
from core.canonical import canonical_sha256  # noqa: E402

H = [hashlib.sha256(f"result-{i}".encode()).hexdigest() for i in range(8)]


def codes(findings):
    return sorted(f["code"] for f in findings)


class Roles(unittest.TestCase):
    def test_derivation(self):
        self.assertEqual(deps.derive_role({"envelope"}), "variation")
        self.assertEqual(deps.derive_role({"variation-set", "envelope"}), "variation")
        for u in ("phi-center", "nuisance-posterior", "xi", "fixed-value"):
            self.assertEqual(deps.derive_role({u}), "central")
            self.assertEqual(deps.derive_role({u, "envelope"}), "central")   # both usages: central
        for bad in (set(), {"prior"}):
            with self.assertRaises(ValueError):
                deps.derive_role(bad)

    def test_15_3_2_upstream_rules(self):
        ok = [{"result_sha256": H[0], "usages": ["envelope"]}]
        self.assertEqual(deps.check_upstream_entries(ok), [])
        self.assertEqual(codes(deps.check_upstream_entries([{"result_sha256": H[0], "usages": []}])),
                         ["upstream.usage"])
        # written as variation, but the eta posterior exported by the upstream constrains the downstream
        wrong = [{"result_sha256": H[0], "usages": ["envelope", "nuisance-posterior"], "role": "variation"}]
        self.assertEqual(codes(deps.check_upstream_entries(wrong)), ["upstream.role_mismatch"])
        right = [dict(wrong[0], role="central")]
        self.assertEqual(deps.check_upstream_entries(right), [])

    def test_15_3_17_numbers_instead_of_hashes(self):
        self.assertNotEqual(H[0], H[0].upper())
        for ref in (0.98, "0.98 +- 0.01", "result-A", H[0].upper(), H[0][:40]):
            self.assertEqual(codes(deps.check_upstream_entries([{"result_sha256": ref, "usages": ["xi"]}])),
                             ["upstream.not_hash"], ref)
        dup = [{"result_sha256": H[0], "usages": ["xi"]}, {"result_sha256": H[0], "usages": ["envelope"]}]
        self.assertEqual(codes(deps.check_upstream_entries(dup)), ["upstream.duplicate"])


class Graph(unittest.TestCase):
    def test_cycles_rejected(self):
        self.assertIsNone(deps.find_cycle({H[0]: [H[1]], H[1]: [H[2]], H[2]: []}))
        cyc = deps.find_cycle({H[0]: [H[1]], H[1]: [H[2]], H[2]: [H[0]]})
        self.assertEqual(cyc[0], cyc[-1])
        self.assertEqual(len(cyc), 4)
        self.assertEqual(deps.find_cycle({H[0]: [H[0]]}), [H[0], H[0]])
        with self.assertRaises(deps.DependencyError) as cm:
            deps.check_acyclic({H[0]: [H[1]], H[1]: [H[0]]})
        self.assertEqual(cm.exception.code, "deps.cycle")

    def test_central_closure(self):
        ups = {H[0]: [{"result_sha256": H[1], "usages": ["xi"]}, {"result_sha256": H[2], "usages": ["envelope"]}],
               H[1]: [{"result_sha256": H[3], "usages": ["phi-center"]}],
               H[2]: [{"result_sha256": H[4], "usages": ["xi"]}]}
        self.assertEqual(deps.central_closure(H[0], ups), {H[1], H[3]})   # the variation branch is not in it


class Versions(unittest.TestCase):
    def payload(self, parents=(), **kw):
        p = {"contract_sha256": H[0], "data_sha256": H[1], "plan_sha256": H[2], "engine_version": "0.1.0",
             "parent_versions": list(parents), "values": {"zeta_hat": [0.1, -0.2]}}
        p.update(kw)
        return p

    def test_id_excludes_backfilled_fields(self):
        p = self.payload()
        v = deps.version_id(p)
        self.assertEqual(deps.version_id(dict(p, version_id="x", result_sha256=H[5])), v)
        # a nested field of that name is content (review F7): a different payload, a different version
        self.assertNotEqual(deps.version_id(dict(p, values={"zeta_hat": [0.1, -0.2], "result_sha256": H[6]})), v)
        self.assertNotEqual(deps.version_id(self.payload(values={"zeta_hat": [0.1, -0.3]})), v)  # new payload
        self.assertEqual(deps.version_id(self.payload(parents=[H[3], H[4]])),
                         deps.version_id(self.payload(parents=[H[4], H[3], H[3]])))          # normalized parents

    def test_result_hash_after_version_id(self):
        p = self.payload()
        r = deps.finalize_result({"beta_hat": [1.0]}, p)
        self.assertEqual(r["version_id"], deps.version_id(p))
        again = deps.finalize_result(r, p)                       # rebuilding from the finished result is stable
        self.assertEqual(again, r)
        self.assertEqual(deps.version_id(dict(p, result_sha256=r["result_sha256"])), r["version_id"])

    def test_15_3a_rebuild_in_acyclic_order(self):
        a = self.payload()
        va = deps.version_id(a)
        b = self.payload(parents=[va], values={"z": 1})
        vb = deps.version_id(b)
        c = self.payload(parents=[va, vb], values={"z": 2})
        vc = deps.version_id(c)
        self.assertEqual(deps.rebuild_order({vc: c, vb: b, va: a}), [va, vb, vc])
        with self.assertRaises(deps.DependencyError) as cm:
            deps.rebuild_order({va: a, vb: dict(b, values={"z": 9})})
        self.assertEqual(cm.exception.code, "version.not_reproducible")
        with self.assertRaises(deps.DependencyError):
            deps.update_digest(self.payload(parents=["1.0"]))
        with self.assertRaises(deps.DependencyError):
            deps.update_digest({"values": {}})


# ------------------------------------------------------------------ phase 4: section 10.3 and A21 (section 19-g7)
def result(h, contract=0, grade="validated-in-scope", uses=("diagnostics", "design-study"), own="same",
           waiting=False, upstream=()):
    r = {"result_sha256": h, "contract_sha256": H[contract], "plan_sha256": H[7], "engine_version": "0.66.1",
         "grade": {"own_grade": grade if own == "same" else own, "effective_grade": grade, "uses": list(uses),
                   "flags": []},
         "upstream": [{"result_sha256": u, "usages": list(us)} for u, us in upstream]}
    if waiting:
        r["waiting_records"] = [{"unit": "u1", "kappa": H[6], "seq": 3}]
    return r


class UpstreamInvalidation(unittest.TestCase):
    """Section 10.3: a revised or downgraded upstream marks the downstream for a redo; a re-judgment of the same kappa
    after the records are resolved is not an upstream revision."""

    def setUp(self):
        self.up = result(H[0], waiting=True, own=None)                   # pending inputs: no own grade
        self.down = result(H[1], upstream=[(H[0], ["xi"])])
        self.other = result(H[2], upstream=[(H[5], ["xi"])])             # cites something else: never marked

    def run_(self, successor, *rest):
        return deps.invalidate([self.down, self.other, *rest], [{"old": self.up, "new": successor}])

    def test_revision_marks_the_downstream(self):
        r = self.run_(result(H[3], contract=4))                          # a new kappa: a revision
        self.assertEqual(list(r["redo"]), [H[1]])
        self.assertEqual(r["redo"][H[1]][0]["code"], "upstream.revision")
        self.assertEqual(r["same_kappa"], [])
        self.assertEqual(self.run_(self.up)["redo"], {})                 # control: the same result, no change

    def test_downgrade_marks_the_downstream(self):
        for successor in (result(H[3], contract=4, grade="calibrated-unvalidated"),
                          result(H[3], contract=4, uses=("diagnostics",))):     # a lost use is a downgrade too
            self.assertEqual(self.run_(successor)["redo"][H[1]][0]["code"], "upstream.downgrade")
        up = result(H[3], contract=4, grade="projection")                 # a variation upstream is marked as well
        r = deps.invalidate([result(H[1], upstream=[(H[0], ["envelope"])])], [{"old": self.up, "new": up}])
        self.assertEqual(r["redo"][H[1]][0]["role"], "variation")

    def test_same_kappa_rejudgment_is_not_a_revision(self):
        later = result(H[3])                                              # same kappa, own grade now recorded
        r = self.run_(later)
        self.assertEqual(r["redo"], {})
        self.assertEqual(r["same_kappa"], [{"downstream": H[1], "kappa": deps.kappa(self.up), "earlier": H[0],
                                            "later": H[3]}])
        # negative controls: the same kappa without pending inputs, or a re-judgment that changes the grade
        not_pending = result(H[0])
        r = deps.invalidate([self.down], [{"old": not_pending, "new": later}])
        self.assertEqual(r["redo"][H[1]][0]["code"], "upstream.revision")
        r = self.run_(result(H[3], grade="calibrated-unvalidated"))
        self.assertEqual(r["redo"][H[1]][0]["code"], "upstream.downgrade")

    def test_redo_propagates_down_the_graph(self):
        grand = result(H[4], upstream=[(H[1], ["phi-center"])])
        r = self.run_(result(H[3], contract=4), grand)
        self.assertEqual(sorted(r["redo"]), sorted([H[1], H[4]]))
        self.assertEqual(r["redo"][H[4]], [{"code": "upstream.needs_redo", "upstream": H[1]}])
        r = deps.invalidate([self.down, grand], [], marked=[H[0]])     # e.g. an identity change of the upstream
        self.assertEqual(sorted(r["redo"]), sorted([H[0], H[1], H[4]]))
        self.assertEqual(deps.invalidate([self.down, grand], [])["redo"], {})   # control

    def test_bad_input_is_refused(self):
        for bad in ({"old": self.up, "new": {"result_sha256": "x"}}, {"old": self.up}, "change"):
            with self.subTest(bad=bad), self.assertRaises(deps.DependencyError):
                deps.invalidate([self.down], [bad])
        with self.assertRaises(deps.DependencyError):
            deps.invalidate([dict(self.down, upstream=[{"result_sha256": 0.98, "usages": ["xi"]}])], [])


def ids(build="ab"):
    """Five synthetic identity items of one model (the real masked hashes: test_calibration_model_identity)."""
    return [{"model": "nominal", "identity": {
        "detector_spec": [H[0], None], "simulation_request": H[1], "run_physics": H[2], "response_pipeline": H[3],
        "build_environment": {"build_hash": build * 32, "geant4_version": "11.2.1", "datasets": {"G4EMLOW": "8.5"}}}}]


THETA_HAT, SPOT = {"k_B": 0.126, "LY": 200.0}, [{"k_B": 0.05, "LY": 200.0}, {"k_B": 0.3, "LY": 200.0}]
BASIS = {"theta_hat": THETA_HAT, "spot_checks": SPOT, "observables": ["mean", "width"], "mc_events": 20000,
         "new_build_first_run": "2026-11-20T09:00:00+00:00"}


def t2(shift=0.0, se=0.01, registered="2026-11-19T12:00:00Z", **reg_over):
    """A T2 equivalence record: sigma_tot^design 1.0 and 0.5, margin 0.1 of them; outcome differences `shift`."""
    reg = {"result_sha256": H[5], "old_identities": ids(), "new_identities": ids("cd"),
           "points": [{"label": "theta-hat", "theta": THETA_HAT}, {"label": "kB-low", "theta": SPOT[0]},
                      {"label": "kB-high", "theta": SPOT[1]}],
           "observables": [{"name": "mean", "sigma_tot_design": 1.0}, {"name": "width", "sigma_tot_design": 0.5}],
           "mc_events": 20000, "margin_fraction": 0.1, "alpha": 0.05, "registered_at": registered}
    reg.update(reg_over)
    out = {"registration_sha256": canonical_sha256(reg), "points": [
        {"label": p["label"], "mc_events": {"old": reg["mc_events"], "new": reg["mc_events"]},
         "observables": {o["name"]: {"old": 1.0, "new": 1.0 + shift, "se_old": se, "se_new": se}
                         for o in reg["observables"]}} for p in reg["points"]]}
    return {"schema": deps.T2_SCHEMA, "registration": reg, "outcome": out}


class IdentityChange(unittest.TestCase):
    """Section 10.3 change of simulation identity; A21 (section 19-g7) T2 carry-over (provisional margin)."""

    def setUp(self):
        self.result = {"result_sha256": H[5], "model_identities": ids()}

    def decide(self, record=None, current=None, **basis):
        return deps.identity_decision(self.result, ids("cd") if current is None else current, record,
                                      dict(BASIS, **basis))

    def codes(self, d):
        return sorted({r["code"] for r in d.get("reasons", ())})

    def test_unchanged_identity_is_kept(self):
        d = self.decide(current=ids())
        self.assertEqual((d["decision"], d["changed"]), ("unchanged", {}))

    def test_changed_identity_without_record_is_redone(self):
        d = self.decide()
        self.assertEqual((d["status"], d["decision"], self.codes(d)), ("failed", "redo", ["t2.missing"]))
        self.assertEqual(d["changed"], {"nominal": ["build_environment"]})
        gone = self.decide(current=[])                                     # a model removed: every item changed
        self.assertEqual(gone["changed"], {"nominal": list(deps.model_identity.ITEMS)})

    def test_passing_record_keeps_the_result_flagged(self):
        d = self.decide(t2(shift=0.01))
        self.assertEqual((d["status"], d["decision"]), ("ok", "carried-over"))
        self.assertEqual(d["flags"], ["identity-carried-over", "provisional-thresholds"])
        self.assertEqual(d["model_identities"], ids("cd"))
        self.assertEqual(len(d["tests"]), 3 * 2)                         # every point and observable
        self.assertTrue(all(t["equivalent"] for t in d["tests"]))

    def test_failing_record_redoes(self):
        for shift, se in ((0.06, 0.001), (0.0, 0.05)):                  # a shift beyond the width margin; too noisy
            with self.subTest(shift=shift, se=se):
                d = self.decide(t2(shift=shift, se=se))
                self.assertEqual((d["decision"], self.codes(d)), ("redo", ["t2.not_equivalent"]))
        self.assertEqual(self.decide(t2(shift=0.04, se=0.001))["decision"], "carried-over")   # control: inside

    def test_record_registered_after_the_new_build_ran_redoes(self):
        for when in ("2026-11-20T09:00:00Z", "2026-11-21T00:00:00+01:00"):
            d = self.decide(t2(registered=when))
            self.assertEqual((d["decision"], self.codes(d)), ("redo", ["t2.registered_late"]))
        d = self.decide(t2(), new_build_first_run=None)
        self.assertEqual((d["decision"], self.codes(d)), ("redo", ["t2.order_unknown"]))
        self.assertEqual(self.decide(t2(registered="2026-11-20T08:59:59Z"))["decision"], "carried-over")  # control

    def test_incomplete_or_loosened_record_redoes(self):
        pts = t2()["registration"]["points"]
        cases = {
            "t2.spot_checks": t2(points=pts[:2]),
            "t2.theta_hat": t2(points=[dict(pts[0], theta={"k_B": 0.13, "LY": 200.0})] + pts[1:]),
            "t2.observables": t2(observables=[{"name": "mean", "sigma_tot_design": 1.0}]),
            "t2.mc_size": t2(mc_events=5000),
            "t2.loosened": t2(margin_fraction=0.2),
            "t2.other_result": t2(result_sha256=H[6]),
            "t2.identities": t2(new_identities=ids("ef")),
        }
        for code, rec in cases.items():
            with self.subTest(code):
                self.assertIn(code, self.codes(self.decide(rec)))
        edited = t2()
        edited["registration"]["alpha"] = 0.01                          # tightened after the outcome: unbound
        self.assertEqual(self.codes(self.decide(edited)), ["t2.outcome_unbound"])
        smaller = t2()
        smaller["outcome"]["points"][1]["mc_events"]["new"] = 1000
        self.assertEqual(self.codes(self.decide(smaller)), ["t2.mc_size"])
        dropped = t2()
        del dropped["outcome"]["points"][2]["observables"]["width"]
        self.assertEqual(self.codes(self.decide(dropped)), ["t2.outcome_missing"])
        self.assertEqual(self.decide(t2(se=0.001, margin_fraction=0.05, alpha=0.01))["decision"], "carried-over")  # tightened

    def test_tost(self):
        self.assertTrue(deps.tost(1.0, 1.0, 0.01, 0.01, 0.1)["equivalent"])
        self.assertFalse(deps.tost(1.0, 1.09, 0.01, 0.01, 0.1)["equivalent"])   # 0.09 + 1.645 * 0.0141 > 0.1
        self.assertTrue(deps.tost(1.0, 1.07, 0.01, 0.01, 0.1)["equivalent"])
        self.assertFalse(deps.tost(1.0, 1.0, 0.1, 0.1, 0.1)["equivalent"])     # no power: not shown equivalent
        self.assertTrue(deps.tost(1.0, 1.05, 0.0, 0.0, 0.1)["equivalent"])

    def test_malformed_record_is_refused(self):
        bad = copy.deepcopy(t2())
        del bad["registration"]["registered_at"]
        for rec in ({"schema": "other"}, bad, t2(registered="2026-11-19 12:00")):
            with self.subTest(rec=str(rec)[:40]), self.assertRaises(deps.DependencyError):
                self.decide(rec)


if __name__ == "__main__":
    unittest.main()
