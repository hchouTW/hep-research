// simreco/Fit.hh: the track fit of simreco (Geant4 program B2.1). C++17 standard library only.
//
// Bending plane x-y, field along z, the track moving along +x. The trajectory model is a chain of circular arcs, one
// per segment between consecutive measuring planes, each with the curvature of the reconstruction field in that
// segment: with s = sin(phi) of the direction in x-y, ds/dx = kappa and y(x2) - y(x1) = (x2 - x1)(s1 + s2)/(c1 + c2)
// (c = cos(phi); exact for a circle and free of 1/kappa). kappa (1/mm, counter-clockwise positive) =
// -rho C B_z 1e-3 / cos(lambda), with rho = q/R the signed inverse rigidity (1/GV) the fit parameter, C =
// 0.299792458 GV/(T m) and lambda the dip angle from the non-bending fit (a positive charge in +z bends toward -y).
// Parameters (y0, s0, rho) at the first plane; Gauss-Newton on chi2 = r^T V^-1 r with V = diag(sigma_y^2) + the
// multiple-scattering covariance Cov(y_i, y_j) = sum_{k < min(i, j)} theta_k^2 (x_i - x_k)(x_j - x_k), theta_k from
// the Highland formula at plane k (x/X0 of the plane over the cosine of the track's angle to its normal, momentum and
// beta from the current rho and the particle's mass). Non-bending: z = z0 + t s_perp by generalized least squares in
// the transverse arc length with the same multiple-scattering structure, tan(lambda) = t.
#ifndef SIMRECO_FIT_HH
#define SIMRECO_FIT_HH

#include <array>
#include <cmath>
#include <vector>

