# hep-detector reconstruction methods: review dispositions

Independent review (step T7) of `git diff 313637c1..2d8e931c -- plugins/hep-research/skills/hep-detector`
(`CONTENT_HEAD` 2d8e931c), by one fresh-context reviewer (general-purpose subagent, same model family)
given only the review packet of the task file. The report is kept in the run's work root
(`review/report.md`, not committed). Verdict: no critical finding; accept after the two major fixes.

The reviewer checked as correct: the first-photon density, the fluorescence timing relation,
logarithmic weighting, the broken-lines / filter-plus-smoother equivalence, the annealing and
Gaussian-sum filters, LArTPC recombination and 3D failure modes, the scintillator gamma-to-electron
step, the muon critical energy, IACT cleaning and the displacement method, surface-array saturation as
censoring, group versus phase index; all 13 citations consistent; all anchors resolve; Check lines
present; no experiment performance numbers; no duplication with hep-statistics or hep-ml.

Paths are relative to `skills/hep-detector/references/`.

| # | Severity | File | Finding | Disposition | Changed text |
|---|---|---|---|---|---|
| 1 | major | photon-likelihood-reconstruction.md | First-photon density with noise in `f`, `F` is exact only if `mu` is the total (signal plus noise) above-threshold mean; the Check line read as signal-only `mu` | fixed | "`mu` is the total mean number of above-threshold photoelectrons in the readout window (signal plus noise), and `f` and `F` are the corresponding normalized mixture density over the window and its cumulative"; Check line: "the total expected `mu` (signal plus noise) of every hit channel" |
| 2 | major | photon-likelihood-reconstruction.md | `-ln L` per degree of freedom counted only hit channels although the likelihood runs over unhit channels too, and has no reference distribution | fixed | "divided by a stated count (for example hit channels minus fitted parameters, although the likelihood also runs over unhit channels): a crude normalization, empirical and with no reference distribution, whose energy and topology dependence is calibrated on simulation" |
| 3 | minor | detector-measurement-framework.md | Least squares with asymmetric tails is not biased in itself; bias needs a most-probable-value model or truncation | fixed | "asymmetric tails (Landau, bremsstrahlung): inefficient, and biased when the model uses the most-probable value or hit selection truncates the tails; wrong hits: biased" |
| 4 | minor | photon-likelihood-reconstruction.md | "Below the critical energy ... range" overclaims for roughly 100 GeV to `E_c`, where muons are not contained | fixed | "Well below the muon critical energy ionization dominates ... so range is the estimator for a contained muon; between roughly a hundred GeV and the critical energy ... its energy is poorly constrained" |
| 5 | minor | tracking-and-vertexing.md | The double integral of `B` is the figure of merit only with measurements inside the field | fixed | "(the sagitta-like double integral of `B` when the measurements lie inside the field; `int B dl` with the lever arm of the outer planes when they lie outside it)" |
| 6 | minor | photon-likelihood-reconstruction.md | Hit and unhit terms must share one threshold model | fixed | "The hit and unhit terms use the same threshold model, so for each channel the probabilities of a hit and of no hit sum to one." |
| 7 | minor | noble-liquid-neutrino-and-rare-event-detectors.md | "pitch grows at large angle to the wire plane" ambiguous | fixed | "grows as the track points along the drift direction (the charge on each wire is spread over a long time) or along the wire orientation" |
| 8 | minor | ground-based-detection-arrays.md | Missing station time-variance model for the direction fit and lateral-distribution-shape uncertainty of the size | fixed | size bullet: "that uncertainty also includes the uncertainty of the assumed lateral-distribution shape, which the reference-distance choice above keeps small but not zero"; new bullet "**Station times.**" on the time-variance model (links the existing arrival-direction bullet, no restatement) |
| 9 | minor | photon-likelihood-reconstruction.md | Moon shadow applies only to cosmic-ray shower or muon detectors; state it or move it | not fixed | The item already states its applicability in its label ("Pointing (detectors of cosmic-ray muons or showers)"); it is the only mention in the references (single owner), and the content specification (item A, section 8) places it here |
| 10 | minor | detector-principles-summary.md (wiring) | The summary does not link the new file | not fixed | Repository convention and acceptance criterion 4: the summary's "Reference index" section belongs to its routing part (`tools/reference_inventory.py`, `ROUTING_HEADING` matches "index"), which is at 4081 B of a 4096 B budget and may not grow; the content specification says "no change". The file is reached from the SKILL.md Resources row and from event-reconstruction, neutrino-astronomy and noble-liquid references |
| 11 | minor | calorimetry-ecal-hcal.md | Later hadronic start needs `lambda_I >> X0`; weaker contrast in low-`Z` media | fixed | "(strongly in high-`Z` absorbers; the contrast is weaker in low-`Z` media)" |
| 12 | optional | tracking-and-vertexing.md | Garbled sentence in the unchanged track-fit paragraph ("Use the smoother ... outlier down-weighting for wrong hits: rather than treating the trajectory ...") | fixed on user request | Kalman-filter description moved directly after "handles multiple scattering naturally:"; then "The filter assumes Gaussian process noise; ... Use the smoother for unbiased residuals at every layer, and down-weight outliers to handle wrong hits." |

