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
                self.assertNotIn(str(Path.home()), json.dumps(doc))
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
                                 "USINE": "proposed"})
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


if __name__ == "__main__":
    unittest.main()
