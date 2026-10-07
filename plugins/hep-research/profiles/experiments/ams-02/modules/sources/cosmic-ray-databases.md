# Cosmic-Ray Databases: CRDB (LPSC) and the ASI SSDC Cosmic Ray Database

## When to read this file

If this session has not read them yet, read the profile's [working rules](../working-rules.md) first.

Read when the user asks to compare AMS with other experiments, to find which paper or dataset holds a published cosmic-ray measurement, to retrieve published data in bulk or from a script, to plot a compilation, or names CRDB or the SSDC cosmic-ray database. Do not read it to answer "what did AMS measure": that comes from the AMS papers through [source-index](../../evidence/index.md) (`source-policy`).

## Contents

1. [What the two databases are](#what-the-two-databases-are)
2. [Rules for using them with AMS data](#rules-for-using-them-with-ams-data)
3. [Cross-checking an AMS number](#cross-checking-an-ams-number)
4. [Pitfalls](#pitfalls)
5. [Querying and citing](#querying-and-citing)
6. [Failure modes](#failure-modes)
7. [Required source classes](#required-source-classes)
8. [Questions to ask the user](#questions-to-ask-the-user)

## What the two databases are

Both are Tier 6 secondary compilations of published data: navigation and cross-check only, never the source of an AMS number.

- **CRDB (LPSC Grenoble), https://lpsc.in2p3.fr/crdb/**: [Documented, S50 (website), C125-C128]. Cosmic-ray data and meta-data from 10^6 to 10^21 eV: leptons, nuclei (isotopes, elements, groups), antinuclei and dipole anisotropy, entered from publications with the ADS and DataThief. Access by a website, a REST interface and a pip-installable Python library; exports in USINE, GALPROP and csv formats. On 2026-10-02 the page stated version V4.2 (September 2026) with 143 experiments from 614 publications (C125; the counts change with each release). The four papers to cite are in S51 (C129): 2014, v4.0 (2020), v4.1 (2023) and the v4.2 preprint (2026); the v4.1 abstract says the database includes the hundreds of thousands of AMS-02 and PAMELA time-series points as entered by the CRDB team, whose agreement with the AMS papers was not checked.
- **ASI SSDC Cosmic Ray Database, https://tools.ssdc.asi.it/CosmicRays/sf_search.jsp**: [Documented, S52 search page at screenshot level, C183; S53 2017 abstract, C130]. The page, seen only as one screenshot of its search form (2026-10-02, no query run), is headed "COSMIC RAY Database" (subtitle "Database for charged Cosmic Ray measurements"), says it gives access to published data from missions dedicated to charged cosmic-ray measurements, that its data-set is "not comprehensive but in expansion", that data sit in a SQL database searched by particle species, measurement and/or mission name (refined search available), that results come as a table to plot, export and download and include published points with uncertainties and some meta-data, that manipulated data (for example energy-rigidity conversion or unit change) are flagged in the output file, and that users should consult the original publication. The form has a Particle selector, a Plot selector pair, an Experiments selector reading "All selected (25)", special-dataset boxes "SEP events" and "trapped", and a button "Most recent time-dependent AMS data available here!". It calls itself "CRDB" and shows "Version 3.3", which is **not** the LPSC CRDB or its version (V4.2): always say which database. **Not known** (no query was run): which 25 experiments, which AMS-02 datasets and periods, the output formats, access terms, and whether login is needed for any function [Unknown/needs input]; do not describe them, and do not script requests to it (scripted requests got HTTP 429, timeouts and a single-sign-on redirect). A 2017 proceedings (S53, C130) describes the database as "under development" and built to support PAMELA and AMS-02 retrieval; it is older context, not a description of the current holdings. Re-check by running a query in a browser.

Which AMS datasets these databases hold, and with what values, is [Unknown/needs input] until a query is run and the version and date recorded. One test query of CRDB was run on 2026-10-02 (proton flux, native rigidity axis, `exp_dates=AMS`, conversions and combinations off, via `<plugin root>/profiles/experiments/ams-02/scripts/crdb_query.py`): the export returned two AMS02 sub-experiments with different data-taking ranges, 2011/05/19-2013/11/26 and 2011/05/19-2018/05/26 (72 rows each); the CRDB release was not recorded, no value was compared with a paper and no ledger claim rests on it. Content changes with each CRDB release, so run a new query before relying on it.

## Rules for using them with AMS data

1. **A database value is a transcription.** Label it `[Secondary: CRDB, version V, retrieved date]` and give the primary AMS paper (S-number from the index) to check it against. An AMS number you quote as a result needs its own claim in the index (invariant 9); if the index has none, answer symbolically or cite the paper without the number.
2. **Keep the native variable.** Each AMS paper states whether its flux is in rigidity or in energy (the ledger claims say which, for example the 2014 lepton fluxes are in energy, C115-C119, and the antiproton flux in rigidity, C120-C122). Query with the same axis and with conversions off (below). Convert only with `|Z|`, `A` and the rest mass stated, and only through exact conversions (isotopic and leptonic fluxes, leptonic ratios, p-bar/p, C127); approximate conversions of element fluxes use a proxy A and mass and can produce systematic errors larger than the data uncertainties (C127), which is the same trap as invariant 1.
3. **Do not merge sub-experiments.** One experiment appears as several datasets (time-averaged, per Bartels rotation, per day, different periods and analyses); the default query returns all datasets regardless of period overlap, and the page advises keeping the datasets over the longest periods (C126). Never average them or treat their union as one measurement; time series are excluded by default (`time_series=no`, C128). Which AMS datasets a given release holds is [Unknown/needs input] until it is queried and recorded; C129 records only the abstracts' statements that CRDB v4.1 included AMS-02 and PAMELA time series and v4.2 added AMS-02 data, with no list of datasets or periods.
4. **A systematic of 0 in CRDB means "not separately quoted"** for old data (C126). AMS papers quote systematics separately: take them from the paper's claims, not from CRDB.
5. **Record version and date** with anything extracted: counts and content change with each release (C125, C129).
6. **Agreement between experiments is not validation.** Cite a metric and a trigger (invariant 10) rather than "consistent with PAMELA".

## Cross-checking an AMS number

1. Fix the estimand and variable (invariant 1): species, rigidity or energy, time resolution.
2. Query on the native axis with `combo_level=0` and `energy_convert_level=0`, restricted to the AMS sub-experiments (`exp_dates=AMS`, optionally with a time interval); use the Python library or REST (C128). Say why: combo level 0 returns native points only (levels 1-2 form ratios or products at query time within 5% or 20% in energy), and conversion level 0 returns only the queried axis (level 1 exact conversions only; level 2 uses a proxy A and mass for elements and, per the page, is a last resort that can cause systematic errors larger than the data uncertainties) (C127). Time series are excluded by default (C128).
3. Map each returned `SUBEXP_NAME` to its AMS paper through its name and data-taking range, then to the ledger source and claim (period and range must match the claim's scope).
4. Compare value, bins and uncertainty with the paper's statement; where they differ, the paper wins, and the difference (transcription from a plot, rebinning, a different data period) is worth reporting to the CRDB team.
5. Note the `PUBLI-DATAORIGIN` (table or plot) and the energy-scale column when present (C126).

## Pitfalls

- **Unit labels differ.** CRDB gives kinetic energy per nucleon in GeV (the per-nucleon meaning is in the symbol, since V4.1, C127); `<plugin root>/core/kinematics/relativistic.py` labels it GeV/n. The numbers are the same convention; check a conversion with the script and state `Z`, `A` and the mass. The two formulae quoted in C127 agree with the script for one helium-4 point (checked 2026-10-02).
- **Combos and conversions are query-time products.** Combos multiply or divide native data of one sub-experiment within 5% (level 1) or 20% (level 2) in energy and add relative errors in quadrature (C127): a CRDB "B/C" may be a combination of two native fluxes and not a published ratio.
- **Names are not unique across versions.** Sub-experiment names encode period and technique (C126); two AMS datasets with similar names can be different analyses.
- **The two databases are different services** with different maintainers; the SSDC one is the ASI Cosmic Ray Database (C130). Say which one.

## Querying and citing

[General method] `<plugin root>/profiles/experiments/ams-02/scripts/crdb_query.py` runs ONE query with the defaults of the cross-check procedure above (`url` builds the REST URL offline; `fetch --num H --energy-type R --out FILE` saves the export and a `.meta.json` sidecar with the request, UTC retrieval time, the CRDB export date from the file header, a SHA-256 and the CRDB version only if you pass `--crdb-version`; `summarize FILE` lists the sub-experiments with their data-taking ranges and row counts and labels every row secondary). It never retries a block (401, 403, 429) and never converts or combines. The page's own REST example is `curl -L 'http://lpsc.in2p3.fr/crdb/rest.php?num=B&den=C&energy_type=EKN' > db.dat`, and the parameters are in C128 (mandatory `num`, `den`, `energy_type`; a positron is `e%2B`). A native-axis AMS query would add `exp_dates=AMS&combo_level=0&energy_convert_level=0`. The Python library is installed with `pip install crdb` and can generate the list of citations for returned datasets (C128). Cite the CRDB papers (S51) and, for each dataset used, its primary paper; for the SSDC database cite S52 and S53 and say that only the search form was seen.

## Failure modes

- Quoting a CRDB or SSDC value as an AMS result, or as "verified" because it came from a database.
- Using approximate element conversions, or default combos, without saying so.
- Treating several AMS sub-experiments as one dataset, or forgetting that time series are excluded by default.
- Reading a CRDB "0 systematics" as an AMS statement.
- Describing the SSDC page's holdings, experiments list, output formats or terms of use (only its search form was seen), or confusing it, or its "Version 3.3", with the LPSC CRDB.
- Quoting CRDB counts or version without date, or hammering a service that returned 429.

## Required source classes

Tier 6 for the databases and their descriptions (S50-S53); Tier 1 AMS papers (and their ledger claims) for every AMS value; Tier 4 or textbook kinematics for conversions (`<plugin root>/core/kinematics/relativistic.py`). Secondary-only evidence must be labeled secondary (`source-policy`).

## Questions to ask the user

Which database (CRDB at LPSC or the ASI SSDC one)? Which species, rigidity or energy range, and which AMS dataset (time-averaged, per rotation, daily)? Is the goal a comparison with other experiments, a data export, or a check of a transcribed value? Which database version and retrieval date should be recorded?
