"""adapters/cr-propagation (WP13): DRAGON2 runs to grid-node predictions, the comparison gate, a tabulated-grid fit and
the limit benchmark against the closed-form 1D thin-disc model of theory:cr-secondary-ratio.

Offline (CI-safe, no DRAGON2, no network): everything runs on DRAGON2 outputs recorded on E2 on 2026-10-15
(tests/adapters/fixtures/cr_propagation/: nine runs, their run specs and computational-run records, the build record),
plus five diagnostic runs recorded on 2026-10-16 (radial boundary at 60 kpc; three of them with a local gas patch,
dragon2-gas-fixed-r.patch).
Live (HEP_DRAGON2_LIVE_TEST=1 with HEP_DRAGON2_BIN and HEP_DRAGON2_DATA): run X1 is rerun through dragon2_run.py and its
output must equal the recorded one (DRAGON2 is deterministic; relative 1e-6 allows for printf rounding only).

Criteria fixed before the comparison (limit-benchmark-plan.json, committed before any DRAGON2 B/C value was compared
with the closed form; the tolerances are not changed here):
- C1 absolute: X1 / closed form within 0.30 at every DRAGON2 node in 10-1000 GeV/n;
- C2 degeneracy: X2 / X1 and X3 / X1 (same D0/L) within 0.10 at the same nodes;
- C3 slope: d ln(B/C) / d ln(E/n) over 100-1000 GeV/n within 0.05 of the closed form;
- C4 grid fit: tabulated-grid on D0 in {2, 3, 4.5}e28 (L = 4 kpc) recovers the T_truth run's D0 = 3.6e28 within 0.05
  in ln D0, every node gated.
A check that fails is reported in benchmark-results.json and VALIDATION.md with its likely cause; its test then
asserts what is established (see the class docstrings), never a widened tolerance. Amendment of 2026-10-16 (a unit
correction, not a tolerance change): DRAGON2's columns are per total kinetic energy, and the converter now multiplies
each by its mass number A; C1 and C3 were recomputed on the same runs.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "cr-propagation"
CONVERT = ADAPTER / "assets" / "dragon2_to_prediction.py"
RUN = ADAPTER / "assets" / "dragon2_run.py"
FIX = Path(__file__).resolve().parent / "fixtures" / "cr_propagation"
PROFILE = ROOT / "profiles" / "theory" / "cr-secondary-ratio"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADAPTER / "assets"))

import dragon2_run  # noqa: E402
import dragon2_to_prediction as conv  # noqa: E402
import dragon2_translate  # noqa: E402
from contracts.comparison.gate import check as gate_check  # noqa: E402
from contracts.project import load_project  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

try:
    import numpy as np  # noqa: F401
    import scipy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:  # pragma: no cover
    HAVE_NUMPY = False

PLAN = json.loads((FIX / "limit-benchmark-plan.json").read_text(encoding="utf-8"))
RESULTS = json.loads((FIX / "benchmark-results.json").read_text(encoding="utf-8"))
NUM = ["NUC_5010", "NUC_5011"]
DEN = ["NUC_6012", "NUC_6013", "NUC_6014"]
OXY = ["NUC_8016", "NUC_8017", "NUC_8018"]
EDGES = [10.0, 17.7827941004, 31.6227766017, 56.2341325190, 100.0, 177.827941004, 316.227766017, 562.341325190, 1000.0]
LEVEL = "crsr:local-interstellar"
RUNS = ("X1", "X2", "X3", "G_low2", "G_low", "G_high", "G_high2", "T_truth", "D_X3_R30",
        "D_X1_R60", "D_X3_R60", "D_X1_R60_UG", "D_X2_R60_UG", "D_X3_R60_UG")
GRID = ("G_low2", "G_low", "X1", "G_high", "G_high2")
KPC_DZ = 0.02


def mentions_path(text, path):
    """Whether text names path as a whole path (not inside a longer one): with a home of /root, /opt/.../Cellar/root/
    is no match."""
    return re.search(r"(?<![\w./-])" + re.escape(str(path)) + r"(?![\w.-])", text) is not None


def spec(name):
    return json.loads((FIX / "specs" / f"{name}.json").read_text(encoding="utf-8"))


def output(name):
    return FIX / "outputs" / f"{name}.txt"


def record(name):
    return FIX / "runs" / f"{name}.computational-run.json"


def ratio_at_nodes(name, num=NUM, den=DEN, lo=10.0, hi=1000.0):
    e, cols = conv.read_output(output(name))
    r = conv.ratio(cols, num, den)
    sel = [i for i, x in enumerate(e) if lo <= x <= hi]
    return [e[i] for i in sel], [r[i] for i in sel]


def node_params(name):
    s = spec(name)
    d = s["diffusion"]
    return {"D0": d["D0_1e28"] * 1e28, "D0_unit": "cm^2 s^-1", "L": float(s["grid"]["L_kpc"]), "L_unit": "kpc",
            "delta": d["delta"], "R0_GV": d["DiffRefRig_GV"], "etaT": d["etaT"], "cross_sections": "illustrative-A"}


def convert(name, out_dir, edges=EDGES):
    out = Path(out_dir) / f"{name}.prediction.json"
    args = [sys.executable, "-I", str(CONVERT), "--txt", str(output(name)), "--numerator", ",".join(NUM),
            "--denominator", ",".join(DEN), "--edges", ",".join(str(x) for x in edges), "--level", LEVEL,
            "--run-record", str(record(name)), "--status", "synthetic", "--status", "unvalidated",
            "--artifact-id", f"dragon2-bc-node-{name}", "--out", str(out)]
    for k, v in node_params(name).items():
        args += ["--param", f"{k}={v}"]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=120)
    return proc, out


def profile_vocab():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "hep-research.project.json"
        p.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.10,<1.0", "experiments": [],
                                 "theory": [{"profile": "theory:cr-secondary-ratio", "version": "0.1.0"}]}))
        return Vocabulary.with_profiles(load_project(p).profiles)


def measurement_from(pred, components):
    """A SYNTHETIC dataset-record on the prediction's own observable (same bins, level and conventions)."""
    obs = json.loads(json.dumps(pred["extension"]["observable"]))
    vals = pred["extension"]["values"]
    return {"contract_version": "2.9.0", "artifact_id": "dragon2-synthetic-bc-data", "artifact_type": "dataset-record",
            "objective": "SYNTHETIC B/C data made from the DRAGON2 run T_truth (no noise)",
            "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": "0.11.0", "contracts": "2.9.0", "profiles": {}},
            "provenance": {"producer_skill": "hep-measurement", "created": "2026-10-15", "evidence_ids": []},
            "inputs": [], "outputs": [], "status": ["synthetic", "unvalidated"], "unresolved_inputs": [],
            "extension": {"dataset_id": "synthetic:dragon2-t-truth", "source_evidence_ids": [], "observable": obs,
                          "data": {"edges": vals["edges"], "values": vals["values"], "unit": "1",
                                   "uncertainties": components},
                          "covariance": {"status": "absent"}, "status": "synthetic"}}


# ------------------------------------------------------------------ closed form and DRAGON2's gas column

def bronf_ferr_column(r_kpc, l_kpc, dz=KPC_DZ):
    """Hydrogen nucleon column sum_l n(z_l) dz (kpc cm^-3) of DRAGON2's BronfFerr gas at radius r, on DRAGON2's own
    equidistant z grid of |z| <= L (formulas from DRAGON2 gas.cc, TH2Gas and THIGas, case BronfFerr; HII is 0 there;
    H2 already counts two nucleons)."""
    n = int(round(2 * l_kpc / dz)) + 1
    zs = [-l_kpc + i * dz for i in range(n)]
    h2_h = 0.059 if r_kpc > 2.5 else 0.015
    h2_n = 2.0 * (150.0 * math.exp(-((r_kpc - 0.05) / 0.2) ** 2) + 0.49 * math.exp(-((r_kpc - 5.3) / 2.2) ** 2)
                  + 0.24 * math.exp(-((r_kpc - 8.1) / 1.5) ** 2))
    if r_kpc < 2.5:
        hi_h = 0.045
    elif r_kpc < 8.5:
        hi_h = 0.115
    else:
        hi_h = 0.115 * math.exp((r_kpc - 8.5) / 6.7)
    if r_kpc < 3.0:
        hi_n = 0.57 * math.exp((r_kpc - 3.0) / 0.4) + 8.0 * math.exp(-(r_kpc / 0.2) ** 2)
    elif r_kpc < 13.0:
        hi_n = 0.57
    else:
        hi_n = 0.57 * math.exp(-(r_kpc - 13.0) / 4.0)
    return sum(h2_n * math.exp(-math.log(2) * (z / h2_h) ** 2) + hi_n * math.exp(-math.log(2) * (z / hi_h) ** 2)
               for z in zs) * dz


def closed_form(name, energies, r_oxygen):
    """The profile's thin-disc closed form (predict.thin_disc_ratio via evaluate) at DRAGON2's parameters, with
    h n_H = half DRAGON2's gas column at the observer and the observed O/C ratio of the same run at each energy."""
    sys.path.insert(0, str(PROFILE / "scripts"))
    import predict
    cfg = predict.load_json(predict.DEFAULT_CONFIG)
    s = spec(name)
    h = 0.1
    n_h = bronf_ferr_column(s["grid"]["observer_kpc"][0], s["grid"]["L_kpc"]) / (2 * h)
    over = {"D0_cm2_s": s["diffusion"]["D0_1e28"] * 1e28, "L_kpc": s["grid"]["L_kpc"], "delta": s["diffusion"]["delta"],
            "R0_GV": s["diffusion"]["DiffRefRig_GV"], "h_kpc": h, "n_H_cm3": n_h}
    out = []
    for e, r_o in zip(energies, r_oxygen):
        parents = [dict(p, observed_ratio_to_reference=(1.0 if p["name"] == "C" else r_o)) for p in cfg["parents"]]
        out.append(predict.evaluate(dict(cfg, parents=parents, energies_gev_per_n=[e]), over)["ratio"][0])
    return out


def slope(x, y):
    lx, ly = [math.log(v) for v in x], [math.log(v) for v in y]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    return sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)


def check_c1():
    e, bc = ratio_at_nodes("X1")
    _, oc = ratio_at_nodes("X1", OXY, DEN)
    cf = closed_form("X1", e, oc)
    return e, [b / c for b, c in zip(bc, cf)], bc, cf


def check_c2():
    e, x1 = ratio_at_nodes("X1")
    return e, {n: [a / b for a, b in zip(ratio_at_nodes(n)[1], x1)] for n in ("X2", "X3", "D_X3_R30")}


