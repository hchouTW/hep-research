#!/usr/bin/env python3
"""cr-provider/1 entrypoint of the emulator: B/C from the hep-ml Gaussian-process emulator of USINE, inside its domain.

It reads only an ml-artifact (task surrogate, written by hep-ml's write_ml_artifact.py) and the model file the
artifact lists as its checkpoint (format gp-pca-emulator/1, written by hep-ml's train_emulator.py) and imports no
skill: the Gaussian-process prediction and the stored DomainModel are evaluated here from the model's numbers (the
adapter tests check both against hep-ml's own classes). Default artifact: the committed E2 emulator
tests/adapters/fixtures/cr_propagation/e2/emulator.ml-artifact.json; HEP_EMULATOR_ML_ARTIFACT names another one (then
the provider version is the declared version + '+model.' + the first 12 hex digits of the model's sha256, so a
registry entry or cache made for the committed model never answers for it).

Checks at start (any failure fails every request with provider-error, R4): the model file's sha256 equals the
artifact's model_hash; the artifact is a surrogate whose extrapolation_policy action is reject; the model's feature
boxes equal the declared domain; the model reproduces its stored self-check predictions within 1e-9.
Request: transport null or equal to the training transport (the model's context; else the request is refused with
out-of-domain: the emulator knows no other transport); observable B/C on axis rigidity with bins that are a contiguous
run of the training bins (edges equal within relative 1e-9; else unsupported-observable); want lis only (not
decomposable). Point: inside the declared box (protocol) and 'inside' by the DomainModel (unit-cube coordinates);
'sparse' or 'outside' is refused with out-of-domain and the DomainModel's reasons, or with
--allow-outside-validated-range evaluated and labelled outside-validated-range (r3 5.2, E2).
Values: exp of the emulated ln(B/C) per bin (the training values were USINE's ratios of bin integrals, r3 P2).
Uncertainties (P10): the emulator error as kind numerical, one fully correlated component per principal component
(scale x latent GP sigma x basis, times the value) and one uncorrelated component for the dropped components; their
quadrature sum is the emulator's variance per bin and their sum of outer products its covariance between bins.
Labels: the training data's labels from the model (synthetic, unvalidated). numerical_tolerance: the largest relative
hold-out error recorded in the artifact's regression_validation (max_relative_error), else null. Deterministic.

Usage:
  python3 emulator_provider.py --request REQUEST.json --response RESPONSE.json [--allow-outside-validated-range]
  python3 emulator_provider.py --serve [--allow-outside-validated-range]
Exit codes: 0 ok, 1 refused or every point failed, 3 some points failed, or NumPy/SciPy missing (status
missing-dependency on stdout, a failed response with provider-error written), 2 unreadable request or unwritable
response.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER = HERE.parent
PLUGIN_ROOT = ADAPTER.parents[1]
sys.dont_write_bytecode = True
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
from core.provider.entrypoint import respond, write_json_atomic  # noqa: E402
from core.provider.hashing import canonical_sha256  # noqa: E402
from core.provider.protocol import (  # noqa: E402
    OUTSIDE_LABEL,
    OUTSIDE_OPTION,
    failed_response,
    failed_result,
    response_status,
)
from core.status import exit_code  # noqa: E402

PROVIDER_ID = "emulator"
ARTIFACT_ENV = "HEP_EMULATOR_ML_ARTIFACT"
DEFAULT_ARTIFACT = PLUGIN_ROOT / "tests" / "adapters" / "fixtures" / "cr_propagation" / "e2" / "emulator.ml-artifact.json"
MODEL_FORMAT = "gp-pca-emulator/1"
EDGE_RTOL = 1e-9
SELF_CHECK_ATOL = 1e-9
SQRT5 = math.sqrt(5.0)


class ModelError(RuntimeError):
    """The artifact or model cannot be used (every request fails with provider-error)."""


class DomainRefusal(Exception):
    """A point the DomainModel puts outside the training domain (refused with out-of-domain)."""


# ---------------------------------------------------------------------------------------------- model
def _matern52(xa, xb, lengths, signal):
    import numpy as np

    diff = (xa[:, None, :] - xb[None, :, :]) / lengths
    r = np.sqrt(np.maximum((diff ** 2).sum(axis=2), 0.0))
    return signal * (1.0 + SQRT5 * r + 5.0 / 3.0 * r ** 2) * np.exp(-SQRT5 * r)


class Emulator:
    """The Gaussian-process emulator and its domain, from an ml-artifact and its model file."""

    def __init__(self, artifact_path: Path):
        import numpy as np

        self.artifact_path = Path(artifact_path)
        try:
            self.artifact = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ModelError(f"cannot read the ml-artifact {self.artifact_path.name}: {exc}") from None
        ext = self.artifact.get("extension") or {}
        if self.artifact.get("artifact_type") != "ml-artifact" or ext.get("task") != "surrogate":
            raise ModelError("the artifact is not an ml-artifact of task surrogate")
        if (ext.get("extrapolation_policy") or {}).get("action") != "reject":
            raise ModelError("the artifact's extrapolation_policy action is not reject")
        checkpoints = [o.get("ref") for o in self.artifact.get("outputs") or [] if o.get("kind") == "checkpoint"]
        if len(checkpoints) != 1:
            raise ModelError("the artifact must list exactly one checkpoint (the model file)")
        model_path = self.artifact_path.parent / checkpoints[0]
        try:
            raw = model_path.read_bytes()
        except OSError as exc:
            raise ModelError(f"cannot read the model file {checkpoints[0]}: {exc}") from None
        self.model_sha256 = hashlib.sha256(raw).hexdigest()
        if ext.get("model_hash") != "sha256:" + self.model_sha256:
            raise ModelError(f"the model file's sha256 {self.model_sha256[:12]}... is not the artifact's model_hash")
        model = json.loads(raw)
        if model.get("format") != MODEL_FORMAT:
            raise ModelError(f"the model is not {MODEL_FORMAT}")
        self.model, self.ext = model, ext
        self.features = model["features"]
        self.x = np.asarray(model["training_unit"], float)
        self.mean = np.asarray(model["output_mean"], float)
        self.basis = np.asarray(model["basis"], float)
        self.residual_var = np.asarray(model["residual_variance"], float)
        self.components = []
        for comp in model["components"]:
            lengths, signal, nugget = np.asarray(comp["lengths"], float), float(comp["signal"]), float(comp["nugget"])
            try:
                chol = np.linalg.cholesky(_matern52(self.x, self.x, lengths, signal) + nugget * np.eye(len(self.x)))
            except np.linalg.LinAlgError as exc:
                raise ModelError(f"the model's kernel matrix cannot be factorized: {exc}") from None
            self.components.append((lengths, signal, float(comp["scale"]), np.asarray(comp["alpha"], float), chol))
        self.domain = model.get("domain_model")
        if self.domain is None:
            raise ModelError("the model has no DomainModel (trained on too few points)")
        self._tree = None
        check = model.get("self_check") or {}
        mean, sigma, _ = self.predict_unit(np.asarray(check.get("unit"), float))
        if not (np.allclose(mean, check["transformed_mean"], rtol=0.0, atol=SELF_CHECK_ATOL)
                and np.allclose(sigma, check["transformed_sigma"], rtol=0.0, atol=SELF_CHECK_ATOL)):
            raise ModelError("the model does not reproduce its self-check predictions")
        context = model.get("context") or {}
        self.transport = context.get("transport")
        self.edges = [float(e) for e in model["outputs"]["edges"]]

    def unit(self, point: dict):
        import numpy as np

        row = []
        for feat in self.features:
            value, lo, hi = float(point[feat["name"]]), feat["min"], feat["max"]
            if feat["scale"] == "log":
                row.append((math.log(value) - math.log(lo)) / (math.log(hi) - math.log(lo)) if value > 0 else -math.inf)
            else:
                row.append((value - lo) / (hi - lo))
        return np.asarray(row, float)

    def predict_unit(self, u):
        """(ln mean, ln sigma, per-component ln sigma vectors) for unit-cube rows u."""
        import numpy as np
        from scipy.linalg import solve_triangular

        u = np.atleast_2d(u)
        mean = np.repeat(self.mean[None, :], len(u), axis=0)
        var = np.repeat(self.residual_var[None, :], len(u), axis=0)
        parts = []
        for c, (lengths, signal, scale, alpha, chol) in enumerate(self.components):
            ks = _matern52(u, self.x, lengths, signal)
            v = solve_triangular(chol, ks.T, lower=True)
            latent = np.maximum(signal - (v ** 2).sum(axis=0), 0.0)
            mean += np.outer(scale * (ks @ alpha), self.basis[:, c])
            var += np.outer(scale ** 2 * latent, self.basis[:, c] ** 2)
            parts.append(np.outer(scale * np.sqrt(latent), self.basis[:, c]))
        return mean, np.sqrt(var), parts

    def domain_status(self, u) -> tuple[str, list[str]]:
        """The DomainModel's status of one unit-cube row (the logic of check_surrogate_domain.DomainModel.details)."""
        import numpy as np
        from scipy.spatial import cKDTree

        dm = self.domain
        if not np.all(np.isfinite(u)):
            return "outside", ["non-finite"]
        white = dm["whitener"]
        cont = [int(j) for j in dm["continuous"]]
        xc = u[cont]
        mean = np.asarray(white["mean"], float)
        constant = np.asarray(white["constant"], bool)
        tol = np.asarray(white["constant_tol"], float)
        mismatch = bool((np.abs(xc[constant] - mean[constant]) > tol[constant]).any())
        active = ~constant
        thresholds = dm["thresholds"]
        reasons = []
        maha = knn = resid = 0.0
        if active.any():
            dim, dropped = int(white["dim"]), int(white["dropped"])
            basis = np.asarray(white["basis"], float).reshape(int(active.sum()), dim)
            xa = xc[active] - mean[active]
            z = xa @ basis
            maha = float(np.linalg.norm(z))
            if dropped:
                null = np.asarray(white["null"], float).reshape(int(active.sum()), dropped)
                resid = float(np.linalg.norm(xa @ null))
            if dim:
                if self._tree is None:
                    self._tree = cKDTree(np.asarray(dm["z_fit"], float).reshape(int(dm["n_fit"]), dim))
                dist, _ = self._tree.query(z[None, :], k=[int(dm["k"])])
                knn = float(dist[0, 0])
        out = maha > thresholds["mahalanobis"]
        if thresholds["residual"] is not None:
            out = out or resid > thresholds["residual"]
        sparse = (not out) and knn > thresholds["knn"]
        if maha > thresholds["mahalanobis"]:
            reasons.append("Mahalanobis distance above threshold (far from the training cloud)")
        if thresholds["residual"] is not None and resid > thresholds["residual"]:
            reasons.append("off a near-zero-variance direction of the training data (a constraint it obeys)")
        if mismatch:
            reasons.append("a feature constant in training has another value")
        if sparse and not mismatch:
            reasons.append("k-NN distance above threshold (in a hole or thin region of the training data)")
        if out or mismatch:
            return "outside", reasons
        return ("sparse" if sparse else "inside"), reasons


