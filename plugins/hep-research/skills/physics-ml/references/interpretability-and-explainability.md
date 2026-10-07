# Interpretability and Explainability Reference

Whether an explanation, attribution, or learned representation is actually evidence
for the claim being made about it. For calibration/uncertainty of the underlying
predictions see [uncertainty-and-calibration.md](uncertainty-and-calibration.md); for
proving a component causes a metric change (as opposed to a model's internal
reasoning) see [ablation-and-design-review.md](ablation-and-design-review.md).

## Interpretation discipline

**An explanation method produces another model-derived quantity; it is not
automatically evidence of the model's causal reasoning.** A saliency map, attention
weight, or attribution score is itself an output of a computation over the model - it
requires the same skepticism as any other model output, not less because it looks
like an explanation.

Explicitly guard against these unsupported transitions:

- `attention weight -> explanation` - attention shows where the model placed weight,
  not why, and multiple attention patterns can produce equivalent outputs.
- `feature attribution -> causal importance` - an attribution score is correlational
  with the model's output under the attribution method's own assumptions; it is not a
  causal claim about the underlying process without further evidence.
- `latent-space clustering -> learned physical mechanism` - a visually structured
  embedding is not sufficient evidence that the network discovered underlying
  structure; see the representation-learning section below.

When the interpretation is scientifically important, require before trusting it:

- **Perturbation checks** - does removing/changing the highlighted feature actually
  change the output, not just receive a high attribution score?
- **Randomization / sanity checks** - does the explanation change when model weights
  or labels are randomized? An explanation method that produces similar output for a
  randomly-initialized model is not explaining the trained model's behavior.
- **Stability checks** - does the explanation change meaningfully under small,
  semantically irrelevant input perturbations? An unstable explanation is a weak one.
- **Alternative explanation methods** - do different attribution approaches (gradient-
  based, perturbation-based, SHAP-like) agree? Disagreement is informative, not a bug
  to average away.
- **Domain-informed validation** - does the explanation correspond to a mechanism that
  can be checked against known domain structure (a known physical relationship, a
  controlled synthetic case with a known ground-truth answer)?

Do not build a catalog of explainability packages here - the discipline above applies
regardless of which library produced the attribution.

## Representation learning and embeddings

Embeddings, contrastive/self-supervised objectives, and metric learning produce
internal representations whose quality must be validated the same way an explanation
must be:

- **Collapse** - the representation-collapse failure mode described in
  [optimization-and-training-dynamics.md](optimization-and-training-dynamics.md) is
  common in contrastive/self-supervised training specifically: watch for embeddings
  that lose diversity (e.g. shrink toward a point, or toward a low-dimensional
  subspace) even while the training loss looks fine. Check embedding-space diversity
  directly (e.g. the effective rank or spread of a batch of embeddings), not only the
  loss curve.
- **Positive/negative sampling** choices determine what invariances the representation
  actually learns; an invariance not encoded by the sampling strategy will not
  reliably appear in the embedding, however plausible it sounds.
- **Embedding normalization** (e.g. L2-normalizing before a similarity computation)
  changes what the downstream distance metric measures - state whether embeddings are
  normalized before reporting a similarity or retrieval result.
- **Evaluation**: probing (train a small supervised model on frozen embeddings to test
  what they encode), retrieval evaluation (nearest-neighbor quality against a known
  relevance signal), and representation similarity (e.g. comparing two models'
  internal representations) are the standard tools - each answers a different
  question, and none of them alone establishes what the representation "means."

## Scientific interpretation of representations

Guard specifically against claims of the form *"the latent-space clustering proves
that the network learned the underlying physics."* A visually structured embedding is
not sufficient evidence on its own. Before making a claim like this, validate with:

- **Controlled probes** against known physical variables - does a simple probe
  recover a known quantity from the embedding significantly better than chance/a
  baseline?
- **Downstream tasks** - does the representation actually improve a task that depends
  on the claimed structure, not just look structured under a 2D projection (which can
  itself be misleading - a projection method can impose apparent structure that is not
  in the full-dimensional representation)?
- **Interventions** - does changing the claimed factor in a controlled way move the
  embedding in the expected direction?
- **Nuisance sensitivity** - is the embedding appropriately invariant to variables it
  should not depend on, and appropriately sensitive to the ones it should?
- **Ablations** on the training signal that would plausibly cause the claimed
  structure - see [ablation-and-design-review.md](ablation-and-design-review.md).
- **Independent representations** - does a differently-initialized or differently-
  trained model show the same structure? Structure that appears in only one run is
  weaker evidence than structure that reappears independently.

Calibrate the interpretation to the evidence actually gathered - "the embedding is
consistent with X" and "the network learned X" are different claims requiring
different amounts of support.

## Deliverables

- Which unsupported-transition risk applies (attention/attribution/clustering), and
  which of the validation checks above were actually run.
- For attributions: at least a perturbation or randomization/sanity check, not the
  attribution alone.
- For representations: the collapse check (embedding diversity), and if a scientific
  claim is being made about learned structure, which of the controlled-probe/
  downstream-task/intervention/nuisance-sensitivity checks support it.
- The claim's strength stated in proportion to the evidence gathered.
