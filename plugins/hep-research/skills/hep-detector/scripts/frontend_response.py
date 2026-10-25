#!/usr/bin/env python3
"""Front-end electronics response: noise, thresholds, timing, quantization, pileup, SiPM, dead time, sampled
waveforms, hit efficiency.

Purpose: put numbers on how readout electronics shapes a detector's response - the
equivalent noise charge of a charge-sensitive amplifier and CR-(RC)^n shaper and its
optimum shaping time, the noise-hit rate above a threshold, timing jitter and walk,
quantization error, the pileup (Campbell) mean and spread of a shaped signal, SiPM
saturation and correlated noise, ballistic deficit, dead time, and the noise of a sum
of correlated channels. For reconstruction and simulation: optimal-filter weights of a
sampled pulse (correlated and Campbell pileup noise, optional phase and baseline constraints,
joint amplitude-time errors), hit efficiency of a Landau or Gaussian signal against noise
occupancy versus threshold (the operating window), and a seeded synthetic sampled readout
reconstructed by those estimators with closure against the analytic prediction (output
labelled synthetic in status_label). For calibration: the binomial fit of a threshold scan (S-curve) or
the expected errors of a scan design, and the threshold dispersion after per-channel trim. Each result carries its assumptions and a validity
list; a non-empty validity list means the input is outside the range where the relation holds.

Subcommands (all numbers on the command line; JSON on stdout):
  enc          ENC (electrons) from capacitance, series/parallel/1/f noise, peaking time, order
  noise-rate   Rice up-crossing rate above a threshold, fake hits per event
  timing       jitter, leading-edge walk, constant-fraction mode, TDC quantization
  quantize     effective quantization error and the bias that survives averaging
  pileup       Campbell mean and sigma of a shaped Poisson pulse train (unipolar or bipolar)
  sipm         SiPM saturation, crosstalk (Borel) and dark-count mean and variance
  ballistic    amplitude deficit for a rectangular current of finite duration
  deadtime     measured rate and live fraction (non-paralyzable or paralyzable), or the inverse
  cluster-noise  noise of a sum of N channels with pairwise correlation rho
  leakage-scale  silicon leakage current at another temperature, I ~ T^2 exp(-E_eff / 2kT)
  optimal-filter  amplitude weights and variance from a few samples (optimal filter, uncorrelated template,
                  largest sample) with correlated and pileup noise; phase-error and baseline bias; time error
  hit-efficiency  efficiency (Landau or Gaussian signal) and noise occupancy versus threshold; operating window
  waveform-toy    seeded synthetic sampled readout (noise, pileup, jitter, ADC) reconstructed by those
                  estimators, with closure against the analytic prediction
  s-curve         binomial fit of a threshold scan (threshold, noise, errors, goodness of fit), or the
                  expected errors of a scan design
  threshold-trim  threshold dispersion after per-channel trim (trim range, step, DAC nonlinearity)

Conventions: the shaper's response to a unit input charge is g(t) = (t/tau)^n exp(-t/tau),
normalized to peak 1, with peaking time t_p = n tau. The bipolar shape of the pileup
subcommand is tau dg/dt, which is not peak-normalized; --mean-amp is the amplitude of the
unipolar pulse. Noise densities are one-sided:
i_n^2 = 2 q I_leak (+ 4kT/R_p), e_n^2 in V^2/Hz, 1/f density A_f/f in V^2/Hz. Then
ENC^2 = (i_n^2/2) int g^2 + C^2 (e_n^2/2) int g'^2 + C^2 A_f int |G'(f)|^2/f df, all in
closed form for CR-(RC)^n. Units: capacitance pF, e_n nV/sqrt(Hz), leakage nA, times ns,
rates Hz unless the option says otherwise. Sampled-waveform subcommands (optimal-filter, waveform-toy) take
amplitudes in units of the per-sample electronic noise sigma for a unit-peak pulse; hit-efficiency takes charges in
one unit of the user's choice (electrons, say). Standard library plus the plugin's core/stats linear solver.
See <plugin root>/skills/hep-detector/references/front-end-electronics-and-signal-processing.md.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed or the input file is unreadable or invalid (JSON with ok false);
2 invalid input (JSON with error_kind invalid-input on stdout, the usage on stderr).
Run: python3 <plugin root>/skills/hep-detector/scripts/frontend_response.py enc --capacitance 10 --en 1 --leakage 1000 --peaking 25
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from core.stats._linalg import solve  # noqa: E402
from core.stats.statistical_toys import chi2_sf  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection', 'outside-validated-range')  # contracts/vocab/core.json artifact_statuses


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': 'invalid-input', 'error': message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: error: {message}\n')


Q_E = 1.602176634e-19      # C
K_B = 1.380649e-23         # J/K
E_EFF_SI = 1.21            # eV, effective band gap for silicon leakage-current scaling
K_B_EV = 8.617333262e-5    # eV/K


def _num(value, name, positive=True, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if positive and (value < 0 or (value == 0 and not allow_zero)):
        raise ValueError(f'{name} must be {"non-negative" if allow_zero else "greater than zero"}')
    return float(value)


def _order(n):
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 10:
        raise ValueError('shaper order must be an integer from 1 to 10')
    return n


# ---------------------------------------------------------------- shaper integrals

def _norm(n):
    """Peak of (t/tau)^n exp(-t/tau), reached at t = n tau."""
    return n ** n * math.exp(-n)


def shaper_integrals(order, tau):
    """Closed-form integrals of the peak-normalized CR-(RC)^n response g(t).

    Returns int g dt, int g^2 dt, int g'^2 dt, and the 1/f index int |G'(f)|^2 / f df.
    """
    n = _order(order)
    tau = _num(tau, 'tau')
    norm = _norm(n)
    gamma = math.gamma
    int_g = tau * gamma(n + 1) / norm
    int_g2 = tau * gamma(2 * n + 1) / 2 ** (2 * n + 1) / norm ** 2
    int_gp2 = (n * n * gamma(2 * n - 1) / 2 ** (2 * n - 1)
               - 2 * n * gamma(2 * n) / 2 ** (2 * n)
               + gamma(2 * n + 1) / 2 ** (2 * n + 1)) / tau / norm ** 2
    flicker = gamma(n + 1) ** 2 / (2 * n * norm ** 2)
    return {'int_g': int_g, 'int_g2': int_g2, 'int_gp2': int_gp2, 'flicker_index': flicker}


def _half_beta(a, b):
    """int_0^inf x^(2a) / (1 + x^2)^b dx = B(a + 1/2, b - a - 1/2) / 2."""
    return 0.5 * math.gamma(a + 0.5) * math.gamma(b - a - 0.5) / math.gamma(b)


def rice_nu0(order, tau, noise_type):
    """Zero-level up-crossing rate nu_0 = sqrt(m2/m0)/(2 pi) of white noise through CR-(RC)^n.

    Parallel (current) noise sees |G|^2 ~ 1/(1+x^2)^(n+1); series (voltage) noise sees
    x^2/(1+x^2)^(n+1). Returns None when m2 diverges (series noise with n = 1).
    """
    n = _order(order)
    tau = _num(tau, 'tau')
    b = n + 1
    if noise_type == 'parallel':
        a0, a2 = 0, 1
    elif noise_type == 'series':
        a0, a2 = 1, 2
    else:
        raise ValueError("noise type must be 'series' or 'parallel'")
    if b - a2 - 0.5 <= 0:
        return None
    return math.sqrt(_half_beta(a2, b) / _half_beta(a0, b)) / (2 * math.pi * tau)


# ---------------------------------------------------------------- enc

def enc(capacitance_pf, peaking_ns, order=1, en_nv=0.0, leakage_na=0.0, rp_ohm=None,
        af_v2=0.0, temperature_k=300.0):
    """Equivalent noise charge in electrons, by term, and the series/parallel optimum."""
    c = _num(capacitance_pf, 'capacitance', allow_zero=True) * 1e-12
    tp = _num(peaking_ns, 'peaking time') * 1e-9
    n = _order(order)
    en = _num(en_nv, 'e_n', allow_zero=True) * 1e-9
    ileak = _num(leakage_na, 'leakage current', allow_zero=True) * 1e-9
    af = _num(af_v2, 'A_f', allow_zero=True)
    temp = _num(temperature_k, 'temperature')
    in2 = 2 * Q_E * ileak
    if rp_ohm is not None:
        in2 += 4 * K_B * temp / _num(rp_ohm, 'R_p')
    tau = tp / n
    ints = shaper_integrals(n, tau)
    par2 = in2 / 2 * ints['int_g2']
    ser2 = c * c * en * en / 2 * ints['int_gp2']
    flk2 = c * c * af * ints['flicker_index']
    total = math.sqrt(par2 + ser2 + flk2) / Q_E
    # parallel ~ a*tp, series ~ b/tp  ->  tp_opt = sqrt(b/a)
    a = par2 / tp
    b = ser2 * tp
    optimum = None
    if a > 0 and b > 0:
        tp_opt = math.sqrt(b / a)
        enc_opt = math.sqrt(2 * math.sqrt(a * b) + flk2) / Q_E
        optimum = {'peaking_ns': tp_opt * 1e9, 'enc_electrons': enc_opt}
    validity = []
    if c == 0 and (en > 0 or af > 0):
        validity.append('zero capacitance: series and 1/f terms vanish; check that C includes amplifier and strays')
    return {
        'enc_electrons': total,
        'terms_electrons': {'parallel': math.sqrt(par2) / Q_E, 'series': math.sqrt(ser2) / Q_E,
                            'flicker': math.sqrt(flk2) / Q_E},
        'dominant_term': (None if par2 + ser2 + flk2 == 0 else
                          max((('parallel', par2), ('series', ser2), ('flicker', flk2)), key=lambda x: x[1])[0]),
        'optimum_series_vs_parallel': optimum,
        'shaper': {'order': n, 'peaking_ns': tp * 1e9, 'tau_ns': tau * 1e9},
        'assumptions': ['charge-sensitive amplifier, ideal CR-(RC)^n shaper with equal time constants',
                        'stationary noise, one-sided densities; i_n^2 = 2 q I_leak (+ 4kT/R_p)',
                        'instantaneous charge collection (no ballistic deficit)'],
        'validity': validity,
    }


def leakage_scale(current_na, from_celsius, to_celsius, e_eff_ev=E_EFF_SI):
    """Silicon leakage current scaled to another temperature: I ~ T^2 exp(-E_eff / 2kT)."""
    i0 = _num(current_na, 'leakage current', allow_zero=True)
    t1 = _num(from_celsius + 273.15, 'temperature')
    t2 = _num(to_celsius + 273.15, 'temperature')
    e = _num(e_eff_ev, 'E_eff')
    factor = (t2 / t1) ** 2 * math.exp(-e / (2 * K_B_EV) * (1 / t2 - 1 / t1))
    return i0 * factor


# ---------------------------------------------------------------- noise rate

def noise_rate(threshold_sigma, peaking_ns, order=2, noise_type='series', series_fraction=None,
               channels=1, window_ns=None):
    """Rice up-crossing rate nu = nu_0 exp(-T^2/2 sigma^2); fake hits per channel and event."""
    thr = _num(threshold_sigma, 'threshold (in units of sigma)', allow_zero=True)
    tp = _num(peaking_ns, 'peaking time') * 1e-9
    n = _order(order)
    tau = tp / n
    if series_fraction is not None and noise_type != 'mixed':
        raise ValueError("series fraction applies only to noise type 'mixed'")
    if noise_type == 'mixed':
        frac = _num(series_fraction if series_fraction is not None else -1, 'series fraction', allow_zero=True)
        if frac > 1:
            raise ValueError('series fraction must be between 0 and 1')
        nus, nup = rice_nu0(n, tau, 'series'), rice_nu0(n, tau, 'parallel')
        nu0 = None if (nus is None and frac > 0) else math.sqrt(frac * (nus or 0) ** 2 + (1 - frac) * nup ** 2)
    else:
        nu0 = rice_nu0(n, tau, noise_type)
    validity = []
    if nu0 is None:
        validity.append('series noise through CR-RC (order 1) has an undefined crossing rate without a further '
                        'bandwidth limit; use the measured noise spectrum or a higher order')
        return {'nu0_hz': None, 'rate_per_channel_hz': None, 'threshold_sigma': thr, 'noise_type': noise_type,
                'assumptions': ['stationary Gaussian noise (Rice formula)'], 'validity': validity}
    rate = nu0 * math.exp(-thr * thr / 2)
    out = {'nu0_hz': nu0, 'nu0_times_tau': nu0 * tau, 'nu0_times_peaking': nu0 * tp, 'rate_per_channel_hz': rate,
           'threshold_sigma': thr, 'noise_type': noise_type,
           'assumptions': ['stationary Gaussian noise (Rice formula); white series/parallel noise through '
                           'CR-(RC)^n; 1/f, pickup and random-telegraph noise are not included'],
           'validity': validity}
    if isinstance(channels, bool) or not isinstance(channels, int) or channels < 1:
        raise ValueError('channels must be a positive integer')
    nch = channels
    if window_ns is not None:
        w = _num(window_ns, 'window') * 1e-9
        out['window_ns'] = w * 1e9
        out['expected_fake_hits_per_event'] = nch * rate * w
        out['probability_channel_has_fake'] = 1 - math.exp(-rate * w)
    if thr < 2:
        validity.append('threshold below 2 sigma: hits overlap and the crossing count saturates; '
                        'the formula counts crossings, not separate hits')
    if thr > 6:
        validity.append('threshold above 6 sigma: the real rate is set by non-Gaussian tails (pickup, RTS), '
                        'not by this formula; measure it')
    return out


# ---------------------------------------------------------------- timing

def timing(rise_ns, snr, threshold_fraction=None, amplitudes=None, cfd_fraction=None, cfd_delay_ns=None,
           tdc_lsb_ps=None):
    """Jitter t_r/(S/N); leading-edge walk; CFD mode and crossing; TDC quantization."""
    tr = _num(rise_ns, 'rise time')
    s = _num(snr, 'signal-to-noise ratio')
    out = {'jitter_ps': tr / s * 1e3,
           'assumptions': ['linear leading edge; t_r is the 0-100 % rise time (for a 10-90 % rise time the '
                           'slope is 0.8 A/t_r, so multiply the jitter by 1.25); noise slowly varying on the edge'],
           'validity': []}
    if s < 5:
        out['validity'].append('S/N below 5: the linear-edge jitter formula underestimates; noise can cause '
                               'early or missed crossings')
    if threshold_fraction is not None and amplitudes is not None:
        f = _num(threshold_fraction, 'threshold')
        a1, a2 = (_num(a, 'amplitude') for a in amplitudes)
        if f >= min(a1, a2):
            raise ValueError('threshold must be below both amplitudes')
        out['walk_ps'] = f * tr * (1 / a1 - 1 / a2) * 1e3
        out['walk_note'] = 'crossing time of a linear edge is T t_r / A; correct per channel with amplitude or ToT'
    if cfd_fraction is not None and cfd_delay_ns is not None:
        f = _num(cfd_fraction, 'CFD fraction')
        if f >= 1:
            raise ValueError('CFD fraction must be below 1')
        td = _num(cfd_delay_ns, 'CFD delay')
        if td < (1 - f) * tr:
            out['cfd'] = {'mode': 'amplitude-and-rise-time-compensated', 'crossing_after_start_ns': td / (1 - f),
                          'depends_on_rise_time': False}
        else:
            out['cfd'] = {'mode': 'true constant fraction', 'crossing_after_start_ns': td + f * tr,
                          'depends_on_rise_time': True}
    if tdc_lsb_ps is not None:
        lsb = _num(tdc_lsb_ps, 'TDC bin')
        out['tdc_quantization_ps'] = lsb / math.sqrt(12)
        out['tdc_note'] = ('lsb/sqrt(12) is the rms over random phases; at a fixed phase it averages out only if '
                           'noise dithers by at least about 0.5 bin')
    return out


# ---------------------------------------------------------------- quantization

def _phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def quantize(noise_lsb, grid=200):
    """Effective error of rounding x + noise; the bias that survives averaging, maximized over x."""
    s = _num(noise_lsb, 'noise (LSB)', allow_zero=True)
    worst = 0.0
    worst_x = 0.0
    for i in range(grid):
        x = (i + 0.5) / grid
        if s == 0:
            mean = round(x)
        else:
            mean = 0.0
            for k in range(-int(8 * s) - 2, int(8 * s) + 3):
                p = _phi((k + 0.5 - x) / s) - _phi((k - 0.5 - x) / s)
                mean += k * p
        bias = mean - x
        if abs(bias) > abs(worst):
            worst, worst_x = bias, x
    validity = []
    if s < 0.5:
        validity.append('noise below 0.5 LSB: at a fixed true value the error is deterministic and does not '
                        'average out (lsb/sqrt(12) remains the rms only over a broad spread of true values)')
    return {'noise_lsb': s, 'sigma_effective_lsb': math.sqrt(s * s + 1 / 12),
            'max_abs_bias_lsb': abs(worst), 'at_true_fraction_of_lsb': worst_x,
            'assumptions': ['uniform quantizer (no differential nonlinearity); Gaussian noise before rounding'],
            'validity': validity}


# ---------------------------------------------------------------- pileup

def pileup(rate_hz, mean_amp, second_moment, peaking_ns, order=1, bipolar=False):
    """Campbell's theorem: mean nu <a> int g, variance nu <a^2> int g^2 (stationary Poisson)."""
    nu = _num(rate_hz, 'rate', allow_zero=True)
    a1 = _num(mean_amp, 'mean amplitude', positive=False)
    a2 = _num(second_moment, 'second moment of amplitude', allow_zero=True)
    if a2 < a1 * a1:
        raise ValueError('second moment must be at least the square of the mean amplitude')
    tp = _num(peaking_ns, 'peaking time') * 1e-9
    n = _order(order)
    tau = tp / n
    ints = shaper_integrals(n, tau)
    if bipolar:
        int_g, int_g2 = 0.0, tau * tau * ints['int_gp2']
    else:
        int_g, int_g2 = ints['int_g'], ints['int_g2']
    out = {'mean': nu * a1 * int_g, 'sigma': math.sqrt(nu * a2 * int_g2),
           'occupancy_per_peaking_time': nu * tp, 'shape': 'bipolar (tau dg/dt)' if bipolar else 'unipolar',
           'assumptions': ['stationary Poisson arrivals; pulses add linearly (no saturation or dead time)'],
           'validity': []}
    if bipolar:
        out['max_offset_after_rate_step'] = nu * a1 * tau
        out['note'] = ('zero mean only in steady state: after a step in rate the offset is nu <a> tau g(t), '
                       'maximal at t_p = n tau after the step')
    if nu * tp > 1:
        out['validity'].append('more than one pulse per peaking time: amplitude estimates need a multi-pulse fit; '
                               'saturation and baseline effects are not modeled')
    return out


