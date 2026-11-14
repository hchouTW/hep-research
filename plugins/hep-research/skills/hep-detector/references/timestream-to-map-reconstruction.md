# Timestream to Map: Reconstruction for Scanning Radiometers

Owner: hep-detector. This page gives reconstruction method text for scanning radiometers and polarimeters whose
output is a map built from a detector timestream. Every method statement comes from a source read on 2026-11-06
and is scoped to the study that source describes; it is not a family-wide method. Sources and their read levels are
under [Sources read](#sources-read): all four were read at `page` level and support only their named sections.
Where no source read gives a method, the text says "no method text: no source read", and that stays a gap.

What this page does not establish: no tool in this plugin implements these methods, nothing here was run, and no
statement is a quality or validation claim. Cosmological inference on the map belongs to hep-statistics and
hep-theory. Scan settings and the setting axis follow the rule in
[frequency- and scan-encoded spectroscopy reconstruction](frequency-and-scan-encoded-spectroscopy-reconstruction.md):
established, never inferred; a naive average over chunks that drops pointing or conditions is not a substitute for
the timestream.

## Destriping and map-making

<!-- example: source citation (experiments named as the source of a method) -->
Scope: Planck-like simulations only (LFI 70 GHz and 100 GHz, HFI-like), four papers read at `page` level (Keihanen
et al. 2004, Poutanen et al. 2005, Kurki-Suonio et al. 2009, Tristram et al. 2011). No real data enter the sources
read. The output is a map with its noise description; cosmological inference is excluded.

- **Signal extraction: calibration** (Tristram et al., Photometric calibration, Dipole calibration). A gain per
  detector from the time-dependent orbital dipole, solved as a linear problem and iterated with the offsets; the
  orbital dipole is known and not fixed on the sky. A single polarization-sensitive detector is degenerate if
  polarization is modelled and biased if it is neglected.
- **Finding and association** (Poutanen et al., Destriping technique; Kurki-Suonio et al., Derivation). Pointing
  assigns samples to pixels, and crossing points link the baseline segments. With baselines sufficiently connected
  the null space is one-dimensional; with crossings clustered in a small region for short segments, errors may
  blow up.
- **Parameter estimation** (Keihanen et al., Maximum-likelihood analysis of the destriping problem, Map-making
  algorithm; Poutanen et al., ROMA and MapCUMBA; Kurki-Suonio et al., Derivation). Destriping: a joint fit of map and
  baselines, conjugate gradient for the amplitudes, then binning, optionally with a noise prior (Madam), which
  approaches the minimum-variance map as the number of base functions grows; or a maximum-likelihood map with a noise
  filter (ROMA, MapCUMBA), which assumes the noise spectrum is known; on real data it must be estimated.
- **Pointing and polarization angle** (Kurki-Suonio et al., Derivation; Poutanen et al., Methods). Pointing-matrix
  rows `(1, cos 2 psi, sin 2 psi)` on the pixel of the beam centre; no beam deconvolution, so the map is smoothed by
  beam and pixel. A pixel is kept when its inverse condition number passes a limit; a pixel with fewer than three
  sufficiently different angles is excluded with its samples.
- **Identifiable quantity** (Kurki-Suonio et al., Derivation; Tristram et al., The map-making problem). `I`, `Q`,
  `U` per pixel in calibrated temperature. A constant offset is unidentifiable: a monopole claimed from the map is
  degenerate with a constant noise offset. Anisotropy and polarization stay identifiable.
- **PID or topology.** Not applicable, for a readout reason: the data are sky-brightness samples per detector,
  modelled as signal plus noise, with no particle or event object.
- **Uncertainty and quality** (Keihanen et al., Covariance of the output map; Kurki-Suonio et al., Derivation,
  Conclusions; Poutanen et al., Conclusions; Tristram et al., Dipole calibration). The map covariance; the residual
  split into six components, three with analytic estimates; null-space handling; a gain error from a Fisher term.
  Pixelization noise from sub-pixel signal biases power spectra unless corrected.
- **Null modes and coadding.** The destriping matrix is singular. Poutanen et al. state an explicit zero-sum
  condition; Kurki-Suonio et al. solve orthogonal to the null space and say this holds exactly only when no pixels
  are excluded. A stated constraint fixes the offset, not added data. Coadding repeated circles into rings is
  equivalent to uncoadded destriping only for ideal scanning (Kurki-Suonio et al., Ring set or not), so a coadded
  product carries that condition.
<!-- /example -->

Failure modes: a monopole read from the map; a map noise claim without a noise model; a pre-averaged, normalized
map with no pointing or noise description offered for combination; polarization in pixels below the angle or
condition limit.

No method text, no source read: modulation (for example a modulator in the optics; the sources use scan-driven
angle change only); filtering and the filter transfer function, including signal injection before filtering (these
sources solve baselines rather than filter); ground and balloon scan strategies; beam asymmetry and deconvolution,
and bandpass mismatch; correlated noise between detectors (a part of Kurki-Suonio et al. on it was not read);
time-domain preparation of detector data (pointing reconstruction, glitches, waveform level); noise estimation
from data (named as needed, not given); map combination across experiments.

## Sources read

<!-- example: source citation (experiments named as the source of a method) -->
Each source was read on 2026-11-06 from its arXiv e-print. Identifiers are as recorded when reading. `full-text`:
the whole body was read; `page`: only the sections named, some long paragraphs only up to a length cut-off.

- E. Keihanen et al., "Madam - a map-making method for CMB experiments" (2004), arXiv:astro-ph/0412517, DOI
  10.1111/j.1365-2966.2005.09055.x. `page`: abstract; Maximum-likelihood analysis of the destriping problem;
  Map-making algorithm; Covariance of the output map; Data sets; Conclusions.
- T. Poutanen et al., "Comparison of map-making algorithms for CMB experiments" (2005), arXiv:astro-ph/0501504, DOI
  10.1051/0004-6361:20052845. `page`: Methods; ROMA and MapCUMBA; Destriping technique; Conclusions.
- H. Kurki-Suonio et al., "Destriping CMB temperature and polarization maps" (2009), arXiv:0904.3623, DOI
  10.1051/0004-6361/200912361. `page`: abstract; Ring set or not (opening); Derivation; Scanning (opening);
  Conclusions.
- M. Tristram et al., "Iterative destriping and photometric calibration for Planck-HFI, polarized, multi-detector
  map-making" (2011), arXiv:1103.2281, DOI 10.1051/0004-6361/201116871. `page`: abstract; The map-making problem;
  Photometric calibration; Dipole calibration; Polarization-sensitive detectors (part).
<!-- /example -->

**Done when:** the representation (timestream or coadded rings), pointing and polarization angles, noise model and
null-mode constraint are stated, every method used is one of those above with its source section, and each quantity
the sources do not support (a monopole, pixels below the condition limit, a signal transfer where filtering was
applied) is reported as unknown.
