# T07 diagnosis: vertex pull z tail, fixture 7002 stratum 9 (evaluation attempt 1, block 11)

> Copy of the ledger file `<private>/worktree/.superpowers/sdd/finish-plan/t07-vz-diagnosis.md` (git-ignored, SHA-256 `af11380e1d13a5b4199c36b2e6d726cb7930b6a959336c0a5f4591ce84afed55`), copied into the tracked records on 2026-11-14 (G3) because `decisions.md` cites it. Content unchanged below this note; it held no absolute host path. Relative paths such as `evidence/...` and `jobs/...` are under `<private>/`.

Status: **readings done (block 2), block-1 job drafted, not submitted.** Development data only. Nothing in the worktree changed but this file. No recipe, frozen file, threshold or configuration changed anywhere; no candidate change is coded, only described (section 4). No commit, no push, no Slurm submission, no subagent, no network.

Inputs read from block 11: the scored record `evidence/evaluation-b11/T07/scores/t07-score-7002-b11-s9.records.jsonl` and `evidence/evaluation-b11/T07/summary/7613452/summary.log`, nothing else. Block-11 scoring was not redone.

Frame: the scoring's global ACTS frame is x = fixture z (beam axis), y = u (bending), **z = v** (non-bending, the axis along which the fixture separates vertices; t07_evaluation_scoring.truth_position). So "vertex pull z" is the pull along the vertex-separation axis.

Stratum 9 = momentum bin 3 ([12, 24) GeV), occupancy o1: 6 tracks, 2 vertices of 3 tracks, 100 noise hits per plane. The fixture has no material, so the vertex resolution in v does not depend on momentum: strata 0, 3, 6, 9 are replicas for this pull.

## 1. Readings available now (step 1)

### 1.1 The block-11 record

Vertex pull z, 18,907 far primary vertices in 9,600 events: centre +0.0060, width (sigma_68 − 1) +0.0080, both pass; mean +0.011, **rms 1.079**; tail k 200, 1.058 %, DEFF_hat 1.002, U 1.189 % > 1 % (step 4 fail). Same bin, x: tail 0.72 % (pass), rms 1.036; y: 0.25 %, rms 1.003. Core is Gaussian, the excess is in the tail only.

### 1.2 The Freeze-B run on block 2 (job 7585954)

The Freeze-B run scored no pulls. I scored the vertex pulls from its kept records and truth files (`noise-b2-s*.record`, `.t07truth`, `clean-b2-s*`) with the scoring module's own section-7 functions (`owners_of`, `track_event`, `vertex_event`, `truth_position`, `is_near`; core `trimmed_centre`, `sigma_68`), in a reading-only Python pass on login (`py313 -I -B`, nice, about 3 min CPU in all). Script: `jobs/t07-vz-diag/vz_diag.py`; logs and helpers in `jobs/t07-vz-diag/b2-reading/`. Noise bins 12,000 events (9,600 far), clean bins 3,000 (2,400 far).

| Bin | n | centre | sigma_68 | rms | tail | U (v4 5.2, 95 %) |
| --- | --- | --- | --- | --- | --- | --- |
| noise s9 | 18,921 | +0.003 | 1.011 | 1.078 | **0.909 %** (172) | **1.031 % (above L)** |
| noise s6 | 18,919 | +0.000 | 1.004 | 1.060 | 0.830 % | 0.947 % |
| noise s7 (o2) | 19,182 | −0.013 | 1.001 | 1.028 | 0.433 % | 0.519 % |
| noise s8 (o3) | 28,797 | −0.011 | 1.007 | 1.013 | 0.351 % | 0.414 % |
| noise s10 (o2) | 19,187 | +0.009 | 1.003 | 1.011 | 0.323 % | 0.399 % |
| noise s11 (o3) | 28,798 | +0.012 | 1.012 | 1.014 | 0.333 % | 0.395 % |
| noise s0, s3 (o1) | 18,922, 18,910 | +0.013, +0.004 | 1.003, 1.005 | 1.060, 1.069 | 0.814 %, 0.841 % | 0.930 %, 0.959 % |
| clean s9 | 4,736 | −0.016 | 1.015 | 1.050 | 0.676 % | 0.971 % |
| clean s6, s3, s0 (o1) | 4,744, 4,731, 4,730 | | 1.003, 1.008, 1.009 | 1.066, 1.073, 1.079 | 0.822 %, 0.930 %, 0.655 % | 1.073 %, 1.194 %, 0.972 % |
| clean s7, s10 (o2); s8, s11 (o3) | 4,795 to 7,200 | | 0.988 to 1.012 | 0.993 to 1.026 | 0.29 to 0.50 % | 0.55 to 0.81 % |

Pooled o1 z tail: noise 642 / 75,672 = **0.848 %** (95 % CP 0.794 to 0.905 %); clean 146 / 18,941 = 0.771 % (0.669 to 0.884 %). o2 and o3: 0.29 to 0.50 %.

Development block 1 said the same before Freeze B (job 7524096, d1-stage7b-reading.md, 3,000 events per bin): far z tails at o1 clean 0.55, 0.74, 0.57, 0.91 % and noise 0.59, 1.08, 0.87, 0.93 % (strata 0, 3, 6, 9); o2 0.23 to 0.54 %; o3 0.17 to 0.38 %. Its P5 "held" against a limit that was not the gate's.

### 1.3 Outlier or consistent?

**Consistent with block 2. This is an o1 property of both fixtures, not something specific to stratum 9 or to noise.**

