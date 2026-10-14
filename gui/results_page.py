"""Results page: the files, time points and saved data sets of one recording."""

from __future__ import annotations

import logging
import math
import os
import queue
import threading
import tkinter as tk
from functools import partial
from tkinter import ttk

from PIL import Image, ImageTk

from capillary import datasets, pattern_shift
from capillary.video import probe_video

from . import tasks
from .dialogs import ImageViewer, confirm, show_error
from .media import format_time
from .theme import COLORS, FONTS, icon, px
from .widgets import ScrollFrame, Tooltip

log = logging.getLogger(__name__)

THUMB_WIDTH = 230
ROLE_TITLES = {
    'velocity': 'Velocity',
    'velocity_above_zero': 'Velocity, negative set to 0',
    'correlation': 'Correlation',
    'velocity_above_zero_with_correlation': 'Velocity with correlation bands',
    'line_velocity': 'Velocity along the line',
    'space_time': 'Space-time diagram',
}
#: Chip text and colours of each kind of data set, and the page that measures it.
KIND_LOOK = {
    'line': ('CENTRE LINE', 'success', 'success_soft', 'line'),
    'velocity': ('TWO BOXES', 'accent', 'accent_soft', 'analyze'),
}
#: What the direction check of an arterial limb found, as a card states it.
LIMB_TEXT = {
    'arterial': ('Arterial limb: the pooled flow runs towards the apex.', 'Success.Panel.TLabel'),
    'venous': ('Drawn as the arterial limb, but the pooled flow runs towards the base: the venous limb.',
               'Warning.Panel.TLabel'),
    'unknown': ('Arterial limb not confirmed: the pooled flow was not resolved.', 'Muted.Panel.TLabel'),
}
#: Which end of a whole-loop line the direction of its flow puts on the arterial limb, as a card states it.
LOOP_TEXT = {
    'start': ('Whole loop: the flow runs along the line, so its start is on the arterial limb.',
              'Success.Panel.TLabel'),
    'end': ('Whole loop: the flow runs against the line, so its end is on the arterial limb.',
            'Success.Panel.TLabel'),
    'unknown': ('Whole loop: the pooled flow was not resolved, so the arterial limb is unknown.', 'Muted.Panel.TLabel'),
}
#: A whole loop whose two limbs moved opposite ways along the line.
MOVEMENT_TEXT = ('The two limbs moved opposite ways along the line, as the picture moving does, not flow: the '
                 'study summary does not count this loop.', 'Warning.Panel.TLabel')


