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
- **Aim 2** (before-to-after change on the nicotine visit) needs the före and
  efter recordings of the active visit; the control visit is not used.

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

`recording_phases` turns one recording's official times into frames of its
video: the rest, the occlusion and the time after release, as the measure
pages offer them for the range.
"""

from __future__ import annotations

import argparse
import datetime
import functools
import math
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
#: The phases of every recording, in order.
PHASES = ('rest', 'occlusion', 'after release')

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


@functools.lru_cache(maxsize=4)
def _times_by_name(folder: str) -> dict:
    """``{name: (occlusion_s, release_s or None)}`` from the official times, read once per folder."""
    return {row.name: (float(row.occlusion_s), None if pd.isna(row.release_s) else float(row.release_s))
            for row in official_times(folder).itertuples(index=False)}


@dataclass(frozen=True)
class Phases:
    """One recording's phases as frames of its video, from its official times.

    `windows` gives each phase's first and last frame (inclusive), kept
    `REST_MARGIN_S` away from the events around it: the rest from 2 s after
    the start to 2 s before the occlusion, the occlusion from 2 s after it to
    2 s before the release, and after release up to 2 s before the video ends.
    Without a release time only the rest is given. When an official time lies
    after the end of the video, no window is given, because the times do not
    fit it. `notes` says what the user should know about the times.
    """

    occlusion_s: float
    release_s: Optional[float]
    duration_s: float
    windows: dict
    notes: tuple

    def phase_of(self, first: int, last: int, fps: float) -> str:
        """The phases frames `first`..`last` lie in, by the official times themselves (no margins).

        'rest', 'occlusion', 'after release', or several joined by ' + '. Without
        a release time, frames after the occlusion began are 'occlusion or later'.
        '' when the times do not fit the video.
        """
        if not self.windows:
            return ''
        start, stop = first / fps, (last + 1) / fps
        spans = [('rest', 0.0, self.occlusion_s)]
        if self.release_s is None:
            spans.append(('occlusion or later', self.occlusion_s, math.inf))
        else:
            spans += [('occlusion', self.occlusion_s, self.release_s), ('after release', self.release_s, math.inf)]
        return ' + '.join(phase for phase, low, high in spans if start < high and stop > low)


def recording_phases(name: str, fps: float, frame_count: int, folder: str = METADATA) -> Optional[Phases]:
    """The phases of the recording `name` in its video (`fps`, `frame_count`); None without official times."""
    times = _times_by_name(folder).get(nfc(name))
    if times is None or not fps or fps <= 0 or frame_count < 1:
        return None
    occlusion, release = times
    duration = frame_count / fps
    late = [(event, seconds) for event, seconds in (('occlusion', occlusion), ('release', release))
            if seconds is not None and seconds > duration]
    if late:
        listed = ' and '.join(f'{event} ({seconds:.1f} s)' for event, seconds in late)
        return Phases(occlusion, release, duration, {}, (
            f'The official {listed} {"lies" if len(late) == 1 else "lie"} after the end of the video '
            f'({duration:.1f} s at {fps:g} fps), so the times do not fit it. Check its frame rate '
            '(metadata/README.md).',))
    spans = {'rest': (REST_MARGIN_S, occlusion - REST_MARGIN_S)}
    if release is not None:
        spans['occlusion'] = (occlusion + REST_MARGIN_S, release - REST_MARGIN_S)
        spans['after release'] = (release + REST_MARGIN_S, duration - REST_MARGIN_S)
    windows = {}
    for phase, (start_s, stop_s) in spans.items():
        first = math.ceil(round(start_s * fps, 6))
        last = min(math.ceil(round(stop_s * fps, 6)) - 1, frame_count - 1)
        if last >= first:
            windows[phase] = (first, last)
    notes = []
    rest = occlusion - 2 * REST_MARGIN_S
    if rest < MIN_REST_S:
        notes.append(f'Only {max(rest, 0.0):.0f} s of rest before the occlusion; the aims need {MIN_REST_S:.0f} s.')
    if release is None:
        notes.append('No official release time, so only the rest is known.')
    return Phases(occlusion, release, duration, windows, tuple(notes))


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
        row['aim2'] = _status([chosen[('active', 'före')], chosen[('active', 'efter')]])
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
                aims = [aim for aim, status, uses in (('1', person.aim1, phase == 'före'),
                                                       ('2', person.aim2, role == 'active'))
                        if status != 'no' and uses]
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
