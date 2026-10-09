"""The study's recordings: what each one is, and which ones the aims can use.

Built from the official occlusion and release times exported from DynCap
(`metadata/`, see its README). A recording's name says what it is:

    [ISMOKE_]<subject>_<condition><före|efter>[2|_försökN]_<date>_<time>

- ESMOKE: W = e-cigarette with nicotine (active), Q = without nicotine (control).
- ISMOKE: S = heated tobacco (active), C = no exposure (control).
- före is before the exposure, efter after; försökN (ESMOKE) or a trailing 2
  (ISMOKE) a further attempt.
- The same subject code in ESMOKE and ISMOKE is a different person.

Both aims use resting CBV, from the rest before the occlusion, so a recording
is usable when its rest is long enough (`MIN_REST_S`); a missing release time
does not matter.

- **Aim 1** (inter-day reproducibility) needs the före recording of both
  visits: one active day, one control day.
- **Aim 2** (before-to-after change, active minus control) needs the före and
  efter recordings of both visits.

When a visit has several attempts of the same recording, the last usable one
is chosen, on the assumption that a recording was repeated because the
earlier attempt failed. Every alternative is listed, so the choice can be
checked against DynCap.

Names and visits that do not fit the pattern are flagged, not corrected:

- a name without före or efter;
- a visit day with two conditions;
- a före recorded long after the day's first recording (probably an efter);
- a condition on more than one day;
- a rest too short to measure.

Run ``python -m capillary.inventory`` for a summary, and ``--out`` to write the
tables.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from typing import Optional

import pandas as pd

METADATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'metadata')
STUDIES = {'ESMOKE': 'ESMOKE_timestamps.csv', 'ISMOKE': 'ISMOKE_timestamps.csv'}
ROLES = {'W': 'active', 'Q': 'control', 'S': 'active', 'C': 'control'}
#: Seconds of rest a recording needs: from 2 s after the start to 2 s before the occlusion.
MIN_REST_S = 30.0
REST_MARGIN_S = 2.0
#: A före this long after the day's first recording is flagged as probably an efter.
LATE_BEFORE_MIN = 45.0

_NAME = re.compile(r'^(?P<ismoke>ISMOKE_)?(?P<subject>FP\d+)_?(?P<condition>[WQSC])(?P<phase>före|efter)?'
                   r'(?P<suffix>\d)?(?:_försök(?P<attempt>\d+))?_(?P<date>\d{2}-[A-Za-z]{3}-\d{4})_'
                   r'(?P<time>\d{2}-\d{2}-\d{2})$')


@dataclass(frozen=True)
class RecordingName:
    """What a recording's name says."""

    name: str
    study: str
    subject: str
    condition: str               # W, Q, S or C
    phase: Optional[str]         # 'före', 'efter', or None when the name has neither
    attempt: int                 # 1, or N for försökN / a trailing digit
    started: datetime.datetime

    @property
    def role(self) -> str:
        return ROLES[self.condition]

    @property
    def date(self) -> datetime.date:
        return self.started.date()


def nfc(text: str) -> str:
    """`text` with composed characters. macOS file names spell ö as o + a combining mark, the metadata as one."""
    return unicodedata.normalize('NFC', text)


def parse_name(name: str) -> Optional[RecordingName]:
    """The parts of a recording's name, or None when it does not follow the pattern."""
    name = nfc(name)
    match = _NAME.match(name)
    if match is None:
        return None
    started = datetime.datetime.strptime(f'{match["date"]} {match["time"]}', '%d-%b-%Y %H-%M-%S')
    attempt = int(match['attempt'] or match['suffix'] or 1)
    return RecordingName(name=name, study='ISMOKE' if match['ismoke'] else 'ESMOKE', subject=match['subject'],
                         condition=match['condition'], phase=match['phase'], attempt=attempt, started=started)


