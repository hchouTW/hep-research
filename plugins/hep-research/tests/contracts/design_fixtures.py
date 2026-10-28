#!/usr/bin/env python3
"""SYNTHETIC design-project fixtures for contracts/design.py (detector system design spec M0): a generic space
spectrometer with three candidates (a short lever arm with many layers, a long lever arm with few layers, and a probe
with a deliberately too-short lever arm), F1 evaluations of the momentum-resolution core and the Gaussian-core
charge-confusion rate at 1000 GV produced by running the real tools (tracker_resolution.py momentum and
charge_confusion_rate.py gaussian-core), their computational-runs and output files. All parameter values are proposals
chosen for the fixture, not any experiment's numbers.

The Builder is also the test helper: tests copy or rebuild a project and add or mutate artifacts with it, so every
hash and binding stays consistent unless a test breaks one on purpose.

Usage: python3 tests/contracts/design_fixtures.py   (rewrites contracts/fixtures/design/spectrometer/)
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "contracts" / "fixtures" / "design" / "spectrometer"
SYN = "SYNTHETIC design fixture; parameter values are proposals, not an experiment's numbers"
NS = "spectrometer-demo"
PROTON_MASS = 0.93827208816
TRACKER = "skills/hep-detector/scripts/tracker_resolution.py"
CONFUSION = "skills/hep-detector/scripts/charge_confusion_rate.py"
CREATED = "2026-10-24"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def param(value, unit, source="fixture proposal", status="proposal"):
    return {"value": value, "unit": unit, "source": source, "status": status}


def calib(method="track-based alignment with cosmic and beam-like control samples"):
    return {"method": method, "control_samples": ["synthetic control sample"]}


def budget_row(estimate, uncertainty, unit, basis="estimate", source="fixture engineering estimate"):
    return {"allocation": estimate * 1.2, "estimate": estimate, "uncertainty": uncertainty, "unit": unit,
            "basis": basis, "source": source, "fidelity": "F1"}


def tracker_subsystem(n_layers: int, lever_arm_m: float, point_um: float = 10.0, layer_x0: float = 0.01,
                      passive_x0: float = 0.03) -> dict:
    pos = [round(i * lever_arm_m / (n_layers - 1), 6) for i in range(n_layers)]
    return {"role": "tracking", "technology": "silicon microstrip",
            "parameters": {"layer_positions_m": param(pos, "m"), "point_resolution_um": param(point_um, "um"),
                           "layer_x_over_x0": param([layer_x0] * n_layers, "1"),
                           "passive_x_over_x0": param(passive_x0, "1")},
            "interfaces": ["DES-MAG-001"], "calibration": calib()}


def magnet_subsystem(field_t: float = 0.5) -> dict:
    return {"role": "bending", "technology": "permanent magnet",
            "parameters": {"field_T": param(field_t, "T")}, "interfaces": ["DES-TRK-001"],
            "calibration": calib("field map from Hall-probe survey")}


def budgets(trk_mass: float, n_layers: int) -> dict:
    return {"mass": {"DES-TRK-001": budget_row(trk_mass, 0.2 * trk_mass, "kg"),
                     "DES-MAG-001": budget_row(2000.0, 400.0, "kg")},
            "power": {"DES-TRK-001": budget_row(25.0 * n_layers, 5.0 * n_layers, "W"),
                      "DES-MAG-001": budget_row(0.0, 0.0, "W")},
            "channel_count": {"DES-TRK-001": budget_row(20000.0 * n_layers, 4000.0 * n_layers, "1"),
                              "DES-MAG-001": budget_row(0.0, 0.0, "1")},
            "data_rate": {"DES-TRK-001": budget_row(0.5 * n_layers, 0.1 * n_layers, "Mbit/s"),
                          "DES-MAG-001": budget_row(0.0, 0.0, "Mbit/s")}}


def den(value, tol=0.0):
    return {"value": value, "tolerance": tol}


def spec_ext(version: int = 1, resolution_target: float = 0.6, confusion_target: float = 0.05) -> dict:
    return {
        "design_id": NS, "spec_version": version,
        "objectives": [{"id": f"{NS}:PHY-001", "description": "SYNTHETIC: charge-separated proton spectrum to 1 TV",
                        "observable": "proton and antiproton flux versus rigidity", "range": "10 GV to 1000 GV",
                        "precision_goal": "statistics-limited at 1000 GV"}],
        "requirements": [
            {"id": f"{NS}:REQ-TRK-001", "parents": [f"{NS}:PHY-001"], "quantity": "momentum-resolution-core",
             "comparator": "<=", "target": resolution_target, "unit": "1",
             "denominator": {"rigidity_GV": den(1000.0), "species": den("proton")}, "kind": "driving",
             "allocation": f"{NS}:ALC-TRK-001", "verification": {"method": "analysis then simulation"}},
            {"id": f"{NS}:REQ-CC-001", "parents": [f"{NS}:PHY-001", f"{NS}:REQ-TRK-001"],
             "quantity": "charge-confusion-rate", "comparator": "<=", "target": confusion_target, "unit": "1",
             "denominator": {"rigidity_GV": den(1000.0), "species": den("proton"), "charge_sign": den("positive"),
                             "curvature_offset_per_GV": den(0.0)}, "kind": "driving",
             "allocation": f"{NS}:ALC-CC-001", "verification": {"method": "simulation validated with data"}}],
        "allocations": [
            {"id": f"{NS}:ALC-TRK-001", "requirement": f"{NS}:REQ-TRK-001", "rule": "quadrature", "independent": True,
             "items": [{"name": "intrinsic", "value": 0.4}, {"name": "scattering", "value": 0.05},
                       {"name": "alignment", "value": 0.25}], "margin": 0.1},
            {"id": f"{NS}:ALC-CC-001", "requirement": f"{NS}:REQ-CC-001", "rule": "linear",
             "items": [{"name": "core", "value": 0.01}, {"name": "tails", "value": 0.03}], "margin": 0.01}],
        "constraints": [{"id": f"{NS}:CON-MASS-001", "type": "mass", "hardness": "hard", "quantity": "mass-budget",
                         "comparator": "<=", "target": 7500.0, "unit": "kg", "denominator": {},
                         "subsystems": ["DES-TRK-001", "DES-MAG-001"]}],
        "comparison_basis": {"quantity": "mass-budget", "tolerance_relative": 0.05,
                             "note": "candidates are compared at equal mass"}}


class Builder:
    """Writes a design project: <root>/artifacts (the artifacts_dir) and <root>/decisions (decision records)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.art = self.root / "artifacts"
        self.dec = self.root / "decisions"
        self.art.mkdir(parents=True, exist_ok=True)
        self.dec.mkdir(parents=True, exist_ok=True)

    # -- files
    def path(self, rel: str) -> Path:
        return self.art / rel

    def write(self, rel: str, doc) -> str:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        return rel

    def read(self, rel: str) -> dict:
        return json.loads(self.path(rel).read_text(encoding="utf-8"))

    def inp(self, rel: str) -> dict:
        doc = self.read(rel)
        out = {"ref": rel, "sha256": sha256(self.path(rel)), "artifact_type": doc["artifact_type"],
               "artifact_id": doc["artifact_id"]}
        sticky = [s for s in doc.get("status", []) if s in ("failed", "unvalidated", "preliminary", "synthetic",
                                                            "asimov", "user-supplied")]
        if sticky:
            out["status"] = sticky
        return out

    def rebind(self, rel: str) -> None:
        """Refresh the sha256 of every input of rel (after a deliberate upstream change, to make it current)."""
        doc = self.read(rel)
        doc["inputs"] = [self.inp(i["ref"]) if self.path(i["ref"]).is_file() else i for i in doc.get("inputs", [])]
        self.write(rel, doc)

    @staticmethod
    def envelope(atype, aid, ext, producer="hep-detector", inputs=(), outputs=(), status=("synthetic",)) -> dict:
        sticky = {s for i in inputs for s in i.get("status", [])}  # a consumer carries its inputs' sticky statuses
        status = list(dict.fromkeys(list(status) + sorted(sticky - set(status))))
        return {"contract_version": "3.14.0", "artifact_id": aid, "artifact_type": atype, "objective": SYN,
                "versions": {"plugin": "0.36.0", "contracts": "3.14.0",
                             "plugin_release": {"release": "unreleased", "digest": "unknown"}},
                "provenance": {"producer_skill": producer, "created": CREATED},
                "inputs": list(inputs), "outputs": list(outputs), "status": list(status), "unresolved_inputs": [],
                "extension": ext}

    # -- artifacts
    def spec(self, version: int = 1, rel: str | None = None, created: str = CREATED, **kw) -> str:
        doc = self.envelope("design-spec", f"{NS}-spec-v{version}", spec_ext(version, **kw))
        doc["provenance"]["created"] = created
        return self.write(rel or f"design-spec.v{version}.json", doc)

    def candidate(self, name: str, subsystems: dict | None = None, budget: dict | None = None,
                  derived_from: str | None = None, overrides: dict | None = None, description: str = "",
                  status=("synthetic",)) -> str:
        ext = {"candidate_id": f"{NS}:{name}", "design_id": NS, "description": description}
        inputs = []
        if subsystems is not None:
            ext["subsystems"] = subsystems
        if budget is not None:
            ext["budgets"] = budget
        if derived_from:
            ext["derived_from"] = f"{NS}:{derived_from}"
            ext["overrides"] = overrides or {}
            # a variant binds its base by the parameters it inherits (TRC-06): a base change is judged per evaluation
            inputs.append(dict(self.inp(f"candidates/{derived_from}.json"), binding="parameters"))
        return self.write(f"candidates/{name}.json", self.envelope("design-candidate", f"{NS}-{name}", ext,
                                                                   inputs=inputs, status=status))

    def chain_files(self, name: str) -> list[str]:
        out, cid = [], f"{NS}:{name}"
        while cid:
            rel = f"candidates/{cid.split(':', 1)[1]}.json"
            out.append(rel)
            cid = self.read(rel)["extension"].get("derived_from")
        return out

    def effective(self, name: str) -> dict:
        subs: dict = {}
        for rel in reversed(self.chain_files(name)):
            ext = self.read(rel)["extension"]
            for key in ("subsystems", "overrides"):
                for sid, s in (ext.get(key) or {}).items():
                    cur = subs.setdefault(sid, {})
                    for k, v in s.items():
                        if k == "parameters":
                            cur.setdefault("parameters", {}).update(copy.deepcopy(v))
                        else:
                            cur[k] = copy.deepcopy(v)
        return subs

    def run(self, run_id: str, script: str, args: list[str], inputs: list[str]) -> tuple[str, dict]:
        """Run a plugin tool for real; write its output file and computational-run (argv, script_sha256)."""
        argv = ["python3", script, *args]
        proc = subprocess.run([sys.executable, "-I", "-B", str(ROOT / script), *args], capture_output=True, text=True,
                              cwd=str(ROOT), timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"{script} {args} exited {proc.returncode}: {proc.stdout} {proc.stderr}")
        output = json.loads(proc.stdout)
        out_rel = self.write(f"outputs/{run_id}.json", output)
        ext = {"input_manifest": [{"path": r, "sha256": sha256(self.path(r))} for r in inputs],
               "tools": [{"name": Path(script).stem, "version": "plugin"}], "commands": [" ".join(argv)],
               "environment": {"python": "3"}, "seeds": {}, "tolerances": {}, "exit_status": 0,
               "output_hashes": {out_rel: sha256(self.path(out_rel))}, "argv": argv,
               "script_sha256": {script: sha256(ROOT / script)}}
        rel = self.write(f"runs/{run_id}.computational-run.json",
                         self.envelope("computational-run", f"{NS}-{run_id}", ext, producer="hep-detector",
                                       inputs=[self.inp(r) for r in inputs], outputs=[{"ref": out_rel}]))
        return rel, output

    def fake_run(self, run_id: str, entry: str, op_args: list[str], options: dict, output: dict,
                 inputs: list[str]) -> str:
        """A computational-run of a synthetic test tool: argv from options {flag: value(s)}, output written as given."""
        args = list(op_args)
        for flag, val in options.items():
            args.append(flag)
            args += [repr(v) if isinstance(v, float) else str(v) for v in (val if isinstance(val, list) else [val])]
        argv = ["python3", entry, *args]
        out_rel = self.write(f"outputs/{run_id}.json", output)
        ext = {"input_manifest": [{"path": r, "sha256": sha256(self.path(r))} for r in inputs],
               "tools": [{"name": Path(entry).stem, "version": "test"}], "commands": [" ".join(argv)],
               "environment": {"python": "3"}, "seeds": {}, "tolerances": {}, "exit_status": 0,
               "output_hashes": {out_rel: sha256(self.path(out_rel))}, "argv": argv,
               "script_sha256": {entry: "0" * 64}}
        return self.write(f"runs/{run_id}.computational-run.json",
                          self.envelope("computational-run", f"{NS}-{run_id}", ext, inputs=[self.inp(r) for r in inputs],
                                        outputs=[{"ref": out_rel}]))

    def evaluation(self, eid: str, cand: str, fom: str, denominator: dict, value, bound: str, fidelity: str = "F1",
                   unit: str = "1", run_rel: str | None = None, parameter_refs=None, upstream: list[str] = (),
                   extra_inputs: list[str] = (), **ext_extra) -> str:
        ext = {"evaluation_id": f"{NS}:{eid}", "candidate": f"{NS}:{cand}", "figure_of_merit": fom,
               "denominator": denominator, "bound": bound, "fidelity": fidelity}
        if value is not None:
            ext["value"], ext["unit"] = value, unit
        if run_rel:
            ext["run_ref"] = run_rel
        if parameter_refs is not None:
            ext["parameter_refs"] = sorted(parameter_refs)
        ext.update(ext_extra)
        refs = self.chain_files(cand) + ([run_rel] if run_rel else []) + list(upstream) + list(extra_inputs)
        return self.write(f"evaluations/{eid}.json",
                          self.envelope("design-evaluation", f"{NS}-{eid}", ext, inputs=[self.inp(r) for r in refs]))

    # -- the two F1 tools, mapped as their contracts declare
    def eval_resolution(self, eid: str, cand: str, rigidity: float = 1000.0) -> str:
        subs = self.effective(cand)
        trk, mag = subs["DES-TRK-001"]["parameters"], subs["DES-MAG-001"]["parameters"]
        x0 = sum(trk["layer_x_over_x0"]["value"]) + trk["passive_x_over_x0"]["value"]
        args = ["momentum", "--positions-m", *map(repr, trk["layer_positions_m"]["value"]),
                "--point-resolution-um", repr(trk["point_resolution_um"]["value"]),
                "--field-tesla", repr(mag["field_T"]["value"]), "--x-over-x0", repr(x0), "--charge", "1",
                "--mass-gev", repr(PROTON_MASS), "--pt", repr(rigidity), "--status", "synthetic"]
        run_rel, out = self.run(f"{eid}", TRACKER, args, self.chain_files(cand))
        p = out["points"][0]
        bound = "optimistic" if p["intrinsic_relative"] >= p["scattering_relative"] else "estimate"
        refs = ["DES-TRK-001.parameters.layer_positions_m", "DES-TRK-001.parameters.point_resolution_um",
                "DES-TRK-001.parameters.layer_x_over_x0", "DES-TRK-001.parameters.passive_x_over_x0",
                "DES-MAG-001.parameters.field_T"]
        extra = {} if bound == "optimistic" else {"uncertainty": {"minus": 0.5 * p["total_relative"],
                                                                  "plus": 0.5 * p["total_relative"], "coverage": 0.6827,
                                                                  "interval": "central", "distribution": "gaussian"}}
        return self.evaluation(eid, cand, "momentum-resolution-core", {"rigidity_GV": rigidity, "species": "proton"},
                               p["total_relative"], bound, run_rel=run_rel, parameter_refs=refs,
                               validity={"assumptions": ["uniform field", "lambda = 0", "Gaussian point errors",
                                                         "no misalignment"], "in_domain": True}, **extra)

    def eval_confusion(self, eid: str, cand: str, upstream_rel: str, rigidity: float = 1000.0,
                       offset: float = 0.0) -> str:
        up = self.read(upstream_rel)["extension"]
        sigma = up["value"] / rigidity
        args = ["gaussian-core", "--edges", repr(rigidity), repr(rigidity * 2), "--sigma-inv-r", repr(sigma),
                "--status", "synthetic"]
        run_rel, out = self.run(f"{eid}", CONFUSION, args, self.chain_files(cand) + [upstream_rel])
        return self.evaluation(eid, cand, "charge-confusion-rate",
                               {"rigidity_GV": rigidity, "species": "proton", "charge_sign": "positive",
                                "curvature_offset_per_GV": offset},
                               out["bins"][0]["lower_bound_at_low_edge"], "optimistic", run_rel=run_rel,
                               parameter_refs=[], upstream=[upstream_rel])