# ---------------------------------------------------------------- sipm

def sipm(cells, npe, crosstalk=0.0, dcr_hz=0.0, gate_ns=0.0):
    """SiPM saturation, Borel crosstalk, and dark-count mean/variance in fired cells.

    crosstalk is the measured (datasheet) probability P_ct that an avalanche triggers at
    least one more; with Poisson secondaries the mean number per avalanche is
    lambda = -ln(1 - P_ct), and the total per primary is Borel(lambda).
    """
    if isinstance(cells, bool) or not isinstance(cells, int) or cells < 1:
        raise ValueError('number of cells must be a positive integer')
    nc = cells
    mu = _num(npe, 'photoelectrons', allow_zero=True)
    pct = _num(crosstalk, 'crosstalk probability', allow_zero=True)
    if pct >= 1:
        raise ValueError('crosstalk probability must be below 1')
    p = -math.log1p(-pct)
    if p >= 1:
        raise ValueError('crosstalk probability >= 1 - 1/e gives a supercritical branching process (no finite mean)')
    dcr = _num(dcr_hz, 'dark count rate', allow_zero=True)
    gate = _num(gate_ns, 'gate', allow_zero=True) * 1e-9
    fired = nc * (1 - math.exp(-mu / nc))
    borel_mean = 1 / (1 - p)
    borel_var = p / (1 - p) ** 3
    lam = dcr * gate
    second = borel_var + borel_mean ** 2
    validity = []
    if mu / nc > 0.2:
        validity.append('more than 20 % of cells fired: nonlinear regime; use a measured response curve, and '
                        'note that light longer than the cell recovery time raises the effective cell count')
    if p > 0.5:
        validity.append('mean secondaries above 0.5: branching is near critical; check the device data')
    return {'fired_cells': fired, 'linearity_fraction': fired / mu if mu > 0 else 1.0,
            'crosstalk_cells_per_primary': {'mean': borel_mean, 'variance': borel_var,
                                            'crosstalk_probability': pct, 'mean_secondaries_lambda': p},
            'dark_counts_in_gate': {'mean_cells': lam * borel_mean, 'sigma_cells': math.sqrt(lam * second)},
            'assumptions': ['prompt, uniform illumination for saturation; crosstalk as a Borel branching process; '
                            'afterpulses not included'],
            'validity': validity}


