# Model: LO parton-model F_2 and the O(alpha_s) longitudinal structure function

**Synthetic only.** No published F_L value was read for this profile. Every number it produces comes from invented
toy densities and invented alpha_s values, and the only numerical benchmark is an analytic closed form on those toys.

## What is computed

- F_2(x, Q^2) = x sum_q e_q^2 (q + qbar), photon exchange, naive quark-parton model [dispm:C01].
- F_L = F_2 - 2 x F_1 at its leading order, O(alpha_s^1). Moch, Vermaseren and Vogt write
  x^-1 F_L = C_L,ns (x) q_ns + <e^2> (C_L,q (x) q_s + C_L,g (x) g) [dispm:C03] with
  C_L,a = sum_n (alpha_s/(4 pi))^n c_L,a^(n) and c_L,ns^(1) = 4 C_F x, c_L,ps^(1) = 0, c_L,g^(1) = 8 n_f x (1 - x)
  [dispm:C04]. With the convolution C (x) f = int_x^1 dy/y C(y) f(x/y) [dispm:C02] this becomes the
  Altarelli-Martinelli form

  F_L(x, Q^2) = (alpha_s/(4 pi)) x^2 int_x^1 dz/z^3 [ (16/3) F_2(z) + 8 sum_q e_q^2 (1 - x/z) z g(z) ]

  (`derivations/derivation-record.md`).

## Assumptions

- Photon exchange only; n_f effectively massless flavours (zero-mass scheme); the toy uses n_f = 4.
- Leading twist: power corrections and target-mass terms O(M^2/Q^2) are dropped.
- mu_R = mu_F = Q. At O(alpha_s) the F_L coefficient functions are scheme independent.
- q_ns = sum (e_i^2 - <e^2>)(q_i + qbar_i). The paper calls this "the corresponding non-singlet combination" and
  does not write it out; this choice reproduces LO F_2, and its flavour trace vanishes (checked in SymPy).
- Parton densities are number densities, and they and alpha_s are inputs. In this profile they are SYNTHETIC
  Beta-form toys (`benchmarks/toy-closed-form.json`) and are not evolved in Q^2, so Q^2 enters only through the toy
  alpha_s value attached to it.

## Validity domain

Q^2 well above the nucleon mass squared and W^2 above the resonance region, where leading-twist factorization
applies. The profile derives no numerical bounds. At very small x, higher orders and resummation matter; at large x,
target-mass and higher-twist terms do. Neither is estimated here.

## What the outputs can and cannot claim

| Output | Can claim | Cannot claim |
|---|---|---|
| Altarelli-Martinelli form | an exact rewriting of the cited O(alpha_s) coefficient functions | anything beyond O(alpha_s) |
| Toy F_L, F_2 grid | that the quadrature matches the closed form to 1e-10 and converges | any physical F_L; agreement with data |
| Positivity, F_L <= F_2 | F_L >= 0 for non-negative densities (analytic); F_L <= F_2 on the toy points | F_L <= F_2 in general (not proven here) |

## Excluded

NLO and NNLO coefficient functions, DGLAP evolution, PDF sets, heavy-quark mass effects, Z and W exchange, polarized
structure functions, and any comparison with measured structure functions.
