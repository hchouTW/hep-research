# cr-propagation r4: escalation queue

Written only by the orchestrator (`workflow-r4.md` §8). Each item: work package; type (`capability`,
`tolerance-miss`, `rule-conflict`, `repo-mismatch`, `budget`, `blocked`); evidence; handling attempted; affected
downstream work packages; suggested human decision. A queued item never stops unaffected work packages.

| # | Date | WP | Type | Evidence | Handling attempted | Affected | Suggested decision | State |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-26 | ENV → B1 | capability | `$CRPROP_OUT/capabilities.json`: env-usine absent, net-sources absent (`CRPROP_SOURCES` empty; source hosts time out from the sandbox, D2) | none possible without the source (D4: no download from elsewhere) | B1, B3, C2U, D3, E1 wait (`waiting-capability`); F1 waits, and takes the D8 DRAGON2 fallback (insufficient for v1) only if USINE is confirmed unobtainable | maintainer places the USINE V3.5 tarball in `$HOME/hep-work/crprop-sources/`, or declares USINE unobtainable so F1 takes D8 | open (critical; maintainer notified per D12) |
| 2 | 2026-10-26 | ENV → D2 | capability | env-galprop absent (no GALPROP v57 tarball) | none (D5) | D2 waits; at RC, if still absent, D2 is marked `unavailable` (its fallback) and D3 compares DRAGON2 and USINE only | maintainer places the GALPROP v57 tarball, or accepts D2 `unavailable` | open |
| 3 | 2026-10-26 | ENV → F1 | capability | net-data partial: hepdata.net HTTP 200; `lpsc.in2p3.fr/crdb/` timed out (curl exit 28) | none | F1's CRDB cross-check only (r3 F1: CRDB is secondary); HEPData or the paper's tables remain the primary data path | none needed unless F1 needs CRDB; then allow the host | open (non-blocking) |