# ---------------------------------------------------------------- ballistic deficit

def _cum_g(t, n, tau):
    """int_0^t g(t') dt' for the peak-normalized CR-(RC)^n response."""
    if t <= 0:
        return 0.0
    x = t / tau
    s = sum(x ** k / math.factorial(k) for k in range(n + 1))
    return tau * math.factorial(n) * (1 - math.exp(-x) * s) / _norm(n)


def ballistic(collection_ns, peaking_ns, order=1):
    """Peak amplitude for a rectangular current of duration T_c, relative to an instantaneous charge."""
    tc = _num(collection_ns, 'collection time')
    tp = _num(peaking_ns, 'peaking time')
    n = _order(order)
    tau = tp / n

    def out(t):
        return (_cum_g(t, n, tau) - _cum_g(t - tc, n, tau)) / tc

    lo, hi = 0.0, tc + 20 * tp
    steps = 4000
    best_t = max((lo + (hi - lo) * i / steps for i in range(steps + 1)), key=out)
    a, b = max(lo, best_t - (hi - lo) / steps), best_t + (hi - lo) / steps
    for _ in range(100):
        m1, m2 = a + (b - a) / 3, b - (b - a) / 3
        if out(m1) < out(m2):
            a = m1
        else:
            b = m2
    peak = out((a + b) / 2)
    result = {'relative_amplitude': peak, 'deficit': 1 - peak, 'time_of_peak_ns': (a + b) / 2,
              'assumptions': ['rectangular induced current of duration T_c; ideal CR-(RC)^n shaper'],
              'validity': []}
    result['approximation_deficit'] = n * (tc / tp) ** 2 / 24
    if tc > tp:
        result['validity'].append('T_c > t_p: the n (T_c/t_p)^2/24 approximation overestimates; use the exact value')
    return result


# ---------------------------------------------------------------- dead time

def deadtime(dead_ns, rate_hz=None, measured_hz=None, model='nonparalyzable'):
    """Measured rate and live fraction, or the true rate from a measured one (Poisson arrivals)."""
    tau = _num(dead_ns, 'dead time') * 1e-9
    if model not in ('nonparalyzable', 'paralyzable'):
        raise ValueError("model must be 'nonparalyzable' or 'paralyzable'")
    if (rate_hz is None) == (measured_hz is None):
        raise ValueError('give exactly one of the true rate or the measured rate')
    out = {'model': model, 'dead_time_ns': tau * 1e9,
           'assumptions': ['Poisson arrivals; a single dead-time source. Bunched beams, spills and trigger rules '
                           'need a measured live fraction'],
           'validity': []}
    if rate_hz is not None:
        n = _num(rate_hz, 'rate', allow_zero=True)
        m = n / (1 + n * tau) if model == 'nonparalyzable' else n * math.exp(-n * tau)
        out.update({'true_rate_hz': n, 'measured_rate_hz': m, 'live_fraction': m / n if n > 0 else 1.0})
        if model == 'paralyzable' and n * tau > 1:
            out['validity'].append('beyond the turnover (n tau > 1): the same measured rate also arises from a '
                                   'lower true rate')
        return out
    m = _num(measured_hz, 'measured rate', allow_zero=True)
    if model == 'nonparalyzable':
        if m * tau >= 1:
            raise ValueError('measured rate cannot reach 1/dead time for a non-paralyzable system')
        n = m / (1 - m * tau)
        out.update({'measured_rate_hz': m, 'true_rate_hz': n, 'live_fraction': m / n if n > 0 else 1.0})
        return out
    if m * tau > math.exp(-1):
        raise ValueError('measured rate above the paralyzable maximum 1/(e tau)')
    lo, hi = 0.0, 1.0 / tau        # low-rate branch of m = n exp(-n tau): increasing on [0, 1/tau]
    for _ in range(200):
        mid = (lo + hi) / 2
        if mid * math.exp(-mid * tau) < m:
            lo = mid
        else:
            hi = mid
    n = (lo + hi) / 2
    out.update({'measured_rate_hz': m, 'true_rate_hz_low_branch': n,
                'live_fraction': m / n if n > 0 else 1.0})
    out['validity'].append('paralyzable inversion is two-valued; the low-rate branch is reported')
    return out


# ---------------------------------------------------------------- cluster noise

def cluster_noise(channels, sigma, rho):
    """sigma of a sum of N channels with equal sigma and pairwise correlation rho."""
    if isinstance(channels, bool) or not isinstance(channels, int) or channels < 1:
        raise ValueError('channels must be a positive integer')
    s = _num(sigma, 'sigma')
    r = _num(rho, 'rho', positive=False)
    if channels > 1 and not -1 / (channels - 1) <= r <= 1:
        raise ValueError('rho must lie in [-1/(N-1), 1] for a valid covariance')
    total = s * math.sqrt(channels + channels * (channels - 1) * r)
    return {'sigma_sum': total, 'sigma_sum_if_independent': s * math.sqrt(channels),
            'ratio_to_independent': total / (s * math.sqrt(channels)),
            'assumptions': ['equal per-channel sigma and a single pairwise correlation coefficient'],
            'validity': []}


# ---------------------------------------------------------------- sampled pulses

def pulse(t, n, tau):
    """Peak-normalized CR-(RC)^n response g(t) = (t/tau)^n exp(-t/tau) / (n^n e^-n); zero for t <= 0."""
    if t <= 0:
        return 0.0
    x = t / tau
    return math.exp(n * math.log(x) - x) / _norm(n)


def pulse_derivative(t, n, tau):
    """dg/dt of the peak-normalized CR-(RC)^n response (1/time unit of tau)."""
    if t <= 0:
        return 0.0
    return pulse(t, n, tau) * (n / t - 1 / tau)


def pulse_autocorrelation(delta, n, tau):
    """int_0^inf g(t) g(t + |delta|) dt in closed form (time unit of tau).

    With g = (t/tau)^n e^(-t/tau)/N: tau^-2n N^-2 e^(-d/tau) sum_k C(n, k) d^(n-k) (n+k)! (tau/2)^(n+k+1).
    """
    d = abs(delta)
    total = 0.0
    for k in range(n + 1):
        total += math.comb(n, k) * d ** (n - k) * math.factorial(n + k) * (tau / 2) ** (n + k + 1)
    return total * math.exp(-d / tau) / (tau ** (2 * n) * _norm(n) ** 2)


def _support_ns(n, tau, rel=1e-7):
    """Time after which the peak-normalized pulse stays below rel (to bound a pileup history)."""
    t = n * tau
    while pulse(t, n, tau) > rel:
        t += tau
    return t


def _sample_times(peaking_ns, period_ns, samples, first_offset_ns):
    if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= 64:
        raise ValueError('samples must be an integer from 1 to 64')
    period = _num(period_ns, 'sampling period')
    first = _num(first_offset_ns, 'first-sample offset', positive=False)
    return [peaking_ns + first + i * period for i in range(samples)]


