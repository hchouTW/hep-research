# Synthetic detector model (illustrative)

All parameters live in `benchmarks/path-b.json`; every value is invented.

- **Process and variable.** Events are e+e- -> mu+mu- at a fixed sqrt(s). The measured variable is cos theta, the angle between the incoming e- and the outgoing mu-, in the CM frame.
- **Generator.** cos theta is drawn from f(c) = 1 + a c^2 + b c on [-1, 1] by accept-reject. The total number of events is Poisson with mean L x sigma. The parameters a, b and sigma are synthetic inputs.
- **Efficiency.** Each event is kept with probability eps(c) = e0 - e1 c^4. This is a smooth loss toward the beam pipe, with acceptance and efficiency folded into one function.
- **Resolution.** The reconstructed cos theta is c + N(0, sigma_c). Reconstructed values outside [-1, 1] are lost (counted as underflow/overflow).
- **Fiducial measurement.** Truth is binned in cos theta with edges from the benchmark. The outermost truth bins (|cos theta| > 0.9) absorb migration and are not reported. The reported fiducial region is |cos theta| < 0.9.
- **Response.** `scripts/detector.py` computes R[k][j] = P(reco bin k and selected | truth bin j) by integrating the shape, the efficiency and the Gaussian smearing over each truth bin. Normalization is `includes_efficiency`: column sums equal the bin efficiency, minus losses outside the reco range.
- **Luminosity.** L carries an invented 2% fully correlated uncertainty.

Limitations (by construction): the response uses the generated shape within each bin, so model dependence is not studied; there is no background, no charge confusion, no radiative effects and no beam-energy spread.
