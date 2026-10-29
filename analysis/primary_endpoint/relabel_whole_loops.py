"""Re-save as whole loops the lines of 2026-10-29 placed without the 'Whole loop' role (fixed before unblinding).

python3 analysis/primary_endpoint/relabel_whole_loops.py [--data <data folder>] [--dry-run]

During blind placement on 2026-10-29 the lines of the last 13 recordings in the
order of their codes (placed 11:58-12:13) were saved with no role, so
`capillary.aims` would not count them as whole loops. They had been placed as
the protocol asks: round whole loops, over the official rest, in the order of
the observer's ranking. The role was lost because the Centre line page gives a
recording seen before the role its line had then (`gui.line_page.restore_state`):
returning to the first of them restored the role of a try-out line placed there
at 09:56, before blind placement, and every new line kept it.

Each line is saved again under the name the app would have suggested (set1 ->
loop1, ..., in the order placed), with the role 'whole loop', from its own saved
points, frames and space-time diagram. The app's `regenerate_line_report`
measures the diagram again and adds what a whole loop reports: the arterial end,
each limb's pattern shift and the movement check. Before anything is moved the
script checks that the 3-s blocks and every other number of the summary come
out exactly as saved. The old files then go to the data folder's .trash.

Nothing is printed that would unblind: recordings show under their codes, and no
velocity or score is shown.
"""

from __future__ import annotations

import argparse
import datetime
import math
import os
import shutil
import sys

os.environ.setdefault('MPLBACKEND', 'Agg')
REPOSITORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPOSITORY)

from capillary import aims, blinding, datasets, pattern_shift  # noqa: E402
from gui import tasks  # noqa: E402
from gui.settings import DataFolder  # noqa: E402

OBSERVER = 'SJ'
#: When the lines without a role were placed (the last whole loop before them was saved at 11:58:29).
PLACED_FROM, PLACED_TO = '2026-10-29T11:58:30', '2026-10-29T12:13:00'
#: Lines and recordings found on 2026-10-29 (`--progress`); anything else stops the script.
EXPECTED_LINES, EXPECTED_RECORDINGS = 29, 13
#: Summary entries that depend on the role; every other one must come out as saved.
ROLE_KEYS = ('line_role', 'limb_check', 'arterial_end')
WHY = ("saved without the 'Whole loop' role during blind placement: returning to a recording seen before restored "
       "the role of its try-out line (none), and the next lines kept it. Same points, frames and space-time "
       "diagram; measured again from the saved diagram with the role 'whole loop' "
       "(gui.tasks.regenerate_line_report). DEVLOG 2026-10-29.")


class _Job:
    """What `regenerate_line_report` reports its progress to; nothing to show here."""

    def report(self, fraction, text=''):
        pass


def chosen(table, studies: dict):
    """The lines to re-save: no role, over the official rest, by `OBSERVER` in the window, on the aims' recordings."""
    lines = table[(table['observer'] == OBSERVER) & (table['role'] == '') & (table['phase'] == aims.REST)
                  & table['created'].between(PLACED_FROM, PLACED_TO) & table['recording'].isin(studies)]
    return lines.sort_values(['recording', 'created'])


def new_names(lines, table) -> list:
    """(recording, old name, new name): loop1, loop2, ... per recording in the order the lines were placed."""
    out = []
    for recording, group in lines.groupby('recording', sort=True):
        taken = set(table.loc[table['recording'] == recording, 'dataset'])
        for place, old in enumerate(group['dataset'], start=1):
            new = f'loop{place}'
            if new in taken:
                raise SystemExit(f'{blinding.code(recording)} already has a data set {new}; nothing changed')
            out.append((recording, old, new))
    return out


def _same(first, second) -> bool:
    if isinstance(first, float) and isinstance(second, float) and math.isnan(first) and math.isnan(second):
        return True
    return first == second


def relabel(folder: DataFolder, recording: str, old: str, new: str) -> list:
    """Save `old` again as the whole loop `new`; returns the old files, to be moved once all are checked."""
    old_files = datasets.line_dataset_files(folder.statistics, recording, old)
    new_files = datasets.line_dataset_files(folder.statistics, recording, new)
    record = datasets.read_provenance(old_files['provenance'])
    saved = dict(record['summary'])
    with open(old_files['velocity'], encoding='utf-8') as handle:
        saved_blocks = handle.read()
    for part in ('space_time', 'velocity'):          # the blocks are measured again below and compared
        shutil.copy2(old_files[part], new_files[part])
    record['dataset'] = new
    record['line']['role'] = pattern_shift.WHOLE_LOOP
    record['relabelled'] = {'from': old, 'on': datetime.datetime.now().isoformat(timespec='seconds'), 'why': WHY,
                            'software': datasets.software_version()}
    datasets.write_provenance(new_files['provenance'], record)
    result = tasks.regenerate_line_report(_Job(), folder=folder, stem=recording, name=new, fps=record['video']['fps'],
                                          mm_per_pixel=record['mm_per_pixel'],
                                          time_points=record.get('time_points_s') or ())
    with open(new_files['velocity'], encoding='utf-8') as handle:
        if handle.read() != saved_blocks:
            raise SystemExit(f'{blinding.code(recording)} {old}: the 3-s blocks came out differently; old files kept')
    fresh = datasets.read_provenance(new_files['provenance'])['summary']     # as saved, like `saved` (NaN as null)
    changed = [key for key, value in saved.items() if key not in ROLE_KEYS and not _same(value, fresh.get(key))]
    if changed or result['summary'].get('line_role') != pattern_shift.WHOLE_LOOP:
        raise SystemExit(f'{blinding.code(recording)} {old}: {", ".join(changed) or "the role"} came out differently; '
                         'old files kept')
    reports = datasets.line_report_files(folder.reports, recording, old).values()
    return list(old_files.values()) + [path for path in reports if os.path.exists(path)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data', default=None, help="the app's data folder (default: from settings.csv)")
    parser.add_argument('--dry-run', action='store_true', help='only list what would be re-saved')
    args = parser.parse_args(argv)
    folder = DataFolder(args.data or aims.default_data_folder() or REPOSITORY)
    table = aims.collect(folder.statistics)
    studies = aims.aims_studies()
    lines = chosen(table, studies)
    if (len(lines), lines['recording'].nunique()) != (EXPECTED_LINES, EXPECTED_RECORDINGS):
        raise SystemExit(f'found {len(lines)} lines on {lines["recording"].nunique()} recordings, expected '
                         f'{EXPECTED_LINES} on {EXPECTED_RECORDINGS}; nothing changed')
    plan = new_names(lines, table)
    for recording, old, new in sorted(plan, key=lambda item: (blinding.code(item[0]), item[2])):
        print(f'{blinding.code(recording)}  {old} -> {new}')
    if args.dry_run:
        return 0
    old_paths = []
    for recording, old, new in plan:
        old_paths += relabel(folder, recording, old, new)
    trash = tasks.move_to_trash(folder, old_paths, 'lines re-saved as whole loops')
    print(f'{len(plan)} lines on {len({r for r, _, _ in plan})} recordings re-saved as whole loops; the 3-s blocks '
          f'and the pooled pattern shift came out as saved. Old files: {trash}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
