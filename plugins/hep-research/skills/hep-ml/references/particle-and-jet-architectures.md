# Architectures for Particles, Jets and Hits

Variable-length, unordered inputs: jet constituents, reconstructed objects in an event, detector hits, tracks. The
symmetry reasoning is in [geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md); analysis use
(weights, metrics, decorrelation) is in [ml-analysis.md](ml-analysis.md). Citations were looked up on INSPIRE-HEP or
arXiv on 2026-10-13.

## Choose the representation first

| Input | Natural structure | Default family |
|---|---|---|
| Tens of engineered event or jet variables | Table | BDT or MLP ([multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md)) |
| Jet constituents, event objects | Set (permutation invariant) | Deep Sets/PFN, then ParticleNet or ParT |
| Constituents where Lorentz symmetry should be exact | Set with Lorentz structure | LorentzNet, PELICAN |
| Hits or cells with neighbor relations (tracker, calorimeter) | Graph or point cloud | GNN (EdgeConv-type, message passing) |
| Fixed calorimeter or detector grid | Image | CNN (but check sparsity: most cells are empty) |
| Time-ordered readout (waveforms) | Sequence | 1D CNN or small transformer |

Images of jets throw away the per-particle information and depend on pixelization and preprocessing (centering,
rotation, flipping). Prefer a set representation unless the detector itself is a grid.

## Per-particle features

The usual set, relative to the jet axis or event frame:

- **Position:** Δη, Δφ (wrapped into (−π, π]), ΔR.
- **Momentum:** log pT, log E, log(pT/pT,jet), log(E/E_jet).
- **Identity:** charge, particle-ID flags (from the reconstruction).
- **Tracks (for flavor tagging):** impact parameters and their significances, secondary-vertex association.

Logs tame the steep spectra. Standardize with statistics from the training partition only, and store them with the
model.

Wrap φ differences. A raw φ difference across the ±π boundary is a classic silent bug: it turns a narrow jet into a
wide one.

## Families

- **Deep Sets / Energy and Particle Flow Networks.** f({p_i}) = F(Σ_i Φ(p_i)): permutation invariant by
  construction, fast, a strong baseline (Zaheer et al., arXiv:1703.06114; Komiske, Metodiev, Thaler, JHEP 01 (2019)
  121, arXiv:1810.05165). EFNs weight the sum by the energy fraction z_i and use only angles inside Φ, which makes
  them infrared and collinear (IRC) safe. That matters when the score is compared to a fixed-order calculation or
  must be robust to soft radiation. PFNs drop that restriction and gain performance.
- **ParticleNet (dynamic graph CNN).** EdgeConv blocks on k-nearest-neighbor graphs, first in (η, φ), then in the
  learned feature space (Qu & Gouskos, PRD 101 (2020) 056019, arXiv:1902.08570). Cost grows with k·N.
- **Particle Transformer (ParT).** Self-attention over particles. Pairwise interaction features are added as an
  attention bias: ln Δ, ln k_T, ln z and ln m² of each pair (Qu, Li, Qian, ICML 2022, arXiv:2202.03772). The same
  paper introduced the JetClass dataset (100 M jets per its abstract, read 2026-10-14; how they divide into training,
  validation and test sets is `unverified` here), used for pre-training and benchmarks. Without
  positional encoding, attention is permutation equivariant; pool with a class token or masked mean for invariance.
- **Lorentz-equivariant networks.** LorentzNet (Gong et al., JHEP 07 (2022) 030, arXiv:2201.08187) and PELICAN
  (Bogatskiy et al., arXiv:2211.00454) build on Minkowski inner products p_i·p_j, so the output is exactly Lorentz
  invariant (or covariant). They are very data efficient and small. Check that the detector-level inputs actually
  carry the symmetry: acceptance, η–φ segmentation and the beam axis break full Lorentz invariance. Detector-level
  applications add beam "spurion" inputs that reduce the symmetry to boosts along and rotations about the beam axis,
  so exact Lorentz invariance is not what is deployed (`unverified`: which of the two cited networks uses which
  spurion inputs was not checked in an opened source; read each paper before attributing).
