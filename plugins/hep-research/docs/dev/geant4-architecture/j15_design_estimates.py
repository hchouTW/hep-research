"""Design estimates for the J15 minimal spectrometer (synthetic geometry), final version.

World-centred frame, stack axis x, at_mm = front face, B = (0, 0, +0.5 T): bending plane x-y, non-bending z.
Inputs: PDG Atomic & Nuclear Properties pages (2020 edition, retrieved 2026-10-21).
These numbers choose parameters only; they are never benchmark references.
Standard library only; scipy is used for chi2/F quantiles when available.
"""
import math
from fractions import Fraction

SI = dict(rho=2.329, X0=9.370, lam=46.52, I=173.0e-9, ZA=0.49848)   # I in GeV
PVT = dict(rho=1.032, X0=42.54, lam=78.80, I=64.7e-9, ZA=0.54141)
PB = dict(rho=11.35, X0=0.5612, lam=17.59, RM=1.602, Ec=7.43)
MP, MMU, ME, K = 0.938272, 0.105658, 0.000511, 0.307075
C_GEV = 0.299792458                     # GeV per (T m) for unit charge; also c in m/ns
B, EPS, N = 0.5, 10e-6, 6

# ---------------- geometry (mm) ----------------
FIELD = (-520.0, 320.0)
SI_C = [-500.0 + 160.0 * k for k in range(N)]
# each TOF station: two layers of the same material (G4_PLASTIC_SC_VINYLTOLUENE), 10 mm each, 10 mm apart
TOF_LAYER_MM, TOF_GAP_MM = 10.0, 10.0
TOF1 = [(-810.0, TOF_LAYER_MM), (-790.0, TOF_LAYER_MM)]   # (front face, thickness)
TOF2 = [(490.0, TOF_LAYER_MM), (510.0, TOF_LAYER_MM)]
CAL = (550.0, 350.0)
HALF = dict(si=100.0, field=150.0, tof2=200.0, cal=250.0)
WORLD = 1200.0
L = (SI_C[-1] - SI_C[0]) / 1000.0
def station_centre(st):
    return (st[0][0] + st[-1][0] + st[-1][1]) / 2


D = (station_centre(TOF2) - station_centre(TOF1)) / 1000.0


def exact_A(n):
    """4 (X^T X)^-1[2,2] for an equal-weight quadratic fit on n equally spaced points over [0, 1] (exact rational)."""
    xs = [Fraction(i, n - 1) for i in range(n)]
    S = [[sum(x ** (i + j) for x in xs) for j in range(3)] for i in range(3)]
    det = (S[0][0] * (S[1][1] * S[2][2] - S[1][2] * S[2][1]) - S[0][1] * (S[1][0] * S[2][2] - S[1][2] * S[2][0])
           + S[0][2] * (S[1][0] * S[2][1] - S[1][1] * S[2][0]))
    cof22 = S[0][0] * S[1][1] - S[0][1] * S[1][0]
    return float(4 * cof22 / det)


def closed_A(n):
    return 720 * (n - 1) ** 3 / ((n - 2) * n * (n + 1) * (n + 2))


def arc_y(x_mm, rig_gv, angle_rad=0.0, sign=-1):
    """y(x) for a circle of radius R entered at angle a0 (rad from +x, in x-y)."""
    R = rig_gv / (C_GEV * B) * 1000.0
    y = math.tan(angle_rad) * (min(x_mm, FIELD[0]) + 1000.0)
    if x_mm <= FIELD[0]:
        return y
    s0 = math.sin(angle_rad)
    xa = min(x_mm, FIELD[1])
    s1 = s0 + sign * (xa - FIELD[0]) / R                     # d(sin a)/dx = sign / R
    if abs(s1) >= 1:
        return float("nan")
    y += R * sign * (math.sqrt(1 - s0 ** 2) - math.sqrt(1 - s1 ** 2))
    if x_mm <= FIELD[1]:
        return y
    return y + math.tan(math.asin(s1)) * (x_mm - FIELD[1])


def max_abs_y_in_field(rig_gv, angle_rad, sign=-1, step=1.0):
    x, m = FIELD[0], 0.0
    while x <= FIELD[1]:
        m = max(m, abs(arc_y(x, rig_gv, angle_rad, sign)))
        x += step
    return m


