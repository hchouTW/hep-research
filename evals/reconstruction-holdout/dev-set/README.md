# T13 development set (harness shakedown only; never the holdout)

Agent-written development material for the T13 harness shakedown (t13-harness-spec.md, section 4; K11). It is **not**
the holdout and says nothing about it: it was written by the builders, inside the repository, from the public level of
the writer brief (section 3) only. It is tuned on and cannot confirm anything. Every prompt starts with "DEVELOPMENT
SET". It is far below the frozen design (6 groups), so it validates only with `--design none`:

```
python3 ../score_holdout.py validate --tasks tasks.json --answers answers.json --design none
```

Reference values come from the stated parameters: DEV01 two clusters, the larger 5.0 + 2.0 + 1.0 = 8.0 GeV; DEV02 the
noise-free line x = 0.5 cm + 0.02 z; DEV05 mean 90.0 GeV, so the 1 % check against 100 GeV fails; DEV06 the flight-time
difference L/c (sqrt(1 + (m_K/p)^2) - sqrt(1 + (m_pi/p)^2)) = 0.352 ns, accepted within 2 %. DEV03 gives no sensor
positions and no light model; DEV04 is 512 bytes of no stated layout. Every report field states its claim kind and
unit (round 13; DEV06's flight-time difference is a value in ns, and DEV05 and DEV06 carry a field for the run).

Shakedown: copy `tasks.json` and `inputs/` into a fresh run root and run `run_holdout.py run` there (paid model
calls: only on the user's word); score with `--design none`.
