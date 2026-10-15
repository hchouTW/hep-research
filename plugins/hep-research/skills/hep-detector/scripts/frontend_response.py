#!/usr/bin/env python3
"""Front-end electronics response: noise, thresholds, timing, quantization, pileup, SiPM, dead time.

Purpose: put numbers on how readout electronics shapes a detector's response - the
equivalent noise charge of a charge-sensitive amplifier and CR-(RC)^n shaper and its
optimum shaping time, the noise-hit rate above a threshold, timing jitter and walk,
quantization error, the pileup (Campbell) mean and spread of a shaped signal, SiPM
saturation and correlated noise, ballistic deficit, dead time, and the noise of a sum
of correlated channels. Each result carries its assumptions and a validity list; a
non-empty validity list means the input is outside the range where the relation holds.

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

Conventions: the shaper's response to a unit input charge is g(t) = (t/tau)^n exp(-t/tau),
normalized to peak 1, with peaking time t_p = n tau. The bipolar shape of the pileup
subcommand is tau dg/dt, which is not peak-normalized; --mean-amp is the amplitude of the
unipolar pulse. Noise densities are one-sided:
i_n^2 = 2 q I_leak (+ 4kT/R_p), e_n^2 in V^2/Hz, 1/f density A_f/f in V^2/Hz. Then
ENC^2 = (i_n^2/2) int g^2 + C^2 (e_n^2/2) int g'^2 + C^2 A_f int |G'(f)|^2/f df, all in
closed form for CR-(RC)^n. Units: capacitance pF, e_n nV/sqrt(Hz), leakage nA, times ns,
rates Hz unless the option says otherwise. Standard library only.
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

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


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
        else:
            result = cluster_noise(args.channels, args.sigma, args.rho)
        text = json.dumps({'status': args.status, 'command': args.command, **result}, indent=2, allow_nan=False)
    except (OverflowError, ZeroDivisionError) as exc:
        return _fail(f'{exc} (result not finite: check the input range)')
    except ValueError as exc:
        if 'JSON' in str(exc):
            return _fail('result not finite: check the input range')
        parser.error(str(exc))
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
