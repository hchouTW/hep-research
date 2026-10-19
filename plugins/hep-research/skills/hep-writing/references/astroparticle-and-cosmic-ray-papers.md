# Astroparticle and Cosmic-Ray Papers

<!-- example: experiment-specific illustration -->
How writing and reading conventions shift for astroparticle physics and cosmic-ray
papers — ground-based air-shower arrays (Pierre Auger, Telescope Array), imaging
atmospheric Cherenkov telescopes (CTA, H.E.S.S., MAGIC, VERITAS), water/ice Cherenkov
and neutrino observatories (IceCube, HAWC, LHAASO), and space-based direct detection
(AMS-02, DAMPE, CALET, Fermi-LAT). This file covers the *writing/venue/citation*
differences; the physics content itself (spectrum, composition, anisotropy, shower
physics, statistics for point-source searches) is `hep-detector`'s domain (statistics: `hep-statistics`) — see their
astroparticle references (cosmic-ray spectrum and composition, extensive air showers,
ground-based arrays, imaging Cherenkov, neutrino astronomy, space-based direct
detection, astroparticle statistics) for the content itself. Everything below assumes
that physics is already worked out and focuses on how to write it up.
<!-- /example -->

## Table of contents
- [How the structure differs from collider HEP](#how-the-structure-differs-from-collider-hep)
- [Journals and venues](#journals-and-venues)
- [Collaboration author lists and acknowledgments](#collaboration-author-lists-and-acknowledgments)
- [Citations: ADS vs. INSPIRE-HEP](#citations-ads-vs-inspire-hep)
<!-- example: experiment-specific illustration -->
- [Checking a collaboration's publication pattern](#checking-a-collaborations-publication-pattern)
<!-- /example -->
- [Figures: spectra, skymaps, and exposure](#figures-spectra-skymaps-and-exposure)
- [Phrasing conventions specific to this field](#phrasing-conventions-specific-to-this-field)
- [Reading checklist additions](#reading-checklist-additions)

## How the structure differs from collider HEP

The section-by-section backbone in `paper-structure.md` still applies (Introduction →
Instrument/Dataset → Analysis → Systematics → Results → Summary), with these
substitutions:

- **"Detector" becomes "Instrument," "Observatory," or "Array."** A ground array
  paper describes station spacing, trigger logic, and array livetime rather than a
  collider subdetector's geometry; ask which term the target collaboration's prior
  papers use rather than guessing.
<!-- example: experiment-specific illustration -->
- **"Luminosity" becomes "exposure."** Ground-based arrays report exposure in units
  of area × solid angle × time (e.g. km²·sr·yr for Auger surface-detector analyses);
  space-based spectrometers report it in m²·sr·s or as an effective-area-vs-energy
  curve integrated over livetime. State how the exposure was calculated (Monte Carlo
  vs. data-driven) the same way a collider paper would justify a luminosity
  measurement.
<!-- /example -->
- **An arrival-direction / anisotropy section is often its own block**, distinct from
  the energy-spectrum section, since the statistical treatment (pre-trial vs.
  post-trial significance over a scanned sky region, angular resolution) differs from
  a spectral measurement's.
- **Atmospheric and hadronic-interaction-model systematics replace detector-alignment
  systematics as a dominant uncertainty** for air-shower analyses — state which
  interaction model(s) (e.g. QGSJET, EPOS, Sibyll) were used to estimate this
  systematic, since results are known to shift between model choices.
- **Multi-messenger context**, when relevant, needs its own short paragraph: whether
  this result is associated with a specific alert (a GCN/Astronomer's Telegram
  circular, a particular gravitational-wave or neutrino event), what the coincidence
  window and localization were, and whether the association is being claimed or only
  reported as a search.
<!-- example: experiment-specific illustration -->
- **Solar modulation** is a required systematic discussion for any low-energy
  (sub-~30 GeV/nucleon) cosmic-ray flux measurement from a space-based detector —
  state the solar activity period (which matters for AMS-02/PAMELA-era comparisons)
  and whether a force-field or numerical modulation model was used to compare across
  epochs.
<!-- /example -->

## Journals and venues

Venue facts for astroparticle journals (JCAP, ApJ/ApJL, Astroparticle Physics,
A&A, PRD) are in the quick-reference table of `latex-venue-setup.md`, with sources
and verification dates; this section only adds what differs in practice.

As with the collider-physics class files, always pull the current `.cls`/`.bst` from
the publisher rather than reconstructing from memory — AASTeX in particular changes
version numbers with formatting-relevant changes (author lists, table environments).

<!-- example: experiment-specific illustration -->
arXiv category: `astro-ph.HE` (high-energy astrophysical phenomena) is the primary
category for most cosmic-ray/gamma-ray/neutrino result papers; cross-list `hep-ex` if
the result also has direct particle-physics relevance (e.g. an AMS-02 antimatter/dark
matter search). See `latex-venue-setup.md`'s arXiv-specific-rules section for the
general category-selection guidance.
<!-- /example -->

## Collaboration author lists and acknowledgments

<!-- example: experiment-specific illustration -->
- Large observatory collaborations (Pierre Auger, IceCube, AMS-02, CTA, HAWC,
  LHAASO, Telescope Array) follow the same "don't hand-type hundreds of `\author{}`
  lines" rule as collider collaborations — ask for the collaboration's current
  author-list boilerplate/macro package rather than guessing, and use
  `\collaboration{}` (REVTeX) or the venue's equivalent macro.
- Acknowledgments sections are typically longer and more itemized than a single-PI
  paper's: national funding agencies per member institution, host-country and
  host-site permissions (e.g. Malargüe, Argentina for Auger; the National Science
  Foundation's Office of Polar Programs for IceCube's South Pole site; La Palma or
  Roque de los Muchachos site agreements for Canary Islands-based telescopes). Ask
  the user for the collaboration's existing acknowledgments template rather than
  drafting one from scratch — this is boilerplate that changes rarely and is
  centrally maintained.
<!-- /example -->

## Citations: ADS vs. INSPIRE-HEP

INSPIRE-HEP indexes most astroparticle-physics literature already (it absorbed the
former SPIRES/astro coverage for HEP-adjacent work), but the NASA Astrophysics Data
System (ADS, `ui.adsabs.harvard.edu`) is the dominant citation database for the more
astronomy-facing venues (ApJ/ApJL, A&A, MNRAS) and for anything with a strong
astronomy (rather than particle-physics) readership:

- **Use INSPIRE-HEP** when the paper's primary audience/venue is HEP-style (PRD, JCAP,
  a paper that also gets cross-listed to `hep-ex`/`hep-ph`) — same workflow as
  `citations-and-bibliography.md` describes.
- **Use ADS** when targeting ApJ/ApJL/A&A/MNRAS, or when citing astronomy-side source
  papers (optical/radio counterpart identifications, catalogs) that INSPIRE doesn't
  index as completely. ADS's BibTeX export uses `bibcode` identifiers (e.g.
  `2017ApJ...848L..12A`) as the natural key, analogous to INSPIRE's
  `Surname:2012abc`-style keys — keep ADS's key format for the same reason: collaborators
  and referees on astronomy-side venues expect it.
- **A single paper may need both**: pull the HEP-side citations from INSPIRE and the
  astronomy-side ones from ADS into the same `.bib` file. A paper in both databases has
  different keys: deduplicate by DOI, then arXiv identifier, then record id (rule 9 of
  `academic-papers-guide.md`).
- **Citation style**: ApJ/A&A/MNRAS commonly use `natbib` author-year citation
  (`\citep{}`/`\citet{}`) rather than the numbered style collider-physics venues use
  — check the specific venue's current style file rather than assuming numbered
  citations carry over.

## Checking a collaboration's publication pattern

Collaborations differ in ways that change how their results are found, cited and
built on. Check, for the specific collaboration and date, rather than assuming the
collider pattern; record what you checked with its date (`../../hep-literature/references/citation-verification.md`):

- **Venue mix.** Some publish almost only short letters plus an occasional long
  review that consolidates them; others split results across letters and long
  methods papers. Read the collaboration's own publication list and INSPIRE-HEP.
- **arXiv posting.** Not every collaboration posts preprints: check the INSPIRE-HEP
  record's `arxiv_eprints` field before assuming a paper has, or will get, an arXiv
  version, and ask the user which policy their own collaboration follows. An absent
  preprint is a fact about the record; why it is absent is not, unless a source says.
- **Author lists.** Large collaborations maintain the author-list macro and
  acknowledgments boilerplate centrally; get them from the collaboration (see
  "Collaboration author lists and acknowledgments" above), never draft them.
- **Data tables outside the journal.** Flux tables and supplemental data may sit on
  the collaboration's site rather than (or as well as) HEPData; look there before
  reading values off a figure.
- **Web-only technical notes.** A collaboration site's method or "advances" pages
  may point to a peer-reviewed paper, or to none. Cite the paper when one is named;
  otherwise cite the page as a website with an access date, never as peer-reviewed
  literature.
- **Highlight pages** on a collaboration's domain may be written by journalists or
  journal magazines, not the collaboration: see `outreach-and-public-facing-summaries.md`
  ("Collaboration voice vs. syndicated commentary").

Counts, names and dated facts about a specific collaboration belong in its experiment
profile's evidence ledger with a verification date (see the context-resolution steps
in the skill's SKILL.md), not in this file.

## Figures: spectra, skymaps, and exposure

In addition to the figure types in `figures-and-tables.md`:

| Goal | Good choice |
|---|---|
| Cosmic-ray energy spectrum | Flux scaled by `E^n` (commonly `n = 2.6`–`3`) vs. energy, log-log, to flatten the power law and make features (knee/ankle/cutoff) visible; state the chosen `n` in the caption |
| Arrival-direction / anisotropy map | All-sky map in an equal-area projection (Mollweide or Hammer-Aitoff), with equatorial (J2000) or Galactic coordinates stated explicitly in the caption/axis labels — do not assume the reader infers which |
| Point-source significance map | Pre-trial significance map, with the post-trial (global) significance of the maximum stated in the caption or text, never presented as if pre-trial were the final number |
| Effective area / exposure vs. energy | Line plot, log x-axis if the energy range spans more than ~1 decade; state livetime and any duty-cycle correction separately from the effective-area curve itself |
| Elemental/mass composition | Stacked or overlaid distributions per assumed primary species (often `<Xmax>` or a similar shower-depth observable vs. energy), with model-prediction bands for reference compositions |

Skymaps in particular are easy to get wrong in ways a reader can't fix after the
fact: always label the coordinate system, projection, and whether what's plotted is
significance, excess counts, or flux — three different quantities that look similar
as a heatmap but mean very different things.

## Phrasing conventions specific to this field

Significance wording, including pre-trial vs. post-trial and "detection" vs. "hint",
lives in `scientific-style.md` (Significance language). Specific to this field:

- **"Exposure" and "livetime"** are not interchangeable: exposure already folds in
  geometric acceptance and duty cycle; livetime is the raw observing time before
  those corrections. State which one a quoted uncertainty is derived from.
- **Composition language** ("proton-dominated," "mixed composition," "consistent with
  a heavier composition") should be tied to the specific observable and model set used
  to infer it — composition inferences are strongly model-dependent (choice of
  hadronic-interaction model), and stating a composition claim without that caveat
  overstates certainty.

## Reading checklist additions

When reading someone else's astroparticle/cosmic-ray paper, extend
`../../hep-literature/references/reading-papers.md`'s HEP-specific checklist with:

- **Exposure/livetime and duty cycle**: stated explicitly, and consistent with the
  array's/instrument's known operating history for that period?
- **Trials factor**: for any point-source or anisotropy search, is a post-trial
  significance given, not just pre-trial (`scientific-style.md`)?
- **Hadronic-interaction-model dependence**: for composition or shower-based results,
  is the model-dependence of the result itself discussed, or only the model-driven
  systematic uncertainty band shown without comment on how much conclusions would
  change under a different model?
- **Solar-cycle/epoch context**: for direct-detection flux results below the knee,
  is the solar activity period stated, and is it relevant to the comparison being
  drawn against another experiment's data taken in a different epoch?

**Done when:** the draft states exposure (not just livetime), the solar-modulation period where relevant, the interaction models behind composition claims, and pre- and post-trial significances.