- Against block-2 s9 (0.909 %), block 11's 1.058 % is +1.5 sigma (binomial difference). The rms values agree (1.079 against 1.078).
- Against the pooled o1 noise rate (0.848 %) it is high: P(k ≥ 200 | n 18,907) = 0.0013 per bin. But failing only needs k ≥ 167 (pass at 95 % iff k ≤ 166 at n ≈ 18,900).
- At the block-2 rates a single noise o1 bin passes with probability 0.68, a clean o1 bin about 0.96. All 8 o1 bins pass together with probability about 0.2. **So under the frozen recipe, a T07 fail in some o1 bin was the likely outcome.** On block 2 the Freeze-B run itself already reads above L in noise s9 (U 1.031 %), and in clean s3 and s6 at a quarter of the size. Nobody saw this, because that run scored no pulls.
- v4 5.4 sets the rate slack at 0.49 % for 9,600 events. The fixture plus recipe sits at about 0.85 % at o1, outside v4's "conditions for the 1 % family target". v4 says that outside those conditions "a correct recipe may fail".

### 1.4 What the block-2 tails are

From `b2-reading/b2-run.log` and `b2c.log`. "Pure" means summed weight from other truth vertices' tracks below 0.05 and from unmatched tracks below 0.05. "Merged" means the vertex holds the largest weight of two truth vertices.

| Bin | all tail | pure: n, tail | contaminated: share of vertices, tail, share of all tails | merged vertices: n, tail |
| --- | --- | --- | --- | --- |
| noise s9 | 0.909 % | 18,675, **0.300 %** (sigma_68 0.997) | 1.30 %, 47 %, **116 of 172** | 168, 61 % (103 of 172) |
| noise s6 | 0.830 % | 18,676, 0.209 % | 1.28 %, 49 %, 118 of 157 | 175, 59 % |
| noise s0 / s3 | 0.81 / 0.84 % | 0.241 / 0.225 % | 1.26 %, 46 / 49 % | 172 / 178, 58 / 56 % |
| clean s9 | 0.676 % | 4,680, 0.171 % | 1.18 %, 43 %, 24 of 32 | 38, 55 % |
| clean s6 / s3 / s0 | 0.82 / 0.93 / 0.66 % | 0.277 / 0.257 / 0.193 % | 0.99 to 1.40 % | 34 / 43 / 44 |
| noise s10 (o2) | 0.323 % | 0.205 % | 0.87 %, 14 %, 23 of 62 | 13 |
| noise s11 (o3) | 0.333 % | 0.315 % | 2.02 %, 1.2 %, 7 of 96 | 2 |

Further readings, noise s9:

- **Separation.** By truth Δv to the nearest vertex: tail 8.0 % at [5, 6) u_v, 4.2 % at [6, 7), 1.6 % at [7, 8), 0.52 % at [8, 10), 0.39 % at [10, 15), 0.25 % at [15, 25). Pure vertices at [5, 6) have 0 of 681 in the tail.
- **Track count.** By count of tracks at weight ≥ 0.5: tail 0.34 % at 3 tracks, 46 % at 4, 76 % at 5, 67 % at 6+.
- **Merged events.** All 168 merged vertices sit in events with one reconstructed vertex for two truth vertices. In 115 of them every foreign track's chi2 to the vertex is below the annealing cutOff 9. In 117, every foreign track's compatibility is below maxVertexChi2 18.42, the cut that, with useFastCompatibility, takes tracks out of the seed pool.
- **Covariance.** Fitted var_zz over the truth-slope linear model (d1-stage7b-reading 3.3), pure vertices: 5/25/50/75/95 % at 0.994 / 0.998 / 0.999 / 1.014 / 1.162. By var_xx quartile (poorly measured x along the beam), pure tails are 0.33, 0.27, 0.30 and 0.00 % (the top 1 %, 187 vertices).
- **Noise.** No vertex holds weight from an unmatched track (0 in every bin). Vertices with a heavy track that carries a noise hit: 3 in s9 (0 tails), 0 to 1 tails per bin elsewhere.

**Reading:** about 1.3 % of o1 vertices are a single AMVF vertex fitted between two truth vertices 5 to 7.5 u_v apart, holding both clusters' tracks. This is d1-stage7b-reading's class (a). It is matched to one of them by more than 50 % weight, so its z residual is about half the separation against the σ_z of 4 to 6 tracks, and it carries about two thirds of the tail. With those vertices excluded (a counterfactual, not a method), every o1 bin reads 0.17 to 0.30 %, against 0.27 % for a Gaussian.

## 2. Hypotheses and what each predicts (fixed before the block-1 job)

These were formed after the block-2 reading. The block-1 job is the independent test, on new events, with these predictions. Bins: 7002 s9, 7002 s6, 7002 s10, 7001 s9, each with 24,000 events (about 37,800 far vertices at o1). "Tail" below means the vertex pull z tail.

**(a) Association: vertices holding tracks of another truth vertex (the merge of close pairs).**
Predicts, in each o1 bin (7002 s9, s6, 7001 s9):
- all-vertex tail 0.6 to 1.1 %;
- pure-vertex tail at most 0.45 %, with pure sigma_68 within 0.98 to 1.02;
- contaminated vertices 0.8 to 1.8 % of vertices, carrying at least 55 % of the tails;
- merged vertices carrying at least 45 % of the tails, with at least 95 % of them at Δv < 8 u_v;
- tail at most 0.45 % over vertices with Δv ≥ 10 u_v.

In o2 (7002 s10): all-vertex tail at most 0.55 %, merged at most 0.2 % of vertices.

Refuted if, in any o1 bin, the pure tail exceeds 0.5 %, or contaminated vertices carry under 40 % of the tails.

**(b) Clean vertices with an underestimated z uncertainty (covariance: initialVariances 1e4, AMVF defaults, linearization).**
Predicts:
- pure-vertex tail above 0.5 %, or pure sigma_68 above 1.03;
- var_zz over the model below 0.97 at the median;
- a pure tail above 1 % in the top var_xx decile (where a weak x constraint, or the prior, would act);
- |model pull| tail below the fitted-pull tail among pure vertices.

