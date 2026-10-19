"""Synthetic golden-scenario project for the communication audits (plan T5/T6, Section 3): one observed result
(simulated by a fixture: no real measured data), one synthetic illustration, a Markdown manuscript whose abstract,
body sentence and caption carry the observed claim, and a traceability record linking them. Every number is a
placeholder."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-writing" / "scripts"))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.communication import claim_digest, evidence_fingerprint  # noqa: E402

ART = PLUGIN / "contracts" / "fixtures" / "artifacts" / "valid"
SYN = "SYNTHETIC golden-scenario fixture; values are placeholders, not physics"
CAP = "communication:traceability-v1"

ABSTRACT = "We measure the ratio R = 1.02 +/- 0.05 in the synthetic fixture sample."
BODY = "The fitted ratio is R = 1.02 +/- 0.05 (stat), consistent with unity."
CAPTION = "Figure 1: the ratio R = 1.02 +/- 0.05 compared with the synthetic illustration at 0.98."
ILLUSTRATION = "A synthetic illustration gives R = 0.98 for orientation only."

MANUSCRIPT = f"""# Synthetic fixture paper

## Abstract

{ABSTRACT}

## Results

{BODY}

{ILLUSTRATION}

## Figures

{CAPTION}
"""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p: Path, obj) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj, indent=1), encoding="utf-8")
    return p


def observed_result(value="1.02", unc="0.05"):
    d = json.loads((ART / "statres_frequentist.json").read_text(encoding="utf-8"))
    d["artifact_id"], d["status"] = "fixture-synthetic-obs", ["observed"]
    d["objective"] = SYN + " (an input labeled observed by the fixture, not real data)"
    d["extension"]["results"] = {"ratio": {"value": value, "unit": "1", "stat": unc, "rounding": "decimals:2"}}
    return d


def synthetic_prediction():
    d = json.loads((ART / "prediction.json").read_text(encoding="utf-8"))
    d["artifact_id"], d["objective"] = "fixture-synthetic-syn", SYN
    d["extension"]["results"] = {"ratio": {"value": "0.98", "unit": "1"}}
    return d


def build_project(root: Path, *, manuscript: str = MANUSCRIPT, obs_value: str = "1.02") -> dict:
    """Write the project and return {"root", "record", "obs", "syn", "paper"} paths; the record is current."""
    root = Path(root)
    obs = write(root / "artifacts" / "obs.json", observed_result(obs_value))
    syn = write(root / "artifacts" / "syn.json", synthetic_prediction())
    paper = write(root / "paper" / "main.md", manuscript)
    rec = record(root, obs, syn)
    path = write(root / "artifacts" / "comm.json", rec)
    return {"root": root, "record": path, "obs": obs, "syn": syn, "paper": paper, "doc": rec}


def edge(eid, target, role="supports", usage="used-in-claim", locator="extension.results.ratio"):
    return {"id": eid, "target_kind": "artifact", "target": target, "locator": locator, "role": role, "usage": usage}


def record(root: Path, obs: Path, syn: Path) -> dict:
    inputs = [{"ref": "artifacts/obs.json", "artifact_type": "statistical-result", "artifact_id": "fixture-synthetic-obs",
               "sha256": sha(obs), "version": json.loads(obs.read_text())["contract_version"], "status": ["observed"]},
              {"ref": "artifacts/syn.json", "artifact_type": "prediction", "artifact_id": "fixture-synthetic-syn",
               "sha256": sha(syn), "version": json.loads(syn.read_text())["contract_version"], "status": ["synthetic", "unvalidated"]}]
    doc = {"contract_version": CONTRACTS_VERSION, "artifact_id": "fixture-synthetic-golden-communication",
           "artifact_type": "communication", "objective": SYN, "bindings": {"experiments": [], "theory": []},
           "versions": {"plugin": "0.6.12", "contracts": CONTRACTS_VERSION, "profiles": {}},
           "provenance": {"producer_skill": "hep-writing", "created": "2026-10-12", "evidence_ids": []},
           "required_capabilities": [CAP], "inputs": inputs, "outputs": [], "status": ["synthetic", "unvalidated"],
           "unresolved_inputs": [], "extension": {}}
    c1 = {"id": "claim:C1", "text": "The ratio R is 1.02 +/- 0.05 (synthetic fixture).", "claim_type": "measurement",
          "scope": {"text": "synthetic fixture sample; statistical uncertainty only"}, "status": ["observed"],
          "evidence": [edge("ev:C1-a", "artifacts/obs.json")], "unresolved_inputs": [], "workflow_state": "edited"}
    c2 = {"id": "claim:C2", "text": "A synthetic illustration gives R = 0.98 (synthetic fixture).", "claim_type": "illustration",
          "scope": {"text": "illustration only"}, "status": ["synthetic", "unvalidated"],
          "evidence": [edge("ev:C2-b", "artifacts/syn.json")], "unresolved_inputs": []}
    for c in (c1, c2):
        c["assessment"] = {"verdict": "supported", "rationale": "value and uncertainty read from the named artifact field",
                           "evidence_ids": [e["id"] for e in c["evidence"]], "assessor": {"identity": "fixture", "role": "author"},
                           "date": "2026-10-12", "claim_digest": claim_digest(c),
                           "evidence_fingerprints": {e["id"]: evidence_fingerprint(e, doc) for e in c["evidence"]}, "currency": "current"}
    occ = [{"id": "occ:abstract", "claim_id": "claim:C1", "document_id": "doc:paper", "locator": "section:Abstract", "passage": ABSTRACT,
            "value": {"value": "1.02", "unit": "1", "rounding": "decimals:2"}, "state": "mapped"},
           {"id": "occ:body", "claim_id": "claim:C1", "document_id": "doc:paper", "locator": "section:Results", "passage": BODY,
            "value": {"value": "1.02", "unit": "1", "rounding": "decimals:2"}, "state": "mapped"},
           {"id": "occ:caption", "claim_id": "claim:C1", "document_id": "doc:paper", "locator": "section:Figures", "passage": CAPTION,
            "value": {"value": "1.02", "unit": "1", "rounding": "decimals:2"}, "state": "mapped"},
           {"id": "occ:illustration", "claim_id": "claim:C2", "document_id": "doc:paper", "locator": "section:Results",
            "passage": ILLUSTRATION, "state": "mapped"}]
    doc["extension"] = {"traceability_version": "1.0.0", "scope": {"occurrences": True, "sources": False},
                        "documents": [{"id": "doc:paper", "path": "paper/main.md", "format": "markdown",
                                       "audience": "journal readers", "purpose": "main text"}],
                        "claims": [c1, c2], "occurrences": occ, "sources_read": [], "evidence_ledgers": [],
                        "reporting_context": {"result_type": "measurement", "method": {"uncertainty_split": "stat-only"},
                                              "fields": {"value": {"state": "provided", "value": "1.02"}, "unit": {"state": "provided", "value": "1"},
                                                         "uncertainty_definition": {"state": "provided", "value": "68% interval, statistical"},
                                                         "statistical_uncertainty": {"state": "provided", "value": "0.05"},
                                                         "systematic_uncertainty": {"state": "not-applicable", "reason": "fixture: statistical only by construction"},
                                                         "scope": {"state": "provided", "value": "synthetic fixture sample"},
                                                         "corrections_applied": {"state": "provided", "value": "none (fixture)"}}},
                        "limitations": ["synthetic fixture: the observed label simulates a measured input and is not real data"]}
    return doc


def refresh_assessments(doc: dict) -> dict:
    """Re-pin every assessment to the current claim text and input digests (used when a test edits the record)."""
    for c in doc["extension"]["claims"]:
        a = c.get("assessment")
        if a:
            a["claim_digest"] = claim_digest(c)
            a["evidence_fingerprints"] = {e["id"]: evidence_fingerprint(e, doc) for e in c["evidence"]}
    return doc


def save(project: dict) -> Path:
    return write(project["record"], project["doc"])


def clone(doc: dict) -> dict:
    return copy.deepcopy(doc)
