# Nuclear interactions in detector material

How a nucleus that crosses the material of an instrument is lost (survival) or turned into a lighter species that
the instrument then counts (feed-down), and how the two corrections enter a measurement. The cross-section
conventions (inelastic or charge-changing, targets, straight-ahead approximation, uncertainty model) are in
`<plugin root>/skills/hep-theory/references/nuclear-cross-sections.md`; the order of the corrections in the chain is in
`<plugin root>/skills/hep-measurement/references/correction-chain.md` ("Nuclei and isotopes"). The tool is
`scripts/survival_feeddown.py`.

## Survival

- The interaction length of a nucleus in a pure material of molar mass A (the atomic mass in g/mol, not the integer
  mass number) is `lambda = A / (N_A sigma)` (g/cm2), with sigma the inelastic cross section per target nucleus. In a
  mixture with mass fractions w_i and molar masses A_i (g/mol), `1/lambda = sum_i w_i N_A sigma_i / A_i`, which is
  the same as crossing the components one after the other.
- Over layers of grammage x_k, `P = exp(-sum_k x_k / lambda_k)`; the flux above the material divides the counted
  flux by P. x_k is the grammage along the track: a planar layer of normal grammage t_k crossed at angle theta to its
  normal has `x_k = t_k / cos(theta)`. With a range of directions, compute P per event or per direction bin and
  average over the accepted directions; P at the mean grammage is not the mean P. Only the material between the point where the flux is defined (top of atmosphere for a balloon-borne
  instrument, top of instrument, or a layer) and the layers whose charge selects the species counts; state which.
- Material outside the instrument (residual atmosphere above a balloon, a pressure vessel or dome) counts in both
  survival and feed-down. Fragments made there cannot be tagged by the instrument's charge layers, so their
  feed-down comes from cross-section models or simulation, and its cross-section uncertainty can dominate a
  secondary-to-primary ratio at high energy. The overburden and the secondaries made in it belong in the instrument
  response ([space-based direct detection](space-based-direct-detection.md), "Instrument response functions").
- Which cross section: a selection that requires the same charge in every layer measures charge-changing survival;
  one that requires the same isotope measures inelastic survival. The cross section and the selection agree.
  `survival_feeddown.py` reads every cross section under the key `inelastic`, whatever its kind: for a charge-tagged
  selection put the charge-changing cross sections there and name the kind in the table's `source`.
- Survival depends on energy through sigma(E): the correction is per bin, from cross sections at that energy.
- `P = exp(-sum x/lambda)` covers only the nuclear (inelastic or charge-changing) losses. Other losses in the same
  material are separate factors with their own source, never folded into lambda: scattering or energy loss that takes
  a nucleus out of the acceptance or below a selection threshold (at low energy the energy also changes across the
  stack, so sigma is not constant along it), and the efficiency of the charge-consistency cuts for nuclei that did
  not interact. Take them from a simulation of the instrument or from data, and count each once (in the acceptance
  or in the survival, not both).

## Feed-down

- A heavier nucleus that fragments above the selecting layers can be counted as a lighter species. To first order
  `N_feed = N_heavy (1 - P_heavy) f(heavy -> light)`, with N_heavy the number arriving above the material and f the
  fraction of its interactions that leave a fragment reconstructed as the light species. Second-step fragmentation
  and the survival of the fragment itself are neglected at this order; when they matter, use a species-migration
  response (`references/response-and-forward-folding.md`, "Species migration") instead of a subtraction. The tool
  refuses a fraction from a species into itself; it has no charges, so it checks only that the two species differ.
- Feed-down is subtracted before the survival correction of the light species (a background in reco space). A
  fixed subtraction ignores that N_heavy is itself measured at the same time: the coupled treatment is in
  `<plugin root>/skills/hep-measurement/references/backgrounds.md` ("Coupled species").
- Fragmentation in the layers that measure the charge is tagged by comparing the charge measured before and after;
  only the untagged part is feed-down.

## Uncertainty

- The cross sections are the dominant input: vary them as model alternatives and with a scale nuisance s
  (sigma -> (1 + s) sigma). At s = 0, `dP/ds = P ln P`, and `dN_feed/ds = -N_heavy f P_heavy ln P_heavy` for the heavy
  species' scale. In a cosmic-ray measurement, the same cross sections may also enter the interpretation
  (production in the interstellar medium); declare that correlation together with the correction (see the
  hep-theory reference and [cosmic-ray propagation](cosmic-ray-spectrum-and-composition.md#propagation)).
- The material description (grammage, composition) is a second input, with its own uncertainty from the detector
  model or a beam test; a grammage scale enters exactly like a cross-section scale.

## Catalog effects and correction keys

The corrections are named with the catalog effects `survival` and `fragmentation_feeddown`
(`<plugin root>/contracts/vocab/effects.json`). `survival_feeddown.py` writes them as recipe steps with the correction
keys of `measurement:correction-keys-v1` (target scope `species:<name>`, the sha256 of the cross-section table as
calibration digest, variation `nominal`, the declared stage), so a reviewer can trace each factor to the step that
applies it (hep-measurement's review, "Spec against implementation").

## Worked example (synthetic)

The example of the correction chain: x = 10 g/cm2 and lambda = 20 g/cm2 for the light species give P = 0.607 and a
correction 1/P = 1.65; 1000 heavy nuclei with P_heavy = 0.55 and f = 0.10 give 1000 x 0.45 x 0.10 = 45 feed-down
events (`tests/skills/hep_detector/test_survival_feeddown.py` reproduces both).
