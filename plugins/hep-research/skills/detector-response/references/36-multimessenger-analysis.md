# Multi-Messenger Analysis

Covers the analysis practices specific to combining information across messengers -
electromagnetic radiation, gravitational waves, high-energy neutrinos
([neutrino astronomy](34-neutrino-astronomy.md)), and charged cosmic rays - for the
same astrophysical event or source. The individual-messenger detection and background
methodology (IACT, neutrino telescope, surface array) is in the preceding references;
this file is about what changes when a claim rests on the *coincidence* between two or
more of them, which is a distinct and stricter statistical problem than a single-
messenger detection.

## Why coincidence claims need their own statistics

A single-messenger excess and a plausible coincident counterpart is not, by itself,
evidence of association - the question is always "how often would an unrelated
background produce a coincidence at least this good by chance", which requires a
well-defined background rate for the messenger providing the counterpart, not just for
the primary detection. Coincidence significance is not the product of the two
individual-messenger p-values (that double-counts the information and is a common,
serious error): the correct approach evaluates a joint likelihood or a single test
statistic built from both messengers' data together, or, when the two analyses are
genuinely independent, combines them with a method (Fisher's combined-probability
test is standard) that has known statistical properties under the null - see
[statistical inference](../../hep-statistics/references/08-inference.md) for the general combination and look-
elsewhere machinery this inherits.

## Timing and pointing coincidence windows

A coincidence search requires a **pre-defined time and pointing window**, fixed before
looking at the data whenever possible (or, if defined afterward, with the
look-elsewhere correction below applied to whatever choice was made):

- **Time window**: set by the light-crossing or causality argument for the
  progenitor hypothesis (e.g. seconds around a gravitational-wave merger time for a
  prompt electromagnetic or neutrino counterpart; longer, source-class-dependent
  windows for other progenitor scenarios), and by each messenger's own timing
  resolution and latency. A window chosen after seeing where an interesting event
  happened to fall is exactly the look-elsewhere problem in time rather than in sky
  position, and needs the same trials correction.
- **Pointing/localization coincidence**: each messenger localizes to some solid angle
  (arcseconds for optical follow-up, square degrees for a neutrino alert, tens to
  thousands of square degrees for a gravitational-wave skymap), and a claimed
  spatial coincidence must be evaluated against the **chance overlap rate** given both
  localization areas and the sky density of potential unrelated sources of the same
  apparent type, not just "the error regions overlap."

## Alert follow-up and public alerts

Real-time multi-messenger programs (gravitational-wave alerts triggering neutrino and
electromagnetic follow-up, and vice versa - e.g. a neutrino alert triggering
optical/gamma-ray follow-up of its localization) introduce analysis considerations
that a single, offline dataset does not have:

- **The alert's own false-alarm rate (FAR)** must be folded into any subsequent
  significance calculation for a claimed multi-messenger association - an alert issued
  at a loose FAR threshold (to maximize timely follow-up) is a weaker prior than one at
  a stringent threshold, and treating every public alert as equally reliable ignores
  information the sending collaboration already computed.
- **Retracted or updated alerts**: alert pipelines revise localization and
  significance as more data arrives (including retracting some alerts entirely); an
  analysis using archival alert data must use the final, reviewed alert properties
  and note if follow-up decisions were made using since-superseded preliminary
  information.
- **Follow-up sample selection is not blind in the way a scheduled survey is**: which
  telescopes triggered, how quickly, and with what depth depends on visibility,
  weather, and resource allocation that correlates with the alert's own properties
  (localization size, time of day) - a systematic to consider before treating a
  non-detection at one wavelength as equivalent evidence to a same-significance
  non-detection at another.

## Systematics distinctive to multi-messenger comparisons

- **Absolute timing must be on a common clock/timescale** across instruments (e.g.
  UTC with stated leap-second handling and each instrument's own absolute timing
  systematic) before any timing-coincidence significance is meaningful; a
  millisecond-scale timing offset between facilities is routinely larger than the
  timing precision either instrument quotes internally.
- **Astrometric/pointing systematics are per-instrument** and must be added, not
  assumed identical, when comparing localizations from different technologies (an
  optical position with sub-arcsecond systematic, a neutrino-telescope position with
  a degree-scale systematic dominated by ice/water optical-property modeling).
- **Distance and redshift**, where relevant (e.g. gravitational-wave luminosity
  distance versus an electromagnetic counterpart's redshift-derived distance),
  carry their own model dependence (cosmological parameters, peculiar-velocity
  corrections) that should be stated rather than treated as an exact cross-check.

## Deliverables

- The time and pointing coincidence window used, whether it was pre-registered
  or defined after inspecting the data, and the trials/look-elsewhere correction
  applied if the latter.
- The chance-coincidence rate given both messengers' localization areas/time windows
  and the relevant sky/time density of unrelated candidate sources - not just a
  statement that regions overlap.
- The combination method used for a joint or combined significance (joint likelihood,
  or a named combined-probability test), explicitly not a naive product of
  individual p-values.
- For an alert-triggered follow-up: the alert's stated FAR and localization at the
  time follow-up decisions were made, and whether later revisions or retractions
  affect the archival analysis.
- Per-instrument absolute timing and astrometric systematics, placed on a common
  reference frame/timescale before any coincidence claim is quantified.
