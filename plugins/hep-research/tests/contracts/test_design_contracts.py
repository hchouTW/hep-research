"""Detector system design M0: tool contract 1.1.0 (ART-40..ART-48) and the declared directions of the M0 contracts
(tracker_resolution momentum, charge_confusion_rate gaussian-core), checked numerically against the tools and against
known tail and misalignment counterexamples (T-57, ART-45, ART-46, RSK-01); version compatibility (T-59)."""
from __future__ import annotations

import copy
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from statistics import NormalDist

import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts.tool_contract import check  # noqa: E402
from core.interpreter_guard import child_flags  # noqa: E402
from design_fixtures import attach_cases, fake_contract  # noqa: E402

CONTRACTS = ROOT / "contracts" / "tool_contracts"
SCRIPTS = ROOT / "skills" / "hep-detector" / "scripts"
PROTON = 0.93827208816
PHI = NormalDist().cdf


def tool(script: str, *args) -> dict:
    p = subprocess.run([sys.executable, *child_flags(), "-I", "-B", str(SCRIPTS / script), *map(str, args)], capture_output=True,
                       text=True, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads(p.stdout)


def momentum(positions, sigma_um=10.0, field=0.5, x0=0.08, pt=1000.0) -> dict:
    return tool("tracker_resolution.py", "momentum", "--positions-m", *positions, "--point-resolution-um", sigma_um,
                "--field-tesla", field, "--x-over-x0", x0, "--charge", 1, "--mass-gev", PROTON, "--pt", pt)


def confusion(rigidity, sigma_inv_r) -> float:
    out = tool("charge_confusion_rate.py", "gaussian-core", "--edges", rigidity, 2 * rigidity, "--sigma-inv-r", sigma_inv_r)
    return out["bins"][0]["lower_bound_at_low_edge"]


LAYOUT = [0.0, 0.75, 1.5, 2.25, 3.0]


# ---------------------------------------------------------------- the shipped contracts pass the checker


def case_m0_contracts_pass_with_help_check():
    """ART-47: the M0 contracts match their tools' command lines (help check) and are consistent design blocks."""
    for name in ("tracker_resolution", "charge_confusion_rate"):
        res = check(json.loads((CONTRACTS / f"{name}.json").read_text()))
        assert res["status"] == "pass", (name, res["findings"])


# ---------------------------------------------------------------- T-57: per-input directions (ART-45)


def case_t57_sigma_inv_r_order_preserving():
    """ART-45: the confusion rate's sigma(1/R) input, varied at two points: a better (smaller) curvature resolution
    gives a better (smaller) rate, so the input is order-preserving as declared."""
    contract = json.loads((CONTRACTS / "charge_confusion_rate.json").read_text())
    m = contract["operations"][0]["design"]["figures_of_merit"][0]["inputs"][1]
    assert (m["input"], m["direction"]) == ("sigma_inv_r", "order-preserving")
    assert confusion(1000.0, 2e-4) < confusion(1000.0, 4e-4)
    # and through the declared mapping sigma(1/R) = (relative resolution) / R: a better resolution, a smaller rate
    assert confusion(1000.0, 0.06 / 1000.0) < confusion(1000.0, 0.49 / 1000.0)


# ---------------------------------------------------------------- T-57: bound directions (ART-46, RSK-01)


def case_t57_gaussian_core_is_a_lower_bound_against_tails_and_offset():
    """ART-46: a curvature distribution with a non-Gaussian tail (a Laplace component of fraction 1e-3 and scale
    5 sigma, as large-angle scattering or wrong hits make) has a larger wrong-sign rate than the Gaussian-core value,
    so the operation is optimistic (a lower bound); a curvature offset raises one sign's rate above the no-offset
    value, which is why the contract's validity domain requires a zero offset."""
    R, sigma = 1000.0, 0.49 / 1000.0
    core = confusion(R, sigma)
    k = 1.0 / R
    assert math.isclose(core, PHI(-k / sigma), rel_tol=1e-9)
    f, lam = 1e-3, 5 * sigma
    tailed = (1 - f) * PHI(-k / sigma) + f * 0.5 * math.exp(-k / lam)
    assert tailed > core
    offset = 0.3 * sigma
    assert PHI(-(k - offset) / sigma) > core  # the sign whose curvature the offset pulls toward zero


def _toy_curvature_sigma(positions, sigma_m, align_m, n=4000, seed=7) -> float:
    """Spread of the least-squares curvature 2c of y = a + b x + c x^2 fitted to hits with Gaussian point errors and
    a fixed random misalignment per toy (standard library only)."""
    rng = random.Random(seed)
    xs = positions
    s = [sum(x ** p for x in xs) for p in range(5)]
    m = [[s[0], s[1], s[2]], [s[1], s[2], s[3]], [s[2], s[3], s[4]]]

    def solve(rhs):
        a = [row[:] + [r] for row, r in zip(m, rhs)]
        for i in range(3):
            piv = a[i][i]
            for j in range(i + 1, 3):
                fct = a[j][i] / piv
                for c in range(i, 4):
                    a[j][c] -= fct * a[i][c]
        out = [0.0] * 3
        for i in (2, 1, 0):
            out[i] = (a[i][3] - sum(a[i][c] * out[c] for c in range(i + 1, 3))) / a[i][i]
        return out
    ks = []
    for _ in range(n):
        ys = [rng.gauss(0, sigma_m) + rng.gauss(0, align_m) for _ in xs]
        rhs = [sum(y * x ** p for x, y in zip(xs, ys)) for p in range(3)]
        ks.append(2 * solve(rhs)[2])
    mean = sum(ks) / n
    return math.sqrt(sum((k - mean) ** 2 for k in ks) / (n - 1))


def case_t57_tracker_optimistic_above_crossover_against_misalignment():
    """ART-46, ART-48: above the crossover rigidity the exact-fit core is optimistic: a toy fit with the same point
    errors reproduces the tool's curvature error, and the same fit with a layer misalignment as large as the point
    resolution (not in the tool) is worse."""
    out = momentum(LAYOUT)
    p = out["points"][0]
    assert p["intrinsic_relative"] >= p["scattering_relative"]  # measurement-dominated at 1000 GV
    tool_sigma_k = out["intrinsic"]["sigma_curvature_per_m"]
    ideal = _toy_curvature_sigma(LAYOUT, 10e-6, 0.0)
    misaligned = _toy_curvature_sigma(LAYOUT, 10e-6, 10e-6)
    assert abs(ideal / tool_sigma_k - 1) < 0.05
    assert misaligned > 1.2 * tool_sigma_k


def case_t57_tracker_below_crossover_is_not_a_bound():
    """ART-48, FID-04: below the crossover the PDG 0.016 GeV form without the Highland log term overstates thin-material
    scattering, so the tool's total is not a lower bound there (the contract declares an estimate)."""
    out = momentum(LAYOUT, pt=10.0)
    p = out["points"][0]
    assert p["scattering_relative"] > p["intrinsic_relative"]  # scattering-dominated at 10 GV
    x0, beta = 0.08, p["beta"]
    highland_log = p["scattering_relative_highland"] * (1 + 0.038 * math.log(x0 / beta ** 2))
    assert highland_log < p["scattering_relative"]
    assert math.hypot(p["intrinsic_relative"], highland_log) < p["total_relative"]
    contract = json.loads((CONTRACTS / "tracker_resolution.json").read_text())
    pieces = contract["operations"][0]["design"]["figures_of_merit"][0]["bound"]
    assert [x["bound"] for x in pieces] == ["optimistic", "estimate"]


# ---------------------------------------------------------------- T-59: versions and 1.1.0 checks (ART-42, ART-43)


def case_t59_contract_versions():
    """ART-43: 1.0.0 contracts still validate; a 1.1.0 contract with a design block validates; a 1.0.0 contract that
    uses a 1.1.0 feature is refused."""
    old = json.loads((CONTRACTS / "tag_and_probe_efficiency.json").read_text())
    assert old["contract_version"] == "1.0.0" and check(old)["status"] == "pass"
    fake = dict(fake_contract("syn-x", "momentum-resolution-core", "estimate"),
                entry="skills/hep-detector/scripts/tracker_resolution.py")  # an existing file; help not compared
    assert check(fake, help_check=False)["status"] == "pass", check(fake, help_check=False)["findings"]
    old = dict(copy.deepcopy(fake), contract_version="1.0.0")
    assert "tool.needs_1_1_0" in {f["code"] for f in check(old, help_check=False)["findings"]}


def case_t59_positionals_and_config_fields_against_help():
    """ART-42: a positional config file is declared with its fields and compared with the usage line."""
    doc = {"contract_version": "1.1.0", "tool_id": "toy-spectrometer", "entry": "skills/hep-detector/scripts/toy_spectrometer.py",
           "operations": [{"operation_id": "resolution", "summary": "resolution of the toy at given rigidities",
                           "invocation": {"kind": "cli", "output": "json-stdout",
                                          "positionals": [{"position": 0, "input": "config"}],
                                          "options": [{"flag": "--species", "input": "species"},
                                                      {"flag": "--rigidity", "input": "rigidity"},
                                                      {"flag": "--era", "input": "era"}]},
                           "inputs": [{"name": "config", "kind": "path", "unit": "n/a", "required": True,
                                       "constraint": "JSON configuration",
                                       "fields": [{"field": "field_T", "kind": "magnetic-field", "unit": "T",
                                                   "constraint": "> 0"}]},
                                      {"name": "species", "kind": "parameter", "unit": "n/a", "required": True, "constraint": "a species"},
                                      {"name": "rigidity", "kind": "rigidity", "unit": "GV", "required": True, "constraint": "> 0"},
                                      {"name": "era", "kind": "parameter", "unit": "n/a", "required": False, "constraint": "an era"}],
                           "outputs": [{"name": "sigma", "kind": "relative-resolution", "unit": "1"}],
                           "failure_states": [{"exit_code": 2, "status": "invalid-input", "meaning": "bad input"}],
                           "required_capabilities": [], "purposes": ["exploration"],
                           "side_effects": {"writes_files": False, "network": False, "subprocess": False}}]}
    res = check(doc)
    assert res["status"] == "pass", res["findings"]
    bad = copy.deepcopy(doc)
    bad["operations"][0]["invocation"].pop("positionals")
    codes = {f["code"] for f in check(bad)["findings"]}
    assert {"tool.positional_mismatch", "tool.input_unreachable"} <= codes
    fields_on_number = copy.deepcopy(doc)
    fields_on_number["operations"][0]["inputs"][2]["fields"] = doc["operations"][0]["inputs"][0]["fields"]
    assert "tool.fields_not_path" in {f["code"] for f in check(fields_on_number)["findings"]}


DESIGN_MUTATIONS = [
    (lambda fd: fd["inputs"].append({"input": "nope", "from": {"const": 1}}), "tool.design_unknown_input"),
    (lambda fd: fd["inputs"].__setitem__(0, {"input": "level", "from": {"upstream": "charge-confusion-rate"}}),
     "tool.design_no_direction"),
    (lambda fd: fd["inputs"].__setitem__(0, {"input": "level", "from": {"upstream": "charge-confusion-rate"},
                                             "direction": "order-preserving"}), "tool.design_upstream_undeclared"),
    (lambda fd: fd.update(bound=[{"bound": "optimistic", "when": [{"input": "level", "min": 0}]}]),
     "tool.design_bound_open"),
    (lambda fd: fd.update(validity=[{"denominator": "energy_GeV", "min": 0}]), "tool.design_condition_denominator"),
    (lambda fd: fd.update(inputs=[]), "schema.min_items"),
]


def case_design_block_consistency():
    """ART-40, ART-41: the checker refuses inconsistent design blocks."""
    for mutate, code in DESIGN_MUTATIONS:
        doc = fake_contract("syn-x", "momentum-resolution-core", "estimate")
        mutate(doc["operations"][0]["design"]["figures_of_merit"][0])
        assert code in {f["code"] for f in check(doc, help_check=False)["findings"]}, code


class DesignContractTests(unittest.TestCase):
    pass


attach_cases(DesignContractTests, globals())

if __name__ == "__main__":
    unittest.main()
