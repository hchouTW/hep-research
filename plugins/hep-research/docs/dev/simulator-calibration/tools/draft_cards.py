#!/usr/bin/env python3
"""Draft the phase task cards and gate-record templates from Part B (§17 rows, §8.7 rows) and the decision index.
Usage: python3 -I tools/draft_cards.py   (run from the package root, after tools/build_decision_index.py)
Writes drafts/simcal-tasks/phase-<n>.md and drafts/simcal-gates/phase-<n>.md. The §17 text and the §8.7 rows are copied
verbatim; the per-phase lists of scripts and test sections below are the drafter's reading (marked Inferred in the cards)
and are refreshed from Part B in phase 0 (simcal-task.md, Section E9)."""
import json, os, re
SPEC = "simulator-calibration-v7.37.4-clean-en.md"
L = open(SPEC, encoding="utf-8").read().split("\n")
idx = json.load(open("simcal-decision-index.json", encoding="utf-8"))

def cells(line):
    t = re.sub(r"`[^`]*`", lambda m: m.group(0).replace("|", "\x00"), line).replace("\\|", "\x01")
    return [c.strip().replace("\x00", "|").replace("\x01", "\\|") for c in t.strip().strip("|").split("|")]

s17 = next(i for i, l in enumerate(L) if l.startswith("## 17."))
e17 = next(i for i, l in enumerate(L) if l.startswith("## 18."))
pre_end = next(i for i in range(s17, e17) if L[i].startswith("| Phase |"))
BUL17 = [l for l in L[s17:pre_end] if l.startswith("- ") or l.startswith("  - ")]
g4s = next(i for i in range(s17, e17) if L[i].startswith("**g4sim preconditions**"))
G4ROWS = [l for l in L[g4s:e17] if l.startswith("| ") and not l.startswith("| Item of this workflow") and not re.match(r"^\|\s*-{3}", l)]
G4PRE = [l for l in L[g4s:e17] if l.startswith("- ")]
ROW = {}
for i in range(s17, e17):
    m = re.match(r"^\| ([0-5]) ([^|]+) \|", L[i])
    if m:
        c = cells(L[i]); ROW[int(m.group(1))] = {"line": i + 1, "title": m.group(2).strip(), "content": c[1], "gate": c[2]}
s87 = next(i for i, l in enumerate(L) if l.startswith("### 8.7"))
e87 = next(i for i, l in enumerate(L) if l.startswith("## 9."))
T87 = []
for i in range(s87, e87):
    if L[i].startswith("| ") and not re.match(r"^\|\s*-{3}", L[i]):
        c = cells(L[i])
        if c[0] != "Threshold": T87.append((i + 1, c))

