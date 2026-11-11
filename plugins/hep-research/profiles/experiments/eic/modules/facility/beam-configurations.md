# EIC beam configurations

> Scope: EIC facility (the collider) design targets and requirements, not any one experiment and not achieved values.
> Method owner: [hep-measurement](../../../../../skills/hep-measurement/SKILL.md) for how a configuration enters a measurement design; hep-theory owns the kinematics computed from it.

Every number below is a design target of the 2021 Conceptual Design Report (CDR) or the Yellow Report, quoted from the claim cited on the same line. A study names the configuration it uses and labels these numbers design targets. Proposed early-running plans of ePIC are not facility values and are not listed here.

## Ranges

- The CDR design covers electron-proton center-of-mass energies E_CM from 20 to 140 GeV (eic:C38).
- The Yellow Report states the machine requirements as a luminosity of 10^33 to 10^34 cm^-2 s^-1 over center-of-mass energies between 20 and 140 GeV, with electron and light-ion polarizations above 70% and ion beams from deuterium to the heaviest nuclei (eic:C53).
- The electron storage ring has beam energies up to 18 GeV; the hadron storage ring runs protons between 41 and 275 GeV and ions from 41 to 110 GeV per nucleon (eic:C40).
- The highest design luminosity, 10^34 cm^-2 s^-1, is reached with 10 GeV electrons on 275 GeV protons, E_CM 105 GeV (eic:C39).
- Polarization: electron, proton and light-ion beams (deuteron and ³He) are planned highly polarized, about 70%; heavy ion beams will be unpolarized (eic:C43).
- The Yellow Report expects 70% polarization for the electron and proton beams and the same level for ³He; electron polarization is longitudinal, while protons and light ions are required in both longitudinal and transverse polarization (eic:C55).

The CDR tables read here list no light-ion configuration.

## Named configurations

Electron-proton rows quote CDR Table 3.3 and Table 3.4 (energies and E_CM) and the Table 3.3 setting for the luminosity; electron-gold rows quote CDR Table 3.5. Ion energies are per nucleon. A and Z are given only where a cited claim states them.

| Configuration (E_e x E_h) | Species | A, Z | E_e (GeV) | E_h per nucleon (GeV) | E_CM as listed (GeV) | Luminosity in 10^33 cm^-2 s^-1 (eic:C45) | Polarization (facility-wide design level, not per configuration) | Claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 18x275 | e + p | — | 18 | 275 | 140.7 | 1.54 | electron and proton about 70% | eic:C44, eic:C45, eic:C43 |
| 10x275 | e + p | — | 10 | 275 | 104.9 | 10.00 | electron and proton about 70% | eic:C44, eic:C45, eic:C43 |
| 10x100 | e + p | — | 10 | 100 | 63.2 | 4.48 | electron and proton about 70% | eic:C44, eic:C45, eic:C43 |
| 5x100 | e + p | — | 5 | 100 | 44.7 | 3.68 | electron and proton about 70% | eic:C44, eic:C45, eic:C43 |
| 5x41 | e + p | — | 5 | 41 | 28.6 | 0.44 | electron and proton about 70% | eic:C44, eic:C45, eic:C43 |
| 18x110 | e + ¹⁹⁷Au | A = 197, Z = 79 | 18 | 110 | 89.0 | — | electron about 70%; gold unpolarized | eic:C46, eic:C43 |
| 10x110 | e + ¹⁹⁷Au | A = 197, Z = 79 | 10 | 110 | 66.3 | — | electron about 70%; gold unpolarized | eic:C46, eic:C43 |
| 5x110 | e + ¹⁹⁷Au | A = 197, Z = 79 | 5 | 110 | 46.9 | — | electron about 70%; gold unpolarized | eic:C46, eic:C43 |
| 5x41 | e + ¹⁹⁷Au | A = 197, Z = 79 | 5 | 41 | 28.6 | — | electron about 70%; gold unpolarized | eic:C46, eic:C43 |

The electron-gold luminosities of Table 3.5 are not quoted: the profile has not established whether they are per nucleon or per nucleus. The luminosities of the other interaction-region setting (Table 3.4) are lower at the higher energies and are not listed.

## Center-of-mass energies, derived

Each value is recomputed from the cited beam energies and the crossing angle of eic:C41 with the plugin script; it agrees with the E_CM the CDR lists. For gold, the value is per nucleon pair, with M the proton mass.

- derived: 140.7 GeV from eic:C44, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 18 --E-hadron 275 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5
- derived: 104.9 GeV from eic:C44, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 10 --E-hadron 275 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5
- derived: 63.2 GeV from eic:C44, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 10 --E-hadron 100 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5
- derived: 44.7 GeV from eic:C44, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 5 --E-hadron 100 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5
- derived: 28.6 GeV from eic:C44, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 5 --E-hadron 41 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5
- derived: 89.0 GeV from eic:C46, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 18 --E-hadron 110 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5 (per nucleon pair, M = proton mass)
- derived: 66.3 GeV from eic:C46, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 10 --E-hadron 110 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5 (per nucleon pair, M = proton mass)
- derived: 46.9 GeV from eic:C46, eic:C41 via skills/hep-theory/scripts/dis_kinematics.py --E-lepton 5 --E-hadron 110 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5 (per nucleon pair, M = proton mass)

The x and y arguments only satisfy the script's interface; the center-of-mass energy does not depend on them.

## Using a configuration in a spec

A measurement-spec or theory-spec that uses an EIC configuration names it in its conventions block under the key `eic:beam_energy_configuration`, as the electron and hadron energies joined by an x and followed by the species, for example the label shown in the first code block. It records the beam values under `eic:beams`, in `extension.parameters` of a theory-spec or `extension.experiment_fields` of a measurement-spec, with the structure of the second code block. Every value is an object with a `value` and a `source`; the source is either a numeric claim of this profile that carries a `scope.number_kind` and states that value, or the string `user-supplied`. Polarization values are fractions between zero and one; a claim that quotes a percentage supports the fraction whose hundredfold equals that percentage. A hadron other than the proton states A, Z and the energy per nucleon. A spec whose status contains `projection` also records `eic:geometry_release` next to `eic:beams`. The conventions block also states `rapidity_frame`, `polarization_convention` when a beam is polarized, `azimuth_convention` when the observable uses azimuthal angles, and `eic:crossing_angle_treatment` (see `conventions.json`).

```text
"eic:beam_energy_configuration": "18x275 e+p"
```

```json
{"eic:beams": {
  "electron": {"energy_GeV": {"value": 18, "source": "eic:C44"}, "polarization": {"value": 0.7, "source": "eic:C43"}},
  "hadron": {"species": "p", "A": 1, "Z": 1, "energy_per_nucleon_GeV": {"value": 275, "source": "eic:C44"},
             "polarization": {"value": 0.7, "source": "eic:C43"}},
  "crossing_angle_mrad": {"value": 25, "source": "eic:C41"}}}
```

## General method

DIS kinematics built on these beam settings belong to hep-theory (`<plugin root>/skills/hep-theory/references/dis-kinematics.md`, `<plugin root>/skills/hep-theory/references/hadron-structure-essentials.md`); this module supplies only the facility values.
