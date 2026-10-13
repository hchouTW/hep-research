"""hep-statistics audit T15: simultaneous signal and control regions from a model card, with signal contamination of the
control region and a luminosity shared by every channel (one auxiliary measurement). Checks: the pyhf fit equals the
closed-form solution of the two-region system; Asimov closure is unbiased with the contamination modeled; a card that
omits the contamination is biased by exactly the analytic amount and the closure check fails; a duplicated auxiliary
measurement, a prior in a frequentist model and a contamination claim without a modeled CR signal are refused, both by
the converter and by the statistical-result contract. SYNTHETIC. Skipped (unverified) without pyhf."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "pyhf-combine" / "assets"))
try:
    import pyhf  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
import model_card as mc  # noqa: E402  (pyhf is imported inside fit only)

S_SR, S_CR, B_SR, B_CR = 5.0, 1.5, 10.0, 40.0
LUMI = {"type": "constrained-normalization", "parameter": "lumi", "hi": 1.02, "lo": 0.98}


def card(contamination=True, minor=True, n_sr=17.0, n_cr=50.0):
    samples = [{"name": "signal", "channel": "SR", "yields": [S_SR], "modifiers": [{"type": "poi", "parameter": "mu"}]},
               {"name": "bkg", "channel": "SR", "yields": [B_SR], "modifiers": [{"type": "free-normalization", "parameter": "k_bkg"}]},
               {"name": "bkg", "channel": "CR", "yields": [B_CR], "modifiers": [{"type": "free-normalization", "parameter": "k_bkg"}]}]
    if contamination:
        samples.append({"name": "signal", "channel": "CR", "yields": [S_CR], "modifiers": [{"type": "poi", "parameter": "mu"}]})
    constraints = []
    if minor:
        samples += [{"name": "minor", "channel": "SR", "yields": [2.0], "modifiers": [dict(LUMI)]},
                    {"name": "minor", "channel": "CR", "yields": [3.0], "modifiers": [dict(LUMI)]}]
        constraints = [{"parameter": "lumi", "kind": "auxiliary-measurement", "aux_id": "lumi-run2", "form": "gaussian", "width": 0.02}]
    return {"poi": "mu", "ensemble": "conditional-fluctuated-aux", "signal_contamination": "modeled" if contamination else "not-modeled",
            "channels": [{"name": "SR", "role": "signal-region", "observed": [n_sr]},
                         {"name": "CR", "role": "control-region", "observed": [n_cr]}],
            "samples": samples, "constraints": constraints}


@unittest.skipUnless(HAVE, "pyhf not installed: SR/CR model-card checks unverified")
class FidelitySTH312(unittest.TestCase):
    """STH-T3.12, confirmed with pyhf 0.7.6 before the fix: a validation region with 200 observed events against 40
    expected moved mu_hat from 0.70 to -3.94 (it entered the fit), and a constraint width of 0.5 instead of 0.02 left
    the fit unchanged (the width was ignored)."""

    @unittest.skipUnless(HAVE, "pyhf not installed")
    def test_validation_region_is_excluded_from_the_fit(self):
        import copy
        base = mc.fit(card())
        vr = copy.deepcopy(card())
        vr["channels"].append({"name": "VR", "role": "validation-region", "observed": [200.0]})
        vr["samples"].append({"name": "bkg", "channel": "VR", "yields": [40.0],
                              "modifiers": [{"type": "free-normalization", "parameter": "k_bkg"}]})
        r = mc.fit(vr)
        self.assertAlmostEqual(r["poi_hat"], base["poi_hat"], places=6)
        self.assertEqual(r["validation_regions_excluded"], ["VR"])
        self.assertNotIn("VR", [ch["name"] for ch in mc.to_pyhf(vr)["channels"]])

    def test_constraint_width_reaches_the_model(self):
        import copy
        c = copy.deepcopy(card())
        for smp in c["samples"]:
            for m in smp["modifiers"]:
                if m["parameter"] == "lumi":
                    m.pop("hi")
                    m.pop("lo")
        c["constraints"][0]["width"] = 0.1
        mods = [m for ch in mc.to_pyhf(c)["channels"] for smp in ch["samples"] for m in smp["modifiers"] if m["name"] == "lumi"]
        self.assertTrue(mods)
        for m in mods:
            self.assertAlmostEqual(m["data"]["hi"], 1.1)
            self.assertAlmostEqual(m["data"]["lo"], 0.9)
        bad = copy.deepcopy(card())
        bad["constraints"][0]["width"] = 0.5        # disagrees with hi/lo = 1.02/0.98
        with self.assertRaises(mc.CardRefused):
            mc.to_pyhf(bad)


@unittest.skipUnless(HAVE, "pyhf not installed: SR/CR model-card checks unverified")
class SrCrModelCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import model_card as mc
        cls.mc = mc

    def test_fit_equals_the_closed_form_solution(self):
        n_sr, n_cr = 17.0, 50.0
        mu = (n_sr * B_CR - n_cr * B_SR) / (S_SR * B_CR - S_CR * B_SR)
        k = (n_sr - mu * S_SR) / B_SR
        r = self.mc.fit(card(minor=False, n_sr=n_sr, n_cr=n_cr))
        # an NLL tolerance of 1e-10 fixes mu to about sqrt(2e-10) sigma_mu = 1.4e-5 sigma_mu (sigma_mu is about 1 here);
        # a first tolerance of 1e-6 was below that resolution (observed difference 5e-6)
        self.assertAlmostEqual(r["poi_hat"], mu, delta=5e-5)
        self.assertAlmostEqual(r["values"]["k_bkg"], k, delta=5e-5)

    def test_asimov_closure_with_contamination(self):
        truth = {"mu": 1.3, "k_bkg": 0.9}
        c = self.mc.asimov_closure(card(), card(), truth)
        self.assertEqual(c["status"], "pass", c)
        self.assertLess(abs(c["fitted"]["k_bkg"] - 0.9), 1e-4)
        self.assertLess(abs(c["pulls"]["lumi"]), 1e-3)

    def test_omitted_contamination_is_biased_and_detected(self):
        truth = {"mu": 1.3, "k_bkg": 0.9}
        c = self.mc.asimov_closure(card(contamination=False, minor=False), card(minor=False), truth)
        expected_bias = -1.3 * S_CR * B_SR / (B_CR * S_SR)            # k absorbs mu s_CR / b_CR
        self.assertAlmostEqual(c["bias"], expected_bias, delta=1e-5)
        self.assertEqual(c["status"], "fail")

    def test_refusals(self):
        dup = card()
        dup["samples"][-1]["modifiers"] = [{"type": "constrained-normalization", "parameter": "lumi_cr", "hi": 1.02, "lo": 0.98}]
        dup["constraints"].append({"parameter": "lumi_cr", "kind": "auxiliary-measurement", "aux_id": "lumi-run2", "form": "gaussian", "width": 0.02})
        prior = card()
        prior["constraints"][0]["kind"] = "prior"
        claim = card(contamination=False)
        claim["signal_contamination"] = "modeled"
        for doc, code in ((dup, "stats.duplicate_auxiliary"), (prior, "stats.prior_in_frequentist_model"),
                          (claim, "stats.contamination_not_in_model")):
            with self.assertRaises(self.mc.CardRefused) as cm:
                self.mc.to_pyhf(doc)
            self.assertIn(code, str(cm.exception))


class ModelCardContract(unittest.TestCase):
    def result(self, model_card):
        base = json.loads((ROOT / "contracts/fixtures/artifacts/valid/statres_frequentist.json").read_text())
        d = copy.deepcopy(base)
        d["contract_version"] = d["versions"]["contracts"] = CONTRACTS_VERSION
        d["extension"]["likelihood"]["model_card"] = model_card
        return validate_artifact(d)

    def test_contract_rules(self):
        self.assertTrue(self.result(card()).ok)
        dup = card()
        dup["constraints"].append(dict(dup["constraints"][0], parameter="lumi_cr"))
        rep = self.result(dup)
        self.assertIn("stats.duplicate_auxiliary", {f.code for f in rep.errors})
        rep = self.result(card(contamination=False))
        self.assertIn("stats.contamination_not_modeled", {f.code for f in rep.findings if f.severity == "unresolved"})
        bad = card()
        del bad["ensemble"]
        self.assertIn("schema.required", {f.code for f in self.result(bad).errors})


if __name__ == "__main__":
    unittest.main()