# Drafter's reading per phase (Inferred): scripts of §14 whose checks the §17 content delivers, and the §15 sections that test it.
PHASE = {
 0: {"scripts": ["`calib_chain.py` (DAG, injection-point split, candidate methods, P4)", "`calib_contract.py check` (contract rules of §5.2; in phase 0 only the declarations of the locking-stage checks, §17)",
                 "`calib_deps.py` (hash references, cycle checks, upstream roles from usage)", "`calib_use.py` (Appendix C decision table, rule 0 `incomplete`)",
                 "`calib_data.py` (raw-unit lineage, read events, failure records, reuse input of Appendix C.1)"],
     "homes": ["`contracts/` (the seven abstract-object schemas; contract, data release, plan and result schemas; §13)"],
     "tests": ["Appendix C exhaustive tests (with the reference implementation `calib_use_decision_table.py`, `c5279adf…`)", "§15.3.1 (P4)", "§15.3.2", "§15.3.3", "§15.3.11", "§15.3.12", "§15.3.13",
               "§15.3.14 (with hand-written decision-record stubs, §17)", "§15.3.15", "§15.3.17 (dependency and use rules)", "§15.3a (phase-0 cases: lineage, failure records, acyclic ids, `incomplete` aggregation)"],
     "out": ["Any simulation of the toy detector (phase 1); the locking-stage checks that need model quantities (phase 2, §17)", "`calib_validate.py` behavior beyond the grade function (phase 2, §17)", "Every g4sim item (phase 3 and later)"],
     "risks": ["D5 and D11 need the author before this phase (index)", "The reference implementation at `c5279adf…` is not in the package (`simcal-task.md`, Section E7, item 2)"]},
 1: {"scripts": ["`calib_reweight.py` (weights; the weight formula of §3.6)", "`calib_kernel_check.py` (P0)", "`calib_contract.py preflight` (A0)",
                 "`calib_design.py` (P2; P5 with feasibility and the final method; Sobol design points and P6 held-back set, D80)", "`calib_emulator.py` (only the P6 interface stub)"],
     "homes": ["`core/calibration/` (engine home, hep-statistics; §13)"],
     "tests": ["§15.3.1 (A0, P0, P2, P5; the weight formula of §3.6, reweighting and rerun agree)", "§15.3.9 (MC-noise items of P5)", "§15.3.16 (the P0 cases)", "§15.2 (reweighting and rerun agree)", "§15.1 (toy detector simulation)"],
     "out": ["The joint likelihood, P3, P7, G1–G9 and validation (phase 2)", "The surrogate model beyond the P6 stub (phase 3)"],
     "risks": ["D37, D41 and D42 need the author before this phase (index)", "Several §8.7 values of this phase are design values: results carry `provisional-thresholds` until calibrated"]},
 2: {"scripts": ["`calib_likelihood.py`", "`calib_fit.py` (G1, G2, G3, G6, G7; locally linear toys)", "`calib_interval.py`", "`calib_identify.py` (P3, G5)", "`calib_closure.py` (G8)", "`calib_reweight.py` (G4)",
                 "`calib_shift.py` (P8, G9)", "`calib_validate.py`", "`calib_propagate.py` (principal components of the joint posterior, ξ versions)",
                 "`calib_design.py` (P7; Σ_boot and b_J of P5, §17)", "`calib_contract.py check` (calls the locking-stage checks of §17; the N_d,c recheck at θ̂, D21; the formal P7 check)", "`calib_data.py` (the locking-stage checks of §17)"],
     "homes": ["`core/calibration/`; reuses `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py` (§13)"],
     "tests": ["§15.3.1 (P3, P7, G1–G8, P8, G9)", "§15.3.4–§15.3.10", "§15.3.13", "§15.3.14 (retested with real decision records, §17)", "§15.3.16 (the cases of phase-2 gates)", "§15.3.17",
               "§15.3a (phase-2 cases: inference flags, G7 rank, general response, power lower bound, propagation packages, pass/fail summaries of weighted MC)"],
     "out": ["G4-L (phase 5)", "The g4sim event-interval check (phase 3, §17)"],
     "risks": ["25 Appendix D entries need the author before this phase (index); D68 is decided together with D3 and §19-14.1f (A1)", "Most §8.7 rows belong to this phase: calibrate each before the gate run that uses it, never on the gate run itself"]},
 3: {"scripts": ["`calib_emulator.py` (surrogate training set, P6, V_emu)", "`adapters/geant4/assets/g4sim_calib_eval.py` (new, §7.1)", "`calib_chain.py` (candidate methods from §11.4 Table 2)",
                 "`calib_contract.py check` (the masked-hash model identity, added to the checker in phase 3, §17; the PDE-split contract checks, §14)", "`calib_likelihood.py` (the map term U(θ)φ_map, §14)",
                 "`calib_design.py` (g4sim support and recording levels, §6.1; event-interval check; seeds of the mapping runs; θ-noise item of P5; efficiency-map and PDE-split checks of §6.6–§6.7)",
                 "`calib_kernel_check.py` (P0 with k_B on the synthetic ZDC fixture)", "`calib_propagate.py` (efficiency-map bases, joint-pattern replicas)"],
     "homes": ["`adapters/geant4/` (evaluator; §13)", "g4sim modules used: `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`), `adapters/geant4/assets/`"],
     "tests": ["§15.3.1 (P6; P0 (k_B))", "§15.3.16 (the cases of the synthetic ZDC fixture and P6)", "§15.3.19 (g4sim binding)",
               "§15.2 (g4sim items: synthetic ZDC, common random numbers, efficiency map φ, PDE split, map varies with θ, RICH replica)", "§15.3a (phase-3 cases: efficiency-map basis and g4sim model identity)", "G8 for the three-method combination (§17)"],
     "out": ["Dependency-graph invalidation, conditions export and specialization documents (phase 4)", "Learned density ratios and G4-L (phase 5)"],
     "risks": ["D6, D83, D84, D85 and four deferred §19 items need the author before this phase (index)", "Geant4 was not run for the PDE split's evidence; repeat with Geant4 transport (§15.2)",
               "g4sim preconditions of §17: S7 is merged with gate 3 (TR yield) a recorded gap and the RICH replica not yet expressed (`docs/dev/geant4-architecture/g4sim-gates/S7.md`); read each stage's gate record, not only its status"]},
 4: {"scripts": ["`calib_deps.py` (upstream invalidation, change of simulation identity, §10.3)", "`calib_propagate.py` (conditions-database export, feedback into g4sim, §10.4)", "`calib_use.py` (offline check of `source_of_facts` on exported snapshots and overlays, §10.4)", "`calib_contrib.py` (contribution decomposition)"],
     "homes": ["hep-detector `simulation-calibration/` (the eight specialization documents and the domain card; §13; new)"],
     "tests": ["§15.3.17", "§15.3.18 (contribution decomposition)", "§15.3.19 (g4sim binding)"],
     "out": ["Extensions of phase 5"],
     "risks": ["Five deferred §19 items need the author before this phase (index): §19-1, §19-4, §19-g6, §19-g7, §19-g8", "Specialization must not require modifying the generic layer (§17 gate)"]},
 5: {"scripts": ["`calib_reweight.py` (G4-L)", "the learned density-ratio path (§6.2; hep-ml)", "partial pooling and the marginal-likelihood form of V_model (§5.4)"],
     "homes": ["`core/calibration/`; hep-ml for the learned density ratio (§13)"],
     "tests": ["the negative tests of each extension (§15.3)", "the gates of phases 0–4 unchanged (§17)"],
     "out": ["Anything that changes the gates of the first four phases (§17)"],
     "risks": ["The §19 items deferred to phase 5 (§19-12, §19-14; tagged \"blocks no phase\") need the author before they are implemented (index)", "§19-9 is split: its C++ density-kernel part blocks phase 3, its classifier/SBI-boundary part is deferred to phase 5 (index lists it under phase 3); it needs the author before this phase too"]},
}
REPO = ("Confirmed in hep-research `main` at 5c2d1c7 (0.65.1): `contracts/` with `validate.py` and `schemas/`; `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py`; "
        "`core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`); `core/partition/` (`states.py`, `campaign.py`); "
        "`adapters/batch-schedulers/batch_campaign.py`; `skills/hep-computing/scripts/lint_task.py`. Not present yet (to be created by this workflow): `core/calibration/`, "
        "every `calib_*.py` script, `adapters/geant4/assets/g4sim_calib_eval.py`, hep-detector `simulation-calibration/`, `docs/dev/simulator-calibration/`.")

