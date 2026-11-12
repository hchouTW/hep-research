"""reco.timing.time-chain/1: the T10 timing development binding (t10-timing-stage-plan.md; decisions.md, U12 A as for T08, T09).

A development binding in Python, not a native backend: the native timing-backend gap stays open. Modules:

- timing_payload: timing-payload/1, one conditions payload per chain step (offset, walk, propagation) keyed by the channel map
  timing-channel-map/1, with derived payloads that record their source (plan R32, R37).
- time_chain: per hit, the value before and after each step in chain order with that step's payload identity, the amplitude,
  both ends' times or the position with its source, and the path length (plan R35); single-ended and two-ended counters.
- event_time: external, common linear, per-track leave-one-out linear and median event times, each recording its source,
  estimator, hits and weights (plan R35); time of flight and beta.

Synthetic constants only (R31); no timing, TOF or PID quality is claimed. The calibration-interface checks CAI-T10-1 and -2 are
fixture_tools/t10_cai.py, outside the recipe; the recipe never imports it.
"""

RECIPE = "reco.timing.time-chain/1"
