"""Old-version readers (v6.3 D11a): read an operator-semantics table of version 1.0.0, which has no stages and no
member coverage, through the coverage contract the semantic lock pins. The table is never upgraded or rewritten; the
reader adds the contract's stage, covers, class coverage and factors next to the table's own 'applies'. Only the
pinned contract is used: an unpinned one, one whose digest differs from the pin, or a table that no longer matches
the contract's table digest yields no operators, so the rules treat them as unsupported."""
from __future__ import annotations

from contracts.release_manifest import canonical_sha256

READERS = {"1.0.0": "differential-flux-1.0.0-via-coverage"}


def read_table(table: dict, coverage: dict | None, pinned: str | None) -> dict:
    reader = READERS.get(str(table.get("table_version")))
    out = {"reader": reader, "table_id": table.get("table_id"), "status": "pinned", "operators": {}}
    if reader is None:
        return dict(out, status="unsupported_version")
    if not isinstance(coverage, dict):
        return dict(out, status="no_contract")
    if pinned is None:
        return dict(out, status="unpinned")
    if canonical_sha256(coverage) != pinned:
        return dict(out, status="mismatch")
    if coverage.get("table_sha256") != canonical_sha256(table) or coverage.get("table_id") != table.get("table_id"):
        return dict(out, status="table_changed")
    cov_ops = {o["operator_id"]: o for o in coverage.get("operators", [])}
    for op in table.get("operators", []):
        c = cov_ops.get(op.get("operator_id"))
        if c is None:
            continue
        out["operators"][op["operator_id"]] = {
            "operator_id": op["operator_id"], "applies": list(op.get("applies", [])), "input_kind": op.get("input_kind"),
            "output_kind": op.get("output_kind"), "stage": c.get("stage"), "covers": list(c.get("covers", [])),
            "class_coverage": dict(c.get("class_coverage", {})), "factors": list(c.get("factors", []))}
    return out
