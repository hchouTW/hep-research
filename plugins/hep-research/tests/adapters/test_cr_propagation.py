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
from tests.core.provider_conformance import ProviderConformance  # noqa: E402

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
        self.assertAlmostEqual(slab["transport_pars"]["Va"], 5.0 * math.sqrt(5.0 / 0.1), places=6)
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
                got = usine_reader.ratio_of_bin_integrals(tables, "B/C", res["bc_rigidity_edges_gv"], "rigidity")
                self.assertEqual(got, res["runs"][name]["B/C"])
                if "10Be/9Be" in res["runs"][name]:
                    got = usine_reader.ratio_of_bin_integrals(tables, "10Be/9Be", res["be_ekn_edges_gev"], "ekn")
                    self.assertEqual(got, res["runs"][name]["10Be/9Be"])

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
        self.assertEqual(set(decl["domain"]), set(usine_provider.POINT_TARGETS))
        lo, hi = usine_provider.ekn_range(USINE_REQUEST["observables"], ["9Be", "10Be", "10B", "11B", "12C"])
        self.assertEqual(lo, 0.1)
        self.assertEqual(hi, max(usine_reader.ekn_from_rigidity(200.0, z, a) for z, a in ((5, 10), (5, 11), (6, 12))))
        t = usine_provider.transport_for({}, {"V_c_kms": 5.0, "L_kpc": 6.0, "eta": -0.5})
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


if __name__ == "__main__":
    unittest.main()
