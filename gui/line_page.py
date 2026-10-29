"""Centre line page: red-cell velocity from the slope of the streaks in a space-time diagram.

The user clicks points along the middle of one capillary, from where the blood
comes from to where it goes. In every frame the brightness along that line is
sampled; stacked over time this is the space-time diagram, in which red cells
and plasma gaps moving along the vessel draw slanted streaks. Their slope is
the speed (`capillary.spacetime`). The panel shows the diagram of the frames
around the playhead with the slope found, so every estimate can be checked by
eye, and the measurement repeats it block by block over the chosen frames.

The measurement also pools the pattern shift over the whole range
(`capillary.pattern_shift`), which measures flow too faint for single blocks,
as at rest. A line can be marked as a capillary loop's arterial limb, drawn
from its base to the apex: the direction of the pooled flow then shows
whether it is the arterial limb (towards the apex) or the venous one. Or it
can go round a whole loop, from the base of one limb over the apex to the
base of the other (since 2026-10-14), which measures resting flow in more
loops: the direction then shows which end of the line lies on the arterial
limb, and each limb is measured on its own as a check against movement.

The lines of the recording's saved data sets are drawn faintly, so that a
capillary is not measured twice. During blind placement (`gui.blind`) the
preview and every result are hidden, and the range is the official rest.

On a stabilized video a dashed outline shows where every frame of the range
has picture: where the picture moved, the stabilized frame has a black strip
along its edge, and a line that reaches it is refused
(`capillary.stabilize.check_picture`, since 2026-10-14).
"""

from __future__ import annotations

import logging
import math
import re
import tkinter as tk
from functools import partial
from tkinter import ttk

import numpy as np
from PIL import Image, ImageDraw, ImageTk

from capillary import datasets, pattern_shift, spacetime, stabilize

from . import blind, tasks
from .jobs import LatestOnlyWorker
from .measure_page import INSPECTOR_WIDTH, MeasurePage, stat
from .theme import COLORS, FONTS, icon, px
from .video_view import Tool
from .widgets import InfoRow, Tooltip, section, separator

log = logging.getLogger(__name__)

PREVIEW_HEIGHT = 130
ARTERIAL, WHOLE_LOOP = pattern_shift.ARTERIAL_LIMB, pattern_shift.WHOLE_LOOP
#: What a line can follow: the role saved with its data set ('' for any stretch), the option's text, the
#: start of the data set names suggested for it and the option's tooltip.
ROLES = (
    ('', 'Any stretch of a capillary', 'set',
     'Click along the capillary in the direction of flow: positive velocity runs from the first point to the last.'),
    (ARTERIAL, 'Arterial limb, from its base to the apex', 'limb',
     'The line follows the arterial limb of a capillary loop: click at the base of the limb and follow it to the '
     'apex, the tip of the loop. The measurement checks the direction of the flow pooled over the range: blood '
     'flows up the arterial limb towards the apex and down the venous limb. Saved with the data set.'),
    (WHOLE_LOOP, 'Whole loop, base to base over the apex', 'loop',
     'The line goes round a whole capillary loop: click at the base of one limb, follow it up to the apex, over '
     'the apex and down the other limb to its base. Flow runs one way round the loop, so the line collects the '
     'signal of both limbs: at rest it measured more loops than single limbs did. The direction of the pooled '
     'flow shows which limb is arterial, and each limb is measured on its own as a check against movement. '
     'Saved with the data set.'),
)
ROLE_NAMES = {role: base for role, _, base, _ in ROLES}
#: What the direction check of an arterial limb found (`capillary.pattern_shift.limb_from_direction`):
#: the status icon and the text shown with a result.
LIMB_CHECKS = {
    'arterial': ('ok', 'Arterial limb: the flow runs towards the apex.'),
    'venous': ('warning', 'The flow runs towards the base: this is the venous limb, or the line was drawn from '
                          'the apex. For the arterial velocity, measure the loop\'s other limb from its base.'),
    'unknown': ('info', 'Arterial limb not confirmed: the pooled flow was not resolved, so its direction is '
                        'unknown.'),
}
#: Which end of a whole-loop line lies on the arterial limb (`capillary.pattern_shift.loop_from_direction`).
LOOP_CHECKS = {
    'start': ('ok', 'The flow runs along the line, so the limb where it starts is the arterial limb.'),
    'end': ('ok', 'The flow runs against the line, so the limb where it ends is the arterial limb.'),
    'unknown': ('info', 'The pooled flow was not resolved, so which limb is arterial is unknown.'),
}
#: A whole loop whose limbs moved opposite ways along the line (`capillary.pattern_shift.loop_limbs`).
MOVEMENT_CHECK = ('warning', 'The two limbs moved opposite ways along the line, as the picture moving does, not '
                             'flow. The study summary does not count this loop.')
#: Names the page suggested itself, which a change of the line's role may replace.
SUGGESTED_NAME = re.compile(r'^(set|limb|loop)\d+$')


def format_velocity(value: float) -> str:
    """mm/s with enough digits for the slow flows these recordings show."""
    if value is None or not math.isfinite(value):
        return '–'
    return f'{value:.4f}' if abs(value) < 0.1 else f'{value:.3f}'


def _finite(value) -> bool:
    """Whether `value` is a finite number (None and NaN, as in a summary read back from JSON, are not)."""
    try:
        return math.isfinite(value)
    except TypeError:
        return False


