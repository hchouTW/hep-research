# Interpretability and Explainability Reference

Whether an explanation, attribution or learned representation is evidence for the claim made about it. Calibration of
predictions: [uncertainty-and-calibration.md](uncertainty-and-calibration.md); whether a component causes a metric
change: [ablation-and-design-review.md](ablation-and-design-review.md).

## Interpretation discipline

An explanation is another model-derived quantity, not evidence of the model's causal reasoning. Guard against three
unsupported steps: attention weight -> explanation (attention shows where weight was placed, not why, and different
patterns can give equivalent outputs); feature attribution -> causal importance (an attribution is correlational under
its method's assumptions); latent-space clustering -> learned physical mechanism.

When the interpretation matters scientifically, require: a **perturbation** check (changing the highlighted feature
changes the output); a **randomization** check (the explanation changes when weights or labels are randomized); a
**stability** check under small irrelevant input changes; **agreement between methods** (gradient-based,
perturbation-based, Shapley-like; disagreement is information, not noise to average); and **domain validation** against
a known physical relation or a synthetic case with a known answer. The discipline applies whatever library produced
the attribution.

## Representations and embeddings

Check embedding diversity directly (effective rank, spread), not only the loss: contrastive and self-supervised
training can collapse while the loss looks fine. The positive and negative sampling decides which invariances are
learned; state whether embeddings are normalized before a similarity is reported. Probing, retrieval and
representation-similarity evaluations each answer a different question.

"The latent-space clustering proves that the network learned the physics" needs, before it is claimed: a probe that
recovers a known physical variable better than a baseline; a downstream task that depends on the claimed structure (a
2-D projection can impose structure that the full representation lacks); interventions that move the embedding as
expected; invariance to nuisance variables; ablations of the training signal; and the same structure in an
independently trained model. "Consistent with X" and "learned X" are different claims. Deliver which risk applies,
which checks ran, and a claim no stronger than they support.
