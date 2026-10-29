# Nuclear interactions in detector material

How a nucleus that crosses the material of an instrument is lost (survival) or turned into a lighter species that
the instrument then counts (feed-down), and how the two corrections enter a measurement. The cross-section
conventions (inelastic or charge-changing, targets, straight-ahead approximation, uncertainty model) are in
`<plugin root>/skills/hep-theory/references/nuclear-cross-sections.md`; the order of the corrections in the chain is in
`<plugin root>/skills/hep-measurement/references/correction-chain.md` ("Nuclei and isotopes"). The tool is
`scripts/survival_feeddown.py`.

## Survival

- The interaction length of a nucleus in a pure material of mass number A is `lambda = A / (N_A sigma)` (g/cm2), with
  sigma the inelastic cross section per target nucleus. In a mixture with mass fractions w_i,
  `1/lambda = sum_i w_i N_A sigma_i / A_i`, which is the same as crossing the components one after the other.
- Over layers of grammage x_k, `P = exp(-sum_k x_k / lambda_k)`; the flux above the material divides the counted
  flux by P. Only the material between the point where the flux is defined (top of instrument, or a layer) and the
  layers whose charge selects the species counts; state which.
- Which cross section: a selection that requires the same charge in every layer measures charge-changing survival;
  one that requires the same isotope measures inelastic survival. The cross section and the selection agree.
- Survival depends on energy through sigma(E): the correction is per bin, from cross sections at that energy.

## Feed-down

- A heavier nucleus that fragments above the selecting layers can be counted as a lighter species. To first order
  `N_feed = N_heavy (1 - P_heavy) f(heavy -> light)`, with N_heavy the number arriving above the material and f the
  fraction of its interactions that leave a fragment reconstructed as the light species. Second-step fragmentation
  and the survival of the fragment itself are neglected at this order; when they matter, use a species-migration
  response (`references/response-and-forward-folding.md`, "Species migration") instead of a subtraction.
- Feed-down is subtracted before the survival correction of the light species (a background in reco space). A
  fixed subtraction ignores that N_heavy is itself measured at the same time: the coupled treatment is in
  `<plugin root>/skills/hep-measurement/references/backgrounds.md` ("Coupled species").
- Fragmentation in the layers that measure the charge is tagged by comparing the charge measured before and after;
  only the untagged part is feed-down.

## Uncertainty

- The cross sections are the dominant input: vary them as model alternatives and with a scale nuisance s
  (sigma -> (1 + s) sigma). At s = 0, `dP/ds = P ln P`, and `dN_feed/ds = -N_heavy f P_heavy ln P_heavy` for the heavy
  species' scale. The same cross sections may also enter the interpretation (production in the interstellar
  medium); declare that correlation together with the correction (see the hep-theory reference).
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
