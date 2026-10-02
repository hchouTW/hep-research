# Astroparticle and Cosmic-Ray Papers

How writing and reading conventions shift for astroparticle physics and cosmic-ray
papers — ground-based air-shower arrays (Pierre Auger, Telescope Array), imaging
atmospheric Cherenkov telescopes (CTA, H.E.S.S., MAGIC, VERITAS), water/ice Cherenkov
and neutrino observatories (IceCube, HAWC, LHAASO), and space-based direct detection
(AMS-02, DAMPE, CALET, Fermi-LAT). This file covers the *writing/venue/citation*
differences; the physics content itself (spectrum, composition, anisotropy, shower
physics, statistics for point-source searches) is `hep-analysis`'s domain — see its
astroparticle references (cosmic-ray spectrum and composition, extensive air showers,
ground-based arrays, imaging Cherenkov, neutrino astronomy, space-based direct
detection, astroparticle statistics) for the content itself. Everything below assumes
that physics is already worked out and focuses on how to write it up.

## Table of contents
- [How the structure differs from collider HEP](#how-the-structure-differs-from-collider-hep)
- [Journals and venues](#journals-and-venues)
- [Collaboration author lists and acknowledgments](#collaboration-author-lists-and-acknowledgments)
- [Citations: ADS vs. INSPIRE-HEP](#citations-ads-vs-inspire-hep)
- [Worked example: AMS-02's publication pattern](#worked-example-ams-02s-publication-pattern)
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
- **"Luminosity" becomes "exposure."** Ground-based arrays report exposure in units
  of area × solid angle × time (e.g. km²·sr·yr for Auger surface-detector analyses);
  space-based spectrometers report it in m²·sr·s or as an effective-area-vs-energy
  curve integrated over livetime. State how the exposure was calculated (Monte Carlo
  vs. data-driven) the same way a collider paper would justify a luminosity
  measurement.
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
- **Solar modulation** is a required systematic discussion for any low-energy
  (sub-~30 GeV/nucleon) cosmic-ray flux measurement from a space-based detector —
  state the solar activity period (which matters for AMS-02/PAMELA-era comparisons)
  and whether a force-field or numerical modulation model was used to compare across
  epochs.

## Journals and venues

In addition to the collider-physics venues in `latex-and-formatting.md` (sources and
last-verified dates are in its final section; rows marked "Not checked" were not verified):

| Venue | Class file | Typical length | Notes |
|---|---|---|---|
| PRD (astro-ph flavor) | `revtex4-2` (`\documentclass[aps,prd,reprint]{revtex4-2}`) | No fixed limit for regular articles (Letters 4,500 words) | Same class as collider PRD; astroparticle results commonly published here |
| JCAP | `article` + SISSA's `jcappub.sty` | No fixed limit | JHEP-family house style; `\bibliographystyle{JHEP}` |
| ApJ / ApJL | AASTeX v7 (`aastex7.cls`; TeX distributions may still ship `aastex631`) | ApJL: 3,500 words, ≤ 5 figures+tables (soft limits); abstract ≤ 250 words | Get the current class from the AAS journals author-resources page; natbib author-year citation is the house default |
| Astroparticle Physics (Elsevier) | `elsarticle.cls` | Not checked | Elsevier house style; check current author guidelines for citation style option |
| A&A | A&A's own `aa.cls` | Not checked | Used for some multi-messenger/counterpart papers | 

As with the collider-physics class files, always pull the current `.cls`/`.bst` from
the publisher rather than reconstructing from memory — AASTeX in particular changes
version numbers with formatting-relevant changes (author lists, table environments).

arXiv category: `astro-ph.HE` (high-energy astrophysical phenomena) is the primary
category for most cosmic-ray/gamma-ray/neutrino result papers; cross-list `hep-ex` if
the result also has direct particle-physics relevance (e.g. an AMS-02 antimatter/dark
matter search). See `latex-and-formatting.md`'s arXiv-specific-rules section for the
general category-selection guidance.

## Collaboration author lists and acknowledgments

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
  astronomy-side ones from ADS into the same `.bib` file. Deduplicate by DOI when a
  paper appears in both databases with different keys, the same way
  `citations-and-bibliography.md` recommends deduplicating by INSPIRE key.
- **Citation style**: ApJ/A&A/MNRAS commonly use `natbib` author-year citation
  (`\citep{}`/`\citet{}`) rather than the numbered style collider-physics venues use
  — check the specific venue's current style file rather than assuming numbered
  citations carry over.

## Worked example: AMS-02's publication pattern

The Alpha Magnetic Spectrometer (AMS-02) collaboration (source: `ams02.space`,
cross-checked against INSPIRE-HEP records) is a useful concrete illustration of
several points above, precisely because it deviates from the "typical" pattern in a
few visible ways:

- **Single-venue, letter-only publishing.** Of AMS-02's collaboration papers (31 as
  of 2026-09-10, verified against `ams02.space/publications` and cross-checked
  against raw page content — see the verification note below), essentially all are
  Physical Review Letters — short, headline-result papers rather than long
  PRD-style methods papers. Don't assume every large collaboration spreads results
  across PRL *and* PRD the way collider experiments often do; check the specific
  collaboration's own publication list rather than defaulting to the collider
  pattern.
- **No arXiv preprint, by design.** Checking INSPIRE-HEP directly (not just the
  collaboration's own site) confirms AMS-02's PRL papers carry no `arxiv_eprints`
  field at all — e.g. "Properties of Iron Primary Cosmic Rays" (PRL 126, 041104,
  2021) and the 2016 antiproton-flux PRL are both published with no arXiv companion.
  This is a deliberate collaboration policy, not a missing upload: **do not assume
  every physics paper has, or will get, an arXiv preprint** — ask the user which
  policy their own collaboration follows before defaulting to "post to arXiv first."
- **One long review alongside many short letters.** "The Alpha Magnetic Spectrometer
  on the International Space Station: Part II — Results from the First Seven Years"
  is published in *Physics Reports*, not PRL — a single comprehensive review sitting
  alongside dozens of individual-result letters. This is the review-article pattern
  from `paper-genre-variants.md`'s "Review articles" section applied at collaboration
  scale: a Phys. Rept. periodically consolidates and cross-references the individual
  PRL results rather than duplicating their derivations.
- **A very large, structured author list.** AMS-02 is 44 institutions across the
  Americas, Europe, and Asia, with one PI (Samuel C. C. Ting) and six named deputy
  PIs, operating out of CERN (which hosts the Payload Operations Control Center) in
  partnership with NASA and ESA. This is exactly the scale where
  "Collaboration author lists and acknowledgments" above applies literally — get the
  current author-list macro and acknowledgments boilerplate from the collaboration
  rather than drafting anything by hand.
- **Per-paper supplemental data links, separate from the journal.** AMS-02's own
  publications page links "supplemental material and data" for each paper directly
  from the collaboration website, alongside (not instead of) the journal's own DOI
  and an INSPIRE-HEP citation-count link. When citing or building on an AMS-02
  result, check the collaboration site for this supplemental link, not just the
  journal page — the underlying flux tables are often published there rather than
  (or in addition to) HEPData.
- **A mixed-citability technical-progress genre — check each page, don't
  generalize from one.** AMS-02's `ams02.space/advances-data-analysis` section
  documents incremental analysis-method improvements, and checking three of them
  directly shows a genuinely mixed picture, not a uniform one: the
  coordinate-measurement-precision page resolves to a dedicated instrumentation
  paper (G. Ambrosi et al., *Nucl. Instrum. Methods Phys. Res. A* **869**, 29
  (2017)), and the ECAL-reconstruction page to another (A. Kounine et al.,
  *Nucl. Instrum. Methods Phys. Res. A* **869**, 110 (2017)) — while the
  tracker-charge-sign-identification page cites only an *older* PRL for
  comparison, with no DOI, arXiv ID, or proceedings reference for the
  improvement it actually describes. Don't assume a page's citability from
  another page in the same site section, in either direction: some incremental
  analysis improvements get a dedicated NIM A–style paper of their own, and some
  stay web-only. Check the specific page: if it names a paper, cite that paper
  directly (not the web page) for the technique; if it doesn't, either find
  where a later peer-reviewed paper incorporates and describes it, or cite the
  web page explicitly as a website (with an access date), never as if it were
  peer-reviewed literature on its own. Ask the user's own collaboration whether
  it maintains an equivalent "advances" page and what fraction of its entries
  get a dedicated write-up before assuming either way.
- **The `ams02.space/physics/*` "highlight" pages are not collaboration-authored
  outreach**, despite living on the collaboration's own domain — see
  `outreach-and-public-facing-summaries.md`'s "Collaboration voice vs.
  syndicated commentary" section for the worked byline-by-byline breakdown (a journalist's
  recap, an APS *Physics Magazine* Synopsis, and an APS *Physics Magazine*
  Viewpoint, none written by the collaboration itself).

**Verification note (this is a live-changing fact, not a fixed one):** the counts
above were checked by fetching the collaboration page directly and cross-checking
against its raw content (not just an AI-summarized paraphrase of it — a first-pass
summary claimed 42 publications, which was wrong; an itemized listing and an
independent raw-content check both confirmed 31). This collaboration publishes a
few papers a year, so this count will drift. Re-verify against
`ams02.space/publications` (and INSPIRE-HEP) before citing an exact number, and
update the stamped date above when you do — don't carry this specific number
forward past its verification date as if it were still current. This is
`citation-verification.md`'s "record the lookup date" requirement applied to a
worked example rather than a manuscript claim.

For the physics/instrument content behind these papers (the AMS-02 detector,
analysis techniques, and results themselves), see `hep-analysis`'s dedicated case
study — this section is only about the publication pattern.

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

These extend, not replace, `scientific-style.md`'s significance-language table:

- **Pre-trial vs. post-trial significance** must both be stated whenever a search
  scanned more than one direction, energy bin, or source candidate — quoting only the
  pre-trial number is the astroparticle-physics analogue of the look-elsewhere effect
  in `reading-papers.md`, and referees will ask for the post-trial number if it's
  missing. For an ON/OFF (source vs. background region) count, the pre-trial
  significance is usually Li & Ma's eq. 17 (T.-P. Li and Y.-Q. Ma, ApJ 272, 317
  (1983), doi:10.1086/161295; checked 2026-09-26): cite it and state the ON/OFF
  exposure ratio alpha used. Computing it belongs to `hep-analysis`.
- **"Detection" vs. "hint" vs. "evidence"** for a point source or transient
  association follows the same σ-based conventions as `scientific-style.md`'s table,
  but state explicitly whether the quoted significance is pre- or post-trial each
  time — a "5σ pre-trial" claim is not an observation-level "detection" if the trials
  factor brings it below 5σ post-trial.
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
`reading-papers.md`'s HEP-specific checklist with:

- **Exposure/livetime and duty cycle**: stated explicitly, and consistent with the
  array's/instrument's known operating history for that period?
- **Trials factor**: for any point-source or anisotropy search, is a post-trial
  significance given, not just pre-trial?
- **Hadronic-interaction-model dependence**: for composition or shower-based results,
  is the model-dependence of the result itself discussed, or only the model-driven
  systematic uncertainty band shown without comment on how much conclusions would
  change under a different model?
- **Solar-cycle/epoch context**: for direct-detection flux results below the knee,
  is the solar activity period stated, and is it relevant to the comparison being
  drawn against another experiment's data taken in a different epoch?