def items(n):
    need, other, acc = [], [], []
    for r in idx["appendix_D"] + idx["section_19"]:
        if not re.search(rf"\bphase {n}\b", r["blocks"] or ""): continue
        label = r.get("item") or f"{r['name']} (§19)"
        if r["status"] == "open":
            (need if r["kind"].startswith("needs the author") else other).append(f"{label} (line {r['line']}; {r['kind']})")
        else:
            acc.append(f"{label} (line {r['line']}; {r['status']})")
    return need, other, acc

def phases87(col):
    m = re.match(r"\s*([0-9](?:\s*,\s*[0-9])*)", col)
    ph = {int(x) for x in re.findall(r"[0-9]", m.group(1))} if m else set()
    ph |= {int(x) for x in re.findall(r"\(([0-9]) for ", col)}
    return ph
def t87(n):
    out = []
    for ln, c in T87:
        if n in phases87(c[-1]):
            out.append(f"- §8.7 line {ln}: **{c[0]}** — design value: {c[1]} — calibration: {c[2]} — phase column: {c[-1]}")
    return out

os.makedirs("drafts/simcal-tasks", exist_ok=True); os.makedirs("drafts/simcal-gates", exist_ok=True)
for n in range(6):
    r, p = ROW[n], PHASE[n]
    need, other, acc = items(n)
    card = [f"# Simulator calibration phase {n}: {r['title']}", "",
            "## Background", "",
            f"Phase {n} of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line {r['line']}). "
            "This is a **draft** written with the task package of 2026-11-10: phase 0 refreshes it from Part B and `simcal-decision-index.md`, lints it and registers it before any run a threshold judges (`simcal-task.md`, Sections E4 and E9). "
            "The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.", "",
            "This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.", "",
            "## Objective", "", "#### Goal", "",
            f"Deliver the content of phase {n} of §17 so that its gate holds: {r['gate']}", "",
            "## Scope", "", "### In Scope", "", "#### Scope checklist", "",
            "**Content (§17, verbatim)**", "", f"- [ ] {r['content']}", ""] + (
            ["**Placement bullets of §17 (verbatim; they place work in phases 0 and 2)**", ""] + BUL17 + [""] if n in (0, 2) else []) + (
            ["**g4sim preconditions of §17 (verbatim; the rows this phase's content uses apply)**", ""] + G4PRE + ["", "| Item of this workflow | Required g4sim stage | Deliverable |", "| --- | --- | --- |"] + G4ROWS + [""] if n in (3, 4) else []) + [
            "**Scripts and homes (Inferred from §13, §14 and the content)**", ""] + [f"- [ ] {x}" for x in p["scripts"] + p["homes"]] + [
            "", "**This phase's tests (Inferred; refresh from §15)**", ""] + [f"- [ ] {x}" for x in p["tests"]] + [
            "", "**Common checks**", "", "- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.", "",
            "### Out of Scope", ""] + [f"- {x}" for x in p["out"]] + [
            "", "## Repository Context", "", REPO, "",
            "## Technical Approach", "",
            "1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-" + str(n) + "`.",
            "2. Implement the §17 content through the scripts of §14, each check in exactly one script; follow §14's conventions (JSON output, exit codes 0–3, the standard library plus NumPy/SciPy).",
            "3. Add each test of this phase before the gate run, and show that each negative test is caught.",
            "4. Calibrate each §8.7 value of this phase as its row says, register it, then run the gates.", "",
            "## Deliverables", "", "#### Deliverables", "",
            "- Create the scripts and modules listed in the scope checklist that do not exist yet (Repository Context), with their tests.",
            f"- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-{n}.md`, from the gate-record template of the task package.",
            "- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.", "",
            "## Acceptance Criteria", "",
            "#### Decisions this phase depends on", "",
            "Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1):", ""] + ([f"- {x}" for x in need] or ["- none"]) + [
            "", "Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:", ""] + ([f"- {x}" for x in other] or ["- none"]) + [
            "", "Accepted or decided items that this phase implements (their text in Part B is normative):", ""] + ([f"- {x}" for x in acc] or ["- none"]) + [
            "", "#### Thresholds and test designs", "", f"**Gate (§17, verbatim)**: {r['gate']}", "",
            "**§8.7 rows of this phase (verbatim)**:", ""] + (t87(n) or ["- none"]) + [
            "", "Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.", "",
            "## Validation", "", "#### Environment", "",
            "- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.",
            "- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).", "",
            "#### Risks and stop points", ""] + [f"- {x}" for x in p["risks"]] + [
            "", "#### Execution log", "", "- (filled in during the phase)", "",
            "## Open Questions", "",
            "- Requires confirmation: the directory of the `calib_*.py` scripts; Part B names the scripts (§14) but not their folder (`simcal-task.md`, Open question 6).",
            "- The decisions under \"Needs the author\" above.", "",
            "## References", "",
            f"- Part B §17 (line {r['line']}), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.",
            "- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).", ""]
    open(f"drafts/simcal-tasks/phase-{n}.md", "w", encoding="utf-8").write("\n".join(card))
    gates = [g.strip() for g in re.split(r";\s+", r["gate"]) if g.strip()]
    rec = [f"# Simulator calibration gate record: phase {n}", "",
           "Template. Fill in inside the phase's worktree (`simcal-task.md`, Section E6).", "",
           "| Field | Value |", "| --- | --- |",
           f"| Phase | {n} ({r['title']}) |", f"| Worktree | `../hep-research-simcal-phase-{n}` |", f"| Branch | `simcal/phase-{n}` |",
           "| Commit |  |", "| Task-card SHA-256 (as registered) |  |", "| Environment |  |", "| hep-research and g4sim versions |  |", "| Date |  |", "",
           "| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |", "| --- | --- | --- | --- | --- |"]
    rec += [f"| {g.replace('|', '/')} |  |  |  |  |" for g in gates]
    rec += ["", "## This phase's tests", "", "| Test (§15) | Kind | Caught / passed | Evidence |", "| --- | --- | --- | --- |", "|  |  |  |  |", "",
            "## This phase's thresholds (§8.7)", "", "| Row | Calibrated value or `provisional-thresholds` | Evidence |", "| --- | --- | --- |"]
    rec += [f"| line {ln}: {c[0].replace('|', '/')} |  |  |" for ln, c in T87 if n in phases87(c[-1])] or ["| none |  |  |"]
    rec += ["", "## Review (Section E4, step 10)", "", "- Reviewer, date, findings and their resolution:", "", "## Open items carried to the next phase", "", "-", ""]
    open(f"drafts/simcal-gates/phase-{n}.md", "w", encoding="utf-8").write("\n".join(rec))
print("drafted", sorted(ROW))
