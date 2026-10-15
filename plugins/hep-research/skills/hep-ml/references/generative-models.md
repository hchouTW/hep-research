# Generative Model Reference (VAE, GAN, normalizing flows, flow matching, diffusion)

Training mechanics and failure modes of generative models. Detector fast simulation and its physics validation
(conditioning, constraints, metrics, statistical meaning of generated samples) start at
[fast-simulation-validation.md](fast-simulation-validation.md). No family is "the standard": choose by what the use
needs (exact density, sampling speed, fidelity in the tails) and compare on the physics metrics. Sources opened on
2026-10-14 unless marked.

## Variational autoencoder (VAE)

Loss = reconstruction term + KL divergence of the latent posterior to the prior. The reconstruction likelihood must
match the data: binary cross-entropy assumes values in [0, 1]; for continuous physics quantities use a Gaussian (MSE)
on standardized or log-transformed inputs, and treat the exact zeros of sparse calorimeter data explicitly. Sample
with the reparameterization `z = mu + eps * exp(0.5 * logvar)`, `eps ~ N(0, I)`, or
`torch.distributions.Normal(mu, std).rsample()`; `.sample()` has no gradient. Posterior collapse (the decoder ignores z; blurry averaged outputs; the KL term falls to 0) is the
characteristic failure: anneal the KL weight, use free bits, or weaken the decoder; log reconstruction and KL
separately.

## Generative adversarial network (GAN)

Alternate a discriminator step on real and detached generated samples with a generator step using the non-saturating
loss (generated samples labelled real); the minimax form has vanishing gradients early. Mode collapse (the same few
outputs for any noise) is the characteristic failure: fewer discriminator steps, one-sided label smoothing (0.9 for
real), a diversity term, or WGAN-GP or hinge losses. A discriminator loss near 0 with the generator loss climbing means
the discriminator has won: rebalance, do not train longer. Match the output range to the preprocessing (`tanh` with
data in [-1, 1]).

## Normalizing flows

A flow maps a simple base distribution through a chain of invertible transformations, so it can both sample and
evaluate the density of what it generates (Papamakarios et al., JMLR 22 (2021) 57, arXiv:1912.02762). Training
maximizes the exact log-likelihood of the data: stable, with a density usable for diagnostics (per-event likelihoods,
out-of-distribution scores) and for likelihood-based inference. Costs: invertibility constrains the architecture, and
autoregressive flows are fast in one direction and slow in the other (fast density, slow sampling or the reverse);
distillation into a fast-sampling flow is the usual fix in fast simulation (CaloFlow:
[fast-simulation-validation.md](fast-simulation-validation.md)). Physics inputs with hard edges (thresholds,
positivity, bounded fractions) need a transformation to an unbounded space (log or logit) before the flow, and its
Jacobian in the density.

## Flow matching

Flow matching trains a continuous normalizing flow by regressing its time-dependent vector field onto the vector
fields of fixed conditional probability paths between noise and data (Lipman et al., arXiv:2210.02747): a simulation-
free regression loss, like the diffusion objective, with sampling by integrating an ODE. Training is stable; sampling
needs many network evaluations (an ODE solver), and the step count trades fidelity for speed: report both. The
learned density is available by integrating the divergence along the path, at extra cost.

## Diffusion models

A denoiser is trained to predict the noise added at a randomly drawn time step t (with t embedded, for example
sinusoidally); training is a single stable MSE loss, sampling iterates the reverse process over many (or, with
distillation and modern samplers, fewer) sequential steps: budget sampling separately from training. The training
loss does not track sample quality: generate and inspect samples during training.

## Evaluation and common failures

Held-out likelihood is a weak signal for sample quality. Use physics metrics (feature distributions, FPD/KPD, a
classifier two-sample test with its power, downstream closure:
[fast-simulation-validation.md](fast-simulation-validation.md)); image metrics such as FID use features with no
physics meaning. Check diversity across seeds.

| Symptom | Model | Likely cause |
|---|---|---|
| blurry outputs insensitive to the latent code | VAE | posterior collapse |
| the same few outputs for any noise | GAN | mode collapse |
| discriminator loss to 0 early, generator stuck | GAN | discriminator too strong |
| loss fine, samples are noise | diffusion, flow matching | time embedding not reaching the network, or a noise schedule or path that differs between training and sampling |
| bad density at the edges of the support | flow | a bounded variable not transformed to an unbounded space |
