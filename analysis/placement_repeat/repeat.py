"""The repeat of the blind placement (PLAN.md): 10 recordings drawn at random, placed again from scratch.

python3 analysis/placement_repeat/repeat.py draw                 (once: draws and makes the repeat's data folder)
python3 analysis/placement_repeat/repeat.py switch repeat|main   (points the app at it, or back; app closed)
python3 analysis/placement_repeat/repeat.py progress             (codes and loop names, no result)
python3 analysis/placement_repeat/repeat.py compare [--unblind]  (PLAN.md's comparison)

All take ``--folder`` for the repeat's data folder (default: `DEFAULT_FOLDER`, beside the repository).

- `draw` draws the recordings from PLAN.md's pool with its seed and makes the folder. Its StabilizedVideos/
  holds links to the drawn videos and their stabilization files, so blind placement lists only them; its
  Statistics/ starts empty, so no line of the first placement is drawn and loop1-loop3 are free. It prints
  only the codes the app lists the recordings under; ``placement_repeat.json`` there keeps no names.
- `switch repeat` sets settings.csv to the folder, observer SJ-R and blind placement on; `switch main` sets
  it back to the main data folder, observer SJ, blind placement off.
- `progress` is ``capillary.aims --progress`` for the drawn recordings.
- `compare` refuses while blind placement is on (as ``capillary.aims``). It writes recordings.csv,
  loops.csv and summary.csv (here, or ``--out``) and prints the summary.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPOSITORY)
from capillary import aims, blinding, datasets, inventory, placement  # noqa: E402

#: PLAN.md: the seed (the date of the plan) and how many recordings are drawn.
SEED = 20261105
SIZE = 10
#: Recordings the aims use that PLAN.md leaves out of the pool, and why.
LEFT_OUT = {'FP03_Wefter_21-Oct-2019_10-21-58': 'no line is possible on it (PROTOCOL.md)',
            'ISMOKE_FP04_Sföre_11-Nov-2020_08-58-47': 'its blind lines were looked at after unblinding'}
FIRST_OBSERVER = 'SJ'
REPEAT_OBSERVER = 'SJ-R'
#: The first placement: saved in blind placement on 2026-10-29 (PROTOCOL.md: 10:13-12:37, and the three
#: recordings aim 2 gained at 18:58-19:04).
FIRST_DAY = '2026-10-29'
FIRST_BEFORE = '2026-10-29T19:06'
DEFAULT_FOLDER = os.path.join(os.path.dirname(REPOSITORY), 'capillaroscopy_placement_repeat')
MANIFEST = 'placement_repeat.json'
STATISTICS = 'Statistics'
PLACEMENTS = ('first', 'repeat')
NAN = math.nan


# ------------------------------------------------------------------------------------------------ the draw

def pool() -> list:
    """PLAN.md's pool: the recordings the aims use (`capillary.inventory`) without `LEFT_OUT`, by name (NFC)."""
    names = set(aims.aims_studies())
    left_out = {inventory.nfc(name) for name in LEFT_OUT}
    if not left_out <= names:
        raise SystemExit(f'Not among the recordings the aims use: {", ".join(sorted(left_out - names))}')
    return sorted(names - left_out)


def draw_names(names: list, seed: int = SEED, size: int = SIZE) -> list:
    """`size` of `names` drawn without replacement by numpy's default generator with `seed`, in their order."""
    picks = np.random.default_rng(seed).choice(len(names), size=size, replace=False)
    return [names[i] for i in sorted(picks)]


def _stabilized_files(folder: str, stem: str) -> list:
    """The files of `folder` that belong to `stem`'s stabilized video: the video and its stabilization files."""
    stem = inventory.nfc(stem)
    return [entry for entry in sorted(os.listdir(folder))
            if inventory.nfc(entry).startswith((f'{stem}.', f'{stem}{datasets.SEPARATOR}'))]