- **Graph networks for hits and tracking.** Message passing on hit graphs (edge classification for track building,
  node regression for energy). The Exa.TrkX pipeline uses metric learning and graph networks to group hits into track
  candidates and filter them (Ju et al., EPJC, doi:10.1140/epjc/s10052-021-09675-8, arXiv:2103.06995, abstract read
  2026-10-14). Graph construction (which edges exist) dominates both cost and efficiency; validate it as part of the
  model, report tracking efficiency and fake rate per pT, eta and pileup like any tracking algorithm, and hand the
  physics-performance statement to hep-detector.

Benchmarks: top tagging (Kasieczka et al., SciPost Phys. 7 (2019) 014, arXiv:1902.09914) and JetClass. A
benchmark gain does not transfer automatically to a different detector, pileup or jet definition; re-establish the
baseline (a PFN or a BDT on substructure variables) on your own samples.

## Foundation models

Pre-training on large simulated jet samples, then fine-tuning, is an emerging option. Examples are OmniJet-α (Birk,
Hallin, Kasieczka, Mach. Learn. Sci. Tech. 5 (2024) 035031, arXiv:2403.05618) and masked particle modeling (Golling
et al., Mach. Learn. Sci. Tech. 5 (2024) 035074, arXiv:2401.13537), and a foundation model for hadronic jets used
for reconstruction development, uncertainty quantification and model-agnostic searches (Mikuni & Nachman, PRD 111
(2025) L051504, arXiv:2404.16091, abstract read 2026-10-14; its name OmniLearn is `unverified` here).

- **When it helps:** with a small labeled sample.
- **What it inherits:** the pre-training simulation (generator, detector model, jet definition). Treat that as part
  of the training domain.
- **Default:** a model trained from scratch on your own samples, with the pre-trained one as an ablation.

Generic ImageNet or language pre-training does not apply to particle data.

## Engineering for variable multiplicity

- **Padding plus mask.** Pad to the maximum (or a per-batch maximum) and carry a boolean mask. Every reduction must
  respect it:
  - masked mean with the count clamped to ≥ 1;
  - masked max with padded entries set to −inf;
  - attention keys masked.
- **Empty sets give NaN.** A jet or event with zero constituents after cuts has an attention row that is fully
  masked, and `softmax` over all −inf returns NaN. Guard against it:
  - drop empty sets with a recorded count, or
  - add a learned "empty" token, or
  - replace a fully masked row's scores by zeros before the softmax and zero its output.

  `assets/hep_losses.py` has a NaN-safe `masked_softmax` and `masked_mean`.
- **Cap the multiplicity.** Truncate by pT ordering at a cap (for example 100–150 constituents) and record the
  truncation rate. A cap that cuts signal-like high-multiplicity jets biases the tagger.
- **Bucket batches by multiplicity.** Sorting into similar-length buckets reduces padding waste. With
  `torch.compile`, mark the set dimension dynamic (`torch._dynamo.mark_dynamic` or `dynamic=True`); otherwise every
  new length recompiles.
- **Ragged alternatives.** PyTorch Geometric-style concatenation with a batch index avoids padding for GNNs. awkward
  arrays from uproot need an explicit conversion step; keep it in the dataset, not in the training loop.

## Minimal masked Deep Sets

Verified with torch 2.14.1 on CPU, together with an empty-set check (all-masked row gives a finite score).

```python
import torch
from torch import nn

class DeepSets(nn.Module):
    def __init__(self, n_feat, hidden=128, n_out=1):
        super().__init__()
        self.phi = nn.Sequential(nn.Linear(n_feat, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.rho = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, n_out))

    def forward(self, x, mask):           # x: [B, N, F], mask: [B, N] True = real particle
        h = self.phi(x) * mask.unsqueeze(-1)
        pooled = h.sum(1) / mask.sum(1, keepdim=True).clamp(min=1)   # empty set -> zeros, not NaN
        return self.rho(pooled)

# permutation test: same score for a shuffled input
x, m = torch.randn(4, 30, 7), torch.rand(4, 30) > 0.3
perm = torch.randperm(30)
model = DeepSets(7).eval()
assert torch.allclose(model(x, m), model(x[:, perm], m[:, perm]), atol=1e-5)
```

Every set model should have this permutation test, plus an empty-set test, in its test suite.
