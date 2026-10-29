"""Aim 2, and aim 1 pooled over both studies, for the report page.

python3 analysis/primary_endpoint/secondary.py [--data <data folder>] [--observer SJ]

Run after capillary.aims and its four sensitivity runs (PROTOCOL.md):

    python3 -m capillary.aims
    python3 -m capillary.aims --value reference-only --out Reports/aims/sensitivity_valuereferenceonly
    python3 -m capillary.aims --value mean --out Reports/aims/sensitivity_valuemean
    python3 -m capillary.aims --min-snr 7 --out Reports/aims/sensitivity_minsnr7
    python3 -m capillary.aims --min-snr 9 --out Reports/aims/sensitivity_minsnr9

report.py's tables describe the 200 loops placed before unblinding, as it wrote them at 13:11 on 2026-10-29. This
script writes only what the protocol's two corrections after unblinding added, from capillary.aims' tables, into
Reports/primary_endpoint/dashboard/ of the data folder:

- aim1.json: report.py's aim 1 rows again, now with each analysis pooled over both studies (the primary result). It
  stops unless every per-study row equals the one report.py wrote.
- aim2.json: aim 2 for each analysis, per study and pooled, with how many participants have each value.
- aim2_pairs.json: each aim 2 participant's values before and after nicotine, by study and participant only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import report  # noqa: E402

from capillary import aims  # noqa: E402

#: The folder under Reports/aims/ that holds each of report.ANALYSES, as the commands above write them.
FOLDERS = {'primary': '', 'reference_only': 'sensitivity_valuereferenceonly', 'mean': 'sensitivity_valuemean',
           'snr7': 'sensitivity_minsnr7', 'snr9': 'sensitivity_minsnr9'}


def _table(folder: str, analysis: str, name: str, observer: str) -> pd.DataFrame:
    table = pd.read_csv(os.path.join(folder, 'Reports', 'aims', FOLDERS[analysis], name))
    return table[table['observer'] == observer]


def _same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def aim1(folder: str, observer: str) -> list:
    """report.py's aim 1 rows with the pooled ones, checked against the per-study rows report.py wrote."""
    rows = report._clean(report.aim1_records(
        {key: report.aim1_table(_table(folder, key, 'aim1_pairs.csv', observer)) for key in report.ANALYSES}))
    with open(os.path.join(folder, 'Reports', 'primary_endpoint', 'dashboard', 'aim1.json'), encoding='utf-8') as f:
        written = {row['key']: row for row in json.load(f)}
    new = {row['key']: row for row in rows}
    differ = [f'{key} {name}' for key, row in written.items() for name, value in row.items()
              if not _same(value, new.get(key, {}).get(name))]
    if differ:
        raise SystemExit(f'aim 1 per study differs from what report.py wrote: {", ".join(differ[:10])}')
    return rows


def aim2(folder: str, observer: str) -> list:
    """Aim 2's statistics for each analysis, per study and pooled, with the counts of values behind them."""
    rows = []
    for place, (key, (_, threshold, label, short)) in enumerate(report.ANALYSES.items()):
        stats = _table(folder, key, 'aim2.csv', observer)
        values = _table(folder, key, 'aim2_values.csv', observer)
        before, after = values['active_before_mm_s'], values['active_after_mm_s']
        for row in stats.to_dict('records'):
            mine = values if row['study'] == aims.POOLED else values[values['study'] == row['study']]
            b, a = before[mine.index], after[mine.index]
            both = np.isfinite(b) & np.isfinite(a)
            rows.append({'key': f'{key} {"pooled" if row["study"] == aims.POOLED else row["study"]}', 'analysis': key,
                         'label': label, 'short': short, 'order': place, 'threshold': threshold,
                         **{name: value for name, value in row.items() if name != 'observer'},
                         'with_before': int(np.isfinite(b).sum()), 'with_after': int(np.isfinite(a).sum()),
                         'decreased': int((a[both] < b[both]).sum())})
    return report._clean(rows)


def aim2_pairs(folder: str, observer: str) -> list:
    """Each aim 2 participant: the values before and after nicotine, where each comes from, and the change."""
    values = _table(folder, 'primary', 'aim2_values.csv', observer)
    rows = []
    for r in values.to_dict('records'):
        before, after = r['active_before_mm_s'], r['active_after_mm_s']
        has_b, has_a = np.isfinite(before), np.isfinite(after)
        rows.append({'key': f'{r["study"]} {r["subject"]}', 'study': r['study'], 'subject': r['subject'],
                     'status': {(True, True): 'both', (True, False): 'before only', (False, True): 'after only',
                                (False, False): 'neither'}[(bool(has_b), bool(has_a))],
                     'before_mm_s': before, 'before_from': r['active_before_from'] if has_b else '',
                     'before_loops_placed': r['active_before_loops_placed'],
                     'before_loops_counted': r['active_before_loops_counted'],
                     'after_mm_s': after, 'after_from': r['active_after_from'] if has_a else '',
                     'after_loops_placed': r['active_after_loops_placed'],
                     'after_loops_counted': r['active_after_loops_counted'],
                     'change_mm_s': after - before if has_b and has_a else math.nan,
                     'ratio': after / before if has_b and has_a and before > 0 else math.nan})
    return report._clean(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data', default=None, help="the app's data folder (default: from settings.csv)")
    parser.add_argument('--observer', default='SJ')
    args = parser.parse_args(argv)
    folder = args.data or aims.default_data_folder()
    out = os.path.join(folder, 'Reports', 'primary_endpoint', 'dashboard')
    tables = {'aim1': aim1(folder, args.observer), 'aim2': aim2(folder, args.observer),
              'aim2_pairs': aim2_pairs(folder, args.observer)}
    for name, rows in tables.items():
        with open(os.path.join(out, f'{name}.json'), 'w', encoding='utf-8') as handle:
            json.dump(rows, handle, ensure_ascii=False, separators=(',', ':'))
    print(f'aim 1 per study as report.py wrote it; {", ".join(f"{k}.json {len(v)} rows" for k, v in tables.items())} '
          f'written to {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
