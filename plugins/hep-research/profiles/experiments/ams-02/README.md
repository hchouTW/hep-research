# AMS-02 profile

Profile `experiment:ams-02`, version 2.0.0. It adds knowledge of the Alpha Magnetic Spectrometer on the ISS to the
core skills (`hep-analysis`, `detector-response`, `hep-statistics`, `hep-theory`, `research-communication`,
`hep-computing`). It is never an entry point: a skill reads it when you name AMS-02 or your project config lists it.
Not endorsed by the AMS Collaboration.

This README is for people. The skills route through [index.md](index.md); the rules every answer follows are in
[modules/working-rules.md](modules/working-rules.md); the machine-readable manifest is [profile.json](profile.json).

## What it holds

- **Public-domain reasoning** about subsystems, observables, species, methods and time-dependent analyses
  (`modules/subsystems/`, `species/`, `methods/`, `periods/`, `sources/`).
- **A public evidence ledger**: 60 sources and 184 claims (`evidence/`, ids `ams02:S01`, `ams02:C01`). An AMS number
  is quoted only from a claim whose species, range, period and selection cover the statement. `evidence/index.md` is
  generated.
- **Dataset records** of published measurements (`datasets/`), metadata only.
- **Scripts** (`scripts/`): analysis-spec audit, paper-manifest and CRDB helpers.

It does not hold AMS internal data, notes, calibration constants, pass names, trigger bits, good-run rules or cuts.
Do not give them to the agent unless your project's `agent_policy` allows that content on a qualified host configuration
(none is qualified yet); public material you supply is labelled user-supplied and lives in your project, not here.

Access-controlled AMS-02 software and data knowledge (Offline library usage, EOS production listings, ntuple kits) is
not part of this profile. Authorized members get it from the separate companion plugin `ams02-research`, which
provides the profile `experiment:ams-02-private` and depends on this one. Without it, the skills say the profile is
unavailable and do not answer those topics from memory.

## Layout

| Path | Contents |
|---|---|
| `index.md` | routing map: request type to file |
| `profile.json` | id, version, scope, exclusions, resources, capabilities and their tests |
| `conventions.json` | rigidity definition and sign, charge-sign source, mass-number assumption |
| `modules/` | reference text by topic; `working-rules.md` holds the invariants and labels |
| `evidence/` | `sources.json`, `claims.json`, generated `index.md`, `papers_manifest.json` |
| `datasets/` | one JSON record per published measurement |
| `scripts/` | tools listed above |
| `benchmarks/` | empty (`.keep`) |
| `tests/` | unit tests named in `profile.json` |

## Using it

Name AMS-02 in a request, or pin the profile in `hep-research.project.json` at your project root:

```json
{"schema_version": "1.0.0", "plugin_version": ">=0.3,<1.0",
 "experiments": [{"profile": "experiment:ams-02", "version": "2.0.0"}]}
```

Networked scripts (`scripts/fetch_papers.py`: INSPIRE-HEP, arXiv, OpenAlex and the publisher or repository hosts its PDF
links name; `scripts/crdb_query.py`: CRDB at `lpsc.in2p3.fr`) run only with your approval, over https, and only where the
session's egress policy allows those destinations. They are maintainer tools, not for protected sessions.

## Tests

```bash
python3 -m unittest discover -s tests -t tests    # from this folder
```

All tests are structural and run anywhere. Capability status (`documented`, `tested-in-declared-environment`,
`demonstrated-on-synthetic-data`) is listed per capability in `profile.json`. A passing test checks structure and
consistency, not physical validity.