def draw(folder: str) -> int:
    if os.path.exists(os.path.join(folder, MANIFEST)):
        print(f'Already drawn ({os.path.join(folder, MANIFEST)}): PLAN.md draws once.', file=sys.stderr)
        return 2
    main = aims.default_data_folder()
    if not main or os.path.abspath(main) == os.path.abspath(folder):
        print('settings.csv does not point at the main data folder.', file=sys.stderr)
        return 2
    names = pool()
    drawn = draw_names(names)
    source = os.path.join(main, aims.STABILIZED_FOLDER)
    links = []
    for name in drawn:
        files = _stabilized_files(source, name)
        have = {inventory.nfc(entry) for entry in files}
        if not {f'{name}.avi', f'{name}{datasets.SEPARATOR}stabilization.csv'} <= have:
            print(f'{blinding.code(name)} has no stabilized video or shifts in {source}.', file=sys.stderr)
            return 2
        links += files
    target = os.path.join(folder, aims.STABILIZED_FOLDER)
    os.makedirs(target, exist_ok=True)
    os.makedirs(os.path.join(folder, STATISTICS), exist_ok=True)
    for entry in links:
        os.symlink(os.path.join(source, entry), os.path.join(target, entry))
    codes = sorted(blinding.codes(drawn).values())
    record = {'plan': 'analysis/placement_repeat/PLAN.md', 'drawn': datetime.datetime.now().isoformat(timespec='seconds'),
              'seed': SEED, 'size': SIZE, 'pool': len(names), 'codes': codes,
              'main_data_folder': os.path.abspath(main), 'first_observer': FIRST_OBSERVER,
              'repeat_observer': REPEAT_OBSERVER}
    with open(os.path.join(folder, MANIFEST), 'w', encoding='utf-8') as handle:
        json.dump(record, handle, indent=2)
    print(f'Drew {SIZE} of the {len(names)} recordings of the pool (seed {SEED}) into {folder}')
    print(f'Their codes, as the app lists them: {" ".join(codes)}')
    return 0


def _manifest(folder: str) -> dict:
    try:
        with open(os.path.join(folder, MANIFEST), encoding='utf-8') as handle:
            return json.load(handle)
    except OSError:
        raise SystemExit(f'Nothing drawn in {folder}: run `repeat.py draw` first.')


def drawn(folder: str) -> list:
    """The drawn recordings: PLAN.md's draw made again, checked against the codes the draw kept."""
    record = _manifest(folder)
    names = draw_names(pool(), record['seed'], record['size'])
    if sorted(blinding.codes(names).values()) != record['codes']:
        raise SystemExit(f'The draw made again does not give the codes in {MANIFEST}: the pool has changed.')
    return names


# ------------------------------------------------------------------------------------------- the settings

def _app_running() -> bool:
    """Whether a process started with Application.py runs here (False where /proc cannot tell)."""
    try:
        processes = [pid for pid in os.listdir('/proc') if pid.isdigit() and int(pid) != os.getpid()]
    except OSError:
        return False
    for pid in processes:
        try:
            with open(f'/proc/{pid}/cmdline', 'rb') as handle:
                parts = handle.read().split(b'\0')
        except OSError:
            continue
        if any(os.path.basename(part) == b'Application.py' for part in parts):
            return True
    return False


def write_settings(changes: dict, path: str = aims.SETTINGS) -> None:
    """settings.csv with `changes` (``{key: value}``; None removes the row), the other rows as they were."""
    with open(path, newline='', encoding='utf-8') as handle:
        rows = [row for row in csv.reader(handle) if row]
    for key, value in changes.items():
        keys = [row[0].strip() for row in rows]
        if key in keys:
            if value is None:
                del rows[keys.index(key)]
            else:
                rows[keys.index(key)] = [key, value]
        elif value is not None:
            rows.append([key, value])
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        csv.writer(handle, lineterminator='\n').writerows(rows)


def switch(to: str, folder: str) -> int:
    record = _manifest(folder)
    if _app_running():
        print('Close the app first: it writes settings.csv itself and would undo the switch.', file=sys.stderr)
        return 2
    if to == 'repeat':
        changes = {'Application_path': os.path.abspath(folder), 'observer': REPEAT_OBSERVER, aims.BLIND_SETTING: '1'}
    else:
        changes = {'Application_path': record['main_data_folder'], 'observer': FIRST_OBSERVER,
                   aims.BLIND_SETTING: None}
    write_settings(changes)
    print(f'The app now opens on {changes["Application_path"]}, observer {changes["observer"]}, blind placement '
          f'{"on" if changes[aims.BLIND_SETTING] else "off"}.')
    return 0


def progress(folder: str) -> int:
    names = drawn(folder)
    table = aims.collect(os.path.join(folder, STATISTICS))
    print(f'Observer {REPEAT_OBSERVER}:')
    print(aims.progress(table[table['observer'] == REPEAT_OBSERVER], {name: 'Drawn' for name in names}))
    return 0


# ------------------------------------------------------------------------------------------ the comparison