def he_to_h_ratio(e_gev_n, zi, ai, zf, af):
    """Python port of DRAGON2's TGalpropXSec::He_to_H_CS_ratio (xsec.cc, inherited from GALPROP), the factor DRAGON2
    applies to every tabulated production cross section as sigma (1 + 0.11 ratio); used only to size the helium term
    in the C1 report."""
    def fi(x, x1, x2, y1, y2):
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    en, d, am, z, f = [0.43, 0.73, 1.51], [2.45, 3.45, 4.40], [0.082, 0.047, 0.031], [6.0, 8.0, 26.0], [-0.76, -0.41, 1.0]
    if ai <= af:
        return 0.0
    if e_gev_n < en[1]:
        amu, delta = fi(e_gev_n, en[0], en[1], am[0], am[1]), fi(math.log(e_gev_n), math.log(en[0]), math.log(en[1]), d[0], d[1])
    else:
        amu, delta = fi(e_gev_n, en[1], en[2], am[1], am[2]), fi(math.log(e_gev_n), math.log(en[1]), math.log(en[2]), d[1], d[2])
    if e_gev_n < en[0]:
        amu, delta = am[0], d[0]
    if e_gev_n > en[2]:
        amu, delta = am[2], d[2]
    fz = fi(math.log(zi), math.log(z[0]), math.log(z[1]), f[0], f[1]) if zi < z[1] else \
        fi(math.log(zi), math.log(z[1]), math.log(z[2]), f[1], f[2])
    if zi - zf <= zi // 2:
        return math.exp(amu * abs(zi - zf - fz * delta) ** 1.43)
    x = math.exp(amu * abs(zi // 2 - fz * delta) ** 1.43)
    y = x - math.exp(amu * abs(zi // 2 - 1 - fz * delta) ** 1.43)
    b = (zi // 2) * y / x
    return x / (zi // 2) ** b * (zi - zf) ** b


def helium_production_factor(e_gev_n, r_oxygen):
    """Production-weighted helium enhancement (1 + 0.11 ratio) of the illustrative C->B and O->B channels."""
    c = 70.0 * (1 + 0.11 * he_to_h_ratio(e_gev_n, 6, 12, 5, 11))
    o = 35.0 * r_oxygen * (1 + 0.11 * he_to_h_ratio(e_gev_n, 8, 16, 5, 11))
    return (c + o) / (70.0 + 35.0 * r_oxygen)


def check_c3():
    e, bc = ratio_at_nodes("X1", lo=100.0)
    _, oc = ratio_at_nodes("X1", OXY, DEN, lo=100.0)
    return slope(e, bc), slope(e, closed_form("X1", e, oc))


# ------------------------------------------------------------------ tests

class RecordedEvidence(unittest.TestCase):
    """The fixtures are what the adapter declares: nine runs with specs, outputs whose SHA-256 match their run records,
    a build record, and every record a valid computational-run with the program version and commit in tools."""

    def test_records_validate_and_match_outputs(self):
        import hashlib
        build = json.loads((FIX / "dragon2-build.computational-run.json").read_text())
        for doc, name in [(build, "build")] + [(json.loads(record(n).read_text()), n) for n in RUNS]:
            with self.subTest(record=name):
                self.assertEqual([f.code for f in validate_artifact(doc).errors], [])
                ext = doc["extension"]
                self.assertEqual(ext["exit_status"], 0)
                self.assertTrue(any("cd588707fe03c76f19bda1b8092e136dcbe3fe90" in t["version"] for t in ext["tools"]
                                    if t["name"] == "DRAGON2"))
                self.assertFalse(mentions_path(json.dumps(doc), Path.home()), name)
        for n in RUNS:
            ext = json.loads(record(n).read_text())["extension"]
            self.assertEqual(ext["output_hashes"], {f"output/{n}.txt": hashlib.sha256(output(n).read_bytes()).hexdigest()})
            xml = dragon2_run.render_xml(dragon2_run.check_spec(spec(n)))
            self.assertIn(hashlib.sha256(xml.encode()).hexdigest(),
                          [i["sha256"] for i in ext["input_manifest"] if i["path"] == f"{n}.xml"])

    def test_adapter_declaration(self):
        doc = json.loads((ADAPTER / "adapter.json").read_text())
        tools = {t["name"].split(" ")[0]: t["status"] for t in doc["tools"]}
        self.assertEqual(tools, {"DRAGON2": "tested-in-declared-environment", "GALPROP": "proposed",
                                 "USINE": "tested-in-declared-environment"})  # USINE since cr-propagation B1
        self.assertEqual(doc["owner_skill"], "hep-computing")
        self.assertEqual(doc["status"], "proposed")


class RunSpec(unittest.TestCase):
    def test_spec_errors_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            bad = dict(spec("X1"), grid=dict(spec("X1")["grid"], dz_kpc=0.03))
            p = Path(td) / "bad.json"
            p.write_text(json.dumps(bad))
            proc = subprocess.run([sys.executable, "-I", str(RUN), "--spec", str(p), "--out", str(Path(td) / "r"),
                                   "--data-dir", td, "--prepare-only"], capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 2, proc.stdout)
            self.assertEqual(json.loads(proc.stdout)["status"], "error")

    def test_missing_program_exit_3(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data"
            data.mkdir()
            env = {k: v for k, v in os.environ.items() if k not in ("HEP_DRAGON2_BIN", "HEP_DRAGON2_DATA")}
            p = Path(td) / "s.json"
            s = dict(spec("X1"))
            s.pop("production_table")
            p.write_text(json.dumps(s))
            (Path(td) / "src.param").write_text("6012 3000 2.0 7. 2.35 165 2.15\n")
            proc = subprocess.run([sys.executable, "-I", str(RUN), "--spec", str(p), "--out", str(Path(td) / "r"),
                                   "--data-dir", str(data), "--source-param", str(Path(td) / "src.param"),
                                   "--dragon", str(Path(td) / "no-such-binary")], capture_output=True, text=True,
                                  timeout=60, env=env)
            self.assertEqual(proc.returncode, 3, proc.stdout)
            self.assertEqual(json.loads(proc.stdout)["status"], "missing-dependency")
            proc = subprocess.run([sys.executable, "-I", str(RUN), "--spec", str(p), "--out", str(Path(td) / "r")],
                                  capture_output=True, text=True, timeout=60, env=env)
            self.assertEqual(proc.returncode, 3, proc.stdout)

    def test_production_table_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            orig = Path(td) / dragon2_run.TABLE_NAME
            orig.write_text('"header\n    8.16     6.12\t10.000\t1.0\t0.0\tx\n    8.16     6.12\t20.000\t1.0\t0.0\tx\n'
                            '    6.12     5.11\t10.000\t50.0\t0.0\tx\n')
            target = Path(td) / "new.dat"
            n = dragon2_run.write_table(orig, target, spec("X1")["production_table"])
            rows = [ln.split() for ln in target.read_text().splitlines()[1:]]
            self.assertEqual(n, 6)
            self.assertEqual([r[:4] for r in rows[:2]], [["8.16", "6.12", "10.000", "0.000000"],
                                                         ["8.16", "6.12", "20.000", "0.000000"]])
            self.assertIn(["6.12", "5.11", "20.000", "70.000000"], [r[:4] for r in rows])
            self.assertIn(["8.16", "5.11", "10.000", "35.000000"], [r[:4] for r in rows])


@unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed")
class Converter(unittest.TestCase):
    """Converter output: a valid grid-node prediction that passes the gate against a measurement on the same
    observable, and fails it against one in other bins; refusals exit 2."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.preds = {}
        for n in RUNS:
            proc, out = convert(n, cls.tmp.name)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            cls.preds[n] = json.loads(out.read_text())
        cls.vocab = profile_vocab()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_predictions_validate(self):
        for n, doc in self.preds.items():
            with self.subTest(run=n):
                self.assertEqual([f.code for f in validate_artifact(doc, self.vocab).errors], [])
                ext = doc["extension"]
                self.assertEqual(ext["representation"], "grid")
                self.assertEqual(ext["parameter_point"]["D0"], spec(n)["diffusion"]["D0_1e28"] * 1e28)
                self.assertEqual(ext["values"]["edges"], EDGES)
                self.assertIn("synthetic", doc["status"])
                self.assertEqual(doc["inputs"][0]["artifact_id"], f"dragon2-run-{n}")

    def test_cli_validate(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "hep-research.project.json"
            project.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.10,<1.0",
                                           "experiments": [], "theory": [{"profile": "theory:cr-secondary-ratio",
                                                                          "version": "0.1.0"}]}))
            proc = subprocess.run([sys.executable, str(ROOT / "contracts" / "validate.py"),
                                   str(Path(self.tmp.name) / "X1.prediction.json"), "--profiles-from", str(project)],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertTrue(json.loads(proc.stdout)["ok"], proc.stdout)

    def test_ratio_is_per_nucleon(self):
        """DRAGON2's ASCII output is its internal density per total kinetic energy (dragon.cc writes
        GetFluxAtSunPosition, which computes weight = A but does not apply it; particle.cc scales the spallation source
        by A_parent / A_daughter). A ratio at equal E/n weights every NUC column by its mass number A."""
        cols = {"NUC_5011": [1.0, 2.0], "NUC_6012": [4.0, 4.0], "NUC_6013": [0.0, 1.0], "Pri_p": [3.0, 3.0]}
        self.assertEqual(conv.ratio(cols, ["NUC_5011"], ["NUC_6012", "NUC_6013"]),
                         [11.0 / 48.0, 22.0 / (48.0 + 13.0)])
        self.assertEqual(conv.ratio(cols, ["Pri_p"], ["NUC_6012"]), [3.0 / 48.0, 3.0 / 48.0])
        with self.assertRaisesRegex(conv.ConvertError, "mass number"):
            conv.ratio({"Sec_e+": [1.0], "NUC_6012": [1.0]}, ["Sec_e+"], ["NUC_6012"])
        e, raw = conv.read_output(output("X1"))
        unweighted = [sum(cols_) for cols_ in zip(*(raw[c] for c in NUM))]
        den = [sum(cols_) for cols_ in zip(*(raw[c] for c in DEN))]
        _, r = ratio_at_nodes("X1", lo=0.0, hi=1e9)
        # boron is 11B only here, carbon almost all 12C: the per-nucleon B/C is 11/12 of the raw column ratio
        for a, n, d in zip(r, unweighted, den):
            self.assertAlmostEqual(a / (n / d), 11.0 / 12.0, delta=2e-3)

    def test_bin_average_matches_nodes(self):
        e, r = ratio_at_nodes("X1", lo=0.0, hi=1e9)
        lo, hi = e[10], e[11]
        avg = conv.bin_average(e, r, [lo, hi])[0]
        # ln(ratio) linear in ln(E) between two nodes: the ln-average lies between the node values
        self.assertTrue(min(r[10], r[11]) <= avg <= max(r[10], r[11]))
        exact = (r[11] - r[10]) / math.log(r[11] / r[10])  # mean of exp(linear) over the bin, in closed form
        self.assertAlmostEqual(avg / exact, 1.0, places=10)

    def test_gate(self):
        meas = measurement_from(self.preds["T_truth"], [])
        for n, doc in self.preds.items():
            with self.subTest(run=n):
                res = gate_check(doc, meas, {"measurement_conditions": doc["extension"]["parameter_point"]})
                self.assertTrue(res["comparable"], res.get("mismatches"))
        other = json.loads(json.dumps(meas))
        other["extension"]["observable"]["variables"][0]["edges"] = [10.0, 100.0, 1000.0]
        other["extension"]["data"].update(edges=[10.0, 100.0, 1000.0], values=[0.06, 0.02])
        res = gate_check(self.preds["X1"], other, {"measurement_conditions": self.preds["X1"]["extension"]["parameter_point"]})
        self.assertFalse(res["comparable"])

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "p.json"
            common = [sys.executable, "-I", str(CONVERT), "--txt", str(output("X1")), "--denominator", "NUC_6012",
                      "--param", "D0=1", "--out", str(target)]
            cases = {"outside range": ["--numerator", "NUC_5011", "--level", LEVEL, "--edges", "0.1,10"],
                     "unknown column": ["--numerator", "NUC_9999", "--level", LEVEL, "--edges", "10,100"],
                     "no level": ["--numerator", "NUC_5011", "--edges", "10,100"],
                     "hash mismatch": ["--numerator", "NUC_5011", "--level", LEVEL, "--edges", "10,100",
                                       "--run-record", str(record("X2"))]}
            for what, extra in cases.items():
                with self.subTest(case=what):
                    proc = subprocess.run(common + extra, capture_output=True, text=True, timeout=60)
                    self.assertEqual(proc.returncode, 2, proc.stdout)
                    self.assertEqual(json.loads(proc.stdout)["status"], "error")
                    self.assertFalse(target.exists())


@unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed")
class LimitBenchmark(unittest.TestCase):
    """C1-C3 of limit-benchmark-plan.json on the recorded runs. The numbers this code computes must equal the recorded
    benchmark-results.json, and each verdict must be what the declared tolerance gives. Outcome on E2 (2026-10-15,
    C1 and C3 recomputed 2026-10-16 after the per-nucleon correction): C1 and C3 pass; C2 fails its declared
    tolerance, and its test asserts what is established instead: the L = 2 run agrees within 2% while the L = 8 run is
    low, and the diagnostic run with the radial boundary moved from 20 to 30 kpc moves it towards X1 (the attribution
    is in Diagnostics)."""

    def test_plan_was_declared_first(self):
        self.assertTrue(PLAN["declared_before_comparison"])
        self.assertEqual([c["id"] for c in PLAN["checks"]], ["C1-absolute", "C2-degeneracy", "C3-slope", "C4-grid-fit"])
        self.assertEqual([a["check"] for a in PLAN.get("amendments", [])], ["C4-grid-fit", "C1-absolute"])

    def test_c1_absolute(self):
        e, rel, _, _ = check_c1()
        rec = RESULTS["C1-absolute"]
        self.assertEqual([round(x, 3) for x in e], [round(x, 3) for x in rec["energies_gev_per_n"]])
        for a, b in zip(rel, rec["dragon2_over_closed_form"]):
            self.assertAlmostEqual(a, b, places=6)
        self.assertEqual(max(abs(x - 1) for x in rel) <= 0.30, rec["passed"])
        if not rec["passed"]:
            self.assertTrue(all(x > 1 for x in rel))
            _, oc = ratio_at_nodes("X1", OXY, DEN)
            residual = [x / helium_production_factor(en, r) for x, en, r in zip(rel, e, oc)]
            for a, b in zip(residual, rec["after_dividing_dragon2_helium_production_term"]):
                self.assertAlmostEqual(a, b, places=6)
            self.assertTrue(all(x > 1.10 for x in residual))

    def test_c2_degeneracy(self):
        _, ratios = check_c2()
        rec = RESULTS["C2-degeneracy"]
        for n in ("X2", "X3", "D_X3_R30"):
            for a, b in zip(ratios[n], rec["ratio_to_X1"][n]):
                self.assertAlmostEqual(a, b, places=6)
        dev = max(abs(x - 1) for n in ("X2", "X3") for x in ratios[n])
        self.assertEqual(dev <= 0.10, rec["passed"])
        if not rec["passed"]:
            self.assertLessEqual(max(abs(x - 1) for x in ratios["X2"]), 0.10)
            moved = [abs(b - 1) < abs(a - 1) for a, b in zip(ratios["X3"], ratios["D_X3_R30"])]
            self.assertEqual(all(moved), rec["radial_boundary_moves_X3_towards_X1"])

    def test_c3_slope(self):
        s_d, s_c = check_c3()
        rec = RESULTS["C3-slope"]
        self.assertAlmostEqual(s_d, rec["dragon2"], places=6)
        self.assertAlmostEqual(s_c, rec["closed_form"], places=6)
        self.assertEqual(abs(s_d - s_c) <= 0.05, rec["passed"])

    def test_recorded_verdicts(self):
        """The verdicts committed with the adapter; changing one needs a new recorded run and report."""
        self.assertEqual({k: RESULTS[k]["passed"] for k in ("C1-absolute", "C2-degeneracy", "C3-slope", "C4-grid-fit")},
                         RESULTS["expected_verdicts"])


@unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed")
class Diagnostics(unittest.TestCase):
    """Diagnostic runs of 2026-10-16 (no tolerance declared in advance; they attribute the C2 failure and test the 1D
    limit). With the radial boundary at 60 kpc and the gas uniform in R (local patch dragon2-gas-fixed-r.patch, so not
    DRAGON2 as released), DRAGON2 reaches the thin-disc closed form: X2/X1 and X3/X1 within 2%, and DRAGON2 / closed
    form within 5% after its helium production term at L = 2, 4 and 8. With the real gas and the boundary at 60 kpc,
    X3/X1 is within 10%: the radial boundary at 20 kpc is the main cause of the C2 failure."""

    def ratios(self, a, b):
        return [x / y for x, y in zip(ratio_at_nodes(a)[1], ratio_at_nodes(b)[1])]

    def test_recorded_numbers(self):
        rec = RESULTS["diagnostics"]
        for a, b in zip(self.ratios("D_X3_R60", "D_X1_R60"), rec["real_gas_rmax60"]["X3_over_X1"]):
            self.assertAlmostEqual(a, b, places=6)
        for key, num in (("X2_over_X1", "D_X2_R60_UG"), ("X3_over_X1", "D_X3_R60_UG")):
            for a, b in zip(self.ratios(num, "D_X1_R60_UG"), rec["uniform_gas_rmax60"][key]):
                self.assertAlmostEqual(a, b, places=6)

    def test_radial_boundary_is_the_main_cause_of_c2(self):
        self.assertTrue(all(abs(x - 1) <= 0.10 for x in self.ratios("D_X3_R60", "D_X1_R60")))

    def test_one_dimensional_limit(self):
        for n in ("D_X2_R60_UG", "D_X3_R60_UG"):
            self.assertTrue(all(abs(x - 1) <= 0.02 for x in self.ratios(n, "D_X1_R60_UG")), n)
        for n in ("D_X1_R60_UG", "D_X2_R60_UG", "D_X3_R60_UG"):
            e, bc = ratio_at_nodes(n)
            _, oc = ratio_at_nodes(n, OXY, DEN)
            after = [b / c / helium_production_factor(en, r) for b, c, en, r in zip(bc, closed_form(n, e, oc), e, oc)]
            for a, b in zip(after, RESULTS["diagnostics"]["uniform_gas_rmax60"]["after_dividing_dragon2_helium_production_term"][n]):
                self.assertAlmostEqual(a, b, places=6)
            self.assertTrue(all(abs(x - 1) <= 0.05 for x in after), n)

    def test_gas_patch_is_recorded(self):
        patch = (FIX / "dragon2-gas-fixed-r.patch").read_text(encoding="utf-8")
        self.assertEqual(patch.count("DRAGON_GAS_FIXED_R"), 4)
        for n in ("D_X1_R60_UG", "D_X2_R60_UG", "D_X3_R60_UG"):
            tools = json.loads(record(n).read_text(encoding="utf-8"))["extension"]["tools"]
            self.assertIn("dragon2-gas-fixed-r.patch", tools[0]["version"])


def grid_fit_c4(td):
    sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))
    import covariance_fit as cf
    preds = {}
    for n in GRID + ("T_truth",):
        proc, out = convert(n, td)
        if proc.returncode != 0:
            raise AssertionError(proc.stdout + proc.stderr)
        preds[n] = json.loads(out.read_text())
    y = preds["T_truth"]["extension"]["values"]["values"]
    comps = [{"name": "stat", "kind": "statistical", "correlation": "uncorrelated", "values": [0.03 * v for v in y]},
             {"name": "scale", "kind": "systematic", "correlation": "fully-correlated", "values": [0.02 * v for v in y]}]
    meas = measurement_from(preds["T_truth"], comps)
    fixed = {k: v for k, v in preds["X1"]["extension"]["parameter_point"].items() if k != "D0"}
    return cf.grid_fit({"model": "tabulated-grid", "measurement": meas, "predictions": [preds[n] for n in GRID],
                        "grid": {"parameters": [{"name": "D0", "scale": "log"}]},
                        "gate_plan": {"measurement_conditions": fixed}})


@unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed")
class GridFit(unittest.TestCase):
    """C4 (as amended before it ran): covariance_fit.py model tabulated-grid consumes the converter's artifacts
    unchanged; five D0 nodes (factor 1.5 apart, L = 4 kpc), data = the T_truth run (D0 = 3.6e28)."""

    def test_tabulated_grid_recovers_d0(self):
        with tempfile.TemporaryDirectory() as td:
            out = grid_fit_c4(td)
        self.assertEqual(out["gate"], {"predictions_gated": len(GRID), "comparable": len(GRID)})
        par = out["fits"][0]["parameters"][0]
        rec = RESULTS["C4-grid-fit"]
        self.assertAlmostEqual(par["best_fit"], rec["D0_fit"], delta=1e-6 * rec["D0_fit"])
        self.assertEqual(abs(math.log(par["best_fit"] / 3.6e28)) <= 0.05, rec["passed"])

# ------------------------------------------------------------------ D1 (cr-propagation r4): DRAGON2 physics items

D1_FIX = FIX / "dragon2"
D1_ITEMS = ("isotopic", "convection", "decay", "reacceleration", "losses")
D1_CLOSED_FORM_ITEMS = ("convection", "decay")  # items with a B2 closed form
D1_USINE_ITEMS = ("convection", "decay", "reacceleration", "losses")  # D1-1a: every item against USINE (B1)
# recorded runs: name -> (item file, gas override); losses run on Galprop gas (BronfFerr's n_HII = 0 makes DRAGON2's
# nuclear Coulomb loss diverge), so its item-off run is the isotopic item on Galprop gas
D1_RUNS = {"isotopic": ("isotopic", None), "convection": ("convection", None), "decay": ("decay", None),
           "reacceleration": ("reacceleration", None), "losses": ("losses", None), "losses_off": ("isotopic", "Galprop")}
D1_ITEM_OFF = {"losses": "losses_off"}  # every other item's item-off run is "isotopic"
D1_TOLERANCE = 0.03  # D1-1, frozen in acceptance.json and VALIDATION CRPROP-D1 before the runs
BORON_CARBON_RIGIDITY_EDGES = [2.0 * 500.0 ** (k / 16) for k in range(17)]  # 16 log-uniform bins, 2-1000 GV
BERYLLIUM_EKN_EDGES = [0.05 * 200.0 ** (k / 12) for k in range(13)]  # 12 log-uniform bins, 0.05-10 GeV/n
D1_OBSERVABLES = {"B/C": (NUM, DEN, BORON_CARBON_RIGIDITY_EDGES, "rigidity"),
                  "10Be/9Be": (["NUC_4010"], ["NUC_4009"], BERYLLIUM_EKN_EDGES, "ekn")}
D1_SECONDARIES = {"7Be": 4007, "9Be": 4009, "10Be": 4010, "10B": 5010, "11B": 5011}


def d1_spec(item):
    return json.loads((D1_FIX / "specs" / f"D1_{item}.json").read_text(encoding="utf-8"))


def d1_output(item):
    return D1_FIX / "outputs" / f"D1_{item}.txt"


def d1_record(item):
    return D1_FIX / "runs" / f"D1_{item}.computational-run.json"


def d1_closed_form_columns(item):
    """The run's columns with every secondary replaced by the B2 closed form (convection_decay.network_mid_plane) at
    each DRAGON2 energy node: parents 12C and 16O from the same run (per E/n), the run's D0, delta, R0, L, V_c, decay
    switch, the isotopic ILLUSTRATIVE set, h = 0.1 kpc and n_H = DRAGON2's BronfFerr column at the observer / (2 h).
    Values go back to DRAGON2's per-total-kinetic-energy unit (divided by A), so the same reader applies."""
    sys.path.insert(0, str(PROFILE / "scripts"))
    import convection_decay as cd
    import predict
    s = d1_spec(item)
    t = s["transport"]
    energies, cols = conv.read_output(d1_output(item))
    h = 0.1
    n_h = bronf_ferr_column(s["grid"]["observer_kpc"][0], s["grid"]["L_kpc"], dz=s["grid"]["dz_kpc"]) / (2 * h)
    decay_on = bool(t["decay"]["enabled"])
    secondaries = [
        {"name": "7Be", "Z": 4, "A": 7, "stable_assumption": "fully stripped 7Be (r3 P6); DRAGON2 keeps naked "
                                                             "electron-capture nuclei stable"},
        {"name": "9Be", "Z": 4, "A": 9},
        dict({"name": "10Be", "Z": 4, "A": 10}, **({"decay": {"mode": "beta-", "daughter": "10B"}} if decay_on else
                                                   {"stable_assumption": "decay off in this item"})),
        {"name": "10B", "Z": 5, "A": 10},
        {"name": "11B", "Z": 5, "A": 11},
    ]
    cfg = {"parents": [{"name": "C", "Z": 6, "A": 12, "observed_ratio_to_reference": 1.0},
                       {"name": "O", "Z": 8, "A": 16, "observed_ratio_to_reference": 1.0}],
           "secondaries": secondaries,
           "transport": {"D0_cm2_s": t["diffusion"]["D0_cm2_s"], "R0_GV": t["diffusion"]["R0_gv"],
                         "delta": t["diffusion"]["delta"], "L_kpc": t["geometry"]["L_kpc"], "h_kpc": h,
                         "n_H_cm3": n_h, "V_c_kms": t["convection"]["V_c_kms"]},
           "cross_section_set": "models/xs-illustrative-decay.json"}
    xs = predict.load_cross_sections(cfg)
    params = cd.model_parameters(cfg)
    out = {k: list(v) for k, v in cols.items()}
    for i, e_n in enumerate(energies):
        c12, o16 = 12.0 * cols["NUC_6012"][i], 16.0 * cols["NUC_8016"][i]
        cfg_i = dict(cfg, parents=[dict(cfg["parents"][0]), dict(cfg["parents"][1], observed_ratio_to_reference=o16 / c12)])
        dens = cd.network_mid_plane(params, e_n, cfg_i, xs)["density"]
        for name, uid in D1_SECONDARIES.items():
            out[f"NUC_{uid}"][i] = dens[name] * c12 / (uid % 1000)
    return energies, out


def d1_ratios(energies, cols):
    return {obs: conv.ratio_of_bin_integrals(energies, cols, num, den, edges, axis)
            for obs, (num, den, edges, axis) in D1_OBSERVABLES.items()}


def d1_comparison():
    """D1-1 per closed-form item: DRAGON2 / closed form per bin and the item-effect diagnostic against the item-off
    run (harmonized-v1-isotopic), for B/C (rigidity) and 10Be/9Be (ekn)."""
    dragon = {i: d1_ratios(*conv.read_output(d1_output(i))) for i in ("isotopic",) + D1_CLOSED_FORM_ITEMS}
    closed = {i: d1_ratios(*d1_closed_form_columns(i)) for i in ("isotopic",) + D1_CLOSED_FORM_ITEMS}
    out = {}
    for item in ("isotopic",) + D1_CLOSED_FORM_ITEMS:
        rows = {}
        for obs in D1_OBSERVABLES:
            ratio = [d / c for d, c in zip(dragon[item][obs], closed[item][obs])]
            effect = [(d / d0) / (c / c0) for d, d0, c, c0 in zip(dragon[item][obs], dragon["isotopic"][obs],
                                                                   closed[item][obs], closed["isotopic"][obs])]
            dev = max(abs(r - 1) for r in ratio)
            eff_dev = max(abs(r - 1) for r in effect)
            rows[obs] = {"dragon2": dragon[item][obs], "closed_form": closed[item][obs], "dragon2_over_closed": ratio,
                         "max_abs_deviation": dev, "passed": dev <= D1_TOLERANCE,
                         "item_effect_passed": eff_dev <= D1_TOLERANCE,
                         "item_effect_dragon2": [d / d0 for d, d0 in zip(dragon[item][obs], dragon["isotopic"][obs])],
                         "item_effect_closed": [c / c0 for c, c0 in zip(closed[item][obs], closed["isotopic"][obs])],
                         "item_effect_ratio": effect, "item_effect_max_abs_deviation": max(abs(r - 1) for r in effect)}
        out[item] = rows
    return out


def d1_usine_comparison():
    """D1-1a (item effects) and D1-1b (offsets) against USINE: DRAGON2 / USINE per bin (USINE's numbers from B1's
    usine/usine-results.json, computed from the same harmonized-v1-<item>.json on the same bins) and the item effect,
    each code's ratio with the item over its ratio without it (DRAGON2's losses item against its Galprop-gas item-off
    run, USINE's against d1-isotopic)."""
    u = json.loads((FIX / "usine" / "usine-results.json").read_text(encoding="utf-8"))
    dragon = {r: d1_ratios(*conv.read_output(d1_output(r))) for r in D1_RUNS}
    out = {}
    for item in ("isotopic",) + D1_USINE_ITEMS:
        off = D1_ITEM_OFF.get(item, "isotopic")
        rows = {}
        for obs in D1_OBSERVABLES:
            ref, ref0 = u["runs"][f"d1-{item}"][obs], u["runs"]["d1-isotopic"][obs]
            ratio = [d / r for d, r in zip(dragon[item][obs], ref)]
            effect = [(d / d0) / (r / r0) for d, d0, r, r0 in zip(dragon[item][obs], dragon[off][obs], ref, ref0)]
            dev, eff_dev = max(abs(x - 1) for x in ratio), max(abs(x - 1) for x in effect)
            rows[obs] = {"dragon2": dragon[item][obs], "usine": ref, "dragon2_over_usine": ratio,
                         "dragon2_item_off_run": off, "max_abs_deviation": dev, "passed": dev <= D1_TOLERANCE,
                         "item_effect_dragon2": [d / d0 for d, d0 in zip(dragon[item][obs], dragon[off][obs])],
                         "item_effect_usine": [r / r0 for r, r0 in zip(ref, ref0)],
                         "item_effect_ratio": effect, "item_effect_max_abs_deviation": eff_dev,
                         "item_effect_passed": eff_dev <= D1_TOLERANCE}
        out[item] = rows
    return out

class D1Items(unittest.TestCase):
    """cr-propagation D1: every item has its harmonized-v1-<item>.json, a translated run spec and a recorded run (D1-2);
    the closed-form items are compared with B2 (D1-1, recomputed offline from the recorded outputs and checked against
    d1-item-results.json; the verdict is whatever the recorded numbers give, never a widened tolerance)."""

    def test_item_files_are_transport_blocks(self):
        from contracts.schema import validate
        sch = json.loads((ROOT / "contracts" / "schemas" / "ext_theory_spec.json").read_text(encoding="utf-8"))
        base = json.loads((FIX / "specs" / "harmonized-v1-isotopic.json").read_text(encoding="utf-8"))["transport"]
        for item in D1_ITEMS:
            with self.subTest(item=item):
                doc = json.loads((FIX / "specs" / f"harmonized-v1-{item}.json").read_text(encoding="utf-8"))
                rep = validate(doc["transport"], sch["properties"]["transport"], Vocabulary())
                self.assertTrue(rep.ok, [e.as_dict() for e in rep.errors][:3])
                changed = sorted(k for k in base if base[k] != doc["transport"][k])
                self.assertEqual(changed, {"isotopic": [], "convection": ["convection"], "decay": ["decay"],
                                           "reacceleration": ["reacceleration"], "losses": ["losses"]}[item])

    def test_runs_are_recorded_and_translated_from_the_item_files(self):  # D1-2
        import hashlib
        channels = json.loads((D1_FIX / "channels-illustrative-decay.json").read_text(encoding="utf-8"))
        for item, (source, gas) in D1_RUNS.items():
            with self.subTest(item=item):
                s = d1_spec(item)
                doc = json.loads((FIX / "specs" / f"harmonized-v1-{source}.json").read_text(encoding="utf-8"))
                # DRAGON2's own sources stated (K3): harmonized-v1's injection variable and abundances are refused
                again = dragon2_translate.spec_from_transport(dragon2_translate.with_dragon2_sources(doc["transport"]),
                                                              s["name"], channels, z_range=(4, 8),
                                                              ekn_range_gev=(0.04, 2000.0), gas_model=gas)
                self.assertEqual(again, s)
                rec = json.loads(d1_record(item).read_text(encoding="utf-8"))
                self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
                ext = rec["extension"]
                self.assertEqual(ext["exit_status"], 0)
                self.assertEqual(ext["output_hashes"],
                                 {f"output/D1_{item}.txt": hashlib.sha256(d1_output(item).read_bytes()).hexdigest()})
                xml = dragon2_run.render_xml(dragon2_run.check_spec(s))
                self.assertIn(hashlib.sha256(xml.encode()).hexdigest(),
                              [i["sha256"] for i in ext["input_manifest"] if i["path"] == f"D1_{item}.xml"])
                self.assertTrue(any("cd588707fe03c76f19bda1b8092e136dcbe3fe90" in t["version"] for t in ext["tools"]
                                    if t["name"] == "DRAGON2"))
                self.assertFalse(mentions_path(json.dumps(rec), Path.home()), item)

    def test_translator_records_what_dragon2_cannot_express(self):
        s = d1_spec("reacceleration")
        self.assertEqual(s["flags"]["reacc_flag"], 1)
        # A1R convention: USINE thin disc (D_pp constant 4/3) -> DRAGON2 Ptuskin94 whole halo (1): V_A sqrt(4 h / L)
        self.assertAlmostEqual(s["reacceleration"]["vA_kms"], 50.0 * math.sqrt(4 * 0.1 / 4.0), places=5)
        self.assertTrue(any("transport_conventions.py reacceleration" in x and "relative error bound" in x
                            for x in s["substitutes"]))
        self.assertEqual(d1_spec("losses")["flags"]["eloss_flag"], 1)
        self.assertEqual(d1_spec("convection")["convection"], {"v0_kms": 10.0, "dvdz_kmskpc": 0.0})
        for item in D1_RUNS:
            gas = "Galprop" if item.startswith("losses") else "BronfFerr"
            self.assertEqual(d1_spec(item)["galaxy"]["gas"], gas)
            self.assertTrue(any(f": {gas} (" in x for x in d1_spec(item)["substitutes"]))
        t = json.loads((FIX / "specs" / "harmonized-v1-losses.json").read_text(encoding="utf-8"))["transport"]
        with self.assertRaisesRegex(dragon2_run.SpecError, "diverges"):  # D1-L: losses on HII-free gas refused
            dragon2_run.spec_from_transport(t, "x", {"6012->5011": 1.0}, z_range=(4, 8), ekn_range_gev=(0.1, 10.0),
                                            gas_model="BronfFerr")
        with self.assertRaises(dragon2_run.SpecError):
            t = json.loads((FIX / "specs" / "harmonized-v1-isotopic.json").read_text(encoding="utf-8"))["transport"]
            t = dict(t, diffusion=dict(t["diffusion"], breaks=[{"kind": "low", "R_break_gv": 5.0}]))
            dragon2_run.spec_from_transport(t, "x", {"6012->5011": 1.0}, z_range=(4, 8), ekn_range_gev=(0.1, 10.0))

    def test_decay_half_life_is_nubase(self):
        from core.constants.physical import half_life_seconds
        self.assertEqual(d1_spec("decay")["half_lives_s"]["4010"], half_life_seconds("Be-10")["value"])
        self.assertNotIn("half_lives_s", d1_spec("isotopic"))

    @unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed")
    def test_closed_form_comparison_matches_the_record(self):  # D1-1
        got = d1_comparison()
        rec = json.loads((D1_FIX / "d1-item-results.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["tolerance"], D1_TOLERANCE)
        for item, rows in got.items():
            for obs, row in rows.items():
                with self.subTest(item=item, observable=obs):
                    want = rec["items"][item][obs]
                    for key in ("dragon2", "closed_form", "dragon2_over_closed", "item_effect_ratio"):
                        for a, b in zip(row[key], want[key]):
                            self.assertTrue(math.isclose(a, b, rel_tol=1e-9), (key, a, b))
                    self.assertEqual(row["passed"], want["passed"])
                    self.assertEqual(row["passed"], row["max_abs_deviation"] <= D1_TOLERANCE)
                    self.assertEqual(row["item_effect_passed"], want["item_effect_passed"])

    @unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed")
    def test_usine_comparison_matches_the_record(self):  # D1-1, reacceleration and losses
        u = json.loads((FIX / "usine" / "usine-results.json").read_text(encoding="utf-8"))
        self.assertEqual(u["bc_rigidity_edges_gv"], BORON_CARBON_RIGIDITY_EDGES)
        self.assertEqual(u["be_ekn_edges_gev"], BERYLLIUM_EKN_EDGES)
        got = d1_usine_comparison()
        rec = json.loads((D1_FIX / "d1-item-results.json").read_text(encoding="utf-8"))["usine_items"]
        for item, rows in got.items():
            for obs, row in rows.items():
                with self.subTest(item=item, observable=obs):
                    want = rec[item][obs]
                    for key in ("dragon2", "usine", "dragon2_over_usine", "item_effect_ratio"):
                        for a, b in zip(row[key], want[key]):
                            self.assertTrue(math.isclose(a, b, rel_tol=1e-9), (key, a, b))
                    self.assertEqual(row["passed"], want["passed"])
                    self.assertEqual(row["item_effect_passed"], want["item_effect_passed"])
                    self.assertEqual(row["item_effect_passed"], row["item_effect_max_abs_deviation"] <= D1_TOLERANCE)

    def test_ratio_of_bin_integrals(self):
        """P2: a ratio of bin integrals, not the bin average of the ratio; P3: isotopes at equal rigidity."""
        e = [0.05 * 1.2 ** i for i in range(80)]
        cols = {"NUC_6012": [x ** -2.7 / 12 for x in e], "NUC_5011": [0.3 * x ** -3.2 / 11 for x in e]}
        got = conv.ratio_of_bin_integrals(e, cols, ["NUC_5011"], ["NUC_6012"], [1.0, 10.0], "ekn")[0]
        want = (0.3 * (1.0 ** -2.2 - 10.0 ** -2.2) / 2.2) / ((1.0 ** -1.7 - 10.0 ** -1.7) / 1.7)
        self.assertAlmostEqual(got / want, 1.0, places=12)
        r = conv.ratio_of_bin_integrals(e, cols, ["NUC_5011"], ["NUC_6012"], [2.0, 20.0], "rigidity")[0]
        lo_b, hi_b = conv.ekn_from_rigidity(2.0, 5, 11), conv.ekn_from_rigidity(20.0, 5, 11)
        lo_c, hi_c = conv.ekn_from_rigidity(2.0, 6, 12), conv.ekn_from_rigidity(20.0, 6, 12)
        num = 0.3 * (lo_b ** -2.2 - hi_b ** -2.2) / 2.2
        den = (lo_c ** -1.7 - hi_c ** -1.7) / 1.7
        self.assertAlmostEqual(r / (num / den), 1.0, places=12)
        with self.assertRaises(conv.ConvertError):
            conv.ratio_of_bin_integrals(e, cols, ["NUC_5011"], ["NUC_6012"], [0.01, 1.0], "ekn")


# ------------------------------------------------------------------ D1 provider entrypoint (cr-provider/1)

import dragon2_provider  # noqa: E402
from tests.core.provider_conformance import ProviderConformance  # noqa: E402

PROVIDER = ADAPTER / "assets" / "dragon2_provider.py"
PROVIDER_REQUEST = {
    "protocol": "cr-provider/1", "provider": "dragon2", "provider_version": dragon2_provider.declaration()["version"],
    "points": [{"D0_cm2_s": 3.0e28, "delta": 0.5, "L_kpc": 4.0}],
    "observables": [{"id": "B/C", "axis": "ekn", "unit": "GeV/n", "bins": [[10.0, 31.6227766017], [31.6227766017, 100.0]]}],
    "want": ["lis"], "seed": None}


def live_dragon2_reason():
    if os.environ.get("HEP_DRAGON2_LIVE_TEST") != "1":
        return "live DRAGON2 runs: set HEP_DRAGON2_LIVE_TEST=1, HEP_DRAGON2_BIN and HEP_DRAGON2_DATA"
    if not (os.environ.get("HEP_DRAGON2_BIN") and Path(os.environ["HEP_DRAGON2_BIN"]).is_file()
            and os.environ.get("HEP_DRAGON2_DATA") and Path(os.environ["HEP_DRAGON2_DATA"]).is_dir()):
        return "DRAGON2 not installed (HEP_DRAGON2_BIN or HEP_DRAGON2_DATA unset or missing)"
    return None


class Dragon2ProviderConformance(ProviderConformance, unittest.TestCase):
    """D1-PRV-1 and D1-PRV-2: C1's conformance mixin on the DRAGON2 provider (about five DRAGON2 runs of under a
    minute each on E2; skipped unless the live test is asked for and DRAGON2 is installed)."""
    PROVIDER_ID = "dragon2"
    REQUEST = PROVIDER_REQUEST
    VOCAB_PROFILES = (PROFILE / "profile.json",)
    TIMEOUT_S = 3600.0

    def unavailable_reason(self):
        return live_dragon2_reason()


class Dragon2ProviderOffline(unittest.TestCase):
    """The provider's parts that need no DRAGON2: its built-in transport and cross sections equal the fixtures they
    stand for, the run ranges cover every bin, a point is written into its block, a missing DRAGON2 fails the point
    with provider-error (R4) and another production set is refused."""

    def test_defaults_equal_their_sources(self):
        iso = json.loads((FIX / "specs" / "harmonized-v1-isotopic.json").read_text(encoding="utf-8"))
        self.assertEqual(dragon2_provider.DEFAULT_TRANSPORT, dragon2_translate.with_dragon2_sources(iso["transport"]))
        self.assertEqual(dragon2_provider.ILLUSTRATIVE_CHANNELS_MB,
                         json.loads((D1_FIX / "channels-illustrative-decay.json").read_text(encoding="utf-8")))
        xs = json.loads((PROFILE / "models" / "xs-illustrative-decay.json").read_text(encoding="utf-8"))
        uid = {"C": 6012, "O": 8016, **{k: v for k, v in D1_SECONDARIES.items()}}
        self.assertEqual({f"{uid[a]}->{uid[b]}": v for k, v in xs["production_mb"].items() for a, b in [k.split("->")]},
                         dragon2_provider.ILLUSTRATIVE_CHANNELS_MB)

    def test_declaration_and_ranges(self):
        decl = dragon2_provider.declaration()
        self.assertEqual(decl["id"], "dragon2")
        self.assertEqual(decl["version"], json.loads((ADAPTER / "adapter.json").read_text())["version"])
        self.assertEqual(set(decl["observables"]), set(dragon2_provider.OBSERVABLES))
        self.assertEqual(set(decl["domain"]), set(dragon2_provider.POINT_TARGETS))
        zr, er = dragon2_provider.run_ranges([{"id": "B/C", "axis": "rigidity", "unit": "GV", "bins": [[2.0, 1000.0]]},
                                              {"id": "10Be/9Be", "axis": "ekn", "unit": "GeV/n", "bins": [[0.05, 10.0]]}])
        self.assertEqual(zr, (4, 8))
        self.assertLessEqual(er[0], 0.05)
        self.assertGreaterEqual(er[1], conv.ekn_from_rigidity(1000.0, 6, 12))
        t = dragon2_provider.transport_for({}, {"V_c_kms": 5.0, "L_kpc": 6.0})
        self.assertEqual((t["convection"]["V_c_kms"], t["geometry"]["L_kpc"]), (5.0, 6.0))
        with self.assertRaisesRegex(ValueError, "ILLUSTRATIVE isotopic"):
            other = dict(dragon2_provider.DEFAULT_TRANSPORT, cross_sections={"production_set": "Evoli2019"})
            dragon2_provider.transport_for({"transport": other}, {})

    def test_losses_run_on_gas_with_ionized_hydrogen(self):
        """D1-L: with losses on, the provider's run uses Galprop gas (DRAGON2's nuclear Coulomb loss diverges where
        n_HII = 0), and the reacceleration speed goes through transport_conventions (A1R)."""
        t = dict(dragon2_provider.DEFAULT_TRANSPORT, losses=["ionization", "coulomb"])
        spec_l = dragon2_run.spec_from_transport(dragon2_provider.transport_for({"transport": t}, {}), "x",
                                                 dragon2_provider.ILLUSTRATIVE_CHANNELS_MB, z_range=(5, 8),
                                                 ekn_range_gev=(1.0, 100.0))
        self.assertEqual((spec_l["galaxy"]["gas"], spec_l["flags"]["eloss_flag"]), ("Galprop", 1))
        spec_r = dragon2_run.spec_from_transport(dragon2_provider.transport_for({}, {"V_A_kms": 30.0}), "y",
                                                 dragon2_provider.ILLUSTRATIVE_CHANNELS_MB, z_range=(5, 8),
                                                 ekn_range_gev=(1.0, 100.0))
        self.assertAlmostEqual(spec_r["reacceleration"]["vA_kms"], 30.0 * math.sqrt(4 * 0.1 / 4.0), places=5)

    def test_missing_dragon2_is_a_failed_point(self):
        env = {k: v for k, v in os.environ.items() if k not in ("HEP_DRAGON2_BIN", "HEP_DRAGON2_DATA")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory() as td:
            req, resp = Path(td) / "req.json", Path(td) / "resp.json"
            req.write_text(json.dumps(PROVIDER_REQUEST))
            proc = subprocess.run([sys.executable, str(PROVIDER), "--request", str(req), "--response", str(resp)],
                                  capture_output=True, text=True, timeout=120, env=env)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            doc = json.loads(resp.read_text())
            self.assertEqual(doc["status"], "failed")
            self.assertEqual(doc["results"][0]["reason"], "provider-error")
            self.assertIn("HEP_DRAGON2_BIN", doc["results"][0]["detail"])
            self.assertNotIn("predictions", doc["results"][0])


@unittest.skipUnless(os.environ.get("HEP_DRAGON2_LIVE_TEST") == "1", "live DRAGON2 run: set HEP_DRAGON2_LIVE_TEST=1, "
                     "HEP_DRAGON2_BIN and HEP_DRAGON2_DATA")
class LiveDragon2(unittest.TestCase):
    """Reruns X1 (about 2.5 minutes on E2) and compares the output with the recorded one."""

    def test_rerun_x1_reproduces_the_recorded_output(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "X1"
            proc = subprocess.run([sys.executable, "-I", str(RUN), "--spec", str(FIX / "specs" / "X1.json"),
                                   "--out", str(out), "--record", str(Path(td) / "X1.run.json")],
                                  capture_output=True, text=True, timeout=3600)
            self.assertEqual(proc.returncode, 0, proc.stdout)
            e_new, c_new = conv.read_output(out / "output" / "X1.txt")
            e_old, c_old = conv.read_output(output("X1"))
            self.assertEqual(e_new, e_old)
            for col in NUM + DEN + OXY:
                for a, b in zip(c_new[col], c_old[col]):
                    self.assertTrue(math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-300), (col, a, b))
            self.assertEqual([f.code for f in validate_artifact(json.loads((Path(td) / "X1.run.json").read_text())).errors], [])
            shutil.rmtree(out, ignore_errors=True)


# ------------------------------------------------------------------ B1 (cr-propagation r4): USINE tool and provider

import hashlib  # noqa: E402

import usine_provider  # noqa: E402
import usine_to_prediction as usine_reader  # noqa: E402
import usine_translate  # noqa: E402

USINE_FIX = FIX / "usine"
USINE_RUNS = ("harmonized-v1", "d1-isotopic", "d1-convection", "d1-decay", "d1-reacceleration", "d1-losses",
              "b1-slab-all-items")
USINE_PROVIDER = ADAPTER / "assets" / "usine_provider.py"
USINE_READER = ADAPTER / "assets" / "usine_to_prediction.py"
USINE_LIVE_RTOL = 1e-6  # B1-2, frozen in acceptance.json and VALIDATION CRPROP-B1 before the runs
USINE_READER_RTOL = {"Ekn": 1e-4, "R": 2e-3}  # CRPROP-B1 reader check, fixed before the comparison


def usine_spec(name):
    return json.loads((USINE_FIX / "specs" / f"{name}.json").read_text(encoding="utf-8"))


def usine_translation(name):
    s = usine_spec(name)
    return usine_translate.translate(s["transport"], name, s["ekn_range_gev"])


def usine_tables(name):
    t = usine_translation(name)
    return usine_reader.read_run(USINE_FIX / "outputs" / name, t["model"], t["species"])


def live_usine_reason():
    if os.environ.get("HEP_USINE_LIVE_TEST") != "1":
        return "live USINE runs: set HEP_USINE_LIVE_TEST=1, HEP_USINE_BIN and HEP_USINE_DATA"
    if not (os.environ.get("HEP_USINE_BIN") and Path(os.environ["HEP_USINE_BIN"]).is_file()
            and os.environ.get("HEP_USINE_DATA") and Path(os.environ["HEP_USINE_DATA"]).is_dir()):
        return "USINE not installed (HEP_USINE_BIN or HEP_USINE_DATA unset or missing)"
    return None


class UsineTranslator(unittest.TestCase):
    """B1 translator, offline: the built-in ILLUSTRATIVE sets and parent ratios equal their profile sources, every
    recorded run's inputs are what the translator writes today from its spec, the records validate and hash the
    committed outputs, and what USINE cannot express is recorded or refused."""

    def test_illustrative_sets_equal_the_profile(self):
        for key, xs in usine_translate.ILLUSTRATIVE_SETS.items():
            with self.subTest(set=key):
                src = json.loads((PROFILE / "models" / f"{key}.json").read_text(encoding="utf-8"))
                self.assertEqual(xs["production_mb"], src["production_mb"])
                self.assertEqual(xs["inelastic_mb"], src["inelastic_mb"])
                self.assertEqual(src["target"].split()[0], "hydrogen")
        bench = json.loads((PROFILE / "benchmarks" / "bc-benchmark.json").read_text(encoding="utf-8"))
        self.assertEqual({p["name"]: p["observed_ratio_to_reference"] for p in bench["parents"]},
                         usine_translate.PARENT_RATIOS)

    def test_unit_constants(self):
        self.assertTrue(math.isclose(usine_translate.KPC2_PER_MYR_CM2_S, 3.0172e29, rel_tol=1e-4))
        # USINE's own km/s -> kpc/Myr factor in its shipped Kpp formulae is 1.022712e-3
        self.assertTrue(math.isclose(usine_translate.KPC_PER_MYR_PER_KM_S, 1.022712e-3, rel_tol=1e-6))

    def test_specs_render_to_the_recorded_inputs(self):
        hv1 = json.loads((FIX / "specs" / "harmonized-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(usine_spec("harmonized-v1")["transport"], hv1["transport"])
        for name in USINE_RUNS:
            with self.subTest(run=name):
                files = usine_translate.render(usine_translation(name), "<TOOL_HOME>/inputs", "<RUN_DIR>")
                for fname, text in files.items():
                    self.assertEqual(text, (USINE_FIX / "inputs" / name / fname).read_text(encoding="utf-8"), fname)

    def test_records_validate_and_hash_the_outputs(self):
        for name in USINE_RUNS:
            with self.subTest(run=name):
                rec = json.loads((USINE_FIX / "runs" / f"{name}.computational-run.json").read_text(encoding="utf-8"))
                self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
                self.assertEqual(rec["status"], ["unvalidated"])
                ext = rec["extension"]
                outputs = {f"out/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted((USINE_FIX / "outputs" / name).iterdir())}
                self.assertEqual(ext["output_hashes"], outputs)
                self.assertEqual(sorted(outputs), sorted(f"out/{f}" for f in
                                                         usine_translate.expected_outputs(usine_translation(name))))
                self.assertEqual(sorted(i["path"] for i in ext["input_manifest"]),
                                 sorted(usine_translate.render(usine_translation(name), "", "")))
                self.assertTrue(any("fb53006db41d1a640bf1b5af1a4b0f899ca59673" in t["version"] for t in ext["tools"]
                                    if t["name"] == "USINE"))
                self.assertFalse(mentions_path(json.dumps(rec), Path.home()), name)

    def test_translator_records_what_usine_cannot_express(self):
        t = usine_translation("harmonized-v1")
        self.assertEqual(t["model"], "Model2DKisoVc")
        self.assertEqual((t["geometry"]["L"], t["geometry"]["h"], t["geometry"]["R"]), (4.0, 0.1, 20.0))
        self.assertEqual(t["gas_cm3"], {"HI": 1.0, "HII": 0.0, "H2": 0.0, "He": 0.0})
        self.assertEqual(t["production_mb"], {"12C->11B": 70.0, "16O->11B": 35.0})
        for needle in ("observer at r = 8.3 kpc", "He_to_H_number 0.1: not used", "on 12C, 16O and 11B",
                       "uniform in r up to radius_kpc"):
            self.assertTrue(any(needle in x for x in t["substitutes"]), needle)
        slab = usine_translation("b1-slab-all-items")
        self.assertEqual(slab["model"], "Model1DKisoVc")
        # whole-halo V_A by transport_conventions' zone conversion (A1R): sqrt(L/(3h)) at first order (B1X rerun)
        self.assertAlmostEqual(slab["transport_pars"]["Va"], 5.0 * math.sqrt(5.0 / (3 * 0.1)), places=6)
        conv = slab["reacceleration_conversion"]
        self.assertEqual(conv["conversion_status"], "approximate")
        self.assertAlmostEqual(conv["relative_error_bound"], (1 + conv["lam_max"]) / 5, places=12)
        self.assertTrue(any("sqrt(L/(3h))" in x and "relative_error_bound" in x for x in slab["substitutes"]))
        own = usine_spec("b1x-init-test")["transport"]
        with self.assertRaisesRegex(usine_translate.SpecError, "whole-halo"):
            usine_translate.translate(dict(own, reacceleration=dict(own["reacceleration"], zone="whole-halo")), "x",
                                      (1.0, 10.0))
        self.assertTrue(slab["switches"]["IsELossAdiabatic"] and slab["switches"]["IsDecayBETA"])
        self.assertFalse(slab["switches"]["IsDecayEC"])
        self.assertIn("(1+(Rl1/Rig)^((delta-dl1)/sl1))^sl1", slab["K_formula"])
        self.assertEqual(slab["beta_unstable"], ["10Be"])
        self.assertTrue(math.isclose(slab["transport_pars"]["K0"] * usine_translate.KPC2_PER_MYR_CM2_S, 3.0e28,
                                     rel_tol=1e-14))
        base = usine_spec("d1-isotopic")["transport"]
        refused = {
            "gradient": dict(base, convection={"V_c_kms": 5.0, "dVc_dz_kms_per_kpc": 1.0}),
            "high break": dict(base, diffusion=dict(base["diffusion"], breaks=[{"kind": "high", "R_break_gv": 300.0,
                                                                              "delta_below": 0.5, "s": 0.1}])),
            "other set": dict(base, cross_sections={"production_set": "GALPROP opt12"}),
            "unknown loss": dict(base, losses=["synchrotron"]),
            "kind": dict(base, geometry={"kind": "sphere", "L_kpc": 4.0}),
            "gas": dict(base, gas={"model": "BronfFerr"}),
            "two slopes": dict(base, sources=dict(base["sources"], injection=[{"gamma": 2.3}, {"gamma": 2.4}])),
            "zone": dict(base, reacceleration=dict(base["reacceleration"], V_A_kms=10.0, zone="halo-only")),
        }
        for why, tr in refused.items():
            with self.subTest(refused=why), self.assertRaises(usine_translate.SpecError):
                usine_translate.translate(tr, "x", (1.0, 10.0))

    def test_cost_record(self):  # B1-4: the USINE row of CRPROP-COST comes from this record
        rec = json.loads((FIX / "cost" / "usine-harmonized-v1.computational-run.json").read_text(encoding="utf-8"))
        self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
        res = rec["extension"]["resources"]
        self.assertEqual(len(res["runs"]), 3)
        self.assertEqual(res["median_wall_s"], sorted(r["wall_s"] for r in res["runs"])[1])
        self.assertEqual(res["median_peak_rss_bytes"], sorted(r["peak_rss_bytes"] for r in res["runs"])[1])
        conv = res["grid_convergence"]
        for key in ("energy_grid_doubled", "spatial_doubled", "both_doubled"):
            self.assertGreaterEqual(conv[key], 0.0)
        self.assertFalse(mentions_path(json.dumps(rec), Path.home()))

    def test_energy_grid(self):
        g = usine_translate.energy_grid((0.04, 2000.0))
        n = g["points_per_decade"]
        self.assertLessEqual(g["ekn_min_gev"], 0.8 * 0.04)
        self.assertGreaterEqual(g["ekn_max_gev"], 1.25 * 2000.0)
        self.assertAlmostEqual((g["n_points"] - 1) / n, math.log10(g["ekn_max_gev"] / g["ekn_min_gev"]), places=9)
        g = usine_translate.energy_grid((50.0, 100.0))
        self.assertLessEqual(g["ekn_min_gev"], usine_translate.NORM_EKN_GEV)

    def test_half_life_check(self):
        spec = usine_translation("d1-decay")
        with tempfile.TemporaryDirectory() as td:
            chart = Path(td) / usine_translate.CHART_FILE
            line = " 10.01   4  10  10Be        BETA  2.500  ||  {hl} 0.012 Myr   10B   |   0.  0.  XXX  ---  ||  0  |\n"
            chart.write_text("# test chart (written here)\n" + line.format(hl="1.387"), encoding="utf-8")
            self.assertIn("NUBASE2020", usine_translate.check_half_lives(spec, Path(td))[0])
            chart.write_text(line.format(hl="1.51"), encoding="utf-8")
            with self.assertRaisesRegex(usine_translate.SpecError, "differs from NUBASE2020"):
                usine_translate.check_half_lives(spec, Path(td))
        self.assertEqual(usine_translate.check_half_lives(usine_translation("d1-isotopic"), Path("/nonexistent")), [])


class UsineReader(unittest.TestCase):
    """B1 reader, offline: ratios of bin integrals (r3 P2), isotopes on the data's axis (P3), units read and checked
    (P11); checked against USINE's own element-ratio tables of every recorded run."""

    def test_reader_matches_usine_element_ratios(self):
        for name in USINE_RUNS:
            t = usine_translation(name)
            tables = usine_tables(name)
            for quantity, obs in (("B/C", "B/C"), ("10BE/9BE", "10Be/9Be")):
                if obs == "10Be/9Be" and "10Be" not in t["species"]:
                    continue
                for axis, kind in (("Ekn", "ekn"), ("R", "rigidity")):
                    with self.subTest(run=name, ratio=obs, axis=axis):
                        xs, ys, meta = usine_reader.read_table(USINE_FIX / "outputs" / name /
                                                               usine_reader.table_name(quantity, t["model"], axis))
                        lo, hi = tables["12C" if obs == "B/C" else "9Be"][0][0], tables["10B" if obs == "B/C"
                                                                                       else "10Be"][0][-1]
                        dev = []
                        for x, y in zip(xs, ys):
                            try:
                                dev.append(abs(usine_reader.point_ratio(tables, obs, x, kind) / y - 1.0))
                            except usine_reader.ReadError:  # a rigidity node outside one isotope's table
                                pass
                        self.assertGreater(len(dev), 0.8 * len(xs), (lo, hi))
                        self.assertLessEqual(max(dev), USINE_READER_RTOL[axis])

    def test_results_file_is_recomputed(self):
        res = json.loads((USINE_FIX / "usine-results.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(res["runs"]), sorted(USINE_RUNS))
        for name in USINE_RUNS:
            tables = usine_tables(name)
            with self.subTest(run=name):
                # relative 1e-12 against the recorded numbers: libm differs across platforms in the last digits
                got = usine_reader.ratio_of_bin_integrals(tables, "B/C", res["bc_rigidity_edges_gv"], "rigidity")
                assert_close_tree(self, got, res["runs"][name]["B/C"], "B/C", rel=1e-12)
                if "10Be/9Be" in res["runs"][name]:
                    got = usine_reader.ratio_of_bin_integrals(tables, "10Be/9Be", res["be_ekn_edges_gev"], "ekn")
                    assert_close_tree(self, got, res["runs"][name]["10Be/9Be"], "10Be/9Be", rel=1e-12)

    def test_ratio_of_bin_integrals_power_law(self):
        e = [0.01 * 1.25 ** i for i in range(90)]
        tables = {"12C": (e, [x ** -2.7 for x in e]), "11B": (e, [0.3 * x ** -3.2 for x in e]), "10B": (e, [0.0] * 90)}
        got = usine_reader.ratio_of_bin_integrals(tables, "B/C", [1.0, 10.0], "ekn")[0]
        want = (0.3 * (1.0 ** -2.2 - 10.0 ** -2.2) / 2.2) / ((1.0 ** -1.7 - 10.0 ** -1.7) / 1.7)
        self.assertAlmostEqual(got / want, 1.0, places=12)
        got = usine_reader.ratio_of_bin_integrals(tables, "B/C", [2.0, 20.0], "rigidity")[0]
        lo_b, hi_b = (usine_reader.ekn_from_rigidity(r, 5, 11) for r in (2.0, 20.0))
        lo_c, hi_c = (usine_reader.ekn_from_rigidity(r, 6, 12) for r in (2.0, 20.0))
        want = (0.3 * (lo_b ** -2.2 - hi_b ** -2.2) / 2.2) / ((lo_c ** -1.7 - hi_c ** -1.7) / 1.7)
        self.assertAlmostEqual(got / want, 1.0, places=12)
        self.assertAlmostEqual(usine_reader.rigidity_from_ekn(usine_reader.ekn_from_rigidity(7.0, 6, 12), 6, 12), 7.0,
                               places=12)
        with self.assertRaises(usine_reader.ReadError):
            usine_reader.ratio_of_bin_integrals(tables, "B/C", [0.001, 1.0], "ekn")
        with self.assertRaises(usine_reader.ReadError):  # no beryllium in this network
            usine_reader.ratio_of_bin_integrals(tables, "Be/B", [1.0, 10.0], "ekn")

    def test_read_table_refuses_other_units_and_modulation(self):
        good = USINE_FIX / "outputs" / "d1-isotopic" / usine_reader.table_name("12C", "Model2DKisoVc")
        text = good.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            for why, bad in (("unit", text.replace("[GeV/n m^{2} s sr]^{-1}", "[GeV m^{2} s sr]^{-1}")),
                             ("modulated", text.replace("phi0.00GV", "phi0.50GV")),
                             ("columns", text.replace("e-0", "e-0 1", 1).replace("# Ekn", "# Ekn", 1))):
                with self.subTest(refused=why):
                    path = Path(td) / good.name
                    path.write_text(bad, encoding="utf-8")
                    with self.assertRaises(usine_reader.ReadError):
                        usine_reader.read_isotope(Path(td), "12C", "Model2DKisoVc")

    def test_reader_cli_writes_a_prediction(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "run"
            shutil.copytree(USINE_FIX / "outputs" / "d1-decay", run / "out")
            (run / "translation.json").write_text(json.dumps(usine_translation("d1-decay")), encoding="utf-8")
            proc = subprocess.run([sys.executable, "-I", str(USINE_READER), "--run-dir", str(run), "--observable",
                                   "10Be/9Be", "--axis", "ekn", "--edges", "0.1,1,10", "--param", "D0_cm2_s=3e28",
                                   "--out", str(Path(td) / "p.json")], capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            pred = json.loads((Path(td) / "p.json").read_text(encoding="utf-8"))
        want = usine_reader.ratio_of_bin_integrals(usine_tables("d1-decay"), "10Be/9Be", [0.1, 1.0, 10.0], "ekn")
        self.assertEqual(pred["values"]["values"], want)
        self.assertEqual(pred["representation"], "numerical")
        self.assertEqual(pred["parameter_point"]["usine_run"], "d1-decay")


USINE_REQUEST = {
    "protocol": "cr-provider/1", "provider": "usine", "provider_version": usine_provider.declaration()["version"],
    "points": [{"D0_cm2_s": 3.0e28, "delta": 0.5, "L_kpc": 4.0}],
    "observables": [{"id": "B/C", "axis": "rigidity", "unit": "GV", "bins": [[2.0, 20.0], [20.0, 200.0]]},
                    {"id": "10Be/9Be", "axis": "ekn", "unit": "GeV/n", "bins": [[0.1, 1.0], [1.0, 10.0]]}],
    "want": ["lis"], "seed": None}
FAKE_USINE = """#!{python}
# Offline stand-in for the usine executable (adapter tests only): copies the recorded tables of one run into the
# output folder named on the command line; it computes nothing and ignores the initialisation file.
import shutil, sys
from pathlib import Path
src = Path({src!r})
out = Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
for path in src.iterdir():
    shutil.copyfile(path, out / path.name)
sys.exit(1)
"""


class UsineProviderOffline(unittest.TestCase):
    """The provider's parts that need no USINE: its built-in transport equals the fixture it stands for, the run range
    covers every bin, a point is written into its block, a missing USINE fails the point with provider-error (R4),
    another cross-section set is refused, and with a stand-in executable replaying the d1-isotopic tables its
    predictions are the reader's ratios of those tables."""

    def test_defaults_and_declaration(self):
        self.assertEqual(usine_provider.DEFAULT_TRANSPORT, usine_spec("d1-isotopic")["transport"])
        decl = usine_provider.declaration()
        self.assertEqual(decl["id"], "usine")
        self.assertEqual(decl["version"], json.loads((ADAPTER / "adapter.json").read_text())["version"])
        self.assertEqual(set(decl["observables"]), set(usine_reader.OBSERVABLES))
        read = set(usine_provider.POINT_TARGETS) | set(usine_provider.LOW_BREAK_TARGETS)
        patterned = {n for n in decl["domain"] if usine_provider.PHI_NAME.fullmatch(n) or usine_provider.XS_NAME.fullmatch(n)}
        self.assertEqual(set(decl["domain"]), read | patterned)
        self.assertTrue(read <= set(decl["domain"]))
        lo, hi = usine_provider.ekn_range(USINE_REQUEST["observables"], ["9Be", "10Be", "10B", "11B", "12C"])
        self.assertEqual(lo, 0.1)
        self.assertEqual(hi, max(usine_reader.ekn_from_rigidity(200.0, z, a) for z, a in ((5, 10), (5, 11), (6, 12))))
        t, notes = usine_provider.transport_for({}, {"V_c_kms": 5.0, "L_kpc": 6.0, "eta": -0.5})
        self.assertEqual(notes, [])
        self.assertEqual((t["convection"]["V_c_kms"], t["geometry"]["L_kpc"], t["diffusion"]["eta"]), (5.0, 6.0, -0.5))

    def _call(self, request, env):
        with tempfile.TemporaryDirectory() as td:
            req, resp = Path(td) / "req.json", Path(td) / "resp.json"
            req.write_text(json.dumps(request))
            proc = subprocess.run([sys.executable, str(USINE_PROVIDER), "--request", str(req), "--response", str(resp)],
                                  capture_output=True, text=True, timeout=300, env=env)
            return proc, json.loads(resp.read_text())

    def test_missing_usine_is_a_failed_point(self):
        env = {k: v for k, v in os.environ.items() if k not in ("HEP_USINE_BIN", "HEP_USINE_DATA")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc, doc = self._call(USINE_REQUEST, env)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(doc["status"], "failed")
        self.assertEqual(doc["results"][0]["reason"], "provider-error")
        self.assertIn("HEP_USINE_BIN", doc["results"][0]["detail"])
        self.assertNotIn("predictions", doc["results"][0])

    def test_replayed_tables_give_the_reader_ratios(self):
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "bin" / "usine"
            fake.parent.mkdir()
            fake.write_text(FAKE_USINE.format(python=sys.executable, src=str(USINE_FIX / "outputs" / "d1-isotopic")))
            fake.chmod(0o755)
            env = dict(os.environ, HEP_USINE_BIN=str(fake), HEP_USINE_DATA=td, PYTHONDONTWRITEBYTECODE="1")
            env.pop("HEP_USINE_RUN_DIR", None)
            proc, doc = self._call(USINE_REQUEST, env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            other = dict(usine_provider.DEFAULT_TRANSPORT, cross_sections={"production_set": "GALPROP opt12"})
            proc2, refused = self._call(dict(USINE_REQUEST, transport=other), env)
        res = doc["results"][0]
        tables = usine_tables("d1-isotopic")
        for pred, obs in zip(res["predictions"], USINE_REQUEST["observables"]):
            edges = [obs["bins"][0][0]] + [b for _, b in obs["bins"]]
            self.assertEqual(pred["values"]["values"],
                             usine_reader.ratio_of_bin_integrals(tables, obs["id"], edges, obs["axis"]))
        self.assertEqual(res["labels"], ["synthetic", "unvalidated"])
        self.assertEqual(res["evaluation"]["numerical_tolerance"], usine_provider.NUMERICAL_TOLERANCE)
        self.assertEqual(proc2.returncode, 1)
        self.assertEqual(refused["results"][0]["reason"], "provider-error")
        self.assertIn("ILLUSTRATIVE", refused["results"][0]["detail"])


class UsineProviderConformance(ProviderConformance, unittest.TestCase):
    """B1-PRV-1 and B1-PRV-2: C1's conformance mixin on the USINE provider (about six USINE runs of a few seconds each
    on E2; skipped unless the live test is asked for and USINE is installed)."""
    PROVIDER_ID = "usine"
    REQUEST = USINE_REQUEST
    VOCAB_PROFILES = (PROFILE / "profile.json",)
    TIMEOUT_S = 3600.0

    def unavailable_reason(self):
        return live_usine_reason()


@unittest.skipUnless(os.environ.get("HEP_USINE_LIVE_TEST") == "1", "live USINE runs: set HEP_USINE_LIVE_TEST=1, "
                     "HEP_USINE_BIN and HEP_USINE_DATA")
class LiveUsine(unittest.TestCase):
    """B1-2: every recorded run is translated again from its spec, run with the installed USINE, and each table must
    reproduce the recorded one within relative 1e-6 (USINE is deterministic; the tables have 6 significant digits).
    With HEP_USINE_LIVE_TEST=1 but no USINE installed, the test fails instead of skipping."""

    def test_reruns_reproduce_the_recorded_outputs(self):
        self.assertIsNone(live_usine_reason())
        binary, data_dir = Path(os.environ["HEP_USINE_BIN"]), Path(os.environ["HEP_USINE_DATA"])
        with tempfile.TemporaryDirectory() as td:
            for name in USINE_RUNS:
                with self.subTest(run=name):
                    spec = usine_translation(name)
                    res = usine_translate.run_usine(spec, Path(td) / name, binary, data_dir)
                    self.assertTrue(res["ok"], res["log_tail"])
                    rec = usine_translate.record(spec, res, binary)
                    self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
                    for fname in usine_translate.expected_outputs(spec):
                        rerun = usine_reader.read_table(Path(td) / name / "out" / fname)
                        recorded = usine_reader.read_table(USINE_FIX / "outputs" / name / fname)
                        self.assertEqual(rerun[0], recorded[0], fname)
                        for a, b in zip(rerun[1], recorded[1]):
                            self.assertTrue(math.isclose(a, b, rel_tol=USINE_LIVE_RTOL, abs_tol=1e-300),
                                            (fname, a, b))


# ------------------------------------------------------------------ B3 (cr-propagation r4): harmonized comparison

B3_FIX = FIX / "b3"
# frozen in acceptance.json: B3-1 (superseded for B3's verdict by B3-1a/b/c, decisions.md A1.10), B3-1a, B3-1c, B3-2
B3_TOL = {"B3-1": 0.02, "B3-1a": 0.02, "B3-1c": 0.005, "B3-2": 0.005}


def load_b3_study():
    """b3_study.py loaded from its file (no fixture folder added to sys.path)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("b3_study", B3_FIX / "b3_study.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def b3_results():
    return json.loads((B3_FIX / "b3-results.json").read_text(encoding="utf-8"))


@unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed by the closed forms")
class B3HarmonizedComparison(unittest.TestCase):
    """B3, offline: the closed forms of theory:cr-secondary-ratio against the recorded USINE V3.5 nominal runs
    (b3/outputs/), recomputed from the committed tables; the decomposition check (B3-2) and the channel flags (B3-3)
    from the recorded results (the 170 response and rerun runs are indexed by the sha256 of their table data lines in
    b3-run-index.json, their tables kept outside the repository). B3-1 is superseded for B3's verdict by B3-1a, B3-1b
    and B3-1c (decisions.md A1.10)."""

    @classmethod
    def setUpClass(cls):
        cls.b3 = load_b3_study()
        cls.res = b3_results()

    def tables(self, cfg):
        spec = json.loads((B3_FIX / "runs" / f"{cfg}-nom.computational-run.json").read_text(encoding="utf-8"))
        model = "Model2DKisoVc" if "-2d" in cfg else "Model1DKisoVc"
        species = [n.split("_")[2] for n in spec["extension"]["output_hashes"] if "_Ekn_" in n]
        names = {s.upper(): s for s in usine_translate.translate(self.b3.load_spec(cfg)["transport"], cfg,
                                                                  (0.04, 2000.0))["species"]}
        return usine_reader.read_run(B3_FIX / "outputs" / f"{cfg}-nom", model,
                                     [names[s] for s in species if s in names])

    def test_specs_are_explicit_and_reach_usine(self):
        for cfg in self.b3.CONFIGS:
            with self.subTest(config=cfg):
                doc = self.b3.load_spec(cfg)
                t = doc["transport"]
                for block, keys in (("geometry", ("kind", "L_kpc", "disc_halfwidth_pc")),
                                    ("diffusion", ("D0_cm2_s", "R0_gv", "eta", "delta", "breaks")),
                                    ("reacceleration", ("V_A_kms", "zone", "relation", "w")),
                                    ("convection", ("V_c_kms", "dVc_dz_kms_per_kpc")), ("gas", ("model",))):
                    for key in keys:
                        self.assertIn(key, t[block], (block, key))
                self.assertEqual("radius_kpc" in t["geometry"], t["geometry"]["kind"] == "cylinder-2d")
                spec = usine_translate.translate(t, f"{cfg}-nom", doc["ekn_range_gev"])
                files = usine_translate.render(spec, "<TOOL_HOME>/inputs", "<RUN_DIR>")
                self.assertEqual(self.b3.check_used(spec, t, files["usine.init.par"]), [])
                rec = json.loads((B3_FIX / "runs" / f"{cfg}-nom.computational-run.json").read_text(encoding="utf-8"))
                self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
                self.assertFalse(mentions_path(json.dumps(rec), Path.home()))
                for p in sorted((B3_FIX / "outputs" / f"{cfg}-nom").iterdir()):
                    self.assertEqual(rec["extension"]["output_hashes"][f"out/{p.name}"],
                                     hashlib.sha256(p.read_bytes()).hexdigest(), p.name)

    def test_h1_2d_equals_the_b1_harmonized_run(self):
        hv1 = json.loads((USINE_FIX / "usine-results.json").read_text(encoding="utf-8"))
        got = usine_reader.ratio_of_bin_integrals(self.tables("h1-2d"), "B/C", hv1["bc_rigidity_edges_gv"],
                                                  "rigidity")
        for a, b in zip(got, hv1["runs"]["harmonized-v1"]["B/C"]):
            self.assertTrue(math.isclose(a, b, rel_tol=1e-6), (a, b))

    def test_b3_1_numbers_recomputed(self):
        for cfg in self.b3.CLOSED_FORM_CONFIGS:
            with self.subTest(config=cfg):
                got = self.b3.compare_b31(self.tables(cfg), self.b3.load_spec(cfg)["transport"])
                rec = self.res["b3_1"][cfg]
                for k, v in got["bins"].items():
                    self.assertTrue(math.isclose(v["max_dev"], rec["bins"][k]["max_dev"], rel_tol=1e-9))
                    self.assertTrue(math.isclose(got["nodes_max_dev"][k], rec["nodes_max_dev"][k], rel_tol=1e-9))

    def test_b3_1_fails_under_harmonized_v1(self):
        """B3-1 as frozen (harmonized-v1, 2D, R = 20 kpc): B/C misses 2%; superseded for B3's verdict (A1.10)."""
        self.assertGreater(self.res["b3_1"]["h1-2d"]["bins"]["B/C"]["max_dev"], B3_TOL["B3-1"])
        self.assertLessEqual(self.res["b3_1"]["dec-2d"]["bins"]["10Be/9Be"]["max_dev"], B3_TOL["B3-1"])

    def test_b3_1a_matched_1d_geometry(self):
        """B3-1a: USINE Model1DKisoVc against the 1D thin-disc closed form, bins and nodes within 2%."""
        for cfg, keys in (("h1-1d", ("B/C",)), ("dec-1d", ("B/C", "10Be/9Be"))):
            got = self.b3.compare_b31(self.tables(cfg), self.b3.load_spec(cfg)["transport"])
            for k in keys:
                with self.subTest(config=cfg, observable=k):
                    self.assertLessEqual(got["bins"][k]["max_dev"], B3_TOL["B3-1a"])
                    self.assertLessEqual(got["nodes_max_dev"][k], B3_TOL["B3-1a"])

    def test_b3_1b_offset_reported_and_attributed(self):
        """B3-1b (no tolerance): per-bin offsets under harmonized-v1 in b3-results.json, recomputed, with the
        attribution: the 2D/1D USINE ratio accounts for the offset (radial escape) and moving the radial boundary to
        40 kpc removes it; the target (hydrogen-only on both sides) is stated."""
        b1b = self.res["b3_1b"]
        for key in ("h1-2d B/C", "dec-2d B/C", "dec-2d 10Be/9Be"):
            cfg, obs = key.split()
            with self.subTest(case=key):
                row = b1b[key]
                got = self.b3.compare_b31(self.tables(cfg), self.b3.load_spec(cfg)["transport"])["bins"][obs]
                for a, b in zip(got["ratio"], row["closed_over_usine_2d"]):
                    self.assertTrue(math.isclose(a, b, rel_tol=1e-9))
                o2 = self.b3.observables(self.tables(cfg))[obs]
                o1 = self.b3.observables(self.tables(cfg.replace("2d", "1d")))[obs]
                for a, b, c, d in zip(o2, o1, row["usine_2d_over_usine_1d"], row["closed_over_usine_2d"]):
                    self.assertTrue(math.isclose(a / b, c, rel_tol=1e-9))
                    self.assertLess(abs(c * d - 1.0), 1e-3)  # what radial escape leaves: the 1D agreement (B3-1a)
        self.assertIn("hydrogen-only", b1b["attribution"])
        self.assertIn("radial escape", b1b["attribution"])
        self.assertLess(self.res["b3_1"]["h1-2d-r40"]["bins"]["B/C"]["max_dev"], 0.001)

    def test_b3_1c_fourier_bessel(self):
        """B3-1c: USINE harmonized-v1 2D (committed outputs) against the Fourier-Bessel thin-disc solution with the
        same inputs (2000 terms, computed here, offline), within 0.5% on B3's bins: B/C of h1-2d, 10Be/9Be of
        dec-2d."""
        for cfg, obs in self.b3.B31C_CASES:
            with self.subTest(config=cfg, observable=obs):
                tables = self.tables(cfg)
                fb = self.b3.bessel_2d_tables(tables, self.b3.load_spec(cfg)["transport"], self.b3.BESSEL_TERMS[-1])
                dev = self.b3.max_dev(self.b3.observables(fb)[obs], self.b3.observables(tables)[obs])
                self.assertLessEqual(dev, B3_TOL["B3-1c"])
                self.assertTrue(math.isclose(dev, self.res["b3_1c"][f"{cfg} {obs}"]["max_dev"], rel_tol=1e-9))

    def test_b3_2_and_b3_3(self):
        chans = json.loads((B3_FIX / "b3-channels.json").read_text(encoding="utf-8"))
        rows = {(r["config"], r["channel"]): r for r in chans["channels"]}
        n = 0
        for cfg, cres in self.res["b3_2"].items():
            self.assertLessEqual(cres["closure"]["max"], B3_TOL["B3-2"])
            for chan, entry in cres["channels"].items():
                row = rows[(cfg, chan)]
                self.assertEqual(row["norm"]["max_dev"], entry["norm_max_dev"])
                self.assertEqual(row["norm"]["must_rerun"], entry["norm_max_dev"] > B3_TOL["B3-2"])
                self.assertLessEqual(entry["norm_max_dev"], B3_TOL["B3-2"], (cfg, chan))  # B3-2
                self.assertTrue(row["inelastic"]["must_rerun"])
                slope = self.res["slope"].get(cfg, {}).get(chan)
                if slope is None:
                    self.assertTrue(row["slope"]["must_rerun"])
                else:
                    ok = min(slope["post_propagation_weight"]["max"], slope["energy_basis"]["max"]) <= B3_TOL["B3-2"]
                    self.assertEqual(row["slope"]["must_rerun"], not ok)
                n += 1
        self.assertEqual(n, len(rows))
        # energy coupling (all-2d): a post-propagation weight does not replace energy-basis responses
        self.assertGreater(self.res["slope"]["all-2d"]["12C->11B"]["post_propagation_weight"]["max"], B3_TOL["B3-2"])
        self.assertLessEqual(self.res["slope"]["dec-2d"]["12C->11B"]["post_propagation_weight"]["max"],
                             B3_TOL["B3-2"])

    def test_run_index_covers_the_plan(self):
        idx = json.loads((B3_FIX / "b3-run-index.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(r["name"] for r in idx["runs"]), sorted(i["name"] for i in self.b3.run_plan()))
        self.assertTrue(all(r["ok"] for r in idx["runs"]))
        for r in idx["runs"]:
            if r["kind"] == "nominal":
                for s, h in r["isotope_table_data_sha256"].items():
                    model = "Model2DKisoVc" if "-2d" in r["config"] else "Model1DKisoVc"
                    path = B3_FIX / "outputs" / r["name"] / usine_reader.table_name(s, model)
                    self.assertEqual(self.b3.data_sha256(path), h)

    def test_production_table_is_linear_in_its_nodes(self):
        spec = usine_translate.translate(self.b3.load_spec("dec-2d")["transport"], "x", (0.04, 2000.0))
        nodes = self.b3.table_nodes()
        self.assertEqual(len(nodes), 91)
        self.assertTrue(math.isclose(nodes[15], 10 ** -1.5, rel_tol=1e-12))
        text = self.b3.production_table(spec, {"12C->11B": [float(i) for i in range(91)]})
        block = text.split("12C -> 11B\n")[1].split("\n\n")[0].split("\n")
        self.assertEqual([float(x) for x in block], [float(i) for i in range(91)])
        self.assertIn("12C -> 10Be\n4.000000000e+00", text)


# ------------------------------------------------------------------ B1X (cr-propagation r4, decision A1.7): high break,
# USINE's own cross-section files and data-normalised abundances, no transport field silently ignored

B1X_RUN, SHIPPED_RUN = "b1x-init-test", "shipped-init-test"
B1X_RTOL = 1e-6  # B1X-2, B1X-3, frozen in acceptance.json and VALIDATION CRPROP-B1X before the runs
BORON_CARBON_TABLES = {axis: f"local_fluxes_BC_{axis}_Model1DKisoVc_SolMod0DFF_phi0_00GV.out" for axis in ("Ekn", "R")}
SHIPPED_QUANTITIES = "B/C:KEKN:0.;B/C:kR:0."


def b1x_translation():
    s = usine_spec(B1X_RUN)
    return usine_translate.translate(s["transport"], B1X_RUN, s["ekn_range_gev"], grid=s["ekn_grid"])


def ratio_table_deviation(table_a, table_b):
    """(number of common nodes, largest relative deviation on them) of two USINE tables."""
    xa, ya, _ = usine_reader.read_table(table_a)
    xb, yb, _ = usine_reader.read_table(table_b)
    a, b = dict(zip(xa, ya)), dict(zip(xb, yb))
    common = sorted(set(a) & set(b))
    return len(common), max(abs(b[x] / a[x] - 1.0) for x in common)


def usine_init_k_factor(rig, delta, r_break, delta_break, s_break):
    """The break factor of USINE V3.5's shipped K line (inputs/init.TEST.par line 133)."""
    return (1 + (rig / r_break) ** (delta_break / s_break)) ** (-s_break)


class UsineB1XOffline(unittest.TestCase):
    """B1X offline: the high break and USINE's own inputs are translated as recorded, the recorded run reproduces the
    recorded shipped example, the records hash their committed inputs, a missing HEP_USINE_DATA is refused, and no
    transport field is silently ignored (B1X-4)."""

    def test_high_break_is_usine_formula(self):
        t = b1x_translation()
        self.assertTrue(t["K_formula"].endswith("*(1+(Rig/Rh1)^((delta-dh1)/sh1))^(-sh1)"), t["K_formula"])
        p = t["transport_pars"]
        brk = usine_spec(B1X_RUN)["transport"]["diffusion"]["breaks"][0]
        self.assertEqual((p["Rh1"], p["dh1"], p["sh1"]), (brk["R_break_gv"], brk["delta_above"], brk["s"]))
        # init.TEST.par Model1DKisoVc: delta 6.141924e-01, Rbreak 125.89254, Deltabreak 2.281522e-01, sbreak 0.010023191
        for rig in (1.0, 50.0, 125.89254, 300.0, 1e4):
            ours = (1 + (rig / p["Rh1"]) ** ((p["delta"] - p["dh1"]) / p["sh1"])) ** (-p["sh1"])
            self.assertAlmostEqual(ours / usine_init_k_factor(rig, 6.141924e-01, 125.89254, 2.281522e-01,
                                                              0.010023191), 1.0, places=12)
        self.assertTrue(math.isclose(p["K0"], 0.035859151, rel_tol=1e-12))
        self.assertTrue(any("high break form" in x for x in t["substitutes"]))
        low_and_high = dict(usine_spec("b1-slab-all-items")["transport"])
        low_and_high["diffusion"] = dict(low_and_high["diffusion"], breaks=low_and_high["diffusion"]["breaks"] + [
            {"kind": "high", "R_break_gv": 300.0, "delta_above": 0.3, "s": 0.05, "s_convention": "usine"}])
        t2 = usine_translate.translate(low_and_high, "x", (1.0, 10.0))
        self.assertIn("(1+(Rl1/Rig)^((delta-dl1)/sl1))^sl1*(1+(Rig/Rh2)^((delta-dh2)/sh2))^(-sh2)", t2["K_formula"])

    def test_half_specified_high_break_refused(self):
        base = usine_spec(B1X_RUN)["transport"]
        for brk in ({"kind": "high", "R_break_gv": 300.0, "s": 0.05}, {"kind": "high", "R_break_gv": 300.0,
                                                                       "delta_above": 0.3},
                    {"kind": "high", "R_break_gv": 300.0, "delta_below": 0.3, "s": 0.05}):
            with self.subTest(brk=brk), self.assertRaises(usine_translate.SpecError):
                usine_translate.translate(dict(base, diffusion=dict(base["diffusion"], breaks=[brk])), "x", (1.0, 10.0))

    def test_renders_to_the_recorded_inputs(self):
        files = usine_translate.render(b1x_translation(), "<TOOL_HOME>/inputs", "<RUN_DIR>")
        self.assertEqual(sorted(files), ["usine.init.par"])  # nothing written from USINE's files
        recorded = sorted(p.name for p in (USINE_FIX / "inputs" / B1X_RUN).iterdir())
        self.assertEqual(recorded, ["usine.init.par"])
        text = files["usine.init.par"]
        self.assertEqual(text, (USINE_FIX / "inputs" / B1X_RUN / "usine.init.par").read_text(encoding="utf-8"))
        for needle in ("fProd @ M=1 @ <TOOL_HOME>/inputs/XS_NUCLEI/sigProdGALPROP17_OPT12.dat",
                       "fTotInelAnn @ M=1 @ <TOOL_HOME>/inputs/XS_NUCLEI/sigInelTripathi99+Coste12.dat",
                       "fCRData @ M=1 @ <TOOL_HOME>/inputs/crdata_crdb20170523.dat",
                       "NormList @ M=0 @ H,He:PAMELA|20|kEkn;C,N,O,F,Ne,Na,Mg,Al,Si:HEAO|10.6|kEkn",
                       "ListOfCRs @ M=0 @ [1H,30Si]", "PureSecondaries @ M=0 @ Li,Be,B", "Targets @ M=0 @ H,He",
                       "ParVals @ M=0 @ 8,0.1,0.2038018", "He:FORMULA|0.1", "HII:FORMULA|0.033",
                       "kSSISOTFRAC,kSSISOTABUND,kFIPBIAS", "eta_s[SHARED:-1]", "Va*1.022712e-3*beta",
                       "IsDecayEC @ M=0 @ true", "NBins @ M=0 @ 33"):
            self.assertIn(needle, text)
        self.assertNotIn("<RUN_DIR>", text)

    def test_records_validate_and_hash(self):
        for name in (B1X_RUN, SHIPPED_RUN):
            with self.subTest(run=name):
                rec = json.loads((USINE_FIX / "runs" / f"{name}.computational-run.json").read_text(encoding="utf-8"))
                self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
                self.assertEqual(rec["status"], ["unvalidated"])
                outputs = {f"out/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted((USINE_FIX / "outputs" / name).iterdir())}
                self.assertEqual(rec["extension"]["output_hashes"], outputs)
                self.assertFalse(mentions_path(json.dumps(rec), Path.home()), name)
        rec = json.loads((USINE_FIX / "runs" / f"{B1X_RUN}.computational-run.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(rec["extension"]["output_hashes"]),
                         sorted(f"out/{f}" for f in usine_translate.expected_outputs(b1x_translation())))
        in_place = sorted(i["path"] for i in rec["extension"]["input_manifest"] if i.get("read_in_place"))
        self.assertEqual(in_place, ["<TOOL_HOME>/inputs/XS_NUCLEI/sigInelTripathi99+Coste12.dat",
                                    "<TOOL_HOME>/inputs/XS_NUCLEI/sigProdGALPROP17_OPT12.dat",
                                    "<TOOL_HOME>/inputs/crdata_crdb20170523.dat"])

    def test_committed_form_hashes(self):
        """B1 verifier note: sha256 in input_manifest is of the file as run; committed_form_sha256 is of the committed
        placeholder form, for the seven B1 runs and the B1X run."""
        for name in USINE_RUNS + (B1X_RUN,):
            with self.subTest(run=name):
                ext = json.loads((USINE_FIX / "runs" / f"{name}.computational-run.json").read_text(encoding="utf-8"))[
                    "extension"]
                self.assertIn("committed_form_sha256", ext["input_manifest_note"])
                for item in ext["input_manifest"]:
                    if item.get("read_in_place"):
                        continue
                    committed = hashlib.sha256((USINE_FIX / "inputs" / name / item["path"]).read_bytes()).hexdigest()
                    self.assertEqual(item["committed_form_sha256"], committed, item["path"])
                    if item["path"] != "usine.init.par":  # no path inside: as run equals committed
                        self.assertEqual(item["sha256"], committed, item["path"])

    def test_recorded_run_reproduces_the_shipped_example(self):
        """B1X-2 and B1X-3 on the recorded tables (the live class reruns both)."""
        for axis, fname in BORON_CARBON_TABLES.items():
            with self.subTest(axis=axis):
                n, dev = ratio_table_deviation(USINE_FIX / "outputs" / SHIPPED_RUN / fname,
                                               USINE_FIX / "outputs" / B1X_RUN / fname)
                self.assertEqual(n, 33)
                self.assertLessEqual(dev, B1X_RTOL)

    def test_missing_usine_data_is_refused(self):
        spec = b1x_translation()
        for data_dir in (None, "", "/nonexistent-usine-inputs"):
            with self.subTest(data_dir=data_dir), self.assertRaisesRegex(usine_translate.UsineDataMissing,
                                                                         "HEP_USINE_DATA"):
                usine_translate.usine_input_paths(spec, data_dir)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(usine_translate.UsineDataMissing, "sigProdGALPROP17_OPT12"):
                usine_translate.usine_input_paths(spec, td)
            env = {k: v for k, v in os.environ.items() if k not in ("HEP_USINE_BIN", "HEP_USINE_DATA")}
            proc = subprocess.run([sys.executable, "-I", str(ADAPTER / "assets" / "usine_translate.py"), "translate",
                                   "--transport", str(USINE_FIX / "specs" / f"{B1X_RUN}.json"), "--name", B1X_RUN,
                                   "--out", str(Path(td) / "run"), "--ekn-range", "0.05,5000",
                                   "--ekn-grid", "33,0.05,5000"], capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["status"], "missing-dependency")
        self.assertIn("HEP_USINE_DATA", out["error"])
        self.assertIn("usine:XS_NUCLEI/sigProdGALPROP17_OPT12.dat", out["error"])
        self.assertEqual(usine_translate.usine_input_paths(usine_translation("d1-decay"), None), {})

    def test_usine_file_names(self):
        base = usine_spec(B1X_RUN)["transport"]
        for bad in ("usine:../secret.dat", "usine:/abs/x.dat", "usine:XS_NUCLEI/x.txt", "usine:"):
            with self.subTest(bad=bad), self.assertRaises(usine_translate.SpecError):
                usine_translate.translate(dict(base, cross_sections=dict(base["cross_sections"], production_set=bad)),
                                          "x", (1.0, 10.0))
        for abund in ("fitted", "data-normalised usine:x.dat C,N:HEAO", "data-normalised usine:x.dat Fe:HEAO@10",
                      "data-normalised usine:x.dat C:HEAO@10;C:PAMELA@20"):
            with self.subTest(abund=abund), self.assertRaises(usine_translate.SpecError):
                usine_translate.translate(dict(base, sources=dict(base["sources"], abundances=abund)), "x", (1.0, 10.0))

    def test_network_top_and_isotopic_are_used_or_refused(self):
        """B1X-4 example: network_top Ni-64 with the ILLUSTRATIVE set (network ends at 16O) is refused, never
        dropped; with USINE's own files it sets the network."""
        base = usine_spec("d1-isotopic")["transport"]
        for species in ({"network_top": "Ni-64", "isotopic": True}, {"network_top": "O-16", "isotopic": False}):
            with self.subTest(species=species), self.assertRaises(usine_translate.SpecError):
                usine_translate.translate(dict(base, species=species), "x", (1.0, 10.0))
        own = usine_spec(B1X_RUN)["transport"]
        t = usine_translate.translate(dict(own, species={"network_top": "Ni-64", "isotopic": True}), "x", (1.0, 10.0))
        self.assertEqual(t["network_range"], "[1H,64Ni]")
        with self.assertRaises(usine_translate.SpecError):
            usine_translate.translate(dict(own, species={"network_top": "Ni-64", "isotopic": False}), "x", (1.0, 10.0))

    def test_no_field_silently_ignored(self):
        """B1X-4: every field of the transport blocks of the recorded specs, changed or removed, changes the generated
        files or the recorded substitutes, or is refused; an unknown key is refused."""
        def outcome(tr, grid):
            try:
                t = usine_translate.translate(tr, "x", (0.05, 5000.0), grid=grid)
            except usine_translate.SpecError:
                return "refused"
            return (usine_translate.render(t, "<TOOL_HOME>/inputs", "<RUN_DIR>"), t["substitutes"])

        def changed(value):
            if isinstance(value, bool):
                return not value
            if isinstance(value, (int, float)):
                return value * 1.1 + 0.1
            if isinstance(value, str):
                return value + " (changed)"
            if isinstance(value, list):
                return value[:-1] if value else ["changed"]
            return {}

        checked = 0
        for name in (B1X_RUN, "b1-slab-all-items", "d1-decay", "harmonized-v1"):
            spec = usine_spec(name)
            grid = spec.get("ekn_grid")
            base = outcome(spec["transport"], grid)
            self.assertNotEqual(base, "refused", name)
            for block, value in spec["transport"].items():
                keys = list(value) if isinstance(value, dict) else [None]
                for key in keys:
                    for how in ("change", "remove"):
                        tr = json.loads(json.dumps(spec["transport"]))
                        if key is None:
                            if how == "remove":
                                tr.pop(block)
                            else:
                                tr[block] = changed(tr[block])
                        elif how == "remove":
                            tr[block].pop(key)
                        else:
                            tr[block][key] = changed(tr[block][key])
                        with self.subTest(run=name, field=f"{block}.{key}" if key else block, how=how):
                            self.assertNotEqual(outcome(tr, grid), base)
                            checked += 1
            for block in ("geometry", "diffusion", "gas", "species"):
                tr = json.loads(json.dumps(spec["transport"]))
                tr[block]["unknown_key"] = 1.0
                with self.subTest(run=name, unknown=block):
                    self.assertEqual(outcome(tr, grid), "refused")
            with self.subTest(run=name, unknown="top"):
                self.assertEqual(outcome(dict(spec["transport"], halo={}), grid), "refused")
        self.assertGreater(checked, 100)

    def test_defaults_are_recorded(self):
        minimal = {"geometry": {"L_kpc": 4.0}, "diffusion": {"D0_cm2_s": 3e28, "delta": 0.5},
                   "gas": {"model": "n_H = 1 cm^-3"},
                   "sources": {"injection": [{"gamma": 2.3}]},
                   "cross_sections": {"production_set": "xs-illustrative-A"}}
        t = usine_translate.translate(minimal, "x", (1.0, 10.0))
        note = next(x for x in t["substitutes"] if x.startswith("not given in the transport block"))
        for needle in ("geometry.kind = cylinder-2d", "geometry.disc_halfwidth_pc = 100.0 pc",
                       "geometry.radius_kpc = 20.0 kpc", "geometry.local_bubble_radius_kpc = 0.0 kpc",
                       "diffusion.eta = 1.0", "diffusion.R0_gv = 1.0 GV", "reacceleration.V_A_kms = 0.0 km/s",
                       "convection.V_c_kms = 0.0 km/s", "transport.losses = []", "decay.enabled = False",
                       "cross_sections.inelastic_set = xs-illustrative-A"):
            self.assertIn(needle, note)
        self.assertIn("species.network_top = 16O (the network of xs-illustrative-A)", note)
        self.assertTrue(any("eta_s = 0" in x for x in t["substitutes"]))


@unittest.skipUnless(os.environ.get("HEP_USINE_LIVE_TEST") == "1", "live USINE runs: set HEP_USINE_LIVE_TEST=1, "
                     "HEP_USINE_BIN and HEP_USINE_DATA")
class LiveUsineB1X(unittest.TestCase):
    """B1X-2 and B1X-3: USINE's shipped example inputs/init.TEST.par is run in place ('usine -l', USINE's own inputs),
    and the transport block written to match it (high break on the K line, USINE's cross-section files and NormList)
    is run through the translator; their B/C tables must agree within relative 1e-6 on the common nodes, and the
    translator's run must reproduce the recorded one. Two USINE runs of about 15-25 s each. With HEP_USINE_LIVE_TEST=1
    but no USINE installed, the tests fail instead of skipping."""

    @classmethod
    def setUpClass(cls):
        cls.reason = live_usine_reason()
        if cls.reason:
            return
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary, cls.data_dir = Path(os.environ["HEP_USINE_BIN"]), Path(os.environ["HEP_USINE_DATA"])
        shipped = Path(cls.tmp.name) / SHIPPED_RUN
        shipped.mkdir()
        env = dict(os.environ, USINE=str(usine_translate.tool_home(cls.binary)))
        cls.shipped_proc = subprocess.run([str(cls.binary), "-l", str(cls.data_dir / "init.TEST.par"),
                                           str(shipped / "out"), SHIPPED_QUANTITIES, "0", "1", "1", "0"], cwd=shipped,
                                          capture_output=True, text=True, timeout=3600, env=env)
        cls.shipped_out = shipped / "out"
        cls.spec = b1x_translation()
        cls.run_dir = Path(cls.tmp.name) / B1X_RUN
        cls.result = usine_translate.run_usine(cls.spec, cls.run_dir, cls.binary, cls.data_dir)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "tmp", None):
            cls.tmp.cleanup()

    def setUp(self):
        self.assertIsNone(self.reason)

    def _compare_with_shipped(self):
        for axis, fname in BORON_CARBON_TABLES.items():
            with self.subTest(axis=axis):
                self.assertTrue((self.shipped_out / fname).is_file(), self.shipped_proc.stdout[-800:])
                n, dev = ratio_table_deviation(self.shipped_out / fname, self.run_dir / "out" / fname)
                self.assertGreaterEqual(n, 30)
                self.assertLessEqual(dev, B1X_RTOL)

    def test_high_break_reproduces_the_shipped_example(self):
        """B1X-2."""
        self.assertTrue(self.result["ok"], self.result["log_tail"])
        init = (self.run_dir / "usine.init.par").read_text(encoding="utf-8")
        self.assertIn("K00:FORMULA|beta^eta_t*K0*(Rig/R0)^delta*(1+(Rig/Rh1)^((delta-dh1)/sh1))^(-sh1)", init)
        self._compare_with_shipped()

    def test_usine_cross_sections_reproduce_the_shipped_example(self):
        """B1X-3: USINE's files are read in place (named by their path in HEP_USINE_DATA, never copied) and the run
        reproduces the shipped example and the recorded run; B1X-5: no committed fixture equals a USINE input file."""
        self.assertTrue(self.result["ok"], self.result["log_tail"])
        init = (self.run_dir / "usine.init.par").read_text(encoding="utf-8")
        for rel in self.spec["usine_inputs"].values():
            self.assertIn(f"@ {self.data_dir.resolve() / rel}", init)
        usine_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in self.data_dir.rglob("*") if p.is_file()}
        run_files = [p for p in self.run_dir.rglob("*") if p.is_file()]
        self.assertFalse({hashlib.sha256(p.read_bytes()).hexdigest() for p in run_files} & usine_hashes)
        committed = [p for p in FIX.rglob("*") if p.is_file()]
        self.assertFalse({hashlib.sha256(p.read_bytes()).hexdigest() for p in committed} & usine_hashes)
        self._compare_with_shipped()
        for fname in usine_translate.expected_outputs(self.spec):
            rerun = usine_reader.read_table(self.run_dir / "out" / fname)
            recorded = usine_reader.read_table(USINE_FIX / "outputs" / B1X_RUN / fname)
            self.assertEqual(rerun[0], recorded[0], fname)
            for a, b in zip(rerun[1], recorded[1]):
                self.assertTrue(math.isclose(a, b, rel_tol=B1X_RTOL, abs_tol=1e-300), (fname, a, b))
        rec = usine_translate.record(self.spec, self.result, self.binary)
        self.assertEqual([f.code for f in validate_artifact(rec).errors], [])


# ------------------------------------------------------------------ E2 (cr-propagation r4): emulator and its provider

import emulator_provider  # noqa: E402

E2_FIX = FIX / "e2"
EMULATOR_PROVIDER = ADAPTER / "assets" / "emulator_provider.py"
E2_SUMMARY = json.loads((E2_FIX / "summary.json").read_text(encoding="utf-8"))
E2_HOLDOUT = json.loads((E2_FIX / "holdout.json").read_text(encoding="utf-8"))
E2_EDGES = E2_HOLDOUT["observable"]["bins"]
EMULATOR_REQUEST = {
    "protocol": "cr-provider/1", "provider": "emulator", "provider_version": "1.0.0",
    "points": [dict(E2_HOLDOUT["truth"]["point"]), dict(E2_HOLDOUT["holdout"][0]["point"])],
    "observables": [{"id": "B/C", "axis": "rigidity", "unit": "GV", "bins": E2_EDGES[2:9]}],
    "want": ["lis"], "seed": None}


def hep_ml_scripts():
    path = str(ROOT / "skills" / "hep-ml" / "scripts")
    if path not in sys.path:
        sys.path.insert(0, path)


def e2_call(request, env=None, allow_outside=False):
    with tempfile.TemporaryDirectory() as td:
        req, resp = Path(td) / "req.json", Path(td) / "resp.json"
        req.write_text(json.dumps(request))
        argv = [sys.executable, str(EMULATOR_PROVIDER), "--request", str(req), "--response", str(resp)]
        proc = subprocess.run(argv + (["--allow-outside-validated-range"] if allow_outside else []),
                              capture_output=True, text=True, timeout=300,
                              env=env or dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return proc, json.loads(resp.read_text())


class EmulatorProviderConformance(ProviderConformance, unittest.TestCase):
    """E2-PRV-1 and E2-PRV-2: C1's conformance mixin on the emulator provider (the committed model; no USINE)."""
    PROVIDER_ID = "emulator"
    REQUEST = EMULATOR_REQUEST
    VOCAB_PROFILES = (PROFILE / "profile.json",)

    def unavailable_reason(self):
        return "HEP_EMULATOR_ML_ARTIFACT is set (the conformance test uses the committed model)" if os.environ.get(
            emulator_provider.ARTIFACT_ENV) else None


class EmulatorArtifact(unittest.TestCase):
    """The committed emulator: its ml-artifact validates and names the model by hash, the provider's declaration is the
    model's training box, the model was trained for the USINE provider's DEFAULT_TRANSPORT, and the provider's
    Gaussian-process and DomainModel arithmetic equals hep-ml's own classes."""

    @classmethod
    def setUpClass(cls):
        hep_ml_scripts()
        import check_surrogate_domain
        import train_emulator
        cls.csd, cls.te = check_surrogate_domain, train_emulator
        cls.emu = emulator_provider.Emulator(E2_FIX / "emulator.ml-artifact.json")
        cls.model = json.loads((E2_FIX / "emulator-model.json").read_text(encoding="utf-8"))

    def test_artifact_validates_and_names_the_model(self):
        art = json.loads((E2_FIX / "emulator.ml-artifact.json").read_text(encoding="utf-8"))
        rep = validate_artifact(art)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        ext = art["extension"]
        self.assertEqual(ext["task"], "surrogate")
        self.assertEqual(ext["extrapolation_policy"]["action"], "reject")
        self.assertEqual(ext["model_hash"], "sha256:" + hashlib.sha256((E2_FIX / "emulator-model.json").read_bytes())
                         .hexdigest())
        self.assertEqual(ext["model_hash"], "sha256:" + E2_SUMMARY["final_model_sha256"])
        self.assertEqual(ext["splits"]["overlap_check"]["result"], "pass")
        self.assertEqual(set(art["status"]), {"synthetic", "unvalidated"})
        self.assertEqual(ext["training_domain"], {f["name"]: [f["min"], f["max"]] for f in self.model["features"]})

    def test_declaration_is_the_training_box_and_transport(self):
        decl = emulator_provider.declaration()
        self.assertEqual(decl["version"], "1.0.0")
        self.assertEqual(decl["domain"], {f["name"]: {"min": f["min"], "max": f["max"]} for f in self.model["features"]})
        self.assertEqual(self.model["context"]["transport"], usine_provider.DEFAULT_TRANSPORT)
        self.assertEqual(self.model["context"]["provider_version"], usine_provider.declaration()["version"])
        self.assertEqual(self.emu.edges, [E2_EDGES[0][0]] + [b for _, b in E2_EDGES])

    def test_prediction_equals_hep_ml(self):
        ref = self.te.GaussianProcessEmulator(self.model)
        u = np.random.default_rng(11).uniform(0.0, 1.0, size=(300, 5))
        mine, sig, parts = self.emu.predict_unit(u)
        theirs, their_sig = ref.predict_unit(u)
        np.testing.assert_allclose(mine, theirs, rtol=0, atol=1e-12)
        np.testing.assert_allclose(sig, their_sig, rtol=0, atol=1e-12)
        # the uncertainty components add in quadrature to the emulator's variance (P10)
        quad = sum(p ** 2 for p in parts) + self.emu.residual_var[None, :]
        np.testing.assert_allclose(np.sqrt(quad), sig, rtol=1e-12, atol=0)

    def test_domain_status_equals_hep_ml(self):
        dm = self.csd.DomainModel.from_dict(self.model["domain_model"])
        u = np.vstack([np.random.default_rng(12).uniform(-0.1, 1.1, size=(1500, 5)),
                       np.asarray(self.model["training_unit"])])
        theirs = dm.classify(u)[0]
        mine = [self.emu.domain_status(row)[0] for row in u]
        self.assertEqual(mine, theirs)
        self.assertGreater(theirs.count("sparse") + theirs.count("outside"), 0)


class EmulatorValidation(unittest.TestCase):
    """E2-1 and E2-2 recomputed offline from the committed hold-out sets (USINE values) with the committed provider,
    equal to the recorded numbers (criteria of VALIDATION CRPROP-E2, fixed before the runs)."""

    def test_holdout_criteria(self):
        sys.path.insert(0, str(FIX / "e1"))
        import active_addition as e1
        emu = emulator_provider.Emulator(E2_FIX / "emulator.ml-artifact.json")
        observed = np.asarray(E2_HOLDOUT["truth"]["values"])
        sigma_stat, cov = e1.synthetic_covariance(observed)
        cov_inv = np.linalg.inv(cov)
        last = E2_SUMMARY["rounds"][E2_SUMMARY["final_round"]]["holdout"]
        for key, recorded in (("holdout", last), ("confirmation", E2_SUMMARY["confirmation"])):
            with self.subTest(set=key):
                recs = E2_HOLDOUT[key]
                self.assertEqual(len(recs), 32)
                # point by point in the provider's own unit coordinates, as the provider evaluates them (the GP mean
                # carries rounding noise of about 1e-10 in ln B/C, so a batched product would differ in the 8th digit)
                u = np.array([emu.unit(r["point"]) for r in recs])
                pred = np.exp(np.vstack([emu.predict_unit(row)[0] for row in u]))
                b = pred - np.asarray([r["values"] for r in recs])
                dchi2 = np.einsum("ij,jk,ik->i", b, cov_inv, b)
                pull = np.abs(b) / sigma_stat[None, :]
                # relative 1e-4 against the recorded numbers: the GP's scipy/numpy linear algebra differs across
                # platforms (Linux drift about 3e-7 relative); E2-1 and E2-2 below are checked unchanged
                self.assertAlmostEqual(float(dchi2.max()), recorded["dchi2_max"], delta=1e-4 * recorded["dchi2_max"])
                self.assertAlmostEqual(float(pull.max()), recorded["pull_max"], delta=1e-4 * recorded["pull_max"])
                self.assertTrue((dchi2 <= 1.0).all())          # E2-1
                self.assertTrue((pull <= 0.2).all())           # E2-2
                self.assertEqual([emu.domain_status(row)[0] for row in u], ["inside"] * len(u))
        hashes = {r["point_hash"] for r in E2_SUMMARY["training_points"]}
        self.assertFalse(hashes & {r["point_hash"] for r in E2_HOLDOUT["holdout"] + E2_HOLDOUT["confirmation"]})

    def test_synthetic_fit_comparison(self):
        e23 = E2_SUMMARY["e2_3"]
        self.assertTrue(e23["passed"])
        self.assertTrue(all(s <= 0.2 for s in e23["shift_in_sigma_usine"]))          # E2-3 best fit
        self.assertTrue(all(abs(w) <= 0.10 for w in e23["width_ratio_minus_one"]))   # E2-3 widths
        self.assertLessEqual(e23["usine"]["evaluations"], 300)
        self.assertLessEqual(E2_SUMMARY["usine_evaluations"], 500)


class EmulatorProviderRefusals(unittest.TestCase):
    """The emulator's own refusals: another transport (out-of-domain), bins that are not training bins
    (unsupported-observable), a point the DomainModel calls sparse or outside (out-of-domain; evaluated and labelled
    with --allow-outside-validated-range), a tampered model (provider-error), and the version of another model."""

    def test_transport_and_bins(self):
        other = json.loads(json.dumps(usine_provider.DEFAULT_TRANSPORT))
        other["geometry"]["L_kpc"] = 6.0
        proc, doc = e2_call(dict(EMULATOR_REQUEST, transport=other))
        self.assertEqual((proc.returncode, doc["status"], doc["reason"]), (1, "failed", "out-of-domain"))
        proc, doc = e2_call(dict(EMULATOR_REQUEST, transport=usine_provider.DEFAULT_TRANSPORT))
        self.assertEqual(proc.returncode, 0, doc)
        bad = dict(EMULATOR_REQUEST, observables=[{"id": "B/C", "axis": "rigidity", "unit": "GV",
                                                    "bins": [[2.0, 3.0], [3.0, 4.0]]}])
        proc, doc = e2_call(bad)
        self.assertEqual((proc.returncode, doc["reason"]), (1, "unsupported-observable"))

    def test_domain_model_refusal(self):
        corner = {"D0_cm2_s": 1.0e28, "delta": 0.8, "eta": 1.5, "V_A_kms": 100.0, "V_c_kms": 30.0}
        emu = emulator_provider.Emulator(E2_FIX / "emulator.ml-artifact.json")
        status, _ = emu.domain_status(emu.unit(corner))
        self.assertIn(status, ("sparse", "outside"))
        req = dict(EMULATOR_REQUEST, points=[EMULATOR_REQUEST["points"][0], corner])
        proc, doc = e2_call(req)
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(doc["status"], "incomplete")
        self.assertEqual(doc["results"][0]["status"], "ok")
        self.assertEqual(doc["results"][1]["reason"], "out-of-domain")
        self.assertIn("DomainModel status", doc["results"][1]["detail"])
        self.assertNotIn("predictions", doc["results"][1])
        proc, doc = e2_call(req, allow_outside=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("outside-validated-range", doc["results"][1]["labels"])
        self.assertNotIn("outside-validated-range", doc["results"][0]["labels"])

    def test_tampered_or_other_model(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            shutil.copyfile(E2_FIX / "emulator.ml-artifact.json", td / "emulator.ml-artifact.json")
            model = json.loads((E2_FIX / "emulator-model.json").read_text(encoding="utf-8"))
            model["components"][0]["alpha"][0] *= 1.001
            (td / "emulator-model.json").write_text(json.dumps(model))
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HEP_EMULATOR_ML_ARTIFACT=str(td / "emulator.ml-artifact.json"))
            proc, doc = e2_call(EMULATOR_REQUEST, env=env)
            self.assertEqual((proc.returncode, doc["reason"]), (1, "provider-error"))
            self.assertIn("model_hash", doc["detail"])
            shutil.copyfile(E2_FIX / "emulator-model.json", td / "emulator-model.json")
            proc, doc = e2_call(EMULATOR_REQUEST, env=env)
            self.assertEqual(doc["reason"], "provider-version-mismatch")
            sha = E2_SUMMARY["final_model_sha256"][:12]
            proc, doc = e2_call(dict(EMULATOR_REQUEST, provider_version=f"1.0.0+model.{sha}"), env=env)
            self.assertEqual(proc.returncode, 0, doc)


# ------------------------------------------------------------------ D3 (cr-propagation r4): cross-code comparison

D3_FIX = FIX / "d3"
D3_TOLERANCE = 0.05  # D3-1 and D3-3, frozen in acceptance.json and VALIDATION CRPROP-D3 before the comparison
D3_PASSING = ("harmonized-v1", "isotopic", "convection", "decay")  # D3-3 configurations within 5% (recorded verdict)


def load_d3_study():
    """d3_study.py loaded from its file (no fixture folder added to sys.path)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("d3_study", D3_FIX / "d3_study.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_close_tree(case, got, want, path="", rel=1e-9):
    if isinstance(want, dict):
        case.assertEqual(sorted(got), sorted(want), path)
        for k in want:
            assert_close_tree(case, got[k], want[k], f"{path}/{k}", rel)
    elif isinstance(want, list):
        case.assertEqual(len(got), len(want), path)
        for i, (a, b) in enumerate(zip(got, want)):
            assert_close_tree(case, a, b, f"{path}[{i}]", rel)
    elif isinstance(want, float) and not isinstance(want, bool):
        case.assertTrue(math.isclose(got, want, rel_tol=rel, abs_tol=1e-300), (path, got, want))
    else:
        case.assertEqual(got, want, path)


@unittest.skipUnless(HAVE_NUMPY, "numpy and scipy are needed (USINE reader, Bessel zeros)")
class D3CrossCode(unittest.TestCase):
    """D3, offline: DRAGON2 cd588707 against USINE V3.5 (GALPROP unavailable, decisions A1.2), recomputed from the
    recorded runs: D1's DRAGON2 outputs and B1's USINE numbers (level 1, reused), the two D3 DRAGON2 runs
    (d3/dragon2/) and the D3 USINE runs (d3/usine/: matched level 1, attribution ladder, geometry checks, level 2).
    D3-1 (5%, frozen) fails and is reported; D3-3 passes for the configurations on DRAGON2's BronfFerr gas and fails for
    reacceleration (first-order zone conversion) and the losses pair (Galprop gas geometry), each attributed with
    evidence; D3-2 passes: every level-2 difference is measured by a USINE run or estimated. The verdicts are whatever
    the recorded numbers give, never a widened tolerance."""

    @classmethod
    def setUpClass(cls):
        cls.d3 = load_d3_study()
        cls.res = json.loads((D3_FIX / "d3-results.json").read_text(encoding="utf-8"))

    def test_results_are_recomputed_from_the_recorded_runs(self):  # D3-1, D3-2, D3-3
        got = self.d3.jsonable(self.d3.analyze(lambda name: D3_FIX / "usine" / "outputs" / name, None))
        assert_close_tree(self, got, self.res)

    def test_d3_1_level_one_fails_and_is_reported(self):
        self.assertEqual(self.res["tolerance"], D3_TOLERANCE)
        self.assertEqual(self.res["bc_rigidity_edges_gv"], BORON_CARBON_RIGIDITY_EDGES)
        v = self.res["verdicts"]["D3-1"]
        self.assertFalse(v["passed"])
        for cfg, row in self.res["level1"].items():
            with self.subTest(config=cfg):
                self.assertEqual(row["B/C"]["passed"], row["B/C"]["max_abs_deviation"] <= D3_TOLERANCE)
                self.assertGreater(row["B/C"]["max_abs_deviation"], 0.3)  # DRAGON2/USINE 1.28-1.77
        # the level-1 offset equals the product of the matched settings' effects times the matched residual
        lad = self.res["ladder"]
        for a, b in zip(lad["product_of_steps_times_matched_residual"], lad["level1_offset"]):
            self.assertAlmostEqual(a / b, 1.0, places=9)

    def test_d3_3_matched_level_one(self):
        v = self.res["verdicts"]["D3-3"]
        self.assertFalse(v["passed"])
        self.assertEqual(sorted(c for c, ok in v["configurations"].items() if ok), sorted(D3_PASSING))
        for cfg, row in self.res["matched"].items():
            with self.subTest(config=cfg):
                self.assertEqual(row["B/C"]["passed"], row["B/C"]["max_abs_deviation"] <= D3_TOLERANCE)
                s = row["settings"]
                self.assertTrue(s["helium"])
                self.assertEqual(s["inelastic"], "dragon2")
                self.assertEqual(s["source_eta_s"], -1.0)
                gas_model = self.d3.LEVEL1_CONFIGS[cfg][2]
                col = self.d3.gas_columns(gas_model, 8.3, 4.0, 0.02)
                self.assertAlmostEqual(s["gas_cm3"]["He"], 0.11 * col["nucleons"] / 0.2, places=12)
                oc = row["O_over_C"]["10 GeV/n"]
                self.assertAlmostEqual(oc["usine"] / oc["dragon2"], 1.0, places=5)  # parent ratio matched
        # attributions of the failing configurations, with evidence
        rc = self.res["reacceleration_check"]
        self.assertTrue(rc["within_bound"])  # within transport_conventions' first-order bound (A1R) x item effect
        for cfg in ("losses-off", "losses"):  # Galprop gas geometry: a uniform thin disc cannot express it
            self.assertLessEqual(self.res["geometry_checks"][cfg]["B/C"]["max_abs_deviation"], D3_TOLERANCE)
            self.assertLess(self.res["geometry_checks"][cfg]["B/C"]["max_abs_deviation"],
                            self.res["matched"][cfg]["B/C"]["max_abs_deviation"])
        g = self.res["geometry_estimates"]["Galprop"]["geometry_factor"]
        self.assertAlmostEqual(self.res["matched"]["losses-off"]["B/C"]["dragon2_over_usine"][-1], g, delta=0.02)
        # with like-for-like gas the losses item effects agree within 3% (D1-1a found 6.1% against ionization only)
        self.assertLessEqual(self.res["losses_check"]["item_effect_max_abs_deviation"], 0.03)
        # 10Be/9Be with decay: the matched gap is D1's thick-gas factor (finite gas layer), within 0.5% in every bin
        self.assertLessEqual(self.res["decay_check"]["matched_over_F_max_abs_deviation"], 0.005)

    def test_d3_2_every_level_two_difference_is_attributed(self):
        v = self.res["verdicts"]["D3-2"]
        self.assertTrue(v["passed"])
        self.assertLessEqual(v["residual_max_abs_deviation"], v["allowed"])
        diffs = self.res["level2_differences"]
        self.assertTrue(all(d["kind"] == "model-alternative" and d["attribution"] in ("measured", "estimated")
                            and d["evidence"] and len(d["effect_on_bc"]) == 2 for d in diffs))
        steps = [n for n, st in self.res["level2"]["steps"].items() if st["effect"] is not None]
        measured = {d["evidence"].split()[2] for d in diffs if d["attribution"] == "measured"}
        self.assertEqual(measured, set(steps))  # every swap step is a registered difference
        prod = [1.0] * 16
        for n in steps:
            prod = [p * e for p, e in zip(prod, self.res["level2"]["steps"][n]["effect"])]
        for p, r, t in zip(prod, self.res["level2"]["residual_dragon2_over_last_step"],
                           self.res["level2"]["dragon2_over_usine"]):
            self.assertAlmostEqual(p * r / t, 1.0, places=9)

    def test_dragon2_runs_are_recorded_and_translated(self):
        import hashlib
        specs = self.d3.dragon2_specs()
        for name, s in specs.items():
            with self.subTest(run=name):
                # relative 1e-12 against the committed spec: libm differs across platforms in the last digits
                assert_close_tree(self, s, json.loads((D3_FIX / "dragon2" / "specs" / f"{name}.json")
                                                      .read_text(encoding="utf-8")), name, rel=1e-12)
                rec = json.loads((D3_FIX / "dragon2" / "runs" / f"{name}.computational-run.json").read_text(encoding="utf-8"))
                self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
                ext = rec["extension"]
                self.assertEqual(ext["exit_status"], 0)
                out = D3_FIX / "dragon2" / "outputs" / f"{name}.txt"
                self.assertEqual(ext["output_hashes"], {f"output/{name}.txt": hashlib.sha256(out.read_bytes()).hexdigest()})
                xml = dragon2_run.render_xml(dragon2_run.check_spec(s))
                self.assertIn(hashlib.sha256(xml.encode()).hexdigest(),
                              [i["sha256"] for i in ext["input_manifest"] if i["path"] == f"{name}.xml"])
                self.assertTrue(any("cd588707fe03c76f19bda1b8092e136dcbe3fe90" in t["version"] for t in ext["tools"]
                                    if t["name"] == "DRAGON2"))
                self.assertFalse(mentions_path(json.dumps(rec), Path.home()), name)
        self.assertNotIn("production_table", specs["D3_l2_dragon2"])
        self.assertEqual(specs["D3_harmonized_v1"]["production_table"]["channels_mb"],
                         {"6012->5011": 70.0, "8016->5011": 35.0})

    def test_usine_runs_are_recorded(self):
        import hashlib
        plan = self.d3.usine_plan()
        self.assertEqual(sorted(p.name for p in (D3_FIX / "usine" / "runs").iterdir()),
                         sorted(f"{i['name']}.computational-run.json" for i in plan))
        for item in plan:
            with self.subTest(run=item["name"]):
                rec = json.loads((D3_FIX / "usine" / "runs" / f"{item['name']}.computational-run.json")
                                 .read_text(encoding="utf-8"))
                self.assertEqual([f.code for f in validate_artifact(rec).errors], [])
                self.assertEqual(rec["extension"]["exit_status"], 0)
                self.assertFalse(mentions_path(json.dumps(rec), Path.home()))
                for f in (D3_FIX / "usine" / "outputs" / item["name"]).iterdir():
                    self.assertEqual(rec["extension"]["output_hashes"][f"out/{f.name}"],
                                     hashlib.sha256(f.read_bytes()).hexdigest(), f.name)
                if item["kind"] == "level2" and not (os.environ.get("HEP_USINE_DATA")
                                                     and os.environ.get("HEP_DRAGON2_DATA")):
                    continue  # its tables are built from USINE's and DRAGON2's own files (not in the repository)
                want = {e["path"]: e["committed_form_sha256"] for e in rec["extension"]["input_manifest"]
                        if "committed_form_sha256" in e}
                d2 = os.environ.get("HEP_DRAGON2_DATA")
                got = self.d3.committed_hashes(item, Path(d2) if d2 else None, None)
                self.assertEqual(got, want)

    def test_ports_of_dragon2_code_and_inelastic_table(self):
        for e in (0.05, 0.3, 0.43, 0.6, 1.0, 1.51, 3.0, 100.0):
            for zi, ai, zf, af in ((6, 12, 5, 11), (8, 16, 5, 10), (8, 16, 4, 9), (6, 12, 4, 7)):
                self.assertEqual(self.d3.helium_production_ratio(e, zi, ai, zf, af), he_to_h_ratio(e, zi, ai, zf, af))
        self.assertAlmostEqual(self.d3.gas_columns("BronfFerr", 8.3, 4.0, 0.02)["nucleons"],
                               bronf_ferr_column(8.3, 4.0), places=12)
        inel = self.d3.load_inelastic()
        # relative 1e-12 against the committed table: libm (pow) differs across platforms in the last digits
        assert_close_tree(self, self.d3.table_nodes(), inel["ekn_gev"], "ekn_gev", rel=1e-12)
        self.assertEqual(sorted(inel["sigma_h_mb"]), sorted(self.d3.INELASTIC_NUCLIDES))
        for nuc, vals in inel["sigma_h_mb"].items():
            a = usine_translate.charge_and_mass(nuc)[1]
            self.assertAlmostEqual(inel["he_over_h"][nuc], 2.10 / a ** 0.055, places=12)
            self.assertTrue(all(v > 0 for v in vals))
            tail = [v for e, v in zip(inel["ekn_gev"], vals) if e >= 1000.0]
            self.assertEqual(len(set(tail)), 1, nuc)  # DRAGON2 clamps the energy at 1e6 MeV
        self.assertNotIn("Users", json.dumps(inel))


class TranslatorSourceItems(unittest.TestCase):
    """K3-2 (escalation 12): both translators translate sources.abundances or refuse it with a reason, handle the
    injection spectrum_variable that harmonized-v1 states, and the USINE translator refuses a gas density term without
    its unit instead of reading it as 0. Offline; nothing is run."""

    HARMONIZED_FILES = ("harmonized-v1", "harmonized-v1-isotopic", "harmonized-v1-convection", "harmonized-v1-decay",
                 "harmonized-v1-reacceleration", "harmonized-v1-losses")

    @staticmethod
    def harmonized(name="harmonized-v1-isotopic"):
        return json.loads((FIX / "specs" / f"{name}.json").read_text(encoding="utf-8"))["transport"]

    @staticmethod
    def with_sources(t, **injection_and_abundances):
        t = json.loads(json.dumps(t))
        abund = injection_and_abundances.pop("abundances", t["sources"].get("abundances"))
        t["sources"]["injection"] = [dict(i, **injection_and_abundances) for i in t["sources"]["injection"]]
        if abund is None:
            t["sources"].pop("abundances", None)
        else:
            t["sources"]["abundances"] = abund
        for i in t["sources"]["injection"]:
            for k in [k for k, v in i.items() if v is None]:
                del i[k]
        return t

    def dragon2(self, t):
        return dragon2_translate.spec_from_transport(t, "x", dragon2_provider.ILLUSTRATIVE_CHANNELS_MB, z_range=(4, 8),
                                                     ekn_range_gev=(0.05, 100.0))

    def test_harmonized_v1_states_the_injection_variable(self):
        for name in self.HARMONIZED_FILES:
            with self.subTest(file=name):
                inj = self.harmonized(name)["sources"]["injection"]
                self.assertEqual({i["spectrum_variable"] for i in inj}, {"kinetic_energy_per_nucleon"})
        self.assertEqual(usine_spec("harmonized-v1")["transport"], self.harmonized("harmonized-v1"))

    def test_dragon2_refuses_what_its_source_cannot_express(self):
        t = self.harmonized()
        with self.assertRaisesRegex(dragon2_run.SpecError, "factor beta"):  # harmonized-v1: per E_k/n
            self.dragon2(t)
        for variable in ("kinetic_energy_per_nucleon", "total_energy"):
            with self.subTest(variable=variable), self.assertRaisesRegex(dragon2_run.SpecError, "spectrum_variable"):
                self.dragon2(self.with_sources(t, spectrum_variable=variable,
                                               abundances=dragon2_translate.DRAGON2_OWN_ABUNDANCES))
        cases = {"parent list": (self.with_sources(t, spectrum_variable="rigidity"), "sources.abundances"),
                 "other text": (self.with_sources(t, spectrum_variable="rigidity", abundances="fitted"),
                                "sources.abundances"),
                 "eta": (self.with_sources(dragon2_translate.with_dragon2_sources(t), eta=1.0), "beta factor"),
                 "unknown variable": (self.with_sources(t, spectrum_variable="momentum"), "one of"),
                 "unknown key": (self.with_sources(t, measure="rigidity"), "keys among")}
        for why, (tr, pattern) in cases.items():
            with self.subTest(refused=why), self.assertRaisesRegex(dragon2_run.SpecError, pattern):
                self.dragon2(tr)

    def test_dragon2_translates_its_own_sources_and_records_defaults(self):
        t = self.harmonized()
        own = self.dragon2(dragon2_translate.with_dragon2_sources(t))
        raw = dragon2_run.spec_from_transport(t, "x", dragon2_provider.ILLUSTRATIVE_CHANNELS_MB, z_range=(4, 8),
                                              ekn_range_gev=(0.05, 100.0))
        # the run directory is the D1 translator's: same XML, same single injection slope; only notes are added
        self.assertEqual(dragon2_run.render_xml(dragon2_run.check_spec(own)),
                         dragon2_run.render_xml(dragon2_run.check_spec(raw)))
        self.assertEqual(own["injection_gamma"], raw["injection_gamma"])
        self.assertEqual(own["substitutes"][:len(raw["substitutes"])], raw["substitutes"])
        self.assertTrue(any("spectrum_variable 'rigidity'" in x for x in own["substitutes"]))
        self.assertTrue(any(dragon2_translate.DRAGON2_OWN_ABUNDANCES in x and "kept" in x for x in own["substitutes"]))
        unstated = self.dragon2(self.with_sources(t, spectrum_variable=None, abundances=None))
        self.assertTrue(any("spectrum_variable not stated: rigidity" in x for x in unstated["substitutes"]))
        self.assertTrue(any("sources.abundances not given" in x for x in unstated["substitutes"]))
        # the provider translates through this module, so a harmonized-v1 transport fails its point with the reason
        with self.assertRaisesRegex(dragon2_run.SpecError, "sources.abundances|spectrum_variable"):
            dragon2_translate.spec_from_transport(dragon2_provider.transport_for({"transport": t}, {}), "p",
                                                  dragon2_provider.ILLUSTRATIVE_CHANNELS_MB, z_range=(4, 8),
                                                  ekn_range_gev=(0.05, 100.0))

    def test_dragon2_command_line_applies_the_same_source_checks(self):
        """dragon2_run.py --from-transport goes through dragon2_translate: harmonized-v1's sources are refused (exit 2,
        no spec written), DRAGON2's own are translated and the written spec carries the source notes."""
        channels = D1_FIX / "channels-illustrative-decay.json"
        with tempfile.TemporaryDirectory() as td:
            for label, transport, code in (("harmonized-v1", self.harmonized(), 2),
                                           ("dragon2 sources", dragon2_translate.with_dragon2_sources(self.harmonized()),
                                            None)):
                with self.subTest(transport=label):
                    item, out = Path(td) / f"{code}.json", Path(td) / f"out-{code}"
                    item.write_text(json.dumps({"transport": transport}), encoding="utf-8")
                    proc = subprocess.run([sys.executable, "-I", str(RUN), "--from-transport", str(item), "--channels",
                                           str(channels), "--name", "cli", "--out", str(out), "--data-dir",
                                           str(Path(td) / "no-data")], capture_output=True, text=True, timeout=300)
                    doc = json.loads(proc.stdout)
                    if code == 2:
                        self.assertEqual(proc.returncode, 2, proc.stdout)
                        self.assertEqual(doc["status"], "error")
                        self.assertRegex(doc["error"], "spectrum_variable|sources.abundances")
                        self.assertFalse((out / "cli.spec.json").exists())
                    else:  # translated; stops later at the missing data directory (exit 3)
                        self.assertEqual((proc.returncode, doc["status"]), (3, "missing-dependency"), proc.stdout)
                        spec = json.loads((out / "cli.spec.json").read_text(encoding="utf-8"))
                        self.assertTrue(any("spectrum_variable 'rigidity'" in x for x in spec["substitutes"]))
                        self.assertTrue(any(dragon2_translate.DRAGON2_OWN_ABUNDANCES in x for x in spec["substitutes"]))

    def test_usine_injection_variable(self):
        t = usine_spec("harmonized-v1")["transport"]
        base = usine_translate.translate(t, "x", (0.04, 2000.0))
        self.assertEqual(base["source"]["eta_s"], 0.0)
        self.assertTrue(any("spectrum_variable 'kinetic_energy_per_nucleon'" in x for x in base["substitutes"]))
        cases = {("total_energy", None): 0.0, ("rigidity", None): -1.0, ("rigidity", 1.0): 0.0,
                 ("kinetic_energy_per_nucleon", -1.0): -1.0}
        for (variable, eta), want in cases.items():
            with self.subTest(variable=variable, eta=eta):
                got = usine_translate.translate(self.with_sources(t, spectrum_variable=variable, eta=eta), "x",
                                                (0.04, 2000.0))
                self.assertTrue(math.isclose(got["source"]["eta_s"], want, rel_tol=1e-12, abs_tol=1e-15))
        rig = usine_translate.translate(self.with_sources(t, spectrum_variable="rigidity"), "x", (0.04, 2000.0))
        init = usine_translate.render(rig, "<TOOL_HOME>/inputs", "<RUN_DIR>")["usine.init.par"]
        self.assertIn("eta_s[SHARED:-1", init)
        self.assertTrue(any("dRig/dE_k/n = (A/|Z|)/beta" in x for x in rig["substitutes"]))
        # not stated (e.g. the B1 and F1 transports): E_k/n, recorded as a default; the committed runs keep eta_s 0
        unstated = usine_translate.translate(self.with_sources(t, spectrum_variable=None), "x", (0.04, 2000.0))
        self.assertEqual(unstated["source"]["eta_s"], 0.0)
        self.assertTrue(any("sources.injection.spectrum_variable = kinetic_energy_per_nucleon" in x
                            for x in unstated["substitutes"]))
        for bad in ("momentum", "per-nucleon"):
            with self.subTest(refused=bad), self.assertRaisesRegex(usine_translate.SpecError, "spectrum_variable"):
                usine_translate.translate(self.with_sources(t, spectrum_variable=bad), "x", (0.04, 2000.0))

    def test_usine_abundances_translated_or_refused(self):
        t = usine_spec("harmonized-v1")["transport"]
        got = usine_translate.translate(t, "x", (0.04, 2000.0))
        self.assertEqual(got["norm_points"], {"C": 1.0, "O": 0.9})
        self.assertFalse(any("sources.abundances" in x and "not parsed" in x for x in got["substitutes"]))
        for text in ("fitted", "dragon2:BaseModel_DRAGONxsec.source.param", "solar"):
            with self.subTest(refused=text), self.assertRaisesRegex(usine_translate.SpecError, "sources.abundances"):
                usine_translate.translate(self.with_sources(t, abundances=text), "x", (0.04, 2000.0))
        unstated = usine_translate.translate(self.with_sources(t, abundances=None), "x", (0.04, 2000.0))
        self.assertEqual(unstated["norm_points"], got["norm_points"])
        self.assertTrue(any("sources.abundances not given" in x for x in unstated["substitutes"]))

    def test_usine_gas_term_without_unit_is_refused(self):
        t = usine_spec("harmonized-v1")["transport"]
        own = usine_spec("b1x-init-test")["transport"]
        # the D3 string that aborted a run: n_HI without its unit was read as 0 before K3
        for model in ("uniform in the thin disc, n_HI = 0.867, n_HII = 0.033 cm^-3, n_H2 = 0 cm^-3",
                      "n_H = 1", "n_H = 1 m^-3"):
            with self.subTest(model=model), self.assertRaisesRegex(usine_translate.SpecError, "without the unit"):
                usine_translate.translate(dict(own, gas=dict(own["gas"], model=model)), "x", (1.0, 10.0))
        with self.assertRaisesRegex(usine_translate.SpecError, "without the unit"):
            usine_translate.translate(dict(t, gas=dict(t["gas"], model="uniform, n_H = 1")), "x", (1.0, 10.0))
        ok = usine_translate.translate(dict(own, gas=dict(own["gas"], model="n_HI = 0.867 cm^-3, n_HII = 0.033 cm-3")),
                                       "x", (1.0, 10.0))
        self.assertTrue(math.isclose(ok["gas_cm3"]["HI"], 0.867, rel_tol=1e-12))
        self.assertTrue(math.isclose(ok["gas_cm3"]["HII"], 0.033, rel_tol=1e-12))
        self.assertEqual(ok["gas_cm3"]["H2"], 0.0)  # not written at all: 0, recorded
        self.assertTrue(any("H2 not given, 0 cm^-3" in x for x in ok["substitutes"]))


@unittest.skipUnless(os.environ.get("HEP_USINE_LIVE_TEST") == "1", "live USINE runs: set HEP_USINE_LIVE_TEST=1, "
                     "HEP_USINE_BIN and HEP_USINE_DATA")
class LiveUsineD3(unittest.TestCase):
    """D3: the matched run m-isotopic is built again by d3_study.py, run with the installed USINE and must reproduce
    the recorded tables within relative 1e-6 (one USINE run of a few seconds)."""

    def test_matched_run_reproduces_the_recorded_tables(self):
        self.assertIsNone(live_usine_reason())
        d3 = load_d3_study()
        binary, data_dir = Path(os.environ["HEP_USINE_BIN"]), Path(os.environ["HEP_USINE_DATA"])
        item = d3.plan_item("m-isotopic")
        with tempfile.TemporaryDirectory() as td:
            res = d3.execute(item, Path(td), binary, data_dir, None, None)
            self.assertTrue(res["ok"], res["log_tail"])
            for f in (D3_FIX / "usine" / "outputs" / "m-isotopic").iterdir():
                rerun = usine_reader.read_table(Path(td) / "runs" / "m-isotopic" / "out" / f.name)
                recorded = usine_reader.read_table(f)
                for a, b in zip(rerun[1], recorded[1]):
                    self.assertTrue(math.isclose(a, b, rel_tol=USINE_LIVE_RTOL, abs_tol=1e-300), (f.name, a, b))

F1_FIX = FIX / "f1"
try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE_NUMPY_SCIPY_F1 = True
except ImportError:  # pragma: no cover
    HAVE_NUMPY_SCIPY_F1 = False
FORCE_FIELD = ROOT / "skills" / "hep-measurement" / "scripts" / "solar_modulation_force_field.py"


def _f1_usine_spec(**changes):
    """The B1X run spec (USINE's own inputs, network to Si-30) with the transport changed as given."""
    t = json.loads(json.dumps(usine_spec("b1x-init-test")["transport"]))
    for key, value in changes.items():
        t[key] = value
    return t


class UsineF1Offline(unittest.TestCase):
    """Work package F1, offline: force-field modulation by USINE (quantities at phi, the reader's modulated tables and
    their phi check, agreement with the plugin's force-field tool contract on recorded USINE tables), production-channel
    modifiers (validation, the scaled table, the second fProd line, never rendered into a fixture), pure-secondary
    isotopes, and the provider's new point parameters (low break, high-break Deltabreak kept, one phi, xs triplets)."""

    def test_modulation_quantities_and_record(self):
        t = usine_translate.translate(_f1_usine_spec(), "f1-q", (0.5, 100.0), phi_gv=0.7312345)
        self.assertEqual(t["solar_modulation"], {"model": "SolMod0DFF", "phi_gv": 0.7312345, "rig0_gv": 0.2})
        self.assertIn(":KEKN:0.,0.7312345", usine_translate.quantities(t))
        self.assertEqual(usine_translate.quantities(t).count("KEKN"), 1)   # one phi list per E-type group
        self.assertTrue(any("SolMod0DFF" in sub for sub in t["substitutes"]))
        plain = usine_translate.translate(_f1_usine_spec(), "f1-q", (0.5, 100.0))
        self.assertIsNone(plain["solar_modulation"])
        self.assertIn(":KEKN:0.;", usine_translate.quantities(plain))
        for bad in (-0.1, float("nan"), "x"):
            with self.assertRaises(usine_translate.SpecError):
                usine_translate.translate(_f1_usine_spec(), "f1-q", (0.5, 100.0), phi_gv=bad)

    def test_production_modifier_validation_and_table(self):
        mod = {"channel": "12C+H->11B", "norm": 1.2, "slope_le": 0.5, "threshold_ekn_gev": 8.0}
        t = usine_translate.translate(_f1_usine_spec(), "f1-m", (0.5, 100.0), production_modifiers=[mod])
        self.assertEqual(t["production_modifiers"][0]["fragment"], "11B")
        files = usine_translate.render(t, "<TOOL_HOME>/inputs", "<RUN_DIR>")
        self.assertEqual(set(files), {"usine.init.par"})   # the scaled table is never rendered into a fixture
        self.assertIn("fProd @ M=1 @ <RUN_DIR>/xs_production_modified.dat", files["usine.init.par"])
        self.assertLess(files["usine.init.par"].index("sigProdGALPROP17_OPT12.dat"),
                        files["usine.init.par"].index("xs_production_modified.dat"))
        for bad in ({**mod, "channel": "12C->11B"}, {**mod, "channel": "56Fe+H->11B"}, {**mod, "norm": 0.0},
                    {**mod, "extra": 1}, {k: v for k, v in mod.items() if k != "slope_le"}):
            with self.assertRaises(usine_translate.SpecError):
                usine_translate.translate(_f1_usine_spec(), "f1-m", (0.5, 100.0), production_modifiers=[bad])
        with self.assertRaises(usine_translate.SpecError):   # the ILLUSTRATIVE sets have no production file
            usine_translate.translate(usine_spec("d1-isotopic")["transport"], "f1-m", (0.5, 100.0),
                                      production_modifiers=[mod])
        # the scaled table, from a stand-in production file in USINE's format (made-up numbers, not USINE's)
        with tempfile.TemporaryDirectory() as scratch:
            xs = Path(scratch) / "XS_NUCLEI"
            xs.mkdir()
            rows = "\n".join(f"{10.0 + i:.6e}\t{20.0 + i:.6e}" for i in range(5))
            (xs / "sigProdGALPROP17_OPT12.dat").write_text(
                "# stand-in\n sigma    mb      H,He\n\n1.000000e-01      1.000000e+03    5\n\n16O -> 11B\n" + rows
                + "\n\n12C -> 11B\n" + rows + "\n", encoding="utf-8")
            text = usine_translate.modified_production_table(t, Path(scratch))
        lines = text.splitlines()
        block = [ln.split() for ln in lines[lines.index("12C -> 11B") + 1:][:5]]
        self.assertNotIn("16O -> 11B", text)
        for i, (h_val, he_val) in enumerate(block):
            ekn = 0.1 * 10 ** i
            bias = (ekn / 8.0) ** 0.5 if ekn < 8.0 else 1.0
            self.assertAlmostEqual(float(h_val), 1.2 * bias * (10.0 + i), delta=1e-5 * (10.0 + i))
            self.assertAlmostEqual(float(he_val), 20.0 + i, delta=1e-5)   # target He untouched

    def test_pure_secondary_isotopes(self):
        src = dict(_f1_usine_spec()["sources"])
        src["abundances"] += " pure:13C,15N"
        t = usine_translate.translate(_f1_usine_spec(sources=src), "f1-p", (0.5, 100.0))
        self.assertEqual(t["pure_secondaries"][-2:], ["13C", "15N"])
        self.assertIn("PureSecondaries @ M=0 @ " + ",".join(t["pure_secondaries"]),
                      usine_translate.render(t, "<TOOL_HOME>/inputs", "<RUN_DIR>")["usine.init.par"])
        src["abundances"] = src["abundances"].replace("pure:13C,15N", "pure:10B")   # B is not normalised
        with self.assertRaises(usine_translate.SpecError):
            usine_translate.translate(_f1_usine_spec(sources=src), "f1-p", (0.5, 100.0))

    def test_reader_reads_modulated_tables_with_phi_check(self):
        out = F1_FIX / "force-field"
        tables = usine_reader.read_run(out, "Model1DKisoVc", ["11B", "12C"], 0.7312345)
        lis = usine_reader.read_run(out, "Model1DKisoVc", ["11B", "12C"], 0.0)
        self.assertLess(tables["11B"][1][14], lis["11B"][1][14])   # modulation lowers the flux at 1 GeV/n
        with self.assertRaises(usine_reader.ReadError):
            usine_reader.read_run(out, "Model1DKisoVc", ["11B"], 0.75)   # header phi 0.731 GV
        with tempfile.TemporaryDirectory() as scratch:
            for name in ("phi0_731GV", "phi0_800GV"):
                shutil.copy(out / "local_fluxes_11B_Ekn_Model1DKisoVc_SolMod0DFF_phi0_731GV.out",
                            Path(scratch) / f"local_fluxes_11B_Ekn_Model1DKisoVc_SolMod0DFF_{name}.out")
            with self.assertRaises(usine_reader.ReadError):   # two modulated tables: ambiguous
                usine_reader.modulated_table(Path(scratch), "11B", "Model1DKisoVc")

    def test_usine_force_field_agrees_with_the_tool_contract(self):
        """USINE's SolMod0DFF on its own LIS table equals the plugin's force-field tool (subprocess, the tool
        contract solar_modulation_force_field) within 1e-3 (USINE's masses and 6-digit tables)."""
        from core.constants.physical import nuclear_mass_gev
        out = F1_FIX / "force-field"
        lis = usine_reader.read_run(out, "Model1DKisoVc", ["11B", "12C"], 0.0)
        toa = usine_reader.read_run(out, "Model1DKisoVc", ["11B", "12C"], 0.7312345)
        with tempfile.TemporaryDirectory() as scratch:
            for nuc, (z, a) in (("11B", (5, 11)), ("12C", (6, 12))):
                table = Path(scratch) / f"{nuc}.json"
                table.write_text(json.dumps({"variable": "Ek_per_nucleon",
                                             "points": [[x, y] for x, y in zip(*lis[nuc])]}), encoding="utf-8")
                for k in (2, 8, 20, 40, 60, 75):
                    ekn, flux = toa[nuc][0][k], toa[nuc][1][k]
                    proc = subprocess.run([sys.executable, str(FORCE_FIELD), "--modulate", "--energy", repr(ekn),
                                           "--energy-kind", "Ek_per_nucleon", "--mass", repr(nuclear_mass_gev(z, a)),
                                           "--charge", str(z), "--mass-number", str(a), "--phi", "0.7312345",
                                           "--lis-table", str(table)], capture_output=True, text=True, timeout=120)
                    self.assertEqual(proc.returncode, 0, proc.stdout)
                    with self.subTest(nuclide=nuc, ekn=ekn):
                        self.assertLess(abs(json.loads(proc.stdout)["flux_toa"] / flux - 1.0), 1e-3)

    def test_provider_point_parameters(self):
        base = _f1_usine_spec()
        base["diffusion"]["breaks"] = [{"kind": "low", "R_break_gv": 4.0, "delta_below": -0.8, "s": 0.05},
                                       base["diffusion"]["breaks"][0]]
        change = base["diffusion"]["delta"] - base["diffusion"]["breaks"][1]["delta_above"]
        t, notes = usine_provider.transport_for({"transport": base}, {"R_break_gv": 3.0, "delta_below": -0.5,
                                                                     "delta": 0.5})
        low, high = t["diffusion"]["breaks"]
        self.assertEqual((low["R_break_gv"], low["delta_below"], low["s"]), (3.0, -0.5, 0.05))
        self.assertAlmostEqual(0.5 - high["delta_above"], change, places=12)   # Deltabreak kept
        self.assertEqual(len(notes), 1)
        with self.assertRaises(usine_provider.PointError):   # no low break to set
            usine_provider.transport_for({"transport": _f1_usine_spec()}, {"R_break_gv": 3.0})
        with self.assertRaises(usine_provider.PointError):
            usine_provider.transport_for({"transport": base}, {"unknown_kms": 1.0})
        phi, mods = usine_provider.run_options({"phi_2011_2016_gv": 0.7, "xs_norm_12C_H_11B": 1.1,
                                                "xs_slope_12C_H_11B": 0.1, "xs_threshold_12C_H_11B_gev": 8.0})
        self.assertEqual(phi, 0.7)
        self.assertEqual(mods, [{"channel": "12C+H->11B", "norm": 1.1, "slope_le": 0.1, "threshold_ekn_gev": 8.0}])
        for bad in ({"phi_a_gv": 0.5, "phi_b_gv": 0.6}, {"xs_norm_12C_H_11B": 1.1},
                    {"xs_threshold_12C_H_11B": 8.0, "xs_norm_12C_H_11B": 1.0, "xs_slope_12C_H_11B": 0.0}):
            with self.assertRaises(usine_provider.PointError):
                usine_provider.run_options(bad)
        self.assertEqual(usine_provider.run_options({"delta": 0.5}), (0.0, []))


# ---------------------------------------------------------------------------------------------- C2UF (appended)
TWO_DATASET_FIX = FIX / "c2uf"


def _same_document(case, a, b, where="response", rel=1e-12):
    """Equal JSON documents; numbers equal within relative rel (default 1e-12, the platform's last digits), all
    else exactly."""
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        case.assertEqual(type(a), type(b), where)
    if isinstance(a, dict):
        case.assertEqual(sorted(a), sorted(b), where)
        for k in a:
            _same_document(case, a[k], b[k], f"{where}/{k}", rel)
    elif isinstance(a, list):
        case.assertEqual(len(a), len(b), where)
        for i, (x, y) in enumerate(zip(a, b)):
            _same_document(case, x, y, f"{where}[{i}]", rel)
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        case.assertTrue(math.isclose(a, b, rel_tol=rel, abs_tol=0.0), (where, a, b))
    else:
        case.assertEqual(a, b, where)


@unittest.skipUnless(HAVE_NUMPY, "needs numpy and scipy")
class EmulatorPinnedResponses(unittest.TestCase):
    """C2UF: the per-model declaration leaves the committed E2 model's answers unchanged (responses recorded with the
    provider before the change; on the recording machine they agree to the last bit)."""

    def test_e2_responses_are_unchanged(self):
        pinned = json.loads((TWO_DATASET_FIX / "e2-pinned-responses.json").read_text(encoding="utf-8"))
        env = {k: v for k, v in os.environ.items() if k != "HEP_EMULATOR_ML_ARTIFACT"}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for case in pinned["cases"]:
            proc, doc = e2_call(case["request"], env=env, allow_outside=case["allow_outside"])
            self.assertEqual(proc.returncode, case["exit"], case["name"])
            for res in doc.get("results") or []:
                (res.get("evaluation") or {}).pop("elapsed_s", None)
            # relative 1e-4: the GP's scipy/numpy linear algebra differs across platforms (the emulator sigma of
            # the ill-conditioned kernel drifted 6e-6 relative on Linux); recorded on macOS
            _same_document(self, case["response"], doc, case["name"], rel=1e-4)


# The C2UF emulator fixture is K4's retraining with the kernel condition bound 1e10 (L1, decision B1.3): portable, so
# the A1.21 skip on a self-check refusal is gone and such a refusal fails the tests.


@unittest.skipUnless(HAVE_NUMPY, "needs numpy and scipy")
class EmulatorPerModelDeclaration(unittest.TestCase):
    """C2UF: a model that lists its observables declares them (B/C and 10Be/9Be on ekn), its box as the domain and a
    '+model.<hash>' version; requests are answered per observable slice; an undeclared axis is refused."""

    @classmethod
    def setUpClass(cls):
        cls.artifact = TWO_DATASET_FIX / "emulator.ml-artifact.json"
        cls.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HEP_EMULATOR_ML_ARTIFACT=str(cls.artifact))
        proc = subprocess.run([sys.executable, str(EMULATOR_PROVIDER), "--declaration"], capture_output=True,
                              text=True, timeout=300, env=cls.env)
        try:
            out = json.loads(proc.stdout)
        except ValueError:
            out = None
        try:
            cls.decl = out["declaration"]
        except (TypeError, KeyError):
            raise AssertionError(f"--declaration failed (exit {proc.returncode}): stdout {proc.stdout!r} "
                                 f"stderr {proc.stderr[-2000:]!r}") from None
        cls.model = json.loads((TWO_DATASET_FIX / "emulator-model.json").read_text(encoding="utf-8"))

    def test_declaration_comes_from_the_model(self):
        sha = hashlib.sha256((TWO_DATASET_FIX / "emulator-model.json").read_bytes()).hexdigest()
        self.assertEqual(self.decl["id"], "emulator")
        self.assertEqual(self.decl["version"], f"1.0.0+model.{sha[:12]}")
        self.assertEqual(self.decl["observables"], ["10Be/9Be", "B/C"])
        self.assertEqual(self.decl["axes"], ["ekn"])
        self.assertEqual(self.decl["domain"], {f["name"]: {"min": f["min"], "max": f["max"]}
                                               for f in self.model["features"]})
        self.assertEqual(self.decl["axis_ranges"]["ekn"]["min"], 0.05)

    def test_both_observables_are_answered_and_rigidity_is_refused(self):
        obs = self.model["outputs"]["observables"]
        point = {"D0_cm2_s": 3.0e28, "delta": 0.45, "V_A_kms": 70.0, "V_c_kms": 1.0}
        req = {"protocol": "cr-provider/1", "provider": "emulator", "provider_version": self.decl["version"],
               "transport": self.model["context"]["transport"], "points": [point],
               "observables": [{"id": o["id"], "axis": "ekn", "unit": "GeV/n",
                                "bins": [[a, b] for a, b in zip(o["edges"], o["edges"][1:])]} for o in obs],
               "want": ["lis"], "seed": None}
        proc, doc = e2_call(req, env=self.env)
        self.assertEqual(doc["status"], "ok", doc)
        preds = doc["results"][0]["predictions"]
        self.assertEqual([len(p["values"]["values"]) for p in preds], [len(o["edges"]) - 1 for o in obs])
        self.assertEqual(preds[1]["observable"]["process"], obs[1]["observable"]["process"])
        self.assertEqual(preds[0]["parameter_point"]["ml_artifact"], "ml-emulator-usine-c2uf")
        sub = dict(req, observables=[dict(req["observables"][1], bins=req["observables"][1]["bins"][2:5])])
        proc, doc = e2_call(sub, env=self.env)
        self.assertEqual(doc["results"][0]["predictions"][0]["values"]["values"], preds[1]["values"]["values"][2:5])
        bad = dict(req, observables=[{"id": "B/C", "axis": "rigidity", "unit": "GV", "bins": [[2.0, 3.0]]}])
        proc, doc = e2_call(bad, env=self.env)
        self.assertEqual(doc["status"], "failed")

F1_WINDOWS = {"BIG": ((0.45, 0.52), (0.266, 0.338)), "SLIM": ((0.49, 0.53), (0.258, 0.304)),
              "QUAINT": ((0.43, 0.50), (0.297, 0.367))}   # VALIDATION.md CRPROP-F1, fixed before any fit (D9)


class UsineF1Record(unittest.TestCase):
    """F1 record (tests/adapters/fixtures/cr_propagation/f1/f1-reproduction.json, written by
    examples/bc-usine-reproduction/run.py stage record): F1-2 labels, the D9 verdict recomputed from the recorded best
    fits against the windows of VALIDATION.md, the USINE run tally within the A1.8 cap, no data value committed. With
    HEP_USINE_DATA set, the data stage is rerun and its dataset-record validates with the same labels."""

    @classmethod
    def setUpClass(cls):
        cls.rec = json.loads((F1_FIX / "f1-reproduction.json").read_text(encoding="utf-8"))

    def test_f1_2_labels(self):
        self.assertEqual(self.rec["data"]["status"], ["observed"])
        self.assertTrue(self.rec["data"]["covariance_note"].startswith("model-supplied"))
        self.assertEqual(self.rec["crdb_crosscheck"]["row_roles"], ["secondary"])
        self.assertTrue(self.rec["crdb_crosscheck"]["label"].startswith("secondary"))

    def test_d9_recomputed(self):
        kpc2_myr = (648000.0 / math.pi * 1.495978707e13 * 1e3) ** 2 / (1e6 * 365.25 * 86400.0)
        for fam in self.rec["families"]:
            (d_lo, d_hi), (k_lo, k_hi) = F1_WINDOWS[fam.split("-")[0]]
            row = self.rec["families"][fam]
            with self.subTest(family=fam):
                pt = row["best_fit"]
                k10 = pt["D0_cm2_s"] / kpc2_myr * 10 ** pt["delta"]
                self.assertAlmostEqual(k10, row["K10"], places=9)
                self.assertAlmostEqual(row["delta_window"][0], d_lo, places=6)
                self.assertAlmostEqual(row["delta_window"][1], d_hi, places=6)
                self.assertAlmostEqual(row["K10_window"][0], k_lo, delta=5e-4)
                self.assertAlmostEqual(row["K10_window"][1], k_hi, delta=5e-4)
                self.assertEqual(row["delta_in_window"], d_lo <= pt["delta"] <= d_hi)
                self.assertEqual(row["K10_in_window"], row["K10_window"][0] <= k10 <= row["K10_window"][1])
                passed = row["status"] == "converged" and row["delta_in_window"] and row["K10_in_window"]
                self.assertEqual(row["D9"].startswith("passed"), passed)
        judged = self.rec["judged_for_D9"]
        self.assertEqual(judged[:2], ["BIG", "SLIM"])
        self.assertEqual(judged[2], "QUAINT-Vc0" if (self.rec.get("quaint_vc_boundary_kkt") or {}).get("kkt_ok")
                         else "QUAINT")
        self.assertEqual(self.rec["D9_all"], all(self.rec["families"][f]["D9"] == "passed" for f in judged))

    def test_budget_and_no_data_values(self):
        self.assertLessEqual(self.rec["usine_runs"], 2600)   # A1.8 cap of F1 raised to 2600 by A1.16
        text = (F1_FIX / "f1-reproduction.json").read_text(encoding="utf-8")
        self.assertNotIn('"values"', text)
        self.assertNotIn('"edges"', text)

    def test_k1_rejudge_under_the_noise_rule(self):
        """K1-2: BIG, SLIM and QUAINT-Vc0 re-judged under the noise-aware rule of VALIDATION.md CRPROP-K1 (k = 0.5,
        EDM <= max(1e-5, k sigma_noise)), each with its measured noise floor, threshold and EDM; at most 600 USINE runs."""
        rj = self.rec["rejudge"]
        self.assertEqual(rj["work_package"], "K1")
        self.assertLessEqual(rj["usine_runs"], 600)
        self.assertEqual(rj["families"], ["BIG", "QUAINT-Vc0", "SLIM"])
        for fam in rj["families"]:
            row = self.rec["families"][fam]
            noise, conv = row["noise"], row["convergence"]
            with self.subTest(family=fam):
                self.assertEqual((noise["mode"], noise["k"]), ("measure", 0.5))
                self.assertGreater(noise["sigma_m2lnl"], 0.0)
                self.assertLessEqual(noise["evaluations"], noise["max_evaluations"])
                thr = max(1e-5, 0.5 * noise["sigma_m2lnl"])
                self.assertLessEqual(abs(conv["edm_threshold"] - thr), 1e-12 * thr)
                self.assertEqual(row["status"], conv["status"])
                if conv["status"] == "converged":
                    self.assertEqual(conv["reasons"], [])
                    self.assertLessEqual(conv["edm"], conv["edm_threshold"])
                else:
                    self.assertTrue(conv["reasons"])
                    if conv["edm"] is not None and "gradient_not_small" in conv["reasons"]:
                        self.assertGreater(conv["edm"], conv["edm_threshold"])

    @unittest.skipUnless(os.environ.get("HEP_USINE_DATA") and HAVE_NUMPY_SCIPY_F1, "needs HEP_USINE_DATA, numpy, scipy")
    def test_data_stage_rebuilds_the_labelled_record(self):
        with tempfile.TemporaryDirectory() as scratch:
            proc = subprocess.run([sys.executable, str(ROOT / "examples" / "bc-usine-reproduction" / "run.py"),
                                   "--out", scratch, "--stages", "data"], capture_output=True, text=True, timeout=600)
            self.assertEqual(proc.returncode, 0, proc.stdout[-800:] + proc.stderr[-800:])
            doc = json.loads((Path(scratch) / "data" / "bc-observed.json").read_text(encoding="utf-8"))
            self.assertEqual(doc["status"], self.rec["data"]["status"])
            self.assertTrue(validate_artifact(doc).ok)
            self.assertEqual(doc["extension"]["covariance"]["note"], self.rec["data"]["covariance_note"])


if __name__ == "__main__":
    unittest.main()