# ---------------------------------------------------------------------------------------------- provider
def artifact_path() -> Path:
    return Path(os.environ[ARTIFACT_ENV]) if os.environ.get(ARTIFACT_ENV) else DEFAULT_ARTIFACT


def declaration(emulator: Emulator | None = None) -> dict:
    adapter = json.loads((ADAPTER / "adapter.json").read_text(encoding="utf-8"))
    decls = adapter["provider"] if isinstance(adapter["provider"], list) else [adapter["provider"]]
    decl = dict(next(d for d in decls if d["id"] == PROVIDER_ID))
    decl.setdefault("version", adapter["version"])
    if os.environ.get(ARTIFACT_ENV) and emulator is not None:
        decl["version"] = f"{decl['version']}+model.{emulator.model_sha256[:12]}"
    return decl


def _bin_slice(edges: list[float], wanted: list[float]) -> slice | None:
    """The slice of training bins whose edges equal `wanted` (relative 1e-9), or None."""
    for start, edge in enumerate(edges):
        if abs(edge - wanted[0]) <= EDGE_RTOL * abs(edge):
            stop = start + len(wanted) - 1
            if stop < len(edges) and all(abs(edges[start + i] - w) <= EDGE_RTOL * abs(w) for i, w in enumerate(wanted)):
                return slice(start, stop)
            return None
    return None