def first_placement(main_folder: str, names) -> pd.DataFrame:
    """The first placement's whole loops on `names` (`capillary.aims.loops`): observer SJ, saved in blind
    placement on 2026-10-29."""
    table = aims.collect(os.path.join(main_folder, STATISTICS))
    created = table['created'].astype(str)
    keep = (table['observer'] == FIRST_OBSERVER) & table['recording'].isin(names) & \
        created.str.startswith(FIRST_DAY) & (created < FIRST_BEFORE)
    return aims.loops(table[keep])


def repeat_placement(folder: str, names) -> pd.DataFrame:
    """The repeat's whole loops on `names` (`capillary.aims.loops`): observer SJ-R in the repeat's folder."""
    table = aims.collect(os.path.join(folder, STATISTICS))
    return aims.loops(table[(table['observer'] == REPEAT_OBSERVER) & table['recording'].isin(names)])


def overlap(first_points, second_points) -> float:
    """How far two lines run along each other: the larger share of either within `placement.MATCH_PX` of the
    other. From `placement.MIN_LINE_OVERLAP` they lie on the same capillary (PLAN.md)."""
    covered_first, covered_second, _ = placement.line_overlap(first_points, second_points)
    return max(covered_first, covered_second)


def _ranked(loop_table: pd.DataFrame, recording: str) -> pd.DataFrame:
    """The recording's loops named loop1-loop3, in the order of the ranking (column ``rank``)."""
    group = loop_table[loop_table['recording'] == recording]
    group = group.assign(rank=group['dataset'].map(aims.rank))
    return group[group['rank'].between(1, aims.RANKED_LOOPS)].sort_values('rank')


def _lies_on(points, others: pd.DataFrame) -> tuple:
    """(the name of the loop of `others` that the line `points` lies on, or ''; the largest overlap)."""
    best, name = 0.0, ''
    for other in others.itertuples(index=False):
        share = overlap(points, other.points)
        if share > best:
            best, name = share, other.dataset
    return (name if best >= placement.MIN_LINE_OVERLAP else ''), best


def compare(first: pd.DataFrame, repeat: pd.DataFrame, names, studies: dict) -> tuple:
    """(one row per recording, one row per loop): PLAN.md's comparison of two placements (`aims.loops`)."""
    values = {key: aims.per_recording(table).set_index('recording') for key, table in zip(PLACEMENTS, (first, repeat))}
    codes = blinding.codes(names)
    recordings, loop_rows = [], []
    for name in names:
        ranked = {key: _ranked(table, name) for key, table in zip(PLACEMENTS, (first, repeat))}
        for this, other in (PLACEMENTS, PLACEMENTS[::-1]):
            for loop in ranked[this].itertuples(index=False):
                on, share = _lies_on(loop.points, ranked[other])
                loop_rows.append({'code': codes[name], 'recording': name, 'placement': this, 'dataset': loop.dataset,
                                  'counted': bool(loop.counted), 'why_not': loop.why_not, 'snr': loop.snr,
                                  'speed_mm_s': loop.speed_mm_s, 'length_px': loop.length_px,
                                  f'lies_on_{other}': on, 'overlap': share})
        references = {key: table[table['rank'] == 1] for key, table in ranked.items()}
        both = all(len(table) for table in references.values())
        row = {'code': codes[name], 'recording': name, 'study': studies.get(name, ''),
               'first_loops': len(ranked['first']), 'repeat_loops': len(ranked['repeat'])}
        share = overlap(references['first']['points'].iloc[0], references['repeat']['points'].iloc[0]) if both else NAN
        row.update(same_reference=bool(share >= placement.MIN_LINE_OVERLAP) if both else None, reference_overlap=share,
                   repeat_reference_lies_on=_lies_on(references['repeat']['points'].iloc[0], ranked['first'])[0]
                   if both else '')
        for key in PLACEMENTS:
            reference = references[key]
            row[f'{key}_reference_counted'] = bool(reference['counted'].iloc[0]) if len(reference) else None
            row[f'{key}_reference_mm_s'] = float(reference['speed_mm_s'].iloc[0]) if len(reference) else NAN
            found = name in values[key].index
            for column in ('value_mm_s', 'value_from', 'mean_mm_s', 'loops_counted'):
                row[f'{key}_{column}'] = values[key].at[name, column] if found else (NAN if column != 'value_from' else '')
        if np.isfinite(row['first_value_mm_s']) and np.isfinite(row['repeat_value_mm_s']):
            first_loop = ranked['first'][ranked['first']['dataset'] == row['first_value_from']]
            repeat_loop = ranked['repeat'][ranked['repeat']['dataset'] == row['repeat_value_from']]
            row['values_same_capillary'] = bool(overlap(first_loop['points'].iloc[0], repeat_loop['points'].iloc[0])
                                                >= placement.MIN_LINE_OVERLAP)
        else:
            row['values_same_capillary'] = None
        recordings.append(row)
    return pd.DataFrame(recordings), pd.DataFrame(loop_rows)


