#!/usr/bin/env python3
"""M2 step 2: migrate the legacy AMS evidence ledger into the ams-02 profile with namespaced IDs.

Reads $LEGACY_REPO/ams-analysis/data/{sources,claims,papers_manifest}.json (agentic-ai-skills@3e995a4)
and writes plugins/hep-research/profiles/experiments/ams-02/evidence/{sources,claims,legacy_id_map,papers_manifest}.json.

Record-level changes (all listed in legacy_id_map.json "changes"):
  * id 'S01' -> 'ams02:S01', 'C01' -> 'ams02:C01'; references (source_ids, supersedes, superseded_by) likewise;
    the old value is kept as legacy_id.
  * access_date renamed verification_date (same meaning: the day the source was read at its level).
    A missing access_date becomes verification_date 'unknown' (never a fabricated date).
  * formal_status added, derived only from the legacy tier class in references/source-policy.md.
  * evidence_status added, derived only from support_kind.
Every other field is copied unchanged. Prose inside fields is not edited: bare S/C IDs in text mean ams02:S/C.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

HERE = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
LEGACY = Path(os.environ.get("LEGACY_REPO", HERE / ".legacy" / "agentic-ai-skills")) / "ams-analysis" / "data"
OUT = HERE / "plugins" / "hep-research" / "profiles" / "experiments" / "ams-02" / "evidence"
NS = "ams02"
TIER_CLASS = {1: "published", 2: "official-document", 3: "preliminary", 4: "reference", 5: "other-experiment", 6: "secondary"}
EVIDENCE_STATUS = {"primary": "public-fact", "absence_search": "public-fact", "third_party_context": "public-fact", "general_method": "general-method"}


def q(x: str) -> str:
    return f"{NS}:{x}"


def main() -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=LEGACY, text=True).strip()
    sources = json.loads((LEGACY / "sources.json").read_text(encoding="utf-8"))
    claims = json.loads((LEGACY / "claims.json").read_text(encoding="utf-8"))
    out_s, out_c, idmap = [], [], {}
    for s in sources:
        n = {"id": q(s["id"]), "legacy_id": s["id"]}
        for k, v in s.items():
            if k == "id":
                continue
            if k == "access_date":
                n["verification_date"] = v if v else "unknown"
            elif k in ("supersedes", "superseded_by"):
                n[k] = [q(x) for x in v]
            else:
                n[k] = copy.deepcopy(v)
        if "access_date" not in s:
            n["verification_date"] = "unknown"
        n["formal_status"] = TIER_CLASS[s["tier"]]
        out_s.append(n)
        idmap[s["id"]] = n["id"]
    for c in claims:
        n = {"id": q(c["id"]), "legacy_id": c["id"]}
        for k, v in c.items():
            if k == "id":
                continue
            n[k] = [q(x) for x in v] if k == "source_ids" else copy.deepcopy(v)
        n["evidence_status"] = EVIDENCE_STATUS[c.get("support_kind", "primary")]
        out_c.append(n)
        idmap[c["id"]] = n["id"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sources.json").write_text(json.dumps(out_s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "claims.json").write_text(json.dumps(out_c, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = json.loads((LEGACY / "papers_manifest.json").read_text(encoding="utf-8"))
    for p in manifest.get("papers", []):
        for key in ("ledger_source_ids", "source_ids"):
            if isinstance(p.get(key), list):
                p[key] = [q(x) for x in p[key]]
    (OUT / "papers_manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "legacy_id_map.json").write_text(json.dumps({
        "source": f"agentic-ai-skills@{commit} ams-analysis/data", "namespace": NS, "ids": idmap,
        "changes": [
            "id and reference fields namespaced; old value in legacy_id",
            "access_date renamed verification_date (missing -> 'unknown')",
            "formal_status added from tier class (source-policy.md tier table): " + json.dumps(TIER_CLASS),
            "evidence_status added from support_kind: " + json.dumps(EVIDENCE_STATUS),
            "papers_manifest source-ID lists namespaced",
        ]}, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(out_s), "claims": len(out_c), "commit": commit}))


if __name__ == "__main__":
    main()