Refuted as the cause if: pure tail ≤ 0.45 %, model ratio median within 0.98 to 1.02, and no var_xx band above 1 %. **Block 2 already refutes it** (pure 0.17 to 0.30 %, median ratio 0.999, top var_xx band 0 of 187). That is consistent with d1-stage7b-reading section 6: the 1e4 prior carries at most 0.12 % of the x information.

**(c1) Noise hits or fake tracks inside vertices.**
Predicts: tails enriched where a heavy track carries a noise hit or unmatched weight, and noise o1 tail exceeding clean o1 by more than 0.3 % absolute.

Refuted if such vertices carry under 10 % of the tails and the s9 noise−clean difference is within 2 sigma. Block 2: 0 to 1 tail per bin from them, no unmatched weight. Clean o1 (0.77 %) and noise o1 (0.85 %) agree within 1.3 sigma.

**(c2) Something specific to stratum 9 (momentum).**
v resolution is momentum-independent here (no material, straight v view). Predicts: s9 and s6 differ by more than 3 sigma. Not expected; block 2 has s9 and s6 within 0.8 sigma.

**(c3) Seed-pool and annealing lock-in.** A refinement of (a), the mechanism a method change would act on. Predicts:
- in at least 60 % of merged vertices, every foreign track has chi2 < 9 (cutOff) and compatibility < 18.42 (maxVertexChi2);
- every merged vertex lies in an event with fewer reconstructed than truth vertices.

The second point means the second cluster was never seeded, rather than seeded and then merged. Block 2: 115 and 117 of 168, and 168 of 168.

## 3. The block-1 job (step 3), drafted for the coordinator

- Script `jobs/t07-vz-diag/t07-vz-diag.sh`, sha256 `35750bedc813a50a2fb1aef3bece2c4aba3e2f230a7671486c32794eaf7698ef`.
- Manifest `jobs/t07-vz-diag/SOURCES.sha256`, sha256 `670d2190cad206a9ce9d75f605f06696a3231ba37fae5494cac9e3b225f79f59`, 64 files. It lists:
  - the 57 tracked files of `t07diag-tree/plugins/hep-research/adapters/acts-tracking/`;
  - the scoring module with its core, layout and package `__init__`s;
  - `jobs/t07-vz-diag/vz_diag.py` (`482b6e4d…`) and `rate_summary.py` (`42b49874…`).

  The script holds the manifest's hash; the manifest does not list the script.
- What it does, in order:
  1. Opening checks: the manifest's own hash, every entry in the live tree, the interpreter hash and Python 3.13.18, NumPy 2.4.6 and SciPy 1.17.1, libActsCore, job 7551619's binary record, the base commit, block 1.
  2. Snapshot: a clone of t07diag-tree at 659735cc, the manifest files copied over it and checked in the copy. The live tree is hidden by bwrap where that works, and every later step runs from the copy.
  3. Build from the copy, then binaries-equal: `acts_tracking_finder` and `t07_fixture_generator` must equal job 7551619's record, the binaries evaluated on block 11. Track and vertex sources also equal the Freeze-B summary's (`track_vertexing.cpp` 7f6209d5, `track_finding.cpp` a147d22e).
  4. Draws on **block 1 only**, event indices 5,000,000 to 5,023,999. Development used 0 to 2,999; the function refuses any other block. Bins 7002 s9, 7002 s6, 7002 s10, 7001 s9. The finder runs with the vertex step, in `t07_fake_rate.finder_command`'s form. A noise data file is deleted once the record and the truth both name its SHA-256.
  5. `vz_diag.py`, which refuses blocks 11 and 12 by header, then `rate_summary.py`: the v4 5.2 rule at 95 % and 99 %, labelled "DEV-READING", never a verdict.
- Resources (fixed): 4 CPUs × 4,000 MB, time limit 1:30:00, partition edr2-al9_short_serial, account ams.
  - Wall: predicted 15 to 30 min, refuted above 60. Estimate: build about 6 min at `-j 4` (337 s at `-j 1` in 7585954); draws about 3 min (o1 noise 12k events in 7585954: generate 7 s, find 13 s; o2 11 s and 35 s; doubled here); diagnosis about 6 min (35 s per 12k o1 bin on login).
  - MaxRSS: predicted at most 4 GB, refuted above 12 GB (build 1.5 GB in 7585954).
  - Evidence: at most 1.5 GB.
  - Cost: about 1 to 2 CPU-hours billed.
- Outputs go to `evidence/t07-vz-diag-<job>/`: per-vertex JSON, `vz-diag.log` and `rate-summary.log`. The truth files and records are kept so a later candidate job can use the **same block-1 events** as its baseline.

## 4. What would justify a method change, and what would mean accepting the failure

### Candidate changes (proposals only, none applied)

Each is chosen from the mechanism in 1.4 and (c3), not tuned against the gate. Each is one AMVF configuration item in `track_vertexing.cpp`, and each would be a new recipe hash under v4 3.4.

| Candidate | Mechanism it targets | Risk to measure |
| --- | --- | --- |
| C1: `maxVertexChi2` (seed-pool removal with useFastCompatibility) 18.42 → 9 | After one candidate absorbs both clusters, the second cluster's tracks (compatibility < 18.42) leave the seed pool, so the second vertex is never seeded: 168 of 168 merged events have one vertex. At 9, tracks 3 to 4.3 sigma away stay seedable, and the multi-vertex fit can then share them | More candidates, so more splits and ghosts (o3), and merge-check deletions. Vertex finding, assignment and o3 tails must not move |
| C2: annealing `cutOff` 9 → 4 | The midpoint fit is a fixed point while (Δv/2)² ≲ cutOff in single-track units, i.e. Δv ≲ 6 u_v at 9. That matches the merge share falling to 0 above 7.5 u_v. At 4 the fixed point ends near Δv 4 u_v, below the far range | Correct tracks are down-weighted more (a 2-dof chi2 above 4 for 13.5 % of tracks). That narrows the pulls (an M-estimator effect, so the width gate is at risk), lowers the weight-0.5 counts used by assignment and primaries, and lowers efficiency |
| C3: `tracksMaxSignificance` 5 → 3 | Fewer foreign tracks admitted into a new candidate | d1-stage7b found the IP proxy alone does not gate the merge (48 of 90). Efficiency loss for true tracks with large IP |