def official_times(folder: str = METADATA) -> pd.DataFrame:
    """Both studies' official times, one row per recording: study, subject, occlusion_s, release_s, name."""
    frames = []
    for study, file_name in STUDIES.items():
        table = pd.read_csv(os.path.join(folder, file_name), sep=';', encoding='utf-8')
        table = table.rename(columns={'occlusion': 'occlusion_s', 'release': 'release_s', 'source_file': 'name'})
        table.insert(0, 'study', study)
        table['name'] = table['name'].map(nfc)
        frames.append(table)
    return pd.concat(frames, ignore_index=True)


def recordings(folder: str = METADATA) -> pd.DataFrame:
    """One row per recording: its name's parts, the official times, the usable rest, and issues found.

    Columns: name, study, subject, condition, role, phase, phase_inferred,
    attempt, date, time, occlusion_s, release_s, rest_s, usable, issues.
    """
    rows = []
    for row in official_times(folder).itertuples(index=False):
        parsed = parse_name(row.name)
        if parsed is None:
            raise ValueError(f'unexpected recording name: {row.name}')
        rest = float(row.occlusion_s) - 2 * REST_MARGIN_S
        rows.append({'name': row.name, 'study': parsed.study, 'subject': parsed.subject,
                     'condition': parsed.condition, 'role': parsed.role, 'phase': parsed.phase,
                     'phase_inferred': False, 'attempt': parsed.attempt, 'date': parsed.date,
                     'time': parsed.started.time(), 'started': parsed.started,
                     'occlusion_s': float(row.occlusion_s), 'release_s': row.release_s, 'rest_s': rest,
                     'usable': rest >= MIN_REST_S, 'issues': []})
    table = pd.DataFrame(rows).sort_values(['study', 'subject', 'started']).reset_index(drop=True)
    for _, day in table.groupby(['study', 'subject', 'date']):
        _check_day(table, day.index)
    for _, subject in table.groupby(['study', 'subject']):
        for condition, same in subject.groupby('condition'):
            if same['date'].nunique() > 1:
                for i in same.index:
                    table.at[i, 'issues'].append(f'{condition} recorded on {same["date"].nunique()} days')
    for i in table.index[~table['usable']]:
        table.at[i, 'issues'].append(f'rest only {table.at[i, "rest_s"]:.0f} s')
    table['issues'] = table['issues'].apply('; '.join)
    return table.drop(columns='started')


def _check_day(table: pd.DataFrame, index) -> None:
    """Flag what does not fit on one visit day, and infer a missing phase from the time of day."""
    day = table.loc[index]
    if day['condition'].nunique() > 1:
        for i in index:
            table.at[i, 'issues'].append('two conditions on one day: ' + ', '.join(sorted(day['condition'].unique())))
    first = day['started'].min()
    first_after = day.loc[day['phase'] == 'efter', 'started'].min()
    for i in index:
        if pd.isna(table.at[i, 'phase']):
            before_efter = pd.isna(first_after) or table.at[i, 'started'] < first_after
            table.at[i, 'phase'] = 'före' if before_efter else 'efter'
            table.at[i, 'phase_inferred'] = True
            table.at[i, 'issues'].append(f'name has no före/efter; taken as {table.at[i, "phase"]} from the time of day')
        late = (table.at[i, 'started'] - first).total_seconds() / 60
        if table.at[i, 'phase'] == 'före' and late > LATE_BEFORE_MIN:
            table.at[i, 'issues'].append(f'före {late:.0f} min after the day\'s first recording: probably an efter')


