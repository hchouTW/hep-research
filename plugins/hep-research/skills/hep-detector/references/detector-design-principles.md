# Detector design principles

Method for designing or upgrading an instrument: how physics requirements flow down to subsystem specifications,
which trade-offs and figures of merit decide between layouts, and how a design is optimized by simulation. Formulas
live in the references that own them and are linked, not copied. Facts about a named experiment's detector come
from its bound profile, the user, or the sourced detector atlas (`<plugin root>/profiles/reference/detector-atlas/`,
read with `<plugin root>/skills/hep-detector/scripts/detector_atlas.py query`), never from memory.

Routing boundary: designing the instrument (layers, field, material, granularity, timing) is hep-detector; designing
the measurement or analysis that uses it (estimand, selection, backgrounds, systematics plan) is hep-measurement.

## Requirements flow down

1. **Start from the measurement.** State the observable, its range, the precision needed at the edge of the range,
   and the backgrounds the detector must reject (for example a wrong-sign or misidentified species at a stated
   level). Write each as a number with its rate: "sigma(p)/p below 10% at 1 TeV/c", "charge confusion below 1e-4",
   "proton rejection 1e4 at 90% positron efficiency".
2. **Turn each into a subsystem requirement**, keeping the chain of assumptions: a momentum requirement fixes a
   curvature resolution, which fixes point resolution, field integral and lever arm; a rejection requirement fixes
   the number of independent samples and their resolution. Record which requirement drives which specification, so a
   later change of one is traced to the others.
3. **Add the operational constraints**: mass, power, data rate, radiation tolerance, cost, and, for an upgrade, what
   can change in a running detector (the existing tracks, the alignment reference, the eras it creates; see
   "Adding a tracking layer to a running detector" in [calibration and alignment](calibration-and-alignment.md)).
4. **Write acceptance criteria before the design study**: the figure of merit, the value that passes, and the test
   (simulation, test beam) that will show it.

## Trade-offs and figures of merit

- **Tracking**: point resolution, field and lever arm against material. The intrinsic term grows as p / (B L^2) and
  the scattering term as 1/(beta B L) sqrt(x/X0) ([tracking and vertexing](tracking-and-vertexing.md), "Momentum
  measurement"); the crossover rigidity and the MDR summarize the pair. Lever arm is the strongest lever; added
  layers help less than added length, and each adds material.
- **Impact parameter**: radius and material of the innermost layer ([tracking and vertexing](tracking-and-vertexing.md),
  "Vertexing").
- **Calorimetry**: stochastic, noise and constant terms against depth, sampling fraction and segmentation
  ([calorimetry](calorimetry-ecal-hcal.md), "The resolution decomposition"); containment against mass.
- **Particle identification**: separation power in sigma as the figure of merit, with the number of samples and the
  tails ([particle identification](particle-identification.md)).
- **Timing, triggering and pileup**: rate capability, dead time and live time
  ([triggers, luminosity and pileup](triggers-luminosity-pileup.md)).
- **Common equations and their validity**: [core detector equations](core-detector-equations.md).

A figure of merit is useful only with its denominator: resolution at which momentum, rejection at which efficiency,
acceptance for which source distribution. Compare layouts at equal cost or mass when that is the binding constraint.

## Optimization by simulation

1. **Analytic scan first.** `<plugin root>/skills/hep-detector/scripts/tracker_resolution.py` gives the exact
   least-squares curvature resolution for stated layer positions (with the Gluckstern approximation for comparison),
   the scattering term, the MDR, the impact-parameter form, and `scan`, the layouts that meet a stated requirement.
   `multiple_scattering.py` gives the Highland angle and material budget of a stack.
2. **Fast simulation** of the candidates: `toy_spectrometer.py` (seeded, synthetic) produces events and periods for
   a declared layout, including an era that adds a layer, so selection, response and stability tools can be run on
   the design before any hardware exists.
3. **Full simulation** (Geant4) for the finalists, with the validation discipline of
   [detector simulation](detector-simulation.md): tails, material, and the response at the edges of the range.
4. **Test beam and prototypes**: measure what simulation cannot be trusted for (tails, noise, charge collection),
   and feed it back into the simulation before the final comparison.
5. **Record the decision**: layouts compared, figures of merit, the requirement each met or missed, and the
   assumptions (field map, material, alignment) that the conclusion depends on.

## Failure modes

- Quoting a resolution without its momentum, angle or species.
- Optimizing the core resolution while the requirement is set by a tail (charge confusion, misidentification).
- Comparing the Gluckstern estimate of one layout with a full fit of another; compare like with like and state the
  approximation (`tracker_resolution.py` reports both).
- Adding material for support or cooling without carrying it into the scattering term.
- Designing an upgrade without planning the alignment and calibration of the new configuration against the old one.