Not candidates:
- `doFullSplitting` and `maxMergeVertexSignificance`: they act on lost vertices (class b), not on tails.
- `initialVariances` and covariance changes: (b) is refuted.
- Any scale, offset or inflation from pulls: R12 forbids it, and it would be void.
- Any change to the matching, the far/near rule, the gate or L: those are Freeze A matters, not method.

### A principled change is justified only if all of these hold

1. The block-1 job confirms (a) and (c3) on new events, as predicted in section 2, and (b) and (c1) stay refuted.
2. One candidate, fixed before its run, is run in a second bounded block-1 job on the same events (5,000,000+, the same 4 bins plus o3 7002 s11 for ghosts). Against this job's baseline it shows:
   - o1 z tail pooled per fixture at most 0.50 %, with 95 % CP upper at most 0.55 %;
   - vertex finding: far lower bound still at least 0.97;
   - assignment: U at most 0.7 %;
   - centre within ±0.03 and sigma_68 within 0.97 to 1.03 in x, y and z;
   - o2 and o3 tails up by at most 0.1 % absolute;
   - no new not-positive-definite covariance, no failed event.

   The 0.50 % threshold comes from attempt 2's 99 % rule, which passes a bin iff k ≤ 157 at n ≈ 18,900. A true 0.50 % passes all 8 o1 bins with probability 1.000; 0.70 % passes them with 0.88; today's 0.85 % with 0.001.