def request_problem(request, emulator: Emulator):
    """(reason, detail) for a request this emulator cannot answer beyond the generic protocol checks, else None."""
    if not isinstance(request, dict) or not isinstance(request.get("observables"), list):
        return None  # malformed: the generic checks of respond() report it
    transport = request.get("transport")
    if transport is not None and canonical_sha256(transport) != canonical_sha256(emulator.transport):
        return ("out-of-domain", "the emulator was trained for one transport block (sha256 "
                f"{canonical_sha256(emulator.transport)[:12]}...); a request naming another cannot be emulated")
    for obs in request["observables"]:
        if not isinstance(obs, dict) or obs.get("id") != "B/C" or obs.get("axis") != "rigidity":
            continue  # undeclared observables and axes are refused by respond()
        bins = obs.get("bins")
        try:
            wanted = [float(bins[0][0])] + [float(b[1]) for b in bins]
        except (TypeError, IndexError, ValueError):
            return None
        if _bin_slice(emulator.edges, wanted) is None:
            return ("unsupported-observable", f"B/C bins must be a contiguous run of the training bins "
                    f"(edges {emulator.edges[0]:g} ... {emulator.edges[-1]:g} GV, {len(emulator.edges) - 1} bins)")
    return None


def prediction(emulator: Emulator, obs: dict, point: dict, values, comps, residual, status: str) -> dict:
    edges = [float(obs["bins"][0][0])] + [float(b[1]) for b in obs["bins"]]
    ctx = emulator.model.get("context") or {}
    uncertainties = [{"name": f"emulator-pc{c + 1}", "kind": "numerical", "correlation": "fully-correlated",
                      "gaussian": True, "values": [float(v) for v in part]} for c, part in enumerate(comps)]
    uncertainties.append({"name": "emulator-dropped-components", "kind": "numerical", "correlation": "uncorrelated",
                          "gaussian": True, "values": [float(v) for v in residual]})
    return {
        "observable": {
            "quantity": "ratio",
            "process": "unmodulated local interstellar B/C emulated from USINE V3.5 runs (Gaussian-process emulator "
                       f"{emulator.artifact.get('artifact_id')}): ratio of bin integrals of 10B+11B over 12C as "
                       "in the training runs",
            "species": [{"name": "boron"}, {"name": "carbon"}],
            "variables": [{"name": "rigidity", "unit": "GV", "edges": edges}],
            "phase_space": {"definition": "local interstellar flux at the observer of the training runs, before solar "
                                          "modulation", "fiducial": False},
            "level": "crsr:local-interstellar",
            "normalization": {"kind": "exposure", "value": "not-applicable",
                              "convention": "ratio of two bin-integrated fluxes; the normalization cancels"},
            "bin_semantics": "bin-averaged",
            "unit": "1",
            "conventions": {"energy_variable": "rigidity in GV: the ratio of the bin-integrated fluxes of the training "
                                               "runs (r3 P2), isotopes summed at equal rigidity (P3)",
                            "frame": "Galactic rest frame (interstellar gas at rest)"},
            "validity_range": {"variable": "rigidity", "min": edges[0], "max": edges[-1], "unit": "GV"},
        },
        "derivation_status": "numerical-evidence",
        "parameter_point": {**{k: float(v) for k, v in point.items()},
                            "emulator_model": "sha256:" + emulator.model_sha256,
                            "ml_artifact": emulator.artifact.get("artifact_id"), "domain_status": status,
                            "training_provider": f"{ctx.get('provider')} {ctx.get('provider_version')}"},
        "representation": "numerical",
        "values": {"edges": edges, "values": [float(v) for v in values], "unit": "1"},
        "uncertainties": uncertainties,
        "allowed_transformations": ["solar modulation per isotope is not possible: the emulator gives element ratios "
                                    "only", "sub-range of the training bins"],
    }


