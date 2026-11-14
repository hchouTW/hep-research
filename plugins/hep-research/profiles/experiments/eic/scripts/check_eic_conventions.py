#!/usr/bin/env python3
"""Check the EIC-specific parts of a measurement-spec or theory-spec against the experiment:eic profile.

What it checks (rule codes; the spec field format is in modules/facility/beam-configurations.md):
  eic.configuration_missing          error    no eic:beam_energy_configuration in the conventions block, or no eic:beams
  eic.frame_conflated                error    rapidity_frame missing, or the frame convention equates lab and CM frames
  eic.ion_normalization_missing      error    a non-proton hadron without A, Z or a per-nucleon energy
  eic.polarization_convention_missing error/warning  polarization_convention missing (error when a beam is polarized,
                                              warning when only the observable text mentions polarization or asymmetry)
  eic.azimuth_convention_missing     warning  azimuthal observables named but azimuth_convention missing
  eic.crossing_angle_undeclared      warning  eic:crossing_angle_treatment missing
  eic.beam_value_unsourced           error    a beam value cites neither 'user-supplied' nor a numeric eic claim with a
                                              scope.number_kind whose text states that value
  eic.projection_unlabelled          error/warning  status 'projection' without eic:geometry_release (error), or the
                                              observable text says projection while status lacks it (warning)
  eic.scope_mixing                   warning  the observable text uses the profile's prohibited facility/detector phrase,
                                              or a beam value cites a proposed run plan (number_kind 'proposal')
Info findings (never change the verdict): eic.deprecated_key (old convention keys) and, with --profiles-from,
eic.unknown_key_info (a convention key outside the merged core and profile vocabulary).

Usage (from the plugin root):
  python3 profiles/experiments/eic/scripts/check_eic_conventions.py SPEC.json [--profiles-from hep-research.project.json]
Output: JSON with status, verdict (blocked, needs-work, acceptable-with-open-inputs), defects and unresolved inputs.
Exit codes (core.status): 0 no error or warning, 1 errors or warnings, 2 unreadable input or not a spec, 3 missing
dependency. Imports only core, contracts, the standard library and the profile's own number_rules module.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_ROOT = SCRIPT_DIR.parent
PLUGIN_ROOT = PROFILE_ROOT.parents[2]
CLAIMS_PATH = PROFILE_ROOT / "evidence" / "claims.json"

SPEC_TYPES = ("measurement-spec", "theory-spec")
PROTON_NAMES = {"p", "proton", "p+", "h", "1h"}
DEPRECATED_KEYS = {"eic:hadron_beam_direction": "rapidity_frame", "eic:polarization_sign": "polarization_convention"}
LAB_EQUALS_CM = re.compile(r"\blab(oratory)?( frame)?\s*(=|==|equals|is the same as|coincides with)\s*(the )?"
                           r"(cm|cms|c\.m\.|cent(er|re)[- ]of[- ]mass)")
POLARIZATION_WORDS = re.compile(r"asymmetr|polari[sz]", re.IGNORECASE)
AZIMUTH_WORDS = re.compile(r"azimuth|φ_h|φ_s|phi_h|phi_s|sivers|collins|trento", re.IGNORECASE)
PROJECTION_WORD = re.compile(r"\bprojection", re.IGNORECASE)
SCOPE_PHRASE = " ".join(("EIC", "detector")).lower()  # built at run time: the profile never writes the phrase


def emit(report, exit_status):
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return exit_status


def load_dependencies():
    """core.status for exit codes, contracts for --profiles-from, number_rules for number tokens."""
    sys.path.insert(0, str(PLUGIN_ROOT))
    sys.path.insert(0, str(SCRIPT_DIR))
    import core.status as run_status  # noqa: E402
    import number_rules  # noqa: E402
    return run_status, number_rules


def collect_strings(node):
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [text for value in node.values() for text in collect_strings(value)]
    if isinstance(node, list):
        return [text for value in node for text in collect_strings(value)]
    return []


def spec_parts(spec):
    """(conventions block, beam-field container and its path, observable text) of a measurement- or theory-spec."""
    extension = spec.get("extension") or {}
    if spec["artifact_type"] == "measurement-spec":
        conventions = (extension.get("observable") or {}).get("conventions") or {}
        fields_path, fields = "extension.experiment_fields", extension.get("experiment_fields") or {}
        texts = [spec.get("objective", "")] + collect_strings(extension.get("estimand")) + collect_strings(extension.get("observable"))
    else:
        conventions = extension.get("conventions") or {}
        fields_path, fields = "extension.parameters", extension.get("parameters") or {}
        texts = [spec.get("objective", "")]
        for part in ("model", "assumptions", "validity_domain"):
            texts += collect_strings(extension.get(part))
    conventions_path = ("extension.observable.conventions" if spec["artifact_type"] == "measurement-spec"
                        else "extension.conventions")
    return conventions, conventions_path, fields, fields_path, " ".join(t for t in texts if isinstance(t, str))


def beam_values(beams, beams_path):
    """(path, kind, V) for each beam value of eic:beams; kind is 'polarization' or 'number'."""
    electron, hadron = beams.get("electron") or {}, beams.get("hadron") or {}
    entries = [(f"{beams_path}.electron.energy_GeV", "number", electron.get("energy_GeV")),
               (f"{beams_path}.electron.polarization", "polarization", electron.get("polarization")),
               (f"{beams_path}.hadron.energy_per_nucleon_GeV", "number", hadron.get("energy_per_nucleon_GeV")),
               (f"{beams_path}.hadron.polarization", "polarization", hadron.get("polarization")),
               (f"{beams_path}.crossing_angle_mrad", "number", beams.get("crossing_angle_mrad"))]
    return [entry for entry in entries if entry[2] is not None]


def value_problem(kind, beam_value, claims, number_rules):
    """None when the value is sourced, else the reason; also the cited claim (or None)."""
    if not isinstance(beam_value, dict) or "value" not in beam_value or "source" not in beam_value:
        return "a beam value must be {\"value\": number, \"source\": \"eic:Cnn\" or \"user-supplied\"}", None
    source, number = beam_value["source"], beam_value["value"]
    if source == "user-supplied":
        return None, None
    claim = claims.get(source)
    if claim is None or not claim.get("numeric_quotation_allowed") or not claim.get("scope", {}).get("number_kind"):
        return f"{source} is not a numeric eic claim with a scope.number_kind", None
    if not isinstance(number, (int, float)) or isinstance(number, bool):
        return "the value is not a number", claim
    candidates = [float(number)] + ([100.0 * float(number)] if kind == "polarization" else [])
    if not any(number_rules.contains_number(claim["claim"], candidate) for candidate in candidates):
        return f"{source} does not state {number}", claim
    return None, claim


def check(spec, claims, number_rules, vocabulary=None):
    conventions, conventions_path, fields, fields_path, observable_text = spec_parts(spec)
    defects, unresolved = [], []

    def add(code, level, path, message):
        defects.append({"code": code, "level": level, "path": path, "message": message})

    beams = fields.get("eic:beams")
    beams_path = f"{fields_path}.eic:beams"
    if "eic:beam_energy_configuration" not in conventions or not isinstance(beams, dict):
        missing = [name for name, present in (("eic:beam_energy_configuration", "eic:beam_energy_configuration" in conventions),
                                               ("eic:beams", isinstance(beams, dict))) if not present]
        add("eic.configuration_missing", "error", conventions_path if "eic:beams" not in missing else fields_path,
            f"missing {', '.join(missing)}")
    beams = beams if isinstance(beams, dict) else {}

    frame_text = str(conventions.get("frame", "")).lower()
    if "rapidity_frame" not in conventions:
        add("eic.frame_conflated", "error", conventions_path, "rapidity_frame is missing: state the frame and its +z direction")
    elif LAB_EQUALS_CM.search(frame_text):
        add("eic.frame_conflated", "error", f"{conventions_path}.frame", "the frame convention equates the laboratory and center-of-mass frames")

    hadron = beams.get("hadron") or {}
    species = str(hadron.get("species", "")).strip().lower()
    if hadron and species not in PROTON_NAMES:
        lacking = [name for name in ("A", "Z", "energy_per_nucleon_GeV") if hadron.get(name) is None]
        if lacking:
            add("eic.ion_normalization_missing", "error", f"{beams_path}.hadron",
                f"hadron '{hadron.get('species')}' needs {', '.join(lacking)} (ion energies per nucleon)")

    values = beam_values(beams, beams_path)
    polarized = any(kind == "polarization" and isinstance(v, dict) and v.get("value") not in (None, 0) for _, kind, v in values)
    if "polarization_convention" not in conventions:
        if polarized:
            add("eic.polarization_convention_missing", "error", conventions_path, "a beam is polarized but polarization_convention is missing")
        elif POLARIZATION_WORDS.search(observable_text):
            add("eic.polarization_convention_missing", "warning", conventions_path, "the observable mentions polarization or an asymmetry but polarization_convention is missing")

    if AZIMUTH_WORDS.search(observable_text) and "azimuth_convention" not in conventions:
        add("eic.azimuth_convention_missing", "warning", conventions_path, "azimuthal observables are named but azimuth_convention is missing")

    if "eic:crossing_angle_treatment" not in conventions:
        add("eic.crossing_angle_undeclared", "warning", conventions_path, "eic:crossing_angle_treatment is missing")

    proposal_cited = []
    for path, kind, beam_value in values:
        problem, claim = value_problem(kind, beam_value, claims, number_rules)
        if problem:
            add("eic.beam_value_unsourced", "error", path, problem)
        elif beam_value["source"] == "user-supplied":
            unresolved.append({"path": path, "value": beam_value["value"], "reason": "user-supplied value; not checked against the profile"})
        if claim is not None and claim.get("scope", {}).get("number_kind") == "proposal":
            proposal_cited.append(path)

    statuses = spec.get("status") or []
    if "projection" in statuses and "eic:geometry_release" not in fields:
        add("eic.projection_unlabelled", "error", "status", "status contains projection but eic:geometry_release is missing")
    elif "projection" not in statuses and PROJECTION_WORD.search(observable_text):
        add("eic.projection_unlabelled", "warning", "status", "the observable text says projection but status lacks it")

    if SCOPE_PHRASE in observable_text.lower():
        add("eic.scope_mixing", "warning", "objective", "the text merges the facility and one experiment: say EIC for the facility and ePIC for the experiment")
    for path in proposal_cited:
        add("eic.scope_mixing", "warning", path, "cites a proposed run plan of ePIC (not a facility design value); say so in the spec's text")

    for key, replacement in DEPRECATED_KEYS.items():
        if key in conventions:
            add("eic.deprecated_key", "info", f"{conventions_path}.{key}", f"{key} was removed from the profile; use {replacement}")
    if vocabulary is not None:
        for key in conventions:
            if key not in DEPRECATED_KEYS and not vocabulary.has("convention_keys", key):
                add("eic.unknown_key_info", "info", f"{conventions_path}.{key}", f"{key} is not in the merged core and profile vocabulary")

    levels = {d["level"] for d in defects}
    verdict = "blocked" if "error" in levels else "needs-work" if "warning" in levels else "acceptable-with-open-inputs"
    return verdict, defects, unresolved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path, help="measurement-spec or theory-spec JSON file")
    parser.add_argument("--profiles-from", type=Path, dest="profiles_from",
                        help="hep-research.project.json whose bound profiles extend the convention vocabulary")
    args = parser.parse_args(argv)
    try:
        run_status, number_rules = load_dependencies()
    except ImportError as exc:
        return emit({"status": "missing-dependency", "message": str(exc)}, 3)
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return emit({"status": "rejected", "message": f"unreadable input: {exc}"}, run_status.exit_code("rejected"))
    if not isinstance(spec, dict) or spec.get("artifact_type") not in SPEC_TYPES:
        return emit({"status": "rejected", "message": f"not a measurement-spec or theory-spec: {args.spec.name}"},
                    run_status.exit_code("rejected"))
    vocabulary = None
    if args.profiles_from:
        from contracts.project import load_project  # noqa: E402
        from contracts.vocab import Vocabulary  # noqa: E402
        try:
            project = load_project(args.profiles_from)
        except (OSError, ValueError) as exc:
            return emit({"status": "rejected", "message": f"unreadable project config: {exc}"}, run_status.exit_code("rejected"))
        if not project.report.ok:
            return emit({"status": "rejected", "message": "invalid project config: " + "; ".join(
                f"{f.code}: {f.message}" for f in project.report.errors)}, run_status.exit_code("rejected"))
        vocabulary = Vocabulary.with_profiles(project.profiles)
    claims = {c["id"]: c for c in json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))}
    verdict, defects, unresolved = check(spec, claims, number_rules, vocabulary)
    status = "ok" if verdict == "acceptable-with-open-inputs" else "refused"
    return emit({"status": status, "verdict": verdict, "spec": args.spec.name, "defects": defects, "unresolved": unresolved},
                run_status.exit_code(status))


if __name__ == "__main__":
    sys.exit(main())
