"""theory:cr-secondary-antiprotons external benchmark (open question B2): Table VI of di Mauro et al., PRD 90 (2014)
085017, arXiv:1408.0288v3, against the profile's implementation of the same paper's closed-form parametrizations
(Eqs. (11)-(13), (B1)-(B2); Tables III-V, VII) with the proton flux of arXiv:1402.0321v2 Sec. 2.3. Tolerance per entry:
the paper's own Table VI relative error."""
import contextlib
import copy
import io
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import published_benchmark as pb  # noqa: E402

BENCH = json.loads((ROOT / "benchmarks" / "published-source-term-dimauro2014.json").read_text(encoding="utf-8"))
XS = json.loads((ROOT / "models" / "xs-dimauro2014-pp.json").read_text(encoding="utf-8"))


class TranscriptionTests(unittest.TestCase):
    """The transcribed numbers stay as printed (a change needs a new reading of the source)."""

    def test_table_vi_values(self):
        t = BENCH["table_vi"]
        self.assertEqual(BENCH["energies_gev"], [5.0, 10.0, 100.0, 500.0, 1000.0])
        self.assertEqual(t["eq11"]["q"], [1.23e-30, 4.31e-31, 1.70e-33, 2.42e-35, 3.13e-36])
        self.assertEqual(t["eq12"]["q"], [1.47e-30, 4.87e-31, 1.82e-33, 2.82e-35, 4.16e-36])
        self.assertEqual(t["eq13"]["q"], [1.67e-30, 5.17e-31, 1.77e-33, 3.39e-35, 6.83e-36])
        self.assertEqual(t["eq13"]["rel_error_percent"], [5.4, 4.8, 6.8, 8.8, 10.0])

    def test_parameter_tables(self):
        p = XS["parametrizations"]
        self.assertEqual(len(p["eq11"]["C"]), 6)
        self.assertEqual(len(p["eq12"]["C"]), 8)
        self.assertEqual(len(p["eq13"]["C"]), 11)
        self.assertEqual(p["eq13"]["C"][8], -1.822e-11)
        self.assertEqual(XS["sigma_in"]["elastic"]["eta2"], -4.65e-3)

    def test_published_inputs_are_labelled(self):
        self.assertFalse(XS["illustrative"])
        self.assertEqual(XS["source"], "crpb:S02")
        self.assertEqual(BENCH["source"]["table"], "Table VI")
        self.assertEqual(BENCH["source"]["access_date"], "2026-10-15")
        self.assertIn("1408.0288v3", BENCH["source"]["arxiv"])
        self.assertIn("1402.0321v2", BENCH["inputs"]["proton_flux"]["source"])


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required (requirements-core.txt)")
class PublishedBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = pb.benchmark(BENCH)
        cls.rows = {(r["form"], r["T_gev"]): r for r in cls.b["rows"]}

    def test_checks_pass(self):
        self.assertTrue(all(self.b["checks"].values()), self.b["checks"])

    def test_twelve_of_fifteen_entries_reproduced_within_the_paper_error(self):
        self.assertEqual(self.b["entries"], 15)
        self.assertEqual(self.b["reproduced_entries"], 12)
        for (form, t), r in self.rows.items():
            if t in BENCH["expected_status"]["reproduced"][form]:
                self.assertLessEqual(abs(r["rel_dev"]), r["tolerance"], r)

    def test_low_energy_entries_within_three_percent(self):
        for form in pb.FORMS:
            for t in (5.0, 10.0):
                self.assertLess(abs(self.rows[(form, t)]["rel_dev"]), 0.03, (form, t))

    def test_not_reproduced_entries_are_documented(self):
        doc = BENCH["expected_status"]["documented_not_reproduced"]
        for (form, t), r in self.rows.items():
            if r["status"] != "reproduced":
                self.assertIn(f"{form}@{t:g}", doc)
        self.assertGreater(abs(self.rows[("eq11", 1000.0)]["rel_dev"]), self.rows[("eq11", 1000.0)]["tolerance"])

    def test_upper_limit_converged_for_eq11_eq12_not_eq13(self):
        inp = BENCH["inputs"]
        for form in ("eq11", "eq12"):
            a = pb.source_term_pp(XS, inp, form, 1000.0, 1e6)
            b = pb.source_term_pp(XS, inp, form, 1000.0, 1e7)
            self.assertLess(abs(a / b - 1.0), 2e-3, form)
        a = pb.source_term_pp(XS, inp, "eq13", 1000.0, 1e6)
        b = pb.source_term_pp(XS, inp, "eq13", 1000.0, 1e7)
        self.assertGreater(abs(a / b - 1.0), 0.05)

    def test_linear_in_gas_density(self):
        inp = dict(BENCH["inputs"], n_H_cm3=2.0)
        q2 = pb.source_term_pp(XS, inp, "eq12", 10.0)
        self.assertAlmostEqual(q2 / self.rows[("eq12", 10.0)]["q_profile"], 2.0, delta=1e-9)

    def test_threshold(self):
        # below the pp threshold E_p = 7 m_p there is no antiproton
        self.assertEqual(pb.dsigma_de(XS, "eq12", 6.9 * pb.M_P_GEV, 2.0 * pb.M_P_GEV), 0.0)
        self.assertGreater(pb.dsigma_de(XS, "eq12", 50.0, 5.0), 0.0)

    def test_discrimination_wrong_flux_index_fails(self):
        bench = copy.deepcopy(BENCH)
        bench["inputs"]["proton_flux"]["P2"] = 2.70
        bad = pb.benchmark(bench)
        self.assertFalse(bad["checks"]["expected_entries_within_paper_error"])

    def test_cli_exit_zero(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            code = pb.main([])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["reproduced_entries"], 12)


if __name__ == "__main__":
    unittest.main()
