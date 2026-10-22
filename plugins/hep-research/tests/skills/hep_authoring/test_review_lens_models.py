"""Per-lens model choice of the independent review (contracts 3.4.0; docs/dev/independent-review-spec.md sections
5.1 and A2): lens_models / start --lens-model fixes the model of a lens's lens slot in every round; its shadow keeps
the rotation, moved on when the rotation would give it the fixed model. Without it the slot allocation is bit for bit
the one released in 0.22.0. Synthetic data only."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R

import review as DRV  # noqa: E402  (the harness puts the driver's folder on sys.path)

MODELS3 = ["model-a", "model-b", "model-c"]
LENS_CFG = {"config_version": "1.0.0", "models": MODELS3, "lens_models": {"design": "model-c"}}


def old_allocate_slots(lenses, models, seed, first=1, offset=0, plan=None):
    """allocate_slots exactly as released in 0.22.0 (contracts 3.3.0), the reference for bit-for-bit equality."""
    roles = plan if plan is not None else [("lens", L) for L in lenses] + [("shadow", L) for L in lenses]
    ids = [f"S{i}" for i in range(first, first + len(roles))]
    DRV.U.rng(DRV.U.derive(seed, "slots")).shuffle(ids)
    out = {}
    m = len(models)
    for n, ((role, lens), sid) in enumerate(zip(roles, ids)):
        i = lenses.index(lens)
        model = models[(i + offset) % m] if role == "lens" else models[(i + offset + 1) % m]
        out[sid] = {"role": role, "lens": lens, "model": model}
    return out


class LensModelTests(unittest.TestCase):
    def test_allocation_without_lens_models_is_bit_for_bit_the_old_one(self):
        lens_sets = (["facts", "design", "sources", "bypass"], ["facts", "design", "sources", "bypass", "statistics"],
                     ["facts", "design"])
        model_sets = (["m"], ["a", "b"], ["a", "b", "c"], ["a", "a", "b"])
        n = 0
        for seed in (f"{i:064x}" for i in range(0, 4000, 37)):
            for lenses in lens_sets:
                for models in model_sets:
                    for offset in (0, 1, 2):
                        plan = [("lens", L) for L in lenses] + [("shadow", L) for L in lenses[1:]]
                        for p in (None, plan):
                            ref = old_allocate_slots(lenses, models, seed, offset=offset, plan=p)
                            self.assertEqual(DRV.allocate_slots(lenses, models, seed, offset=offset, plan=p), ref)
                            self.assertEqual(DRV.allocate_slots(lenses, models, seed, offset=offset, plan=p,
                                                                lens_models={}), ref)
                            n += 1
        self.assertGreater(n, 2500)

    def test_start_without_options_keeps_the_released_slots(self):
        """The harness review (seed 7, models a and b): slot labels and models pinned from 0.22.0."""
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.start()
            got = {s: (v["role"], v["lens"], v["model"]) for s, v in h.rv.slots()["1"].items()}
            ref = old_allocate_slots(["facts", "design", "sources", "bypass"], ["model-a", "model-b"],
                                     DRV.round_seed(h.rv, 1))
            self.assertEqual(got, {s: (v["role"], v["lens"], v["model"]) for s, v in ref.items()})
            cfg = json.loads((h.project / "reviews" / "review-config.json").read_text(encoding="utf-8"))
            self.assertEqual(cfg, {"config_version": "1.0.0", "models": ["model-a", "model-b"]})

    def test_fixed_lens_slot_and_rotating_shadow(self):
        lenses = ["facts", "design", "sources", "bypass"]
        for seed in ("1" * 64, "2" * 64, "3" * 64):
            for offset in (0, 1, 2):
                base = DRV.allocate_slots(lenses, MODELS3, seed, offset=offset)
                fixed = DRV.allocate_slots(lenses, MODELS3, seed, offset=offset, lens_models={"design": "model-c"})
                self.assertEqual(sorted(base), sorted(fixed))
                for sid, v in fixed.items():
                    if v["lens"] != "design":
                        self.assertEqual(v, base[sid])
                    elif v["role"] == "lens":
                        self.assertEqual(v["model"], "model-c")
                    else:
                        self.assertNotEqual(v["model"], "model-c")
                        if base[sid]["model"] != "model-c":
                            self.assertEqual(v["model"], base[sid]["model"])  # the shadow keeps the rotation

    def test_shadow_moves_off_the_fixed_model(self):
        # models a, b: design (index 1) rotates to lens b, shadow a; fixing design to a moves the shadow to b
        out = DRV.allocate_slots(["facts", "design"], ["model-a", "model-b"], "4" * 64, lens_models={"design": "model-a"})
        got = {(v["role"], v["lens"]): v["model"] for v in out.values()}
        self.assertEqual((got[("lens", "design")], got[("shadow", "design")]), ("model-a", "model-b"))
        out = DRV.allocate_slots(["facts", "design"], ["model-a"], "4" * 64, lens_models={"design": "model-a"})
        self.assertEqual({v["model"] for v in out.values()}, {"model-a"})  # one model: no other choice

    def test_start_option_writes_the_config_and_fixes_the_design_lens(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            (h.project / "reviews" / "review-config.json").unlink()
            h.run("start", h.doc_rel, "--seed", "7", "--models", ",".join(MODELS3), "--lens-model", "design=model-c",
                  expect=0)
            cfg = json.loads((h.project / "reviews" / "review-config.json").read_text(encoding="utf-8"))
            self.assertEqual(cfg, {"config_version": "1.0.0", "models": MODELS3, "lens_models": {"design": "model-c"}})
            slots = h.rv.slots()["1"]
            self.assertEqual([v["model"] for v in slots.values() if v == {"role": "lens", "lens": "design", "model": v["model"]}],
                             ["model-c"])
            self.assertEqual(h.st()["rounds"][1]["config"], cfg)

    def test_start_option_refusals(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t), config={"config_version": "1.0.0", "models": MODELS3}).setup()
            before = (h.project / "reviews" / "review-config.json").read_bytes()
            out = h.run("start", h.doc_rel, "--lens-model", "design=model-z")
            self.assertEqual(out["_exit"], 2)
            self.assertIn("lens_models.design: model-z is not in models", out["error"])
            out = h.run("start", h.doc_rel, "--lens-model", "designs=model-a")
            self.assertEqual(out["_exit"], 2)
            self.assertIn("not in the lens table", out["error"])
            out = h.run("start", h.doc_rel, "--lens-model", "design")
            self.assertEqual(out["_exit"], 2)
            self.assertEqual((h.project / "reviews" / "review-config.json").read_bytes(), before)
            h.start()  # an unfinished review now uses the configuration
            other = h.project / "docs" / "other.md"
            other.write_text(H.DOC.replace("small design note", "second note"), encoding="utf-8")
            out = h.run("start", "docs/other.md", "--lens-model", "facts=model-b")
            self.assertEqual(out["_exit"], 2)
            self.assertIn("finish them first", out["error"])
            self.assertEqual((h.project / "reviews" / "review-config.json").read_bytes(), before)

    def test_config_rules(self):
        self.assertEqual(R.config_problems(LENS_CFG), [])
        bad = dict(LENS_CFG, lens_models={"design": "model-z", "Bad Lens": "model-a"})
        probs = R.config_problems(bad)
        self.assertIn("lens_models.design: model-z is not in models", probs)
        self.assertIn("lens_models: 'Bad Lens' is not a lens name", probs)
        self.assertTrue(R.config_problems(dict(LENS_CFG, lens_models={"design": ""})))
        self.assertEqual(R.effective_config({"models": ["m"]})["lens_models"], {})
        self.assertEqual(R.weak_config(LENS_CFG), [])


if __name__ == "__main__":
    unittest.main()