def emulator_respond(request, decl: dict, emulator: Emulator, allow_outside: bool) -> dict:
    """respond() of core/provider with the emulator's request checks first and the DomainModel per point."""
    problem = request_problem(request, emulator)
    if problem:
        return failed_response(request, *problem)
    refused: dict[int, str] = {}

    def evaluate_point(req, point, context):
        u = emulator.unit(point)
        status, reasons = emulator.domain_status(u)
        outside = context["outside"]
        if status != "inside":
            if not allow_outside:
                refused[id(point)] = f"DomainModel status {status}: {'; '.join(reasons)}"
                raise DomainRefusal(refused[id(point)])
            outside = True
        mean, _, parts = emulator.predict_unit(u)
        values = [math.exp(v) for v in mean[0]]
        preds = []
        for obs in req["observables"]:
            wanted = [float(obs["bins"][0][0])] + [float(b[1]) for b in obs["bins"]]
            sl = _bin_slice(emulator.edges, wanted)
            vals = values[sl]
            comps = [[p[0][i] * values[i] for i in range(sl.start, sl.stop)] for p in parts]
            residual = [math.sqrt(emulator.residual_var[i]) * values[i] for i in range(sl.start, sl.stop)]
            preds.append(prediction(emulator, obs, point, vals, comps, residual, status))
        labels = list((emulator.model.get("training") or {}).get("status") or [])
        if outside:
            labels.append(OUTSIDE_LABEL)
        tol = (emulator.ext.get("regression_validation") or {}).get("max_relative_error")
        return {"predictions": preds, "labels": labels, "computational_run_ref": None,
                "numerical_tolerance": float(tol) if isinstance(tol, (int, float)) else None}

    response = respond(request, decl, evaluate_point, allow_outside)
    if refused and response.get("results"):
        for k in range(len(response["results"])):
            point = request["points"][k]
            if id(point) in refused:
                response["results"][k] = failed_result(k, point, "out-of-domain", refused[id(point)])
        response["status"] = response_status(response["results"])
    return response


