"""Process driver helpers of the independent review mechanism (docs/dev/independent-review-spec.md, P1), used only by
skills/hep-authoring/scripts/review.py: units and sampling (units), canaries (canary), packets and the instruction
generator (packet), observe (observe), receipt (receipt), the report (report) and file storage with the event-log lock
(store). The schemas, rules, state table and check are contracts/review.py; nothing here re-implements them.
"""
