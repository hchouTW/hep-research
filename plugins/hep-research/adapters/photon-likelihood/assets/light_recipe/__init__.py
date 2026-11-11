"""reco.light.channel-likelihood/1, the T09 development binding (decisions.md, U12 A; t07-t09-task-sheets.md, T09): the
all-channel photon likelihood of the hep-detector reference photon-likelihood-reconstruction.md, on the analytic light model of
fixture t09-sphere/1 (t04-values-v4.md section 4.3). A development binding in Python, not a native backend: the native backend
is a recorded gap.

Stage 1 (D3 stage 1 brief): the readout (light-readout/1), the charge-only likelihood over every live channel with one
threshold model shared by the hit and no-hit terms, saturated channels censored, dead and disabled channels excluded, a fit from
one seed, and the product light-likelihood-product/1. The time term, multistart seeds and topology come in later stages; the
per-channel states and the threshold model are built so that the time term can use them (charge and time of one sensor will be
modelled jointly, never assumed independent: plan section 8.2).

Every result is labelled shared-model closure: the events and the fit share the light model, so it tests the code, not the model
(plan section 11.1).
"""

RECIPE = "reco.light.channel-likelihood/1"
LABEL = "shared-model closure"
LABEL_MEANING = ("the fixture's events and this fit share the stated analytic light model of t04-values-v4.md section 4.3: a "
                 "closure of the code, not a test of the model or of any instrument (plan section 11.1)")
LIKELIHOOD = "charge-only, all live channels (stage 1)"
PARAMETERS = ("x", "y", "z", "u1", "u2", "e_vis")
PARAMETER_UNITS = {"x": "m", "y": "m", "z": "m", "u1": "1 (tangent component at the fitted direction)",
                   "u2": "1 (tangent component at the fitted direction)", "e_vis": "1 (E_vis = N_exp / (1000 S), section 4.3)"}
