"""Every number of the statistics report "Statistics for Aims 1 and 2", worked through step by step (2026-11-03)

python analysis/statistics_report/report_numbers.py --aim1 <table> --aim2 <table> [--observer SJ]

The report (a Claude Docs document) explains what each of the protocol's statistics computes, worked
through on the study's own values. This prints every intermediate step the report quotes, from the
same functions the protocol's analysis uses (`capillary.aims`, `capillary.agreement`).

The per-participant values are not in the repository. Either source works:
- `capillary.aims`' tables on the computer that holds the data: `--aim1 Reports/aims/aim1_pairs.csv
  --aim2 Reports/aims/aim2_values.csv --observer SJ`;
- the report page's tables, which name only study and participant: its aim 1 participants table and
  `aim2_pairs.json`.

Printed:
- aim 1, pooled and per study: each pair, the typical error with its chi-square interval, the CV and
  log CV, the smallest detectable change, Bland-Altman (bias, limits, their intervals, slope, ratios)
  and the two-way ANOVA behind ICC(A,1) and ICC(C,1);
- aim 2, per study and pooled: each participant's change, the paired t-test step by step, the same on
  the log scale, the Wilcoxon signed-rank test with its ranks and exact p, the Hodges-Lehmann
  estimate, the sign test, and how the change relates to the value before (Spearman);
- tables that do not depend on the values: the Wilcoxon test's smallest possible p by n, Wilson
  intervals for the yields reported on 2026-10-29, how wide the intervals get with more participants,
  and the smallest effect aim 2 could detect with 80% power.
"""
import argparse
import itertools
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
from capillary import agreement, aims  # noqa: E402

#: Yields reported at unblinding (DEVLOG and PROTOCOL.md, 2026-10-29): counted, out of.
YIELDS = (('whole loops that count', 91, 200), ('recordings with a value', 54, 90),
          ('aim 1 participants with both visits', 9, 24), ('aim 2 participants with before and after', 8, 23))


def read(path: str, observer: str, columns: dict) -> pd.DataFrame:
    """A table of the report page (JSON list) or of `capillary.aims` (CSV), with `columns` renamed to the
    names used here; one observer's rows from a `capillary.aims` table."""
    if path.endswith('.json'):
        with open(path, encoding='utf-8') as handle:
            table = pd.DataFrame(json.load(handle))
    else:
        table = pd.read_csv(path)
        if 'observer' in table and observer:
            table = table[table['observer'] == observer]
    for wanted, choices in columns.items():
        found = next((c for c in choices if c in table.columns), None)
        if found is None:
            raise SystemExit(f'{path}: no column {" or ".join(choices)}')
        table = table.rename(columns={found: wanted})
    return table


def wilson(k: int, n: int, z: float = 1.959964) -> tuple:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z / (1 + z * z / n) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return centre - half, centre + half


