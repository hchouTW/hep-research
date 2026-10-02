# HEP 4: Likelihood-analysis architecture

**Request:** "Draw the statistical analysis: signal, background, systematics to a limit."
**Type:** dependency graph (Graphviz). Frequentist profile-likelihood setting assumed (state it).

```dot
digraph stat {
    rankdir=LR; node [shape=box, style=rounded, fontname="Helvetica"];
    data [label="Observed data", style="rounded,filled", fillcolor="#dddddd"];
    sig  [label="Signal model\nμ · s(θ)"];
    bkg  [label="Background model\nb(θ)"];
    sys  [label="Systematic uncertainties", shape=note];
    nuis [label="Nuisance parameters θ\n+ constraint terms"];
    L    [label="Likelihood L(μ, θ)"];
    PL   [label="Profile-likelihood ratio\ntest statistic"];
    res  [label="Limit (CLs) /\nsignificance / interval", shape=box, style="rounded,bold"];
    sys -> nuis [style=dashed, label="parametrized as"];
    nuis -> sig; nuis -> bkg;
    sig -> L; bkg -> L; data -> L;
    L -> PL -> res;
}
```
**Checks:** μ (parameter of interest) vs θ (nuisance); constraint terms attach to nuisances; correlations = shared θ, no arrows between systematics; Asimov/expected vs observed are separate branches (not drawn here); no Bayesian priors implied.
**Caption:** Structure of the likelihood analysis. The signal and background models depend on the signal strength μ and nuisance parameters θ that encode systematic uncertainties, and are confronted with the observed data in the likelihood. The profile-likelihood-ratio test statistic yields limits, significances, or confidence intervals on μ.
