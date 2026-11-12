"""Agreement between two measurements of the same thing: Bland-Altman and the intraclass correlation.

Used for the study's reproducibility: a participant's resting velocity on two
days (`capillary.aims`), and the same recording placed twice
(`analysis/placement_repeat/`).

- **Bland-Altman** (Bland & Altman, Lancet 1986;327:307-10, and Stat Methods
  Med Res 1999;8:135-60): the mean difference (bias) and the 95% limits of
  agreement, bias +- 1.96 SD of the differences, each with an approximate
  confidence interval (standard error sqrt(s^2/n) for the bias and
  sqrt(3 s^2/n) for a limit). A difference that grows with the size of the
  measurement shows as a slope of the differences on the means (proportional
  bias). Velocities span an order of magnitude, so the same is also done on a
  log scale, where bias and limits become ratios.
- **Intraclass correlation** (McGraw & Wong, Psychol Methods 1996;1:30-46),
  two-way model, single measurements: absolute agreement ICC(A,1), which is
  Shrout & Fleiss's ICC(2,1), and consistency ICC(C,1), their ICC(3,1), with
  the F-distribution confidence intervals of McGraw & Wong.

Pairs with a missing value (NaN) are left out everywhere. Nothing here imports
a GUI toolkit.
"""

from __future__ import annotations

import math

import numpy as np

NAN = float('nan')
#: Limits of agreement are bias +- this many SD of the differences (95% of differences).
LOA_Z = 1.96


def _pairs(a, b) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if a.shape != b.shape:
        raise ValueError(f'paired measurements must have the same length, got {a.size} and {b.size}')
    keep = np.isfinite(a) & np.isfinite(b)
    return a[keep], b[keep]


def _t(confidence: float, df: float) -> float:
    from scipy import stats
    return float(stats.t.ppf(0.5 + confidence / 2, df))


# ------------------------------------------------------------------------- Bland-Altman

def bland_altman(a, b, confidence: float = 0.95) -> dict:
    """Agreement of paired measurements; differences are ``a - b``.

    Returns ``n``; ``bias`` with ``bias_ci_low/high``; ``sd`` of the
    differences; ``loa_low`` and ``loa_high`` (bias -+ 1.96 SD) each with
    ``_ci_low/_ci_high``; and the proportional bias, ``slope`` of the
    differences on the pair means with ``slope_ci_low/high``. NaN where there
    are too few pairs (2 for the bias and limits, 3 for the slope).
    """
    a, b = _pairs(a, b)
    n = int(a.size)
    keys = ('bias', 'bias_ci_low', 'bias_ci_high', 'sd', 'loa_low', 'loa_low_ci_low', 'loa_low_ci_high',
            'loa_high', 'loa_high_ci_low', 'loa_high_ci_high', 'slope', 'slope_ci_low', 'slope_ci_high')
    result = {'n': n, **{key: NAN for key in keys}}
    if n == 0:
        return result
    difference = a - b
    bias = float(difference.mean())
    result['bias'] = bias
    if n < 2:
        return result
    sd = float(difference.std(ddof=1))
    t = _t(confidence, n - 1)
    se_bias = sd / math.sqrt(n)
    se_limit = sd * math.sqrt(3.0 / n)
    low, high = bias - LOA_Z * sd, bias + LOA_Z * sd
    result.update(sd=sd, bias_ci_low=bias - t * se_bias, bias_ci_high=bias + t * se_bias,
                  loa_low=low, loa_low_ci_low=low - t * se_limit, loa_low_ci_high=low + t * se_limit,
                  loa_high=high, loa_high_ci_low=high - t * se_limit, loa_high_ci_high=high + t * se_limit)
    if n >= 3:
        mean = (a + b) / 2
        spread = float(np.sum((mean - mean.mean()) ** 2))
        if spread > 0:
            slope = float(np.sum((mean - mean.mean()) * (difference - bias)) / spread)
            residual = difference - bias - slope * (mean - mean.mean())
            se_slope = math.sqrt(float(np.sum(residual ** 2)) / (n - 2) / spread)
            t2 = _t(confidence, n - 2)
            result.update(slope=slope, slope_ci_low=slope - t2 * se_slope, slope_ci_high=slope + t2 * se_slope)
    return result