Fix commit: recorded in STATE.md (T7) and below in the next commit, since a commit cannot contain its own sha.

Fix commits: `9ff83cdf` (content fixes, this file) and `37b68e3d` (reference inventory regenerated by the T5
procedure after the fixes changed reference sizes).

## Re-review

One fresh-context re-reviewer was given the earlier report, `git diff 2d8e931c 9ff83cdf` and this file (report
in the work root, `review/rereview.md`). Verdict: all findings resolved or justifiably deferred; accept.
Findings 1-8 and 11 resolved; reasons for 9, 10 and 12 accepted (for 10 it suggests softening the README's
"indexes the rest" in a follow-up). No physics error, experiment number, unlabelled approximation or missing
Check line was introduced. It raised three new minor wording points, left open in this run because the one fix
round of the review (OQ-1 default) is used and none is critical or major:

| # | Severity | File | Finding | Disposition |
|---|---|---|---|---|
| A | minor | photon-likelihood-reconstruction.md | "`-ln L` per degree of freedom, that is divided by a stated count" reads against its own caveat; mixed punctuation in the list of quality variables | fixed on user request: "the minimum of `-ln L` divided by a stated count, often called per degree of freedom (...), a crude normalization with no reference distribution ...", list separated by semicolons (marker phrase kept) |
| B | minor | photon-likelihood-reconstruction.md | "the muon is rarely contained" depends on detector size; suggested "often not contained in the instrumented volume" | fixed on user request: "often not contained in the instrumented volume" |
| C | minor, optional | ground-based-detection-arrays.md | The surface-array Check line could name the station time-variance model | fixed on user request: Check line names "the station time-variance model used in the direction fit" |

## Follow-up review: the 12 deferred cells

One fresh-context reviewer (general-purpose subagent, same model family) reviewed
`git diff 37b68e3d..6bfc7873 -- plugins/hep-research/skills/hep-detector` (report in the work root,
`deferred/review/report.md`). Verdict: approve after the three major items; no critical finding; citations,
anchors, Check lines, example blocks and ownership in order.

| # | Severity | File | Finding | Disposition | Changed text |
|---|---|---|---|---|---|
| 1 | major | ground-based-detection-arrays.md | "the geomagnetic part scales with `sin alpha`" wrong for an energy; quadratic scaling is a fit | fixed | geomagnetic amplitude `sin alpha`, fluence `sin^2 alpha`; charge-excess part independent of `alpha`, fraction grows with air density; "approximately quadratically (*approximate*, an exponent fitted in simulation)" |
| 2 | major | noble-liquid-neutrino-and-rare-event-detectors.md | Maximum-current-over-energy cut works only in small-contact germanium; calibration peaks incomplete | fixed | small-contact geometry and weighting-field reason, semi-coaxial caveat; double-escape peaks (single-site proxy, not uniform), single-escape and full-energy peaks (multi-site-rich), acceptance extrapolated and cross-checked on the two-neutrino continuum or simulation |
| 3 | major | noble-liquid-neutrino-and-rare-event-detectors.md | Dissolved or gaseous sources impossible in solid germanium; fiducial fraction energy dependent | fixed | "events uniform in the bulk (cosmogenic or neutron-activation lines) ... as a function of energy, since the charge resolution degrades the cut near threshold" |
| 4 | minor | noble-liquid-neutrino-and-rare-event-detectors.md | Resolving time can be below the rise time; rate per detector | fixed | "a resolving time (of order the rise time, or below it with pulse-shape tests)"; "scale as the resolving time times the square of that detector's event rate, which favours small or segmented detectors" |
| 5 | minor | noble-liquid-neutrino-and-rare-event-detectors.md | Reviewer doubted (from memory) that the cited paper treats the light channel | fixed (reworded) | Abstract read via INSPIRE-HEP (arXiv:1404.1231, abstract+metadata, 2026-10-30): pulse-shape rejection on both heat and light signals; citation kept on "pulse-shape tests on the rising edge, or a two-pulse fit, on the heat signal and on a faster channel such as the light detector" |
| 6 | minor | noble-liquid-neutrino-and-rare-event-detectors.md | Phonon partition needs athermal-phonon sensors | fixed | "With several athermal-phonon sensors (not a thermistor bolometer read by one sensor)" |
| 7 | minor | gaseous-and-specialized-tracking-technologies.md | `n^2` ghost count restates the strips paragraph | fixed | "Stereo views give ghost intersections as for strips (see the strips paragraph above)" |
| 8 | minor | gaseous-and-specialized-tracking-technologies.md | Bending-projection-first holds only for axial layers in a field | fixed | "When the axial layers measure the bending coordinate in a field, finding proceeds in that projection first" |
| 9 | minor | gaseous-and-specialized-tracking-technologies.md | Clusters are photosensor channels; staggered layers; double-ended readout | fixed | channel spans several fibres, staggered layers and light spread; "except a coarse one from the time difference or amplitude ratio with double-ended readout" |
| 10 | minor | gaseous-and-specialized-tracking-technologies.md | Scattering measures `p beta`, needs radiation lengths; larger cells | fixed | "Scattering measures `p beta`, not `p` ... radiation lengths (the Highland formula, *approximate*)"; "comparing non-adjacent films (larger cells) pushes that limit up" |
| 11 | minor | gaseous-and-specialized-tracking-technologies.md | Film gap is an alignment parameter | fixed | "plus the gap between films" |
| 12 | minor | gaseous-and-specialized-tracking-technologies.md | Following a predicted track back is for hybrid set-ups | fixed | "In hybrid set-ups ...; standalone emulsion detectors scan the full area instead" |
| 13 | minor | ground-based-detection-arrays.md | Polarization geometry of the footprint asymmetry | fixed | interference along `v x B`, no interference along `v x (v x B)`, where the polarization measures the charge-excess fraction |
| 14 | minor | ground-based-detection-arrays.md | Geometric distance to slant depth needs the density profile; other `X_max` observables; EM-only stated twice | fixed | curvature and spectral slope added; density-profile conversion listed; duplicate EM-only sentence removed from the `X_max` bullet |
| 15 | minor | ground-based-detection-arrays.md | "leading energy-scale systematic" not universal | fixed | "usually the leading" |

