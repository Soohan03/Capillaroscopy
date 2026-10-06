"""Analyze page: red-cell velocity from two boxes on one capillary.

Box 1 sits downstream (the blood reaches it last), box 2 upstream on the same
capillary. A plug passing darkens box 2 first and box 1 a few frames later; the
delay between the two brightness signals, over the separation of the boxes,
is the velocity. The page guides through placing the boxes, previews that
signal live, and runs the measurement over the chosen range of frames.
"""

from __future__ import annotations

import math
import tkinter as tk
from functools import partial
from tkinter import ttk

import numpy as np

from capillary import datasets
from capillary.roi import ROI
from capillary.velocity import resolvable_range

from . import tasks
from .jobs import LatestOnlyWorker
from .measure_page import INSPECTOR_WIDTH, MeasurePage, stat
from .theme import COLORS, FONTS, icon, px, quality_of, rounded_rect
from .video_view import Tool
from .widgets import LineChart, Tooltip, color_swatch, section, separator

BOX_NAMES = ('Box 1', 'Box 2')
BOX_ROLES = ('downstream', 'upstream')
BOX_COLORS = ('box1', 'box2')


class BoxTool(Tool):
    """Click places the selected box, drag moves a box, right-click (or Ctrl+click) places box 2."""

    def __init__(self, page):
        self.page = page
        self._dragging = None

    def press(self, x, y, event):
        page = self.page
        ctrl = bool(event.state & 0x0004)
        hit = None if ctrl else page.box_at(event.x, event.y)
        if hit is not None:
            page.select_box(hit)
            cx, cy = page.boxes[hit]
            self._dragging = (hit, x - cx, y - cy)
            return
        target = 1 if ctrl else page.selected
        page.place_box(target, x, y)
        self._dragging = (target, 0.0, 0.0)

    def drag(self, x, y, event):
        if self._dragging is not None:
            index, dx, dy = self._dragging
            self.page.place_box(index, x - dx, y - dy, advance=False, preview=False)

    def release(self, x, y, event):
        if self._dragging is not None:
            self._dragging = None
            self.page.schedule_preview()

    def right_click(self, x, y, event):
        self.page.place_box(1, x, y)

    def cursor_at(self, x, y, event):
        return 'fleur' if self.page.box_at(event.x, event.y) is not None else 'crosshair'