namespace simreco {

constexpr double kC = 0.299792458;  // GV per (T m) for unit charge

struct Hit {
  double x = 0, y = 0, z = 0, sigma_y = 0, sigma_z = 0, x_over_x0 = 0;
};

struct FitResult {
  bool ok = false;
  double rho = 0, y0 = 0, s0 = 0, tan_lambda = 0, z0 = 0, chi2 = 0;
  double sigma_rho = 0;  // from the inverse normal matrix of the last iteration
  int ndof = 0, iterations = 0;
};

// The field the reconstruction assumes on each segment [x_k, x_k+1] (tesla, z component).
using SegmentField = std::vector<double>;

inline void Propagate(const std::vector<Hit>& h, const SegmentField& bz, double y0, double s0, double rho,
                      double cos_lambda, std::vector<double>& y, std::vector<double>& s, std::vector<double>& sperp) {
  std::size_t n = h.size();
  y.assign(n, 0.);
  s.assign(n, 0.);
  sperp.assign(n, 0.);
  y[0] = y0;
  s[0] = s0;
  for (std::size_t k = 0; k + 1 < n; ++k) {
    double dx = h[k + 1].x - h[k].x;
    double kappa = -rho * kC * bz[k] * 1e-3 / cos_lambda;
    double s1 = s[k] + kappa * dx;
    if (s1 > 0.999999) s1 = 0.999999;  // a track turning back is outside the model; clamp, the fit then fails chi2
    if (s1 < -0.999999) s1 = -0.999999;
    double c0 = std::sqrt(1 - s[k] * s[k]), c1 = std::sqrt(1 - s1 * s1);
    y[k + 1] = y[k] + dx * (s[k] + s1) / (c0 + c1);
    double dphi = std::asin(s1) - std::asin(s[k]);
    sperp[k + 1] = sperp[k] + (std::fabs(kappa) > 1e-15 ? dphi / kappa : dx / c0);
    s[k + 1] = s1;
  }
}

// Symmetric positive-definite solve by Cholesky (n small). Returns false when not positive definite.
inline bool Cholesky(std::vector<double>& a, int n) {
  for (int j = 0; j < n; ++j) {
    double d = a[j * n + j];
    for (int k = 0; k < j; ++k) d -= a[j * n + k] * a[j * n + k];
    if (!(d > 0)) return false;
    d = std::sqrt(d);
    a[j * n + j] = d;
    for (int i = j + 1; i < n; ++i) {
      double v = a[i * n + j];
      for (int k = 0; k < j; ++k) v -= a[i * n + k] * a[j * n + k];
      a[i * n + j] = v / d;
    }
    for (int i = 0; i < j; ++i) a[i * n + j] = 0.;
  }
  return true;
}

// x = A^-1 b with A given by its Cholesky factor L (lower).
inline std::vector<double> CholSolve(const std::vector<double>& L, int n, std::vector<double> b) {
  for (int i = 0; i < n; ++i) {
    for (int k = 0; k < i; ++k) b[i] -= L[i * n + k] * b[k];
    b[i] /= L[i * n + i];
  }
  for (int i = n - 1; i >= 0; --i) {
    for (int k = i + 1; k < n; ++k) b[i] -= L[k * n + i] * b[k];
    b[i] /= L[i * n + i];
  }
  return b;
}

inline bool Solve3(double m[3][3], double v[3], double out[3]) {
  double det = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
               m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  if (std::fabs(det) < 1e-300) return false;
  for (int i = 0; i < 3; ++i) {
    double c[3][3];
    for (int r = 0; r < 3; ++r)
      for (int q = 0; q < 3; ++q) c[r][q] = q == i ? v[r] : m[r][q];
    out[i] = (c[0][0] * (c[1][1] * c[2][2] - c[1][2] * c[2][1]) - c[0][1] * (c[1][0] * c[2][2] - c[1][2] * c[2][0]) +
              c[0][2] * (c[1][0] * c[2][1] - c[1][1] * c[2][0])) /
             det;
  }
  return true;
}

// Highland width (rad) of the projected angle after a slab of x/X0 for unit charge, momentum p (GeV/c) and beta.
inline double Highland(double xx0, double p, double beta, double z = 1.) {
  if (xx0 <= 0 || p <= 0) return 0.;
  return 0.0136 * z / (beta * p) * std::sqrt(xx0) * (1 + 0.038 * std::log(xx0 * z * z / (beta * beta)));
}

struct FitOptions {
  bool multiple_scattering = true;
  double mass_GeV = 0.;  // the particle's mass, from the particle table
  double charge = 1.;    // the particle's charge number: p = |q| / |rho|, Highland's z
  int max_iterations = 20;
};

// The covariance of the measured coordinates in one projection: diag(sigma^2) plus the multiple scattering at each
// plane, theta_k^2 (d_i - d_k)(d_j - d_k) with d the distance along the projection's lever (x in the bending plane,
// s_perp in the non-bending one), theta_k the projected Highland width.
inline std::vector<double> Covariance(const std::vector<Hit>& h, const std::vector<double>& d,
                                      const std::vector<double>& s, double cos_lambda, double rho,
                                      const FitOptions& opt, bool bending) {
  int n = static_cast<int>(h.size());
  std::vector<double> V(static_cast<std::size_t>(n * n), 0.);
  for (int i = 0; i < n; ++i) V[i * n + i] = bending ? h[i].sigma_y * h[i].sigma_y : h[i].sigma_z * h[i].sigma_z;
  if (!opt.multiple_scattering || rho == 0) return V;
  double z = opt.charge != 0 ? std::fabs(opt.charge) : 1.;
  double p = z / std::fabs(rho);  // GeV/c: rho = q / R and R = p / |q|
  double beta = p / std::hypot(p, opt.mass_GeV);
  for (int k = 0; k < n; ++k) {
    double cosang = std::sqrt(1 - s[k] * s[k]) * cos_lambda;  // the track's angle to the plane normal (x)
    double th = Highland(h[k].x_over_x0 / cosang, p, beta, z);
    double th2 = bending ? th * th / (cos_lambda * cos_lambda) : th * th;
    for (int i = k + 1; i < n; ++i)
      for (int j = k + 1; j < n; ++j) V[i * n + j] += th2 * (d[i] - d[k]) * (d[j] - d[k]);
  }
  return V;
}

// z = z0 + t s_perp by generalized least squares; false when the covariance is not positive definite.
inline bool FitLine(const std::vector<Hit>& h, const std::vector<double>& sp, const std::vector<double>& s,
                    double cos_lambda, double rho, const FitOptions& opt, double& z0, double& t) {
  int n = static_cast<int>(h.size());
  std::vector<double> L = Covariance(h, sp, s, cos_lambda, rho, opt, false);
  if (!Cholesky(L, n)) return false;
  std::vector<double> one(static_cast<std::size_t>(n), 1.), z(static_cast<std::size_t>(n));
  for (int i = 0; i < n; ++i) z[i] = h[i].z;
  std::vector<double> a = CholSolve(L, n, one), b = CholSolve(L, n, sp);
  double s11 = 0, s12 = 0, s22 = 0, r1 = 0, r2 = 0;
  for (int i = 0; i < n; ++i) {
    s11 += a[i];
    s12 += b[i];
    s22 += b[i] * sp[i];
    r1 += a[i] * z[i];
    r2 += b[i] * z[i];
  }
  double det = s11 * s22 - s12 * s12;
  if (!(det > 0)) return false;
  z0 = (s22 * r1 - s12 * r2) / det;
  t = (s11 * r2 - s12 * r1) / det;
  return true;
}

inline double LineChi2(const std::vector<Hit>& h, const std::vector<double>& sp, const std::vector<double>& s,
                       double cos_lambda, double rho, const FitOptions& opt, double z0, double t) {
  int n = static_cast<int>(h.size());
  std::vector<double> L = Covariance(h, sp, s, cos_lambda, rho, opt, false);
  if (!Cholesky(L, n)) return INFINITY;
  std::vector<double> r(static_cast<std::size_t>(n));
  for (int i = 0; i < n; ++i) r[i] = h[i].z - (z0 + t * sp[i]);
  std::vector<double> Vr = CholSolve(L, n, r);
  double c = 0;
  for (int i = 0; i < n; ++i) c += r[i] * Vr[i];
  return c;
}

inline FitResult FitTrack(const std::vector<Hit>& h, const SegmentField& bz, const FitOptions& opt) {
  FitResult res;
  int n = static_cast<int>(h.size());
  if (n < 3) return res;
  // non-bending first with the straight-line arc length, refined after the bending fit
  double cos_lambda = 1.0, t = 0, z0 = 0;
  double y0 = h[0].y, s0 = 0, rho = 0;
  {
    double dx = h[n - 1].x - h[0].x;
    s0 = dx > 0 ? (h[n - 1].y - h[0].y) / std::hypot(dx, h[n - 1].y - h[0].y) : 0;
  }
  std::vector<double> y, s, sp;
  for (int it = 0; it < opt.max_iterations; ++it) {
    // non-bending straight line in s_perp, generalized least squares with the multiple-scattering covariance
    Propagate(h, bz, y0, s0, rho, cos_lambda, y, s, sp);
    if (!FitLine(h, sp, s, cos_lambda, rho, opt, z0, t)) return res;
    cos_lambda = 1 / std::sqrt(1 + t * t);
    std::vector<double> xs(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) xs[i] = h[i].x;
    std::vector<double> L = Covariance(h, xs, s, cos_lambda, rho, opt, true);
    if (!Cholesky(L, n)) return res;
    // Jacobian by central differences
    double par[3] = {y0, s0, rho}, step[3] = {1e-3, 1e-6, std::max(1e-6, 1e-4 * std::fabs(rho))};
    std::vector<std::array<double, 3>> J(static_cast<std::size_t>(n));
    for (int a = 0; a < 3; ++a) {
      double pp[3] = {par[0], par[1], par[2]}, pm[3] = {par[0], par[1], par[2]};
      pp[a] += step[a];
      pm[a] -= step[a];
      std::vector<double> yp, ym, tmp1, tmp2;
      Propagate(h, bz, pp[0], pp[1], pp[2], cos_lambda, yp, tmp1, tmp2);
      Propagate(h, bz, pm[0], pm[1], pm[2], cos_lambda, ym, tmp1, tmp2);
      for (int i = 0; i < n; ++i) J[i][a] = (yp[i] - ym[i]) / (2 * step[a]);
    }
    std::vector<double> r(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) r[i] = h[i].y - y[i];
    // normal equations J^T V^-1 J d = J^T V^-1 r
    std::vector<std::vector<double>> VJ(3);
    for (int a = 0; a < 3; ++a) {
      std::vector<double> col(static_cast<std::size_t>(n));
      for (int i = 0; i < n; ++i) col[i] = J[i][a];
      VJ[a] = CholSolve(L, n, col);
    }
    std::vector<double> Vr = CholSolve(L, n, r);
    double M[3][3], b[3], d[3];
    for (int a = 0; a < 3; ++a) {
      b[a] = 0;
      for (int i = 0; i < n; ++i) b[a] += J[i][a] * Vr[i];
      for (int c = 0; c < 3; ++c) {
        M[a][c] = 0;
        for (int i = 0; i < n; ++i) M[a][c] += J[i][a] * VJ[c][i];
      }
    }
    if (!Solve3(M, b, d)) return res;
    {
      double e3[3] = {0, 0, 1}, col[3];
      if (Solve3(M, e3, col) && col[2] > 0) res.sigma_rho = std::sqrt(col[2]);
    }
    y0 += d[0];
    s0 += d[1];
    rho += d[2];
    if (std::fabs(s0) >= 1) return res;
    res.iterations = it + 1;
    if (std::fabs(d[2]) < 1e-12 * std::max(1.0, std::fabs(rho)) && std::fabs(d[0]) < 1e-9 && it > 1) break;
  }
  Propagate(h, bz, y0, s0, rho, cos_lambda, y, s, sp);
  // final chi2 with the final covariances (bending and non-bending)
  std::vector<double> xs(static_cast<std::size_t>(n));
  for (int i = 0; i < n; ++i) xs[i] = h[i].x;
  std::vector<double> L = Covariance(h, xs, s, cos_lambda, rho, opt, true);
  if (!Cholesky(L, n)) return res;
  std::vector<double> r(static_cast<std::size_t>(n));
  for (int i = 0; i < n; ++i) r[i] = h[i].y - y[i];
  std::vector<double> Vr = CholSolve(L, n, r);
  double chi2 = 0;
  for (int i = 0; i < n; ++i) chi2 += r[i] * Vr[i];
  chi2 += LineChi2(h, sp, s, cos_lambda, rho, opt, z0, t);
  res.ok = std::isfinite(rho) && std::isfinite(chi2);
  res.rho = rho;
  res.y0 = y0;
  res.s0 = s0;
  res.tan_lambda = t;
  res.z0 = z0;
  res.chi2 = chi2;
  res.ndof = 2 * n - 5;
  return res;
}

}  // namespace simreco

#endif