def bland_altman_ratio(a, b, confidence: float = 0.95) -> dict:
    """Bland-Altman on a log scale: how many times larger `a` is than `b`.

    Only pairs of the same sign (neither zero) count; their magnitudes are
    compared. Returns ``n``, the geometric mean ``ratio`` a/b with
    ``ratio_ci_low/high``, and the limits ``loa_low`` and ``loa_high`` as
    ratios (95% of pairs have a/b between them).
    """
    a, b = _pairs(a, b)
    same_sign = (a * b) > 0
    result = {'n': int(same_sign.sum()), 'ratio': NAN, 'ratio_ci_low': NAN, 'ratio_ci_high': NAN,
              'loa_low': NAN, 'loa_high': NAN}
    if not same_sign.any():
        return result
    stats = bland_altman(np.log(np.abs(a[same_sign])), np.log(np.abs(b[same_sign])), confidence)
    for key, source in (('ratio', 'bias'), ('ratio_ci_low', 'bias_ci_low'), ('ratio_ci_high', 'bias_ci_high'),
                        ('loa_low', 'loa_low'), ('loa_high', 'loa_high')):
        value = stats[source]
        result[key] = math.exp(value) if math.isfinite(value) else NAN
    return result


# ------------------------------------------------------------------ intraclass correlation

def icc(ratings, confidence: float = 0.95) -> dict:
    """Intraclass correlation of an (items x raters) table; items with a missing rating are left out.

    Returns ``n`` (items used), ``k`` (raters), ``agreement`` = ICC(A,1) and
    ``consistency`` = ICC(C,1), each with ``_ci_low/_ci_high`` (McGraw &
    Wong 1996, two-way model, single measurements).
    """
    x = np.asarray(ratings, dtype=float)
    if x.ndim != 2:
        raise ValueError('ratings must be a 2-D table: one row per item, one column per rater')
    x = x[np.all(np.isfinite(x), axis=1)]
    n, k = x.shape
    result = {'n': int(n), 'k': int(k)}
    for key in ('agreement', 'consistency'):
        result.update({key: NAN, f'{key}_ci_low': NAN, f'{key}_ci_high': NAN})
    if n < 2 or k < 2:
        return result
    from scipy import stats

    grand = float(x.mean())
    ss_rows = k * float(np.sum((x.mean(axis=1) - grand) ** 2))
    ss_columns = n * float(np.sum((x.mean(axis=0) - grand) ** 2))
    ss_error = float(np.sum((x - grand) ** 2)) - ss_rows - ss_columns
    ms_rows = ss_rows / (n - 1)
    ms_columns = ss_columns / (k - 1)
    ms_error = max(ss_error, 0.0) / ((n - 1) * (k - 1))
    alpha = 1.0 - confidence

    consistency_denominator = ms_rows + (k - 1) * ms_error
    if consistency_denominator > 0:
        result['consistency'] = (ms_rows - ms_error) / consistency_denominator
        if ms_error > 0:
            f0 = ms_rows / ms_error
            f_low = f0 / stats.f.ppf(1 - alpha / 2, n - 1, (n - 1) * (k - 1))
            f_high = f0 * stats.f.ppf(1 - alpha / 2, (n - 1) * (k - 1), n - 1)
            result['consistency_ci_low'] = (f_low - 1) / (f_low + k - 1)
            result['consistency_ci_high'] = (f_high - 1) / (f_high + k - 1)

    agreement_denominator = ms_rows + (k - 1) * ms_error + k * (ms_columns - ms_error) / n
    if agreement_denominator > 0:
        rho = (ms_rows - ms_error) / agreement_denominator
        result['agreement'] = rho
        if ms_error > 0 and rho < 1:
            a = k * rho / (n * (1 - rho))
            b = 1 + k * rho * (n - 1) / (n * (1 - rho))
            numerator = (a * ms_columns + b * ms_error) ** 2
            denominator = (a * ms_columns) ** 2 / (k - 1) + (b * ms_error) ** 2 / ((n - 1) * (k - 1))
            v = numerator / denominator if denominator > 0 else (n - 1) * (k - 1)
            f_star = stats.f.ppf(1 - alpha / 2, n - 1, v)
            f_star_upper = stats.f.ppf(1 - alpha / 2, v, n - 1)
            spread = k * ms_columns + (k * n - k - n) * ms_error
            result['agreement_ci_low'] = n * (ms_rows - f_star * ms_error) / (f_star * spread + n * ms_rows)
            result['agreement_ci_high'] = n * (f_star_upper * ms_rows - ms_error) / (spread + n * f_star_upper * ms_rows)
    return {key: float(value) if isinstance(value, (float, np.floating)) else value for key, value in result.items()}
