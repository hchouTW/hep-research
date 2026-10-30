# hep-detector reconstruction coverage audit (base 313637c1, plugin 0.49.1)

Audit made on 2026-10-30 at the base commit `313637c16fd1fb4871d4ab3714ada7ab54ec5dd6` (plugin
0.49.1), before any content change, for task `hep-detector-reco` (step T2). Each cell crosses one
detector family with one reconstruction task; the sections named under Evidence were read and
the references grepped for synonyms (algorithm names, estimator names, method names) before a cell
was marked missing.

Marks: C covered (the method is described with its assumptions or failure modes); P partial (named
or described only in principle, without the method, its assumptions or its failure modes); M
missing (absent, or one sentence); `-` not applicable. Tasks: T1 local signal to hit; T2 pattern
recognition and candidate finding; T3 parameter estimation; T4 vertex, position, direction; T5
energy or momentum; T6 identity (PID, charge, topology); T7 per-event uncertainty, quality, tails.

Anchors are relative to `skills/hep-detector/references/` and use the slug rule of
`tests/skills/hep_detector/test_reference_links.py`; every anchor below was resolved against the
base files by the script at the end of this file.

## Matrix

| # | Family | T1 | T2 | T3 | T4 | T5 | T6 | T7 |
|---|---|---|---|---|---|---|---|---|
| F1 | Silicon pixel and strip | C | P | C | P | C | - | C |
| F2 | Gas wire, drift tubes, muon systems | C | C | C | - | C | C | C |
| F3 | Gaseous TPC | C | P | P | C | C | C | C |
| F4 | Scintillating fibre, nuclear emulsion | C | P | P | P | - | - | C |
| F5 | Calorimeters | C | C | C | M | C | P | P |
| F6 | Timing layers, TOF | C | - | C | P | - | C | C |
| F7 | Cherenkov PID (RICH, DIRC, TOP, threshold) | C | C | C | - | - | C | C |
| F8 | Multi-sample dE/dx, TRD, nuclear charge | C | - | C | - | - | C | C |
| F9 | Single-phase LArTPC | C | M | M | P | P | P | P |
| F10 | Dual-phase noble-liquid TPC | C | C | P | P | C | C | C |
| F11 | Cryogenic bolometer, germanium | C | P | C | P | C | C | C |
| F12 | Water Cherenkov | C | P | P | P | P | P | M |
| F13 | Liquid scintillator | C | - | M | M | P | P | M |
| F14 | Neutrino telescope (ice, water) | C | M | P | P | P | C | P |
| F15 | IACT | P | M | P | C | P | C | P |
| F16 | Air-shower surface array | P | - | C | C | C | P | M |
| F17 | Fluorescence telescope | P | M | C | M | C | C | P |
| F18 | Radio detection | M | M | M | M | M | M | M |
| F19 | Space-borne composite spectrometer | - | P | P | - | C | C | C |

Counts (computed by the script below from the table above): 118 applicable cells; C 60, P 39, M 19;
15 not applicable. Non-covered: 58 = A 19 + B 7 + C 6 + D 14 + Deferred 12.

## Reconciliation with the expected matrix

The audited matrix equals the expected matrix of the task file cell for cell. The base commit is
the 0.49.1 release against which the expected matrix and the patch were prepared, and the reading
below found no cell expected P or M that is now C, and no newly P or M cell outside groups A to D.
No group premise has changed: no reference at the base owns a photon-counting likelihood method,
an estimator-choice section, track- or vertex-finding algorithms, propagation in a non-uniform
field, LArTPC imaging reconstruction, calorimeter shower position, IACT image cleaning, surface-array
station handling or fluorescence geometry (a grep for the algorithm and method names, for example
Hough, cellular automaton, combinatorial Kalman, Runge-Kutta, adaptive vertex, broken lines,
tomographic, view matching, logarithmic weight, image cleaning, displacement method,
shower-detector plane, found only the one-line mentions cited below).

## Evidence for every non-covered cell

