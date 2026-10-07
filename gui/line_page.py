"""Centre line page: red-cell velocity from the slope of the streaks in a space-time diagram.

The user clicks points along the middle of one capillary, from where the blood
comes from to where it goes. In every frame the brightness along that line is
sampled; stacked over time this is the space-time diagram, in which red cells
and plasma gaps moving along the vessel draw slanted streaks. Their slope is
the speed (`capillary.spacetime`). The panel shows the diagram of the frames
around the playhead with the slope found, so every estimate can be checked by
eye, and the measurement repeats it block by block over the chosen frames.
"""

from __future__ import annotations

import math
import tkinter as tk
from functools import partial
from tkinter import ttk

import numpy as np
from PIL import Image, ImageDraw, ImageTk

from capillary import spacetime

from . import tasks
from .jobs import LatestOnlyWorker
from .measure_page import INSPECTOR_WIDTH, MeasurePage, stat
from .theme import COLORS, FONTS, icon, px
from .video_view import Tool
from .widgets import InfoRow, Tooltip, section, separator

PREVIEW_HEIGHT = 130


def format_velocity(value: float) -> str:
    """mm/s with enough digits for the slow flows these recordings show."""
    if value is None or not math.isfinite(value):
        return '–'
    return f'{value:.4f}' if abs(value) < 0.1 else f'{value:.3f}'


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
            'right-click a point to remove it.'))
        self.points_row = InfoRow(frame, 'Points', tooltip='Clicked points; the line is a smooth curve through them.')
        self.points_row.pack(fill='x', pady=(0, px(2)))
        self.length_row = InfoRow(frame, 'Length', tooltip='Length of the curve through the points.')
        self.length_row.pack(fill='x', pady=(0, px(2)))
        self.range_row = InfoRow(frame, 'Measurable', tooltip=(
            'Speeds this line can measure in 3-s blocks at this frame rate. Faster flow moves more than the '
            'patterns along the line can follow between two frames; draw a longer line to measure it. Slower '
            'flow hardly moves within a block.'))
        self.range_row.pack(fill='x')
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
        return state

    def restore_state(self, state):
        super().restore_state(state)
        self.points = list((state or {}).get('points', []))
        self.preview = None
        self._preview_center = None
        self._update_line_ui()
        self._update_preview_ui()
        self.schedule_preview(50)

    def apply_record(self, record):
        """Put the line and range of a saved data set's provenance back (Results page)."""
        try:
            points = [(float(x), float(y)) for x, y in record['line']['points']]
        except (KeyError, TypeError, ValueError):
            return False
        if len(points) < 2:
            return False
        self.points = points
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
        self._update_line_ui()
        self._update_preview_ui()

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
        if shape is not None and not spacetime.SpaceTimeSampler(line).inside(shape):
            return 'The line runs too close to the edge of the image.'
        return None

    def _update_line_ui(self):
        count = len(self.points)
        self.points_row.set(str(count) if count else '–')
        line = self.centreline()
        if line is None:
            self.length_row.set('–')
            self.range_row.set('–')
        else:
            length = line.length_px
            self.length_row.set(f'{length:.0f} px  ·  {length * self.app.settings.mm_per_pixel * 1000:.0f} µm')
            slowest, fastest = spacetime.resolvable_speeds(length, self.player.fps, self.app.settings.mm_per_pixel)
            self.range_row.set(f'{format_velocity(slowest)} – {format_velocity(fastest)} mm/s'
                               if math.isfinite(fastest) else 'too short')
        self.line_hint.configure(text=self._hint_text(long=True))
        self.view.set_hint(self._hint_text(long=False))
        self.update_measure_state()

    def _hint_text(self, long):
        if self.player.source is None:
            return None if not long else ''
        if not self.points:
            return ('Click on the video where the blood enters a capillary segment, then follow the middle of the '
                    'vessel in the direction of flow.' if long else 'Click where the blood enters a capillary')
        if len(self.points) == 1:
            return ('Now click further along the same capillary, in the direction of flow. Add more points to '
                    'follow its bends.' if long else 'Click further along the capillary, in the direction of flow')
        if not long:
            return None
        return ('Click beyond the end to extend the line, on the line to add a point there; drag points to keep '
                'the line in the middle of the vessel. A longer straight-ish stretch measures faster flow.')

    def draw_overlay(self):
        canvas = self.view.canvas
        canvas.delete('overlay')
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
        if self.points:
            cx, cy = self.view.to_canvas(*self.points[0])
            label = canvas.create_text(cx + px(9), cy - px(9), text='start', anchor='sw', font=FONTS['small_bold'],
                                       fill='#111111', tags=('overlay',))
            x0, y0, x1, y1 = canvas.bbox(label)
            canvas.create_rectangle(x0 - px(3), y0, x1 + px(3), y1, fill=color, outline='', tags=('overlay',))
            canvas.tag_raise(label)
        canvas.tag_raise('hint')
        canvas.tag_raise('readout')

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

    def schedule_preview(self, delay_ms=220):
        if self._preview_after is not None:
            self.after_cancel(self._preview_after)
        self._preview_after = self.after(delay_ms, self._request_preview)

    def _request_preview(self):
        self._preview_after = None
        if self.player.source is None or self._line_problem() is not None:
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

    def _update_preview_ui(self):
        labels = self.metric_labels
        result = self.preview
        problem = self._line_problem() if self.player.source is not None else 'Select a recording with a video.'
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
                                        'the middle of a capillary with visible flow; very slow or paused flow '
                                        'cannot be measured.' if math.isfinite(snr) else
                             'No clear streaks in these frames.')

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
                       observer=self.observer())
        return self.app.jobs.submit(f'Centre line · {recording.stem} · {name}', work, lane='analysis', on_done=done,
                                    on_error=failed, on_cancel=cancelled, key=('line', recording.stem))

    def result_status(self, result):
        median = result['summary'].get('median')
        return f' (median {format_velocity(median)} mm/s)' if median is not None and math.isfinite(median) else ''

    def describe_result(self, frame, result):
        summary = result['summary']
        median = summary.get('median', float('nan'))
        big = ttk.Frame(frame, style='Panel.TFrame')
        big.pack(fill='x', pady=(0, px(6)))
        if math.isfinite(median):
            ttk.Label(big, text=format_velocity(median), style='Big.Panel.TLabel').pack(side='left')
            ttk.Label(big, text=' mm/s median', style='Muted.Panel.TLabel').pack(side='left', anchor='s',
                                                                                 pady=(0, px(4)))
        else:
            ttk.Label(big, text='No velocity could be resolved', style='Bold.Panel.TLabel').pack(side='left')
        q25, q75 = summary.get('q25', float('nan')), summary.get('q75', float('nan'))
        stat(frame, 'Middle 50 %', f'{format_velocity(q25)} – {format_velocity(q75)} mm/s' if math.isfinite(q25)
             else '–', tooltip='Interquartile range of the block estimates.')
        resolved = summary.get('resolved_fraction', float('nan'))
        stat(frame, 'Resolved blocks', _percent(resolved),
             style='Warning.Panel.TLabel' if math.isfinite(resolved) and resolved < 0.25 else 'Mono.Panel.TLabel',
             tooltip='Share of the 3-s blocks with clear streaks. With few resolved blocks the median rests on '
                     'little data.')
        snr = summary.get('median_snr', float('nan'))
        stat(frame, 'Median signal-to-noise', f'{snr:.0f}' if math.isfinite(snr) else '–')
        fastest = summary.get('fastest_mm_s', float('nan'))
        stat(frame, 'Measurable up to', f'{format_velocity(fastest)} mm/s' if math.isfinite(fastest) else '–')
        notes = []
        if math.isfinite(resolved) and resolved < 0.25:
            notes.append('Few blocks were resolved, so the median is uncertain.')
        if math.isfinite(median) and math.isfinite(fastest) and abs(median) > 0.85 * fastest:
            notes.append('Close to the fastest this line can measure; a longer line would be safer.')
        if math.isfinite(median) and median < 0:
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
