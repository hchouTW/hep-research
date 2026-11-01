# Event display checklist

Tick each line with evidence (a command and its output, a file, a screenshot). An unticked line is reported as
not done, never as passed. Guide: [event-displays.md](event-displays.md); facts: [event-display-facts.md](event-display-facts.md).

## Before building

- [ ] The request is written down (`assets/event-display/task.md` for durable work): which events, which results, which bindings (event / dataset / static), who will open the page and where.
- [ ] Policy checked: the project's `agent_policy`, blinding and data-sharing rules allow these events and results to go into a static page. If not sure, ask.
- [ ] Every result to show already exists and has a producer (a computational-run, a file the user named). Nothing will be computed for the page.
- [ ] Units and coordinate frame of every branch are known (not inferred from values).

## Export

- [ ] `export_events.py` returned `ok` into a new folder; `export-record.json` lists exactly the selected events (`--entries`/`--events`) with sha256 and object counts; no `Tracks` written.
- [ ] Every result export returned `ok`, or its refusal was resolved upstream (not by editing a payload or forcing a flag).
- [ ] `--errors disabled` was used only for a weighted histogram without Sumw2, and the panel says so.
- [ ] `python3 export_histogram.py --self-test` returned `ok` (after any change to the exporter).

## Web and bundle

- [ ] `web/package-lock.json` is committed in the project; `npm ci` (not `npm install`) built `web/dist`.
- [ ] `npm ls jsroot` shows one JSROOT; `@angular/core` is 20.x.
- [ ] `build_bundle.py` returned `ok`; coverage gaps (events without results) are understood and visible.
- [ ] `check_bundle.py bundle --spec bundle-spec.json` returned `ok`: digests, no unlisted objects, relative paths, every payload equals its sidecar's derivations, every sidecar equals its source; `unchecked_sources` is empty (or each unchecked panel is named in the hand-off).

## Browser

- [ ] `test_page.py bundle` returned `ok` with every check listed (default event, panels' readback, rapid switching, tampered object refused, no external request, no page error).
- [ ] A person or a screenshot confirmed the page shows the event and the charts sensibly (camera, geometry not hiding the event, titles readable).
- [ ] Any new panel module has its own validator, readback and test entry, and the mutation test (alter one number in the module) makes `test_page.py` fail.

## Delivery

- [ ] Served over HTTPS, or plain HTTP on loopback only; neither `file://` nor plain HTTP to another host is offered.
- [ ] Labels (`synthetic`, `unvalidated`, `user-supplied`, schematic geometry) are visible on the page and in the hand-off.
- [ ] A `computational-run` records inputs with sha256, commands, tool versions (Python, Node, the npm lockfile's digest), outputs and the check results.
- [ ] The hand-off says what the checks do not prove: the physics of the analysis, the mapping, the units and the geometry need the project owner's review.