| Cell | Mark | Group | Anchor | What is there, and what is missing |
|---|---|---|---|---|
| F1 T2 | P | B | tracking-and-vertexing.md#from-hits-to-tracks-pattern-recognition | seeding, search window and ambiguity resolution in principle; no track-finding algorithm (road following, combinatorial Kalman filter, transforms, cellular automaton, learned) and no efficiency classes |
| F1 T4 | P | B | tracking-and-vertexing.md#vertexing | vertex fit resolution and impact parameter; no vertex-finding algorithm (iterative, adaptive, multi-vertex) or merged, split and fake vertices |
| F3 T2 | P | B | gaseous-and-specialized-tracking-technologies.md#time-projection-chambers-tpc | TPC principle, distortions and `t_0`; track finding on the 3D point cloud only through the generic pattern-recognition paragraph |
| F3 T3 | P | B | gaseous-and-specialized-tracking-technologies.md#distinctive-but-generalizable-reconstruction-and-performance-features-tpc | scaling and distortion maps; no fit propagation through a non-uniform field |
| F4 T2 | P | Deferred | gaseous-and-specialized-tracking-technologies.md#scintillating-fiber-trackers | fibre principle only; linking out of scope |
| F4 T3 | P | Deferred | gaseous-and-specialized-tracking-technologies.md#nuclear-emulsions | emulsion principle only; out of scope |
| F4 T4 | P | Deferred | gaseous-and-specialized-tracking-technologies.md#features-emulsion | vertex location in emulsion named; out of scope |
| F5 T4 | M | D | calorimetry-ecal-hcal.md#electromagnetic-showers | shower development and Moliere radius; no position estimator (centroid bias, logarithmic weights, depth) or direction |
| F5 T6 | P | D | calorimetry-ecal-hcal.md#calorimeter-based-identification | `E/p` and shower shape named; no shape-variable method or data-driven rejection measurement |
| F5 T7 | P | D | calorimetry-ecal-hcal.md#leakage-dead-material-and-containment | average leakage corrections; no per-event energy error, leakage flags or pulls |
| F6 T4 | P | B | timing-detectors.md#distinctive-but-generalizable-reconstruction-and-performance-features-timing | event start time as an object; no use of time in vertex finding |
| F9 T2 | M | C | noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs | one bullet "pattern recognition on wire-time images" |
| F9 T3 | M | C | noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs | no 3D strategy (view matching, tomographic imaging) or track fit |
| F9 T4 | P | C | noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs | `t0` need stated; no vertex or cosmic-removal method |
| F9 T5 | P | C | noble-liquid-neutrino-and-rare-event-detectors.md#neutrino-detectors | calorimetric vs kinematic energy; no `dQ/dx` corrections, recombination inversion, range or multiple-scattering momentum |
| F9 T6 | P | C | noble-liquid-neutrino-and-rare-event-detectors.md#features-neutrino-detectors | track/shower topology named; no Bragg-peak or shower-start identification |
| F9 T7 | P | C | noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs | ambiguities listed; no broken, merged, reversed tracks or control samples |
| F10 T3 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs | "xy from the light pattern" named; no light-pattern estimator |
| F10 T4 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs | no light-response map or near-wall bias |
| F11 T2 | P | Deferred | noble-liquid-neutrino-and-rare-event-detectors.md#rare-event-detectors | pileup named; out of scope |
| F11 T4 | P | Deferred | noble-liquid-neutrino-and-rare-event-detectors.md#rare-event-detectors | fiducialization by position named; position method out of scope |
| F12 T2 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | ring counting named; no ring-finding or hit-cleaning method |
| F12 T3 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | "charge/time likelihoods" named; no per-channel likelihood (unhit channels, first-photon time, noise) |
| F12 T4 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | vertex and direction named only |
| F12 T5 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | energy named only; no expected-light energy estimate |
| F12 T6 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | ring sharpness for e/mu named; no hypothesis comparison or neutral-pion two-ring fit |
| F12 T7 | M | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | nothing on per-event errors or quality variables |
| F13 T3 | M | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | one sentence on light yield; no estimator |
| F13 T4 | M | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | no vertex from timing |
| F13 T5 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | quenching named; no non-linearity model or non-uniformity map |
| F13 T6 | P | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | weak directionality noted; no delayed-coincidence or particle-type handling |
| F13 T7 | M | A | noble-liquid-neutrino-and-rare-event-detectors.md#water-cherenkov-and-liquid-scintillator-detectors | absent |
| F14 T2 | M | A | neutrino-astronomy.md#detection-principle | "pattern of hits is fit"; no hit cleaning, first guess or coincident-event splitting |
| F14 T3 | P | A | neutrino-astronomy.md#detection-principle | hypothesis fit named; no likelihood ingredients |
| F14 T4 | P | A | neutrino-astronomy.md#event-topologies | angular resolution by topology; no direction-fit method or wrong-minimum handling |
| F14 T5 | P | A | neutrino-astronomy.md#event-topologies | deposited vs neutrino energy; no muon energy-loss estimator |
| F14 T7 | P | A | neutrino-astronomy.md#event-topologies | resolutions quoted by topology; no per-event error or quality variables |
| F15 T1 | P | D | imaging-atmospheric-cherenkov.md#the-technique | night-sky background stated; image cleaning only named (noble-liquid-neutrino-and-rare-event-detectors.md#astroparticle-systems-within-the-same-framework) |
| F15 T2 | M | D | imaging-atmospheric-cherenkov.md#the-technique | no cleaning or island selection method |
| F15 T3 | P | A | imaging-atmospheric-cherenkov.md#the-technique | Hillas moments and classifiers; no image-template likelihood |
| F15 T5 | P | D | imaging-atmospheric-cherenkov.md#energy-reconstruction | size and impact distance in principle; no reconstruction-choice comparison |
| F15 T7 | P | D | imaging-atmospheric-cherenkov.md#the-technique | no per-event direction error or point-source check |
| F16 T1 | P | D | ground-based-detection-arrays.md#surface-detector-arrays | station signal and time named; no station calibration in reference-muon units or saturation handling |
| F16 T6 | P | D | ground-based-detection-arrays.md#surface-detector-arrays | composition motivation of the scintillator layer; no muon/electromagnetic separation method |
| F16 T7 | M | D | ground-based-detection-arrays.md#surface-detector-arrays | no per-event error from station fluctuations |
| F17 T1 | P | D | ground-based-detection-arrays.md#fluorescence-detectors | camera pixels named; no pixel selection |
| F17 T2 | M | D | ground-based-detection-arrays.md#fluorescence-detectors | no shower-detector-plane finding |
| F17 T4 | M | D | ground-based-detection-arrays.md#fluorescence-detectors | no timing geometry fit or monocular degeneracy |
| F17 T7 | P | D | ground-based-detection-arrays.md#atmospheric-monitoring | atmosphere as nuisance; no geometry-error propagation into `X_max` and energy |
| F18 T1-T7 | M | Deferred | ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays | radio named; out of scope (7 cells) |
| F19 T2 | P | B | space-based-direct-detection.md#rigidity-not-energy-is-the-natural-variable---for-a-spectrometer | spectrometer measurement in principle; track finding through the generic paragraph only |
| F19 T3 | P | B | space-based-direct-detection.md#rigidity-not-energy-is-the-natural-variable---for-a-spectrometer | rigidity from curvature; no propagation in a non-uniform field |

