"""core/provider (cr-provider/1, cosmic-ray propagation plan r3 C1): acceptance C1-1 to C1-6 on synthetic providers
written into a temporary folder, the protocol rules against contracts/schemas/cr_provider.json, and the command
lines. The closed-form provider of the cr-secondary-ratio profile has its own conformance test in that profile."""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.recipe_semantics import canonical_sha256 as contracts_sha256  # noqa: E402
from contracts.schema import validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.provider import hashing, protocol  # noqa: E402
from core.provider.conformance import comparable_hash, run_conformance  # noqa: E402
from core.provider.entrypoint import respond  # noqa: E402
from core.provider.registry import REGISTRY_FORMAT, RegistryError, parse_registry  # noqa: E402
from core.provider.runner import ProviderRunner  # noqa: E402

DECLARATION = {"id": "toy-linear", "entrypoint": "toy_provider.py", "protocol": "cr-provider/1", "version": "1.0.0",
               "domain": {"D0_cm2_s": {"min": 1e27, "max": 1e30}, "L_kpc": {"min": 1.0, "max": 20.0}},
               "axis_ranges": {"rigidity": {"min": 1.0, "max": 1000.0}},
               "observables": ["B/C"], "axes": ["rigidity"], "decomposable": True, "deterministic": True,
               "output_units": {"ratio": "1", "energy": "GV"}}

# A synthetic provider: B/C = (D0/1e28) / L * (bin centre)^-0.5 split into two channels 0.6 + 0.4. MODE selects a
# failure: "ok", "crash" (exits 7 before answering), "garbage" (writes a non-protocol response), "raise" (an exception
# in the evaluation), "print" (prints to stdout while evaluating, which must not reach --serve's channel).
TOY = textwrap.dedent('''\
    import json, sys
    sys.path.insert(0, {root!r})
    from pathlib import Path
    from core.provider.entrypoint import provider_main
    MODE = {mode!r}
    DECL = {decl!r}
    CALLS = Path(__file__).with_suffix(".calls")

    def evaluate_point(request, point, context):
        with open(CALLS, "a") as fh:
            fh.write("1\\n")
        if MODE == "raise":
            raise RuntimeError("synthetic failure in the closed form")
        if MODE == "print":
            print("chatter on stdout")
        preds, comps = [], []
        for obs in request["observables"]:
            edges = [obs["bins"][0][0]] + [hi for _, hi in obs["bins"]]
            vals = [point.get("D0_cm2_s", 3e28) / 1e28 / point.get("L_kpc", 4.0) * (0.5 * (lo + hi)) ** -0.5
                    for lo, hi in obs["bins"]]
            preds.append({{"observable": {{"quantity": "ratio", "variables": [{{"name": "rigidity", "unit": "GV",
                          "edges": edges}}], "level": "top-of-instrument", "normalization": {{"kind": "exposure",
                          "value": "not-applicable"}}, "bin_semantics": "bin-averaged", "unit": "1"}},
                          "parameter_point": dict(point), "representation": "numerical",
                          "values": {{"edges": edges, "values": vals, "unit": "1"}}, "uncertainties": [],
                          "allowed_transformations": []}})
            comps += [{{"observable": obs["id"], "id": "C->B", "kind": "channel", "values": [0.6 * v for v in vals],
                       "unit": "1"}}, {{"observable": obs["id"], "id": "O->B", "kind": "channel",
                       "values": [0.4 * v for v in vals], "unit": "1"}}]
        out = {{"labels": ["synthetic"], "numerical_tolerance": 1e-12, "computational_run_ref": None}}
        if "lis" in context["want"]:
            out["predictions"] = preds
        if "components" in context["want"]:
            out["components"] = comps
        return out

    if __name__ == "__main__":
        if MODE == "crash":
            sys.stderr.write("synthetic crash: segmentation fault in the solver\\n")
            sys.exit(7)
        if MODE == "garbage" and "--response" in sys.argv:
            Path(sys.argv[sys.argv.index("--response") + 1]).write_text('{{"hello": 1}}')
            sys.exit(0)
        sys.exit(provider_main(DECL, evaluate_point))
''')


def request(points=None, want=("lis", "components"), provider="toy-linear", version="1.0.0") -> dict:
    return {"protocol": "cr-provider/1", "provider": provider, "provider_version": version,
            "points": points or [{"D0_cm2_s": 3e28, "L_kpc": 4.0}, {"D0_cm2_s": 6e28, "L_kpc": 8.0}],
            "observables": [{"id": "B/C", "axis": "rigidity", "unit": "GV", "bins": [[2.0, 4.0], [4.0, 8.0]]}],
            "want": list(want), "seed": None}