def participants(table: pd.DataFrame) -> pd.DataFrame:
    """One row per participant: the visits, the recordings chosen for the aims, and whether each aim can use them.

    ``aim1`` and ``aim2`` are 'yes', 'check' (usable, but a chosen recording
    has an issue to check in DynCap) or 'no' (something is missing).
    """
    rows = []
    for (study, subject), recs in table.groupby(['study', 'subject'], sort=False):
        row = {'study': study, 'subject': subject}
        visits = recs.groupby('date')
        row['visits'] = ', '.join(f'{date:%Y-%m-%d} {"/".join(sorted(group["condition"].unique()))}'
                                  for date, group in visits)
        chosen = {}
        for role in ('active', 'control'):
            days = recs[recs['role'] == role]['date'].unique()
            row[f'{role}_day'] = f'{max(days):%Y-%m-%d}' if len(days) else ''
            day_recs = recs[(recs['role'] == role) & (recs['date'] == max(days))] if len(days) else recs.iloc[0:0]
            for phase in ('före', 'efter'):
                candidates = day_recs[(day_recs['phase'] == phase) & day_recs['usable']]
                chosen[(role, phase)] = candidates.iloc[-1] if len(candidates) else None
                row[f'{role}_{phase}'] = chosen[(role, phase)]['name'] if len(candidates) else ''
                row[f'{role}_{phase}_alternatives'] = ', '.join(candidates['name'].iloc[:-1])
        if row['active_day'] and row['control_day']:
            row['days_apart'] = abs((pd.Timestamp(row['active_day']) - pd.Timestamp(row['control_day'])).days)
            row['first_visit'] = 'active' if row['active_day'] < row['control_day'] else 'control'
        else:
            row['days_apart'], row['first_visit'] = None, ''
        row['aim1'] = _status([chosen[('active', 'före')], chosen[('control', 'före')]])
        row['aim2'] = _status([chosen[key] for key in chosen])
        row['issues'] = '; '.join(sorted({issue for issues in recs['issues'] if issues for issue in issues.split('; ')}))
        rows.append(row)
    return pd.DataFrame(rows)


def mark_use(table: pd.DataFrame, people: pd.DataFrame) -> pd.DataFrame:
    """`table` with a ``used_for`` column: which aims use each recording, and as what (e.g. 'aims 1, 2: active före')."""
    table = table.copy()
    table['used_for'] = ''
    names = table.set_index('name').index
    for person in people.itertuples(index=False):
        for role in ('active', 'control'):
            for phase in ('före', 'efter'):
                name = getattr(person, f'{role}_{phase}')
                aims = [aim for aim, status in (('1', person.aim1), ('2', person.aim2))
                        if status != 'no' and (aim == '2' or phase == 'före')]
                if name and aims:
                    label = f'aim{"s" if len(aims) > 1 else ""} {", ".join(aims)}'
                    table.loc[names == name, 'used_for'] = f'{label}: {role} {phase}'
    return table


def _status(needed) -> str:
    if any(recording is None for recording in needed):
        return 'no'
    return 'check' if any(recording['issues'] for recording in needed) else 'yes'


def video_stems(folder: str) -> set:
    """Names (without extension) of the videos directly inside `folder`."""
    try:
        return {nfc(os.path.splitext(name)[0]) for name in os.listdir(folder)
                if name.lower().endswith(('.avi', '.mp4'))}
    except OSError:
        return set()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python -m capillary.inventory', description=__doc__.split('\n\n')[0])
    parser.add_argument('--out', help='folder to write recordings.csv and participants.csv to')
    parser.add_argument('--have', action='append', default=[],
                        help='a folder with downloaded videos; the summary lists which chosen ones are missing')
    args = parser.parse_args(argv)
    people = participants(recordings())
    table = mark_use(recordings(), people)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        table.to_csv(os.path.join(args.out, 'recordings.csv'), index=False)
        people.to_csv(os.path.join(args.out, 'participants.csv'), index=False)
    print(f'{len(table)} recordings of {len(people)} participants; {int((~table["usable"]).sum())} with too little rest')
    for study, group in people.groupby('study'):
        counts = {aim: group[aim].value_counts().to_dict() for aim in ('aim1', 'aim2')}
        print(f'{study}: {len(group)} participants; aim 1 {counts["aim1"]}; aim 2 {counts["aim2"]}')
    used = table[table['used_for'] != '']
    print(f'used for the aims: {len(used)} recordings, {int(used["used_for"].str.contains("1").sum())} of them for aim 1')
    if args.have:
        have = set().union(*(video_stems(folder) for folder in args.have))
        missing = used[~used['name'].isin(have)]
        print(f'downloaded: {len(used) - len(missing)}; still to download: {len(missing)} '
              f'({int(missing["used_for"].str.contains("1").sum())} of them for aim 1)')
        if args.out:
            missing[['name', 'study', 'subject', 'used_for']].to_csv(os.path.join(args.out, 'to_download.csv'), index=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
