# g4sim performance budget

Section 16 of the plan. The gates of S2 (gate 7) and S8 (gate 1) are judged against these numbers. Written in S1 and registered in `g4sim-task-registry.json` before any S2 run. Numbers may be tightened, never loosened, except by a human decision with a stated reason (Section E7).

| Quantity | Limit | Basis |
| --- | --- | --- |
| Construction time for 10⁵ placements | at most 60 s | Measured on E5: 0.16 s with transportation only. The limit leaves room for a full physics list, which the measurement does not contain |
| Construction memory for 10⁵ placements | at most 2 GB | Measured on E5: 73 MB peak, same setup |
| Scorer overhead at 10³ steps per event | at most 25 % of the wall time without scorers | Proposal: `g4sim_run` does not exist yet, so this is not measured |
| MT merge time | at most 5 % of the run's wall time | Proposal, not measured, for the same reason |
| check-spec for 10⁶ touchables | at most 300 s | Expansion and the gap rule, measured on E5 at 10⁵ placements in one mother: 2.8 s and 2.9 s, linear, so about 60 s at 10⁶. check-spec itself arrives in S2 |

S4 adds the throughput of the response pipeline (Section 16):

| Quantity | Limit | Basis |
| --- | --- | --- |
| Response pipeline in Python, on one core | at most 25 % of the transport wall time of the same events on one core | Proposal, written before any measurement, on the reasoning of the scorer overhead: the response should not change what a study costs. If Python cannot meet it, `g4sim_digi` is built (Section 10.2) |

Measurements of this limit, 2026-11-07, E5 login host, shared, one core, light yield 100 per MeV, four channels; the limit stays as written (`g4sim-approvals.md`):

| Workload | Events | Bins per event | Response / transport | Within 0.25 |
| --- | --- | --- | --- | --- |
| e+ 1 to 60 MeV, plastic block, the registered measurement | 2,000 | 37 | 3.53 | No |
| e+ 100 MeV, PbWO4 block | 1,000 | 50 | 1.28 | No |
| e+ 1 GeV, PbWO4 block | 200 | 139 | 0.40 | No |
| e+ 10 GeV, PbWO4 block | 30 | 198 | 0.06 | Yes |

The limit names no reference workload, and the ratio follows it: the response grows with bins, the transport with the shower. The last three rows are single short scratch runs. Throughput was about 17,000 bins per second. None of this includes `photon_times`, one draw per detected photon, which can dominate at a high light yield, so a workload with per-photon timing must be measured before `g4sim_digi` is settled in S8.

S8 measured the registered workload again on a Slurm node (2026-11-09, hpa-wn22, job 7529257, one core, build 26), and with a time drawn for every detected photon (`--photon-times`: decay 2.1 ns, exponential transit 1 ns), twice each:

| Workload | Events | Bins | Transport (s) | Response (s) | Response / transport | Within 0.25 |
| --- | --- | --- | --- | --- | --- | --- |
| e+ 1 to 60 MeV, plastic block, the registered measurement | 2,000 | 74,864 | 0.747, 0.706 | 2.57, 2.52 | 3.44, 3.57 | No |
| The same, with photon times | 2,000 | 74,864 | 0.709, 0.758 | 12.78, 12.67 | 18.0, 16.7 | No |

So Python cannot meet the limit, and `g4sim_digi` is built in S8 (Section 10.5).

`g4sim_digi` on the same workload (2026-11-09, hpa-wn19, Slurm job 7530315, `response_throughput.py --digi`, its wall time reading the job and bins and writing every row; output then in `%a`, since replaced by IEEE bits):

| Workload | Transport (s) | g4sim_digi (s) | Response / transport | Within 0.25 |
| --- | --- | --- | --- | --- |
| The registered measurement | 0.714, 0.769 | 0.164, 0.164 | 0.23, 0.21 | Yes |
| The same, with photon times (1.9 million time rows) | 0.722, 0.710 | 0.565, 0.565 | 0.78, 0.80 | No |

With a time for every detected photon the response stays above the limit in C++ too: on the login host the times' draws took about 0.3 s and writing their 60 MB about 0.2 to 0.5 s. No S8 gate judges this; it is recorded so that a study with per-photon timing knows its cost.

Measured by `adapters/geant4/tests/g4proto/s4_gates/response_throughput.py`: the transport time is the event loop of a one-thread `g4sim_run` (`G4SIM_INITIALIZED` to `G4SIM_DONE`), and the response time covers photon numbers, their distribution among channels, sensor and electronics for every bin of those events.

Measurements: E5, Geant4 11.4.3, GCC 11.5.0, 2026-11-05, one run each, on a shared host. They are orders of magnitude, not benchmarks. The two proposals should be reviewed against first measurements in S2; a limit may then be tightened.

Rule for judging: a quantity is measured on the environment that runs the gate, and a limit that cannot be met stops the phase under Section E7, item 5.