3. Then: return to Freeze B (new recipe hash, Freeze-B run on block 5, the user's word), with that run scoring every T07 gate as a development reading. Attempt 2 follows at 99 %.

### Accept "T07 failed at attempt 1" if any of these holds

- (a) is refuted, i.e. the pure tail exceeds 0.5 %. Then the residual is covariance or linearization, and R12 forbids the obvious remedies.
- No candidate reaches 0.50 % at o1 without breaking a criterion of point 2.
- The only candidate that works needs a value picked by scanning against this tail; that would be tuning on the gate.
- The user declines a return to Freeze B. Without a change, attempt 2 at 99 % would fail with near certainty: P(all 8 o1 bins pass) is about 0.001 at 0.85 %.

In that case the record should name the cause: AMVF at ACTS defaults merges 3-track vertex pairs at 5 to 7.5 u_v, which the [5, 25) far range admits and v4 §17 already lists as "where confusion really happens".

## 5. Concerns

1. **The failure was foreseeable from records already on file.** Development job 7524096 read o1 z tails up to 1.08 %, and block 2 reads a fail-level U in noise s9 and in two clean o1 bins. The Freeze-B run scored no pulls. Any attempt 2 should have its Freeze-B run on block 5 compute every gate as a development reading before evaluation.
2. **The hypotheses were sharpened after reading block 2.** The block-1 job's predictions are what tests them. The block-2 numbers are labelled as development readings by the frozen definitions, not verdicts.
3. **The block-2 reading was a Python pass over evidence on login** (about 3 min of nice'd CPU, no test module, no build, no draw), as d1-stage7b-reading did. If the login rule is read strictly, the coordinator should know.
4. **Block 11's k = 200 sits in the upper tail** of the block-2 o1 rate (p = 0.0013 per bin; 1.5 sigma above block-2 s9 itself). It does not change the conclusion, since failing needed only k ≥ 167, but no block-11 events may be inspected to explain it.
5. **The scoring's primary rule counts a midway vertex as the matched truth vertex's measurement.** That is by the frozen definition, and changing it is a Freeze A matter, not a remedy.
6. **The job relies on build reproducibility.** It rebuilds from the snapshot and requires the hashes of job 7551619's binaries; a different hash fails before any draw. The binary hash depends on glibc and the CPU class only through the libm code path at run time (v4 2.1), not at build time.
7. **The vertex pass in `vz_diag.py` is new code.** Its pulls and primaries are `vertex_event`'s own output, called as `score_bin` calls it at the 50 % match. Its added columns (purity, Δv, model, chi2 and compatibility) have no unit test, and its counts have not been compared with a `score_bin` run on the same bin, because no scored block-2 or block-1 bin exists. It is a diagnostic tool, not part of any gate. A cheap check for the coordinator, if wanted: `score_bin` on one block-2 noise bin, comparing the z-tail count with `vz_diag`'s.

## Candidate stage (2026-11-13; the user chose "Test candidates on block 1")

Status: **C1 job drafted, not submitted. Pre-registration written and hashed before any candidate job.** No commit, no push, no submission, no subagent, no network. Development data only, nothing of blocks 11 and 12 read. The worktree's recipe and frozen files are untouched.

The candidates live only on branch t07/vz-diagnosis (t07diag-tree, uncommitted). In `track_vertexing.cpp` there are compile-time switches, inert unless defined: `T07_VZ_CANDIDATE` 1, 2 or 3 (C1, C2, C3), and `T07_VZ_TRACE`, which sets the AMVF finder's logger to VERBOSE on stderr and adds `T07VZ-EVENT` markers. Branch file sha256 `ab4e1d6c…`; the Freeze-B file is `7f6209d5…`.

### Job 7623497 (block 1, frozen recipe): (a) confirmed

The z tail in o1 reads 0.90 to 0.94 %, against 0.23 to 0.29 % for pure vertices. Contaminated vertices carry 70 to 75 % of the tails. Merged vertices sit at Δv < 8 u_v (355 of 356, 364 of 367, 321 of 323), which settles review M2.

vz_diag v2 run on 7623497's records shows two more things:
- **The x tail is also the merge.** Merged vertices have an x tail of 40 to 43 %; the rest 0.29 to 0.34 % (noise s9 0.74 % overall). This settles review I2a: removing merges should lower x too.
- **Merged vertices hold a median of 2 of the 3 foreign tracks.** One or more held foreign tracks have compatibility ≥ 9 in 151 to 182 of the 323 to 367 merged vertices per o1 bin, and two or more in only 20 to 23. These counts fix the C1 prediction.

### Review findings answered

- **I1 (same events).** The job regenerates each bin at first event 5,000,000 and refuses (exit 1, before any finder run) unless each data SHA-256 equals 7623497's: s9 7267e46a, s6 b94aaa7b, s10 a57e3dc2, clean s9 6aae1dfc. It also refuses before any draw unless the CPU model is 7623497's (AMD EPYC 9645). The baseline is rerun in the same job and must equal 7623497's records byte for byte.
- **I2 (criteria).** These live in `jobs/t07-vz-diag/t07-vz-candidates-prereg.md`, sha256 `ac3cd0b3789aec597d981fc02e95c986c3cf4091bb43110c89060da8a28e444a`. The rules:
  - order C1, C2, C3, stopping at the first that meets all criteria;
  - at most three, no scan, no other knob;
  - K1 to K7 as in section 4, plus x and y bounds (K3: not above the baseline's 95 % upper bound, and an attempt-2 pass probability ≥ 0.95);
  - the attempt-2 cut-off computed per bin from n scaled to 9,600 far events, the bin's DEFF_hat and `core.bounds_at` at 99 %.

  `vz_compare.py` reads the criteria from the file's JSON block and refuses any other hash.
- **I3 (seeded or discarded).** The tb and tc runs are traced. `vz_trace.py` classifies each lost far truth vertex: never seeded; seeded, not good (isGoodVertex); seeded, good, not kept (keepNewVertex, i.e. the contamination limit or the merge check, which the log does not separate); or kept, then absent. The prediction for the baseline is "seeded, not good" in at least 50 % of lost vertices in merged events, refuted if "never seeded" or "not kept" is the largest class. The C1 rationale's "never seeded" (diagnosis 2 (c3)) is treated as unshown until this reads.

### The C1 job

- **Files.**
  - Script `jobs/t07-vz-diag/t07-vz-c1.sh`, sha256 `b4a6367edc8f02581a572293a521bf29e835946c416de0cfeed95242fb6f9a2d`.
  - Manifest `SOURCES-c1.sha256`, sha256 `50cd6d61a6d1441d974fe790d8d6437264b6a560be7425ecdcb8924e10eb6003`, 68 files. It lists acts-tracking with the branch's `track_vertexing.cpp`, the scoring module with core and layout, `vz_diag.py` v2 `a9bc0936…`, `vz_gates.py` `7e0bd8ac…`, `vz_trace.py` `72c95c5a…`, `vz_compare.py` `add5c963…`, `vz_checks.py` `8db64b42…`, and the pre-registration.
- **Bins.** Block 1, first event 5,000,000: 7002 s9, s6, s10 and 7001 s9 at 24,000 events (7623497's events), and 7002 s11 (o3, new) at 12,000.
- **Builds from the snapshot.**
  - b0, no switch: full build. The generator must equal 7551619's `9c6598…`. The finder's hash against `550d96…` is a reading.
  - tb (trace), tc (trace + C1), pc (C1): the finder only.
- **Runs.** tb and tc on every bin; pc on the four reference bins.
- **K8 checks.** tb equals 7623497's records; pc equals tc; tc's finding lines equal tb's; no failed event or vertexing defect.
- **Scoring.** The frozen `score_bin` on a DevelopmentBin, with the attempt-2 replays and evaluation-size margins (`vz_gates.py`), then `vz_trace.py`, `vz_diag.py` v2 and `vz_compare.py`.
- **Resources.** 4 CPUs × 4,000 MB, 3:00 limit. Wall 40 to 90 min, refuted above 150. MaxRSS ≤ 6 GB, refuted above 14. Evidence ≤ 3 GB.

**C1 is predicted not to meet K1.** The prediction: merged vertices fall 15 to 50 %, o1 z tail 0.60 to 0.85 %, and o3 splits at most 2 × the baseline + 5. If the trace reads as predicted, the job's main value is the mechanism, and C2 follows by the pre-registered order.

**Pre-flight on login** (reading-only Python over 7623497's outputs, about 3 min): `vz_gates.py` on all four reference records reproduces job 7623497's tails exactly (s9 351/37,845, clean s9 342/37,865). `vz_checks.py` and `vz_compare.py` run on baseline against itself with s11 as a copy of s10, and `vz_trace.py` on a synthetic trace. **By the pre-registered criteria the baseline itself fails K1 and K2 in every o1 bin, and K3 on x in noise s9** (attempt-2 pass probability 0.935 against the 0.95 minimum). So the criteria are not met by doing nothing.

### Concerns (candidate stage)

1. **The trace's ACTS message format is inferred, not seen.** The strings come from libActsCore. The parser accepts 1/0 or true/false, and finding no seed line at all is a crash (exit 3), not a reading. The keepNewVertex result does not separate contamination from the merge check.
2. **Tracing is assumed to change no number.** The job checks it, since tb must byte-equal 7623497's records. If it fails, K8 fails and the run does not count as a trial.
3. **The branch source with no switch may not reproduce `550d96…` bit for bit.** That is a recorded reading; record equality is the binding check.
4. **`jobs/t07-vz-diag/SOURCES.sha256` (7623497's manifest) no longer verifies against the live `vz_diag.py`,** which is now v2. 7623497's snapshot copy of v1 is in its evidence tree; that job is not to be rerun.
5. **o3 has a single new bin at 12,000 events, without a 7623497 reference.** Its baseline is this job's traced run.
6. **C1 is predicted to fail.** The pre-registered order still runs it first. A failed C1 costs about 1 hour and gives the I3 reading that decides whether the C2 rationale holds.

### C1 result (job 7623624) and the instrument repair

**C1 is a valid trial (K8 met, 6/6) and does not meet the criteria.** It fails:
- K1: o1 pooled z tail 0.888 % noise (673/75,778) and 0.849 % clean, against a 0.50 % maximum;
- K2: attempt-2 pass probability 0.18 to 0.40.

K3 to K7 are met. Under the pre-registered order, C1 stands as trial 1 of 3.

The no-switch build reproduces the frozen finder `550d96…` exactly. Traced binaries: tb `2229612e…`, tc `7bcd1e87…`, pc `6e1db159…`.

**Predictions against outcome (pre-registration section 3):**

| Prediction | Outcome | Verdict |
| --- | --- | --- |
| o1 z tail 0.60 to 0.85 % | 0.881 % (noise s9), 0.895 % (noise s6), 0.849 % (clean s9) | Refuted on the high side in the two noise bins |
| Merged vertices fall 15 to 50 % | 356 → 301, 367 → 315, 323 → 272 (14 to 16 %) | At the low edge; refuted in s6 |
| o1 vertex finding +0.2 to 0.8 % | +0.13 to +0.15 % | Refuted low |
| o3 splits at most 2 × baseline + 5 | s11 15 → 125 (all events) | Refuted |
| K1 not met | Not met | Holds |

**The trace instrument failed in C1 and was repaired after C1.**
- Cause: at the levels this ACTS 48.2.0 build prints, AMVF logs exactly two lines per seeded candidate: "Vertex is good vertex: b" and "New vertex will be saved: b". It logs no seed-position line. The other strings I took from libActsCore are not emitted here.
- Repair: `vz_trace.py` v2 (`5264eab7…`) opens a candidate at each "good" line. It classifies a lost vertex by elimination, only in far events with exactly one lost truth vertex: the event's unsaved candidates are the attempts at it. Position-based attribution is kept for any future build that logs positions.
- Test: run on all ten real C1 traces (tb and tc, five bins). It parses every candidate, the number of saved candidates equals the final vertex count in every far event, and no lost vertex was left unclassified.
- **The pre-registration (sha256 `ac3cd0b3…`) stands unchanged.** Its text names no log-message format: only the classes "never seeded", "seeded but not good (isGoodVertex)" and "seeded, good, not kept (keepNewVertex)". The message strings were named only in `vz_trace.py` v1's docstring.

**Supplementary I3 reading, from C1's kept traces** (`jobs/t07-vz-diag/c1-i3-supplement/`). Lost far truth vertices in merged events, by elimination:

| Bin | Baseline: never seeded / good, not kept / not good | C1: never seeded / good, not kept / not good |
| --- | --- | --- |
| noise s9 | 238 / 66 / 51 (of 355) | 157 / 71 / 71 (of 299) |
| noise s6 | 255 / 66 / 45 (of 366) | 166 / 70 / 78 (of 314) |
| clean s9 | 220 / 60 / 43 (of 323) | 143 / 67 / 62 (of 272) |
| noise s10 (o2) | 22 / 0 / 14 (of 36) | 1 / 1 / 10 (of 12) |

- **The prediction "seeded, not good in at least 50 %" is refuted.** "Never seeded" is the largest class at 62 to 70 %, so the original reading in (c3), that the second cluster is never seeded, holds for about two thirds.
- Lost vertices outside merged events (about 190 per o1 bin, class (b)) are almost all "seeded, good, not kept". That is the z-only merge check or the contamination limit.
- C1 converts part of "never seeded" into seeded-but-rejected attempts, with few net recoveries. This is why it moved the tail so little.
- Caveat: elimination cannot tell an unsaved candidate aimed at the lost cluster from one at stragglers of the kept cluster.

### The C2 job (annealing cutOff 9 → 4), drafted, not submitted

- **Files.**
  - Script `jobs/t07-vz-diag/t07-vz-c2.sh`, sha256 `bf55f32adeb5f01b6ad74a82b38a9b6be87be62dbaba88e7c28881e439d10b9d`.
  - Manifest `SOURCES-c2.sha256`, sha256 `4f97c8aa41652197edaa93dfca9367d77a4ac892159b9d18cbc0127272861300`, 69 files. It is C1's manifest plus vz_trace v2 and `t07-vz-c2-predictions.md` (`e1a3346c…`).
  - Pre-registration hash checked: `ac3cd0b3…`.
- **Differences from C1.** CAND=2. Each traced run keeps its whole stderr gzipped, so no message can be filtered away again.
- **The same as C1.** Events checked by digest against 7623497, the CPU class check, tb byte-equal to 7623497's records, pc equal to tc, the frozen scoring, the criteria K1 to K8, and 4 CPUs × 4 GB with a 3:00 limit.
- **Predictions** (`t07-vz-c2-predictions.md`, fixed before the job):
  - o1 merged vertices fall 60 to 90 %;
  - the "never seeded" share falls below 40 %;
  - o1 z tail 0.35 to 0.60 %, so K1 is borderline, with no confident call either way;
  - z sigma_68 − 1 between −0.05 and 0.00, which puts K6 at risk;
  - vertex finding +0.3 to 1.2 %;
  - o3 splits at most 3 × baseline + 10;
  - wall 30 to 70 min.

### Concerns (after C1)

1. **The I3 classification is by elimination, without positions.** It is sound for o1 merged events, with one lost vertex and one kept, but not a positional proof.
2. **C1 multiplied o3 and o2 splits (s11 15 → 125, s10 31 → 75)** while staying within K7, since splits are not a criterion. A Freeze-B proposal of any candidate should read split counts.
3. **C2's main risk is pull width (K6)**, from down-weighting correct tracks.
4. **`SOURCES-c1.sha256` no longer verifies against the live `vz_trace.py`,** which is now v2. C1's snapshot keeps v1 in its evidence tree.

### C2 result (job 7624555, COMPLETED, 28 min 19 s, 2.1 GB): valid trial 2 of 3, criteria not met

K8 is met (6/6). Criteria:

| Criterion | Count | Detail |
| --- | --- | --- |
| K1 | NOT MET | o1 pooled z tail 0.691 % noise (520/75,201), 0.672 % clean |
| K2 | NOT MET, 2/3 | noise s9 0.982 against 0.99 |
| K3 | met, 6/6 | |
| K4 | NOT MET, 2/5 | o1 vertex finding fell 0.57 to 0.62 % in every o1 bin, against a largest drop of 0.5 %; o2 and o3 met |
| K5 | met, 5/5 | |
| **K6** | **NOT MET, 0/15** | sigma_68 − 1 from −0.041 to −0.080 on x, y and z in every bin, against ±0.03; the centres are fine |
| K7 | met, 6/6 | the tails fell |

C2 predictions (`t07-vz-c2-predictions.md`), scored:

| Prediction | Outcome | |
| --- | --- | --- |
| o1 merged vertices fall 60 to 90 % | rose: 356 → 381, 367 → 394, 323 → 346 | refuted |
| "Never seeded" share below 40 % | 54 to 55 % (206/380, 217/393, 190/346) | refuted |
| o1 z tail 0.35 to 0.60 % | 0.702, 0.681, 0.672 % | refuted (high) |
| z sigma_68 − 1 within −0.05 to 0.00 | −0.059, −0.066, −0.064 | refuted (narrower) |
| Vertex finding +0.3 to 1.2 % | −0.6 % | refuted |
| K1 borderline, no call | not met | |
| K6 at risk | failed everywhere | held |
| Assignment ≤ 0.7 % | met | held |
| o2 and o3 within K7 | met | held |
| o3 splits ≤ 3 × baseline + 10 | 15 → 19 | held |
| Wall 30 to 70 min | 28 min | below the range; not refuted by its "above 150" rule |

**Reading.** C2 lowered the tail by narrowing every pull, not by removing merges. Down-weighting correct tracks inflates the covariance against the scatter. Merges rose and vertex finding fell. This is a covariance distortion (an R12-style effect, though no constant comes from a pull), not a remedy.

### The C3 job (tracksMaxSignificance 5 → 3), the last pre-registered candidate, drafted, not submitted

- **Script and manifest.**
  - Script `jobs/t07-vz-diag/t07-vz-c3.sh`, sha256 `e4d35dad89b6cd4fbb75bcdcc4713927282f0cfe72893df247d68dd68cc69b8d`.
  - Manifest `SOURCES-c3.sha256`, sha256 `c82deb81e655717a88670c1335b7c23d991955d621ef38a5f1240bf4df8d3989`, 70 files: C2's plus `t07-vz-c3-predictions.md` `d27f0c5c…`.
- **Same as C2:** structure, events checked by digest against 7623497, the CPU class, the traced baseline byte-equal to 7623497's records, untraced C3 equal to traced C3, the frozen scoring, K1 to K8, the pre-registration hash `ac3cd0b3…`, and I3 from the whole stderr.
- **Predictions** (fixed in the hashed file):
  - o1 z tail 0.60 to 0.90 %, **K1 predicted not met**;
  - z sigma_68 − 1 within ±0.02 (K6 met);
  - merged vertices −50 % to +10 %;
  - "never seeded" 40 to 70 %;
  - vertex finding −1.0 to +0.3 % (K4 at risk);
  - o2 and o3 splits 1 to 5 × the baseline;
  - wall 25 to 60 min.

## For the user: what the three trials show about the mechanism

To be completed with C3's result. These statements hold whatever C3 gives.

1. **The tail is a reconstruction failure, not a covariance error.**
   - About 1.3 % of o1 vertices are one fitted vertex holding two truth vertices 5 to 7.5 u_v apart.
   - Those vertices carry about two thirds of the z tail and most of the x tail.
   - Pure vertices read 0.23 to 0.29 %, against 0.27 % for a Gaussian.
   - It is a property of AMVF at ACTS defaults on 3-track vertex pairs. The fixture's far range [5, 25) u_v admits those pairs, and v4 §17 already lists the regime.
2. **Most absorbed clusters are never seeded.**
   - About two thirds of the lost vertices in merged events were never seeded: the absorbing fit takes the second cluster's tracks out of the seed pool.
   - The rest are seeded and then rejected (not good, or not kept).
   - The lost vertices outside merges are seeded and then removed by AMVF's keep step (merge check or contamination).
3. **C1 and C2 each acted on one link of that chain without breaking it.**
   - C1 (keep more tracks seedable) turned some never-seeded cases into rejected attempts and removed only about 15 % of merges. Splits rose sharply.
   - C2 (a harder annealing cut) did not separate the clusters at all; merges rose. It lowered the tail only by shrinking every pull width below 0.94. That would trade a tail failure for a width failure, and is not a principled fix.
4. **What follows.** If C3 also fails, the pre-registered outcome stands: no method change is justified, and "T07 failed at attempt 1" stands. A remedy would need a change to how AMVF seeds or splits close 3-track clusters. That is a different method, or a Freeze A amendment of the far range, and both belong to the user. No combination of these settings and no other value is proposed: that would be a scan.

## Seed-finder study (prepared 2026-11-13, on the user's word; development only; T07 stays failed at attempt 1)

**Status: pre-registration written and hashed; S1 job drafted, not submitted.** The variant switch `T07_VZ_SEEDER` is on branch t07/vz-diagnosis only (uncommitted over b7a0cd18). The edit adds 37 lines and deletes none; every added line is inside an `#if` that is false by default.

- **Pre-registration:** `jobs/t07-vz-diag/t07-seed-prereg.md`, sha256 `3012f373c8f2d9e97b9db5a0f2fbe17ba25cc14c5c2ab468f47c8a08e62126ff`. It records the header facts (seeders, paths, lines, defaults), the truth reading, variants S1 and S2 with a null stop rule, the K1 to K8 criteria of `ac3cd0b3` unchanged, and S1's predictions.
- **S1 job:** `jobs/t07-vz-diag/t07-seed-s1.sh`, sha256 `a585707fe1317f5ac068e474bae707ef5ec06671f45c95ad5d27646c5a018818`. Manifest `SOURCES-s1.sha256`, sha256 `976af123c4a42955868b2c00d7fc5669fdd59c1cd21d3bed5780094cc44eef5f`, 69 files (branch `track_vertexing.cpp` `042225b4…`).
- The job has the C3 job's structure: digests against 7623497, the CPU class, traced baseline byte-equal to 7623497's records, traced and untraced S1 compared, frozen scoring, K1 to K8, the pre-registration hash, and the whole stderr for I3.

**The finding that shapes the study** (`jobs/t07-vz-diag/seed-reading/`, truth emulation on 7623497's o1 events):
- The current seeder, a GaussianTrackDensity of each track's own (d0, z0) covariance with no width parameter, already gives two peaks with the global maximum on a cluster in every merged event: 356 of 356 (noise s9) and 323 of 323 (clean s9).
- Merges occur at a z0 centre separation of median 5.4 u_v, against 6.4 for close pairs that did not merge. That is at tracksMaxSignificance 5.
- So the merge forms when the candidate admits tracks around a correctly placed seed, as C3 showed, not at seeding.
- A finer seeder is predicted null. S1 tests this. S2 runs only if S1 is not null.

**Concerns.**
1. The study is predicted null: the coordinator's premise (close clusters do not get separate seeds) is not supported at truth level. The emulation uses truth z0 with width u_v and ignores reco covariance and d0. S1 is the reconstruction-level test.
2. Whether a seed width (S2) reaches the fit when no vertex constraint is used is not stated in the installed headers; the AMVF source is not installed.
3. The variant code has not been compiled. A compile error stops the job before any draw.
4. The null rule is read from the job's diag logs (merged counts, z tail); no script prints it as a single line.

## Post-fit split study (2026-11-14; the user: "do T07: attempt 2 (a method change and a return to Freeze B)", method "Post-fit split test")

- **Pre-registration:** `jobs/t07-vz-diag/t07-split-prereg.md`, sha256 `d6151d34c9fa0b5e7ee6477983256d3fdd37098c06199859efff41f1e94ab47c`
  (hashed before any fixture run). **Deviation 1:** `t07-split-deviation-1.md` `e6bede816dc1311c0ce68d5f8626d3ba5ca712c0970722096102680e4cf0147e`
  (the rule recorded in the `vertex_fitter` value, since the record format fixes the configuration keys; rule, criteria and predictions unchanged).
- Method: AMVF vertices with >= 4 own tracks (weight >= 0.5); z0-sorted, cut at the largest gap; Billoir fits of one vs two vertices (time
  neutralised); split when Delta chi2 (3 dof) exceeds the quantile at 1e-3 / B(n), B(n) = 2^(n-1) - 1 - n. Switch `T07_VZ_SPLIT` (default 0 =
  frozen finder). Unit test `t07_split_test.cpp` c93c4dd2. Code `t07_vz_split.hpp` 7be3ac83, `track_vertexing.cpp` 096553c5.
- Job `t07-split.sh` cef676f7, manifest `SOURCES-split.sha256` 143a6e5f (72 files). Fresh review (jobs/t07-vz-diag/SPLIT-REVIEW.md): READY TO
  SUBMIT, 0/0/4/4. Predicted: K1 more likely not met (o1 z tail 0.45-0.70 %); if K1-K8 are met, a Freeze B return is put to the user.

### Split study result (job 7649462, COMPLETED, 34 min 7 s, 4.6 GB; JOB RESULT PASS = every step ran)

- Valid trial: K8 met (6/6), 0 failed vertexing events, 0 fit failures, 0 ndf mismatches.
- Criteria: K1 NOT MET (o1 pooled z tail 0.929 % noise, 0.898 % clean), K2 NOT MET (0/3), K3 5/6, K4 met (finding unchanged), K5, K6, K7, K8 met.
- The test barely acted: o1 bins tested about 4,450 vertices each and split 18 to 26 (0.4 to 0.6 %); merged vertices 354/364/321 against the
  baseline's 356/367/323 (down about 0.6 %). About 900 per bin had Delta above the 1 % point of chi2(3), but almost none passed the Bonferroni
  threshold (21.1 at 5 own tracks, 23.0 at 6). s11 split 61 of 33,721 (0.18 %, under the 0.5 % refutation).
- Predictions refuted: merges were to fall 45-80 % (refutation: less than 30 %); the z tail was to be 0.45-0.70 % (refutation: above 0.75 %).
  The pre-registered prediction "SPLIT does not meet all criteria" holds.
- Reading: with the threshold fixed for validity (alpha 1e-3 over every admissible partition), the z0-based two-group test has too little
  power on the fixture's merged 3+3 clusters at 5-7.5 u_v, where real vertices sit off the reference line and the z0 partition is degraded
  (the review's minor 3). Raising alpha or changing the partition rule now would be a value picked after seeing the result.
- Outcome by the pre-registration: one candidate, no second value; the study ends. "T07 failed at attempt 1" stands. No Freeze B return is
  proposed.
