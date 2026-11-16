"""Read aliases for the schema ids of hep-research 0.69.0 and earlier (simcal rename, 0.70.0; docs/dev/simcal-naming-map.md).

The simulator parameter calibration workflow (simcal) wrote its files under bare "calibration" ids until 0.69.0. Since
0.70.0 every writer emits the simcal ids; a reader accepts the old id of the same schema through `is_schema`, which
prints the notice `simcal.legacy_schema_id` once per old id on stderr. No reader rewrites an id: an old file is read and
hashed as written, so its hash citations still resolve. The aliases are removed in 0.72.0 (a migration tool for old
files follows before then). This is the only module that holds the old ids.
"""

from __future__ import annotations

import sys

REMOVED_IN = "0.72.0"

# old id -> new id (the 9 simcal schema ids written or read by code, and the g4sim evaluator's state)
OLD_TO_NEW_ID = {
    "calibration-contract/1": "simcal-contract/1",
    "calibration-data-release/1": "simcal-data-release/1",
    "calibration-fixture/1": "simcal-fixture/1",
    "calibration-ledger/1": "simcal-ledger/1",
    "calibration-plan/1": "simcal-plan/1",
    "calibration-result/1": "simcal-result/1",
    "calibration-identity-equivalence/1": "simcal-identity-equivalence/1",
    "calibration-decisions/1": "simcal-decisions/1",
    "calibration-ask-tell/1": "simcal-ask-tell/1",
    "g4sim-calib-eval-state/1": "g4sim-simcal-eval-state/1",
}
NEW_TO_OLD_ID = {new_id: old_id for old_id, new_id in OLD_TO_NEW_ID.items()}

_noticed: set = set()


def notice(old_id: str) -> None:
    """Print the deprecation notice for an old id, once per id and process."""
    if old_id in _noticed:
        return
    _noticed.add(old_id)
    print(f"simcal.legacy_schema_id: {old_id} is read as {OLD_TO_NEW_ID[old_id]} (the id of hep-research 0.69.0 and earlier; "
          f"read until {REMOVED_IN})", file=sys.stderr)


def is_schema(doc, new_id: str) -> bool:
    """True when `doc` is a dict whose `schema` is `new_id`, or the old id of the same schema (with the notice)."""
    if not isinstance(doc, dict):
        return False
    got = doc.get("schema")
    if got == new_id:
        return True
    if got is not None and got == NEW_TO_OLD_ID.get(new_id):
        notice(got)
        return True
    return False
