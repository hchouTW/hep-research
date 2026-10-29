#!/usr/bin/env python3
"""Within-case permutation test with the output as the unit (runbook C3.6).
Input JSON: {"cases": {"<case_id>": {"baseline": [s1, s2, s3], "candidate": [s1, s2, s3]}, ...}}
where each s is the number of gold items held in one output (undeterminable counted as not held).
Output JSON: T, one-sided p for candidate > baseline and for baseline > candidate, leave-one-case-out check.
Exact enumeration of all within-case re-splits (C(6,3)=20 per case; 8,000 for 3 cases)."""
import itertools, json, math, sys

def case_stats(base, cand):
    pool = list(base) + list(cand)
    total = sum(pool)
    # statistic of one split = sum(candidate part) - sum(baseline part) = 2*sum(candidate part) - total
    return [2 * sum(pool[i] for i in idx) - total for idx in itertools.combinations(range(len(pool)), len(cand))]

def p_value(per_case, observed, direction):
    dist = {0: 1}  # exact distribution of the sum, by convolution over cases
    for stats in per_case:
        new = {}
        for t, w in dist.items():
            for s in stats:
                new[t + s] = new.get(t + s, 0) + w
        dist = new
    n = sum(dist.values())
    if direction > 0:
        return sum(w for t, w in dist.items() if t >= observed) / n
    return sum(w for t, w in dist.items() if t <= observed) / n

def analyse(cases):
    ids = sorted(cases)
    obs = {c: sum(cases[c]["candidate"]) - sum(cases[c]["baseline"]) for c in ids}
    per = [case_stats(cases[c]["baseline"], cases[c]["candidate"]) for c in ids]
    T = sum(obs.values())
    top_up = max(ids, key=lambda c: obs[c]); top_down = min(ids, key=lambda c: obs[c])
    return {"T": T, "per_case": obs,
            "p_candidate_better": p_value(per, T, +1), "p_baseline_better": p_value(per, T, -1),
            "leave_one_out_up": {"removed": top_up, "remaining_T": T - obs[top_up], "positive": T - obs[top_up] > 0},
            "leave_one_out_down": {"removed": top_down, "remaining_T": T - obs[top_down], "negative": T - obs[top_down] < 0},
            "n_assignments": math.prod(len(s) for s in per) if per else 1}

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    print(json.dumps(analyse(data["cases"]), indent=1))
