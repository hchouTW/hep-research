# Geometric and Equivariant Learning Reference

Symmetry reasoning for model design (sets, graphs, point clouds, rotation and Lorentz equivariance); where to encode a
constraint: [scientific-machine-learning.md](scientific-machine-learning.md); architectures:
[particle-and-jet-architectures.md](particle-and-jet-architectures.md).

## Symmetry reasoning

1. Which symmetry does the problem have (permutation of set elements, rotation, translation, the Lorentz group for
   four-momenta)?
2. Is the required mapping **invariant** (a jet label regardless of orientation) or **equivariant** (a per-particle
   vector)? Forcing invariance on a task that needs equivariance discards what the output requires.
3. Is it **exact** (a conservation law, a geometric fact) or **approximate** (idealized conditions the data do not
   fully meet)?
4. Enforce it in the architecture (hard), through augmentation or the objective (soft, needing coverage or a justified
   weight), or leave it to the data?
5. What is lost: an exactly invariant model cannot recover a quantity that depends on the variable it is invariant to.

Sets need permutation-invariant pooling (invariant outputs) or permutation-equivariant message passing (per-element
outputs). Graphs help only when their edges encode a relation the task depends on; compare with a set model. Point
clouds are sets with coordinates: a detector-frame-dependent quantity must not be made rotation invariant.

## Lorentz symmetry

Four-momenta transform under the Lorentz group, not only 3-D rotations: a model enforcing spatial rotations on
relativistic kinematics enforces the wrong group. Lorentz-invariant models cannot recover frame-dependent quantities,
which is sometimes the point (invariant mass) and sometimes not. At detector level the beam axis, the acceptance and
the eta-phi segmentation break full Lorentz symmetry, so deployed Lorentz-equivariant taggers add beam "spurion" inputs
that reduce the symmetry to boosts along and rotations about the beam axis
([particle-and-jet-architectures.md](particle-and-jet-architectures.md)).

## Reviewing an exact-symmetry architecture

Is the symmetry exact for these data; invariant or equivariant output; what valid information does enforcement
remove; does it beat an unconstrained baseline at matched budget
([ablation-and-design-review.md](ablation-and-design-review.md))? Deliver the symmetry, exact or approximate with the
justification, where it is enforced and why, what is lost, and the baseline comparison.
