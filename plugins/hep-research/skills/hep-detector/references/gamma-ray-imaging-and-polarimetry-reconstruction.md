# Gamma-Ray Imaging and Polarimetry: Reconstruction

Owner: hep-detector. This page gives reconstruction method text for four instrument families that the general
pages do not cover: Compton telescopes and cameras, pair-conversion gamma-ray telescopes, coded-aperture imaging,
and radiation polarimetry (photoelectric and Compton). Every method statement comes from a source read on
2026-11-06 and is scoped to the instrument, code or study that source describes; it is not a family-wide method.
Sources and their read levels are under [Sources read](#sources-read): a source read at `page` level supports only
its named sections. Where no source read gives a method, the text says "no method text: no source read", and that
stays a gap.

What this page does not establish: no tool in this plugin implements these methods, nothing here was run, and no
statement is a quality or validation claim. Numbers are as printed in the source; figures were not viewed, only
captions. Space-based instruments in general, and their instrument response functions, are in
[space based direct detection](space-based-direct-detection.md); tracking and the Kalman fit in
[tracking and vertexing](tracking-and-vertexing.md); calorimetry in [calorimetry ecal hcal](calorimetry-ecal-hcal.md).
The variant (Compton, pair, coded mask, collimated, focusing; photoelectric, Compton or modulated polarimeter) is a
fact to establish, never inferred from a name.

## Compton telescopes and cameras

<!-- example: source citation (instruments and experiments named as the source of a method) -->
Scope: the Nuclear Compton Telescope (NCT), a balloon-borne compact germanium telescope, read in full (Bandstra et
al. 2011); and a cone-transform inversion tested on synthetic data only, read at `page` level (Kuchment et al.,
arXiv:1604.03805, 2016).

- **Signal extraction** (Bandstra et al., The NCT instrument). The onboard electronics return the energy and timing
  of each strip above threshold, and the analysis works from 3D interaction positions with energies. Strip-to-hit
  details are in cited papers not read. The paper reports that the measured background below about 300 keV
  disagreed with simulation, and that range was excluded.
- **Finding and association: interaction order** (Bandstra et al., Event Reconstruction). For three or more
  interactions, a Compton kinematic discrepancy (CKD) figure of merit with `N - 2` degrees of freedom is evaluated
  over the `N!` orderings and the best is kept, up to seven interactions. For two interactions, the ordering that
  maximizes the Klein-Nishina probability times the photoabsorption probability is taken. Two-site events have no
  kinematic degree of freedom, their ordering is often ambiguous, and they were 65.8% of the selected events.
- **Parameter estimation: the cone** (Bandstra et al., Introduction; Kuchment et al., Introduction). The
  Compton formula gives the scatter angle from the deposited energies, and the first two sites give the cone axis,
  so each event yields a Compton circle (cone). A short separation of the first two sites lets the strip pitch
  dominate the angular error; a minimum first-separation cut narrowed the angular resolution in simulation.
- **Direction and imaging** (Bandstra et al., Image of the Crab Nebula; Kuchment et al., Reconstructions in
  3D). Backprojection of the circles, and list-mode maximum-likelihood expectation maximization (five iterations in
  that analysis), which revealed the source where raw backprojection did not. Kuchment et al. convert cone
  data to Radon data by three methods, then use filtered backprojection on synthetic data; a detector geometry that
  is not admissible gives limited-data blurring, and one formula with singular integrals failed numerically.
- **Energy** (Bandstra et al., The NCT instrument, Analysis of the Crab spectrum). The sum of the deposits after
  ordering, under the assumption of full absorption; on- and off-source spectra compared with simulation by
  chi-square. The 511 keV atmospheric line was cut out. Partial absorption has no method here.
- **Event rejection** (Bandstra et al., Background Reduction, table of cuts). CKD rejection, the BGO
  anticoincidence, an Earth-horizon cut and an interaction count of two to seven. This is event rejection, not a
  particle type: in simulation CKD eliminated instrumental events effectively, but real photons dominate the
  remaining background and CKD does not remove them.
- **Uncertainty and quality** (Bandstra et al., The ARM, Significance of the Crab detection, Analysis of the Crab
  ARM; Kuchment et al., Comparison, Remarks). The angular resolution measure (ARM) histogram and its FWHM;
  off-source points; and the excess variance computed from independent Poisson classes of circles, because one
  circle crosses several sky points: counting circles as independent per point gives the wrong significance. An
  off-source ARM contains source counts unless they are modelled. Kuchment et al. report L2 and H1 errors
  under added noise, and one method broke down at 20% noise.
<!-- /example -->

Failure modes: first site of a two-site event taken without a stated prior; total energy summed when escape is not
excluded; circles counted as independent per sky point; a single-site spectrum treated as Compton imaging.

No method text, no source read: an escape hypothesis and incomplete absorption; Compton polarization (not performed
by NCT for lack of counts; see [radiation polarimetry](#radiation-polarimetry)); electron-tracking Compton
telescopes; two-layer time-of-flight and liquid-xenon TPC telescopes (named only); other compact telescopes (named
by reference only); Compton cameras at finite distance with real data (Kuchment et al. assume a pure surface
measure and say the correct weight is unclear); material and passive-mass effects on ordering; Doppler-broadening
correction (named as a limit on the ARM only); an ordering error rate; extended sources.

## Pair-conversion gamma-ray telescopes

<!-- example: source citation (instruments and experiments named as the source of a method) -->
Scope: the Fermi Large Area Telescope only: a silicon-strip tracker with tungsten converters, a CsI calorimeter and
a segmented anticoincidence detector (ACD). The 2009 instrument paper (Fermi-LAT Collaboration, arXiv:0902.1089)
was read at `page` level: sec. 2.2 and parts of 2.2.1-2.2.3, 2.4, 2.4.1, 2.4.2, the start of 2.4.3, 2.4.3.2,
and 2.5 to the sensitivity text. The Pass 8 paper
(arXiv:1303.3514, 2013) was read in full; it is a status report with work then in progress, so its items are not
taken as final.

- **Signal extraction** (0902.1089 secs. 2.2.1, 2.4.1, 2.4.2). Adjacent strips are clustered, giving z plus x or y;
  time over threshold per layer; crystal pedestals and gains, with the two crystal ends giving the energy and the
  position along the crystal. With two or more particles in a plane, x-y pairing is ambiguous.
- **Finding and association** (0902.1089 sec. 2.4.1; 1303.3514 Tracker Reconstruction). A
  calorimeter-seeded pattern recognition, then a blind search; a Kalman hit search in the covariance ellipse, with
  gaps allowed, and at high energy a cone on the first hit to limit backsplash hits. Pass 8 links hits in a tree.
  The pre-Pass-8 finding depends on the calorimeter, backsplash hits confuse it, and conversions rarely look like
  clean two-track events.
- **Parameter estimation** (0902.1089 sec. 2.4.1; 1303.3514 Vertexing). A Kalman fit with material; the energy is
  shared between tracks by their observed scattering and the tracks refitted; the best track plus a second within a
  distance give a vertex at closest approach, combined covariantly. Single-track energies are poorly determined
  because calorimeter deposits overlap.
- **Vertex and direction** (0902.1089 secs. 2.4.1, 2.4.3.2; 1303.3514 Vertexing). Most events above 1 GeV have no
  recognizable vertex, and single tracks are assigned their own vertex: single-track output is normal, not a
  failure. A classification tree chooses between the vertex and the best track; a neutral-energy solution that adds
  the calorimeter centroid reduces non-Gaussian tails. Conversions in the thick section give about twice worse
  directions, and tracks may point far from the photon when energy goes to secondary photons. Event time was not
  read.
- **Energy** (0902.1089 secs. 2.4.2, 2.4.3.2; 1303.3514 Energy Reconstruction). Three leakage corrections,
  named PC, SP and LK in the paper, with a tree choosing among them; at low energy the tracker acts
  as a sampling calorimeter, since around 100 MeV about half the energy can lie in it. Pass 8 adds a crystal-level
  profile fit. Near 1 TeV crystal saturation sets in.
- **Gamma selection** (0902.1089 secs. 2.2.1, 2.4.3.2; 1303.3514 ACD Reconstruction, Event selection). The ACD veto
  is applied only on tiles that tracks point to, because a blanket veto kills high-energy photons through
  backsplash; time over threshold at the track end; topology and shower match enter classification trees. Two-track
  vertices reduce contamination. Irreducible background cannot be separated.
- **Uncertainty and quality** (0902.1089 secs. 2.4.3.2, 2.5; 1303.3514 Event-by-event Errors, Clustering). Tree
  probabilities serve as selection knobs, with hierarchical event classes (transient, source, diffuse); reducible
  background from vertexed versus unvertexed flux; an event covariance from hit composition and material.
  Effective area, PSF containment and energy dispersion are given per class. Ghost signals bias the calorimeter
  match, and the circular error is inaccurate far off axis.
<!-- /example -->

In this instrument, finding, energy and fit are coupled: energy seeds the finding, tracks correct the energy, and
the energy sets the fit weights. Treat them as one loop, not three independent steps. Sourced facts on a named
instrument's detector come from the bound profile or `detector_atlas.py query`, not from this page.

Failure modes: a missing two-track vertex treated as a reconstruction failure; tracks labelled e+ or e- (no charge
sign is measured in the text read); a blanket anticoincidence veto at high energy; class purity quoted without a
background model; a magnetic spectrometer treated as a pair telescope.

No method text, no source read: spark-chamber pair telescopes (named only); gas TPC, emulsion and other pair
telescopes; a charge-sign measurement and the individual e+ and e- energies; low-energy scattering tails beyond the
neutral-energy fix; pair polarimetry (preliminary in Pass 8); event time and clock; tracker-only and
calorimeter-only classes (proposals in Pass 8).

## Coded-aperture imaging

<!-- example: source citation (instruments and experiments named as the source of a method) -->
Scope: the coded-mask variant only, two-dimensional, source at infinity, from one review read at `page` level
(Braga 2019): the Introduction through Masks and antimasks, the Signal-to-noise ratio section to the flux
definitions, and the start of the one-dimensional cameras section. Near-field use is excluded by the review.

- **Signal extraction** (The concept, Image formation, Masks and antimasks). The detector event map, in counts per
  pixel for an energy range and integration time, is the shadowgram `D`. Flat-field factors from equal illumination
  correct multiplicative pixel sensitivity per energy range; additive background variation cannot be flat-fielded
  out.
- **Finding and association.** No method text: no source read. The sections read give no source-finding or peak
  selection algorithm, only that a source gives a peak.
- **Parameter estimation** (Image formation). `D = S (x) M + B`, with `S` the sky, `M` the mask and `B` the
  background; the sky is reconstructed by cross-correlation with a decoding array `G`, often by FFT. For URA and
  MURA patterns `M (x) G` is a delta function, so the fully coded field has no intrinsic sidelobes; ghost peaks come
  from the incomplete shadowgrams of the partly coded field, from background and from pattern choice.
- **Direction** (Detector plane resolution, Geometry and fields of view, Image formation). A sky-bin grid with
  `theta = atan(xi / l)`; angular resolution from the mask cell and detector pixel sizes over the mask-detector
  distance `l`; location accuracy scales as the resolution over the signal-to-noise ratio. A mask cell about equal
  to the pixel size gives the lowest position uncertainty. A repeated pattern on a large mask gives direction
  ambiguity (a rotating mask is named as a remedy).
- **Energy: flux per band** (Introduction, Signal-to-noise ratio). One image per energy range, and
  `F = N_H S / (A_eff T Delta E)`, with `A_eff` including the open fraction and the detector efficiency. Energy
  redistribution is not treated.
- **PID or topology.** No method text: no source read; no event classification is in the text read.
- **Uncertainty and quality** (Masks and antimasks, Signal-to-noise ratio). Variance per sky bin
  `sigma^2 = N_S + N_T`; a signal-to-noise ratio per peak; the difference of mask and antimask exposures removes the
  background. In the review's simulation a mask-only image with a background ramp shows artifacts, and other sources
  in the field add noise to every peak.
<!-- /example -->

Failure modes: ghosts in the fully coded field of a URA or MURA mask blamed on intrinsic sidelobes, instead of on
partial coding, background or a non-ideal pattern; a spectrum taken without `A_eff`; a source in the partly coded
field used without ghost handling; intensity read from a normalized or cropped map; absolute position without
pointing.

No method text, no source read: collimated imaging (a collimator appears only as a field-of-view device); focusing
optics (named as comparisons only); reconstruction in the partly coded field (the ghost problem is stated, no
correction); extended sources; attitude and pointing bias (the words are absent from the text searched); iterative
or likelihood inversion (only cited); near-field coded imaging (excluded); crossed one-dimensional cameras
(described, no reconstruction); rotating-mask timing analysis (named only); off-axis mask-thickness effects
(neglected in the derivation).

## Radiation polarimetry

The output is Stokes parameters or a modulation curve over an ensemble of photons, never a polarization per photon.
The general polarimeter row (analyzing power) is in
[detector comparison tables](detector-comparison-tables.md#table-9-specialized-and-auxiliary-detectors).

### Photoelectric polarimeters

<!-- example: source citation (instruments and experiments named as the source of a method) -->
Scope: IXPE as described by ixpeobssim, read at `page` level (Baldini et al. 2022; sections listed under Sources
read). ixpeobssim is a simulation and high-level analysis framework built on parametrized response; its input is
reconstructed level-2 events, and it does not reconstruct tracks. Do not read it as the instrument's reconstruction.

- **Signal extraction and finding.** No method text: no source read. Level-1 track images exist, but the code
  cannot generate them and no image processing, track axis or absorption-point reconstruction is given (Output data
  format, Event weights).
- **Parameter estimation** (Introduction, Basic polarization analysis). Event Stokes parameters
  `q_i = 2 cos 2 phi_i`, `u_i = 2 sin 2 phi_i` are summed over a subset of events and corrected by the effective
  area and the modulation factor, with optional weights. The Stokes form avoids the dependence between polarization
  degree and angle. Only ensemble sums are interpreted; polarization is recovered on a statistical basis.
- **Space and time** (Introduction, Dithering and pointing history). Each event has a time, an energy, two sky
  coordinates and an azimuth; dithering is removed through the aspect solution and the pointing history is kept.
  The dither averages spurious modulation over the detector, so exposure needs the dither pattern.
- **Energy** (Response functions, Spectro-polarimetric fitting). Stokes spectra `I_k, Q_k, U_k` in pulse-invariant
  channels, with a response matrix and a modulation response function, fitted with standard tools (effective area
  for `I`, modulation response for `Q` and `U`). The simple analysis neglects energy dispersion by default; verify
  that per case.
- **PID or topology.** No method text: no source read. Event weights describe reconstruction quality only.
- **Uncertainty and quality** (Introduction, Spectro-polarimetric fitting, Event weights). Spurious modulation is
  subtracted (the procedure is in a reference not read); per-bin errors come from sums of `q^2` and `u^2`; a ground
  truth extension supports checks of response effects. Only unweighted `I` follows pure counting statistics; `Q`,
  `U` and weighted `I` do not. An end-to-end test of weights is a stated limitation.
<!-- /example -->

### Compton polarimeters

<!-- example: source citation (instruments and experiments named as the source of a method) -->
Scope: POLAR, one paper on a channel-level correction, read at `page` level (Xiao et al., arXiv:1507.04474);
polarization reconstruction there is summarized and referred to other papers.

- **Signal extraction** (abstract, start of Crosstalk and response non-uniformity modeling, Conclusion). One matrix
  for crosstalk and non-uniformity, from mono-energetic calibration, applied by a linear transformation from channel
  amplitudes to energy depositions. Uncorrected crosstalk smears energy over channels.
- **Finding and association** (POLAR instrument). The scatter azimuth is taken from the line joining the two bars
  with the highest deposits, a correlation with the outgoing photon direction shown in Monte Carlo. The bar choice
  is a proxy, not the true scatter sequence.
- **Parameter estimation** (POLAR instrument). The modulation curve `K {1 + mu cos[2 (xi - xi_0)]}` is fitted over
  all detected photons of a burst, and `p = mu / mu_100`.
- **Space and direction.** No method text: no source read. Only the detector-frame angle is given; the
  detector-to-sky rotation was not read.
- **Energy** (abstract, Conclusion). The energy deposition per bar from the transformation, with energy
  calibration.
- **PID or topology.** No method text: no source read.
- **Uncertainty and quality** (POLAR instrument, Conclusion). `mu_100` from Monte Carlo and 100% polarized beams;
  residual crosstalk and non-uniformity from test runs; radioactive sources for in-flight calibration. A
  polarization systematic budget is not in the sections read.
<!-- /example -->

### Modulated-readout polarimeters

No method text: no source read, for any of the seven axes. Azimuthal modulation in the photoelectric and Compton
polarimeters above is the analyzer's response, not a modulated readout, and does not fill this variant.

Failure modes (all variants): a single event or track read as a measured polarization; a degree without the
modulation factor or `mu_100`; a sky angle without the detector-to-sky rotation; weighted Stokes sums treated as
counting statistics; a simulation framework read as the instrument's reconstruction.

No method text, no source read: photoelectric track reconstruction and absorption point; Compton scatter ordering
and multi-site reconstruction beyond the two-bar proxy (the link to [Compton telescopes](#compton-telescopes-and-cameras)
was not assessed); Compton beam polarimeters on electron beams; unpolarized and rotated controls (the correction is
named, its procedure is in a reference not read); the detector-to-sky rotation for the Compton polarimeter.

## Sources read

<!-- example: source citation (instruments and experiments named as the source of a method) -->
Each source was read on 2026-11-06 from its arXiv e-print. Identifiers are as recorded when reading; no DOI was
recorded for arXiv:1604.03805 and arXiv:1303.3514. `full-text`: the whole body was read; `page`: only the sections
named.

- M. S. Bandstra et al., "Detection and Imaging of the Crab Nebula with the Nuclear Compton Telescope" (2011),
  arXiv:1106.0323, DOI 10.1088/0004-637X/738/1/8. `full-text` (count tables in the significance section not viewed).
- P. Kuchment et al., "3D Image Reconstruction from Compton camera data" (2016), arXiv:1604.03805. `page`: abstract,
  Introduction, Definitions, the start of the inversion section with the admissibility condition, Reconstructions in
  3D (methods 1 to 3, comparison start), Conclusion and Remarks.
- Fermi-LAT Collaboration, "The Large Area Telescope on the Fermi Gamma-ray Space Telescope Mission" (2009),
  arXiv:0902.1089, DOI 10.1088/0004-637X/697/2/1071. `page`: sec. 2.2 and parts of 2.2.1-2.2.3, 2.4, 2.4.1, 2.4.2,
  the start of 2.4.3, 2.4.3.2, and 2.5 to the sensitivity text.
- Fermi-LAT Collaboration, "Pass 8: Toward the Full Realization of the Fermi-LAT Scientific Potential" (2013),
  arXiv:1303.3514. `full-text`; a status report of work in progress.
- J. Braga, "Coded Aperture Imaging in High-Energy Astrophysics" (2019), arXiv:1909.08595, DOI
  10.1088/1538-3873/ab450a. `page`: Introduction through Masks and antimasks, Signal-to-noise ratio to the flux
  definitions, the start of the one-dimensional cameras section, Future; word searches of the body.
- L. Baldini et al., "ixpeobssim: a Simulation and Analysis Framework for the Imaging X-ray Polarimetry Explorer"
  (2022), arXiv:2203.06384, DOI 10.1016/j.softx.2022.101194. `page`: abstract, Introduction, Architectural
  Overview, Output data format, Response functions, Low-level implementation, Event weights, Dithering and pointing
  history, Basic polarization analysis, Spectro-polarimetric fitting.
- H. Xiao et al., "A crosstalk and non-uniformity correction method for the space-borne Compton polarimeter POLAR"
  (arXiv 2015), arXiv:1507.04474, DOI 10.1016/j.astropartphys.2016.06.007. `page`: abstract, Introduction, POLAR
  instrument, the start of Crosstalk and response non-uniformity modeling, Conclusion.
<!-- /example -->

**Done when:** the instrument variant is stated, every method used is one of those above with its source section,
and each quantity a source does not support (a first site without a prior, a charge sign, a source in the partly
coded field without ghost handling, a polarization per photon, a sky angle without a rotation) is reported as
unknown.