class LineTool(Tool):
    """Click adds a point (on the line: inserts one there), drag moves a point, right-click removes one."""

    def __init__(self, page):
        self.page = page
        self._dragging = None

    def press(self, x, y, event):
        index = self.page.point_at(event.x, event.y)
        if index is None:
            index = self.page.add_point(x, y, event.x, event.y)
        self._dragging = index

    def drag(self, x, y, event):
        if self._dragging is not None:
            self.page.move_point(self._dragging, x, y)

    def release(self, x, y, event):
        if self._dragging is not None:
            self._dragging = None
            self.page.line_changed()

    def right_click(self, x, y, event):
        index = self.page.point_at(event.x, event.y)
        if index is not None:
            self.page.remove_point(index)

    def cursor_at(self, x, y, event):
        return 'fleur' if self.page.point_at(event.x, event.y) is not None else 'crosshair'


class LinePage(MeasurePage):
    key = 'line'
    title = 'Centre line'
    kind = 'line'
    measure_label = 'Measure velocity and save'
    min_frames = spacetime.DEFAULT_BLOCK_FRAMES

    def __init__(self, parent, app):
        self.points: list[tuple[float, float]] = []
        #: the lines of the recording's saved data sets: (name, curve in video pixels), drawn faintly
        self.saved_lines: list[tuple[str, np.ndarray]] = []
        self._saved_key = None
        #: the open video's shift file (`capillary.stabilize.read_shifts`) and the video it was read for
        self._shifts = None
        self._shifts_path = None
        self.preview = None
        self._preview_token = 0
        self._preview_after = None
        self._preview_center = None
        self._preview_photo = None
        super().__init__(parent, app)
        self.view.tool = LineTool(self)
        self.view.pixel_text = lambda frame, x, y: f'x {x}   y {y}   ·   brightness {int(frame[y, x])}'
        self.preview_worker = LatestOnlyWorker(self, tasks.line_preview, self._preview_ready)

    # --------------------------------------------------------------------- sections
    def build_sections(self, body):
        frame = section(body, 'Centre line', help_text=(
            'Click points along the middle of one capillary, starting where the blood comes from and following '
            'it to where it goes. Positive velocities mean flow from the first point towards the last. Every '
            'pixel along the line contributes, and a longer line can measure faster flow: the range it can '
            'measure is shown below. Drag a point to move it, click on the line to add a point there, '
            'right-click a point to remove it. For the resting velocity of a capillary loop, choose Whole loop, '
            'click from the base of one limb over the apex to the base of the other, and set the range to the '
            'official rest. The lines of data sets already saved for the recording are drawn faintly. On a '
            'stabilized video the dashed outline shows where every frame of the range has picture: where the '
            'picture moved, stabilizing leaves a black strip along the frame\'s edge, so keep the line inside it.'))
        self.points_row = InfoRow(frame, 'Points', tooltip='Clicked points; the line is a smooth curve through them.')
        self.points_row.pack(fill='x', pady=(0, px(2)))
        self.length_row = InfoRow(frame, 'Length', tooltip='Length of the curve through the points.')
        self.length_row.pack(fill='x', pady=(0, px(2)))
        self.range_row = InfoRow(frame, 'Measurable', tooltip=(
            'Speeds this line can measure in 3-s blocks at this frame rate. Faster flow moves more than the '
            'patterns along the line can follow between two frames; draw a longer line to measure it. Slower '
            'flow hardly moves within a block.'))
        self.range_row.pack(fill='x', pady=(0, px(2)))
        self.pooled_row = InfoRow(frame, 'Pooled', tooltip=(
            'Measuring also pools the pattern shift over the whole range: how far the pattern along the line '
            'moves between a frame and the next eight. It measures flow too faint for single 3-s blocks, as at '
            'rest, from 1 px per frame upwards. Faster flow is limited by how far a cell moves while the shutter '
            'is open: on simulated recordings with the shutter open the whole frame, a 120-px line measured up '
            'to about 8 px per frame within 1%, and a 300-px line round a loop up to 40.'))
        self.pooled_row.pack(fill='x')
        ttk.Label(frame, text='The line follows', style='Muted.Panel.TLabel').pack(anchor='w', pady=(px(10), px(2)))
        self.role_var = tk.StringVar(master=frame, value='')
        self.role_buttons = {}
        for role, text, _, tip in ROLES:
            button = ttk.Radiobutton(frame, text=text, value=role, variable=self.role_var, style='Panel.TRadiobutton',
                                     command=self._role_changed)
            button.pack(anchor='w')
            Tooltip(button, tip, wrap=340)
            self.role_buttons[role] = button
        actions = ttk.Frame(frame, style='Panel.TFrame')
        actions.pack(fill='x', pady=(px(10), 0))
        reverse = ttk.Button(actions, text='Reverse', image=icon('swap', 13, COLORS['text']), compound='left',
                             command=self.reverse_line)
        reverse.pack(side='left')
        Tooltip(reverse, 'Make the last point the first: the direction that counts as positive flips (X)')
        undo = ttk.Button(actions, text='Remove last point', style='Ghost.TButton', command=self.remove_last_point)
        undo.pack(side='left', padx=(px(6), 0))
        Tooltip(undo, 'Backspace')
        ttk.Button(actions, text='Clear', style='Ghost.TButton', command=self.clear_line).pack(side='left',
                                                                                             padx=(px(2), 0))
        self.line_hint = ttk.Label(frame, text='', style='Faint.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                   justify='left')
        self.line_hint.pack(anchor='w', pady=(px(10), 0))
        separator(body)

        preview = section(body, 'Space-time preview', help_text=(
            f'The brightness along the line (top: first point, bottom: last point) over the '
            f'{tasks.LINE_PREVIEW_FRAMES} frames around the current frame, time to the right, with still '
            'structure and changes that happen along the whole line at once removed. Red cells and plasma gaps '
            'moving along the vessel draw slanted streaks; their slope is the speed. Orange lines show the slope '
            'found, if one was found; the thin white line marks the current frame.'))
        self.preview_image = tk.Label(preview, bg=COLORS['video_bg'], bd=0, width=px(INSPECTOR_WIDTH - 32),
                                      height=px(PREVIEW_HEIGHT))
        self.preview_image.pack(fill='x')
        self.preview_caption = ttk.Label(preview, text='', style='Faint.Panel.TLabel')
        self.preview_caption.pack(anchor='w', pady=(px(3), px(6)))
        numbers = ttk.Frame(preview, style='Panel.TFrame')
        numbers.pack(fill='x')
        self._preview_parts = (self.preview_image, self.preview_caption, numbers)    # hidden during blind placement
        self.metric_labels = {}
        for column, (key, label) in enumerate((('velocity', 'Velocity (mm/s)'), ('snr', 'Signal-to-noise'))):
            cell = ttk.Frame(numbers, style='Panel.TFrame')
            cell.grid(row=0, column=column, sticky='w', padx=(0, px(18)))
            ttk.Label(cell, text=label, style='Faint.Panel.TLabel').pack(anchor='w')
            value = tk.Label(cell, text='–', font=FONTS['mono_big'], bg=COLORS['panel'], fg=COLORS['text'], bd=0)
            value.pack(anchor='w')
            self.metric_labels[key] = value
        self.preview_status = tk.Frame(preview, bg=COLORS['panel'])
        self.preview_status.pack(fill='x', pady=(px(8), 0))
        separator(body)

    # ----------------------------------------------------------------------- state
    def video_for(self, recording):
        return recording.video

    def capture_state(self):
        state = super().capture_state()
        state['points'] = list(self.points)
        state['role'] = self.role_var.get()
        return state

    def restore_state(self, state):
        super().restore_state(state)
        self.points = list((state or {}).get('points', []))
        if state and 'role' in state:              # a recording seen before keeps its line's role; others keep the last
            self.role_var.set(state['role'])
        self.keep_blind_role()
        self.preview = None
        self._preview_center = None
        self._update_line_ui()
        self._update_preview_ui()
        self.schedule_preview(50)

    def show_recording(self, recording):
        self._shifts, self._shifts_path = None, None     # read again: the video may have been stabilized anew
        super().show_recording(recording)
        self._load_saved_lines()

    def _shift_table(self):
        """The open video's shift file (`capillary.stabilize.read_shifts`), read once; None if it has none."""
        source = self.player.source
        path = source.path if source is not None else None
        if path != self._shifts_path:
            self._shifts, self._shifts_path = None, path
            if path is not None:
                try:
                    self._shifts = stabilize.read_shifts(path)
                except (OSError, ValueError):
                    log.warning('Could not read the shift file of %s', path, exc_info=True)
        return self._shifts

    def _picture_check(self, sampler):
        """Whether the line stays in the picture in every frame of the range; None for a video without shifts."""
        shifts, selected, shape = self._shift_table(), self.current_range(), self.view.frame_shape()
        if shifts is None or selected is None or shape is None:
            return None
        return stabilize.check_picture(shifts, shape, sampler.bounds, *selected)

    def suggest_name(self, existing):
        return datasets.suggest_dataset_name(existing, ROLE_NAMES.get(self.role_var.get(), 'set'))

    def _load_saved_lines(self):
        """Read the lines of the recording's saved data sets (once per recording and list of data sets)."""
        recording = self.recording
        key = (recording.stem, tuple(recording.line_sets)) if recording is not None else None
        if key == self._saved_key:
            return
        self._saved_key = key
        self.saved_lines = []
        for name in (recording.line_sets if recording is not None else []):
            record = datasets.read_provenance(
                datasets.line_dataset_files(self.app.folder.statistics, recording.stem, name)['provenance'])
            try:
                curve = spacetime.Centreline.from_points(record['line']['points']).curve()
            except (KeyError, TypeError, ValueError):
                continue
            self.saved_lines.append((name, curve))
        self.draw_overlay()

    def apply_record(self, record):
        """Put the line, its role and the range of a saved data set's provenance back (Results page)."""
        try:
            points = [(float(x), float(y)) for x, y in record['line']['points']]
        except (KeyError, TypeError, ValueError):
            return False
        if len(points) < 2:
            return False
        self.points = points
        role = record['line'].get('role') or ''
        self.role_var.set(role if role in ROLE_NAMES else '')
        frames = record.get('frames', {})
        first, last = frames.get('first'), frames.get('last')
        if first is not None and last is not None and self.player.source is not None:
            last = min(int(last), self.player.frame_count - 1)
            self.range = None if (first, last) == (0, self.player.frame_count - 1) else (int(first), last)
        self.refresh()
        self.schedule_preview(50)
        return True

    def update_banner(self):
        recording = self.recording
        if recording is not None and recording.video and not recording.is_stabilized:
            self.banner.show('This recording is not stabilized. Movement of the skin moves the vessel under the '
                             'line; stabilize it before measuring.', 'warning',
                             action=lambda: self.app.stabilize(recording), action_text='Stabilize now')
        else:
            self.banner.hide()

    def refresh(self):
        super().refresh()
        self.keep_blind_role()
        self._update_line_ui()
        self._update_preview_ui()

    def keep_blind_role(self):
        """During blind placement every line is a whole loop (`gui.blind.ROLE`): the other roles are closed, and a
        role remembered from before (`restore_state`) gives way to it, the suggested name with it."""
        on = self.app.blind
        for role, button in self.role_buttons.items():
            button.state(['disabled'] if on and role != blind.ROLE else ['!disabled'])
        if on and self.role_var.get() != blind.ROLE:
            self.role_var.set(blind.ROLE)
            if self.recording is not None and SUGGESTED_NAME.match(self.name_var.get().strip()):
                self.name_var.set(self.suggest_name(self.existing_names()))
            self.draw_overlay()

    # ------------------------------------------------------------------------ the line
    def centreline(self):
        return spacetime.Centreline.from_points(self.points) if len(self.points) >= 2 else None

    def _clamp(self, x, y):
        shape = self.view.frame_shape()
        if shape is None:
            return float(x), float(y)
        return float(min(max(x, 0.0), shape[1] - 1)), float(min(max(y, 0.0), shape[0] - 1))

    def point_at(self, cx, cy):
        """Index of the point under canvas position (cx, cy), or None."""
        best, best_distance = None, px(8)
        for index, (x, y) in enumerate(self.points):
            px_, py_ = self.view.to_canvas(x, y)
            distance = math.hypot(px_ - cx, py_ - cy)
            if distance <= best_distance:
                best, best_distance = index, distance
        return best

    def _segment_at(self, cx, cy):
        """Index of the point after which a click on the curve at (cx, cy) inserts one, or None."""
        if len(self.points) < 2:
            return None
        curve = self.centreline().curve()
        canvas = np.array([self.view.to_canvas(x, y) for x, y in curve])
        distances = np.hypot(canvas[:, 0] - cx, canvas[:, 1] - cy)
        nearest = int(np.argmin(distances))
        if distances[nearest] > px(6):
            return None
        per_segment = (len(curve) - 1) / (len(self.points) - 1)
        return min(int(nearest / per_segment), len(self.points) - 2)

    def add_point(self, x, y, cx=None, cy=None):
        if self.player.source is None:
            return None
        point = self._clamp(x, y)
        segment = self._segment_at(cx, cy) if cx is not None else None
        if segment is None:
            self.points.append(point)
            index = len(self.points) - 1
        else:
            index = segment + 1
            self.points.insert(index, point)
        self._line_moved()
        return index

    def move_point(self, index, x, y):
        if 0 <= index < len(self.points):
            self.points[index] = self._clamp(x, y)
            self._line_moved(preview=False)

    def remove_point(self, index):
        if 0 <= index < len(self.points):
            del self.points[index]
            self.line_changed()

    def remove_last_point(self):
        if self.points:
            self.remove_point(len(self.points) - 1)

    def clear_line(self):
        self.points = []
        self.line_changed()

    def reverse_line(self):
        if len(self.points) >= 2:
            self.points.reverse()
            self.line_changed()
            self.app.set_status('Line reversed: positive velocity now runs the other way along it.')

    def role(self):
        """The line's role as saved with the data set: `ARTERIAL`, `WHOLE_LOOP`, or None for any stretch."""
        return self.role_var.get() or None

    def _role_changed(self):
        if self.recording is not None and SUGGESTED_NAME.match(self.name_var.get().strip()):
            self.name_var.set(self.suggest_name(self.existing_names()))
        self.draw_overlay()
        self._update_line_ui()
        self.app.set_status({
            ARTERIAL: 'The line is an arterial limb, from its base (first point) to the apex (last point).',
            WHOLE_LOOP: 'The line goes round a whole loop, from the base of one limb (first point) over the apex '
                        'to the base of the other (last point).',
        }.get(self.role(), 'The line follows any stretch of a capillary.'))

    def _line_moved(self, preview=True):
        self.draw_overlay()
        self._update_line_ui()
        if preview:
            self.schedule_preview()

    def line_changed(self):
        self.preview = None
        self._line_moved()
        self._update_preview_ui()

    def _line_problem(self):
        """Why the current line cannot be measured, or None."""
        line = self.centreline()
        if line is None:
            return 'Click at least two points along a capillary.'
        if line.length_px < spacetime.MIN_LENGTH_PX:
            return f'The line is too short; it needs at least {spacetime.MIN_LENGTH_PX} px.'
        shape = self.view.frame_shape()
        sampler = spacetime.SpaceTimeSampler(line)
        if shape is not None and not sampler.inside(shape):
            return 'The line runs too close to the edge of the image.'
        check = self._picture_check(sampler)
        if check is not None and check.problem() is not None:
            if check.off_picture and not check.lost and self._outline() is not None:
                return f'{check.problem()} The dashed outline shows where every frame of the range has picture.'
            return check.problem()
        return None

    def _update_line_ui(self):
        count = len(self.points)
        self.points_row.set(str(count) if count else '–')
        line = self.centreline()
        mm_per_pixel = self.app.settings.mm_per_pixel
        if line is None:
            self.length_row.set('–')
            self.range_row.set('–')
            self.pooled_row.set('–')
        else:
            length = line.length_px
            self.length_row.set(f'{length:.0f} px  ·  {length * mm_per_pixel * 1000:.0f} µm')
            slowest, fastest = spacetime.resolvable_speeds(length, self.player.fps, mm_per_pixel)
            self.range_row.set(f'{format_velocity(slowest)} – {format_velocity(fastest)} mm/s in 3-s blocks'
                               if math.isfinite(fastest) else 'too short')
            self.pooled_row.set(f'from {format_velocity(pattern_shift.MIN_SPEED * self.player.fps * mm_per_pixel)} '
                                'mm/s over the range' if length >= pattern_shift.MIN_LENGTH_PX else 'too short')
        self.line_hint.configure(text=self._hint_text(long=True))
        self.view.set_hint(self._hint_text(long=False))
        self.update_measure_state()

    def _hint_text(self, long):
        if self.player.source is None:
            return None if not long else ''
        role = self.role()
        if not self.points:
            if role == ARTERIAL:
                return ('Click at the base of the arterial limb, the end away from the loop\'s tip, then follow the '
                        'middle of the limb up to the apex.' if long else 'Click at the base of the arterial limb')
            if role == WHOLE_LOOP:
                return ('Click at the base of one limb of the loop, then follow the middle of that limb up to the '
                        'apex, over it and down the other limb to its base.' if long
                        else 'Click at the base of one limb of the loop')
            return ('Click on the video where the blood enters a capillary segment, then follow the middle of the '
                    'vessel in the direction of flow.' if long else 'Click where the blood enters a capillary')
        if len(self.points) == 1:
            if role == ARTERIAL:
                return ('Now click further up the limb, towards the apex. Add more points to follow its bends.'
                        if long else 'Click further up the limb, towards the apex')
            if role == WHOLE_LOOP:
                return ('Now click further up the limb, then round the apex and down the other limb. Add points to '
                        'follow the bends.' if long else 'Follow the limb up, round the apex and down the other')
            return ('Now click further along the same capillary, in the direction of flow. Add more points to '
                    'follow its bends.' if long else 'Click further along the capillary, in the direction of flow')
        if not long:
            return None
        if role == ARTERIAL:
            return ('End the line at the apex; drag points to keep it in the middle of the limb. Then set the range '
                    'to the official rest and measure: the pooled flow should run towards the apex.')
        if role == WHOLE_LOOP:
            return ('End the line at the base of the other limb; drag points to keep it in the middle of the vessel, '
                    'round the apex too. Then set the range to the official rest and measure.')
        return ('Click beyond the end to extend the line, on the line to add a point there; drag points to keep '
                'the line in the middle of the vessel. A longer straight-ish stretch measures faster flow.')

    def draw_overlay(self):
        canvas = self.view.canvas
        canvas.delete('overlay')
        if self.view.frame_shape() is not None:
            self._draw_picture_area(canvas)
            self._draw_saved_lines(canvas)
        if self.view.frame_shape() is None or not self.points:
            canvas.tag_raise('hint')
            return
        color = COLORS['line']
        if len(self.points) >= 2:
            points = [self.view.to_canvas(x, y) for x, y in self.centreline().curve()]
            coords = [value for point in points for value in point]
            canvas.create_line(*coords, fill='#000000', width=px(4), tags=('overlay',))
            canvas.create_line(*coords, fill=color, width=px(2), tags=('overlay',))
            # an arrowhead halfway along shows which way counts as positive (at the end a point would hide it)
            middle = len(points) // 2
            stretch = points[max(0, middle - 8)] + points[min(len(points) - 1, middle + 8)]
            canvas.create_line(*stretch, fill='#000000', width=px(4), arrow='last',
                               arrowshape=(px(12), px(13), px(6)), tags=('overlay',))
            canvas.create_line(*stretch, fill=color, width=px(2), arrow='last',
                               arrowshape=(px(11), px(12), px(5)), tags=('overlay',))
        for index, (x, y) in enumerate(self.points):
            cx, cy = self.view.to_canvas(x, y)
            radius = px(5) if index == 0 else px(3.5)
            canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline='#000000',
                               fill=color if index == 0 else '#FFFFFF', width=1, tags=('overlay',))
        role = self.role()
        tags = [(0, 'base' if role == ARTERIAL else 'start')]
        if role in (ARTERIAL, WHOLE_LOOP) and len(self.points) >= 2:
            tags.append((len(self.points) - 1, 'apex' if role == ARTERIAL else 'end'))
        for index, text in tags:
            cx, cy = self.view.to_canvas(*self.points[index])
            anchor, dx, dy = 'sw', px(9), -px(9)
            if role == WHOLE_LOOP and len(self.points) >= 2:
                # a loop's two bases lie side by side: each label goes outwards, away from the other base
                other = self.points[-1 if index == 0 else 0]
                anchor, dx, dy = ('e', -px(9), 0) if self.points[index][0] <= other[0] else ('w', px(9), 0)
            label = canvas.create_text(cx + dx, cy + dy, text=text, anchor=anchor, font=FONTS['small_bold'],
                                       fill='#111111', tags=('overlay',))
            x0, y0, x1, y1 = canvas.bbox(label)
            canvas.create_rectangle(x0 - px(3), y0, x1 + px(3), y1, fill=color, outline='', tags=('overlay',))
            canvas.tag_raise(label)
        canvas.tag_raise('hint')
        canvas.tag_raise('readout')

    def _outline(self):
        """Where the line's middle may go, (x0, y0, x1, y1) in video pixels: the part of the frame that every
        frame of the range shows the picture in (`capillary.stabilize.picture_area`), less the half-width the
        line also samples to either side. None for a video without shifts, or when no such part is left."""
        shifts, selected, shape = self._shift_table(), self.current_range(), self.view.frame_shape()
        if shifts is None or selected is None or shape is None:
            return None
        area = stabilize.picture_area(shifts, shape, *selected)
        inset = spacetime.DEFAULT_HALF_WIDTH_PX
        if area is None or area[0] + inset > area[2] - inset or area[1] + inset > area[3] - inset:
            return None
        return area[0] + inset, area[1] + inset, area[2] - inset, area[3] - inset

    def _draw_picture_area(self, canvas):
        """The outline of `_outline`, dashed; orange while the line reaches beyond the picture."""
        outline = self._outline()
        if outline is None:
            return
        line = self.centreline()
        check = self._picture_check(spacetime.SpaceTimeSampler(line)) if line is not None else None
        color = COLORS['picture_edge_crossed'] if check is not None and check.off_picture else COLORS['picture_edge']
        x0, y0 = self.view.to_canvas(outline[0], outline[1])
        x1, y1 = self.view.to_canvas(outline[2], outline[3])
        canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=px(1.5), dash=(px(6), px(4)), tags=('overlay',))

    def _draw_saved_lines(self, canvas):
        """The lines of the recording's saved data sets: thin, dashed, with their names at the first point."""
        color = COLORS['saved_line']
        for name, curve in self.saved_lines:
            points = [self.view.to_canvas(x, y) for x, y in curve[::4]] + [self.view.to_canvas(*curve[-1])]
            coords = [value for point in points for value in point]
            canvas.create_line(*coords, fill='#000000', width=px(3), tags=('overlay',))
            canvas.create_line(*coords, fill=color, width=px(1.5), dash=(px(5), px(3)), tags=('overlay',))
            x, y = points[0]
            canvas.create_text(x - px(6), y + px(6), text=name, anchor='ne', font=FONTS['small_bold'], fill=color,
                               tags=('overlay',))

    # ---------------------------------------------------------------------- preview
    def after_frame(self, index):
        if self.player.playing:
            if self._preview_center is None or abs(index - self._preview_center) >= 30:
                self.schedule_preview(0)
        else:
            self.schedule_preview()
            self._update_preview_ui()          # moves the current-frame marker in the diagram

    def on_show(self):
        super().on_show()
        self.schedule_preview(50)

    def on_range_change(self):
        self.draw_overlay()                  # the outline of the picture follows the range
        self._update_preview_ui()            # and whether the line stays inside it
        if self.preview is None:
            self.schedule_preview(50)

    def schedule_preview(self, delay_ms=220):
        if self._preview_after is not None:
            self.after_cancel(self._preview_after)
        self._preview_after = self.after(delay_ms, self._request_preview)

    def _request_preview(self):
        self._preview_after = None
        if self.player.source is None or self._line_problem() is not None or self.app.blind:
            self.preview = None
            self._update_preview_ui()
            return
        count = min(tasks.LINE_PREVIEW_FRAMES, self.player.frame_count)
        if count < spacetime.MIN_BLOCK_FRAMES:
            return
        start = max(0, min(self.player.index - count // 2, self.player.frame_count - count))
        self._preview_center = self.player.index
        self._preview_token += 1
        self.preview_worker.request(self._preview_token, self.player.source.path, list(self.points), start, count,
                                    self.app.settings.mm_per_pixel)

    def _preview_ready(self, token, result):
        if token != self._preview_token:
            return
        self.preview = result
        self._update_preview_ui()

    def _set_status(self, kind, text, action=None, action_text=''):
        for child in self.preview_status.winfo_children():
            child.destroy()
        if not text:
            return
        colors = {'ok': COLORS['success'], 'warning': COLORS['warning'], 'info': COLORS['muted']}
        tk.Label(self.preview_status, image=icon(kind, 13, colors[kind]), bg=COLORS['panel'], bd=0).pack(
            side='left', anchor='n', padx=(0, px(6)), pady=(px(1), 0))
        tk.Label(self.preview_status, text=text, bg=COLORS['panel'], fg=COLORS['text'], font=FONTS['small'],
                 wraplength=px(INSPECTOR_WIDTH - 60), justify='left', bd=0).pack(side='left', fill='x')
        if action is not None:
            ttk.Button(self.preview_status, text=action_text, command=action).pack(side='right', anchor='n')

    def _show_image(self, image):
        self._preview_photo = ImageTk.PhotoImage(image) if image is not None else None
        self.preview_image.configure(image=self._preview_photo or '')

    def _show_preview_parts(self, show):
        """Show the diagram, its caption and numbers, or hide them (blind placement)."""
        image, caption, numbers = self._preview_parts
        if show and not image.winfo_manager():
            image.pack(fill='x', before=self.preview_status)
            caption.pack(anchor='w', pady=(px(3), px(6)), before=self.preview_status)
            numbers.pack(fill='x', before=self.preview_status)
        elif not show and image.winfo_manager():
            for part in self._preview_parts:
                part.pack_forget()

    def _update_preview_ui(self):
        labels = self.metric_labels
        result = self.preview
        problem = self._line_problem() if self.player.source is not None else 'Select a recording with a video.'
        self._show_preview_parts(not self.app.blind)
        if self.app.blind:
            self._set_status('info', problem if problem is not None and self.points else
                             'Hidden during blind placement, so that lines are placed by the anatomy alone, not by '
                             'what they measure.')
            return
        if problem is not None or result is None or isinstance(result, Exception):
            for value in labels.values():
                value.configure(text='–', fg=COLORS['text'])
            self._show_image(None)
            self.preview_caption.configure(text='')
            if isinstance(result, Exception) and problem is None:
                self._set_status('warning', f'The preview could not read the video: {result}')
            elif problem is None:
                self._set_status('info', 'Reading frames…')
            else:
                self._set_status('info', problem if self.points else '')
            return

        self._show_image(render_space_time(result, self.player.index, px(INSPECTOR_WIDTH - 32), px(PREVIEW_HEIGHT)))
        frames, positions = result['diagram'].shape
        self.preview_caption.configure(text=f'{frames} frames ({frames / result["fps"]:.1f} s)  ·  {positions - 1} px '
                                            'along the line')
        velocity, snr = result['velocity'], result['snr']
        labels['velocity'].configure(text=format_velocity(velocity),
                                     fg=COLORS['text'] if not (math.isfinite(velocity) and velocity < 0)
                                     else COLORS['warning'])
        labels['snr'].configure(text=f'{snr:.0f}' if math.isfinite(snr) else '–',
                                fg=COLORS['success'] if result['resolved'] else COLORS['muted'])
        slowest, fastest = result['limits_mm_s']
        speed_mm_s = result['speed'] * result['fps'] * self.app.settings.mm_per_pixel
        if result['resolved'] and velocity < 0:
            self._set_status('warning', 'The streaks run from the last point towards the first: the flow seems to '
                                        'go against the line. Reverse the line if so; positive velocity counts flow '
                                        'from the first point to the last.', self.reverse_line, 'Reverse')
        elif result['resolved']:
            self._set_status('ok', f'Flow along the line, about {format_velocity(velocity)} mm/s in these frames '
                                   f'(signal-to-noise {snr:.0f}).')
        elif math.isfinite(speed_mm_s) and abs(speed_mm_s) > fastest * 0.999:
            self._set_status('warning', f'The flow may be faster than this line can measure (above '
                                        f'{format_velocity(fastest)} mm/s). Draw a longer line along the capillary.')
        elif math.isfinite(speed_mm_s) and abs(speed_mm_s) < slowest:
            self._set_status('warning', 'Hardly any movement in these frames: the flow is paused or slower than '
                                        f'{format_velocity(slowest)} mm/s.')
        else:
            self._set_status('warning', 'No clear streaks in these frames (signal-to-noise '
                                        f'{snr:.0f}, {spacetime.MIN_SNR:.0f} needed). Check that the line follows '
                                        'the middle of a capillary. Faint flow, as at rest, can still be measured: '
                                        'Measure pools the pattern shift over the whole range.'
                             if math.isfinite(snr) else 'No clear streaks in these frames.')

    # -------------------------------------------------------------------- measuring
    def measure_blockers(self):
        problem = self._line_problem()
        if problem is not None:
            return [problem]
        if self.recording is not None and self.app.jobs.find(('line', self.recording.stem)) is not None:
            return ['A measurement of this recording is already running.']
        return []

    def submit_measurement(self, name, start, end, done, failed, cancelled):
        recording = self.recording
        work = partial(tasks.measure_line_dataset, folder=self.app.folder, stem=recording.stem, name=name,
                       video_path=self.player.source.path, points=list(self.points), start=start, end=end,
                       mm_per_pixel=self.app.settings.mm_per_pixel, time_points=list(self.markers),
                       observer=self.observer(), role=self.role())
        return self.app.jobs.submit(f'Centre line · {self.app.display_name(recording.stem)} · {name}', work,
                                    lane='analysis', on_done=done, on_error=failed, on_cancel=cancelled,
                                    key=('line', recording.stem))

    def empty_chart_message(self, result):
        if _finite(result['summary'].get('pattern_shift_velocity_mm_s')):
            return ('Fewer than two 3-s blocks were resolved, so there is no time course to plot; the velocity '
                    'pooled over the range is above.')
        return super().empty_chart_message(result)

    def result_status(self, result):
        summary = result['summary']
        parts = []
        pooled, median = summary.get('pattern_shift_velocity_mm_s'), summary.get('median')
        if _finite(pooled):
            parts.append(f'pattern shift {format_velocity(pooled)} mm/s')
        if _finite(median):
            parts.append(f'median of the 3-s blocks {format_velocity(median)} mm/s')
        check = summary.get('limb_check')
        if check:
            parts.append({'arterial': 'arterial limb confirmed', 'venous': 'the flow shows the venous limb',
                          'unknown': 'limb not confirmed'}.get(check, check))
        end = summary.get('arterial_end')
        if end:
            parts.append({'start': 'arterial limb at the start of the loop', 'end': 'arterial limb at the end of the loop',
                          'unknown': 'arterial limb unknown'}.get(end, end))
        if summary.get('loop_movement'):
            parts.append('the limbs moved opposite ways: not counted')
        return f' ({"; ".join(parts)})' if parts else ''

    def describe_result(self, frame, result):
        summary = result['summary']
        nan = float('nan')
        check = summary.get('limb_check')
        checks = [LIMB_CHECKS[check]] if check in LIMB_CHECKS else []
        if summary.get('arterial_end') in LOOP_CHECKS:
            checks.append(LOOP_CHECKS[summary['arterial_end']])
        if summary.get('loop_movement'):
            checks.append(MOVEMENT_CHECK)
        for kind, text in checks:
            row = tk.Frame(frame, bg=COLORS['panel'])
            row.pack(fill='x', pady=(0, px(8)))
            colors = {'ok': COLORS['success'], 'warning': COLORS['warning'], 'info': COLORS['muted']}
            tk.Label(row, image=icon(kind, 13, colors[kind]), bg=COLORS['panel'], bd=0).pack(
                side='left', anchor='n', padx=(0, px(6)), pady=(px(1), 0))
            tk.Label(row, text=text, bg=COLORS['panel'], fg=COLORS['text'], font=FONTS['small'],
                     wraplength=px(INSPECTOR_WIDTH - 60), justify='left', bd=0).pack(side='left', fill='x')

        pooled = summary.get('pattern_shift_velocity_mm_s', nan)
        median = summary.get('median', nan)
        big = ttk.Frame(frame, style='Panel.TFrame')
        big.pack(fill='x', pady=(0, px(6)))
        if _finite(pooled):
            ttk.Label(big, text=format_velocity(pooled), style='Big.Panel.TLabel').pack(side='left')
            ttk.Label(big, text=' mm/s pooled over the range', style='Muted.Panel.TLabel').pack(
                side='left', anchor='s', pady=(0, px(4)))
        elif _finite(median):
            ttk.Label(big, text=format_velocity(median), style='Big.Panel.TLabel').pack(side='left')
            ttk.Label(big, text=' mm/s median of the 3-s blocks', style='Muted.Panel.TLabel').pack(
                side='left', anchor='s', pady=(0, px(4)))
        else:
            ttk.Label(big, text='No velocity could be resolved', style='Bold.Panel.TLabel').pack(side='left')

        _subheading(frame, 'Pattern shift, pooled over the range')
        halves = [nan, nan]
        if 'pattern_shift_snr' not in summary:
            ttk.Label(frame, text='Not computed for this data set; regenerate its report on the Results page.',
                      style='Faint.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40), justify='left').pack(anchor='w')
        else:
            shift_snr = summary.get('pattern_shift_snr', nan)
            stat(frame, 'Velocity', f'{format_velocity(pooled)} mm/s' if _finite(pooled) else 'not resolved')
            low, high = summary.get('pattern_shift_ci95_low_mm_s', nan), summary.get('pattern_shift_ci95_high_mm_s', nan)
            if _finite(low) and _finite(high):
                stat(frame, '95% interval', f'{format_velocity(low)} – {format_velocity(high)} mm/s',
                     tooltip='From leaving out one 3-s block at a time. It covers the statistical scatter only, '
                             'not a systematic error such as a line off the middle of the vessel.')
            stat(frame, 'Signal-to-noise', f'{shift_snr:.1f}  ({pattern_shift.MIN_SNR:.0f} needed)'
                 if _finite(shift_snr) else '–')
            halves = [summary.get(f'pattern_shift_{half}_mm_s', nan) for half in ('first_half', 'second_half')]
            half_snrs = [summary.get(f'pattern_shift_{half}_snr', nan) for half in ('first_half', 'second_half')]
            if any(_finite(value) for value in half_snrs):
                stat(frame, 'Halves', '  /  '.join(format_velocity(v) if _finite(v) else 'not resolved' for v in halves)
                     + ' mm/s', tooltip='The first and the second half of the range in time, each pooled on its '
                                        'own: whether the flow stayed the same.')
        _subheading(frame, '3-s blocks')
        q25, q75 = summary.get('q25', nan), summary.get('q75', nan)
        stat(frame, 'Median', f'{format_velocity(median)} mm/s' if _finite(median) else 'none resolved')
        stat(frame, 'Middle 50 %', f'{format_velocity(q25)} – {format_velocity(q75)} mm/s' if _finite(q25)
             else '–', tooltip='Interquartile range of the block estimates.')
        resolved = summary.get('resolved_fraction', nan)
        stat(frame, 'Resolved blocks', _percent(resolved),
             tooltip='Share of the 3-s blocks with clear streaks. With few resolved blocks the median rests on '
                     'little data.')
        snr = summary.get('median_snr', nan)
        stat(frame, 'Median signal-to-noise', f'{snr:.0f}' if _finite(snr) else '–')
        fastest = summary.get('fastest_mm_s', nan)
        stat(frame, 'Measurable up to', f'{format_velocity(fastest)} mm/s' if _finite(fastest) else '–')

        notes = []
        phase = summary.get('phase') or ''
        if '+' in phase:
            notes.append(f'The range covers {phase.replace(" + ", ", ")}: the pooled velocity mixes them. '
                         'Set the range to one official phase.')
        if _finite(halves[0]) and _finite(halves[1]) and halves[0] * halves[1] < 0:
            notes.append('The halves run in opposite directions.')
        if _finite(median) and _finite(resolved) and resolved < 0.25:
            notes.append('Few 3-s blocks were resolved, so their median is uncertain.')
        if _finite(median) and _finite(fastest) and abs(median) > 0.85 * fastest:
            notes.append('The blocks are close to the fastest this line can measure; a longer line would be safer.')
        if not check and not summary.get('arterial_end') and (
                (_finite(pooled) and pooled < 0) or (not _finite(pooled) and _finite(median) and median < 0)):
            notes.append('Negative: the flow runs from the last point towards the first.')
        for note in notes:
            ttk.Label(frame, text=note, style='Warning.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                      justify='left').pack(anchor='w', pady=(px(4), 0))

    # ---------------------------------------------------------------------- keyboard
    def handle_page_key(self, event):
        keysym = event.keysym
        if keysym in ('BackSpace', 'Delete'):
            self.remove_last_point()
        elif keysym.lower() == 'x':
            self.reverse_line()
        else:
            return False
        return True


def render_space_time(result, current_frame, width, height):
    """The preview diagram as an image: time to the right, the line from top (first point) to bottom."""
    diagram = np.asarray(result['diagram'], dtype=float)
    cleaned = diagram - diagram.mean(axis=0, keepdims=True)
    cleaned = cleaned - cleaned.mean(axis=1, keepdims=True)
    low, high = np.percentile(cleaned, [1, 99])
    scaled = np.clip((cleaned - low) / max(high - low, 1e-9) * 255, 0, 255).astype(np.uint8).T   # positions x frames
    image = Image.fromarray(scaled).resize((width, height), Image.Resampling.BILINEAR).convert('RGB')
    draw = ImageDraw.Draw(image)
    frames, positions = diagram.shape
    if result['resolved'] and math.isfinite(result['speed']):
        speed = result['speed']                       # positions per frame, + = downwards in the image
        for i in range(4):
            middle = positions * (i + 0.5) / 4
            t0, t1 = 0.0, float(frames)
            p0 = middle - speed * (frames / 2)
            p1 = middle + speed * (frames / 2)
            draw.line([(t0 / frames * width, p0 / positions * height), (t1 / frames * width, p1 / positions * height)],
                      fill=(255, 159, 28), width=2)
    offset = current_frame - result['start']
    if 0 <= offset < frames:
        x = (offset + 0.5) / frames * width
        draw.line([(x, 0), (x, height)], fill=(255, 255, 255), width=1)
    return image


def _percent(value):
    return f'{100 * value:.0f} %' if value is not None and math.isfinite(value) else '–'


def _subheading(parent, text):
    ttk.Label(parent, text=text, style='Bold.Panel.TLabel').pack(anchor='w', pady=(px(8), px(2)))
