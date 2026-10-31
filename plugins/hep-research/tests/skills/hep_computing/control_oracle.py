"""The reconstruction v12.1 reference model as an oracle for the control-layer helper (stage C1; Delivery §5.1).

The model is development material at the repository root (evals/reconstruction-v12/spec/
v12-en-reference-model.py, outside the plugin package on purpose: evals/ does not ship). The environment variable
HEP_RESEARCH_V12_MODEL may name another copy. Locating it:
- found: the model is loaded and its scenarios, helpers and mutations are rebound to the implementation;
- not found, but this is a development checkout (the repository's evals/reconstruction-v12 folder exists): the
  tests FAIL, because the oracle is missing where it must be;
- not found and not a development checkout (an installed plugin, which ships without evals/): the tests are SKIPPED
  with the reason MODEL_MISSING, which unittest prints; they never pass silently.

Rebinding: every function defined in the model (scenarios t01..t91, the scenario helpers new_log, run, check,
recontract, ..., and the mutation factories) is re-created with a namespace in which each engine name the model
defines is replaced by the implementation's object of the same name (control_layer_support.derivation). Model data
built from model classes (the ALIGN and CAL families) is converted to the implementation's classes. A scenario run in
that namespace therefore exercises only the implementation; the model contributes only the scenario code.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import os
import sys
import types
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REPO = PLUGIN.parents[1]
DEV_FOLDER = REPO / "evals" / "reconstruction-v12"
MODEL_PATH = Path(os.environ.get("HEP_RESEARCH_V12_MODEL") or DEV_FOLDER / "spec" / "v12-en-reference-model.py")
SCRIPTS = PLUGIN / "skills" / "hep-computing" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from control_layer_support import derivation as impl  # noqa: E402

MODEL_FOUND = MODEL_PATH.is_file()
DEV_CHECKOUT = DEV_FOLDER.is_dir()
MODEL_MISSING = (f"reconstruction v12.1 reference model not found at {MODEL_PATH} and this is not a development "
                 f"checkout: the scenario, mutation and differential tests of the control layer did NOT run")
ENGINE_CLASSES = ("StepSpec", "Deliverable", "Family")


def require_model(case):
    """Fail (development checkout) or skip with MODEL_MISSING (installed plugin) when the model is absent."""
    if MODEL_FOUND:
        return
    if DEV_CHECKOUT:
        case.fail(f"the reference model is missing from the development checkout: {MODEL_PATH}")
    case.skipTest(MODEL_MISSING)


_LOADED: dict = {}


def load_model():
    if "model" not in _LOADED:
        spec = importlib.util.spec_from_file_location("reconstruction_v12_reference_model", MODEL_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _LOADED["model"] = module
    return _LOADED["model"]


def to_impl(value, model):
    """Convert model engine objects (StepSpec, Deliverable, Family) inside plain containers to the implementation's."""
    for name in ENGINE_CLASSES:
        if isinstance(value, getattr(model, name)):
            return getattr(impl, name)(**{f.name: to_impl(getattr(value, f.name), model)
                                          for f in dataclasses.fields(value)})
    if isinstance(value, dict):
        return {k: to_impl(v, model) for k, v in value.items()}
    return value


def rebound_namespace():
    """The model's globals with every engine name replaced by the implementation's, and every model function rebound
    to this namespace (so the scenarios, helpers and mutation factories call the implementation)."""
    if "namespace" in _LOADED:
        return _LOADED["namespace"]
    model = load_model()
    namespace: dict = {}
    for name, value in vars(model).items():
        if hasattr(impl, name) and not name.startswith("__"):
            namespace[name] = getattr(impl, name)
        elif isinstance(value, types.FunctionType) and value.__module__ == model.__name__:
            namespace[name] = types.FunctionType(value.__code__, namespace, value.__name__, value.__defaults__,
                                                 value.__closure__)
        else:
            namespace[name] = to_impl(value, model)
    namespace["MUTATIONS"] = {
        label: (target, types.FunctionType(make.__code__, namespace, make.__name__, make.__defaults__,
                                           make.__closure__))
        for label, (target, make) in model.MUTATIONS.items()}
    _LOADED["namespace"] = namespace
    return namespace


def model_names_missing_in_impl() -> list[str]:
    """Engine names the model defines (classes and non-scenario functions) that the implementation lacks; the
    scenario helpers and mutation factories are exempt (they stay model code, rebound)."""
    model = load_model()
    helpers = {"spec", "base_steps", "new_log", "recontract", "approve", "run", "check", "expect", "reco_spec",
               "t3c_steps", "iteration_steps", "partitioned_steps", "_chain", "run_tests", "h",
               "_mut_fail_only_from_computed", "_mut_newest_producer"}
    missing = []
    for name, value in vars(model).items():
        if name.startswith("__") or name in helpers or (name.startswith("t") and name[1:3].isdigit()):
            continue
        if isinstance(value, (types.FunctionType, type)) and getattr(value, "__module__", "") == model.__name__ \
                and not name.startswith("_NoWriter") and not hasattr(impl, name):
            missing.append(name)
    return missing


def scenarios(namespace) -> list:
    return [namespace[name] for name in sorted(namespace) if name.startswith("t") and name[1:3].isdigit()
            and isinstance(namespace[name], types.FunctionType)]


def run_scenarios(funcs, stop_at_first=False) -> list[tuple[str, str]]:
    failed = []
    for func in funcs:
        try:
            func()
        except Exception as exc:  # noqa: BLE001  (any exception is a failed scenario)
            failed.append((func.__name__, f"{type(exc).__name__}: {exc}"))
            if stop_at_first:
                break
    return failed


class Mutated:
    """Context manager: apply one model mutation to the implementation module, restore it on exit."""

    def __init__(self, namespace, label):
        self.target, self.make = namespace["MUTATIONS"][label]
        self.namespace = namespace

    def __enter__(self):
        self.original = getattr(impl, self.target)
        mutated = self.make(self.original)
        setattr(impl, self.target, mutated)
        self.namespace_original = self.namespace.get(self.target)
        self.namespace[self.target] = mutated
        return self

    def __exit__(self, *exc):
        setattr(impl, self.target, self.original)
        self.namespace[self.target] = self.namespace_original
        return False
