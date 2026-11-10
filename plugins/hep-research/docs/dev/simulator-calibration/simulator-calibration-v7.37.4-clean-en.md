# Simulator parameter calibration workflow: abstract model, general architecture and specialization interface (v7.37.4 frozen version, clean edition)

**Nature of this file**: This file is the clean edition of the frozen version v7.37.4; its rules are the same as in v7.37.4, except for the changes settled by computation or by the plugin sources that Appendix E lists under "Changes from the computation, g4sim-binding and triage pass", "g4sim S7 (hep-research 0.63.0)", "Verification of acceptance and S7; §19-g9", "g4sim S8 and S9 (hep-research 0.65.0)" and "Verification of the D28 fixes and S8/S9"; each new rule among them is tagged in the body "(settled by computation, …; to be confirmed by the author)", or "(accepted by the author, 2026-11-09; source en/…)" for a requirement this workflow imposes because of the g4sim sources (tagged "(settled by plugin source, …; to be confirmed by the author)" until the author accepted these requirements on 2026-11-09, Appendix E, "Author's acceptance of 2026-11-09 (plugin-source rules, D28 choices, D86, D87)"); the other corrections to the g4sim binding (statements of plugin facts) are listed in Appendix E and are not tagged. The author's acceptance of 2026-11-09 (Appendix E, "Author's acceptance of 2026-11-09") made normative every class-1 proposal of `triage.md` except D68, together with the merges D13 → D63 and D64 → D22: these entries and §19 items begin "**Accepted by the author (2026-11-09).**", and their resolutions are written into the body; the tagged rules "(…; to be confirmed by the author)" are not affected by it. The author's decision of 2026-11-09 on D28 (Appendix E, "D28 revision (author decision of 2026-11-09)") made the revision of D28 proposed in `research-D28.md` normative in the same way: D28 begins "**Accepted by the author (2026-11-09; revised 2026-11-09 after en/research-D28.md).**", and its new P5 bounds are design values of §8.7. Its independent verification (`d28-verify.md`) was applied as normative text in the same way (Appendix E, "Verification of the D28 revision"); the three choices that this introduced beyond `research-D28.md`, first tagged as new choices of the D28 verification to be confirmed by the author, were accepted by the author on 2026-11-09 and are tagged "(choice of the D28 verification, accepted by the author, 2026-11-09; source en/d28-verify.md …)". The g4sim S8 and S9 check against the hep-research v0.65.0 sources (Appendix E, "g4sim S8 and S9 (hep-research 0.65.0)") added two proposals, written in place: the model identity of alignment overlays and condition snapshots (§5.1, D86) and the statistical roles of conditions and alignment (§11.4, D87). The author accepted both on 2026-11-09 (Appendix E, "Author's acceptance of 2026-11-09 (plugin-source rules, D28 choices, D86, D87)"): D86 and D87 begin "**Accepted by the author (2026-11-09).**", and the texts in place are tagged "(accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md …; D86)" or "(…; D87)". The author's decision of 2026-11-09 on the fixed-map mode (Appendix E, "Author decision of 2026-11-09 (fixed-map mode)") made normative that the fixed-map mode need not keep the linear construction of U (§6.7): the decided text begins "**Decided by the author (2026-11-09).**", and the tag of the M1 rule now covers only its k/n centre. The author's decision of 2026-11-10 on the PDE split (Appendix E, "Author decision of 2026-11-10 (PDE split)") made the split of the SiPM PDE out of the efficiency map normative (§5.1, §6.6, §6.7 "PDE split", §8.7, §11.4, §14, §15, §16, §17, §19 PDE item, C6, C20; D83 (20)–(23) stay proposed): the decided texts begin "**Decided by the author (2026-11-10).**" or are tagged "(decided by the author, 2026-11-10; …)" (as "(decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md)" or a variant naming another source), and the §14 module table, §17, C6 and C20 name it as "decided by the author on 2026-11-10". **This English edition is the primary version.** The Traditional Chinese clean edition (`simulator-calibration-v7.37.4-clean.md`, SHA-256 92e0c8e5262536773c490f5a91f72e903f516d9fc05067aee81b42ceef459cf8) is kept as a reference translation without normative force. It was the line-aligned source of this file, and it corresponds to this English edition as it stood before the changes of the primary edition (SHA-256 38a5cd1f11f7b70724f4706af67c38e77baec059433d7f9d5af700254d6f5655); the changes listed in Appendix E have not yet been carried into it, and line alignment with it is kept where possible but is no longer guaranteed. Where the two differ, this English edition prevails and the difference is reported as a defect of the reference translation. Where this edition appears to differ from a rule of the frozen version, the difference is reported as a defect and resolved with the author (Appendix D); it is not decided by the implementer. In this file, "the original file" and "the original text" always mean the frozen version v7.37.4, never the Chinese clean edition. The cleanup did the following:

- Removed version annotations, review numbers and the version-by-version historical narrative;
- Rearranged paragraphs, lists and tables;
- Removed Appendix B (mapping of old review topics), rewrote the version-by-version record in §18 as a summary of design decisions, and added Appendix D (known inconsistencies and items to clarify);
- Added §14.1 (execution binding for Linux and Slurm). This is the only **new** normative section in this file: it specifies only the execution layer, does not change any statistical rule apart from the items to be confirmed listed in §19, and has not gone through the R2 regression of v7.37.4. The places where this edition, in the body, chooses a reading of the original text are listed in Appendix D.

The version-by-version revision record and the source of each decision are kept in the sealed original file.

| Item | Content |
| --- | --- |
| Frozen version it is based on | `simulator-calibration-v7.37.4.md` (SHA-256 c1d6233df96c8436d7f6cea5d915d2db7571f694128d2746a855b837f031d215) |
| Reference implementation | `calib_use_decision_table.py` (the version attached to v7.37.4, SHA-256 c5279adf41acfcfb21e8aa67295756d1a551361e6a9aa5fa68d98bb4f17a3de3) |
| Review status | The header of the original file says "this erratum has not yet been independently verified", because the header was written before the review. Afterwards a full-text R2 regression of v7.37.4 was done; all four obligations were judged supported, with no major (the record is in `simulator-calibration-v7.37.4-regression-review.md`, delivered in the same batch, SHA-256 91b39404f91df32226e321095e1c71bfa4d45aeaf09f2fc578cea7960d349d9e; it is not in the original file). This means that that review found no major; it does not guarantee that there are no defects; the minors adopted in that review are listed in Appendix D. |
| This clean edition | Cleaned up segment by segment in seven independent workspaces, then compared segment by segment against the original file by reviewers who did not take part in the cleanup, followed by one round of independent re-check and one Linux/Slurm execution-readiness review. The problems found have been fixed, or are listed in Appendix D and §19. The English edition was translated from the Chinese clean edition line by line and checked in independent verification, re-check and third-pass review rounds; from this version on it is the primary version (line 3). Five independent content reviews of the English edition were then applied: the body changes are listed in Appendix E, the items that need the author in Appendix D (D26 onward and the extended D7, D9, D14, D21). Ten computation reports, a g4sim binding check against the hep-research v0.62.0 sources and an independent triage of all open items were then applied (Appendix E, "Changes from the computation, g4sim-binding and triage pass"; `apply-computations.md`): settled items are marked in Appendix D and §19, and every Appendix D entry and §19 item carries its triage class and the earliest §17 phase it blocks. The author's acceptance of 2026-11-09 was then applied (Appendix E, "Author's acceptance of 2026-11-09"; `acceptance-applied.md`): the accepted items are normative, and the items still open are listed in "How to read this document". The g4sim S7 check against the hep-research v0.63.0 sources (`g4sim-S7-check.md`) was then applied (Appendix E, "g4sim S7 (hep-research 0.63.0)"; `s7-applied.md`). The independent verification of these two passes (`accept-s7-verify.md`) and the computation of §19-g9 (`compute-19-g9.md`) were then applied (Appendix E, "Verification of acceptance and S7; §19-g9"). The study of D28 (`research-D28.md`) was then applied after the author's decision of 2026-11-09 (Appendix E, "D28 revision (author decision of 2026-11-09)"), and then its independent verification (`d28-verify.md`; Appendix E, "Verification of the D28 revision"). The g4sim S8 and S9 check against the hep-research v0.65.0 sources (`g4sim-S8-S9-check.md`) was then applied (Appendix E, "g4sim S8 and S9 (hep-research 0.65.0)"), and then the independent verification of the last two passes (`d28-s89-verify.md`; Appendix E, "Verification of the D28 fixes and S8/S9"). The author's decision of 2026-11-09 on the fixed-map mode was then applied (Appendix E, "Author decision of 2026-11-09 (fixed-map mode)"), and then the author's acceptance of 2026-11-09 of the plugin-source rules, the three D28-verification choices, D86 and D87 (Appendix E, "Author's acceptance of 2026-11-09 (plugin-source rules, D28 choices, D86, D87)"). |

## How to read this document

The classification of sections below is the editor's reading suggestion; the original file has no such classification. The force of the rules is determined by the body text of each section.

- **Normative content**: §2–§11, §14 (including the execution binding of §14.1) and Appendix C; §15 is the acceptance criteria.
  - The rules of §10.2 are governed by the decision table of Appendix C: when the text of §10.2 and the table disagree, the table governs, and the disagreement is reported as a defect.
  - The reference implementation `calib_use_decision_table.py` runs exhaustive tests over the scope of Appendix C.
- **Nature of the other sections**:
  - §1 states the scope (its simulator rule is normative and detailed in §11.4); §12, §13, §17, §19, Appendix A, Appendix D and Appendix E are, respectively, the sufficiency check, integration, implementation roadmap, open questions, symbol table, known inconsistencies and the change list of the English primary edition; the owner list in §15.3a restates §14, and §14 governs.
  - The §0 summary, the comparison study of §16 and the §18 summary of design decisions (explaining why the design is as it is and which alternatives are not adopted) are all explanatory.
- **Suggested reading order**:
  1. §0;
  2. §2.1 joint likelihood;
  3. §5 contract and §8 gates;
  4. §9 validation and §10.2 evidence grade;
  5. Appendix C;
  6. §14 division of work among scripts;
  7. §15 tests.
- **Section numbers** are the same as in the frozen version, so the documents can be cross-referenced; the Chinese reference translation was in addition aligned line by line with this file before the changes of Appendix E (whose line numbers refer to that state).
- **When implementing**: read Appendix D first. Entries of Appendix D and items of §19 that begin "**Accepted by the author (2026-11-09).**" are normative, and the body implements them: D7, D14–D18, D20–D24, D26–D28, D32, D33, D35, D36, D38, D43, D44, D49, D53, D54, D56, D59–D63, D65, D66, D69–D72, D74, D76–D80, the merged D13 (into D63) and D64 (into D22), D86 and D87, and the §19 items on the mislabeling of uncertainty sources and on bitwise reproducibility in §14.1; D28 is in force as revised on 2026-11-09 (it begins "**Accepted by the author (2026-11-09; revised 2026-11-09 after en/research-D28.md).**"). The §6.7 rule on U in the fixed-map mode, which begins "**Decided by the author (2026-11-09).**", is normative in the same way, and so are, as decided by the author on 2026-11-10, the §6.7 "PDE split", the §19 PDE item ("PDE in the efficiency map …", third sub-item; §19-g4c in `triage.md`) and the text tagged "(decided by the author, 2026-11-10; …)". The other entries remain open: D1–D6, D8–D12, D19, D25, D29, D30, D34, D37, D39–D42, D45–D48, D50–D52, D55, D57, D58, D67, D68, D73, D75, D81–D85, and every §19 item not marked accepted or decided; D31 has no open part left (its response-layer requirement is one of the plugin-source rules accepted on 2026-11-09). For these, confirm with the author of the specification and do not decide yourself, except for the parts marked "Settled by computation" or "Settled by plugin source"; text tagged "(settled by computation, …; to be confirmed by the author)" is implemented as written and kept easy to change until the author confirms or vetoes it; text tagged "(accepted by the author, 2026-11-09; source en/…)" (the plugin-source rules, the three choices of the D28 verification, and the D86 and D87 texts) is normative, as accepted by the author on 2026-11-09 (Appendix E, "Author's acceptance of 2026-11-09 (plugin-source rules, D28 choices, D86, D87)"); for D19, D25 and the open items of §14.1 listed in §19, implement the reading written in the body and keep it easy to change until the author confirms.

---

## 0. Summary

This document defines, for hep-research, a simulator parameter calibration workflow that is independent of the detector type. It uses independent control observables to determine the free parameters of the simulator, attaches uncertainties, diagnostics and a scope of validity, and stops parameters that have not passed the checks from flowing downstream.

The derivation order of the document is bottom-up:

1. Compare the simulation chains of eight detector types, keep only the shared elements, and write them as the abstract response model (§3).
2. The general architecture (§4–§10) uses only objects of the abstract model.
3. Detector types and experiment instances connect through the specialization interface (§11), and the eight types are used to check whether the abstraction is sufficient (§12).

**Nature of the document**: This document is a specification, not a declaration that the engine has been implemented or that the tests have been completed. Thresholds still awaiting simulation calibration are in §8.7; the phased implementation is in §17.

**Main design points**

| Topic | Current design | Location |
| --- | --- | --- |
| Systematic errors and model discrepancy | Correlated data systematic errors are represented by nuisances η, model discrepancy by ν; ν and η enter the prediction through link functions. Link functions are declared per observable according to the observable's range (log, identity, logit, Fisher z; normalized shapes use the alr/ilr vector link), so the corrected prediction does not go out of bounds | §2.1, §5.4 |
| Sources of errors | All errors and covariances are produced by the model at the reference point θ_ref, including the event-level parametric bootstrap for shared events; uncertainties computed from observed values are not used | §2.1 |
| Rounding | Rounding is allowed only when it is negligible, in which case it is included as ρ²/12; when the condition does not hold, the contract is rejected | §2.1 |
| Constraint rules | References are defined on edges; injection points must split nodes; the "directed reachability condition" is only a necessary condition; comparison nodes have no separate constraints based on parameter semantics, and directions that cannot be constrained are decided by Fisher | §3.4 |
| MC noise budget | Limited by the θ-level matrix order Σ_MC ⪯ f·Σ_data; Σ_MC is computed from the response of θ̂ to the MC summary statistics and covers non-Gaussian blocks; G7 tests it by refits with K sets of seeds | §6.7, §8.2 |
| Shift mode | Validation terms use the full residual response vector; the central-value difference is quantified; multiple φ use a matrix condition; the conditions are decided by gates P8 and G9 | §5.5, §9.2 |
| G8 closure | The overall false-alarm rate is controlled by Holm; N_c is derived from power; boundary points check only under-coverage; the closure test is built from real MC, with each pseudo-data set using its own independent MC | §8.4 |
| Validation | Validation reuse and "No change of mode after a failure" are both keyed by raw data unit, and failure records carry time order; rules are locked before the validation data are seen; alternative hypotheses are declared as simulation settings; the design-stage gate P7 estimates power (P7 is not a mandatory gate); the deterministic constraints N_d admit only exact constraints that hold by construction, declared by the contract, and C_r⁺ is defined in standardized coordinates | §8.1, §9.2, §9.4, §9.5 |
| Evidence grade | `incomplete` is a status (rule 0), decided after the mandatory-gate-failure rule (rule 1); the role of an upstream is derived from how it is used; the grade rules are written as a decision table and tested exhaustively | §10.2, Appendix C |
| Propagation | Principal components of the upstream joint posterior are exported (shared nuisances are exported with the joint posterior); shared nuisances have versions; when different packages constrain the same shared nuisance with different versions, they cannot be multiplied independently and are combined by a joint fit or by a validated full joint factor; downstream uses the upstream's propagation package as a whole | §10.4 |
| g4sim binding | The layer of g4sim in which a parameter sits determines the candidate methods; "seed" and "independent MC" are defined by g4sim's event intervals and Philox streams; MC noise is divided into three layers, and efficiency-map errors are represented by shared φ; known approximations of g4sim are listed as model discrepancy; models are identified by their g4sim identity; the phasing is scheduled according to the g4sim stages already merged | §11.4, §6.6, §6.7, §5.4, §5.1, §10.3, §17 |
| Interface and workflow | The interface includes φ, ψ, M inputs; every gate states its remedy level; P3 is in implementation phase 2 (§17) | §8.2, §11 |

**Design principles**

| # | Principle | Where implemented |
| --- | --- | --- |
| 1 | A successful fit does not mean that the model is credible; credibility is decided by validation that is declared in advance and has sufficient power | §9 |
| 2 | Rules are locked before the validation data are seen; data are separated from rules by commitment hashes | §5 |
| 3 | Correctness decisions depend only on the properties of the kernels and on the DAG; mechanism classes and degeneracy modes are only hints | §3, §8 |
| 4 | Cost and reachability are derived from the rules; identifiability is decided by Fisher | §3.4, §3.6, §8.3 |
| 5 | Quantities for "whether to accept" are expressed as effect sizes relative to V^unc_data; gates that need a probabilistic decision state the overall false-alarm rate and the power explicitly | §8 |
| 6 | Downstream references only by hash; uncertainties propagate through shared, versioned nuisances and are not counted twice | §10 |
| 7 | All gates of the same pipeline stage are run; every gate states its remedy level | §8.1 |

**Terminology**: "pipeline stage" means A0, A–G (§4.2); "implementation phase" means phases 0–5 of the roadmap (§17); the ZDC study's own stages are called Phase.

---

## 1. Purpose and scope

The two 11-parameter fits of the ZDC ECAL study both failed to converge and stopped at the boundary, yet no tool could point out the cause at the time. This workflow fills exactly this gap, and generalizes to any "parameters → simulation → observables" chain.

| Problem | Product | This workflow |
| --- | --- | --- |
| Simulation tuning | Simulator parameters | Handled (core use) |
| Post-hoc correction model | Corrections applied to the simulation output | Handled (treated as parameters on analysis nodes) |
| Calibration constants | Per-channel constants applied to data | Not handled; results are referenced as φ or as conditions |

**Simulator**: Geant4 simulation always goes through g4sim (`detector-spec/1`, `simulation-request/1`, `g4sim-run/1` and `response-pipeline/1`). The binding rules are in §11.4. Simulators that do not go through g4sim (toy detectors, external frameworks) may still connect through the evaluator interface of §7.1, but do not get the checks derived in §11.4.

**Not covered**:

- Tuning from the measured physical quantity itself;
- The physics content of particle transport, algorithms for specific functionals, integration with experiment frameworks;
- Per-channel parameters numbering in the thousands or more, event-level unbinned likelihoods, selection among a large number of discrete models;
- Cross-event effects (space-charge accumulation, dead time, pile-up), listed as open questions (§19).

---

## 2. Inference problem and terminology

### 2.1 Joint likelihood

#### Composition of the likelihood

All calibration observables enter the same likelihood. The likelihood is made up of three kinds of blocks, Gaussian, binomial and Poisson, plus the following nuisances (D33):

- ν: model discrepancy (§5.4);
- η: correlated data systematic errors;
- φ_P: externally constrained parameters in profile mode, with constraint center φ_P⁰ and constraint covariance Σ_φP, which may be correlated (§5.2 clause 5, §5.5, §10.4); φ in shift mode are not in the likelihood and enter through the ±1σ refits (§5.5, §7.5);
- γ: the MC nuisances of non-Gaussian blocks (γ of BB-lite, the efficiency nuisance of the auxiliary binomial likelihood), each constrained by its MC auxiliary measurement m_MC ("Finite simulation statistics in non-Gaussian blocks" below);
- ω: the free normalizations of count shapes ("Count likelihood and the normalization parameter ω" below), which have no constraint term.

```latex
-2\ln L(\theta,\nu,\eta,\phi_P,\gamma,\omega) = \sum_{b}\, -2\ln L_b\!\left(y_b \mid \mu_b\right)
+ \sum_{b'} -2\ln L^{\mathrm{aux}}_{b'}\!\left(m_{\mathrm{MC},b'} \mid \gamma_{b'}\right)
+ \sum_k \nu_k^2 + \sum_j \eta_j^2
+ (\phi_P-\phi_P^{0})^{T}\,\Sigma_{\phi_P}^{-1}\,(\phi_P-\phi_P^{0})
```

The second sum runs over the MC nuisances of the non-Gaussian blocks; the ω are free.

The subsections of this section:

- How the prediction connects to the nuisances through link functions ("Link functions");
- Which observables may enter which kind of block ("Block rules");
- The data-side representation of normalized shapes: count likelihood and ω, expected total, Gaussian summary statistics, event samples, and the fallback for zero counts;
- Gaussian blocks and the calibration-side constraints by construction N_d,c;
- Sources of errors: count-type errors, event-level parametric bootstrap, externally released uncertainty tables, rounding;
- Toys for shapes conditioned on the total, and when C_r depends on the observed total in holdout;
- Finite simulation statistics in non-Gaussian blocks.

#### Link functions

Each observable chooses a link function g according to its **range**, declared one by one in the contract's `observables[]` (§3.3):

| Range | Link function g | Rationale |
| --- | --- | --- |
| Always-positive quantities (widths, ratios, counts, scales) | log | Remains positive after correction |
| Quantities that can be positive or negative (offsets, residual means) | identity | The quantity may be zero or negative |
| Quantities within (0, 1) (efficiencies, tail probabilities) | logit | Remains within (0, 1) after correction |
| Quantities within (−1, 1) (correlation coefficients) | Fisher z | Remains within (−1, 1) after correction |
| Normalized shapes (K components, summing to 1) | Vector link: additive log-ratio alr(p)_k = ln(p_k / p_K), k = 1…K−1 (or isometric log-ratio ilr) | The inverse transform p = softmax(alr, 0) always lies in the simplex; the K components together take only K−1 link coordinates; the reference category (alr) or the contrast basis (ilr) is declared by the contract (§5.2) |

The functional class only gives a default value and does not determine the link function; two observables of the same functional class may have different link functions (for example log for a tail width, logit for a tail probability).

```latex
g\!\left(\mu_{b,i}\right) = g\!\left(m_{b,i}(\theta,\phi)\right) + \sum_k \nu_k\, u_{k,i} + \sum_j \eta_j\, s_{j,i}
```

- u_k: principal components of the model discrepancy, defined in link space (§5.4).
- s_j: the effect of the j-th correlated systematic error in link space. For example a common energy scale, luminosity, selection efficiency.

**Normalized shapes**: i refers to the K−1 alr (or ilr) coordinates, not to the K components. u_k and s_j are defined in this K−1-dimensional space; after correction the prediction is converted back to K components by softmax, so it always lies in the simplex. **alr/ilr acts only on the prediction side**; the data side chooses its representation according to the counts ("Data-side representation of normalized shapes").

One component must not be dropped and logit then used separately on each of the remaining components: the sum after correction is no longer constrained, and negative components may result (example: for p = (0.6, 0.35, 0.05), with the first two components each shifted by +0.5 in logit space, the third component becomes −0.182).

This has two effects:

1. Binomial predictions always fall within (0, 1), and Poisson and always-positive predictions are always positive.
2. Correlated systematic errors act as nuisances on all blocks: correlations across blocks hold naturally, and the Peelle bias caused by "scaling the covariance by the measured values" is avoided.

#### Block rules

- Binomial blocks and Poisson blocks must not overlap with other blocks, in both **data events** and **simulated events**.
- Observables that share events must be converted to Gaussian summary statistics, and their joint covariance is obtained by the event-level parametric bootstrap ("Event-level parametric bootstrap").
- Conversion conditions: expected count per bin ≥ 5, and both nε and n(1−ε) ≥ 5; normalized shapes use a stricter condition instead (expected count per bin ≥ n_min, "Gaussian summary statistics for normalized shapes").
- All conversion conditions take the worst case over the same set of evaluation points as the Gaussian-summary-statistic condition, and are decided when the contract is locked, without looking at the observed data:
  - When they do not hold, the checker rejects the contract (§5.2); normalized shapes are first merged according to the merging rule ("Merging").
  - They are recomputed at the fit point; when they do not hold, the contract is rejected and the validation data are not opened.

#### Data-side representation of normalized shapes

By default the data of a normalized shape enter through the count likelihood (next subsection). Only when the shape shares events with other observables and must be converted to a Gaussian summary statistic under the block rules are the data represented as a Gaussian in alr (or ilr) coordinates ("Gaussian summary statistics for normalized shapes").

#### Count likelihood and the normalization parameter ω

**Default: count likelihood**. The data of the shape enter a Poisson block as K bin counts: one Poisson per bin, with the total absorbed by a free normalization parameter ω; this is equivalent to the multinomial likelihood conditioned on the total. The predicted bin probabilities are the p converted back by softmax. The likelihood is still defined when any bin count is zero, and there is no need to take the alr of the data.

**Role of ω**:

- ω is a profiled nuisance, belongs to β (§9.2), and is fitted only with calibration data.
- When the shape is a validation observable, ω is not fitted with y_v; instead the shape is conditioned on the total (multinomial likelihood). The sum of the validation residuals over the K bins is therefore 0 by construction, and this direction is included in N_d (§9.2).
- The same holds for free-ω shapes in cross-validation: ω is each shape's own normalization and the other folds have no information about it, so the out-of-fold residuals are conditioned on the shape's observed total in that fold, with the bin probabilities taken from that fold's training fit. The bins of a shape are not split across different folds (the fold split is by observable, §9.3).
- Unconditioned absolute-count shapes have no ω and are not conditioned on the total in either holdout or cross-validation.

**The total is not declared separately as an observable**:

- A shape that enters through the count likelihood cannot share events with other observables (block rules), and the total shares all of its events.
- When the shape enters as a Gaussian summary statistic, the conditioned quantity is the total number of events N_tot,s of the event sample ("Event samples and normalization components"), which is likewise not declared separately; but selection-dependent functions of the total (efficiency N_pass/N_tot, ratios) may be summary statistics and share events with the shape.
- When the model predicts absolute counts, the shape enters as unconditioned K bin counts, and the information on the total is already contained in them.

#### Expected total of validation shapes: N_decl and N_exp

The expected total of a validation shape falls into two classes. For a free-ω shape the model does not derive the total: ω is free precisely because the absolute normalization of the simulation is not trusted, so a model-derived expected total could not support the guarantee "expected total ≥ 10 ⇒ P(N_obs = 0) ≤ e⁻¹⁰", and the toy totals of P7 would also differ systematically from the N_obs of the V stage.

**(i) Free-ω shapes that enter through the count likelihood** (conditioned on the total; Gaussian-summary-statistic shapes are not in this class, and are instead declared per sample under "Event samples and normalization components"):

- The contract declares the expected total N_decl and its basis (exposure times an external rate, or a previous measurement; the source of the basis is written into the contract). `calib_contract.py check` confirms that the basis is recorded, without reading validation data.
- The model provides only the bin probabilities p(θ) and does not derive the total.
- When conditioning on the total, the total is ancillary under the null hypothesis, so N_decl is used only for design:
  - At lock, N_decl ≥ 10 is required. When N_decl is correct, P(N_obs = 0) ≤ e⁻¹⁰ ≈ 4.54 × 10⁻⁵ (with equality at N_decl = 10). A misestimated N_decl affects only the design-stage power estimate and this probability, not the size of T_v.
  - The toys of P7 use N_decl as the total ("Toys for shapes conditioned on the total"); the V stage uses the observed N_obs as the total and re-decides the power with the same procedure.
- N_decl ≥ 10 does not change with the evaluation point.
- **Cross-validation**: the contract likewise declares N_decl, with the basis being that fold's observed total in the calibration data (it is known before lock). `calib_contract.py check` verifies through `calib_data.py` that the two are equal; when they are not equal the contract is rejected, so P7 and the V stage use the same total (§9.3).

**(ii) Unconditioned absolute-count shapes** (no free ω):

- The expected total N_exp is the validation-sample exposure declared by the contract (luminosity, number of events or number of triggers, etc., which are metadata, not observed values) times the absolute rate of the simulation at the evaluation point.
- When the simulation has no absolute normalization (for example a particle gun), the shape must not enter in this class and may enter only as a free-ω shape. The decision is based on the contract field `sim_absolute_normalization` (yes/no, declared for each simulated sample, with a basis, for example the conversion from the generator's cross section and the luminosity). When the field is missing it is treated as "no"; `calib_contract.py check` rejects a contract in which a shape enters as an absolute-count shape while the corresponding sample is "no".
- N_exp takes the minimum over the same set of evaluation points as the rounding condition (scan points, prior vertices, and their combinations with nuisance ±2σ; η that change the rate, for example luminosity or trigger efficiency, are among them; the evaluation points of "Rounding"), and ≥ 10 is required.

**When the condition of (i) or (ii) does not hold**: when N_decl or N_exp < 10, the contract must not use the shape (remove it, or redefine it together with other observables, §9.3; N_exp is a total, and merging bins does not change it); when `sim_absolute_normalization` is "no", the shape may enter only as a free-ω shape instead ((ii), second item). A contract that still does not comply is rejected by the checker (§5.2 clause 9, items 4 and 5).

**Recomputation at the fit point**: after the fit converges, `calib_fit.py` recomputes the N_exp of (ii) at the fit point (θ̂, ν̂, η̂, φ̂) together with the rounding condition; when it does not hold, it is handled in the same way as a rounding recomputation that does not hold (the contract is rejected, and the validation data are not opened).

#### Gaussian summary statistics for normalized shapes

The conditions are decided when the contract is locked, without looking at the validation data.

**Condition on the expected count per bin**:

- Expected count per bin ≥ n_min (design value 20, §8.7), taking the worst case over the same evaluation points as N_exp (scan points, prior vertices and their combinations with nuisance ±2σ).
- Expected count per bin: for a free-normalization event sample it is N_decl,s·P_k(θ) (for multiple components see "Event samples and normalization components" (b)); for an absolute-count shape it is exposure × the absolute rate of the simulation.
- It is recomputed at the fit point (θ̂, ν̂, η̂, φ̂) together with N_exp; when the recomputation does not hold, the handling is the same as for N_exp (the contract is rejected, and the validation data are not opened).
- The block conversion conditions ("Block rules") are also decided on the same set of points.

**Data-side estimator**:

- The summary statistic of a shape is **always** computed as the alr/ilr of n_k + ½ over all K bins (including the reference category) (Jeffreys correction), with no branch for zero bins, so it is defined for any observed counts.
- The estimators of other summary statistics (location, width, mean, efficiency, etc.) must also be defined for all counts:
  - The contract declares for each summary statistic the value convention for 0 or 1 events and for a denominator of 0; `calib_contract.py check` rejects estimators without a convention.
  - The value convention must satisfy the N_d declared within the same sample (for example, when f_A + f_B = 1 is declared, the convention for 0 events must make the sum of the two equal to 1), which the checker verifies; otherwise a correct release would also trigger the data-side check when N_tot,s = 0.
  - The data, the bootstrap and the toys apply the same convention (when conditioning on N_tot,s, the selected counts in toys can be very small).

**Prediction side**: per §5.3, the prediction-side summary statistic is the expectation of the same estimator under the data distribution, E[alr(n + ½)]. Expected counts: for an absolute-count shape, exposure × the absolute rate of the simulation; a free-normalization event sample is conditioned on N_tot,s, giving N_tot,s·P_k(θ) ("Event samples and normalization components" (c)). The computation uses one of two methods:

1. Use the model to generate count samples with the same expected counts as the validation sample, apply the same estimator, and take the average;
2. When λ_k ≥ n_min, apply the same estimator to the **unnormalized** counts of high-statistics MC (the +½ is negligible on MC; the +½ on the data side cancels the first-order Jensen bias of ln: at λ = 20, E[ln(n + ½)] − ln λ = −1.2 × 10⁻⁴, with standard deviation 0.227).

Both make the residual mean 0. The MC **must not** first be normalized to the data size and then have ½ added: that shifts the prediction by ½(1/λ_k − 1/λ_K), i.e. shifts the residual (data − prediction) by about −0.095σ at λ_k = 20 with reference bin λ_K = 200.

**Covariance**: includes the cross terms with other summary statistics that share events, obtained by the "Event-level parametric bootstrap"; the delta method is used only as a cross-check.

**Fixed representation**: the representation, K and the merging are fixed in the contract and do not change afterwards because of observed data.

#### Merging

- When the above conditions (worst case over the evaluation points) do not hold, adjacent bins are merged according to the merging rule declared in advance in the contract, using the worst expected count over the evaluation points, until the expected count per bin is ≥ n_min at every evaluation point.
- Merging is completed and fixed when the contract is locked; the merging rule must not depend on the observed counts.
- When, after merging, the condition still does not hold at one or more evaluation points and the shape must be a Gaussian summary statistic (shared events), the checker rejects that observable (no further merging).
- When the recomputation at the fit point does not hold, the contract is rejected as stated above, with no re-merging.

#### Event samples and normalization components

**Definitions**:

- **Event sample**: Gaussian summary statistics are all taken from event samples. An event sample is a set of events declared by a release, counted before any selection that defines a summary statistic.
- **Normalization component**: an event sample consists of one or more normalization components. A component is a subset of events whose normalization is independent of the others (for example different run periods, each with its own luminosity); each event belongs to exactly one component; components are determined by the release metadata, not by observed values. When there is only one component, the sample has only one normalization.
- **N_tot,s, N_decl,s**: N_tot,s,j is the total number of events of component j, and N_tot,s = (N_tot,s,j) is the vector they form; N_decl,s,j is the expected number of events that the contract declares for component j. Below, N_tot,s and N_decl,s in a multi-component sample both refer to the vector over components, and "N_tot,s = 0" means that all components are 0.

**Sample composition rules**:

- Summary statistics that share events must be taken from the same event sample; samples do not share events with each other.
- When sets declared within the same release overlap, or a derived summary statistic spans different sets (for example an efficiency combining two periods), the contract merges them into one sample, but the original normalization of each set is kept as its own component.
- **Containment rule**: a sample that contains calibration observables must be **entirely contained in the calibration release**: each of its events belongs to the calibration release, and validation observables that share events are taken only from these events.
- This sharing is allowed only in cross-validation (with the `cv` flag). Validation observables in holdout **must not** share events with calibration observables (decided at release level: the calibration release and the validation release must not share raw units, §9.5), because the containment rule would make them computable from the calibration release before lock, and holdout would no longer be blind. So in holdout a sample that contains calibration observables contains only calibration observables, and V_cv = 0.
- When the event sets of the calibration release and the validation release overlap and the merged sample contains events that belong only to the validation release, the contract is rejected: the N_tot,s of such a mixed sample carries sealed validation information, which cannot be obtained before lock. The remedy is to change the validation observable so that it is taken only from events of the calibration release, or so that it does not share events with calibration observables.

**Why condition on N_tot,s**: when the normalization of a sample is not trustworthy (`sim_absolute_normalization` is no, or the contract declares it free), the vector N_tot,s of component total event counts is a sufficient statistic for these normalizations, and is ancillary for **all** summary statistics in the sample (shapes, efficiency N_pass/N_tot, means, etc.).

- The conditioning is on N_tot,s, not on the total of an individual shape: the count N_pass of an individual shape that passes the selection is not ancillary (the efficiency depends on it), and conditioning on the shape's own total would cancel the data variance in the efficiency direction of the shared events, leaving it without power.
- The conditioning is on the vector over components, not only on the sum Σ_j N_tot,s,j: when conditioning only on the sum, the proportions of the components in the toys are sampled from the model, while the true proportions are determined by the untrustworthy relative normalizations, and summary statistics that span components would make T_v in effect test the relative normalization.

**(a) Declaration**: for each component of each free-normalization sample, the contract declares N_decl,s,j and its basis.

- When the sample contains any calibration observable (calibration samples in holdout, all samples in cross-validation; in holdout, calibration and validation do not share events, §9.5): by the containment rule it lies entirely in the calibration release, so N_tot,s is calibration data and can be read before lock. The basis is this observed value; `calib_contract.py check` verifies equality through `calib_data.py` (reading only the totals), and when they are not equal the contract is rejected.
- When the sample belongs entirely to validation data: the basis is exposure times an external rate, or a previous measurement; the checker confirms that the basis is recorded, without reading validation data.

**(b) Conditions at lock** (n_min, block conversion conditions, merging) are decided at the evaluation points with the expected count per bin Σ_j N_decl,s,j·P_{k,j}(θ). P_{k,j} is the model probability that an event of component j falls into that bin; with a single component this is N_decl,s·P_k(θ), where P_k(θ) is the probability given by the model that "an event of the sample falls into bin k of the shape" (including the selection probability).

**(c) After N_tot,s is known** (before lock for samples that contain calibration observables; at opening for samples that belong entirely to validation):

- The expectation of the prediction, the event-level bootstrap and the toys are all conditioned on N_tot,s: each set draws N_tot,s,j events from the model in each component j (the numbers of events across components are fixed to the observed values, not sampled from the model), and then applies the selection and the same estimator. So N_pass and the efficiency keep their binomial variance; a misestimated N_decl,s does not change the scale of V or the size of T_v.
- When, at opening, the bootstrap conditioned on N_tot,s for a sample that belongs entirely to validation is rank-deficient in the directions of the sample (decided with τ_num; for example a total of only 1 or 2 events, or a collapse caused by some components being 0; the decision is owned by `calib_validate.py`), it is handled in the same way as N_tot,s = 0: the rank-deficient directions are removed and recorded.
- Before opening (P7, design of Ĉ_r), samples that belong entirely to validation use N_decl,s in place of N_tot,s.

**Recomputation at the fit point**: according to the merging fixed at lock, with no re-merging; decided with N_tot,s·P_k(θ̂) (with N_decl,s·P_k(θ̂) for samples that belong entirely to validation); when it does not hold, the contract is rejected (the validation data are not opened).

**N_tot,s does not satisfy n_min at opening**: when a sample that belongs entirely to validation does not satisfy n_min with N_tot,s at opening, it is not rejected (the data have already been read), and the result records this. When V contains a bootstrap, T_v is always calibrated by toys ("Event-level parametric bootstrap"), and the toys and the prediction are both computed under N_tot,s with the same estimator, so the size is still correct; the degradation of the Gaussian approximation affects only the power, which the V stage re-decides under N_tot,s.

**Bootstrap at opening**:

- Regenerated only for samples that belong entirely to validation data: their N_tot,s is known only at opening; they do not share events with calibration data, so there is no V_cv term.
- The number of events is N_tot,s, the next unused event interval under the seed rules of §6.6 is used, and B is the same as at lock.
- Counted in the bootstrap budget of §6.7 (n_open: one set for each free-normalization sample that belongs entirely to validation, estimated at design time with N_decl,s).
- The frozen V̂ (MC part) and the calibration side are unchanged.
- When regenerating the bootstrap and the toys with N_tot,s at opening fails, it is, as for count shapes, a numerical failure (`incomplete`, redo per §7.3).

**Some components are 0**:

- Summary-statistic directions that depend only on these components are removed per "Fallback for N_obs = 0 and N_tot,s = 0".
- Summary statistics that span components then collapse onto the summary statistics of other components (for example t ≡ ε_2 when N_tot,s,1 = 0), leaving directions on N_d^⊥ with only rounding variance; these directions are removed as well under the rank-deficiency handling of the bootstrap in (c) above (decided with τ_num). Everything else proceeds as usual.
- In cross-validation, some components being 0 is known before lock: summary statistics that depend only on these components have σ_i⁽⁰⁾ = 0, and the contract is rejected per §5.2 (remedy: do not use them). The fallback is used only for cases that become known only after opening.

**The rank-deficiency handling is the only exception**: this rank-deficiency handling is the only exception to "N_d is declared by the contract and is not decided by numerical rank" (§9.2, §15.3a).

- The true variance of a removed direction is exactly 0, so the true covariance has no gray zone. An estimate with finite B may misjudge (estimate a direction whose true variance is not 0 as 0, or the reverse); T_v is calibrated by toys, so this affects only the power.
- When a near-collapse is not removed, the rounding ratio in the remaining directions can far exceed 1/25; but T_v is calibrated by toys and the toys apply the same rounding, so this affects only the power.

#### Fallback for N_obs = 0 and N_tot,s = 0

This is a fallback declared in advance, and it **applies only to** the following two classes:

- A free-ω count shape observes N_obs = 0;
- A free-normalization event sample observes N_tot,s = 0.

**Handling**:

- The K − 1 directions of the shape (for an event sample, the dimensions spanned on N_d^⊥ by all summary statistics of the sample, regardless of the values they take under the value conventions, for example the 0/0 of an efficiency at N_tot = 0) have no variance: the conditioned residual of a count shape is always 0; when a sample is conditioned on N_tot,s = 0, the prediction, the bootstrap and the toys of the summary statistics have no variance.
- These directions do not enter T_v, k is reduced accordingly, and the result records this.
- It is not written to the failure record, and it is not `incomplete`.
- All toys (calibration of T_v, power) apply the same handling.

**Cases where it does not apply**:

- Unconditioned absolute-count shapes (the model predicts absolute counts, no free ω): N_obs = 0 is ordinary data, the residual is −μ, and it enters T_v as usual.
- An event sample with N_tot,s > 0 in which the count of some summary-statistic shape that passes the selection is 0: when conditioning on N_tot,s this count is still random, alr(½, …, ½) is an ordinary data value, and it enters T_v as usual.

**k = 0**: if as a result no validation direction remains (k = 0), T_v is undefined. The decision is recorded as `no-testable-direction`, the provisional failure record is changed to `withdrawn`, and the grade is `calibrated-unvalidated` per §9.5 (`no-testable-direction`).

#### Gaussian blocks

```latex
-2\ln L_G = r^{T} V_G^{-1} r,\quad r = y_G - \mu_G,\quad
V_G = V_{\rm data}^{\rm unc} + V_{\rm MC} + V_{\rm emu} + V_{\rm learn}\ \Big|_{\theta_{\rm ref}}
```

- V_data^unc is the data errors within the same data release that are uncorrelated with each other.
- Correlations between two releases that arise from shared events are represented by cross covariances (for example V_cv between calibration and validation). Holdout does not share events per §9.5, so V_cv = 0; V_cv appears only between cross-validation and the calibration release.
- Correlated systematic errors are all represented by η.
- All covariance terms are computed at the reference point θ_ref and updated by fixed-point iteration (§7.3).

#### Calibration-side constraints by construction N_d,c

**Definition**: N_d,c is the exact constraints by construction declared among calibration observables, for example sums by definition, or relations determined by known component totals in event samples that contain calibration observables. The declaration rules, the standardization of ñ_j and the declaration check are the same as in §9.2; this applies to all modes (including `none`), and N_d,c is declared per §5.2.

**Why project**: N_d,c leaves V_G with only rounding variance in these directions, or makes it exactly singular; without projection V_G⁻¹ is undefined in these directions, and with rounding the rounding condition is ∞.

**Rules**:

- The calibration-side Gaussian likelihood is computed on N_d,c^⊥, with the same construction as C_r⁺ of §9.2: in standardized coordinates, the orthogonal complement Ũ_⊥ of N_d,c is constructed from the declared ñ_j,

  −2 ln L_G = r̃ᵀ Ũ_⊥ (Ũ_⊥ᵀ Ṽ_G Ũ_⊥)⁻¹ Ũ_⊥ᵀ r̃ (r̃ and Ṽ_G are in standardized coordinates).

- A, Σ_θ, the Fisher of P3 and G5, the ln det diagnostics and all toy fits use the same projection.
- Without rounding, this is equivalent to removing one dependent observable per constraint, and the result does not depend on which one is removed; with rounding terms the two differ slightly (as in §9.2), and the projection governs.
- On the calibration side the rounding condition is likewise decided only on N_d,c^⊥ (C̃⁽⁰⁾ and R are both projected onto Ũ_⊥, "Rounding").
- **Data side**: whether the data satisfy the constraints in the N_d,c directions is verified by the data-side constraint check of §9.2. Calibration data can be read before the fit, so this is checked at lock, and when they do not comply the contract is rejected.
- **Cross-validation**: each training fit is projected with the constraints contained in its calibration observables. The observables spanned by a constraint are in the same fold per §9.3; for declared constraints that are not of the types listed in §9.3, the observables they span must likewise be in the same fold, and `calib_design.py` rejects fold splits that do not comply. So in the training fits of the other folds the whole group is calibration observables.

#### Sources of errors

Principle: **always produced by the model at θ_ref, not determined by observed values**.

- **Count-type errors** (Poisson, binomial, summary statistics derived from counts) are computed from the predicted expectation at θ_ref.
- **The joint covariance of shared events** is estimated by the event-level parametric bootstrap (next subsection).
- **Externally released uncertainty tables** are handled according to the source declaration ("Externally released uncertainty tables").
- **Rounding** is allowed only when it is negligible ("Rounding").

#### Event-level parametric bootstrap

**Applies to**: joint covariances of shared events, including those between summary statistics of the same batch of events, between shapes and other summary statistics, and V_cv between calibration and validation.

**Procedure**:

- Generate B sets of event samples from the model at θ_ref. The number of events is sampled from a Poisson with the expectation at θ_ref; when the normalization of the sample is free, the number of events is the total number of events N_tot,s of that sample (for samples that belong entirely to validation, N_decl,s before opening, "Event samples and normalization components"). Summary statistics that share events are all in the same sample, so there is only one number of events.
- For each set, compute all summary statistics with the same estimator (§5.3), and take the sample covariance.
- Let p be the dimension of this bootstrap matrix (the number of all shared-event summary statistics); B ≥ max(500, 50p).
- Do not resample from the observed events.
- The bootstrap events are a kind of MC use; per §6.6 they use their own event interval, and they are counted in the event budget of §6.7.

**Correction factor for reporting**: when the matrix being inverted is **as a whole** this bootstrap sample covariance, the **reported** quadratic-form effect sizes (for example the χ²/ndf diagnostic) are multiplied by (B − p − 2)/(B − 1).

- This factor does not enter any decision: when V contains a bootstrap part, T_v is always calibrated by toys (§9.2), the observed value and the reference toys are multiplied by the same constant, and the p-value is unchanged; moreover, multiplying by the factor only corrects the mean and does not make the distribution χ².
- When the bootstrap is only part of C_r, the factor is not applied.

**Bootstrap noise must not move θ̂ without being accounted for**. The estimated covariance V̂ affects θ̂ through the GLS weights, so:

**(i) Common random numbers and regeneration** (used for the fits of the actual data, of the cross-validation folds and of the G8 pseudo-data themselves):

- All §7.3 iterations of the same result generate the bootstrap with **the same random numbers** (common random numbers: the same event interval, the same Philox key and the same set of uniform random numbers).
- At every θ_ref update the events are **regenerated** at the new θ_ref instead of reusing the old events: the number of events is obtained from the same uniform random number through the inverse CDF of the Poisson; the quantities of each event are generated from the model at θ_ref with the same random numbers (inverse CDF or other sampling determined by the random numbers); the response parameters are re-digitized with the same Philox key.
- In this way V̂ changes only slightly between neighboring θ_ref. V̂ jumps when events cross bin boundaries, so V̂ is a piecewise-constant function of θ_ref, not a smooth function; the §7.3 convergence criterion 0.1σ_tot is much larger than these jumps, and in numerical checks convergence takes 3–4 iterations. The convergence of the iteration is not disturbed by bootstrap sampling noise, and every iteration is a correct estimate of V(θ_ref).
- The toys for Ĉ_r, reference distributions, power and intervals freeze V̂; see (ii) and §7.3 "Toy data and V̂".

**(ii) Frozen V̂**: the K refits of G7, and the toys listed in §7.3 "Toy data and V̂", use the **V̂ matrix** at convergence of the fit they imitate (what is frozen is the matrix itself; the bootstrap is not regenerated at the θ_ref of each refit), so G7 tests only the MC noise of the prediction. If it were instead regenerated with an independent bootstrap in each refit, θ̂ would gain a spread of about (p − d)/B · Σ_data, which G7 would count as MC noise; it grows with p at fixed B, is about 0.02 Σ_data under B ≥ max(500, 50p), and matters relative to Σ_MC (linear Gaussian, p = 50, B = 2500, K = 10, Σ_MC = 0.1 Σ_data: the false-alarm rate of G7 rises from the nominal 0.01, which the frozen V̂ gives exactly, to 0.029 for d = 1 and 0.042 for d = 3; en/compute-D12.md).

**(iii) Σ_boot: the contribution of bootstrap sampling noise to θ̂**:

- Estimated at the design stage with **toy data**, **not with Asimov**: the residual of Asimov data at the true value is 0, so any positive-definite V̂ gives θ̂ = θ*, and the estimate is always 0.
- **Procedure**: generate N_t sets of toy data from the model at θ_ref (data noise; ν, η sampled according to their constraints); for each toy, recompute V̂ and θ̂ with K_b mutually independent bootstrap realizations (each using a different event interval, §6.6).
- Σ_boot is the pooled estimate of the within-toy sample covariance of (θ̂, ζ̂) (the toy fits also give ζ̂; for ζ see §10.4), with degrees of freedom ν_b = N_t(K_b − 1). This estimates E_y[Cov_boot(θ̂ | y)], that is, the part that the sampling noise of V̂ adds on top of the data noise.
- **Use**: P5 and σ_tot use its θ block, and the export of §10.4 uses the whole; in both uses Σ_boot is first divided by the w of §7.3. The w of Σ_boot is always computed with ε̂⁺; when all toys converge, w = 0.891 at the default n = N_t K_b = 60, and 0.935, 0.956 at n = 120, 200.
- **Number of sets**: N_t ≥ 10, K_b ≥ 6 and ν_b ≥ max(50, d + 5) are required (default N_t = 10, K_b = 6, ν_b = 50), so that the estimate of the θ block is of full rank and the ⪯ decision of P5 is meaningful in every direction.
  - Besides the sampling part √(2/ν_b), the relative standard deviation of the estimate has a part from Cov_boot(θ̂ | y) varying with the toy data, so N_t has a separate lower bound (linear Gaussian numerical check: for p = 10, 30, 50 and d = 1–6, the relative standard deviation of the trace is 0.10–0.28 and the mean bias ≤ 7%, within the precision of the true-value estimate; at N_t = 5, K_b = 6 it is 0.33 for d = 3).
  - Σ_boot itself is ≲ 0.02 Σ_data, so the effect of this precision on σ_tot is below 1%.
- **Explicit approximation (ζζ block)**: the dimension of ζ may exceed ν_b (for example the φ_map of an efficiency map can reach the number of replicas − 1), in which case the estimate of the ζζ block is low-rank; Σ_β + Σ_boot is still positive definite, so the export does not fail (Σ_boot,ζζ is only of the order of about 2% of Σ_data).
- **P5**: Σ_boot / w is folded into σ_tot per §8.1, and P5 requires Σ_boot / w ⪯ f·Σ_data (w per §7.3, with ε̂⁺; the same f as for Σ_MC, §6.7), so that, as for Σ_MC, the bootstrap-noise term actually used in σ_tot is at most a fraction f/(1 + f) of the variance in any linear combination of parameters (en/compute-D7.md). This decision of P5 is made at the design-stage θ_ref (Σ_boot is estimated only at that point). B ≥ max(500, 50p) makes this condition hold in the usual case (Σ_boot/Σ_data is about (p − d)/B ≤ 0.02, so Σ_boot / w ≲ 0.03 Σ_data even at X = 4).
- **Explicit approximation (reuse after the fit)**: σ_tot after the fit reuses the design-stage Σ_boot and does not re-estimate it at θ̂: P5 has already limited Σ_boot / w to within f·Σ_data, and the change between θ_ref and θ̂ is of higher order.

**θ that require resimulation** (acting at the Geant4 layer, §3.6), and nodes that the plan evaluates only by reweighting: the regeneration of (i) is replaced by resimulating the bootstrap events at the new θ_ref with **the same global event interval, the same Geant4 seed and Philox key**, and the event volume is included in the budget of §6.7. Particle histories may diverge after θ changes, so the correlation is incomplete; the convergence fraction of §8.7 has a separate acceptance test for this configuration.

**The bootstrap is not reused by reweighting**:

- When events are generated at the old θ_ref⁰ (density q) and then weighted with w = p/q to the new θ_ref (density p), the mean of the weighted summary statistics is correct, but its variance across the B sets in a bin is N∫_bin p(x) w(x) dx, not the N∫_bin p(x) dx that V(θ_ref) requires.
- The ratio in each bin is E_p[w | bin]: over the whole space E_p[w] = E_q[w²] ≥ 1, but this does not hold bin by bin, and in bins where p < q the ratio is < 1 (example: for q = N(0, 1), p = N(0.5, 1), the four bins x < −1, (−1, 0), (0, 1), x > 1 give 0.437, 0.722, 1.145, 2.081 respectively; in another example one bin is too high by a factor of 1.35, 2.82 at Kish ESS/N = 0.914, 0.503).
- So the reweighted bootstrap is not an estimate of V(θ_ref), and the claim "it is only a less informative estimate" does not hold; moreover V̂ is too high in some bins and too low in others, G6 and T_v are not necessarily biased toward the conservative side, and acceptance based on the overall rejection rate does not necessarily detect it.
- Therefore the bootstrap is always regenerated per (i); `calib_design.py` rejects plans that reuse bootstrap events by reweighting (remedy level: plan).

#### Externally released uncertainty tables

**Source declaration**: `data_release` declares a **source** for each uncertainty component (§5.1):

| Source | Meaning |
| --- | --- |
| `observed` | Computed from observed values, for example σ² = n |
| `expected` | **Statistical** component set from expected counts |
| `systematic` | Design errors such as scale, systematic errors, resolution or tolerance, with no statistical dependence on observed values |

**Relative systematic errors** ("f% of the measured value") may be expressed only as a single proportion f, or as a function f(·), declared by the contract, of the prediction or of a binning variable; a per-bin table of f_k is treated as a `systematic` table. This workflow computes σ_sys = f·μ(θ_ref), and recomputes it with θ_ref at every iteration of §7.3.

**Correlation structure**: the release must also declare the correlation structure.

- **Fully correlated** (one common scale, for example luminosity or energy scale): enters as one η, with effect s_j = f·μ (converted into link space).
- **Uncorrelated per bin**: enters V_data^unc as σ_sys².
- When no correlation structure is declared, the release is rejected at ingestion.

**Handling by source** (`calib_data.py` handles them only according to this declaration and does not read the values of the table):

- `observed` and `expected` components are sealed together with the observed values, are not provided to any script, and do not enter the computation. The statistical component of `expected` is replaced by the value that this workflow recomputes at θ_ref per the above ("Count-type errors" and "Event-level parametric bootstrap"), not added on top of it.
- Only `systematic` components are submitted separately from the observed values (the commitment hash covers both), and they may be read before the observed values are opened.
- `observed` components must not be used: they are sealed together with the observed values, and `calib_data.py` does not provide them to any script; at opening they become part of the validation read together with the observed values (§9.5), but they do not enter any computation.
- Statistical errors are always recomputed from the prediction at θ_ref per the above; the release must provide counts or equivalent information. When this is not possible (for example only ratios and errors computed from observed values are available):
  - A validation observable keeps its validation role and is decided as **untestable** (§9.5);
  - A calibration observable has no legitimate error, and the checker rejects a contract that contains it (it must be removed or its counts supplied);
  - An observable must not be switched to another role.
- When the declaration is missing, the release is rejected at ingestion (an input error, occurring before any κ).

**Source labeling is the publisher's responsibility** (applicability precondition):

- This workflow does not judge mislabeling from the numerical values of tables. Any value-based judgment must trade off missing a true mislabeling against misjudging a legitimate table (for example, two value-based checks once considered misjudged a constant table and a smooth legitimate table, respectively), and the consequences of a misjudgment (validation does not pass, a failure record is written) cannot be withdrawn.
- So if a publisher labels a component computed from observed values as `systematic` (for example a table with σ² = n or σ = f·|y|), or labels a non-statistical design error as `expected`, this workflow cannot detect it: the former amounts to reading validation data before opening, and the latter causes that component to be discarded and C_r to be underestimated.
- The claim `validated-in-scope` presupposes that the publisher's source labels are correct; `calibration-result` records the source declarations of the releases used and their submitters (§10.1).

#### Rounding

**Scope**: values that enter a Poisson or binomial likelihood as integer counts have no rounding issue; their discreteness is handled by the likelihood, and this item does not apply to them (their ρ is recorded as 0).

**Resolution ρ_i**:

- The representation resolution ρ_i of the other released values (the last-digit unit of the floating-point type or of the published digits; derived quantities propagate along lineage) is computed by `calib_data.py` from the format declared by the release, without reading observed values.
- The magnitude is taken as the maximum within the predicted ±5σ_i⁽⁰⁾ range, so ρ_i is not underestimated when the nominal value is close to 0 or a significant-digits format is used.
- This ρ_i is used for the rounding condition and for V_data^unc; the tolerance of the data-side constraint check is computed separately from the values actually read (§9.2).
- σ_i⁽⁰⁾ is the data standard deviation produced by the model, without rounding (the s_i of §9.2).

Rounding is included in V_data^unc as ρ_i²/12, and **is allowed only when it is negligible**.

**Condition**:

- Let R = diag((ρ_i/σ_i⁽⁰⁾)²) (the squared rounding step in standardized coordinates; R_ii = 0 where ρ_i = 0; an observable with σ_i⁽⁰⁾ = 0 and ρ_i > 0 is rejected per §5.2), and let C̃⁽⁰⁾ be the standardized covariance without rounding.
- The largest generalized eigenvalue max_u uᵀRu / uᵀC̃⁽⁰⁾u ≤ 1/25 is required, that is, in every direction the rounding step is ≤ 1/5 of the noise standard deviation without rounding in that direction. This condition does not depend on the choice of eigenvectors.
- When declared constraints by construction exist among calibration observables, C̃⁽⁰⁾ and R are first projected onto N_d,c^⊥ ("Calibration-side constraints by construction N_d,c").
- For a single observable it is ρ_i ≤ 0.2σ_i⁽⁰⁾; for a pair of observables with correlation coefficient c and each with ρ/σ = ρ̃, the condition is 1 − |c| ≥ 25ρ̃².

**Effect of double-precision observables**: the R of double-precision observables is zero, so the largest ratio is determined by the **conditional covariance given all double-precision observables** (Schur complement) of the rounded observables.

- Adding a double-precision observable b can only leave the ratio unchanged or make it larger.
- The ratio is unchanged when, given the existing double-precision observables, the partial covariance of b with every rounded observable is 0 (for example, b is uncorrelated with all existing observables; or b is correlated with the rounded observables only through the existing double-precision observables, with partial correlation 0).
- Otherwise the ratio may become larger, even if b is uncorrelated with the rounded observables themselves (for example, when b has correlation 0.75 with a double-precision observable that is correlated with a rounded observable, and its partial correlation with the rounded observable is not 0, the ratio can rise from 0.0156 to 0.0565). In that case some combined direction has smaller noise, rounding is indeed not negligible in that direction, and the condition itself is right.

**What is checked**: the decision uses only the **data noise**, not V_MC, V_emu, V_learn (they do not yet exist when the contract is locked, and they change with the MC budget of the plan).

- Using only the data noise is **not necessarily** more conservative: V_MC changes the fit operator A, and the actual C_r can be smaller in some directions than the version with data noise only. But P5 limits Σ_MC ⪯ f·Σ_data (f = 0.1), so the actual ratio is at most about 1 + f times the decided value (for example at most about 0.044 at the 1/25 boundary), and the rounding calibration of §8.7 covers this range.
- **Calibration side**: C̃⁽⁰⁾ is the V_data^unc of the calibration observables (without rounding, standardized, including the cross terms of shared events). In modes `holdout` and `none`, calibration observables with σ_i⁽⁰⁾ = 0 and ρ_i = 0 have variance and covariance both 0 in V_data^unc and R_ii also 0, contribute nothing to the ratio, and are therefore removed before standardization; this gives the same result as computing with the Schur complement without standardization.
- **Validation side**: C̃⁽⁰⁾ is Ũ_⊥ᵀ C̃_r^data Ũ_⊥, and R is likewise projected onto Ũ_⊥. When the denominator of a direction is 0: if R is also 0 in that direction, the ratio is recorded as 0; otherwise it is recorded as ∞ and the contract is rejected.
  - C_r^data is the residual covariance with data noise only, composed only of data noise per the formula of §9.2; it is different from the C_r⁽⁰⁾ used by the declaration check of §9.2, which contains V_MC etc. but no rounding.
  - Σ_β is taken from one design-stage Asimov fit **with data noise only**: V_MC = V_emu = V_learn = 0, and the MC nuisances of non-Gaussian blocks (Barlow–Beeston-lite and MC auxiliary binomial) are fixed at their nominal values and do not enter β, that is, the simulation statistics are treated as infinite. This is different from the Asimov Σ_β used for gates in §8.1. So the decision does not change with the MC budget.
- **Cross-validation**: both sides are the same set of observables, and both items are checked.

**Evaluation points**: σ⁽⁰⁾ and C̃⁽⁰⁾ change with θ, so the decision is made **when the contract is locked**, taking the worst case.

- The computation points are combinations of θ points and nuisance points:
  - The θ points include the same set of Sobol scan points used by P5 in §6.7 and all vertices of the θ prior box (when the θ dimension is > 10, a local maximization starting from the worst point of the scan is done instead);
  - At each θ point, ν, η and profile-mode φ take their nominal values, and also ±2σ along each of these nuisance axes in turn (only one moved at a time) (D36).
- The decision is fixed before the fit and does not change with the §7.3 iterations.
- **Recomputation at the fit point**: after §7.3 converges and before the validation data are opened, it is recomputed once more at the fit point (θ̂, ν̂, η̂, φ̂ in profile mode), and σ_i⁽⁰⁾ > 0 is checked for the observables listed in §5.2 (θ̂ may fall outside the sampling boundary but inside the physical boundary).
  - If it does not hold, this is treated as a contract error: the contract is rejected, the calibration fit is void, and the validation data are not opened.
  - This recomputation is executed by `calib_fit.py` after §7.3 converges, calling the same implementation in `calib_data.py`, and the result is written to the record; `calib_data.py` opens the validation data for that κ only when a record exists showing that this recomputation passed (§9.2, §14).

**When it does not hold**: the contract is rejected (`calib_contract.py check` calls the decision of `calib_data.py`, exit code 2); a release with sufficient resolution must be used instead, or the observables causing the violation must be removed; the rejection occurs before any result is produced and before any validation data are opened.

- The handlings "decide as untestable" and "move out of T_v" are not adopted: each such handling opens new boundaries between per-observable/per-direction, calibration side/validation side, and decision time. Cases where the rounding is too coarse but the observable needs to be kept are listed as an open question in §19.
- A contract re-declared after excluding untestable observables is likewise decided by this item (§5.2, §9.2).

**When it holds**: it is sufficient to include the rounding as ρ²/12. Design-stage trial computation: on the boundary where the condition just holds (|c| = 1 − 25ρ̃², ρ̃ = 0.02–0.2), the size of T_v for each true value is 0.046–0.058.

**Rounding correlations along lineage** (for example f and 1 − f, or m derived quantities sharing the same rounding) are not modeled separately: the per-value ρ²/12 overestimates in some directions and underestimates in others. When m derived quantities share the same rounding, the difference is at most (m − 1)ρ²/12; under the condition above, for m = 2 this corresponds to ≤ 0.4% of the variance in the tested direction, and for general m to ≤ 0.4%·(m − 1). Shared rounding with m > 5 must be modeled explicitly in V_data^unc as a fully correlated term.

**Rounding in toys**: the toys of the declaration check and of the rank condition (§9.2 (a)(c)) do not apply rounding; the toys of the T_v calibration and of the power apply the same rounding as the release.

#### Toys for shapes conditioned on the total

- **V stage**: the T_v calibration after opening and the power toys of the validation stage (V) are **conditioned on the observed N_obs**: each toy draws N_obs events from the multinomial distribution, and C_r and J_v are scaled with N_obs ("C_r and the observed total in holdout"), the same construction as the statistic of the actual data.
- **Design stage (P7)**: there is no N_obs, so the N_decl declared by the contract is used instead: each toy draws N_decl events from the multinomial distribution, and C_r and J_v are scaled with N_decl. So P7 and the V stage are the same procedure, with the total taken as N_decl and N_obs respectively (§8.1).
- The total is ancillary under the null hypothesis, so the power that the V stage re-decides under N_obs is exactly the power of the decision rule actually adopted. When N_obs is much smaller than N_decl, the V stage may decide that the power is insufficient (`calibrated-unvalidated`); this is a consequence of the misestimated N_decl, not `incomplete`.
- **Unconditioned absolute-count shapes**: in the toys of P7 the counts are drawn from Poisson(N_exp), the same as the data model of the V stage.
- **Free-normalization event samples** likewise: the toys of P7 draw N_decl,s events per set (the known N_tot,s for samples that contain calibration observables), and the V stage draws N_tot,s events.

#### C_r and the observed total in holdout

θ_ref iterates to θ̂ per §7.3 (using only calibration data), so in `holdout` mode all of the above items are final before the validation data are opened, and C_r does not vary with the values of y_v. There are only two exceptions:

- Residuals of shapes conditioned on the total;
- Event samples that belong entirely to validation and are regenerated with N_tot,s at opening ("Event samples and normalization components").

**Scaling of the residuals of shapes conditioned on the total**: the covariance of the residual r = n − N_obs p(β̂) is N_obs(diag p − ppᵀ) + N_obs² G Σ_β Gᵀ (G = ∂p/∂β).

- The multinomial term within the shape is proportional to N_obs, and the parameter-propagation term within the shape is proportional to N_obs².
- The cross term between the shape and another validation observable o, Cov(r, r_o) = N_obs G (Σ_β J_oᵀ − A V_co), is proportional to the **first power** of N_obs. V_co is the shared-event covariance between o and the calibration data: o is not restricted by the block rules of the shape and may share events with calibration data, but only in cross-validation; holdout does not share events per §9.5, and this term is 0 in holdout. This term agrees with the −J_v A V_cv of the general formula of §9.2; the V_cv of the shape itself is 0 by the block rules. Since this subsection applies only to holdout (see "Cross-validation" below), the cross term reduces in practice to N_obs G Σ_β J_oᵀ.
- The same holds for the d_l of shift mode (§9.2): the shape component is ∂μ_v/∂φ_l = N_obs ∂p/∂φ_l, so the shape block of d_l d_lᵀ is ∝ N_obs², and the part between the shape and other observables is ∝ N_obs.
- At opening each part is scaled accordingly, and J_v is computed with N_obs. Equivalently, when expressed as the proportion r/N_obs, the multinomial term is ∝ 1/N_obs, and the propagation term and the cross term are both unchanged.

**Quantities that do not change with N_obs**: σ_i⁽⁰⁾, the rounding condition and the declaration check are always computed with the **expected** total, and do not change with N_obs after opening.

**Rank condition**: scaling does not change the exact rank. Rank condition (c) is decided with tolerance τ_num, using the expected total, at lock and at the recomputation at the fit point of §9.2 (before opening), and is not re-decided after opening. When N_obs differs from N_decl, the smallest eigenvalue after standardization changes (the multinomial term ∝ 1/N, the propagation term unchanged), but free-ω validation shapes always take the toy path (§9.2) and the size of T_v is calibrated by toys, so this affects only the power.

**When C_r is estimated by toys** (Ĉ_r, §9.2): the term-by-term scaling above does not apply.

- After opening, the toys for Ĉ_r and for the reference distribution regenerate the counts of the shape conditioned on the observed N_obs (the replicas and the other toy parts are generated before opening, §6.6); N_obs is a quantity required by the conditioning itself, not the part being tested.
- When this step fails after opening (for example insufficient budget, or the ratio test does not pass), it is a numerical failure: V is recorded as `incomplete` (§10.2 rule 0), redone with the next seed block per §7.3, and not written as `final`.

**Cross-validation**: the validation data are the calibration data already read, and the statements of this subsection do not apply (§9.3).

#### Finite simulation statistics in non-Gaussian blocks

- **Construction**: Poisson blocks may use Barlow–Beeston-lite; binomial blocks use an MC auxiliary binomial likelihood that keeps the pass and fail counts. If a Bayesian Beta constraint is adopted instead, the prior and the parametrization must be declared, and it must not be treated as the same construction as the auxiliary binomial likelihood of the profile likelihood.
- **Weighted MC**: for each binomial bin, Σw, Σw² and Σw³ of the passing and of the failing events (W_P, S_P, T_P; W_F, S_F, T_F) and their cross covariance V_PF must be provided (V_PF = 0 when pass and fail are disjoint sets of events with independent weights). With W = W_P + W_F and ε̂ = W_P/W, the MC auxiliary binomial likelihood uses the variance-matched effective counts n_eff = ε̂(1 − ε̂) W² / [(1 − ε̂)² S_P − 2ε̂(1 − ε̂) V_PF + ε̂² S_F] and k_eff = n_eff ε̂, and, when ε̂ = 0 or 1, n_eff = W²/(S_P + S_F) and k_eff = n_eff ε̂. The likelihood is L(ε) ∝ ε^(k_eff) (1 − ε)^(n_eff − k_eff) with real k_eff and n_eff (its normalization cancels in every likelihood ratio). When Σw²/Σw is the same for pass and fail this reduces to n_eff = W²/(S_P + S_F), k_eff = n_eff·W_P/W; that reduced form must not be used when they differ, and separate effective counts W_P²/S_P and W_F²/S_F must not be used as the binomial counts (both fail the acceptance of §8.7) (settled by computation, en/compute-D30.md; to be confirmed by the author).
- **Effective-count approximation**: must be validated by the simulation calibration of §8.7. G8 is affected by it, but within the range allowed by P5 its detection capability is limited; G8 passing does not mean that the approximation holds. The acceptance of §8.7 covers a binomial bin when, computed from expected values, k_exp = n_eff·min(ε, 1 − ε) ≥ 30 and Δ_sk = |γ₁ − γ₁,bin| ≤ 0.1, where γ₁ = [(1 − ε)³ T_P − ε³ T_F] / [(1 − ε)² S_P + ε² S_F]^(3/2) and γ₁,bin = (1 − 2ε)/√(n_eff ε(1 − ε)). The expected values are computed before the fit from the per-class weight moments E[w], E[w²], E[w³] of a design-stage MC sample that does not overlap with the nominal MC (§6.6), scaled to the nominal expected counts of the bin; they are not computed from the nominal MC of that bin, because selecting bins on their own fluctuations biases the in-scope ensemble. A class whose weight distribution has no finite third moment (Pareto k ≥ 1/3 on the class weights) has Δ_sk = ∞. A bin outside this range falls under "Unvalidated approximation" below (settled by computation, en/compute-D30.md; to be confirmed by the author).
- **Rejection**: with negative weights or without a valid approximation, this path is rejected, and a verifiable joint model is used instead.
- **Unvalidated approximation**: when the acceptance of §8.7 does not cover the construction (the weighting method or the count range is outside the scope of the acceptance), or when G8 makes no decision (screening level, or independent MC cannot be obtained), the approximation is treated as unvalidated: the result carries `closure-not-tested`, and the grade is capped at `calibrated-unvalidated` (§10.2).
- **profile**: these MC nuisances are profiled together with θ and are included in β (§9.2).

### 2.2 Parameter roles

| Role | Treatment |
| --- | --- |
| Calibration parameters θ | Fitted, with physical boundaries |
| Externally constrained parameters φ | Profiled by default; shift mode may be used only under the conditions of §5.5 |
| Conditioning parameters ψ | Fixed; when the uncertainty is not negligible, they are listed as φ instead |
| Model discrepancy ν | Standard normal constraint (§5.4) |
| Data systematic errors η | Standard normal constraint; the effects s_j are provided by the data release |
| Shape normalization ω | Free profiled nuisance, fitted only with calibration data; validation shapes and out-of-fold residuals in cross-validation are conditioned on the total and do not fit ω (§2.1, §9.3) |
| Discrete models M | Either enumerated (each fitted, the envelope taken) or absorbed (as a component of V_model), one of the two |

### 2.3 Observable roles

The calibration set, the validation set and the measurement set are mutually exclusive. The decision applies to the observable, not to the data set.

The calibration set and the validation set may share events only in cross-validation (in holdout the calibration release and the validation release must not share raw units, §9.5), and the sharing must be declared. The correlations between them enter the validation statistic (§9.2).

### 2.4 Terminology

- **Calibration**: using the calibration set to determine θ.
- **Validation**: a test that is fixed in advance and has sufficient power.
- **Tuning**: calibration that has not passed validation; the result reaches at most `calibrated-unvalidated`.

## 3. Abstract response model

The generic layer recognizes only seven kinds of objects: stage graph, mechanism, functional, control variable, reference, degeneracy mode, parameter index. Of these, only the stage graph and the reference take part in correctness decisions.

### 3.1 Stage graph and stochastic kernels

```latex
p(y \mid z, c;\theta) = \int \prod_{s \in \mathcal{G}}
K_s\!\left(x_s \mid x_{{\rm pa}(s)};\ \theta_s, c\right) dx
```

| Symbol | Meaning |
| --- | --- |
| 𝒢 | Directed acyclic graph (DAG) |
| pa(s) | Upstream nodes of node s |
| z | True state |
| c | Condition |
| θ_s | Parameters acting on node s (the same parameter may act on several nodes) |

Every node must declare the nature of its kernel: density, deterministic function, or black box.

**Injection-point splitting rule**: wherever a reference is injected, the nodes must be split so that the injection point falls exactly on the edge between two nodes. For example, "photoelectric conversion and gain" must be split into a PDE node and a gain node, and single-photoelectron injection falls on the edge between the two.

**Derivation basis (1): calorimeters and Cherenkov-type detectors**

| Abstract node | ECAL | HCAL | RICH | DIRC |
| --- | --- | --- | --- | --- |
| 0 Input | Beam or generator | Same as left | Same as left | Same as left |
| 1 Transport and deposition | Electromagnetic shower deposition | Hadronic shower; sampling | Traversal of radiator; Cherenkov emission (n, dispersion) | Traversal of quartz bar; Cherenkov emission |
| 2 Carrier generation | Photon generation (including Birks quenching) | Scintillation photons (including Birks) | Photons | Photons |
| 3 Carrier transport | Light collection, attenuation | WLS collection, attenuation | Optical propagation, mirrors | Total internal reflection; path ambiguity |
| 4a Conversion | Photoelectric conversion (PDE) | SiPM PDE | Photon detection efficiency | MCP-PMT PDE, TTS |
| 4b Amplification | Gain | Gain, saturation | Internal gain of the photodetector (MaPMT, HPD, SiPM, MCP-PMT) | Gain |
| 5 Electronics | Noise, ADC, saturation | Noise, time window | Threshold, time | TDC, threshold |
| 6 Feature extraction | Crystal energy | Tower energy | Light spots | Pixels and time |
| 7 Reconstruction | Shower energy | Weighted energy | Ring and angle | Likelihood of angle and time |

**Derivation basis (2): ionization and timing detectors**

| Abstract node | TRD | Tracker (silicon or gas) | TOF | μ detector |
| --- | --- | --- | --- | --- |
| 1 Transport and deposition | dE/dx plus TR photons | Ionization; multiple scattering in material | Scintillator deposition | Traversal of absorber; gas ionization |
| 2 Carrier generation | Ionization electrons | Electron-hole pairs, or primary electrons in gas | Scintillation photons (including emission time) | Primary electron clusters |
| 3 Carrier transport | Drift, diffusion | Drift, Lorentz angle, diffusion, attachment, charge sharing | Light propagation, attenuation, path dispersion | Drift, diffusion |
| 4a Conversion | — | — (silicon) / — (gas) | Photoelectric conversion, TTS | — |
| 4b Amplification | Gas gain | Preamplifier (silicon) / gas gain (drift chamber, TPC) | Gain | Avalanche gain |
| 5 Electronics | Shaping, ADC | Noise, threshold, shaping | TDC, slewing | Threshold, time, dead time |
| 6 Feature extraction | Clusters | Clusters or hits | Time points | Hits and segments |
| 7 Reconstruction | Likelihood | Tracks | β | Segments, matched with the tracker |

**Liquid argon (calorimeters and TPCs)** is listed separately, because it has two structures that gas trackers lack:

- Node 2: ionization produces electron-ion pairs and scintillation light. **Recombination** distributes the energy between the charge and light branches in an anti-correlated way; recombination parameters (for example the parameters of the Birks or box model) belong to "nonlinearity / 2" and vary with the electric field.
- Node 3: drift, diffusion, electron attachment (electron lifetime).
- Node 4b: single-phase has no amplification; dual-phase TPCs have electroluminescence amplification in the gas phase.
- The light branch forms a separate DAG branch (light collection → PDE → gain), merged with the charge branch at reconstruction.

**Timing detectors**: the time resolution of MRPCs comes mainly from the jitter of the avalanche process (time / 4b). For LGADs it comes mainly from the Landau term caused by non-uniform ionization (nodes 1–2), and secondarily from avalanche jitter and time-walk (4b, 5).

**Cross-event effects**: cross-event effects such as dead time in μ detectors and pile-up in calorimeters are approximated in this workflow only by "conditioning variables" (for example efficiency conditioned on event rate); correlations between events are not modeled (§1, §19).

**The stage graph has two layers**

- **Semantic layer** (contract): nodes, edges, kernel nature, mapping of parameters to nodes, injection edges.
- **Implementation layer** (plan):
  - kernel registration: density kernels provide `log_density`, deterministic kernels provide `run`, samplable nodes provide `resample`;
  - stored products and their granularity;
  - when g4sim is used, the g4sim object each node maps to (node binding, §11.4).

### 3.2 Mechanism vocabulary

| Mechanism | Standard parameterization | Common nodes |
| --- | --- | --- |
| Input distribution | Parameters of the probability density | 0 |
| Geometry and material | Length, density, sampling fraction, alignment | 1, 7 |
| Physics process parameters | Cross-section scaling, model-internal parameters, production thresholds, multiple-scattering parameters | 1 |
| Yield | Multiplicative factor | 2, 4a |
| Fluctuation | Poisson / Fano, excess noise factor, sampling fluctuation | 1, 2, 4b |
| Nonlinearity | Quenching (Birks), space charge, saturation | 2, 4b, 5 |
| Transport and diffusion | Attenuation length, diffusion, deflection angle, reflectivity, attachment | 3 |
| Time | Emission time, propagation speed, TTS, avalanche jitter, slewing, offset | 1, 2, 3, 4a, 4b, 5 |
| Noise and threshold | Width, rate, threshold | 5 |
| Sharing and crosstalk | Sharing fraction, crosstalk coefficient | 3, 5 |
| Discrete model choice | Enumeration | 1–3 |
| Association | Assignment rules, combinatorial background, path hypotheses | 3, 6, 7 |

This vocabulary may be extended, but extensions require review. The engine's correctness decisions do not depend on the mechanism class.

### 3.3 Observables: functionals of the response distribution

```latex
y_k = T_k\!\left[\, p(\,\cdot \mid \hat z \in B_k,\ c \in C_k;\ \theta) \,\right]
```

- Binning is in the **reconstructed** control variable ẑ; data and simulation use the same reconstruction.
- There are seven classes of functionals: location, core width, tail, efficiency, multiplicity, shape, correlation (including two-dimensional shapes).
- The link function is chosen according to the range of each observable; it is not determined by the seven functional classes alone. For example:
  - tail probabilities use logit; signed correlation quantities cannot use log.
  - Normalized shapes must use the alr / ilr vector link of §2.1 (K−1 dimensions), acting only on the prediction side. The data side defaults to the count likelihood; only under the conditions of §2.1 is it represented by a Gaussian summary statistic on the K−1-dimensional coordinates, keeping the full covariance. Dropping one component and applying logit to each remaining one separately is not allowed.
  - Pearson correlation coefficients may use the Fisher z link, with the endpoints checked.
- The effective sample size of a tail-type functional is computed locally within that functional's determining region.

### 3.4 References and the directed reachability condition

A **reference** is a "known quantity" in the data, defined on an **edge**: it makes the quantity flowing along that edge known (a known value or a known distribution).

**Conversion relation**: an injected signal (LED, laser, light source, pulse) and the actual physical signal may differ in spectrum, angular distribution and time structure. Every mid-chain injected reference must declare its conversion relation to the physical quantity, for example S/S₀ = (R/R₀)^α for laser monitoring; conversion parameters (such as α) are listed as φ, with their source. The checker rejects an injected reference that does not declare a conversion relation.

A **redundant measurement** is represented by a **comparison node** d: the upstream of d is two observation nodes o₁, o₂ that measure the same true value (for example the times of two counters in the three-counter method, or two hits of overlapping modules), and the reference lies on the output edge of d. The reachability condition is applied with d as the observation node (see below); it is still only a necessary condition.

Comparison nodes get no additional constraint based on parameter semantics (for example "may only constrain widths and relative offsets"). Which directions cannot be constrained through d is decided by the Fisher information in P3 and G5:

- If the output distribution of d is invariant along some parameter direction (for example the common T0 offset of two counters, or the common gain scale of two overlapping modules), the Fisher information is zero along that direction, P3 then decides it is not identifiable, and gives a hint via "Common mode of redundant measurements" in §3.5.
- The same decision naturally covers the cases where relative offsets (for example the T0 difference of two counters) and relative scales (for example the relative gain determined by the energy ratio of overlapping modules) can be constrained.

The edge on which a reference lies:

- Known input: on the edge flowing into the root node.
- Mid-chain injection: on the edge between the two nodes after splitting.
- References acting directly on observables (internal constraints, population features): on the edge flowing out of the observation node.

| Reference type | Examples | Inherent limitation |
| --- | --- | --- |
| Known input | Beam energy, known momentum | The uncertainty of the input is listed as φ |
| Mid-chain injection | Light source with known photon number, LED, single photoelectron, pulse | Only parameters downstream of the injection edge can possibly be constrained |
| Internal constraint | Known resonance mass, measurement from another subsystem | Depends on upstream calibration (referenced by hash) |
| Redundant measurement | Overlapping layers, three-counter method, energy ratio of overlapping modules | Can only constrain directions on which the output distribution of d depends (usually width, relative offset, relative scale); common modes are decided by P3 / G5 |
| Population feature | MIP peak, cosmic rays, spectral edge | Feature position depends on the model |
| Tag and probe | tag-and-probe | Correlation between tag and probe causes bias |

**Directed reachability condition** (necessary condition): the reference lies on edge e, and the observation node is o. A parameter on node s **can possibly** be constrained by this reference through o only if both of the following hold:

1. e is upstream of o, or e is the output edge of o;
2. there exists a directed path from s to o that does not pass through e.

How this rule applies:

- On a straight chain, it is equivalent to "only parameters downstream of the injection edge can possibly be constrained".
- On merging branches (E/p), the momentum reference of the tracker branch can constrain the scale of the ECAL branch.
- When the reference acts directly on the observable, all ancestors of o can possibly be constrained.
- Single-photoelectron injection falls between PDE and gain: the gain can possibly be constrained, the PDE cannot.

Whether a parameter is actually identifiable is always decided by P3 and G5.

### 3.5 Degeneracy modes (diagnostic hints)

When P3 and G5 decide that something is not identifiable, the engine uses the table below to explain possible causes and to suggest ways to break the degeneracy. This table does not take part in decisions.

| Mode | Structure | Example | Signal needed to break it |
| --- | --- | --- | --- |
| Binomial thinning chain | Count ~ Poisson(Y·ε₁·ε₂…); all distributions depend only on the product | Light yield × collection efficiency × PDE | Inject a reference with known photon number between two adjacent stages. A k-stage thinning chain needs k−1 mid-chain injection points **plus** a known input at the top of the chain (or an equivalent absolute-scale reference) to be fully separated |
| Poisson stage × subsequent gain | Mean ∝ N·G; relative width ∝ √(F/N) | Number of photoelectrons × gain | Width can separate N/F from G; gain fluctuation (ENF) can be constrained by the single-photoelectron spectrum, while the Fano factor of the production stage needs a separate constraint. TRD does not fit this mode: the π width is determined by the Landau fluctuation of dE/dx, and electrons additionally include the TR photon number and spectrum, so the width alone cannot separate TR yield from gain |
| Addition in quadrature | σ² = Σσᵢ² | Resolution terms | The terms scale differently with the control variable, and the range is wide enough |
| Offset mixed into width | An uncorrected offset broadens the distribution | Alignment and resolution | Signed observables |
| Sum of two terms varying with different variables | Mean = a(v₁) + b(v₂) | Lorentz angle and alignment; T0 and x/v_eff; t₀ and the r–t relation | Vary v₁ or v₂: incidence angle, magnetic-field polarity, hit position |
| Scale and response shape | E_rec = a·E·r(E; b) | Non-compensation (power law), energy loss in dead material | At least three control points spanning the range; use e and π samples together; the functional form of r must be declared |
| Refractive index and geometric scale | Ring radius ∝ f·tan θ_c(n, β) | RICH n and focal length | Use several β (different momenta or particle species) |
| Efficiency, threshold and noise | The three jointly determine the pass rate | All detectors with thresholds | Threshold scan, multiplicity distribution |
| Common mode of redundant measurements | The output of comparison node d depends only on the difference or ratio of o₁, o₂ | Common T0 in the three-counter method; common gain scale of overlapping modules | Another reference acting on a single branch: known input, internal constraint or population feature |

### 3.6 Cost rule: choice of method

The method is chosen in two steps:

1. `calib_chain.py` derives **candidate methods** from node properties.
2. `calib_design.py` decides the **final method** from feasibility (P5).

| Method | Candidate condition | Cost tier | Feasibility |
| --- | --- | --- | --- |
| Analytic reweighting | Kernel has a density; inputs and outputs are stored; support condition holds | Low | Predicted ESS at the worst point within the prior reaches the P5 threshold |
| Step-level reweighting | Physics process parameters; per-step data stored | Low | Same as above; usually infeasible for multi-step processes such as showers |
| Learned density ratio | High-dimensional input, no analytic density; limited to post-hoc correction models | Low | Same as above, and subject to the G4-L check |
| Rerun (deterministic) | Deterministic kernel; inputs stored | Medium | Storage cost acceptable |
| Resimulation | Samplable black-box kernel (for example Geant4 particle transport); inputs stored | High | Decided by the plan: resimulate directly for few points, build a surrogate model for many points |
| Surrogate model | Resimulation-tier parameters, many evaluation points | High | P6 |

For analytic reweighting weights, the denominator is the density actually used to generate the events:

```latex
w_i = \frac{\displaystyle\prod_{s\in S_\theta} K_s\!\left(x_{s,i}\mid x_{{\rm pa}(s),i};\theta'\right)
\prod_{s\in S_q\setminus S_\theta} K_s\!\left(x_{s,i}\mid x_{{\rm pa}(s),i};\theta_0\right)}
{\displaystyle\left[\sum_j c_j \prod_{s\in S_q} q_{j,s}\!\left(x_{s,i}\mid x_{{\rm pa}(s),i}\right)\right]
\prod_{s\in S_\theta\setminus S_q} K_s\!\left(x_{s,i}\mid x_{{\rm pa}(s),i};\theta_0\right)}
```

The numerator is the density of the target distribution on the affected nodes; the denominator is the density with which the events were actually generated: the proposal distribution (or mixture) on S_q, and the nominal kernel on S_θ∖S_q. Check: when S_q is empty and θ′ = θ₀, w = 1.

- S_q: the set of nodes on which the proposal distribution is broadened.
- c_j = n_j / N (balance heuristic).
- The denominator of every event is recomputed with all q_j, old events included.

**Feasibility is decided at the worst point within the prior, not only on the boundary**. With a mixture proposal distribution, the minimum ESS often occurs in the interior, so the prior range must be scanned with Sobol points. For example, for Poisson count reweighting, N_eff/N ≈ exp(−Σ_ch μ_ch (r−1)²); with μ = 1000 and r = 1.1 it is only 4.5×10⁻⁵, which is infeasible, and the next-tier method is used automatically.

**When g4sim is used**, candidate methods are derived from the location of the parameter in g4sim (§11.4 Table 2), not specified by hand; `calib_chain.py` reads the node binding and the parameter location and then gives the candidate methods.

**Alignment** comes in two kinds, with different methods:

- **Alignment assumption on the reconstruction side** (module positions used in reconstruction): acts on the reconstruction node; uses rerun (deterministic).
- **Misalignment of the simulation geometry** (g4sim `alignment-overlay/1`, S9): changes the physical part of the IR, produces a new `geometry_id`, acts on node 1; uses resimulation. Its granularity is a logical placement, not a touchable (§11.4 Table 2).

### 3.7 Parameter index and conditioning structure

Each parameter is located by three coordinates: mechanism class × channel set × conditioning structure. There are four conditioning structures: constant, piecewise independent, parameterized function of the condition, partial pooling (implemented in phase 5).

When g4sim is used, the **channel set** is represented by a cellID field dictionary (or its mask) of `readout-encoding/1`, the same representation as the expanded selection list in the request after g4sim parsing. It must not be represented by the cellID integer itself, because cellID integers of different readout systems can be identical.

A scope is a region in the condition space.

---

## 4. General architecture

### 4.1 Layers

| Layer | Can it change decision logic? | Belongs to |
| --- | --- | --- |
| Abstract response model | Yes (the only layer that can define concepts) | `contracts/` |
| Generic engine | Yes | hep-statistics |
| Detector type | No, it only fills in values | hep-detector |
| Experiment instance | No, it only fills in values | each experiment's profile |

### 4.2 Pipeline

```
A0 Pre-check (not a gate)  On calibration data, check for each acceptance threshold "whether the data itself can reach it"; results written into the contract draft
A  Contract lock           calibration data release hash · validation data commitment hash · alternative hypotheses
B  Design                  plan · P0 P2 P3 P4 P5 P6 P7 P8
C  Method                  G8 closure test
D  Fit                     reference-point iteration · multi-start · G1 G4 G4-L G7
E  Adequacy                G2 G3 G5 G6 G9
F  Validation              open validation data (verify commitment hash) · global test · per-item diagnostics
G  Result                  calibration-result · nuisance export · dependency graph
```

- Whether a pipeline stage has failed is decided only after all gates within that stage have run to completion.
- After a failure, the revision follows the gate's **remedy level** (last column of §8.2):
  - **Change the plan**: completed results are not invalidated; only the affected gates are rerun.
  - **Change the contract**: open a new version; old results are invalidated.
  - **Engine fix**: when a gate reveals an error in the engine itself (not a problem of the contract or the plan), fix the engine, bump the engine version, and rerun all gates.
    - The result records the engine version used; this does not count as a revision of the contract or the plan.
    - The engine version is part of the validation configuration κ: if the validation data has already been read by the validation statistic of an old engine version, the fixed result goes at most to `calibrated-unvalidated` (§9.5 "Validation data can be used only once").
    - Before opening, fit reads made by an old engine version or an old plan through the calibration release declared by this contract do not fall on the holdout's validation units (the holdout's calibration release and validation release do not share raw units, §9.5), so they do not affect the fixed holdout.

---

## 5. Contract, data and plan

### 5.1 Three kinds of objects

| Object | Content | Lock |
| --- | --- | --- |
| `calibration_contract` | Stage graph semantics, parameters, models, observable definitions and roles, references and injection edges, estimators, V_model components, validation settings and alternative hypotheses, thresholds, use, scope, data hashes, A0 result summary | Hash locked before opening the validation data |
| `data_release` | Values of the observables and their declarations (see the list below) | Calibration data: readable before the lock. Validation data: only a commitment hash; opened only after the lock |
| `calibration_plan` | q, design points, event budget, seeds, kernel registration implementation, storage and granularity; when g4sim is used, also the node binding (§11.4), each design point's `run_id` and global event interval (§6.6), and the recording level (§6.1) | Not locked |

Contents of `data_release`:

1. Values of the observables.
2. The `systematic` component of the uncorrelated errors. The statistical component is recomputed by this workflow at θ_ref per §2.1; V_data^unc is the sum of the two, plus the rounding term ρ_i²/12 of §2.1.
3. Effects s_j of correlated systematic errors.
4. **Declaration** of events shared with other data releases (which events are shared). Cross covariances (for example V_cv between calibration and validation) are not release content; they are produced by this workflow per §2.1 by the event-level parametric bootstrap at θ_ref.
5. Source declaration for each component of the uncertainty table (`observed` / `expected` / `systematic`, §2.1):
   - `systematic` is submitted separately from the observed values;
   - `observed` and `expected` are sealed together with the observed values and are not used (the statistical error is recomputed by this workflow);
   - the correctness of the source labels is the publisher's responsibility; the submitter is recorded (§2.1).
6. Relative systematic errors: declared as a single proportion, or as a function, declared in the contract, of the prediction or of a binning variable; the correlation structure is also declared (fully correlated or bin-wise uncorrelated, §2.1).
7. Representation format (floating-point type or published digits) and derivation relations.
8. Whether each observable has a value, and the reasons for untestability (submitted together with the commitment hash, without revealing the value, §5.2, §9.5).
9. Data status, including "whether it comes from simulation": the output of g4sim and the output of other simulation studies are not data (§10.2 rule 2).

The A0 result summary records only "which thresholds are unreachable on the data", not data values, so it does not violate "the contract contains no data values".

**Model identity** (when g4sim is used): the model is "everything other than θ and φ". So model identity cannot directly use the `geometry_id`, `request_id` computed by g4sim for some set of values: those identities change with each design point and with the written-back θ̂. Each model in the contract's `models` is identified by the following five items, which are locked together at the lock:

| Item | How it is computed |
| --- | --- |
| Masked hash of detector-spec | `detector-spec/1` is normalized by g4sim's read procedure, then the fields holding θ, φ in the contract's `parameters[]` (specified by JSON Pointer) are replaced with fixed placeholder values, and the hash is computed with `canonical_sha256`. When the model applies an `alignment-overlay/1` (g4sim S9), the overlay is a separate document applied to the expanded IR, which no item covers on its own, so it is folded into this item: the overlay document is hashed the same way, with `description` and `source_of_facts` removed and the `delta_mm` and `zyx_deg` entries that hold θ, φ masked, and the item is the pair of the two hashes. The IR's `alignment` field (the overlay's full SHA-256) is a derived value and is never hashed. A model without an overlay and a model with an overlay of zero shifts are different models (g4sim gives them different `geometry_id`s), so a plan that varies alignment applies an overlay at every design point, the nominal point included (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md §1.3, W1; D86) |
| Masked hash of simulation-request | Same as above (parameters of the source distribution can be θ, φ) |
| Masked hash of the run card physics settings | All top-level blocks of `g4sim-run/1` except `run` and `output` (that is `physics`, including `physics.fast_sim` (g4sim S8), `kill_policy`, `accounting`, `field_integration`, `placement_impl` (g4sim S8) and, in legacy mode, `ui_commands`), with θ, φ fields (for example cuts, maximum step length) masked likewise; **excluding** the `run` block (`events`, `first_event`, `logical_run_seed`, `seeds`, `seeding`, `mode`, `threads`, `chunk`), because G7, G8 and validation must change seeds and event intervals per §6.6, and the number of threads and `chunk` do not change the output (g4sim §10.2) |
| Masked hash of `response-pipeline/1` | The stages and their parameters, **excluding** the top-level `run_seed` and `replica` (they are seeds, §6.6), with θ, φ fields masked (for example gain, `light_yield_per_MeV`, `resolution_scale`; the PDE is not a `response-pipeline/1` field but the efficiency of the sensor optical surface, §11.4, or, under the PDE split of §6.7, a θ or φ of the evaluator's job builder). Efficiency maps: in fixed-map mode, includes the efficiency map hash (`efficiency_map.map_sha256` of the map as built); in the mode where the map varies with θ, includes instead the settings of the mapping run (the segmentation, the masked hashes of the mapping run's three g4sim specifications, whose `run` block, holding the photon number as `run.events`, is excluded as above, and the component), with the efficiency map hash masked (§6.7). Under the PDE split of §6.7 with a PDE(E) (route 3), it also includes the PDE(E) table, hashed with `canonical_sha256` after removing `description` and `source_of_facts`, with the entries that hold θ, φ masked (JSON Pointer), and, in the fixed-map mode, the SHA-256 of the bytes of the efficiency-1 mapping run's `photons.csv`; in the mode where the map varies with θ, the `photons.csv` hashes are masked like the map hash, and the mapping-run settings stand for them (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md). The map's own `hashes.mapping_run_id` is the mapping request's `request_id`, not its `run_id`, so the plan records the mapping run's `run_id`, seed and interval itself (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md m9). A `condition-snapshot/1` (g4sim S9) enters no g4sim identity (not the IR, the request, the run card or `run_id`), although it changes the response, so it is folded into this item when conditions are applied: it is hashed with `canonical_sha256` after removing `description` and `source_of_facts`, with the row values that hold θ, φ masked (JSON Pointer `/iovs/<k>/rows/<j>/<quantity>`), together with the plan's rule that gives each event its time (`event_time_ns`, §6.6), because a different time can select a different IOV (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md §1.3, W1; D86). A `g4sim-digi-job/1` (g4sim S8) is a document derived from `response-pipeline/1`, the efficiency map and the snapshot; it is not hashed for the model identity; the evaluator builds every job from the hashed `response-pipeline/1`, the map (or the replica of §6.7) and, when conditions are applied, the snapshot (hashed as above, D86), and `calib_design.py` checks that the job's stage, sensor, electronics, timing and channels equal those documents at the evaluation's θ, that its efficiencies are the map's (replica 0) or the declared replica's (g4sim's own, a joint-pattern or a route-3 replica, §6.7); under the PDE split of §6.7, times p (route 2₁), or, for route 3, the PDE(E)-weighted efficiencies and the integerised weighted transit histogram computed from the hashed `photons.csv` and PDE(E) table (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md), and that its `conditions` are the snapshot, with the job's SHA-256 in the execution record (§14.1) (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md). |
| `build_hash` and Geant4 environment | g4sim's `build_hash` (the SHA-256 of the `g4sim_run` executable file), plus the Geant4 version and the version of each Geant4 data set used, taken from the installation record. g4sim's `build_hash` alone does not change when shared libraries or data sets are replaced in place (accepted by the author, 2026-11-09; source en/g4sim-binding-check.md A7). The S8 features of `g4sim_run` (fast-simulation hooks and their models, `placement_impl`) are compiled into that executable, so `build_hash` covers them; the C++ digitization `g4sim_digi` (S8) is a second executable that no g4sim record hashes, and, being identical to the Python digitization (§6.6), it is an execution-environment item (§14.1), not a model item. |

- Masking is used only for this workflow's model identity; it does not change g4sim's own identity rules. `detector-spec/1` is read by `core/canonical.load_spec_json` with its type table, so different spellings of a value give the same hash. g4sim has no such reading procedure for the run card, the request or `response-pipeline/1`, so this workflow normalizes their numbers with a type table generated from their schemas before masking and hashing with `canonical_sha256`.
- The mask list is locked together with the binding of parameters to all specification fields.
  - If normalization produces expanded values, derived values or embedded ids that depend on θ, φ, the hash must be taken after rebuilding from "the specification template with derived fields removed", or they must be masked together via registered dependencies; masking only the original JSON Pointer and leaving the derived values is not allowed.
  - Masking an entire container to hide non-parameter physics settings is forbidden.
  - Changing the binding or the template rules is a contract change.
  - Whether the actual g4sim normalization satisfies this rule awaits integration testing and cannot be presumed from this document.
- For each design point, each resimulation and each write-back of θ̂, the actual g4sim identities (`geometry_id`, `request_id`, `run_id`) are recorded in the plan and in the result (§10.1); they do not enter the model identity.
- Changes to `provenance_id` (labels and sources) do not change the model identity.

### 5.2 Contract fields and checker rules

**Executor**: all checker rules in the table below are executed by `calib_contract.py check`. Three kinds of decisions in it call the implementations of other scripts instead of having a separate copy:

- decisions on the DAG and injection-point splitting: call the implementation in `calib_chain.py`;
- derivation of upstream roles: call the implementation in `calib_deps.py`;
- decisions that read release metadata, lineage or totals (ingestion declarations, rounding, n_min and block-conversion conditions, sample containment, N_decl / N_decl,s equality, "has a value" in cross-validation): call the implementation in `calib_data.py`.

Exception: the recomputation at the fit point (θ̂, ν̂, η̂, φ̂) after the fit has converged (`validation` row, §2.1) is executed after convergence in §7.3 by `calib_fit.py`, not as a run of `calib_contract.py check`: for the recomputation of rounding, σ_i⁽⁰⁾, N_exp, n_min and the block-conversion conditions it calls the implementation in `calib_data.py`, and for the redo of the N_d,c declaration check (clause 6) it calls the implementation in `calib_contract.py check` (D21).

| Block | Checker rules (summary; clauses after the table) |
| --- | --- |
| `stage_graph` | Must be a DAG; nodes are split at every injection point |
| `parameters[]` | Physical bounds and sampling bounds are separate; φ must carry a source; rejected if ψ has a non-negligible uncertainty |
| `models` | Enumeration and absorption are mutually exclusive; the five g4sim identity items; confirmation record for physics lists (clause 1) |
| `source` (when g4sim is used) | The source of node 0 must be `density: analytic` (clause 2) |
| `observables[]` | Roles mutually exclusive; block rules; link functions; vector observables (clause 3) |
| `references[]` | Conversion relations of mid-chain injections; comparison nodes of redundant measurements (clause 4) |
| `estimators` | Data and simulation share the same implementation; true values not available in data must not be used |
| `model_discrepancy` | The kernel function must be positive definite; the inferred form may only be combined with `holdout` validation |
| `upstream[]` | Upstream results and usage; roles derived by `calib_deps.py` (clause 5) |
| `validation` | N_d,c; N_d and the list of unused observables; data release declarations; conditions for rejecting the contract; alternative hypotheses (clauses 6–10) |
| `acceptance`, `intended_use`, `scope` | Hash locked; compared per §10.2 |

**Clause 1: `models`**

1. The same model must not be both enumerated and absorbed.
2. When g4sim is used, each model must carry the five identity items of §5.1.
3. Before two physics lists are used as different models (enumeration, absorption or alternative hypothesis), a confirmation record must be attached that "the two actually use different models in the relevant particle and energy range" (g4sim §11 "Model uncertainty").

**Clause 2: `source` (when g4sim is used)**

1. The source of node 0 must be `density: analytic`.
2. `external` (HepMC3 or text event files) is always rejected (g4sim principle 7, S4 negative test).

**Clause 3: `observables[]`**

1. Roles mutually exclusive; block rules (§2.1).
2. Each observable declares a link function, and its range matches the range of the observable (the table in §2.1).
3. A quantity whose estimator (§5.3) is declared as "binned fractions of a normalized distribution" must belong to a **vector observable**, and must declare:
   - K and all K bins;
   - link: alr (with reference category) or ilr (with contrast basis);
   - data-side representation: count likelihood, or a Gaussian summary statistic meeting the conditions of §2.1 together with the merging rule.
4. The following declarations are always rejected: bins of the same normalized distribution declared as scalar observables; only K−1 bins declared; use of logit.
5. A sub-shape re-declared with the remaining bins after exclusion per §9.2 is not "only K−1 bins declared": it is a new normalized shape, with all K′ ≥ 2 bins declared. When K′ is insufficient:
   - for shapes conditioned on the total or represented in alr/ilr coordinates, when K′ = 1 there is no link coordinate, and the whole shape is left unused (D38);
   - for unconditioned absolute count shapes, when K′ = 1 the remaining bin enters as a Poisson count as usual; the excluded bins are put on the unused list per clause 7.

**Clause 4: `references[]`**

1. A mid-chain injected reference must declare its conversion relation to the physical quantity; the conversion parameters are listed as φ (§3.4).
2. A redundant measurement must be declared with a comparison node; the upstream of the comparison node must be exactly two observation nodes.

**Clause 5: `upstream[]`**

1. List each referenced upstream result (by hash) and its **usage** downstream: as φ center, nuisance posterior constraint, ξ, fixed value, ±1σ variation set, envelope.
2. The roles `central` / `variation` are derived by `calib_deps.py` from the usage (§10.2); if the contract separately writes a role that does not match the derivation, the contract is rejected.

**Clause 6: `validation`—calibration-side constraints by construction N_d,c (all modes, including `none`)**

1. All modes declare the exact constraints N_d,c that hold by construction among the calibration observables (§2.1 "Calibration-side constraints by construction"). When there are no such constraints, the declaration is empty.
2. The form of the declaration and checker rules (a)(b)(c) are the same as in §9.2, decided in the standardized coordinates of V_G. The decision is made twice, both times by the same implementation in `calib_contract.py check`:
   - at the lock: decided with V_data and the design-stage estimate of V_MC;
   - after the fit: redone at θ̂ with the actual V_G, together with the rounding condition, called by `calib_fit.py`. If it does not hold, the contract is rejected and the validation data is not opened.
3. The data-side constraint check is done at the lock on the calibration data, owned by `calib_data.py`.

**Clause 7: `validation`—constraints N_d on the validation residual space and unused observables (when the validation mode is not `none`)**

1. Declare the exact constraints N_d that hold by construction on the space in which the validation residuals lie:
   - `holdout`: on the validation observables;
   - cross-validation: on the calibration observables of each fold.
2. Neither the validation observables nor the calibration observables used for cross-validation may contain the untestable observables of §9.5: they must be excluded in the contract, and N_d is declared on the remaining observables. Containing an untestable observable means rejection; remedy level: contract.
3. N_d may be empty; for each item the construction must be written out: why the data and all predictions satisfy it exactly (§9.2). An item that acts on the data declares, in a contract field next to n_j, the constant c_j of n_jᵀ y = c_j used by the data-side constraint check of §9.2 (for example c_j = 0 for "total − sum of parts", c_j = 1 for f_A + f_B = 1); the declarations of N_d,c (clause 6) carry the same field (D66).
4. The declared n_j must be linearly independent. The checker first standardizes each n_j to ñ_j = S n_j / ‖S n_j‖, then decides by SVD; a ratio of smallest to largest singular value < 10⁻⁸ means rejection. So the conclusion does not change with units or with multiples of the same constraint.
5. The standardization scales s_i are not declared by the contract but produced by the model at θ_ref (§9.2).
6. **Unused observables list**: the contract separately lists the observables in the validation release that are not used (including the unused bins of partially excluded vector observables), and the reason for each item.
   - The reasons are an open enumeration and must cite the clause they rely on, for example untestable (§9.5), rounding condition (§2.1), rank condition (c) (§9.2).
   - Items whose reason is "untestable" are checked by `calib_data.py` against the release's "has a value" declaration; if an item declared to have a value is listed as untestable, the contract is rejected. Other reasons are only recorded.
   - The checker confirms that the list is exactly the observables registered in the validation release (the calibration release in cross-validation) minus those used by the contract.
   - The report also states the lineage of the validation release (whether it is a selection or derivation of another release). So the report is complete only with respect to the registered release, and the fact of a selected-subset release appears in the report.
   - This list is written into the result together with k (§9.5).
   - Unused observables affect only the report, not the grade, so there is no need to compare against the set difference of the parent release, and n_excl is not computed. "Limiting the grade by a threshold on the fraction of testable observables" is not adopted: the contract already decides the use of each observable, and with a fraction threshold, the denominator of the fraction repeatedly turns out to be an exploitable loophole (§9.5 "Reporting").

**Clause 8: `validation`—ingestion declarations of data releases**

A data release must declare the following items; if any one is missing, ingestion is rejected (§2.1):

1. representation format;
2. derivation relations;
3. sources of the uncertainty components;
4. correlation structure of relative systematic errors;
5. whether each observable has a value (missing values, only visually estimated values, and other reasons for being untestable, §9.5; submitted together with the commitment hash, without revealing the values).

**Clause 9: `validation`—conditions for rejecting the contract**

The contract is rejected when any of the following holds:

1. A calibration observable has only an `observed` statistical error and cannot be recomputed.
2. Rounding does not meet the negligibility condition of §2.1 (on the calibration side or the validation side; the worst case is taken over the evaluation points of §2.1—scan points, prior vertices and nuisance combinations).
3. The recomputation at the fit point (θ̂, ν̂, η̂, φ̂) after the fit has converged does not hold (§2.1).
4. The expected total of a validation shape is < 10: for a free-ω count shape this is the N_decl declared in the contract with its basis; for an absolute count shape it is N_exp (§2.1).
5. An unconditioned absolute count shape enters, while the contract field `sim_absolute_normalization` (§2.1 "Expected total of validation shapes" (ii)) of the corresponding simulation sample is "no" (a missing field is treated as "no").
6. An event sample containing calibration observables is not entirely contained in the calibration release (§2.1; compared by `calib_data.py` using event-level lineage).
7. A summary-statistic estimator lacks the value conventions for 0 / 1 events and for a denominator of 0 (§2.1).
8. The value conventions do not satisfy the declared N_d (§2.1).
9. All the observables that make up an "exact relation determined by the observed component totals" are used at the same time, in an event sample that belongs entirely to the validation data (§9.2); in samples that contain calibration observables the relation is declared as N_d or N_d,c instead (D27).
10. The holdout's calibration release and validation release share raw units (at release level, decided by lineage, §9.5).
11. A free-normalization event sample lacks N_decl,s and its basis, or the basis is an observed value and the check by `calib_data.py` finds them unequal (§2.1).
12. The n_min of a shape summary statistic and the block conversion conditions (non-shape observables sharing events: expectation ≥ 5 per bin, both nε and n(1−ε) ≥ 5) do not hold on the same set of evaluation points (computed by `calib_data.py`, §2.1).
13. σ_i⁽⁰⁾ = 0 for any of the following observables (at any evaluation point of §2.1, and in the recomputation at the fit point): validation observables, calibration observables used for cross-validation, and calibration observables with ρ_i > 0. Rationale: the data error enters only through η, and the standardization scale or the rounding ratio is undefined (§2.1, §9.2).

**Clause 10: `validation`—other rules**

1. Predictions are computed in double precision.
2. When the validation mode is not `none`: at least one alternative hypothesis (D32).
3. Alternative hypotheses may only be declared as simulation settings (unabsorbed discrete models or physical effects); any parameter-shift form is always rejected (§9.4). A contract that needs a block type the engine version does not support is likewise rejected (§6.7: contracts with non-Gaussian blocks before implementation phase 2).

### 5.3 Estimators

The computation conventions of each functional are written in the contract.

- On the prediction side of a shape Gaussian summary statistic, the expectation of the estimator under the data distribution is taken per §2.1; the MC is not normalized to the data size and then given the +½.
- The covariance between summary statistics is estimated per §2.1 by the event-level parametric bootstrap at θ_ref (events generated by the model, the same estimator applied to each sample), not by resampling the observed events.

### 5.4 Model discrepancy V_model

V_model consists of one or more components. Each component is a covariance R in link space (relative for log links, in the units of the observable for identity links), and they are added together:

| Component | R | Source of the size |
| --- | --- | --- |
| Model ensemble | The second moment of the differences d_a in link space of the absorbed discrete models relative to the nominal model, R = (1/A) Σ_a d_a d_aᵀ (not the sample covariance; when only one model is absorbed, R = d dᵀ), computed at θ_ref | Simulation, without looking at data |
| Correlation kernel | R_ij = f_{c_i} f_{c_j} C_{c_i c_j} ρ_{c_i c_j}(‖ẑ_i − ẑ_j‖_{M}), indexed by (observable group c, control variable ẑ), group = (functional class, link function) | Declared f, C, ℓ |
| Inferred | f, ℓ of the correlation kernel are fitted by the marginal likelihood (integrated over ν), with a weakly informative prior added (for example f ~ Half-Normal) | Only as a separate version; validation must be `holdout` |

Notes:

- The kernel is indexed by (observable group c, control variable); observable group = the combination (functional class, link function), because observables of the same functional class may have different link functions (§2.1).
  - f_c is declared in the units of that group's link space (relative for the log link, with units for the identity link), so location quantities and width quantities in the same bin each have their own amplitude.
  - Correlations between different groups are specified by C, **default 0**; nonzero is declared only when there is a genuine common physical source.
- ‖·‖_M is a metric on the control-variable space. With multidimensional binning, each dimension has its own correlation length: M = diag(1/ℓ₁², …).
- The inferred form does **not** fit f by the conditional likelihood of ν. In that case f·ν is not identifiable, and f runs off to infinity.
- Positive definiteness: ρ must be a positive definite function, and C must be positive definite; after combination it is checked numerically.
- Principal components: u_k = √λ_k·e_k, with (λ_k, e_k) the eigenpairs of V_model (the sum of its components) in decreasing order of λ_k. They are taken in this order up to the smallest K for which both conditions hold:
  1. the cumulative eigenvalues reach ≥ 99% of tr V_model;
  2. the discarded part V_⊥ = Σ_{k>K} λ_k e_k e_kᵀ, restricted to the calibration observables, satisfies tr(V_G⁻¹ V_⊥) ≤ 0.05. V_G is the covariance of the Gaussian blocks at θ_ref (§2.1), on N_d,c^⊥, without ν and η. For Poisson and binomial blocks, V_G⁻¹ is replaced by the expected Fisher information of the block in link space at θ_ref (settled by computation, en/compute-19-3.md; to be confirmed by the author).
  - Condition 2 is also evaluated on the validation observables, with the expected validation covariance (§9.2) in place of V_G (provisional, §19). All components may always be kept.
  - Why condition 2: condition 1 alone measures the discarded variance in link-space units. It ignores how precisely each observable group is measured, and with identity links it depends on the units. A discarded part that is ≤ 1% of tr V_model can still be many times the data error. It is then absorbed by no ν, and G6 rejects a calibration set that V_model describes correctly (on the toy detector, a G6 size of up to 0.75 at α = 0.01 with the 99% rule, and up to 0.07 with 99.9%).
  - Under condition 2 the size of G6 rises by at most 10% of α for every ndf ≥ 3 that P2 allows.
  - Truncation never lowers the power of G6: with fewer components the G6 statistic is at least as large for every data set, and the reference distribution does not change, because ν is constrained. Its only cost is size.
  - Basis: en/compute-19-3.md.
- The same set of ν acts on both calibration and validation.
- Correlation lengths are declared from physics and must not be chosen to make G6 pass.
- **Correlation kernels of normalized shapes**: f, C, ρ are declared in clr coordinates (clr(p)_k = ln p_k − (1/K)Σ_j ln p_j, K-dimensional, each row summing to 0), then mapped linearly to the alr or ilr coordinates declared by the contract (R_alr = H R_clr Hᵀ, H being the clr → alr matrix).
  - clr is permutation-equivariant over bins, so the model discrepancy does not change with the reference category or the bin order.
  - The model ensemble component is already linearly equivariant among the various log-ratio coordinates and is not affected.

**Known g4sim approximations**: the following differences are approximations that g4sim declares explicitly but that lie outside its guarantees. They are not MC noise; they must enter this workflow per the table below and must not be assumed to be zero.

| Approximation | g4sim basis | Handling in this workflow |
| --- | --- | --- |
| The scintillation photon-number formula is valid only within 0.15 ≤ r ≤ 1 (confirmed by the GB15 prototype at r = 0.15 and r = 1, g4sim S3) | g4sim §10.3, g4sim D10 | If the prior on r extends beyond the valid range: design points outside that range are always evaluated with the full `g4sim_run` and compared in P0; if this cannot be done, narrow the prior or list r as φ instead |
| Multi-component scintillation: g4sim §10.4 splits a bin's photons among components by a multinomial, while Geant4 truncates step by step, which also shifts the mean (g4sim addendum 11.1) | g4sim §10.4; g4sim S7 implements neither the component split in the digitization (`scintillation_event` takes one map) nor a validation run for more than one component (`validation_response_findings` refuses it), and does not export the size | This workflow digitizes such a material itself: a multinomial over components by their yield fractions, then each component through its own map with its own stage name (so each component has its own volume stream) (§19, C19). It measures the mean and variance differences in its own paired comparison of full optical tracking (Cerenkov off, nominal LY, extra yield variation off) and this digitization, and uses them as d_a (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md M4). Without that measurement, multi-component materials whose components have different maps cannot be evaluated through the efficiency map. |
| When the digitization LY differs from the nominal LY, the E^L / E^S split is only an approximation | g4sim §10.3; g4sim does not export the split error (`column_map.json` holds only the scorers and the volume-ID layout) | Checked by P0 at the extreme points of the prior, with the full `g4sim_run` plus response as `resample`. There is no bound for an a-priori feasibility decision. |
| When k_B changes, `edep_visible_ly_split` still splits by the nominal k_B, so the Poisson / Gaussian segmentation of the photon number and the variance v_b deviate | g4sim provides no error bound for this | Whenever k_B is calibrated and there are downstream nodes using the scintillation formula (whether or not LY or r is calibrated at the same time), P0 (P6 when these nodes are evaluated with a surrogate model, §8.1) must include the two extreme points of k_B within the prior, with the full `g4sim_run` plus response as `resample`. The bias is large when r is small (example: at r = 0.5 the variance after re-digitization is only about 0.26 times the true value), so this spot check cannot be omitted; it is also listed as an open question in §19 |
| Class-discretization error of `edep_by_dedx_class` | g4sim §9.1: relative bound k_B(b−a)/(1+k_B a) per class, four classes per decade of x. g4sim §9.1 says the bound is written into `column_map.json`, but the S3 code (`g4sim_simulate.py`) does not write it; `g4sim_simulate.reweighting_bound(rows, k_B)` gives the absolute bound per event and scorer. | Decided by P5 feasibility: the bound is computed with `reweighting_bound` at the **largest k_B within the prior** (the bound increases with k_B; the nominal value may be 0); propagated to θ via A it must be ≤ 0.1σ_tot^design, otherwise resimulation is used instead |
| Efficiency-map method vs. full optical tracking | §10.4 | Discrete model M (either enumeration or absorption); may also serve as an alternative hypothesis of §9.4 (of the "simulation setting" form). The full optical run of the comparison meets g4sim's validation conditions (`validation_findings`, `validation_response_findings`: Cerenkov off, RESOLUTIONSCALE = r, Birks declared, saturation on, by-particle-type off, nominal LY, no extra yield variation, one component) (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md m4); for a multi-component material the comparison is this workflow's own, per the multi-component row above, without the single-component condition; Cherenkov light, where it matters, is a separate node-1 term (g4sim §10.4 option (a) or (b)) |

### 5.5 Two modes for φ

| Mode | Procedure |
| --- | --- |
| profile (default) | Floats under its constraint |
| Shift | Fixed at the nominal value; refit once each at φ_l ± 1σ and ± 2σ; Δθ̂ and the response of the validation residuals (§9.2) are exported together |

Two conditions for shift mode (decided by `calib_shift.py` with gates P8, G9, §8.2):

1. **Information condition** (matrix form): after θ, ν, η are all profiled, the conditional Fisher information I_φφ·rest of the data for each φ in shift mode must satisfy that the largest eigenvalue of Σ_φ^{1/2} I_φφ·rest Σ_φ^{1/2} is ≤ c, default c = 0.1. c bounds the loss of precision, not the coverage: in the linear-Gaussian limit shift mode is unbiased and has nominal coverage for any information, and its total error exceeds the profile-mode error by a factor of at most √(1 + c) (§8.7 note 5).
2. **Linearity**: for each component θ_i and each shift-mode φ_l, let D_il(k) = θ̂_i(φ_l = k) − θ̂_i(φ_l = 0), k = ±1, ±2 (the G9 refits; the other shift-mode φ at nominal), a_il = ½[D_il(+1) − D_il(−1)], and s_i = √(σ_tot,i² + Σ_l a_il²), a normalization built from the symmetric responses (it equals the §7.5 total error if D52 adopts the symmetric difference). With c2,il = ½[D_il(+1) + D_il(−1)], c3,il = {½[D_il(+2) − D_il(−2)] − [D_il(+1) − D_il(−1)]}/6 and c1,il = a_il − c3,il (the cubic–quadratic interpolant through the four refits), the linearity measure is the excess of the prior-averaged second moment of the shift response over the linear model, Δ_i = [(Σ_l c2,il)² + Σ_l (2c2,il² + 4c1,il c3,il + 14c3,il²)] / s_i². The condition holds when Δ_i ≤ t_lin for every i, default t_lin = 0.06, locked in the contract. The test is one-sided: Δ_i < 0 (a response that flattens beyond ±1σ, so that the ±1σ responses overstate the spread) passes. No ratio and no separate rule for near-zero responses is used: a response that is small compared with s_i gives a small Δ_i (settled by computation, en/compute-19-2.md; to be confirmed by the author). It replaces the former tests "symmetry within 30%" and "Δθ̂(±2σ)/Δθ̂(±1σ) within 2 ± 0.3" (§8.7 note 5, D29).

**Applicability limits of shift mode**:

- Shift-mode φ must already be transformed into independent, unit-normal coordinates, block-independent of the external constraints in profile mode; original correlated parameters must not be varied ±1σ component by component and then directly combined by outer-product addition.
- A full correlated block may be whitened; if after whitening the coordinates mix shift and profile roles, the whole block uses profile instead.
- P8, G9 and the export must use the same transformation matrix.
- The rest in the information condition includes the remaining θ, ν, η, profile φ and MC nuisances; I comes from the data and other auxiliary measurements, excluding the external constraint of the shift φ being checked itself.

When both hold:

- the total error exceeds the profile-mode error by a factor of at most √(1 + c) (4.9% at c = 0.1) in the linear regime;
- the difference in central value is a **random quantity**, not an upper bound: its rms is √(c/(1+c))·|∂θ̂/∂φ|·σ_φ (0.30 times at c = 0.1), and about one third of data realizations exceed this value.

This difference is already contained in the ±1σ variation of shift mode, so it is **not** listed separately as a systematic error, to avoid double counting.

---

## 6. Computation plan and sample design

### 6.1 Analytic reweighting

1. q must have an analytic density that can be written out.
2. **Support condition**: supp q ⊇ ⋃_{θ′∈prior} supp K(·;θ′), that is, the **union** of all supports within the prior. Events that were filtered or zero-suppressed at generation are treated as missing support.
3. Reweighting is allowed only when the parameter acts entirely through the probability density of the kernel.
4. Weights are computed from the input and output of that node's kernel.
5. When the ESS at any point within the prior is insufficient, additional events are generated and merged with the formula of §3.6.

**Support and granularity when g4sim is used** (decided by `calib_design.py` from the run card, the request and the plan):

- The q of node 0 is the source distribution of the request, whose density is given by `source-density/1`. The truncation range that a `gaussian` distribution must declare is the support of q; when the support of any θ′ within the prior extends beyond the truncation range, the support condition does not hold.
- The following g4sim settings are all "filtering at generation" and are treated as missing support for the affected nodes and observables:
  - the minimum kinetic energy, time cut and secondary-particle deletion of the run card `kill_policy`;
  - the scorer's `time_window_ns`;
  - pruning by the truth retention rules (deposits of pruned particles are attributed to the nearest retained ancestor; the particles themselves cannot be reweighted);
  - zero suppression in response stage 5.

  They may be ignored only when the filtering condition does not change the observables for any θ′ within the prior (for example a time cut later than the time windows of all observables); this decision is written in the plan and confirmed by P0.
- **Recording level**: for nodes to be evaluated by reweighting or rerun, their inputs and outputs must be recorded as `column` or `event_file`. `moments` contains only linear quantities and cannot be used for reweighting or rerun.

### 6.2 Learned density ratio (phase 5)

- Used only for post-hoc correction models.
- Cross-fitting is used: the weights of each fold are computed by a classifier not trained on that fold.
- Classifier outputs must be probability-calibrated and corrected for the prior ratio.
- V_learn = the variation between repeated trainings + the square of the closure bias on held-out samples.

### 6.3 Rerun and resimulation

The intermediate quantities to store are inferred backward from the parameter list. A rerun of a black-box node is a resimulation, at the same cost tier as a surrogate model.

When g4sim is used, "the intermediate quantities to store" correspond to g4sim scorers and hits:

| Parameter to change | Required intermediate quantity | g4sim delivery |
| --- | --- | --- |
| Birks k_B | `edep_by_dedx_class` (deposits per bin classified by (kind, log x), kind ∈ {ionizing, nonionizing, photon, zero_length}, four classes per decade of x) | S3 |
| Scintillation yield LY, `RESOLUTIONSCALE` r | `edep_visible_ly_split` (E^L, E^S, n^L) | S4 |
| Parameters of response stages 2–5 | Hit files (`simulation-hits/1`), or stage hand-off files | S4; until the stage 2→3 hand-off is confirmed by g4sim (§19), parameters of nodes 3, 4a can only be re-digitized in full from hit files and cannot be reweighted between stages 2 and 3 |
| Reconstruction-side parameters | Column files converted from hits read by simreco | S4 |

Resimulation is executed with `g4sim_run`; each design point has its own `run_id`.

### 6.4 Surrogate model

- Design points are obtained from a Sobol sequence, and a portion is held back for P6. When nodes affected by k_B or r are evaluated with a surrogate model, the spot-check points of §5.4 (the two extreme points of k_B, etc.) are mandatorily included among the P6 held-back points and evaluated with full simulation (§8.1).
- Design points are generated by this workflow and written into the plan: `calib_design.py` generates the Sobol design points and the P6 held-back set, and `calib_emulator.py` generates the training set of the surrogate model (D80). When g4sim is used, each design point is expanded into a set of g4sim specifications (changing only the fields holding θ, φ) and handed to `geant4_run.py` to run by file path; g4sim only executes the point list and does not generate design points (for g4sim GL5 `scan`, see §19).
- The surrogate model interpolates the observables and their V_MC, and outputs V_emu. In the mode where the map varies with θ, it is a regression that does not pass exactly through the design points, and the efficiency-map error of the design points enters through the map term U(θ)φ_map, not V_emu (§6.7 "Two efficiency map modes", D28).
- Queries outside the domain are always rejected.

### 6.5 Order of method combination

From outside to inside: surrogate model or resimulation → rerun → reweighting.

### 6.6 Random numbers

- The same θ scan uses common random numbers. For the mapping runs of the "map varies with θ" mode, this is the default, and the plan may instead give each design point its own seed under the conditions of §6.7 "Two efficiency map modes" (D28, revised 2026-11-09).
- G7, G8 and validation always use new seeds.
- The pseudo-data of G8 form a closure test with real MC (§8.4):
  - for each injection point, one high-statistics MC (number of events ≥ 100 times nominal) serves as the true value;
  - for each set of pseudo-data, one MC of the same size as nominal, whose event interval does not overlap with any other use, fitted with the actual procedure;
  - when this cannot be done, G8 makes no decision, and `closure-not-tested` is added.
- **MC realization of toys** (see also §7.3 "Toy data and V̂"): see below.

#### MC realization of toys

**Scope**: the MC predictions of the following toys must carry MC noise that has the same structure as in the actual fit and is mutually independent:

- Ĉ_r;
- the reference distributions of T_v / T_cv;
- power toys (P7, the rejection rate of cross-validation, the V stage);
- the reference distribution of G6 and the χ̄² weight toys of G2 (§8.2, §8.5, including locally linear toys);
- toys of the interval construction of §7.5 (including the interval toys of each G8 pseudo-data set).

**Rationale**: otherwise the observed statistic contains the noise layer of the nominal MC while the reference distribution does not, and the test size is too large (example: with V_MC ≈ 0.1 V_data and k = 20 it is about 0.10, not 0.05).

The plan declares one of two constructions: **replica difference** (default) or **full**.

**Construction 1: replica difference (default)**

*Principle*:

- Each toy has a **truth point**. The true value of the toy is the prediction of the nominal MC at the truth point, m_nom(truth point) = μ*(truth point) + e_nom(truth point), and the toy data are generated from it.
  - μ* is the prediction without MC noise; e_nom is the noise of the nominal MC.
  - The nominal MC at the truth point is computed with the same events and common random numbers as the nominal fit.
- The prediction of the toy fit is the nominal MC m_nom(θ) plus that toy's own MC perturbation.
- In the residual of the actual data, the MC part is −e_nom(θ̂). The MC part of the toy residual is e_nom(truth point) − e_nom(θ) − perturbation; the first two terms cancel through common random numbers down to the difference caused by the distance between θ and the truth point (when the truth point is θ̂, they cancel completely at the fit point). So the perturbation must be an MC error **independent of e_nom and identically distributed**.

*Truth points of each kind of toy*:

1. **Toys under the null hypothesis** (Ĉ_r, the reference distributions of T_v / T_cv, including each fold of cross-validation): the convergence point of the nominal fit (θ̂, ν̂, η̂, φ̂, γ̂).
   - Shift-mode φ (§9.2) is not in the likelihood: each toy samples the true value of φ from its prior, the toy data are generated from it, and the toy fit still fixes φ at the nominal value. So Ĉ_r, Ĉ_{r,f} and the reference distribution contain the Σ_l d_l d_lᵀ part, consistent with §9.2 "In shift mode the size is a prior average".
   - Power toys likewise.
2. **Toys of the interval construction of §7.5** (actual data, and the interval toys of each G8 pseudo-data set): that scan point θ_s and the nuisances it profiles (§7.3: each scan point has its own reference distribution). The profile construction is used: the true values of ν, η are the profiled values at the scan point, and the constraint centers of the toy (auxiliary measurements) are sampled around the true values according to their constraints (this is what "sampled according to their constraints" in §7.3 "Toy data" means).
3. **Power toys** (P7, the rejection rate of cross-validation, the V stage): the true value under alternative hypothesis a is m_nom(θ̂) + s_a δ̂_a.
   - δ̂_a = m_alt,a − m_nom, computed at θ̂ with common random numbers (the same batch of events, the alternative simulation setting).
   - δ̂_a carries MC noise; using it directly makes the toys' noncentrality parameter on average too high by tr(C_r⁺V_Δ) (§9.4), so it is multiplied by s_a = √(max(0, w(ε̂) λ_a^low) / λ̂_a^single):
     - with toy replacement, w(ε̂) multiplies only the numerator (§9.2); without replacement, w = 1.
     - λ_a^low is the one-sided lower confidence limit of the cross product λ̂_a^cross of §9.4 (obtained from independent MC repetitions or a valid bootstrap, the same as the analytic path).
     - λ̂_a^single is the single-set value obtained from δ̂_a with the same formula.
     - So the toys' noncentrality parameter is not higher than the lower limit of the cross product, and the MC uncertainty of the lower limit is accounted for. The point estimate of λ̂_a^cross is not adopted: then the binomial lower limit of the toy rejection rate does not account for its uncertainty, and with a true power of 0.70–0.75 it would claim a lower limit ≥ 0.8 with probability 0.08–0.36.
   - When λ_a^low ≤ 0 or λ̂_a^single = 0, s_a = 0, the power equals α, and the power is decided to be insufficient.
   - The confidence level is split by Bonferroni per §9.4 between λ_a^low and the binomial lower limit of the toy rejection rate.
   - Here λ̂ is computed with the metric actually used by T_v: Ĉ_r, or, when §7.3 allows, the analytic C_r with V̂ substituted. In cross-validation, the metric of the fold-split statistic is used: E[r_f|a] (the expectation under the alternative hypothesis of the out-of-fold residual of fold f, in residual space; δ̂_a is a difference in prediction space) and the cross product are both computed fold by fold, λ = Σ_f E[r_f|a]ᵀ Ĉ_{r,f}⁺ E[r_f|a]. This is the only place where a λ̂_a computed with Ĉ_r (or with the analytic C_r with V̂ substituted) is used in a decision (§9.2).
   - The MC noise in the direction remains; this is approximation (3):
     - Under the fully whitened T_v of holdout it is conservative. When the metric is the true C_r, the toys' noncentrality parameter is exactly λ_a^low, independent of the direction noise of δ̂_a, and the conservativeness comes entirely from the lower limit λ_a^low. When the metric is the analytic C_r allowed by §7.3 (with V̂ substituted), the power depends not only on λ; the direction noise has a small effect, likewise checked by the acceptance tests of §8.7.
     - For the fold-split statistic of cross-validation, the power at the same λ varies with direction and is not guaranteed to be conservative; it is checked by the acceptance tests of §8.7 in the cross-validation configuration that includes inter-fold correlations.
   - In the design stage of P7, the design-stage θ_ref replaces θ̂.
4. **Pseudo-data of G8**: not under this principle; instead a closure test with real MC (§8.4) is used.
   - The true value is the high-statistics MC of that injection point, and the fit uses that pseudo-data set's own nominal-size MC, so misestimation of V_MC, effective-count approximations and evaluator bias all enter the bias and coverage of G8. Pseudo-data are not sampled from the likelihood model, because then G8 would not see these approximations.
   - Whether G8 can detect them depends on N_c and σ_MC/σ_data, reported by §8.7.
   - The interval toys of pseudo-data set g itself follow item 2, with the fit of pseudo-data set g (its MC and θ̂_g) as nominal.

*Replicas m_a, m_b*:

- Each toy (or pseudo-data set) uses two **of its own** full MC predictions:
  - generated with Geant4 event intervals that do not overlap with any other use or any other toy (new seeds; changing only the response does not count, see "Definitions when g4sim is used" below);
  - generated at the **generation point** with the same procedure and the same number of events as the nominal prediction (with the same reweighting or re-digitization steps);
  - when a surrogate model is used, each rebuilds the surrogate model with an independent set of design-point MC, so each copy is n_dp design-point MCs (§6.4);
  - on the learned path, each is retrained with independent training MC and a new initialization seed.
- The **generation point** is the convergence point of the fit that the toy imitates: θ̂ for toys of the actual data (the design-stage θ_ref for design-stage toys of P7), θ̂_g for the interval toys of G8 pseudo-data set g.

*Perturbation per block*:

- **Gaussian block**: the perturbation is (m_a − m_b)/√2, and the prediction of the toy fit is m_nom(θ) + (m_a − m_b)/√2.
  - The covariance of (m_a − m_b)/√2 is exactly V_MC (including direction and correlations) and independent of e_nom, so the MC error of the toy relative to its true value has the same distribution as −e_nom of the actual data.
  - When Gaussian and the noise of the nominal MC does not change with θ, it is exactly the same. When the noise of the nominal MC varies with θ (for example reweighting or a response scaled with θ gives the Jacobian MC noise), the actual fit has an errors-in-variables bias that the toys do not reproduce; this is approximation (1), tested by the θ-dependent configuration of §8.7 and bounded at design stage, for its bias, by P5 (§8.2 note 3; settled by computation, en/compute-19-13.md; to be confirmed by the author).
  - Whether or not conditioned on the nominal, **no MC noise model is needed**, and there is no offset shared by all toys.
  - "Nominal as the true value, a single replica as the prediction" is not adopted: then the MC error of the toy is e_rep − e_nom, with covariance 2V_MC, and the reference distribution is too wide (with V_MC/V_data = 0.1 and k = 20 the size is about 0.025).
- **Non-Gaussian blocks** (Poisson and binomial, entering the likelihood with MC nuisances, §2.1, §6.7): the toys do a parametric bootstrap of the whole likelihood.
  - The MC nuisance γ̃ at the truth point is used for both the data and the auxiliary measurement. The value of γ̃: for toys under the null hypothesis, the γ̂ of the nominal fit; for interval toys, the profiled value at that scan point; for power toys, γ̂; in the design stage of P7, 1 (that is, Asimov).
  - Poisson blocks: the toy data are generated from μ·γ̃; the toy's MC auxiliary measurement draws m* ~ Poisson(τγ̃) with the nominal τ = (Σw)²/Σw², Σw* = f Σw, Σw²* = f Σw², f = m*/τ. So the toy's MC estimate is centered on γ̃Σw, consistent with the toy data. Bins with τ = 0 have no MC events and are not sampled. f = m*/(τγ̃) is not adopted: it centers the MC estimate on Σw, counting the MC fluctuation once more.
  - Binomial blocks: following its MC auxiliary binomial likelihood (§2.1), with the nominal effective counts (k_eff, n_eff) of that likelihood and the efficiency nuisance ε̃ at the truth point, the toy draws n* = ⌊n_eff⌋ + B with B ~ Bernoulli(n_eff − ⌊n_eff⌋) (randomized rounding), then the number passing k* ~ Binomial(n*, ε̃); the number failing is n* − k*, and the toy's auxiliary measurement (k*, n*) enters the same likelihood ε^(k*) (1 − ε)^(n* − k*). The cross covariance enters only through n_eff. Bins with n_eff = 0 have no MC events and are not sampled. Sampling schemes different from the likelihood are not allowed; in particular continuous draws of k*/n_eff, plain rounding of n_eff, and drawing the efficiency from Beta(k_eff + ½, n_eff − k_eff + ½) are not used (settled by computation, en/compute-D30.md; to be confirmed by the author).
  - What is used is the model the likelihood already assumes, not an additional MC noise model; its applicability is the applicability of the block rules of §2.1. These blocks need no replicas.
- **The interpolation variance V_emu of surrogate models and the closure bias of learned models** (the surrogate model of §6.4 outputs the interpolated V_MC and V_emu separately; V_learn per §6.2 is the variation between repeated trainings plus the square of the closure bias):
  - The replica difference reproduces the part of the design-point MC noise propagated through the surrogate model, and the variation between repeated trainings.
  - V_emu and the squared closure-bias term are not event noise: the toys, in the same way the likelihood itself treats them as variances, each draw N(0, V_emu), N(0, V_learn^bias) once and add them to the prediction. So they are the same assumption in the toys as in the likelihood.

*Reuse of the perturbation and ownership of replicas*:

- The perturbation is computed at the generation point and reused across the §7.3 iterations of that toy and across all θ: additively for Gaussian blocks; for non-Gaussian blocks, the same f multiplies the nominal Σw and Σw² at that θ (no γ̂ at other θ is needed).
- For the folds of cross-validation, the same perturbation is reused at the θ of each fold.
- Each toy has its own pair of replicas; different toys do not share them.
  - The toys estimating Ĉ_r (§9.2) or Ĉ_{r,f} (§9.3) and the toys of the reference distribution are two sets, each with its own replicas.
  - When the same set of interval toys is used for different scan points, the toys at each scan point each have their own replicas, or they share the replicas of the same set of toys and change only the truth point; both are allowed, because the reference distributions of different scan points are each used independently.

*Remaining approximations*:

1. The perturbation is computed at the generation point and then reused at all θ, and the noise of the nominal MC between the truth point and the fit point cancels only approximately through common random numbers (the same kind of approximation as computing V_MC at θ_ref in §2.1);
2. the difference for Gaussian blocks guarantees only the covariance, not higher moments;
3. the alternative shift of power toys is unbiased only in the noncentrality parameter.

All three are tested by the acceptance of §8.7, on a toy detector whose MC noise is known and whose true value has no MC noise.

**Construction 2: full**

Same as the replica difference, but the two replicas are regenerated at every §7.3 iteration of that toy (the difference at the generation point is not reused), removing approximation (1). When resimulation is needed the cost is up to 30 times that of the replica difference (one pair per §7.3 iteration; the budget reserves the iteration limit 30, §6.7); when a surrogate model is used the two are the same, because the design points do not change with iterations.

**Rejected practices**: practices outside the two constructions are rejected by `calib_design.py` (remedy level: plan), including:

- re-digitizing with only the Philox changed;
- reusing the nominal MC without adding a perturbation;
- nominal as the true value, a single replica as the prediction (MC noise counted twice);
- sampling the MC perturbation of Gaussian blocks from models such as N(0, V_MC) (parametric construction).

**Acceptance and generation timing**:

- The T_v size acceptance of §8.7 is run with the construction declared in the plan.
- When T_v is calibrated with toys per §9.2 (always in cross-validation), the replicas of the toys for Ĉ_r and the T_v / T_cv reference distributions must be generated per the plan before the validation data is opened, and must pass the non-overlap check below. When this cannot be done (for example insufficient budget), the reference distribution cannot be computed, V is `incomplete` (except when the outcome is already determined, §10.2 rule 0), and the validation data is not opened (§9.2, §9.5). When k₀ = 0 no toys are needed and this does not apply.
- The following items do not read y_v (shapes conditioned on the total read only the observed total N_obs, event samples belonging entirely to validation read only N_tot,s, §2.1) and may be generated after opening: power toys of the V stage, the redo of the whole ensemble after a failed ratio test (§7.3), and replacements. When they cannot be generated:
  - power toys: handled per "power lower bound cannot be computed" in §9.4;
  - redo and replacement of Ĉ_r or reference-distribution toys: a numerical failure; V is recorded as `incomplete` (the ratio test of §7.3, §10.2 rule 0); it cannot be handled by abandon-power.

#### Definitions when g4sim is used

g4sim's random numbers have two layers, and the seed is the combination of the two layers.

| Layer | Determined by | Description |
| --- | --- | --- |
| Geant4 events | The run card's `logical_run_seed` and the global event interval [first_event, first_event + N) | `per-event` seeding: event i of seed S starts from the seeds (H(S, i, 0), H(S, i, 1)). For the same `build_hash` on the same platform, the same (`logical_run_seed`, global event number) gives the same event, whatever the number of threads and however the interval is split into runs. g4sim does not assume bit-identity across platforms, and §14.1 therefore keeps every ensemble on one execution environment. A fast-simulation hook (`physics.fast_sim`, g4sim S8) belongs to the run card's physics settings: attaching it, even with a model that never triggers, changed 28–33% of the events' deposits under the same (`logical_run_seed`, global event number), so runs with and without a hook, or with different models, never share common random numbers in this layer. |
| Response sampling | Philox key: the first 64 bits of SHA-256 of (`"g4sim-rng/1\0channel"`, `run_seed`, readout system, stage, replica) for channel streams, or of (`"g4sim-rng/1\0volume"`, `run_seed`, stage, replica) for volume streams. `run_seed` and `replica` are the top-level fields of `response-pipeline/1`. Counter: (global event number, cellID or volume ID, sub-index, output group). The sub-index is the segmentation bin in volume streams and 0 in channel streams. | The same event, the same key and the same draw order always give the same uniform variates. g4sim does not take `run_seed` from the run card, so this workflow sets `run_seed` equal to the run card's `logical_run_seed` in every evaluation. Efficiency-map replicas (g4sim S7) have their own volume key, built from the first 60 bits of the map's SHA-256, the stage name `efficiency_map/<component>` and the replica number, with counter (event 0, bin). They do not depend on `run_seed` or on the event, so replica r of a map is the same in every run. Replica r of two different maps are therefore independent draws, also when the two mapping runs shared their photons; replicas that must be coupled across the design points of a scan are drawn by this workflow (§6.7, joint-pattern replicas), with its own key prefix `"calib-map-joint/1"`, never by changing a map document or g4sim's key. The C++ digitization `g4sim_digi` (g4sim S8) uses the same keys, counters and draw order as `core/simulation/digitize.py` (identical at all three levels of g4sim §10.2 on the S8 fixtures), so choosing it changes no random stream; it is an execution-environment item (§14.1). On the `g4sim-digi-job/1` path the channel-stream counter is volume ID × C + c (C the job's channels, in order), not the readout's cellID; the keys are computed by `digitize.job_with_keys` from the job's `run_seed` and `replica`, and `g4sim_digi` uses them without reading `run_seed`. Condition snapshots (g4sim S9, applied only by `digitize.py`) move no draw: every draw is still made, `gain_factor` scales the sensor gain, `threshold` replaces the electronics threshold and a dead channel reads no code. |

- **Common random numbers**: both layers are the same. When θ acts only on the response, the same batch of Geant4 events is re-digitized with the same Philox key. Within one readout system, all evaluations of one ensemble, and all re-digitizations of one batch of events (those at the map replicas that build U, §6.7, included), use the same digitization path (`g4sim-digi-job/1`, in `core/simulation/digitize.py` or `g4sim_digi`, or not), because the channel-stream counter differs between the paths (volume ID × C + c on the job path, the readout's cellID otherwise; response-sampling row above), so two evaluations on different paths share no sensor or electronics noise (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md).
- **New seed**: the global event interval of the Geant4 events does **not overlap** with any previous use under the same `logical_run_seed`, or a different `logical_run_seed` is used. g4sim takes the Philox key from `run_seed` of `response-pipeline/1`, not from the run card, so this workflow always sets `run_seed` equal to `logical_run_seed` (checked by `calib_design.py`). Then both layers are new whenever the (`logical_run_seed`, global event interval) pairs do not overlap, and the Philox key need not be changed separately.
- **`replica` is always 0**: every evaluation's `response-pipeline/1` has `replica` = 0. With a mapped efficiency map, g4sim's `response.scintillation_event` takes Dirichlet replica r of the map whenever `replica` = r > 0, so a non-zero `replica` would change the map, not only the response noise; on the `g4sim-digi-job/1` path (g4sim S8) `replica` enters only the keys, and the job's efficiencies come from the job, but `replica` = 0 is still needed there so that the keys are those of the nominal digitization. Response noise is new whenever (`logical_run_seed` = `run_seed`, event interval) is new. g4sim's own map replicas (§6.7) are evaluated through the `map_replica` argument of `response.scintillation_event`, or, on the `g4sim-digi-job/1` path (`core/simulation/digitize.py`, `g4sim_digi`), by writing replica r's per-bin efficiencies (`efficiency_map.efficiencies(map, bin, r)`) into the job's `efficiencies` (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md), the route by which U may be built in the fixed-map mode (§6.7, decided by the author on 2026-11-09); in both cases with `replica` = 0, so that the photon streams stay those of the nominal digitization (for the joint-pattern replicas of a θ scan, which `map_replica` cannot carry, see §6.7). Response stages are never named `efficiency_map/<k>`, which is the stage name of g4sim's map-replica streams. `calib_design.py` rejects a violation (remedy level: plan) (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md M2).
- **Changing only the response is not a new seed**: re-digitizing the same batch of Geant4 events with only the Philox replica or key changed still shares the noise of the Geant4 layer. This practice is never accepted for the following uses:
  1. the K refits of G7;
  2. the event-level parametric bootstrap of §2.1:
     - all iterations of the same result share one set of event intervals; on the actual data, the folds of cross-validation and the ±1σ, ±2σ refits of G9 also share this set of the fit (fits on the same data, each regenerated at its own θ_ref per §2.1 "Event-level parametric bootstrap" (i));
     - the N_t × K_b sets for estimating Σ_boot in the design stage, the bootstrap of each G6 toy, the bootstrap of each G8 pseudo-data set, and the one bootstrap set used by P7 toys to freeze V̂ (§7.3) each use different event intervals;
     - each θ_ref update regenerates or resimulates per §2.1 with the same event intervals and random numbers; this is the same set of events, not an overlap;
  3. the pseudo-data of G8: one nominal-size MC per set, and the high-statistics truth MC of each injection point. The boundary between the two handlings: when the plan declares that G8 is not run, `closure-not-tested` is added (§8.4); when it declares that G8 is run but the fit MC is not independent (shared, or only the response changed), the plan is rejected;
  4. MC of toys: every replica of the replica-difference or full construction (see above; including the toys of G6 and G2, one pair per toy);
  5. validation;
  6. the two MC sets e⁽¹⁾, e⁽²⁾ of the P7 cross product: **the predictions of both the nominal model and the alternative model must each be independent**, otherwise the cross product still has a bias of tr(C⁺Cov(e⁽¹⁾, e⁽²⁾)) (§9.4).
- **Check** (`calib_design.py`): the plan records the `run_id`, `logical_run_seed`, global event interval and Philox key of each evaluation. Two things are checked; in both, two evaluations overlap only when they have the same `logical_run_seed` and their global event intervals intersect, so the comparison is on (`logical_run_seed`, global event interval) pairs (settled by plugin source, Appendix D31):
  1. Event intervals of different uses are pairwise non-overlapping. Uses include: fit, G7, G8, P7, validation, the parametric bootstrap of §2.1, the MC replicas of toys, the mapping runs of §6.7 (one per efficiency map; within a θ scan whose plan declares the shared seed, the design points share one (`logical_run_seed`, interval) by design, and with independent seeds each design point has its own, §6.7, D28; accepted by the author, 2026-11-09; source en/g4sim-S7-check.md m3; the two mapping runs of a PDE split-check pair share one (`logical_run_seed`, interval) by design, and the efficiency-1 run of the pair may be the production mapping run, §6.7 "PDE split", decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md), the design-stage MC sample that decides the scope of the effective-count approximation of binomial blocks (§2.1 "Finite simulation statistics in non-Gaussian blocks", D30), and the new sets used by each use to replace non-converged members.
  2. Within the same use, sets that need to be independent are pairwise non-overlapping. These sets include: the K sets of G7, each G8 pseudo-data set, the two sets of P7, the B sets of the bootstrap, the N_t × K_b sets of the Σ_boot estimate, the bootstrap of each G6 toy, the bootstrap of each G8 pseudo-data set, the one bootstrap set of P7 toys, the new sets used to replace non-converged members, and every MC replica of each toy (with a surrogate model, including the n_dp design-point MCs of each copy).

  Handling:
  - When G8 is declared to be run, overlaps between pseudo-data sets or with other uses are likewise rejected; when G8 is declared not to be run, the result carries `closure-not-tested`.
  - All other overlaps are always rejected (remedy level: plan).
  - The check also requires that the `run_seed` of every evaluation's `response-pipeline/1` equals its `logical_run_seed`, and that `logical_run_seed` values meant to be distinct are pairwise distinct: g4sim's seed hash H takes values in [1, 2³¹ − 1], so plan-derived seeds can collide (about 2% for 10⁴ seeds; `core/simulation/seeds.py` `seed_uniqueness_problems`, applied to the registry of seed blocks (S_b, t) of §14.1, not to member run records: members of one block share S_b, which that function allows only within one declared `seed_group`). A violation is rejected (remedy level: plan) (accepted by the author, 2026-11-09; source en/g4sim-binding-check.md A1/A3).
  - For every `g4sim-digi-job/1` (g4sim S8), `calib_design.py` also checks that the job's `run_seed` equals its `logical_run_seed`, that `replica` = 0, for a job without `conditions`, that its `keys` equal those `digitize.job_with_keys` computes from the job (`g4sim_digi` uses the precomputed keys and never reads `run_seed`, so a job whose seed was edited without recomputing its keys would run with stale streams); that a job with `conditions` carries no `keys` and is digitized by `core/simulation/digitize.py` only (`job_with_keys` refuses such a job, and `g4sim_digi` would ignore its conditions, D83 (9)); and, for a job with `conditions`, that `event_time_ns` is the event-time rule the plan records (§11.4 "Conditions", D87 (h)) applied to the event interval. A violation is rejected (remedy level: plan) (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md).
  - g4sim's response check (S4, `response.study_keys`) refuses a `response-pipeline/1` document in which two of its own keys (all stages × readout systems at one `run_seed` and `replica`) coincide. It does not compare documents with each other; distinctness across evaluations follows from the (`logical_run_seed` = `run_seed`, event interval) check above.
  - **Key distinctness of this workflow's own streams**: the keys of the joint-pattern replicas (`calib-map-joint/1`), of the route-3 replicas (`calib-map-pde/1`) and of the route-1 thinning streams of the PDE split (`<stage>/pde/<component>`, §6.7) are pairwise distinct and distinct from `response.study_keys` of every pipeline used (`calib_design.py`, remedy level: plan) (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md).

### 6.7 Event budget (matrix condition at θ level)

MC noise enters the likelihood through two carriers, which are mutually exclusive (the block rules of §2.1 guarantee that a bin belongs to only one kind of block):

- **Gaussian blocks**: the noise of the MC prediction enters V_G as V_MC.
- **Poisson and binomial blocks**: MC statistics enter as MC nuisances in β (Barlow–Beeston-lite for Poisson blocks, the MC auxiliary binomial likelihood for binomial blocks, §2.1).
  - Their constraint terms use the MC summary statistic m_MC as the "auxiliary measurement".
  - Poisson templates keep Σw, Σw² per bin; efficiency templates keep the passing and failing parts and their joint covariance.
  - V_m,MC must be obtained from a joint sampling construction of these summary statistics; a Σw² must not be filled in directly for the efficiency itself.
  - These bins are **not** put into V_MC, so they are not double counted.

**Event budget of the bootstrap**: the event-level parametric bootstrap of §2.1 is a third MC use, but it determines only the covariances in V and C_r; it is not noise of the prediction, so it does not belong to the carriers above and does not enter the matrix condition.

- Its budget is B sets × the expected number of events per set × (2 + N_t K_b + n_G6 + n_G8 + n_open), where:
  - 2: the set used by the fit, and the set used by P7 toys to freeze V̂ (§7.3);
  - N_t K_b: the number of sets for estimating Σ_boot in the design stage (§2.1);
  - n_G6: the number of G6 toys (one independent bootstrap set per toy, §8.2);
  - n_G8: the total number of G8 pseudo-data sets (one independent bootstrap set per pseudo-data set, each iterated per §2.1 "Event-level parametric bootstrap" (i), §8.4). If one set is shared, the noise of V̂ becomes a common offset for all pseudo-data, and the false-alarm rate of G8 at the full level rises from 0.068 to 0.136; 0.068 is the value without the Σ_boot widening of §8.4, with the widening it is ≤ α_G8, which is checked by the acceptance tests of §8.7;
  - n_open: bootstraps regenerated at opening (one set per free-normalization sample belonging entirely to validation, §2.1).
- B ≥ max(500, 50p), included in the plan by `calib_design.py` together with the other uses.
- The other toys (Ĉ_r, the T_v / T_cv reference distributions, the power toys of the V stage, and the interval toys of §7.5 (including those of each G8 pseudo-data set)) freeze the V̂ of the fit they imitate (the nominal fit, the V̂_f of each fold, or each pseudo-data set's own, §7.3 "Toy data and V̂"), need no new bootstrap events, and are not included here.
- Every θ_ref update requires regeneration. Response parameters need only re-digitization and add no simulated events. When resimulation is needed (θ at the Geant4 layer, or nodes evaluated only by reweighting, §2.1), each term in the formula above that needs iteration is multiplied by the iteration limit 30 of §7.3:
  - the fit term additionally includes, on the actual data, the folds of cross-validation (n_f folds), likewise iterated per §2.1 "Event-level parametric bootstrap" (i), and the ±1σ, ±2σ refits of G9 (four times per shift-mode φ). They use the fit's set of event intervals (§6.6), so the resimulation amount of this term is (1 + n_f + 4n_shift) × 30 sets;
  - the N_t K_b toy fits and the n_G8 pseudo-data sets each iterate;
  - the n_G6 G6 toys are locally linear toys (§8.5), do not iterate, and are not multiplied.
- The bootstrap of each G6 toy may instead use Wishart sampling W(V̂/(B − 1), B − 1), scaled by the bootstrap covariance used by the fit, in place of event-level resampling (so the n_G6 term needs no events). This is allowed only when the calibration of §8.7 confirms that with it the rejection rate of G6 under the null hypothesis is ≤ 1.5α (including shape and small-count summary statistics); otherwise event-level resampling is used.
- The contribution of bootstrap sampling noise to θ̂ is included in σ_tot as Σ_boot / w, and P5 requires Σ_boot / w ⪯ f·Σ_data (§2.1, §7.3).

**Budget for replacing non-converged members**: the events needed for replacement are also included in the budget. The ensembles with replacement (the toy fits of Σ_boot, the K refits of G7, the pseudo-data of G8 and their independent MC) stop replacement when X reaches k*(n_req) (§7.3), so each ensemble uses at most k*(n_req) − 1 additional sets of new event intervals (for G7, k*(K) − 1 full MC sets), and the budget is reserved according to this upper limit.

**Design-stage MC for the effective-count scope**: the design-stage MC sample from which §2.1 "Finite simulation statistics in non-Gaussian blocks" computes the per-class weight moments of binomial bins is also included in the budget; its event intervals do not overlap with the nominal MC or with any other use (§6.6) (part of the D30 rule: settled by computation, en/compute-D30.md; to be confirmed by the author).

**MC budget of toys** (construction declared per §6.6):

- **Replica-difference construction**:
  - Each toy that needs MC gets two full MC predictions (only those needed by Gaussian blocks), with the same number of events as the nominal prediction, generated once only at the generation point and not iterated, so they are not multiplied by 30 even when resimulation is needed. Toys that need MC include: Ĉ_r, the T_v / T_cv reference distributions, the power of P7 and of the V stage, the reference distribution of G6 and the χ̄² weight toys of G2, the interval toys of §7.5 and the interval toys of each G8 pseudo-data set.
  - When a surrogate model is used, each copy is n_dp design-point MCs (cost about 2n_toy times the nominal MC, §19).
  - Each replaced non-converged toy needs a new pair of replicas; k*(n_req) − 1 pairs are reserved.
  - G8: one nominal-size MC per pseudo-data set (including replacements; with a surrogate model each set is n_dp design-point MCs; without a surrogate model, when resimulation is needed, each set is multiplied by the iteration limit 30); one truth MC with ≥ 100 times the nominal number of events per injection point; one pair of replicas for each interval toy of the pseudo-data.
  - The replicas needed for the redo of the whole ensemble in §7.3 are generated separately at the time of the redo and counted in a budget revision of the plan.
- **Full construction**: two copies per toy per iteration. When resimulation is needed, every iteration of every toy needs one copy for each of all the design points evaluated by that fit, so each toy is 2 × n_eval × 30 copies (n_eval is the number of design points evaluated in one fit; not the n_dp design-point MCs of a surrogate model, §6.4). The ensembles with replacement likewise reserve k* − 1 pairs.

**Matrix condition**: let m = (MC predictions of Gaussian blocks, m_MC of non-Gaussian blocks), with MC covariance V_m = diag(V_MC, V_m,MC); the uncorrelated error of data y is V_y (V^unc_data for Gaussian blocks, the respective expected variances for Poisson and binomial blocks). θ̂ is a function of (y, m); linearize at β̂ by the implicit function theorem:

```latex
B_m = \left[-H_{\beta\beta}^{-1} H_{\beta m}\right]_{\theta},\qquad
B_y = \left[-H_{\beta\beta}^{-1} H_{\beta y}\right]_{\theta},
\qquad H = \nabla^2 \left(-2\ln L\right)
```

```latex
\Sigma_{\rm MC} = B_m V_m B_m^{T} \;\preceq\; f\,\Sigma_{\rm data},
\qquad \Sigma_{\rm data} = B_y V_y B_y^{T}
```

- With only Gaussian blocks, B_m reduces to −A and B_y to A (A being the fit operator of §9.2, V_cc including V_MC), Σ_MC = A V_MC Aᵀ.
- This is the **seed-to-seed** covariance of θ̂ with respect to the MC sample, exactly the quantity checked by G7. It is **not** equal to "the total covariance with MC noise" minus "the covariance without MC noise": this difference overestimates when V_MC and V_data are not proportional (linear Gaussian counterexample: with two parameters and 8 bins the diagonal elements are overestimated by 7–9%).
- σ_tot^design in the design stage (pipeline stage B) is computed with Asimov data at θ_ref = prior center.
- The matrix condition of P5, on the other hand, is decided on the same Sobol scan points as in §3.6, recomputing B_m, B_y point by point with that point's Asimov, and taking the worst (the point with the worst ESS is not necessarily the point with the worst matrix condition; §8.2 P5).
- Implementation phase 1 first provides Gaussian blocks (B_m = −A); MC nuisances of non-Gaussian blocks are added in implementation phase 2 together with the joint likelihood. Before that, contracts containing non-Gaussian blocks cannot be executed (`calib_contract.py check` rejects them by engine version).
- After the fit, recompute at β̂ instead. Σ_MC and Σ_data take the θ block.

**ESS threshold**: the effective sample size required for each observable is

```latex
N_{{\rm req},k} = \frac{s_k^2}{f\,V^{\rm unc}_{{\rm data},kk}}
```

where s_k² is the variance of the contribution of a single event to the k-th observable (estimated by bootstrap). Both P5 and G4 decide by N_eff,k ≥ N_req,k; N_eff is computed with event-level product weights.

Default f = 0.1. This is a matrix-order condition, so correlations between observables caused by the weights are automatically accounted for. When the condition holds, in any linear combination of parameters the standard deviation due to MC noise is ≤ √(f/(1+f)) ≈ 0.30 times the total error. P5 checks this condition with Asimov at the worst point within the prior, and also requires V_MC,kk ≤ f·V^unc_data,kk for each observable.

Kish effective sample size:

```latex
N_{\rm eff} = \frac{\left(\sum_i w_i\right)^2}{\sum_i w_i^2}
```

**Three layers of MC error when g4sim is used**:

| Layer | Shrinks with number of events? | Changes with seed? | Handling |
| --- | --- | --- | --- |
| Geant4 event sampling | Yes | Yes | V_MC (or the MC nuisances of non-Gaussian blocks) |
| Response sampling (Philox) | Yes | Yes | V_MC; estimated together with the layer above by a bootstrap of the same batch of events, not added separately |
| Statistical error of the efficiency map itself (fixed-map mode) | No (shrinks with the photon number of the mapping run) | No (the efficiency map is fixed) | **Does not enter V_MC**; becomes a shared φ instead, with U from digitizations at the replicas or, for observables linear in ε, from the linear construction, see below |
| Statistical error of the efficiency map itself (map varies with θ, see below) | No (shrinks with the photon number of the mapping run) | Yes (the mapping run is redone at each point; with new seeds for G7, G8 and validation) | MC error of the surrogate model: carried by U(θ) = Σ_j w_j(θ) U_j E_j, built from the scan's replicas and profiled with θ (see "Two efficiency map modes") |

If the efficiency map error is put into V_MC, Σ_MC is overestimated (it does not change with the seed): G7 is a one-sided test and cannot see the overestimate, but P5 misestimates the MC budget, and this part of the error is not propagated correctly when shared downstream. Therefore:

- g4sim generates Dirichlet replicas of each efficiency map on demand: replica r ≥ 1 of a bin is `core/simulation/efficiency_map.efficiencies(map, bin, r)`, and `replicas(R)` refuses R < 100 (g4sim §10.4). No replica is stored; a replica is fixed by the map document and r. Whether R ≥ 100 suffices is open (D84).
- **The shared φ is defined in the native coordinates of the efficiency map** (bin × channel × scintillation component: one mapped `efficiency-map/1` document per component, whose bins are those of the production segmentation and whose channels are its `channels` list, in that order; "not detected" is implied by 1 − Σ_c ε_c and is not a separate coordinate; channels that detected no photon in the mapping run are absent and have ε = 0):
  - Let δ_r = ε_r − ε̄ be the difference of the r-th replica from the replica mean (native coordinates); do a singular value decomposition of the matrix [δ_1 … δ_R]/√(R−1) = W S Vᵀ, and let B_map = W S (left singular vectors **multiplied by the singular values**, rank ≤ R−1), so B_map B_mapᵀ equals the sample covariance of the replicas.
  - The shared φ_map are the coefficients on B_map, with constraint N(0, I), ε = ε_0 + B_map φ_map (ε_0 the nominal map, below).
  - Predictions use g4sim's nominal map (replica 0, ε_0 = k/n per bin and channel, the unbiased estimate) as the nominal efficiency map. The basis uses only the spread of the replicas (δ_r = ε_r − ε̄ above), so the center ε_0 and the covariance B_mapB_mapᵀ are consistent. g4sim's replicas are centered on the Jeffreys posterior mean (k + ½)/(n + (C+1)/2), which differs from k/n upward in every bin and channel with ε_c < 1/(C+1), as for typical detection efficiencies (for a sum over B bins with K detected photons, by about B/(2√K) map standard deviations). Replicas are therefore never used as predictions without subtracting their mean, and ε̄ is never used as the nominal map (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md M1). (Confirmed by computation, en/compute-19-g9.md: with the replica mean as the centre, the bias of ln LY reached −0.48 σ_tot on a 212-bin map and −0.11 σ_tot on a 53-bin map, and G8 failed on bias; with k/n it stayed within ±0.07 σ_tot.)
  - **Decided by the author (2026-11-09).** **U in the fixed-map mode.** The fixed-map mode need not keep the linear construction of U from the Jacobian (U = J B_map, below). g4sim's map-document route (`response.scintillation_event`) digitizes only at ε_0 or at one of g4sim's own replicas; its `g4sim-digi-job/1` route (g4sim S8, hep-research v0.65.0) takes per-bin efficiency vectors as data and can digitize at any vector with entries in [0, 1] and per-bin sums ≤ 1, in Python and in `g4sim_digi` (§19, C20). In the fixed-map mode, U (below) may therefore be obtained by digitizing at each replica's per-bin efficiencies through `g4sim-digi-job/1`: the job of replica r has the map's `channels` in that order and, per bin b, `efficiencies` ε^(r) = `efficiency_map.efficiencies(map, b, r)`, and otherwise the fields of the nominal job (`run_seed` = `logical_run_seed`, `replica` = 0, the same stages, transit and events), so that only the map changes. The same rules apply as to the jobs of the joint-pattern replicas of the mode where the map varies with θ (below): the checks of every digitization job of §6.6 (for a job without `conditions`, its `keys` equal those `digitize.job_with_keys` computes; a job with `conditions` carries no `keys` and is digitized by `core/simulation/digitize.py` only), and one digitization path within a readout system (§6.6 "Common random numbers"), the nominal digitization at ε_0 included. Column r of M is the difference of the predictions at replica r from their mean over the R replicas, and U = M V (below); for an observable not linear in ε this is the secant over the replica spread. Digitizing g4sim's own replicas through `map_replica` (§6.6) stays allowed. The linear construction, U = J B_map with J = ∂μ/∂ε at ε_0, that is, column r of M equal to J(ε^(r) − ε_0) centred over the R replicas (J δ_r, divided by √(R − 1)), is allowed as an option only for an observable that is linear in ε, for which it is exact and needs no digitization at the replicas; the plan records, per observable, which of the two constructions it uses, and `calib_design.py` rejects the linear construction for an observable that the plan does not record as linear in ε (remedy level: plan). In both cases the predictions keep the centre ε_0 = k/n (above), and the map term enters them as U φ_map, profiled with θ (below). Cost: each construction of U by digitization takes R digitization jobs over the study's events (R ≥ 100, D84), where the linear construction takes none; they add no simulated events (§6.7 event budget) and are converted into core hours by the pilot (§14.1 "Budget and scheduling limits").
  - **No truncation**: the basis is built only once, so the question "how many components each study keeps" does not exist.
  - The registration key contains the efficiency map hash (`efficiency_map.map_sha256` of the document exactly as `g4sim_efficiency_map.py build` wrote it, which also fixes every replica), the number of replicas R, the `CORE_VERSION` of the replica sampler, the coordinate order, the center ε_0 and the basis version. The map document is never rewritten, not even to drop its `form.uniformity` block (which `efficiency_map.json` does not list, so schema validation of a built map fails in g4sim 0.63.0 and still in 0.65.0, D83): any change of its bytes changes the hash and every replica (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md m2).
- **Propagation in each study**: each study computes by re-digitization the response of the observables to each basis direction, U_k = ∂μ/∂ε · B_map[:, k] (link space; U is the observable × basis matrix; with g4sim, from re-digitizations at the replicas with `replica` = 0 and `map_replica` = r, or through the digitization job with replica r's efficiencies (§6.6): U = M V, M the matrix of the replica differences of μ divided by √(R−1), which is exact when μ is linear in ε (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md §4); when μ is not linear in ε, U is defined as M V, a secant over the replica spread, whose non-linearity was negligible in the §19 computation on local dimension reduction (1 − R² ≤ 7 × 10⁻⁵, en/compute-19-g9.md); in the fixed-map mode, for an observable linear in ε, the linear construction U = J B_map may be used instead (above; decided by the author, 2026-11-09)), and profiles all φ_map,k together with θ (they enter linearly, so the computation is small). A study **may** reduce dimension locally, under the following conditions and procedure:
  - Do a singular value decomposition U = P Λ Qᵀ and keep the first m directions; the local coefficients are φ_loc = Q_mᵀ φ_map (written φ_loc to distinguish them from the conditioning parameters ψ; this is the explicit linear map to the shared φ_map at export; §10.4 uses it to express the local coefficients back in φ_map).
  - m is the smallest number of directions for which both of the following hold (all directions may always be kept; the plan records m and s_⊥ for each study):
    1. the variance of the discarded part U_⊥ = U − P_m Λ_m Q_mᵀ for **every** observable is ≤ 1% of that observable's total efficiency-map variance (decided observable by observable, not on the trace over all);
    2. the discarded part, standardized by the data, satisfies s_⊥ = tr(V_G⁻¹ U_⊥U_⊥ᵀ) ≤ 0.05 per study. V_G is the covariance of the study's Gaussian blocks at θ_ref (§2.1), without ν, η and φ_map. This is the quantity and the bound of condition 2 of §5.4 (settled by computation, en/compute-19-g9.md; to be confirmed by the author).
  - Why condition 2: within one Gaussian block of one study the reduction is exact for any m, because U_mU_⊥ᵀ = 0 gives U_mU_mᵀ + U_⊥U_⊥ᵀ = UUᵀ.
    - Two losses remain. One is the part of U_⊥U_⊥ᵀ between different Gaussian blocks of the study, which is dropped and is second order in U_⊥. The other is the cross covariance with every other study that uses the same φ_map, U_mU′_⊥ᵀ + U_⊥U′_mᵀ + U_⊥U′_⊥ᵀ, which is lost and is first order in U_⊥.
    - Both act in units of the data error. A part that is ≤ 1% of the map variance can be a large multiple of the data variance in the directions where two studies constrain each other.
    - On the synthetic ZDC fixture (g4sim S7 map and replicas; Geant4 transport not run), condition 1 alone lost up to 0.11 of G6 power in a joint fit of two studies at a map/data error ratio of 0.7–0.9, and up to 0.80 at 7–9. The 68% coverage changed by up to 0.045, and G8 failed where the full basis passed.
    - With condition 2, every configuration tested gave a power loss ≤ 0.013 ± 0.004 and a coverage change ≤ 0.004 (settled by computation, en/compute-19-g9.md; to be confirmed by the author).
  - The discarded part is added to V_G of the Gaussian blocks only as the local covariance U_⊥U_⊥ᵀ restricted to each block, and is marked as not shareable. Its cross covariance with other studies is therefore lost. By Cauchy–Schwarz, for any two observables i, j the loss does not exceed √(0.01 V_i) · √(V_j) = 0.1 √(V_i V_j) (V_i, V_j being the respective total efficiency-map variances). When both sides reduce dimension, it is 0.01 √(V_i V_j) plus two cross terms, with Cauchy–Schwarz upper bound (0.1 + 0.1 + 0.01) √(V_i V_j) = 0.21 √(V_i V_j). These bounds are in map-variance units and do not bound the effect on a joint fit or on a §10.4 combination; condition 2 does (en/compute-19-g9.md).
  - Poisson and binomial blocks have no V_G, so whenever the variance of U_⊥ (the diagonal of U_⊥U_⊥ᵀ, in standardized units) of any observable in these blocks exceeds τ_num, dimension reduction is not allowed, and all directions must be kept (D43).
  - PCA must not be done separately in each study's own observable space with the k-th principal component then taken to be the same φ_k.
- R_map = UUᵀ (observable space) is for diagnostics only and does not define shared variables.
- When the efficiency map error makes the information ratio of P3 miss its threshold, the remedy is to increase the photon number of the mapping run, not the number of events: a contract change in the fixed-map mode, a plan change in the mode where the map varies with θ, so the remedy level of P3 is then plan (§8.2, D44).
- **Two efficiency map modes** (declared in the contract, one of the two):
  - **Fixed map**: optical properties are neither θ nor φ. A SiPM PDE under the PDE split (below) is a response parameter, not an optical property, so a PDE that is θ or φ leaves the map fixed (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md). All design points use the same efficiency map, whose statistical error enters as the shared φ_map above. The efficiency map hash belongs to the model identity (§5.1), so increasing the photon number of the mapping run produces a new map and is a contract change.
  - **Map varies with θ**: optical properties (reflectivity, absorption length, etc.) are θ or φ (§11.4 Table 2).
    - Each design point does its own mapping run, and the efficiency map is a derived value of θ: its hash is masked from the model identity per §5.1, and the model identity uses the settings of the mapping run instead (except the photon number, see below). Within one θ scan the mapping runs share one seed and event interval by default (common random numbers), or each design point has its own seed, as the plan declares (the seeds of the mapping runs, below; D28); "new seeds" for G7, G8 and validation are independent of the scan's seeds; "independent seeds" (below) means one seed per design point.
    - In this case the statistical error of the efficiency map **does** change between design points, with θ and between seeds of the mapping run, so it is MC error: it enters through the map term U(θ)φ_map of the surrogate model, built from the scan's replicas as below (the seeds of the mapping runs), and the K refits of G7 must also redo the mapping run with new seeds.
    - The photon number of the mapping run belongs to the event budget of the plan; changing it is a plan change.
    - **Seeds of the mapping runs** (D28, revised 2026-11-09; en/research-D28.md). The plan declares one of the two:
      - **Shared seed** (default). The mapping runs of all design points of the scan use the same `logical_run_seed` and the same event interval [0, N_map), written into every mapping-run card (not through `geant4_run.py scan`, which gives each point its own seed); G7, G8 and validation use new seeds (§6.6). `calib_design.py` checks that the `primaries.csv` of the scan agree event by event. The map errors of the design points are then correlated (on the synthetic fixture: 0.89 between adjacent and 0.49 between extreme design points at a history divergence of 0.1 per step), and g4sim's replicas cannot represent this: replica r is keyed by each map's own SHA-256, so replica r of two design points are independent draws. g4sim's replicas are therefore **not** used for the map term in this case. This workflow draws **joint-pattern replicas** instead:
        - Group the events of the scan by their joint pattern p (the bin of the emission point, and the category at every design point: not detected or the detecting channel), with m_p events each.
        - Replica r draws G_rp ~ Gamma(m_p) per pattern and g_rbc ~ Gamma(½) per (bin, category). At design point j, ε_jbc^(r) is the sum of G_rp over the patterns with bin b and category c at j, plus g_rbc, divided by the bin total.
        - Its marginal law at every design point is g4sim's Dirichlet(k + ½), and jointly it is the Bayesian bootstrap of the shared photons.
        - Categories at design point j: "not detected" (pattern code c_j = 0) and the channels of map j's own `channels` list (pattern codes c_j = 1…C_j, in that order; g4sim lists only the channels that detected at least one photon in that mapping run, so the category sets of two design points can differ). A pattern is (b; c_1, …, c_J) with the design points in the plan's order, and the canonical order of patterns is the lexicographic order of these tuples. At design point j, only its own categories enter numerator and denominator, so its marginal is exactly g4sim's Dirichlet over map j's categories.
        - Key: `rng._key("calib-map-joint/1", scan_key, component, r)` (r = 1, …, R; r = 0 is the nominal ε_0 = k_j/n, which is not drawn), that is, the first 64 bits of SHA-256 of the canonical JSON of that list, as g4sim forms its keys, used with g4sim's Philox sampler. The scan key is the SHA-256 hex digest of the canonical JSON of the four-element list [[sorted `map_sha256` values of the scan's maps of that component], `logical_run_seed`, first event, N_map]. G_rp is drawn from `SubStream(key, p, 0)` with `SubStream.gamma` (counter (p, 0, 0, output group)), p being the pattern's canonical index (< 2³²). g_rbc is drawn from `SubStream(key, b, 1 + u)` with the boost Gamma(1.5)·U² of `efficiency_map._gamma` (`SubStream.gamma` refuses a shape below 1), u being the scan category code of category c, over the union of the scan's channel names in sorted order ("not detected" u = 0, the channels u = 1, 2, …), so that one g_rbc serves every design point whose map has that category.
        - The registration key holds the scan key, the component, the hash of the pattern table (the SHA-256 hex digest of the canonical JSON of the list of [b, c_1, …, c_J, m_p] in canonical order), the coordinate order, the centre ε_0 = k_j/n per design point (§6.7 above), R and the sampler version (`CORE_VERSION` of the Philox and Gamma code used).
        - For observables that are linear in ε, the linearized multinomial covariance from the same pattern table may be used instead of the replicas. It has no finite-R noise (D84). Its map term uses U_j = the row blocks of one factor L of the joint covariance [Σ_jl] = LLᵀ (for example from its eigendecomposition), so that U(θ)U(θ)ᵀ = Σ_jl w_j w_l Σ_jl.
        - **Predictions at a joint-pattern replica** (choice of the D28 verification, accepted by the author, 2026-11-09; source en/d28-verify.md major 1). The `map_replica` argument of `response.scintillation_event` takes only g4sim's own replica r of a map document (§6.6), and the map document is never changed (above), so a joint-pattern replica is never digitized through it. It is digitized through g4sim's digitization job instead (`g4sim-digi-job/1`, g4sim S8: `core/simulation/digitize.py`, or `g4sim_digi`), which takes the efficiencies of each bin as data: the job of design point j at replica r has map j's `channels` in that order and `efficiencies` ε_j^(r) per bin, and otherwise the fields of the nominal job of design point j (`run_seed` = `logical_run_seed`, `replica` = 0, the same stages, transit and events), so that only the map changes, as with `map_replica`. Column r of M_j is the difference of design point j's predictions at replica r from their mean over the R replicas, and U_j = M_j/√(R − 1) (below); for observables not linear in ε this is the secant over the replica spread, as for g4sim's own replicas (above). `calib_design.py` checks once per scan that the job route with g4sim's own replica r of map j (`efficiency_map.efficiencies(map_j, b, r)` per bin) reproduces, event by event, the photoelectrons per (event, volume, channel) of `response.scintillation_event` with `map_replica` = r and the yield factor of `response.yield_factor` (charge and code are not compared, because the job's channel streams are counted by volume ID × C + c, §6.6) (remedy level: plan).
      - **Independent seeds** (allowed when the θ-noise item of P5 passes with Σ_jl = 0, §8.2 note 3). Each design point has its own `logical_run_seed` or a non-overlapping interval. g4sim's replicas of each map are then exact, and replica r of different design points are independent nuisances.
      - **Map term, both cases (except the fallback below).** With U_j = M_j/√(R − 1) (the replica differences of the design point's predictions; columns indexed by r) and the surrogate model's weights w_j(θ), the map term is U(θ)φ_map with U(θ) = Σ_j w_j(θ) U_j E_j. E_j = I with joint-pattern replicas, so φ_map is one nuisance shared by the scan. E_j selects the block of design point j with independent seeds, so there is one φ_j per design point. φ_map is profiled with θ, N(0, I), with U(θ) evaluated at each θ, not held fixed in each minimization. Holding the map term fixed in each minimization (§7.3 fixed point) left an errors-in-variables bias of 0.12–0.52σ with independent seeds on the synthetic fixture.
        - The basis is defined in replica coordinates. No SVD is done per design point, because its signs and order are arbitrary at each point. A local dimension reduction (above) uses, with joint-pattern replicas, one rotation Q from the SVD of [U_1; …; U_J] (rows stacked, columns r), and with independent seeds one Q_j per design point; the two conditions above are applied to U(θ) at the design points and at the Sobol scan points of P5 (the regression weights w_j(θ) take negative values, so the discarded part of U(θ) can exceed that of every design point).
      - **Rejected** (`calib_design.py`, remedy level: plan):
        - g4sim's per-map replicas propagated through the surrogate model as independent under the shared seed. On the synthetic fixture they gave 0.37–0.50 of the map variance and a G6 size of 0.06–0.54 at α = 0.01.
        - Replicas coupled across design points by common uniforms (inverse CDF), or by one g4sim key for the scan. They are comonotone, keep 0.1% of the variance of the difference between design points, and give no slope or curvature noise.
        - Coupled replicas with independent seeds.
        - A surrogate model that interpolates the design points exactly. Its slope inherits the map noise of single design points (slope noise 1.3 times the true slope on the fixture).
      - **Fallback when the pattern table is not available** (the mapping runs' `photons.csv` or `primaries.csv` not kept): the shared seed, with the map covariance U_{j*}U_{j*}ᵀ (U_{j*} from g4sim's own replicas of map j*, through `map_replica` or the job route of §6.6) of the design point j* nearest the current reference point added to V_G and held fixed in each minimization (§7.3 fixed point: j* from θ_ref, then from the previous estimate), not a profiled φ_map; there is then no φ_map shared across the scan, and none is exported (§10.4). The plan records that this assumes full correlation between design points (on the synthetic fixture V_map was 1.02–1.09 of the truth at adjacent correlations of 0.886 or more, and conservative at 1.38 for weak coupling). The θ-noise item of P5 then uses Σ_jl = 0 (an upper bound in every configuration of the study: s and κ were never larger under the shared seed).
      - (Evidence, en/research-D28.md: joint-pattern replicas and the analytic covariance matched the true covariance, correlation 0.886 against 0.886 and difference variance 0.98–1.00 of the truth, in every configuration; G8 passed wherever the oracle passed; synthetic fixture, Geant4 not run.)
      - **Note** (D28; author's decision of 2026-11-09): under the shared seed the true map errors of the design points are highly correlated (≈ 0.89 between adjacent design points at a history divergence of 0.1 per step; 0.59–0.99 over the divergences studied), while g4sim's replicas, keyed by each map's own SHA-256, are essentially uncorrelated across design points (0.013 ± 0.079, with g4sim's own code). Using g4sim's per-map replicas across θ therefore understates the cross-point covariance: propagated through the surrogate model they gave 0.37–0.50 of the true map variance and a G6 size of 0.06–0.54 at α = 0.01, and G8 failed in all six configurations. This is why this workflow draws its own replicas, keyed by the scan (joint-pattern replicas, above). The numbers are synthetic (en/research-D28.md: g4sim's map and replica laws, with a per-photon detection model in place of the optical transport; Geant4 not run).
    - In this mode, observables affected by the efficiency map must be in Gaussian blocks (converted to Gaussian summary statistics if necessary), or enter through a surrogate model (with the error in the map term U(θ)φ_map, above): the MC nuisances of Poisson and binomial blocks carry only the noise of MC counts and have no place to carry efficiency map noise.
    - If the efficiency map redone at θ̂ in the result is to be written back for downstream use (§10.4), its own replicas are used to build a native basis, which becomes the φ_map that downstream can share.
- **PDE split.** **Decided by the author (2026-11-10).** A SiPM PDE may be a response parameter (θ or φ), applied in the digitization job to a map built without it, when the PDE model is exactly the sensor surface's `EFFICIENCY(E)` spectrum: a scale p of it, or a table PDE(E) that replaces it, with every other optical property unchanged. Otherwise, or by the plan's choice, the PDE stays an optical property (resimulation, "map varies with θ"; route 0), which is always allowed (en/research-PDE.md, en/pde-geant4-check.md).
  - **Why it is exact.** In the Geant4 11 source read (release not stated, en/pde-geant4-check.md), `G4OpBoundaryProcess` uses the surface efficiency in `DoAbsorption()`, which kills the photon in every case and labels it `Detection` with that probability, and nowhere else apart from the `EFFICIENCY > 0` test of `DielectricLUTDAVIS` and `CoatedDielectricDielectric` ("Rejected", below). Whether, where and when a photon is absorbed is decided before, by `REFLECTIVITY` and `TRANSMITTANCE`, or, on a metal surface with a complex refractive index, by the reflectivity computed from it. This holds for `dielectric_metal` (every finish, glisur and unified, with or without a complex refractive index; the SiPM skins of the ZDC fixture, §15.1) and for `dielectric_dielectric`, back-painted finishes included (Geant4 not run). So the history of every photon up to its absorption at a sensor does not depend on the efficiency, and ε_bc(PDE) = Σ_E PDE(E) a_bc(E), with a_bc(E) the map built with sensor efficiency 1, resolved in the photon energy at absorption. For a constant p, ε(p) = p·ε(1) with the transit law of the efficiency-1 map, and digitizing at p·ε has the law of a binomial thinning by p of the photoelectrons and of their times (thinning Multinomial(N, A) by p gives Multinomial(N, pA) for any law of N, and the kept photons' times are an iid sample).
  - **Map.** Built with every sensor surface's `efficiency` = 1 and every other optical property nominal. It is a fixed map unless other optical properties are θ or φ. Its hash belongs to the model identity as for any fixed map (§5.1), and the plan records the split, its route and the sensor surfaces set to 1. p is a θ or φ of the evaluator's job builder, not a field of `response-pipeline/1`, so the masked pipeline hash does not change. The production run keeps the nominal sensor surfaces: g4sim's `map-stale` compares only `materials_sha256`, a hash of the IR's materials, and records `surfaces_sha256`, the hash of `optical_surfaces`, without checking it (g4sim v0.65.0, `efficiency_map.component_findings`; en/pde-geant4-check.md, finding 6). This workflow therefore checks itself that the map's `surfaces_sha256` equals g4sim's hash (`canonical_sha256` of the IR's `physical.optical_surfaces`) of the mapping-run specification, whose surfaces equal the production run's except the sensor `efficiency` entries, which are 1 (`calib_contract.py` for a fixed map; `calib_design.py`, remedy level: plan, for the maps of a θ scan).
  - **Wavelength-independent PDE p** (route 2₁, the default). `g4sim_calib_eval.py` writes p·ε_c(b) into the `efficiencies` of each `g4sim-digi-job/1` (ε the nominal k/n, g4sim's replica r, a joint-pattern replica, or ε_0 + B_map φ_map, all of the efficiency-1 map), with the efficiency-1 map's transit histogram. No random stream is added; `run_seed`, `replica` = 0 and the job checks of §6.6 are unchanged. φ_map is defined on the efficiency-1 map (above). Because p is θ while the map is fixed, U depends on p: for an observable the plan records as linear in ε, U(p) = p·U(1), which is exact; otherwise, with a surrogate model, U is built at each design point j from digitizations at p_j·ε^(r) (U_j = M_j V, with the one V of the map) and enters as U(θ) = Σ_j w_j(θ) U_j, and with direct re-digitization U is built at each θ from digitizations at p(θ)·ε^(r); in both cases one φ_map is shared, because replica r of the one map is the same draw at every p. A local dimension reduction then uses one rotation Q from the SVD of the stacked [U_1; …; U_J], with its two conditions applied to U(θ) at the design points and at the Sobol scan points of P5, as for joint-pattern replicas (above).
  - **Wavelength-dependent PDE(E)** (route 3). The efficiencies are Σ_i PDE(E_i)/n_b over the detections i of channel c in bin b (PDE(E_i) interpolated as Geant4 interpolates the surface's `EFFICIENCY` vector: linearly, with the edge values outside the table), and the transit histogram is weighted by PDE(E_i), both from the photon energies in the `photons.csv` of the efficiency-1 mapping run. `efficiency-map/1` stores no energies of the detected photons, so route 3 needs that `photons.csv` kept: a map document without it cannot be used for a PDE(E). `calib_design.py` checks that the detections of the `photons.csv`, binned by emission point in the production segmentation, equal the map's `detected` counts per (bin, channel) and its transit counts (remedy level: plan); `photons_sha256` is the SHA-256 of the file's bytes as g4sim wrote them. Neither a constant scale of the efficiency-1 map (−4.8 sd and 95% coverage ≤ 0.004 in the study) nor a scale of a map built at a nominal PDE(E) (wrong for any change of shape) is allowed for a PDE(E). The `photons.csv` and the PDE(E) table enter the model identity through the `response-pipeline/1` item of §5.1. The job's transit counts are non-negative integers (`digitize.check_job`, g4sim v0.65.1; en/pde-geant4-check.md, finding 8), so the weighted histogram is scaled to 10⁶ and rounded (error ≤ 5 × 10⁻⁷ of the total, per cell; D83 (22)).
  - **Route-3 replicas.** The plan declares an energy grid (by default the grid of the PDE(E) table). Per bin, replica r draws Dirichlet(k + ½) over the categories (channel c, energy cell e) and "not absorbed at a sensor", and its efficiencies are Σ_e w̄_ce π^(r)_b,ce, with w̄_ce the mean PDE(E_i) over the detections in cell (c, e), or, for a cell with no detection, the mean of PDE(E) over the cell, uniform in E, so that the centre stays the per-photon weighting above (the k/n centre of §6.7). In the fixed-map mode the draws are g_bu ~ Gamma(k_bu + ½) from `SubStream(key, b, u)`, with the boost of `efficiency_map._gamma` for a shape below 1, u the category code ("not absorbed" u = 0, then the cells (c, e) in sorted order), normalized per bin; the key is `rng._key("calib-map-pde/1", map_sha256, photons_sha256, component, r)`, and the registration key holds `map_sha256`, `photons_sha256`, the component, the coordinate order, the centre, R, the sampler version and the energy grid. In the mode where the map varies with θ, route-3 replicas are joint-pattern replicas (above) with the `calib-map-joint/1` key, so that the cross-point correlation of D28 is kept: the categories at design point j are "not absorbed" and the cells (c, e) for c in map j's `channels`, every energy cell included, the scan code u orders the union of these cells by (channel name, energy cell), and the registration key is that of the joint-pattern replicas plus the energy grid. The grid is accepted (`calib_design.py`, remedy level: plan) only if the pseudo-mass per bin, K_cat/2 with K_cat the number of categories, is ≤ 0.01 n_b, and the variance of Σ_c ε_bc under the Dirichlet, computed analytically from its parameters (not from the R replicas), is ≥ 0.98 of the multinomial variance of Σ_i PDE(E_i)/n_b (the plug-in (Σ_i q_i² − (Σ_i q_i)²/n_b)/n_b², q_i = PDE(E_i), over the prior or design range of the PDE when it holds θ); the replicas drop the spread of PDE within a cell. Otherwise the grid is changed, and if no grid meets both conditions, the bin is merged or the map photon number is increased (a contract change in the fixed-map mode). When the PDE(E) holds θ, replica r is the same cell draw π^(r) at every design point, U_j is built from digitizations at Σ_e w̄_ce(PDE_j) π^(r)_b,ce, and U(θ) is formed with one shared φ_map, as for route 2₁. These bounds are design values (§8.7).
  - **Map varies with θ** (other optical properties are θ or φ): each design point's mapping run uses sensor efficiency 1, the joint-pattern categories are "absorbed at channel c" (for a PDE(E), the cells of the route-3 replicas above), and the PDE is applied in each job as above.
  - **Nested thinning** (route 1). Digitizing at p·ε re-maps the uniforms of the multinomial when p moves. This gives no bias, but predictions that are not smooth in p (slope noise 0.23 of the slope in the study, against 0.07 for a thinning that keeps each detected photon with probability p from its own stream, which is nested in p), and the b_J item of P5 is not defined for them (§8.2 note 3). For an observable linear in ε this does not arise, because its prediction is μ_0 + p·(μ(1) − μ_0), μ_0 the part that does not depend on ε, with an analytic derivative. So, when p is θ, every readout system that has an observable not linear in ε uses route 1 for all its observables (one digitization path per readout system, §6.6 "Common random numbers"); readout systems whose observables are all linear in ε use route 2₁ (`calib_design.py`, remedy level: plan). Route 1 is not smooth in p either (its predictions are monotone step functions of p), so its residual Jacobian noise is checked by σ_noise (G1, §7.4) and G8, not by b_J; in its readout systems U is built from route-1 digitizations at ε^(r), and its sensor and electronics stages use the job path's keys and channel counter (volume ID × C + c, §6.6). The same applies when p is a φ in profile mode. Route 1 digitizes at the efficiency-1 map, thins each detected photon by p from a volume stream of g4sim's form, key (`"g4sim-rng/1\0volume"`, `run_seed`, `<stage>/pde/<component>`, 0) with `<stage>` the scintillation stage name, counter (global event, volume ID, bin, output group = the index of the detected photon in the order the job draws them), and then applies g4sim's sensor and electronics stages in g4sim's order. The thinning is never applied after dark counts, cross-talk or saturation, and never as a scale of charge or of codes (§11.4 Table 2), and its stream is never named `efficiency_map/<k>` (`calib_design.py`, remedy level: plan). Its keys enter the key-distinctness check of §6.6. Until g4sim offers it (D83 (23)), it is Python workflow code, about 30 times slower than route 2₁ in Python in the study.
  - **Split check** (`calib_design.py`, remedy level: plan). In the fixed-map mode once per efficiency-1 map; in the mode where the map varies with θ once per scan, at the design point nearest the nominal θ; and again after any change of the Geant4 version (§5.1) or of the sensor materials or surfaces. It uses a pair of mapping runs with the same materials, surfaces, `logical_run_seed` and event interval (a sharing that §6.6 allows for this pair), one with sensor `efficiency` = 1 (it may be the production mapping run itself) and one at the nominal PDE p0 (or PDE(E)); both keep `photons.csv` and `primaries.csv`. Geant4 draws one uniform per absorption whatever the efficiency (en/research-PDE.md §1.2), and g4sim v0.65.0 draws no random number when it records a detection (en/pde-geant4-check.md, finding 7), so under the premise the detections at p0 are a subset of those at efficiency 1, with byte-identical `photons.csv` rows. `calib_design.py` checks this nesting event by event; a pair that is not nested fails the check, and the first event that breaks it is recorded: something other than the sensor efficiency changed the photon histories, or Geant4 or a user-supplied sensitive detector draws a number on `Detection`. Per bin and channel and on the transit means, the detections at p0 are compared with the binomial thinning by p0 (or by q_i = PDE(E_i)) of those at efficiency 1, whose noise is then thinning noise only: for a total, r = K_p0/(p0 K₁) − 1 and sd(r) = √((1 − p0)/(p0 K₁)), K₁ the detections at efficiency 1; for a PDE(E), r = K_q/Σ_i q_i − 1 and sd(r) = √(Σ_i q_i(1 − q_i))/Σ_i q_i. The plan is rejected unless the χ² passes at α = 0.01 and, with the difference δμ of the predictions from the two maps (δμ = J δε, or both digitized with one `run_seed`, the digitization noise included in sd(Δθ_i)) propagated to θ via A, |Δθ_i| + 2 sd(Δθ_i) ≤ 0.1σ_tot,i^design(θ*) for every θ_i (the 0.1σ_tot^design scale of §5.4, as D37 proposes, here as an upper confidence bound). The photon number of the pair is sized so that an exact split passes jointly with probability ≥ 0.94 (with the χ²): sd(Δθ_i) ≤ 0.1σ_tot,i^design(θ*)/(2 + z_{1−0.025/d}) for every θ_i, d the number of θ (for a total and d = 1, K₁ ≥ (2 + z_0.975)²(1 − p0)/(p0 b²) with b = 0.1σ_tot/p0: about 2 × 10⁸ detections at efficiency 1 in the study configuration; the χ² alone saw a bias of 1.3% in ε at about 4 × 10⁶ photons). The production map's own statistical error, which φ_map carries, does not enter the check. If the check fails only through 2 sd(Δθ_i), one larger pair, on a new interval and sized by the rule above, may replace it, with both results recorded (a plan change; a contract change in the fixed-map mode when the efficiency-1 run of the pair is the production map, whose hash then changes, §6.7 above); otherwise the PDE stays an optical property (route 0). The bounds are design values (§8.7).
  - **Rejected** (`calib_contract.py`, contract error): a split whose declared PDE parameter changes any optical property other than the sensor `efficiency` (a reflectance, transmittance, refractive index, window or coating tied to the PDE, such as a "reflectivity = 1 − PDE" model); a PDE that depends on the angle of incidence (which g4sim's `efficiency` cannot express); a sensor surface of the efficiency-1 map with an `efficiency` other than 1, or a map whose `surfaces_sha256` is not g4sim's hash of the production surfaces with the sensor `efficiency` entries set to 1 (for the maps of a θ scan, checked by `calib_design.py`, remedy level: plan); a PDE(E) declared as a constant scale of the efficiency-1 map; and, on a surface model whose absorption branch tests `EFFICIENCY > 0` (`DielectricLUTDAVIS`, `CoatedDielectricDielectric`; not configurable in g4sim 0.65.0), a declared PDE(E) that is 0 at an energy the emission spectrum reaches, because there an efficiency of 0 changes the photon history (en/pde-geant4-check.md); `calib_design.py` checks the same condition over the prior or design range (p = 0 included; remedy level: plan). Route 3 without the mapping run's `photons.csv` is rejected by `calib_design.py` (remedy level: plan). In these cases the PDE stays an optical property (route 0).
  - (Evidence, en/research-PDE.md: synthetic per-photon optics with g4sim 0.65.0 code downstream, Geant4 not run. With Geant4's surface model, routes 2₁ and 3 gave the reference law of photoelectrons and photon times, pull widths 0.98–1.02 and coverage at nominal, and σ(p̂) 0.64–0.74 of resimulation, because the efficiency-1 map holds 1/p more detections. With a PDE tied to the sensor reflectance (a fraction ρ of the undetected photons reflected), the split underestimated ε by 1.3–14% at ρ = 0.05–0.50, and at ρ = 0.25 p̂ was biased by +8–9% with coverage 0. The route-3 replicas were not tested in the study, whose fit used the analytic multinomial covariance.)

---

## 7. Inference engine

### 7.1 Evaluator interface

The experiment's adapter only needs to implement the following five functions:

```
evaluate(theta, phi, psi, model, effects_off, seeds)
      → {pred,
         V_MC (joint matrix across observables),
         n_eff[observable] (local value for tail observables),
         node_diag[node] = {n_eff, pareto_k, max_weight_fraction},
         V_emu, V_learn,
         grad (optional)}
resample(node, theta, phi, psi, model, inputs, seeds) → direct sampling of that node
evaluate_from(node, samples, theta, phi, psi, model, seeds)
                                             → propagates downstream from the given node output to get the observables (for P0)
learned_closure(fold)                        → difference of the learned density ratio on the held-out sample (for G4-L)
ask() / tell()                               → asynchronous interface for resimulation and surrogate models
```

`tiers()` and `domain()` are **not** implemented by the adapter; the engine derives them from the contract and the plan:

- candidate methods: `calib_chain.py`;
- feasibility and final method: `calib_design.py`;
- support and surrogate domain: `calib_design.py`, `calib_emulator.py`.

`effects_off` specifies the effects to remove, together with the "value after removal" declared in the contract, for use in §10.5.

**g4sim evaluator**: experiments that use g4sim do not implement the functions above themselves; they use one generic implementation, `adapters/geant4/assets/g4sim_calib_eval.py`.

- Layering: it is in the adapter layer and depends on `core/calibration` (interface definitions) and `core/simulation` (response, Philox, fsum); `core/calibration` does not import the adapter, which is consistent with the existing layering direction.
- Inputs: the three g4sim specifications, `response-pipeline/1`, and the node bindings and recording levels in the plan (§11.4).
- `evaluate`: according to the method derived per §11.4, it chooses reweighting (reading `column` or `event_file`), re-digitization (`core/simulation/response.py`; for scintillation bins `core/simulation/digitize.py` or its C++ build `g4sim_digi`, g4sim S8, which reads no condition snapshot) or resimulation (`g4sim_run`).
- `resample`, `evaluate_from`: node 1 is sampled with `g4sim_run`; nodes 2–5 are propagated downstream with `response.py` from the stage hand-off files. The only stage hand-offs g4sim provides are `response-handoff/1` between stages 3 and 4 (FE4) and between stages 4 and 5 (`simreco-strip`); propagating from nodes 3 and 4a would need a stage 2→3 hand-off, which g4sim does not provide and does not plan, so the whole segment is recomputed from the hit file or the stored scorer quantities (§11.4, §19).
- `ask/tell`: a state file records the `run_id` of each design point. Batch scheduling uses `batch_campaign.py` (§14.1). `geant4_run.py`'s `chunk`, `scan` and `reduce` accept only `layered_sim`/`element_sim` specifications. A `g4sim-run/1` evaluation is one `run-spec` run; a member split across array tasks is a set of runs with disjoint `first_event` ranges, which this workflow merges (exact sums with `core/simulation/rng.merge_partial_sums`).
- `learned_closure`: unrelated to g4sim; it is still provided by the experiments that use learned density ratios (phase 5).

### 7.2 Combination of the likelihood

- θ, ν, η, and φ in profile mode, are fitted together. φ in shift mode is fixed at its nominal value.
- Enumerated discrete models: at the "standard" and "full" strength levels each is fitted separately; at the "screening" level only the nominal model is fitted.
- When only eyeballed or digitized data are available, the result gets the `preliminary` flag.

### 7.3 Reference-point iteration

**Iteration steps**:

1. At the current fit point (θ_ref and the previous ν̂, η̂, and φ̂ in profile mode), compute the following:
   - V_MC, V_emu, the model-ensemble components;
   - the count-type errors of §2.1;
   - event-level parametric bootstrap: regenerated at the current θ_ref with the same set of random numbers (§2.1); the exception is the toys listed below in "Toy data and V̂", which freeze V̂;
   - σ_i⁽⁰⁾ and the ρ²/12 rounding term: whether rounding is allowed has already been decided per §2.1 when the contract was locked and is not re-decided during the iteration; after convergence they are recomputed once, only at the fit point.
2. Minimize with V and u fixed.
3. Set θ_ref ← θ̂ and repeat until the change in θ̂ is < 0.1σ_tot; the iteration limit is 30.

The design-stage toy fits that estimate Σ_boot (§2.1 (iii)) run before Σ_boot has been estimated. Their convergence criterion and the threshold of the ln det diagnostic below both use √(Σ_θ)_ii without Σ_boot (an effect of about 1%, because Σ_boot ≲ 0.02 Σ_data). So the definition of non-convergence for Σ_boot does not depend on Σ_boot itself.

**Diagnostic after convergence**: compute once more with the full Gaussian likelihood including ln det **V_G**; the difference between the two must be < 0.2σ_tot. The bootstrap part of V_G(θ) is frozen at θ_ref in the diagnostic and is not regenerated for each θ, so ln det has no piecewise jumps.

**Toy data and V̂**

- **Toy data** are always generated from the model's event-level noise:
  - counts by Poisson/multinomial sampling;
  - MC predictions carry independent MC noise, with the construction declared in §6.6 "MC realization of toys" (replica difference is the default);
  - ν, η are sampled according to their constraints (§2.1);
  - data noise is not sampled as N(μ, V̂).
- **V̂**: the Σ_boot toys, the G6 toys and the fits of the G8 pseudo-data themselves each use an independent bootstrap realization (§2.1, §6.6, §6.7). The other toys that need this section's iteration freeze the **V̂ matrix** of the one fit they mimic, at that fit's convergence (as in G7, what is frozen is the matrix itself); the iteration only updates the other model-generated errors and the predictions at θ_ref. The V̂ frozen by each toy:

  | toy | frozen V̂ |
  | --- | --- |
  | holdout Ĉ_r, T_v reference distribution, V-stage power, toys of the §7.5 interval construction | V̂ of the actual nominal fit |
  | toys of cross-validation fold f | V̂_f of that fold at convergence on the actual data (§9.3) |
  | interval toys of each G8 pseudo-data set | V̂ of that pseudo-data set at its own convergence (§8.4) |
  | P7 toys (no actual fit at design stage) | V̂ generated at θ_ref with one independent bootstrap realization; in cross-validation mode, each fold's V̂_f is the sub-block of this bootstrap on that fold's training observables, not sampled separately |

  This is the exception to §2.1 "Event-level parametric bootstrap" (i): the "regenerated at each θ_ref update" of (i) applies only to the fits of the actual data, of the folds and of the pseudo-data themselves. So these toys need no new bootstrap events and are not counted in the bootstrap budget of §6.7 or in the non-overlap check of §6.6; the one bootstrap set of P7 is the exception and is counted.
- **Conditioning on V̂**: the frozen V̂ is a GLS weight carrying sampling noise, while the toy data carry the true event-level noise, so the spread of θ̂ in the toys is the sandwich (JᵀŴJ)⁻¹JᵀŴVŴJ(JᵀŴJ)⁻¹. It is the correct sampling distribution conditional on the V̂ actually used, with expectation about Σ_data + Σ_boot (1.019 Σ_data for linear Gaussian, p = 50, d = 3, B = 2500; the curvature with V̂ substituted is 0.981 Σ_data). Therefore:
  - (a) quantities calibrated or estimated with these toys already contain the effect of V̂, and **none of them gets Σ_boot / w added again**: the reference distributions of T_v and T_cv, and Ĉ_r (including J_vΣ_bootJ_vᵀ), and toy-calibrated intervals (the toy-calibrated construction of §7.5 and Feldman–Cousins). Adding Σ_boot / w again to toy-calibrated intervals would double-count about 0.02 Σ_data.
  - (b) only quantities obtained from the curvature do not contain it and get Σ_boot / w added: the profile intervals of §7.5 and σ_tot (§8.1).
- **Explicit approximation**: the curvature with V̂ substituted itself underestimates in expectation by about (p − d)/B times the data part (E[V̂⁻¹] > V⁻¹, §8.1), the same order as Σ_boot. So after Σ_boot / w is added, the quantities in (b) are still low by about one Σ_boot relative to the spread conditional on V̂ (linear Gaussian, p = 50, d = 3, B = 2500: 1.002 vs 1.019, about 0.8% in half-width; smaller when the bootstrap is only part of V). This workflow does not correct it, for the same reason as in §8.1; it is controlled by the lower bound on B in P5 and tested by the coverage of G8.
- **Analytic C_r**: analytic C_r as the χ² reference or for analytic power is used only when V has no bootstrap part (§2.1: C_r with bootstrap always calibrates T_v with toys, the list in §9.2; the power of §9.4 likewise takes the toy path); then Σ_boot = 0 and this term is absent. When V contains bootstrap, the toy-calibrated T_v may still use the analytic C_r with V̂ substituted as its metric (Ĉ_r of §9.2 is optional): it lacks J_vΣ_bootJ_vᵀ, but the observed value and the reference toys use the same metric, so the size is not affected, only the efficiency.

**Handling non-convergence**

**Definition**: a fit counts as not converged if it does not converge within 30 iterations, or if the ln det diagnostic difference is ≥ 0.2σ_tot; toys, pseudo-data and refits all follow the same definition.

The fits that need this section's iteration fall into two classes (single fits on the actual data, ensembles); the rules below apply to all of them. The implementation is only in `calib_fit.py`; the ensembles of other scripts call the same implementation (§14).

**Allowed non-convergence rate**:

- ε_max = 1%. §8.7 performs acceptance only for the case where the convergence fraction of each class of ensemble is ≥ 1 − ε_max; the guarantees below all hold when ε ≤ ε_max.
- Cross-validation toy ensembles (Ĉ_{r,f}, the reference distribution of T_cv, power) have **toys** as members: if any one of a toy's F fold fits is still not converged after multi-start refitting, that toy is not converged. So the allowed value for these ensembles is

  ε_max,cv = min(1 − (1 − ε_max)^F, 2%)

  about 1.99% for F = 2 and 2% for F ≥ 3; this is consistent with the §8.7 acceptance "all folds of each toy converged ≥ 1 − ε_max,cv". The cap is not 5%, because 5% equals the default α.
  - k* of the ratio test is computed with ε_max,cv;
  - the bias bound of replacement is computed, per the definition of w, with the observed ε̂; when ε̂ ≤ ε_max,cv the variance is underestimated at most down to the factor w(ε_max,cv).
  - Cost: non-converged toys are counted in the unfavorable direction per this section, so the effective level of T_cv drops to (α − ε)/(1 − ε) (about 0.031 at ε = 2%, α = 0.05). Power toys are counted by the same rule and the power decision is made at this effective level, so the cost is only in power and does not make the result wrong.

**Class 1: single fits on the actual data**, with no member that can be replaced:

- Actual fit: non-convergence means G1 fails (the extremum is not trustworthy; G1 is a mandatory gate, remedy level: plan).
- The fit of each cross-validation fold on the actual calibration data: uses only that fold's training data, and is fully completed before T_cv is computed. Each fold is first refitted with multi-start per §7.4; if it is still not converged, cross-validation is unusable, the same as G5 failing in some fold (§9.3):
  - T_cv is not computed, no validation read is produced, no failure record is written;
  - V is `incomplete` (§10.2 rule 0);
  - the remedy level is plan (change the fold split or change the fitter);
  - it is not recorded as a G1 failure: that would make the result `failed`, while per §8.1 validation-type gates do not make the result `failed`.
- The ±1σ, ±2σ refits of G9: non-convergence means G9 fails (remedy level per §8.2: change to profile mode).

**Class 2: ensembles**. Members are random repetitions and can replace one another. They include:

- the K refits of G7;
- the pseudo-data of G8;
- the design-stage toy fits for Σ_boot (K_b bootstrap realizations per toy);
- the toys that estimate Ĉ_r (§9.2);
- the reference-distribution toys of T_v and T_cv (including cross-validation redone with full toys when the linearity check fails, §8.5, §9.3);
- power toys (the P7 toys, the cross-validation rejection-rate toys, the V-stage power toys).

Every non-converged member is recorded (seed, event interval, number of iterations or ln det difference) and is handled as follows, according to the ensemble's use.

**Ensembles for estimation and decision (G7, G8, Σ_boot, Ĉ_r)**

**Replacement**: a new member generated with the next unused seed and event interval (§6.6) replaces it, until the number of converged members reaches the required number n_req:

| Ensemble | n_req |
| --- | --- |
| G7 | K |
| G8 | N_c per injection point |
| Σ_boot | K_b per toy; replacement is done within each toy, so ν_b = N_t(K_b − 1) is unchanged; the ratio test treats all N_t K_b realizations as one ensemble, with X summed |
| Ĉ_r | the lower bound on the number of toys in §9.2 |

Statistics are computed from converged members only.

**Non-converged pseudo-data are not counted as not covered**: a fixed non-convergence rate ε would make the observed coverage (1 − ε)c, a shift independent of N_c; at full level d = 3 with N_c = 353 (the value without the non-convergence margin, §8.4) and ε = 1%, the overall false-alarm rate of G8 would rise from about 0.05 to about 0.15.

**The selection effect caused by replacement** is bounded when ε ≤ ε_max:

- **G8**: per §8.4, the worst-case shift is included in the coverage test and in the design of N_c.
- **G7**:
  - in the direction that raises the false-alarm rate (non-convergence concentrated in the refits closest to θ̄), the expectation of T rises by at most about ε/(1 − ε) (about 1% at ε = 1%, far smaller than the difference between the χ² critical value and the expectation), so the false-alarm rate does not rise appreciably;
  - in the other direction (concentrated in the farthest), the expectation drops by at most 1 − w(ε) (7.5% at ε = 1%), which only lowers the power of G7 (example: V_MC underestimated by a factor of 2, d = 1, K = 10: from about 0.29 to 0.23) and does not raise the false-alarm rate.
- **Σ_boot and Ĉ_r**: in any direction, replacement underestimates the variance at most down to a factor w(ε̂) = F₃(χ²_{1,1−ε̂})/(1 − ε̂) (F₃ is the distribution function of χ²₃).
  - The worst case is non-convergence concentrated in the realizations with the largest projection along one direction, which truncates χ²₁, so this factor is independent of dimension; the factor F_{k+2}(χ²_{k,1−ε̂})/(1 − ε̂) for radial truncation of χ²_k is closer to 1 than this factor for every k ≥ 2.
  - ε̂ = X/(n + X), summed over all attempts of the ensemble (including the redo below).
  - **Σ_boot computes w with the conservative add-one estimate ε̂⁺** (not a confidence bound): Σ_boot has few realizations (default n = N_t K_b = 60) and the sampling variance of ε̂ is large (at the default n with ε = 1%, X = 0 in 55% of runs); correcting with the point estimate still underestimates by about 1.1% on average (default n). So the w of Σ_boot is computed with ε̂⁺ = (X + 1)/(n + X + 1); when X = 0, w = w(1/(n + 1)): 0.891 at the default n = 60, and 0.935, 0.956 at n = 120, 200.
  - **Ĉ_r still uses ε̂** (n ≥ 500; average bias about 0.2% when corrected with ε̂); for Ĉ_r, w = 1 when X = 0.
  - Example: w = 0.956, 0.925, 0.891, 0.822 at ε = 0.5%, 1%, 1.64% (1/61), 3.23% (2/62).

**Conservative treatment with the worst-case value**: claims that use Σ_boot and Ĉ_r are always treated with this worst-case value:

- λ̂_a of the power (§9.2, §9.4) is multiplied by w(ε̂). Exception: for s_a of §6.6, only the numerator λ_a^low is multiplied by w(ε̂); the denominator λ̂_a^single is not.
- P5, σ_tot and σ_tot^design (§8.1), and the interval half-widths of §7.5, all use Σ_boot / w (with ε̂⁺).

**This correction is one-sided**:

- In the direction where non-convergence is concentrated in the farthest realizations, it exactly cancels the bias; in the other directions (independent of the outcome, concentrated in the nearest realizations), it makes λ̂_a low by about 1/w(ε̂) − 1 (at ε = 1%: about 8% independent of the outcome, about 9% concentrated in the nearest realizations).
- Σ_boot is corrected with ε̂⁺, so it is high in every direction: at n = 60, ε = 0–1%, on average about +9–12% in the farthest direction, about +12–18% in the outcome-independent direction, and at most about +19% when concentrated in the nearest realizations.
- The cost is that power claims and P5 are conservative:
  - P7 may decide that the power is insufficient for an alternative hypothesis whose true power is about 0.82–0.85;
  - Σ_boot is always inflated: at the default n = 60, by 12%, 22%, 30%, 39%, 47% for X = 0, 1, 2, 3, 4 (for X ≥ k* = 5 the ratio test fails; for larger n the inflation is smaller and k* is larger, e.g. k* = 7 at n = 120). Σ_boot is generally ≲ 0.02 Σ_data and still ≲ 0.03 Σ_data after inflation, far below P5's f·Σ_data = 0.1 Σ_data, so this does not make P5 fail needlessly (§15.2).
- The size of T_v is not affected, because the observed value and the reference toys use the same Ĉ_r.
- The acceptance test of §8.7 checks only one side: after correction, λ must not be overestimated (Σ underestimated) by more than 1%.

**Ensembles for testing (reference-distribution toys of T_v, T_cv; power toys)**

No replacement. Non-converged members stay in the denominator and are counted in the **direction unfavorable to the claim that the ensemble supports**:

- **Reference-distribution toys** support "size ≤ α": non-converged ones count as statistic ≥ observed value, and the p-value is

  (#{T_toy ≥ T_obs} + X + 1)/(n + 1), where X is the number of non-converged toys and n is the total number of toys in the ensemble, converged and non-converged (n_req; not the n of ε̂ = X/(n + X)) (D49).

  So non-convergence can only make rejections fewer, and the false-alarm rate of V does not rise because of it; the cost is that the effective level drops to about (α − ε)/(1 − ε) (about 0.040 at α = 0.05, ε = 1%), and the size acceptance of §8.7 is accordingly split into two parts, with and without non-convergence.
- **Power toys** support "power ≥ 0.8": non-converged ones count as not rejecting, and the decision of each power toy uses the same p-value rule as the actual data. So what P7 and the V stage estimate is exactly the power of the decision rule actually adopted, with the loss from non-convergence already included.

**Ratio test**

**Decision**:

- Each ensemble records its own number of non-converged members X (for G8 the two injection points are summed, n_req = 2N_c).
- The distribution of X is NegBin(n_req, 1 − ε) with replacement (the number of non-converged members before the n_req-th converged one), and Bin(n_req, ε) without replacement.
- When X ≥ k*(n_req), that item is decided as failing. k* is the smallest integer with P(X ≥ k*) < 10⁻³ at ε = ε_max; so when ε ≤ ε_max, the probability that the ratio test gives a false alarm for each ensemble is < 10⁻³.
- Replacement stops when X reaches k*.
- k* is computed by `calib_fit.py` from the exact distribution, not looked up in a table. Examples:
  - Ensembles with replacement (NegBin): k* = 3, 3, 5, 14, 22 for n_req = 5, 10, 60, 500, 1000; 9 for G8 at standard level (d = 3, n_req = 198), and 23 at full level (n_req = 1036).
  - Ensembles without replacement (Bin): 2, 8 for n = 5, 198; for the other n listed above the two are the same.

The decision is not made by "observed fraction > 1%" or "any one not converged": such a threshold equals the allowed true fraction, so the test itself triggers with probability about one half (at ε = 1%, the trigger rate for G8 is about 0.3–0.5 for "observed fraction > 1%" and 0.86–1.0 for "any one"; P5 fails if just one of the 60 realizations of Σ_boot does not converge; 0.096 for G7 at K = 10).

**What fails**:

| Ensemble | On failure |
| --- | --- |
| G7 | G7 fails |
| G8 | G8 fails |
| Σ_boot | P5 fails (Σ_boot cannot be estimated) |
| power toys of P7 | numerical failure: P7 recorded as `incomplete` (same as the V stage, §8.1 "P7 and V give the same handling") |
| toys of Ĉ_r, T_v, T_cv; V-stage power toys | numerical failure: V recorded as `incomplete` |

A numerical failure is not evidence that the data do not fit the model, so:

- the ratio test runs **before** the p-value (or λ̂_a) is computed;
- on failure, no p-value is computed, V (for the P7 toys, P7) is recorded as `incomplete` (§10.2 rule 0), and it is not written as `final`;
- `calib_validate.py` redoes the whole ensemble with the next unused seed block (same κ, each time recorded). The P7 toys are handled by `calib_design.py` calling the same implementation, with the same counting and continuation.

**A redo is treated as a continuation of the same ensemble**: the ratio test decides on X summed over all attempts, and k* is computed from the ensemble's distribution:

- **Ensembles with replacement** (Ĉ_r; X is NegBin): the sum of the numbers of members actually converged in each attempt takes the place of n_req; a failing attempt stops when X reaches k*, so it is not counted as "number of attempts × n_req".
- **Ensembles without replacement** (reference toys of T_v, T_cv and V-stage power toys; X is Bin): each attempt runs all n_req toys, with no early stop; the index of the Bin is the number of all completed toys, that is, number of attempts × n_req.
- w is also computed from the totals: the denominator of ε̂ is the number of fits actually completed (converged and non-converged together).
- The p-value and λ̂_a use the last ensemble.

So a redo cannot lower ε̂ by picking an attempt with a smaller X. When the true fraction exceeds the allowed value, the summed ratio test fails with increasing certainty as the number of attempts grows, and V stays `incomplete`. Because the p-value is never computed before the ratio test passes, a redo also cannot be used to pick a p-value.

**Way out when the summed test still fails**, which differs according to whether the validation data have been opened:

- **After opening**: the record of this κ stays `pending`; the way out is fixing the fitter (a plan revision, which is a new κ and leaves this κ's record `pending`) or abandoning this κ (record `final`).
- **Before opening** (when the holdout Ĉ_r and reference toys are generated before opening): there is no record and the validation data are not opened; under the same κ a summed redo with the next seed block may be done as above, and if the summed test still fails, it stays `incomplete` until a new κ.
- **Cross-validation Ĉ_{r,f} and T_cv reference toys**: completed before T_cv is computed; when the ratio test fails there is no validation read yet, so there is no record, and V is `incomplete`. Within the same κ a summed redo with seed blocks may be done as above, unless the summed G5 proportion of that ensemble is > 20% at the end of the attempt (§9.3, rule settled by computation, en/compute-19-14-1f.md; to be confirmed by the author): then the §9.5 row for a G5 proportion > 20% applies (remedy level plan) and no redo is made; if the summed test still fails, V stays `incomplete` until the fitter is fixed (a plan revision, hence a new κ). There is no `pending` record in this case, so the abandonment of §9.5 does not apply.
- **V-stage power toys**: needed only after T_v or T_cv has been decided as passing; by then the record is already `withdrawn` and cannot be abandoned; the way out is a new κ, or declaring power abandonment per §9.4.

**Toys of the §7.5 interval construction**: one interval construction contains multiple reference distributions (one per scan point of each parameter); a ratio test on each one separately would multiply the false-alarm rate by the number M of reference distributions, so they are **always summed**:

- On the actual data, all toys of one interval construction form one ensemble (X and n both summed, k* computed from the summed n).
- When the summed test fails, the interval is recorded as `incomplete` and the whole interval construction is redone with a new seed block (scan points and observed data unchanged, only the toys regenerated), continuing per the summing rule above until the summed test passes (the interval is built from the last toys) or it is rebuilt after the fitter is fixed (a plan revision). The number of redos has no limit; each one is recorded.
- When the interval is `incomplete`, the mandatory gate G3 that uses it (the 68% region of θ̂) is recorded as `incomplete`, and the result is therefore `incomplete` per §10.2 rule 0; the decision table has no separate input.

**Interval toys in G8**:

- No ratio test is done on the interval toys of each pseudo-data set. Their non-convergence is handled only by the counting in "Intervals and scans" below (it belongs to the interval procedure) and does not make the pseudo-data non-converged; so the replacement rate of G8 is still only the non-convergence rate of the fits of the pseudo-data themselves, and c₀′, p₁′ of §8.4 and the k* of G8 are unchanged.
- The interval toys of the whole of G8 are separately summed into one ensemble with one ratio test, in the same order as for the actual data: on failure G8 is recorded as `incomplete`, and only the interval toys of all pseudo-data are regenerated with a new seed block (the pseudo-data, the independent MC and the fits of the pseudo-data themselves unchanged), continuing per the summing rule until it passes (G8 decides with the last intervals) or the fitter is fixed (a plan revision).

**Intervals and scans**

**Non-convergence of interval toys**: the toys of the toy-calibrated interval construction of §7.5 and of Feldman–Cousins are ensembles for testing; non-converged toys are counted in the direction unfavorable to coverage: at each scan point they count as test statistic ≥ observed value, which keeps that point inside the interval (the interval can only get wider).

- This counting is part of the interval **procedure**: the actual data and each G8 pseudo-data set use the same procedure, so what G8 measures is the coverage of the procedure actually used, and p₁ of §8.4 also refers to the coverage of this procedure.
- Non-convergence of interval toys in G8 is handled only by this counting and does not make the pseudo-data non-converged (see "Ratio test" above).

**Scan points are not iterated**:

- The profile scan on the actual data (§7.5, the profile of G5) is a single fit, and the fits at the scan points **do not go through this section's iteration**: V (including V̂ and the other model-generated errors at θ_ref) is fixed at its value at convergence of the nominal fit, so q(θ) is a ratio of the same likelihood. V̂ is not regenerated at each scan point, because then q(θ) would compare χ² values under different V̂ without ln det, and it would be discontinuous at the piecewise jumps of V̂.
- The variation of V with θ is neglected within the interval range; this is an explicit approximation, tested by the coverage of G8 (the scans of each G8 pseudo-data set are likewise fixed at the V of that pseudo-data set at its own convergence).
- For each toy of the toy-calibrated interval construction of §7.5 (and Feldman–Cousins), the nominal fit iterates as above (V̂ frozen, other errors updated); its scan points likewise **do not iterate**: V is fixed at its value at that toy's convergence (V̂ is the frozen one; the other errors take their values at that toy's convergence). So the toys and the actual data use the same definition of q(θ), and the interval procedure is the same on both sides.

**Non-convergence at scan points**: each scan point is first refitted with multi-start per §7.4. If the extremum is still not converged (the EDM criterion of G1; the 30 iterations and the ln det diagnostic do not apply to scan points):

- in the interval, the point counts as staying inside the interval;
- in G5, it counts as Δ(−2 ln L) < 4 (the direction in which G5 fails);
- the scan point is recorded.

A G5 failure caused only by non-convergence at scan points is a numerical failure; the remedy level is **plan** (change the fitter, refine the scan or add starting points), not the usual contract level of G5 in §8.2.

**Fits of cross-validation folds**

The fit of each fold is likewise first refitted with multi-start per §7.4; only if it is still not converged does it make V `incomplete` per "Class 1" above. The acceptance tests of §8.7 check that, for cross-validation (leave-one-out with n ≤ 20, and the F-fold and the leave-one-out with n > 20 that the plan adopts), at the design points the fraction of toys with all folds converged is ≥ 1 − ε_max,cv.

G6 and the χ̄² weights of G2 use locally linear toys (§8.5), do not go through this section's iteration, and are not covered here.

### 7.4 Finding the extremum

The rules of this section other than the second bullet are new (settled by computation, en/compute-D57.md; to be confirmed by the author); their tolerances are design values of §8.7 (note 6); the σ_noise terms, the comparison of basins including ln det V_G and the per-basin reference-point iteration are reasoned design rules, not computed (note 6, D57).

- At least max(2d, 16) starting points, drawn with scrambled Sobol from the prior range; the scramble seed comes from the seed block of the fit (§6.6), so each toy, pseudo-data set, fold and refit draws its own starts. The number is a design value (§8.7).
- When the objective function is noisy, use SciPy's `differential_evolution` or the bundled NumPy CMA-ES, followed by local refinement.
- **Converged endpoint**: a start whose minimization passes the EDM criterion of G1 with a positive-definite curvature. Starts that do not converge are recorded and form no basin. A fit with no converged endpoint is not converged in the sense of §7.3 (D45).
- **Admission**: a converged endpoint is a basin only if σ_tot,i ≤ R_admit·σ_prior,i for every θ_i (R_admit = 1; σ_tot,i from the curvature at that endpoint, σ_prior,i per §8.3 and D54). An endpoint that fails it is a non-identified stationary point: it is recorded with its −2 ln L, supplies no θ̂ and is not a basin. If no endpoint is admitted, θ̂ is the lowest converged endpoint and G5 is decided there (it fails, since σ_post/σ_prior > 0.5). If a non-identified stationary point lies more than τ_tie below the lowest basin, G5 fails (contract).
- **Separation of basins**: the admitted endpoints are taken in increasing order of −2 ln L; each joins the first basin whose representative (its lowest endpoint) it is not separated from, and otherwise opens a new basin. Two endpoints are separated iff −2 ln L along the straight segment between them, evaluated at 19 equally spaced interior points with V fixed at its value at the representative, exceeds the larger of the two endpoint values by more than τ_bar = max(0.1, 4σ_noise). The difference of −2 ln L between the two endpoints is not a criterion: exactly degenerate basins have equal −2 ln L.
- **Reference-point iteration**: §7.3 is run from the representative of each basin. The −2 ln L of different basins are compared with the full Gaussian likelihood including ln det V_G at each basin's own convergence (the quantity of the ln det diagnostic of §7.3), because V differs between basins. A basin whose iteration ends at a point not separated from another basin is merged into that basin.
- **θ̂** is the representative of the basin with the lowest −2 ln L. Basins within τ_tie = max(0.01, 4σ_noise) of it are tied: θ̂ is then the tied basin first in lexicographic order of θ (contract parameter order), and the tie is recorded. θ̂ supplies every quantity defined at θ̂ (σ_tot, G2, G3, G5, G6, G9) and is the truth point of the toys of §7.3 "Toy data and V̂".
- **Multiple basins**: when two or more basins are admitted, G1 is decided for each basin, every basin is reported (θ, −2 ln L relative to θ̂, σ_tot), and the `multimodal` flag is added.
- **Toys, pseudo-data, folds, refits and scan points** use this section with the same number of starts and the same tolerances; each takes its own θ̂ by the rule above, and its q (§7.5) is referred to its own θ̂. A profile scan point is started, besides its own starts, from the representative of every basin of that fit with the scanned parameter set to the scan value.

### 7.5 Intervals

Intervals are owned by `calib_interval.py`.

- **By default** the profile likelihood ratio is used. The V at scan points is fixed at its value at convergence of the nominal fit (§7.3 "Intervals and scans"). For an interval on a single parameter θ_i, the other θ_j are profiled as well; the decision threshold is q ≤ the quantile of χ²₁ (1 for 68%, 3.84 for 95%):

```latex
q(\theta) = -2\ln\frac{L(\theta, \hat{\hat\nu}, \hat{\hat\eta}, \hat{\hat\phi})}{L(\hat\theta, \hat\nu, \hat\eta, \hat\phi)}
```

- Near a boundary, a Feldman–Cousins-style profile construction is used.
- For frequentist intervals in multi-parameter, non-Gaussian or boundary cases, a profile scan and an explicit toy-calibrated construction are used; Feldman–Cousins must declare the treatment of nuisances and the coverage range.
- MCMC may only be used for separately declared Bayesian posterior inference: list the priors of θ and of all nuisances, the convergence and effective-sample diagnostics, and output a credible interval, which must not be labeled a profile confidence interval.
- **Contributions of shift mode and of bootstrap noise**:
  - Profile intervals do not contain Σ_boot (the sampling noise of V̂ is not in the likelihood); toy-calibrated intervals already contain it (§7.3 "Toy data and V̂"), get no further Σ_boot / w, and only get the shift-mode terms.
  - Profile intervals, after Σ_boot / w is added, are still narrow by about one Σ_boot (about 0.8% in half-width); this is the explicit approximation of §7.3 (b).
  - In the Gaussian case, the total interval half-width at confidence level 1−α is √(σ_q² + z²_{1−α/2} (Σ_l Δθ̂_l² + (Σ_boot / w)_ii)). σ_q is the half-width of the profile interval at the same level, and Δθ̂_l is the response to a ±1σ shift (z = 1 for 68%; z = 1.96 for 95%).
  - In the non-Gaussian case, the shift of each φ and (Σ_boot / w)_ii (for w see §7.3) are reported separately.
- When `multimodal`, the confidence set is {θ : q(θ) ≤ threshold} with q referred to θ̂, the global minimum over all basins: the union of the intervals of the basins, each referred to θ̂ and not to its own basin minimum, so a basin whose profile stays above the threshold contributes nothing. The interval uses the toy-calibrated construction of this section, each toy running §7.4: on the multimodal toy detector the χ²₁ threshold undercovers at 95% (0.929–0.936) when the degeneracy is only weakly broken (settled by computation, en/compute-D57.md; to be confirmed by the author).

---

## 8. Gates

### 8.1 Execution rules and definitions

- Gates belong to pipeline stages B, C, D, E, and to validation F. Within each stage, the decision is made only after all of them have been executed.
- Quantities for "whether to accept" are expressed as effect sizes. Gates that need a probabilistic decision (P0, P6, G2, G4-L, G6, G7, G8, V) state in the contract the overall false-alarm rate α and the multiple-comparison method.

**Classes of gates**:

- **Mandatory gates**: all gates in pipeline stages B, C, D, E **except P7**. If they fail in the final version, the result is `failed` (§10.2 rule 1).
- **Validation-type gates**: P7 (the design-stage forecast of validation power) and validation V of stage F. Their outcome only determines the upper limit of the evidence grade (§10.2 rule 3) and does not make the result `failed`.
  - P7 and V decide the same thing (whether validation can detect the declared deviation), only at different times; the two give the same handling at design stage and at validation stage.
  - Both use the same procedure: the total of a free-ω count shape is N_decl and N_obs respectively, and the event sample is N_decl,s and N_tot,s respectively (§2.1).
  - P7 is the design-stage forecast; the V stage decides again under N_obs.
- **Not applicable**: when the validation mode is `none`, neither P7 nor V applies (not executed, recorded as `not-applicable`), and the grade is determined by §10.2 rule 2 or 3. V and P7 recorded as not applicable for another reason (the outcome is already determined, §10.2 rule 0, or a mandatory gate failed, rule 1) take the same recorded value `not-applicable`; "no testable direction" (k = 0, §9.5) is recorded as `no-testable-direction` (D78).

**Applicability conditions of mandatory gates**: some mandatory gates are meaningful only for particular methods. The gates below are recorded as `not-applicable` when their condition does not hold (not unexecuted, not `incomplete`; §10.2 rule 0 does not count them). Applicability is derived by `calib_design.py` from the methods of the contract and the plan and written to the record; it is not declared by the analyst.

- **P0**: applies when the plan uses any of the following methods: analytic reweighting, step-level reweighting, learned density ratio, deterministic rerun, re-digitization (§3.6).
  - Surrogate models (P6) are not among them; they are checked by P6. So P0 does not apply to a plan that evaluates only with a surrogate model and evaluates all other nodes with full resimulation (`resample`).
  - When the plan evaluates nodes affected by k_B or r with a method in the list above, the spot checks specified in §5.4 (full simulation at the two extreme points of k_B, or design points where r is outside the valid range of the scintillation formula) are also included in P0 and cannot be omitted.
  - When these nodes are evaluated with a surrogate model, the same set of spot-check points is included in the held-out design points of P6 (evaluated with full simulation), executed by P6, and likewise cannot be omitted.
  - A plan that evaluates these nodes with full resimulation has nothing to compare against; whether P0 applies is decided by the list in the first sentence of this item.
- **P6**: applies only when the plan uses a surrogate model. Its χ² test of the pulls is executed only when there are ≥ 30 held-out points; with fewer than 30 only the |Δm| part is decided, and this is not `incomplete`.
- **G4**: applies when the plan has any event weights (analytic reweighting or step-level reweighting). **G4-L**: applies when the plan has a learned density ratio.
- **P8, G9**: apply only when there is a φ in shift mode.
- **G8**: per §8.4, when no decision is made it goes to `closure-not-tested`, not `not-applicable`.
- The other mandatory gates (P2, P3, P4, P5, G1, G2, G3, G5, G6, G7) always apply.

**Symbol definitions**

| Symbol | Definition |
| --- | --- |
| Σ_β, Σ_θ | covariance of β after the fit; Σ_θ is its θ block |
| σ_tot,i | √(Σ_θ + Σ_boot / w)_ii, the total error of θ_i (see below the table) |
| σ_tot,i^design(θ*) | Σ_θ computed with Asimov data at θ*, plus Σ_boot / w estimated with toys per §2.1 (§7.3), taking √(·)_ii (see below the table) |
| σ_MC,i | √Σ_MC,ii (§6.7) |
| σ_Δ,k | MC standard deviation of the k-th observable of the difference between two sets of predictions, estimated by bootstrap |
| σ_noise | standard deviation of the objective function recomputed at θ̂ with K ≥ 5 sets of seeds |

**σ_tot,i**:

- Σ_θ contains the contributions of ν, η, φ in profile mode, and the MC nuisances of non-Gaussian blocks; Σ_boot is the bootstrap sampling noise of §2.1 (estimated with toys at design stage, reused after the fit).
- For w see §7.3: the w of Σ_boot is always computed with ε̂⁺; when all toys converge, w = w(1/(n + 1)), which is 0.891 at the default n = 60, not 1. w = 1 applies only to Ĉ_r with X = 0.
- The convergence criterion of §7.3 and all gates that cite σ_tot use Σ_boot / w with this w: σ_tot,i after the fit; σ_tot,i^design (below) for the design-stage gates (P0, P3, P5, P7) and for G8. Which σ_tot the convergence criterion uses for toy and pseudo-data fits is open (Appendix D51).
- **Explicit approximation**: Σ_θ is the fit curvature with V̂ substituted, which in expectation underestimates by about (p − d)/B times the data part (≤ 2% when B ≥ 50p), so σ_tot² is low relative to the true Var(θ̂) by at most about (p − d)/B (smaller when the bootstrap is only part of V; linear Gaussian: 1.7–1.9%, σ about 1%). This workflow does not correct this term, because when V̂ is only part of V_G there is no general unbiased correction; it is controlled by the lower bound on B in P5 and tested together in the coverage of G8.

**σ_tot,i^design(θ*)**:

- Linearized in the same way as the design-stage version of §6.7.
- Design-stage gates (P0, P3, P5, P7) take θ* = θ_ref; G8 (stage C, no actual fit yet) takes θ* = the injected value.
- Gates after the fit always use σ_tot,i instead.

### 8.2 Gate overview

Cells marked "note n" in the table have their full conditions in the note with the same number below the table.

| Stage | Gate | Check | Suggested default | What failure means | Remedy level |
| --- | --- | --- | --- | --- | --- |
| B | P0 kernel consistency | non-full-resimulation evaluation vs `resample` + `evaluate_from` (note 1) | \|Δθ_i\| ≤ 0.1σ_tot,i^design + z·σ_MC(Δθ_i) (note 1) | the declared density does not match the actual sampling, or support is insufficient | plan (kernel registration); contract if the kernel semantics are wrong |
| B | P2 degrees of freedom | ndf = n_c − dim N_d,c − d_free (note 2) | ndf ≥ max(3, d_free) | G6 cannot test | contract |
| B | P3 expected identifiability | Asimov Fisher (§8.3) | λ_min(R_corr) ≥ 0.1; σ_post/σ_prior ≤ 0.4 | not identifiable; hints given per §3.5 | contract (add observables or references); plan when the miss is caused by efficiency-map error in the mode where the map varies with θ (§6.7) |
| B | P4 reference coverage | directed reachability condition of §3.4 | each θ can possibly be constrained by at least one reference | parameter cannot be constrained by the data | contract |
| B | P5 ESS and MC budget | ESS, §6.7 matrix condition, Σ_boot, Jacobian MC-noise bias b_J, θ-noise s_i, κ_i of the surrogate model (note 3) | Σ_MC ⪯ f·Σ_data; Σ_boot / w ⪯ f·Σ_data (for w see §7.3); N_eff,k ≥ N_req,k; \|b_J,i\| ≤ 0.15σ_tot,i^design (settled by computation, en/compute-19-13.md; to be confirmed by the author); s_i ≤ 0.25, κ_i ≤ 0.05 when the map varies with θ (design values, §8.7; D28) | MC sample or number of bootstraps insufficient, or the MC noise varies too fast with θ for a fit with V fixed, or the surrogate model's slope and curvature in θ carry too much efficiency-map noise | plan |
| B | P6 surrogate accuracy | held-out design points | \|Δm\| ≤ 0.3√V^unc_data + z·σ_Δ; χ² test of the pulls (note 4) | surrogate model not accurate enough | plan |
| B | P7 validation power forecast | according to validation mode (note 5) | simultaneous confidence lower bound of the power for each a ≥ 0.8 (§9.4; note 5) | the validation plan cannot detect the declared deviation; **not a mandatory gate** (note 5) | contract |
| B | P8 information condition for shift mode | §5.5 condition 1: I_φφ·rest computed with Asimov at θ_ref | largest eigenvalue ≤ c (default 0.1, an efficiency bound, §5.5); not applicable when there is no φ in shift mode | the data carry non-negligible information on that φ, and shift mode would lose the data's constraint on φ | contract (change to profile mode) |
| C | G8 closure | §8.4 | according to strength level | the method is biased, or the coverage is wrong | plan (if what is revealed is an engine defect, see the engine fix in §4.2) |
| D | G1 convergence | each basin decided separately | EDM < max(0.002·tol·UP, 0.1σ_noise), tol the minimizer tolerance declared in the plan | extremum not trustworthy | plan |
| D | G4 weight quality | event-level product weights; `node_diag` only as a diagnostic | N_eff,k ≥ N_req,k (§6.7); Pareto k < 0.5 (PSIS-smoothed weights k < 0.7) (note 6) | reweighting estimate unreliable (note 6) | plan |
| D | G4-L learned density ratio | difference from `learned_closure`, propagated to θ with A | same form as P0 | density-ratio estimate not trustworthy | plan |
| D | G7 MC noise consistency | K refits with new seeds, comparing the sample covariance of θ̂ with the predicted Σ_MC (note 7) | T < χ²_{r(K−1), 0.99}; spread in the null space beyond tolerance is a failure (note 7) | V_MC underestimated | plan |
| E | G2 physical boundary | significance of active constraints; the reference distribution is a χ̄² mixture, with weights obtained from locally linear toys | p ≥ 0.01; when not significant only the `boundary-solution` flag is added | the data significantly prefer going beyond the boundary | contract |
| E | G3 sampling limits | support, feasible region, surrogate domain | the 68% region of θ̂ lies entirely within all three | a limit of the sample design, not a physics conclusion | plan |
| E | G5 identifiability | Fisher and profile at θ̂; also fails per §7.4 (admission) | λ_min(R_corr) ≥ 0.05; σ_post/σ_prior ≤ 0.5; profile Δ(−2lnL) ≥ 4 | the data cannot separate some parameters | contract (plan when scan points do not converge, note 8) |
| E | G6 goodness of fit | calibration set, including ν and η (note 9) | p > 0.01 from locally linear toys | the model cannot describe the calibration set | contract (new version of V_model) |
| E | G9 linearity of shift mode | §5.5 condition 2: Δ_i from the refits at θ̂ with ±1σ, ±2σ (note 10) | Δ_i ≤ t_lin = 0.06 for every component (one-sided; note 10; settled by computation, en/compute-19-2.md; to be confirmed by the author) | the linear approximation of shift mode does not hold; d_l of §9.2 and the interval widening of §7.5 are not trustworthy | contract (change to profile mode) |
| F | V | §9 | global test p > α; the power of P7 still holds on the actual data | validation failed or lacks power | contract |

**Notes**

1. **P0**:
   - Check: at ≥ 3 θ′ (including the worst-ESS point within the prior; including the spot-check points specified in §5.4 when there are any), compare the prediction of the non-full-resimulation evaluation used by the plan (analytic or step-level reweighting, learned density ratio, deterministic rerun, re-digitization) with the prediction of `resample` + `evaluate_from`, and propagate to θ with A.
   - Default: for each parameter |Δθ_i| ≤ 0.1σ_tot,i^design + z·σ_MC(Δθ_i); z = z_{1−α/(2M)}, two-sided Bonferroni with M = d × (number of θ′), α = 0.01 (D53).
   - For the applicability conditions see §8.1.
2. **P2**: n_c is the dimension of the calibration data vector entering the likelihood (K per count shape, K − 1 per Gaussian shape, 1 per scalar), excluding the observables listed as unused under §5.2 (D77); d_free is the number of free parameters in β; the calibration likelihood is computed on N_d,c^⊥ (§2.1). At screening level, G6 computed with the asymptotic distribution also uses these degrees of freedom.
3. **P5**: checks five items:
   - the ESS of the worst point within the prior;
   - the matrix condition of §6.7, decided point by point on the same set of Sobol scan points, taking the worst;
   - the bootstrap noise Σ_boot of §2.1: estimated at design stage on N_t toys, each with K_b independent bootstraps, not with Asimov;
   - **the Jacobian MC-noise bias b_J** (Gaussian blocks; settled by computation, en/compute-19-13.md; to be confirmed by the author): when the noise of the nominal MC varies with θ (reweighting, re-digitization, a response scaled with θ, or a surrogate model whose V_MC varies over the design points; approximation (1) of §6.6), the fit with V fixed (§7.3) has an errors-in-variables bias that Σ_MC does not contain and that the toys of §6.6 do not reproduce. On the same Sobol scan points as the matrix condition, with that point's Asimov, compute

     ```latex
     b_J = -F^{-1}(t - u),\qquad
     t_l = \operatorname{tr}(W K_l),\qquad
     u_l = \sum_j \left( J_l^{T} W K_j q_j + J_j^{T} W K_l q_j \right),
     ```

     with J the Jacobian of the prediction, W = (V_data + V_MC)⁻¹, F = JᵀWJ, and q_j the j-th column of WJF⁻¹. K_l = Cov(∂e/∂θ_l, e) is the covariance between the MC noise of the Jacobian and that of the prediction. It is estimated from the per-event contributions in the same way as V_MC (for per-event weights in disjoint bins, K_l = ½ ∂V_MC/∂θ_l). The condition is |b_J,i| ≤ 0.15σ_tot,i^design for every parameter, taking the worst point.
     - The variance that the Jacobian noise adds at the fit point is already in Σ_MC, because V_MC is recomputed at the fit point (§7.3); no separate variance term is added.
     - When the noise of the nominal MC does not vary with θ, K_l = 0 and this item passes.
     - b_J scales as 1/N_MC: on failure, increase the MC by the factor |b_J,i|/(0.15σ_tot,i^design), or move the generation point toward the worst point (remedy level: plan).
     - Not defined for non-Gaussian blocks, or for MC predictions that are not smooth in θ (§19).
     - The 0.15 is a design value (§8.7), to be calibrated in phase 2: in the linear Gaussian configuration of §8.7 note 4 within the P5 range, the extra 68% undercoverage is ≤ 0.008 with it, while without it the loss reaches 0.031 (en/compute-19-13.md).
   - **the θ-noise of the surrogate model** (mode where the map varies with θ; D28, revised 2026-11-09, en/research-D28.md; the bounds are design values of §8.7, provisional thresholds to be calibrated, so results carry `provisional-thresholds` until then): the surrogate model's slope and curvature in θ inherit the map noise of the design points, and no V term carries them. With Σ_jl = Cov(e_j, e_l) of the scan (joint-pattern replicas or the analytic covariance with the shared seed; Σ_jl = 0 for j ≠ l with independent seeds or in the fallback of §6.7), on the same Sobol scan points as the matrix condition (taking the worst), with that point's Asimov, compute s_i = σ_tot,i^design √tr(C⁻¹ Σ_jl ∂_iw_j ∂_iw_l Σ_jl) and κ_i = (σ_tot,i^design)² √tr(C⁻¹ Σ_jl ∂_i²w_j ∂_i²w_l Σ_jl) (the whitened covariances of ∂_i ê and ∂_i² ê, ê = Σ_j w_j(θ) e_j), with Σ_jl = U_jE_j(U_lE_l)ᵀ (or the analytic covariance) and C = V_G + Σ_jl w_j w_l Σ_jl at that point (V_G of §2.1, without ν, η and φ_map; the study had V_G = V_data, and V_MC, V_emu and V_learn in C are a choice of the D28 verification, accepted by the author, 2026-11-09; source en/d28-verify.md major 4). It is computed by `calib_design.py` after the scan's mapping runs and before any fit. For a plan that asks for independent seeds, it may be computed from shared-seed (or pilot) mapping runs of the same design points with the same photon number, keeping only the blocks Σ_jj (Σ_jl = 0 for j ≠ l), whose law does not depend on the seeding; this is the independent-seed value. The condition is s_i ≤ 0.25 and κ_i ≤ 0.05 for every parameter, design values to be calibrated per §8.7 (directions mixed between parameters are not covered, D85 (3)).
     - On the synthetic fixture, with the exact map covariance, the pull width was ≤ 1.05 for s ≤ 0.21 and κ ≤ 0.062, and 1.02–1.10 at s = 0.32, where G8 failed in one of two ensembles. It grew monotonically beyond, to 1.9 at s = 0.74 and κ = 0.18.
     - Remedy (plan): more photons per mapping run (both fall with N_map; ten times the photons, with ten times the data, lowered s by 2.8 and κ by 8 with the shared seed at a divergence of 0.1, and by 2.3 and 5.2 with independent seeds, on the fixture), a smoother surrogate model, or, if independent seeds fail, the shared seed with joint-pattern replicas, which lowered s by up to 4.8 times and κ by up to 5.7 times.
4. **P6**: the z of the |Δm| condition is z_{1−α/(2M)}, two-sided Bonferroni with M = the number of held-out points × observables, α = 0.01 (D53); pulls by χ² test (α = 0.01), executed only with ≥ 30 held-out points (§8.1).
5. **P7**:
   - Check, holdout: with the expected validation errors generated by the model at θ_ref (the contract provides only metadata such as exposure, and N_decl, N_decl,s; §2.1, §9.2), compute λ_a of each alternative hypothesis on the analytic path of §9.4. When §9.2 requires T_v to be calibrated with toys (with bootstrap or estimated C_r), the rejection rate is simulated with toys, as in the V stage (§9.4).
   - Check, cross-validation: the rejection rate is simulated with toys (§9.3).
   - Default: simultaneous confidence lower bound of the power for each a ≥ 0.8 (§9.4). If the lower bound cannot be computed, `incomplete`; if k = 0 is determined before opening, recorded as `no-testable-direction`, not `incomplete` (§9.5). Not applicable when the validation mode is `none`.
   - What failure means: the validation plan cannot detect the declared deviation. P7 is **not a mandatory gate**: if it still fails in the final version, the upper limit of the grade is `calibrated-unvalidated` (§10.2 rule 3).
6. **G4**: for each observable N_eff,k ≥ N_req,k (§6.7); Pareto k < 0.5 for raw weights, or k < 0.7 if PSIS-smoothed weights are used instead. For 0.5 ≤ k < 0.7, the estimator variance of raw weights is infinite.
7. **G7**:
   - Check: K refits with new seeds (new Geant4 events, §6.6), comparing the sample covariance of θ̂ with the predicted Σ_MC. The bootstrap of §2.1 is frozen in the K refits: the V̂ matrix at convergence of the nominal fit is used, not regenerated.
   - Default: T = Σ_i (θ̂_i − θ̄)ᵀ Σ_MC⁺ (θ̂_i − θ̄) < χ²_{r(K−1), 0.99}, r = rank(Σ_MC); spread within the null space beyond tolerance is a failure (see "Rank and calibration of G7" below).
8. **G5**: when it fails because profile scan points do not converge, the remedy level is plan (§7.3), not contract as in the table.
9. **G6**: when V_G contains a bootstrap block, each toy uses one independent bootstrap realization (the reference distribution therefore includes the sampling noise of V̂).
10. **G9** (the threshold 1.5c, the refit reproducibility requirement and the order P8 before G9 are settled by computation, en/compute-19-2.md; to be confirmed by the author):
   - Check: Δ_i of §5.5 condition 2, from the four refits per shift-mode φ; in addition condition 1 is recomputed at θ̂ with the threshold 1.5c. P8 decides at θ_ref with c; the margin keeps the false-alarm rate of the recomputation ≤ 5% when the relative standard deviation of the recomputed eigenvalue is ≤ 0.3 (§8.7 note 5).
   - The refits use the event intervals of the fit (§6.6) and a minimizer tolerance such that the reproducibility of θ̂_i between refits is ≤ 0.01 s_i; at 0.03 s_i the false-alarm rate at Δ_i = t_lin/2 rises to about 0.23 (§8.7 note 5).
   - Not applicable when there is no φ in shift mode. Non-convergence of a refit means G9 fails (§7.3).
   - G9 is decided only after P8 has passed: when the data carry information on φ above c, the refit responses are correlated with the true φ, and selecting on them biases the coverage of the intervals that pass.

**Power of G7**: at K = 10, if V_MC is underestimated by a factor of 2, the detection probability is 0.29 (d = 1), 0.66 (d = 3), 0.91 (d = 6). The "screening" level uses K = 5; "standard" and above use K = 10.

**Rank and calibration of G7**:

- Σ_MC may be positive semidefinite with rank r < d (for example, only one shared template noise direction); then a pseudo-inverse with a pre-locked numerical tolerance is used, and the χ² degrees of freedom are r(K−1).
- First check whether all refit differences lie in the predicted image space; if spread beyond the numerical/MC tolerance appears in a zero-variance direction, it fails directly, and the pseudo-inverse must not eliminate it.
- When r = 0, only zero spread is checked, and no χ² p-value is computed.
- When Σ_MC is estimated from finite samples, varies significantly between refits, or θ̂ is affected by a boundary, calibrate with independent toys that include the estimation process; the χ² distribution for a fixed covariance cannot be applied directly.

### 8.3 Unified identifiability measures

- λ_min: the smallest eigenvalue after the θ block of Σ = F⁻¹ is converted to the correlation matrix R_corr, with F the Fisher information over all of β (the nuisances profiled). For two parameters, λ_min = 1 − |ρ|.
- Information ratio: σ_post,i / σ_prior,i, required for each θ_i; for a bounded uniform prior σ_prior,i = (range of θ_i)/√12 (D54).

P3 and G5 use the same measures; P3 is computed with Asimov at the prior center, with margin left in the threshold.

### 8.4 G8 closure test

**Injection points**:

- **Interior point**: ≥ 2σ_tot^design(injected value) from any physical boundary. Bias and coverage are checked.
- **Boundary point**: a point close to a physical boundary. **Only undercoverage is checked** (one-tailed). A correct but conservative interval (for example FC with coverage above nominal at the boundary) does not fail because of this; overcoverage is only reported.

**Data noise of the pseudo-data**: generated from the model's event-level noise, with events taken from the high-statistics truth MC of that injection point.

- Each pseudo-data set resamples one event sample of the data's size (exposure) from the events of the truth MC; counts and the Gaussian summary statistics of shared events are all computed from this sample, so the center is the truth MC's prediction.
- The resampled events do not overlap with the MC used for fitting, and are included in the non-overlap check of §6.6 and the budget of §6.7.
- This is the same rule as §7.3 "Toy data": counts by Poisson/multinomial sampling, the Gaussian summary statistics of shared events computed by event-level resampling, not sampled as N(μ, V), so failures of n_min and of the Gaussian approximation of the summary statistics enter G8.
- The same representation-format rounding as in the release is applied (§2.1).
- The true values of ν, η, φ are those of the injection point (the truth MC is generated with them); the constraint centers of the pseudo-data (auxiliary measurements) are sampled around the true values according to their respective constraints, the same as the profile construction of §6.6.

**Fits of the pseudo-data**: each pseudo-data set goes through the full fit workflow; this is a closure test built from real MC.

- Including its own independent bootstrap (§2.1, §6.7); its interval toys freeze its own V̂ at convergence (§7.3); non-converged ones are replaced by new pseudo-data per §7.3 and recorded, and are not counted as not covered.
- **Truth**: one high-statistics MC prediction per injection point (number of events ≥ 100 times nominal, shared by all pseudo-data; for non-Gaussian blocks its Σw is the expectation of the truth).
- **Fit**: uses the pseudo-data set's own MC of the same size as nominal and goes through the actual procedure, including its own V_MC, BB-lite and auxiliary binomial likelihood.
  - The Geant4 event interval does not overlap with any other use or with other pseudo-data; changing only the response sampling does not count.
  - "Same size" means by the same procedure as nominal: when a surrogate model is used, it is a surrogate model rebuilt with an independent set of design-point MC, n_dp copies per set; when resimulation is needed, every simulation needed by this pseudo-data set's §7.3 iteration uses its own event interval, and the budget is multiplied by the iteration limit per §6.7.
- **The MC part of the residual** is e_hi − e_g: e_g has the same distribution as the MC noise of the actual fit; e_hi has covariance ≤ V_MC/100 and is a shift shared by all pseudo-data, with standard deviation ≤ 0.1σ_MC (≤ 0.03σ_data per P5); it is listed as an approximation of G8 and checked by the acceptance tests of §8.7.
- So misestimation of V_MC, the effective-count approximation (§2.1) and evaluator bias all enter the bias and coverage of G8. Pseudo-data are not sampled from the likelihood model, because they would then always agree with the fit's assumptions and G8 could not see these three.

**Detection capability**: G8 targets method bias and interval coverage; how large an approximation failure it can detect depends on N_c and σ_MC/σ_data.

- Within the range P5 allows (Σ_MC ⪯ 0.1 Σ_data), the contribution of MC noise to the total variance is small, so when V_MC is underestimated by a factor of 2, the failure rate of G8 when P5 is not saturated is close to α (simulation: 0.05).
- It is higher when P5 is saturated in every parameter direction. This refers to the case where P5, with the misestimated V_MC, decides that saturation holds and the true Σ_MC is about 0.2Σ_data: about 0.29–0.30 at full level d = 3; if saturated with true Σ_MC = 0.1Σ_data, about 0.09. These numbers depend on the configuration; another linear Gaussian configuration (n = 20, d = 3, coverage test at both injection points) gives 0.33 and 0.11; they are only reported, with no threshold.
- The detection rate depends on N_c, σ_MC/σ_data, d, strength level, the number of directions in which P5 is saturated, and how the interval is constructed. For toy-calibrated intervals, whose toys carry the true MC noise (replica difference), the coverage is still nominal when V_MC is misestimated, and G8 cannot detect it; the detection rates above appear only for profile intervals.
- So passing G8 does not mean that V_MC or the effective-count approximation is correct: V_MC is tested by G7 (§8.2), and the effective-count approximation is verified by the simulation calibration of §8.7 (§2.1); §8.7 reports, by simulation, the detection-rate curves of G8 for these two kinds of failure (versus N_c and V_MC/V_data), with no threshold.

**When it cannot be done** (for example when the high-statistics MC or the MC for each pseudo-data set is too costly): the plan declares that G8 is not executed, G8 makes no decision, and the result gets the `closure-not-tested` flag. A plan that declares execution but whose fit MC is not independent is rejected (§6.6).

- Rationale: pseudo-data sharing the fit's MC would carry the same shift of size σ_MC, the reference distributions of both the bias and the coverage tests would fail, and increasing N_c cannot fix it; the shift of a shared truth MC is only ≤ 0.1σ_MC. So the truth may be shared; the fit MC must not.

**Decision**: the test family controls the overall false-alarm rate α_G8 = 0.05 with the Holm procedure. The family size depends on the strength level:

| Level | Family | m |
| --- | --- | --- |
| standard | bias (interior point, d of them), 68% undercoverage (two points, 2d of them) | 3d |
| full | all of standard, plus 95% undercoverage (two points, 2d of them) | 5d |

- **Bias**: test b = 0 with a t test (N_c − 1 degrees of freedom), with statistic b̄ / se. It is decided as a failure when statistically significant (Holm) **and** |b̄| > 0.2σ_tot,i^design(injected value).
- **Coverage**: one-tailed binomial test (undercoverage only), included in the same Holm family.
  - The null-hypothesis coverage is c₀′ = (c − ε_max)/(1 − ε_max) (c = 0.68 or 0.95, ε_max = 1%, §7.3). ε is the non-convergence rate of the fits of the pseudo-data themselves; non-convergence of interval toys belongs to the interval procedure and is not counted.
  - Rationale: non-converged pseudo-data are replaced; if they were all covered ones, the coverage of the converged ones is at least c₀′. So when ε ≤ ε_max, regardless of whether non-convergence and coverage are correlated, the false-alarm rate does not rise because of replacement (when the true coverage equals nominal; at 95% the true coverage is slightly lower per the next sentence, and the bound of replacement is relaxed correspondingly by about the same order).
  - At ε = 0 the 68% test is slightly conservative; at 95%, after the low σ_tot of §8.1 (about (p − d)/B) is included, the true coverage is about 0.948, slightly below c₀′ = 0.9495, close to nominal.
- **No extra margin for bias**: replacing an ε_max fraction of pseudo-data at worst removes a 1% tail on one side of the Gaussian distribution, which moves b̄ by at most about 0.027σ_tot, far smaller than the substantive threshold of 0.2σ_tot (a false alarm requires both to hold) and than the design bias of 0.5σ.

**N_c is the larger of what bias and coverage require**:

- Bias: detect a bias of 0.5σ with power 0.8,

```latex
N_{\rm bias} \ge \left(\frac{z_{1-\alpha_{G8}/(2m)} + z_{0.8}}{0.5}\right)^2
```

- Coverage: detect with power 0.8 a true coverage as low as the target value p₁, computed with exact binomial (one-tailed, α_G8/m, null value c₀′).
  - Power is computed at p₁′ = p₁/(1 − ε_max) (when the non-converged ones are all not covered, the coverage of the converged ones is at most p₁′), so when ε ≤ ε_max the power is still ≥ 0.8.
  - **p₁ is the coverage of the interval procedure actually used**, including the conservative counting of §7.3 for non-converged interval toys: the counting is part of the procedure, and the actual data and each pseudo-data set use the same procedure, so what G8 tests is exactly the coverage of the interval used by the result. A method whose coverage without counting is p₁ has coverage at most about p₁ + ε after counting; the result's interval really has this coverage, so G8 does not need to detect it.
  - Defining p₁ on the method without counting is not adopted (with p₁″ = (p₁ + ε_max)/(1 − ε_max), N_c at full level d = 3 would grow from 518 to 858, and at standard level from 99 to 112), because what G8 protects is the actual coverage of the result, not the coverage of a procedure that is not used.
  - Target for 68% coverage: p₁ = 0.50 at standard level, p₁ = 0.58 at full level. Target for 95% coverage (full level only): p₁ = 0.90.
- The bias formula uses the normal approximation; with the t distribution the required N increases slightly; the exact computation is authoritative.
- **The power of the exact binomial is sawtoothed in N**: adding a few pseudo-data sets to the smallest N with power ≥ 0.8 may bring the power back below 0.8. So N_cov is defined as "the smallest N such that the power is ≥ 0.8 for N and for all larger numbers", and it holds whenever G8 uses at least N_c sets. The table below is computed with this definition.

| d | standard: N_bias | standard: N_cov(68%) | standard: N_c | full: N_cov(68%) | full: N_cov(95%) | full: N_c |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | 53 | 99 | 99 | 369 | 518 | 518 |
| 6 | 59 | 114 | 114 | 416 | 576 | 576 |
| 11 | 65 | 124 | 124 | 453 | 623 | 623 |

The N_cov in the table includes the non-convergence margin (c₀′, p₁′). Without the margin (ε_max = 0), N_c is 92/102/110 (standard) and 353/396/428 (full, set by N_cov(95%)); with the margin, N_c at full level increases by about 47%, mainly from 95% coverage: the distance between p₁′ and c₀′ shrinks from 0.05 to about 0.040.

These values are design values; implementation phase 2 will confirm them by simulation on the toy detector (§8.7).

| Strength level | G8 |
| --- | --- |
| screening | only the Asimov bias of the full evaluation is reported, no decision is made; the result gets the `closure-not-tested` flag, and the upper limit of the evidence grade is `calibrated-unvalidated` |
| standard | N_c per the table above; bias and 68% undercoverage |
| full | N_c per the table above; plus 95% undercoverage |

Locally linear toys **must not** be used for G8.

### 8.5 Locally linear toys and the linearity check

Locally linear toys are used only for the p-value of G6, the χ̄² weights of G2, and the reference distributions of cross-validation.

- The G2 toys take the restricted fit on the boundary as the truth point, with V̂ the same as in G6, and one independent bootstrap per toy.
- Their predictions likewise carry, per §6.6, independent MC noise with the same structure as the actual fit (replica-difference construction: each toy has its own pair of replicas, and the perturbation (m_a − m_b)/√2 is propagated linearly to the fit point with the Jacobian). Otherwise the observed χ² contains nominal MC noise while the reference distribution does not, and with V_MC ≤ 0.1V_data as allowed by P5, the size of G6 can be several times α (estimated as 2.5α–5.6α and about 3.5α, depending on ndf and the computation method).

**Linearity check**: the linear approximation must hold at the toys' **actual landing points**, so the check points are taken directly from the toy distribution:

1. Generate ≥ 50 locally linear toys and take their fit points β̂*.
2. Do a full evaluation at each β̂* and compare Δχ²_full with Δχ²_lin, where Δχ²_full = χ²_full(β̂*) − χ²_full(β̂) and Δχ²_lin is the same difference in the linear model, with β̂ the fit point of the actual data (in cross-validation, of the fold) (D56).
3. It passes only if the fraction with difference > 0.5 is ≤ 5% (the allowed fraction is a design value, see §8.7).

This sampling covers the region where the toys actually are, and three-way and higher interactions are also reflected in the full evaluation. Points at ±2σ along the eigen-directions are still kept as well, to report the directions of nonlinearity.

For cross-validation, the above check is repeated at **the fit point of each fold**. Leave-one-out checks all folds when n ≤ 20; when n > 20, it always includes the two end folds (the first and the last fold in the declared order of the observables, D56) and the 5 folds with the highest leverage, plus 5 more folds drawn at random.

On failure, use a quadratic model or full toys instead.

**The asymptotic distribution** is used only when all of the following hold:

- there are no active constraints;
- the linearity check passes;
- the Poisson expected count per bin is ≥ 5;
- for binomials, nε and n(1−ε) are both ≥ 5.

### 8.6 Strength levels

| Level | What is executed | Enumerated models | Suggested review tier |
| --- | --- | --- | --- |
| screening | all gates of stages B, D, E; G7 with K = 5; G6 may use the asymptotic distribution (subject to the conditions of §8.5); G8 only reports | only the nominal model is fitted | R1 |
| standard | all gates; G7 with K = 10; G8 per §8.4 | each fitted separately, envelope taken | R2 |
| full | all gates; N_c of G8 per the table of §8.4, and 95% coverage checked | each fitted separately, envelope taken | R2, plus a second reviewer |

---

### 8.7 Thresholds to be calibrated in implementation

The thresholds below are **design values**. Their correctness depends on how the inference behaves on the actual model, which is decided more reliably by simulation than by reasoning in text. Implementation phases 1–3 will calibrate them one by one on the toy detector (the toy-detector simulation is delivered in phase 1), and the results are written back into this section. Until calibration is complete, results executed with these design values always get the `provisional-thresholds` flag.

Cells marked "note n" in the table have their full calibration method in the note with the same number below the table.

| Threshold | Design value | Calibration method | Implementation phase of calibration |
| --- | --- | --- | --- |
| N_c and coverage targets of G8 | the table of §8.4 | estimate the overall false-alarm rate and power with 1000 repetitions of G8 | 2 |
| allowed fraction of the linearity check | 5% of toys with difference > 0.5 | compare the G6 p-value distributions and coverage of locally linear toys and full toys | 2 |
| λ estimate of P7 | cross product of two independent MC sets | compare with "single MC set minus tr(C⁺V_Δ)", and verify unbiasedness with alternative hypotheses of known truth | 2 |
| c and linearity threshold of shift mode | c = 0.1 (P8 at θ_ref; 1.5c for the recomputation at θ̂); t_lin = 0.06 for Δ_i of §5.5 (replaces the 30% symmetry and the 2 ± 0.3 ratio; settled by computation, en/compute-19-2.md; to be confirmed by the author) | compare shift and profile coverage in ≥ 1000 repetitions per configuration, with the true φ drawn from its constraint, over the information λ, the nonlinearity of the φ response and the refit noise (note 5) | 2 (first calibration done on a reduced toy; confirmation on the toy detector open, note 5) |
| Bonferroni z of P0, P6 | α = 0.01 | estimate the false-alarm rate with a correct kernel and surrogate model | 1, 3 |
| K of G7 | screening 5, standard 10 | estimate power with a deliberately underestimated V_MC | 2 |
| f in the ESS threshold | 0.1 | check the behavior of G7, G8 at f = 0.1 | 2 (G7, G8 delivered in phase 2) |
| Jacobian MC-noise bias bound of P5 (§8.2 note 3) | \|b_J,i\| ≤ 0.15σ_tot,i^design (settled by computation, en/compute-19-13.md; to be confirmed by the author) | in the θ-dependent configuration of note 4, confirm that with the bound the extra 68%/95% undercoverage is ≤ 0.01 (≥ 10⁴ repetitions) | 2 |
| θ-noise bounds of P5 (§8.2 note 3, fifth item; mode where the map varies with θ) | s_i ≤ 0.25, κ_i ≤ 0.05 (D28, revised 2026-11-09; first estimate from one synthetic study, en/research-D28.md §4.3) | with the exact map covariance of the scan, vary the photons per mapping run, the design-point spacing and the seeding, and confirm that within the bounds the pull standard deviation of θ̂ is ≤ 1.05 (≥ 2000 repetitions per configuration, se of the pull sd ≈ 0.016; the repetition count is a choice of the D28 verification, accepted by the author, 2026-11-09; source en/d28-verify.md minor 9) and G8 passes at the full level of §8.4; include purely nested coupling, whose residual pull width of 1.05 is unexplained (D85) | 3 |
| PDE split (§6.7) | split check: χ² at α = 0.01, and \|Δθ_i\| + 2 sd(Δθ_i) ≤ 0.1σ_tot,i^design with the pair sized by sd(Δθ_i) ≤ 0.1σ_tot,i^design/(2 + z_{1−0.025/d}), a joint pass probability ≥ 0.94 under an exact split; route-3 replicas: pseudo-mass K_cat/2 ≤ 0.01 n_b per bin and Dirichlet variance (analytic) ≥ 0.98 of the multinomial variance; transit integerisation to 10⁶ (design values decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md) | on the ZDC fixture with optics, the false-rejection rate of the split check under an exact split, and its power against a reflectance tied to the PDE; the route-3 replica covariance against the analytic multinomial covariance over several grid sizes (§15.2) | 3 |
| smoothing model of A0 | declared by the contract | confirm correct reporting with the ZDC linearity example | 1 |
| numerical tolerance τ_num of exact constraints (§9.2; variance in standardized units) | 10⁻¹⁰ | four confirmations on the toy detector (note 1) | 2 (D76) |
| negligibility condition for rounding (§2.1) | max_u uᵀRu / uᵀC̃⁽⁰⁾u ≤ 1/25 | confirmation by scan and on both sides of the boundary (note 2) | 2 (D76) |
| n_min of shape Gaussian summary statistics and B of the parametric bootstrap (§2.1) | note 3 | note 3 | 2 (D76) |
| upper limit on the fraction of G5 failures in cross-validation toys (§9.3) | 20% | compare the size of the conditional reference distribution and of the true conditional distribution on critical fold splits (P3 just passing) and on scans of the θ̂ position; confirm that above 20% the size bias is no longer negligible | 2 |
| replica-difference construction of toys (§6.6) | default construction | note 4 | 2 |
| number of toys for the estimated Ĉ_r | ≥ max(500, 10k) | compare the distribution of the ratio of eᵀĈ_r⁺e to eᵀC_r⁺e (median after the correction factor (n−k−2)/(n−1) within 1 ± 10%) | 2 |
| one-sided lower bound of the cross product λ̂_a^cross (§9.4) | independent MC repetitions or a valid bootstrap, with the number of repetitions and the quantile method declared in the plan; level 1 − α_P/(2m) on the toy path, 1 − α_P/m on the analytic path | on alternative hypotheses of known λ_a, over a range of MC noise, confirm that the bound lies below the true λ_a with at least its nominal probability (D59) | 2 |
| basin admission, separation and tie tolerances, and number of starts (§7.4) | R_admit = 1; τ_bar = max(0.1, 4σ_noise) at 19 segment points; τ_tie = max(0.01, 4σ_noise); max(2d, 16) Sobol starts (settled by computation, en/compute-D57.md; to be confirmed by the author) | note 6 | 2 (3 for the RICH replica) |

**Notes**

1. **τ_num**: confirm on the toy detector:
   - constraints that hold by construction (sums by definition, residuals of shapes conditioned on the total) have variance < 10⁻¹⁴ on C̃_r without rounding and nominal residual expectation < 10⁻⁷;
   - a direction with standardized sd 10⁻³ is caught when wrongly declared;
   - when two observables with correlation 1 − 10⁻⁷ are not declared, the rank condition passes;
   - diag(100, 10⁻⁶) and its correlation matrix give the same decision.
2. **Negligibility condition for rounding**:
   - on a scan of σ⁽⁰⁾/ρ from 0.1 to 10, on observable pairs with correlation coefficient |c| just on either side of the boundary 1 − 25ρ̃² (ρ̃ = 0.02, 0.05, 0.1, 0.15, 0.2, including positive and negative correlation), and on uniformly distributed true values, confirm that when the condition holds, the size of T_v for every true value is within α ± 25% (design-stage trial computation 0.046–0.058);
   - confirm that adding a double-precision observable whose partial correlation with the rounded observables is 0 does not change the ratio, while one whose partial correlation is not 0 makes the ratio larger (by 1/(1 − c²) for direct correlation c; case of correlation through a third observable: 0.0156 → 0.0565);
   - confirm that the decision does not depend on the choice of eigenvectors (recompute with an arbitrary rotation when eigenvalues are degenerate);
   - with a ratio that depends monotonically on θ, confirm that the recomputation at the prior vertices and at θ̂ covers the worst case outside the scan points;
   - confirm that the shared rounding difference for m = 2 is 0.33% of the smallest allowed variance.
3. **n_min and B**:
   - **Design values**: n_min = 20; B ≥ max(500, 50p); N_t ≥ 10, K_b ≥ 6, ν_b = N_t(K_b − 1) ≥ max(50, d + 5) (default N_t = 10, K_b = 6); the bootstrap is regenerated with common random numbers at each θ_ref update, not carried over by reweighting.
   - **Calibration method**: with shapes for which the worst condition at the evaluation point just holds (K = 3, 5, 50) and other summary statistics of shared events (p = 10, 30, 50), confirm the following.
   - +½ estimator: the residual mean is 0 with the prediction-side definition of §2.1 (with "normalize MC to the data amount first, then add ½" as the negative control).
   - Size of T_v:
     - the rejection rate of the toy-calibrated T_v computed with the bootstrap covariance differs from α by < 10% on toy ensembles without non-convergence (decided with ≥ 10⁴ repetitions; probability of passing about 0.98 when the true size is α);
     - when non-convergence of ε = 0.5% and 1% is injected and counted per §7.3, only one side is subject to acceptance: rejection rate ≤ 1.1α (likewise with ≥ 10⁴ repetitions). The counting rule guarantees size ≤ α, at the cost of about ε in effective level (about 0.040 at α = 0.05, ε = 1%), which is only reported, not subject to acceptance.
   - **Rejection rate of G6 under the null hypothesis ≤ 1.5α**.
   - Convergence fraction:
     - the fraction converged within 30 iterations in §7.3 ≥ 1 − ε_max = 99% (each class of ensemble of §7.3 has its own acceptance test; cross-validation toy ensembles have toys as members and are checked against 1 − ε_max,cv);
     - for cross-validation (leave-one-out with n ≤ 20, and the F-fold and the leave-one-out with n > 20 that the plan adopts), after multi-start refitting, the fraction of toys with all folds converged ≥ 1 − ε_max,cv (98% for F ≥ 3, 98.01% for F = 2).
   - Inject non-convergence of ε = 0.5% and 1%, split into outcome-independent, and fully correlated in two directions:
     - G8: pseudo-data concentrated in covered/not-covered ones, interval toys concentrated in those with the largest/smallest statistic;
     - G7: concentrated in the refits closest to/farthest from θ̄;
     - reference-distribution and power toys: concentrated in those with the largest/smallest statistic;
     - Σ_boot and Ĉ_r: concentrated in the realizations with the largest/smallest projection along some direction.

     When handled per §7.3, the acceptance criteria are:
     - the false-alarm rate of G7 ≤ 2α when the MC is correct;
     - G8 at standard and full level, at the N_c of §8.4, passes the overall false-alarm rate by the rule of §15.2 (≤ 62 false alarms in 1000 repetitions); the power for 68% and 95% undercoverage, for a method whose coverage under the actual procedure (including the counting of interval toys) is p₁, passes by "≥ 775 detections in 1000 repetitions" (probability of passing 0.98 when the true power is 0.8, 0.04 when it is 0.75);
     - the rejection rate of T_v ≤ 1.1α as above;
     - the power estimated by P7 agrees with the power actually measured with the same decision rule;
     - the trigger rate of the ratio test when ε ≤ ε_max is < 10⁻³ (per ensemble; for G8 additionally including the ensemble of interval toys summed over the whole of G8, and for the actual data the ensemble summed over one interval construction);
     - the bias of Σ_boot and Ĉ_r caused by replacement, in the three cases where non-convergence is independent of the outcome, or concentrated in the realizations with the largest or with the smallest projection along some direction, after the w correction of §7.3 (Σ_boot with ε̂⁺, Ĉ_r with ε̂), is subject to acceptance on one side only: the variance in any direction must not be underestimated by more than 1%, and λ̂_a must not be overestimated by more than 1%. Bias in the conservative direction is only reported: λ̂_a at most about 1/w(ε̂) − 1; Σ_boot, corrected with w(ε̂⁺), on average about +9–19% at the default n = 60 (§7.3).
   - Toy estimate of Σ_boot: average bias relative to the truth (many toys × many bootstraps) < 10%, relative standard deviation of the trace ≤ 0.3; the Asimov estimate is always 0, as the negative control.
   - θ that require resimulation: under common random numbers at the Geant4 layer, the convergence fraction of §7.3 has a separate acceptance test.
   - V̂ regenerated with common random numbers and V̂ generated independently at that θ_ref agree in expectation: decided by the standardized difference |(E V̂ − V)_ij| / √(V_ii V_jj) < 0.05 (also defined for elements whose true value is 0); one carried over by reweighting deviates cell by cell (decided by the same standardized difference, counting both cells that are too high and cells that are too low), as the negative control.
   - When the G6 toys use Wishart sampling instead, their rejection rate has a separate acceptance test.
   - The correction factor is used in the reported effect sizes only when the inverted matrix is entirely bootstrap, and does not enter the decision (§2.1).
4. **Replica-difference construction of toys**:
   - **Size of T_v**: on a toy detector with known MC noise and a truth without MC noise (V_MC/V_data = 0.03, 0.1, 0.3, 1; k = 5, 20; including correlated MC noise, small-count Poisson bins and BB-lite blocks), calibrate T_v with the replica-difference construction; the rejection rate is within α ± 25% (≥ 10⁴ repetitions; tests approximations (1)(2)). The configurations include the case where the noise of the nominal MC varies with θ (for example, a Jacobian carrying MC noise), and the coverage of intervals in that case is reported; this configuration is only reported, not subject to acceptance, and is not a pass condition.
   - **Interval toys**: coverage (truth at the scan point) within nominal.
   - **Truth of G8**: on the toy detector, the truth of G8 is always the known analytic truth, and the events of the pseudo-data are generated by an event generator of the analytic truth. The 100-times truth MC is used only in the actual G8; for its shared shift, the effect on the false-alarm rate is reported separately with a toy configuration that uses a 100-times truth MC (within the range of P5).
   - **False-alarm rate of G8**: when V_MC, the effective-count approximation and the evaluator are all correct, the overall false-alarm rate of G8 computed with the decision rule of §8.4 (the Holm procedure and the joint rule for bias, "significant and |b̄| > 0.2σ_tot") is ≤ α_G8 × 1.25 (including the shift of the shared truth MC). Looking at the t test for bias alone, the shared shift raises the false-alarm rate, so the object of the acceptance tests is the decision rule itself.
   - **Detection rate of G8**: report the detection-rate curves of G8 for V_MC underestimated by a factor of 2 and for failure of the effective-count approximation (versus N_c, V_MC/V_data, d, strength level, the number of directions in which P5 is saturated, and how the interval is constructed), with no threshold; a detection-rate threshold (for example ≥ 0.8) is unreachable within the range of P5.
   - **The effective-count approximation itself**: verified with small-count Poisson bins and weighted MC with non-uniform Σw²/Σw (for binomial blocks: the configurations of en/compute-D30.md, including heavy-tailed weights, and points on the boundary of the range of §2.1); the pull of an MC nuisance is the signed root of the likelihood ratio of its auxiliary likelihood at the true value, sign(p̂ − p)·√(2[ℓ(p̂) − ℓ(p)]), and the 68% interval is −2Δln L ≤ 1 (settled by computation, en/compute-D30.md; to be confirmed by the author). The pass conditions are: for the MC nuisances of BB-lite and of the auxiliary binomial likelihood, mean pull |μ| ≤ 0.1, standard deviation within [0.9, 1.1], coverage of the 68% interval within 0.683 ± 0.03 (≥ 2000 repetitions). For the auxiliary binomial likelihood the acceptance establishes the range k_exp ≥ 30, Δ_sk ≤ 0.1 of §2.1 (en/compute-D30.md: 175 of 175 configurations pass on fresh seeds); a weighting method or count range outside it is unvalidated (§2.1).
   - **Power toys**: after scaling with the cross-product lower bound, when the true power is 0.7–0.8 the frequency of claiming a lower bound ≥ 0.8 is ≤ 5% (tests approximation (3)); this also includes a cross-validation configuration with correlation between folds (4 folds, with events shared across folds), with the same frequency limit.
   - **Surrogate model**: when a surrogate model is used, also test with a toy surrogate model of known interpolation error.
   - **Negative controls**: re-digitization changing only Philox, reusing the nominal MC without perturbation, sampling with N(0, V_MC) where the direction of V_MC is wrong (size too large), and taking nominal as truth with a single replica as prediction (size too small).
5. **Shift mode** (calibrated on a reduced calorimeter-linearity toy with one material-thickness φ, label `synthetic`; en/compute-19-2.md):
   - c: shift-mode coverage is nominal for λ = 0.01–1 (deviation ≤ 0.006 at 68%, ≤ 0.003 at 95%, 10⁴ repetitions); the width ratio to profile mode equals √((σ_f² + b²)/(σ_f² + b²/(1+λ))) within 0.1%, and the rms central-value difference equals √(λ/(1+λ))|b| within 2%. The recomputation of condition 1 at θ̂ with c has false-alarm rate 0.50 at λ = c; with 1.5c it is 10⁻⁴.
   - t_lin: over 14 response forms (quadratic, cubic of both signs, exponential), r = |b|/σ_f = 0.5–4 and refit noise 0–0.03 s_i (4000 repetitions each), Δ_i ≤ 0.06 gives false-alarm rate 0.000 under linear and ≤ 0.011 under near-linear responses (Δ_true ≤ 0.03) at refit noise ≤ 0.01 s_i, rejects every configuration whose 95% coverage is below 0.936 and below profile mode, and the intervals that pass cover ≥ 0.668 / 0.935. Configurations with 0.06 < Δ_true ≲ 0.12 can be rejected although their coverage is acceptable (indifference band). The former rule (30%, 2 ± 0.3) rejected 14 of 42 acceptable configurations with probability 1 and passed a cubic response whose 95% coverage was 0.922.
   - Open: confirmation on the toy detector of §15.1 with the resimulation-level φ, more than one shift-mode φ (the sum over l in Δ_i), and a check of the refit reproducibility in a real fit.
6. **Basins (§7.4)** (settled by computation, en/compute-D57.md; to be confirmed by the author):
   - On the bimodal variant of §15.1 (exact degeneracy, weakly broken degeneracy, close to the bifurcation of the two basins; ≥ 10³ toys each), confirm that the classification (the admitted basins matched by position, and the tied set of θ̂) is unchanged under 10 reseedings of the starts in ≥ 99% of toys; design-stage trial computation (en/compute-D57.md, d = 3, σ_noise = 0): 1.000 with 16 starts, 0.996–0.997 with 8, 0.907–0.970 with 2d = 6.
   - Report the distributions of σ_tot,i/σ_prior,i of admitted and non-admitted endpoints (trial computation: admitted ≤ 1.00, non-admitted ≥ 1.02) and confirm that R_admit separates them.
   - Repeat with an MC-noisy objective (σ_noise > 0, common random numbers and independent seeds) and confirm the stability with τ_bar and τ_tie as given.
   - Report the fraction of toys whose θ̂ lies outside the truth basin and the G8 bias; confirm that the toy-calibrated interval of §7.5 for `multimodal` results has G8 coverage within the targets of §8.4 (trial computation of the profile interval with the χ²₁ threshold: 0.929–0.936 at 95%).
   - Phase 3: confirm the classification on the degeneracy of the RICH replica (§15.1).

`provisional-thresholds` is an orthogonal flag, inherited downstream from **all** upstream (including `variation`) as a union per §10.2; it does not lower the evidence grade, but it forbids use as the basis for formal publication.

## 9. Validation

### 9.1 Validation modes

| Mode | Procedure |
| --- | --- |
| `holdout` | Open the validation data and compute the statistic of §9.2 |
| `cross-validation` | The reference distribution is obtained with toys (§9.3) |
| `none` | No validation; the evidence grade is capped at `calibrated-unvalidated` |

### 9.2 The holdout statistic

#### Covariance of the residuals

Let β = (θ, ν, η, φ in profile mode, the MC nuisances of non-Gaussian blocks, the normalization ω of calibration shapes), A = Σ_β J_cᵀ V_cc⁻¹. When the calibration side declares N_d,c, V_cc⁻¹ means the projected inverse S⁻¹Ũ_⊥(Ũ_⊥ᵀṼ_ccŨ_⊥)⁻¹Ũ_⊥ᵀS⁻¹ of §2.1; the same applies to d_l and to E[r|a] of §9.4.

V contains only V_data^unc, V_MC, V_emu, V_learn; ν and η enter through β, so they are not counted twice. The covariance of the validation residuals is:

```latex
C_{r_v} = V_{vv} + J_v \Sigma_\beta J_v^{T} - J_v A V_{cv} - V_{vc} A^{T} J_v^{T}
+ \sum_{l\in{\rm shift}} d_l d_l^{T}
```

```latex
d_l = \left(\frac{\partial \mu_v}{\partial \phi_l} - J_v A\,\frac{\partial \mu_c}{\partial \phi_l}\right)\sigma_{\phi_l} = \left(\frac{\partial \mu_v}{\partial \phi_l} + J_v \frac{\partial \hat\beta}{\partial \phi_l}\Big|_{\text{refit}}\right)\sigma_{\phi_l}
```

d_l is the **complete** response of the validation residual when the **true** φ_l deviates by 1σ from its nominal value while the fit still holds φ_l fixed at the nominal value: the data y_v move directly by ∂μ_v/∂φ_l, and the movement of the calibration data propagates through the fit to β̂ (−J_vA∂μ_c/∂φ_l).

It is obtained from the ±1σ refits of §5.5: a refit is "data unchanged, φ_l in the model moved", and the resulting ∂β̂/∂φ_l|_refit = −A∂μ_c/∂φ_l, so the sign in the second form is a **plus**. This is the same structure as E[r_v|a] = Δm_v − J_vAΔm_c of §9.4.

**In shift mode the size is a prior average**: Σ_l d_l d_lᵀ is included according to the prior of φ_l (prior-predictive, see below), so the size of T_v equals α only when φ follows its prior distribution.

- At a fixed true φ, the conditional size varies with the true deviation, and can approach 1 when d_l dominates C_r. Example (α = 0.05): k = 1 and d_l = 3, in units where the part of C_r other than d_l d_lᵀ is 1 (so C_r = 10); at true deviations of 0, 1σ, 2σ, 3σ it is 5.7 × 10⁻¹⁰, 6.9 × 10⁻⁴, 0.42, 0.997.
- P8 only limits the information of the calibration data about φ; it does not limit ∂μ_v/∂φ.
- So a failure in shift mode, and the `final` failure record it writes, means the data disagree with "the model plus the declared φ prior"; the cause may be a true deviation of φ, not necessarily the model itself. This is a property of the declared construction; the rules do not change.

**Scope of the formula and generalization**: the A above applies only to a validated locally linear Gaussian representation; β containing MC nuisances does not automatically make A = Σ_βJ_cᵀV_cc⁻¹ applicable to Poisson/binomial likelihoods.

- Mixed or non-Gaussian likelihoods use the implicit-function response derivatives of §6.7, differentiating with respect to the calibration data, the MC auxiliary measurements and the external constraint centers one by one.
- If x_in is the vector of all random inputs (including the validation data), then C_r = D_r Cov(x_in) D_rᵀ, D_r = ∂[y_v − μ_v(β̂(x_in), φ)]/∂x_in; all cross covariances are counted only once.
- The shift-mode d_l likewise uses the complete refit derivatives and does not force in the Gaussian A.

The contract must declare which auxiliary measurements are resampled, or which explicit prior-predictive construction is used; the curvature covariance of Σ_β does not equal the sampling covariance of β̂ under every construction.

**Cases in which T_v is calibrated with toys**: in any of the following cases, T_v is calibrated with complete toys that redo the fit, the MC and the validation procedure (the generation of toy data and the frozen V̂ follow "Toy data and V̂" in §7.3: the bootstrap is not redone):

- low counts;
- active boundaries;
- nonlinearity;
- non-Gaussian blocks;
- an estimated C_r;
- V contains the bootstrap part of §2.1;
- the validation side contains free-ω count shapes, or event samples whose normalization is free and that belong entirely to validation. Their totals are known only after opening, and "low counts" decided from N_decl before opening may not agree with N_obs, so such contracts are fixed to the toy path already at locking, and the path does not need to be re-judged from N_obs after opening; the toys are regenerated after opening conditioned on N_obs according to §2.1.

When C_r is singular, first handle the deterministic constraints, then use the image space and the rank; the n_v degrees of freedom must not be restored by adding an arbitrarily small diagonal term.

#### The subspace N_d of deterministic constraints and the definition of C_r⁺

In this document C_r⁺, C_{r_v}⁺, Ĉ_r⁺ are always defined as here, including in §6.6, §8.7, §9.3, §9.4.

**N_d**: the subspace spanned by the **exact constraints holding by construction** that the contract declares; each one is written as n_jᵀ r = 0. For example, a definitional sum such as "total = sum of the parts" when a release gives both the parts and their sum, or the sum of the shape residuals conditioned on the total in §2.1 being 0. The contract must write out the construction for each one.

- A direction may be listed only when **the data and all predictions satisfy it exactly by construction** (except for rounding).
- A definitional sum requires that the prediction of the derived quantity be derived from the predictions of its components by definition: first compute the predictions of the components in link space with the ν, η corrections added, then sum them by definition; no independent ν, η terms may be added to the derived quantity. Otherwise the sum must not be declared.
- Exact relations whose coefficients depend on the observed component totals (the general form; for example t = Σ_j w_j ε_j between the efficiency t of two merged periods and the component efficiencies, or the same kind of relation between t123, t12 and ε3 with three components): taking t = Σ_j w_j ε_j as the example, the weights w_j = N_tot,s,j / Σ_j N_tot,s,j depend on the observed component totals (the event samples of §2.1 are conditioned on the component vector).
  - When the sample contains calibration observables, N_tot,s is known before locking, the weights are fixed known coefficients, and the relation is declared as N_d as usual.
  - When the sample belongs entirely to the validation data, the weights are known only at opening, and at locking there is no fixed n_j that can express it. So the contract must not use all the observables that make up such a relation at the same time (for all such relations, not only the form "derived quantity plus all components"); at least one is listed as unused according to §5.2 (reason: it has an exact relation with other observables that depends on the observed totals); the checker rejects contracts that use all of them at the same time. Rationale: if it is not declared, (c) decides that it is a contract error; if it is declared with the weights of N_decl, a correct release also triggers the data-side check at opening.
- Directions that merely have small variance, or are satisfied only within MC noise or surrogate-model error (for example the difference of two highly correlated observables), are not constraints; they always stay in C_r and are tested by T_v.

**Standardization and C_r⁺**:

- Let S = diag(s_i), where s_i = σ_i⁽⁰⁾ > 0 is the data standard deviation at θ_ref generated by the model, without rounding (containing only V_data^unc, not the fully correlated systematic errors of η; §2.1). s_i is not declared by the contract, so no threshold can be relaxed by declaring an overly large scale.
- Validation observables with σ_i⁽⁰⁾ = 0 (in cross-validation, the calibration observables of each fold), that is, those whose data error enters only through η, are rejected by the contract checker and should instead be expressed as constraints on η (§5.2).
- C̃_r = S⁻¹ C_r S⁻¹, ñ_j = S n_j / ‖S n_j‖. Let Ũ_⊥ be an orthonormal basis of the orthogonal complement of span{ñ_j}, and P̃_N the orthogonal projection onto span{ñ_j}.
- Define C_r⁺ = S⁻¹ Ũ_⊥ (Ũ_⊥ᵀ C̃_r Ũ_⊥)⁻¹ Ũ_⊥ᵀ S⁻¹, with degrees of freedom k = dim N_d^⊥.
- According to §2.1 only negligible rounding is allowed, so rounding removes no direction.
- Untestable observables are not in the validation contract (§5.2), so the engine does not reduce N_d. Approaches in which the engine reduces N_d (taking intersections, reconditioning, treating near-zero directions as untestable) are not adopted, because they bring defects such as basis dependence, order dependence, rounding-dominated directions and inconsistent evaluation points, while exclusion and re-declaration need no new rules.
- All decisions are made in standardized coordinates, so they do not change with the units of the observables or the scale of the link space. Exact constraints satisfy C_r n_j = 0 when there is no rounding term, and then this definition gives the same T_v as taking the orthogonal complement of n_j in the original coordinates; with rounding terms the two differ slightly, and the definition in standardized coordinates always prevails.

**Directions removed after opening** (the only exception): the fallback of §2.1 that removes directions after opening, including free-ω count shapes with N_obs = 0, event samples with N_tot,s = 0, some components being 0 and the collapse it causes, and bootstrap rank deficiency of samples that belong entirely to validation.

- It removes the K − 1 directions of that shape (for event samples, the dimension of the within-sample summary statistics on N_d^⊥), and k decreases accordingly.
- The projections of the removed directions on N_d^⊥ (in standardized coordinates) are merged into the null space, Ũ_⊥ becomes the remaining orthogonal complement, and C_r⁺ is computed on it with the same formula.
- These cases are always handled according to §2.1, and are the only exception to "not redone in the validation stage, no rank-condition failure in the validation stage".
- The rounding ratios on the remaining directions follow the decision at locking and are not re-judged; removing directions may raise them slightly, which only affects the bound on negligible rounding; this is explicitly accepted.

**Rounding terms are not variance of the constraints**: the rounding included as ρ²/12 in §2.1 makes exact constraints show a tiny variance in C_r. The declaration checks below are always made on C̃_r⁽⁰⁾ **without the rounding terms**; T_v is computed on N_d^⊥ with the C̃_r that contains the rounding terms. The component of the data on N_d contains only rounding and does not enter T_v, so no separate tolerance or completeness check is needed.

#### Declaration check

Owner and timing: `calib_validate.py`, called by `calib_design.py` at P7, executed at θ_ref; and redone with the quantities at θ̂ after the iteration of §7.3 reaches θ̂ and before the validation data are opened (`calib_fit.py` calls the same implementation of `calib_validate.py` after convergence, the result is written to a record, and `calib_data.py` decides from this record whether to open). The check uses only model-generated errors and predictions and does not read the values of y_v.

- (a) The declared subspace has no variance: block norm ‖P̃_N C̃_r⁽⁰⁾ P̃_N‖ ≤ τ_num. When C_r is estimated with toys, use the largest sample variance on span{ñ_j} of the toy residuals **without rounding applied**.
- (b) The residual expectations of the nominal model, the design points and **every alternative hypothesis** are ≤ √τ_num on every ñ_j (exact constraints hold for alternative hypotheses as well, §9.4).
- (c) **Rank condition**: the smallest eigenvalue of Ũ_⊥ᵀ C̃_r⁽⁰⁾ Ũ_⊥ is > τ_num (the eigenvalues do not depend on the choice of basis).

τ_num = 10⁻¹⁰ (§8.7) is a numerical tolerance: the variance of exact constraints in double precision is far smaller than it, and any physically varying direction is far larger than it (for example, for two observables whose standardized covariance is the correlation matrix with correlation 1 − 10⁻⁷, the smallest eigenvalue, i.e. the variance along the unit direction (x₁ − x₂)/√2, is 10⁻⁷; it stays in C_r and (c) passes), so for the declared N_d there is no gray zone between the two kinds of direction.

After untestable observables are excluded, the remaining observables may have directions among them that vary physically but have standardized variance ≤ τ_num (for example the difference of two almost fully correlated observables). It is not a constraint by construction, so it cannot be declared as N_d, and (c) fails; the remedy is not to use one of the observables causing it (listed according to §5.2).

Failure of any item is a **contract error** (N_d listed wrongly, an exact constraint omitted, or some prediction violates a constraint holding by construction). Wrong listing and omission are handled the same way:

- The contract is rejected: at P7 by `calib_design.py`, and in the redo at θ̂ by `calib_fit.py`, reported with exit code 2; the remedy level is the contract; no result is produced.
- Because the declaration check is a precondition of opening (see below), a contract error does not use up the holdout.

When N_d^⊥ is empty, or there are no validation observables after exclusion (k₀ = 0), there is no direction to check, (c) is treated as passed, and it is handled according to "k = 0 determined before opening" in §9.5. These are all decided by the declaration and the model and are completed before opening, so they do not use up the holdout.

#### Preconditions for opening the validation data

`calib_data.py` opens the validation data (in cross-validation, computes T_cv) only for a κ that satisfies all of the following at the same time:

1. The declaration check passes.
2. The rounding conditions of §2.1, σ_i⁽⁰⁾ > 0, the lower bound on the expected total of validation shapes (N_exp of §2.1 "Expected total of validation shapes" (ii); N_decl of (i) is decided at locking), n_min of the shape summary statistics, and the block-conversion conditions also pass when recomputed at the fit point (θ̂, ν̂, η̂, φ̂).
3. P7 is not `incomplete` (§9.4).
4. k₀ > 0. When k₀ = 0 is determined before opening, the data are not opened (§9.5); k depends on the N_obs = 0 fallback of §2.1 and is known only after opening, so k₀ is used here.
5. When k₀ > 0 and T_v is calibrated with toys, the replicas of the toys for Ĉ_r and for the reference distribution have been generated according to §6.6 and have passed the non-overlap check.
6. The calibration data are real data (when they come from simulation, rule 2 has already determined the outcome, §10.2).
7. No mandatory gate has failed (rule 1 has already determined the outcome).
8. No mandatory gate is `incomplete`: completing it may require changing the plan, with κ changing accordingly, and an already opened holdout would cap the new κ, the same as for P7.
9. The calibration release and the validation release of the holdout share no raw units (the lineage comparison of §9.5).
10. P7 decides that the power is sufficient. When P7 fails, the grade is already `calibrated-unvalidated` according to §9.4, and opening would only use up the holdout. In cross-validation, likewise, T_cv is not computed, and there is no validation read and no record, so this κ, which is bound to be capped, does not affect other κ through reads or failure records; in this case V is `not-applicable` (§10.2 rule 0).
11. The ratio test of the reference toys and Ĉ_r generated before opening has not failed (§7.3, §9.5).
12. Data lineage and overlap have been confirmed (§9.5).

So a contract error does not use up the holdout. A κ whose outcome is already determined (the general principle of §10.2 rule 0) is not opened, and these preconditions do not need to be completed for it.

Cross-validation has no act of opening: "not opened" as used in this section and §9.5 means, in cross-validation, "T_cv is not computed"; no validation read is produced and no failure record is written.

#### Fixing C_r in holdout, and untestable observables

According to §2.1, in `holdout` mode C_r does not vary with the values of y_v. Exceptions:

- Shapes conditioned on the total, and event samples that belong entirely to validation and whose bootstrap is regenerated with N_tot,s at opening.
- When N_obs = 0, the directions of that shape are removed according to the fallback of §2.1.
- In the other cases, the terms scale with N_obs according to §2.1: the within-shape multinomial term ∝ N_obs, the within-shape propagation term and the shape block of d_l d_lᵀ ∝ N_obs², the cross terms with other observables and the blocks of d_l d_lᵀ between the shape and other observables ∝ N_obs.

So the declaration check and the rounding conditions are final before the validation data are opened; they are not redone in the validation stage, and there is no rank-condition failure in the validation stage (the only exception is the directions removed by the fallback of §2.1; see "Directions removed after opening" above).

Untestable observables (§9.5) are not in the validation contract (§5.2): they are known before locking, the contract excludes them, and N_d is declared on the remaining observables. So the declaration check, the rounding conditions of §2.1, σ_i⁽⁰⁾ > 0, and the lower bounds on N_exp and n_min are all decided as usual on the remaining observables; when they do not hold, the contract is rejected, the same as in cross-validation.

When exclusion changes a shape or a derived quantity (for example a shape conditioned on the total missing one bin, an alr shape missing the reference bin, a derived quantity t = p1 + p2 missing p1):

- The contract re-declares the shape or the derived relation with the remaining observables (for example the remaining bins conditioned on their own sum).
- `calib_likelihood.py` recomputes the summary statistics and the bootstrap according to §2.1.
- `calib_data.py` first applies the merging rule declared in advance according to §2.1, then decides on n_min at all evaluation points.
- When the recomputation fails (the summary statistics or the bootstrap cannot be computed, or n_min is still not satisfied at some evaluation point after merging), the contract must list the whole shape as unused per §5.2, together with every derived quantity computed from it; a contract that does not do so is rejected (D71).

#### Ĉ_r estimated with toys

- Ĉ_r is estimated only on N_d^⊥; the null space must not be redefined from empirical eigenvalues.
- Number of toys n ≥ max(500, 10k) (§8.7). Passing the rank condition is only a necessary condition and cannot replace the lower bound on the number of toys.
- Quadratic forms computed with Ĉ_r⁺ (including λ̂_a of §9.4) are multiplied by (n − k − 2)/(n − 1) to correct the bias of Ĉ_r⁻¹; in cross-validation it is applied fold by fold with k_f to the quadratic form of fold f, and then summed.
- When C_r is an estimate, T_v is calibrated with toys as above, so the power at P7 and in the V stage is decided by the toy rejection rate along the toy path of §9.4 (the same decision rule, §8.1).
- λ̂_a computed with Ĉ_r is used only in s_a of the power toys of §6.6 (the lower bound of the cross product and the single-set value) and is otherwise only reported as a diagnostic (§8.7 compares it with the toy rejection rate); it is not used for other decisions. λ̂_a is not looked up in a χ²_k table for the P7 decision, because that would make the decision rules of P7 and the V stage differ.
- When toys have non-convergence and are replaced according to §7.3, the diagnostic λ̂_a is additionally multiplied by w(ε̂) (§7.3; for a quadratic form in a single direction, the dimension-independent worst factor is taken), handling the power claim conservatively with the worst replacement bias.
- s_a of §6.6 multiplies w(ε̂) only into the numerator λ_a^low, not into the denominator λ̂_a^single, so s_a can only become smaller (conservative).

#### Data-side constraint check

When the validation data are opened, `calib_data.py` checks that the declared constraints hold within the worst-case rounding bound. Untestable observables are not in the validation contract, so the check is made only for the constraints declared by the contract.

- **Constraints acting on the data** (for example definitional sums): check |n_jᵀ y_v − c_j| ≤ Σ_i |n_ji| ρ_i^obs / 2 + double-precision error.
  - c_j is the constant of the constraint written n_jᵀ y = c_j, declared by the contract together with n_j (for example c_j = 0 for "total − sum of parts", c_j = 1 for f_A + f_B = 1; §5.2 clause 7) (D66).
  - ρ_i^obs is computed from the values actually read, according to the format declared by the release. For a released value used directly, ρ_i^obs is its last-digit unit u_i. For a quantity y_i = f_i(x) that the workflow derives along the lineage from released values x_k, ρ_i^obs / 2 is the half-width, about the computed value f_i(x̃), of a guaranteed enclosure [lo_i, hi_i] of f_i over the rounding box Π_k [x̃_k − u_k/2, x̃_k + u_k/2]: ρ_i^obs / 2 = max(hi_i − f_i(x̃), f_i(x̃) − lo_i), rounded up. `calib_data.py` computes the enclosure step by step along the lineage, as the intersection of (i) the natural interval extension of f_i with outward rounding and (ii) the mean-value form f_i(x̃) + Σ_k G_ik·[−u_k/2, u_k/2], where G_ik is an interval enclosure, with outward rounding, of ∂f_i/∂x_k over the box. A tighter enclosure may be used only if it is equally guaranteed. A lineage step whose output is itself released and read starts again from the box of that read value. For linear f_i this gives exactly Σ_k |∂f_i/∂x_k| u_k / 2. First-order propagation Σ_k |∂f_i/∂x_k(x̃)| u_k / 2 is not used for nonlinear f_i: it is not an upper bound, and a correct release can exceed it (settled by computation, en/compute-D4.md; to be confirmed by the author). A lineage step that divides by, or takes the logarithm of, a box containing 0 has no rule yet (D4).
  - It is computed at the time of the check: for holdout at opening, for cross-validation and for N_d,c on the calibration side at locking. The values have been read by then; this tolerance is used only for the constraint check and takes part in no other decision.
  - ρ_i of §2.1 is not used, because it is computed from the prediction and does not read the observed values. In a significant-digits format, a value read with a larger last-digit unit than the tolerance assumes would make a correct release with a correct model trigger. With the ±5σ_i⁽⁰⁾ window maximum of §2.1 this happens only for a value read beyond the window (at most about 9 × 10⁻⁷ per check for t = a + b in 3-significant-digit format); with the unit at the predicted central value it happens whenever the observed value crosses a decimal boundary that the prediction does not reach (about 6% per check for t = a + b in 3-significant-digit format when the prediction of t lies 1.3σ_t below a decimal boundary; at most about 2% for a true value uniform on the decade grid; en/compute-D73.md). ρ_i^obs makes the bound strict without depending on where the observed value falls.
- **Timing of the check in cross-validation**: the data-side constraint check of cross-validation is made at locking; on a mismatch the contract is rejected (remedy level: contract), and no failure record is written. Rationale: these data are readable before locking; if the check waited until the first computation of T_cv and wrote a `final` record, all later cross-validations on these calibration units would be capped.
- **Identities acting on the residuals** (for example the sum of the shape residuals conditioned on the total being 0): check |n_jᵀ r_v| ≤ double-precision error; this only confirms that the residuals are constructed correctly. No rounding term enters the tolerance: the identities hold by construction for any data values (D70).

**The "has a value" check**:

- The calibration data of cross-validation are readable before locking, so the "has a value" declarations are checked against the data at locking by `calib_contract.py check` calling `calib_data.py` (this read is recorded as a fit read of the calibration data); on a mismatch the contract is rejected (remedy level: contract), without waiting until T_cv is computed.
- For holdout, the "has a value" declarations of the release are checked at opening (§5.2; only the observables used by the validation contract are checked, unused observables are not read). When a validation observable declared to have a value has no value, this means the release itself is corrupt, and it is handled the same way as a triggered constraint check.

This is a strict upper bound; a correct release does not trigger it. Triggering means the release itself is corrupt or a constraint declaration is wrong. For the check made at holdout opening, that validation is decided as failing, and a failure record is written according to §9.5 (conservative handling, not bypassed through `incomplete`). For the checks made at locking (cross-validation, and N_d,c on the calibration side), the contract is rejected (remedy level: contract) and no failure record is written (D62). It is not a statistical test, does not use any α, and does not count toward power.

#### The statistic

The statistic is T_v = r_vᵀ C_r⁺ r_v. Only when Gaussian, a known and fixed C_r, zero residual mean and the linear approximation apply is χ²_k used as the reference (k = dim N_d^⊥, n_v when there are no deterministic constraints). Otherwise it is calibrated with toys as above.

### 9.3 Cross-validation

The **fold split** is by observable:

- A shape (counts or summary statistics), and a derived quantity together with its components, each belong as a whole to one fold.
- All the observables involved in a general-form relation that depends on the observed component totals (§9.2) are in the same fold.
- The observables spanned by any declared N_d,c are in the same fold.
- For free-ω shapes entering through the count likelihood, the out-of-fold residuals are conditioned on the observed total of the shape (ω has no out-of-fold information, §2.1); the sum of the K bin residuals is 0 by construction and is listed in N_d. Unconditioned absolute-count shapes are not conditioned on the total.
- Calibration observables that are unused according to §5.2 do not enter any fit (the nominal fit and the training fits of the folds), so their selection does not change the out-of-fold residuals of other observables.
- When observables entering through Poisson or binomial blocks with per-bin MC nuisances (γ of BB-lite, ε of the auxiliary binomial) are out-of-fold observables, these nuisances are determined only by their own MC auxiliary measurements and are not profiled with the held-out data.

**The statistic**: T_cv = Σ_f r_fᵀ Ĉ_{r,f}⁺ r_f, where r_f is the out-of-fold residual of fold f and Ĉ_{r,f} is the covariance of the out-of-fold residuals of fold f estimated with toys.

- The full covariance across folds is not used: the overall vector of out-of-fold residuals carries d_θ structural linear constraints across folds (the training fit of each fold shares the data of the other folds; exact in the linear Gaussian case, near zero in the nonlinear case). They are not constraints by construction in the sense of §9.2 and would leave the rank condition and k₀ not well defined.
- The r_f of a single fold has no such linear constraint. But when the out-of-fold observables are nonlinear exact functions of the training-fold observables and the training fit is saturated, r_f may also have exact zero directions, which are caught by the rank condition (c); the cause is the fold split, so the remedy level is the plan.
- Correlations between folds are handled by the toy-calibrated reference distribution (see "Reference distribution" below), so the size of T_cv does not depend on a model of the correlations between folds.
- Ĉ_{r,f}⁺, standardization, the declaration check ((a) decided with the largest sample variance on span{ñ_j} of the toy residuals without rounding applied), the rounding conditions of §2.1, the rank condition, the lower bound on the number of toys and the data-side constraint check are all made on each fold separately according to §9.2.
- N_d is declared on the calibration observables of each fold (§5.2), k₀ = Σ_f dim N_{d,f}^⊥, and k is likewise summed fold by fold. The report notes: the stacked out-of-fold residuals have d_θ constraints across folds, so d_θ of the directions in k are not independent (exactly d_θ in the linear Gaussian case; the free ω of each shape is conditioned on the within-fold total and adds no cross-fold constraint; approximate in the nonlinear case). The decision is calibrated with toys and is not affected.
- s_i on these observables is generated by the model, not declared by the contract (§9.2).

**Identifiability of the training fit of each fold**:

- The fold split is written in the plan. `calib_design.py` decides whether the conditions of P3 hold (§8.3; calling the same implementation of `calib_identify.py`) with the Asimov Fisher of each training fold; if any fold fails, that fold split is rejected (remedy level: plan).
- The fit of each fold on the actual data is additionally decided with the conditions of G5 (`calib_validate.py` calls the same implementation of `calib_identify.py`). On failure, cross-validation is not usable: T_cv is not computed, no validation read is produced, V is `incomplete` (§10.2 rule 0), and the remedy level is the plan (change the fold split); it is not recorded as G1, because the gate semantics do not match. Non-convergence of a fold on the actual data is handled the same way (§7.3).
- The toys for Ĉ_{r,f}, the reference distribution and the power (P7, V stage) apply the same G5 condition, handled by **conditioning**: the observed statistic is obtained under the condition that every fold passes G5 on the actual data, so toys failing G5 are not counted, and a new toy is made with the next unused seed and event interval, until the required number of sets is reached.
  - Order: when a fold does not converge in a toy, that toy is first decided as not converged according to §7.3, and G5 is not decided any more; G5 is decided only after all folds converge.
  - A toy failing G5 is not a non-convergence in the sense of §7.3 and does not count in the ε_max ratio test, because G5 is a statistical threshold, and in a borderline fold split the failure rate of toys can be far higher than 1%.
- When toys failing G5 make up > 20% of attempts, the fold split is close to unidentifiable near the actual data:
  - V (P7 for the P7 toys) is `incomplete` (§10.2 rule 0); the remedy level is the plan, and changing the fold split is recommended.
  - The proportion is summed over all attempts of that ensemble and continues across redos, the same as the summing rule of §7.3, so it cannot be selected by redoing.
  - The summed proportion is decided at the end of every attempt: at completion, and also when the attempt ends in a failing ratio test (§7.3); if it is > 20% there, it has the consequence given in this item (for the power toys, the one of the last sub-item below), and no redo with a new seed block is made. Otherwise redos after a failing ratio test could dilute the proportion, and no stop point based on the number of G5 failures alone would be certain (§14.1 "Completion of an ensemble") (settled by computation, en/compute-19-14-1f.md; to be confirmed by the author).
  - The toys for Ĉ_{r,f} and for the reference distribution are completed, and this proportion decided, before T_cv is computed.
  - When the proportion for the power toys is > 20%, it is the same as "power lower bound not yet computed" in §9.4.

**Shape totals in toys**:

- In the toys for Ĉ_{r,f} and for the reference distribution in cross-validation, free-ω shapes generate counts (multinomial sampling) conditioned on the observed total N_obs of the **actual data** in that fold, the same as for holdout (§2.1); so the reference distribution and the observed statistic are under the same N_obs. These toys read only the within-fold totals and no other data values.
- The within-fold total of a shape is known before locking (it is calibration data); the contract declares N_decl equal to this total according to §2.1, and the checker verifies the equality.
- Shapes with total < 10 (including 0) are rejected at locking (removed, or redefined with other observables; neither merging bins nor changing the fold split changes the total of a shape), so the N_obs = 0 fallback does not occur in cross-validation.
- The power toys of P7 are also conditioned on this known N_obs; P7 and the V stage use the same total.

**Untestable calibration observables** are not used in the contract according to §5.2, and N_d is declared on the remaining observables, the same as for holdout.

Example: (t, p1, p2), t = p1 + p2, all three in the same fold, p1 missing a value. Neither mode uses p1; both declare on (t, p2), k = 2. If σ_p1 = 10⁻⁴σ_p2 and ρ_t = ρ_p2 = 0.1σ_p2, t and p2 are almost fully correlated, and the rounding ratio in the t − p2 direction is 2 × 10⁶:

- In cross-validation mode, and in holdout when the parameter propagation term J Σ_β Jᵀ is negligible in the t − p2 direction, the rounding conditions of §2.1 do not hold on the remaining observables and the contract is rejected; a release with sufficient resolution must be used instead, or one of t and p2 must additionally be left unused, after which k = 1.
- In holdout, when that term dominates, the rounding conditions can hold, the contract is accepted, and k = 2.

**Reference distribution**:

- Obtained with ≥ 500 toys, each toy redoing the whole cross-validation; and Ĉ_{r,f} (for every fold) is estimated with another set of toys, so that the statistic and the reference distribution do not share the same set of toys.
- The fit of fold f in each toy freezes the V̂_f of that fold at convergence on the actual data (§7.3 "Toy data and V̂"), not the V̂ of the nominal fit on the full data.
- When the linearity check (including each fold, §8.5) passes, locally linear toys may be used; otherwise complete toys are used.

**Power**: the power of cross-validation is **always simulated with toys**: generate pseudo-data under each alternative hypothesis, redo the cross-validation, and compute the rejection rate. The analytic formula of §9.4 is used only for holdout.

Results carry the `cv` flag.

### 9.4 Alternative hypotheses and power

#### Declaring alternative hypotheses

Alternative hypotheses must be declared as **simulation settings**, not as parameter shifts. Only two forms are allowed:

- a discrete model that is neither chosen nor absorbed;
- a physical effect declared by the contract but absent from the model (the deviation produced by turning that effect on in the simulation).

When g4sim is used, both forms are expressed as differences of g4sim specifications and cited by their identity (§5.1): for example another physics list or EM option (run card), full optical tracking replacing the efficiency map, turning on an additional yield variation (`response-pipeline/1`). When declaring with a physics list, the confirmation record "actually use different models" required by the `models` row of §5.2 must be attached; when the two lists use the same model in the relevant range, its λ_a is necessarily zero, and the checker rejects it.

Deviations expressed as shifts of θ, ν, η, φ (for example ν_k = 2) are always rejected by the checker. Such deviations lie within the null model and are absorbed by the fit; for example with ν_k = 2, λ_a ≤ 4, and the upper limit of power for n_v = 1 is only 0.516.

#### Noncentrality parameter and paths

```latex
\mathbb{E}[r_v \mid a] = \Delta m_{v,a} - J_v A\, \Delta m_{c,a},
\qquad
\lambda_a = \mathbb{E}[r_v \mid a]^{T} C_{r_v}^{+}\, \mathbb{E}[r_v \mid a]
```

The power for each a is required to be ≥ 0.8. The A, C_{r_v} and reference distribution here must agree with those actually adopted in §9.2:

- **Analytic path** (when §9.2 allows χ² as the reference): C_{r_v}⁺ and k = dim N_d^⊥ are defined according to §9.2 (k = n_v when there are no deterministic constraints).
  - The null space **provides no power**: by the definition of N_d, alternative hypotheses declared as simulation settings also satisfy these constraints by construction, so the component of E[r_v|a] on N_d is zero; declaration check (b) of §9.2 confirms this at P7, and if it is not zero, it is a contract error. λ_a = E[r_v|a]ᵀ C_{r_v}⁺ E[r_v|a] is the entire source of power.
  - At α = 0.05, the required λ is 7.85 (k = 1), 9.64 (k = 2), 10.91 (k = 3), 12.83 (k = 5), 16.25 (k = 10) (exact values 7.849, 9.635, 10.903, 12.828, 16.241, rounded up), looked up by k, not by n_v; C must not be made invertible by adding a small diagonal term.
- **Mixed or non-Gaussian likelihoods**: E[r_v|a] is computed with the implicit-function response of §6.7 (not with the Gaussian A).
- **Toy path** (when §9.2 requires T_v to be calibrated with toys; this holds for both P7 and the V stage, so both use the same decision rule):
  - Power is always simulated with toys: generate pseudo-data under each alternative hypothesis, redo the fit and the validation, and compute the rejection rate with the calibrated critical value (the same as for the cross-validation of §9.3).
  - The true value of toys under an alternative hypothesis is m_nom(θ̂) + s_a δ̂_a, with s_a scaled by the one-sided lower bound of the cross product below (§6.6).
  - The confidence level is allocated by Bonferroni: with m alternative hypotheses and simultaneous confidence 1 − α_P (default α_P = 0.05), each hypothesis receives 1 − α_P/m, split into two one-sided bounds at 1 − α_P/(2m) each, one for the lower bound of the cross product and one for the Clopper–Pearson lower bound of the toy rejection rate (D59). So the lower bound of the toy path, like that of the analytic path, includes the MC uncertainty.
- **When the path is decided**: the path (analytic or toy) is decided at P7 from θ_ref and written into the plan; when the conditions at θ̂ change and another path is needed, P7 is redone with the path at θ̂ before opening, so P7 and the V stage still use the same decision rule.

#### Correcting the MC bias

Δm_a is estimated from finite simulation, and λ̂_a is on average too high by tr(C_{r_v}⁺ V_Δ), where V_Δ is the MC covariance of the estimate of E[r_v|a] (from Δm̂_a). The decision uses an unbiased estimate, one of the two:

- Estimate E[r_v|a] separately with two independent sets of MC, written e⁽¹⁾, e⁽²⁾, and take the cross product λ̂_a = e⁽¹⁾ᵀ C_{r_v}⁺ e⁽²⁾. Δm is the difference between the alternative model and the nominal model, and the predictions of both must be independent between the two sets; when g4sim is used, according to §6.6.
- Use a single-set estimate minus tr(C_{r_v}⁺ V_Δ).

Notes:

- An uncorrected single-set MC quadratic form is too high on average; individual realizations are not necessarily too high.
- The unbiasedness conclusion above presupposes that C_r and the response operator are fixed, or independent of the two sets of MC; if they are estimated from the same MC, cross-fitting or joint toy calibration is required.
- The cross product can be negative; its absolute value must not be taken while still claiming unbiasedness.
- e⁽¹⁾, e⁽²⁾ are produced by simulations that satisfy the constraints by construction (predictions without release rounding applied); their components on N_d are only floating-point error, are eliminated by C_{r_v}⁺, and do not enter λ̂_a; if either set exceeds the tolerance √τ_num of declaration check (b) on some constraint, it is decided as a contract error.

#### Uncertainty of power and the decision

An unbiased point estimate is not a guarantee of "sufficient power". P7 and V use a one-sided confidence lower bound declared in advance (by default simultaneous confidence 1 − α_P = 95% over the family of m alternative hypotheses, by Bonferroni: 1 − α_P/m for each hypothesis, split on the toy path as above; D59), and require the power lower bound of every alternative hypothesis to be ≥ 0.8.

- For the cross product, the lower bound is estimated with independent MC repetitions/a valid bootstrap (construction per the §8.7 row; level 1 − α_P/m on the analytic path, 1 − α_P/(2m) on the toy path); for the toy rejection rate the decision uses the one-sided Clopper–Pearson lower bound at 1 − α_P/(2m). If C_r or the response operator is also estimated, its uncertainty is included.
- **A lower bound < 0.8 is "insufficient power"**: P7 or V fails, and the grade is `calibrated-unvalidated` according to §10.2 rule 3. Insufficient precision only makes the lower bound lower, so no separate status is set.
- With several alternative hypotheses, as soon as the lower bound of any alternative hypothesis has been computed and is < 0.8, the power is decided to be insufficient, without waiting for the other alternative hypotheses (the same as "T_v failure takes precedence" in the V stage; the same rule for P7 and the V stage).
- When the MC noise is large, the scaling of s_a and the Bonferroni allocation make the lower bound quite conservative, and a true power of 0.9 may also be decided to be insufficient; this is the conservative direction and is explicitly accepted.
- Only when the lower bound **cannot be computed** (for example there is no second independent set of MC and the V_Δ needed for the single-set estimate cannot be estimated either; or the toys were not run) is that gate recorded as `incomplete` (§14 exit code 3), and the result is not assigned a grade until it is completed, unless the outcome is already determined (§10.2 rule 0, general principle). `incomplete` is neither a pass nor a grade.

**The V stage needs the power lower bound only when T_v is decided as passing**:

- When T_v has been decided as failing (including a triggered data-side constraint check), V is failed (§10.2 rule 3b); the power lower bound does not need to be computed, and if it cannot be computed this does not make V `incomplete`; the provisional failure record written at opening according to §9.5 is changed to `final`.
- When T_v has not yet been decided, the record stays `pending` (§9.5).
- When there is no testable direction (k = 0, §9.5), no power lower bound is needed either.
- **When T_v (T_cv in cross-validation) is decided as passing and the power lower bound of the V stage has not yet been computed** (it cannot be computed, or the ratio test of the power toys of §7.3 keeps failing), V is `incomplete`, and the record is already `withdrawn` according to §9.5 (abandoning that κ can no longer be declared).

**Power abandonment**: completing the lower bound often requires changing the plan (a new κ). So the analyst may declare power abandonment for that κ with `calib_validate.py abandon-power`:

- V is recorded as insufficient power (§10.2 rule 3b, `calibrated-unvalidated`).
- The record stays `withdrawn` (T_v has passed; there is no evidence of disagreement).
- The declaration cannot be withdrawn, and no further power records are accepted for that κ.

**When P7 is `incomplete`**, `calib_data.py` does not open the validation data for that κ (when the outcome is already determined, the data are likewise not opened, and the result is what the lookup gives, §10.2 rule 0): completing P7 often requires changing the plan, with κ changing accordingly; if the data had been opened, the new κ could only reach `calibrated-unvalidated` according to §9.5.

#### The two times

- P7, in the design stage, estimates the power from the expected validation errors that the model generates at θ_ref (the contract provides only metadata such as the exposure, and N_decl, N_decl,s, §2.1).
- At validation, it is recomputed with the actual C_{r_v} (free-ω count shapes with the observed N_obs as the total, event samples with N_tot,s, the same procedure, §2.1).

### 9.5 Results

#### Validation data can be used only once

Once validation data have been read by one validation configuration, they can no longer be used by another configuration to upgrade a result. This rule is keyed on the **data**, not on the time of the contract.

**Definitions**:

- **Validation configuration** κ = (contract hash, plan hash, engine version). Before any validation statistic is computed, `calib_validate.py` takes the hash of the plan and writes it to the record; the plan itself is still not locked, but the validation statistic is permanently bound to the plan hash at that time.
- **Validation read event**: when any validation statistic (T_v of holdout, T_cv of cross-validation, power on the actual data) reads the observable values of some data release D, `calib_data.py` records an entry (hash of D, κ, `validation`, sequence number) (for the sequence number, see "Failure records" below). The validation data of holdout are recorded at opening (when the commitment hash is verified); the calibration data used by cross-validation are recorded when T_cv is first computed. In cross-validation the V-stage power toys read only within-fold totals (fit reads) and run only after T_cv has been computed, so the first validation read is always the first computation of T_cv (D65).
- **Fit read event**: when any script provides the observable values of D to a fit, a design, the A0 preflight or exploration (`calib_data.py` is the only provider), an entry (hash of D, read channel, κ (if any), `fit`, sequence number) is recorded, sharing the same sequence-number series with validation reads. A fit read is not a validation read, but it means the analyst may have seen these values before locking (the calibration data of §5.1 are readable before locking).
- The **read channel** is the contract through which the read happens: a locked contract is represented by its hash; A0 and exploration before locking have no contract hash yet, and are represented by the contract series to which the contract draft belongs and the draft sequence number (`calib_data.py` registers the draft the first time it provides data for it, is the only registrar, and is the script through which `calib_contract.py preflight` obtains data). So every read has an attribution, and there is no read that is "not recorded". The read channel serves review and reproduction; the holdout decision does not look at it.

**Decision**: a file hash is an integrity identifier and cannot by itself represent data independence.

- Every release D must carry the raw data lineage (event/sample/measurement ids, selection ranges, derivation relations); validation read events are recorded along the lineage down to the **raw data units**. For each raw unit, its **first validation read** and all read events (including the read channel) are recorded.
- If, for any raw unit read by the validation statistic of a result, the κ of its first validation read is not equal to the κ of that result, the evidence grade is at most `calibrated-unvalidated` (§10.2 rule 3d).
- **Holdout has one more rule**: before the κ of this result opens the holdout, any read on the validation units (including fit reads) is a non-exempt read and makes the grade at most `calibrated-unvalidated` (rule 3d). Validation reads are never exempt. (Exemption conditions (1)(2), the rules of the frozen version under which a fit read on a holdout validation unit made through a release that this result's contract declares as calibration data could be exempt, and the reuse input `fit-pending` are unreachable under the current rules, because the calibration release and the validation release of a holdout share no raw units; Appendix C keeps `fit-pending` only for compatibility with old records.)
- The validation data of cross-validation are by nature calibration data already read, so only the first validation read is looked at (additionally limited by the failure-record rules below). Because the comparison is with the "first" one, a later read of the same data by another κ does not retroactively downgrade a result already legitimately obtained.
- Reordering, rebinning, changing metadata, changing format, copying a release or reopening a contract series cannot reset the record, because the record is attached to the raw units.

**Holdout must not share events**: at locking and before the holdout is opened, `calib_data.py` compares, by lineage, the calibration release and the validation release of this result's contract. When the two share raw units (whether declared or not), it is a contract error (exit code 2, remedy level: contract; switch to cross-validation, or switch to releases that do not share events), and the validation data are not opened. So in holdout no validation unit can be read through the calibration release.

The approach "declare the sharing and include the correlation through V_cv" is not adopted, because by the inclusion rule these validation observables can be computed exactly from the calibration release before locking (example: the efficiency of two merged periods is determined by the component efficiencies and the component totals), and the analyst could lock only contracts that would pass; V_cv only corrects the correlations of a test fixed in advance and cannot handle such a data-dependent choice.

**Rationale**: the evidential force of holdout comes from "the validation data were not seen before the rules were locked" (principle 2); a unit that has been read in some other way has been seen, and the model, V_model and the alternative hypotheses may all have been adjusted to it. Without "holdout has one more rule", after κ1 calibrates with X, holds out Y and fails, κ2 could calibrate with Y instead, hold out X and obtain `validated-in-scope` (X has no validation read, and κ2 is not cross-validation, so neither `validation` of 3d nor 3f triggers), which amounts to completing "changing the validation method after failing" by swapping roles. With this rule, the fit read of X by κ1 caps κ2: the decision looks at the validation units of this result κ2, and the fact that X is calibration data for κ1 does not change the outcome.

**When the lineage cannot be confirmed**: that validation is recorded as `incomplete` (§10.2 rule 0; except when the outcome is already determined), and `calib_data.py` **does not open** the validation data (holdout) and does not compute T_cv (cross-validation). The lineage is a precondition of opening, the same as when P7 is `incomplete` (§9.4). So when the lineage is not confirmed there is no validation read and no provisional failure record is written, and the record can always be attached to raw units; after the lineage is completed (for example by a new release with lineage), opening follows the general rules.

An exact recomputation with the same κ is reproducible when the records are in the same state (§10.1). Recomputation with the same κ (reproducibility check) is not restricted.

This covers all upgrade paths: changing the contract, changing the plan, engine fixes (§4.2; the engine version enters κ), switching to cross-validation, merging opened validation data into the calibration data and then doing cross-validation, or using calibration data already read as holdout validation data (role swap). To reach `validated-in-scope`, raw units that have never been read by any validation statistic are needed; when validating with holdout, these units also must not have non-exempt reads before opening (under the current rules, that is, any read).

#### No change of mode after a validation failure: failure records

There are only two kinds of **validation failure**: T_v (or T_cv) decided as failing (exceeding the critical value), or a triggered data-side constraint check (including "has a value" disagreeing with the release declaration at opening, §9.2).

- When T_v is decided as passing but the power is insufficient or power abandonment is declared, V fails, but the record is `withdrawn` as below.
- When T_v (T_cv) is decided as failing, V is failed, and the power lower bound is no longer needed (§9.4).
- Data whose lineage is not confirmed are not opened (see above).

On a validation failure, there is a `final` **failure record** on the raw units of the **calibration data** of that result: all raw units of the calibration releases of the contract, recorded along the lineage including units reached only through unused observables, as for validation reads (D60). It is attached to the raw units, not to the contract series, so it cannot be bypassed by opening a new series; it is written as `pending` already at opening (see below). If the decision is not completed after opening, the record stays at `pending`; on abandonment it likewise becomes `final`.

Failure records carry a time: the time is the event sequence number of `calib_data.py` (the single writer); validation read events and failure records share the same increasing series, so there is no clock skew between them.

**The failure record is written in a provisional state already at opening**: when the holdout is opened (for cross-validation, when T_cv is first computed), `calib_data.py`, at the same sequence number at which it records the validation read event of that κ, writes a **provisional failure record** (unit, κ, sequence number, `pending`), attached to the raw units of the calibration data of that result. Its state changes only according to the decision records of `calib_validate.py` (including abandonment):

- The decision for the same κ is completed and passes (T_v or T_cv, compared with its critical value, is within the critical value—when toy calibration is needed, the calibrated critical value—and the data-side constraint check is not triggered) → `withdrawn`;
- The decision fails (including a triggered data-side constraint check; the power lower bound is not needed, §9.4) → `final`;
- **k = 0 determined before opening** (that is, k₀ = 0: no validation observables after untestable observables are excluded, or all remaining observables are subject to constraints by construction and N_d^⊥ is empty): P7 and V are both recorded as `no-testable-direction` (not `incomplete`, no power lower bound needed, §9.4); the validation data are not opened, so no failure record is written (the input other κ see is `none`); the grade is `calibrated-unvalidated` according to `no-testable-direction`.
- The decision is completed and there is no testable direction (k = 0, for example all validation directions come from shapes with N_obs = 0, §2.1) → `withdrawn`: there is no failing decision. The state of V is recorded as `no-testable-direction`: it is not a pass, no power lower bound is needed (there is no direction for which power can be computed, §9.4), and it is not `incomplete`; the grade is `calibrated-unvalidated` according to `no-testable-direction`. When k = 0 and the data-side constraint check is triggered, it is `final` according to "the decision fails" above (failure takes precedence);
- The analyst abandons that κ (does not complete the decision any more) → `final`.

**Abandonment**:

- It is declared for that κ by the analyst with `calib_validate.py abandon`; `calib_validate.py` writes a decision record (decision outcome "abandoned"), and `calib_data.py` changes the record to `final` according to it.
- Abandonment cannot be withdrawn and has no deadline (when it is not declared, the record stays at `pending`).
- Abandonment can be declared only for a κ whose record is still `pending` (not yet decided); when a decision record already exists (pass or fail), `calib_validate.py` rejects the abandonment declaration and the record keeps its state (`withdrawn` does not become `final`, so a κ whose decision passed cannot downgrade other results afterwards).
- Abandonment is the terminal state of that κ: afterwards `calib_validate.py` accepts no decision record for that κ (recomputation with the same κ only reproduces the records from before abandonment), the record stays `final`, and the V of that κ's own result is recorded as failed (§10.2 rule 3). So "decision passes → `withdrawn`" applies only to a κ not yet abandoned.

Records only change state; they are not deleted. The sequence number of a failure record is always the **sequence number of opening**, not the time of the decision, so any validation configuration that starts only after the opening comes after it; if the decision is not completed after opening, the record stays at `pending` and does not disappear. This blocks the whole class of bypasses "see the result after opening, do not complete the decision, switch to cross-validation". Events of different κ do not share a sequence number (single writer); if in an implementation merged writes give the two the same sequence number, the failure record is treated as **earlier than** the validation read (conservative direction).

#### Effect of other κ's failure records on cross-validation

A later result whose validation mode is `cross-validation`, whose calibration data overlap a raw unit, where that unit has a failure record of **another κ** that is **earlier than** the first validation read of this result's validation configuration κ (the first computation of T_cv):

- When there is a `final` record, it can be upgraded only with `holdout` on raw units that qualify for holdout (no validation read by any other κ, and no non-exempt read before this κ opens them; under the current rules, no read at all before opening; D74), and must not switch to cross-validation (§10.2 rule 3f); the same holds when there are also `pending` ones (`final` already caps, and `pending` no longer changes the outcome).
- When there are only `pending` records: compute this result's outcome (effective grade, use) once with the records resolved as `final` and once as `withdrawn` (§10.2 rule 0). If the two differ (typically: rule 2 does not hold, no other condition caps, and no central upstream or grade-limiting flag caps), this result is `incomplete` until all such records are `final` or `withdrawn`, and is then re-judged; while the other κ neither decides nor abandons, the record stays `pending` and this result stays `incomplete`. If the two are the same (for example V fails, the validation data are otherwise reused, or an upstream already caps), that common outcome is given at once. So the outcome does not depend on when the other κ decides, and a recomputation with the same κ is reproducible once the records are resolved.
- `withdrawn` records do not affect the grade.

**Trade-off**: when the resolution does not change the outcome, `pending` is not stricter than `final`; when the resolution would change the outcome, the result waits for resolution (`incomplete`, no use), and in that case it is stricter than `final`. This is the trade-off made in exchange for "the grade does not vary with the time of decision or opening": if the grade under `final` were given before resolution, the same κ would get different outcomes depending on when someone else decided.

**Scope**: this rule applies only to cross-validation.

- The eligibility of mode `holdout` looks only at reads on the validation units. Failure records of other κ can affect holdout only through exemption condition (2) of the frozen version (the unit carries no `final` failure record of another κ earlier than the opening), and (2) is unreachable under the current rules ("Decision" in this section), so they do not change the effective grade and use of holdout; however, with a `pending` input, the result still does not record its own grade according to §10.1.
- Mode `none` has no validation read, "first validation read" is not defined, and the grade is by rules 2, 3 already ≤ `calibrated-unvalidated`, so there is no upgrade path to block.
- A cross-validation result whose calibration data are not real data (§10.2 rule 2) already has grade `projection`, and the `pending` rule does not apply to it either.

So this rule does not change the outcomes of mode `none`, of `holdout`, or of those for which rule 2 holds, and results already legitimately obtained do not become `incomplete` because someone else opens validation data.

The rules above do not apply to the records of this result's own κ (its decision is the V of this result). Otherwise, after a validation failure, switching to cross-validation on calibration data that have never had a validation read would upgrade, which amounts to choosing the validation method. The time condition guarantees that results already legitimately obtained are not downgraded by someone else's later failure, and recomputation with the same κ remains reproducible.

**Design trade-off**: a cross-validation whose first validation read is earlier than the failure record (that is, earlier than the failed κ opening its validation data), for example one already started before the holdout was opened, is not subject to this limit; the time condition cannot distinguish whether it is choosing the validation method. To make such cases reviewable, `calib_data.py` records all validation configurations that have made validation reads on the same batch of calibration raw units; when any configuration fails, the results of the other configurations list this failure record in `calibration-result` as well (report only; the grade is not changed).

#### Result table

| Case | Evidence grade |
| --- | --- |
| Contract error before opening (a failed declaration check or recomputation at the fit point, a holdout whose calibration and validation releases share raw units, or another rejection rule of §5.2; D72; the declaration check and the recomputation at the fit point are always made after the fit, §2.1, so this row is decided before the lookup) | No result; the contract is rejected (exit code 2); the validation data are not opened and there is no validation read |
| Outcome already determined (the general principle of §10.2 rule 0: the table lookup gives the same result under every possible outcome of the inputs not yet decided; for example calibration data from simulation, P7 deciding that the power is insufficient, k₀ = 0 determined before opening, carrying `closure-not-tested` itself) | The grade from the table lookup (`failed`, `projection` or `calibrated-unvalidated`); not opened (in cross-validation T_cv is not computed), V is `not-applicable`, the other opening preconditions do not need to be completed, and there is no validation read and no record |
| A mandatory gate is `incomplete`, and the outcome is not already determined (D72) | `incomplete` (not a grade, §10.2 rule 0) until completed; the validation data are not opened |
| Data lineage cannot be confirmed | `incomplete` (not a grade, §10.2 rule 0); the validation data are not opened |
| P7 is `incomplete` (§8.2, §7.3) | `incomplete` (not a grade, §10.2 rule 0) until completed; the validation data are not opened (rule in §9.2) |
| k₀ > 0, T_v is calibrated with toys (always in cross-validation), and the replicas of the toys for Ĉ_r or the reference distribution could not be generated according to §6.6 (the reference distribution cannot be computed) | `incomplete` (not a grade, §10.2 rule 0) until generated; the validation data are not opened |
| Before opening (in cross-validation, before T_cv is computed), the ratio test of the reference toys of T_v or T_cv, or of Ĉ_r or Ĉ_{r,f}, fails (§7.3) | `incomplete` (not a grade, §10.2 rule 0); the validation data are not opened, and there is no validation read and no record; within the same κ it may be redone as a summed redo with the next seed block according to §7.3, unless, in cross-validation, the summed G5 proportion of that ensemble is > 20% at the end of the attempt (§9.3, rule settled by computation, en/compute-19-14-1f.md; to be confirmed by the author): then the following row applies and no redo is made; when the summed test still fails, it stays `incomplete` until a new κ (for the case after opening, see the row after "Test fails") |
| In cross-validation, the training fit of some fold on the actual calibration data does not converge (§7.3) or fails G5, or the proportion of toys failing G5 in the toys for Ĉ_{r,f}/the reference distribution is > 20% (§9.3) | `incomplete` (not a grade, §10.2 rule 0); T_cv is not computed, and there is no validation read and no failure record; the remedy level is the plan (change the fold split) |
| Test fails: T_v (T_cv) exceeds its (calibrated) critical value, or the data-side constraint check or the "has a value" check is triggered at opening (whether or not the power lower bound can be computed) | `calibrated-unvalidated`, with per-item residual diagnostics |
| Neither the data-side constraint check nor "has a value" is triggered, and after opening the regeneration of shape toys or the bootstrap conditioned on the observed totals fails (§2.1), or the ratio test of the reference toys or Ĉ_r generated after opening fails (§7.3) | `incomplete` (numerical failure, §10.2 rule 0), redone with the next seed block according to §7.3, `final` is not written; the failure record stays `pending` and may be abandoned according to this section. This row is placed after "Test fails" because when the data-side check is triggered V has already been decided as failing and the record is `final`, and no toys are needed |
| No testable direction (k = 0; the data-side constraint check is not triggered) | `calibrated-unvalidated` |
| Test passes, but the power lower bound cannot be computed | `incomplete` (not a grade, §10.2 rule 0) until completed; after power abandonment is declared, `calibrated-unvalidated` (§9.4) |
| Test passes, but the power lower bound < 0.8 | `calibrated-unvalidated` |
| Test passes, and the simultaneous confidence lower bound of the power of all alternative hypotheses is ≥ 0.8 (§9.4) | `validated-in-scope` |

The rows are **mutually exclusive in order**: take the first row that holds.

- The opening preconditions include: the declaration check, the recomputation at the fit point, k₀ > 0, lineage, P7 not `incomplete`, the calibration data being real data, no mandatory gate failed, no mandatory gate `incomplete`, P7 deciding that the power is sufficient, the calibration release and the validation release of the holdout sharing no raw units, and, when k₀ > 0, the toy replicas and the ratio test before opening (full list in §9.2 "Preconditions for opening the validation data"). If any one is missing there is no test; the cases where the outcome is already determined are listed at the head of the table, after contract errors, with V `not-applicable`.
- The "toy replicas" row is restricted to k₀ > 0, so when k₀ = 0 and there are no toys it is still `no-testable-direction`, consistent with §10.2 rule 0.
- When the test fails, power is not needed; when k = 0 there is no test, and power is not needed either.

#### Untestable observables

**Untestable observables** enter neither T_v nor the power computation. They include:

- missing data values;
- only values read off by eye;
- statistical errors available only in a version computed from the observed values, which therefore cannot be recomputed (§2.1).

These are all decided from the per-observable "has a value" declarations of the release and the reasons for being untestable (§5.2, submitted together with the commitment hash, without disclosing the values), and are determined before the contract is locked, so they are excluded in the contract according to §5.2 and do not enter the validation contract. When at opening a validation observable declared to have a value is found to have no value, it is treated as a corrupt release by the data-side check of §9.2.

Overly coarse rounding does not belong to this class: it makes the contract containing that observable rejected (§2.1); the contract may re-declare without using the observable causing it, and list it according to §5.2.

**Reporting**: the result reports the observables used for validation and k, k₀ (k₀ = dim N_d^⊥; in cross-validation k₀ = Σ_f dim N_{d,f}^⊥, §9.3; before the fallback of §2.1 that removes directions after opening is deducted), and the unused observables listed according to §5.2 with their reasons. These are reports only: the testable proportion is not a grade condition, because the contract already decides the use of each observable, and with a threshold on the proportion, the denominator of the proportion repeatedly turns out to be an exploitable loophole.

So the grade does not prevent "validating only part of the observables"; this is borne by two things: the result explicitly reports k and the unused observables, and the power requirement holds only on the k directions actually validated (§9.4), and the validation claim also covers only these directions.

**Explicitly accepted trade-offs**:

- The calibration data of cross-validation are readable before locking, so the unused observables can be chosen from data already read (choosing by outcome), whereas the choice in holdout is blind. Cross-validation results therefore carry the `cv` flag and list the unused observables and their reasons, from which the reader judges. Under such data-dependent choice the size α of T_cv is no longer guaranteed, so `validated-in-scope` in `cv` mode has a weaker meaning: it means "the listed observables are compatible with the model under T_cv", not a frequentist guarantee before the choice.
- The fold split is written in the plan, which is not locked, and may also be chosen after reading the calibration data, or after seeing the convergence and G5 of the folds; this is the same kind of data-dependent choice, and the `cv` flag covers it.
- Validation reads are recorded per whole release and recorded along the lineage to all of its raw units, so units that are reached only through unused observables and were previously read by another κ may also cap this result according to §10.2 rule 3; this is the conservative direction.

The `observed` uncertainty components unsealed together with the observed values at opening are part of the validation read, but do not enter any computation (§2.1). When there is no testable direction (k = 0), the evidence grade stops at `calibrated-unvalidated`.

---

## 10. Results, dependencies and propagation

### 10.1 `calibration-result`

The product kind name is `calibration-result`, and the schema file name is `calibration_result.json`. The content includes:

- the hashes of the contract, data and plan; all contract versions;
- β̂; the exported nuisances and coefficients (§10.4); profile curves;
- the result of every gate and of validation, the power, the evidence grade and flags; the evidence grade records the own grade and the effective grade separately (§10.2);
- results with `pending` inputs (`fit-pending` is unreachable under the current rules, §9.5; old records are handled the same way):
  - The own grade is not recorded (it is not defined, I25 of Appendix C).
  - Every record waited for (raw unit, κ, sequence number) is recorded, together with the (effective grade, use) under each of the two resolutions; the effective grade and use of the result are the common value of the two, and when they differ it is `incomplete`.
  - After the records are resolved, re-judging with the same κ produces a new `calibration-result` (with an own grade, and a different result hash); the old one is kept. "An exact recomputation with the same κ is reproducible" refers to **the same record state** (§9.5).
  - This is a deliberate conservative trade-off: whenever there is a `pending` input, the own grade is not recorded, even when the own grades of the two resolutions are the same (for example, a holdout result with `pending` failure records of other κ on its calibration units); the effective grade and use are not affected (I20, I22), and the cost is one more re-judgment after resolution. Not recording it only when the resolution would change the own grade needs another decision rule, which this workflow does not adopt;
- the envelope of enumerated models; Δθ̂ and central-value differences of shift-mode φ;
- upstream result hashes and nuisance versions; scope;
- the uncertainty-source declarations of every data release used and their submitters (the applicability preconditions of §2.1);
- failure records of concurrent validation configurations (§9.5, report only; the grade is not changed): those already existing when the result is produced are written into the result itself; those appearing only after the result hash are written by `calib_data.py` into annotation records keyed by the result hash, which do not change the result hash, and citers obtain them together through `calib_deps.py`;
- when g4sim is used: the five identities of each model (the masked hashes of §5.1), and the `geometry_id`, `request_id`, `run_id` of the evaluations used at θ̂;
- the dependency inputs needed by the conflict rules of §10.4: the raw-unit lineage of the data used, the MC samples used (`run_id` and global event interval), external auxiliary measurements and shared priors, model-discrepancy components, and the global keys of efficiency-map bases. When these inputs are missing, a citer cannot multiply it independently with other packages (§10.4 rule 4).

### 10.2 Evidence grades, flags and uses

The **grade assignment rules** are decided in order, taking the first that holds; the order is rule 1, 0, 2, 3, 4. Rules 0–4, together with the inheritance, flags, effective grade and use matching below, are written as the decision table of Appendix C; when the two disagree, Appendix C prevails. `calib_use.py` implements it according to the decision table, and the tests check the invariants listed in Appendix C exhaustively over the test scope defined there, including the "outcome already determined" lookup below (D63).

**Rule 1**: any mandatory gate (§8.1: the gates of stages B–E except P7) fails in the final version → `failed`. This rule does not apply to P7 and validation V.

- After a mandatory gate fails, the subsequent gates that are no longer executed according to §4.2, P7 and V are recorded as `not-applicable`, not `incomplete`; so an already failed result does not need to open the validation data in order to obtain `failed`.

**Rule 0** (decided after rule 1): no mandatory gate has failed, and any mandatory gate, P7 or V is `incomplete` in the final version → the result status is `incomplete` (§14 exit code 3). The `incomplete` cases include:

- not executed, inputs missing;
- T_v or T_cv decided as passing while the power lower bound has not yet been computed, and power abandonment has not yet been declared (§9.4);
- data lineage cannot be confirmed (in this case the validation data are not opened, §9.5);
- k₀ > 0 and T_v calibrated with toys, while the replicas of the toys for Ĉ_r or the reference distribution could not be generated (in this case the validation data are not opened, §6.6, §9.5);
- after opening, the regeneration of shape toys or the bootstrap conditioned on the observed totals fails (§2.1);
- the ratio test of the reference toys or Ĉ_r fails (§7.3); these cases after opening apply only when neither the data-side constraint check nor "has a value" is triggered; when triggered, V fails and the record is `final`;
- in cross-validation, some fold does not converge or fails G5 on the actual data, or the proportion of toys failing G5 among the toys for Ĉ_{r,f} or the reference distribution is > 20% (§7.3, §9.3); for the power toys, a proportion > 20% counts as "power lower bound not yet computed", and P7 toys make P7 `incomplete` (D61);
- when the interval construction of §7.5 is `incomplete` (summed ratio test of §7.3), G3 is recorded as `incomplete`.

Cases that are not `incomplete`:

- When T_v fails, V is failed; when k = 0, V is `no-testable-direction`; when k = 0 is determined before opening, P7 and V are likewise `no-testable-direction` (§9.4, §9.5).
- Mandatory gates recorded as `not-applicable` according to the applicability conditions of §8.1 do not count.
- The case in which G8 makes no decision according to §8.4 and `closure-not-tested` is explicitly added is not `incomplete`: it is the prescribed downgrade path and is handled by rule 3.

`incomplete` **is not a grade**: it does not enter the grade order and the use matrix below, cannot be cited as an upstream (citing it is rejected), and is re-judged after completion.

**When there are `pending` failure records of other κ** (§9.5: the failure-record input of cross-validation is `pending`; the holdout reuse input `fit-pending` is unreachable under the current rules, §9.5): rules 1–4 are used only for resolved inputs, so such an input has no single own grade.

1. Resolve the records as `final` and as `withdrawn` respectively, and decide the own grade for each according to rules 1–4;
2. then pass each through the capping of "Effective grade" and the use matching below;
3. when the (effective grade, use) of the two differ, the result status is `incomplete` (§14 exit code 3); when they are the same, the result is that common result.

This decision is made only at the layer of the effective grade (the first step of Appendix C.3); rules 1–4 and Appendix C.2 never see `pending` inputs. So `pending` makes the result `incomplete` only when the resolution would change the effective grade or the use.

**Not opened when the outcome is already determined** (general principle):

- Before the validation data are opened (in cross-validation, before T_cv is computed), `calib_use.py` evaluates Appendix C, C.2 and then C.3 (so capped upstreams count), for each combination of the possible outcomes of the inputs not yet decided, and compares the resulting (effective grade, use). The inputs not yet decided and their possible outcomes are: each `incomplete` mandatory gate, passed or failed; P7, passed or failed; V, "passed, power sufficient and k > 0" or "failed" (D63).
- `incomplete` of the opening preconditions of §9.2 (lineage, toy replicas, the ratio test before opening) is part of V not yet decided: it is not a separate input and adds no combination.
- Before T_cv is computed, every failure record of another κ that already exists counts as earlier than the first validation read; at the computation of T_cv the failure-record input is evaluated again at the sequence number of that read (D69).
- When other κ have `pending` records, the two resolutions are also each looked up once (the same as the first step of C.3).
- When all combinations give the same (effective grade, use), the outcome is **already determined**:
  - not opened (in cross-validation T_cv is not computed, and no validation read or record is produced);
  - V is recorded as `not-applicable` and input as v_pass = False;
  - `incomplete` of P7 and of the opening preconditions does not count under this rule;
  - the result is what the lookup gives.
- A failed mandatory gate (rule 1), calibration data from simulation (rule 2), P7 deciding that the power is insufficient (3b), k₀ = 0 determined before opening (3b), carrying `closure-not-tested` itself (3c), validation data from simulation (3e) and an already capped upstream are all covered by this principle and need not be enumerated.
- An `incomplete` mandatory gate may turn out to be a failure, so it usually makes the lookup results differ (`failed` versus others), and then the outcome is not yet determined. But the lookup already covers each of its possible outcomes (including failure), so if the lookup is still the same under each possible outcome (for example the effective grade of a central upstream is `failed`, and by the effective grade of this section and Appendix C.3 this result is `failed` under any input), the outcome is likewise already determined, the lookup result prevails, and the `incomplete` of the mandatory gate does not count under this rule either.
- This principle applies uniformly to all inputs not yet decided, without exception.
- When they differ, the outcome is not yet determined, and the opening preconditions and this rule apply as usual.

**Rule 2**: the **calibration data** do not use real data (design studies, Asimov; the status of any calibration data release is "from simulation", §5.1), or the validation mode is `none` and intended_use declares only design uses → `projection`. The case of validation data from simulation is not under this rule and is handled by rule 3.

**Rule 3**: any of the following holds → `calibrated-unvalidated` (numbering the same as in Appendix C.2):

- 3a: the validation mode is `none`;
- 3b: P7 fails in the final version; or validation fails, or the power is insufficient, or there is no testable direction (k = 0, §9.5);
- 3c: carries the `closure-not-tested` flag;
- 3d: for some raw data unit read by the validation, the first validation read event belongs to another validation configuration; or the mode of this version is `holdout` and some validation unit has a non-exempt read before the κ of this result opens it (including fit reads; §9.5 "Validation data can be used only once": under the current rules reads on holdout validation units are never exempt; decided by raw units, not by data releases);
- 3e: the status of any data release read by the validation is "from simulation" (§5.1): when real data are used for calibration but simulation output for validation, the validation has no evidential force;
- 3f: the validation mode of this version is `cross-validation`, and the calibration data overlap some raw unit that has a `final` failure record of another κ, where that record is earlier than the first validation read of this result's κ (§9.5 "No change of mode after a validation failure").

**Rule 4**: otherwise → `validated-in-scope`.

**Grade order**:

```
failed  <  projection  <  calibrated-unvalidated  <  validated-in-scope
```

**Grade inheritance follows the role of the upstream**. The role is **derived by the checker from the usage** (`calib_deps.py`); self-declaration is not accepted; if a role is written in the contract, it must be the same as the derived result, otherwise it is rejected.

- `central`: any quantity of the upstream enters the downstream likelihood as a central value or a constraint. This includes: using the upstream θ̂ as the center of φ; constraining the downstream with a posterior version of the nuisances exported by the upstream (§10.4); the upstream ξ entering the downstream; the upstream result determining any fixed value (ψ) of the downstream. The downstream grade is the lowest of its own and those of all `central` upstreams.
- `variation`: the upstream enters the downstream's systematic errors **only** as ±1σ variation sets or envelopes, and the downstream fit (including nuisance constraints) reads none of its quantities. It does not limit the downstream grade; it only requires that its own effective grade allow the use "systematic-error variation sets or envelopes".
- When the same upstream has both usages at the same time, it is decided as `central`.
- Example: when the upstream is `calibrated-unvalidated` and is cited only as an envelope, the downstream can still be `validated-in-scope` and be used for production; if the downstream also uses the η posterior it exports, it is `central`, and the downstream reaches at most `calibrated-unvalidated`.

**Flag inheritance** falls into three classes, with two inheritance sources:

| Class | Flags | Inherited from |
| --- | --- | --- |
| Grade-limiting | `outside-validated-range`, `closure-not-tested` | Union of its own and all `central` upstreams |
| Information only | `boundary-solution`, `multimodal`, `cv` | Union of its own and all `central` upstreams |
| Use-limiting | `preliminary`, `provisional-thresholds` | Union of its own and **all** upstreams (including `variation`) |

- The grade-limiting and information-only flags of `variation` upstreams are listed separately in `variation_flags` for the user to inspect, and do not affect the effective grade.
- What use-limiting flags limit is "whether it can serve as the basis for formal publication"; envelopes produced from data read off by eye or from provisional thresholds likewise cannot support formal publication.

**Effective grade**:

- When there is a `pending` input (rule 0), the capping by central upstreams ("Grade inheritance" above) and by grade-limiting flags (this paragraph), and the use matching below, are computed once for each of the two resolutions, and the two results are then compared.
- The effective grade is the lowest of the own grade and the effective grades of all `central` upstreams (see "Grade inheritance" above).
- When carrying `outside-validated-range` or `closure-not-tested`, effective grade = min(grade, `calibrated-unvalidated`).
- When carrying `preliminary` or `provisional-thresholds`, serving as the basis for formal publication is additionally prohibited.

**Use matrix** (by effective grade):

| Use | `failed` | `projection` | `calibrated-unvalidated` | `validated-in-scope` |
| --- | --- | --- | --- | --- |
| Diagnostics and debugging | ✓ | ✓ | ✓ | ✓ |
| Design studies, sensitivity estimates | ✗ | ✓ | ✓ | ✓ |
| Systematic-error variation sets or envelopes | ✗ | ✗ | ✓ | ✓ |
| Production simulation or corrections | ✗ | ✗ | ✗ | ✓ |
| Basis for formal publication | ✗ | ✗ | ✗ | ✓ (and no `preliminary`, `provisional-thresholds`) |

**Relation to g4sim labels**: the four grades of this section describe only `calibration-result`. The labels used by g4sim and the study protocol (`simulated-unvalidated`, `synthetic`, "compared with cited values", `validated-in-scope` of reference cases) describe simulation studies, not evidence of this workflow. The `validated-in-scope` on the two sides has the same name but a different meaning: the `validated-in-scope` of a simulation study cannot upgrade a calibration result, and the grade of a calibration result does not change the label of a simulation study.

### 10.3 Dependency graph

- The checker rejects circular dependencies; cycles must be merged into one joint fit.
- **When an upstream is revised or downgraded**, the downstream is automatically marked as needing a redo. Upstreams are listed by hash in the downstream contract (§5.2 `upstream[]`), so a redo necessarily changes the contract hash and κ (§9.5); the original validation units of the downstream have already been validation-read by the old κ, and the redone result reaches at most `calibrated-unvalidated` on these units according to rule 3d. To obtain `validated-in-scope` again, raw units never validation-read are needed. This is a deliberate design of §9.5, not an exception.
- **Re-judgment of the same κ after the records are resolved is not an upstream revision**: according to §9.5, a result that has `pending` inputs and can be cited is necessarily one for which the two resolutions give a common (effective grade, use) (otherwise it is `incomplete` and cannot be cited), so the re-judgment after resolution (§10.1) necessarily gives the same (effective grade, use). In this case the downstream is not marked as needing a redo, and the old hash in the downstream contract's `upstream[]` remains valid; `calib_deps.py` records the old and new ones as earlier and later decisions of the same κ.
- **Change of simulation identity**: when any model identity recorded by the result (the five masked hashes of §5.1) changes, the result is marked as needing a redo. For example a Geant4 or g4sim upgrade (`build_hash`, Geant4 version or data-set versions), a change of geometry or material other than θ, φ, a change of response stage or efficiency map. Changes of the values of the θ, φ fields (design points, writing back θ̂) and changing only `provenance_id` do not need a redo. The conditions for keeping old results after a change are listed as an open question in §19; until decided, always redo.
- **Segmented calibration**: the calibration order is arranged according to the DAG and the injection edges.

### 10.4 Propagation: principal components of the joint posterior

**Shared nuisance vector**: all the shared nuisances used by a result are combined into one vector

```latex
\zeta = (\eta,\ \phi_{\rm shared})
```

where η is the data systematic error and φ_shared is the shared φ in profile mode (including the φ of the efficiency map of §6.7). Each component is registered with its own global key (data release hash, source of φ, efficiency map hash). Shift-mode φ is not in ζ (it is not fitted, see below).

**Export**:

```latex
\theta = \hat\theta + G_\xi\,\xi + G_\zeta\,(\zeta - \hat\zeta) + G_s\,\frac{\phi_s - \phi_s^{0}}{\sigma_{\phi_s}},
\qquad \xi \sim N(0, I),\quad G_\zeta = \Sigma_{\theta\zeta}\,\Sigma_{\zeta\zeta}^{-1}
```

- **ζ is centered on the joint posterior**: the upstream exports the **joint** posterior (ζ̂, Σ_ζζ) of ζ, including the cross covariance between η and φ_shared, as one version (version id see below). G_ζ is a **single joint regression**; it must not be computed separately as Σ_θηΣ_ηη⁻¹ and Σ_θφΣ_φφ⁻¹, because when η and φ_shared are correlated, the two marginal regressions misestimate the center and the variance (counterexample: with ρ_ηφ = −0.78, the exported variance of θ₁ is 0.061, the correct one 0.125).
- **Export of bootstrap noise**: the sampling noise of V̂ likewise moves ζ̂ (η and φ_shared are fitted together with θ), so Σ_boot of §2.1 is estimated for (θ, ζ) as a whole. All covariance blocks of this section (Σ_θθ, Σ_θζ, Σ_ζζ) take the corresponding blocks of Σ_β + Σ_boot / w (w computed with ε̂⁺ according to §7.3, the same as for the interval half-width of §7.5 and σ_tot of §8.1); the exported ζ posterior Σ_ζζ therefore also contains Σ_boot,ζζ / w.
- **ξ represents only the residual uncertainty of θ itself**: G_ξ is obtained by eigendecomposition of the conditional covariance Σ_θ|ζ = Σ_θθ − Σ_θζΣ_ζζ⁻¹Σ_ζθ (the sum of the previous item), and already includes the correlation of θ and ν. ν is not exported separately. Thus Var θ = G_ξG_ξᵀ + G_ζΣ_ζζG_ζᵀ + G_sG_sᵀ = Σ_θθ + G_sG_sᵀ (Σ_θθ contains Σ_boot,θθ / w), consistent with the interval widening of §7.5.
- **Shift-mode φ_s**: column l of G_s is the Δθ̂_l obtained from the ±1σ refits of §5.5; φ_s enters downstream with its own prior N(φ_s⁰, σ²) (it is not constrained by the upstream data, so it has no posterior version).
- ξ is registered in the global nuisance registry keyed by the "result hash".

**Downstream use**:

- By default, ξ is treated as N(0, I), and ζ as a constraint by the joint posterior N(ζ̂, Σ_ζζ) of **that version in the cited upstream package**, profiled together with the downstream parameters.
  - Not a newer version in the registry: package rule 1 requires the package to be used as a whole; to use a newer version, a joint fit together with the result that produced that version is required, according to the conflict rules.
  - Not the prior N(0, 1), nor the separate marginals of the components.
  - When the downstream uses only some of the components of ζ, it uses the corresponding marginal of the joint posterior of that version (a Gaussian marginal is just the sub-block), which is still correct.
- If the downstream data pull any component of ζ, the downstream result must export the **joint posterior update** of all the shared nuisances it uses.
- **Version**: a version is a joint constraint summary of a set of shared nuisances.
  - First compute the update payload digest update_digest = hash(contract, data and plan hashes, engine version, parent versions, fit and export values), explicitly excluding its own id, the final result hash and fields back-filled from them; version id = hash(normalized list of parent version ids, update_digest).
  - Then write the version id into the final result and compute the result hash; the registry additionally records the mapping between versions and results.
  - The version id must not be defined in reverse by "the result hash containing the version id", otherwise a content-hash cycle forms.
  - Different payloads give different versions; exactly identical payloads reproduce the same version.
  - Each version records its **lineage**: the updater, and every result in the updater's `central` dependency closure (all `central` upstreams taken recursively, §10.2; including upstreams that enter only through ξ, or θ̂ as φ center or fixed value). Recording only "the results that have constrained this version" is not enough: if two downstreams both use the ξ of the same upstream as a central input, the ζ versions they export are highly correlated, even if neither version contains that upstream's ζ.
- Only when the nuisances are fixed and not constrained by downstream data may the outer products of the terms be added directly.

**Conflict rules** (`calib_deps.py`): every **uncertainty object** used by an analysis (the ξ of each upstream result, each shared nuisance version) has a **source set**:

- ξ_U of result U: {U} ∪ the `central` dependency closure of U;
- a shared nuisance version: its lineage (the updater and its `central` dependency closure).

Decision (first build the complete propagation packages, then check the dependencies between packages):

1. The θ|ζ, ξ and its matching joint ζ version of the same upstream form one **atomic propagation package** with coefficients. The independence of ξ and ζ comes from the Gaussian conditional decomposition of this section; although the two have the same source, a redo of the joint fit cannot be required on that account. The citer must keep that decomposition intact and cannot replace the ζ in it with an arbitrary newer version. The same nuisance key and the same version create only one variable and impose only one constraint in one analysis.
2. Different packages that constrain the same shared nuisance with different versions, or in which the independence of ξ was not preserved after a downstream update, cannot be multiplied independently; they are combined by a joint fit or a validated complete joint factor.
3. Intersecting source sets of different packages are a dependency warning that must be resolved; unless an explicit joint factor already describes all cross correlations, a joint fit is required. Disjoint source sets are also **not proof of independence**: the raw data lineage, MC samples, external auxiliary measurements, shared priors/model discrepancies and efficiency-map bases must also be compared. Shared but non-updated external constraints must also be identified with global keys and counted only once.
4. Multiplication is allowed only when the checks above confirm that there is no unmodeled common random source, or a verifiable conditionally independent factorization has been provided. When dependency information is missing, independent combination is rejected; different result ids or disjoint lineages cannot replace evidence.

**Limits of the Gaussian export**: the conditional regression and Schur complement of this section keep only the first- and second-order information of the joint Gaussian distribution. For upstreams with boundaries, multiple modes or significant non-Gaussianity, equivalence with a complete joint fit cannot be claimed; instead pass the complete joint factor/a reconstructible upstream likelihood, or fit jointly directly. The Bayesian "joint posterior" and the frequentist "local Gaussian constraint summary" must be labeled separately in the result; shared original priors/auxiliary constraints must not be multiplied in again.

Other:

- Enumerated models are listed separately as envelopes.
- When the point of use is outside scope, the `outside-validated-range` flag is added.
- When exporting to a conditions database, the result hash is written into the metadata of the conditions tag.

**Feeding back to g4sim**:

- When calibrated parameters are written back to the g4sim specification (materials or geometry of detector-spec, stage parameters of `response-pipeline/1`), the `source_of_facts` of the value is the hash of the calibration result, with the effective grade and flags attached. g4sim requires every parameter to have `source_of_facts`, otherwise it refuses to run. This holds for the three specifications and `response-pipeline/1`; g4sim S9's `condition-snapshot/1` and `alignment-overlay/1` do not require `source_of_facts` (optional in both schemas), so this workflow writes the hash of the calibration result, with its effective grade and flags, into their `source_of_facts` itself, and `calib_use.py` checks offline that every exported snapshot and overlay carries it (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md).
- Per-channel conditions that do not change the geometry are exported as g4sim `condition-snapshot/1` documents (g4sim §17, S9): one per readout system, with IOVs [start_ns, end_ns) of the run's clock that may not overlap, and rows whose `cell` is a dictionary of the readout's field values; for g4sim's only consumer, `core/simulation/digitize.py`, the cell is {`volume`, `channel`} (the g4sim volume ID and the channel's index in the digitization job). The exported quantities are `gain_factor` (a factor on the sensor gain of `response-pipeline/1`, not an absolute gain), `threshold` (replaces the electronics threshold) and `dead`; `temperature_K` is recorded, but no g4sim stage reads it. Conditions that change the geometry (alignment) are exported as an `alignment-overlay/1` (shifts `delta_mm` and small rotations `zyx_deg` of IR placements named by mother, template and copy number), which g4sim applies to the expanded IR, producing a new `geometry_id`.
- The use matrix (§10.2) specifies that "production simulation" accepts only `validated-in-scope`. This matching must be performed when g4sim reads the parameters, which is a modification of g4sim and is listed as an open question in §19; until g4sim implements it, `calib_use.py` performs an offline check on the exported specification files.

### 10.5 Extension module: contribution decomposition

- Each effect must declare its "value after removal", implemented through `effects_off`.
- When n ≤ 10, evaluate all 2ⁿ subsets; when n > 10, approximate by permutation sampling and report the sampling error.
- **Every subset actually evaluated** must pass the ESS threshold of G4. If any one fails, this decomposition is not output.
- On every permutation, the sum of the terms already equals the total; the purpose of this rule is to prevent some terms from using unreliable estimates.
- Report the covariances between the terms with the bootstrap.
- It must be stated whether the object of the decomposition is the variance or the resolution itself.

## 11. Specialization interface

### 11.1 What a detector type must provide

1. The stage mapping, including the node split at injection points.
2. Mechanism choice and parameterization.
3. The kernel properties of each node; implementations of `log_density`, `run` and `resample`.
4. Storage recommendations.
5. Reference catalog: types and injection edges.
6. Implementations of special functionals, and link functions.
7. (Advisory) Literature values of f, C, ℓ for the V_model correlation kernel.
8. (Advisory) A default list of alternative hypotheses: deviations that lie outside the null model and should be detectable.

### 11.2 What an experiment instance must provide

1. The stage-graph instance and the storage format.
2. Conditioning variables.
3. Control samples, the extraction model, and the effects s_j of the correlated systematic errors.
4. An adapter implementing `evaluate`, `resample`, `evaluate_from`, `learned_closure` and `ask/tell`. When g4sim is used, it instead provides: the three g4sim specifications, `response-pipeline/1`, the node binding and recording levels (§11.4); the evaluator is provided by the generic implementation of §7.1.
5. Conditions database export (when g4sim is used, the conditions snapshot format of §10.4).
6. Threshold defaults: only the values may change, not the kind or order of the gates.

### 11.3 Experiment types

| | Large collider | Space experiment | Under construction | Prototype beam test |
| --- | --- | --- | --- | --- |
| Conditions structure | Segmented (IOV) | Function of conditions, partial pooling | Constant | Constant |
| V_model | Model ensemble | Correlation kernel | Model ensemble | Correlation kernel or none |
| Validation | `holdout` | `holdout` (across periods) | `none`, product is `projection` | `cross-validation`, must satisfy P7 |
| Evaluation path | Mainly ask/tell | Synchronous and ask/tell | Synchronous | Synchronous |

### 11.4 g4sim binding

This section maps the objects of the abstract model to g4sim. The mapping is written in the implementation layer of the plan (§3.1). Scripts that read it:

- `calib_chain.py` reads it to derive candidate methods;
- `calib_contract.py check` and `calib_design.py` read it to run the checks of §5.2, §6.1 and §6.6.

**Table 1: node binding**

| Abstract node | g4sim object | Kernel property | Remarks |
| --- | --- | --- | --- |
| 0 Input | source of `simulation-request/1` | Density (`source-density/1`) | Only `analytic` is accepted (§5.2) |
| 1 Transport and deposition | `g4sim_run` (`detector-spec/1`, run card) | Samplable black box | Birks is computed step by step in the SD; outputs `edep`, `edep_visible`, `edep_by_dedx_class`, hits |
| 2 Carrier generation | Response stage 1 (quantum generation) | Density (Poisson; rounded Gaussian) | A Birks change is not a node-2 operation: `edep_visible` is recomputed deterministically at the output of node 1 from `edep_by_dedx_class` (each class's deposit times 1/(1 + k_B x_c)), with no event weights (g4sim §9.1, g4sim D5; settled by plugin source, D75) |
| 3 Carrier transport | Response stage 2 (transport, efficiency map) | Density (multinomial) or deterministic | The efficiency map applies only to scintillation light; Cherenkov light belongs to node 1 (full optical tracking) |
| 4a Conversion | Both paths apply the PDE inside Geant4: `photon_detected` counts a photon only when `G4OpBoundaryProcess` returns `Detection`, which a sensor surface does with the probability of its `efficiency` spectrum (`optical_surfaces`, g4sim S7). Efficiency-map path: the PDE is folded into ε_c by the mapping run (see below), unless the map is built with sensor `efficiency` = 1 under the PDE split of §6.7, which applies the PDE in the digitization job (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md). Full optical tracking: the PDE acts at the sensor surface during transport (node 1); a QE/PDE(λ) of response stage 3 is listed in g4sim §10.1 but not implemented (no stage kind) | Density (binomial) | See below |
| 4b Amplification | Gain, ENF and dark counts of response stage 3 (`sensor`); SiPM saturation is listed in g4sim §10.1 but not implemented | Density or deterministic | — |
| 5 Electronics | Response stage 4 (built into the core, or connected to FE4 via stage hand-off) | Depends on the stage | FE4 is a file hand-off; the core does not import the skill |
| 5 Readout | Response stage 5 (zero suppression, clustering, crosstalk, dead channels) | Mainly deterministic | Zero suppression causes missing support (§6.1) |
| 6–7 Feature extraction and reconstruction | simreco (`simreco-strip`) or the user's reconstruction | Deterministic | The reconstruction algorithm is not part of g4sim |

**Position of the PDE and the injection-point split**

The efficiency-map path of g4sim outputs the per-channel photoelectron count N_pe,c in response stage 2 (g4sim §10.3 point 4: "the per-channel photoelectron count is the sum of the photons it receives from each cell"). That is, the efficiency map ε_c combines light collection and photon detection: the mapping run counts only photons that the sensor surface detects with the probability of its `efficiency` spectrum (g4sim S7). On the full optical tracking path, the same surface efficiency acts during transport; a QE/PDE(λ) of response stage 3 is listed by g4sim but not implemented. Under the PDE split of §6.7 the map is built with sensor `efficiency` = 1, so that ε_c is light collection only, and the PDE is applied in the digitization job (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md). Accordingly:

- **The edge between 4a/4b** (the position of single-photoelectron injection) lies between response stages 2 and 3.
  - The only stage hand-offs g4sim provides are `response-handoff/1` between stages 3 and 4 (FE4) and between stages 4 and 5 (`simreco-strip`). On the scintillation path, stages 1 and 2 are drawn from one volume sub-stream (`response.py scintillation_event`), so no hand-off exists before stage 3, and none is planned (settled by plugin source, §19).
  - So a single-photoelectron injection reference cannot be declared (P4 can still be decided from the DAG, but the evaluator cannot inject on this edge).
- **The edge between 3/4a** (a light source with a known photon count, the §3.5 binomial thinning chain) does not exist in the efficiency-map path without the PDE split of §6.7: collection efficiency and PDE then appear only as a product in ε_c.
  - To place an injection reference between the two, the efficiency map must be split into a map "reaching the sensor surface" and a separate PDE kernel; g4sim does not provide this as a kernel (settled by plugin source, §19). This workflow may split it when the PDE acts in Geant4 only as the sensor surface's `efficiency` (§6.7 "PDE split"): the map is built with sensor `efficiency` = 1, and the PDE is applied as a scale p of the per-bin efficiencies of `g4sim-digi-job/1` (g4sim S8), or, for a wavelength-dependent PDE, as their spectral weighting from the mapping run's `photons.csv`. The edge 3/4a is then the job's efficiency input, and a reference with a known photon count can be declared there (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md).
  - Without the split (the PDE model is not only the sensor `efficiency`, or the split check of §6.7 fails), such references cannot be declared on the efficiency-map path; collection efficiency and PDE are combined into one parameter (the scale of ε_c), and P3 is decided accordingly.
- **Full optical tracking path** (Cherenkov, or scintillation light without an efficiency map): `photon_detected` counts photons the sensor surface detects with its `efficiency` spectrum, during transport, and `photons.csv` records the energy of each detected photon. The PDE is therefore part of node 1 (changed by resimulation), and there is no stage 2→3 hand-off and no hand-off inside stage 3 (settled by plugin source, §19). To apply a PDE(λ) after transport, the surface `efficiency` is set to 1 and this workflow thins the `photons.csv` rows by their energy itself; g4sim has no response stage for it (§19, C3) (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md M3). Without that, neither injection reference can be declared on this path.
- g4sim's term "photoelectrons" means photoelectrons. On the efficiency-map path the PDE is the `efficiency` spectrum of the sensor's optical surface, applied by Geant4 during the mapping run (`photon_detected` counts `Detection` only); under the PDE split of §6.7 the mapping run uses `efficiency` = 1 and the PDE is applied in the digitization job instead (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md). `response.py scintillation_event` returns photoelectrons per channel, and `sensor_response` applies no PDE draw, so the mapping above holds (settled by plugin source for g4sim S4 and S7, §19).

**Table 2: parameter location and candidate methods**

| Parameter location | Examples | Candidate method (cost tier) | Preconditions |
| --- | --- | --- | --- |
| source of the request | Beam energy distribution, spot size, incidence-angle distribution | Analytic reweighting (low) | `analytic` density; support condition (§6.1) |
| Geometry and materials of detector-spec (except the Birks and scintillation fields); physics settings of the run card | Wrapping thickness, crystal density, cut, step limit | Resimulation (high) | A new `geometry_id` or run card for each design point |
| Birks k_B of a detector-spec material | — | Rerun (deterministic, medium): `edep_visible` is recomputed from `edep_by_dedx_class` | `edep_by_dedx_class` recorded as `column` or `event_file`; discretization error feasible (§5.4). The θ value is applied by the evaluator. The detector-spec Birks constant stays nominal, because `g4sim_run` refuses to run if the read-back constant differs; only the full-simulation spot checks of §5.4 write a new k_B into the detector-spec, which gives a new `geometry_id`. |
| Scintillation yield LY and `RESOLUTIONSCALE` r | — | Re-digitization (medium); analytic reweighting (low) when only LY changes and only the Poisson interval is used | θ binds to `light_yield_per_MeV` and `resolution_scale` of the `scintillation` stage of `response-pipeline/1`, which is what `response.py` reads (accepted by the author, 2026-11-09; source en/g4sim-binding-check.md A5). The detector-spec material fields stay nominal: they fix the E^L/E^S split of `edep_visible_ly_split` and enter `geometry_id`. Also needs `edep_visible_ly_split` and r within the valid range (§5.4). |
| Parameters of response stages 2–5 | Gain, ENF, noise, threshold, crosstalk; a PDE is not a response-stage parameter in g4sim (it is the sensor surface's `efficiency`, see the optical row), except under the PDE split of §6.7 (next row) (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md); otherwise it is part of ε_c (§11.4) | Analytic reweighting (low, for Poisson/binomial/multinomial kernels with inputs and outputs stored); otherwise re-digitization (medium) | Hit file or stage hand-off file; the only hand-offs g4sim provides are 3→4 and 4→5, and there is none before stage 3 (§19), so nodes 3 and 4a can only be re-digitized as a whole from the hit file or the stored scorer quantities |
| PDE under the split of §6.7 (efficiency map built with sensor `efficiency` = 1) | SiPM PDE p (wavelength-independent), or a PDE(E) table | Re-digitization (medium): the evaluator writes p·ε_c(b), or Σ_i PDE(E_i)/n_b, into the job's efficiencies; for observables linear in ε, analytic (μ(p) = μ_0 + p·(μ(1) − μ_0), μ_0 the part that does not depend on ε); when p is θ, a per-photon thinning nested in p for every readout system with an observable not linear in ε (§6.7) | The PDE acts in Geant4 only as `EFFICIENCY` (no reflectance, transmittance, refractive index, window or angle dependence tied to it); the split check of §6.7 passed; `g4sim-digi-job/1` (S8), in Python or `g4sim_digi`; for a PDE(E), the mapping run's `photons.csv` kept and hashed; never as a thinning of charge or of codes, and never after dark counts, cross-talk or saturation (decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md) |
| Optical properties, efficiency map | Reflectivity, absorption length, η(z), and the PDE as the `efficiency` spectrum of the sensor surface when the PDE split of §6.7 is not used or not allowed | Resimulation (high), including the corresponding run that redoes the efficiency map | g4sim S7 (merged): the efficiency map of each design point is rebuilt by its own mapping run; the production run must use the same materials (the response check `map-stale` compares the map's materials hash with the run's), so the production run is resimulated as well; the mapped template is a box placed once with no rotation (§19, C22) (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md m8) |
| Misalignment of the simulated geometry | Shifts and small rotations of IR placements in an `alignment-overlay/1` | Resimulation (high) | g4sim S9 (merged): an applied overlay gives a new `geometry_id`, a zero shift included; one overlay per IR; an entry (mother, template, copy number) moves that daughter in every touchable of its mother, so a per-touchable θ needs a logical of its own in the detector-spec (§19, C28); the overlaid IR must pass check-spec (gap rule and error bounds), so a design point whose overlay leaves the clearances is refused; `geant4_run.py run-spec` takes no overlay, so no recorded run of a misaligned geometry exists yet (§19, C25), and `geant4_run.py reco` reconstructs with the run's overlaid IR, not the nominal one (§19, C26); an overlay at every design point, the nominal one included, is required by §5.1 (D86) |
| Parameters on the reconstruction side | Alignment assumed by reconstruction, clustering parameters | Rerun (deterministic, medium) | simreco column file |
| Physics list, EM option | — | Discrete model M | Confirmation record of §5.2 |
| Fast-simulation model in a `fast_sim_envelope` | A substitute shower model | Discrete model M; no θ, because models have no run-card parameters | g4sim S8: `physics.fast_sim` names a model of `fast_sim_models.json` and the particles it acts on, and the model is compiled into `g4sim_run` (covered by `build_hash`, §5.1); only two test models ship, and a substitute model is validated by the study under hep-ml's protocol, not by g4sim's gates; a model's deposit is a zero-length step, so `edep_visible` ≈ 0 inside the envelope, and no scintillation, Birks or efficiency-map parameter can be calibrated on a volume inside an envelope (§19, C29); a hook changes the events even when it never triggers, so it never shares common random numbers with full simulation (§6.6) |

**Re-digitization and common random numbers**

"Re-digitization" is a kind of deterministic rerun: the same batch of Geant4 events, the same Philox key, different θ, so the two θ use the same stream of uniform variates (the common random numbers of §6.6).

This guarantees only that the inputs are the same, not that the sampled values vary smoothly with θ. In the following cases, the later draws in the same substream fall out of step:

- θ crosses an algorithm switch point, for example the switch between inverse transform and PTRS at Poisson mean 30, or the Poisson/Gaussian switch at μ_b = 10;
- the number of rejection-sampling attempts changes.

This only reduces the variance reduction of common random numbers and causes no bias; when an objective function smooth in θ is needed (§7.4), it is reflected in σ_noise.

**`log_density` of the kernel registration**:

- Poisson and binomial: g4sim samples with PTRS, BTPE or inverse transform, which yields the exact distribution; `log_density` uses the analytic pmf directly.
- Multinomial: implemented as successive conditional binomials; `log_density` uses the multinomial pmf.
- Scintillation photon count when μ_b > 10: g4sim draws "a rounded Gaussian of width √(v_b − 1/12), set to 0 below 0", which is a discrete distribution. `log_density` must be the pmf of this discrete distribution (the Gaussian probability between adjacent half-integers, including the left tail at 0), not the normal density. P0 catches an implementation that uses the wrong one.

**Conditions**: conditions in g4sim that do not change the geometry (`condition-snapshot/1`, g4sim S9: `gain_factor`, `threshold`, `dead`, `temperature_K` per cell and IOV) enter only the response layer, and only through `core/simulation/digitize.py` (`g4sim_digi` does not read them, §19, C24); they correspond to ψ in this workflow (or φ when they have an uncertainty). The IOVs of the conditions structure (§3.7) and the IOVs of the g4sim conditions snapshot use the same index, expressed as [start_ns, end_ns) of the run's clock. g4sim facts that the binding must respect: `gain_factor` is a factor on the sensor gain of `response-pipeline/1`, not a gain; `threshold` replaces the electronics threshold; a dead channel reads no code, but its row still carries photoelectrons and charge (D83 (11)); no g4sim stage reads `temperature_K`; on the digitization-job path the cell is {`volume`, `channel`} (the channel's index in the job), not the readout-encoding fields; a cell no row names takes the snapshot's `defaults`; g4sim's events carry no time of their own, so each event's time is given in the job (`event_time_ns`, §19, C27), and a time no IOV covers is an error. Changing a condition moves no draw, so re-digitization at two condition values uses exact common random numbers; the charge scales with `gain_factor` up to rounding, while `threshold` and `dead` change the code discontinuously ("Re-digitization and common random numbers" above). Binding (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md §1.5, W2, W4; D87): a condition value known without non-negligible uncertainty is ψ, and the snapshot is part of the model identity (§5.1); one with a non-negligible uncertainty (D37) is φ, bound to its snapshot row by the JSON Pointer `/iovs/<k>/rows/<j>/<quantity>`; a per-channel gain or threshold that the study calibrates is θ, bound to the snapshot row of its cell and IOV, with the conditioning structure "piecewise independent" (§3.7) on the snapshot's IOVs, while a gain common to all channels binds to the sensor stage of `response-pipeline/1` instead; `dead` is discrete and is never θ or φ (a different dead-channel set is a different model); `temperature_K` cannot carry θ or φ, and a temperature-dependent gain is expressed as `gain_factor` per IOV; the plan records each event's time as a function of its global event number (§6.6).

---

## 12. Sufficiency check

All eight types fit into the same generic layer, with no special cases.

| Type | Typical parameter → mechanism/node | Possible degeneracies (§3.5) | Abstraction it motivates |
| --- | --- | --- | --- |
| ECAL | Light yield → yield/2; Birks → nonlinearity/2; collection efficiency → transport/3; PDE → yield/4a; gain → 4b; noise → 5; dead material → geometry/1 | Binomial thinning chain (yield × collection × PDE); addition in quadrature; scale and response shape | Binomial thinning chain; injection-point split |
| HCAL | Cross-section scaling, hadronic model parameters → physics process/1; sampling fraction → geometry/1; light yield, Birks → 2; SiPM saturation → nonlinearity/4b | Poisson × gain; scale and response shape (non-compensation as a power law) | Physics-process parameters; fluctuations at the deposition level |
| RICH | Refractive index and dispersion → 1; PDE → 4a; mirror alignment → geometry/3 (changes the light path, needs resimulation) | Refractive index and geometric scale; photon count × per-photon resolution | Parameter placed at the emission node |
| DIRC | Refractive index → nodes 1 and 3 (the same parameter acts on two nodes); bar-surface reflectivity → transport/3; PDE, TTS → 4a | PDE × reflectivity (broken by photon counts at different polar angles, because the number of reflections changes with polar angle); time offset and group velocity | Correlation on the transport node; two-dimensional shape functional |
| TRD | TR yield → yield/1; gas gain → 4b; dE/dx model → discrete choice | Mean: TR yield × gas gain; width: Landau fluctuations of dE/dx and the TR spectrum (the width alone cannot separate yield and gain; π samples and known momentum are needed) | Tail functional and local ESS |
| Tracker | Charge sharing → 3; Lorentz angle → transport/3; gas diffusion, attachment → 3; gas gain → 4b; residual smearing → noise/5 (used only when the microscopic mechanism is not modeled); alignment → geometry/7 | Addition in quadrature; sum of two terms (Lorentz angle and alignment); offset mixed into width | Geometry of the reconstruction node (rerun); redundant measurements can determine the width |
| TOF | Emission time → time/2; effective light speed, attenuation, path dispersion → 3; TTS → 4a; T0, slewing → 5 | Sum of two terms (T0 and x/v_eff); addition in quadrature | Control variables come from other subsystems; a DAG is needed |
| μ detector | Gas gain and HV → 4b (HV listed as φ); threshold → 5; cluster size → sharing/3; multiple scattering in the absorber → physics process/1; t₀ → 5 | Efficiency, threshold and noise; sum of two terms (t₀ and the r–t relation) | Matching functional across branches |

**Acceptance criteria**: when adding a new type, if the generic layer outside §3 needs to be modified, the abstraction is insufficient, and §3 should be revisited and corrected.

---

## 13. Integration with existing hep-research components

| Component | Home | New or reused |
| --- | --- | --- |
| Schemas of the seven abstract objects | `contracts/` | New |
| Schemas of contract, data release, plan, result | `contracts/` | New; `validate.py` only calls the libraries of `calib_deps` and `calib_use` |
| Engine, gates, validation | hep-statistics (`core/calibration/`) | New; reuses `fit_diagnostics`, `toy_ensemble` |
| Eight detector-type specialization documents | hep-detector `simulation-calibration/` | New |
| Generator tuning | hep-theory | New documentation; **does not take the g4sim path** (g4sim requires the calibration workflow to reject an `external` source, and the contract checker does so, §5.2), see §19 |
| Simulation, job submission | hep-computing, `adapters/geant4` | Reused; new ask/tell state file |
| g4sim (specifications, `g4sim_run`, response pipeline, hits, kit) | `contracts/`, `core/simulation`, `adapters/geant4`, hep-detector | Reused; binding in §11.4 |
| g4sim evaluator `g4sim_calib_eval.py` | `adapters/geant4` | New (§7.1) |
| Surrogate models, SBI, learned density ratio | hep-ml | Reused; new documentation on cross-fitting and probability calibration |
| Review | hep-review | New calibration review obligation template and hep-detector domain card |

---

## 14. Tools and scripts

**Conventions**:

- Output is JSON.
- Exit codes:
  - 0: normal;
  - 1: negative decision;
  - 2: input error;
  - 3: incomplete (result status `incomplete`, decided at the layer of the effective grade per §10.2 rule 0).
- Only the standard library plus NumPy/SciPy.
- Each check is **implemented** by exactly one script (table below); other scripts that need the same decision call it and do not write a second copy. "Called by X" in the table means X uses the implementation in that row.

| Script | Checks it alone owns |
| --- | --- |
| `calib_chain.py` | • DAG and injection-point split<br>• Candidate methods (derived from §11.4 Table 2 when g4sim is used)<br>• Directed reachability condition (P4) |
| `calib_contract.py check` | • All contract rules of §5.2, including the `source` row and model identity; except the recomputation at the fit point (`calib_fit.py` calls `calib_data.py`, §5.2)<br>• Declaration check of N_d,c on the calibration side (all modes, §2.1): at lock, and redone at θ̂ when called by `calib_fit.py` (§5.2 clause 6)<br>• N_decl of a free-ω shape has a recorded basis; a simulation without absolute normalization does not enter as an absolute count shape (§2.1)<br>• The value convention of summary-statistic estimators, and that the value convention satisfies the declared N_d<br>• The observables that make up an "exact relation determined by the observed component totals" must not all be used at the same time in an event sample that belongs entirely to the validation data (§9.2, D27); in samples that contain calibration observables the relation is declared as N_d or N_d,c instead; whether a sample belongs entirely to the validation data is decided by `calib_data.py` from event-level lineage<br>• PDE split: the declared PDE parameter acts only as the sensor `efficiency`, not on the angle of incidence; every sensor surface of the efficiency-1 map has `efficiency` = 1, and a fixed map's `surfaces_sha256` equals g4sim's hash of the production `optical_surfaces` with the sensor `efficiency` entries set to 1 (g4sim's `map-stale` does not compare surfaces); a PDE(E) is not declared as a constant scale; and the `EFFICIENCY > 0` condition of §6.7 holds for the declared PDE(E) (§6.7, decided by the author on 2026-11-10) |
| `calib_contract.py preflight` | • A0: on the calibration data, with the smooth model declared by the contract, check whether each threshold is reachable<br>• Obtains data via `calib_data.py` (`calib_data.py` registers the contract draft as the read channel for the A0 read, §9.5) |
| `calib_data.py` | **Release and ingestion**<br>• Data release, commitment hash, sealing and opening<br>• Ingestion checks (only that declarations exist, values are not read): representation format, derived relations, sources of uncertainty components, correlation structure of relative systematic errors, exposure of validation samples (§2.1); existence of the per-observable "has a value" declaration (§5.2)<br>• `systematic` is submitted separately from the observed values; `observed` and `expected` are sealed together with the observed values and provided to no script (§2.1)<br>• Raw data lineage<br>• Registration of contract drafts (sole registrar)<br>**Data-side checks at lock time**<br>• Data-side constraint checks with the calibration data, including N_d,c and the N_d of cross-validation (§2.1, §9.2)<br>• Whether an event sample containing calibration observables is entirely contained in the calibration release: event-level lineage comparison (called by `calib_contract.py check`, §2.1)<br>• Equality check of N_decl, N_decl,s against known observed totals, reading only the totals (called by `calib_contract.py check`, §2.1)<br>• Cross-validation: check "has a value" against the calibration data (called by `calib_contract.py check`, §9.2)<br>• Check that unused observables whose reason is "untestable" agree with the "has a value" declarations (§5.2)<br>• holdout: use lineage to compare the calibration release and validation release for "no shared raw units", once at lock time and once before opening the holdout; sharing means rejection (§9.5)<br>**Decisions on shapes and rounding**<br>• N_decl (≥ 10) and N_exp of validation shapes, shape summary-statistic n_min, block-conversion conditions and merging: called by `calib_contract.py check` at the evaluation points, and by `calib_fit.py` at the fit point (§2.1)<br>• Compute the rounding resolution ρ_i from the release format and lineage; decide the rounding negligibility condition at the evaluation points of §2.1 (combinations of scan points, prior vertices and nuisances) (called by `calib_contract.py check`); recompute at the fit point (θ̂, ν̂, η̂, φ̂) after the fit converges (called by `calib_fit.py`, §2.1)<br>**Opening**<br>• Opens only for a κ that satisfies all of the following (§2.1, §6.6, §9.2, §9.4, §9.5): passes the declaration check; the recomputation at the fit point (θ̂, ν̂, η̂, φ̂) of rounding, σ_i⁽⁰⁾ > 0, N_exp, n_min and block-conversion conditions passes; P7 is not `incomplete`; k₀ > 0; when k₀ > 0 and T_v is calibrated with toys, the replicas of the toys of Ĉ_r and the reference distribution have been generated per §6.6 and pass the non-overlap check; the calibration data is real data; no mandatory gate failed; no mandatory gate is `incomplete`; the calibration release and validation release share no raw units; P7 decides that the power is sufficient; the ratio test of the reference toys and Ĉ_r generated before opening has not failed; data lineage and overlap are confirmed. The "outcome already determined" lookup result of `calib_use.py` is also an input to the opening conditions (§10.2 rule 0)<br>• At opening: data-side constraint checks (§9.2); the "has a value" declarations agree with the content (§5.2, §9.2)<br>**Reads and failure records (§9.5)**<br>• Read events on raw units (unit, hash of the data release, read channel, κ (if any), `fit`/`validation`, sequence number); fit reads are also recorded, including A0 and exploration before the lock<br>• Decide holdout eligibility per §9.5, and derive the reuse inputs of Appendix C (the reuse input `fit-pending` is unreachable under the current rules and is kept only for compatibility with old records)<br>• Failure records (unit, κ, sequence number, status), sharing the same increasing sequence number with read events; written as `pending` at opening (including the calibration data used by cross-validation), changed to `final` or `withdrawn` according to the decision records of `calib_validate.py`<br>• The list of concurrent validation configurations on the same batch of calibration raw units<br>• Annotation records of `computational-run` hashes, keyed by the result hash; those who cite the result obtain them together with it via `calib_deps.py` (§14.1) |
| `calib_kernel_check.py` | • P0 |
| `calib_design.py` | • Generation of the Sobol design points and of the P6 held-back set (§6.4, D80)<br>• Fold split for cross-validation: shapes and derived quantities do not cross folds; the P3 of each training fold calls the same implementation in `calib_identify.py` (§9.3)<br>• P2<br>• P5 (including the Σ_boot estimated with toys in §2.1, b_J of P5, and the θ-noise item s_i, κ_i of P5, §8.2 note 3)<br>• Seeds of the mapping runs of a θ scan (§6.7, D28): the declared seeding; with the shared seed, that the `primaries.csv` of the scan agree event by event, and that the digitization job reproduces the photoelectrons of `response.scintillation_event` with `map_replica` = r for g4sim's own replicas (§6.7, predictions at a joint-pattern replica); rejection of the practices that §6.7 rejects (remedy level: plan)<br>• Every `g4sim-digi-job/1`: `run_seed`, `replica` = 0, keys (jobs without conditions), conditions jobs without keys and in Python only, `event_time_ns` (§6.6); its agreement with `response-pipeline/1`, the map or the declared replica and the snapshot (§5.1)<br>• Fixed-map mode: the linear construction of U only for observables the plan records as linear in ε (§6.7, decided by the author on 2026-11-09)<br>• PDE split: the split check with a nested pair of mapping runs (in the fixed-map mode once per efficiency-1 map, in the mode where the map varies with θ once per scan), and after any change of the Geant4 version or of the sensor materials or surfaces; when p is θ, route 1 for every readout system with an observable not linear in ε; route 1: its stream key, its position before the sensor stages and never as a charge or code scale; the surfaces hash of the maps of a θ scan; route 3: the mapping run's `photons.csv` kept and checked against the map's counts, the energy grid with its pseudo-mass and variance conditions, and the replica key; the `EFFICIENCY > 0` condition over the prior or design range (§6.7, decided by the author on 2026-11-10)<br>• Feasibility and the final method<br>• Support (including g4sim filtering and recording levels, §6.1)<br>• Non-overlap of event intervals and the construction of the MC realization of toys (§6.6): every replica of a replica difference enters the non-overlap check; a plan that takes the nominal as the truth and a single replica as the prediction is rejected<br>• Whether the acceptance of §8.7 covers the weighting construction used; if not, add `closure-not-tested` (§2.1)<br>• Derivation and recording of the applicability conditions of mandatory gates (§8.1)<br>• Reject plans that reuse bootstrap events by reweighting (§2.1)<br>• P7 (the formal check of alternative hypotheses is only in `calib_contract.py`) |
| `calib_identify.py` | • P3, G5<br>• Including the P3 of each cross-validation training fold, and G5 for each fold and toy (`calib_design.py`, `calib_validate.py` call the same implementation, §9.3) |
| `calib_emulator.py` | • Generation of the training set of the surrogate model (§6.4, D80)<br>• P6 (including the spot-check points mandated by §5.4)<br>• Surrogate domain<br>• ask/tell state file |
| `calib_closure.py` | • G8 |
| `calib_fit.py` | • Reference-point iteration, multi-start<br>• G1, G2, G3, G6, G7<br>• Locally linear toys, linearity check<br>• After convergence, call `calib_data.py` to recompute at the fit point (θ̂, ν̂, η̂, φ̂) the rounding, σ_i⁽⁰⁾ > 0, the N_exp of validation shapes (absolute count shapes, §2.1 "Expected total of validation shapes" (ii)), shape summary-statistic n_min and block-conversion conditions (§2.1)<br>• Call `calib_validate.py` to redo declaration checks (a)(b)(c) at θ̂ (§9.2)<br>• Call `calib_contract.py check` to redo the N_d,c declaration check (a)(b)(c) at θ̂ with the actual V_G (§5.2 clause 6, D21)<br>• If any of the three items above does not hold, report a contract error with exit code 2<br>• Iteration limit, the decision of non-convergence, replacement and counting of ensemble members, k* of the ratio test (§7.3); `calib_closure.py`, `calib_design.py`, `calib_interval.py`, `calib_validate.py` call the same implementation for the ensembles of G8, Σ_boot, Ĉ_r, the interval toys of §7.5 and all other kinds of toys |
| `calib_likelihood.py` | • Construction of the joint likelihood, including the error sources of §2.1: count error of the predicted expectation, event-level parametric bootstrap at θ_ref<br>• Blocks; link functions (including alr/ilr for normalized shapes; the data-side representation, applying the merging decided by `calib_data.py`, §2.1)<br>• ν and η; V_model principal components (including shape correlation kernels in clr coordinates, §5.4)<br>• Recomputation of summary statistics and bootstrap when a shape is redeclared (§9.2)<br>• Samples with free ω are conditioned on the observed totals (§2.1)<br>• Pass/fail summaries of weighted MC for binomial blocks (Σw, Σw², Σw³ and cross covariance, §2.1)<br>• Map term U(θ)φ_map of the mode where the map varies with θ, U(θ) = Σ_j w_j(θ)U_jE_j, profiled with θ (§6.7, D28) |
| `calib_interval.py` | • Profile likelihood intervals, Feldman–Cousins, MCMC<br>• Interval widening in shift mode<br>• Inference flags: labeling of credible intervals and of non-Gaussian exports (§7.5, §15.3a) |
| `calib_reweight.py` | • Weights, G4, G4-L |
| `calib_shift.py` | • P8, G9 (the two conditions of §5.5)<br>• ±1σ and ±2σ refits, d_l |
| `calib_validate.py` | **Validation statistics**<br>• Validation statistics (including general response and toy calibration, §9.2); toys of T_v apply the release rounding; toy data and the frozen V̂ per §7.3<br>• C_r⁺ on N_d; standardization (s_i = σ_i⁽⁰⁾)<br>• Decision of bootstrap rank deficiency at opening (τ_num, §2.1)<br>• Decision of whether the toy replicas have been generated (§6.6); minimum number of toys (§9.2, §9.3)<br>• Totaling of the fraction of toys failing G5 and the decision against the 20% threshold (§9.3; the power toys of P7 are handled by `calib_design.py` calling the same implementation)<br>• Cross-validation<br>• Design-stage declaration checks (a)(b)(c) (`calib_design.py` calls the same implementation in P7)<br>• Power and its simultaneous lower confidence bound (§9.4; `calib_design.py` calls the same implementation in P7)<br>• Reporting of k and unused observables<br>• Not in this row: untestable observables are rejected by `calib_contract.py check` per §5.2; the data-side constraint check and the "has a value" check are run by `calib_data.py` at opening (§9.2)<br>**Records**<br>• Write the validation configuration κ before computation<br>• Decision records: pass, fail, `no-testable-direction`<br>• Abandonment declaration of the `abandon` subcommand: accepted only for a κ whose failure record is still `pending` (opened and not yet decided, §9.5); after abandonment, no further decision record for that κ is accepted<br>• Power-abandonment declaration of the `abandon-power` subcommand: accepted only for a κ whose T_v or T_cv has been decided as passing and whose power lower bound has not yet been computed (§9.4)<br>• `calib_data.py` changes the status of failure records according to the decision records (§9.5) |
| `calib_deps.py` | • Dependency graph<br>• Upstream invalidation, invalidation caused by a change of simulation identity (§10.3)<br>• Derive upstream roles from usage (§10.2)<br>• Registration and lineage of ξ and shared-nuisance versions<br>• Update conflicts |
| `calib_use.py` | • The "outcome already determined" lookup before opening (the general principle of §10.2 rule 0); the result is passed to the opening conditions of `calib_data.py`<br>• Grade assignment rules (§10.2 rules 0–4, including `incomplete` aggregation)<br>• Inheritance by role, flags, use matching<br>• Eligibility of `variation` upstreams (Appendix C.3; citation is rejected if ineligible)<br>• Offline use check for feedback into g4sim specifications, condition snapshots and alignment overlays, including their `source_of_facts` (§10.4) |
| `calib_propagate.py` | • Export of joint-posterior principal components, scope, conditions database metadata<br>• Construction and global registration of efficiency-map native bases<br>• Joint-pattern replicas of a shared-seed θ scan (pattern table and its hash, scan key, the R draws, U_j) and the analytic covariance from the same pattern table (§6.7, D28)<br>• Propagation into each study, linear maps for local dimension reduction (§6.7)<br>• U of the fixed-map mode: from digitizations at the replicas (`g4sim-digi-job/1` or `map_replica`), or from the linear construction U = J B_map for the observables the plan records as linear in ε (§6.7, decided by the author on 2026-11-09)<br>• Specifications and conditions snapshots fed back into g4sim (§10.4) |
| `calib_contrib.py` | • Contribution decomposition |

### 14.1 Execution environment: Linux and Slurm

> **Source of this section**: this section is not in the frozen version v7.37.4. It is an execution binding added by the clean edition for running on Linux and Slurm, and it has not gone through the R2 regression of v7.37.4. It specifies only the execution layer; apart from the items to be confirmed listed in §19, it does not change any statistical rule. When the two appear to conflict, the statistical rules prevail, and the conflict is reported as a defect. Until confirmation, this section always takes the handling that does not produce a grade without basis.

This section binds §2.1, §6.6, §6.7, §7.3, §7.5, §8.4, §9.2–§9.5, §11.4 and the scripts of this chapter to Linux and Slurm.

#### Submission

- Batch execution always goes through hep-research's `core/partition/` and `adapters/batch-schedulers/batch_campaign.py` (check-config, plan, freeze, verify-bundle, submit, status, watch, resubmit, reset, reconcile, confirm, abandon, cancel, clear-orphans, merge, report), and follows hep-computing `references/batch-scheduling.md`.
- Every `submit`, `resubmit` and `cancel` needs the user's approval each time.
- Until a trusted submitter has qualified, the agent may submit only in a disposable test environment and with synthetic data (`batch-scheduling.md`), that is, the acceptance of §8.7 and §15. Campaigns of actual calibration studies (including the toys of G8, Σ_boot and P7 that do not read real data), and campaigns that read real calibration data or validation totals, are always submitted by the trusted submitter from a frozen bundle (`freeze`, `submit --bundle`).
- When the project carries `agent_policy`, `submit`, `resubmit`, `cancel`, `reset`, `confirm`, `abandon` and `clear-orphans` of `batch_campaign.py` always go through the trusted submitter (`protected.batch_needs_trusted_submitter`). The `abandon` here abandons a submission; it is not the `calib_validate.py abandon` of §9.5.
- Heavy computation does not run on login nodes.

#### Boundary between plan and execution record

| | Plan (enters the plan hash and κ, §5.1, §9.5) | Execution record (does not enter κ) |
| --- | --- | --- |
| Content | • The allocation function of seed blocks; the b namespace of each (study, use, ensemble[, subset]) and the `logical_run_seed` of each block<br>• Member identity of attempt 0 (use, ensemble[, subset s], attempt a, block b, member index i), and the global event interval, Philox key and toy random-number key it determines<br>• Number of members n_req (with subsets, each n_req,s) and the size of the reserve block (below) | • Campaign settings, partition, account, QoS, `time_limit`, `memory_mb`, chunk size<br>• Job IDs, each attempt and its resource changes<br>• Registration records of blocks (below)<br>• Execution environment: thread count, BLAS backend, hash of the environment lock, the value of `slurm.constraint`, the actual CPU model of the node, and the response implementation (Python `core/simulation/response.py` and `digitize.py`, or `g4sim_digi` with the SHA-256 of its executable (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md); a job with a condition snapshot always runs in Python; the SHA-256 of every `g4sim-digi-job/1` digitized, §5.1) |
| Writer | `calib_design.py` writes the plan; the plan hash is obtained per §9.5 by `calib_validate.py` before computing the validation statistic (the plan itself is not locked) | `batch_campaign.py report` writes it as a `computational-run` record |

- The hash of each `computational-run` record is written by `calib_data.py` into an annotation record keyed by the result hash (the same mechanism as the annotation of concurrent validation configurations in §10.1; the `calib_data.py` row of the §14 table), and does not enter the hashed content of `calibration-result`. So resubmitting with increased resources per hep-research's rules changes neither κ nor the result hash.
- **The execution environment is not in κ** (the plan content of §5.1 does not include it). All members of one ensemble, and all attempts of one single fit, must run under the same execution environment (thread count, BLAS backend, hash of the environment lock, CPU model, the response implementation (Python `core/simulation/response.py` and `digitize.py`, or `g4sim_digi` with the SHA-256 of its executable, which no g4sim record hashes; a job with a condition snapshot always runs in Python); `slurm.constraint` must select a single CPU model); when the `execution` subobjects of the member records show differences, that ensemble or fit is `incomplete` and is rerun under the original execution environment. Whether the execution environment should belong to κ is to be confirmed by the author (§19).
- **Redo and budget revision**: the seed blocks used by the redo and replacement of §7.3 are reserved in advance by the allocation function, so a redo does not need to change the plan and is the same κ (§7.3). The "budget revision" at redo mentioned in §6.7 is treated in this section only as an update of the budget accounts (event count and core hours), and does not change the plan hash; this is written following the more explicit "same κ" of §7.3, to be confirmed by the author (§19). A modification that changes n_req, the allocation function or the event intervals is a change of plan, that is, a new κ.

#### Seed blocks and array tasks

- **Allocation function**: defined for all b ∈ ℕ, and pairwise non-overlapping by construction. For example: g4sim allows at most 2³² global event numbers under one `logical_run_seed`, so each block gets its own seed. Block b of (study, use, ensemble[, subset]) uses `logical_run_seed` S_b = H(plan series identity, study, use, ensemble[, subset], b, t), where H is from `core/simulation/seeds.py` and t ≥ 0 is the smallest value that gives a seed not yet registered in the plan. Member i of the block uses the global event interval [i·N_ev, (i + 1)·N_ev), where m_blk and N_ev are the plan-declared upper limit on members per block and upper limit on events per member, and the plan must satisfy m_blk·N_ev ≤ 2³². The `run_seed` of each evaluation's `response-pipeline/1` equals its S_b (§6.6). H takes values in [1, 2³¹ − 1], so `calib_design.py` checks that the S_b of all registered blocks are pairwise distinct, on the block registry (S_b, t), not on member run records, and the registration record keeps t (per-block seeds, m_blk·N_ev ≤ 2³² and distinct S_b: accepted by the author, 2026-11-09; source en/g4sim-binding-check.md A3). Under the same `logical_run_seed`, f(use, ensemble) + b·Δ must not be used for different (use, ensemble): when b has no upper limit, these intervals eventually overlap.
- The non-overlap check of §6.6 runs, as in the original text, on every evaluation recorded in the plan; the construction of the allocation function additionally guarantees that blocks not yet used also do not overlap, so the "no upper limit on the number of redos" of §7.3 does not run out of blocks. Once the allocation function has been used for any submission, it must not be changed (a change is a change of plan).
- **Primary block and reserve block**:
  - At the start of each attempt a of an ensemble (or subset) (the first is a = 0; each redo of the whole ensemble in §7.3 adds 1), a primary block and a reserve block are registered in order, both before any member is submitted. Once registered, they are no longer allocated to any other use, even if the campaign does not complete.
  - The primary block contains n_req (or n_req,s) members. The reserve block contains the replacement members that the attempt may need: for an ensemble with replacement, k*(n_req) − 1 (§6.7); cross-validation toys add, for G5 renewal (§9.3), the number of G5 failures still possible before the stop point, ⌊0.25 × (Σ_a n_req + X_max)⌋ − F_G5 ("Completion of an ensemble" below), counted at registration; in attempt 0 the former ⌊0.25 n_req⌋ was short by up to 3 members with replacement (settled by computation, en/compute-19-14-1f.md; to be confirmed by the author).
  - The "next unused seed and event interval" of the replacement in §7.3 and the G5 renewal in §9.3 is the unused member with the smallest member index in this attempt's reserve block. When the reserve block is used up, the next block is registered as this attempt's extension reserve block, without changing the plan.
  - The "next unused seed block" of the redo of the whole ensemble in §7.3 and §7.5 is the primary block of the next attempt: the block with the smallest b that has not yet been registered as a primary block or reserve block.
  - Registration of blocks is done by the ensemble implementation of `calib_fit.py`, which writes an append-only registration record on the designated host (part of the execution record; it does not enter the plan hash or κ); the member identities of attempts a ≥ 1 and of extension reserve blocks are determined by the allocation function and this registration record. b increases in registration order within each namespace, so it does not depend on the order in which other ensembles register.
  - With subsets, the primary blocks of the subsets are registered in the order of the subsets in the plan, then their reserve blocks are registered in the same order; the size of each subset's reserve block is k*(Σ_s n_req,s) − 1.
  - The order of members is by (a, registration order of the block, i).
- **Campaign and chunk**:
  - A campaign of an ensemble contains only one (use, ensemble[, subset], b), and the item index of the manifest is the member index i. A reserve block is placed in a separate campaign and submitted only when needed; it must not be placed in the same campaign as the primary block.
  - The items of a resimulation campaign of the reference-point iteration ("Budget and scheduling limits" below) are the design points of that iteration, and the item index follows the order of the design points in the plan.
  - A chunk is a contiguous range [`{start}`, `{stop}`). g4sim's run-card `chunk` field is not read by `g4sim_run` for new specifications; parallelism inside a run is by threads. It is unrelated to the Slurm array (§5.1, §6.6).
- **Random numbers are derived only from the plan and the member identity**:
  - g4sim: `logical_run_seed` is taken from the plan, and the global event interval is written into the member's run card as `run.first_event` and `run.events` (absolute values). The card is handed to `geant4_run.py run-spec` by path and SHA-256, so the interval is part of the card's hash and of `run_id`; `run-spec` takes no seed or event-range options.
  - The g4sim run records of this workflow are not placed in a design artifacts directory: there, `contracts/design.py` (rule C2.1) refuses a `logical_run_seed` repeated outside one declared `seed_group` (accepted by the author, 2026-11-09; source en/g4sim-binding-check.md A19).
  - Other toy random numbers (data noise, constraint centers of ν and η, the prior of φ, N(0, V_emu), N(0, V_learn^bias), Wishart, bootstrap event counts, multi-start perturbations): NumPy `Generator(Philox)`, with keys derived from the member identity and the sampled item. The study is represented by the identity of the contract series; for the interval toys of §7.5: whether the scan point enters the member identity (and hence the random-number key and the replica) is declared by the plan (§6.6 allows both). Regardless of how it is declared, the ratio test of §7.3 always treats all toys of one interval construction as one ensemble (for G8, all interval toys of all pseudo-data), with X and n summed, and k* computed from the summed n. These keys enter the non-overlap check of §6.6 together with the g4sim keys.
- **Not sources of randomness**: the manifest's `{seed}` is only for the adapter to check, and the same holds for `SLURM_ARRAY_TASK_ID`, job IDs and host names. So chunk size, array index and resubmission do not change the result of any member.

#### Member records and ensemble quantities

- The chunk result of a worker program has only one key, `members`, whose value is the list of member records ordered by member index. `merge` and `report` always carry `--rule members=concat`; the adapter's default per-key addition is not used, as it would add lists of equal length element by element.
- Each member record carries its member identity. The numeric fields of a member record (fit results, `status`, iteration count, etc.) depend only on the member identity and must not contain NaN or infinity (the adapter would quarantine it): missing values are represented by `null`, and the state by `status`, whose value is `converged`, `not-converged` (with the reason of §7.3) or `exception` (with the type of exception). For cross-validation toys, a converged member record also carries `g5_pass` (true or false, decided inside the worker program by the implementation of `calib_identify.py`, with the failing fold when false), because G5 renewal and its stop point are decided in member order from it.
- Thread count, BLAS backend, hash of the environment lock, the value of `slurm.constraint` and the CPU model of the node (for example `model name` from `/proc/cpuinfo`) are written in the `execution` subobject of the member record, and are not numeric fields.
- **Inputs of ensemble quantities**: the owning script reads each campaign's `chunks/<id>.json` directly (the authoritative copy collected by `status`/`watch` via `collect()` of `core/partition/campaign.py`), and checks that its SHA-256 is identical to the campaign's collection record (`collected.<chunk>.sha256` in `state.json`, which is what the provenance check of `merge` uses), and also identical to `extension.output_hashes` of `computational-run`. When `merge` reports `refused` (a provenance problem), that ensemble is treated as an engine defect (§4.2) and is `incomplete`. The merged result of `merge` is not used as input, because missing chunks after the stop point would make `merge` produce no merged result. On reading, check that each chunk's `members` has exactly stop − start entries and that the identities match [start, stop) in order; if not, it is treated as an engine defect (§4.2), and that ensemble is `incomplete`.
- **Who computes it**: replacement and counting of members, the decision of non-convergence, the ratio test, k* and w(ε̂) are done only by the ensemble implementation of `calib_fit.py` (§7.3, §14); `calib_closure.py`, `calib_design.py`, `calib_interval.py`, `calib_validate.py` call it. Ensemble quantities such as p-values, λ̂_a, Ĉ_r, Σ_boot are computed by the script that owns the item in the §14 table, from the completed ensemble, on the designated host, by member index (scalar sums always use `math.fsum`; for covariance, first take the mean with `math.fsum`, then the sum of squared deviations with `math.fsum`), and the algorithm used is entered in the execution record. Worker programs do not deliver partial sums.

#### Execution failure is not non-convergence

The "non-convergence" of §7.3 refers only to the result of a fit. When a member produces no member record, it is an execution failure:

| State normalized by the adapter | Category | Handling |
| --- | --- | --- |
| `done`, with a valid member record | Fit result | Counted according to `status` and §7.3 |
| `lost` (including when the scheduler reports completion without valid output), `preempted-or-evicted`, `node-failure` | Execution failure | Rerun with the **same** member identity, within `max_attempts` |
| `timeout`, `out-of-memory` | Execution failure | Rerun with the same identity after changing only `time_limit` or `memory_mb` (the change is entered in the attempt) |
| `failed`, `held`, `cancelled`, `unknown`, `not-submitted`, `abandoned` | Execution failure | Rerun after a human runs `reset` with a reason (through the trusted submitter when the project carries `agent_policy`) |
| `submitting` (submission interrupted or outcome unknown) | Not yet decided | A human inspects with `reconcile`, then runs `confirm` or `abandon` (through the trusted submitter when the project carries `agent_policy`); it is neither an execution failure nor `incomplete` |

- Execution failures do not count toward X, do not trigger replacement, and are not removed from the ensemble. The same member can only be rerun with the same identity, so reruns cannot be used to select members.
- Thread count, `resources.cpus` and `slurm.constraint` must not change on rerun ("The execution environment is not in κ" above).
- The worker program delivers member records with exit code 0 for converged, not-converged and `exception` fits; it exits with a code other than 0 only when no member record is produced.
- **Numerical exceptions**: reproducible numerical exceptions inside a fit (`LinAlgError`, NaN, a query outside the surrogate domain being refused) are caught in the worker program and recorded as `status: "exception"`. Whether they belong to the non-convergence of §7.3 is to be confirmed by the author (§19); until confirmation: if, in member order, the stop point has already been reached before the first `exception` member, that member is after the stop point and does not affect the ensemble; otherwise (the decision uses only the members before it, so it does not depend on whether it counts as non-convergence), that ensemble computes neither X nor any ensemble quantity, and the gates, P7 or V that depend on it are `incomplete`.
- **Single fits and scan points**: Class 1 single fits (the actual fit, each cross-validation fold, G9 refits, §7.3) and the fits of profile scan points are treated the same way:
  - An execution failure is rerun with the same input, is not recorded as non-convergence, and does not make G1, G5 or G9 fail.
  - When reruns are exhausted (the cases listed under "Incomplete" below), the corresponding decision is recorded as `incomplete`: G1 for the actual fit, V for each cross-validation fold, G9 for a G9 refit, and for a scan point the interval it belongs to (hence G3) and G5.
  - When a member record is `exception`, until the author confirms, it is likewise recorded as `incomplete`, not as a G1 or G9 failure, and is not counted, per "Non-convergence at scan points" of §7.3, as staying inside the interval or as Δ(−2 ln L) < 4.
- `time_limit` is set from the pilot's cost on the worst θ with 30 iterations and all starting points (§7.4), plus a margin whose rationale can be stated.

#### Completion of an ensemble

- **Stop point**:
  - Ensemble with replacement: the number of converged members in this attempt reaches n_req; or the X summed over all attempts reaches k*(N_tot), where N_tot = the sum of the numbers of members that actually converged in the previous attempts + n_req (§7.3; in the first attempt N_tot = n_req). The size of the reserve block is only a reserved amount; when it is used up, an extension reserve block is registered as above, and the stop point is not affected.
  - Ensemble with subsets: the replacement for Σ_boot (one subset per toy, n_req,s = K_b) and for G8 (one subset per injection point, n_req,s = N_c) takes place within the subset (§7.3), and replacement members are taken only from the reserve block of the same subset. The stop point is when the number of converged members of every subset reaches n_req,s, or the X summed over all subsets reaches k*(Σ_s n_req,s) (the ratio test treats all members as one ensemble, §7.3).
  - Ensemble without replacement: n_req members.
  - **Cross-validation toy ensembles** (Ĉ_{r,f}, with replacement; the reference distribution of T_cv and the power toys, without replacement) are in addition renewed per §9.3: a toy failing G5 does not count toward n_req (nor, with replacement, toward the converged members of the stop point above). Let F_G5 be the number of G5 failures summed over all attempts, counted in member order. The G5 proportion of §9.3, summed over all attempts, is decided at the end of every attempt: at completion, and also when the attempt ends in a failing ratio test (§7.3); if it is > 20% there, it has the consequence given in §9.3 (V or P7 `incomplete` with remedy level plan; for the power toys, "power lower bound not yet computed"), and no redo with a new seed block is made (settled by computation, en/compute-19-14-1f.md; to be confirmed by the author). Within an attempt, the stop point is also reached at the first member at which F_G5 > 0.25 × (Σ_a n_req + X_max), where Σ_a n_req is the sum of n_req over the attempts registered so far, this one included, and X_max is k*(N_tot) − 1 of the ratio test of this attempt for an ensemble with replacement and 0 for one without; from that member on, every continuation of the attempt ends with the proportion > 20% under either denominator of D68 (en/compute-19-14-1f.md), so the consequence given in §9.3 applies at that point (for the power toys, "power lower bound not yet computed"). If the denominator proposed in D68 (toys for which G5 was decided) is adopted, the earlier stop F_G5 > 0.25 × Σ_a n_req is also valid; which threshold applies follows D68 (§19).
- **Complete**: the ensemble is complete when, in member order, every member up to the stop point has a member record. Members after the stop point are not required to have records and do not enter any statistic; their event intervals are still recorded as used.
- **Incomplete**: when `attempts-exhausted`, `stopped-repeated-failure`, `resets-exhausted` or an exhausted limit (`limits.exceeded`) leaves members before the stop point without records, the ensemble is incomplete, and the gates, P7 or V that depend on it are `incomplete` (§10.2 rule 0, exit code 3); when a human later fills the gap with `reset` or by changing the limits, it is decided again after completion per §10.2. When members before the stop point lack records while the adapter's decision is still `wait` or `resubmit`, it is an input not yet decided. While the adapter's decision for such a member is `needs-reset`, `needs-resource-change`, `no-retries-configured` or `not-submitted`, the input is likewise not yet decided (a human must act: `reset` with a reason, a resource change, setting `max_attempts`, or submission); the ensemble becomes incomplete only through the four conditions above. This classification is safe by the plugin source (`core/partition/states.py`: these four decisions are non-terminal, and each persists until a named human action; `not-submitted` (no attempt record) is decided before every other check, `resets-exhausted` and `stopped-repeated-failure` are tested before `needs-reset`, `no-retries-configured` and `needs-resource-change`, and `attempts-exhausted` before `needs-resource-change`; the limits that this section requires, `limits.max_resets_per_chunk`, `max_submissions` and `max_total_jobs`, bound the number of resets and submissions, so every human action leads either to a member record or to a terminal state that this section maps to `incomplete`, but without a human action the result waits with no time limit; settled by plugin source, §19); while it holds, the owning script reports which members block the ensemble and which human action each needs.
- **No partial decisions**: the completed part must not be used to compute, rescale or decide. hep-research's practice of "reporting missing chunks at merge" does not apply in this workflow.
- **Duplicate outputs**: duplicate outputs of the same member must be bit-identical except for the `execution` subobject. The adapter's `identical_result` (`extension.environment.execution.duplicates` of `computational-run`, which compares the whole `result`) is false for duplicates run on different nodes because `execution` differs; for each duplicate whose `identical_result` is false, the owning script reads that file from `outputs/<chunk>/`, removes `execution` and compares again; if it still differs, that ensemble is `incomplete`, and whether it is an engine defect is checked per §4.2. `merge.conflicting_duplicate` (another file claiming the same chunk appears in `chunks/`) is always treated as an engine defect, and that ensemble is `incomplete`.
- **Order**: replacement, the stopping rule, G5 renewal and the ratio test are always decided in member order, not in completion order.

#### Single writer, data and opening (§9.5)

- The read records, failure records, sequence numbers and opening of `calib_data.py` are executed only on one designated host, by one process serialized with a file lock (site facts: the host, and a local or reliably lockable file system).
- Array tasks, Slurm dependent jobs and worker nodes must not call it, and must not read sealed data or the data releases themselves.
- **Input snapshot**:
  - Worker programs that need data values (calibration data, or the observed totals N_obs, N_tot,s after opening) read only input snapshots produced by `calib_data.py` on the designated host; campaigns cite snapshots by hash.
  - For each campaign that cites a snapshot, `calib_data.py` records a read before submission: for calibration data, a fit read (the read channel is that contract or draft, §9.5); for totals of validation data, a validation read of that κ (§9.5).
  - A snapshot of validation-data totals can be cited only by campaigns of the κ that opened it. When another κ needs these totals, `calib_data.py` must open them for that κ per §9.2 (that κ must itself satisfy all opening preconditions) and produce its own snapshot. A snapshot of calibration data may be cited by several κ; each κ that cites it records a separate fit read.
- **Opening**: opening (for cross-validation, the first computation of T_cv) is approved by a human each time, executed on the designated host, and not triggered by the scheduler. Before opening, the ensembles required by the opening preconditions of §9.2 must all be complete per "Completion of an ensemble" above (`merge` reporting complete is not required).
- Any "earlier than" is decided only by sequence number, not by file time, `sacct` timestamps or node clocks.
- Campaigns after opening (toys, bootstrap and V-stage power conditioned on N_obs or N_tot,s, §2.1, §6.6) receive only these totals, not y_v or T_obs, so the p-value is not computed before the ratio test (§7.3).
- The stdout, stderr and event logs of jobs are treated as outputs, handled per the release and scanning rules of "Logs are outputs" in `batch-scheduling.md`, and must not contain y_v or T_obs.

#### Budget and scheduling limits (§6.7)

- Using the pilot, convert the event budget of §6.7 (including ×30, reserve blocks and n_open) into core hours, allocate them to the campaigns, and write them into each campaign's `limits.max_core_hours`; `limits.max_submissions`, `limits.max_total_jobs` and `limits.max_resets_per_chunk` must all be set. The adapter computes limits only from each campaign's own usage, so the study-level total is obtained by the owning script summing the usage of the campaigns and reporting it. Campaigns of a redo get their own limits, counted in the budget accounts (§19).
- The pilot includes at least the nominal point and the worst θ. The pilot is a separate campaign that uses event intervals reserved in the plan specifically for the pilot, outside the allocation function (or another `logical_run_seed`), and enters the non-overlap check of §6.6; its output does not enter any statistic. `submit --pilot` on an ensemble's campaign is used only to confirm scheduling; its chunks are regular members. The pilot measures the response with the implementation the ensemble will use (Python or `g4sim_digi`, §6.6); a job with a condition snapshot runs in Python only, because `g4sim_digi` reads no conditions (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md). On g4sim's registered workload (e+ of 1–60 MeV in a plastic block, four channels) the Python response took 3.44–3.57 times the transport and `g4sim_digi` 0.21–0.23, but 0.78–0.80 with a time for every detected photon (Python 16.7–18.0); the `g4sim_digi` times were measured before its output changed to IEEE bits.
- The digitizations at the R map replicas that build U (§6.7; in the fixed-map mode through `g4sim-digi-job/1` or `map_replica`, by the author's decision of 2026-11-09, unless the plan uses the linear construction for an observable linear in ε) add no events, but R digitizations of the study's events for each construction of U; they are converted into core hours with the response time per event that the pilot measures, and counted in the campaigns' limits.
- When a limit is exhausted, it is `incomplete` as above. The number of members is decided by the plan, not by the remaining quota.
- A reference-point iteration that needs resimulation (§2.1, §7.3) is prepared iteration by iteration by the driver of `calib_fit.py`, one campaign per iteration, using the same set of event intervals that the fit has in the plan (the actual fit, each cross-validation fold and G9 refits share the set of the fit, §6.6; ensemble members each use the intervals determined by their own member identity). The driver only prepares campaigns and bundles (`freeze`); submission is still approved each time per "Submission" in this section. The iteration state is written through the ask/tell state-file implementation of `calib_emulator.py` (§7.1, §14), and the driver resumes from the state file after an interruption; the iteration limit of 30 counts only fit iterations, not submissions, and time spent waiting for approval does not count toward any limit.

#### Numerical determinism

- Before importing NumPy/SciPy, the worker program itself sets `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to the value fixed in the execution record for that ensemble (or fit) (default 1; not in the plan, does not enter κ, §19). It does not rely on `env_passthrough`: that acts only on the scheduler client, and Slurm jobs run with `--export=NONE` and do not inherit the submitting side's environment.
- The environment lock file (including NumPy, SciPy and the BLAS backend) is entered in the bundle with `freeze --env-lock` (SHA-256). `freeze` only records the hash of the lock file and does not check the environment the job actually uses: that the job uses this environment is guaranteed by the trusted submitter from the bundle, and the worker program additionally writes the hash of the environment lock into the member record.
- Use `slurm.constraint` to restrict the jobs of one ensemble to a single CPU model (site fact); when this cannot be done, additionally fix the BLAS kernels with `OPENBLAS_CORETYPE` or `MKL_CBWR`, and enter this in the execution record.
- "An exact recomputation with the same κ is reproducible" (§9.5, §10.1) means in this section: with the worker program under the same `build_hash` and execution environment, and the designated host under the same environment lock and CPU model (all entered in the execution record), the numeric fields are bit-identical (accepted by the author 2026-11-09, §19).

#### Exit codes and states

| Exit code of `batch_campaign.py` (`merge`/`report` after the campaign ends; row 2 also covers `submit`, `resubmit`, `reset`) | Meaning | Mapping in this chapter |
| --- | --- | --- |
| 0 | Campaign complete | Means only that execution is complete; whether the result passes is still decided by the scripts of this chapter |
| 1 | There are unfinished, failed or blocked chunks | Does not map directly to an exit code; the owning script decides per "Completion of an ensemble" above: complete; not yet decided; or 3 (`incomplete`) when the "Incomplete" conditions are met. Each of the three is **not** 1 (negative decision) |
| 2 | Refusal (configuration, usage or lock, for example `campaign.locked`; `submit` and `resubmit` additionally have `bundle.*`) | 2 (execution configuration error, with the adapter's error code); not a contract error, does not change the contract state. The output JSON distinguishes it from the contract errors of §14 with `"error_kind": "execution"`. Exception: `limits.exceeded` (`submit`, `resubmit`, `reset`) means a limit is exhausted, and is handled as "Incomplete" under "Completion of an ensemble" above (exit code 3) |

- While a campaign is still queued or running, `status` and `watch` also return 1; this is an input not yet decided, not `incomplete`. A campaign still running or queued at the time of the "outcome already determined" lookup (§10.2) is likewise an input not yet decided.
- The `failed` label of `computational-run` means only that the campaign is not complete; it is not the evidence grade `failed` (§10.2 rule 1).
- The large acceptance tests of §8.7 and §15 (for example ≥ 10⁴ repetitions, 1000 G8 runs) run under the same binding, and the results are labeled `synthetic`.

#### Site facts

The following items are provided by the user; implementations and agents must not fill them in themselves:

- `slurm.partition`, `slurm.account`, `slurm.qos`, `slurm.constraint`;
- `resources.time_limit`, `resources.memory_mb`, `resources.cpus` (written as `--cpus-per-task`);
- `MaxArraySize` and per-user job limits, `limits.*` (including `limits.alloc_cpu_factor`), `max_attempts`, `throttle`;
- the host and file system of the single writer, shared and scratch paths, the digest of the container image.

Before choosing, inspect the current state of the cluster with read-only commands, per "Checking what a Slurm cluster can give you" in `batch-scheduling.md`.

---

## 15. Tests and acceptance

### 15.1 Toy detector

Labeled `synthetic`, runs in seconds, truth known. It is a DAG with merging branches:

- **Calorimeter branch**: input → deposition → photon generation (yield) → PDE (binomial thinning) → gain (including ENF) → electronics (noise, threshold).
- **Track branch**: input → momentum measurement.
- **Merge node**: E/p.

References:

- known input (can be switched off);
- a light source with a known photon count, on the "photon generation → PDE" edge;
- single-photoelectron injection, on the "PDE → gain" edge;
- a momentum reference on the track branch.

Also included:

- a pair of "sum of two terms" parameters, and one material thickness φ;
- a pair of overlapping modules on the calorimeter branch (comparison node: energy ratio); a pair of overlapping layers on the track branch (comparison node: position difference);
- two correlated shared nuisances: one data systematic error η (common energy scale) and one shared φ (material thickness), whose posterior correlation is determined by the data, for the joint propagation test of §10.4.

There is also a **subgraph variant**: only the calorimeter branch is kept, with no merge node.

There is also a **bimodal variant**: the pair of overlapping modules is read out as a sum, S = a f + b (1 − f) + ε with f ~ Beta(α, β) and ε ~ N(0, s²). A symmetric Beta gives two exactly degenerate mirror basins; an asymmetric Beta breaks the degeneracy only through the third moment (en/compute-D57.md).

The toy detector stays pure Python and does not depend on g4sim; the threshold calibration of §8.7 and the negative tests of all gates run on it.

**g4sim fixtures** (added only after the corresponding g4sim stages are merged, see §17):

| Fixture | Source | Status | Use |
| --- | --- | --- | --- |
| Synthetic ZDC calorimeter | `examples/zdc-synthetic-ecal` of g4sim S3 (6 × 6 PbWO4, all numbers assumed), extended with explicit Birks constants, scintillation yield and `RESOLUTIONSCALE`, `edep_by_dedx_class` and `edep_visible_ly_split` scorers at `column` or `event_file` level, and a `response-pipeline/1`; for the efficiency-map φ (g4sim S7): an optical crystal material (base `G4_PbWO4` with `optical.rindex`, `absorption_length_mm` and one scintillation component), the 0.25 mm gap as a gap volume of an optical material, a `dielectric_metal` skin on each SiPM with an assumed `efficiency` spectrum, an `optical_scope` requirement, and a single-cell mapping specification (one crystal with its wrapping, gap and SiPMs, placed once, unrotated, with the same materials as the array) with a `photon_detected` scorer (§19, C22) (accepted by the author, 2026-11-09; source en/g4sim-S7-check.md m7) | `synthetic` | Node 0 reweighting, Birks deterministic rerun from `edep_by_dedx_class`, re-digitization of LY and response parameters, resimulation-tier φ (wrapping thickness), efficiency-map φ (§6.7, §19) |
| RICH replica | the g4sim S7 reference case `ams02-rich-replica` (`profiles/reference/geometry-cases/cases/ams02-rich-replica/`, written by its `make_replica.py` from the task package's replica; `synthetic`; full optical tracking; FTFP_BERT_EMZ). The radiator height binds to `params.height_mm` or `params.aero_mm`; the refractive index is the spectrum `materials.aerogel.optical.rindex`, so a θ on it rescales the whole spectrum and needs resimulation. Its photons are counted at the detection plane with no PDE stage (§19, C3) | `synthetic` | The §3.5 "refractive index and geometric scale" degeneracy: that study has found the radiator height and the refractive index to be degenerate; used as a positive test of P3/G5 |

The values of both fixtures come from simulation; they can serve only for tests and comparison, and are not validation data (§10.2).

### 15.2 Positive tests

The tests in this section described with "size α" or "rejection rate α" are all run on toy ensembles without non-convergence; versions with injected non-convergence are decided by the one-sided acceptance of §8.7.

- [ ] G8: N_c computed per §8.4; bias and coverage both pass.
  - Verify the overall false-alarm rate with 1000 repetitions of G8, with the decision rule "number of false alarms ≤ 62" (pass probability 0.96 at a true false-alarm rate of 0.05; 0.02 at 0.08).
  - The non-convergence injection of §8.7 uses the same rule; power uses "detections ≥ 775".
  - This rule cannot distinguish 0.05 from 0.0625; it only blocks clear excesses.
- [ ] Three methods fit simultaneously, bias < 0.5σ.
- [ ] Multiple basins (bimodal variant of §15.1): each admitted basin is reported, with the `multimodal` flag added, and G1 passes for every basin; exactly degenerate basins are not merged; a stationary point with σ_tot,i > σ_prior,i is not reported as a basin; the classification is unchanged under 10 reseedings of the starts in ≥ 99% of 10³ toys (settled by computation, en/compute-D57.md; to be confirmed by the author).
- [ ] Segmented calibration: propagation via joint-posterior principal components agrees with the central values and covariance of the joint fit.
- [ ] Reweighting and rerun of non-generator nodes agree.
- [ ] In a setup where the data's information on φ is exactly c = 0.1, compare the difference between the shift and profile central values with ≥ 1000 repetitions: its rms agrees with √(c/(1+c))·|∂θ̂/∂φ|·σ_φ of §5.5 (relative difference < 10%). In each repetition, the true value of φ is sampled from the constraint N(φ₀, σ_φ²); fixing it at the nominal value makes the rms 4.7% low, which uses up most of the tolerance.
- [ ] E/p constrains the calorimeter scale via the merge node: P4 passes.
- [ ] After adding photon-source injection, yield × PDE is identifiable: P3 passes.
- [ ] The G6 p-value distribution of locally linear toys agrees with that of full toys.
- [ ] When the true value is exactly on the boundary, G2 passes, and the `boundary-solution` flag is added.
- [ ] The validation statistic with cross terms under the null hypothesis: mean is k = dim N_d^⊥ (n_v when there are no deterministic constraints), rejection rate is α.
- [ ] Shape conditioned on the total (K = 5, calibration total 500, reference total before opening 1000): for N_obs = 300, 1200, 1500, 3000, scaling the multinomial term and the propagation term separately per §2.1, the size of T_v is α.
- [ ] When the efficiency is close to 1, ν and η enter via logit, and the prediction always stays within (0, 1).
- [ ] Normalized shapes:
  - p = (0.6, 0.35, 0.05) under shifts of ±0.5, ±5 in alr coordinates: the prediction is always inside the simplex and sums to 1;
  - when the data contain a zero bin (60, 40, 0), the count likelihood is defined;
  - when the reference category or the bin order is swapped, the correlation kernel declared in clr gives the same fit result;
  - after shapes with shared events are merged so that the worst expectation at the evaluation points is ≥ n_min, K and the representation never change in 10⁴ toys;
  - the +½ estimator is defined for any counts (including a zero reference category), and when data and simulation apply the same estimator the residual mean is 0;
  - when the covariance of a shape together with the mean energy of shared events is estimated with an event-level parametric bootstrap, the size of T_v is α, and the covariance does not vary with the observed data.
- [ ] Null space:
  - C_r = diag(1, 0), N_d is the second direction; the rejection rate under H0 equals the α of T_v;
  - for a correctly declared definitional sum under float32 data, published values with four significant digits and derived values, and for residuals of a shape conditioned on the total under double-precision predictions, the data-side constraint check never triggers, and the size of T_v is α;
  - C_r = diag(100, 10⁻⁶) and its correlation matrix give the same decision;
  - two nearly collinear wrong declarations (each with small variance, together spanning a direction of variance 1) are caught by the block norm (a);
  - when a relative perturbation of 10⁻¹² is added to the eigenvalues of N_d^⊥, T_v and the decision do not change.
- [ ] Rounding:
  - a pair of validation observables for which the condition holds exactly (|c| = 1 − 25ρ̃², ρ̃ = 0.02–0.2, including negative correlation) has size within α ± 25% on uniformly distributed true values;
  - when a double-precision K = 50 shape and an uncorrelated rounded observable coexist, the contract decision depends only on that rounded observable;
  - rounding violated only at the upper boundary of the θ prior is caught by the recomputation at the prior vertex or at θ̂;
  - two groups of observable pairs with degenerate eigenvalues, recomputed with arbitrarily rotated eigenvectors, give the same decision;
  - Poisson bins of integer counts do not apply rounding;
  - for a signed quantity with one significant digit and nominal value near 0, ρ_i is computed from the largest magnitude within the ±5σ range;
  - when the cross term between a shape conditioned on the total and another validation observable scales with the first power of N_obs, the size for N_obs = 300–3000 is α.
- [ ] **g4sim (synthetic ZDC)**:
  - response parameters evaluated by re-digitization versus the result evaluated with a full `g4sim_run` plus response: P0 passes;
  - the `edep_visible` obtained by changing k_B with `edep_by_dedx_class` agrees with the `edep_visible` resimulated with the new k_B (difference within `g4sim_simulate.reweighting_bound` evaluated at the new k_B);
  - the width of the scintillation photon count is additionally spot-checked by P0 at the two extreme points of k_B (§5.4: the error of the E^L/E^S split has no upper bound and is not compared in this item).
- [ ] **g4sim (common random numbers)**: with the same batch of Geant4 events and the same Philox key, re-digitizing at two θ, the MC variance of the difference of the two predictions is smaller than that of the difference obtained from two independent sets of events.
- [ ] **g4sim (efficiency map φ)**: when the replica basis in the native coordinates of the efficiency map is used as φ_map, G7 passes, and the coverage of G8 passes; when the same setup instead puts the efficiency-map error into V_MC, the G7 statistic T is far below the median of χ²_{r(K−1)} (V_MC is overestimated; G7 is a one-tailed test and does not decide failure; this item is only reported).
- [ ] **g4sim (efficiency map φ, fixed-map mode, U from the digitization job)**: for an observable linear in ε, U from `g4sim-digi-job/1` digitizations at g4sim's replicas agrees with the linear construction J B_map within the response noise of the digitizations (§6.7).
- [ ] **g4sim (PDE split)**: on the ZDC fixture with optics, the split check of §6.7 passes at the nominal PDE, and the detections of its pair are nested; the photoelectron law of route 2₁ (job efficiencies p·ε_c) agrees with that of a mapping run at efficiency p, and route 1 (per-photon thinning before the sensor stages) agrees with route 2₁ in law; route 3 against a mapping run at a PDE(E): χ² of the efficiencies, the transit means and the integerised histogram, and the covariance of the route-3 replicas of Σ_i PDE(E_i)/n_b against the analytic multinomial covariance; for an observable linear in ε, U(p) = p·U(1) within the response noise of the digitization; once Geant4 is available, these are repeated with Geant4 transport (en/research-PDE.md used a synthetic transport).
- [ ] **g4sim (map varies with θ)**: with the shared seed and joint-pattern replicas, the marginal of the replicas at each design point agrees with g4sim's Dirichlet(k + ½), and their cross-point covariance with the analytic covariance of the same pattern table; G8 passes where it passes with the exact map covariance (§6.7, D28; en/research-D28.md §2, §4.1, §4.2).
- [ ] **g4sim (RICH replica)**: with only a single β, refractive index and radiator height are decided as not identifiable (P3), with a "multiple β" hint; after adding a second particle or momentum, P3 passes.

### 15.3 Negative tests (at least one per gate)

Each gate has at least one negative test. The basic tests of each gate are listed in §15.3.1; the remaining named cases are grouped by topic, one line per case, with the expected result after the arrow (→).

Tests marked "single-gate isolation mode": the test framework may call the function of one gate alone, without going through the pipeline; this is allowed only in tests.

#### 15.3.1 Individual gates

- [ ] **A0**: data deviate from a straight line by 3.5%, threshold 2%; reported as unreachable.
- [ ] **P0**: declared as Poisson, implementation includes ENF; missing support (U(θ, θ+1) takes only a single support).
- [ ] **P0 (k_B)** (phase 3, synthetic ZDC fixture, §17 g4sim preconditions): calibrating only k_B with the scintillation formula downstream (r = 0.5), a P0 configuration that omits the full-simulation spot check at the extreme points of k_B is rejected by `calib_kernel_check.py`; with the spot check, the width bias of re-digitization is detected.
- [ ] **P2**: insufficient observables.
- [ ] **P3**: with only width observables and no photon-source injection, yield × PDE is not identifiable; with a free Fano factor and no single-photoelectron spectrum, Poisson × gain is not identifiable.
- [ ] **P4**: on the subgraph variant, with the known input switched off and only single-photoelectron injection left, yield and PDE are decided as not constrainable.
- [ ] **P5**: q too narrow; the ESS of the mixture proposal at interior points is insufficient; correlated weights make the matrix condition fail; Poisson reweighting is decided infeasible at μ = 1000, and the next-tier method is used automatically; P5 fails when |b_J,i| > 0.15σ_tot,i^design (§8.2 note 3; the linear Gaussian configuration of §8.7 note 4 with MC noise varying with θ, as in en/compute-19-13.md), and the item passes when the noise of the nominal MC does not vary with θ (K_l = 0) (settled by computation, en/compute-19-13.md; to be confirmed by the author). In the mode where the map varies with θ, P5 fails when s_i > 0.25 or κ_i > 0.05 at the worst point (§8.2 note 3, fifth item), computed with Σ_jl = 0 for independent seeds and in the fallback of §6.7 (D28).
- [ ] **P6**: too few design points.
- [ ] **P7**: an alternative hypothesis declared in parameter-shift form such as ν_k = 2 is rejected by the contract checker; with too few validation points the power is insufficient; the power of cross-validation is computed with toys.
- [ ] **P8**: decided as failing when the data's information on the shift-mode φ is c = 0.3.
- [ ] **G1**: limit the number of iterations.
- [ ] **G2**: true value beyond the boundary; when two parameters sit on the boundary at once, the χ̄² reference distribution is used.
- [ ] **G3**: true value outside the feasible region (single-gate isolation mode).
- [ ] **G4**: smoothed histogram density (single-gate isolation mode).
- [ ] **G4-L** (phase 5): no cross-fitting.
- [ ] **G5**: two parameters that appear only as a product.
- [ ] **G6**: the simulation lacks one effect; with a nonlinearity that has cross terms, the linearity check requires switching to a quadratic model.
- [ ] **G7**: with V_MC underestimated by a factor of 3, K = 10, d = 3, detection rate ≥ 0.9. For a fit with only Poisson blocks and MC statistics handled by BB-lite, G7 passes when Σ_MC is computed with the B_m of §6.7; with only A V_MC Aᵀ (Σ_MC = 0), G7 diverges (counterexample).
- [ ] **G8**: a fitter that omits ln det while V_MC changes with θ produces a 0.5σ bias, detected with probability ≥ 0.8.
- [ ] **G9**: decided as failing when Δθ̂ is quadratic or expansive cubic in φ with Δ_i > 0.06, for example Δθ̂ = b(φ + 0.3φ³/6) with |b| = 2σ_tot (Δ_i = 0.17); a compressive response (b(φ − 0.3φ³/6)) passes (settled by computation, en/compute-19-2.md; to be confirmed by the author); condition 1 that holds only at the design stage (θ_ref) and not at θ̂ (with the threshold 1.5c at θ̂) is also decided as failing.
- [ ] **Weight formula (§3.6)**: when S_q is empty and θ′ = θ₀, w ≡ 1; when S_θ∖S_q is non-empty, reweighting and rerun agree.
- [ ] **V**:
  - the formula omitting the cross terms over-rejects, the correct formula does not;
  - when the shift-mode φ counts only the indirect effect, the residual variance is misestimated; when d_l is substituted with the refit ∂β̂/∂φ but with a minus sign, the rejection rate under the null hypothesis deviates from α (§9.2);
  - when the linearity check at the fit point of a cross-validation fold fails, full toys are used instead.

#### 15.3.2 Contract rules

- [ ] In each of the following situations, the contract is rejected:
  - the contract contains data values;
  - observable roles overlap;
  - the dependency graph has a cycle;
  - the simulation side bins by true value;
  - the same model is both enumerated and absorbed;
  - an inference form paired with a non-`holdout` validation;
  - a non-positive-definite kernel function;
  - a block rule is violated;
  - an injection point without a node split;
  - the range of the link function does not match the range of the observable (for example log for a tail probability, log for a signed quantity);
  - the bins of a normalized distribution are declared as scalar observables each using logit, or only K−1 bins are declared;
  - a shape with shared events that must be a Gaussian summary statistic has, at an evaluation point of §2.1, a bin with expected count < n_min (likewise when it holds at the nominal value but not at some prior vertex) and no merging rule, or an evaluation point still fails after merging, or the merging rule is defined by observed counts;
  - an injected reference partway along the chain has no declared conversion relation;
  - a redundant measurement is not declared with a comparison node;
  - an upstream citation does not list its usage; the role written in the contract does not match the role derived from usage (for example written as `variation`, but the η posterior exported by the upstream is used to constrain the downstream).

#### 15.3.3 Data release and sealing

- [ ] A data release lacking the declaration of uncertainty sources → ingestion rejected.
- [ ] The `observed` and `expected` components cannot be read by any script before opening; the `systematic` component can.
- [ ] A calibration observable with only an `observed` statistical error → the contract is rejected.

#### 15.3.4 Declaration of constraints and declaration check

- [ ] A direction with standardized sd 10⁻³ wrongly listed in N_d → the contract is rejected, the validation data are not opened.
- [ ] An exact constraint not declared (C̃_r without rounding has an eigenvalue ≤ τ_num) → the contract is rejected, the validation data are not opened.
- [ ] Two observables with correlation 1 − 10⁻⁷ not declared → the rank condition passes.
- [ ] Declaring linearly dependent constraints (n₃ = n₁ + n₂) → rejected; a correct contract is not wrongly rejected because of noise directions of QR.
- [ ] The prediction of an alternative hypothesis violates an exact constraint → the contract is rejected, not recorded as power.
- [ ] N_d declared with nearly duplicate constraint vectors → rejected: by the SVD check of §5.2 when the standardized singular-value ratio is < 10⁻⁸, otherwise by declaration check (a) or (c).
- [ ] After exclusion, the difference of two nearly perfectly correlated observables makes (c) fail → the contract is rejected; excluding one of them as well → accepted.
- [ ] d = 3, three pairs of calibration observables f_A + f_B = 1 declared as N_d,c → ndf = 6 − 3 − 3 = 0, P2 fails (if wrongly passed, G6 is always p = 1).
- [ ] Mode `none`, calibration observables (p1, p2, t), t = p1 + p2: declared as N_d,c → the likelihood is defined on N_d,c^⊥; not declared → the contract is rejected ((c) or the rounding condition).
- [ ] Cross-validation, observables (p1, p2, t), t = p1 + p2 declared as N_d and all three in the same fold → the training fits of the other folds are computed on N_d,c^⊥, are defined, and (without rounding) give the same result as the fit with t removed; computing directly with V_G⁻¹ without projection serves as the negative control (cond ≈ 10¹⁶).
- [ ] The same set of observables in the calibration data of a holdout → likewise defined.
- [ ] The same set of observables, with data inconsistent in the constraint direction → the contract is rejected at lock time.

#### 15.3.5 Rounding

- [ ] Rounding that does not meet the negligibility condition → the contract is rejected. Including:
  - a calibration or validation observable with efficiency released to two decimal places and σ⁽⁰⁾ = 0.001;
  - a pair of calibration observables, each legal on its own, with correlation 0.999;
  - an observable that violates it only at one end of the prior (for example ε ≥ 0.7).
- [ ] The rounding recomputation at θ̂ fails → `calib_data.py` refuses to open the validation data.
- [ ] An observable t = a + b in significant-digit format (3 digits) whose observed value crosses a decimal boundary → with the last-digit unit of the value actually read as the tolerance, a correct release does not trigger; using the ρ_i of the prediction window as the tolerance serves as the negative control (triggers in about 6% of cases) (the expected rate of this negative control is open: with the §2.1 window maximum the check does not trigger, §9.2; see D73).

#### 15.3.6 Untestable and unused observables

- [ ] Observables (p1, p2, p3, t1, t2), t1 = p1 + p2, t2 = p1 + p3, p1 missing:
  - a holdout contract containing p1 → rejected;
  - excluding p1 and redeclaring N_d on (p2, p3, t1, t2): t1 − p2 − t2 + p3 = 0 holds by construction and must be declared; if omitted, rank condition (c) fails and the contract is rejected (regardless of which basis of the original constraints the contract chose) → accepted after declaration, k = 3, the result lists the unused p1 and the reason (no fraction is computed).
- [ ] A four-bin shape conditioned on the total is missing one bin → the contract redeclares it with the remaining three bins, conditioned on their own sum, redeclares N_decl with the remaining three bins and decides ≥ 10.
- [ ] A K-bin count shape conditioned on the total is missing one bin and is redeclared conditioned on the sum of the remaining bins → accepted, the result lists the unused bin.
- [ ] A K = 2 shape conditioned on the total (or represented in alr/ilr coordinates) with one bin excluded → K′ = 1, the whole shape is not used (§5.2 clause 3 item 5); the same exclusion on an unconditioned absolute count shape → the remaining bin enters as a Poisson count and the excluded bin is listed as unused (§5.2 clause 3, D20).
- [ ] Cross-validation and holdout facing the same kind of missing value → get the same handling (k is also the same when the related observables are in the same fold).
- [ ] In cross-validation, a contract with a calibration observable that has a missing value → rejected; redeclaring N_d after exclusion → accepted.
- [ ] No validation observables after exclusion → P7 and V are `no-testable-direction`, not opened, no record written, grade `calibrated-unvalidated`.
- [ ] (t, p1, p2), t = p1 + p2, σ_p1 = 10⁻⁴σ_p2, ρ_t = ρ_p2 = 0.1σ, p1 missing, cross-validation mode (or holdout with the parameter propagation term negligible in the t − p2 direction) → the contract after excluding p1 is rejected because of the rounding condition of §2.1; additionally not using t → accepted, k = 1 > 0, the grade is not capped because of unused observables (decided by V and power), and the result lists the unused p1, t and the reasons.

#### 15.3.7 Shapes and event samples

- [ ] A free-ω validation shape with N_decl < 10, an absolute count shape with N_exp < 10 → the contract is rejected.
- [ ] A free-ω holdout validation shape with N_decl = 8 → the contract is rejected.
- [ ] N_decl without a recorded basis → rejected by `calib_contract.py check`.
- [ ] A simulation without absolute normalization declared as an absolute count shape → the contract is rejected.
- [ ] `sim_absolute_normalization` missing while declared as an absolute count shape → the contract is rejected.
- [ ] A width summary statistic without a declared 0-event value convention → the contract is rejected.
- [ ] f_A + f_B = 1 declared while the 0-event convention takes f_A = f_B = 0 → the contract is rejected.
- [ ] A free-ω validation shape → takes the toy path already at lock time; the path does not change when N_decl = 50 and N_obs = 3.
- [ ] N_decl = 50 while N_obs = 12 → in the V stage, the power is decided again at N_obs = 12 with the same procedure (lower bound < 0.8 means insufficient power, `calibrated-unvalidated`, not `incomplete`), and the size of T_v is within α ± 25%.
- [ ] With true normalization ω = 0.5, bootstrap conditioned on N_tot,s → the size of T_v with Gaussian summary-statistic shapes is within α ± 25%; generating the bootstrap with ω = 1 serves as the negative control.
- [ ] Particle-gun sample (`sim_absolute_normalization` false), a K = 3 alr shape plus the efficiency N_pass/N_tot of the same batch of events, with a shared bootstrap → when conditioned on N_tot,s, the size of T_v is within α ± 25%, and with an efficiency bias of 3.2σ the power is ≥ 0.6; conditioning on the N_pass of the shape serves as the negative control (rejection rate under the null hypothesis far below α, rejection rate near 0 at an efficiency bias of 6σ).
- [ ] The N_decl,s declared for a holdout calibration sample is not equal to the observed N_tot,s → the contract is rejected.
- [ ] The efficiencies ε1, ε2 of two run periods and the combined efficiency t of both periods, with a model period fraction of 0.45 and a true fraction of 0.5 → when conditioned on the component totals (N1, N2), the size of T_v is within α ± 25%; conditioning only on N1 + N2 serves as the negative control (rejection rate near 1).
- [ ] A free-ω count shape with N_obs = 0 → the direction of that shape is removed and recorded, not `incomplete`.
- [ ] A free-normalization validation event sample with N_tot,s = 0 → the directions of all summary statistics in the sample are removed and recorded, k decreases, not `incomplete`.
- [ ] When the previous item makes k = 0 → `calibrated-unvalidated`.
- [ ] An absolute count shape with N_obs = 0 → enters T_v as usual.
- [ ] N_tot,s > 0 while the N_pass of a summary-statistic shape is 0 → enters T_v as usual.
- [ ] A sample belonging entirely to validation, with two components (400 events each), using ε_1, ε_2 and the combined t of both periods together → the contract is rejected.
- [ ] The same sample using only ε_1, ε_2 → accepted.
- [ ] The same set of observables but the sample contains calibration observables → declaring t = w_1 ε_1 + w_2 ε_2 with known weights as N_d, accepted; the data-side check does not trigger on a correct release.
- [ ] A sample belonging entirely to validation using only ε_2 and t (ε_1 unused, no exact relation) → accepted; at opening N_tot,s = (0, 400) → the collapsed direction t ≡ ε_2 is removed per the rank-deficiency handling, k decreases by 1, not `incomplete`.
- [ ] Using only ε_1, ε_2 while N_tot,s = (0, 400) → the direction of ε_1 is removed per the fallback, k decreases by 1.
- [ ] A three-component sample belonging entirely to validation, using t123, t12 and ε3 together → the contract is rejected.

#### 15.3.8 Cross-validation

- [ ] In cross-validation, the out-of-fold residuals of a count shape are conditioned on the observed total; a plan that assigns the bins of a shape to different folds → rejected.
- [ ] Cross-validation computed with the fold-split statistic T_cv = Σ_f r_fᵀ Ĉ_{r,f}⁺ r_f → in a linear Gaussian toy, the d_θ cross-fold constraints of the overall out-of-fold residuals do not make the rank condition fail, and the size of T_cv is within α ± 25%.
- [ ] A fold split in which the only shape constraining some parameter forms a fold by itself → rejected by `calib_design.py` via P3.
- [ ] A free-ω shape in cross-validation toys → conditioned on the within-fold observed total N_obs of the actual data; conditioning on the toy's own total serves as the negative control (the reference distribution and the observed statistic have different conditioning).
- [ ] The N_decl of cross-validation is not equal to the within-fold observed total → the contract is rejected.
- [ ] In cross-validation, the shape total of some fold is 0 → the contract is rejected at lock time.
- [ ] The data-side constraint check of cross-validation is inconsistent at lock time → the contract is rejected, no failure record.
- [ ] In cross-validation, some fold does not converge or fails G5 on the actual data → V `incomplete`, not `failed`; no validation read and no failure record, the two inputs of C.1 are `none`.
- [ ] G5 fails in 25% of toys → V `incomplete` (changing the fold split is recommended); 10% → after renewing the toys the decision proceeds as usual, not counted in the ratio test.
- [ ] In a cross-validation toy, one fold does not converge and another fold fails G5 → that toy is decided as not converged.
- [ ] In a leave-one-out toy with F = 20, one fold does not converge → that toy is not converged; the ratio test is decided with ε_max,cv = 2%.
- [ ] Cross-validation leave-one-out → ε_max,cv = 2%.

#### 15.3.9 Toys, bootstrap and MC noise

**Bootstrap noise** (phase 2):

- [ ] With p = 50, B = 50p, §7.3 converges within 30 iterations.
- [ ] The false-alarm rate of G7 when the MC is correct is ≤ 2α.
- [ ] The rejection rate of G6 under the null hypothesis is ≤ 1.5α (also holds for p = 100, 200). With only B = 50p and no resampling, the exact size with χ² as the reference at d = 2 is about 0.016 for p = 100 and 0.018 for p = 200; the exact value decreases with d (for p = 100, d ≳ 11 it falls below 1.5α), so the negative control uses only p = 200, d ≤ 6 (exact size ≥ 0.018), with number of toys ≥ 2 × 10⁴, and the decision is a rejection rate significantly > 1.5α.
- [ ] **V_model truncation**: on the toy detector, with a mixed-precision layout (data errors differing by a factor ≥ 5 between observable groups) and model discrepancy ≥ 2× the data error, truncating at 99% of tr V_model alone gives a G6 size clearly above 1.5α. With condition 2 of §5.4 the size is ≤ 1.5α (≥ 10⁴ repetitions) (settled by computation, en/compute-19-3.md; to be confirmed by the author).
- [ ] The toy estimate of Σ_boot has mean bias < 10% and relative standard deviation of the trace ≤ 0.3; when estimated with Asimov it is always 0 (negative control; `calib_design.py` does not accept Asimov as a source of Σ_boot).
- [ ] P5 fails when Σ_boot / w (w per §7.3, with ε̂⁺) exceeds f·Σ_data; negative control: Σ_boot = 0.095 Σ_data with all 60 sets converged (w = 0.891) satisfies Σ_boot ⪯ f·Σ_data but must fail.
- [ ] A plan that reuses bootstrap events by reweighting → rejected by `calib_design.py`.
- [ ] G8 at the standard and full strength levels with 1% non-convergence injected (separately: uncorrelated with coverage, and fully correlated in each of the two directions), with replacement per §7.3 → false alarms ≤ 62 in 1000 repetitions, power detections ≥ 775; negative control: counting non-convergence as not covered, or failing with "observed fraction > 1%", gives clearly excessive false alarms.
- [ ] G7 with K = 10 and 1% injected has false-alarm rate ≤ 2α; failing whenever any set does not converge gives about 0.096 (negative control; 1 − 0.99¹⁰, D26).
- [ ] In a setup with Σ_boot ≲ 0.02 Σ_data, when 0–4 of 60 sets do not converge, P5 does not fail because of it (Σ_boot / w(ε̂⁺) inflates by 12–47%); it fails when the total reaches k* = 5 sets.
- [ ] After λ̂_a is corrected by w(ε̂), under none of the three correlation directions does it overestimate λ by more than 1%; negative control: when corrected instead with the radially truncated χ²_k factor F_{k+2}(χ²_{k,1−ε̂})/(1 − ε̂) (§7.3), with non-convergence truncated along a single direction and k ≥ 2, it overestimates by 3–6%.
- [ ] When 1% of the reference-distribution toys of T_v do not converge, the rejection rate is ≤ 1.1α (≥ 10⁴ repetitions).
- [ ] After Σ_boot is corrected by w(ε̂⁺), at ε = 0.5%, 1% it does not underestimate on average; when corrected with the point estimate ε̂ it underestimates by about 1.1% on average (negative control).
- [ ] V̂ regenerated with common random numbers still agrees with an independently generated one when θ_ref is far from the initial value; one reused by reweighting is about 2.8 times too high in some bin at ESS/N = 0.5 (negative control).

**MC realization of toys and replicas**:

- [ ] On the toy detector whose truth has no MC noise (V_MC/V_data = 0.1, k = 20) → the size of T_v built from replica differences is 0.05 ± 25%.
- [ ] A plan that takes the nominal as the truth and a single replica as the prediction → rejected (the size of the negative control is about 0.025).
- [ ] The correlation of the V_MC model is wrong while the trace is the same → the size of T_v built from replica differences does not change (the V_MC model is not read).
- [ ] Poisson small-count bins → the MC auxiliary measurement is sampled with the Poisson(τγ̃) of BB-lite (γ̃ = γ̂ for toys under the null hypothesis, the profiled value for interval toys, §6.6).
- [ ] A plan in which the toy MC only changes Philox and re-digitizes → rejected by `calib_design.py`.
- [ ] Toy MC estimate of a non-Gaussian block → centered on γ̃Σw (f = m*/τ).
- [ ] At the P5 limit V_MC = 0.1V_data, ndf = 100, the locally linear toys of G6 with replica-difference MC noise → size within α ± 50%; without MC noise as the negative control (size clearly outside α ± 50%).
- [ ] In shift mode the toys sample φ from the prior, and Ĉ_r contains Σ_l d_l d_lᵀ; φ fixed at the nominal value serves as the negative control.
- [ ] Toys of each cross-validation fold → freeze each fold's own V̂_f.

**Construction of the G8 closure test**:

- [ ] In a toy with V_MC/V_data = 1 (outside the P5 range, only to test sensitivity) and N_c taken as the maximum of the §8.4 table, with the G8 truth taken as the toy's known analytic truth (not a 100× truth MC) → the detection rate of G8 for V_MC underestimated by a factor of 2 is higher than the detection rate of the construction that samples pseudo-data from the likelihood model (the latter is about α, negative control); when V_MC is correct, the false-alarm rate computed with the decision rule is ≤ α_G8 × 1.25.
- [ ] A plan that declares running G8 while the pseudo-data share the fit MC → rejected by `calib_design.py`.

**Intervals**:

- [ ] Interval toys → truth at the scan point (not at θ̂), ν and η take the profile values at the scan point.
- [ ] Profile scan points computed with the V of the nominal fit → q(θ) is continuous where the binning of V̂ jumps.
- [ ] An interval calibrated with toys generated with frozen V̂ and event-level noise → Σ_boot / w is not added again (adding it makes the half-width about 1% larger, negative control); the profile interval adds it.

#### 15.3.10 Power

- [ ] **P7 (unbiased)**: for an alternative hypothesis with true value λ = 12.8, the mean of the cross-product estimate is within 12.8 ± 2%; a single-set MC estimate is biased high.
- [ ] The alternative shift δ̂_a of the power toys carries MC noise → the unscaled rejection rate is biased high.
- [ ] Power toys scaled by the point estimate of λ̂_a^cross while the true power is 0.75 → the frequency of claiming a lower bound ≥ 0.8 is higher than 5% (negative control); with a one-sided lower bound and Bonferroni allocation it is ≤ 5%.
- [ ] The ratio test of the P7 power toys fails → P7 `incomplete` (same as in the V stage), redone by `calib_design.py` with the next seed block.
- [ ] A holdout where the T_v decision fails and the power lower bound cannot be computed (no second independent MC set) → V fails, record `final`, grade `calibrated-unvalidated`, not `incomplete`.
- [ ] No second independent MC set (power lower bound cannot be computed) while T_v already exceeds the critical value → V fails (not `incomplete`, §9.4), the provisional failure record written at opening is changed to `final`; afterwards cross-validation with a new κ on the same batch of calibration data → `calibrated-unvalidated`.
- [ ] T_v passes, power lower bound cannot be computed → `incomplete`; after `calib_validate.py abandon-power` it is `calibrated-unvalidated`, and the record stays `withdrawn`; afterwards power records of that κ are rejected.
- [ ] T_cv passes, the ratio test of the power toys keeps failing → `abandon-power` is accepted.

#### 15.3.11 Opening preconditions

- [ ] A κ whose calibration-data lineage is not confirmed → the validation data are not opened, no validation read and no failure record, result `incomplete`.
- [ ] P7 is `incomplete` → the validation data are not opened.
- [ ] k₀ > 0 while the toy replicas could not be generated because of insufficient budget → V is `incomplete`, the validation data are not opened, the two inputs of C.1 are `none`.
- [ ] k₀ = 0 and no toys → `no-testable-direction`, not `incomplete`. When k₀ > 0 and k = 0 only after opening because N_obs = 0, it is handled per the k = 0 handling of §9.5.
- [ ] A κ for which k₀ = 0 is determined before opening, or whose lineage is not confirmed → no validation read, the two inputs of C.1, failure record and reuse, are `none`.
- [ ] The ratio test of the reference toys before opening fails → not opened, `incomplete`.
- [ ] The ratio test before opening fails, and passes after a summed redo with the next seed block → opened as usual.

#### 15.3.12 Outcome already determined

- [ ] The effective grade of a central upstream is `failed`, some mandatory gate of this result is `incomplete` → the lookup gives `failed` under every possible outcome, the outcome is already determined, `failed`, not opened.
- [ ] A mandatory gate is `incomplete` and the outcome is not yet determined → not opened, `incomplete`.
- [ ] A mandatory gate is `incomplete` while the calibration data come from simulation → the lookups differ (`failed` and `projection`), the result is `incomplete`.
- [ ] Calibration data come from simulation → not opened, V `not-applicable`, `projection`.
- [ ] Calibration data come from simulation while P7 is `incomplete` → `projection`.
- [ ] k₀ = 0 determined before opening while lineage is not confirmed → outcome already determined, not opened, `calibrated-unvalidated` (not `incomplete`).
- [ ] Carries `closure-not-tested` itself while the toy replicas have not been generated → not opened, `calibrated-unvalidated`.
- [ ] P7 power insufficient → not opened, `calibrated-unvalidated`.
- [ ] In holdout, P7 power lower bound 0.6 → not opened, V `not-applicable`, `calibrated-unvalidated` (not `incomplete`), even if lineage is not confirmed or the toy replicas have not been generated.
- [ ] P7 lower bound 0.6 under one alternative hypothesis, and not computable under another → P7 decides that the power is insufficient, not opened.
- [ ] Cross-validation κ1 has P7 lower bound 0.6 → T_cv is not computed, no validation read and no record, κ1 is `calibrated-unvalidated`; afterwards κ2 on the same batch of calibration units (power sufficient, T_cv passes) is not capped because of κ1, and can be `validated-in-scope`.
- [ ] The lookup is tested exhaustively (D63, D13): for every own input combination of the test scope of Appendix C with at least one input not yet decided, with and without a capped central upstream, the result of `calib_use.py` equals an independently written enumeration that evaluates C.2 then C.3 for each combination of possible outcomes; a mutant that looks up C.2 only opens the data when a capped upstream already determines the outcome, and is caught.

#### 15.3.13 Validation reads and holdout eligibility

- [ ] After the validation data are read by version 1, the following four cases are all `calibrated-unvalidated`; recomputation with the same κ is not affected:
  - version 2 passes again on the same data;
  - version 2 changes only the plan;
  - version 2 only upgrades the engine version;
  - version 2 switches to cross-validation and merges those data into the calibration data.
- [ ] Role swap: κ1 calibrates with X, holds out Y and fails; κ2 calibrates with Y:
  - κ2 holds out X: X was fit-read by κ1 → κ2 is `calibrated-unvalidated`;
  - κ2 instead holds out Z, which has never been read → not restricted;
  - κ2 instead cross-validates on X alone (X is then κ2's only calibration data) → `calibrated-unvalidated` per the failure-record rule (3f: κ1's `final` record on X);
  - κ2 also declares X as calibration data and holds out a unit that shares events with X → the contract is rejected at lock time (a holdout must not share events).
- [ ] Contract C calibrates with R_c and holds out R_v, which shares events with R_c (whether or not the sharing is declared) → the contract is rejected (declared sharing is rejected at lock time; undeclared sharing found by lineage comparison is rejected at lock time or before opening the holdout), exit code 2, no validation read.
- [ ] κ2 holds out a release that shares raw units with its own calibration release → the contract is rejected at lock time, no validation read, `fit-pending` does not appear.
- [ ] The holdout validation observable t (combined efficiency of two periods) shares events with the calibration observables ε_1, ε_2 → the contract is rejected at lock time; accepted after switching to cross-validation, with the `cv` flag.
- [ ] Calibration release of 1000 events, validation release of 800 events, overlap 300, and the validation summary statistic with shared events is taken from a sample containing 500 events that belong only to validation → the contract is rejected; after changing to take it only from events of the calibration release, it is still rejected in holdout because the two releases share raw units, and can only switch to cross-validation; accepted in cross-validation, with N_tot,s checked before the lock.

#### 15.3.14 Failure records

**State transitions and abandonment**:

- [ ] After κ1 is abandoned with `calib_validate.py abandon` → the record is `final`.
- [ ] κ1 submits a passing decision record after declaring abandonment → rejected by `calib_validate.py`, the record stays `final`, and κ1's own V is recorded as failed.
- [ ] Declaring abandonment after a passing decision (record is `withdrawn`) → rejected, the record stays `withdrawn`, and the cross-validation results of other κ are not affected.
- [ ] k = 0 → V is `no-testable-direction`, no power lower bound is needed, grade `calibrated-unvalidated` (not `incomplete`).
- [ ] The only validation shape (conditioned on the total) has N_obs = 0, making k = 0 → record `withdrawn`, grade `calibrated-unvalidated`.
- [ ] k = 0 while the data-side constraint check triggers → record `final`.
- [ ] A validation observable that the release declares as having a value has no value at opening → treated as a corrupted release, V fails, record `final`.
- [ ] After opening, the data-side constraint check triggers and regenerating the toys also fails → V fails, record `final` (not `pending`).
- [ ] After opening, the data-side check does not trigger while regenerating the toys fails → `incomplete`, record `pending`.

**Effects across κ (cross-validation)**:

- [ ] After a holdout validation fails, a new contract series without the previous-version hash is started and cross-validates on the same batch of calibration data → because the failure record is attached to the raw units, the grade is `calibrated-unvalidated`.
- [ ] A failure record later than the first validation read of some result κ → that result is not affected.
- [ ] Interleaving: κ1 opens the holdout at sequence number 1, κ2 first computes T_cv on the same calibration data at sequence number 2, the decision of κ1 fails at sequence number 3 → the failure record's sequence number is 1 (the sequence number of opening), κ2 is `incomplete` before sequence number 3 and `calibrated-unvalidated` after it.
- [ ] Reverse: κ2 first computes T_cv at sequence number 1, κ1 opens at sequence number 2 and its decision fails at sequence number 3 → κ2 is not restricted, but its result lists this failure record.
- [ ] When the decision of κ1 passes the record is changed to `withdrawn` → κ2 is not affected.
- [ ] Events of different κ with the same sequence number → the failure is treated as earlier.
- [ ] κ1 opens the holdout and then does not run the toy calibration of T_v (decision not complete), and κ2 subsequently cross-validates on the same batch of calibration data → κ2 is `incomplete`; after κ1 abandons or its decision fails, κ2 is `calibrated-unvalidated`; after the decision of κ1 passes, κ2 is not restricted.
- [ ] κ1 has opened the holdout and not yet decided → a design study in mode `none` on the same batch of calibration data is still `projection`; results in mode `holdout` on new units are not affected.
- [ ] κ1 already `final`, κ3 still `pending` → κ2 is `calibrated-unvalidated`.
- [ ] κ1 still `pending`, κ2 cross-validates on the same batch of calibration data and V fails → κ2 is directly `calibrated-unvalidated` (not `incomplete`).
- [ ] In cross-validation (the validation data are the calibration data already read), reads via the calibration release and failure records of other κ are decided as follows:
  - a fit read via the calibration release does not cap the result (Appendix C I22);
  - a `pending` record of another κ earlier than this result's first validation read → `incomplete`; after it becomes `withdrawn`, not restricted; after it becomes `final`, `calibrated-unvalidated` (the grade does not depend on timing);
  - calibration data come from simulation → not opened (V `not-applicable`, §10.2 rule 0), `projection`;
  - V fails, or a central upstream with effective grade `calibrated-unvalidated` is used as the φ center, or it carries `outside-validated-range` itself → the effective grade is directly `calibrated-unvalidated`, with the same uses as under `final` (none of them is `incomplete`);
  - a record later than this result's first validation read → not affected.
- [ ] An upstream that has a `pending` input but a common result, re-judged after the record is resolved → the downstream is not marked as needing a redo.

#### 15.3.15 Grade rules

The grade rules are enumerated exhaustively by the decision table of Appendix C, plus the following named cases:

- [ ] A result whose validation failed → `calibrated-unvalidated`, not `failed`.
- [ ] Validation mode `none`, intended_use has only design uses → `projection`, P7 is not run, it is not decided `failed`.
- [ ] P7 fails in the final version, all other gates pass → `calibrated-unvalidated`.
- [ ] G8 fails in holdout mode → grade is `failed`, stages D–F are recorded as `not-applicable` (not `incomplete`), the validation data are not opened.
- [ ] A `calibrated-unvalidated` upstream cited only as an envelope → does not lower the downstream's grade; but when it carries `provisional-thresholds`, the downstream also carries this flag and cannot be used as the basis for formal publication.

#### 15.3.16 Applicability conditions of mandatory gates

- [ ] A plan using only full resimulation, with no surrogate model, reweighting, deterministic rerun or re-digitization → P0, P6, G4, G4-L are recorded as `not-applicable`, and the result can obtain a grade.
- [ ] A plan evaluated only with a surrogate model, with all other nodes evaluated with `resample` → P0 `not-applicable`, P6 applicable.
- [ ] A plan using only step-level reweighting → both P0 and G4 apply.
- [ ] G5 → always applicable.
- [ ] 20 held-out points → P6 decides only the |Δm| part.
- [ ] Synthetic ZDC calibrating only k_B (rerun) and r (re-digitization) → P0 applies, and includes the spot check at the two extreme points of k_B.
- [ ] Synthetic ZDC calibrating only k_B, with the k_B node evaluated by a surrogate model and no other node using the methods enumerated in §8.1 → P0 `not-applicable`, the spot check at the k_B extreme points is run by P6; when the fixture also includes re-digitization of r, P0 applies.
- [ ] Evaluating the k_B node with a surrogate model → the held-out points of P6 include the two extreme points of k_B.

#### 15.3.17 Propagation and use

- [ ] **Propagation (central)**:
  - Single η: when the upstream exports (η̂, Σ_η), the segmented calibration and the joint fit agree in central value and variance; when the prior N(0,1) is substituted, this test fails (counterexample).
  - Correlated η and shared φ (toy detector, §15.1): when exported with the joint posterior (ζ̂, Σ_ζζ) and the joint regression G_ζ, the segmented calibration and the joint fit agree; when using instead two marginal regressions, each constraining independently, this test fails (counterexample).
- [ ] **Propagation**:
  - citing numbers instead of hashes is rejected;
  - when two results update the same shared nuisance with different versions, a joint fit is required;
  - when the source sets of uncertainty objects intersect, a joint fit is required; all four shapes must be tested:
    - sibling: the ζ versions of two downstreams both take the ξ of the same upstream as central input;
    - triangle: ξ_U and the version updated by a result that has U as a `central` upstream;
    - ξ and ξ: the ξ of two results that have the same upstream as `central`;
    - parent-child: the ξ of upstream R1 and of R2 that has R1 as a `central` upstream (in the counterexample the correlation is −0.707; treating them as independent gives Var(θ₁+θ₂) = 3, the correct value is 1);
  - the θ and ν of an upstream must not be exported separately.
- [ ] **Use**:
  - `projection` used for a production correction is rejected;
  - `failed` plus `outside-validated-range` is still `failed`;
  - `closure-not-tested` keeps the grade at `calibrated-unvalidated`;
  - grade-limiting flags propagate only from `central` upstreams, as a union; those of `variation` upstreams are listed in `variation_flags`; use-limiting flags (`preliminary`, `provisional-thresholds`) propagate from all upstreams.

#### 15.3.18 Other components

- [ ] **Redundant measurements** (P4 tested in phase 0 on the tracker and ECAL fixtures, P3 tested in phase 2 on the toy detector): overlapping layers (position difference of two hits) and overlapping modules (energy ratio of the same shower) are each declared with a comparison node.
  - P4: the alignment and gain of both modules are decided as "possibly constrained" (reachability is only a necessary condition).
  - P3: the position difference constrains the relative alignment, not the common shift; the energy ratio constrains the relative gain, not the common gain scale; the common mode is decided as not identifiable, with a "common mode of redundant measurements" hint.
- [ ] **Contribution decomposition**: when some actually evaluated subset does not reach the ESS threshold, no decomposition is output.
- [ ] **Partial pooling** (phase 5): when the truth is the same in all segments, τ̂ returns to 0.

#### 15.3.19 g4sim binding

From phase 3, under the g4sim preconditions of §17; the `build_hash` item is in phase 4. In each of the following situations, it is rejected or decided:

- [ ] Node 0 uses an `external` source → rejected by the contract checker.
- [ ] A model lacks one of the five identity items of §5.1 → rejected.
- [ ] Two physics lists without a confirmation record that they "actually use different models", used as enumerated models or alternative hypotheses → rejected.
- [ ] A node to be reweighted is recorded only as `moments` → decided infeasible.
- [ ] The run card's `kill_policy` sets a minimum kinetic energy, while some observable depends on particles below this kinetic energy (for example efficiency near threshold) → that node is decided as missing support. The case of a time cut earlier than the scorer time window is already rejected by g4sim's check-spec and does not need to be tested in this workflow.
- [ ] A plan that declares running G8 while the fit MC of the pseudo-data only changes the Philox replica and shares Geant4 events → rejected by `calib_design.py`; when the plan declares not running G8 → `closure-not-tested` is added to the result.
- [ ] The two MC sets of P7 share Geant4 events of the nominal model → rejected by `calib_design.py`.
- [ ] Declaring an injection reference with a known photon count between light collection and PDE on the efficiency-map path (ε_c not split) → rejected.
- [ ] PDE split (§6.7): a declared PDE parameter that also changes a reflectance, transmittance or refractive index, an angle-dependent PDE, or a sensor surface of the efficiency-1 map with `efficiency` ≠ 1 → rejected by `calib_contract.py`; a PDE(E) declared as a constant scale of the efficiency-1 map → rejected by `calib_contract.py`; a split check that fails (χ² at α = 0.01, or |Δθ_i| + 2 sd(Δθ_i) > 0.1σ_tot,i^design for some θ_i), a split-check pair whose detections are not nested, a split-check pair with different seeds or event intervals, route 3 without the mapping run's `photons.csv` or with a `photons.csv` whose detections do not equal the map's counts, a route-3 grid whose pseudo-mass per bin exceeds 0.01 n_b or whose analytic Dirichlet variance is < 0.98 of the multinomial variance, route 2₁ for a readout system with an observable not linear in ε while p is θ, a route-1 thinning after dark counts, cross-talk or saturation, as a charge or code scale or on a stream named `efficiency_map/<k>`, a workflow key (`calib-map-joint/1`, `calib-map-pde/1` or route 1) equal to another or to a `response.study_keys` key, and a PDE prior that reaches 0 on a surface model with the `EFFICIENCY > 0` test → rejected by `calib_design.py` (remedy level: plan); a split-check pair sharing its seed and interval → not flagged as an overlap by §6.6; a declared PDE(E) that is 0 at an emitted energy on a surface model with the `EFFICIENCY > 0` test (synthetic surface declaration), or a fixed efficiency-1 map whose `surfaces_sha256` is not g4sim's hash of the production surfaces with the sensor `efficiency` entries set to 1 → rejected by `calib_contract.py` (for the maps of a θ scan, by `calib_design.py`).
- [ ] Map varies with θ: under the shared seed, the map term uses g4sim's per-map replicas propagated through the surrogate model as independent, or replicas coupled across design points by common uniforms or by one g4sim key for the scan; or coupled replicas with independent seeds; or a surrogate model that interpolates the design points exactly → rejected by `calib_design.py` (remedy level: plan) (§6.7, D28).
- [ ] A plan that declares the shared seed for a θ scan whose mapping runs' `primaries.csv` do not agree event by event → rejected by `calib_design.py` (§6.7, D28).
- [ ] A `g4sim-digi-job/1` whose `run_seed` was changed without recomputing its keys, or with `replica` ≠ 0, or carrying both `keys` and `conditions`, or whose stage, sensor, electronics, timing, channels or efficiencies differ from the hashed documents → rejected by `calib_design.py` (§5.1, §6.6).
- [ ] An exported `condition-snapshot/1` or `alignment-overlay/1` without the calibration result's hash in `source_of_facts` → rejected by `calib_use.py` (§10.4).
- [ ] Fixed-map mode: the linear construction U = J B_map used for an observable that the plan does not record as linear in ε → rejected by `calib_design.py` (remedy level: plan) (§6.7).
- [ ] Scintillation `log_density` switched to the normal density → P0 fails.
- [ ] After `build_hash` changes → the result is marked as needing a redo.
- [ ] g4sim output used as the **calibration** data release → grade is `projection`; only the **validation** data release is g4sim output → grade is `calibrated-unvalidated` (rule 3). These two items can be tested from phase 0 and do not need g4sim.

### 15.3a Regression cases (engine implementation pending)

- The ξ and matching ζ of the same upstream package must be accepted; sibling, triangle and parent-child correlations across packages must still be caught; the constraint of the same version must not be multiplied in more than once.
- Two packages with no result-dependency edge, but using the same raw events or the same external measurement, must not be treated as independent on the grounds that their source sets are disjoint.
- For the same efficiency map in two studies with opposite observable order, the cross-covariance after propagation must equal the result from the native common basis; connecting separate PCAs by the same index must be rejected.
- Raw validation data whose hash changes after a metadata change, reordering, rebinning or format conversion still must not be upgraded by a new κ; with no usable lineage it cannot be decided as passing.
- Mixed Poisson/binomial validation must not use the Gaussian A directly; check the nominal rejection rate with full toys. Degenerate residuals compute the degrees of freedom as k = dim N_d^⊥ (N_d is declared by the contract, not decided by numerical rank; the only exception is the removal of directions after opening per §2.1).
- Bayesian MCMC output must be labeled as a credible interval and cannot pass a frequentist coverage claim; a non-Gaussian export does not claim equivalence to the joint fit.
- The same efficiency center but different pass/fail MC effective counts must give different MC uncertainties.
- The rank-one case of G7 uses K−1 degrees of freedom; a non-zero spread inside the null space must be decided as failing.
- When the shift φ are correlated, whiten first or switch to profile; a zero response must not trigger division by zero.
- When the true power is slightly below 0.8 and the point estimate is above 0.8 but the lower bound is insufficient, P7/V fails, and the grade is `calibrated-unvalidated`. When the T_v decision passes, and there is neither a second independent MC set nor a way to estimate the V_Δ of the single-set estimate, it is recorded as `incomplete`, and no grade is assigned until the gap is filled or power abandonment is declared (then `calibrated-unvalidated`). When T_v fails, no lower bound is needed, and V fails.
- A model template keeps its identity when θ, φ and their derived fields change; it must change identity when non-parametric physics settings change; versions and result hashes can be rebuilt in acyclic order.

Sole owners of the rules above (§14):

- `calib_data`: data lineage, validation reads and failure records on raw units;
- `calib_deps`: propagation packages and common sources;
- `calib_propagate`: efficiency-map native bases and summaries;
- `calib_validate`: general response, toys and the **power lower bound** (`calib_design` calls the same implementation in P7);
- `calib_use`: `incomplete` aggregation of rule 0 and grades;
- `calib_interval`: inference flags;
- `calib_fit`: the rank of G7;
- `calib_likelihood`: pass/fail summaries of weighted MC (phase 2);
- `calib_contract`: model templates.

Each case is acceptance-tested in the phase in which its owning script is delivered (§17):

- Phase 0: lineage, failure records, acyclic ids, `incomplete` aggregation;
- Phase 2: inference flags, G7 rank, general response, power lower bound, propagation packages, pass/fail summaries of weighted MC;
- Phase 3: efficiency-map basis and g4sim model identity.

### 15.4 Review obligation template

- The contract is locked before the validation data are opened, and the commitment hash matches.
- Injection points have node splits.
- Every pipeline stage's gates have results, and the remedy level is recorded.
- The alternative hypotheses are outside the null model, and P7 passes.
- Downstreams cite by hash and ξ version.
- Grades and flags are inherited correctly.
- All contract versions are listed.

---

## 16. Comparison with the ZDC ECAL study

| Problem in the ZDC study | Mechanism that stops it | Concrete implementation with g4sim |
| --- | --- | --- |
| The linearity already deviates from a straight line by 3.5% on data | A0 | — |
| σ_p stays at the spread used at generation | G3; reference-point iteration | The generation distribution is the request's source; its truncation range is the support (§6.1) |
| Impact points fall outside the generation box; division by a smoothed density | §6.1; P0; G4 | The density is given analytically by `source-density/1`, no longer estimated by histogram smoothing; an `external` source is rejected |
| Minuit not converged | G1 | — |
| η sits at its upper bound, the offset sits at 8 mm | G2 (two constraints act at the same time; uses χ̄²) and G3, both run in the same stage | — |
| "New statistics" are resampled from the same events used in the fit | §6.6 | New statistics must be a non-overlapping global event interval; `calib_design.py` checks this with `run_id` and the event interval |
| The DSCB fit-window convention is not validated | `estimators` | — |
| Phase 4–6 use a different parameter set | Hash references | Parameters point to the calibration result hash through `source_of_facts`; simulations are identified by `geometry_id` and `run_id` (§10.4) |
| The waterfall-plot steps have only 103–316 effective events | §10.5 | — |

At the design stage, four further points come up:

- **Three-stage binomial thinning chain**: light yield, longitudinal light collection η and PDE form a three-stage binomial thinning chain.
  - Per §3.5, separating them fully needs **two** intermediate injection points (each between two adjacent stages, injecting a reference with a known photon number, for example a calibrated LED intensity), plus a known input at the top of the chain (the beam energy).
  - The single-photoelectron spectrum can only constrain the gain and the nodes after it.
  - On the g4sim efficiency-map path, η and PDE appear in the efficiency map only as a product (§11.4), so an injection point between them cannot be declared; the two can only be merged into one parameter, or separated on the full optical-tracking path (or under the PDE split of §6.7, which makes the injection point declarable).
- **The validation mode** is `cross-validation`. P7 points out already at the design stage: with too few energy points, the declared alternative hypothesis cannot be detected.
- **φ at the resimulation level** (for example the wrapping thickness): use shift mode when the conditions of §5.5 hold; otherwise a surrogate model is needed (implementation phase 3).
- **Longitudinal light collection η(z)** is given by the g4sim efficiency map (S7); the statistical error of the efficiency map itself enters as a shared φ (§6.7). The 0.07–0.31 for η in the ZDC study is a spread over assumed optical constants; it belongs to the model ensemble or to the size of φ, not to the statistical error of the efficiency map.

**What this workflow does not stop**:

- in the ZDC study, data points D2–D10 (the study's own labels) lack raw data;
- wrong geometry facts (g4sim's `source_of_facts` makes every geometry value traceable to a source, but judging whether the source is correct is not this workflow's job);
- unknown optical constants (g4sim S7 does not require a source for optical properties: only `rindex` is required, and `facts` and `source_of_facts` are optional; unknown constants can only be listed as φ or as discrete models).

---

## 17. Phased implementation roadmap

Each phase runs acceptance tests only on what it delivers itself. The concrete division of work:

- The cases in §15.3 that depend on `calib_validate.py` behavior (in §15.3.14, "submitting a decision record after abandonment is rejected" and "abandoning after the decision passes is rejected") are acceptance-tested in phase 2; phase 0 acceptance-tests only the grade function, using hand-written decision-record stubs.
- Locking-stage checks that need quantities produced by the model are added in phase 2 (after the joint likelihood and the design-stage Asimov are delivered):
  - the rounding-negligibility condition of §2.1, N_decl/N_exp of validation shapes, the n_min lower bound of shape summary statistics and the block-conversion condition are all computed by `calib_data.py` and called by `calib_contract.py check`;
  - Σ_boot of P5 and the b_J item of P5 (§8.2 note 3; it needs K_l from the design-stage MC) are decided by `calib_design.py`.
  - The phase-0 `calib_contract.py check` does not contain these rules; it only checks that the declarations exist.
- In phase 0, the failure-record state transitions are tested with hand-written decision-record stubs; `calib_validate.py` is retested with real decision records after it is delivered in phase 2.

| Phase | Content | Gate |
| --- | --- | --- |
| 0 Abstract model and contracts | Seven schemas; the DAG format, injection-point splitting, three fixtures (ECAL, RICH, tracker; ECAL and tracker each contain a pair of overlapping modules, for tests of redundant measurements); the **graph structure** of the toy detector and subgraph variants (DAG only, no simulation); `calib_chain` (candidate methods, P4); contract, data release and plan schemas; `calib_contract check`; in `calib_deps`, hash references, cycle checks and derivation of upstream roles from usage; `calib_use` (per the decision table of Appendix C, including the `incomplete` of rule 0); in `calib_data`, raw-unit lineage, validation-read and fit-read events (including registration of read channels and contract drafts), failure records (`pending`/`final`/`withdrawn`), and derivation of the reuse input (Appendix C.1); acyclic computation of version ids | The negative tests of the contract, use and grade rules (the exhaustive tests of Appendix C and the named cases of §15.3) and of P4 pass; the three fixtures can derive candidate methods and reachability |
| 1 Evaluation and design stage | Analytic and step-level reweighting (including the support and mixture formulas), rerun, `resample`, `evaluate_from`; the linearized fit operator A for Gaussian blocks (for the design stage; ν and η are included as linear nuisance columns u_k, s_j with N(0,1) constraints, so σ_tot^design already contains their contribution in this phase and does not need to wait for the full likelihood of phase 2); A0, P0, P2, P5 (including feasibility and the final method), the surrogate-interface stub of P6; simulation of the toy detector | The negative tests of A0, P0, P2, P5 pass; reweighting and rerun agree |
| 2 Engine and validation | Joint likelihood (link functions, ν, η); reference-point iteration; `calib_interval`; P3, P7; G1–G8 (except G4-L); locally linear toys and the linearity check; validation (holdout, cross-validation, power); generation of toy replicas and the independence check (for non-g4sim evaluators decided by non-repeating seeds; the g4sim event-interval check is added in phase 3); both modes of φ; the model ensemble of V_model and the correlation-kernel components; propagation of the principal components of the joint posterior and ξ versions | The negative tests of P3, P7, G1–G8, V and propagation pass; segmented calibration and the joint fit agree (all of the above on the toy detector); the negative tests of P8, G9 |
| 3 Surrogate model and g4sim evaluator | ask/tell, P6, V_emu, the combination of resimulation and surrogate model; `g4sim_calib_eval.py` (§7.1); the node binding and candidate-method derivation of §11.4; the g4sim support and recording-level checks of §6.1; the event-interval check of §6.6; the efficiency-map φ of §6.7 (after g4sim S7 is merged), with, in the mode where the map varies with θ, the seeds of the mapping runs, the joint-pattern replicas, the map term U(θ)φ_map and the θ-noise item of P5 (D28); the PDE split of §6.7 (routes 2₁, 3 and 1, the split check with its nested pair, the route-3 replicas; decided by the author on 2026-11-10) | P6 negative tests; G8 passes for the three-method combination; g4sim positive tests on the synthetic ZDC fixture (§15.2); can handle the response-layer parameters of ZDC Phase 3 and φ at the resimulation level (φ must satisfy §5.5, otherwise use a surrogate model); with light-collection parameters, g4sim S7 is also needed |
| 4 Dependency graph and specialization | Upstream invalidation (including a change of simulation identity, §10.3), conditions-database export (g4sim conditions snapshot), feedback into g4sim (§10.4); `calib_contrib`; eight specialization documents (each with a node-binding example per §11.4); the hep-detector domain card | Negative tests of the contribution decomposition and the g4sim binding (§15.3); specialization does not require modifying the generic layer |
| 5 Extensions | Partial pooling; learned density ratios and G4-L; the inference form of V_model (marginal likelihood) | The corresponding negative tests pass; the gates of the first four phases are not changed |

**g4sim preconditions**:

- Phases 0–2 of this workflow use only the toy detector and do not depend on g4sim.
- An item that uses g4sim may start only after the corresponding g4sim stage is **merged** (`merged` in the g4sim status file).
- When a g4sim stage that is `partially-complete` is the precondition, the gaps of that stage must not be gates this item depends on.

| Item of this workflow | Required g4sim stage | Deliverable |
| --- | --- | --- |
| The g4sim model identity of `calib_contract` (the masked hash of §5.1) and its acceptance (§15.3a) | S1 (schemas and read procedures of the three specifications), S4 (`response-pipeline/1`); it is added to the checker in phase 3; the phase-0 checker does not contain this rule | specification schemas, `core/canonical` |
| Integration tests for node-0 reweighting and the `external` rejection | S3 (`source-density/1`), S4 (`external` source) | source density; `external` read |
| Birks deterministic rerun (`edep_by_dedx_class`) | S3 | `edep_by_dedx_class` |
| Re-digitization of response parameters, common random numbers, event intervals | S4; S8 for the digitization-job path (§6.6) | hit, `response.py`, Philox, `edep_visible_ly_split`, `event_file`; from S8, `digitize.py`, `g4sim-digi-job/1` and `g4sim_digi` |
| Synthetic ZDC fixture | S3 (examples), S5 (calorimeter kit, optional) | ZDC specification |
| Efficiency-map φ, light-collection parameters, RICH replica fixture | S7 (mapping runs; for route 3 of the PDE split, with `photons.csv`), S8 (digitization job, for joint-pattern replicas, for U in the fixed-map mode and for the PDE split of §6.7) | efficiency map, Dirichlet replica, optics |
| Simulated geometry misalignment, conditions-snapshot export | S9 (merged, hep-research 0.65.0) | `alignment-overlay/1`, `condition-snapshot/1`, `g4sim_run.py diff` and `--overlay` |

S9 is merged, so the conditions-database export of phase 4 writes `condition-snapshot/1` and `alignment-overlay/1` documents (§10.4); a misaligned geometry can enter phase 3 or 4 only once a recorded run can apply the overlay (§19, C25) (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md).

## 18. Summary of design decisions

This section explains **why** the current design is the way it is, organized by topic. For each topic it states first the current approach, then the rationale, and last the alternative approaches not adopted and why they are not adopted. The rules themselves are as stated in the body sections; this section only explains.

**Common method**: when the same rule was patched over several successive rounds and each patch produced a new edge case, this design does not add further conditions; it pulls back the scope and uses a smaller design that holds on its own and needs no separate further validation. The power of the null space, the rounding rule, the release-side mislabel check, the handling of non-convergence, N_d reduction and the bookkeeping of the testable fraction were all handled this way.

### 18.1 Likelihood and link functions

- **Correlated systematic errors** are represented by the nuisance η, which acts on all blocks (§2.1), to handle the Peelle problem and systematic errors across blocks.
- **The link function is chosen by range** (log, identity, logit, Fisher z; §2.1, §3.3), to handle out-of-range values. Correlation kernels are indexed by (observable group, link function) (§5.4), consistent with choosing by range; the formulation "one fixed link per functional class" is not adopted, because it contradicts the rule of choosing by range.
- **The simplex** is handled with the alr/ilr vector links; ν and η act on the K − 1 dimensional coordinates. Per-component logit is not adopted: after one component is dropped, per-component logit yields a negative component.
- **alr/ilr act only on the prediction side**; the data side defaults to a count likelihood (Poisson, free normalization). alr is not taken on the data side, because it is undefined for zero counts, and at low counts the delta method also underestimates by about 20%.
- **The conditions for using a Gaussian summary statistic are decided only at lock time** (expectation per bin ≥ n_min, taking the worst over the evaluation points), without looking at observed counts; otherwise the data would decide K, the merging and the rejection. The estimator always computes all K bins with n_k + ½, and the covariance uses a parametric bootstrap at θ_ref. Bootstrapping from observed counts is not done, because the probability of a replicate having a zero bin would be underestimated by three orders of magnitude, and some datasets would get −∞. The prediction side must not normalize the MC first and then add ½, because that bias does not cancel in the residual.
- **Errors are not decided by the observed data**: count-type errors are always computed from the predicted expectation; each uncertainty component of a release declares its source (`observed`/`expected`/`systematic`), and `observed` and `expected` are sealed together with the observed values. The rationale is that an uncertainty table computed from observed counts equals the data itself, and reading it before opening is an unrecorded validation read.
- **Source labeling is the publisher's responsibility**, listed as an applicability precondition (§2.1, §19). An automatic mislabel check at opening is not adopted: it repeatedly misfires on legitimate constant tables, smooth integer tables and the like, and adjusting the trigger condition cannot eliminate this.
- **Rounding** is reduced to one basis-independent generalized eigenvalue condition (ratio ≤ 1/25, §2.1); when it does not hold, the contract is rejected and no direction is removed. The two-layer rule per observable and per direction is not adopted: it varies with the choice of eigenvectors, k is not unique under degeneracy, and one unrelated observable can remove most directions. Coarse rounding of calibration observables always rejects the contract; an interval likelihood is not adopted, because when the interval is obtained from Δ(−2 ln L) the coverage can still lie anywhere in 0–0.99 (listed in §19).
- **Σ_MC = B_m V_m B_mᵀ** (implicit-function response, §6.7), which equals the seed-to-seed covariance checked by G7. "The profile covariance minus the covariance with the MC nuisance fixed" is not adopted, because it overestimates when V_MC and V_data are not proportional.
- **The calibration side is computed on the declared N_d,c^⊥** (the same construction as C_r⁺), because constraints by construction among calibration observables make V_G exactly singular, and the likelihood, A and P3 are then all undefined.

### 18.2 Toy construction and MC noise

- **Truth principle** (§6.6): each toy has one truth point; the truth is the prediction of the nominal MC at the truth point, and the prediction used in the fit is the nominal MC plus that toy's own replica difference.
- **Replica-difference construction**: the MC perturbation of a Gaussian block is the difference of two independent replicas at the same generation point divided by √2; its covariance is exactly V_MC, it is independent of the nominal error, and it needs no MC noise model at all. Approaches not adopted:
  - the nominal as truth and a single replica as prediction: the MC noise is counted twice (covariance 2V_MC), all toys share an offset, and the reference distribution is too wide;
  - no perturbation, reusing the nominal MC: the size is too large;
  - sampling the perturbation from a model such as N(0, V_MC): the size depends on V_MC being correct, and G7 sees only V_MC on the calibration side, not a misestimate on the validation side;
  - guarding with a trace-type replica check: a misestimate that changes only the directional distribution always passes.
- **The event-level bootstrap uses common random numbers**: all iterations of the same result share one set of random numbers; at every θ_ref update the bootstrap is regenerated with the same event interval, Philox key and uniform random numbers. Reweighting while reusing the bootstrap events is not adopted: V̂ would deviate from its expectation (high overall, larger or smaller per bin), not necessarily conservatively, and acceptance cannot detect it either.
- **Σ_boot is estimated on toy data** (each recomputes θ̂ with K_b independent bootstrap sets, and the pooled estimate is taken). It is not estimated on Asimov data, because the residual is 0 and the estimate is always 0.
- **A toy freezes the V̂ of the fit it imitates**, so quantities calibrated with toys do not add Σ_boot / w again; only curvature-based quantities (profile intervals, σ_tot) add it. Otherwise it would be counted twice.
- **Non-convergence uses a single conservative structure** (§7.3): ensemble members are replaced up to n_req, decided by the ratio test; the clauses prescribe only the conservative direction, acceptance is always one-sided, and a bias in the conservative direction is only reported, with its cost stated. Correcting case by case with "the worst value of some correlated direction" is not adopted: it fails as soon as one moves to another direction or another gate. Toys for a test are counted in the direction unfavorable to its claim; G8 cannot be counted this way (counting as not covered makes the false-alarm rate exceed α_G8, counting as covered masks undercoverage), so it uses replacement plus the margins c₀′, p₁′ in the test instead. Interval toys are always summed into one ensemble, so that the failure of a single reference distribution does not make a whole pseudo-data set non-converged.

### 18.3 Gates and G8

- **The mandatory gates are stages B–E except P7**; P7 and V are validation-type gates, and their failure only caps the grade at `calibrated-unvalidated`. Otherwise "mandatory gate failed → `failed`" would contradict "validation failed → `calibrated-unvalidated`", and mode `none` would also necessarily fail.
- **The applicability conditions of gates are defined by enumeration**, derived by `calib_design.py`; a gate that does not apply is recorded as `not-applicable`, so that rule 0 can decide.
- **G8 always uses independent MC**; when the plan does not run G8 the result carries `closure-not-tested`, and when the plan declares running it without independence the plan is rejected. With shared MC, adding a shared-variance term does not fix the coverage test.
- **G8 is a closure test with real MC** (high-statistics MC is the truth; each pseudo-data set runs the actual procedure with one independent MC of nominal size). It does not sample from the likelihood model, because that is always consistent with the fit's assumptions and cannot see the effective-count approximation, V_MC misestimates or evaluator bias.
- **The detection ability of G8 is described as it is**: only the detection-rate curve is reported, and no threshold is set. Within the range of P5, the detection rate of G8 for a factor-2 underestimate of V_MC is low, so V_MC is tested by G7, and the effective-count approximation is validated by the simulation calibration of §8.7.
- **N_c is defined as "the smallest N such that the power at N and at all larger numbers of sets is ≥ 0.8"**, because exact binomial power is sawtooth-shaped, and the value that is "first to reach 0.8" falls back below 0.8 at a slightly larger N. p₁ is defined as the coverage of the interval procedure actually used (including the counting of non-convergence), because G8 tests exactly the coverage of the interval used by the result; p₁ is not corrected separately, otherwise N_c at the full level would increase greatly.
- **The two conditions of shift mode are written as gates P8, G9**, owned only by `calib_shift.py`, because written in the contract clauses they had two owners, could not be decided at lock time and had no consequence.

### 18.4 Validation statistic and the null space

- **N_d is declared by the contract and admits only exact constraints** (C_r n_j = 0); C_r⁺ is defined in standardized coordinates, and s_i is produced by the model at θ_ref (σ⁽⁰⁾), not declared freely by the contract. The null space provides no power; a wrong declaration (a wrong entry and an omission are handled the same way) is handled as a contract error at the design stage.
- Approaches not adopted: letting offsets in the null space provide power (with a legitimately declared N_d this does not happen); putting near-deterministic directions into N_d and deciding with a single tolerance (T_v changes with s_i); a fixed numerical tolerance below the storage precision (about 81% false rejection under H0 with float32); computing the rounding upper bound from the declared storage precision (derived values and rounded c_j fall outside the bound).
- **C_r does not depend on y_v**: count-type errors are computed from the predicted expectation, and the declaration check is not redone at the validation stage. Otherwise an observed zero bin would make the rank condition fail and be recorded as V not passing, and the size under H0 would far exceed α.
- **N_d is not reduced**: untestable observables are known before locking; the contract must exclude them and declare N_d on the remaining observables (§5.2, §9.2); holdout and cross-validation are handled the same way, and k₀ is the same in P7 and at the V stage (k differs from k₀ only by the directions removed after opening per §2.1). Reduction of N_d by the engine after opening is not adopted: the truncation depends on the basis, reconditioning for missing bins produces new constraints, sequential removal depends on the order of the evaluation points, the intersection rule collapses on the set of evaluation points, and the provisional k of P7 may also differ from the k at the fit point; each fix produced new defects.
- **Power** is computed with C_r⁺ and the rank k; when toy calibration is needed it is always computed with toys (P7 and the V stage follow the same decision rule). The unbiased estimate uses the cross product of two independent MC sets (or a single set minus the trace), because "independent MC unrelated to C" cannot remove the bias of the quadratic form. On the toy path, the alternative shift is scaled by the one-sided lower bound of the cross product, and the confidence level is split by Bonferroni, so that the power lower bound is not overly optimistic because of the MC uncertainty of the cross product.
- **A power lower bound < 0.8 means insufficient power**; only when the lower bound cannot be computed is it `incomplete`, to distinguish "insufficient precision" from "insufficient power".

### 18.5 Cross-validation

- **The statistic is computed per fold**: T_cv = Σ_f r_fᵀ Ĉ_{r,f}⁺ r_f, k₀ = Σ_f k₀,f; correlation between folds is handled by the toy-calibrated reference distribution. Pooled out-of-fold residuals are not adopted: they carry d_θ structural constraints across folds, and k₀ is not well defined; with χ² as the reference, ignoring correlation between folds, the size is too large.
- **The fold split is by observable**; out-of-fold residuals of count shapes are conditioned on the observed in-fold totals of the actual data. Each training fold must pass P3; when G5 fails or there is non-convergence in a fold, V is `incomplete` with remedy level plan, and it is not recorded as a G1 failure (`failed`).
- **Calibration observables with missing values must be excluded in the contract**, not handled by reduction, because that changes the fit of every fold and the null directions by construction. The data-side constraint check is done at lock time; otherwise the first computation of T_cv could leave a permanent `final` record.
- **ε_max,cv = min(1 − (1 − ε_max)^F, 2%)**; the upper limit is not 5%, because 5% equals α.
- **Selection by outcome is an explicitly accepted trade-off**: the unused observables in cross-validation may be chosen based on data already read, whereas the holdout choice is blind; so cross-validation results carry the `cv` flag and list the unused observables and the reasons.

### 18.6 Normalization of totals and event samples

- **Expected total**: unconditioned absolute count shapes use N_exp (the exposure declared by the contract times the model's rate); free-ω shapes use N_decl, declared by the contract with a justification, and once the observed total is available they are always conditioned on the observed value. A total derived from the model is not adopted: computed with ω̂ from the nominal calibration fit, the ω of a holdout validation shape is never fitted, and locking precedes the fit; taking ω = 1, ω is free precisely because the absolute normalization of the simulation is not trusted, the total in P7 would differ systematically from that at the V stage, and it is undefined for simulations without absolute normalization.
- **The object of conditioning is the total event count N_tot,s of the event sample**, which is an ancillary statistic for all summary statistics in the sample; summary statistics that share events must be in the same sample. Conditioning on a shape's own total is not done, because that would remove the data variance of summary statistics that share events and depend on the selection (for example efficiencies), driving the rejection rate in the related directions toward 0.
- **A sample may contain several normalization components**, conditioned on the vector of the component totals. Sets that each have an independent normalization are not merged into one normalization, because when conditioning on the sum the toys sample the component proportions from the model, and T_v would in effect test the relative normalization.
- **A sample that contains calibration observables must be contained entirely in the calibration release**; otherwise N_tot,s carries sealed validation information and cannot be obtained before locking.

### 18.7 Blindness of holdout and read records

- **Validation data can be used only once, keyed by the data**: reads are recorded along the lineage down to the raw data unit, not keyed by contract series or data hash; otherwise opening a new series or repackaging the data would reset the record.
- **κ = (contract, plan, engine version)**; the κ of the first validation read must equal the κ of the result, so a recomputation with the same κ is unaffected. Fit reads are recorded too, and the first read of a holdout validation unit must belong to this κ, to stop the role swap "calibration unit reused as holdout".
- **Failure records carry a sequence number and are written as `pending` at opening**; when the decision passes they become `withdrawn`, on failure or abandonment `final`. Writing only when the decision fails would let someone who opens and does not complete the decision upgrade by switching to cross-validation; only records earlier than the first validation read of this result's κ apply, otherwise later failures by others would downgrade a legitimately obtained grade on recomputation. The `pending`/`final` rule of failure records is not used for mode `none`, because the time condition is undefined there and `pending` would be stricter than `final`.
- **After a validation failure**, a result whose calibration data overlap a failure record can be upgraded only by holdout on new data.
- **Holdout must not share events with calibration observables**; validation with shared events can only use cross-validation (V_cv = 0 in holdout). Rationale: with shared events, the validation observables can be computed from the calibration release before locking, and the analyst could lock only contracts that would pass. Therefore exemption conditions (1)(2) and `fit-pending` are unreachable under the current rules.
- **Validation data are not opened while the lineage is unconfirmed**; when the validation data come from simulation, the result cannot be `validated-in-scope`.

### 18.8 Evidence grade and "outcome already determined"

- **`incomplete` is a status, not a grade**: it does not enter the use matrix and cannot be referenced. Rule 1 precedes rule 0; otherwise a result whose mandatory gate has already failed would have to open the one-time validation data to get `failed`.
- **Upstream roles are derived from usage by `calib_deps.py`**, not declared by the contract itself; only `central` takes part in the minimum, and use-limiting flags are inherited from all upstreams. Otherwise upstreams used for systematic errors would improperly pull down the downstream grade, and self-declaration would also contradict the posterior propagation of §10.4.
- **`pending` is decided only at the layer of the effective grade**: it is resolved separately as `final` and as `withdrawn`, and then (effective grade, uses) are compared; if they are the same, that is the result; only if they differ is it `incomplete`. So `pending` is stricter than `final` only when the resolution would change the result, and the result does not depend on the time of the decision or of opening. Delaying opening is not adopted (it could be delayed indefinitely), nor is deciding only by own grade (it would be `incomplete` for no reason when the upstream or a flag already caps).
- **The testable fraction is only reported; it is not a grade condition**; the grade only requires k > 0 (the opening precondition is k₀ > 0). Rationale: the contract already determines the use of each observable, and each rule added to the fraction bookkeeping adds one more loophole (the pre-exclusion set varies with unrelated data, relisting into the measurement set, double counting by derived releases, etc.), so the fraction threshold is deleted.
- **"Outcome already determined" is a general principle**: before opening, Appendix C (C.2 then C.3) is evaluated for each combination of the possible outcomes of the inputs not yet decided; when all give the same (effective grade, use), the data are not opened, and V is recorded as `not-applicable` (not counted in rule 0; D63, D78). It applies uniformly to all inputs not yet decided, including `incomplete` mandatory gates. Enumerating the "do not open" cases one by one is not adopted: the enumeration kept missing cases (k₀ = 0, 3c, 3e, capped upstream), and a missed case literally stayed at a permanent `incomplete`.
- **A re-judgment with the same κ after the record is resolved does not count as an upstream revision**, because the (effective grade, uses) of a `pending` result that can be referenced is necessarily unchanged after resolution; after an upstream revision, a result on the same validation units reaches at most `calibrated-unvalidated`, which is a deliberate design of §9.5.

### 18.9 Decision table

- The rules of §10.2 are written as the decision table of Appendix C; `calib_use_decision_table.py` checks the invariants exhaustively and uses mutants (rule formulations with known defects) to confirm that each mutant is caught by at least one invariant.
- Decision bases such as the usage table are stated as independent tables (for example `ENTERS_DOWNSTREAM_FIT`), not shared with the program under test, so that the invariants do not become circular reasoning. The invariants come in two forms, own layer and effective layer; inputs with `pending` have no single own grade, and `assign()` rejects them.

### 18.10 Propagation and model identity

- **Shared nuisances are combined into ζ = (η, φ_shared)**, exporting the joint posterior and a single joint regression, because exporting with two marginal regressions misestimates when the two are correlated. Each uncertainty object has a source set, and whenever the source sets of any two objects intersect, a joint fit is required; a single rule covers sibling, triangle, parent-child and other correlation shapes, because rules that enumerated the shapes one by one kept missing one.
- **The model identity is a five-item masked hash**: the hash is taken after the θ, φ fields are replaced by placeholder values. A hash of the whole run card is not adopted (it contains the seeds and event intervals, so a seed change made per the rules would be misjudged as a model change), nor is taking only some of the blocks (the calibration parameters are themselves in those blocks, so the identity would change at every design point).

The complete version history (the changes in each version, the review sources and the numerical counterexamples) is kept in the sealed source `simulator-calibration-v7.37.4.md`.

## 19. Remaining open questions

The following questions remain undecided under the current rules. Items marked "Settled …" or "Partly settled …" record what has been decided since by computation or from the plugin sources, and what remains open; each item ends with its triage class and the earliest §17 phase it blocks (Appendix D introduction). Items that begin "**Accepted by the author (2026-11-09).**" are decided and normative.

- The default source table for the correlation kernels f, C, ℓ. [triage: defer to phase 4; blocks phase 4]
- (Partly settled by computation, see en/compute-19-2.md) Thresholds of shift mode: c = 0.1 is kept as an efficiency bound (coverage does not depend on it; the error exceeds profile mode by at most √(1 + c)); the recomputation of condition 1 at θ̂ uses 1.5c; the 30% symmetry and 2 ± 0.3 ratio are replaced by Δ_i ≤ 0.06 (§5.5, §8.2 note 10, §8.7 note 5; new rules, to be confirmed by the author). Open: confirmation on the toy detector of §15.1 with the resimulation-level φ, more than one shift-mode φ (the sum over l in Δ_i and the cross terms φ_l φ_m), how the refit reproducibility ≤ 0.01 s_i is checked in a real fit, and the assumption of the 1.5c margin that the relative standard deviation of the recomputed eigenvalue is ≤ 0.3; until then results that use shift mode keep `provisional-thresholds`. [triage: compute; blocks no phase (phase-2 deliverable, `provisional-thresholds`)]
- (Partly settled by computation, see en/compute-19-3.md) Truncating the V_model principal components (§5.4).
  - G6: settled. Truncation never lowers the power of G6 (power loss ≤ 0 at all tested alternatives, including discrepancies along the discarded eigen-directions). Its effect is a higher size: up to 0.75 at α = 0.01 with the 99% rule alone. Condition 2 of §5.4 (tr(V_G⁻¹V_⊥) ≤ 0.05, a new rule to be confirmed by the author) bounds this at ≤ 1.1α for every ndf ≥ 3, and on the toy detector it matched full rank in size and power.
  - Open: the effect of the discarded part on the size of T_v. Applying condition 2 to the validation observables with the expected validation covariance is provisional until a T_v size study on the toy detector (≥ 10⁴ repetitions, holdout and cross-validation, acceptance within α ± 25% as in §8.7 note 4) confirms it. The extension of condition 2 to Poisson and binomial blocks (Fisher information in place of V_G⁻¹) was not simulated. [triage: compute; blocks no phase (phase 2)]
- The default list of alternative hypotheses for each type (§11.1 item 8). [triage: defer to phase 4; blocks phase 4]
- The G8 cost for resimulation-level parameters: can pseudo-data be produced with the surrogate model and spot-checked separately with full simulation? Would this create circularity? [triage: defer to phase 3; blocks phase 3]
- Cross-event effects (space-charge buildup, dead time, pile-up): currently only approximated by conditioning variables (§3.1); event-level nodes are added when needed. [triage: defer beyond the §17 roadmap; blocks no phase]
- The simulation calibration results for the thresholds of §8.7. First calibrations by computation exist for the shift-mode thresholds (§8.7 note 5), the basin tolerances (note 6), the range of the effective-count approximation of binomial blocks (note 4), the Jacobian bias bound of P5 (§8.2 note 3) and the θ-noise bounds of P5 (§8.2 note 3, fifth item; en/research-D28.md, D85); each still needs its confirmation on the toy detector. [triage: compute; blocks no phase (`provisional-thresholds`)]
- Non-local or multimodal degeneracy: Fisher sees only locally, and `multimodal` is detected only when multi-start finds it (multi-start and the basin rules are now specified in §7.4, D57). [triage: defer to phase 3; blocks phase 3]
- How C++ density kernels are registered; the boundary between θ-parameterized classifiers and SBI. [triage: defer to phase 3 (C++ registration) and phase 5 (classifier/SBI boundary); blocks phase 3]
- (Added in the clean edition, not in the original file) Six points in the §14.1 execution binding to be confirmed by the author (the third is accepted by the author (2026-11-09), the fifth is settled by plugin source and the sixth by computation; see the sub-items):
  - Whether reproducible numerical exceptions inside a fit (`LinAlgError`, NaN, a rejected query outside the surrogate's domain) count as "non-convergence" in §7.3; §14.1 provisionally records them as `exception`, and an ensemble or fit that contains such members is `incomplete` until the author decides. Decide together with D50. [triage: author decision; blocks phase 2]
  - Whether the "budget revision" of §6.7 changes the plan hash and κ: §7.3 writes a redo as "the same κ", while the event budget belongs to the plan; §14.1 follows the more explicit "the same κ" of §7.3: the seed blocks for a redo are reserved in advance by the allocation function, and a "budget revision" only updates the budget accounts and does not change the plan hash. [triage: accept?; blocks phase 2]
  - **Accepted by the author (2026-11-09).** Adopted: "an exact recomputation with the same κ is reproducible" means bitwise-identical numerical fields in the same recorded execution environment, as written in §14.1 "Numerical determinism", which now states it without "to be confirmed". The question was whether it means bitwise identical or identical decisions. [triage: accept; blocks phase 2; accepted by the author 2026-11-09]
  - Whether the execution environment (thread count, environment lock, CPU class) belongs to κ: following §5.1, §14.1 does not put them in the plan and only requires an ensemble or fit to run in one and the same execution environment (including a single CPU model); the alternative is to put them in the plan hash, so that a hardware or environment change after opening becomes a new κ (capped by rule 3d). [triage: accept?; blocks phase 2]
  - (Settled by plugin source) A member before the stop point whose adapter decision is `needs-reset`, `needs-resource-change`, `no-retries-configured` or `not-submitted` leaves the ensemble not yet decided (§14.1). In `core/partition/states.py` (`RETRY_CLASS` and the order of the checks of the decision function) these four decisions are non-terminal, and each persists until a named human action; `not-submitted` (no attempt record) is decided before every other check, `resets-exhausted` and `stopped-repeated-failure` are tested before `needs-reset`, `no-retries-configured` and `needs-resource-change`, and `attempts-exhausted` before `needs-resource-change`. Because §14.1 requires `limits.max_resets_per_chunk`, `max_submissions` and `max_total_jobs` to be set, the number of resets and submissions is bounded, so every human action leads either to a member record or to a terminal state, which §14.1 maps to `incomplete`; without a human action the result waits with no time limit. [triage: plugin fact; blocks phase 2]
  - (Settled by computation, see en/compute-19-14-1f.md) When the G5 renewal of cross-validation toys stops: the G5 proportion, summed over all attempts, is decided at the end of every attempt, including an attempt that ends in a failing ratio test, and a proportion > 20% there makes V (P7) `incomplete` with remedy level plan, with no redo (§9.3, §14.1; a new rule, to be confirmed by the author). Within an attempt, renewal stops at the first member at which F_G5 > 0.25 × (Σ_a n_req + X_max) (§14.1); this point is reached only when every continuation of the attempt ends with the proportion > 20%, under either denominator of D68. If the proportion were decided only at completion of the last attempt, no stop point based on F_G5 alone would be certain, because redos after a failing ratio test can dilute the proportion. Open: only the choice of threshold, which follows D68: with the denominator proposed there (toys for which G5 was decided), the earlier stop F_G5 > 0.25 × Σ_a n_req is also valid and makes the reserve ⌊0.25 n_req⌋ exactly sufficient in attempt 0. See also D81. [triage: compute; blocks phase 2]
- **Accepted by the author (2026-11-09).** Adopted: the current text, as a documented limitation: correct labeling of uncertainty sources is an applicability precondition of §2.1 for which the publisher is responsible, and there is no check from the values (§18.1). Mislabeling of uncertainty sources (the applicability precondition of §2.1): this workflow does not judge mislabeling from the values. Providing a guarantee needs a release-side mechanism (for example source labels signed by an independent release process), which is not part of this workflow. [triage: accept; blocks no phase; accepted by the author 2026-11-09]
- Observables whose rounding is not negligible (the condition of §2.1 does not hold): currently the contract is always rejected, and so is a contract redeclared after excluding untestable observables. [triage: defer to phase 5; blocks no phase]
  - An interval likelihood over the rounding cell combined with a Neyman construction (the Feldman–Cousins of §7.5) might keep them, but first needs a proof that the coverage is uniform over the grid position.
  - The corresponding approach on the validation side (calibrating T_v with toys that contain the actual rounding and whose truth scans the grid position) needs the same proof.
- (Partly settled by computation, see en/compute-19-13.md) When the noise of the nominal MC varies with θ (the Jacobian carries MC noise), approximation (1) of §6.6 has, for Gaussian blocks, a design-stage bound in the fourth item of P5 (§8.2 note 3; a new rule, to be confirmed by the author):
  - the part of the Jacobian noise that only adds variance is contained in Σ_MC, because V_MC is recomputed at the fit point; the part not contained is the errors-in-variables bias b_J, which the toys of §6.6 do not reproduce (toy-calibrated intervals then have the same coverage as profile intervals);
  - in the linear Gaussian configuration of §8.7 note 4 within the P5 range, without this item the 68% coverage dropped by up to 0.031 (|b_J| ≈ 0.33σ_tot); with |b_J,i| ≤ 0.15σ_tot,i the extra undercoverage stayed ≤ 0.008; on the reweighting toy detector, P5 without this item already kept |b_J| ≤ 0.04σ_tot;
  - open: non-Gaussian blocks (MC nuisances of BB-lite and of the auxiliary binomial likelihood whose templates vary with θ), where P5 has no Jacobian term and this effect is found only by G8 (at standard level with probability of about 0.6–0.8 when the 68% loss is about 0.02–0.03); and MC predictions that are not smooth in θ (resimulation whose particle histories diverge), where the Jacobian of the MC is not defined and the noise of the objective function is handled by G1 (σ_noise) and §7.4;
  - open: the threshold 0.15 is a design value, to be calibrated on the toy detector per §8.7 in phase 2. [triage: compute; blocks no phase (phase 2; G8 catches it meanwhile); the b_J item of P5 that this computation added is a phase-2 deliverable, §17]
- The cost of the toy replica-difference construction (§6.6) is about 2n_toy times the nominal MC. Whether several toys can share fewer replicas (which makes the toys correlated) while still guaranteeing the quantiles of the reference distribution is not yet decided; sharing is currently not allowed. [triage: defer to phase 5; blocks no phase]
- The interpolation variance V_emu of the surrogate model and the closure bias of learned models (V_learn^bias) are sampled in toys according to the likelihood's own assumptions (§6.6). Their scale is supported by the pull χ² of P6 and the held-out-sample closure test; their directional distribution has no independent test; this is also a limitation of the likelihood itself. [triage: accept?; blocks no phase]

**Related to g4sim**. Items marked "g4sim" need a change on the g4sim side, raised through g4sim's design-error correction procedure; this workflow does not assume the outcome on its own:

- **Generator tuning and the `external` source** (g4sim; settled by plugin source): g4sim requires the calibration workflow to reject `external` sources (g4sim §3 principle 7, and the S4 negative test "An `external` source used by the calibration workflow must be rejected"), and provides the refusal function (`g4sim_physics_check.py` `calibration_findings`) that `calib_contract.py` can call. So generator tuning cannot use the g4sim path, and the reject rule of §5.2 is binding. Narrowing it to "reject only when node 0 needs reweighting" would be a g4sim design-change request, not a decision of this specification; generator tuning goes through hep-theory (§13). [triage: plugin fact; blocks no phase]
- **`scan`** (g4sim; settled by plugin source): g4sim GL5 says "`scan` produces design points (S layer)", but g4sim delivers no design-point generator for calibration, and no phase plans one: `geant4_run.py scan` is a grid product for `layered_sim`/`element_sim` specifications only, with an independent seed per point, and the `scan` of g4sim §11 is used only for convergence scans of cut and step-limit. So this workflow generates design points itself (§6.4; owner per D80). [triage: plugin fact; blocks phase 1]
- **k_B and the E^L/E^S split** (g4sim; settled by plugin source as a negative): when k_B changes, the split error of `edep_visible_ly_split` has no bound. The `column_map.json` schema has no field for split-error bounds, g4sim records a split error only for an LY change (g4sim §10.3), and no g4sim phase plans it. So the fallback of §5.4 is the operative rule: P0 spot checks at the k_B extremes (with P6 when evaluated with a surrogate model, §8.1). Asking g4sim to add this bound in `column_map.json`, or interval classes of μ_s in `edep_by_dedx_class`, remains an optional change request. [triage: plugin fact; blocks phase 3]
- **PDE in the efficiency map and the hand-off point between response stages** (g4sim):
  - (Settled by plugin source: not provided) The stage hand-off format of `response-pipeline/1` covers only 3→4 and 4→5 (`response_pipeline.json` `$defs.stage_handoff`, `response.py` `handoff()`); on the scintillation path stages 1 and 2 are drawn in one function, so no hand-off exists before stage 3, and none is planned. The interim rules of §11.4 hold: no single-photoelectron injection reference, and nodes 3–4a are re-digitized as a whole. [triage: plugin fact; blocks phase 3]
  - (Settled by plugin source, g4sim S7) On the efficiency-map path, ε_c includes the PDE. A mapped `efficiency-map/1` counts, in each bin, the photons for which `G4OpBoundaryProcess` returns `Detection` at a sensor (`photon_detected`). Geant4 gives that status to an absorbed photon with the probability of the surface's `EFFICIENCY`, which g4sim fills from `optical_surfaces.<name>.efficiency`. So k_c/n is light collection × PDE, integrated over the transported emission spectrum of the component, and `sensor_response` applies no further PDE; under the PDE split of §6.7 the map is built with sensor `efficiency` = 1, so that k_c/n is the probability of absorption at the sensor, and the PDE is applied in the digitization job (decided by the author, 2026-11-10; §19 PDE item). A mapping run therefore needs a sensor surface with an `efficiency` spectrum. Without one, no photon is detected. The `$comment` of `efficiency_map.json` ("reaches each channel") is outdated and does not change this (D83). [triage: plugin fact; blocks phase 3]
  - **Decided by the author (2026-11-10).** (The g4sim side is settled by plugin source, g4sim S7: g4sim has no PDE stage kind and no ε scale in `response-pipeline/1`, and `efficiency-map/1` holds detection counts only.) The PDE may be split out of ε_c on this workflow's side when the PDE model is exactly the sensor surface's `EFFICIENCY(E)` (§6.7 "PDE split"); resimulation stays allowed. The split is exact because `G4OpBoundaryProcess` uses the surface efficiency in `DoAbsorption()`, which kills the photon in every case, and otherwise only in the `EFFICIENCY > 0` test of `DielectricLUTDAVIS` and `CoatedDielectricDielectric`, so the photon histories, sensor reflections included, do not depend on it; this was confirmed in the Geant4 11 source read for `dielectric_metal`, the surface of the fixture's SiPMs, and for `dielectric_dielectric` (en/pde-geant4-check.md; Geant4 not run). The mapping run uses sensor `efficiency` = 1. A wavelength-independent PDE p is applied as p·ε_c in the per-bin efficiencies of `g4sim-digi-job/1` (g4sim S8, hep-research v0.65.0), in Python and in `g4sim_digi`, with no extra stream; its law equals that of a binomial thinning of the photoelectrons (thinning Multinomial(N, A) by p gives Multinomial(N, pA)) and of a mapping run at efficiency p. A wavelength-dependent PDE(E) is applied by weighting the efficiency-1 map and its transit histogram by PDE(E), from the photon energies of the mapping run's `photons.csv`: `efficiency-map/1` stores no energies of the detected photons, but the mapping run records them. A per-photon binomial thinning is kept for the full optical tracking path (`photons.csv`, §11.4) and, nested in p, for every readout system with an observable not linear in ε when p is θ (§6.7). A split check with a nested pair of mapping runs (sensor efficiency 1 and the nominal PDE, same seed and events), sized so that an exact split passes with probability ≥ 0.94, is required, also after any change of the Geant4 version, and the split is refused when the PDE parameter changes any other optical property (for a PDE tied to the sensor reflectance, ε was underestimated by 1.3–14% in the synthetic study, en/research-PDE.md), depends on the angle of incidence, or, on the LUT-DAVIS or coated surface models, is 0 at an energy the emission spectrum reaches; the PDE then stays an optical property (resimulation). There is no hand-off inside stage 3. [triage: plugin fact, reclassified as author decision in the g4sim S7 pass (en/g4sim-S7-check.md §1); blocks phase 3; decided by the author 2026-11-10]
- **Derived fields of the model identity** (g4sim): the masked hash of §5.1 requires that derived values of θ, φ do not remain in the hashed specification. g4sim's `params` expressions are kept as strings before geometry expansion (g4sim §6.5), so masking the original fields suffices; whether the normalization of `response-pipeline/1` and of the run card likewise produces no derived values needs to be confirmed with integration tests in phase 3. Partly answered by the plugin source: the schemas of the run card and of `response-pipeline/1` have no derived fields (parameters are literal values), but the top-level `run_seed` and `replica` of `response-pipeline/1` must be excluded from its masked hash (§5.1), and g4sim normalizes spellings only for `detector-spec/1` (§5.1). g4sim S9's IR `alignment` field holds the overlay's SHA-256, a value derived from θ when θ is an alignment, so the model identity must not hash the IR (§5.1 masking rule); the overlay document is hashed instead (§5.1, D86); g4sim S8's `g4sim-digi-job/1` is derived from `response-pipeline/1` and the map and is not hashed, but is checked against them (§5.1). [triage: defer to phase 3; blocks phase 3]
- **Enforcement for production use** (g4sim): whether g4sim, when it reads parameters whose `source_of_facts` is a calibration result, rejects results that are not `validated-in-scope` according to the use matrix of §10.2. Not settled by the plugin source: g4sim enforces only `source_of_facts`, and only for the specifications and pipelines, and no phase plans a use-matrix check (C14 below); the offline check of `calib_use.py` (§14) covers this workflow's side. g4sim S9's `condition-snapshot/1` and `alignment-overlay/1` do not even require `source_of_facts` (optional in both schemas), so `calib_use.py` must also check that every exported snapshot and overlay carries it (§10.4) (accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md). [triage: defer to phase 4; blocks phase 4]
- **Conditions for keeping old results after the simulation identity changes**: after a Geant4 or g4sim version upgrade, whether old results may be kept, without redoing them, through a pre-registered T2 equivalence test at θ̂ on the calibration observables (g4sim §18). Until this is decided, always redo (§10.3). Not settled by the plugin source: g4sim's own regression rule after a Geant4 update is T2, which supports the direction but does not decide it for calibration results. [triage: defer to phase 4; blocks phase 4]
- **Posterior update of ξ**: when downstream data pull the upstream ξ, ξ has no version update like that of ζ. Currently correctness is guaranteed by the conflict rule of §10.4 (a later analysis that references both has intersecting source sets and must fit jointly), at the cost of more joint fits. Whether to add versions to ξ is to be evaluated in phase 4. [triage: defer to phase 4; blocks phase 4]
- (Partly settled by computation, see en/compute-19-g9.md; Geant4 optical transport not run) **Local dimension reduction of the efficiency-map φ** (§6.7).
  - Settled: within one study with one Gaussian block, the reduction is exact. Two effects remain:
    - the part of U_⊥U_⊥ᵀ between different Gaussian blocks: within the acceptance at a map/data error ratio ≤ 1 (G6 power loss ≤ 0.003), and a loss of 0.011 at a ratio of about 7;
    - the cross covariance lost between studies that share φ_map: with the 1% rule alone it fails the acceptance already at a ratio of 0.7–0.9 (G6 power loss 0.11 in a joint fit, up to 0.80 when the map dominates; 68% coverage changes by up to 0.045; G8 fails where the full basis passes), although the Cauchy–Schwarz bounds of §6.7 hold.
  - The second condition added to §6.7, s_⊥ = tr(V_G⁻¹U_⊥U_⊥ᵀ) ≤ 0.05 (a new rule, to be confirmed by the author), met the acceptance in every configuration: one or two blocks, one study or two joint studies, R = 100 and 400, both centres, truth from the replica model, from mapping-run resampling, from a repeated mapping run, and with full event-level re-digitization. G6 power loss ≤ 0.013 ± 0.004, G8 coverage changes ≤ 0.004, and no new G8 failures, over ≥ 10³ pseudo-data sets per configuration.
  - Non-linearity in ε is negligible (1 − R² ≤ 7 × 10⁻⁵). The plan's 1 − R² check is vacuous when the native dimension of the map is ≥ R − 1.
  - The k/n centre of §6.7 is confirmed (with the replica mean, the bias of ln LY reached −0.48 σ_tot).
  - Open: the confirmation with a real Geant4 mapping run of the ZDC fixture extended with optics (§15.1; plan in en/g4sim-S7-check.md §4); its re-digitizations can now run as `g4sim-digi-job/1` jobs in `g4sim_digi` (C11). The noise of U from R replicas, found in the same computation, is not a reduction effect and is recorded as D84. [triage: compute; blocks phase 3]

**g4sim capabilities this workflow needs that g4sim does not yet provide** (g4sim-binding checks against hep-research v0.62.0, v0.63.0 and v0.65.0: g4sim S0–S9 are merged, with S7 partially complete because its gate 3, TR yield, is a recorded gap; S8's conditional `g4sim_digi` is built and GDML import was not triggered; `g4sim-binding-check.md` (C), `g4sim-S7-check.md`, `g4sim-S8-S9-check.md`; rows whose state or phase cell says "Provided" or "partly provided" record what g4sim has since provided, with its limits). The column "Cited in the body" lists the places before this table that cite the row by its number or rely on the stated g4sim state:

| # | Needed by this specification | g4sim state | Planned phase | Cited in the body |
| --- | --- | --- | --- | --- |
| C1 | Mapped efficiency maps on a grid, one per scintillation component, with arrival times, ≥ 100 Dirichlet replicas, mapping and validation runs (§6.7, §11.4) | Provided by S7: `efficiency-map/1` with `form.kind` `mapped` (bins of the production segmentation, `emitted`, `detected` per channel, `transit_counts` over `transit_edges_ns`, `component`, `emission_spectrum`, `hashes`), built by `g4sim_efficiency_map.py plan`/`build`; replica r ≥ 1 generated on demand by `core/simulation/efficiency_map.efficiencies(map, bin, r)` (`replicas(R)` refuses R < 100), none stored; response checks `component_findings` and `validation_response_findings`. Limits: the mapped template must be a box placed once with no rotation on its chain; validation runs only for single-component materials, with Cerenkov off | S7 (merged) | §6.7, §11.4, §15.1 |
| C2 | Optical physics, photon hits with wavelength, Cherenkov via full optical tracking, the RICH replica fixture (§11.4, §15.1) | Provided by S7: `G4OpticalPhysics` in `physics.extra_constructors` with `physics.optical` process switches and `optical_scope`; `photon_detected` with one `photons.csv` row per detection (event, scorer, volume, arrival time, transit time, photon energy in eV, emission point, direction, parent track); Cherenkov by full optical tracking (gate 2, `cherenkov_handling`); the RICH replica as the synthetic reference case `ams02-rich-replica`. Missing: photon hits in `simulation-hits/1` (`photon_hit` is declared, but the index lists only three kinds) | S7 (merged, partial) | §11.4, §15.1 |
| C3 | QE/PDE(λ) of stage 3 for photon hits (§11.4 Table 1 row 4a) | listed, no stage kind, no code | not planned | §11.4 (full optical tracking path), §15.1 (RICH row) |
| C4 | SiPM saturation (§11.4 Table 1 row 4b) | listed, not in `sensor_response` | not planned | §11.4 Table 1 row 4b |
| C5 | Stage 2→3 hand-off, and a hand-off inside stage 3 (single-photoelectron injection, §11.4) | only 3→4 and 4→5 | not planned | §11.4 (edges 4a/4b, 3/4a) |
| C6 | ε_c split into a collection map and a PDE kernel (§11.4) | none in g4sim as a kernel; with S7 maps built at sensor `efficiency` = 1 and the S8 job, this workflow may split it when the PDE acts only as `EFFICIENCY`: a scale p of the job's efficiencies, or for a PDE(E) a spectral weighting from the mapping run's `photons.csv` (§6.7 "PDE split", decided by the author on 2026-11-10); the spectral form is not in `efficiency-map/1`, and the job's transit counts are integers (D83 (21), (22)) | not planned; requested upstream (D83 (20)–(23)) | §6.7, §11.4 (edge 3/4a), §19 (PDE item) |
| C7 | Exported sizes in `column_map.json`: the `edep_by_dedx_class` bound, the LY split error, the multi-component difference (§5.4) | scorers and `volume_id` only; the bound exists only as a function | not planned | §5.4 |
| C8 | Bound on the E^L/E^S split under a k_B change, or μ_s classes in `edep_by_dedx_class` (§5.4) | none | not planned | §5.4 |
| C9 | A production driver from hit files or scorer columns to `response.py` (re-digitization over a whole run) | `core/simulation/digitize.py` composes the scintillation stages from bins (event, volume, bin, E^L, E^S, n^L) of `edep_visible_ly_split`, and `g4sim_digi` runs the same job in C++ (S8); nothing builds the job from `response-pipeline/1`, the efficiency map and the run's output, and no driver covers the other stage kinds | partly provided by S8; `g4sim_calib_eval.py` (§7.1) must build the jobs | §7.1 |
| C10 | Splitting one member across jobs and merging (§7.1, §14.1) | `chunk`/`reduce` serve the older programs only; `rng.merge_partial_sums` exists | not planned | §7.1, §14.1 |
| C11 | C++ response for throughput (cost tiers, §3.6, §6.5) | Provided by S8 for scintillation bins: `g4sim_digi` runs a `g4sim-digi-job/1` (photon numbers, the multinomial over channels, photon times, sensor, electronics) with keys from `digitize.job_with_keys`, identical to `digitize.py` at all three levels of g4sim §10.2 on the S8 fixtures (declared tolerance 8 ulp). On the registered workload it takes 0.21–0.23 of the transport (Python 3.44–3.57), 0.78–0.80 with a time for every detected photon. Limits: no other stage kind, no condition snapshot (C24), one component per job (C19), no job builder (C9); the job format has no schema file (D83 (14)) | S8 (merged) | §7.1, §14.1 |
| C12 | Conditions snapshots by IOV; alignment overlays with a new `geometry_id` (§10.4, §11.4 Table 2) | Provided by S9: `condition-snapshot/1` (one readout; IOVs [start_ns, end_ns) that may not overlap; per-cell `gain_factor`, `threshold`, `dead`, `temperature_K`), applied per channel by event time in `core/simulation/digitize.py` only; `alignment-overlay/1` (shifts and rotations of IR placements by mother, template, copy number), applied after expansion, with `g4sim_run.py diff` and `--overlay`. Limits: `g4sim_digi` reads no conditions (C24); no stage reads `temperature_K`; events carry no time (C27); one overlay per IR, per logical placement (C28); no overlay in `run-spec` (C25); `source_of_facts` optional in both | S9 (merged) | §3.6, §10.4, §11.4, §17 |
| C13 | Design-point generator (GL5 `scan`) (§6.4) | none | not planned | §6.4 |
| C14 | Use-matrix enforcement (`validated-in-scope`) when parameters are read (§10.2) | only `source_of_facts` is required, for the specifications and pipelines; S9's `condition-snapshot/1` and `alignment-overlay/1` do not require it | not planned | §10.4, §19 (production use) |
| C15 | `build_hash` covering the Geant4 libraries and data-set versions (§5.1, §10.3) | covers the `g4sim_run` executable file only (with its S8 fast-simulation hooks and `placement_impl`); the `g4sim_digi` executable (S8) is covered by no g4sim record | not planned | §5.1, §14.1 |
| C16 | A tie between `response-pipeline/1` `run_seed` and the run card's `logical_run_seed` (§6.6) | none; a `g4sim-digi-job/1` (S8) has its own `run_seed`, and `g4sim_digi` uses its precomputed keys without reading it | not planned; enforced by `calib_design.py`, for the job too (§6.6) | §6.6 |
| C17 | Key distinctness across `response-pipeline/1` documents (§6.6) | only within one document | not planned; covered by the check of §6.6 | §6.6 |
| C18 | `first_event` in the computational-run record (§14.1) | only in the hits index and the run card | not planned; the plan keeps the intervals (§6.6) | §6.6, §14.1 |
| C19 | Digitization of a multi-component material (photons of a bin split among components by their yield fractions, then each component through its own map, g4sim §10.4) | `scintillation_event` takes one map and has no component split; only the checks exist | not planned; `g4sim_calib_eval.py` must provide it (§5.4) | §5.4 |
| C20 | Digitization at a given efficiency vector (ε_0 + B_map φ_map) or with a scale of ε_c | Through the map document (`response.scintillation_event`), ε is only the nominal k/n (replica 0) or a Dirichlet replica. On the digitization-job path `g4sim-digi-job/1` (g4sim S8: `core/simulation/digitize.py`, `g4sim_digi`; hep-research v0.65.0), ε is data: one vector per bin, entries in [0, 1], sum ≤ 1, so digitization at ε_0 + B_map φ_map, at a joint-pattern replica (§6.7), at p·ε_c or at a spectral weighting of ε_c is possible, in Python and in `g4sim_digi` | partly provided by S8; joint-pattern replicas are digitized through the digitization job (§6.7); in the fixed-map mode U may be obtained by digitizing at each replica's per-bin efficiencies through the digitization job, and the linear construction of §6.7 is an option only for observables linear in ε (decided by the author on 2026-11-09, §6.7); the PDE split is digitized through the digitization job, as a scale p or a spectral weighting of the efficiency-1 map's efficiencies (§6.7 "PDE split", decided by the author on 2026-11-10) | §6.7 |
| C21 | Photon hits in `simulation-hits/1` | `photon_hit` declared, not written; detections are in `photons.csv` | not planned | — |
| C22 | A mapping run for a template placed more than once, or rotated | Refused; a single-cell mapping specification with the same materials is needed | not planned | §11.4 Table 2, §15.1 |
| C23 | Joint replicas of the efficiency maps of a θ scan whose mapping runs shared their photons (§6.7) | replica r is keyed by each map's own SHA-256, so the replicas of different maps are independent; this is not documented (D83 (6)) | not planned; this workflow draws joint-pattern replicas keyed by the scan (§6.7); a g4sim scan key is not requested (D83 (6)) | §6.6, §6.7 |
| C24 | Condition snapshots in the C++ digitization | `g4sim_digi` does not read them; only Python's `job_with_keys` refuses such a job, and `g4sim_digi` itself does not reject one (D83 (9)) | not planned; a study with conditions digitizes in Python (§14.1) | §7.1, §11.4 (conditions), §14.1 |
| C25 | An alignment overlay in a recorded run (`geant4_run.py run-spec`, its computational-run record and input manifest) | `run-spec` takes no overlay; only `g4sim_run.py simulate` and `geometry-check` take `--overlay`, and they write no computational-run record | not planned; requested upstream (D83 (7)) | §11.4 Table 2, §17 |
| C26 | Reconstruction of a misaligned simulation with the nominal geometry (§3.6, two kinds of alignment) | `geant4_run.py reco` builds simreco's planes from the run's own IR, which is the overlaid one | not planned; requested upstream (D83 (10)) | §11.4 Table 2 |
| C27 | Event times in g4sim's outputs (g4sim §17, "events may carry timestamps") | none: the time of each event is given in the digitization job (`event_time_ns`) | not planned; the plan records the times (§11.4, D87); requested upstream (D83 (17)) | §5.1, §6.6, §11.4 |
| C28 | Alignment of individual touchables | an overlay entry moves a daughter in every touchable of its mother; a touchable of its own needs a logical of its own in the detector-spec | not planned | §3.6, §11.4 Table 2 |
| C29 | Visible energy of fast-simulation deposits | a model's deposit is a zero-length step, so `edep_visible` ≈ 0 inside a `fast_sim_envelope`; documented only in a code comment (D83 (12)) | not planned | §11.4 Table 2 |

---

## Appendix A: Symbol table

One symbol per row; variants of the same object, or a group of parallel quantities, are combined into one row (for example w(ε), w(ε̂), w(ε̂⁺); m_a, m_b; E^L, E^S, n^L). The definitions in the sections cited in parentheses govern. Symbols with several meanings are listed in D14; code uses section-qualified identifiers for them, and no rule depends on the shared letter (D14).

| Symbol | Meaning |
| --- | --- |
| (see also) | σ_tot,i, σ_tot,i^design, σ_MC,i, σ_Δ,k, σ_noise, Σ_β, Σ_θ are defined in the table of §8.1 |
| θ | calibration parameters |
| φ | externally constrained parameters (shift mode or profile mode, §5.5) |
| ψ | conditioning parameters |
| ν | model-discrepancy nuisance (link space) |
| u_k | principal-component directions of ν (principal components of V_model, §5.4; link space) |
| η | correlated data-systematic-error nuisance (link space) |
| s_j | effect of the j-th component of η (link space; different from the standardization scale s_i) |
| β | (θ, ν, η, φ in profile mode, MC nuisance of non-Gaussian blocks, normalization ω of calibration shapes) (§9.2) |
| ζ | shared nuisance vector (η, shared φ in profile mode), exported as a joint posterior (§10.4) |
| B_m | linear response of θ̂ to the MC summary statistics (§6.7) |
| B_y | linear response of θ̂ to the data (§6.7) |
| V_m | covariance of the MC summary statistics (§6.7) |
| κ | validation configuration (contract hash, plan hash, engine version) (§9.5) |
| g | link function (log, identity, logit, Fisher z; for normalized shapes the alr/ilr vector links), declared according to the range of the observable (§2.1) |
| K_s | kernel of node s |
| pa(s) | upstream nodes of node s |
| e | edge on which the reference sits |
| q | proposal distribution |
| w | reweighting weight p/q |
| N_eff | Kish effective sample size |
| n_eff, k_eff | effective event count and effective pass count of the MC auxiliary binomial likelihood of a weighted efficiency, variance-matched (§2.1); distinct from the Kish N_eff; n* is its randomized rounding in toys (§6.6) |
| k_exp, Δ_sk | expected minority effective count n_eff·min(ε, 1 − ε) and skewness mismatch \|γ₁ − γ₁,bin\| that bound the validated range of the auxiliary binomial likelihood (§2.1, §8.7) |
| w(ε), w(ε̂), w(ε̂⁺) | the non-convergence correction factor F₃(χ²_{1,1−ε})/(1 − ε) of §7.3, different from the reweighting weight w; ε̂ = X/(n + X), ε̂⁺ = (X + 1)/(n + X + 1); the w in Σ_boot / w and λ̂_a·w refers to it |
| x_in | vector of all random inputs in §9.2 (including the validation data) |
| J | Jacobian |
| A | linearized fit operator (§9.2) |
| Σ_β | covariance of β |
| Σ_MC | covariance of θ̂ propagated from MC noise |
| Σ_data | covariance of θ̂ propagated from data errors |
| Σ_boot | covariance of (θ̂, ζ̂) propagated from the sampling noise of the event-level parametric bootstrap of §2.1, estimated with toys at the design stage |
| N_t | number of toys used to estimate Σ_boot |
| K_b | number of bootstrap sets per toy |
| ν_b | pooled degrees of freedom of Σ_boot, N_t(K_b − 1) |
| N_decl | for a free-ω shape that enters through a count likelihood, the expected total declared by the contract with a justification; in cross-validation the justification is the observed total of that fold in the calibration data, checked for equality by the checker (§2.1) |
| N_exp | expected total of an unconditioned absolute count shape: exposure declared by the contract × absolute rate of the simulation at the evaluation point (§2.1) |
| N_obs | observed total of a shape (§2.1) |
| n_c | number of calibration observables in P2: the dimension of the calibration data vector entering the likelihood, excluding unused observables (§8.2 note 2, D77) |
| N_d,c | exact constraints by construction declared among calibration observables (declared in §5.2, in all modes including `none`); on the calibration side the likelihood, A, Fisher and the rounding condition are all computed on its orthogonal complement N_d,c^⊥ (§2.1). Same construction as N_d on the validation side, in a different space |
| N_decl,s | expected total event count of a free-normalization event sample, declared by the contract with a justification (§2.1). When the sample contains calibration observables, the justification is the N_tot,s readable before locking, checked for equality by the checker; a sample that belongs entirely to validation uses it in place of N_tot,s before opening. In a multi-component sample it is the vector of components (N_decl,s,j) |
| N_tot,s | observed total event count of an event sample, the quantity on which the summary statistics in the sample are conditioned (§2.1); in a multi-component sample it is the vector of components (N_tot,s,j) |
| P_k(θ) | model probability that an event of the sample falls in bin k of a shape (including selection, §2.1); in a multi-component sample P_{k,j} is the probability for component j |
| ε_max | non-convergence rate allowed by §7.3 (1%) |
| ε_max,cv | allowed non-convergence for cross-validation toy ensembles, min(1 − (1 − ε_max)^F, 2%), with F the number of folds (§7.3) |
| k* | critical non-convergence count of an ensemble's ratio test at n_req (§7.3) |
| T_v | holdout validation statistic r_vᵀ C_r⁺ r_v (§9.2) |
| T_cv | cross-validation validation statistic (§9.3) |
| C_r | covariance of the validation residuals (§9.2) |
| C_r⁺ | S⁻¹ Ũ_⊥ (Ũ_⊥ᵀ C̃_r Ũ_⊥)⁻¹ Ũ_⊥ᵀ S⁻¹; in this document C_r⁺, C_{r_v}⁺, Ĉ_r⁺ are always defined this way (§9.2) |
| k | validation degrees of freedom: dim N_d^⊥ (n_v when there is no deterministic constraint), minus the directions removed after opening per §2.1: for a free-ω count shape with N_obs = 0 subtract K − 1; for an event sample with N_tot,s = 0 subtract the dimension of the sample's summary statistics on N_d^⊥; when some components are 0 (and for the collapse this causes), and for bootstrap rank deficiency of a sample that belongs entirely to validation, subtract the number of removed directions. These subtractions do not apply to absolute count shapes, which enter T_v as usual when N_obs = 0. Untestable observables are not in the validation contract (§5.2), so k depends only on the observables and N_d declared by the contract (§9.2) |
| k₀ | dim N_d^⊥, i.e. the validation degrees of freedom before subtracting the directions removed after opening per §2.1; the opening precondition is k₀ > 0; in cross-validation it is the sum over folds (§9.2, §9.3, §9.5) |
| V_emu | interpolation variance of the surrogate model (§6.4); toys sample N(0, V_emu) according to the likelihood's own assumptions (§6.6) |
| V_learn^bias | squared closure-bias term in V_learn (§6.2); toys sample N(0, V_learn^bias) according to the likelihood's own assumptions (§6.6) |
| m_a, m_b | the two MC replicas of a toy; the perturbation of a Gaussian block is (m_a − m_b)/√2 (§6.6) |
| γ̂ | MC nuisance of the nominal fit (§6.6) |
| τ | effective event count (Σw)²/Σw² (§6.6) |
| γ̃ | MC nuisance at the truth point of a toy (§6.6) |
| s_a | scaling factor of the alternative shift for power toys (§6.6) |
| λ_a^low | one-sided lower confidence bound of the cross product used by s_a (§6.6, §9.4) |
| λ̂_a^single | single-set noncentrality parameter used by s_a (§6.6) |
| R_corr | correlation matrix |
| λ_min | smallest eigenvalue of R_corr |
| G_ξ | exported residual coefficient matrix (§10.4) |
| G_ζ | exported shared-nuisance coefficient matrix (§10.4) |
| G_s | exported coefficient matrix of shift-mode φ (§10.4) |
| ξ | θ's own residual uncertainty, not a shared nuisance (§10.4) |
| d_l | full response of the validation residuals to the shift-mode φ_l (§9.2) |
| λ_a | noncentrality parameter of alternative hypothesis a; the null space provides no power (§9.4) |
| N_d | subspace spanned by the exact constraints that hold by construction on the validation side (§9.2) |
| n_j | the j-th constraint n_jᵀr = 0 (§9.2) |
| ñ_j | standardized unit constraint vector S n_j / ‖S n_j‖ (§9.2) |
| P̃_N | orthogonal projection onto span{ñ_j} (§9.2) |
| Ũ_⊥ | orthonormal basis of the orthogonal complement of span{ñ_j} in standardized coordinates: of N_d on the validation side (§9.2), of N_d,c on the calibration side (§2.1); after opening, when directions are removed per §2.1, the remaining orthogonal complement instead |
| S | standardization scale matrix diag(s_i) (§9.2) |
| s_i = σ_i⁽⁰⁾ | elements of S: the data standard deviation produced by the model at θ_ref, without rounding (§2.1, §9.2) |
| ρ_i | representation resolution of the released value (last-digit unit of the floating-point type or of the published digits; derived quantities propagated along the lineage), taken as the maximum over the predicted ±5σ_i⁽⁰⁾ range according to the format declared by the release, without reading the observed value; used for the rounding condition and V_data^unc; recorded as 0 for integer counts (§2.1) |
| ρ_i^obs | last-digit unit used by the data-side constraint check: computed from the values actually read, according to the format declared by the release, with derived quantities propagated along the lineage; used only for the constraint check (§9.2) |
| τ_num | numerical tolerance for exact constraints (standardized variance, §9.2, §8.7) |
| C̃_r⁽⁰⁾ | standardized residual covariance without the rounding term (§9.2) |
| R | squared standardized rounding step diag((ρ_i/σ_i⁽⁰⁾)²) (§2.1) |
| C_r^data | residual covariance with data noise only (Σ_β taken from the design-stage Asimov fit with data noise only), used only for the rounding condition of §2.1; different from the C_r⁽⁰⁾ used by the declaration check |
| p | dimension of the event-level parametric bootstrap matrix (§2.1) |
| B | number of resamples of the event-level parametric bootstrap (§2.1) |
| ω | normalization parameter of a shape count likelihood |
| n_min | lower bound on the expected count per bin for Gaussian summary statistics of shapes (worst over the evaluation points, recomputed at the fit point, §2.1) |
| clr | centered log-ratio; the correlation kernels of normalized shapes are declared in these coordinates (§5.4) |
| m | size of the G8 test family (also the number of alternative hypotheses of §9.4; D14) |
| N_c | number of G8 pseudo-data sets |
| B_map | basis of the efficiency-map replicas in native coordinates (§6.7) |
| φ_map | shared coefficients on B_map (§6.7) |
| R_map | second moment of the efficiency map in observable space, diagnostic only (§6.7) |
| Σ_jl | covariance of the map-induced errors e_j, e_l of the predictions at design points j, l of a θ scan (§6.7, §8.2 note 3) |
| w_j(θ) | weights of the surrogate model in the design-point values, μ̂(θ) = Σ_j w_j(θ) μ_j (§6.7) |
| U_j, E_j, U(θ) | map term of the mode where the map varies with θ: U_j the replica differences of design point j's predictions divided by √(R − 1) (with the analytic covariance, the row blocks of a factor L of [Σ_jl] = LLᵀ); E_j = I with joint-pattern replicas, the block of design point j with independent seeds; U(θ) = Σ_j w_j(θ) U_j E_j (§6.7) |
| s_i, κ_i (P5) | whitened slope and curvature noise of the surrogate model in θ_i, inherited from the map noise of the design points (§8.2 note 3, fifth item); not the standardization scale s_i of §9.2 nor the validation configuration κ (D14) |
| `geometry_id` | one of the g4sim identities (g4sim §7.2); for the model identity see §5.1 |
| `request_id` | one of the g4sim identities (g4sim §7.2) |
| `run_id` | one of the g4sim identities (g4sim §7.2) |
| `build_hash` | one of the g4sim identities (g4sim §7.2) |
| E^L, E^S, n^L | the three quantities of g4sim `edep_visible_ly_split` (g4sim §10.3) |
| d | number of calibration parameters, dim θ (written d_θ in §9.3); not the comparison node d of §3.4 |
| n_v | number of validation observables, the dimension of r_v (§9.2) |
| n_req | required number of members of an ensemble: converged members with replacement, all members without replacement (§7.3); with subsets n_req,s |
| X | number of non-converged members of an ensemble (§7.3); summed over all attempts in the ratio test and in ε̂, that of the last attempt in the p-value of a testing ensemble |
| F | number of cross-validation folds (§7.3, §9.3) |
| n_dp | number of design-point MCs with which a surrogate model is built (§6.4, §6.6) |
| n_eval | number of design points evaluated in one fit in the full construction with resimulation (§6.7) |
| V_G | covariance of the Gaussian blocks, V_data^unc + V_MC + V_emu + V_learn (§2.1) |
| V_MC | covariance of the MC noise of the predictions of Gaussian blocks; enters V_G (§2.1, §6.7); the bins of Poisson and binomial blocks are not in it |
| V_cv | shared-event covariance between calibration and validation observables; nonzero only in cross-validation (§2.1, §9.2) |
| Ĉ_r, Ĉ_{r,f} | toy estimate of C_r on N_d^⊥ (§9.2); in cross-validation, of the covariance of the out-of-fold residuals of fold f (§9.3) |
| α | level of a test, stated where it is used (0.05 for T_v and the power decision; 0.01 for G6, P0 and P6); α_G8 = 0.05 is the family-wise level of G8 (§8.4) |
| α_P | simultaneous level of the power lower bounds, default 0.05 (§9.4) |
| M | Bonferroni count of P0/P6 (§8.2 notes 1, 4); not the metric M of §5.4 |
| f | MC fraction of P5, Σ_MC ⪯ f·Σ_data, default 0.1 (§6.7); other uses of f are listed in D14 |
| c | threshold of the information condition of shift mode, default 0.1 (§5.5) |
| EDM, tol, UP | in G1 (§8.2): estimated distance to the minimum, the minimizer tolerance, and the error definition of the objective (Minuit conventions); tol is the minimizer tolerance declared in the plan (D79) |
| φ_loc | local coefficients of the efficiency map after local dimension reduction, Q_mᵀ φ_map (§6.7) |

## Appendix C: Decision table for the evidence grade

The rules of §10.2 are governed by the following decision table; where the text and this table disagree, this table governs and the disagreement is reported as a defect.

**Reference implementation**: `calib_use_decision_table.py` (provided with this document; uses only the standard library). `calib_use.py` must agree with the reference implementation's `assign`, `effective`, `allowed_uses` and `variation_upstream_admissible` input by input, and pass the same set of tests.

- C.2 (`assign()`) is defined only for resolved inputs. For inputs with `pending` or `fit-pending`, the first step of C.3 (`effective()`) looks up C.2 once for each of the two resolutions; `assign()` rejects such inputs (I25).
- The validation-read events themselves (which κ read a given piece of data first) are inputs here; their derivation in `calib_data.py` is tested by the named cases of §15.3.

**Test scope** (exhaustive):

- All combinations of own inputs (in mode `none`, P7, V, reuse and the validation-data source are fixed at not applicable; the reference implementation represents them with neutral values: P7 not failed, the three V inputs yes, reuse `none`, validation data not from simulation), each paired with "no upstream" and with "each single upstream" (7 usage sets: each of the 6 usages alone and {envelope, nuisance posterior}; × 4 grades; × 5 flag sets: no flag, or exactly one of `provisional-thresholds`, `closure-not-tested`, `preliminary`, `outside-validated-range`).
- Own combinations that reach `validated-in-scope` under at least one resolution (a resolved input has only one resolution; those with `pending` whose two resolutions differ are also among them) are additionally paired with every ordered pair of upstreams, so the `pending` rule is also tested with two upstreams.
- The "which usages enter the downstream fit" used by I11 is written as a separate, independent table (`ENTERS_DOWNSTREAM_FIT`), not shared with the role derivation under test.
- The "outcome already determined" lookup of §10.2 rule 0 is tested exhaustively as well: for every own input combination above with at least one input not yet decided (an `incomplete` mandatory gate, P7, V), the lookup over all combinations of their possible outcomes, evaluated with C.2 then C.3, is compared with an independently written enumeration. These tests are added to the reference implementation; the version whose SHA-256 is given in the front matter does not contain them (D63, D13).

**Mutant check** (`--mutants`): rerun with the following mutants; each must violate at least one invariant.

1. P7 listed as a mandatory gate.
2. Validation-data reuse decided only by contract time.
3. Self-declared roles accepted.
4. Use-limiting flags (`preliminary`, `provisional-thresholds`) inherited only from `central` upstreams.
5. Role derivation that treats nuisance posteriors or ξ as variation sets.
6. Flag inheritance that reads only the first upstream.
7. `incomplete` treated as passing.
8. Rule 0 before rule 1.
9. The cap of grade-limiting flags removed.
10. Non-qualifying `variation` upstreams let through.
11. `pending` failure records ignored (a record written only when the decision fails).
12. The failure-record rule applied to mode `none`.
13. `pending` not excluding the cases of rule 2.
14. Holdout looking only at validation reads and ignoring fit reads.
15. Fit reads of cross-validation also capped.
16. Holdout `pending` (`fit-pending`) deferred unconditionally.
17. Holdout `pending` (`fit-pending`) treated as withdrawn.
18. Cross-validation `pending` still `incomplete` when other conditions already cap.
19. `pending` decided only by the own grade, ignoring the caps from central upstreams and grade-limiting flags.
20. `pending` always given `failed` when capped.
21. `pending` always given `projection` when capped.
22. When capped, `pending` ignoring a lower central upstream and always given `calibrated-unvalidated`.
23. A `pending` result with the correct effective grade but one extra use-limiting flag, losing the use "basis for formal publication" (`publication` in the reference implementation).
24. A `pending` whose resolution changes the own grade decided only by the first upstream.
25. "Outcome already determined" lookup evaluated with C.2 only (capped upstreams ignored).

**Consistency with the body**: Appendix C incorporates rule 0 of §10.2 (`incomplete`), the raw units and the first validation read of §9.5, and the power lower bound of §9.4 ("sufficient power" = simultaneous lower confidence bound ≥ 0.8). The `closure-not-tested` downgrade path of G8 is not affected by rule 0: it is an explicit downgrade, not an omission.

**C.1 Inputs**

| Input | Values | Source | Reference implementation field |
| --- | --- | --- | --- |
| A mandatory gate, P7 or V is `incomplete` | yes/no | §10.2 rule 0. Mandatory gates recorded as `not-applicable` per §8.1 are not counted; V can be `incomplete` only while T_v has not been decided as failing (§9.4) | `incomplete` |
| A mandatory gate failed | yes/no | §8.1 (stages B–E, except P7), final version | `mandatory_gate_failed` |
| Real data used | yes/no | Status of the **calibration data** release (§5.1); if any calibration data come from simulation, this counts as no. Validation data from simulation is a separate input (3e) | `real_data` |
| Validation mode | `none`/`holdout`/`cross-validation` | contract | `vmode` |
| intended_use has only design uses | yes/no | contract | `design_only` |
| P7 failed | yes/no; not applicable in mode `none` | §8.2 | `p7_failed` |
| V passes, power is sufficient, there is a testable direction (k > 0) | Three inputs, each yes/no; not applicable in mode `none`. "There is a testable direction" only means k > 0. When the data are not opened because the outcome is already determined (in cross-validation, T_cv is not computed), V is recorded as `not-applicable` and input as "no" (v_pass = False), it is not counted as an `incomplete` input, and the result is what the lookup gives; this covers cases such as 3c, 3e and a capped upstream (the general principle of §10.2 rule 0) | §9 | `v_pass`, `power_ok`, `testable_ok` |
| Reuse of the raw units read by validation | `none`/`fit`/`fit-pending`/`validation`; not applicable in mode `none` (fixed at `none`). For the definition of each value see "Values of the reuse input" below | §9.5 | `validation_data_reuse` |
| Validation data from simulation | yes/no; not applicable in mode `none` | §5.1 | `validation_data_simulated` |
| The calibration data overlap a raw unit, and that unit has a failure record of another κ earlier than the first validation read of this result's κ (on both sides, all raw units of the calibration releases of the contract, §9.5, D60); before T_cv is computed, every existing failure record of another κ counts as earlier; the input is evaluated again at the sequence number of that read (§10.2, D69) | `none`/`final`/`pending`. Only `withdrawn` records, or no record, gives `none`; when there are both `final` and `pending`, `final` is taken. Every mode has this input, but it affects only the results of mode `cross-validation` | §9.5 (for the writing and states of failure records see "States of failure records" below) | `earlier_failure_record` |
| Own flags | subset | §7, §8, §10.4 | `own_flags` |
| Usage, effective grade and flags of each upstream | — | §5.2 `upstream[]` | `usages`, `effective_grade`, `flags` |

**Values of the reuse input** (derived by `calib_data.py` from the read events (including the hash of the data release and its role in this result's contract) and the failure records):

- `validation`: for some raw unit read by validation, the first validation read belongs to another κ.
- `fit`: not the former, but some validation unit has a non-exempt read before the first validation read of this result's κ. Under the current rules the calibration release and the validation release of a holdout share no raw units (§9.5), so no earlier read on a holdout validation unit is exempt.
- `fit-pending`: **unreachable under the current rules; kept in the reference implementation for compatibility with old records.** In old records it means: neither of the first two, but whether a fit read on some validation unit is exempt depends on a failure record of another κ that is earlier than the opening and still `pending`; when that record is resolved as `final` it becomes `fit`, as `withdrawn` it becomes `none`.
- `none`: none of the above.

Failure records of other κ do not affect holdout through the failure-record input (I20); in old records they act on holdout through the reuse input: a `final` record makes the fit read non-exempt, giving `fit`, and a `pending` record makes it `fit-pending`.

**States of failure records** (§9.5): a failure record is written as `pending` at opening, with the sequence number of the opening; it is `final` when the decision fails or that κ is abandoned; it is `withdrawn` when the decision passes, or when k = 0 and the data-side constraint check (including "has a value") is not triggered; when it is triggered the record is `final` (D22, D64); declaring power abandonment does not change the record.

**κ without validation reads**: in the following cases κ has no validation read at all, and the reuse input and the failure-record input both take `none`. The result is then already decided by rule 0, 1, 2, 3b or by the "outcome already determined" lookup, and the values of these two inputs do not affect the result.

- k₀ = 0 is determined before opening;
- the lineage is unconfirmed;
- P7 is `incomplete`;
- a mandatory gate is `incomplete` and the outcome is not yet determined;
- the outcome is already determined, so the data are not opened or T_cv is not computed (the general principle of §10.2 rule 0);
- the toy replicas could not be produced;
- in cross-validation a fold does not converge or fails G5 on the actual data, or the fraction of G5 failures among the toys of Ĉ_{r,f}/the reference distribution is > 20%, and T_cv is not computed;
- before opening (in cross-validation, before computing T_cv), the ratio test of the reference toys, Ĉ_r or Ĉ_{r,f} fails (§9.5);
- rules 1, 2 have already decided the result (mandatory gate failed, calibration data from simulation), so the data are not opened or T_cv is not computed.

When a contract is rejected, no result is produced and the decision table is not applied (§9.2, §9.5).

**C.2 Grade (in order, the first that holds is taken)**

| # | Condition | Grade |
| --- | --- | --- |
| 1 | A mandatory gate failed | `failed` |
| 0 | No mandatory gate failed, and a mandatory gate, P7 or V is `incomplete`. None of the following count: gates not run after a mandatory gate failed; V, P7 and the opening preconditions when the data are not opened because the outcome is already determined; `incomplete` mandatory gates when the outcome is already determined (the general principle of §10.2 rule 0); gates recorded as `not-applicable` per the applicability conditions of §8.1 | `incomplete` (a status, not a grade; cannot be referenced) |
| 2 | No real data; or mode `none` and only design uses | `projection` |
| 3a | Mode `none` | `calibrated-unvalidated` |
| 3b | P7 failed; or V does not pass; or the simultaneous lower confidence bound of power < 0.8; or no testable direction (k = 0) | `calibrated-unvalidated` |
| 3c | Carries `closure-not-tested` itself | `calibrated-unvalidated` |
| 3d | The reuse input is `validation`; or the mode is `holdout` and the reuse input is `fit` | `calibrated-unvalidated` |
| 3e | The validation data come from simulation | `calibrated-unvalidated` |
| 3f | The mode is `cross-validation`, and the calibration data (all raw units of the calibration releases of the contract, §9.5) contain a raw unit with a `final` failure record earlier than the first validation read of this result's κ | `calibrated-unvalidated` |
| 4 | Otherwise | `validated-in-scope` |

The inputs of C.2 do not include `pending` and `fit-pending`: these two values appear only in the first step of C.3, which looks up this table once for each of the two resolutions (`final`/`fit` and `withdrawn`/`none`). So every row of this table decides only on resolved inputs, and rows 3d, 3f do not need to list the `pending` values.

**C.3 Upstream roles, flags and effective grade**

| Step | Rule |
| --- | --- |
| `pending` (first step) | When there are inputs with `pending` or `fit-pending`, resolve them separately as `final` (`fit`) and as `withdrawn` (`none`), look up C.2 for each to get the own grade, and then for each apply the following steps of this table to get (effective grade, uses). When the two differ, the result status is `incomplete` (no uses, cannot be referenced); when they are the same, that is the result (§10.2 rule 0). When a mandatory gate failed or there is an `incomplete` input, the two resolutions give the same result (`failed` is still `failed` after capping; `incomplete`) |
| Upstream | The effective grade must be one of the four grades; an `incomplete` result cannot be referenced |
| Role | Usage includes one of φ center, nuisance posterior, ξ, fixed value → `central`; only variation set or envelope → `variation`; no usage → rejected (`calib_deps.py`) |
| Eligibility of a `variation` upstream | Its effective grade and flags must allow "systematic-error variation sets or envelopes"; otherwise the reference is rejected (`calib_use.py`; reference implementation `variation_upstream_admissible`) |
| Flags | own ∪ all flags of all `central` upstreams ∪ `preliminary`, `provisional-thresholds` of all upstreams; the other flags of `variation` upstreams go into `variation_flags` |
| Effective grade | min(grade, effective grades of all `central` upstreams); when the flags contain `outside-validated-range` or `closure-not-tested`, additionally min(·, `calibrated-unvalidated`) |
| Uses | The §10.2 use matrix by effective grade; when the flags contain `preliminary` or `provisional-thresholds`, "formal publication" is removed |

**C.4 Invariants**

| # | Invariant |
| --- | --- |
| I1 | Only a mandatory gate failure gives `failed`; validation failure, P7 failure and mode `none` do not (layer: own; effective-layer form I1e, see below) |
| I2 | Mode `none` is never `validated-in-scope` (layer: own; effective layer I2e) |
| I3 | When the reuse input is `validation` (the first validation read of some validation unit belongs to another κ), grade ≤ `calibrated-unvalidated` (layer: own; effective layer I3e) |
| I4 | When P7 fails, grade ≤ `calibrated-unvalidated` (layer: own; effective layer I4e) |
| I5 | Without real data, effective grade ≤ `projection` |
| I6 | The effective grade is not higher than any `central` upstream, nor higher than the own grade (for resolved inputs; D15) |
| I7 | `validated-in-scope` requires all conditions to hold at the same time (layer: own; effective layer I7e; the `pending` failure-record input is handled in I7e) |
| I8 | When any upstream (including `variation`) carries `preliminary` or `provisional-thresholds`, the result cannot be used for formal publication |
| I9 | Production use accepts only `validated-in-scope` |
| I10 | The use matrix is monotone in the grade |
| I11 | When the usage contains any central usage, the role must be `central` |
| I12 | In mode `none`, with only design uses, no mandatory gate failed and no `incomplete` input, the grade is `projection` (layer: own; effective layer I12e) |
| I13 | When the validation data come from simulation, grade ≤ `calibrated-unvalidated` (layer: own; effective layer I13e) |
| I14 | When the calibration data contain a raw unit with a `final` failure record earlier than the first validation read of this result's κ, and the mode is `cross-validation`, grade ≤ `calibrated-unvalidated`; failure records later than that read do not affect the grade (layer: own; effective layer I14e) |
| I15 | With no mandatory gate failed and an `incomplete` input, the status is `incomplete`, with no uses at all; when a mandatory gate failed, always `failed`; with no `incomplete` input and outside the cases of I19, I23, the effective grade is never `incomplete` (the own grade is defined only for resolved inputs, I25) |
| I16 | A reference to an `incomplete` upstream is rejected |
| I17 | When the flags (own or of a `central` upstream) contain `outside-validated-range` or `closure-not-tested`, effective grade ≤ `calibrated-unvalidated` |
| I18 | A `variation` upstream is accepted if and only if its effective grade ≥ `calibrated-unvalidated` (stated with a table independent of `allowed_uses`) |
| I19 | With no mandatory gate failed and no `incomplete` input, mode `cross-validation`, real data used, the failure-record input `pending`, no other capping condition holding, and no cap from a central upstream or a grade-limiting flag, the result (effective grade) is `incomplete`, with no uses |
| I20 | The results of modes `none` and `holdout`, and results that do not use real data, do not depend on the failure-record input (`none`, `final`, `pending` give the same result; the reference implementation checks each enumerated case together with its upstreams) |
| I21 | In mode `holdout`, with the reuse input `fit` (the validation unit has a non-exempt read before opening), grade ≤ `calibrated-unvalidated` (layer: own; effective layer I21e) |
| I22 | The results of mode `cross-validation` (effective grade and uses) are the same when the reuse input is `fit`, `fit-pending` and `none` (fit reads do not cap cross-validation; the converse of I21, preventing over-capping; checked together with upstreams) |
| I23 | (`fit-pending` is unreachable under the current rules; this invariant is meaningful only for old records.) In mode `holdout`, with real data used, the reuse input `fit-pending`, no other capping condition holding, and no cap from a central upstream or a grade-limiting flag, the result (effective grade) is `incomplete`, with no uses; conversely, for results with no `incomplete` input and no mandatory gate failed that are not among the cases listed here and in I19, the effective grade is never `incomplete` |
| I24 | With a `pending` input, the result equals the (effective grade, uses) computed for each of the two resolutions with the independently written caps (effective grades of central upstreams; grade-limiting flags of own and of central upstreams) and the independently written use matrix (use-limiting flags taken from own and from all upstreams): when the two are the same it is that, when they differ it is `incomplete`. I5, I6, I8–I10, I17, the effective-layer forms of the nine in the table below and "mandatory gate failed → `failed`" are checked for these results likewise |
| I25 | The own grade (C.2, `assign()`) is defined only for resolved inputs: with a `pending` or `fit-pending` input, `assign()` rejects; I20, I22 are stated in terms of the effective grade and uses |

**Layer**: the word "grade" has two layers in C.4.

- I5, I6, I8–I11, I15–I20, I22–I25 are stated on the effective grade or the uses, according to their text.
- The table text of the following nine is at the **own layer** (`assign()`, only for resolved inputs); each has an **effective-layer form**, checked for every result that has a grade (including `pending` results).
- Both layers are checked by `calib_use_decision_table.py`.

| Own layer | Effective-layer form |
| --- | --- |
| I1 | I1e: the effective grade is `failed` only when a mandatory gate failed or some central upstream has effective grade `failed` (the own-layer I1 does not hold at the effective layer: when a central upstream is `failed`, the effective grade is `failed`) |
| I2, I3, I4, I13, I14 | I2e, I3e, I4e, I13e, I14e: under the same condition, effective grade ≤ `calibrated-unvalidated` |
| I21 | I21e: in mode `holdout`, with the reuse input `fit` or `fit-pending`, effective grade ≤ `calibrated-unvalidated` (one of the two resolutions of `fit-pending` is `fit`, so it cannot be `validated-in-scope`) |
| I7 | I7e: when the effective grade is `validated-in-scope`, all conditions of the own-layer I7 hold (`fit-pending` in holdout counts as `fit`; it does not hold when the failure-record input is not `none` and the mode is `cross-validation`), every central upstream has effective grade `validated-in-scope`, and neither the result itself nor any central upstream carries a grade-limiting flag |
| I12 | I12e: in mode `none`, with only design uses, no mandatory gate failed and no `incomplete` input, effective grade = min(`projection`, the lowest effective grade of the central upstreams) (the own-layer I12 does not hold at the effective layer) |

---

## Appendix D: Known inconsistencies and items to clarify

The items below have two sources: the minors adopted in the v7.37.4 full-text R2 regression (record in `simulator-calibration-v7.37.4-regression-review.md`), and inconsistencies in the original text found while preparing this edition. This clean edition does **not** rule on these points; the body is written as in the original text, and the author needs to decide before implementation. D16–D20 and D22–D25 are exceptions: for these, this edition follows the more explicit of the places (or writes as in the original text and states the interpretation), as noted in each entry; D21 is written as in both places of the original text. None of them changes the decision functions of the decision table. D26–D80 were added in the English primary edition from five independent content reviews: D26 lists numerical examples corrected in the body after recomputation; D27–D80 are items for the author, where the body is left unchanged and the resolution given is only proposed, to be confirmed by the author (until the acceptance of 2026-11-09, below). D7, D9, D14 and D21 were extended in the same pass. In the computation, g4sim-binding and triage pass (Appendix E, "Changes from the computation, g4sim-binding and triage pass"), entries settled by computation or by the plugin sources are marked "Settled …" or "Partly settled …" with what remains open; D13 and D64 are merged (their numbers are kept); D81 and D82 record side findings of the computation reports; D83 (added in the g4sim S7 pass) lists g4sim defects to raise upstream; D84 (added with the computation of §19-g9) records its side finding on the number of efficiency-map replicas; D85 (added with the D28 revision) records the open points of that revision; D86 and D87 (added in the g4sim S8 and S9 pass, accepted by the author on 2026-11-09) record the model identity of alignment overlays and condition snapshots and the statistical roles of conditions and alignment, whose texts are written in place in §5.1 and §11.4 with the tag "(accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md …; D86)" or "(…; D87)"; and each entry ends with its triage class and the earliest §17 phase it blocks, "[triage: class; blocks phase n]" (classes: accept; accept?, a reading supplied by the reviewer or the reviewer unsure; merge; compute; plugin fact; defer; author decision; from `triage.md`). On 2026-11-09 the author accepted every class-1 proposal (accept) as `triage.md` writes it, except D68, and the merges D13 → D63 and D64 → D22. These entries begin "**Accepted by the author (2026-11-09).**" (the merged ones "Merged into …; accepted by the author (2026-11-09)"), followed by what was adopted and where; their resolutions are written into the body as normative text, the wording "(proposed, to be confirmed by the author)" in them is replaced by "(adopted)", and their tags end "accepted by the author 2026-11-09". D28 was revised on 2026-11-09 by a further decision of the author (en/research-D28.md): it begins "**Accepted by the author (2026-11-09; revised 2026-11-09 after en/research-D28.md).**", and its tag ends "revised 2026-11-09". On 2026-11-09 the author also accepted D86, D87, every rule tagged "(settled by plugin source, …; to be confirmed by the author)" and the three choices tagged "(new choice of the D28 verification, …; to be confirmed by the author)" (Appendix E, "Author's acceptance of 2026-11-09 (plugin-source rules, D28 choices, D86, D87)"): D86 and D87 begin "**Accepted by the author (2026-11-09).**", their tags end "accepted by the author 2026-11-09", and those tags now read "(accepted by the author, 2026-11-09; source en/…)". The classes 1? (accept?) and 6 (author decision), D68, D81–D85 and the rules tagged "(settled by computation, …; to be confirmed by the author)" or "(a new rule, to be confirmed by the author)" still need the author; their proposals are not applied.

| # | Location | Content |
| --- | --- | --- |
| D1 | §9.2, §9.3 | When the fold split makes rank condition (c) fail, the remedy level is written inconsistently: §9.2 writes "contract" (exit code 2), §9.3 writes "plan". Neither produces T_cv, but an implementer cannot decide whether to reject the contract or the plan. [triage: accept?; blocks phase 2] |
| D2 | §9.4, §9.5 | With several alternative hypotheses, one lower bound may be computed and < 0.8 while another cannot be computed. Under §9.4 this is decided as insufficient power; the order of the §9.5 table, however, lands first on "lower bound cannot be computed → `incomplete`". [triage: accept?; blocks phase 2] |
| D3 | §9.5 table | "The ratio test before opening fails (redo within the same κ)" is ordered before "G5 fails in a fold (remedy level: plan)". When both happen at once, the remedy given by the first match cannot solve the problem. The result is `incomplete` either way. Computation 19-14-1f (tagged rule in §9.3, §14.1) needs this case resolved toward the plan remedy with no redo; §9.5 and §7.3 now state that exception, and the author should confirm it together with D3. [triage: accept?; blocks phase 2] |
| D4 | §9.2 | How ρ_i^obs of nonlinear derived quantities is propagated along the lineage is not specified; with first-order linear propagation, even a correct release may trigger the data-side constraint check. **Partly settled by computation, see en/compute-D4.md.** ρ_i^obs of a derived quantity is propagated as the half-width of a guaranteed enclosure over the rounding box of its read inputs along the lineage (interval arithmetic with outward rounding, intersected with the mean-value form; §9.2, a new rule to be confirmed by the author); first-order propagation is not used, because it is not a bound (on the fixtures a correct release exceeded it at rates up to 2.5·10⁻³). The enclosure is exact for linear relations, gave 0 false triggers in 12 × 10⁶ correct releases (3 significant digits and fixed decimals, including decimal-boundary crossings), and caught every value shifted by at least twice the larger of the bounds of the correct and of the shifted release (the triage criterion "shifted by ≥ 2× the bound" is well posed only with that larger bound). Open for the author: a constraint whose enclosure is unbounded because a lineage step divides by, or takes the logarithm of, a box containing 0 (possible for a read value of 0 (fixed-decimal formats) or for a difference whose box straddles 0 (any format: 1.00 − 1.00 in 3-significant-digit format has the box [−0.01, 0.01]); it did not occur on the fixtures). Options: the constraint is uncheckable and passes vacuously, or a contract that declares a constraint over a derived quantity whose format admits such a box is rejected at locking. [triage: compute; blocks phase 2] |
| D5 | §2.1, §9.2 | After a bin is excluded from a free-ω count shape, how the N_decl of the sub-shape is declared is not specified. [triage: accept?; blocks phase 0] |
| D6 | §8.4 | When the truth MC is weighted, it is not specified whether the "resample at the size of the data" of G8 pseudo-data samples by weight or unweights; with negative weights neither is feasible. [triage: defer to phase 3; blocks phase 3] |
| D7 | §2.1, §6.7, §7.3, §8.2, §15.3.9 | **Accepted by the author (2026-11-09).** Adopted: P5 is Σ_boot / w ⪯ f·Σ_data everywhere, as already written in §2.1, §6.7, §7.3, §8.2 and §15.3.9 (settled by computation); no further body change. The condition of P5 is written as Σ_boot ⪯ f·Σ_data in §2.1 ("P5" item), §6.7 (last bullet of the bootstrap budget) and the §15.3.9 case "P5 fails when Σ_boot exceeds f·Σ_data", and as Σ_boot / w ⪯ f·Σ_data in §2.1 ("Use" item), §7.3 ("Conservative treatment"), §8.2 (P5 row) and the §15.3.9 case "0–4 of 60 sets do not converge". w ≈ 0.891 by default, so the two forms differ by about 12% (up to 47%) in the P5 margin. The majority, and the §15.3.9 non-convergence case, support /w. Proposed resolution (adopted): /w everywhere: §2.1 "P5 requires Σ_boot / w ⪯ f·Σ_data (w per §7.3, with ε̂⁺)", §6.7 "P5 requires Σ_boot / w ⪯ f·Σ_data (§2.1, §7.3)", §15.3.9 "when Σ_boot / w exceeds f·Σ_data". **Settled by computation, see en/compute-D7.md**: /w everywhere. Only Σ_boot / w ⪯ f·Σ_data bounds the bootstrap-noise term actually used in σ_tot to a share f/(1 + f) of the variance in every direction (the guarantee of §6.7); the raw form lets it reach (f/w)·Σ_data and, in a linear-Gaussian toy, broke the guarantee in 24–96% of its passes when P5 was near binding. At the default B ≥ max(500, 50p) the two forms give the same decisions. §2.1 ("P5" item and the reuse after the fit), §6.7 and §15.3.9 are now written with /w (Appendix E). See also D82. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D8 | §2.1 | The object rejected when the condition still does not hold after merging is written as "that observable" in one place and as "the contract" in another. [triage: accept?; blocks phase 2] |
| D9 | §6.7, §8.5, §7.3 | Each G2 toy uses an independent bootstrap set, but the bootstrap budget formula of §6.7 has no n_G2 term, and the enumeration of the non-overlap check lists only G6. The list in §7.3 "Toy data and V̂" of toys that use an independent bootstrap realization likewise omits the G2 toys. [triage: accept?; blocks phase 2] |
| D10 | §5.2, §2.1 | The decision on N_d,c at lock time uses the design-stage estimate of V_MC, but V_MC belongs to the plan, which is not locked. [triage: accept?; blocks phase 2] |
| D11 | §10.1 | The content list of `calibration-result` does not list k, k₀ and the list of unused observables (§5.2, §9.5 require them to be written into the result). [triage: accept?; blocks phase 0] |
| D12 | §2.1 | In the numerical example of G7, the baseline with V̂ frozen is written as "0.000" (original file §2.1: "rises from 0.000 to 0.033"). The reviewer of the v7.37.4 regression record derives by construction that it should be 0.01; the original file has no value 0.01, and this inference is not in the original file either; to be confirmed by the author. **Settled by computation, see en/compute-D12.md.** With V̂ frozen, the refit deviations have covariance exactly Σ_MC, so T ~ χ²_{d(K−1)} and the false-alarm rate is exactly 0.01 (simulated, 10⁴ repetitions: 0.0104 [0.0085, 0.0126] for d = 1, 0.0105 [0.0086, 0.0127] for d = 3); "0.000" is wrong and the reviewer's 0.01 is right. The regenerated value 0.033 depends on a setup the original file does not state, and it is not reproduced within its 95% interval (0.029 for d = 1, 0.042 for d = 3 at p = 50, B = 2500, K = 10, Σ_MC = 0.1 Σ_data). The sentence of §2.1 (ii) now states that setup, and that the extra spread grows with p only at fixed B. Open: only the wording, for the author to confirm. [triage: compute; blocks no phase] |
| D13 | §10.2, Appendix C | **Merged into D63; accepted by the author (2026-11-09).** The tests come with the definition of the lookup in D63: Appendix C "Test scope" and §15.3.12 now require exhaustive tests of the lookup, to be added to the reference implementation. The general principle "outcome already determined" is implemented by the caller; the reference implementation adds no tests for it. See also D63, D69. [triage: merge into D63; blocks phase 0 (through D63); accepted by the author 2026-11-09] |
| D14 | Appendix A | **Accepted by the author (2026-11-09).** Adopted: the editorial resolution; Appendix A is kept, and code uses section-qualified identifiers for the symbols listed here (now stated in the introduction of Appendix A); no rule changes. The P2 use of N_obs is renamed n_c by D77. Symbol clashes: s_j and s_i (and the θ-noise s_i of P5, §8.2 note 3); κ (the validation configuration, and the θ-noise κ_i of P5); R (the rounding-step matrix, the correlation kernel of V_model, the number of efficiency-map replicas in §6.7); m (the size of the G8 family, the number of retained directions in §6.7, the number of derived quantities sharing a rounding in §2.1, the number of alternative hypotheses of §9.4); N_obs denotes both the number of observables (P2, see D77) and the observed total of a shape; A (the fit operator, and the number of absorbed models of the model-ensemble component of §5.4); f (the MC fraction of P5, the relative systematic proportion of §2.1, the toy scaling m*/τ of §6.6, the kernel amplitude f_c of §5.4); c (the shift-mode threshold, a correlation coefficient in §2.1, the observable-group index of §5.4, the condition c of §3.1); S (the standardization matrix, the singular values in §6.7); d (the number of calibration parameters, also d_θ in §9.3, and the comparison node d of §3.4); F (the number of folds, and the distribution functions F₃, F_{k+2} of §7.3); e (the reference edge, the MC errors e_nom, e_hi, e_g, e⁽¹⁾, e⁽²⁾, the direction e of the §8.7 Ĉ_r row); p (the bootstrap dimension, the shape probability vector, the target density of reweighting); ε (the non-convergence rate of §7.3 and §8.4, an efficiency in §2.1 and §8.5, the efficiency map of §6.7); w (the replacement factor of §7.3, the event weight of §2.1 and §6.7, the surrogate-model weights w_j(θ) of §6.7); C (the number of channels in §6.7, the covariance C of the θ-noise item of P5); k (k* of §7.3, the Pareto k of G4, the observable index, the number of validation directions); K (the G7 refits, the seed sets for σ_noise, the shape bins of §8.7 note 3); n (the converged members in ε̂, the leave-one-out n, the number of Ĉ_r toys); B (the bootstrap sets; B_m, B_y, B_map); r (the rank of Σ_MC in G7, r of §5.4); τ (the effective count of §6.6) and τ̂ (the partial-pooling spread of §15.3.18); C̃⁽⁰⁾ of the rounding condition (§2.1, §8.7; data noise only) and C̃_r⁽⁰⁾ of the declaration check (§9.2); S and Ũ_⊥ written without distinction for the validation side (§9.2) and the calibration side (V_cc⁻¹ in A, §9.2 "Covariance of the residuals"). Renamed in the English primary edition (Appendix E): the local efficiency-map coefficients ψ → φ_loc (§6.7); n_dp of the full construction → n_eval (§6.7); m, N, F of §14.1 → m_blk, N_ev, N_tot, F_G5; g = ∂θ̂/∂φ of §15.2 written out. [triage: accept; blocks no phase; accepted by the author 2026-11-09] |
| D15 | Appendix C, reference implementation | **Accepted by the author (2026-11-09).** Adopted: the I6 text of Appendix C.4 now also states "nor higher than the own grade (for resolved inputs)", which the reference implementation already tests. For resolved inputs the reference implementation additionally checks "the effective grade is not higher than the own grade" (message labeled I6); the text of I6 does not list this. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D16 | §15.3.17 | **Accepted by the author (2026-11-09).** Adopted: four shapes, as listed; §15.3.17 is already written so; no body change. The original text says "all three shapes must be tested" but lists four; this edition writes four, as listed. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D17 | §19, §6.7 | **Accepted by the author (2026-11-09).** Adopted: the per-observable rule of §6.7; §6.7 and §19 are already written so; no body change. §19 says "discard ≤ 1% of the trace", while §6.7 explicitly prescribes a per-observable decision, not the trace over all; this edition follows §6.7. [triage: accept; blocks phase 3; accepted by the author 2026-11-09] |
| D18 | §7.3, §8.7 | **Accepted by the author (2026-11-09).** Adopted: the §8.7 scope in §7.3 and §8.7, as already written; no body change. Acceptance scope of per-fold convergence in cross-validation: the original §7.3 writes only leave-one-out with n ≤ 20, while §8.7 covers the F folds adopted by the plan and leave-one-out with n > 20; this edition follows §8.7 in both places. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D19 | §6.6 | For the interval toys of G8 pseudo-data, the original text says "per the previous item", which literally refers to the power toys; following the interval-toy item of the same section (which contains "the interval toys of each G8 pseudo-data set"), this edition writes it as per item 2 (interval toys); to be confirmed by the author. [triage: accept?; blocks phase 2] |
| D20 | §5.2 clause 3 | **Accepted by the author (2026-11-09).** Adopted: the edition's reading (the excluded bin goes on the unused list per clause 7, and the remaining bin enters as a Poisson count), as already written in §5.2 clause 3 item 5 and §15.3.6; no body change. The original text "when K′ = 1, the remaining bin enters as a Poisson count as usual and is listed per this section" does not say which item is listed or where; this edition interprets it as the excluded bin being put in the unused list per clause 7. See also D38. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D21 | §5.2, §14 | **Accepted by the author (2026-11-09).** Adopted: `calib_data.py` for the recomputations at the fit point (rounding, σ_i⁽⁰⁾, N_exp, n_min, block conversion) and `calib_contract.py check` for the N_d,c redo (clause 6); the executor paragraph of §5.2 is aligned with clause 6, and "until D21 is confirmed" is removed from the `calib_fit.py` row of §14. Which implementation `calib_fit.py` calls for the recomputation at the fit point after fitting: the "executor" paragraph before the table writes the `calib_data.py` implementation (the `validation` row), while clause 6 writes that the N_d,c declaration check is redone by the same implementation of `calib_contract.py check`. A possible reading: the recomputation of rounding, σ_i⁽⁰⁾, N_exp, n_min and the block-conversion condition uses `calib_data.py`, and the redo of the N_d,c declaration check uses `calib_contract.py check`; this edition wrote both places as in the original text. The §14 table listed neither call: the `calib_fit.py` row had no call for the N_d,c redo at θ̂, and the `calib_contract.py check` row mentioned only the lock-time decision. Following clause 6, which is the only place that names the implementation of the N_d,c redo, the English primary edition adds that call to both rows (Appendix E); the conflict between the executor paragraph and clause 6 is resolved by this acceptance. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D22 | §9.5 failure records | **Accepted by the author (2026-11-09).** Adopted: `final` when k = 0 and the data-side constraint check is triggered (failure takes precedence), as already written in §9.5; with D64, the "States of failure records" of Appendix C.1 now say the same. In the original text "when k = 0 and the data-side constraint check triggers, it is `final` per the previous row", "the previous row" literally refers to the item "k = 0 determined before opening" (no record written), which does not agree with "failure takes precedence"; following "failure takes precedence", this edition writes "`final` per 'the decision fails' above". Merged here: D64 (the C.1 wording that implements this decision). [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D23 | Appendix C.1 | **Accepted by the author (2026-11-09).** Adopted: the C.1 text of this edition, as already written; no body change. The original C.1 lists only the failure of the ratio test in cross-validation before T_cv is computed, and writes "the result is then already decided by rule 0, 1, 2 or 3b"; but a failed ratio test before holdout opening likewise has no validation read (§9.5 table), and "outcome already determined" can also be decided via 3c, 3e or a capped upstream (§15.3.12). This edition adds to C.1 the failure of the ratio test before holdout opening (per the §9.5 table), and writes the reason as "rule 0, 1, 2, 3b or the 'outcome already determined' lookup". [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D24 | §15.3.11 | **Accepted by the author (2026-11-09).** Adopted: k₀ = 0 in §15.3.11, as already written; no body change. The original text of this case says "k = 0 determined before opening", a term defined in §9.5 (i.e. k₀ = 0); following the wording of Appendix C.1, this edition changes it to k₀ = 0, with no change in meaning. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D25 | §2.1 Externally released uncertainty tables | In the original text "the statistical component of `expected` is replaced by the value this workflow recomputes per the previous item", "the previous item" is literally the event-level bootstrap; following "statistical errors are always recomputed from the prediction at θ_ref per the above" in the same paragraph, this edition writes it as count-type errors and the bootstrap; to be confirmed by the author. [triage: accept?; blocks phase 2] |
| D26 | §7.3, §9.2, §9.3, §15.3.9 | **Accepted by the author (2026-11-09).** Adopted: the corrected numerical examples and the stated setups listed below, which are already in the body; no further body change. Numerical examples corrected in the body of the English primary edition after recomputation by the editors (old → new): (1) §7.3 "Non-converged pseudo-data are not counted as not covered": the overall false-alarm rate of G8 rises "to about 0.2" → "to about 0.15" (full level, d = 3, N_c = 353, ε = 1%, non-converged sets counted as not covered in every parameter and at both levels; Monte Carlo with the Holm family of §8.4 and independent parameters: 0.145; 0.152 if the twelve coverage tests are treated as independent; at most 0.163 by the union bound). (2) §7.3 "Ratio test", naive thresholds: "overall false-alarm rate of G8 0.45–0.85 at ε = 1%" → "about 0.3–0.5 for 'observed fraction > 1%' and 0.86–1.0 for 'any one'" (n_req = 2N_c with the N_c of the §8.4 table, NegBin; 0.32–0.46 standard, 0.47–0.50 full; 0.86–0.92 standard, ≈ 1.00 full). The preceding "about one half" holds for "observed fraction > 1%"; "any one" triggers with 0.86–1.0 for G8 and 0.096 for G7; the body sentence is left as in the original text. (3) Same place: "0.105 for G7 at K = 10" → "0.096" (1 − 0.99¹⁰ = 0.0956; 0.105 is 1 − 0.99¹¹); the same correction is made in the §15.3.9 G7 negative control ("failing whenever any set does not converge gives about 0.105" → "about 0.096"). (4) §9.2 rank condition: "the difference of two observables with correlation 1 − 10⁻⁷ has standardized variance 10⁻⁷" → the smallest eigenvalue, i.e. the variance along the unit direction (x₁ − x₂)/√2, is 10⁻⁷ (the variance of x₁ − x₂ itself is 2 × 10⁻⁷). Not corrections but stated setups, recomputed and unchanged: the §9.2 size example (5.7 × 10⁻¹⁰, 6.9 × 10⁻⁴, 0.42, 0.997) holds for α = 0.05, d_l = 3 and C_r = 10, now stated (the original "d = 3" is read as d_l = 3, the only reading that reproduces the numbers); the §9.3 rounding ratio 2 × 10⁶ holds for ρ = 0.1σ_p2, now stated; the §7.3 k* values hold for NegBin counting the non-converged members before the n_req-th converged one, now stated. No conclusion drawn from these numbers changes. [triage: accept; blocks no phase; accepted by the author 2026-11-09] |
| D27 | §5.2 clause 9 item 9, §14 `calib_contract.py check` row, §2.1, §9.2, §15.3.7 | **Accepted by the author (2026-11-09).** Adopted: the proposed qualifier, in §5.2 clause 9 item 9 and in the `calib_contract.py check` row of §14. Clause 9 item 9 and the §14 row reject a contract in which all observables of an "exact relation determined by the observed component totals" are used together, with no qualifier. §9.2 forbids this only when the event sample belongs entirely to the validation data (with calibration observables the weights are known before lock and the relation is declared as N_d as usual); §2.1 lists relations determined by known component totals as legitimate N_d,c constraints; §15.3.7 requires the case with calibration observables to be accepted. A checker built from §5.2 would reject every cross-validation contract that uses all of them. Proposed resolution (adopted): add to clause 9 item 9 and to the §14 row "in an event sample that belongs entirely to the validation data (§9.2); in samples that contain calibration observables the relation is declared as N_d or N_d,c instead". [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D28 | §6.7 "Two efficiency map modes", §6.6, §8.2 P5 and note 3, §8.7, §14, §15, §17, §19 (C23), Appendix A | **Accepted by the author (2026-11-09; revised 2026-11-09 after en/research-D28.md).** Revision adopted by the author's decision of 2026-11-09 ("proceed as recommended", with the note below; en/research-D28.md; synthetic fixture with g4sim's map and replica laws, Geant4 not run), written into §6.6 (common random numbers, the response-sampling row, check item 1), §6.7 (the MC-error table row and "Two efficiency map modes"), §8.2 (P5 row, note 3 fifth item), §8.7, §14 (`calib_design.py`, `calib_likelihood.py`, `calib_propagate.py`), §15.2, §15.3.1, §15.3.19, §17, §19 (C23) and Appendix A. The accepted shared seed is kept as the default and made conditional, and the way its map error is estimated is replaced. Under the shared seed, g4sim's replicas, keyed by each map's SHA-256, are independent across design points (g4sim's own code: correlation 0.013 ± 0.079 against a true 0.886). So they cannot give the cross-point covariance that this entry requires the map term to contain: propagated through the surrogate model they gave 0.37–0.50 of the map variance and a G6 size of 0.06–0.54 at α = 0.01, and G8 failed in every configuration; they also make a φ_map shared across θ undefinable. The revision: (1) With the shared seed, the map term comes from workflow-side joint-pattern replicas (a Bayesian bootstrap of the shared photons with Jeffreys pseudo-counts, keyed by the scan, with g4sim's Dirichlet(k + ½) as the marginal at every design point), or from the analytic covariance of the same pattern table for observables linear in ε. φ_map is then one nuisance shared by the scan. (2) A plan may instead give each design point its own seed, using g4sim's replicas unchanged with one φ_j per design point, when the new θ-noise item of P5 passes for it. Between the oracle arms it is more efficient for the level (RMS of θ̂ 0.77–0.99 of the shared seed and G6 power higher by 0.08–0.41 at equal strength); with the per-point φ_j profiled as required, the RMS was 0.88–1.20 against 1.01–1.15 for the shared seed with profiled joint-pattern replicas (lower in four of the six configurations, higher in P1d1 and P1d0), and the G6 power higher by 0.04–0.34. Its surrogate model's slope and curvature noise was 1.05–5.7 times larger. At 10⁷ photons per mapping run it failed G8 on coverage in one of two configurations where the shared seed passed. (3) In both cases the map term is profiled through the surrogate model with θ, not held fixed (held fixed per §7.3, independent seeds left a bias of 0.12–0.52σ). (4) Comonotone coupling, a g4sim scan key, coupled replicas with independent seeds, and interpolating surrogate models are rejected. (5) Fallback without a pattern table: the shared seed with the nearest design point's replicas (full correlation assumed), held fixed per §7.3, not profiled. The θ-noise of the surrogate model, a separate finding (§8.2 note 3, fifth item: s_i ≤ 0.25, κ_i ≤ 0.05, design values of §8.7 under `provisional-thresholds` until calibrated), limits coverage in this mode independently of the replicas. **Note** (§6.7 "Two efficiency map modes", as the author asked): under the shared seed the true map errors of the design points are highly correlated (≈ 0.89 between adjacent points at a history divergence of 0.1 per step; 0.59–0.99 over the divergences studied), but g4sim's replicas are essentially uncorrelated (0.013 ± 0.079); this is why this workflow draws its own scan-keyed replicas. Open points of the revision: D85. Earlier acceptance (2026-11-09, kept as the default case): "independent" means independent of the seeds of the other uses (G7, G8, validation); within a θ scan the mapping runs share a seed (the same `logical_run_seed` in every mapping-run card, not through `geant4_run.py scan`, which gives each point its own seed), so the map errors are correlated between design points and must not be treated as independent. This resolved the conflict between the table row and first sub-item of §6.7 (a new seed per design point) and its later sub-item (one seed per scan). The same event interval [0, N_map), until then a rule settled by plugin source (en/g4sim-S7-check.md D28) outside that acceptance, is part of the revised text the author adopted. The requirement that V_emu not treat the map errors as independent is now carried by the map term U(θ)φ_map of §6.7. [triage: accept; blocks phase 3; accepted by the author 2026-11-09; revised 2026-11-09] |
| D29 | §5.5 condition 2, §8.2 G9 | The linearity test of shift mode is not operationally defined: the measure of "symmetry within 30%", whether the 2 ± 0.3 ratio is taken per side or on the symmetric average, how both apply to vector θ, and the threshold of "near-zero response" where the contract-locked absolute tolerance replaces the ratio. G9 is mandatory and its failure forces profile mode. Proposed resolution (proposed, to be confirmed by the author): for each component i with \|Δθ̂_i(±1σ)\| above the absolute tolerance, \|Δθ̂_i(+1σ) + Δθ̂_i(−1σ)\| / (\|Δθ̂_i(+1σ)\| + \|Δθ̂_i(−1σ)\|) ≤ 0.3, and Δθ̂_i(±2σ)/Δθ̂_i(±1σ) ∈ [1.7, 2.3] for each side separately; components below the tolerance use the absolute test only. See also D52. **Partly settled by computation, see en/compute-19-2.md**: the relative tests are replaced by one absolute, one-sided measure per component, Δ_i = [(Σ_l c2,il)² + Σ_l (2c2,il² + 4c1,il c3,il + 14c3,il²)] / s_i² ≤ t_lin = 0.06 (§5.5, a new rule to be confirmed by the author), computed from the four G9 refits with the symmetric response a_il; no near-zero switch is needed. The relative tests of the proposed reading rejected harmless or conservative nonlinearity with probability 1 and passed an expansive cubic response with 95% coverage 0.922; the 30% symmetry test was the only failing test in 0.05% of repetitions. An alternative with the same performance keeps two absolute measures (\|c2,i\|/s_i ≤ 0.15 and the expansive odd part 6 max(0, sign(a_i)·c3,i)/s_i ≤ 0.10), if the author prefers separate even and odd tests. Open: more than one shift-mode φ, confirmation on the toy detector, the refit reproducibility check (§8.7 note 5). [triage: accept?; blocks phase 2] |
| D30 | §2.1 "Finite simulation statistics in non-Gaussian blocks", §6.6, §6.7, §8.7 note 4, Appendix A | The MC auxiliary binomial likelihood for weighted MC is not defined: how the effective event count n_eff and the effective pass count are obtained from (Σw, Σw²) of pass and fail and their cross covariance, and how a non-integer n_eff is handled in the toy draw Binomial(n_eff, ε̃) of §6.6. n_eff is not in Appendix A. The §8.7 acceptance of the effective-count approximation cannot be run until this is fixed. Proposed resolution (proposed, to be confirmed by the author): the author defines the conversion (for example n_eff = (Σw)²/Σw² over pass ∪ fail, pass count n_eff·Σw_pass/Σw) and the non-integer handling before implementation phase 2. **Settled by computation, see en/compute-D30.md** (new rules, to be confirmed by the author). n_eff and k_eff are the variance-matched effective counts n_eff = ε̂(1 − ε̂)W²/[(1 − ε̂)²S_P − 2ε̂(1 − ε̂)V_PF + ε̂²S_F], k_eff = n_eff ε̂ (Kish over pass ∪ fail only when ε̂ = 0 or 1); Kish over pass ∪ fail and separate Kish counts fail the §8.7 acceptance when Σw²/Σw differs between pass and fail. In toys a non-integer n_eff is handled by randomized rounding, n* = ⌊n_eff⌋ + Bernoulli(n_eff − ⌊n_eff⌋), k* ~ Binomial(n*, ε̃), fitted with the same likelihood. The acceptance (pull = signed root of the likelihood ratio, now stated in §8.7 note 4) holds for k_exp ≥ 30 and Δ_sk ≤ 0.1 computed from design values (175 of 175 configurations on fresh seeds); outside, the approximation is unvalidated (§2.1). Not part of D30 and still open with D33: the reuse of the toy auxiliary measurement across θ for a θ-dependent efficiency template. [triage: compute; blocks phase 2] |
| D31 | §6.6 "New seed" and "Check", §14.1 "Allocation function" | "New seed" allows either a non-overlapping event interval or a different `logical_run_seed`, but check 1 and 2 of §6.6 compare event intervals only, although the plan records `logical_run_seed`. An implementation of the check that compares intervals alone rejects plans that reuse an interval under a different `logical_run_seed`, including every plan built with the allocation-function example of §14.1, which gives each (study, use, ensemble[, subset]) its own `logical_run_seed`. Proposed resolution (proposed, to be confirmed by the author): in both checks, two intervals overlap only when they have the same `logical_run_seed` and intersect as ranges of global event numbers; the check compares (`logical_run_seed`, global event interval) pairs. §14.1 now states that its example presupposes this reading. **Partly settled by plugin source** (`core/simulation/seeds.py`, `SimSeed.hh`, `core/simulation/rng.py`; en/g4sim-binding-check.md (B), A1, A3): event i of logical run S is seeded (H(S, i, 0), H(S, i, 1)), so for the Geant4 layer the proposal is right, and the checks of §6.6 now compare (`logical_run_seed`, global event interval) pairs. The response layer takes its Philox key from `run_seed` and `replica` of `response-pipeline/1`, not from S, so §6.6 now also requires `run_seed` = `logical_run_seed` in every evaluation and pairwise distinct `logical_run_seed` values (H takes values in [1, 2³¹ − 1]); the allocation example of §14.1 gives each block its own seed, because one seed carries at most 2³² events, and no longer presupposes this entry. The response-layer requirement, which this workflow imposes because g4sim has no tie between the two seeds, was accepted by the author on 2026-11-09 with the other plugin-source rules (Appendix E, "Author's acceptance of 2026-11-09 (plugin-source rules, D28 choices, D86, D87)"), its extension to the digitization job included; no open part of this entry remains. g4sim S7 (v0.63.0) does not change this: response keys still come from `run_seed` and `replica` of `response-pipeline/1`. It adds that a non-zero `replica` also selects Dirichlet replica r of a mapped efficiency map, so §6.6 now also requires `replica` = 0 in every evaluation (en/g4sim-S7-check.md M2). g4sim S8 (v0.64.0) adds a second document with its own `run_seed` and `replica`, the `g4sim-digi-job/1`: its keys are computed in Python by `digitize.job_with_keys`, and `g4sim_digi` uses them without reading `run_seed`, so the tie is extended to the job and its keys are recomputed by `calib_design.py` (§6.6); a job with conditions, which `job_with_keys` refuses, carries no keys and runs in Python only. On this path a non-zero `replica` changes the keys but not the map, whose ε comes from the job (en/g4sim-S8-S9-check.md W9, W10). [triage: plugin fact; blocks phase 3] |
| D32 | §5.2 clause 10 item 2 | **Accepted by the author (2026-11-09).** Adopted: the proposed wording, in §5.2 clause 10 item 2. "At least one alternative hypothesis" has no mode qualifier, while in mode `none` P7 and V do not apply (§8.1) and the `validation` block and clause 7 are qualified by "when the validation mode is not `none`". Whether a mode-`none` contract without an alternative hypothesis is rejected is not decided. Proposed resolution (adopted): "2. When the validation mode is not `none`: at least one alternative hypothesis." [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D33 | §2.1 "Composition of the likelihood" | **Accepted by the author (2026-11-09).** Adopted: the proposed formula and nuisance list (φ_P with Σ_φP, the MC auxiliary terms over γ, free ω), in §2.1 "Composition of the likelihood". The reuse of the toy auxiliary measurement across θ (D30) is not decided by this. The joint likelihood formula sums a diagonal penalty (φ_l − φ_l⁰)²/σ²_φl over all φ, although shift-mode φ are not in the likelihood (§5.5, §6.6) and profile-mode φ may have correlated constraints (§5.2 clause 5, §5.5, §10.4); it omits the constraint terms of the MC nuisances of non-Gaussian blocks (BB-lite, auxiliary binomial, with m_MC as auxiliary measurement) and does not mention the free normalizations ω; "three classes of nuisance" is fewer than β contains. Proposed resolution (adopted): −2 ln L = Σ_b −2 ln L_b(y_b \| μ_b) + Σ_b′ −2 ln L_b′^aux(m_MC,b′ \| γ_b′) + Σ_k ν_k² + Σ_j η_j² + (φ_P − φ_P⁰)ᵀ Σ_φP⁻¹ (φ_P − φ_P⁰), with φ_P the profile-mode φ, the second sum over the MC nuisances of non-Gaussian blocks, and the ω free; adjust the list of nuisances accordingly. See also D30: how the toy auxiliary measurement of a θ-dependent efficiency template is reused across θ (§6.6 "Reuse of the perturbation") belongs to this composition and is not settled by en/compute-D30.md. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D34 | §2.1 "Event-level parametric bootstrap", §7.3, §8.1 | With several event samples (which share no events), it is not specified whether the bootstrap dimension p, and hence B ≥ max(500, 50p), is per sample or over all shared-event summary statistics, nor which p enters the (B − p − 2)/(B − 1) reporting factor and the (p − d)/B bias statements of §7.3 and §8.1. Proposed resolution (proposed, to be confirmed by the author): p and B per sample; the bias statements use the p of the sample concerned. [triage: accept?; blocks phase 2] |
| D35 | §2.1 "Rounding" (σ_i⁽⁰⁾ = 0, ρ_i = 0) | **Accepted by the author (2026-11-09).** Adopted: "In modes `holdout` and `none`, …", in §2.1 "Rounding". Calibration observables with σ_i⁽⁰⁾ = 0 and ρ_i = 0 are removed before standardization only "under holdout"; mode `none` has the same observables and the same division by σ_i⁽⁰⁾ = 0 but no rule (cross-validation rejects them, clause 9 item 13). Proposed resolution (adopted): "In modes `holdout` and `none`, …". [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D36 | §2.1 evaluation points (rounding, N_exp), §5.2 clause 9 | **Accepted by the author (2026-11-09).** Adopted: the proposed evaluation points, including the profile-mode φ axes, in §2.1 "Rounding". The evaluation points are θ points × (ν, η nominal and ±2σ along each nuisance axis); profile-mode φ also move the prediction (σ⁽⁰⁾, N_exp, expected counts), but whether φ axes are included is not stated, so implementations find different worst cases. Proposed resolution (adopted): "At each θ point, ν, η and profile-mode φ take their nominal values, and also ±2σ along each of these nuisance axes in turn (only one moved at a time)." [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D37 | §2.2, §5.2 `parameters[]` | The criterion by which the checker decides that a conditioning parameter ψ has a "non-negligible uncertainty" (and must be listed as φ) is not specified, so the rule cannot be executed by `calib_contract.py check`. Proposed resolution (proposed, to be confirmed by the author): the effect on θ̂ propagated via A is ≤ 0.1σ_tot^design, as for the class-discretization bound of §5.4. [triage: accept?; blocks phase 1] |
| D38 | §5.2 clause 3 item 5 | **Accepted by the author (2026-11-09).** Adopted: the proposed wording (alr/ilr, K′ = 1, whole shape unused), in §5.2 clause 3 item 5. "For shapes conditioned on the total or represented with alr, when K′ < 2 there is no link coordinate": ilr shapes are equally affected, and K′ < 2 can only mean K′ = 1 here (K′ = 0 is the whole-shape exclusion). Proposed resolution (adopted): "for shapes conditioned on the total or represented in alr/ilr coordinates, when K′ = 1 there is no link coordinate, and the whole shape is left unused". See also D20. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D39 | §5.4 correlation kernel | For C_{c_i c_j} ≠ 0 between observable groups with different correlation lengths ℓ, the form of ρ_{c_i c_j} (which ℓ or M applies) is not specified; the numerical positive-definiteness check then decides acceptance by implementation choice. Proposed resolution (proposed, to be confirmed by the author): the author specifies a construction that preserves positive definiteness (for example a convolution or a linear model of coregionalization). [triage: author decision; blocks phase 2] |
| D40 | §6.7 "After the fit, recompute at β̂ instead" | It is not stated what the post-fit Σ_MC and Σ_data are used for, or whether the matrix condition of P5 is decided again at β̂ and can fail (§2.1 says Σ_boot is not re-estimated after the fit). Proposed resolution (proposed, to be confirmed by the author): "After the fit, Σ_MC and Σ_data are recomputed at β̂ (θ block) for G7 and for reporting; P5 is not decided again." [triage: accept?; blocks phase 2] |
| D41 | §3.3, §6.7, §7.1, §8.2 G4 | The event set over which N_eff,k is computed for observable k (all events of the sample, the events entering observable k or its bin, or, for tail functionals, the "determining region", which is not defined) is not specified, although P5 and G4 decide on N_eff,k ≥ N_req,k. Proposed resolution (proposed, to be confirmed by the author): the events that enter observable k (its bin for counts); the author defines the determining region of tail functionals. [triage: accept?; blocks phase 1] |
| D42 | §6.7, §8.2 P5 row and note 3 | §6.7 says P5 also requires V_MC,kk ≤ f·V^unc_data,kk for each observable; the P5 row and note 3 of §8.2 do not list this condition. The two agree only when V_MC,kk = s_k²/N_eff,k, not for surrogate or re-digitization noise, and the condition has no meaning for non-Gaussian bins, which are not in V_MC. Proposed resolution (proposed, to be confirmed by the author): either add "V_MC,kk ≤ f·V^unc_data,kk for each Gaussian-block observable" to the P5 row and note 3, or delete the clause from §6.7. [triage: accept?; blocks phase 1] |
| D43 | §6.7 local dimension reduction | **Accepted by the author (2026-11-09).** Adopted: the threshold τ_num (standardized units), in §6.7 "Propagation in each study". Local dimension reduction is forbidden "whenever U_⊥ has a non-negligible component" in Poisson and binomial blocks, with no threshold (the 1% rule of the same item cannot be meant, because the discarded part has nowhere to go in these blocks). Proposed resolution (adopted): "whenever U_⊥ has a component in these blocks above the numerical tolerance τ_num (in standardized units)". [triage: accept; blocks phase 3; accepted by the author 2026-11-09] |
| D44 | §6.7 efficiency map, §8.2 P3 row | **Accepted by the author (2026-11-09).** Adopted: remedy level plan in the mode where the map varies with θ, in the P3 row of §8.2 and in §6.7. The remedy for a P3 miss caused by efficiency-map error is to increase the photon number of the mapping run: a contract change in fixed-map mode, but a plan change in the mode where the map varies with θ. The P3 row of §8.2 lists only the remedy level "contract". Proposed resolution (adopted): state that in the mode where the map varies with θ the remedy level of P3 is plan. [triage: accept; blocks phase 3; accepted by the author 2026-11-09] |
| D45 | §7.3, §7.4, §8.2 G1 | The definition of non-convergence (30 iterations, ln det diagnostic) does not say (a) whether a non-converged member of a Class 2 ensemble (G7, G8, Σ_boot, Ĉ_r, T_v reference, power, interval toys) is first refitted with multi-start, as required for Class 1 fits, cross-validation toys and scan points, nor what a multi-start refit adds when §7.4 already starts every fit from ≥ 2d points; nor (b) whether a member whose minimization fails the EDM criterion of G1 counts as not converged. Both change X and therefore the ratio test, w(ε̂) and the toy p-values. Proposed resolution (proposed, to be confirmed by the author): every fit, single or member, uses the starts of §7.4 in each iteration; a fit is not converged if any of the three criteria (EDM of G1 at the last iteration, 30 iterations, ln det) still fails after one further multi-start round. §7.4 (tagged, D57) now runs §7.3 from each basin representative after one multi-start, and a fit with no converged endpoint is not converged; the proposal above must be reconciled with it when D45 is decided. [triage: accept?; blocks phase 2] |
| D46 | §7.3, §8.5, §6.7, §8.2 note 9 | When the linearity check fails and G6 or G2 falls back to full toys (§8.5), no non-convergence rule is given for these toys (they are not in the Class 2 list of §7.3, and the "statistic ≥ observed" counting of testing ensembles would make G6 pass more easily, the anti-conservative direction for a mandatory gate); it is not stated whether their independent bootstrap is regenerated in the iteration, and the bootstrap budget of §6.7 assumes the G6 toys do not iterate. It is likewise not stated whether locally linear cross-validation toys (§8.5) can be non-converged, while §7.3 speaks of multi-start refitting of their fold fits. Proposed resolution (proposed, to be confirmed by the author): the author defines the counting direction (non-converged full G6/G2 toys counted as statistic ≥ observed is not acceptable for a goodness-of-fit gate), the bootstrap handling and the budget term. [triage: accept?; blocks phase 2] |
| D47 | §8.2 G3, §7.5 | "The 68% region of θ̂" of G3 is not defined: the joint region q ≤ χ²_{d,0.68}, the box of the per-parameter 68% intervals of §7.5, or the total interval including shift-mode terms and Σ_boot / w. For d ≥ 2 these give different outcomes of a mandatory gate. Proposed resolution (proposed, to be confirmed by the author): the author chooses one; the box of the per-parameter total intervals of §7.5 is the reading closest to the interval construction. [triage: author decision; blocks phase 2] |
| D48 | §7.5 | The default is the profile likelihood ratio with the other θ_j profiled (a multi-parameter case), while a later item requires a toy-calibrated construction "in multi-parameter, non-Gaussian or boundary cases". It is not decided whether d ≥ 2 by itself requires the toy-calibrated construction. This changes whether Σ_boot / w is added, whether interval toys and their ratio test exist, and what G8 can detect (§8.4). Proposed resolution (proposed, to be confirmed by the author): "multi-parameter" means a joint region for several parameters, not a one-parameter interval with the others profiled. [triage: accept?; blocks phase 2] |
| D49 | §7.3 "Ensembles for testing" and "Selection effect" | **Accepted by the author (2026-11-09).** Adopted: n = n_req (the total number of toys), in §7.3 "Ensembles for testing". In ε̂ = X/(n + X), n is the number of converged members; in the p-value (#{T_toy ≥ T_obs} + X + 1)/(n + 1), which counts the X non-converged toys in the numerator, n must be the total number of toys (n_req), or the p-value is too large by about (n_req + 1)/(n_req − X + 1) and can exceed 1. The same symbol is not distinguished, and the decision near α depends on it (also for power toys). Proposed resolution (adopted): "where X is the number of non-converged toys and n is the total number of toys in the ensemble, converged and non-converged (n_req; not the n of ε̂ = X/(n + X))". [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D50 | §7.3 "What fails", §14.1 | A failed ratio test of the G7, G8 or Σ_boot ensemble makes G7, G8 or P5 fail (a mandatory gate, `failed` if final), while a failed ratio test of the interval toys (actual data, hence G3, or of G8) or of the V and P7 ensembles gives `incomplete`, because "a numerical failure is not evidence that the data do not fit the model". The two handlings of the same kind of numerical failure, within the same gate G8, are not reconciled; §14.1 treats exceptions as `incomplete`. Proposed resolution (proposed, to be confirmed by the author): the author confirms the difference or aligns the two. [triage: author decision; blocks phase 2] |
| D51 | §7.3 reference-point iteration | It is not stated whether the convergence criterion "the change in θ̂ is < 0.1σ_tot" is per component or a norm, which σ_tot applies to a toy or pseudo-data fit (that of the actual fit or the fit's own curvature), or what "the difference between the two" of the ln det diagnostic compares. Proposed resolution (proposed, to be confirmed by the author): max_i \|Δθ̂_i\| / σ_tot,i < 0.1 between successive iterations, with σ_tot,i from the current curvature of that fit; for the diagnostic, max_i \|θ̂_lndet,i − θ̂_i\| / σ_tot,i < 0.2 between the minimum of the full likelihood and the iterated θ̂. [triage: accept?; blocks phase 2] |
| D52 | §7.5 total interval, §9.2 d_l, §10.4 G_s, §5.5 | The ±1σ shift responses are used without saying which one: the total-interval formula uses "the response Δθ̂_l to a ±1σ shift", d_l and ∂β̂/∂φ_l\|_refit of §9.2 and the columns of G_s of §10.4 are "obtained from the ±1σ refits", while §5.5 allows up to 30% asymmetry between the two signs. The total-interval formula also gives no rule for adding shift-mode terms to a toy-calibrated interval (which takes the shift terms but no Σ_boot / w, §7.5). Proposed resolution (proposed, to be confirmed by the author): use the symmetric difference ½[Δ(+1σ) − Δ(−1σ)] everywhere; for a toy-calibrated interval replace σ_q by the half-width of that interval and omit the (Σ_boot / w)_ii term. See also D29. Note: the linearity measure Δ_i of §5.5 (en/compute-19-2.md) is built from the symmetric difference, whatever is chosen here. [triage: author decision; blocks phase 2] |
| D53 | §8.2 P0, P6 (notes) | **Accepted by the author (2026-11-09).** Adopted: two-sided z_{1−α/(2M)}, in §8.2 notes 1 (P0) and 4 (P6). The Bonferroni z of P0 (d parameters × number of θ′, α = 0.01) and of P6 bound absolute values (\|Δθ_i\|, \|Δm\|), but the text does not say whether z is one- or two-sided. Proposed resolution (adopted): z = z_{1−α/(2M)}, two-sided Bonferroni with M = d × (number of θ′) for P0 and M = the number of held-out points × observables for P6. [triage: accept; blocks phase 1; accepted by the author 2026-11-09] |
| D54 | §8.3 | **Accepted by the author (2026-11-09).** Adopted: the θ block of F⁻¹ over β, the ratio per parameter, and σ_prior = range/√12 for a uniform prior, in §8.3. It is not stated whether R_corr is the θ block of F⁻¹ over all of β (nuisances profiled) or of the whole β, whether σ_post/σ_prior must hold for each θ_i, or how σ_prior is defined for a bounded uniform prior. These change P3 and G5 outcomes. Proposed resolution (adopted): θ block of F⁻¹ over β, per parameter, σ_prior = range/√12 for a uniform prior. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D55 | §8.4 injection points and pseudo-data | The distance of the boundary injection point from the boundary is not given (the interior point has ≥ 2σ_tot^design); the resampling of pseudo-data from the truth MC is not stated to be with replacement, nor whether the number of events is fixed at the data size or Poisson around the expectation for the exposure (which matters for free-ω count shapes). D6 covers only weighted truth MC. Proposed resolution (proposed, to be confirmed by the author): the author specifies the boundary distance and the resampling (with replacement; size per the data's sampling model). [triage: author decision; blocks phase 2] |
| D56 | §8.5 linearity check | **Accepted by the author (2026-11-09).** Adopted: the proposed definitions of Δχ²_full, Δχ²_lin and the end folds, in §8.5. Δχ²_full and Δχ²_lin are not defined (relative to which point), and "the two end folds" of leave-one-out is not defined. Proposed resolution (adopted): Δχ²_full = χ²_full(β̂*) − χ²_full(β̂) and Δχ²_lin the same difference in the linear model, with β̂ the fit point of the actual data or of the fold; the end folds are the first and last fold in the declared order of the observables. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D57 | §7.4, §7.5, §8.7 | The criterion that separates two converged starts into different basins (a distance or Δ(−2 ln L) tolerance) is not specified, nor which basin supplies θ̂ for the gates, the truth point of toys and the reference-point iteration, nor how toys treat multimodality. Proposed resolution (proposed, to be confirmed by the author): the author specifies the tolerance; θ̂ is the global minimum. **Partly settled by computation, see en/compute-D57.md**: separation by the rise of −2 ln L along the segment between the endpoints (τ_bar = max(0.1, 4σ_noise)), admission only of endpoints with σ_tot,i ≤ σ_prior,i, θ̂ = the lowest basin, ties within τ_tie = max(0.01, 4σ_noise) broken in lexicographic order, max(2d, 16) starts, every toy running the same multi-start and taking its own global minimum, and the union of intervals referred to the global minimum and toy-calibrated when `multimodal` (§7.4, §7.5, §8.7 row and note 6; new rules, to be confirmed by the author). The design value of the triage, "max_i \|Δθ_i\|/σ_tot,i > 0.5 and Δ(−2 ln L) > 0.1", is rejected: it merges exactly degenerate basins. Open: (1) the tolerances are design values of §8.7 note 6 and still need calibration in implementation (σ_noise > 0, where the terms max(·, 4σ_noise) were reasoned and not computed; V differing between basins, where the comparison of basins with the full likelihood including ln det V_G was reasoned and not computed, because V is fixed in the toy; the coverage of the toy-calibrated interval; the RICH replica); (2) for the author, the remedy level of G8 under multimodality: the G8 bias test fails on every bimodal variant (the data pick the wrong basin in 9–48% of pseudo-data sets), which §8.2 assigns to the plan, while the cause is the contract (parameterization, a missing observable or the prior range); a note in §8.4 could give remedy level contract when the pseudo-data θ̂ fall in a non-truth basin; (3) endpoints on a physical boundary (G2) were not tested; (4) σ_prior of a uniform prior: settled by the acceptance of D54 (range/√12, §8.3). [triage: compute; blocks phase 2] |
| D58 | §9.2 "Cases in which T_v is calibrated with toys", §9.4 "When the path is decided" | Three conditions that send T_v and the power to the toy path have no criterion: "low counts" (no threshold; N_decl, N_exp, per-bin expectation or n_min?), "active boundaries" (no tolerance; which parameters and which boundary?) and "nonlinearity" (not tied to a named check; the §8.5 linearity check is a candidate but is used in §9.3 for another decision). The path changes the critical value of T_v, the power lower bound and the plan hash, so implementations can reach different P7/V outcomes. Proposed resolution (proposed, to be confirmed by the author): low counts: some validation bin has expected count < n_min at some evaluation point of §2.1; active boundary: some component of β̂ lies within 1σ_tot of a boundary of its allowed range (the criterion of the `boundary-solution` flag); nonlinearity: the §8.5 linearity check fails at θ_ref (P7) or at θ̂. [triage: accept?; blocks phase 2] |
| D59 | §9.4 "Uncertainty of power and the decision", §6.6, Appendix C.2 row 3b | **Accepted by the author (2026-11-09).** Adopted: Bonferroni with α_P/m per hypothesis, split into one-sided α_P/(2m) bounds, Clopper–Pearson for the toy rejection rate, in §9.4; a new §8.7 row for the cross-product bound. The confidence procedure of the power lower bound is not specified: no family-wise method is named (elsewhere Bonferroni or Holm are named), "by default 97.5% each, then multiple comparisons over the family" can be read as 97.5% per hypothesis followed by a family correction or as 97.5% for the family, the binomial interval is not named, and the construction of the cross-product bound (number of repetitions, quantile method) is open. Near 0.8 these choices change P7/V. Proposed resolution (adopted): Bonferroni: with m alternative hypotheses and simultaneous confidence 1 − α_P (default 0.05), each hypothesis receives 1 − α_P/m, split into one-sided 1 − α_P/(2m) bounds for the cross product and (Clopper–Pearson) for the toy rejection rate; add a §8.7 row for the cross-product bound construction. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D60 | §9.5 failure records, Appendix C.1 / C.2 row 3f | **Accepted by the author (2026-11-09).** Adopted: reading (a) on both sides, in §9.5 "No change of mode after a validation failure" and in Appendix C.1 (failure-record input) and C.2 (row 3f). The raw units to which a failure record is attached ("the raw units of the calibration data of that result"), and the raw units of "the calibration data" of a later result compared with it in 3f, are not specified as precisely as validation reads (recorded per whole release along the lineage, including units reached only through unused observables). Reading (a): all raw units of the calibration releases of the contract; reading (b): only the units reached by the calibration observables used in the fit. They give different grades (3f). Proposed resolution (adopted): (a) on both sides, consistent with the conservative direction chosen for reads. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D61 | §10.2 rule 0, §9.3, §9.4, Appendix C.1 | **Accepted by the author (2026-11-09).** Adopted: the proposed rule-0 wording, in §10.2 rule 0. The denominator of the proportion (D68) is not decided by this. The rule-0 bullet makes the result `incomplete` when "the proportion of toys failing G5 is > 20%" without saying which toys; §9.3 makes this `incomplete` before T_cv for the Ĉ_{r,f} and reference toys, but for the power toys only "power lower bound not yet computed", which applies only after T_cv passes; C.1 confirms that V can be `incomplete` only while T_v has not been decided as failing (Appendix C governs, "How to read this document"). Proposed resolution (adopted): "in cross-validation, some fold does not converge or fails G5 on the actual data, or the proportion of toys failing G5 among the toys for Ĉ_{r,f} or the reference distribution is > 20% (§7.3, §9.3); for the power toys, a proportion > 20% counts as 'power lower bound not yet computed', and P7 toys make P7 `incomplete`". See also D68. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D62 | §9.2 "Data-side constraint check" | **Accepted by the author (2026-11-09).** Adopted: the failure-record sentence is restricted to the check at holdout opening, and at locking the contract is rejected with no record, in the closing paragraph of §9.2 "Data-side constraint check". The closing paragraph says that a triggered check makes "that validation decided as failing, and a failure record is written", for every data-side and "has a value" check; in cross-validation and for N_d,c the same check runs at lock and a mismatch rejects the contract with no failure record. Proposed resolution (adopted): restrict the failure-record sentence to the check made at holdout opening and state that for the checks at lock (cross-validation, N_d,c) the contract is rejected and no record is written. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D63 | §10.2 rule 0 "outcome already determined", Appendix C.2, C.3 | **Accepted by the author (2026-11-09).** Adopted: the lookup evaluates Appendix C (C.2 then C.3) for each combination of possible outcomes of the inputs not yet decided, in §10.2 "Not opened when the outcome is already determined" (and the §18.8 summary); with D13, exhaustive tests of the lookup are added to the test scope of Appendix C and to §15.3.12. `calib_use.py` is said to look up "Appendix C.2 once for each possible outcome" but compares (effective grade, use), which only C.3 produces, and capped upstreams must count; "is not an input of C.2" for the lineage, toy-replica and ratio-test incompleteness is literally false (it makes V `incomplete`); the possible outcomes of P7 are not stated, and those of `incomplete` mandatory gates only implicitly (§10.2, "including failure"). An implementation that looks up only C.2 opens data in cases that are determined. Proposed resolution (adopted): evaluate Appendix C (C.2 then C.3) for each combination of possible outcomes of the inputs not yet decided (each `incomplete` mandatory gate passed or failed, P7 passed or failed, V passed with sufficient power and k > 0, or failed); the opening-precondition `incomplete` is part of V not yet decided. See also D13, D69. Merged here: D13 (the reference implementation has no tests for the lookup; the tests come with its definition). [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D64 | Appendix C.1 "States of failure records", §9.5, D22 | **Merged into D22; accepted by the author (2026-11-09).** D22 is class 1: the C.1 wording proposed below is applied in Appendix C.1 "States of failure records". C.1 says a record is `withdrawn` "when there is no testable direction (k = 0)"; §9.5 (and D22) make the record `final` when k = 0 and the data-side constraint check (including "has a value") is triggered (failure takes precedence). Appendix C governs where it differs from the text. Proposed resolution (adopted): "withdrawn when the decision passes, or when k = 0 and the data-side constraint check (including 'has a value') is not triggered; when it is triggered the record is `final`". [triage: merge into D22; blocks phase 0 (through D22); accepted by the author 2026-11-09] |
| D65 | §9.5 "Validation read event", C.1, C.2 | **Accepted by the author (2026-11-09).** Adopted: the proposed sentence, in §9.5 "Validation read event". The definition lists "power on the actual data" among the statistics whose reads are validation reads, but then fixes the cross-validation validation read at the first computation of T_cv. If V-stage power toys of cross-validation (which read within-fold totals) ran before T_cv, the two sentences give different first validation reads and change which failure records are "earlier". Proposed resolution (adopted): "In cross-validation the V-stage power toys read only within-fold totals (fit reads) and run only after T_cv has been computed, so the first validation read is always the first computation of T_cv." [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D66 | §9.2 "Data-side constraint check", N_d declaration | **Accepted by the author (2026-11-09).** Adopted: n_jᵀ y = c_j with c_j declared by the contract together with n_j, in §9.2 "Data-side constraint check" and in a contract field (§5.2 clause 7 item 3, also for N_d,c). The data-side check \|n_jᵀ y_v − c_j\| ≤ … uses a constant c_j that is not defined anywhere, and no contract field declares it. Proposed resolution (adopted): "a constraint acting on the data is written n_jᵀ y = c_j, with c_j declared by the contract together with n_j (for example c_j = 0 for 'total − sum of parts', c_j = 1 for f_A + f_B = 1)", with a contract field for it. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D67 | §9.2 standardization S | S = diag(σ_i⁽⁰⁾) is given "at θ_ref"; it is not stated whether S is re-evaluated at the fit point for the declaration-check redo and for T_v (with rounding terms C_r⁺ depends on S), or whether, for shapes conditioned on the total, S uses the expected total or N_obs. Proposed resolution (proposed, to be confirmed by the author): S at the fit point (θ̂, ν̂, η̂, φ̂ in profile mode) with the expected total for shapes conditioned on the total, not re-evaluated after opening. [triage: accept?; blocks phase 2] |
| D68 | §9.3 G5 renewal | The denominator of "> 20% of attempts" is not stated: whether toys that did not converge (for which G5 is not decided) count. Near 20% the choices differ; §19 covers only the stop rule. Proposed resolution (proposed, to be confirmed by the author): (number of toys failing G5) / (number of toys for which G5 was decided, i.e. with all folds converged). The §14.1 stop point 0.25 × (Σ_a n_req + X_max) presupposes a denominator that includes non-converged toys; under the proposed denominator it remains a valid (later) stop point, and the author should confirm both together (§19). See also D61. Computation (en/compute-19-14-1f.md): the §14.1 stop point is certain only if the proportion is also decided at the end of an attempt that fails the ratio test, which §9.3 and §14.1 now state (a new rule, to be confirmed by the author); with that rule it is valid under both denominators, and under the denominator proposed here the earlier stop F_G5 > 0.25 × Σ_a n_req is also valid and is the earliest plan-only stop in the first attempt with replacement. The choice of denominator, and with it of the threshold, remains open. [triage: accept; blocks phase 2] |
| D69 | §10.2 rule 0 lookup, §9.5, C.1 | **Accepted by the author (2026-11-09).** Adopted: the proposed sentence, in §10.2 "Not opened when the outcome is already determined". The failure-record input is defined relative to "the first validation read of this result's κ", which does not yet exist when the lookup is made before T_cv. Proposed resolution (adopted): "Before T_cv is computed, every failure record of another κ that already exists counts as earlier than the first validation read; at the computation of T_cv the input is evaluated again at the sequence number of that read." See also D13, D63. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D70 | §9.2 residual identities | **Accepted by the author (2026-11-09).** Adopted: no rounding term, in §9.2 "Data-side constraint check" (residual identities). The alternative in the proposal ("otherwise state the tolerance with Σ\|n_ji\|ρ_i/2") is not taken: `triage.md` writes only "no rounding term", and it governs. "Check \|n_jᵀ r_v\| ≤ double-precision error; this only confirms that the residuals are constructed correctly (ρ_i according to §2.1, including derived propagation)": the parenthetical suggests ρ_i enters, but the tolerance has no rounding term. Proposed resolution (adopted): no rounding term enters (the identities hold for any data values by construction); otherwise state the tolerance with Σ\|n_ji\|ρ_i/2. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D71 | §9.2 recomputation failure at the fit point | **Accepted by the author (2026-11-09).** Adopted: the proposed wording, in §9.2 "Fixing C_r in holdout, and untestable observables". "The contract must leave the whole shape unused, otherwise it is rejected; when that is not possible, the whole shape or derived quantity is excluded together": leaving a shape unused is itself exclusion, and when it would be "not possible" is not said. Proposed resolution (adopted): "the contract must list the whole shape as unused per §5.2, together with every derived quantity computed from it; a contract that does not do so is rejected". [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D72 | §9.5 result table | **Accepted by the author (2026-11-09).** Adopted: the two rows, in the §9.5 result table: "Contract error before opening" at the head of the table (a contract that is rejected produces no result, Appendix C.1), and "A mandatory gate is `incomplete`" after "Outcome already determined". The order of the other rows (D2, D3) is not changed. The table is "mutually exclusive in order: take the first row that holds", but some cases match no row: a mandatory gate `incomplete` with the outcome not determined (precondition 8); a holdout whose calibration and validation releases share raw units; a failed declaration check or fit-point recomputation. Proposed resolution (adopted): add rows "A mandatory gate is `incomplete` (outcome not already determined) → `incomplete` until completed; the validation data are not opened" and "Contract error before opening → no result; the contract is rejected (exit code 2); no validation read". See also D2, D3. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D73 | §9.2 data-side constraint check ("about 6%") | "(estimated at about 6%)" has no stated referent: the false-trigger probability of a correct release per check, or a share of affected observables, and under which format and distribution. Proposed resolution (proposed, to be confirmed by the author): the author states what is estimated, for example "in a trial computation, a false-trigger probability of about 6% per check for a significant-digits format". **Partly settled by computation, see en/compute-D73.md.** The 6% is the reviewer's estimate (RG2 F1 of the v7.37.3 regression; the original file attributes it to the reviewer) of the per-check false-trigger probability of a correct release under the old tolerance, for t = a + b in 3-significant-digit format. It is reproduced (6.1 ± 0.02%) only with the unit at the predicted central value and the prediction of t 1.3σ_t below a decimal boundary; with the ±5σ_i⁽⁰⁾ window maximum of §2.1 there are no triggers (≤ 9 × 10⁻⁷ per check), and with a uniform position on the decade grid at most about 2%. §9.2 now states the setup. Open for the author: the negative control of §15.3.5, which as written ("using the ρ_i of the prediction window as the tolerance") would show no triggers; proposed wording: "negative control: with the last-digit unit at the predicted central value as the tolerance and the prediction of t 1.3σ_t below the boundary, about 6% of checks trigger (with the §2.1 window maximum, none)". [triage: compute; blocks no phase] |
| D74 | §9.5 holdout eligibility | **Accepted by the author (2026-11-09).** Adopted: the proposed wording, in §9.5 "Effect of other κ's failure records on cross-validation". "(never read by a validation read, …)" read literally forbids reuse even by the same κ (a reproducibility recomputation after opening), while the condition concerns reads before this κ's opening. Proposed resolution (adopted): "(no validation read by any other κ, and no non-exempt read before this κ opens them; under the current rules, no read at all before opening)". [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D75 | §11.4 Table 1 node 2, §15.1, §17 vs §6.3, §11.4 Table 2, §15.3.16 | The Birks k_B method is written as "reweighting with `edep_by_dedx_class`" (Table 1, §15.1, §17) and as "rerun (deterministic)" (Table 2, §6.3, §15.3.16). Recomputing `edep_visible` from the per-class deposits forms no event weight. The name decides whether G4 applies (§8.1: event weights), P0's method list and the cost tier (§3.6, §6.5). Proposed resolution (proposed, to be confirmed by the author): deterministic rerun from `edep_by_dedx_class` (no event weights) in Table 1, §15.1 and §17; until confirmed, implementations must not derive G4 applicability from this method. **Settled by plugin source** (g4sim §9.1 and g4sim §8.8, `g4sim_simulate.py` `reweighted`; en/g4sim-binding-check.md (B)): g4sim's "reweighting" multiplies each deposit class by the visible-energy weight w(x) = 1/(1 + k_B x); it is a deterministic recomputation of `edep_visible` and forms no event weight. So the method is a deterministic rerun, G4 does not apply, and the discretization bound k_B(b − a)/(1 + k_B a) is the bound of §5.4. Table 1 of §11.4, §15.1 and §17 are written accordingly (Appendix E). g4sim does not export the bound (§5.4), so the evaluator calls `reweighting_bound` itself. g4sim S8 (v0.64.0) adds a limit: inside a `fast_sim_envelope` a model's deposit is a zero-length step, so `edep_visible` ≈ 0, and the rerun from `edep_by_dedx_class` and the LY split are meaningless for volumes inside an envelope (§11.4 Table 2, C29, D83 (12)). [triage: plugin fact; blocks phase 3] |
| D76 | §8.7, §15.3.9, §17 | **Accepted by the author (2026-11-09).** Adopted: the option "move these three rows to phase 2" (the triage choice; the alternative of splitting them is not taken), in the §8.7 table. §8.7 schedules the calibration of τ_num, the rounding condition and n_min/B in phase 1, but §17 adds these locking-stage rules (and Σ_boot of P5) only in phase 2, §15.3.9 labels the bootstrap-noise tests phase 2, and note 3 uses T_v, G6, G7, G8 and P7 (phase 2), while §17 tests in each phase only what it delivers. Proposed resolution (adopted): move these three rows to phase 2, or split them (phase 1: the parts that need only A and the toy detector; phase 2: the rest). [triage: accept; blocks phase 1; accepted by the author 2026-11-09] |
| D77 | §8.2 P2, Appendix A, §15.3.4 | **Accepted by the author (2026-11-09).** Adopted: n_c with the proposed counting rule, in the P2 row and note 2 of §8.2 and in Appendix A. In P2 (ndf = N_obs − dim N_d,c − d_free), N_obs denotes a number of calibration observables, not the observed total of a shape (Appendix A), and the counting rule is not stated: whether a count shape contributes K bins (its free ω being counted in d_free) or K − 1, whether a Gaussian alr/ilr shape contributes K − 1, and whether observables listed as unused under §5.2 are excluded. P2 is mandatory (ndf ≥ max(3, d_free)). Proposed resolution (adopted): n_c = the dimension of the calibration data vector entering the likelihood (K per count shape, K − 1 per Gaussian shape, 1 per scalar), excluding unused observables; rename to n_c in P2. [triage: accept; blocks phase 1; accepted by the author 2026-11-09] |
| D78 | §8.1, §9.5, §10.2, Appendix C.1 | **Accepted by the author (2026-11-09).** Adopted: the identifiers `not-applicable` and `no-testable-direction`, with V's "not applicable" the same value as that of §8.1; defined in §8.1 and used in §2.1, §8.2, §9.2, §9.5, §10.2, §14, §15.3, §18.8 and Appendix C.1. The recorded values for V and P7 are spelled `not-applicable` and "not applicable", and "no testable direction" has no identifier; it is not stated whether V's "not applicable" (outcome already determined, or after a mandatory gate failed) is the same recorded value as the `not-applicable` of §8.1 (applicability conditions, mode `none`), and the C.1 inputs do not name it. Proposed resolution (adopted): identifiers `not-applicable` and `no-testable-direction`, with V's "not applicable" being the same value as the `not-applicable` of §8.1. [triage: accept; blocks phase 0; accepted by the author 2026-11-09] |
| D79 | §8.2 G1, §7.3 scan points | **Accepted by the author (2026-11-09).** Adopted: tol is the minimizer tolerance declared in the plan, in the G1 row of §8.2 and in Appendix A. The G1 threshold EDM < max(0.002·tol·UP, 0.1σ_noise) uses Minuit conventions (now listed in Appendix A), but the value or source of tol is not given. Proposed resolution (adopted): tol is the minimizer tolerance declared in the plan. [triage: accept; blocks phase 2; accepted by the author 2026-11-09] |
| D80 | §6.4, §14 | **Accepted by the author (2026-11-09).** Adopted: the proposed owners, in §6.4 and in the `calib_design.py` and `calib_emulator.py` rows of §14. Design-point generation is attributed to `calib_design.py` and `calib_emulator.py` jointly (§6.4); the §14 table lists it in neither row, which conflicts with "each check is implemented by exactly one script". Proposed resolution (adopted): `calib_design.py` (plan) for the Sobol points and the P6 held-back set, `calib_emulator.py` for the surrogate's training set. [triage: accept; blocks phase 1; accepted by the author 2026-11-09] |
| D81 | §14.1 "Completion of an ensemble", §7.3 | With replacement, a redo whose carried X (the non-converged members summed over the previous attempts) already reaches k*(N_tot) ends with no member, and so does every later redo, because N_tot no longer grows; the ensemble then stays `incomplete` under that κ. This is consistent with "fails with increasing certainty" of §7.3, but the specification does not state it (side finding of en/compute-19-14-1f.md). Proposed resolution (proposed, to be confirmed by the author): state in §7.3 and §14.1 that such a redo is not registered and the ensemble is `incomplete` under that κ (remedy level: plan). [not triaged: added after the triage; blocks phase 2] |
| D82 | §2.1 "Event-level parametric bootstrap" (P5), §8.2 P5 | Side findings of en/compute-D7.md: λ_max of the ν_b = 50 design-stage estimate of Σ_boot is noisy and biased upward, so near f neither form of P5 is a calibrated test of the true Σ_boot (with a true ratio 0.087 < f the raw form still failed 70–76% of the time); P5 is a point-estimate gate, which matters only for plans with B well below 50p. (p − d)/B understates the true ratio by 3% at B = 50p and by 10–20% at B ≈ 180–450; the statement "≤ 0.02 at B ≥ 50p" of §2.1 still holds in the toy (0.0185). Proposed resolution (proposed, to be confirmed by the author): no rule change; state in §2.1 that P5 decides on the point estimate. [not triaged: added after the triage; blocks no phase] |
| D83 | §5.1, §6.6, §6.7, §10.4, §11.4, §14.1, §19 (g4sim S7, S8, S9) | g4sim defects found by the g4sim S7 check (en/g4sim-S7-check.md, "Notes for a g4sim design-error report"), to be raised through g4sim's design-error correction procedure; this workflow does not assume their outcome. (1) **Affects this workflow**: `efficiency_map.json` does not list `form.uniformity`, which `g4sim_efficiency_map.py build` writes (`form` has `additionalProperties: false`), so every built map fails its own `efficiency-map/1` schema in g4sim 0.63.0, and still in 0.65.0. Stripping the block to pass validation would change the map hash and every Dirichlet replica, which §6.7 forbids; how this workflow's checks treat a built map until g4sim fixes the schema is for the author. (2) The `$comment` of `efficiency_map.json` says "reaches each channel" where `photon_detected` counts detections (§19, PDE item). (3) `core/simulation/hits.py` writes only the first three kinds into the hits index although it declares `photon_hit` (C21). (4) `hashes.mapping_run_id` of a mapped map holds the mapping request's `request_id`, not a `run_id` (§5.1). (5) Nothing ties `run_seed` of `response-pipeline/1` to the run card; S7's gate 4 digitizes with a fixed constant (C16, D31). (6) **Map replicas across design points** (en/research-D28.md, D28): g4sim keys replica r by the map's own SHA-256, so the replicas of maps whose mapping runs shared their photons are independent; this is correct for each map alone, but `efficiency_map.py` and g4sim §10.4 do not say it, and say nothing on mapping runs that share a seed. Requested: (a) state in g4sim §10.4 and the module docstring that replica r of two maps are independent, also when their mapping runs shared photons; (b) optionally, a function that draws joint replicas for a set of maps built from the same events (the joint-pattern construction of §6.7), so that this workflow need not join `primaries.csv` and `photons.csv` itself; digitizing at such a replica needs no new g4sim function, because the digitization job `g4sim-digi-job/1` (g4sim S8) takes the efficiencies of each bin as data (§6.7, C20). A replica key derived from a scan instead of the map hash is **not** requested: with g4sim's Marsaglia–Tsang sampler it gives comonotone replicas (correlation 0.99999 across design points, 0.0009 of the true variance of their difference), which §6.7 rejects (C23). Items (1)–(6) are all still open in hep-research v0.65.0 (en/g4sim-S8-S9-check.md §1.7). Items (7)–(19) were found by the g4sim S8 and S9 check (en/g4sim-S8-S9-check.md §4; hep-research v0.65.0). Major: (7) **No recorded run of a misaligned geometry**: `geant4_run.py run-spec` builds `g4sim_run.simulate`'s arguments with no overlay and its options take none; only `g4sim_run.py simulate` and `geometry-check` take `--overlay`, and they write no computational-run record (C25); requested: `--overlay` and `--overlay-sha256` on `run-spec`, with the overlay in `input_manifest`. (8) **The overlay hash mixes sources into `geometry_id`**: `alignment.apply` puts `canonical_sha256` of the whole overlay, `description` and `source_of_facts` included, into the IR's physical part, so a change of label or source changes `geometry_id`, although g4sim routes sources to the marker part; requested: hash only `shifts` into the physical part (§5.1, D86). (9) **`g4sim_digi` silently ignores conditions**: only the Python `job_with_keys` refuses a job with `conditions`; `g4sim_digi` reads neither `conditions` nor `event_time_ns` and does not reject them (C24); requested: refuse such a job. (10) **Reconstruction uses the true misalignment**: `geant4_run.py reco` takes simreco's planes from the run's own `ir.json`, which is the overlaid IR, so the case of §3.6 in which reconstruction assumes the nominal geometry cannot be run (C26); requested: an option to reconstruct with the IR without the overlay, or with a second overlay; latent until (7) is fixed. Minor: (11) a dead channel's row still carries photoelectrons and charge, only its code is `None`; requested: null charge, or document it. (12) a fast-simulation deposit is a zero-length step, so `edep_visible` ≈ 0 inside a `fast_sim_envelope`, documented only in a code comment of `NewRun.cc` (C29); requested: document it, and warn when an envelope's material scintillates and a scorer asks for `edep_visible` or `edep_visible_ly_split`. (13) `g4sim_digi` never reads `run_seed` or `replica` and cannot check its keys; requested: a `digitize.check_keys(job)` and a statement in its usage (C16). (14) `g4sim-digi-job/1` has no schema in `contracts/schemas/`, and its parameters carry no `source_of_facts`, so the job path bypasses `response.check_pipeline`; requested: a schema and a builder from `response-pipeline/1` (C9, C11). (15) the snapshot's `defaults` is an untyped object merged unchecked by `conditions.at`, so a default `gain_factor` ≤ 0 or a misspelled key passes. (16) `conditions.at` scans the rows of the IOV for every channel and event; requested: an index by cell. (17) g4sim §17 says "events may carry timestamps", but no g4sim output does; times enter only as the job's `event_time_ns` (C27); requested: state it, or record times in the hits index. (18) `temperature_K` is accepted and read by no stage, so a snapshot that changes only temperatures has no effect, silently; requested: document it in `condition_snapshot.json`, or warn. (19) a second overlay is refused (one overlay per IR), although g4sim §17 speaks of "overlay layers"; requested: document it, or allow ordered layers. Items (20)–(23) come from the research on the PDE split (en/research-PDE.md; en/pde-geant4-check.md; hep-research v0.65.0). (20) **Efficiency only at absorption**: g4sim §10.4 and `efficiency_map.py` do not state that a map built with sensor `efficiency` = 1 is the absorption-at-sensor map, and that the map at efficiency η(E) is its η(E)-weighting, because Geant4 uses `EFFICIENCY` only in `DoAbsorption` (confirmed in the Geant4 source for `dielectric_metal` and `dielectric_dielectric`; in `DielectricLUTDAVIS` and `CoatedDielectricDielectric`, `EFFICIENCY > 0` also selects absorption over transmission). Requested: state it, and add to S7's gates a regression check, rerun on every change of the Geant4 version: a mapping run at η against η times the map at 1, per bin and channel, χ² and transit means; and, if g4sim later configures the LUT-DAVIS or coated models, refuse a sensor `efficiency` of 0 at an energy the spectrum reaches. (21) **Spectral map**: an optional form of `efficiency-map/1` with detections per (bin, channel, energy bin) and transit counts per energy bin, so that a PDE(E) can be applied without joining `photons.csv`. (22) **Real transit weights**: the mapped transit of `g4sim-digi-job/1` accepts non-negative integers only (`digitize.check_job`); requested: non-negative reals, so that a spectrally weighted histogram needs no integerisation. (23) **Per-photon PDE in the job** (optional): a `pde` field of `g4sim-digi-job/1` that keeps each detected photon with probability p from its own documented stream (one output group per photon, `<stage>/pde/<component>`), in `digitize.py` and `g4sim_digi`, giving the nested thinning of §6.7 (finite-difference slope noise 0.069 of the slope, against 0.234 for a scale of the efficiencies). Items (20)–(23) block nothing: the split of §6.7 works with g4sim 0.65.0 as it is; (21) and (22) remove workarounds, and (23) moves the nested thinning into g4sim. Proposed resolution (proposed, to be confirmed by the author): raise (1)–(23) upstream; (1) blocks a schema check of mapped maps in phase 3; (7) blocks a misaligned geometry in phase 3 or 4; (9) blocks a phase-3 evaluator that sends jobs with conditions to C++; (10) blocks the reconstruction-side alignment study of §3.6 with a misaligned simulation; (6), (8) (this workflow masks and strips the overlay itself, §5.1) and (11)–(23) block nothing. [not triaged: added after the triage; blocks phase 3] |
| D84 | §6.7 efficiency map (replicas R), §8.2 G6, §19 (local dimension reduction) | Side finding of en/compute-19-g9.md (synthetic ZDC fixture with the g4sim S7 map builder and replica sampler; Geant4 optical transport not run): the basis B_map, and hence U, is estimated from R Dirichlet replicas, and this finite-replica noise is not propagated. It is not an effect of dimension reduction: it appears with the full basis. When the efficiency-map error exceeds the data error in many independent directions, it inflates the size of G6 (α = 0.01). Evidence: in a localized cosmic-muon z scan whose map dependence has 20 independent directions (21 observables), R = 100 misestimated the per-observable map variances by −43% / +34% (R = 400: −18% / +14%) and gave a relative Frobenius error of UUᵀ of 0.48 (0.25 at R = 400); the G6 size of the full basis, alone and in joint fits with a positron study, was 0.017–0.028 at a map/data error ratio of about 0.9 and 0.044–0.12 at ratios of 2.9–9.0 with R = 100, and ≤ 0.016 and 0.015–0.027 with R = 400, against ≤ 1.5α of §8.7; the G8 coverage failures of the full basis at the higher ratios occurred at R = 100. Studies whose map dependence has low rank (5 and 3 directions under the 1% rule, of 12 observables) stayed at 0.004–0.018. g4sim's minimum R ≥ 100 (`replicas(R)`, §6.7) therefore does not suffice for such studies, and a fixed larger R alone is not supported by the evidence (R = 400 still gave 0.027). Proposed resolution (proposed, to be confirmed by the author): add to §6.7 a design-stage size check of G6 for every study with efficiency-map φ: the G6 size of the full basis is estimated with toys that redraw the replica set (replicas r > R, which g4sim generates on demand) and must be ≤ 1.5α (§8.7); when it fails, R is increased (a plan change, as for the photon number) or the G6 reference distribution is toy-calibrated with redrawn replicas; the plan records R and the check. A minimum-R rule (for example R ≥ 400, or R growing with the number of directions whose map/data error ratio exceeds 1) is the alternative; its value needs calibration per §8.7. Cross-reference (D28 revision, en/research-D28.md §4.2): the joint-pattern replicas of a shared-seed θ scan (§6.7) carry one finite-R error common to all design points, so this entry applies to them unchanged; at R = 200 and a map/data error ratio of 2.5 the G6 size was 0.024 with these replicas against 0.0095 with the analytic covariance of §6.7, which avoids the finite-R noise for observables linear in ε. Cost (g4sim S8, en/g4sim-S8-S9-check.md §1.7): re-digitizing at redrawn replica sets now costs about 15 times less with `g4sim_digi` than in Python (0.21–0.23 against 3.44–3.57 of the transport on g4sim's registered workload), except with a time for every detected photon and for jobs with a condition snapshot, which run in Python (§14.1); the entry is otherwise unchanged. In the fixed-map mode U may now be obtained by digitizing at the replicas through `g4sim-digi-job/1`, with the linear construction U = J B_map as an option for observables linear in ε only (§6.7, decided by the author on 2026-11-09); both use the same R replicas, so this entry applies to both, and the digitized construction adds R digitization jobs per construction of U. [not triaged: added after the triage; blocks phase 3] |
| D85 | §6.7 "Two efficiency map modes", §8.2 note 3 (P5, fifth item), §8.7, §6.6 (toys), §10.4 | Open points of the D28 revision (en/research-D28.md §4.3, §7; synthetic fixture with g4sim's map and replica laws, Geant4 not run). (1) Under purely nested coupling (no divergence of photon histories between design points) the shared seed left a pull width of 1.05 at κ = 0.006 that s and κ do not explain (2.3 se at N = 1000, 3.1 se at N = 2000, so probably not a fluctuation); it goes with a positive level–slope correlation (+0.115) that only nested coupling has; at 10⁷ photons (Q1d0) G8 still passed; at 10⁶ photons (P1d0, κ = 0.062, outside the bound) the V-fixed arms failed G8 on 68% and 95% coverage and only the arm profiling φ_map passed. (2) Not simulated: G7 (whose K refits redo the mapping runs); toy-calibrated intervals (the replica difference of §6.6, which rebuilds the surrogate model and would carry the θ-noise); a φ_map shared across studies (§10.4). (3) Only R = 200, one study, one optical θ and 20 observables linear in ε: width-type observables need the replica route (the analytic covariance is for linear observables only), whose digitization through `g4sim-digi-job/1` (§6.7) was not exercised in the study, multi-parameter scans need s_i and κ_i per direction with mixed terms not studied, and the D84 interaction (G6 size 0.024 at R = 200) was not explored. (4) The P5 bounds s_i ≤ 0.25, κ_i ≤ 0.05 come from twelve (configuration, seeding) points of one study (§8.7). (5) The history divergence between design points was modelled (0, 0.1, 0.4 per step); a real mapping-run pair gives the adjacent correlation directly from the pattern table. (6) Cost (g4sim S8, en/g4sim-S8-S9-check.md §1.7): the re-digitizations of these checks, the G7 refits of (2) among them, become about 15 times cheaper with `g4sim_digi` (0.21–0.23 against 3.44–3.57 of the transport on g4sim's registered workload); the open points are otherwise unchanged. Proposed resolution (proposed, to be confirmed by the author): calibrate the bounds per the §8.7 row in phase 3 together with the Geant4 confirmation of §19-g9, add a G7 and a toy-calibrated-interval check in the map-varies-with-θ configuration, and keep `provisional-thresholds` until then. [not triaged: added after the triage; blocks no phase (phase-3 calibration; `provisional-thresholds`)] |
| D86 | §5.1 model identity, §11.4 Table 2 (misalignment), §19 (derived fields) | **Accepted by the author (2026-11-09).** Adopted: the folding into the existing items, as written in place in §5.1 — the overlay into the masked detector-spec item (the pair of the two hashes, the IR's `alignment` field never hashed), the snapshot, with the plan's event-time rule, into the `response-pipeline/1` item; the count of five items stays; a plan that varies alignment applies an overlay at every design point, the nominal point included (§5.1, §11.4 Table 2, §19). Model identity of alignment overlays and condition snapshots (g4sim S9; en/g4sim-S8-S9-check.md §1.3, W1). g4sim's `geometry_id` hashes the IR's physical part, which records the overlay's full SHA-256, but the masked model identity of §5.1 hashes the detector-spec, and the overlay is a separate document, so no item covers it; a condition snapshot enters no g4sim identity (not the IR, the request, the run card or `run_id`), and `digitize.digitize` returns rows only, although the snapshot changes the response. The overlay's SHA-256 also covers `description` and `source_of_facts`, so a pure change of source changes `geometry_id` (D83 (8)). Proposed resolution (adopted; written in place in §5.1, tagged "accepted by the author, 2026-11-09"): fold both into existing items, so that the count of five items (§5.1, §5.2, §10.1, §10.3, §15.3.19, §18.10) stays: the overlay into the masked detector-spec item (hashed with `canonical_sha256` after removing `description` and `source_of_facts` and masking the `delta_mm`, `zyx_deg` entries that hold θ, φ; the item is the pair of the two hashes; the IR's `alignment` field, an embedded id that depends on θ, is never hashed, as the masking rule of §5.1 requires), and the snapshot into the `response-pipeline/1` item (hashed after removing `description` and `source_of_facts`, with the row values that hold θ, φ masked by the JSON Pointer `/iovs/<k>/rows/<j>/<quantity>`, together with the plan's event-time rule, because a different time can select a different IOV); a plan that varies alignment applies an overlay at every design point, the nominal point included, because g4sim gives an overlay of zero shifts its own `geometry_id`. The alternative, a sixth item for each, which would have changed the count "five" at those places, is not adopted. Which snapshot values hold θ, φ follows D87. [not triaged: added after the triage; blocks phase 3; accepted by the author 2026-11-09] |
| D87 | §11.4 "Conditions" and Table 2, §2.2, §3.6, §3.7, §5.2 `parameters[]` | **Accepted by the author (2026-11-09).** Adopted: the binding (a)–(h) below, as written in place in §11.4 "Conditions" — known `gain_factor`/`threshold` → ψ; with a non-negligible uncertainty → φ by the JSON Pointer of the snapshot row, re-digitized in Python only; calibrated per channel and IOV → θ, "piecewise independent" on the snapshot's IOVs (a common gain binds to the `sensor` stage); `dead` never θ or φ; `temperature_K` no role; overlay shifts and rotations → θ or φ at the resimulation level, an overlay at every design point; reconstruction-side alignment → θ of nodes 6–7; the plan records each event's time. Which values have a non-negligible uncertainty follows the criterion of D37, which stays open. Statistical roles of g4sim's conditions and alignment (g4sim S9; en/g4sim-S8-S9-check.md §1.5, W2, W4). g4sim fixes the objects but not their roles; §11.4 said only "ψ (or φ when they have an uncertainty)". Proposed binding (adopted; written in place in §11.4 "Conditions", tagged "accepted by the author, 2026-11-09"): (a) `gain_factor`, `threshold` of a (cell, IOV), known: ψ, the snapshot row, with the snapshot hash in the response item of §5.1 (D86); (b) the same with a non-negligible uncertainty (the criterion of D37): φ, bound to the snapshot row by the JSON Pointer `/iovs/<k>/rows/<j>/<quantity>`, by re-digitization (medium), in Python only (C24), masked; (c) the same, calibrated per channel and IOV: θ with the conditioning structure "piecewise independent" (§3.7) on the snapshot's IOVs, by re-digitization with exact common random numbers, masked; a gain common to all cells binds to the `sensor` stage gain of `response-pipeline/1` instead; (d) `dead`: ψ only, a different dead set is a different model; (e) `temperature_K`: no role, since no g4sim stage reads it; a temperature-dependent gain is tabulated by this workflow as `gain_factor` per IOV, which is also how the "function of conditions" structure of space experiments (§11.3) is represented, because g4sim has only piecewise IOV tables; (f) overlay `delta_mm`, `zyx_deg` of a (mother, template, copy number): θ or φ at the resimulation level (φ needs §5.5 or a surrogate model), bound to the overlay entry; a per-touchable θ needs a logical of its own in the detector-spec (C28); every design point applies an overlay, also at θ = 0 (D86); the sampling range of θ stays within the clearances of check-spec, otherwise design points are refused; masked overlay hash; (g) reconstruction-side alignment: θ of nodes 6–7, simreco geometry, rerun (deterministic), in the reconstruction specification (§3.6); (h) the plan records each event's time (`event_time_ns` of the digitization job) as a function of its global event number, because g4sim's events carry no time (C27). Reasons: g4sim gives a zero-shift overlay its own `geometry_id`, so an unshifted run is a different g4sim object from the θ = 0 design point; the overlaid IR must pass check-spec; conditions apply only through `digitize.py`, so a study with time-dependent conditions pays the Python cost (§14.1). Related: D37, whose "non-negligible uncertainty" criterion for ψ now has concrete g4sim objects (the snapshot rows); D37 itself is not changed. [not triaged: added after the triage; blocks phase 3; accepted by the author 2026-11-09] |

---

## Appendix E: Changes in the English primary edition

This appendix is kept, unchanged, in the separate file `simulator-calibration-v7.37.4-clean-en.appendix-E.md` of the task package (`simcal-task.md`, Section E12). Its line numbers refer to this file, whose lines above are unchanged. The single file is restored by replacing this heading and this paragraph with that file.
