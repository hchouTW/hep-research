"""core/calibration/deps (simulator calibration phase 0): hash references, cycle checks, roles derived from usage, and
acyclic version ids (Part B sections 5.2 clause 5, 10.2, 10.3, 10.4; sections 15.3.2, 15.3.17, 15.3a)."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import deps  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
