#!/usr/bin/env python3
"""Export a trained xgboost BDT (a train_bdt.py fold model) for deployment: JSON or UBJSON through save_model, ONNX, or
a ROOT file for TMVA RBDT inference (ML3 extensions).

Formats:
  json, ubj  xgboost's own formats (Booster.load_model then save_model); no pickle is read or written.
  onnx       onnxmltools.convert_xgboost (optional: onnxmltools and onnx, which the plugin does not install); needs
             --n-features for the input shape.
  tmva       ROOT.TMVA.Experimental.SaveXGBoost (optional: PyROOT with TMVA and xgboost in the same interpreter; ROOT
             6.x writes a file that TMVA's RBDT reads); needs --n-features. The model is re-read as an XGBClassifier.
A missing optional package gives status missing-dependency (exit 3) with the install command; nothing is written.
The output records the sha256 of the written file, to pass on as model_hash.
Usage: export_bdt.py MODEL.json|MODEL.ubj --to json|ubj|onnx|tmva --out PATH [--n-features N] [--key-name NAME]
       [--status LABEL]
Output JSON: status (ok, rejected, missing-dependency), status_label, inputs, defaults_used, out, sha256, format.
Exit codes: 0 written; 2 bad input (unreadable model, missing --n-features); 3 a missing optional package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

INSTALL = {"xgboost": "pip install 'xgboost>=3.4,<4'  (optional extra `bdt`)",
           "onnx": "pip install onnxmltools onnx  (not part of the plugin's extras; check their licenses first)",
           "tmva": "ROOT with TMVA, in an interpreter that also has xgboost (conda-forge root, LCG or "
                   "`pip install root`; see skills/hep-computing/references/root-usage-patterns.md)"}


class Stop(Exception):
    def __init__(self, status, **fields):
        super().__init__(status)
        self.status, self.fields = status, fields


def _need(name):
    try:
        return __import__(name)
    except ImportError as exc:
        raise Stop("missing-dependency", error=f"{name} is not installed ({exc})",
                   install=INSTALL["tmva" if name == "ROOT" else ("onnx" if name.startswith("onnx") else name)]) from exc


def export(args) -> dict:
    src = Path(args.model)
    if not src.is_file():
        raise Stop("rejected", error=f"{src} not found")
    if args.to in ("onnx", "tmva") and not args.n_features:
        raise Stop("rejected", error=f"--to {args.to} needs --n-features (the model's input dimension)")
    if args.to == "onnx":
        onnxmltools = _need("onnxmltools")
        _need("onnx")
    if args.to == "tmva":
        ROOT = _need("ROOT")
    xgb = _need("xgboost")
    booster = xgb.Booster()
    try:
        booster.load_model(str(src))
    except Exception as exc:  # xgboost raises XGBoostError for an unreadable file
        raise Stop("rejected", error=f"{src} is not an xgboost model: {exc}") from exc
    out = Path(args.out)
    if args.to in ("json", "ubj"):
        if out.suffix.lstrip(".") != args.to:
            raise Stop("rejected", error=f"--out must end in .{args.to} (xgboost picks the format from the suffix)")
        booster.save_model(str(out))
    elif args.to == "onnx":
        from onnxmltools.convert.common.data_types import FloatTensorType
        model = onnxmltools.convert_xgboost(booster, initial_types=[("input", FloatTensorType([None, args.n_features]))])
        out.write_bytes(model.SerializeToString())
    else:
        clf = xgb.XGBClassifier()
        clf.load_model(str(src))
        ROOT.TMVA.Experimental.SaveXGBoost(clf, args.key_name, str(out), num_inputs=args.n_features)
    return {"out": str(out), "format": args.to, "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "source": {"path": str(src), "sha256": hashlib.sha256(src.read_bytes()).hexdigest()},
            "xgboost": xgb.__version__}


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model", help="an xgboost model saved with save_model (.json or .ubj)")
    ap.add_argument("--to", required=True, choices=("json", "ubj", "onnx", "tmva"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-features", type=int)
    ap.add_argument("--key-name", default="bdt", help="object name in the ROOT file (tmva; default bdt)")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    head = {"status_label": args.status, "inputs": {k: v for k, v in vars(args).items() if k != "status"},
            "defaults_used": [k for k in ("key_name", "status") if f"--{k.replace('_', '-')}" not in given]}
    try:
        out = export(args)
    except Stop as stop:
        print(json.dumps({"status": stop.status, **head, **stop.fields}, indent=1))
        return exit_code(stop.status)
    except OSError as exc:
        print(json.dumps({"status": "rejected", **head, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", **head, **out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
