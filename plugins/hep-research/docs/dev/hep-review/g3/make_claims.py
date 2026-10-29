#!/usr/bin/env python3
"""Write skills/hep-review/assets/claims.json through the claim lifecycle (never by hand). Development tool.

    make_claims.py pilot     the pilot-checked-scope claim from G2, g2h and g2x
    make_claims.py g3        both claims: the pilot one and the evaluated-scope claim measured by G3
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))
sys.dont_write_bytecode = True

from hep_review_support import evaluation as E  # noqa: E402

REGISTRY = ROOT / "skills" / "hep-review" / "assets" / "claims.json"
SINGLE_PAGE_MEASURED_AT = "9c499a24"  # G2, g2h and g2x ran under this packet text, validator 0.1.0 and host profile
G3_MEASURED_AT = "9fd4faca"           # every G3 trial ran under this tree (results committed before decryption)


def _show(commit: str, rel: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:plugins/hep-research/{rel}"], cwd=ROOT, capture_output=True,
                          check=True).stdout


def _constant(source: bytes, name: str) -> str:
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def parts_at(commit: str) -> dict:
    """The fingerprint parts of the tree a claim was measured on, read from the repository history."""
    sup = "skills/hep-review/scripts/hep_review_support/"
    return E.fingerprint_parts(
        **MODEL, host=json.loads(_show(commit, "skills/hep-review/assets/host_profile.json")),
        packet=_constant(_show(commit, sup + "coordinator.py"), "PACKET"),
        validator_version=_constant(_show(commit, "contracts/hep_review.py"), "LATEST_VALIDATOR"),
        reader=E.reader_digest({name: _show(commit, sup + name) for name in E.READER_FILES}))
MODEL = {"model_alias": "claude-opus-5-5 (session model, inherited by general-purpose subagents)",
         "model_pinned": False, "date": "2026-10-29"}


def pilot_claim() -> dict:
    scope = {"domain": "statistics", "method": "assumption-check + recompute (0.1% relative)", "format": "text + JSON",
             "material": "single-page analyses, up to three planted defects, closed-form checks",
             "host": "claude-code-cli-macos", "tier": "R2"}
    binding = {"policy": "docs/dev/hep-review/pilot/frozen-protocol.md, g2h/frozen-protocol.md, g2x/frozen-protocol.md",
               "rubric": "pilot/grader-instructions.md, pilot/g2x/grader-instructions.md",
               "gold": "salted commitments: pilot/commitments.json, g2h/commitments.json, g2x/evidence/commitments.json",
               "suite": "G2 (Claude-authored), g2h (held out, seed with the user), g2x (Codex-authored, held out)",
               "case_distribution": {"G2": {"C01": 4, "C02": 4, "C03": 4, "C04": 4},
                                     "g2h": {"C01": 5, "C02": 5, "C03": 3, "C04": 2},
                                     "g2x": {"C01": 8, "C02": 4, "C03": 2, "C04": 2}},
               "trial_plan": "3 trials per instance: 48 + 45 + 48 = 141 trials, 47 cases"}
    results = {"content_misses": "0 of 141 trials", "G2": "both gates 48/48", "g2h": "both gates 45/45",
               "g2x": "scientific gate pass (37/39 defect-trials counted; the 2 uncounted were found but quarantined), "
                      "engineering 47/48 (one fabricated digest)",
               "c02_false_alarms": "0 of 39 control trials"}
    limitations = ["no miss rate measured: every suite was at the ceiling",
                   "reviewers and two of three grader runs are the same model family",
                   "Claude wrote the G2/g2h oracles and every authoring brief; Codex gold is author self-assessment",
                   "3 trials per instance with identical packets: 141 trials are 47 cases"]
    c = E.make_claim("hep-review/statistics-single-page", scope, binding, results=results, limitations=limitations,
                     parts=parts_at(SINGLE_PAGE_MEASURED_AT), measured_at=SINGLE_PAGE_MEASURED_AT)
    c = E.transition(c, "pilot-checked-scope", at="2026-10-29",
                     evidence={"engineering_gate": True, "graders_calibrated": True, "kind": "pilot",
                               "report": "docs/dev/hep-review/g2h-report.md (and g2-report.md, g2x-report.md)"})
    # the packet text and validator changed after these pilots (1dfb15fa, 0bea7326): the claim needs reassessment
    return E.reassess_if_changed(c, E.fingerprint_parts(**MODEL), at="2026-10-29")


def g3_claim() -> dict:
    scope = {"domain": "statistics (estimators, intervals, normalisation, look-elsewhere, unfolding-style inversions)",
             "method": "assumption-check + recompute (0.1% relative)", "format": "text + JSON",
             "material": "multi-step analyses of 800-2,000 words with two interacting planted defects each "
                         "(numerical and particle-physics-convention defects included)",
             "host": "claude-code-cli-macos", "tier": "R2"}
    binding = {"policy": "docs/dev/hep-review/g3/frozen-protocol.md", "rubric": "pilot/g2x/grader-instructions.md",
               "gold": "salted commitments: g3/evidence/commitments.json (Codex-authored, held encrypted by the user)",
               "suite": "g3 (Codex-authored, held out)",
               "case_distribution": {"C01": 12, "C02": 5, "C03": 2, "C04": 1},
               "trial_plan": "3 trials per instance, 60 trials; graders Claude forward, Claude reversed, Codex"}
    results = {"defect_detection": "71/72 = 0.986, 95% CI [0.925, 0.9997] (miss rate 0.014, CI [0.0003, 0.075])",
               "numerical_defects": "26/27, CI [0.810, 0.9991]", "convention_defects": "18/18, CI [0.8146, 1.0]",
               "c02_false_alarm": "0/15, CI [0.0, 0.2181]", "c03_gap_kept": "6/6", "c04": "3/3",
               "engineering": "60/60 digest-bound, R2, verified, export recompute, no quarantine",
               "miss": "g3dd81149-t2 D2 (equal-tailed interval released as shortest): reviewer asserted the "
                       "opposite; t1 and t3 found it"}
    limitations = ["every C01 instance had exactly two defects (the brief allowed 2-4): no evidence beyond two",
                   "20 cases with 3 trials each: 60 trials are 20 cases; intervals assume trial independence",
                   "Codex gold is author self-assessment carried by executable oracles; Claude wrote the brief",
                   "reviewers share a scratch folder: one reviewer's scratch file was overwritten by another's "
                   "(noticed and discarded); no-other-evaluations-seen is advisory"]
    c = E.make_claim("hep-review/statistics-multi-step", scope, binding, results=results, limitations=limitations,
                     parts=parts_at(G3_MEASURED_AT), measured_at=G3_MEASURED_AT)
    evidence = {"engineering_gate": True, "graders_calibrated": True, "kind": "held-out-evaluation",
                "report": "docs/dev/hep-review/g3-report.md"}
    return E.reassess_if_changed(E.transition(c, "evaluated-scope", evidence=evidence, at="2026-10-29"),
                                 E.fingerprint_parts(**MODEL), at="2026-10-29")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv not in (["pilot"], ["g3"]):
        print(__doc__)
        return 2
    claims = [pilot_claim()] + ([g3_claim()] if argv == ["g3"] else [])
    REGISTRY.write_text(json.dumps({"note": "written by docs/dev/hep-review/g3/make_claims.py through the claim "
                                            "lifecycle; checked by evaluation.check_registry",
                                    "claims": claims}, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "problems": E.check_registry(REGISTRY, current=True)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
