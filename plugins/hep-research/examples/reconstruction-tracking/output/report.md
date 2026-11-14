# T07 tracking example: generate, find, refit (synthetic)

Fixture t07-telescope-clean/1, block 1 (tuning), stratum 0, 2 events, 1 T, ACTS 48.2.0. Synthetic data only. No tracking quality claim: the counts are what the programs wrote, not an efficiency; T07's quality verdict waits for K09 at Freeze B.

| Event | Hits | Seeds | Candidates | Selected | Search-truncated | Failure category |
|---|---|---|---|---|---|---|
| 0 | 48 | 24 | 6 | 6 | no | none |
| 1 | 48 | 24 | 6 | 6 | no | none |

Finding (reco.track.acts-ckf-planar/1): 12 tracks selected, evidence class data-side, reported as finding: yes.
Refit (reco.track.acts-kf-refit/1): 12 hit sets from the truth file, 12 fitted, 0 failed, evidence class truth-assisted, reported as finding: no. Counted apart from finding.

| Check | Result |
|---|---|
| every wrapper operation is ok with exit 0 | pass |
| the finder's command names no truth file | pass |
| the record and both products name the generated data file | pass |
| the record says finding, on the data side | pass |
| the finder's product says finding, on the data side | pass |
| the refit's product is truth-assisted and never finding | pass |
| the refit's product holds every R33 record | pass |
| the hit sets are truth-assisted and the refit names them | pass |
| predicted, filtered and smoothed stay apart in the finder's product | pass |
| the finder's product holds the record's selected tracks | pass |
