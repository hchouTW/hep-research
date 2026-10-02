# HEP 7: Feynman-style interaction

**Request:** "Draw e⁺e⁻ → μ⁺μ⁻ via a virtual photon."
**Type:** Feynman diagram (s-channel, tree-level QED). Process is fully specified by the user, so a formal diagram is appropriate. If the process had been vague ("some Higgs process"), ask for it (and the model) rather than invent vertices.

Vertex checks: γ*e⁺e⁻ and γ*μ⁺μ⁻ are QED vertices; charge conserved (0 → +1 − 1); fermion-flow continuous on each line.

```latex
% Requires \usepackage[compat=1.1.0]{tikz-feynman}. Manual placement: compiles and lays out correctly with pdfLaTeX, XeLaTeX, or LuaLaTeX.
\begin{tikzpicture}
  \begin{feynman}
    \vertex (a);
    \vertex [above left=of a]  (i1) {\(e^{-}\)};
    \vertex [below left=of a]  (i2) {\(e^{+}\)};
    \vertex [right=of a]       (b);
    \vertex [above right=of b] (f1) {\(\mu^{+}\)};
    \vertex [below right=of b] (f2) {\(\mu^{-}\)};
    \diagram* {
      (i1) -- [fermion] (a) -- [fermion] (i2),          % e+ in: arrow points away from the vertex
      (a)  -- [photon, edge label=\(\gamma^{*}\)] (b),
      (f1) -- [fermion] (b) -- [fermion] (f2),          % mu+ out: arrow points toward the vertex
    };
  \end{feynman}
\end{tikzpicture}
```
The manual version was compiled with Tectonic (XeTeX), LuaLaTeX, and pdfLaTeX and inspected (identical layout): incoming $e^-$ arrow toward the vertex, $e^+$ drawn with the arrow away from it, $\mu^+$ arrow toward the second vertex, $\mu^-$ away. The automatic-layout variant (`\feynmandiagram [horizontal=a to b] {...}`, in `../../references/tikz-patterns.md`) needs LuaLaTeX: under LuaLaTeX it was compiled and gives a clean diagram with correct arrows (with $e^+$ on top); under XeTeX and pdfLaTeX it "compiles" (exit 0) with a warning but ignores the layout keys and draws a garbled diagram, so a clean compile is not evidence of a correct figure.

Channel: s-channel (propagator carries $s=(p_{e^-}+p_{e^+})^2$). Adding Z exchange would require stating the electroweak assumption.
**Caption:** Leading-order Feynman diagram for $e^+e^-\to\mu^+\mu^-$ through s-channel virtual-photon exchange. Time runs left to right; arrows on fermion lines indicate fermion-number flow.