def _noise_covariance(times, n, tau, rho, pileup_rate_hz, pileup_rms):
    """Per-sample noise covariance in units of the electronic noise variance.

    Electronic part rho^|i-j| (exponential correlation, unit variance per sample); pileup part from Campbell's
    theorem, nu <a^2> int g(t) g(t + t_i - t_j) dt, with <a^2> in units of the electronic noise variance.
    """
    m = len(times)
    nu_a2 = pileup_rate_hz * 1e-9 * pileup_rms ** 2  # per ns, so that the ns autocorrelation is dimensionless
    cov = [[0.0] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            cov[i][j] = rho ** abs(i - j) + (nu_a2 * pulse_autocorrelation(times[i] - times[j], n, tau)
                                             if nu_a2 > 0 else 0.0)
    return cov


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _matvec(m, v):
    return [_dot(row, v) for row in m]


def _solve_vec(a, v, info=None):
    return [row[0] for row in solve(a, [[x] for x in v], error=ValueError, what='noise covariance', info=info)]


def _filter_weights(g, cov, info=None, extra=()):
    """Optimal-filter amplitude weights and their variance.

    Without constraints w = R^-1 g / (g^T R^-1 g), variance 1/(g^T R^-1 g). With extra constraint vectors c_k
    (w . c_k = 0, e.g. the pulse derivative for phase insensitivity or a vector of ones for baseline insensitivity),
    w = R^-1 C (C^T R^-1 C)^-1 e_1 with C = [g, c_1, ...], variance ((C^T R^-1 C)^-1)_11 (Lagrange multipliers).
    """
    cols = [g, *extra]
    rinv = [_solve_vec(cov, c, info if i == 0 else None) for i, c in enumerate(cols)]
    gram = [[_dot(ci, rj) for rj in rinv] for ci in cols]
    if gram[0][0] <= 0:
        raise ValueError('the pulse has no projection on the samples (all samples outside the pulse)')
    m = len(cols)
    sol_info = {}
    lam = [row[0] for row in solve(gram, [[1.0 if i == 0 else 0.0] for i in range(m)], error=ValueError,
                                   what='constraint matrix', info=sol_info)]
    if m > 1 and sol_info.get('min_pivot_ratio', 1.0) < 1e-12:
        raise ValueError('the constraints are degenerate with these samples (add samples or drop a constraint)')
    w = [sum(lam[k] * rinv[k][i] for k in range(m)) for i in range(len(g))]
    return w, lam[0]


def _check_rho(rho):
    r = _num(rho, 'rho', allow_zero=True)
    if r >= 1:
        raise ValueError('rho must be below 1')
    return r


# ---------------------------------------------------------------- optimal filter

def _constraint_vectors(constraints, times, n, tau):
    extra = []
    for c in constraints:
        if c == 'phase':
            extra.append([pulse_derivative(t, n, tau) for t in times])
        elif c == 'baseline':
            extra.append([1.0] * len(times))
        else:
            raise ValueError("constraints must be 'phase' and/or 'baseline'")
    if len(set(constraints)) != len(constraints):
        raise ValueError('a constraint is given twice')
    return extra


def optimal_filter(order, peaking_ns, period_ns, samples, first_offset_ns, rho=0.0, pileup_rate_hz=0.0,
                   pileup_rms=0.0, amplitude=None, phase_errors_ns=(), constraints=()):
    """Amplitude (and time) estimators from a few samples of a known pulse: optimal filter, uncorrelated
    template fit, largest sample; their variances, the bias from a phase error and from a baseline offset.

    Units: amplitudes and noise in units of the per-sample electronic noise sigma; the pulse has unit peak.
    """
    n = _order(order)
    tp = _num(peaking_ns, 'peaking time')
    tau = tp / n
    times = _sample_times(tp, period_ns, samples, first_offset_ns)
    r = _check_rho(rho)
    nu = _num(pileup_rate_hz, 'pileup rate', allow_zero=True)
    a_rms = _num(pileup_rms, 'pileup amplitude rms', allow_zero=True)
    g = [pulse(t, n, tau) for t in times]
    if max(g) <= 0:
        raise ValueError('every sample is before the pulse starts: move the first sample later')
    cov = _noise_covariance(times, n, tau, r, nu, a_rms)
    info = {}
    extra = _constraint_vectors(list(constraints), times, n, tau)
    if len(extra) + 1 > len(times):
        raise ValueError('more constraints than samples')
    w, var = _filter_weights(g, cov, info, extra)
    gg = _dot(g, g)
    w_t = [x / gg for x in g]
    var_t = _dot(w_t, _matvec(cov, w_t))
    k = max(range(len(g)), key=lambda i: g[i])
    sigma_max = math.sqrt(cov[k][k]) / g[k]
    pile_sigma = math.sqrt(nu * 1e-9 * a_rms ** 2 * pulse_autocorrelation(0.0, n, tau))
    out = {'sample_times_ns': times, 'pulse_samples': g, 'constraints': list(constraints), 'weights_optimal': w,
           'sigma_optimal': math.sqrt(var), 'sigma_template_uncorrelated': math.sqrt(var_t),
           'sigma_largest_sample': sigma_max, 'largest_sample_index': k,
           'pileup_sigma_per_sample': pile_sigma,
           'baseline_offset_gain': {'optimal': sum(w), 'template_uncorrelated': sum(w_t), 'largest_sample': 1 / g[k]},
           'assumptions': ['known CR-(RC)^n pulse shape and phase; stationary Gaussian noise with exponential '
                           'sample correlation rho^|i-j| plus Campbell pileup noise (unipolar pulses, Poisson '
                           'arrivals); sigmas are for unit pulse amplitude in units of the per-sample electronic '
                           'noise'],
           'validity': []}
    if constraints:
        out['sigma_optimal_unconstrained'] = math.sqrt(_filter_weights(g, cov)[1])
    out['note'] = ('baseline_offset_gain: a constant offset b on every sample (pileup mean, pedestal error) biases '
                   'the amplitude by b times this sum; it is 1/g_peak-like, not zero, for unipolar pulses')
    if phase_errors_ns:
        biases = []
        for dt in phase_errors_ns:
            d = _num(dt, 'phase error', positive=False)
            shifted = [pulse(t + d, n, tau) for t in times]
            biases.append({'phase_error_ns': d, 'optimal': _dot(w, shifted) - 1,
                           'template_uncorrelated': _dot(w_t, shifted) - 1,
                           'largest_sample': shifted[k] / g[k] - 1})
        out['relative_bias_from_phase_error'] = biases
        out['phase_convention'] = ('phase error dt > 0: the pulse started dt earlier than the weights assume, so each '
                                   'sample lies dt later on the pulse')
    if amplitude is not None:
        a = _num(amplitude, 'amplitude')
        gp = [a * pulse_derivative(t, n, tau) for t in times]
        cols = [g, gp]
        rinv_cols = [_solve_vec(cov, c) for c in cols]
        f = [[_dot(cols[i], rinv_cols[j]) for j in range(2)] for i in range(2)]
        det = f[0][0] * f[1][1] - f[0][1] * f[1][0]
        if det <= 1e-300 * max(abs(f[0][0] * f[1][1]), 1e-300):
            out['validity'].append('amplitude and time are not separable with these samples (singular Fisher '
                                   'matrix); add samples on the rising edge')
        else:
            out['amplitude_and_time_fit'] = {
                'amplitude': a, 'sigma_amplitude': math.sqrt(f[1][1] / det), 'sigma_time_ns': math.sqrt(f[0][0] / det),
                'correlation': -f[0][1] / math.sqrt(f[0][0] * f[1][1]),
                'note': 'linearized (Fisher) errors of a joint amplitude and time fit at the true phase'}
            if a / math.sqrt(var) < 10:
                out['validity'].append('amplitude below 10 times the noise: a fit with free time follows the noise and '
                                       'is biased upward; the linearized time error is optimistic')
    if info.get('min_pivot_ratio') is not None and info['min_pivot_ratio'] < 1e-10:
        out['validity'].append('noise covariance nearly singular (rho close to 1 or samples much closer than the '
                               'correlation time): weights are unstable against small changes of the covariance')
    if g[0] > 0.5 and len(g) > 1:
        out['validity'].append('the first sample is above half the peak: no pre-sample constrains the baseline')
    return out


# ---------------------------------------------------------------- Landau distribution

LANDAU_MPV = -0.22278298273298675  # most probable lambda of the standard Landau phi(lambda) (Kolbig convention)
_LN_V0 = math.log(2 / math.pi) - 1.0  # ln V(-pi/2) in the Zolotarev integral below


def _ln_v(theta):
    a = math.pi / 2 + theta
    return math.log(2 / math.pi) + math.log(a) - math.log(math.cos(theta)) + a * math.tan(theta)


def _adaptive_simpson(f, a, b, tol, pieces=16, depth=50):
    def rec(a, b, fa, fm, fb, whole, tol, depth):
        m = (a + b) / 2
        lm, rm = (a + m) / 2, (m + b) / 2
        flm, frm = f(lm), f(rm)
        left = (m - a) / 6 * (fa + 4 * flm + fm)
        right = (b - m) / 6 * (fm + 4 * frm + fb)
        if depth <= 0 or abs(left + right - whole) <= 15 * tol:
            return left + right + (left + right - whole) / 15
        return rec(a, m, fa, flm, fm, left, tol / 2, depth - 1) + rec(m, b, fm, frm, fb, right, tol / 2, depth - 1)
    if b <= a:
        return 0.0
    h = (b - a) / pieces
    total = 0.0
    for i in range(pieces):
        x0, x1 = a + i * h, a + (i + 1) * h
        xm = (x0 + x1) / 2
        f0, fm, f1 = f(x0), f(xm), f(x1)
        total += rec(x0, x1, f0, fm, f1, h / 6 * (f0 + 4 * fm + f1), tol / pieces, depth)
    return total


def _zolotarev(lam, density):
    """Standard Landau density or distribution function at lambda (Kolbig's phi; MPV at LANDAU_MPV).

    The Landau distribution is the stable law alpha = 1, beta = 1 (Nolan's S1) with scale pi/2 and location 0, so
    lambda = (pi/2) z + ln(pi/2) with z standard S1(1, 1, 1, 0); Nolan's (1997) integrals for z, split at the peak of
    the integrand, are smooth on (-pi/2, pi/2)."""
    z = (lam - math.log(math.pi / 2)) / (math.pi / 2)
    shift = -math.pi * z / 2

    def le(theta):
        return shift + (_LN_V0 if theta <= -math.pi / 2 else _ln_v(theta))

    def f(theta):
        if theta >= math.pi / 2:
            return 0.0
        e = le(theta)
        if e > 6:
            return 0.0
        return math.exp(e - math.exp(e)) if density else math.exp(-math.exp(e))
    lo, hi = -math.pi / 2, math.pi / 2
    if le(lo) < 0:
        for _ in range(200):
            mid = (lo + hi) / 2
            if le(mid) < 0:
                lo = mid
            else:
                hi = mid
        split = (lo + hi) / 2
    else:
        split = -math.pi / 2
    total = _adaptive_simpson(f, -math.pi / 2, split, 1e-12) + _adaptive_simpson(f, split, math.pi / 2, 1e-12)
    return total / math.pi if not density else 0.5 * total / (math.pi / 2)


def landau_pdf(lam):
    """phi(lambda) = (1/pi) int_0^inf exp(-t ln t - lambda t) sin(pi t) dt."""
    lam = _num(lam, 'lambda', positive=False)
    if lam < -8:
        return 0.0
    return _zolotarev(lam, True)


def landau_cdf(lam):
    """int_-inf^lambda phi."""
    lam = _num(lam, 'lambda', positive=False)
    if lam < -8:
        return 0.0
    return min(1.0, max(0.0, _zolotarev(lam, False)))


# ---------------------------------------------------------------- hit efficiency and noise occupancy

def _gauss_expect(f, mean, sigma, points=160, span=9.0):
    """E[f(X)] for X ~ N(mean, sigma^2), Simpson over mean +- span sigma."""
    m = points + points % 2
    h = 2 * span / m
    total = 0.0
    for i in range(m + 1):
        u = -span + i * h
        wgt = 1 if i in (0, m) else (4 if i % 2 else 2)
        total += wgt * f(mean + sigma * u) * math.exp(-u * u / 2)
    return total * h / 3 / math.sqrt(2 * math.pi)


def hit_efficiency(thresholds, noise, signal_model='landau', mpv=None, xi=None, mean=None, sigma_signal=None,
                   signal_fraction=1.0, threshold_dispersion=0.0, peaking_ns=None, order=2, noise_type='series',
                   series_fraction=None, window_ns=None, min_efficiency=None, max_occupancy=None):
    """Hit efficiency and noise occupancy versus threshold: the operating window of a binary or zero-suppressed
    channel.

    Efficiency: P(f Q + noise + threshold offset > T) for a Landau (MPV, xi) or Gaussian signal Q on the channel
    (fraction f of the deposit), noise sigma and a Gaussian channel-to-channel threshold spread, averaged over
    channels. Occupancy: the probability that noise alone is above threshold at one sampling instant, and the
    expected noise up-crossings in a window (Rice, CR-(RC)^n), both averaged over the threshold spread.
    """
    if not thresholds:
        raise ValueError('give at least one threshold')
    sn = _num(noise, 'noise sigma')
    sthr = _num(threshold_dispersion, 'threshold dispersion', allow_zero=True)
    frac = _num(signal_fraction, 'signal fraction')
    if frac > 1:
        raise ValueError('signal fraction must be at most 1')
    s_eff = math.hypot(sn, sthr)
    if signal_model == 'landau':
        if mpv is None or xi is None:
            raise ValueError('the Landau signal needs --mpv and --xi')
        q_mp = _num(mpv, 'most probable signal') * frac
        width = _num(xi, 'Landau width xi') * frac

        cache = {}

        def cdf(q):
            lam = (q - q_mp) / width + LANDAU_MPV
            key = round(lam, 6)
            if key not in cache:
                cache[key] = landau_cdf(lam)
            return cache[key]

        def ineff(t):
            return _gauss_expect(cdf, t, s_eff)
        model = {'model': 'landau', 'mpv_on_channel': q_mp, 'xi_on_channel': width}
    elif signal_model == 'gauss':
        if mean is None or sigma_signal is None:
            raise ValueError('the Gaussian signal needs --mean and --sigma-signal')
        mu = _num(mean, 'mean signal') * frac
        ss = _num(sigma_signal, 'signal sigma', allow_zero=True) * frac
        tot = math.hypot(ss, s_eff)

        def ineff(t):
            return _phi((t - mu) / tot)
        model = {'model': 'gauss', 'mean_on_channel': mu, 'sigma_on_channel': ss}
    else:
        raise ValueError("signal model must be 'landau' or 'gauss'")
    nu0 = None
    if peaking_ns is not None:
        rate = noise_rate(0.0, peaking_ns, order, noise_type, series_fraction)
        nu0 = rate['nu0_hz']
    if window_ns is not None:
        window = _num(window_ns, 'window') * 1e-9
        if nu0 is None:
            raise ValueError('noise crossings in a window need --peaking (and --order, --noise-type)')
    rows = []
    for t in thresholds:
        thr = _num(t, 'threshold', positive=False)
        eff = 1 - ineff(thr)
        s2 = sn * sn + sthr * sthr
        row = {'threshold': thr, 'threshold_over_noise': thr / sn, 'efficiency': eff, 'inefficiency': 1 - eff,
               'noise_probability_above_at_sample': _phi(-thr / math.sqrt(s2))}
        if nu0 is not None:
            mean_rate = nu0 * sn / math.sqrt(s2) * math.exp(-thr * thr / (2 * s2))
            row['noise_crossing_rate_hz'] = mean_rate
            if window_ns is not None:
                row['noise_crossings_per_window'] = mean_rate * window
                row['noise_occupancy_upper_bound'] = min(1.0, row['noise_probability_above_at_sample']
                                                         + mean_rate * window)
        rows.append(row)
    out = {'signal': model, 'noise_sigma': sn, 'threshold_dispersion': sthr, 'sigma_for_efficiency': s_eff,
           'nu0_hz': nu0, 'thresholds': rows,
           'assumptions': ['signal and noise independent and additive; Gaussian noise and Gaussian threshold spread '
                           '(efficiency and occupancy are channel averages); a Landau signal has no Bichsel '
                           'broadening (thin silicon is wider than Landau: give the measured width or fit the MPV '
                           'and xi to data); noise crossings by the Rice formula for white noise through '
                           'CR-(RC)^n; the occupancy upper bound adds the probability of starting above threshold '
                           'to the expected crossings'],
           'validity': []}
    if min_efficiency is not None or max_occupancy is not None:
        ok = []
        for row in rows:
            good = True
            if min_efficiency is not None and row['efficiency'] < min_efficiency:
                good = False
            if max_occupancy is not None:
                occ = row.get('noise_occupancy_upper_bound', row['noise_probability_above_at_sample'])
                if occ > max_occupancy:
                    good = False
            row['in_window'] = good
            if good:
                ok.append(row['threshold'])
        out['operating_window'] = ({'lowest_threshold': min(ok), 'highest_threshold': max(ok),
                                    'thresholds_in_window': len(ok)} if ok else None)
        if not ok:
            out['validity'].append('no scanned threshold meets both targets: the operating window is closed '
                                   '(raise the signal on the channel or lower the noise)')
        out['occupancy_measure'] = ('noise_occupancy_upper_bound' if window_ns is not None
                                    else 'noise_probability_above_at_sample')
    low = [r['threshold_over_noise'] for r in rows if r['threshold_over_noise'] < 3]
    high = [r['threshold_over_noise'] for r in rows if r['threshold_over_noise'] > 6]
    if low:
        out['validity'].append('thresholds below 3 noise sigma: noise crossings overlap and the Rice count '
                               'overstates separate noise hits')
    if high:
        out['validity'].append('thresholds above 6 noise sigma: the noise occupancy is set by non-Gaussian tails '
                               '(pickup, random telegraph signals); measure it')
    if frac < 1:
        out['validity'].append('signal fraction below 1 (charge sharing): efficiency at the cell edge, not '
                               'averaged over the track position')
    return out


# ---------------------------------------------------------------- waveform toy

def _poisson(rng, mean):
    if mean <= 0:
        return 0
    if mean > 50:
        return max(0, int(round(rng.gauss(mean, math.sqrt(mean)))))
    limit, k, p = math.exp(-mean), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def waveform_toy(order, peaking_ns, period_ns, samples, first_offset_ns, amplitude, events=20000, seed=1,
                 rho=0.0, phase_jitter_ns=0.0, pileup_rate_hz=0.0, pileup_mean_amp=0.0,
                 pileup_amplitudes='fixed', adc_lsb=None, adc_bits=12, pedestal=5.0, constraints=()):
    """Seeded toy of a sampled readout: pulses, correlated noise, Poisson pileup, phase jitter and an ADC, then
    reconstruction with the largest sample, the uncorrelated template fit and two optimal filters (weights from
    electronic noise only, and matched to electronic plus pileup noise). Reports the bias and resolution of each
    against the analytic prediction (closure).

    Units: amplitudes, noise, pedestal and ADC bin in units of the per-sample electronic noise sigma.
    """
    import random
    n = _order(order)
    tp = _num(peaking_ns, 'peaking time')
    tau = tp / n
    times = _sample_times(tp, period_ns, samples, first_offset_ns)
    amp = _num(amplitude, 'amplitude')
    if isinstance(events, bool) or not isinstance(events, int) or not 100 <= events <= 200000:
        raise ValueError('events must be an integer from 100 to 200000')
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('seed must be a non-negative integer')
    r = _check_rho(rho)
    jitter = _num(phase_jitter_ns, 'phase jitter', allow_zero=True)
    nu = _num(pileup_rate_hz, 'pileup rate', allow_zero=True)
    a_mean = _num(pileup_mean_amp, 'pileup mean amplitude', allow_zero=True)
    if pileup_amplitudes not in ('fixed', 'exponential'):
        raise ValueError("pileup amplitudes must be 'fixed' or 'exponential'")
    a2 = a_mean ** 2 * (2 if pileup_amplitudes == 'exponential' else 1)
    lsb = None if adc_lsb is None else _num(adc_lsb, 'ADC bin')
    if isinstance(adc_bits, bool) or not isinstance(adc_bits, int) or not 4 <= adc_bits <= 24:
        raise ValueError('ADC bits must be an integer from 4 to 24')
    ped = _num(pedestal, 'pedestal', positive=False)
    g = [pulse(t, n, tau) for t in times]
    if max(g) <= 0:
        raise ValueError('every sample is before the pulse starts: move the first sample later')
    cov_e = _noise_covariance(times, n, tau, r, 0.0, 0.0)
    cov_t = _noise_covariance(times, n, tau, r, nu, math.sqrt(a2))
    extra = _constraint_vectors(list(constraints), times, n, tau)
    if len(extra) + 1 > len(times):
        raise ValueError('more constraints than samples')
    w_e, _ = _filter_weights(g, cov_e, extra=extra)
    w_m, _ = _filter_weights(g, cov_t, extra=extra)
    gg = _dot(g, g)
    w_t = [x / gg for x in g]
    k = max(range(len(g)), key=lambda i: g[i])
    w_k = [0.0] * len(g)
    w_k[k] = 1 / g[k]
    estimators = {'largest_sample': w_k, 'template_uncorrelated': w_t, 'optimal_electronic': w_e,
                  'optimal_matched': w_m}
    pile_mean = nu * 1e-9 * a_mean * shaper_integrals(n, tau)['int_g']  # stationary mean offset per sample
    support = _support_ns(n, tau)
    t_lo, t_hi = times[0] - support, times[-1]
    span_s = (t_hi - t_lo) * 1e-9
    top = 2 ** adc_bits - 1
    rng = random.Random(seed)
    sq = math.sqrt(1 - r * r)
    sums = {name: [0.0, 0.0, 0.0, 0.0] for name in estimators}  # moments of (estimate - amplitude)
    saturated = 0
    for _ in range(events):
        d = rng.gauss(0.0, jitter) if jitter > 0 else 0.0
        v = [amp * pulse(t + d, n, tau) for t in times]
        x = rng.gauss(0.0, 1.0)
        for i in range(len(v)):
            if i:
                x = r * x + sq * rng.gauss(0.0, 1.0)
            v[i] += x
        if nu > 0 and a_mean > 0:
            for _p in range(_poisson(rng, nu * span_s)):
                t0 = rng.uniform(t_lo, t_hi)
                a = rng.expovariate(1 / a_mean) if pileup_amplitudes == 'exponential' else a_mean
                for i, t in enumerate(times):
                    v[i] += a * pulse(t - t0, n, tau)
        if lsb is not None:
            sat = False
            for i in range(len(v)):
                code = math.floor((v[i] + ped) / lsb + 0.5)
                if code <= 0 or code >= top:
                    sat = True
                code = min(max(code, 0), top)
                v[i] = code * lsb - ped
            saturated += sat
        for name, w in estimators.items():
            e = _dot(w, v) - amp
            s = sums[name]
            e2 = e * e
            s[0] += e
            s[1] += e2
            s[2] += e2 * e
            s[3] += e2 * e2
    results = {}
    for name, w in estimators.items():
        s1, s2, s3, s4 = (x / events for x in sums[name])
        bias = s1
        var = max(s2 - s1 * s1, 0.0)
        sd = math.sqrt(var)
        mu4 = s4 - 4 * s1 * s3 + 6 * s1 * s1 * s2 - 3 * s1 ** 4  # central fourth moment
        # standard error of the sample sd from the fourth moment (exact to first order for any distribution;
        # pileup with exponential amplitudes is far from Gaussian)
        sd_err = math.sqrt(max(mu4 - var * var, 0.0) / events) / (2 * sd) if sd > 0 else 0.0
        bias_err = sd / math.sqrt(events)
        pred_sigma = math.sqrt(_dot(w, _matvec(cov_t, w)))
        pred_bias = pile_mean * sum(w)
        results[name] = {
            'mean': amp + bias, 'bias': bias, 'relative_bias': bias / amp, 'sigma': sd,
            'sigma_mc_error': sd_err, 'bias_mc_error': bias_err,
            'predicted_sigma': pred_sigma, 'predicted_bias': pred_bias,
            'closure_z_bias': (bias - pred_bias) / bias_err if bias_err > 0 else None,
            'closure_z_sigma': (sd - pred_sigma) / sd_err if sd_err > 0 else None}
    validity = []
    ideal = jitter == 0 and lsb is None
    if not ideal:
        validity.append('phase jitter or an ADC is on: the predictions cover noise and pileup only, so closure '
                        'z-scores measure the effect of jitter and quantization, not a failure')
    if saturated:
        validity.append(f'{saturated} events had a sample at the ADC limits (0 or full scale): raise the pedestal '
                        'or the number of bits, or treat saturation explicitly')
    if nu * tp * 1e-9 > 1:
        validity.append('more than one pileup pulse per peaking time: a multi-pulse fit is needed')
    return {'status_label': 'synthetic', 'seed': seed, 'events': events, 'amplitude': amp,
            'constraints': list(constraints),
            'sample_times_ns': times, 'pulse_samples': g, 'pileup_mean_offset_per_sample': pile_mean,
            'saturated_events': saturated, 'estimators': results,
            'assumptions': ['synthetic toy: CR-(RC)^n pulse with unit peak; stationary Gaussian electronic noise '
                            'with sample correlation rho^|i-j| (AR(1)); Poisson pileup in continuous time with '
                            'fixed or exponential amplitudes; Gaussian phase jitter; uniform ADC with a known '
                            'pedestal (no differential nonlinearity); no baseline correction, so the pileup mean '
                            'appears as a bias'],
            'validity': validity}


# ---------------------------------------------------------------- calibration: S-curves and threshold trim

def _scurve_terms(q, t, s):
    z = (q - t) / s
    p = min(max(_phi(z), 1e-15), 1 - 1e-15)
    dens = math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
    return p, (-dens / s, -dens * z / s)  # dp/dT, dp/ds


def _scurve_fisher(charges, injections, t, s):
    f = [[0.0, 0.0], [0.0, 0.0]]
    for q, n in zip(charges, injections):
        p, g = _scurve_terms(q, t, s)
        w = n / (p * (1 - p))
        for a in range(2):
            for b in range(2):
                f[a][b] += w * g[a] * g[b]
    return f


def _inv2(f):
    det = f[0][0] * f[1][1] - f[0][1] * f[1][0]
    if not det > 0:
        return None
    return [[f[1][1] / det, -f[0][1] / det], [-f[1][0] / det, f[0][0] / det]]


def _check_scan(charges, injections):
    if len(charges) < 3:
        raise ValueError('an S-curve needs at least 3 injected charges')
    if len(injections) != len(charges):
        raise ValueError('give one injection count per charge, or a single count for all')
    qs = [_num(q, 'injected charge', positive=False) for q in charges]
    if any(b <= a for a, b in zip(qs, qs[1:])):
        raise ValueError('injected charges must be strictly increasing')
    ns = []
    for n in injections:
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError('injection counts must be positive integers')
        ns.append(n)
    return qs, ns


def scurve_fit(charges, hits, injections):
    """Binomial maximum-likelihood fit of an S-curve, hits ~ Bin(N, Phi((Q - T)/sigma)): threshold T, noise sigma,
    their covariance (inverse Fisher matrix at the fit), and the deviance goodness of fit."""
    if len(injections) == 1:
        injections = list(injections) * len(charges)
    qs, ns = _check_scan(charges, injections)
    if len(hits) != len(qs):
        raise ValueError('give one hit count per injected charge')
    ks = []
    for k, n in zip(hits, ns):
        if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= n:
            raise ValueError('hit counts must be integers between 0 and the number of injections')
        ks.append(k)
    frac = [k / n for k, n in zip(ks, ns)]
    if max(frac) < 0.5 or min(frac) > 0.5:
        raise ValueError('the scan does not cross 50 %: extend the injected-charge range')
    # start: linear interpolation of the 50 % point; width from the 16-84 % span, else a tenth of the range
    t0 = next(qs[i] + (0.5 - frac[i]) * (qs[i + 1] - qs[i]) / (frac[i + 1] - frac[i])
              for i in range(len(qs) - 1) if frac[i] <= 0.5 <= frac[i + 1] and frac[i + 1] > frac[i])
    lo = [q for q, f in zip(qs, frac) if f <= 0.16]
    hi = [q for q, f in zip(qs, frac) if f >= 0.84]
    s0 = max((min(hi) - max(lo)) / 2 if lo and hi else (qs[-1] - qs[0]) / 10, (qs[-1] - qs[0]) * 1e-4)

    def loglik(t, s):
        total = 0.0
        for q, k, n in zip(qs, ks, ns):
            p = _scurve_terms(q, t, s)[0]
            total += k * math.log(p) + (n - k) * math.log(1 - p)
        return total

    t, s = t0, s0
    ll = loglik(t, s)
    converged = False
    for _ in range(200):
        u = [0.0, 0.0]
        for q, k, n in zip(qs, ks, ns):
            p, g = _scurve_terms(q, t, s)
            r = (k - n * p) / (p * (1 - p))
            u[0] += r * g[0]
            u[1] += r * g[1]
        cov = _inv2(_scurve_fisher(qs, ns, t, s))
        if cov is None:
            break
        dt = cov[0][0] * u[0] + cov[0][1] * u[1]
        ds = cov[1][0] * u[0] + cov[1][1] * u[1]
        step = 1.0
        while step > 1e-6:
            nt, ns_ = t + step * dt, s + step * ds
            if ns_ > 0:
                nll = loglik(nt, ns_)
                if nll >= ll - 1e-12:
                    break
            step /= 2
        else:
            break
        moved = abs(step * dt) + abs(step * ds)
        t, s, ll = nt, ns_, nll
        if moved < 1e-10 * (abs(t) + s):
            converged = True
            break
    cov = _inv2(_scurve_fisher(qs, ns, t, s))
    if cov is None:
        raise ValueError('the S-curve fit has a singular information matrix (no points in the transition)')
    deviance = 0.0
    for q, k, n in zip(qs, ks, ns):
        p = _scurve_terms(q, t, s)[0]
        if k > 0:
            deviance += 2 * k * math.log(k / (n * p))
        if k < n:
            deviance += 2 * (n - k) * math.log((n - k) / (n * (1 - p)))
    ndf = len(qs) - 2
    transition = sum(1 for f in frac if 0.05 < f < 0.95)
    out = {'threshold': t, 'noise': s, 'sigma_threshold': math.sqrt(cov[0][0]), 'sigma_noise': math.sqrt(cov[1][1]),
           'correlation': cov[0][1] / math.sqrt(cov[0][0] * cov[1][1]), 'converged': converged,
           'deviance': deviance, 'ndf': ndf,
           'p_value': chi2_sf(max(deviance, 0.0), ndf) if ndf > 0 else None,
           'points_in_transition': transition,
           'assumptions': ['hits binomial with a Gaussian-noise turn-on Phi((Q - T)/sigma); the fitted width is the '
                           'quadrature sum of the channel noise, the injection-amplitude noise and any threshold '
                           'jitter during the scan; the charge scale is that of the injection circuit (its '
                           'capacitor and pulser uncertainty is common to every channel it serves); deviance '
                           'approximately chi2(ndf) only when the expected counts are not small'],
           'validity': []}
    if not converged:
        out['validity'].append('the fit did not converge to the requested precision: inspect the scan')
    if transition < 2:
        out['validity'].append('fewer than 2 points between 5 % and 95 %: the noise is poorly constrained; use a '
                               'finer charge step (about sigma/2) around the threshold')
    if ndf > 0 and out['p_value'] is not None and out['p_value'] < 1e-3:
        out['validity'].append('poor fit (p < 1e-3): non-Gaussian noise, a drifting threshold, crosstalk or an '
                               'injection nonlinearity; do not quote sigma as the ENC')
    return out


def scurve_design(charges, injections, threshold, noise):
    """Expected errors of the S-curve fit for a scan design (Fisher information at an assumed threshold and noise)."""
    if len(injections) == 1:
        injections = list(injections) * len(charges)
    qs, ns = _check_scan(charges, injections)
    t = _num(threshold, 'assumed threshold', positive=False)
    s = _num(noise, 'assumed noise')
    cov = _inv2(_scurve_fisher(qs, ns, t, s))
    if cov is None:
        raise ValueError('the design has no information on the threshold and noise (no charges near threshold)')
    transition = sum(1 for q in qs if abs(q - t) < 2 * s)
    out = {'assumed_threshold': t, 'assumed_noise': s, 'expected_sigma_threshold': math.sqrt(cov[0][0]),
           'expected_sigma_noise': math.sqrt(cov[1][1]), 'expected_relative_sigma_noise': math.sqrt(cov[1][1]) / s,
           'charges_within_2_sigma': transition, 'total_injections': sum(ns),
           'assumptions': ['asymptotic (Fisher) errors of the binomial S-curve fit at the assumed values'],
           'validity': []}
    if transition < 3:
        out['validity'].append('fewer than 3 charges within 2 noise sigma of the threshold: errors are large and '
                               'the asymptotic approximation is poor')
    return out


def threshold_trim(spread, trim_bits, trim_step, dac_nonlinearity=0.0):
    """Threshold dispersion after per-channel trim: a Gaussian untrimmed spread, a trim DAC of 2^b codes of step D
    centred on the target. Channels inside the range keep a uniform residual (rms D/sqrt(12)); channels beyond
    it keep the excess. Exact for a Gaussian spread much wider than D (the residual is uniform over a code)."""
    s0 = _num(spread, 'untrimmed threshold spread')
    if isinstance(trim_bits, bool) or not isinstance(trim_bits, int) or not 1 <= trim_bits <= 16:
        raise ValueError('trim bits must be an integer from 1 to 16')
    step = _num(trim_step, 'trim step')
    dnl = _num(dac_nonlinearity, 'trim DAC nonlinearity', allow_zero=True)
    half = (2 ** trim_bits - 1) * step / 2  # the extreme codes correct offsets of +-half
    edge = half + step / 2  # beyond it the residual exceeds half a step
    a = edge / s0
    tail = 2 * _phi(-a)  # fraction of channels beyond the trim range
    dens = math.exp(-a * a / 2) / math.sqrt(2 * math.pi)
    # beyond the edge the residual is |x| - half = (|x| - edge) + step/2; with u = |x|/s0 - a > 0:
    # E[u^2] part (1 + a^2) Q(a) - a phi(a), E[u] part phi(a) - a Q(a), both per side
    e2 = (1 + a * a) * _phi(-a) - a * dens
    e1 = dens - a * _phi(-a)
    excess2 = 2 * (s0 * s0 * e2 + step * s0 * e1 + step * step / 4 * _phi(-a))
    resid2 = (1 - tail) * step * step / 12 + max(excess2, 0.0) + dnl * dnl
    out = {'untrimmed_spread': s0, 'trim_range_half_width': half, 'fraction_beyond_range': tail,
           'residual_dispersion': math.sqrt(resid2), 'quantization_part': step / math.sqrt(12),
           'assumptions': ['Gaussian untrimmed spread centred on the target; ideal trim codes plus an rms DAC '
                           'nonlinearity in quadrature; the residual of a trimmed channel uniform over one code'],
           'validity': []}
    if step > s0:
        out['validity'].append('trim step larger than the untrimmed spread: the uniform-residual approximation '
                               'fails; trimming may not help')
    if tail > 1e-3:
        out['validity'].append(f'{tail:.2%} of channels lie beyond the trim range: widen the range (more bits or a '
                               'larger step) or mask them; they dominate the noise occupancy')
    return out


# ---------------------------------------------------------------- cli

def _fail(message, kind='failed'):
    print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': kind, 'error': message}, indent=2))
    print(f'frontend_response.py: error: {message}', file=sys.stderr)
    return 1


def main():
    parser = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('enc', help='equivalent noise charge')
    p.add_argument('--capacitance', type=float, required=True, help='total input capacitance, pF')
    p.add_argument('--peaking', type=float, required=True, help='peaking time t_p, ns')
    p.add_argument('--order', type=int, default=1, help='shaper order n of CR-(RC)^n (default 1)')
    p.add_argument('--en', type=float, default=0.0, help='series white noise, nV/sqrt(Hz)')
    p.add_argument('--leakage', type=float, default=0.0, help='leakage current, nA')
    p.add_argument('--rp', type=float, help='parallel (bias/feedback) resistance, ohm')
    p.add_argument('--af', type=float, default=0.0, help='1/f coefficient A_f, V^2 (density A_f/f)')
    p.add_argument('--temperature', type=float, default=300.0, help='K, for the R_p thermal noise (default 300)')

    p = sub.add_parser('noise-rate', help='noise-hit rate above a threshold (Rice)')
    p.add_argument('--threshold', type=float, required=True, help='threshold in units of the noise sigma')
    p.add_argument('--peaking', type=float, required=True, help='peaking time, ns')
    p.add_argument('--order', type=int, default=2, help='shaper order (default 2)')
    p.add_argument('--noise-type', choices=['series', 'parallel', 'mixed'], default='series', dest='noise_type')
    p.add_argument('--series-fraction', type=float, dest='series_fraction',
                   help='mixed only: fraction of the noise variance that is series noise')
    p.add_argument('--channels', type=int, default=1, help='number of channels (default 1)')
    p.add_argument('--window', type=float, help='readout or integration window, ns')

    p = sub.add_parser('timing', help='jitter, walk, CFD, TDC')
    p.add_argument('--rise', type=float, required=True, help='rise time, ns')
    p.add_argument('--snr', type=float, required=True, help='signal-to-noise ratio (amplitude/noise sigma)')
    p.add_argument('--threshold', type=float, help='leading-edge threshold, same units as --amplitudes')
    p.add_argument('--amplitudes', type=float, nargs=2, help='two amplitudes to compare for walk')
    p.add_argument('--cfd-fraction', type=float, dest='cfd_fraction')
    p.add_argument('--cfd-delay', type=float, dest='cfd_delay', help='CFD delay, ns')
    p.add_argument('--tdc-lsb', type=float, dest='tdc_lsb', help='TDC bin, ps')

    p = sub.add_parser('quantize', help='quantization error and residual bias')
    p.add_argument('--noise-lsb', type=float, required=True, dest='noise_lsb', help='noise sigma in LSB')

    p = sub.add_parser('pileup', help='Campbell mean and sigma of shaped pileup')
    p.add_argument('--rate', type=float, required=True, help='pulse rate per channel, Hz')
    p.add_argument('--mean-amp', type=float, required=True, dest='mean_amp', help='mean pulse amplitude <a>')
    p.add_argument('--second-moment', type=float, dest='second_moment',
                   help='<a^2> (default <a>^2, i.e. fixed amplitude)')
    p.add_argument('--peaking', type=float, required=True, help='peaking time, ns')
    p.add_argument('--order', type=int, default=1)
    p.add_argument('--bipolar', action='store_true', help='bipolar shaping (tau dg/dt)')

    p = sub.add_parser('sipm', help='SiPM saturation and correlated noise')
    p.add_argument('--cells', type=int, required=True, help='number of cells (an integer)')
    p.add_argument('--npe', type=float, required=True, help='expected primary photoelectrons (before saturation)')
    p.add_argument('--crosstalk', type=float, default=0.0,
                   help='crosstalk probability P_ct (an avalanche triggers at least one more), as on a datasheet')
    p.add_argument('--dcr', type=float, default=0.0, help='dark count rate, Hz')
    p.add_argument('--gate', type=float, default=0.0, help='integration gate, ns')

    p = sub.add_parser('ballistic', help='ballistic deficit')
    p.add_argument('--collection', type=float, required=True, help='charge-collection time T_c, ns')
    p.add_argument('--peaking', type=float, required=True, help='peaking time, ns')
    p.add_argument('--order', type=int, default=1)

    p = sub.add_parser('deadtime', help='dead time and live fraction')
    p.add_argument('--dead-time', type=float, required=True, dest='dead_time', help='ns')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--rate', type=float, help='true rate, Hz')
    g.add_argument('--measured', type=float, help='measured rate, Hz')
    p.add_argument('--model', choices=['nonparalyzable', 'paralyzable'], default='nonparalyzable')

    p = sub.add_parser('leakage-scale', help='silicon leakage current at another temperature')
    p.add_argument('--current', type=float, required=True, help='leakage current at --from-celsius, nA')
    p.add_argument('--from-celsius', type=float, required=True, dest='from_celsius')
    p.add_argument('--to-celsius', type=float, required=True, dest='to_celsius')
    p.add_argument('--e-eff', type=float, default=E_EFF_SI, dest='e_eff',
                   help=f'effective band gap in eV (default {E_EFF_SI})')

    p = sub.add_parser('cluster-noise', help='noise of a sum of correlated channels')
    p.add_argument('--channels', type=int, required=True)
    p.add_argument('--sigma', type=float, required=True)
    p.add_argument('--rho', type=float, required=True, help='pairwise correlation coefficient')

    def sampling_args(p):
        p.add_argument('--order', type=int, default=1, help='shaper order n of CR-(RC)^n (default 1)')
        p.add_argument('--peaking', type=float, required=True, help='peaking time t_p, ns')
        p.add_argument('--period', type=float, required=True, help='sampling period, ns')
        p.add_argument('--samples', type=int, required=True, help='number of samples (1 to 64)')
        p.add_argument('--first-offset', type=float, required=True, dest='first_offset',
                       help='time of the first sample relative to the pulse peak, ns (negative: before the peak)')
        p.add_argument('--rho', type=float, default=0.0,
                       help='correlation of the electronic noise between neighbouring samples (rho^|i-j|; default 0)')
        p.add_argument('--pileup-rate', type=float, default=0.0, dest='pileup_rate',
                       help='pileup pulse rate per channel, Hz (default 0)')
        p.add_argument('--constraints', nargs='+', choices=['phase', 'baseline'], default=[],
                       help='optimal-filter constraints: phase (w . g\' = 0), baseline (sum w = 0)')

    p = sub.add_parser('optimal-filter', help='optimal-filter weights, variances, phase and baseline bias')
    sampling_args(p)
    p.add_argument('--pileup-rms', type=float, default=0.0, dest='pileup_rms',
                   help='rms pileup amplitude sqrt(<a^2>), in units of the per-sample electronic noise')
    p.add_argument('--amplitude', type=float,
                   help='pulse amplitude in noise units, for the joint amplitude and time fit errors')
    p.add_argument('--phase-errors', type=float, nargs='+', default=[], dest='phase_errors',
                   help='phase errors to evaluate, ns (positive: the pulse started earlier than assumed)')

    p = sub.add_parser('hit-efficiency', help='hit efficiency and noise occupancy versus threshold')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--thresholds', type=float, nargs='+', help='thresholds, in the unit of the charges')
    g.add_argument('--scan', type=float, nargs=3, metavar=('LOW', 'HIGH', 'STEPS'),
                   help='scan STEPS thresholds evenly from LOW to HIGH')
    p.add_argument('--noise', type=float, required=True, help='noise sigma (ENC), in the unit of the charges')
    p.add_argument('--signal-model', choices=['landau', 'gauss'], default='landau', dest='signal_model')
    p.add_argument('--mpv', type=float, help='landau: most probable deposited charge')
    p.add_argument('--xi', type=float, help='landau: width parameter xi (FWHM is about 4.02 xi)')
    p.add_argument('--mean', type=float, help='gauss: mean signal')
    p.add_argument('--sigma-signal', type=float, dest='sigma_signal', help='gauss: signal sigma')
    p.add_argument('--signal-fraction', type=float, default=1.0, dest='signal_fraction',
                   help='fraction of the deposit on this channel (charge sharing, trapping; default 1)')
    p.add_argument('--threshold-dispersion', type=float, default=0.0, dest='threshold_dispersion',
                   help='channel-to-channel threshold sigma after trim, same unit')
    p.add_argument('--peaking', type=float, help='peaking time, ns (for noise crossings)')
    p.add_argument('--order', type=int, default=2, help='shaper order (default 2)')
    p.add_argument('--noise-type', choices=['series', 'parallel', 'mixed'], default='series', dest='noise_type')
    p.add_argument('--series-fraction', type=float, dest='series_fraction')
    p.add_argument('--window', type=float, help='readout or integration window, ns')
    p.add_argument('--min-efficiency', type=float, dest='min_efficiency', help='efficiency target, e.g. 0.99')
    p.add_argument('--max-occupancy', type=float, dest='max_occupancy',
                   help='noise occupancy target per channel and window (or per sample without --window)')

    p = sub.add_parser('waveform-toy', help='seeded synthetic sampled readout and its reconstruction')
    sampling_args(p)
    p.add_argument('--amplitude', type=float, required=True, help='pulse amplitude in noise units')
    p.add_argument('--events', type=int, default=20000, help='events (100 to 200000; default 20000)')
    p.add_argument('--seed', type=int, default=1, help='random seed (default 1)')
    p.add_argument('--phase-jitter', type=float, default=0.0, dest='phase_jitter', help='Gaussian phase sigma, ns')
    p.add_argument('--pileup-mean-amp', type=float, default=0.0, dest='pileup_mean_amp',
                   help='mean pileup amplitude, noise units')
    p.add_argument('--pileup-amplitudes', choices=['fixed', 'exponential'], default='fixed',
                   dest='pileup_amplitudes')
    p.add_argument('--adc-lsb', type=float, dest='adc_lsb', help='ADC bin in noise units (default: no ADC)')
    p.add_argument('--adc-bits', type=int, default=12, dest='adc_bits', help='ADC bits (default 12)')
    p.add_argument('--pedestal', type=float, default=5.0, help='pedestal in noise units (default 5)')

    p = sub.add_parser('s-curve', help='S-curve fit of a threshold scan, or the errors of a scan design')
    p.add_argument('--charges', type=float, nargs='+', required=True, help='injected charges, increasing')
    p.add_argument('--injections', type=int, nargs='+', required=True,
                   help='injections per charge (one value for all, or one per charge)')
    p.add_argument('--hits', type=int, nargs='+', help='hits per charge (fit mode)')
    p.add_argument('--design-threshold', type=float, dest='design_threshold',
                   help='design mode: assumed threshold, same unit as the charges')
    p.add_argument('--design-noise', type=float, dest='design_noise', help='design mode: assumed noise sigma')

    p = sub.add_parser('threshold-trim', help='threshold dispersion after per-channel trim')
    p.add_argument('--spread', type=float, required=True, help='untrimmed threshold spread (Gaussian sigma)')
    p.add_argument('--trim-bits', type=int, required=True, dest='trim_bits', help='trim DAC bits')
    p.add_argument('--trim-step', type=float, required=True, dest='trim_step', help='trim DAC step, same unit')
    p.add_argument('--dac-nonlinearity', type=float, default=0.0, dest='dac_nonlinearity',
                   help='rms trim DAC nonlinearity, same unit (default 0)')

    # one unwrapped usage line, so a reader of the first line (contracts/tool_contract.py) sees every subcommand
    parser.usage = '%(prog)s [-h] {' + ','.join(sub.choices) + '} ...'
    for p in sub.choices.values():
        p.add_argument('--status', choices=STATUSES, default='unvalidated',
                       help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()
    try:
        if args.command == 'enc':
            result = enc(args.capacitance, args.peaking, args.order, args.en, args.leakage, args.rp, args.af,
                         args.temperature)
        elif args.command == 'noise-rate':
            result = noise_rate(args.threshold, args.peaking, args.order, args.noise_type, args.series_fraction,
                                args.channels, args.window)
        elif args.command == 'timing':
            if (args.threshold is None) != (args.amplitudes is None):
                raise ValueError('walk needs both --threshold and --amplitudes')
            if (args.cfd_fraction is None) != (args.cfd_delay is None):
                raise ValueError('CFD needs both --cfd-fraction and --cfd-delay')
            result = timing(args.rise, args.snr, args.threshold, args.amplitudes, args.cfd_fraction,
                            args.cfd_delay, args.tdc_lsb)
        elif args.command == 'quantize':
            result = quantize(args.noise_lsb)
        elif args.command == 'pileup':
            second = args.second_moment if args.second_moment is not None else args.mean_amp ** 2
            result = pileup(args.rate, args.mean_amp, second, args.peaking, args.order, args.bipolar)
        elif args.command == 'sipm':
            result = sipm(args.cells, args.npe, args.crosstalk, args.dcr, args.gate)
        elif args.command == 'ballistic':
            result = ballistic(args.collection, args.peaking, args.order)
        elif args.command == 'deadtime':
            result = deadtime(args.dead_time, args.rate, args.measured, args.model)
        elif args.command == 'leakage-scale':
            current = leakage_scale(args.current, args.from_celsius, args.to_celsius, args.e_eff)
            result = {'leakage_na': current, 'scale_factor': current / args.current if args.current else None,
                      'from_celsius': args.from_celsius, 'to_celsius': args.to_celsius, 'e_eff_ev': args.e_eff,
                      'assumptions': ['bulk generation current, I ~ T^2 exp(-E_eff / 2kT), E_eff for silicon; '
                                      'surface and breakdown currents do not scale this way'],
                      'validity': []}
        elif args.command == 'optimal-filter':
            result = optimal_filter(args.order, args.peaking, args.period, args.samples, args.first_offset, args.rho,
                                    args.pileup_rate, args.pileup_rms, args.amplitude, args.phase_errors,
                                    args.constraints)
        elif args.command == 'hit-efficiency':
            if args.scan is not None:
                low, high, steps = args.scan
                if steps != int(steps) or not 2 <= steps <= 400 or high <= low:
                    raise ValueError('--scan needs LOW < HIGH and an integer STEPS from 2 to 400')
                thresholds = [low + (high - low) * i / (int(steps) - 1) for i in range(int(steps))]
            else:
                thresholds = args.thresholds
            result = hit_efficiency(thresholds, args.noise, args.signal_model, args.mpv, args.xi, args.mean,
                                    args.sigma_signal, args.signal_fraction, args.threshold_dispersion, args.peaking,
                                    args.order, args.noise_type, args.series_fraction, args.window,
                                    args.min_efficiency, args.max_occupancy)
        elif args.command == 'waveform-toy':
            result = waveform_toy(args.order, args.peaking, args.period, args.samples, args.first_offset,
                                  args.amplitude, args.events, args.seed, args.rho, args.phase_jitter,
                                  args.pileup_rate, args.pileup_mean_amp, args.pileup_amplitudes, args.adc_lsb,
                                  args.adc_bits, args.pedestal, args.constraints)
        elif args.command == 's-curve':
            design = args.design_threshold is not None or args.design_noise is not None
            if design == (args.hits is not None):
                raise ValueError('give --hits (fit) or both --design-threshold and --design-noise (design)')
            if design:
                if args.design_threshold is None or args.design_noise is None:
                    raise ValueError('design mode needs both --design-threshold and --design-noise')
                result = scurve_design(args.charges, args.injections, args.design_threshold, args.design_noise)
                result['mode'] = 'design'
            else:
                result = scurve_fit(args.charges, args.hits, args.injections)
                result['mode'] = 'fit'
        elif args.command == 'threshold-trim':
            result = threshold_trim(args.spread, args.trim_bits, args.trim_step, args.dac_nonlinearity)
        else:
            result = cluster_noise(args.channels, args.sigma, args.rho)
    except (OverflowError, ZeroDivisionError) as exc:
        return _fail(f'{exc} (result not finite: check the input range)')
    except ValueError as exc:
        parser.error(str(exc))
    try:
        text = json.dumps({'status': args.status, 'command': args.command, **result}, indent=2, allow_nan=False)
    except ValueError:
        return _fail('result not finite: check the input range')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