def bethe(T, m, mat):
    """Mean ionization loss (MeV/cm), no density effect (fine for beta*gamma ~ 1)."""
    g = (T + m) / m
    b2 = 1 - 1 / g ** 2
    bg2 = b2 * g * g
    wmax = 2 * ME * bg2 / (1 + 2 * g * ME / m + (ME / m) ** 2)
    return K * mat['ZA'] / b2 * (0.5 * math.log(2 * ME * bg2 * wmax / mat['I'] ** 2) - b2) * mat['rho']


def lose(T, m, mat, cm, n=200):
    for _ in range(n):
        T -= bethe(T, m, mat) * cm / n / 1000.0
    return T


def beta(T, m):
    g = (T + m) / m
    return math.sqrt(1 - 1 / g ** 2)


def main():
    print("== geometry ==")
    print(f"Si centres {SI_C} mm; L = {L:.3f} m")
    print(f"TOF1 layers {TOF1}, TOF2 layers {TOF2} (front face, thickness mm); station centres "
          f"{station_centre(TOF1):.0f} / {station_centre(TOF2):.0f} mm; D = {D:.3f} m")
    print(f"margins to field mother: {SI_C[0] - 0.15 - FIELD[0]:.2f} / {FIELD[1] - SI_C[-1] - 0.15:.2f} mm; "
          f"world +-{WORLD:.0f} mm contains gun -1000 and calo end {CAL[0] + CAL[1]:.0f}")

    print("\n== tracker ==")
    for n in (4, 6, 8, 100):
        assert abs(exact_A(n) - closed_A(n)) < 1e-9 * closed_A(n)
    print("A_N exact LSQ == closed form for N = 4, 6, 8, 100:",
          {n: round(exact_A(n), 2) for n in (4, 6, 8)})
    mdr = C_GEV * B * L * L / (EPS * math.sqrt(exact_A(N)))
    x = N * 0.03 / SI['X0']
    th = 0.0136 * math.sqrt(x) * (1 + 0.038 * math.log(x))
    ms = th / (C_GEV * B * L)
    print(f"MDR (measurement term alone = 1) = {mdr:.1f} GV; MS term (beta=1, Highland with log on total) "
          f"{100 * ms:.2f} % (x1.0-1.4 bracket {100 * ms:.2f}-{140 * ms:.2f} %)")
    print("  B/N table (same lever arm L, equally spaced planes; beta = 1):")
    for bt, n in ((0.15, 6), (0.5, 6), (1.0, 6), (0.5, 4), (0.5, 8)):
        mdr_bn = C_GEV * bt * L * L / (EPS * math.sqrt(exact_A(n)))
        xn = n * 0.03 / SI['X0']
        ms_bn = 0.0136 * math.sqrt(xn) * (1 + 0.038 * math.log(xn)) / (C_GEV * bt * L)
        print(f"    B {bt:4.2f} T, N {n}: MDR {mdr_bn:6.0f} GV; MS {100 * ms_bn:.1f}-{140 * ms_bn:.1f} %; "
              f"equal-terms rigidity {ms_bn * mdr_bn:.0f}-{1.4 * ms_bn * mdr_bn:.0f} GV")
    for name, m in (("mu", MMU), ("p", MP)):
        for R in (0.6, 1, 2, 5):
            b = R / math.hypot(R, m)
            print(f"  {name} {R} GV: beta={b:.3f}  MS {100 * ms / b:.2f}-{140 * ms / b:.2f} %  "
                  f"crossover {ms / b * mdr:.0f}-{1.4 * ms / b * mdr:.0f} GV")

    print("\n== acceptance (positive unit charge bends toward -y; normal incidence) ==")

    def rmin(cond):
        lo, hi = 0.05, 100.0
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            lo, hi = (lo, mid) if cond(mid) else (mid, hi)
        return hi
    print(f"  stays inside field mother (|y|<=150 to x=320): {rmin(lambda r: max_abs_y_in_field(r, 0) <= HALF['field']):.3f} GV")
    print(f"  hits Si6 (|y|<=100):  {rmin(lambda r: abs(arc_y(SI_C[-1], r)) <= HALF['si']):.3f} GV")
    print(f"  hits TOF2 first layer (|y|<=200 at x={TOF2[0][0]:.0f}): "
          f"{rmin(lambda r: abs(arc_y(TOF2[0][0], r)) <= HALF['tof2']):.3f} GV")
    xb = TOF2[1][0] + TOF2[1][1]
    print(f"  hits both TOF2 layers (|y|<=200 at x={xb:.0f}): "
          f"{rmin(lambda r: abs(arc_y(xb, r)) <= HALF['tof2']):.3f} GV")
    rm = 39.5
    print(f"  calo front axis within 250-2R_M: {rmin(lambda r: abs(arc_y(CAL[0], r)) <= HALF['cal'] - 2 * rm):.3f} GV")
    print(f"  calo rear  axis within 250-2R_M: {rmin(lambda r: abs(arc_y(CAL[0] + CAL[1], r)) <= HALF['cal'] - 2 * rm):.3f} GV")

    print("\n== field-check grid: 50 mrad in the bending plane, AGAINST the bend (+y start for a positive charge) ==")
    for R in (0.6, 1, 10, 100, 1000):
        ys = [arc_y(s, R, +0.05) for s in SI_C]
        print(f"  {R:>6} GV: max|y| in field {max_abs_y_in_field(R, +0.05):6.1f} mm; Si1..Si6 y = "
              + ", ".join(f"{v:6.1f}" for v in ys) + f"; TOF2 layers y = {arc_y(TOF2[0][0], R, +0.05):6.1f}, "
              f"{arc_y(TOF2[1][0], R, +0.05):6.1f} mm")
    print("  (all |y| within Si 100 mm, field 150 mm and TOF2 200 mm => every grid track reaches every plane)")
    print("  for comparison, WITH the bend (-50 mrad start toward -y):")
    for R in (0.6, 1):
        print(f"  {R:>6} GV: Si6 y = {arc_y(SI_C[-1], R, -0.05):6.1f} mm; TOF2 first layer y = {arc_y(TOF2[0][0], R, -0.05):6.1f} mm")
    print("  normal incidence (0 mrad):")
    for R in (0.6, 1):
        print(f"  {R:>6} GV: Si6 y = {arc_y(SI_C[-1], R, 0.0):6.1f} mm; TOF2 layers y = {arc_y(TOF2[0][0], R, 0.0):6.1f}, "
              f"{arc_y(TOF2[1][0], R, 0.0):6.1f} mm")

    print("\n== proton energy loss and beta change ==")
    for R in (0.6, 1, 2):
        T0 = math.hypot(R, MP) - MP
        tof_cm = 2 * TOF_LAYER_MM / 10                       # both layers of a station
        T1 = lose(T0, MP, PVT, tof_cm)
        dp = (math.hypot(T0 + MP, 0) ** 2 - MP ** 2) ** 0.5 - ((T1 + MP) ** 2 - MP ** 2) ** 0.5
        Ta = lose(T0, MP, PVT, tof_cm / 2)                   # TOF1 station centre (after its first layer)
        Tb = lose(lose(T1, MP, SI, N * 0.03), MP, PVT, tof_cm / 2)  # TOF2 station centre
        print(f"  {R} GV: T={1000 * T0:.0f} MeV, TOF1 loss (2 layers) {1000 * (T0 - T1):.2f} MeV, dp/p {100 * dp / R:.2f} %, "
              f"beta mid-TOF1 -> mid-TOF2 change {100 * (beta(Ta, MP) - beta(Tb, MP)) / beta(Ta, MP):.2f} %")

    print("\n== TOF ==")
    print("  per-layer resolution sigma_t; station time = mean of its two layers (independent layers assumed)")
    for st in (0.08, 0.10, 0.15):
        s_station = st / math.sqrt(2)
        print(f"  sigma_t {1000 * st:.0f} ps per layer: station {1000 * s_station:.1f} ps -> sigma_beta/beta (beta=1) "
              f"{100 * math.sqrt(2) * s_station * C_GEV / D:.2f} % (one layer per station: "
              f"{100 * math.sqrt(2) * st * C_GEV / D:.2f} %); layer-pair difference {1000 * math.sqrt(2) * st:.0f} ps")
    dx = (TOF1[1][0] + TOF1[1][1] / 2) - (TOF1[0][0] + TOF1[0][1] / 2)
    print(f"  flight time between the two layers of a station (beta=1): {dx / 1000 / C_GEV * 1000:.1f} ps")

    print("\n== material in front of the calorimeter ==")
    n_tof = len(TOF1) + len(TOF2)
    x_tof = n_tof * TOF_LAYER_MM / 10 / PVT['X0']
    x_si = N * 0.03 / SI['X0']
    l_tof = n_tof * TOF_LAYER_MM / 10 / PVT['lam']
    l_si = N * 0.03 / SI['lam']
    print(f"  {n_tof} TOF layers: {100 * x_tof:.2f} % X0, {100 * l_tof:.2f} % lambda_I; Si: {100 * x_si:.2f} % X0, {100 * l_si:.2f} % lambda_I")
    print(f"  total {100 * (x_tof + x_si):.2f} % X0 (TOF {100 * x_tof / (x_tof + x_si):.0f} %), {100 * (l_tof + l_si):.2f} % lambda_I")
    print(f"  TOF1 alone (upstream of the tracker): {100 * 2 * TOF_LAYER_MM / 10 / PVT['X0']:.2f} % X0")

    print("\n== calorimeter ==")
    tp, ts, n = 0.2, 0.5, 50
    X = tp / PB['X0'] + ts / PVT['X0']
    lam = tp / PB['lam'] + ts / PVT['lam']
    print(f"  Pb2/PVT5 x50: {n * X:.2f} X0, {n * lam:.3f} lambda_I, {n * (tp + ts):.0f} cm")

    print("\n== statistics ==")
    try:
        from scipy.stats import chi2, f, norm, t
        print(f"  two-stage factor, criterion on the TRUE SE: P(chi2_15 >= 15/1.2) = {chi2.sf(12.5, 15):.3f}; "
              f"90 % needs 15/chi2_0.10(15) = {15 / chi2.ppf(0.10, 15):.3f}")
        print(f"  two-stage factor, criterion on the ESTIMATED SE (both runs K=16): P(F15,15 <= 1.2) = "
              f"{f.cdf(1.2, 15, 15):.3f}; 90 % needs F_0.90(15,15) = {f.ppf(0.90, 15, 15):.3f}")
        print(f"  t_0.95(30) = {t.ppf(0.95, 30):.3f}, t_0.95(15) = {t.ppf(0.95, 15):.3f}, t_0.975(15) = {t.ppf(0.975, 15):.3f}")
        print("  gate operating characteristics (se = tol/4 known, alpha = 0.05, pass z_0.95, fail z_{1-0.05/m}):")
        za = norm.ppf(0.95)
        for d in (0, 0.5, 1, 2):
            mu, s = d, 0.25
            p_pass = norm.cdf((1 - za * s - mu) / s) - norm.cdf((-(1 - za * s) - mu) / s)
            row = [f"pass {p_pass:.3f}"]
            for m in (1, 6, 30):
                zf = norm.ppf(1 - 0.05 / m)
                thr = 1 + zf * s
                p_fail = norm.sf((thr - mu) / s) + norm.cdf((-thr - mu) / s)
                row.append(f"fail(m={m}) {p_fail:.3f}")
            print(f"    true diff {d} tol: " + ", ".join(row))
    except ImportError:
        print("  scipy not available: f(true SE) = 1.755, F_0.90(15,15) = 1.972 (see document)")

    print("\n== event counts (se of the difference <= tol/4) ==")
    for name, sd, tol in (("calo total deposit 10 GeV e-, sd/mean 0.035", 0.035, 0.01),
                          ("rear leakage fraction 10 GeV e-, sd 0.02-0.03 (absolute)", 0.025, 0.002)):
        print(f"  {name}: tol {tol}: {(math.sqrt(2) * sd / (tol / 4)) ** 2:,.0f} per point")


if __name__ == "__main__":
    main()