def build(root: Path) -> Builder:
    """The M0 acceptance project: spec v1, three candidates, F1 resolution and charge confusion for each."""
    if root.exists():
        shutil.rmtree(root)
    b = Builder(root)
    b.spec(1)
    b.candidate("cand-A", {"DES-TRK-001": tracker_subsystem(9, 1.0), "DES-MAG-001": magnet_subsystem()},
                budgets(400.0, 9), description="short lever arm, many layers")
    b.candidate("cand-B", {"DES-TRK-001": tracker_subsystem(5, 3.0), "DES-MAG-001": magnet_subsystem()},
                budgets(380.0, 5), description="long lever arm, few layers")
    b.candidate("cand-P", {"DES-TRK-001": tracker_subsystem(5, 0.3), "DES-MAG-001": magnet_subsystem()},
                budgets(150.0, 5), description="probe: deliberately too-short lever arm")
    for c in ("A", "B", "P"):
        r = b.eval_resolution(f"CALC-TRK-{c}", f"cand-{c}")
        b.eval_confusion(f"CALC-CC-{c}", f"cand-{c}", r)
    return b


def main() -> None:
    build(OUT)
    (OUT / "README.md").write_text(
        "# SYNTHETIC design fixture (detector system design M0)\n\n"
        "Generated by `tests/contracts/design_fixtures.py`; do not edit by hand. `artifacts/` is the artifacts_dir\n"
        "(spec, three candidates, F1 evaluations, runs and tool outputs); `decisions/` holds decision records\n"
        "(none in M0). Parameter values are proposals chosen for the fixture, not an experiment's numbers.\n",
        encoding="utf-8")
    (OUT / "decisions" / "README.md").write_text(
        "# Decision records (none in M0)\n\nDesign decision records live outside the artifacts_dir (REP-05, DEC-19); "
        "`contracts/design.py --decisions` reads this folder.\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()


def fake_contract(tool: str, fom: str, bound, fidelity: str = "F1", denominator: dict | None = None,
                  inputs: list | None = None, required: list | None = None, better: str = "smaller", unit: str = "1",
                  validity: list | None = None) -> dict:
    """A synthetic 1.1.0 tool contract for tests: operation 'run', one '--<input>' option per mapped input (inputs:
    [(name, expr, direction or None)]), the value at 'value' of the output. Its entry is never executed."""
    inputs = inputs or [("level", {"const": 1.0}, None)]
    denominator = denominator if denominator is not None else {"rigidity_GV": "number", "species": "string"}
    maps = []
    for name, expr, direction in inputs:
        m = {"input": name, "from": expr}
        if direction:
            m["direction"] = direction
        maps.append(m)
    return {"contract_version": "1.1.0", "tool_id": tool, "entry": f"fake/{tool.replace('-', '_')}.py",
            "operations": [{"operation_id": "run", "summary": "synthetic test tool",
                            "invocation": {"kind": "cli", "output": "json-stdout",
                                           "options": [{"flag": "--" + n.replace("_", "-"), "input": n} for n, _, _ in inputs]},
                            "inputs": [{"name": n, "kind": "parameter", "unit": "n/a", "required": True,
                                        "constraint": "synthetic"} for n, _, _ in inputs],
                            "outputs": [{"name": "value", "kind": "parameter", "unit": unit}],
                            "failure_states": [{"exit_code": 2, "status": "invalid-input", "meaning": "synthetic"}],
                            "required_capabilities": [], "purposes": ["exploration"],
                            "side_effects": {"writes_files": False, "network": False, "subprocess": False},
                            "design": {"fidelity": fidelity, "figures_of_merit": [{
                                "id": fom, "better": better, "unit": unit, "bound": bound, "denominator": denominator,
                                "value": {"path": "value"}, "operation_args": ["run"], "inputs": maps,
                                "validity": validity or [], "required_upstreams": required or []}]}}]}


# ---------------------------------------------------------------- test helpers


def copy_fixture(dst: Path) -> Builder:
    """A writable copy of the committed M0 project."""
    shutil.copytree(OUT, dst)
    return Builder(dst)


def derive(b: Builder, contracts: list | None = None) -> dict:
    from contracts.design import CONTRACT_DIR, derive as _derive
    dirs = [CONTRACT_DIR] + [Path(c) for c in contracts] if contracts else None
    return _derive(b.art, b.dec, dirs)


def matrix(d: dict, req: str, cand: str) -> dict:
    """The compliance-matrix row of requirement (or constraint) id suffix req for candidate name cand."""
    for item in d["requirements"] + d["constraints"]:
        if item["id"].endswith(":" + req):
            for m in item["matrix"]:
                if f"{NS}:{cand}" in m["candidates"]:
                    return m
    raise KeyError((req, cand))


def entry(d: dict, req: str, cand: str, eid: str) -> dict:
    """The used or skipped record of evaluation eid in that matrix row."""
    m = matrix(d, req, cand)
    for r in m["used"] + m["skipped"]:
        if r["evaluation"].endswith(":" + eid):
            return r
    raise KeyError(eid)


def error_codes(d: dict, rel_part: str = "") -> set:
    return {e["code"] for e in d.get("errors", []) if rel_part in e["path"]}


def write_contracts(folder: Path, *contracts: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for c in contracts:
        (folder / f"{c['tool_id']}.json").write_text(json.dumps(c, indent=1) + "\n", encoding="utf-8")
    return folder


def fake_eval(b: Builder, eid: str, cand: str, contract: dict, value: float, options: dict | None = None,
              denominator: dict | None = None, upstream: list[str] = (), bound: str | None = None,
              fidelity: str | None = None, fom: str | None = None, **ext) -> str:
    """An evaluation produced by a synthetic contract's tool (fake_contract)."""
    fd = contract["operations"][0]["design"]["figures_of_merit"][0]
    options = options if options is not None else {"--level": 1.0}
    run_rel = b.fake_run(eid, contract["entry"], ["run"], options, {"value": value},
                         b.chain_files(cand) + list(upstream))
    den = denominator if denominator is not None else {"rigidity_GV": 1000.0, "species": "proton"}
    return b.evaluation(eid, cand, fom or fd["id"], den, value,
                        bound or (fd["bound"] if isinstance(fd["bound"], str) else "estimate"),
                        fidelity=fidelity or contract["operations"][0]["design"]["fidelity"], unit=fd["unit"],
                        run_rel=run_rel, parameter_refs=[], upstream=upstream, **ext)


def gauss(sigma: float, coverage: float = 0.6827, interval: str = "central", distribution: str = "gaussian") -> dict:
    return {"minus": sigma, "plus": sigma, "coverage": coverage, "interval": interval, "distribution": distribution}


def edit(b: Builder, rel: str, fn) -> None:
    """Apply fn to the JSON document at rel and write it back (hashes of consumers are NOT refreshed)."""
    doc = b.read(rel)
    fn(doc)
    b.write(rel, doc)


def decision(b: Builder, name: str, category: str, artifacts: list[str], actor: str = "human", **extra) -> Path:
    rec = {"record_version": "1.1.0", "decision_id": name, "analysis": NS, "decision": f"synthetic {category}",
           "category": category, "actor": {"kind": actor, "id": "fixture-reviewer"}, "time": "2026-10-24T12:00:00Z",
           "seen": {"state": "not-applicable"},
           "artifacts": [{"ref": r, "sha256": sha256(b.path(r))} for r in artifacts]}
    rec.update(extra)
    p = b.dec / f"{name}.json"
    p.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    return p


def attach_cases(cls, namespace: dict):
    """Make each module-level case_<name>(b?, tmp_path?) a unittest method test_<name> of cls: tmp_path is a fresh
    temporary folder and b a writable copy of the committed project in it (the repository runs tests with unittest)."""
    import inspect
    import tempfile

    def make(fn, params):
        def method(self):
            with tempfile.TemporaryDirectory() as tmp:
                kw = {}
                if "tmp_path" in params:
                    kw["tmp_path"] = Path(tmp)
                if "b" in params:
                    kw["b"] = copy_fixture(Path(tmp) / "p")
                fn(**kw)
        method.__doc__ = fn.__doc__
        return method
    for name, fn in list(namespace.items()):
        if name.startswith("case_") and callable(fn):
            setattr(cls, "test_" + name[len("case_"):], make(fn, inspect.signature(fn).parameters))
    return cls
