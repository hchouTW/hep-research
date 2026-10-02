# Geometric and Equivariant Learning Reference

Reasoning about symmetry in model design - sets, graphs, point clouds, and
group/rotation/Lorentz equivariance. This is symmetry *reasoning*, not an
architecture catalog; for choosing/sizing architectures generally see
[architecture-selection.md](architecture-selection.md), and for when to enforce a
constraint via architecture vs. objective vs. augmentation see
[scientific-machine-learning.md](scientific-machine-learning.md)'s constraint table,
which applies directly to symmetry constraints too.

## Symmetry reasoning

Require the symmetry assumption to be scientifically justified, not assumed from the
architecture literature. Work through:

1. What symmetry does the problem actually have? (Permutation of a set's elements,
   rotation of a point cloud, the Lorentz group for four-momenta, translation, etc.)
2. Is the desired input-output mapping **invariant** (output unchanged under the
   symmetry - e.g. classifying a jet regardless of detector orientation) or
   **equivariant** (output transforms the same way the input does - e.g. predicting a
   per-particle vector quantity)? Getting this wrong is a common design error: forcing
   invariance onto a task that needs equivariance discards information the output
   actually requires.
3. Is the symmetry **exact** (a genuine conservation law or geometric fact) or
   **approximate** (holds statistically, or only under idealized conditions the data
   does not fully satisfy)?
4. Should it be enforced **architecturally** (hard guarantee, e.g. a permutation-
   invariant aggregation), **encouraged through data augmentation** (soft, requires
   augmentation coverage to actually work), **encouraged through the objective** (soft,
   requires the loss weight to be justified), or **learned from data** (no guarantee,
   but no risk of over-constraining either)?
5. What information might be lost by enforcing it? An exactly-invariant architecture
   cannot recover a quantity that depends on the very variable it was made invariant
   to, even if that dependence turns out to matter.

## Permutation invariance and equivariance (sets, graphs, point clouds)

- **Sets** (unordered collections, e.g. particles in an event with no meaningful
  ordering) need permutation-invariant aggregation for invariant outputs (e.g. a
  symmetric pooling over per-element embeddings) or permutation-equivariant layers
  (message passing that updates each element using its neighbors, order-independent)
  for per-element outputs.
- **Graphs** add explicit relational structure (edges) to the set; message passing
  operates on that structure. The inductive bias only helps when the graph's edges
  encode a relation the task actually depends on - a graph built from an arbitrary or
  uninformative adjacency is not obviously better than a set representation, and that
  comparison is worth running.
- **Point clouds** are sets with geometric coordinates attached; whether rotation/
  translation equivariance should be enforced depends on question 1 above - a
  detector-frame-dependent quantity should *not* be made rotation-invariant.

## Domain-specific symmetries: Lorentz-aware modeling

For HEP and other relativistic settings, four-momenta transform under the Lorentz
group, not merely under 3D rotation - a model that enforces only spatial rotational
invariance/equivariance on relativistic kinematic inputs is enforcing the wrong group.
Lorentz-equivariant architectures exist specifically for this; whether to use one
follows the same reasoning as any other symmetry choice above, including question 5 -
Lorentz-invariant architectures cannot recover frame-dependent quantities, which is
sometimes exactly what is wanted (e.g. invariant mass) and sometimes not.

## Reviewing a proposed exact-symmetry architecture

When a new architecture proposes exact symmetry enforcement, ask:

- Is the symmetry actually exact for this data, or only approximately so?
- Should the output be invariant or equivariant, and does the architecture match that?
- Does enforcing it remove valid information the task needs?
- Does it improve results relative to an unconstrained baseline given the same budget
  - see [ablation-and-design-review.md](ablation-and-design-review.md)?

## Deliverables

- The symmetry identified, and whether the required mapping is invariant or
  equivariant.
- Whether the symmetry is treated as exact or approximate, and the justification.
- Where it is enforced (architecture, augmentation, objective, or left to the data),
  and why.
- What information, if any, is lost by the chosen enforcement.
- Comparison against an unconstrained baseline at matched budget.