def _report_thumbnail(path, width):
    image = Image.open(path).convert('RGBA')
    background = Image.new('RGBA', image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert('RGB')
    image.thumbnail((width, width), Image.Resampling.LANCZOS)
    return image


def _velocity_text(value):
    if value is None or not math.isfinite(value):
        return '–'
    return f'{value:.4f}' if abs(value) < 0.1 else f'{value:.3f}'


class ResultsPage(ttk.Frame):
    key = 'results'
    title = 'Results'
    uses_library = True

    def __init__(self, parent, app):
        super().__init__(parent, style='TFrame')
        self.app = app
        self.recording = None
        self._token = 0
        self._results: queue.Queue = queue.Queue()
        self._cards = {}
        self._photos = []
        self._focus = None
        self.scroll = ScrollFrame(self, background=COLORS['bg'])
        self.scroll.canvas.configure(bg=COLORS['bg'])
        self.scroll.body.configure(style='TFrame', padding=(px(24), px(18), px(24), px(24)))
        self.scroll.pack(fill='both', expand=True)

    # ------------------------------------------------------------------- recordings
    def show_recording(self, recording):
        self.recording = recording
        self._rebuild()

    def on_show(self):
        pass

    def on_hide(self):
        pass

    def handle_key(self, event):
        return False

    def focus_dataset(self, kind, name):
        self._focus = (kind, name)
        self._highlight()

    def _rebuild(self):
        self._token += 1
        token = self._token
        body = self.scroll.body
        for child in body.winfo_children():
            child.destroy()
        self._cards = {}
        self._photos = []
        recording = self.recording
        if recording is None:
            ttk.Label(body, text='Select a recording', style='Title.TLabel').pack(anchor='w')
            ttk.Label(body, text='Its files, time points and saved data sets appear here.', style='Muted.TLabel').pack(
                anchor='w', pady=(px(4), 0))
            return

        header = ttk.Frame(body, style='TFrame')
        header.pack(fill='x')
        ttk.Label(header, text=recording.stem, style='Title.TLabel').pack(side='left')
        ttk.Button(header, text='Show in folder', image=icon('folder', 14, COLORS['muted']), compound='left',
                   command=lambda: self.app.open_folder(recording.video)).pack(side='right')
        ttk.Button(header, text='Two boxes', command=lambda: self.app.show_page('analyze')).pack(
            side='right', padx=(0, px(8)))
        ttk.Button(header, text='Measure along a line', command=lambda: self.app.show_page('line')).pack(
            side='right', padx=(0, px(8)))

        self._files_card(body, recording)
        self._time_points_card(body, recording)

        names = [(kind, name) for kind in ('line', 'velocity') for name in recording.datasets_of(kind)]
        title = ttk.Frame(body, style='TFrame')
        title.pack(fill='x', pady=(px(22), px(8)))
        ttk.Label(title, text='Data sets', style='Subtitle.TLabel').pack(side='left')
        ttk.Label(title, text=f'{len(names)}' if names else '', style='Muted.TLabel').pack(side='left',
                                                                                           padx=(px(8), 0))
        if not names:
            empty = tk.Frame(body, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'])
            empty.pack(fill='x')
            ttk.Label(empty, text='No data sets yet. Measure velocity on the Centre line page (or with two boxes); '
                                  'each measurement is saved here with its report.', style='Muted.Panel.TLabel',
                      padding=(px(16), px(16))).pack(anchor='w')
            return
        for kind, name in names:
            self._cards[(kind, name)] = self._dataset_card(body, kind, name)
        self._loader = threading.Thread(target=self._load, args=(token, recording, names), name='results', daemon=True)
        self._loader.start()
        self.after(60, self._poll, token)

    def shutdown(self, timeout=3.0):
        """Stop loading cards (after the current one) and wait for the loader."""
        self._token += 1
        loader = getattr(self, '_loader', None)
        if loader is not None:
            loader.join(timeout)

    # ------------------------------------------------------------------------ cards
    def _card(self, parent, padding=(px(16), px(14))):
        outer = tk.Frame(parent, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'], bd=0)
        outer.pack(fill='x', pady=(px(10), 0))
        inner = ttk.Frame(outer, style='Panel.TFrame', padding=padding)
        inner.pack(fill='both', expand=True)
        inner.outer = outer
        return inner

    def _files_card(self, parent, recording):
        card = self._card(parent)
        ttk.Label(card, text='FILES', style='Section.Panel.TLabel').grid(row=0, column=0, columnspan=4, sticky='w',
                                                                         pady=(0, px(8)))
        rows = (
            ('Raw recording', recording.raw, None),
            ('Stabilized video', recording.stabilized,
             (('Re-stabilize' if recording.is_stabilized else 'Stabilize'), lambda: self.app.stabilize(recording))
             if recording.raw else None),
        )
        for row, (label, path, action) in enumerate(rows, start=1):
            present = path is not None
            ttk.Label(card, image=icon('ok' if present else 'close', 13,
                                       COLORS['success'] if present else COLORS['faint']),
                      style='Panel.TLabel').grid(row=row, column=0, sticky='w', pady=px(3))
            ttk.Label(card, text=label, style='Bold.Panel.TLabel' if present else 'Muted.Panel.TLabel').grid(
                row=row, column=1, sticky='w', padx=(px(8), px(16)))
            detail = ''
            if present:
                try:
                    size = os.path.getsize(path) / 1e9
                    info = probe_video(path)
                    detail = (f'{os.path.basename(path)}  ·  {size:.2f} GB  ·  {info.frame_count} frames at '
                              f'{info.fps:g} fps  ·  {format_time(info.duration_s)}')
                except (OSError, FileNotFoundError):
                    detail = os.path.basename(path)
            else:
                detail = 'none'
            ttk.Label(card, text=detail, style='Muted.Panel.TLabel').grid(row=row, column=2, sticky='w')
            if action is not None:
                text, command = action
                ttk.Button(card, text=text, style='Small.Ghost.TButton', command=command).grid(row=row, column=3,
                                                                                               sticky='e')
        card.columnconfigure(2, weight=1)

    def _time_points_card(self, parent, recording):
        points = datasets.load_time_points(datasets.time_points_file(self.app.folder.statistics, recording.stem))
        card = self._card(parent)
        ttk.Label(card, text='TIME POINTS', style='Section.Panel.TLabel').pack(anchor='w', pady=(0, px(6)))
        text = ('   '.join(format_time(p) for p in points) if points
                else 'None marked. Mark events on the Centre line or Two boxes page (M).')
        ttk.Label(card, text=text, style='Mono.Panel.TLabel' if points else 'Muted.Panel.TLabel',
                  wraplength=px(900), justify='left').pack(anchor='w')

    def _dataset_card(self, parent, kind, name):
        card = self._card(parent)
        head = ttk.Frame(card, style='Panel.TFrame')
        head.pack(fill='x')
        chip, foreground, background, _ = KIND_LOOK[kind]
        tk.Label(head, text=chip, font=FONTS['section'], fg=COLORS[foreground], bg=COLORS[background],
                 padx=px(7), pady=px(2)).pack(side='left')
        ttk.Label(head, text=name if name else '(no name)', style='Subtitle.Panel.TLabel').pack(side='left',
                                                                                              padx=(px(10), 0))
        card.when = ttk.Label(head, text='', style='Muted.Panel.TLabel')
        card.when.pack(side='right')
        card.summary = ttk.Frame(card, style='Panel.TFrame')
        card.summary.pack(fill='x', pady=(px(8), 0))
        ttk.Label(card.summary, text='Loading…', style='Faint.Panel.TLabel').pack(anchor='w')
        card.images = ttk.Frame(card, style='Panel.TFrame')
        card.images.pack(fill='x', pady=(px(10), 0))
        actions = ttk.Frame(card, style='Panel.TFrame')
        actions.pack(fill='x', pady=(px(12), 0))
        regenerate = ttk.Button(actions, text='Regenerate report', command=partial(self._regenerate, kind, name))
        regenerate.pack(side='left')
        Tooltip(regenerate, 'Write the report of this data set again, e.g. after adding time points. The '
                            'measured data is not changed.' if kind == 'velocity' else
                            'Measure the saved space-time diagram again and write its report, e.g. after adding '
                            'time points. The video is not needed.')
        card.restore = ttk.Button(actions, text='Restore positions', command=partial(self._restore, kind, name))
        card.restore.pack(side='left', padx=(px(8), 0))
        card.restore.state(['disabled'])
        Tooltip(card.restore, 'Open the recording with the line (or boxes) and range this data set was measured '
                              'with.')
        ttk.Button(actions, text='Show files', style='Ghost.TButton',
                   command=partial(self._show_files, kind, name)).pack(side='left', padx=(px(8), 0))
        ttk.Button(actions, text='Move to trash', image=icon('trash', 13, COLORS['danger']), compound='left',
                   style='Ghost.TButton', command=partial(self._delete, kind, name)).pack(side='right')
        card.record = None
        return card

    # ----------------------------------------------------------------------- loading
    def _load(self, token, recording, names):
        for kind, name in names:
            if token != self._token:
                return
            try:
                info = tasks.dataset_info(self.app.folder, recording.stem, name, kind)
                thumbs = []
                for role, path in info['images']:
                    try:
                        thumbs.append((role, path, _report_thumbnail(path, px(THUMB_WIDTH))))
                    except OSError:
                        log.warning('Could not read %s', path, exc_info=True)
                info['thumbs'] = thumbs
            except Exception as exc:  # noqa: BLE001 - shown on the card
                log.warning('Could not load data set %s %s', kind, name, exc_info=True)
                info = {'error': str(exc)}
            self._results.put((token, kind, name, info))

    def _poll(self, token):
        if token != self._token:
            return
        done = False
        while True:
            try:
                result_token, kind, name, info = self._results.get_nowait()
            except queue.Empty:
                break
            if result_token == self._token:
                self._fill(kind, name, info)
                done = (kind, name) == list(self._cards)[-1]
        if not done:
            self.after(80, self._poll, token)
        else:
            self._highlight()

    def _fill(self, kind, name, info):
        card = self._cards.get((kind, name))
        if card is None:
            return
        for child in card.summary.winfo_children():
            child.destroy()
        if 'error' in info:
            ttk.Label(card.summary, text=f'Could not be read: {info["error"]}', style='Danger.Panel.TLabel').pack(
                anchor='w')
            return
        if info.get('modified'):
            card.when.configure(text=f'{info["modified"]:%d %b %Y, %H:%M}')
        record, summary = info.get('record'), info.get('summary')
        card.record = record
        lines = []
        if summary and kind == 'line':
            lines += _line_summary_lines(summary)
        elif summary:
            median = summary.get('median', float('nan'))
            if median is not None and math.isfinite(median):
                lines.append((f'Median velocity {_velocity_text(median)} mm/s   (middle 50 %: '
                              f'{_velocity_text(summary.get("q25"))} – {_velocity_text(summary.get("q75"))})',
                              'Bold.Panel.TLabel'))
            else:
                lines.append(('No velocity could be resolved', 'Bold.Panel.TLabel'))
            resolved = summary.get('resolved_fraction', 0) or 0
            zero = summary.get('zero_lag_fraction')
            parts = [f'{100 * resolved:.0f} % of windows resolved']
            if zero is not None and math.isfinite(zero):
                parts.append(f'{100 * zero:.0f} % lag 0 (too fast, or a change both boxes saw at once)')
            r = summary.get('median_correlation')
            if r is not None and math.isfinite(r):
                parts.append(f'median correlation {r:.2f}')
            lines.append(('   ·   '.join(parts), 'Muted.Panel.TLabel'))
        if record:
            lines.append((_describe_record(record), 'Muted.Panel.TLabel'))
            card.restore.state(['!disabled'])
        else:
            lines.append(('Made before data sets recorded their settings: the box positions, range and '
                          'calibration of this measurement are not known.', 'Faint.Panel.TLabel'))
        if not info.get('complete', True):
            lines.append(('Some files of this data set are missing.', 'Danger.Panel.TLabel'))
        for text, style in lines:
            ttk.Label(card.summary, text=text, style=style, wraplength=px(900), justify='left').pack(anchor='w',
                                                                                                    pady=(px(1), 0))
        for child in card.images.winfo_children():
            child.destroy()
        if not info.get('thumbs'):
            ttk.Label(card.images, text='No report images yet: regenerate the report.', style='Faint.Panel.TLabel').pack(
                anchor='w')
            return
        cells = []
        for role, path, image in info['thumbs']:
            photo = ImageTk.PhotoImage(image)
            self._photos.append(photo)
            cell = ttk.Frame(card.images, style='Panel.TFrame')
            button = tk.Label(cell, image=photo, bd=0, cursor='hand2', highlightthickness=1,
                              highlightbackground=COLORS['border'])
            button.pack()
            button.bind('<Button-1>', lambda e, p=path, r=role: self._open_image(p, r))
            Tooltip(button, 'Click to enlarge')
            ttk.Label(cell, text=ROLE_TITLES.get(role, role), style='Faint.Panel.TLabel').pack(anchor='w',
                                                                                             pady=(px(3), 0))
            cells.append(cell)
        _reflow(card.images, cells, px(THUMB_WIDTH) + px(14))

    def _highlight(self):
        if self._focus is None:
            return
        for key, card in self._cards.items():
            card.outer.configure(highlightbackground=COLORS['accent'] if key == self._focus else COLORS['border'],
                                 highlightthickness=2 if key == self._focus else 1)
        card = self._cards.get(self._focus)
        if card is not None:
            self.update_idletasks()
            total = max(1, self.scroll.body.winfo_height())
            self.scroll.canvas.yview_moveto(max(0, card.outer.winfo_y() - px(10)) / total)

    # ----------------------------------------------------------------------- actions
    def _open_image(self, path, role):
        ImageViewer(self, path, title=f'{ROLE_TITLES.get(role, role)}  ·  {os.path.basename(path)}',
                    on_open_folder=lambda: self.app.open_folder(path))

    def _show_files(self, kind, name):
        folder = self.app.folder
        files = (datasets.line_dataset_files if kind == 'line' else datasets.velocity_dataset_files)(
            folder.statistics, self.recording.stem, name)
        first = next((path for path in files.values() if os.path.exists(path)), None)
        self.app.open_folder(first or folder.statistics)

    def _restore(self, kind, name):
        card = self._cards.get((kind, name))
        if card is None or not card.record:
            return
        page = KIND_LOOK[kind][3]
        self.app.show_page(page)
        if self.app.pages[page].apply_record(card.record):
            self.app.set_status(f'Positions and range of "{name}" restored.')

    def _regenerate(self, kind, name):
        recording = self.recording
        card = self._cards.get((kind, name))
        record = card.record if card is not None else None
        settings = self.app.settings
        mm_per_pixel = (record or {}).get('mm_per_pixel') or settings.mm_per_pixel
        fps = ((record or {}).get('video') or {}).get('fps')
        if not fps:
            try:
                fps = probe_video(recording.video).fps
            except (OSError, FileNotFoundError):
                fps = None
        fps = fps or 30.0
        stem = recording.stem
        points = datasets.load_time_points(datasets.time_points_file(self.app.folder.statistics, stem))
        regenerate = tasks.regenerate_line_report if kind == 'line' else tasks.regenerate_velocity_report
        work = partial(regenerate, folder=self.app.folder, stem=stem, name=name, fps=fps,
                       mm_per_pixel=mm_per_pixel, time_points=points)
        source = 'recorded with the data set' if record and record.get('mm_per_pixel') else 'from the settings'

        def done(_result):
            self.app.set_status(f'Report of "{name}" written again ({mm_per_pixel:g} mm per pixel, {source}).')
            if self.recording is not None and self.recording.stem == stem:
                self._focus = (kind, name)
                self._rebuild()

        def failed(exc):
            show_error(self, 'The report could not be written', str(exc) or type(exc).__name__,
                       'The details are in capillaroscopy.log.')

        job = self.app.jobs.submit(f'Report · {stem} · {name}', work, lane='analysis', on_done=done, on_error=failed,
                                   key=('report', stem, kind, name))
        if job is None:
            self.app.set_status('That report is already being written.')

    def _delete(self, kind, name):
        recording = self.recording
        folder = self.app.folder
        paths = datasets.dataset_paths(folder.statistics, folder.reports, recording.stem, name, kind)
        if not paths:
            return
        if any(job.key and recording.stem in job.key for job in self.app.jobs.active()):
            show_error(self, 'Recording in use', 'Wait until the jobs working on this recording have finished.')
            return
        listing = '\n'.join(tasks.relative_path(folder, path) for path in paths[:12])
        if len(paths) > 12:
            listing += f'\n… and {len(paths) - 12} more'
        what = 'centre-line' if kind == 'line' else 'two-box'
        if not confirm(self, 'Move data set to trash?', f'The {what} data set "{name}" of {recording.stem} and its '
                       f'report ({len(paths)} files) are moved to the .trash folder in the data folder.',
                       listing, ok='Move to trash', danger=True):
            return
        try:
            target = tasks.move_to_trash(folder, paths, f'{recording.stem} {name}')
        except OSError as exc:
            show_error(self, 'Could not move the files', str(exc))
            return
        self.app.set_status(f'Moved "{name}" to {os.path.relpath(target, folder.root)}.')
        self.app.refresh_library()


def _reflow(container, cells, cell_width):
    """Lay `cells` out in as many columns as fit, again whenever `container` is resized."""
    state = {'columns': None}

    def arrange(_event=None):
        columns = max(1, container.winfo_width() // cell_width)
        if columns == state['columns']:
            return
        state['columns'] = columns
        for index, cell in enumerate(cells):
            cell.grid(row=index // columns, column=index % columns, sticky='nw', padx=(0, px(14)), pady=(0, px(10)))

    container.bind('<Configure>', arrange)
    container.after_idle(arrange)


def _finite(value):
    """Whether `value` is a finite number (a summary read back from JSON has None for NaN)."""
    try:
        return math.isfinite(value)
    except TypeError:
        return False


def _line_summary_lines(summary):
    """``(text, style)`` lines for a centre-line data set: its pattern shift, its 3-s blocks, the limb check."""
    lines = []
    if 'pattern_shift_snr' in summary:
        pooled, snr = summary.get('pattern_shift_velocity_mm_s'), summary.get('pattern_shift_snr')
        snr_text = f'signal-to-noise {snr:.1f}' if _finite(snr) else 'no estimate'
        if _finite(pooled):
            text = f'Pattern shift over the range {_velocity_text(pooled)} mm/s'
            low, high = summary.get('pattern_shift_ci95_low_mm_s'), summary.get('pattern_shift_ci95_high_mm_s')
            if _finite(low) and _finite(high):
                text += f'   (95% interval {_velocity_text(low)} – {_velocity_text(high)})'
            lines.append((text, 'Bold.Panel.TLabel'))
            parts = [snr_text]
            halves = ('first_half', 'second_half')
            if any(_finite(summary.get(f'pattern_shift_{half}_snr')) for half in halves):
                velocities = [summary.get(f'pattern_shift_{half}_mm_s') for half in halves]
                parts.append('halves ' + ' / '.join(_velocity_text(v) if _finite(v) else 'not resolved'
                                                    for v in velocities))
            lines.append(('   ·   '.join(parts), 'Muted.Panel.TLabel'))
        else:
            lines.append((f'Pattern shift over the range: not resolved ({snr_text}, {pattern_shift.MIN_SNR:.0f} '
                          'needed)', 'Bold.Panel.TLabel'))
    else:
        lines.append(('Pattern shift: not computed for this data set; regenerate its report.', 'Faint.Panel.TLabel'))
    median, resolved = summary.get('median'), summary.get('resolved_fraction') or 0
    parts = [f'{100 * resolved:.0f} % of 3-s blocks resolved']
    if _finite(median):
        parts.insert(0, f'3-s blocks: median {_velocity_text(median)} mm/s (middle 50 %: '
                        f'{_velocity_text(summary.get("q25"))} – {_velocity_text(summary.get("q75"))})')
    snr = summary.get('median_snr')
    if _finite(snr):
        parts.append(f'median signal-to-noise {snr:.0f}')
    lines.append(('   ·   '.join(parts), 'Muted.Panel.TLabel'))
    if _finite(median) and resolved < 0.25:
        lines.append(('Few 3-s blocks were resolved, so their median is uncertain.', 'Warning.Panel.TLabel'))
    if summary.get('limb_check') in LIMB_TEXT:
        lines.append(LIMB_TEXT[summary['limb_check']])
    if summary.get('arterial_end') in LOOP_TEXT:
        lines.append(LOOP_TEXT[summary['arterial_end']])
    if summary.get('loop_movement'):
        lines.append(MOVEMENT_TEXT)
    phase = summary.get('phase') or ''
    if '+' in phase:
        lines.append((f'The range covers {phase.replace(" + ", ", ")}: the pooled velocity mixes them.',
                      'Warning.Panel.TLabel'))
    return lines


def _describe_record(record):
    parts = []
    frames = record.get('frames') or {}
    video = record.get('video') or {}
    fps = video.get('fps') or 30
    if 'first' in frames and 'last' in frames:
        parts.append(f'frames {frames["first"]}–{frames["last"]} ({format_time(frames["first"] / fps)} – '
                     f'{format_time(frames["last"] / fps)})')
    phase = (record.get('summary') or {}).get('phase')
    if phase:
        parts.append(f'{phase} by the official times')
    boxes = record.get('boxes')
    if boxes:
        parts.append(f'Box 1 at ({boxes["box1"]["x"]}, {boxes["box1"]["y"]}), Box 2 at ({boxes["box2"]["x"]}, '
                     f'{boxes["box2"]["y"]}), {boxes["width_px"]}×{boxes["height_px"]} px')
        if record.get('distance_px') is not None:
            parts.append(f'{record["distance_px"]:.1f} px apart')
    line = record.get('line')
    if line:
        length = line.get('length_px')
        parts.append(f'line of {len(line.get("points", []))} points, '
                     + (f'{length:.0f} px ({line.get("length_um", 0):.0f} µm)' if length else 'length unknown')
                     + (f', {line["role"]}' if line.get('role') else ''))
    if record.get('mm_per_pixel'):
        parts.append(f'{record["mm_per_pixel"]:g} mm/px')
    if record.get('observer'):
        parts.append(f'by {record["observer"]}')
    if video.get('folder'):
        parts.append(f'from {video["folder"]}')
    commit = (record.get('software') or {}).get('git_commit')
    if commit:
        parts.append(f'code {commit[:7]}')
    return '   ·   '.join(parts)