def load_emulator():
    """(emulator, None) or (None, reason) for the configured artifact."""
    try:
        return Emulator(artifact_path()), None
    except (ModelError, KeyError, TypeError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def answer(request, allow_outside: bool, emulator, problem) -> dict:
    if emulator is None:
        return failed_response(request, "provider-error", f"the emulator cannot be loaded ({problem})")
    decl = declaration(emulator)
    box = {f["name"]: {"min": f["min"], "max": f["max"]} for f in emulator.features}
    if box != decl["domain"]:
        return failed_response(request, "provider-error", "the model's feature boxes differ from the declared domain")
    return emulator_respond(request, decl, emulator, allow_outside)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--request", type=Path, help="request file (with --response)")
    parser.add_argument("--response", type=Path, help="response file to write (with --request)")
    parser.add_argument("--serve", action="store_true", help="JSON Lines session on stdin/stdout")
    parser.add_argument(OUTSIDE_OPTION, action="store_true", dest="allow_outside",
                        help=f"evaluate points outside the domain; their results are labelled {OUTSIDE_LABEL}")
    args = parser.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy.linalg  # noqa: F401
        import scipy.spatial  # noqa: F401
    except ImportError as exc:  # the hep-computing script contract: exit 3, status missing-dependency
        missing = f"NumPy and SciPy are needed: {exc}"
        if args.response and not args.serve:
            try:
                write_json_atomic(args.response, failed_response(None, "provider-error", missing))
            except OSError:
                pass
        print(json.dumps({"status": "missing-dependency", "error": missing}))
        return 3
    emulator, problem = load_emulator()
    if args.serve:
        if args.request or args.response:
            parser.error("--serve takes no --request or --response")
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
            except ValueError as exc:
                response = failed_response(None, "invalid-request", f"not JSON: {exc}")
            else:
                response = answer(request, args.allow_outside, emulator, problem)
            sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
            sys.stdout.flush()
        return 0
    if not (args.request and args.response):
        parser.error("give --request and --response, or --serve")
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        response, code = failed_response(None, "invalid-request", f"cannot read the request: {exc}"), 2
    else:
        response = answer(request, args.allow_outside, emulator, problem)
        code = exit_code(response["status"])
    try:
        write_json_atomic(args.response, response)
    except OSError as exc:
        print(json.dumps({"status": "rejected", "error": f"cannot write the response: {exc}"}))
        return 2
    print(json.dumps({"status": response["status"], "response": str(args.response)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