Covered items that the change must link to, not rewrite (each was read and is C at the base):
event-reconstruction.md#clustering; calorimetry-ecal-hcal.md#hadronic-showers-and-non-compensation;
particle-identification.md#combining-many-samples;
cherenkov-imaging-variants-and-photosensors.md#cherenkov-pid-variants;
noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs (dual-phase pulse finding, pairing
and corrections); front-end-waveform-processing.md#lar-tpc-signal-processing;
ground-based-detection-arrays.md#surface-detector-arrays (front fit, reference distance,
constant-intensity cut); detector-measurement-framework.md#forward-model-and-inverse-problem.

## Script

Run from the plugin root by extracting the block below:
`sed -n '/^```python$/,/^```$/p' docs/dev/hep-detector-reco/coverage-audit.md | sed '1d;$d' | python3 -`.
Output at the base: `cells 133 {'C': 60, 'P': 39, '-': 15, 'M': 19} applicable 118`, `non-covered 58
{'B': 7, 'Deferred': 12, 'D': 14, 'C': 6, 'A': 19}`, `anchors resolved 31`. It recomputes the counts from the matrix, checks that every non-covered cell has exactly one evidence
row with a group, and resolves every anchor against `skills/hep-detector/references/`.

```python
import re, collections, pathlib
text = pathlib.Path("docs/dev/hep-detector-reco/coverage-audit.md").read_text()
matrix = re.search(r"## Matrix\n(.*?)\n\nCounts", text, re.S).group(1)
cells = {}
for line in matrix.splitlines():
    f = [c.strip() for c in line.strip("|").split("|")]
    if re.fullmatch(r"F\d+", f[0]):
        for t, mark in enumerate(f[2:9], 1):
            cells[(f[0], f"T{t}")] = mark
counts = collections.Counter(cells.values())
print("cells", len(cells), dict(counts), "applicable", len(cells) - counts["-"])
evidence = re.search(r"## Evidence for every non-covered cell\n(.*?)\n\nCovered", text, re.S).group(1)
rows, groups = {}, collections.Counter()
for line in evidence.splitlines():
    f = [c.strip() for c in line.strip("|").split("|")]
    m = re.fullmatch(r"(F\d+) T(\d)(?:-T(\d))?", f[0])
    if not m:
        continue
    for t in range(int(m.group(2)), int(m.group(3) or m.group(2)) + 1):
        key = (m.group(1), f"T{t}")
        assert key not in rows, key
        assert cells[key] == f[1], (key, cells[key], f[1])
        rows[key] = (f[2], f[3]); groups[f[2]] += 1
noncov = {k for k, v in cells.items() if v in ("P", "M")}
assert noncov == set(rows), sorted(noncov ^ set(rows))
print("non-covered", len(noncov), dict(groups))
def slug(h):
    t = re.sub(r"[`*]", "", h.strip().lower()); t = re.sub(r"[^\w\- ]", "", t)
    return re.sub(r" ", "-", t)
refs = pathlib.Path("skills/hep-detector/references")
anchors = {a for _, a in rows.values()} | set(re.findall(r"[\w-]+\.md#[\w-]+", text.split("Covered items")[1].split("## Script")[0]))
for a in sorted(anchors):
    name, frag = a.split("#")
    heads = [slug(h) for h in re.findall(r"^#+ (.*)$", (refs / name).read_text(), re.M)]
    assert frag in heads, a
print("anchors resolved", len(anchors))
```
