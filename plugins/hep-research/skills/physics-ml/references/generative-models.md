# Generative Model Reference (VAE / GAN / Diffusion)

Training loops, losses, and failure modes specific to generative models. Assumes
familiarity with [training-loop.md](training-loop.md); this file covers
what differs from a standard supervised loop.

## Variational autoencoder (VAE)

Loss is reconstruction error plus a KL-divergence term pulling the latent
distribution toward a standard normal prior:

```python
def vae_loss(recon_x, x, mu, logvar, kl_weight=1.0):
    recon_loss = nn.functional.binary_cross_entropy(recon_x, x, reduction="sum")
    kl = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return recon_loss + kl_weight * kl, recon_loss.detach(), kl.detach()
```

- **Reparameterization trick** is required for the latent sample to be
  differentiable: sample `eps ~ N(0, I)` and compute
  `z = mu + eps * torch.exp(0.5 * logvar)`, never `z = Normal(mu, std).sample()`
  directly (that path has no gradient).
- **Posterior collapse** (the decoder ignores `z` and the encoder outputs
  `mu≈0, logvar≈0` for everything) is the characteristic VAE failure: reconstructions
  look like a blurry "average" sample and are insensitive to `z`. Mitigations:
  KL annealing (start `kl_weight` near 0 and ramp up over training), free bits
  (only penalize KL above a small per-dimension threshold), or a lower-capacity
  decoder relative to the latent size.
- Track `recon_loss` and `kl` separately in logs, not just their sum - a collapsing
  KL term toward 0 while reconstruction stays flat is the collapse signature above.

## Generative adversarial network (GAN)

Two networks, alternating updates, each optimizing against the other:

```python
# Discriminator step: maximize log D(real) + log(1 - D(fake))
d_optimizer.zero_grad(set_to_none=True)
real_pred = discriminator(real_batch)
fake = generator(noise).detach()  # detach: don't backprop into G here
fake_pred = discriminator(fake)
d_loss = criterion(real_pred, torch.ones_like(real_pred)) + criterion(fake_pred, torch.zeros_like(fake_pred))
d_loss.backward()
d_optimizer.step()

# Generator step: maximize log D(fake) (the non-saturating loss, not the minimax one)
g_optimizer.zero_grad(set_to_none=True)
fake = generator(noise)
fake_pred = discriminator(fake)
g_loss = criterion(fake_pred, torch.ones_like(fake_pred))  # label flipped vs. D's target
g_loss.backward()
g_optimizer.step()
```

- Use the **non-saturating generator loss** (`criterion(fake_pred, ones)`, as above)
  rather than the literal minimax `-log(1 - D(fake))` - the latter has vanishing
  gradients early in training when the discriminator easily rejects the generator.
- `.detach()` the generator's output before the discriminator step so that step's
  backward pass doesn't touch the generator's parameters; the generator step then
  runs its own fresh forward pass through both networks.
- **Mode collapse** (generator produces a narrow variety of outputs regardless of
  input noise) is the characteristic GAN failure. Mitigations: reduce the
  discriminator's relative advantage (fewer D steps per G step, label smoothing on
  real labels only, e.g. `0.9` instead of `1.0`), add a diversity-encouraging term
  or minibatch discrimination, or switch to a more stable objective (WGAN-GP,
  hinge loss) if collapse persists.
- Watch both losses together, not either alone: a discriminator loss near 0 with
  generator loss climbing means D has "won" and G's gradients are near-useless -
  rebalance update frequency or learning rates rather than training longer.
- Normalize generator output range to match the data preprocessing (e.g. `tanh`
  output with data scaled to `[-1, 1]`, not `[0, 1]`) - a range mismatch is a common
  source of a generator that never improves past noisy static.

## Diffusion models (denoising objective)

Conceptual training loop for a DDPM-style denoiser (the standard modern approach
for image/audio generation as of this writing):

```python
def diffusion_training_step(model, x0, noise_scheduler, optimizer):
    batch_size = x0.size(0)
    t = torch.randint(0, noise_scheduler.num_timesteps, (batch_size,), device=x0.device)
    noise = torch.randn_like(x0)
    x_t = noise_scheduler.add_noise(x0, noise, t)  # forward process: x0 -> noisy x_t
    predicted_noise = model(x_t, t)
    loss = nn.functional.mse_loss(predicted_noise, noise)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()
    return loss.item()
```

- The network predicts the **noise** added at a randomly sampled timestep `t`, not
  the clean image directly - `t` must be passed into the model (typically via a
  sinusoidal timestep embedding, conceptually the same construction as the
  positional encoding in
  [transformer-architectures.md](transformer-architectures.md)).
- Training is comparatively stable (a single well-behaved MSE loss, no adversarial
  dynamics to balance) but **sampling is expensive**: generating one sample requires
  iterating the reverse process across many (or, with modern samplers, few but
  still sequential) timesteps - budget for this separately from training compute.
- Do not evaluate sample quality from training loss alone; MSE on noise prediction
  does not track perceptual sample quality well. Generate and inspect actual
  samples periodically during training.

## Evaluation

Held-out likelihood/loss is a necessary but weak signal for generative quality.
Prefer, in addition:

- **Visual/manual inspection** of generated samples at fixed intervals - cheap and
  catches mode collapse, artifacts, and degenerate outputs that a scalar metric
  can miss.
- **Distributional metrics** (e.g. FID for images) when comparing checkpoints or
  configurations quantitatively - these compare feature-space statistics of
  generated vs. real samples rather than per-sample fidelity.
- **Diversity checks**: generate many samples from different noise seeds/latents
  and confirm they differ meaningfully - a model that reproduces the same handful
  of outputs has collapsed even if individual samples look good.

## Common failure modes

| Symptom | Likely model | Likely cause |
|---|---|---|
| Blurry, "averaged" outputs insensitive to latent code | VAE | Posterior collapse - anneal or floor the KL term |
| Same few outputs regardless of input noise | GAN | Mode collapse - rebalance D/G updates, add diversity term |
| Discriminator loss → 0 quickly, generator stuck | GAN | D too strong too early - fewer D steps, label smoothing, lower D learning rate |
| Loss looks fine, samples are noise/garbage | Diffusion | Timestep embedding not actually reaching the model, or noise schedule mismatch between training and sampling code |
| Training loss fine, generation much worse than train-time reconstructions | VAE/Diffusion | Evaluating with teacher-forced/ground-truth-conditioned code path instead of the real generation path |