def exact_signed_rank(n: int) -> np.ndarray:
    """The null distribution of W+ for n untied differences: counts of each W+ over all 2^n sign patterns."""
    counts = np.zeros(n * (n + 1) // 2 + 1, dtype=int)
    for signs in itertools.product((0, 1), repeat=n):
        counts[sum(rank for rank, s in zip(range(1, n + 1), signs) if s)] += 1
    return counts


def hodges_lehmann(values: np.ndarray) -> float:
    """The median of all pairwise (Walsh) averages, (x_i + x_j) / 2 with i <= j."""
    return float(np.median([(values[i] + values[j]) / 2 for i in range(len(values)) for j in range(i, len(values))]))


def aim1_part(pairs: pd.DataFrame) -> None:
    both = pairs[np.isfinite(pairs['nicotine']) & np.isfinite(pairs['control'])]
    for label, group in [*both.groupby('study', sort=True), ('pooled', both)]:
        a, c = group['nicotine'].to_numpy(float), group['control'].to_numpy(float)
        n = len(a)
        print(f'\nAIM 1, {label}: {n} participants with both visits')
        if label == 'pooled':
            for row in group.itertuples(index=False):
                print(f'  {row.study} {row.subject}: nicotine visit {row.nicotine:.3f}, control visit {row.control:.3f}, '
                      f'difference {row.nicotine - row.control:+.3f} mm/s, '
                      f'ln ratio {math.log(row.nicotine / row.control):+.2f}')
        if n < 2:
            continue
        d = a - c
        r = aims.reproducibility(a, c)
        te = r['typical_error_mm_s']
        low, high = (te * math.sqrt((n - 1) / stats.chi2.ppf(q, n - 1)) for q in (0.975, 0.025))
        print(f'  mean of all values {r["grand_mean_mm_s"]:.4f} (nicotine {a.mean():.4f}, control {c.mean():.4f})')
        print(f'  SD of the differences {d.std(ddof=1):.4f}; TE = SD / sqrt 2 = {te:.4f} mm/s (95% CI {low:.4f}-{high:.4f})')
        mean = r['grand_mean_mm_s']
        print(f'  CV {r["cv_percent"]:.1f}% ({100 * low / mean:.0f}-{100 * high / mean:.0f}%); '
              f'log CV {r["cv_log_percent"]:.1f}%')
        log_te = math.log(1 + r['cv_log_percent'] / 100)
        print(f'  SDC = 2.77 x TE = {r["sdc_mm_s"]:.4f} mm/s ({100 * r["sdc_mm_s"] / r["grand_mean_mm_s"]:.0f}% of the mean); '
              f'on the log scale a factor of {math.exp(2.77 * log_te):.2f}')
        ba = agreement.bland_altman(a, c)
        ratio = agreement.bland_altman_ratio(a, c)
        print(f'  Bland-Altman: bias {ba["bias"]:+.4f} (95% CI {ba["bias_ci_low"]:+.4f} to {ba["bias_ci_high"]:+.4f}); '
              f'limits {ba["loa_low"]:+.4f} ({ba["loa_low_ci_low"]:+.3f} to {ba["loa_low_ci_high"]:+.3f}) and '
              f'{ba["loa_high"]:+.4f} ({ba["loa_high_ci_low"]:+.3f} to {ba["loa_high_ci_high"]:+.3f}); slope '
              f'{ba["slope"]:.2f} ({ba["slope_ci_low"]:.2f} to {ba["slope_ci_high"]:.2f}); as ratios x{ratio["ratio"]:.2f} '
              f'({ratio["ratio_ci_low"]:.2f}-{ratio["ratio_ci_high"]:.2f}), '
              f'limits x{ratio["loa_low"]:.2f} to x{ratio["loa_high"]:.2f}')
        print(f'  paired t-test of the bias: t = {stats.ttest_rel(a, c).statistic:.2f}, df {n - 1}, p = '
              f'{stats.ttest_rel(a, c).pvalue:.3f}')
        x = np.column_stack([a, c])
        grand = x.mean()
        ms_rows = 2 * float(np.sum((x.mean(axis=1) - grand) ** 2)) / (n - 1)
        ms_columns = n * float(np.sum((x.mean(axis=0) - grand) ** 2))
        ms_error = (float(np.sum((x - grand) ** 2)) - ms_rows * (n - 1) - ms_columns) / (n - 1)
        icc = agreement.icc(x)
        print(f'  ANOVA: MS between people {ms_rows:.5f} (df {n - 1}), between visits {ms_columns:.5f} (df 1), residual '
              f'{ms_error:.5f} (df {n - 1}); MS_R / MS_E = {ms_rows / ms_error:.2f}')
        print(f'  ICC(A,1) {icc["agreement"]:.3f} ({icc["agreement_ci_low"]:.2f} to {icc["agreement_ci_high"]:.2f}); '
              f'ICC(C,1) {icc["consistency"]:.3f} ({icc["consistency_ci_low"]:.2f} to {icc["consistency_ci_high"]:.2f})')


def aim2_part(values: pd.DataFrame) -> float:
    """Prints aim 2; returns the pooled SD of the log ratios (for the power table)."""
    complete = values[np.isfinite(values['before']) & np.isfinite(values['after'])]
    pooled_sd = math.nan
    for label, group in [*complete.groupby('study', sort=True), ('pooled', complete)]:
        b, a = group['before'].to_numpy(float), group['after'].to_numpy(float)
        n = len(b)
        print(f'\nAIM 2, {label}: {n} participants with a value before and after nicotine')
        change, log_ratio = a - b, np.log(a / b)
        for row, ch in zip(group.itertuples(index=False), change):
            print(f'  {row.study} {row.subject}: before {row.before:.3f}, after {row.after:.3f}, change {ch:+.3f} mm/s, '
                  f'ratio {row.after / row.before:.2f}')
        r = aims.response(b, a)
        se = change.std(ddof=1) / math.sqrt(n)
        print(f'  change: mean {change.mean():+.4f}, SD {change.std(ddof=1):.4f}, SE {se:.4f}; t = {change.mean() / se:.2f}, '
              f'df {n - 1}, p = {r["t_test_p"]:.3f}; 95% CI {r["change_ci_low_mm_s"]:+.4f} to {r["change_ci_high_mm_s"]:+.4f} '
              f'(t quantile {stats.t.ppf(0.975, n - 1):.3f})')
        print(f'  log scale: mean ln ratio {log_ratio.mean():+.3f}, SD {log_ratio.std(ddof=1):.3f}; ratio {r["ratio"]:.2f} '
              f'({r["ratio_ci_low"]:.2f}-{r["ratio_ci_high"]:.2f}), p = {r["log_t_test_p"]:.3f}')
        ranks = stats.rankdata(np.abs(change))
        w_plus, w_minus = float(ranks[change > 0].sum()), float(ranks[change < 0].sum())
        counts = exact_signed_rank(n)
        extreme = int(sum(counts[: int(min(w_plus, w_minus)) + 1]))
        print(f'  Wilcoxon: ranks of |change| {[int(x) if x == int(x) else x for x in ranks]}, W+ (increases) {w_plus:g}, '
              f'W- {w_minus:g}; {extreme} of {2 ** n} sign patterns give a sum this small, two-sided p = '
              f'{min(1.0, 2 * extreme / 2 ** n):.4f} (scipy {r["wilcoxon_p"]:.4f}); on the ln ratios p = '
              f'{stats.wilcoxon(log_ratio).pvalue:.4f}')
        down = int((change < 0).sum())
        print(f'  Hodges-Lehmann change {hodges_lehmann(change):+.4f} mm/s; sign test {down} of {n} down, p = '
              f'{stats.binomtest(down, n).pvalue:.4f}')
        if n >= 3:
            rho = stats.spearmanr(b, change)
            print(f'  change against the value before: Spearman rho {rho.statistic:+.2f} (p = {rho.pvalue:.3f})')
        if label == 'pooled':
            pooled_sd = float(log_ratio.std(ddof=1))
    return pooled_sd


def general_part(pooled_log_sd: float) -> None:
    print('\nWILCOXON: the smallest two-sided p, every difference the same way')
    for n in range(3, 11):
        counts = exact_signed_rank(n)
        cumulative = np.cumsum(counts) / counts.sum()
        critical = [w for w in range(len(cumulative)) if 2 * cumulative[w] <= 0.05]
        print(f'  n = {n}: {2 / 2 ** n:.4f}; significant at 0.05 when the smaller rank sum is at most '
              f'{critical[-1] if critical else "(never)"}')
    print('\nWILSON 95% intervals for the yields reported on 2026-10-29')
    for name, k, n in YIELDS:
        low, high = wilson(k, n)
        print(f'  {name}: {k} of {n} = {100 * k / n:.0f}% ({100 * low:.0f}-{100 * high:.0f}%)')
    print('\nTHE TYPICAL ERROR: the 95% interval as a multiple of the estimate')
    for n in (9, 12, 18, 24, 48):
        print(f'  {n} participants: {math.sqrt((n - 1) / stats.chi2.ppf(0.975, n - 1)):.2f} to '
              f'{math.sqrt((n - 1) / stats.chi2.ppf(0.025, n - 1)):.2f}')
    print('\nICC with two visits: the 95% interval for an observed ICC (consistency form)')
    for rho in (0.5, 0.75):
        for n in (9, 24, 48):
            f0, f = (1 + rho) / (1 - rho), stats.f.ppf(0.975, n - 1, n - 1)
            low, high = f0 / f, f0 * f
            print(f'  ICC {rho} with {n} participants: {(low - 1) / (low + 1):.2f} to {(high - 1) / (high + 1):.2f}')
    if math.isfinite(pooled_log_sd):
        print(f'\nAIM 2: the smallest true fall a paired t-test (two-sided 0.05) finds with 80% power, SD of the ln ratio '
              f'{pooled_log_sd:.3f} as observed pooled')
        for n in (5, 8, 10, 13, 23):
            def power(delta):
                df, nc = n - 1, delta / (pooled_log_sd / math.sqrt(n))
                tc = stats.t.ppf(0.975, df)
                return 1 - stats.nct.cdf(tc, df, nc) + stats.nct.cdf(-tc, df, nc)
            lo, hi = 0.0, 5.0
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if power(mid) < 0.8 else (lo, mid)
            print(f'  {n} participants: ln ratio {-hi:.2f}, a fall of {100 * (1 - math.exp(-hi)):.0f}%')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--aim1', required=True,
                        help="aim 1's pairs: capillary.aims' aim1_pairs.csv or the report page's table")
    parser.add_argument('--aim2', required=True,
                        help="aim 2's values: capillary.aims' aim2_values.csv or the page's aim2_pairs.json")
    parser.add_argument('--observer', default='SJ', help="the observer, for capillary.aims' tables (default SJ)")
    args = parser.parse_args()
    aim1_part(read(args.aim1, args.observer, {'nicotine': ('active_mm_s',), 'control': ('control_mm_s',)}))
    sd = aim2_part(read(args.aim2, args.observer, {'before': ('active_before_mm_s', 'before_mm_s'),
                                                   'after': ('active_after_mm_s', 'after_mm_s')}))
    general_part(sd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