Fix commit: recorded in STATE.md (follow-up) in the next commit.

Fix commit: `93735497`.

### Re-review of the follow-up fixes

One fresh-context re-reviewer was given the follow-up report, `git diff 6bfc7873 93735497` and the table above
(report in the work root, `deferred/review/rereview.md`). Verdict: all 15 findings resolved, no physics error
introduced; approve. Its new points, left open because the follow-up's one fix round is used and none is critical or
major:

| # | Severity | File | Finding | Disposition |
|---|---|---|---|---|
| D1 | minor | noble-liquid-neutrino-and-rare-event-detectors.md | Phonon parenthetical mixes the number and the kind of sensors | fixed on user request: "several fast sensors of athermal phonons (for example superconducting transition-edge sensors), rather than thermistors that respond mainly to the thermal phonons" |
| D2 | minor | gaseous-and-specialized-tracking-technologies.md | "plus the gap between films" reads as part of the in-plane affine map | fixed on user request: "(... shift, rotation, expansion), plus the longitudinal gap between films" |
| D3 | minor | ground-based-detection-arrays.md | "approximately quadratically ... (*approximate*" is redundant | fixed on user request: "scales quadratically ... (*approximate*: the exponent, close to 2, is fitted in simulation" |
| D4 | minor | noble-liquid-neutrino-and-rare-event-detectors.md | Scope of "on the heat signal and on a faster channel" ambiguous; long line | fixed on user request: "Pileup is searched for on the heat signal and on a faster channel where one exists ... by a template fit ..., by pulse-shape tests ..., or by a two-pulse fit", rewrapped |
| D5 | optional | ground-based-detection-arrays.md, noble-liquid-neutrino-and-rare-event-detectors.md | Check lines could name the density profile and the energy dependence of the fiducial fraction | fixed on user request: radio Check line names the density profile; germanium Check line adds "as a function of energy" |

All open items above (A, B, C, 12, D1-D5) were fixed after the run on the user's request ("fix item in Still open"); see STATE.md.

### Re-review of the open-item fixes

A fresh-context re-reviewer of `git diff 976114a6 1450e47f` found all nine items (A, B, C, 12, D1-D5) resolved, nothing
critical or major, and four new points, all fixed in the next commit:

| # | Severity | File | Finding | Disposition |
|---|---|---|---|---|
| N1 | minor | tracking-and-vertexing.md | "Use the smoother for unbiased residuals": smoothed residuals include the hit (the glossary defines an unbiased residual as one whose prediction excludes the measurement) | fixed: "Use the smoother for the best estimate at every layer; for unbiased residuals remove the hit from the smoothed state (or refit without it), since a smoothed residual includes the hit" |
| N2 | minor | noble-liquid-neutrino-and-rare-event-detectors.md | "as a function of energy" attached to the calibration peaks in the Check line | fixed: "its calibration, as a function of energy, with uniformly distributed events or calibration peaks" |
| N3 | cosmetic | noble-liquid-neutrino-and-rare-event-detectors.md | Short and over-long lines after the rewrap | fixed: rewrapped |
| N4 | cosmetic | photon-likelihood-reconstruction.md | "often called per degree of freedom" | fixed: "often called the value per degree of freedom" |