def _te_interval(differences) -> tuple:
    """The typical error (SD of the differences / sqrt 2) and its 95% interval (chi-square, n - 1 df), as
    analysis/primary_endpoint/report.py."""
    d = np.asarray(differences, dtype=float)
    if d.size < 2:
        return NAN, NAN, NAN
    df = d.size - 1
    te = float(np.std(d, ddof=1) / math.sqrt(2))
    return te, te * math.sqrt(df / stats.chi2.ppf(0.975, df)), te * math.sqrt(df / stats.chi2.ppf(0.025, df))


#: `aims.reproducibility`'s names for its two series, called active and control there.
_RENAME = {'participants': 'pairs', 'mean_active_mm_s': 'mean_repeat_mm_s', 'mean_control_mm_s': 'mean_first_mm_s'}


def agreement_of(first, repeat) -> dict:
    """Aim 1's statistics (`capillary.aims.reproducibility`) of the two placements' values (pairs with both),
    Bland-Altman as the repeat minus the first, and 95% intervals for the typical error and the CV."""
    f, r = np.asarray(first, dtype=float), np.asarray(repeat, dtype=float)
    keep = np.isfinite(f) & np.isfinite(r)
    f, r = f[keep], r[keep]
    out = {_RENAME.get(key, key): value for key, value in aims.reproducibility(r, f).items()}
    _, low, high = _te_interval(r - f)
    mean = out['grand_mean_mm_s']
    out.update(te_ci_low_mm_s=low, te_ci_high_mm_s=high, cv_ci_low=100 * low / mean if f.size else NAN,
               cv_ci_high=100 * high / mean if f.size else NAN)
    return out


def _tally(first, repeat) -> dict:
    """How many of the pairs (`first`, `repeat`, booleans) are true in both, in the first only, the repeat only,
    in neither."""
    f, r = np.asarray(first, dtype=bool), np.asarray(repeat, dtype=bool)
    return {'both': int((f & r).sum()), 'first_only': int((f & ~r).sum()), 'repeat_only': int((~f & r).sum()),
            'neither': int((~f & ~r).sum())}


def summarize(recordings: pd.DataFrame, loop_table: pd.DataFrame) -> list:
    """PLAN.md's comparisons, one dict each (summary.csv)."""
    rows = []
    placed = recordings[recordings['same_reference'].notna()]
    same = placed[placed['same_reference'].astype(bool)]
    k, n = len(same), len(placed)
    interval = stats.binomtest(k, n).proportion_ci(method='exact') if n else None
    rows.append({'comparison': '1. the same reference capillary', 'recordings': n, 'same': k,
                 'share': k / n if n else NAN, 'share_ci_low': interval.low if n else NAN,
                 'share_ci_high': interval.high if n else NAN})
    rows.append({'comparison': '2. its velocity (the same reference, counted in both)',
                 **_tally(same['first_reference_counted'].astype(bool), same['repeat_reference_counted'].astype(bool)),
                 **agreement_of(same['first_reference_mm_s'], same['repeat_reference_mm_s'])})
    for label, column in (("3. the recording's value (PROTOCOL.md)", 'value_mm_s'),
                          ('also: the mean of the counted loops (the secondary value)', 'mean_mm_s')):
        first, repeat = (recordings[f'{key}_{column}'].astype(float) for key in PLACEMENTS)
        row = {'comparison': label, **_tally(np.isfinite(first), np.isfinite(repeat)), **agreement_of(first, repeat)}
        if column == 'value_mm_s':
            row['same_capillary'] = int(recordings['values_same_capillary'].eq(True).sum())
        rows.append(row)
    repeat_loops = loop_table[loop_table['placement'] == 'repeat'] if len(loop_table) else pd.DataFrame()
    on = repeat_loops['lies_on_first'] if len(repeat_loops) else pd.Series(dtype=str)
    rows.append({'comparison': "also: the repeat's loops on a capillary of the first placement",
                 'loops': len(repeat_loops), 'on_first': int((on != '').sum()),
                 **{f'on_first_{name}': int((on == name).sum()) for name in ('loop1', 'loop2', 'loop3')}})
    return rows


def _fmt(value, digits: int = 3) -> str:
    return aims._fmt(value, digits)


