# Citation and documentation checks (2026-10-03)

All lookups were read-only and made through the WebFetch tool, after the user approved them on 2026-10-03. `curl` to
these hosts is refused by the container proxy. INSPIRE search queries (`/api/literature?q=`) returned a fixed record,
so the path endpoints `/api/arxiv/<id>` and `/api/doi/<doi>` were used instead. WebFetch passes each page through a
summarizing model, so quoted snippets are near-verbatim.

| # | Source as cited in the plugin | Checked at | Result |
|---|---|---|---|
| 1 | T.-P. Li, Y.-Q. Ma, ApJ 272 (1983) 317, doi:10.1086/161295 | INSPIRE doi; ADS scan articles.adsabs.harvard.edu/pdf/1983ApJ...272..317L | matches. The significance formula is eq. 17; eq. 15 is -2 ln(lambda) ~ chi2(1) |
| 2 | R. Barlow, C. Beeston, Comput. Phys. Commun. 77 (1993) 219, doi:10.1016/0010-4655(93)90005-W | INSPIRE doi | matches |
| 3 | J. S. Conway, PHYSTAT 2011, CERN-2011-006, p. 115, doi:10.5170/CERN-2011-006.115, arXiv:1103.0354 | INSPIRE arxiv | **correction**: a proceedings paper, not a journal article |
| 4 | R. D. Cousins, V. L. Highland, NIM A 320 (1992) 331, doi:10.1016/0168-9002(92)90794-5 | INSPIRE doi | matches |
| 5 | M. Pivk, F. R. Le Diberder, NIM A 555 (2005) 356, arXiv:physics/0402083 | INSPIRE arxiv | matches |
| 6 | C. Langenbruch, EPJC 82 (2022) 393, arXiv:1911.01303 | INSPIRE arxiv | matches |
| 7 | H. Dembinski, M. Kenzie, C. Langenbruch, M. Schmelling, NIM A 1040 (2022) 167270, arXiv:2112.04574 | INSPIRE arxiv | matches |
| 8 | A. Vehtari et al., Bayesian Analysis 16 (2021), doi:10.1214/20-BA1221, arXiv:1903.08008 | Crossref; arXiv | matches except the start page 667, which no record gave: the page is not quoted |
| 9 | S. Talts et al., arXiv:1804.06788 | INSPIRE; arXiv | **correction**: preprint; no journal version recorded |
| 10 | K. Cranmer, J. Pavez, G. Louppe, arXiv:1506.02169 | INSPIRE | **correction**: preprint; no journal version recorded |
| 11 | ATLAS Collaboration, Rep. Prog. Phys. 88 (2025) 067801, arXiv:2412.01600 | INSPIRE | **addition**: now published |
| 12 | K. Cranmer et al., SciPost Phys. 12 (2022) 037, arXiv:2109.04981 | INSPIRE | matches |
| 13 | A. Buckley et al., JHEP 04 (2019) 064, arXiv:1809.05548 | INSPIRE | matches |
| 14 | E. Gross, O. Vitells, EPJC 70 (2010) 525, arXiv:1005.1891 | INSPIRE; arXiv PDF | matches. The upcrossing formula is eq. (3), written as an upper bound: P(q > c) <= P(chi2_s > c) + <N(c0)> (c/c0)^((s-1)/2) exp(-(c-c0)/2) |
| 15 | D. V. Lindley, Biometrika 44 (1957) 187, doi:10.1093/biomet/44.1-2.187 | Crossref | matches |
| 16 | G. Cowan, K. Cranmer, E. Gross, O. Vitells, EPJC 71 (2011) 1554, erratum EPJC 73 (2013) 2501, arXiv:1007.1727 | INSPIRE; arXiv PDF | matches; Z_A = sqrt(2((s+b) ln(1+s/b) - s)) is eq. (97) in the arXiv numbering; the erratum is now cited |
| 17 | G. Cowan, "Discovery sensitivity for a counting experiment with background uncertainty", note, 30 May 2012, www.pp.rhul.ac.uk/~cowan/stat/medsig/medsigNote.pdf | the note | formula is eq. (20); model eq. (12), n ~ Pois(s+b), m ~ Pois(tau b), tau = b/sigma_b^2 (eq. 19). Unpublished note |
| 18 | Feldman & Cousins PRD 57 (1998) 3873; Junk NIM A 434 (1999) 435; Read J. Phys. G 28 (2002) 2693 | INSPIRE | match |

## Combine documentation (recommended tag v11.1.0 per the landing page)

- `lnN`: <https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/part2/settinguptheanalysis/> — the
  symmetric form multiplies the yield by kappa^theta; the asymmetric form `kappa_down/kappa_up` gives the yield ratios
  at -1 and +1 sigma. Interpolation (<.../what_combine_does/model_and_likelihood/>, "Normalization Effects"):
  kappa^A = kappa_up for nu >= 0.5, 1/kappa_down for nu <= -0.5, and a smooth function of nu in between
  (I(nu) = 48 nu^5 - 40 nu^3 + 15 nu).
- `shape`: bin fractions interpolated vertically with a polynomial inside |nu| < 1 (the 3nu^5 - 10nu^3 + 15nu form)
  and linearly outside; `shapeN` interpolates the log fractions; the normalization effect of a shape nuisance is an
  asymmetric log-normal. The docs do not say how its kappa is computed, so the plugin does not state it.
- FitDiagnostics (<.../part3/nonstandard/>): `fit_b`, `fit_s`, `nuisances_prefit`; with `--plots`
  `covariance_fit_s`/`covariance_fit_b`; `--saveShapes` writes `shapes_prefit`, `shapes_fit_sb`, `shapes_fit_b`;
  pulls via `diffNuisances.py`.
- Impacts (same page, "Nuisance parameter impacts"): the shift of the POI when the NP is fixed at its **post-fit**
  +-1 sigma values with all other parameters profiled; `combineTool.py -M Impacts -d WS -m M --doInitialFit
  --robustFit 1`, then `--doFits`, then `-o impacts.json`, and `plotImpacts.py -i impacts.json -o impacts`; the plot
  shows (nu - nu0)/Delta nu, with nu0 the pre-fit value, and the post-fit/pre-fit uncertainty ratio.

None of these Combine statements was executed in this run (Combine is not installed here).