class ToyProviders:
    """Synthetic providers and their registry in a temporary folder."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def make(self, mode: str = "ok", provider_id: str = "toy-linear", user_supplied: bool = False) -> dict:
        decl = dict(DECLARATION, id=provider_id, entrypoint=f"{provider_id}.py")
        path = self.folder / f"{provider_id}.py"
        path.write_text(TOY.format(root=str(ROOT), mode=mode, decl=decl), encoding="utf-8")
        return {"declaration": decl, "version": "1.0.0", "entrypoint_path": str(path), "component": "tests",
                "user_supplied": user_supplied}

    def calls(self, provider_id: str = "toy-linear") -> int:
        path = self.folder / f"{provider_id}.calls"
        return len(path.read_text().splitlines()) if path.is_file() else 0

    def registry(self, *items) -> dict:
        return {"format": REGISTRY_FORMAT, "providers": list(items)}


class ProviderTestCase(unittest.TestCase):
    def setUp(self):
        self._workdir = tempfile.TemporaryDirectory()
        self.toys = ToyProviders(Path(self._workdir.name))

    def tearDown(self):
        self._workdir.cleanup()


class RegistryRefusal(ProviderTestCase):
    """C1-1: a provider not in the registry is refused; nothing runs."""

    def test_unregistered_provider_is_refused_without_running(self):
        reg = self.toys.registry(self.toys.make())
        with ProviderRunner(reg) as runner:
            out = runner.evaluate(request(provider="not-listed"))
        self.assertEqual(out["status"], "failed")
        self.assertEqual(out["reason"], "unregistered-provider")
        self.assertEqual(out["results"], [])
        self.assertEqual(self.toys.calls(), 0)
        self.assertTrue(validate(out, {"$ref": "cr_provider.json#/$defs/response"}, Vocabulary()).ok)

    def test_registered_version_is_required(self):
        with ProviderRunner(self.toys.registry(self.toys.make())) as runner:
            out = runner.evaluate(request(version="9.9.9"))
        self.assertEqual(out["reason"], "provider-version-mismatch")
        self.assertEqual(self.toys.calls(), 0)

    def test_registry_problems_are_named(self):
        item = self.toys.make()
        bad = [dict(item, entrypoint_path="relative.py"), self.toys.registry(item, item),
               dict(item, declaration=dict(item["declaration"], protocol="cr-provider/2"))]
        for doc in (self.toys.registry(bad[0]), bad[1], self.toys.registry(bad[2]), {"providers": []}):
            with self.subTest(doc=str(doc)[:60]), self.assertRaises(RegistryError):
                parse_registry(doc)

    def test_user_supplied_outputs_are_labelled(self):
        with ProviderRunner(self.toys.registry(self.toys.make(user_supplied=True))) as runner:
            out = runner.evaluate(request())
        self.assertEqual(out["status"], "ok")
        for res in out["results"]:
            self.assertIn("user-supplied", res["labels"])


class SingleShotAndServe(ProviderTestCase):
    """C1-2: single-shot and --serve responses agree after removing elapsed_s and time stamps (PRV-2)."""

    def test_same_hash_single_shot_and_serve(self):
        reg = self.toys.registry(self.toys.make())
        with ProviderRunner(reg) as single, ProviderRunner(reg, session="serve") as served:
            one = single.evaluate(request())
            two = served.evaluate(request())
            three = served.evaluate(request())  # the session is reused
        self.assertEqual(one["status"], "ok")
        self.assertEqual(comparable_hash(one), comparable_hash(two))
        self.assertEqual(comparable_hash(two), comparable_hash(three))
        self.assertEqual(served.stats["provider_calls"], 2)

    def test_stdout_prints_do_not_break_serve(self):
        reg = self.toys.registry(self.toys.make("print"))
        with ProviderRunner(reg, session="serve") as served:
            self.assertEqual(served.evaluate(request())["status"], "ok")

    def test_conformance_report_passes_for_a_good_provider(self):
        report = run_conformance(self.toys.registry(self.toys.make()), "toy-linear", request())
        self.assertEqual(report["status"], "pass", json.dumps(report["checks"], indent=1))
        for name, response in report["responses"].items():
            with self.subTest(response=name):
                rep = validate(response, {"$ref": "cr_provider.json#/$defs/response"}, Vocabulary())
                self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors][:3])

    def test_conformance_report_fails_for_a_broken_provider(self):
        report = run_conformance(self.toys.registry(self.toys.make("garbage")), "toy-linear", request())
        self.assertEqual(report["status"], "fail")


class Cache(ProviderTestCase):
    """C1-3: a cache hit does not call the provider."""

    def test_cache_hit_does_not_call_the_provider(self):
        reg = self.toys.registry(self.toys.make())
        cache = Path(self._workdir.name) / "cache"
        with ProviderRunner(reg, cache_dir=cache) as runner:
            first = runner.evaluate(request())
            self.assertEqual(self.toys.calls(), 2)
            second = runner.evaluate(request())
            self.assertEqual(self.toys.calls(), 2)
            self.assertEqual(runner.stats["cache_hits"], 2)
            self.assertEqual(runner.stats["provider_calls"], 1)
        self.assertEqual(comparable_hash(first), comparable_hash(second))
        # the cache is keyed by the point hash: one folder per point
        keys = {hashing.point_hash(None, "toy-linear", "1.0.0", p) for p in request()["points"]}
        self.assertEqual({p.name for p in cache.iterdir()}, keys)

    def test_partial_hit_sends_only_the_missing_point(self):
        reg = self.toys.registry(self.toys.make())
        cache = Path(self._workdir.name) / "cache"
        with ProviderRunner(reg, cache_dir=cache) as runner:
            runner.evaluate(request(points=[{"D0_cm2_s": 3e28, "L_kpc": 4.0}]))
            out = runner.evaluate(request(points=[{"D0_cm2_s": 3.0e28, "L_kpc": 4}, {"D0_cm2_s": 5e28, "L_kpc": 4}]))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(self.toys.calls(), 2)  # 3e28 and 3.0e28 / 4 and 4.0 are one key
        self.assertEqual(out["results"][0]["point"], {"D0_cm2_s": 3.0e28, "L_kpc": 4})

    def test_other_bins_are_a_miss(self):
        reg = self.toys.registry(self.toys.make())
        cache = Path(self._workdir.name) / "cache"
        with ProviderRunner(reg, cache_dir=cache) as runner:
            runner.evaluate(request())
            other = request()
            other["observables"][0]["bins"] = [[2.0, 3.0], [3.0, 8.0]]
            runner.evaluate(other)
        self.assertEqual(self.toys.calls(), 4)


class CacheAndTheorySpec(ProviderTestCase):
    """The cache never mixes theory-specs: with a transport block the point hash covers it and theory_spec_ref is part
    of the key; a request naming a theory_spec_ref without a transport block is never cached."""

    def test_theory_spec_ref_without_transport_is_not_cached(self):
        reg = self.toys.registry(self.toys.make())
        cache = Path(self._workdir.name) / "cache"
        with ProviderRunner(reg, cache_dir=cache) as runner:
            for ref in ("spec-a.json", "spec-b.json", "spec-a.json"):
                runner.evaluate(dict(request(), theory_spec_ref=ref, transport=None))
            self.assertEqual(runner.stats["cache_hits"], 0)
        self.assertEqual(self.toys.calls(), 6)
        self.assertFalse(cache.exists() and any(cache.iterdir()))

    def test_theory_spec_ref_is_part_of_the_key(self):
        reg = self.toys.registry(self.toys.make())
        cache = Path(self._workdir.name) / "cache"
        transport = {"geometry": {"kind": "cylinder-2d", "radius_kpc": 20.0}}
        with ProviderRunner(reg, cache_dir=cache) as runner:
            runner.evaluate(dict(request(), theory_spec_ref="spec-a.json", transport=transport))
            runner.evaluate(dict(request(), theory_spec_ref="spec-b.json", transport=transport))
            self.assertEqual(runner.stats["cache_hits"], 0)
            runner.evaluate(dict(request(), theory_spec_ref="spec-a.json", transport=transport))
            self.assertEqual(runner.stats["cache_hits"], 2)
            runner.evaluate(dict(request(), theory_spec_ref="spec-a.json",
                                 transport={"geometry": {"kind": "cylinder-2d", "radius_kpc": 15.0}}))
            self.assertEqual(runner.stats["cache_hits"], 2)  # another transport block is another point hash
        self.assertEqual(self.toys.calls(), 6)


class Failures(ProviderTestCase):
    """C1-4: a forced provider crash is reported as failed with the reason (R4)."""

    def test_crash_is_failed_with_reason(self):
        for session in ("single", "serve"):
            with self.subTest(session=session), ProviderRunner(self.toys.registry(self.toys.make("crash")),
                                                               session=session) as runner:
                out = runner.evaluate(request())
                self.assertEqual(out["status"], "failed")
                for res in out["results"]:
                    self.assertEqual(res["status"], "failed")
                    self.assertEqual(res["reason"], "provider-failed")
                    self.assertIn("segmentation fault", res["detail"])
                    self.assertNotIn("predictions", res)
                    self.assertIn("failed", res["labels"])

    def test_exception_in_the_evaluation_is_provider_error(self):
        with ProviderRunner(self.toys.registry(self.toys.make("raise"))) as runner:
            out = runner.evaluate(request())
        self.assertEqual({r["reason"] for r in out["results"]}, {"provider-error"})
        self.assertIn("synthetic failure", out["results"][0]["detail"])

    def test_invalid_response_is_refused(self):
        with ProviderRunner(self.toys.registry(self.toys.make("garbage"))) as runner:
            out = runner.evaluate(request())
        self.assertEqual({r["reason"] for r in out["results"]}, {"invalid-response"})

    def test_timeout(self):
        item = self.toys.make()
        Path(item["entrypoint_path"]).write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
        with ProviderRunner(self.toys.registry(item), timeout_s=1.0) as runner:
            out = runner.evaluate(request())
        self.assertEqual({r["reason"] for r in out["results"]}, {"provider-timeout"})

    def test_failures_are_not_cached(self):
        cache = Path(self._workdir.name) / "cache"
        with ProviderRunner(self.toys.registry(self.toys.make("raise")), cache_dir=cache) as runner:
            runner.evaluate(request())
        self.assertFalse(cache.exists() and any(cache.iterdir()))


class Domain(ProviderTestCase):
    """C1-5: out of domain is refused with reason out-of-domain; --allow-outside-validated-range gives a prediction
    labelled outside-validated-range."""

    OUTSIDE = {"D0_cm2_s": 3e28, "L_kpc": 40.0}

    def test_out_of_domain_refused(self):
        with ProviderRunner(self.toys.registry(self.toys.make())) as runner:
            out = runner.evaluate(request(points=[{"D0_cm2_s": 3e28, "L_kpc": 4.0}, self.OUTSIDE]))
        self.assertEqual(out["status"], "incomplete")
        res = out["results"][1]
        self.assertEqual((res["status"], res["reason"]), ("failed", "out-of-domain"))
        self.assertNotIn("predictions", res)
        self.assertIn("L_kpc", res["detail"])
        self.assertEqual(self.toys.calls(), 1)  # only the in-domain point reached the provider

    def test_allow_outside_labels_the_prediction(self):
        with ProviderRunner(self.toys.registry(self.toys.make()), allow_outside=True) as runner:
            out = runner.evaluate(request(points=[self.OUTSIDE, {"D0_cm2_s": 3e28, "L_kpc": 4.0}]))
        self.assertEqual(out["status"], "ok")
        self.assertIn("outside-validated-range", out["results"][0]["labels"])
        self.assertIn("predictions", out["results"][0])
        self.assertNotIn("outside-validated-range", out["results"][1]["labels"])

    def test_provider_side_refuses_too(self):
        decl = DECLARATION
        out = respond(request(points=[self.OUTSIDE]), decl, lambda *a: {})
        self.assertEqual(out["results"][0]["reason"], "out-of-domain")

    def test_bins_outside_the_axis_range(self):
        req = request()
        req["observables"][0]["bins"] = [[0.5, 2.0], [2.0, 4.0]]
        with ProviderRunner(self.toys.registry(self.toys.make())) as runner:
            out = runner.evaluate(req)
        self.assertEqual((out["status"], out["reason"]), ("failed", "out-of-domain"))
        with ProviderRunner(self.toys.registry(self.toys.make()), allow_outside=True) as runner:
            out = runner.evaluate(req)
        self.assertEqual(out["status"], "ok")
        self.assertTrue(all("outside-validated-range" in r["labels"] for r in out["results"]))

    def test_unknown_parameter(self):
        with ProviderRunner(self.toys.registry(self.toys.make())) as runner:
            out = runner.evaluate(request(points=[{"D0_cm2_s": 3e28, "V_A_kms": 10.0}]))
        self.assertEqual(out["results"][0]["reason"], "unknown-parameter")


class Hash(unittest.TestCase):
    """C1-6: the core hash equals contracts/recipe_semantics.py canonical_sha256 on 10 random objects."""

    @staticmethod
    def random_value(rng: random.Random, depth: int = 0):
        kind = rng.randrange(8 if depth < 3 else 5)
        if kind == 0:
            return rng.uniform(-1e30, 1e30)
        if kind == 1:
            return rng.randint(-10**12, 10**12)
        if kind == 2:
            return "".join(rng.choice("abcXYZ_/:é∂β 0123") for _ in range(rng.randint(0, 12)))
        if kind == 3:
            return rng.choice([True, False, None])
        if kind == 4:
            return rng.choice([1e-300, 5e-324, 0.1, -0.0, 3e28])
        if kind in (5, 6):
            return {f"k{rng.randint(0, 99)}_{i}": Hash.random_value(rng, depth + 1) for i in range(rng.randint(0, 5))}
        return [Hash.random_value(rng, depth + 1) for _ in range(rng.randint(0, 5))]

    def test_canonical_hash_equals_contracts_on_ten_random_objects(self):
        rng = random.Random(20261026)
        for i in range(10):
            hashed = {"transport": self.random_value(rng), "provider": f"p{i}", "provider_version": "1.0.0",
                   "point": {f"x{j}": repr(rng.uniform(0, 1e30)) for j in range(rng.randint(1, 6))},
                   "extra": self.random_value(rng)}
            with self.subTest(i=i):
                self.assertEqual(hashing.canonical_sha256(hashed), contracts_sha256(hashed))

    def test_point_hash_is_canonical_sha256_of_the_plan_object(self):
        rng = random.Random(5)
        for i in range(10):
            transport = {"geometry": {"L_kpc": rng.uniform(1, 20)}, "losses": ["ionization"]} if i % 2 else None
            point = {"D0_cm2_s": rng.uniform(1e27, 1e30), "delta": rng.uniform(0.2, 0.9), "L_kpc": rng.randint(1, 20)}
            plan_object = {"transport": transport, "provider": "toy", "provider_version": "v",
                   "point": {k: repr(float(point[k])) for k in sorted(point)}}
            with self.subTest(i=i):
                self.assertEqual(hashing.point_hash(transport, "toy", "v", point), contracts_sha256(plan_object))

    def test_number_forms_share_one_key(self):
        self.assertEqual(hashing.point_hash(None, "p", "1", {"L_kpc": 4, "D0_cm2_s": 3e28}),
                         hashing.point_hash(None, "p", "1", {"D0_cm2_s": 30000000000000000000000000000, "L_kpc": 4.0}))
        with self.assertRaises(ValueError):
            hashing.point_key({"L_kpc": float("nan")})


class SchemaAgreement(unittest.TestCase):
    """The core rules and contracts/schemas/cr_provider.json agree on the request, response and declaration."""

    def schema_ok(self, value, name) -> bool:
        return validate(value, {"$ref": f"cr_provider.json#/$defs/{name}"}, Vocabulary()).ok

    def test_requests(self):
        good = request()
        bad = [dict(good, protocol="cr-provider/2"), dict(good, points=[]), dict(good, extra=1),
               dict(good, points=[{"L_kpc": "4"}]), dict(good, want=[]),
               dict(good, observables=[{"id": "B/C", "axis": "ekn", "unit": "GV", "bins": [[1, 2]]}])]
        self.assertEqual(protocol.check_request(good), [])
        self.assertTrue(self.schema_ok(good, "request"))
        for b in bad:
            with self.subTest(request=str(b)[:80]):
                self.assertTrue(protocol.check_request(b))
        for b in bad[:5]:
            self.assertFalse(self.schema_ok(b, "request"))

    def test_want_beyond_lis_and_components(self):
        req = request(want=("lis", "modulated"))
        self.assertEqual(protocol.check_request(req), [])
        self.assertFalse(self.schema_ok(req, "request"))
        out = respond(req, DECLARATION, lambda *a: {})
        self.assertEqual((out["status"], out["reason"]), ("failed", "unsupported-want"))
        self.assertTrue(self.schema_ok(out, "response"))

    def test_declarations(self):
        self.assertEqual(protocol.check_declaration(DECLARATION), [])
        self.assertTrue(self.schema_ok(DECLARATION, "declaration"))
        self.assertTrue(self.schema_ok([DECLARATION, dict(DECLARATION, id="other")], "declarations"))
        for bad in (dict(DECLARATION, entrypoint="../x.py"), dict(DECLARATION, axes=["energy"]),
                    dict(DECLARATION, protocol="x"), {k: v for k, v in DECLARATION.items() if k != "domain"},
                    dict(DECLARATION, domain={"L_kpc": {"min": 5, "max": 1}})):
            with self.subTest(bad=str(bad)[:60]):
                self.assertTrue(protocol.check_declaration(bad))
        # min > max is a core rule the schema subset cannot state
        self.assertFalse(self.schema_ok(dict(DECLARATION, entrypoint="../x.py"), "declaration"))

    def test_components_need_a_decomposable_provider(self):
        out = respond(request(), dict(DECLARATION, decomposable=False), lambda *a: {})
        self.assertEqual(out["reason"], "not-decomposable")


class CommandLines(ProviderTestCase):
    def run_cli(self, *argv, stdin=None):
        return subprocess.run([sys.executable, "-I", *map(str, argv)], capture_output=True, text=True, timeout=120,
                              input=stdin, cwd=self._workdir.name, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_help(self):
        for script in ("core/provider/runner.py", "core/provider/conformance.py"):
            with self.subTest(script=script):
                proc = self.run_cli(ROOT / script, "--help")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("usage:", proc.stdout)

    def test_runner_single_shot_and_serve(self):
        reg = Path(self._workdir.name) / "registry.json"
        reg.write_text(json.dumps(self.toys.registry(self.toys.make())), encoding="utf-8")
        req = Path(self._workdir.name) / "request.json"
        req.write_text(json.dumps(request()), encoding="utf-8")
        resp = Path(self._workdir.name) / "response.json"
        proc = self.run_cli(ROOT / "core/provider/runner.py", "--provider-registry", reg, "--request", req,
                            "--response", resp)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["status"], "ok")
        lines = json.dumps(request()) + "\n\nnot json\n" + json.dumps(request(provider="nope")) + "\n"
        proc = self.run_cli(ROOT / "core/provider/runner.py", "--provider-registry", reg, "--serve", stdin=lines)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        answers = [json.loads(x) for x in proc.stdout.splitlines()]
        self.assertEqual([a["status"] for a in answers], ["ok", "failed", "failed"])
        self.assertEqual([a.get("reason") for a in answers[1:]], ["invalid-request", "unregistered-provider"])
        self.assertEqual(comparable_hash(answers[0]), comparable_hash(json.loads(resp.read_text())))

    def test_runner_exit_codes(self):
        reg = Path(self._workdir.name) / "registry.json"
        reg.write_text("{}", encoding="utf-8")
        proc = self.run_cli(ROOT / "core/provider/runner.py", "--provider-registry", reg, "--request", reg,
                            "--response", Path(self._workdir.name) / "r.json")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)["status"], "rejected")
        reg.write_text(json.dumps(self.toys.registry(self.toys.make())), encoding="utf-8")
        req = Path(self._workdir.name) / "request.json"
        req.write_text(json.dumps(request(points=[{"L_kpc": 400.0}])), encoding="utf-8")
        proc = self.run_cli(ROOT / "core/provider/runner.py", "--provider-registry", reg, "--request", req,
                            "--response", Path(self._workdir.name) / "r.json")
        self.assertEqual(proc.returncode, 1)

    def test_provider_single_shot_exit_codes(self):
        item = self.toys.make()
        req = Path(self._workdir.name) / "request.json"
        resp = Path(self._workdir.name) / "response.json"
        for points, code in (([{"L_kpc": 4.0}], 0), ([{"L_kpc": 400.0}], 1), ([{"L_kpc": 4.0}, {"L_kpc": 400.0}], 3)):
            req.write_text(json.dumps(request(points=points)), encoding="utf-8")
            proc = self.run_cli(item["entrypoint_path"], "--request", req, "--response", resp)
            with self.subTest(points=points):
                self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        proc = self.run_cli(item["entrypoint_path"], "--request", Path(self._workdir.name) / "missing.json",
                            "--response", resp)
        self.assertEqual(proc.returncode, 2)

    def test_core_holds_no_component_path(self):
        """R1: core/provider holds no profiles/, adapters/ or skills/ path string (check_layering's text rule)."""
        import re
        for path in sorted((ROOT / "core" / "provider").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertIsNone(re.search(r"""["'][^"'\n]*\b(profiles|adapters|skills)/""", text))


# ------------------------------------------------------------------ declared modulation (contracts 3.15.0, K2)
CONFORMANCE = {"reference_point": {"L_kpc": 4.0, "phi_p_gv": 0.5},
               "observables": [{"id": "B/C", "axis": "rigidity", "unit": "GV", "bins": [[2.0, 4.0], [4.0, 8.0]]}],
               "tolerance": 1e-3,
               "result": {"status": "passed", "max_relative_deviation": 4e-5, "nodes_compared": 40,
                          "isotopes": ["11B", "12C"], "tool": "SYNTHETIC force-field tool",
                          "provider_version": "1.0.0"}}
MODULATION = {"model": "force-field", "implementation": "SYNTHETIC force field per isotope", "parameters": ["phi_p_gv"],
              "conformance": CONFORMANCE}
MODULATED = dict(DECLARATION, id="toy-modulated", domain=dict(DECLARATION["domain"], phi_p_gv={"min": 0.0, "max": 2.0}),
                 modulation=MODULATION)
# the toy's level: top-of-atmosphere in mode "toa", or for a point with a modulation potential; else local interstellar
LEVELLED_TOY = TOY.replace('"level": "top-of-instrument"', '"level": ("top-of-atmosphere" if MODE == "toa" or any('
                           'v for k, v in point.items() if k.startswith("phi_")) else "crsr:local-interstellar")')


def changed(base: dict, path: str, value) -> dict:
    """A deep copy of base with the dotted path set to value (None removes it)."""
    out = json.loads(json.dumps(base))
    *keys, last = path.split(".")
    node = out
    for k in keys:
        node = node[k]
    if value is None:
        node.pop(last)
    else:
        node[last] = value
    return out


class DeclaredModulation(ProviderTestCase):
    """K2-1: the optional modulation block; schema and core agree; the runner refuses a top-of-atmosphere prediction
    without the block, a point that would be modulated twice, and a phi for a provider without the block."""

    def schema_ok(self, value) -> bool:
        return validate(value, {"$ref": "cr_provider.json#/$defs/declaration"}, Vocabulary()).ok

    def make(self, mode: str = "ok", decl: dict = MODULATED) -> dict:
        path = Path(self._workdir.name) / f"{decl['id']}-{mode}.py"
        path.write_text(LEVELLED_TOY.format(root=str(ROOT), mode=mode, decl=dict(decl, entrypoint=path.name)),
                        encoding="utf-8")
        return {"declaration": dict(decl, entrypoint=path.name), "version": "1.0.0", "entrypoint_path": str(path),
                "component": "tests", "user_supplied": False}

    def test_declaration_with_the_block(self):
        self.assertEqual(protocol.check_declaration(MODULATED), [])
        self.assertTrue(self.schema_ok(MODULATED))
        self.assertEqual(protocol.modulation_parameters(MODULATED), ["phi_p_gv"])
        self.assertEqual(protocol.modulation_parameters(DECLARATION), [])

    def test_bad_blocks_agree_with_the_schema(self):
        both = {"model": changed(MODULATED, "modulation.model", "drift"),
                "implementation": changed(MODULATED, "modulation.implementation", ""),
                "no conformance": changed(MODULATED, "modulation.conformance", None),
                "not passed": changed(MODULATED, "modulation.conformance.result.status", "failed"),
                "tolerance looser than 1e-3": changed(MODULATED, "modulation.conformance.tolerance", 2e-3),
                "zero tolerance": changed(MODULATED, "modulation.conformance.tolerance", 0.0),
                "parameter name": changed(MODULATED, "modulation.parameters", ["potential"]),
                "no nodes": changed(MODULATED, "modulation.conformance.result.nodes_compared", 0),
                "extra field": changed(MODULATED, "modulation.extra", 1),
                # L2 (contracts 3.16.0): the result names the provider version it was obtained at
                "no provider version": changed(MODULATED, "modulation.conformance.result.provider_version", None),
                "empty provider version": changed(MODULATED, "modulation.conformance.result.provider_version", "")}
        # rules the schema subset cannot state (cross-field): core only
        core_only = {"phi without the block": changed(MODULATED, "modulation", None),
                     "parameter outside the domain": changed(MODULATED, "modulation.parameters", ["phi_q_gv"]),
                     "deviation above the tolerance": changed(MODULATED,
                                                              "modulation.conformance.result.max_relative_deviation",
                                                              2e-3),
                     "reference point without phi": changed(MODULATED, "modulation.conformance.reference_point",
                                                            {"L_kpc": 4.0}),
                     "reference point outside the domain": changed(MODULATED,
                                                                   "modulation.conformance.reference_point.L_kpc", 99.0),
                     "undeclared observable": changed(MODULATED, "modulation.conformance.observables",
                                                      [{"id": "Be/B", "axis": "rigidity", "unit": "GV",
                                                        "bins": [[2.0, 4.0]]}]),
                     "result of another provider version": changed(MODULATED, "version", "1.1.0")}
        for name, bad in both.items():
            with self.subTest(both=name):
                self.assertTrue(protocol.check_declaration(bad))
                self.assertFalse(self.schema_ok(bad))
        for name, bad in core_only.items():
            with self.subTest(core=name):
                self.assertTrue(protocol.check_declaration(bad))
                self.assertTrue(self.schema_ok(bad))

    def test_registry_refuses_a_block_without_a_passing_result(self):
        item = self.make()
        item["declaration"] = changed(item["declaration"], "modulation.conformance.result.status", "failed")
        with self.assertRaises(RegistryError) as ctx:
            parse_registry(self.toys.registry(item))
        self.assertIn("passed", str(ctx.exception))

    def test_conformance_holds_only_at_the_version_it_was_obtained_at(self):
        """L2-1: the registry (and conformance.run_conformance through it) refuses a declaration whose conformance
        result names another version than the registry entry's; check_declaration compares with the version the
        caller resolved, else with the declaration's own."""
        unversioned = changed(MODULATED, "version", None)
        self.assertEqual(protocol.check_declaration(unversioned), [])           # nothing to compare with
        self.assertEqual(protocol.check_declaration(unversioned, "1.0.0"), [])
        problems = protocol.check_declaration(unversioned, "1.1.0")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("provider_version '1.0.0' differs from the provider version '1.1.0'", problems[0])
        self.assertIn("rerun", problems[0])
        self.assertTrue(protocol.check_declaration(MODULATED, "1.1.0"))         # the caller's version wins
        item = self.make()
        self.assertIn("toy-modulated", parse_registry(self.toys.registry(item)))
        item["version"] = "1.1.0"                                               # a new provider version, gate not rerun
        with self.assertRaises(RegistryError) as ctx:
            parse_registry(self.toys.registry(item))
        self.assertIn("differs from the provider version '1.1.0'", str(ctx.exception))
        item = self.make()
        item["declaration"] = changed(item["declaration"], "modulation.conformance.result.provider_version", None)
        with self.assertRaises(RegistryError) as ctx:
            parse_registry(self.toys.registry(item))
        self.assertIn("result: exactly", str(ctx.exception))

    def test_top_of_atmosphere_without_the_block_is_an_invalid_response(self):
        with ProviderRunner(self.toys.registry(self.make("toa", dict(DECLARATION, id="toy-toa")))) as runner:
            out = runner.evaluate(request(provider="toy-toa"))
        self.assertEqual({r["reason"] for r in out["results"]}, {"invalid-response"})
        self.assertIn("no modulation block", out["results"][0]["detail"])

    def test_declared_modulation_levels(self):
        points = [{"L_kpc": 4.0, "phi_p_gv": 0.5}, {"L_kpc": 4.0}]
        with ProviderRunner(self.toys.registry(self.make())) as runner:
            out = runner.evaluate(request(points=points, provider="toy-modulated"))
        self.assertEqual(out["status"], "ok", out)
        levels = [r["predictions"][0]["observable"]["level"] for r in out["results"]]
        self.assertEqual(levels, ["top-of-atmosphere", "crsr:local-interstellar"])
        with ProviderRunner(self.toys.registry(self.make("toa"))) as runner:   # modulated without a potential
            out = runner.evaluate(request(points=[{"L_kpc": 4.0}], provider="toy-modulated"))
        self.assertEqual(out["results"][0]["reason"], "invalid-response")
        self.assertIn("without a modulation parameter", out["results"][0]["detail"])

    def test_a_point_modulated_twice_is_refused(self):
        decl = dict(MODULATED, domain=dict(MODULATED["domain"], phi_q_gv={"min": 0.0, "max": 2.0}),
                    modulation=dict(MODULATION, parameters=["phi_p_gv", "phi_q_gv"]))
        self.assertEqual(protocol.check_declaration(decl), [])
        with ProviderRunner(self.toys.registry(self.make(decl=decl))) as runner:
            out = runner.evaluate(request(points=[{"L_kpc": 4.0, "phi_p_gv": 0.5, "phi_q_gv": 0.6}],
                                          provider="toy-modulated"))
        self.assertEqual(out["results"][0]["reason"], "invalid-request")
        self.assertIn("modulated", out["results"][0]["detail"])
        self.assertEqual(self.toys.calls("toy-modulated-ok"), 0)   # refused before the provider runs
        out = respond(request(points=[{"L_kpc": 4.0, "phi_p_gv": 0.5, "phi_q_gv": 0.6}], provider="toy-modulated"),
                      decl, lambda *a: {})
        self.assertEqual(out["results"][0]["reason"], "invalid-request")   # the provider side refuses too

    def test_phi_for_a_provider_without_the_block_is_an_unknown_parameter(self):
        with ProviderRunner(self.toys.registry(self.toys.make())) as runner:
            out = runner.evaluate(request(points=[{"L_kpc": 4.0, "phi_p_gv": 0.5}]))
        self.assertEqual(out["results"][0]["reason"], "unknown-parameter")

    def test_a_cached_top_of_atmosphere_result_is_checked_too(self):
        cache = Path(self._workdir.name) / "cache"
        registry = self.toys.registry(self.toys.make())
        with ProviderRunner(registry, cache_dir=cache) as runner:
            self.assertEqual(runner.evaluate(request())["status"], "ok")
        for path in cache.glob("*/*.json"):
            doc = json.loads(path.read_text())
            for pred in doc["result"]["predictions"]:
                pred["observable"]["level"] = "top-of-atmosphere"
            path.write_text(json.dumps(doc))
        with ProviderRunner(registry, cache_dir=cache) as runner:
            out = runner.evaluate(request())
        self.assertEqual(runner.stats["cache_hits"], 2)
        self.assertEqual({r["reason"] for r in out["results"]}, {"invalid-response"})


if __name__ == "__main__":
    unittest.main()
