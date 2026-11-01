# T-PERF — native vs detsim in one environment (W5, 2026-11-02)

Host E2: macOS 27.2 arm64 (8 cores), APFS. Same environment identity for native and detsim runs; native runs use
exactly the plan's command and variables. Script: `WR/scratch/W5/perf.sh`; raw timings `WR/scratch/W5/perf/`
(`/usr/bin/time -l`: wall time, maximum resident set size). Cold = first run after setup, warm = second.

| Backend | Run | Wall (s) | Peak RSS (MiB) | Notes |
|---|---|---|---|---|
| Allpix Squared AP-BOOT (10 events) | native cold | 3.82 | 418 | `allpix -c example.conf` + the three overrides |
| | native warm | 3.09 | 399 | |
| | detsim replicate 20 | 4.05 | 455 | backend 2.76 s inside; controller Python 3.15 + PyROOT extraction |
| | detsim replicate 21 | 4.32 | 466 | |
| Garfield++ GF-QUERY task 1 (6 points) | native cold | 1.61 | 585 | the rendered query script with the plan's variables |
| | native warm | 1.36 | 594 | |
| | detsim replicate 20 | 1.80 | 588 | backend 1.36 s inside; controller Python 3.13 |
| | detsim replicate 21 | 1.72 | 598 | |

Output volume: Allpix run folder 2.46 MB (input snapshot 2.12 MB — mostly the 2 MB field map — native output 0.23 MB);
Garfield++ run folder 96 KB (input snapshot 32 KB). Observables rows: 156 (Allpix), 30 (Garfield++).

Overhead of detsim over a warm native run: about 0.5-1.2 s for Allpix (controller start, ROOT read of the output,
hashing, F_FULLFSYNC of every file) and about 0.2-0.4 s for Garfield++. No speed-up is claimed.

Decisions fixed from these numbers (TASK.md 10.2 step 9, 10.5):
- Input-copy threshold stays 256 MiB: copying the largest first-batch input (2 MB) costs no measurable time; larger
  inputs are APFS clones (own inode) where available.
- Foreground / background: both first-batch runs finish in under 5 s with budget timeouts of 120 s; budget + 60 s is
  below the host's 10-minute foreground limit, so they run in the foreground; a capability whose budget + 60 s exceeds
  that limit runs in the background and is polled with `inspect --view state` no more than every 30 s.