def report(rows: list, recordings: pd.DataFrame) -> str:
    """The printed summary of `summarize`."""
    one, two, three, mean, loops_ = rows
    lines = [f'Drawn recordings: {len(recordings)}; with loops in the first placement '
             f'{int((recordings["first_loops"] > 0).sum())}, in the repeat {int((recordings["repeat_loops"] > 0).sum())}',
             '',
             f'1. The same reference capillary: {one["same"]} of {one["recordings"]} recordings with a reference in '
             f'both ({_fmt(100 * one["share"], 0)}%, 95% CI {_fmt(100 * one["share_ci_low"], 0)}-'
             f'{_fmt(100 * one["share_ci_high"], 0)}%)']
    for label, row in (('2. Its velocity, where it counts in both', two), ("3. The recording's value", three),
                       ('Also: the mean of the counted loops', mean)):
        tally = (f'counts in both {row["both"]}, first only {row["first_only"]}, repeat only {row["repeat_only"]}, '
                 f'neither {row["neither"]}') if label.startswith('2') else \
            (f'a value in both {row["both"]}, first only {row["first_only"]}, repeat only {row["repeat_only"]}, '
             f'neither {row["neither"]}')
        lines += ['', f'{label}: {row["pairs"]} pairs ({tally})']
        if label.startswith('3'):
            lines.append(f'  the two values from the same capillary in {row["same_capillary"]} of {row["both"]}')
        if row['pairs']:
            lines.append(f'  mean first {_fmt(row["mean_first_mm_s"])}, repeat {_fmt(row["mean_repeat_mm_s"])} mm/s; '
                         f'typical error {_fmt(row["typical_error_mm_s"])} mm/s, CV {_fmt(row["cv_percent"], 0)}% '
                         f'(95% CI {_fmt(row["cv_ci_low"], 0)}-{_fmt(row["cv_ci_high"], 0)}%), log scale '
                         f'{_fmt(row["cv_log_percent"], 0)}%, smallest detectable change {_fmt(row["sdc_mm_s"])} mm/s')
            lines.append(f'  repeat - first: bias {_fmt(row["ba_bias"])} mm/s, limits {_fmt(row["ba_loa_low"])} to '
                         f'{_fmt(row["ba_loa_high"])}; ICC(A,1) {_fmt(row["icc_a1"], 2)} ({_fmt(row["icc_a1_ci_low"], 2)} '
                         f'to {_fmt(row["icc_a1_ci_high"], 2)})')
    lines += ['', f"Also: {loops_['on_first']} of the repeat's {loops_['loops']} loops lie on a capillary of the first "
                  f"placement (on its loop1 {loops_['on_first_loop1']}, loop2 {loops_['on_first_loop2']}, loop3 "
                  f"{loops_['on_first_loop3']})"]
    return '\n'.join(lines)


def compare_main(folder: str, out: str, unblind: bool) -> int:
    if aims.blind_placement_on() and not unblind:
        print('Blind placement is on in the app, so the comparison stays hidden until the repeat is placed.\n'
              'Use `repeat.py progress` to see how far it got, or --unblind to show it.', file=sys.stderr)
        return 2
    record = _manifest(folder)
    names = drawn(folder)
    first = first_placement(record['main_data_folder'], names)
    repeat = repeat_placement(folder, names)
    recordings, loop_table = compare(first, repeat, names, aims.aims_studies())
    rows = summarize(recordings, loop_table)
    os.makedirs(out, exist_ok=True)
    recordings.to_csv(os.path.join(out, 'recordings.csv'), index=False)
    loop_table.to_csv(os.path.join(out, 'loops.csv'), index=False)
    pd.DataFrame(rows).to_csv(os.path.join(out, 'summary.csv'), index=False)
    print(report(rows, recordings))
    print(f'\nTables in {out}')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('command', choices=('draw', 'switch', 'progress', 'compare'))
    parser.add_argument('to', nargs='?', choices=('repeat', 'main'), help='for switch: where the app should point')
    parser.add_argument('--folder', default=DEFAULT_FOLDER, help="the repeat's data folder")
    parser.add_argument('--out', default=HERE, help='where compare writes its tables')
    parser.add_argument('--unblind', action='store_true', help='compare although blind placement is on')
    args = parser.parse_args(argv)
    if args.command == 'draw':
        return draw(args.folder)
    if args.command == 'switch':
        if not args.to:
            parser.error('switch needs repeat or main')
        return switch(args.to, args.folder)
    if args.command == 'progress':
        return progress(args.folder)
    return compare_main(args.folder, args.out, args.unblind)


if __name__ == '__main__':
    sys.exit(main())