class AnalyzePage(MeasurePage):
    key = 'analyze'
    title = 'Analyze'
    measure_label = 'Measure velocity and save'
    min_frames = datasets.MIN_VELOCITY_FRAMES

    def __init__(self, parent, app):
        self.boxes = [None, None]
        self.selected = 0
        self.box_w = self.box_h = app.settings.box_size
        self.preview = None
        self._preview_token = 0
        self._preview_after = None
        self._preview_center = None
        self._blur_caches = {}
        super().__init__(parent, app)
        self.view.tool = BoxTool(self)
        self.view.pixel_text = lambda frame, x, y: f'x {x}   y {y}   ·   brightness {int(frame[y, x])}'
        self.preview_worker = LatestOnlyWorker(self, tasks.velocity_preview, self._preview_ready)

    # --------------------------------------------------------------------- sections
    def build_sections(self, body):
        frame = section(body, 'Boxes', help_text=(
            'Place Box 1 downstream and Box 2 upstream on the same capillary, both inside the vessel. '
            'Each box records the mean brightness inside it in every frame; a red-cell plug passing '
            'darkens Box 2 first and Box 1 a little later. Positive velocities mean flow from Box 2 '
            'towards Box 1. The further apart the boxes, the faster the flow that can still be resolved.'))
        self.box_rows = []
        for index in range(2):
            row = tk.Frame(frame, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'],
                           bd=0, cursor='hand2')
            row.pack(fill='x', pady=(0, px(6)))
            swatch = color_swatch(row, COLORS[BOX_COLORS[index]], 12)
            swatch.pack(side='left', padx=(px(10), px(8)), pady=px(9))
            name = tk.Label(row, text=BOX_NAMES[index], font=FONTS['bold'], bg=COLORS['panel'], fg=COLORS['text'])
            name.pack(side='left')
            role = tk.Label(row, text=BOX_ROLES[index], font=FONTS['small'], bg=COLORS['panel'], fg=COLORS['muted'])
            role.pack(side='left', padx=(px(6), 0))
            clear = ttk.Button(row, image=icon('close', 9, COLORS['muted']), style='Ghost.TButton',
                               command=partial(self.clear_box, index))
            clear.pack(side='right', padx=(0, px(4)))
            Tooltip(clear, f'Remove {BOX_NAMES[index]}')
            position = tk.Label(row, text='not placed', font=FONTS['mono_small'], bg=COLORS['panel'],
                                fg=COLORS['faint'])
            position.pack(side='right', padx=(0, px(6)))
            for widget in (row, swatch, name, role, position):
                widget.bind('<Button-1>', lambda e, i=index: self.select_box(i))
            self.box_rows.append((row, (swatch, name, role, position), position, clear))

        size_row = ttk.Frame(frame, style='Panel.TFrame')
        size_row.pack(fill='x', pady=(px(4), 0))
        ttk.Label(size_row, text='Box size', style='Muted.Panel.TLabel').pack(side='left')
        self.size_w = tk.StringVar(value=str(self.box_w))
        self.size_h = tk.StringVar(value=str(self.box_h))
        ttk.Label(size_row, text='px', style='Muted.Panel.TLabel').pack(side='right')
        height = ttk.Spinbox(size_row, from_=2, to=200, width=4, textvariable=self.size_h, command=self._size_changed)
        height.pack(side='right', padx=(0, px(4)))
        ttk.Label(size_row, text='×', style='Muted.Panel.TLabel').pack(side='right', padx=px(4))
        width = ttk.Spinbox(size_row, from_=2, to=200, width=4, textvariable=self.size_w, command=self._size_changed)
        width.pack(side='right')
        for spin in (width, height):
            spin.bind('<Return>', lambda e: self._size_changed())
            spin.bind('<FocusOut>', lambda e: self._size_changed())
        Tooltip(width, 'Width and height of both boxes in video pixels. An odd size samples one pixel less '
                       '(kept from the original tool so earlier measurements stay comparable).')

        self.separation = ttk.Label(frame, text='', style='Mono.Panel.TLabel')
        self.resolvable = ttk.Label(frame, text='', style='Mono.Panel.TLabel')
        for label, value, tip in (
                ('Separation', self.separation, 'Distance between the box centres.'),
                ('Measurable', self.resolvable,
                 'Speeds these boxes can resolve at this frame rate. Faster flow crosses both boxes within one '
                 'frame (a lag of 0, reported as unresolved); move the boxes further apart to measure it. '
                 'The slow limit is a lag of half the shortest report window (100 frames).')):
            row = ttk.Frame(frame, style='Panel.TFrame')
            row.pack(fill='x', pady=(px(4), 0))
            name = ttk.Label(row, text=label, style='Muted.Panel.TLabel')
            name.pack(side='left')
            Tooltip(name, tip)
            value.pack(in_=row, side='right')
            value.lift(row)  # created before the row frame, so raise it above it

        actions = ttk.Frame(frame, style='Panel.TFrame')
        actions.pack(fill='x', pady=(px(10), 0))
        swap = ttk.Button(actions, text='Swap boxes', image=icon('swap', 13, COLORS['text']), compound='left',
                          command=self.swap_boxes)
        swap.pack(side='left')
        Tooltip(swap, 'Exchange Box 1 and Box 2 (X)')
        ttk.Button(actions, text='Clear', style='Ghost.TButton', command=self.clear_boxes).pack(side='left',
                                                                                              padx=(px(6), 0))
        self.box_hint = ttk.Label(frame, text='', style='Faint.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                  justify='left')
        self.box_hint.pack(anchor='w', pady=(px(10), 0))
        separator(body)

        signal = section(body, 'Signal preview', help_text=(
            f'Brightness in both boxes over {tasks.PREVIEW_FRAMES} frames around the current frame, each scaled '
            'to its own range. When both boxes sit on the same capillary the two curves have the same shape, '
            'shifted by the lag. The correlation (r) says how well they match once aligned; the report marks '
            'it with the same colour bands. The velocity here is a single-window estimate.'))
        self.signal_chart = LineChart(signal, height=88, normalize=True)
        self.signal_chart.pack(fill='x')
        legend = ttk.Frame(signal, style='Panel.TFrame')
        legend.pack(fill='x', pady=(px(4), px(6)))
        for index in range(2):
            color_swatch(legend, COLORS[BOX_COLORS[index]], 8).pack(side='left', padx=(0 if index == 0 else px(12), px(4)))
            ttk.Label(legend, text=BOX_NAMES[index], style='Faint.Panel.TLabel').pack(side='left')
        self.preview_window = ttk.Label(legend, text='', style='Faint.Panel.TLabel')
        self.preview_window.pack(side='right')

        numbers = ttk.Frame(signal, style='Panel.TFrame')
        numbers.pack(fill='x')
        self.metric_labels = {}
        for column, (key, label) in enumerate((('r', 'Correlation'), ('lag', 'Lag'), ('velocity', 'Velocity'))):
            cell = ttk.Frame(numbers, style='Panel.TFrame')
            cell.grid(row=0, column=column, sticky='w', padx=(0, px(14)))
            ttk.Label(cell, text=label, style='Faint.Panel.TLabel').pack(anchor='w')
            value = tk.Label(cell, text='–', font=FONTS['mono_big'], bg=COLORS['panel'], fg=COLORS['text'], bd=0)
            value.pack(anchor='w')
            self.metric_labels[key] = value
        self.quality_label = tk.Label(numbers, text='', font=FONTS['tiny'], bg=COLORS['panel'], fg=COLORS['muted'],
                                      bd=0)
        self.quality_label.grid(row=1, column=0, sticky='w')
        self.signal_status = tk.Frame(signal, bg=COLORS['panel'])
        self.signal_status.pack(fill='x', pady=(px(8), 0))
        separator(body)

    # ----------------------------------------------------------------------- state
    def video_for(self, recording):
        return recording.video

    def capture_state(self):
        state = super().capture_state()
        state.update(boxes=list(self.boxes), selected=self.selected, size=(self.box_w, self.box_h))
        return state

    def restore_state(self, state):
        super().restore_state(state)
        state = state or {}
        self.boxes = list(state.get('boxes', [None, None]))
        self.selected = state.get('selected', 0)
        self.box_w, self.box_h = state.get('size', (self.app.settings.box_size, self.app.settings.box_size))
        self.size_w.set(str(self.box_w))
        self.size_h.set(str(self.box_h))
        self.preview = None
        self._preview_center = None
        self._update_boxes_ui()
        self._update_signal_ui()
        self.schedule_preview(50)

    def apply_record(self, record):
        """Put the boxes, size and range of a saved data set's provenance back (Results page)."""
        boxes = record.get('boxes', {})
        try:
            self.box_w, self.box_h = int(boxes['width_px']), int(boxes['height_px'])
            self.boxes = [(int(boxes['box1']['x']), int(boxes['box1']['y'])),
                          (int(boxes['box2']['x']), int(boxes['box2']['y']))]
        except (KeyError, TypeError, ValueError):
            return False
        frames = record.get('frames', {})
        first, last = frames.get('first'), frames.get('last')
        if first is not None and last is not None and self.player.source is not None:
            last = min(int(last), self.player.frame_count - 1)
            self.range = None if (first, last) == (0, self.player.frame_count - 1) else (int(first), last)
        self.size_w.set(str(self.box_w))
        self.size_h.set(str(self.box_h))
        self.selected = 0
        self.refresh()
        self.schedule_preview(50)
        return True

    def update_banner(self):
        recording = self.recording
        if recording is not None and recording.video and not recording.is_stabilized:
            self.banner.show('This recording is not stabilized. Movement of the skin adds to the signal in the '
                             'boxes; stabilize it before measuring.', 'warning',
                             action=lambda: self.app.stabilize(recording), action_text='Stabilize now')
        else:
            self.banner.hide()

    def refresh(self):
        super().refresh()
        self._update_boxes_ui()
        self._update_signal_ui()

    # ------------------------------------------------------------------------ boxes
    def _roi(self, index):
        x, y = self.boxes[index]
        return ROI(int(x), int(y), self.box_w, self.box_h)

    def _clamp(self, x, y):
        shape = self.view.frame_shape()
        if shape is None:
            return int(x), int(y)
        return ROI(int(math.floor(x)), int(math.floor(y)), self.box_w, self.box_h).clamped_center(shape)

    def place_box(self, index, x, y, advance=True, preview=True):
        if self.player.source is None:
            return
        first_placement = self.boxes[index] is None
        self.boxes[index] = self._clamp(x, y)
        if advance and index == 0 and first_placement and self.boxes[1] is None:
            self.selected = 1
        else:
            self.selected = index
        self.draw_overlay()
        self._update_boxes_ui()
        if preview:
            self.schedule_preview()

    def select_box(self, index):
        self.selected = index
        self.draw_overlay()
        self._update_boxes_ui()

    def clear_box(self, index):
        self.boxes[index] = None
        self.selected = index
        self._boxes_changed()

    def clear_boxes(self):
        self.boxes = [None, None]
        self.selected = 0
        self._boxes_changed()

    def swap_boxes(self):
        self.boxes = [self.boxes[1], self.boxes[0]]
        self._boxes_changed()
        if self.boxes[0] and self.boxes[1]:
            self.app.set_status('Boxes swapped: Box 1 is now where Box 2 was.')

    def nudge(self, dx, dy, both=False):
        indices = (0, 1) if both else (self.selected,)
        moved = False
        for index in indices:
            if self.boxes[index] is not None:
                x, y = self.boxes[index]
                self.boxes[index] = self._clamp(x + dx, y + dy)
                moved = True
        if moved:
            self._boxes_changed()

    def _boxes_changed(self):
        self.draw_overlay()
        self._update_boxes_ui()
        self.schedule_preview()

    def _size_changed(self):
        try:
            width, height = int(self.size_w.get()), int(self.size_h.get())
            if not (2 <= width <= 200 and 2 <= height <= 200):
                raise ValueError
        except ValueError:
            self.size_w.set(str(self.box_w))
            self.size_h.set(str(self.box_h))
            return
        if (width, height) == (self.box_w, self.box_h):
            return
        self.box_w, self.box_h = width, height
        self.boxes = [self._clamp(*box) if box else None for box in self.boxes]
        self._boxes_changed()

    def box_at(self, cx, cy):
        """Index of the box under canvas point (cx, cy), the selected one first, or None."""
        shape = self.view.frame_shape()
        if shape is None:
            return None
        tolerance = px(5)
        for index in (self.selected, 1 - self.selected):
            if self.boxes[index] is None:
                continue
            x0, x1, y0, y1 = self._roi(index).bounds(shape)
            left, top = self.view.to_canvas(x0, y0)
            right, bottom = self.view.to_canvas(x1, y1)
            if left - tolerance <= cx <= right + tolerance and top - tolerance <= cy <= bottom + tolerance:
                return index
        return None

    def distance_px(self):
        if None in self.boxes or self.view.frame_shape() is None:
            return None
        return self._roi(0).distance_to(self._roi(1), self.view.frame_shape())

    def _update_boxes_ui(self):
        for index, (row, parts, position, clear) in enumerate(self.box_rows):
            selected = index == self.selected
            background = COLORS['accent_soft'] if selected else COLORS['panel']
            row.configure(bg=background, highlightbackground=COLORS['accent'] if selected else COLORS['border'])
            for widget in parts:
                widget.configure(bg=background)
            if self.boxes[index] is None:
                position.configure(text='not placed', fg=COLORS['faint'])
                clear.state(['disabled'])
            else:
                x, y = self.boxes[index]
                position.configure(text=f'x {x}  y {y}', fg=COLORS['text'])
                clear.state(['!disabled'])
        distance = self.distance_px()
        if distance is None:
            self.separation.configure(text='–')
            self.resolvable.configure(text='–')
        else:
            um = distance * self.app.settings.mm_per_pixel * 1000
            self.separation.configure(text=f'{distance:.1f} px  ·  {um:.1f} µm')
            slowest, fastest = resolvable_range(distance, self.player.fps, self.app.settings.mm_per_pixel)
            self.resolvable.configure(text=f'{slowest:.3f} – {fastest:.2f} mm/s' if math.isfinite(fastest) else '–')
        self.box_hint.configure(text=self._hint_text(long=True))
        self.view.set_hint(self._hint_text(long=False))
        self.update_measure_state()

    def _hint_text(self, long):
        if self.player.source is None:
            return None if not long else ''
        if self.boxes[0] is None and self.boxes[1] is None:
            return ('Click on the video to place Box 1 at the downstream end of a capillary segment.'
                    if long else 'Click the downstream end of a capillary to place Box 1')
        if self.boxes[1] is None:
            return ('Now click upstream on the same capillary to place Box 2 (or right-click anywhere).'
                    if long else 'Click upstream on the same capillary to place Box 2')
        if self.boxes[0] is None:
            return 'Click on the video to place Box 1 downstream.' if long else 'Click to place Box 1 (downstream)'
        if not long:
            return None
        return (f'Drag a box to move it; a click elsewhere moves {BOX_NAMES[self.selected]}. '
                'W A S D nudge it by one pixel, Shift + W A S D moves both. Mouse wheel zooms.')

    def draw_overlay(self):
        canvas = self.view.canvas
        canvas.delete('overlay')
        shape = self.view.frame_shape()
        if shape is None:
            return
        centers = []
        both = None not in self.boxes
        for index in (1 - self.selected, self.selected):     # selected box on top
            if self.boxes[index] is None:
                continue
            x0, x1, y0, y1 = self._roi(index).bounds(shape)
            left, top = self.view.to_canvas(x0, y0)
            right, bottom = self.view.to_canvas(x1, y1)
            color = COLORS[BOX_COLORS[index]]
            if index == self.selected:
                canvas.create_rectangle(left - px(3), top - px(3), right + px(3), bottom + px(3), outline='#FFFFFF',
                                        width=1, dash=(3, 3), tags=('overlay',))
            canvas.create_rectangle(left, top, right, bottom, outline='#000000', width=px(4), tags=('overlay',))
            canvas.create_rectangle(left, top, right, bottom, outline=color, width=px(2), tags=('overlay',))
            # the number goes on the side facing away from the other box, clear of the flow arrow
            cx, cy = (left + right) / 2, (top + bottom) / 2
            ux, uy = -0.7, -0.7
            if both:
                ox, oy = self.view.to_canvas(*self.boxes[1 - index])
                length = math.hypot(cx - ox, cy - oy)
                if length > 1:
                    ux, uy = (cx - ox) / length, (cy - oy) / length
            reach = math.hypot(right - left, bottom - top) / 2 + px(11)
            label = canvas.create_text(cx + ux * reach, cy + uy * reach, text=str(index + 1), anchor='center',
                                       font=FONTS['small_bold'], fill='#111111', tags=('overlay',))
            lx0, ly0, lx1, ly1 = canvas.bbox(label)
            rounded_rect(canvas, lx0 - px(4), ly0 - px(1), lx1 + px(4), ly1 + px(1), px(3), fill=color, outline='',
                         tags=('overlay',))
            canvas.tag_raise(label)
            centers.append((index, (left + right) / 2, (top + bottom) / 2, (right - left) / 2, (bottom - top) / 2))
        if len(centers) == 2:
            ordered = sorted(centers)   # box 1 then box 2
            (_, x1, y1, hw1, hh1), (_, x2, y2, hw2, hh2) = ordered
            length = math.hypot(x1 - x2, y1 - y2)
            margin2 = math.hypot(hw2, hh2) + px(6)
            margin1 = math.hypot(hw1, hh1) + px(6)
            if length > margin1 + margin2 + px(12):
                ux, uy = (x1 - x2) / length, (y1 - y2) / length
                start = (x2 + ux * margin2, y2 + uy * margin2)
                end = (x1 - ux * margin1, y1 - uy * margin1)
                canvas.create_line(*start, *end, fill='#000000', width=px(3), arrow='last',
                                   arrowshape=(px(9), px(10), px(4)), tags=('overlay',))
                canvas.create_line(*start, *end, fill='#F1F4F8', width=px(1.5), arrow='last',
                                   arrowshape=(px(8), px(9), px(3)), dash=(5, 3), tags=('overlay',))
        canvas.tag_raise('hint')
        canvas.tag_raise('readout')

    # ---------------------------------------------------------------------- preview
    def after_frame(self, index):
        if self.player.playing:
            if self._preview_center is None or abs(index - self._preview_center) >= 30:
                self.schedule_preview(0)
        else:
            self.schedule_preview()

    def schedule_preview(self, delay_ms=220):
        if self._preview_after is not None:
            self.after_cancel(self._preview_after)
        self._preview_after = self.after(delay_ms, self._request_preview)

    def _request_preview(self):
        self._preview_after = None
        if self.player.source is None or None in self.boxes:
            self.preview = None
            self._update_signal_ui()
            return
        count = min(tasks.PREVIEW_FRAMES, self.player.frame_count)
        start = max(0, min(self.player.index - count // 2, self.player.frame_count - count))
        self._preview_center = self.player.index
        self._preview_token += 1
        self.preview_worker.request(self._preview_token, self.player.source.path, self._roi(0), self._roi(1),
                                    start, count, self.app.settings.mm_per_pixel)

    def _preview_ready(self, token, result):
        if token != self._preview_token:
            return
        self.preview = result
        self._update_signal_ui()

    def _set_signal_status(self, kind, text, action=None, action_text=''):
        for child in self.signal_status.winfo_children():
            child.destroy()
        if not text:
            return
        colors = {'ok': COLORS['success'], 'warning': COLORS['warning'], 'info': COLORS['muted']}
        names = {'ok': 'ok', 'warning': 'warning', 'info': 'info'}
        tk.Label(self.signal_status, image=icon(names[kind], 13, colors[kind]), bg=COLORS['panel'], bd=0).pack(
            side='left', anchor='n', padx=(0, px(6)), pady=(px(1), 0))
        tk.Label(self.signal_status, text=text, bg=COLORS['panel'], fg=COLORS['text'], font=FONTS['small'],
                 wraplength=px(INSPECTOR_WIDTH - 60), justify='left', bd=0).pack(side='left', fill='x')
        if action is not None:
            ttk.Button(self.signal_status, text=action_text, command=action).pack(side='right', anchor='n')

    def _update_signal_ui(self):
        labels = self.metric_labels
        result = self.preview
        if self.player.source is None or None in self.boxes or result is None or isinstance(result, Exception):
            for value in labels.values():
                value.configure(text='–', fg=COLORS['text'])
            self.quality_label.configure(text='')
            self.preview_window.configure(text='')
            if self.player.source is not None and None not in self.boxes and result is None:
                self.signal_chart.set_message('Reading frames…')
                self._set_signal_status('info', '')
            elif isinstance(result, Exception):
                self.signal_chart.set_message('The preview could not read the video.')
                self._set_signal_status('warning', str(result))
            else:
                self.signal_chart.set_message('Place both boxes to see their brightness signals.')
                self._set_signal_status('info', '')
            return

        fps = result['fps']
        x = (result['start'] + np.arange(len(result['a']))) / fps
        self.signal_chart.set_data([(x, result['a'], COLORS['box1']), (x, result['b'], COLORS['box2'])],
                                   vlines=[(self.player.index / fps, COLORS['faint'])])
        self.preview_window.configure(text=f'{len(result["a"])} frames around the playhead')
        r, lag, velocity = result['r'], result['lag'], result['velocity']
        quality, color = quality_of(r)
        labels['r'].configure(text=f'{r:.2f}' if math.isfinite(r) else '–', fg=color)
        self.quality_label.configure(text=quality if math.isfinite(r) else '', fg=color)
        labels['lag'].configure(text=f'{abs(lag):.0f} fr' if math.isfinite(lag) else '–', fg=COLORS['text'])
        labels['velocity'].configure(text=f'{velocity:.3f}' if math.isfinite(velocity) else '–',
                                     fg=COLORS['text'] if (not math.isfinite(velocity) or velocity >= 0)
                                     else COLORS['warning'])

        if not math.isfinite(r) or not math.isfinite(lag):
            self._set_signal_status('warning', 'No usable signal in these frames: the brightness in a box does not '
                                               'change, or the boxes overlap.')
        elif lag == 0:
            self._set_signal_status('warning', 'Lag of 0 frames: both boxes change at the same moment. Either the '
                                               'flow is too fast for this separation (move the boxes further '
                                               'apart), or the brightness of the whole image is changing, e.g. '
                                               'flicker or focus, which hides the plugs.')
        elif velocity < 0:
            self._set_signal_status('warning', 'The signal reaches Box 1 before Box 2, so the flow seems to run from '
                                               'Box 1 to Box 2. If so, swap the boxes; the report counts flow from '
                                               'Box 2 to Box 1 as positive.', self.swap_boxes, 'Swap')
        elif abs(lag) >= result['max_lag']:
            self._set_signal_status('warning', 'The lag is at the limit of the window: the flow may be slower than '
                                               'these frames can show, or the boxes are on different vessels.')
        elif r < 0.25:
            self._set_signal_status('warning', 'Weak correlation: the boxes may not be on the same capillary, or the '
                                               'flow pauses in these frames.')
        else:
            self._set_signal_status('ok', f'Flow from Box 2 to Box 1, about {velocity:.3f} mm/s in these frames '
                                          f'(lag {abs(lag):.0f} frames = {abs(lag) / fps * 1000:.0f} ms).')

    # -------------------------------------------------------------------- measuring
    def measure_blockers(self):
        missing = [BOX_NAMES[i] for i in range(2) if self.boxes[i] is None]
        if missing:
            return [f'Place {" and ".join(missing)} on the video.']
        if self._overlap():
            return ['The boxes overlap; move them apart along the capillary.']
        if self.recording is not None and self.app.jobs.find(('velocity', self.recording.stem)) is not None:
            return ['A measurement of this recording is already running.']
        return []

    def _overlap(self):
        shape = self.view.frame_shape()
        a = self._roi(0).bounds(shape)
        b = self._roi(1).bounds(shape)
        return a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]

    def submit_measurement(self, name, start, end, done, failed, cancelled):
        recording = self.recording
        path = self.player.source.path
        cache = self._blur_caches.setdefault(path, {})
        work = partial(tasks.measure_velocity_dataset, folder=self.app.folder, stem=recording.stem, name=name,
                       video_path=path, box1=self._roi(0), box2=self._roi(1), start=start, end=end,
                       mm_per_pixel=self.app.settings.mm_per_pixel, time_points=list(self.markers),
                       blur_cache=cache)
        return self.app.jobs.submit(f'Velocity · {recording.stem} · {name}', work, lane='analysis', on_done=done,
                                    on_error=failed, on_cancel=cancelled, key=('velocity', recording.stem))

    def result_status(self, result):
        median = result['summary'].get('median')
        return f' (median {median:.3f} mm/s)' if median is not None and math.isfinite(median) else ''

    def describe_result(self, frame, result):
        summary = result['summary']
        median = summary.get('median', float('nan'))
        big = ttk.Frame(frame, style='Panel.TFrame')
        big.pack(fill='x', pady=(0, px(6)))
        if math.isfinite(median):
            ttk.Label(big, text=f'{median:.3f}', style='Big.Panel.TLabel').pack(side='left')
            ttk.Label(big, text=' mm/s median', style='Muted.Panel.TLabel').pack(side='left', anchor='s',
                                                                                 pady=(0, px(4)))
        else:
            ttk.Label(big, text='No velocity could be resolved', style='Bold.Panel.TLabel').pack(side='left')
        q25, q75 = summary.get('q25', float('nan')), summary.get('q75', float('nan'))
        stat(frame, 'Middle 50 %', f'{q25:.3f} – {q75:.3f} mm/s' if math.isfinite(q25) else '–',
             tooltip='Interquartile range of the window estimates.')
        stat(frame, 'Resolved windows', _percent(summary.get('resolved_fraction')),
             tooltip='Share of window positions that gave a velocity.')
        zero = summary.get('zero_lag_fraction', float('nan'))
        stat(frame, 'Too fast to resolve', _percent(zero),
             style='Mono.Panel.TLabel' if not (math.isfinite(zero) and zero > 0.1) else 'Warning.Panel.TLabel',
             tooltip='Share of window estimates with a lag of 0 frames: faster than these boxes can measure. '
                     'Move the boxes further apart if this is large.')
        stat(frame, 'Median correlation', f'{summary.get("median_correlation", float("nan")):.2f}')

    # ---------------------------------------------------------------------- keyboard
    def handle_page_key(self, event):
        keysym = event.keysym
        key = keysym.lower()
        shift = bool(event.state & 0x0001)
        steps = {'w': (0, -1), 'a': (-1, 0), 's': (0, 1), 'd': (1, 0)}
        if key in steps and self.player.source is not None:
            self.nudge(*steps[key], both=shift)
        elif keysym == '1':
            self.select_box(0)
        elif keysym == '2':
            self.select_box(1)
        elif key == 'x':
            self.swap_boxes()
        elif keysym in ('Delete', 'BackSpace'):
            self.clear_box(self.selected)
        else:
            return False
        return True


def _percent(value):
    return f'{100 * value:.0f} %' if value is not None and math.isfinite(value) else '–'
