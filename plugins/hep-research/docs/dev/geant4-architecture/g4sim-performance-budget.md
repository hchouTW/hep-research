# g4sim performance budget

Section 16 of the plan. The gates of S2 (gate 7) and S8 (gate 1) are judged against these numbers. Written in S1 and registered in `g4sim-task-registry.json` before any S2 run. Numbers may be tightened, never loosened, except by a human decision with a stated reason (Section E7).

| Quantity | Limit | Basis |
| --- | --- | --- |
| Construction time for 10⁵ placements | at most 60 s | Measured on E5: 0.16 s with transportation only. The limit leaves room for a full physics list, which the measurement does not contain |
| Construction memory for 10⁵ placements | at most 2 GB | Measured on E5: 73 MB peak, same setup |
| Scorer overhead at 10³ steps per event | at most 25 % of the wall time without scorers | Proposal: `g4sim_run` does not exist yet, so this is not measured |
| MT merge time | at most 5 % of the run's wall time | Proposal, not measured, for the same reason |
| check-spec for 10⁶ touchables | at most 300 s | Expansion and the gap rule, measured on E5 at 10⁵ placements in one mother: 2.8 s and 2.9 s, linear, so about 60 s at 10⁶. check-spec itself arrives in S2 |

S4 adds the throughput of the response pipeline (Section 16).

Measurements: E5, Geant4 11.4.3, GCC 11.5.0, 2026-11-05, one run each, on a shared host. They are orders of magnitude, not benchmarks. The two proposals should be reviewed against first measurements in S2; a limit may then be tightened.

Rule for judging: a quantity is measured on the environment that runs the gate, and a limit that cannot be met stops the phase under Section E7, item 5.
