# Model: tree-level e+e- -> mu+mu- via one photon

**Process.** e-(p1) e+(p2) -> mu-(p3) mu+(p4) through a single s-channel virtual photon at lowest order, so the cross section is of order alpha^2.

**Assumptions** (also in `conventions.json`):
- Point-like spin-1/2 fermions with QED vertex -i e gamma^mu and alpha = e^2/(4 pi).
- Unpolarized beams. The spin-averaged squared amplitude averages over 4 initial spin states and sums over final spins. The PDG passage read does not state this explicitly, so it is `[Inferred]` to be the standard convention behind eq. 51.2.
- Electrons are massless. The muon mass is kept in the symbolic result and set to zero (beta -> 1) in the numerical prediction.
- No Z exchange, no gamma-Z interference, no radiative corrections, and no running of alpha.

**Validity domain.** sqrt(s) must be well above 2 m_mu, where the threshold factor beta(3 - beta^2)/2 departs from 1, and well below m_Z, where Z exchange grows. The benchmark point is sqrt(s) = 10 GeV `[Proposal]`. Quantitative estimates of the Z and radiative effects are **not** made here (listed under checks not run). The size of the mass correction is computed symbolically; its numerical value needs a muon mass, which this profile does not cite.

**Results** (derived in `scripts/derive.py`, matching PDG eqs. 51.2 and 51.3):
- d sigma / d Omega = (alpha^2 / 4s) beta [1 + cos^2 theta + (1 - beta^2) sin^2 theta]
- sigma = (4 pi alpha^2 / 3s) beta (3 - beta^2)/2, which tends to 4 pi alpha^2 / 3s = 86.8 nb / s[GeV^2] as beta -> 1
- d sigma / d cos theta (massless) = (3/8) sigma (1 + cos^2 theta). It is even in cos theta, so A_FB = 0 at this order.

**Inapplicable here:** detector, data, blinding, luminosity, experiment bindings, PDFs, factorization scale, parton shower.
