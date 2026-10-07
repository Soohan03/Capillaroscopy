"""Validation page: observers read space-time blocks by hand, blinded, to check the centre-line velocity.

A real recording has no ground truth, so the estimator is compared with
people (`capillary.validation`). A *reading set* is drawn from saved
centre-line data sets; every observer reads every block of it, one at a time,
without seeing where it comes from or what the estimator found, by drawing
lines along the streaks or marking that there are none; the *agreement*
(Bland-Altman, ICC, kappa) is computed once the readings are done.

The page has two modes: the overview (reading sets, their readings and the
agreement) and reading, which fills the page with one block at a time.
"""

from __future__ import annotations

import datetime
import math
import os
import random
import time
import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Optional

import numpy as np
from PIL import Image, ImageTk

from capillary import datasets, validation

from . import tasks
from .dialogs import Dialog, ImageViewer, show_error
from .theme import COLORS, FONTS, icon, px
from .widgets import ScrollFrame, Tooltip, register_wheel

SET_LIST_WIDTH = 300
READER_PANEL_WIDTH = 330
THUMB_WIDTH = 300
PLOT_TITLES = {'bland_altman': 'Bland-Altman plots', 'scatter': 'Against each other'}


# ------------------------------------------------------------------------ the block

def block_image(block: np.ndarray) -> np.ndarray:
    """The block as observers see it (`validation.DISPLAY`): uint8, frames down, positions across."""
    data = np.asarray(block, dtype=float)
    data = data - data.mean(axis=0, keepdims=True)
    data = data - data.mean(axis=1, keepdims=True)
    low, high = np.percentile(data, [1, 99])
    return np.clip((data - low) / max(high - low, 1e-9) * 255, 0, 255).astype(np.uint8)


class BlockGeometry:
    """Where a block of `frames` x `positions` lies on a canvas: one scale for both axes, centred.

    One pixel along the line is drawn as wide as one frame is tall, so a streak
    at 45 degrees moves 1 px per frame. Block coordinates are (frame, position)
    with the centre of the first sample at (0, 0).
    """

    def __init__(self, frames: int, positions: int, width: float, height: float, margin: float = 0.0):
        self.frames, self.positions = int(frames), int(positions)
        usable_w, usable_h = max(1.0, width - 2 * margin), max(1.0, height - 2 * margin)
        self.scale = max(min(usable_w / self.positions, usable_h / self.frames), 1e-6)
        self.width, self.height = self.positions * self.scale, self.frames * self.scale
        self.left, self.top = (width - self.width) / 2, (height - self.height) / 2

    def to_canvas(self, frame: float, position: float) -> tuple[float, float]:
        return self.left + (position + 0.5) * self.scale, self.top + (frame + 0.5) * self.scale

    def to_block(self, x: float, y: float) -> tuple[float, float]:
        """(frame, position) under canvas point (x, y), kept inside the block."""
        position = min(max((x - self.left) / self.scale - 0.5, 0.0), self.positions - 1.0)
        frame = min(max((y - self.top) / self.scale - 0.5, 0.0), self.frames - 1.0)
        return frame, position

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.left + self.width and self.top <= y <= self.top + self.height


def _segment_distance(px_, py_, x0, y0, x1, y1) -> float:
    dx, dy = x1 - x0, y1 - y0
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else min(max(((px_ - x0) * dx + (py_ - y0) * dy) / length, 0.0), 1.0)
    return math.hypot(px_ - (x0 + t * dx), py_ - (y0 + t * dy))


class BlockCanvas(tk.Canvas):
    """One block, and the lines the observer draws along its streaks.

    Drag to draw a line; drag an end to move it; right-click a line to remove
    it. Lines are kept in block coordinates, ``[frame, position, frame,
    position]``, as `capillary.validation` stores them.
    """

    def __init__(self, parent, on_change, on_rejected=None):
        super().__init__(parent, bg=COLORS['video_bg'], highlightthickness=0, bd=0, takefocus=1)
        self.on_change = on_change
        self.on_rejected = on_rejected
        self.block = None
        self.image = None
        self.lines: list[list[float]] = []
        self.geometry: Optional[BlockGeometry] = None
        self.message = ''
        self._photo = None
        self._photo_size = None
        self._drag = None              # (line index, which end), and whether the line is new
        self._new = False
        self.bind('<Configure>', lambda e: self.redraw())
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<B1-Motion>', self._motion_drag)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<ButtonPress-3>', self._right)
        self.bind('<Motion>', self._hover)

    def show(self, block, lines=(), message=''):
        self.block = None if block is None else np.asarray(block)
        self.image = None if block is None else block_image(block)
        self.lines = [list(map(float, line)) for line in lines]
        self.message = message
        self._photo_size = None
        self._drag = None
        self.redraw()

    def usable_lines(self) -> list[list[float]]:
        return [line for line in self.lines if validation.usable_line(line)]

    def remove_last(self):
        if self.lines:
            self.lines.pop()
            self._draw_lines()
            self.on_change()

    def clear_lines(self):
        if self.lines:
            self.lines = []
            self._draw_lines()
            self.on_change()

    # -------------------------------------------------------------------- drawing
    def redraw(self):
        self.delete('all')
        width, height = self.winfo_width(), self.winfo_height()
        if width < 40 or height < 40:
            return
        if self.image is None:
            self.geometry = None
            self.create_text(width / 2, height / 2, text=self.message, fill=COLORS['header_muted'],
                             font=FONTS['subtitle'], width=width - px(80), justify='center')
            return
        frames, positions = self.image.shape
        self.geometry = geometry = BlockGeometry(frames, positions, width, height, margin=px(34))
        size = (max(1, int(round(geometry.width))), max(1, int(round(geometry.height))))
        if self._photo_size != size:
            picture = Image.fromarray(self.image).resize(size, Image.Resampling.BILINEAR)
            self._photo = ImageTk.PhotoImage(picture)
            self._photo_size = size
        self.create_image(geometry.left, geometry.top, image=self._photo, anchor='nw')
        self.create_rectangle(geometry.left - 1, geometry.top - 1, geometry.left + geometry.width,
                              geometry.top + geometry.height, outline=COLORS['header_muted'])
        self.create_text(geometry.left, geometry.top - px(8), anchor='sw', fill=COLORS['header_muted'],
                         font=FONTS['small'], text=f'along the line  →   ({positions - 1} px, start on the left)')
        self.create_text(geometry.left - px(8), geometry.top, anchor='ne', fill=COLORS['header_muted'],
                         font=FONTS['small'], text='time\n↓')
        self._draw_lines()

    def _draw_lines(self):
        self.delete('lines')
        geometry = self.geometry
        if geometry is None:
            return
        for line in self.lines:
            x0, y0 = geometry.to_canvas(line[0], line[1])
            x1, y1 = geometry.to_canvas(line[2], line[3])
            usable = validation.usable_line(line)
            color = COLORS['line'] if usable else COLORS['faint']
            self.create_line(x0, y0, x1, y1, fill='#000000', width=px(4), tags=('lines',))
            self.create_line(x0, y0, x1, y1, fill=color, width=px(2), tags=('lines',))
            for x, y in ((x0, y0), (x1, y1)):
                r = px(3.5)
                self.create_oval(x - r, y - r, x + r, y + r, fill='#FFFFFF', outline='#000000', tags=('lines',))

    # ---------------------------------------------------------------------- mouse
    def _end_at(self, x, y):
        """(line index, end) of the line end under (x, y), or None."""
        geometry = self.geometry
        best, best_distance = None, px(8)
        for index, line in enumerate(self.lines):
            for end in (0, 1):
                cx, cy = geometry.to_canvas(line[2 * end], line[2 * end + 1])
                distance = math.hypot(cx - x, cy - y)
                if distance <= best_distance:
                    best, best_distance = (index, end), distance
        return best

    def _line_at(self, x, y):
        geometry = self.geometry
        best, best_distance = None, px(6)
        for index, line in enumerate(self.lines):
            x0, y0 = geometry.to_canvas(line[0], line[1])
            x1, y1 = geometry.to_canvas(line[2], line[3])
            distance = _segment_distance(x, y, x0, y0, x1, y1)
            if distance <= best_distance:
                best, best_distance = index, distance
        return best

    def _press(self, event):
        self.focus_set()
        if self.geometry is None:
            return
        end = self._end_at(event.x, event.y)
        if end is not None:
            self._drag, self._new = end, False
            return
        if not self.geometry.contains(event.x, event.y):
            return
        frame, position = self.geometry.to_block(event.x, event.y)
        self.lines.append([frame, position, frame, position])
        self._drag, self._new = (len(self.lines) - 1, 1), True
        self._draw_lines()

    def _motion_drag(self, event):
        if self._drag is None or self.geometry is None:
            return
        index, end = self._drag
        frame, position = self.geometry.to_block(event.x, event.y)
        self.lines[index][2 * end:2 * end + 2] = [frame, position]
        self._draw_lines()

    def _release(self, event):
        if self._drag is None:
            return
        index, _ = self._drag
        line = self.lines[index]
        x0, y0 = self.geometry.to_canvas(line[0], line[1])
        x1, y1 = self.geometry.to_canvas(line[2], line[3])
        if self._new and math.hypot(x1 - x0, y1 - y0) < px(12):
            del self.lines[index]                     # a click, not a line
        elif not validation.usable_line(line):
            del self.lines[index]
            if self.on_rejected is not None:
                self.on_rejected()
        self._drag, self._new = None, False
        self._draw_lines()
        self.on_change()

    def _right(self, event):
        if self.geometry is None:
            return
        index = self._line_at(event.x, event.y)
        if index is not None:
            del self.lines[index]
            self._draw_lines()
            self.on_change()

    def _hover(self, event):
        if self.geometry is None:
            cursor = ''
        elif self._end_at(event.x, event.y) is not None:
            cursor = 'fleur'
        elif self.geometry.contains(event.x, event.y):
            cursor = 'crosshair'
        else:
            cursor = ''
        if str(self.cget('cursor')) != cursor:
            self.configure(cursor=cursor)


# ----------------------------------------------------------------------- reading mode

class Reader(ttk.Frame):
    """One block after another: the observer draws lines along the streaks, or marks that there are none.

    What is on screen is saved as it changes, so stopping at any moment loses
    nothing. The time spent on a block is recorded with it.
    """

    def __init__(self, parent, page):
        super().__init__(parent, style='TFrame')
        self.page = page
        self.reading_set: Optional[validation.ReadingSet] = None
        self.reading: Optional[validation.Reading] = None
        self.index = 0
        self.finished = False
        self._shown_at = time.monotonic()
        self._base_seconds = 0.0
        self._paused = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        holder = ttk.Frame(self, style='TFrame', padding=(px(14), px(12), px(12), px(12)))
        holder.grid(row=0, column=0, sticky='nsew')
        self.canvas = BlockCanvas(holder, on_change=self._lines_changed, on_rejected=self._line_rejected)
        self.canvas.pack(fill='both', expand=True)

        tk.Frame(self, bg=COLORS['border'], width=1).grid(row=0, column=1, sticky='ns')
        panel = ttk.Frame(self, style='Panel.TFrame', padding=(px(18), px(16), px(18), px(16)), width=px(READER_PANEL_WIDTH))
        panel.grid(row=0, column=2, sticky='ns')
        panel.pack_propagate(False)
        wrap = px(READER_PANEL_WIDTH - 40)
        ttk.Label(panel, text='READING', style='Section.Panel.TLabel').pack(anchor='w')
        self.who = ttk.Label(panel, text='', style='Subtitle.Panel.TLabel', wraplength=wrap)
        self.who.pack(anchor='w', pady=(px(4), 0))
        self.position = ttk.Label(panel, text='', style='Mono.Panel.TLabel')
        self.position.pack(anchor='w', pady=(px(10), px(4)))
        self.progress = ttk.Progressbar(panel, style='Thin.Horizontal.TProgressbar', maximum=1.0)
        self.progress.pack(fill='x')
        self.progress_text = ttk.Label(panel, text='', style='Faint.Panel.TLabel')
        self.progress_text.pack(anchor='w', pady=(px(3), 0))

        ttk.Label(panel, style='Muted.Panel.TLabel', wraplength=wrap, justify='left', text=(
            'Drag along a streak to draw a line on it: red cells and plasma gaps moving along the vessel draw '
            'slanted streaks, and their slope is the speed. Draw a line on each clear streak you see (two or three '
            'are enough); the block\'s slope is their mean. Drag an end to adjust a line, right-click it to '
            'remove it.\n\nIf there are no clear streaks, press "No clear streaks".')).pack(
            anchor='w', pady=(px(16), 0))

        self.status = tk.Label(panel, text='', bg=COLORS['panel'], fg=COLORS['text'], font=FONTS['small'],
                               wraplength=wrap, justify='left', anchor='w')
        self.status.pack(fill='x', pady=(px(16), 0))

        tools = ttk.Frame(panel, style='Panel.TFrame')
        tools.pack(fill='x', pady=(px(12), 0))
        self.none_button = ttk.Button(tools, text='No clear streaks', command=self.no_streaks)
        self.none_button.pack(side='left')
        Tooltip(self.none_button, 'This block shows no streaks whose slope you could read (N)')
        self.clear_button = ttk.Button(tools, text='Remove lines', style='Ghost.TButton',
                                       command=self.canvas.clear_lines)
        self.clear_button.pack(side='left', padx=(px(6), 0))
        Tooltip(self.clear_button, 'Remove every line on this block (Backspace removes the last one)')

        navigation = ttk.Frame(panel, style='Panel.TFrame')
        navigation.pack(side='bottom', fill='x')
        self.next_button = ttk.Button(navigation, text='Next block  →', style='Accent.TButton', command=self.next,
                                      padding=(px(12), px(8)))
        self.next_button.pack(fill='x')
        Tooltip(self.next_button, 'Keep the lines and go on (Enter or →)')
        row = ttk.Frame(navigation, style='Panel.TFrame')
        row.pack(fill='x', pady=(px(8), 0))
        self.back_button = ttk.Button(row, text='←  Previous', command=self.previous)
        self.back_button.pack(side='left')
        Tooltip(self.back_button, 'Back to the block before (←)')
        stop = ttk.Button(row, text='Finish later', style='Ghost.TButton', command=self.finish_later)
        stop.pack(side='right')
        Tooltip(stop, 'Back to the overview; everything so far is saved (Esc)')
        ttk.Label(navigation, text='Saved after every change.', style='Faint.Panel.TLabel').pack(anchor='w',
                                                                                            pady=(px(8), 0))

    # ---------------------------------------------------------------------- state
    @property
    def item_id(self) -> Optional[str]:
        if self.reading is None or not self.reading.order:
            return None
        return self.reading.order[self.index]

    def start(self, reading_set, reading):
        self.reading_set, self.reading = reading_set, reading
        first = reading.first_unread()
        self.index = first if first is not None else 0
        self.finished = first is None
        self.who.configure(text=f'{reading.observer}  ·  session {reading.session}')
        self._show()

    def _show(self):
        reading = self.reading
        if self.finished:
            self.canvas.show(None, message=f'All {len(reading.order)} blocks are read.\n\n'
                                           'Go back to look at a block again, or finish.')
        else:
            item_id = self.item_id
            lines = reading.lines(item_id) if reading.outcome(item_id) == validation.SLOPE else []
            self.canvas.show(self.reading_set.block(item_id), lines)
            self._shown_at = time.monotonic()
            self._paused = False
            self._base_seconds = reading.seconds(item_id) if math.isfinite(reading.seconds(item_id)) else 0.0
        self.canvas.focus_set()
        self._update_panel()

    def _seconds(self) -> float:
        """Time spent on the current block: earlier visits plus this one, without time away from the page."""
        return self._base_seconds + (0.0 if self._paused else time.monotonic() - self._shown_at)

    def pause(self):
        """The page is left: save, and stop counting time on this block."""
        if self.reading is None or self.finished or self._paused:
            return
        self.store()
        self._base_seconds = self._seconds()
        self._paused = True

    def resume(self):
        if self._paused:
            self._shown_at = time.monotonic()
            self._paused = False
        self.canvas.focus_set()

    def store(self):
        """Save what is on screen for the current block."""
        if self.reading is None or self.finished:
            return
        item_id = self.item_id
        lines = self.canvas.usable_lines()
        try:
            if lines:
                self.reading.record_lines(item_id, lines, self._seconds())
            elif self.reading.outcome(item_id) == validation.SLOPE:
                self.reading.clear(item_id)
        except OSError as exc:
            show_error(self, 'The reading could not be saved', str(exc))

    def _update_panel(self, note=None, kind='info'):
        reading = self.reading
        total = len(reading.order)
        read = reading.read_count
        self.position.configure(text='Finished' if self.finished else f'Block {self.index + 1} of {total}')
        self.progress.configure(value=read / total if total else 0)
        self.progress_text.configure(text=f'{read} of {total} read')
        if note is None:
            if self.finished:
                note, kind = 'Every block has a reading. Finish to go back to the overview.', 'ok'
            else:
                outcome = reading.outcome(self.item_id)
                count = len(self.canvas.usable_lines())
                if count:
                    note, kind = f'{count} line{"s" if count != 1 else ""} drawn.', 'ok'
                elif outcome == validation.NO_STREAKS:
                    note, kind = 'Marked: no clear streaks.', 'ok'
                else:
                    note = 'Not read yet.'
        colors = {'info': COLORS['muted'], 'ok': COLORS['success'], 'warning': COLORS['warning']}
        self.status.configure(text=note, fg=colors[kind])
        self.back_button.state(['!disabled'] if (self.index > 0 or self.finished) else ['disabled'])
        self.none_button.state(['disabled'] if self.finished else ['!disabled'])
        self.clear_button.state(['disabled'] if self.finished else ['!disabled'])
        self.next_button.configure(text='Finish' if self.finished else
                                   ('Last block: finish  →' if self.index == total - 1 else 'Next block  →'))

    # -------------------------------------------------------------------- actions
    def _lines_changed(self):
        self.store()
        self._update_panel()

    def _line_rejected(self):
        self._update_panel(f'That line is too flat to give a slope: it must span at least '
                           f'{validation.MIN_LINE_FRAMES:.0f} frames from top to bottom.', 'warning')

    def next(self):
        if self.reading is None:
            return
        if self.finished:
            self.finish_later()
            return
        item_id = self.item_id
        if not self.canvas.usable_lines() and self.reading.outcome(item_id) != validation.NO_STREAKS:
            self._update_panel('Draw a line along at least one streak, or press "No clear streaks" (N) if this '
                               'block has none.', 'warning')
            return
        self.store()
        self._advance()

    def _advance(self):
        reading = self.reading
        if self.index + 1 < len(reading.order):
            self.index += 1
        else:
            unread = reading.first_unread()
            if unread is None:
                self.finished = True
            else:
                self.index = unread
                self._show()
                self._update_panel('Some blocks were skipped; this is the first of them.', 'warning')
                return
        self._show()

    def previous(self):
        if self.reading is None:
            return
        if self.finished:
            self.finished = False
            self.index = len(self.reading.order) - 1
        elif self.index > 0:
            self.store()
            self.index -= 1
        else:
            return
        self._show()

    def no_streaks(self):
        if self.reading is None or self.finished:
            return
        self.canvas.lines = []
        try:
            self.reading.record_no_streaks(self.item_id, self._seconds())
        except OSError as exc:
            show_error(self, 'The reading could not be saved', str(exc))
            return
        self._advance()

    def finish_later(self):
        self.store()
        self.page.leave_reading()

    def handle_key(self, event) -> bool:
        keysym = event.keysym
        if keysym in ('Return', 'KP_Enter', 'Right', 'KP_Right'):
            self.next()
        elif keysym in ('Left', 'KP_Left'):
            self.previous()
        elif keysym.lower() == 'n':
            self.no_streaks()
        elif keysym in ('BackSpace', 'Delete'):
            self.canvas.remove_last()
        elif keysym == 'Escape':
            self.finish_later()
        else:
            return False
        return True


# ------------------------------------------------------------------------ dialogs

class NewReadingSetDialog(Dialog):
    """Name, data sets, blocks per data set, sampling and seed of a new reading set."""

    def __init__(self, parent, sources, existing):
        super().__init__(parent, 'New reading set')
        self.existing = set(existing)
        body = self.body
        wrap = px(560)
        ttk.Label(body, text='New reading set', style='Title.Panel.TLabel').pack(anchor='w')
        ttk.Label(body, style='Muted.Panel.TLabel', wraplength=wrap, justify='left', text=(
            'Blocks of 3 s are drawn at random from the chosen centre-line data sets, never overlapping, and '
            'copied into the set. Observers then read them by hand without knowing where they come from or what '
            'the estimator found.')).pack(anchor='w', pady=(px(6), px(14)))

        ttk.Label(body, text='Name', style='Bold.Panel.TLabel').pack(anchor='w')
        self.name = tk.StringVar(value=datasets.suggest_dataset_name(existing, base='reading'))
        self.name_entry = ttk.Entry(body, textvariable=self.name, width=40)
        self.name_entry.pack(anchor='w', pady=(px(3), px(12)))

        head = ttk.Frame(body, style='Panel.TFrame')
        head.pack(fill='x')
        ttk.Label(head, text='Data sets', style='Bold.Panel.TLabel').pack(side='left')
        ttk.Button(head, text='None', style='Link.Ghost.TButton', command=lambda: self._check_all(False)).pack(
            side='right')
        ttk.Button(head, text='All', style='Link.Ghost.TButton', command=lambda: self._check_all(True)).pack(
            side='right')
        box = tk.Frame(body, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'])
        box.pack(fill='x', pady=(px(3), px(12)))
        scroll = ScrollFrame(box)
        scroll.canvas.configure(height=px(min(220, 26 * max(1, len(sources)) + 8)), width=px(540))
        scroll.pack(fill='both', expand=True)
        self.checks = []
        for stem, name in sources:
            variable = tk.BooleanVar(value=True)
            ttk.Checkbutton(scroll.body, text=f'{stem}  ·  {name}', variable=variable, style='Panel.TCheckbutton',
                            command=self._update_summary).pack(anchor='w', padx=px(8), pady=px(2))
            self.checks.append(((stem, name), variable))

        options = ttk.Frame(body, style='Panel.TFrame')
        options.pack(fill='x')
        ttk.Label(options, text='Blocks per data set', style='Bold.Panel.TLabel').grid(row=0, column=0, sticky='w')
        self.count = tk.StringVar(value=str(validation.DEFAULT_BLOCKS_PER_DATASET))
        ttk.Spinbox(options, from_=1, to=40, textvariable=self.count, width=5,
                    command=self._update_summary).grid(row=0, column=1, sticky='w', padx=(px(10), 0))
        self.count.trace_add('write', lambda *_: self._update_summary())
        ttk.Label(options, text='Seed', style='Bold.Panel.TLabel').grid(row=0, column=2, sticky='w', padx=(px(24), 0))
        self.seed = tk.StringVar(value=str(random.SystemRandom().randrange(1, 1_000_000)))
        seed_entry = ttk.Entry(options, textvariable=self.seed, width=10)
        seed_entry.grid(row=0, column=3, sticky='w', padx=(px(10), 0))
        Tooltip(seed_entry, 'Recorded with the set. The same seed and data sets draw the same blocks, and give '
                            'every observer the same order again.')
        self.balanced = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text='Half from blocks the estimator resolved, half from blocks it did not',
                        variable=self.balanced, style='Panel.TCheckbutton').pack(anchor='w', pady=(px(12), 0))
        ttk.Label(body, style='Faint.Panel.TLabel', wraplength=wrap, justify='left', text=(
            'Recommended: agreement on velocity needs resolved blocks, agreement on whether a block can be read '
            'at all needs both kinds.')).pack(anchor='w', padx=(px(22), 0))
        self.summary = ttk.Label(body, text='', style='Muted.Panel.TLabel')
        self.summary.pack(anchor='w', pady=(px(12), 0))
        self.error = ttk.Label(body, text='', style='Danger.Panel.TLabel', wraplength=wrap)
        self.error.pack(anchor='w', pady=(px(6), 0))

        self.button('Draw blocks', self._ok, 'Accent.TButton', default=True)
        self.button('Cancel', self.cancel)
        self._update_summary()

    def _check_all(self, value):
        for _, variable in self.checks:
            variable.set(value)
        self._update_summary()

    def _chosen(self):
        return [source for source, variable in self.checks if variable.get()]

    def _update_summary(self):
        try:
            count = int(self.count.get())
        except ValueError:
            count = 0
        chosen = len(self._chosen())
        self.summary.configure(text=f'Up to {count * chosen} blocks from {chosen} data set'
                                    f'{"s" if chosen != 1 else ""}.' if count > 0 else '')

    def _ok(self):
        name = self.name.get().strip()
        message = validation.validate_set_name(name)
        if message is None and name in self.existing:
            message = f'A reading set named "{name}" already exists.'
        if message:
            self.error.configure(text=message)
            return
        sources = self._chosen()
        if not sources:
            self.error.configure(text='Choose at least one data set.')
            return
        try:
            count = int(self.count.get())
            if not 1 <= count <= 40:
                raise ValueError
        except ValueError:
            self.error.configure(text='Blocks per data set must be a whole number from 1 to 40.')
            return
        try:
            seed = int(self.seed.get())
            if seed < 0:
                raise ValueError
        except ValueError:
            self.error.configure(text='The seed must be a whole number, for example 1234.')
            return
        self.finish({'name': name, 'sources': sources, 'blocks_per_dataset': count,
                     'balanced': bool(self.balanced.get()), 'seed': seed})


class StartReadingDialog(Dialog):
    """Who reads, and which session."""

    def __init__(self, parent, reading_set, observer=''):
        super().__init__(parent, 'Start reading')
        self.reading_set = reading_set
        body = self.body
        wrap = px(460)
        ttk.Label(body, text='Start reading', style='Title.Panel.TLabel').pack(anchor='w')
        ttk.Label(body, style='Muted.Panel.TLabel', wraplength=wrap, justify='left', text=(
            f'The {len(reading_set.items)} blocks of "{reading_set.name}" are shown one at a time, in an order of '
            'your own, without where they come from or what the estimator found. Everything is saved as you go; '
            'you can stop and continue later.')).pack(anchor='w', pady=(px(6), px(14)))
        grid = ttk.Frame(body, style='Panel.TFrame')
        grid.pack(fill='x')
        ttk.Label(grid, text='Observer', style='Bold.Panel.TLabel').grid(row=0, column=0, sticky='w')
        self.observer = tk.StringVar(value=observer)
        self.entry = ttk.Entry(grid, textvariable=self.observer, width=12)
        self.entry.grid(row=0, column=1, sticky='w', padx=(px(10), 0))
        ttk.Label(grid, text='initials', style='Faint.Panel.TLabel').grid(row=0, column=2, sticky='w',
                                                                          padx=(px(8), 0))
        ttk.Label(grid, text='Session', style='Bold.Panel.TLabel').grid(row=1, column=0, sticky='w', pady=(px(8), 0))
        self.session = tk.StringVar(value='1')
        ttk.Spinbox(grid, from_=1, to=20, textvariable=self.session, width=5).grid(row=1, column=1, sticky='w',
                                                                                   padx=(px(10), 0),
                                                                                   pady=(px(8), 0))
        self.info = ttk.Label(body, text='', style='Muted.Panel.TLabel', wraplength=wrap, justify='left')
        self.info.pack(anchor='w', pady=(px(12), 0))
        ttk.Label(body, style='Faint.Panel.TLabel', wraplength=wrap, justify='left', text=(
            'A second session by the same observer, some days later and in a new order, measures how well '
            'one person repeats their own reading.')).pack(anchor='w', pady=(px(8), 0))
        self.error = ttk.Label(body, text='', style='Danger.Panel.TLabel', wraplength=wrap)
        self.error.pack(anchor='w', pady=(px(6), 0))
        self.observer.trace_add('write', lambda *_: self._observer_changed())
        self.session.trace_add('write', lambda *_: self._update_info())
        self.button('Start', self._ok, 'Accent.TButton', default=True)
        self.button('Cancel', self.cancel)
        self._observer_changed()
        self.entry.focus_set()

    def _observer_changed(self):
        if validation.validate_observer(self.observer.get()) is None:
            self.session.set(str(self.reading_set.next_session(self.observer.get())))
        self._update_info()

    def _update_info(self):
        observer = validation.normalize_observer(self.observer.get())
        try:
            session = int(self.session.get())
        except ValueError:
            self.info.configure(text='')
            return
        if not observer or validation.validate_observer(observer):
            self.info.configure(text='')
            return
        existing = {r.session: r for r in self.reading_set.readings() if r.observer == observer}
        reading = existing.get(session)
        total = len(self.reading_set.items)
        if reading is None:
            done = [s for s in sorted(existing) if existing[s].is_complete]
            text = f'Starts session {session} for {observer}.'
            if done:
                text += f' Finished before: session{"s" if len(done) > 1 else ""} {", ".join(map(str, done))}.'
        elif reading.is_complete:
            text = f'{observer} has finished session {session}: you can look through it and change readings.'
        else:
            text = f'Continues {observer}\'s session {session}: {reading.read_count} of {total} blocks read.'
        self.info.configure(text=text)

    def _ok(self):
        message = validation.validate_observer(self.observer.get())
        if message:
            self.error.configure(text=message)
            return
        try:
            session = int(self.session.get())
            if session < 1:
                raise ValueError
        except ValueError:
            self.error.configure(text='The session must be a whole number from 1.')
            return
        self.finish((validation.normalize_observer(self.observer.get()), session))


# --------------------------------------------------------------------------- set list

class SetList(tk.Canvas):
    """The reading sets: name and a line of detail per row."""

    def __init__(self, parent, on_select):
        super().__init__(parent, bg=COLORS['panel'], highlightthickness=0, bd=0, width=px(SET_LIST_WIDTH))
        self.on_select = on_select
        self.rows: list[tuple[str, str]] = []
        self.selected: Optional[str] = None
        self.hover: Optional[str] = None
        self.row_height = px(58)
        self.empty_text = ''
        self.bind('<Configure>', lambda e: self.redraw())
        self.bind('<ButtonPress-1>', self._click)
        self.bind('<Motion>', self._motion)
        self.bind('<Leave>', lambda e: self._set_hover(None))
        register_wheel(self, lambda steps, e: self.yview_scroll(-steps * 2, 'units'))
        self.configure(yscrollincrement=px(20))

    def set_rows(self, rows, selected, empty_text=''):
        self.rows, self.selected, self.empty_text = list(rows), selected, empty_text
        self.redraw()

    def _row_at(self, y):
        index = int(self.canvasy(y) // self.row_height)
        return self.rows[index][0] if 0 <= index < len(self.rows) else None

    def _click(self, event):
        name = self._row_at(event.y)
        if name is not None:
            self.on_select(name)

    def _motion(self, event):
        self._set_hover(self._row_at(event.y))

    def _set_hover(self, name):
        if name != self.hover:
            self.hover = name
            self.redraw()

    def redraw(self):
        self.delete('all')
        width = self.winfo_width()
        if width < 20:
            return
        height = self.row_height
        self.configure(scrollregion=(0, 0, width, max(len(self.rows) * height, self.winfo_height())))
        if not self.rows:
            self.create_text(width / 2, px(50), text=self.empty_text, fill=COLORS['faint'], font=FONTS['small'],
                             width=width - px(40), justify='center')
            return
        for row, (name, detail) in enumerate(self.rows):
            top = row * height
            if name == self.selected:
                self.create_rectangle(0, top, width, top + height, fill=COLORS['accent_soft'], outline='')
                self.create_rectangle(0, top, px(3), top + height, fill=COLORS['accent'], outline='')
            elif name == self.hover:
                self.create_rectangle(0, top, width, top + height, fill=COLORS['panel_alt'], outline='')
            self.create_line(px(12), top + height - 1, width - px(12), top + height - 1, fill=COLORS['border'])
            self.create_text(px(16), top + px(12), text=name, anchor='nw', font=FONTS['bold'], fill=COLORS['text'],
                             width=width - px(28))
            self.create_text(px(16), top + px(32), text=detail, anchor='nw', font=FONTS['small'],
                             fill=COLORS['muted'], width=width - px(28))


# ------------------------------------------------------------------------------ page

def _finite(value) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool) \
        and math.isfinite(value)


def _signed(value, digits=4):
    return f'{value:+.{digits}f}' if _finite(value) else '–'


def _between(low, high, digits=4):
    return f'{low:+.{digits}f} to {high:+.{digits}f}' if _finite(low) and _finite(high) else '–'


def _ratio_limits(low, high):
    if not (_finite(low) and _finite(high)):
        return '–'
    return f'{100 * (low - 1):+.0f} % to {100 * (high - 1):+.0f} %'


def _with_ci(value, low, high, digits=2):
    if not _finite(value):
        return '–'
    text = f'{value:.{digits}f}'
    return text + (f'  ({low:.{digits}f} to {high:.{digits}f})' if _finite(low) and _finite(high) else '')


def _percent(value):
    return f'{100 * value:.0f} %' if _finite(value) else '–'


def _thumbnail(path, width):
    image = Image.open(path).convert('RGBA')
    background = Image.new('RGBA', image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert('RGB')
    image.thumbnail((width, width), Image.Resampling.LANCZOS)
    return image


class ValidationPage(ttk.Frame):
    key = 'validation'
    title = 'Validation'
    uses_library = False

    def __init__(self, parent, app):
        super().__init__(parent, style='TFrame')
        self.app = app
        self.names: list[str] = []
        self.selected: Optional[str] = None
        self.current: Optional[validation.ReadingSet] = None
        self.reading_mode = False
        self._photos = []
        self._agreement_job = None

        self.overview = ttk.Frame(self, style='TFrame')
        self.overview.columnconfigure(2, weight=1)
        self.overview.rowconfigure(0, weight=1)
        side = ttk.Frame(self.overview, style='Panel.TFrame')
        side.grid(row=0, column=0, sticky='ns')
        header = ttk.Frame(side, style='Panel.TFrame', padding=(px(16), px(14), px(10), px(8)))
        header.pack(fill='x')
        ttk.Label(header, text='Reading sets', style='Subtitle.Panel.TLabel').pack(side='left')
        self.count = ttk.Label(header, text='', style='Muted.Panel.TLabel')
        self.count.pack(side='left', padx=(px(8), 0), pady=(px(2), 0))
        new = ttk.Button(header, text='New…', command=self.new_set)
        new.pack(side='right')
        Tooltip(new, 'Draw a new reading set from centre-line data sets')
        ttk.Separator(side, orient='horizontal').pack(fill='x')
        self.set_list = SetList(side, self.select)
        self.set_list.pack(fill='both', expand=True)
        ttk.Separator(side, orient='horizontal').pack(fill='x')
        ttk.Label(side, text='Observers read the blocks of a set by hand,\nblinded; the agreement shows how '
                             'well\nthe estimator matches them.', style='Faint.Panel.TLabel',
                  padding=(px(16), px(8))).pack(fill='x')
        tk.Frame(self.overview, bg=COLORS['border'], width=1).grid(row=0, column=1, sticky='ns')
        self.details = ScrollFrame(self.overview, background=COLORS['bg'])
        self.details.canvas.configure(bg=COLORS['bg'])
        self.details.body.configure(style='TFrame', padding=(px(24), px(18), px(24), px(24)))
        self.details.grid(row=0, column=2, sticky='nsew')
        self.overview.pack(fill='both', expand=True)

        self.reader = Reader(self, self)
        app.jobs.add_listener(self._jobs_changed)

    # ---------------------------------------------------------------- page protocol
    def show_recording(self, recording):
        pass

    def on_show(self):
        if self.reading_mode:
            self.reader.resume()
        else:
            self.refresh()

    def on_hide(self):
        if self.reading_mode:
            self.reader.pause()

    def handle_key(self, event) -> bool:
        if self.reading_mode:
            return self.reader.handle_key(event)
        return False

    def refresh(self):
        folder = self.app.folder.validation
        self.names = validation.list_reading_sets(folder)
        if self.selected not in self.names:
            self.selected = self.names[0] if self.names else None
        rows = []
        for name in self.names:
            try:
                reading_set = validation.load_reading_set(folder, name)
                readings = reading_set.readings()
                observers = sorted({r.observer for r in readings})
                detail = f'{len(reading_set.items)} blocks  ·  ' + (
                    f'{len(readings)} reading{"s" if len(readings) != 1 else ""} by {", ".join(observers)}'
                    if readings else 'not read yet')
            except (OSError, ValueError, KeyError) as exc:
                detail = f'cannot be read: {exc}'
            rows.append((name, detail))
        self.count.configure(text=str(len(self.names)) if self.names else '')
        self.set_list.set_rows(rows, self.selected, 'No reading sets yet.')
        self._load_selected()
        self._rebuild()

    def select(self, name):
        if name != self.selected:
            self.selected = name
            self.set_list.set_rows(self.set_list.rows, name, self.set_list.empty_text)
            self._load_selected()
            self._rebuild()

    def _load_selected(self):
        self.current = None
        self._load_error = ''
        if self.selected is not None:
            try:
                self.current = validation.load_reading_set(self.app.folder.validation, self.selected)
                if not self.current.items:
                    raise ValueError('it holds no blocks')
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.current = None
                self._load_error = str(exc) or type(exc).__name__

    # ------------------------------------------------------------------- overview
    def _card(self, parent, title=None):
        outer = tk.Frame(parent, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'], bd=0)
        outer.pack(fill='x', pady=(px(12), 0))
        inner = ttk.Frame(outer, style='Panel.TFrame', padding=(px(16), px(14)))
        inner.pack(fill='both', expand=True)
        if title:
            ttk.Label(inner, text=title.upper(), style='Section.Panel.TLabel').pack(anchor='w', pady=(0, px(8)))
        return inner

    def _line_sources(self):
        return [(recording.stem, name) for recording in self.app.recordings for name in recording.line_sets]

    def _rebuild(self):
        body = self.details.body
        for child in body.winfo_children():
            child.destroy()
        self._photos = []
        reading_set = self.current
        if reading_set is None and self.selected is not None:
            ttk.Label(body, text=self.selected, style='Title.TLabel').pack(anchor='w')
            ttk.Label(body, text=f'This reading set cannot be read: {self._load_error}', style='Danger.TLabel',
                      wraplength=px(900), justify='left').pack(anchor='w', pady=(px(8), 0))
            return
        if reading_set is None:
            self._empty_state(body)
            return
        header = ttk.Frame(body, style='TFrame')
        header.pack(fill='x')
        ttk.Label(header, text=reading_set.name, style='Title.TLabel').pack(side='left')
        ttk.Button(header, text='Show in folder', image=icon('folder', 14, COLORS['muted']), compound='left',
                   command=lambda: self.app.open_folder(os.path.join(reading_set.directory,
                                                                     validation.SET_FILE))).pack(side='right')
        record = reading_set.record
        sources = reading_set.source_summary()
        recordings = {source['recording'] for source in sources}
        sampling = record.get('sampling') or {}
        created = record.get('created', '')
        try:
            created = f'{datetime.datetime.fromisoformat(created):%d %b %Y, %H:%M}'
        except ValueError:
            pass
        resolved = sum(1 for item in reading_set.items if item.estimate.get('resolved'))
        first = reading_set.items[0]
        balanced = (' (half of each data set\'s blocks drawn from resolved ones, where it had enough)'
                    if sampling.get('balanced') else '')
        ttk.Label(body, style='Muted.TLabel', wraplength=px(900), justify='left', text=(
            f'{len(reading_set.items)} blocks of {first.frames / first.fps:.1f} s from {len(sources)} '
            f'centre-line data set{"s" if len(sources) != 1 else ""} of {len(recordings)} '
            f'recording{"s" if len(recordings) != 1 else ""}  ·  {resolved} resolved by the estimator when drawn'
            f'{balanced}  ·  drawn {created}  ·  seed {record.get("seed")}')).pack(anchor='w', pady=(px(4), 0))

        self._readings_card(body, reading_set)
        self._agreement_card(body, reading_set)
        self._sources_card(body, sources)

    def _empty_state(self, body):
        ttk.Label(body, text='Validation by observers', style='Title.TLabel').pack(anchor='w')
        card = self._card(body)
        sources = self._line_sources()
        text = ('A recording has no ground truth, so the centre-line velocity is checked against people: blocks '
                'of 3 s are drawn from your centre-line data sets into a reading set, every observer reads them by '
                'hand (blinded: without seeing where a block comes from or what the estimator found), and the '
                'agreement between the estimator and the observers, between observers, and between two sessions '
                'of one observer is computed with Bland-Altman limits of agreement, intraclass correlation and '
                'kappa.')
        ttk.Label(card, text=text, style='Panel.TLabel', wraplength=px(820), justify='left').pack(anchor='w')
        if sources:
            ttk.Label(card, text=f'{len(sources)} centre-line data set{"s" if len(sources) != 1 else ""} '
                                 'available.', style='Muted.Panel.TLabel').pack(anchor='w', pady=(px(10), 0))
            ttk.Button(card, text='New reading set…', style='Accent.TButton', command=self.new_set).pack(
                anchor='w', pady=(px(12), 0))
        else:
            ttk.Label(card, text='There are no centre-line data sets yet. Measure velocity along a centre line on a '
                                 'few capillaries first (Centre line page); a reading set is drawn from those '
                                 'data sets.', style='Warning.Panel.TLabel', wraplength=px(820),
                      justify='left').pack(anchor='w', pady=(px(10), 0))
            ttk.Button(card, text='Go to the Centre line page', command=lambda: self.app.show_page('line')).pack(
                anchor='w', pady=(px(12), 0))

    def _readings_card(self, body, reading_set):
        card = self._card(body, 'Readings')
        readings = reading_set.readings()
        total = len(reading_set.items)
        if not readings:
            ttk.Label(card, text='No one has read this set yet.', style='Muted.Panel.TLabel').pack(anchor='w')
        else:
            table = ttk.Frame(card, style='Panel.TFrame')
            table.pack(fill='x')
            for column, title in enumerate(('Observer', 'Session', 'Read', 'No clear streaks', 'Last saved', '')):
                ttk.Label(table, text=title, style='Faint.Panel.TLabel').grid(row=0, column=column, sticky='w',
                                                                              padx=(0, px(22)), pady=(0, px(4)))
            for row, reading in enumerate(readings, start=1):
                none = sum(1 for item in reading_set.items if reading.outcome(item.id) == validation.NO_STREAKS)
                try:
                    saved = f'{datetime.datetime.fromisoformat(reading.updated):%d %b %Y, %H:%M}'
                except ValueError:
                    saved = reading.updated or '–'
                values = (reading.observer, str(reading.session), f'{reading.read_count} of {total}', str(none), saved)
                for column, value in enumerate(values):
                    style = 'Bold.Panel.TLabel' if column == 0 else 'Panel.TLabel'
                    if column == 2:
                        style = 'Success.Panel.TLabel' if reading.is_complete else 'Warning.Panel.TLabel'
                    ttk.Label(table, text=value, style=style).grid(row=row, column=column, sticky='w',
                                                                  padx=(0, px(22)), pady=px(2))
                text = 'Look through' if reading.is_complete else 'Continue'
                ttk.Button(table, text=text, style='Small.Ghost.TButton',
                           command=partial(self.start_reading, reading.observer, reading.session)).grid(
                    row=row, column=5, sticky='w')
        start = ttk.Button(card, text='Start reading…', style='Accent.TButton', command=self.ask_reading)
        start.pack(anchor='w', pady=(px(12), 0))
        Tooltip(start, 'Read the blocks as an observer: a new observer, a new session, or continue one')

    def _agreement_card(self, body, reading_set):
        card = self._card(body, 'Agreement')
        ttk.Label(card, style='Muted.Panel.TLabel', wraplength=px(900), justify='left', text=(
            'Measures every block again with the current estimator and compares it with every reading, the '
            'observers with each other, and each observer\'s sessions with each other. It shows the estimator\'s '
            'results, so compute it once everyone has finished reading.')).pack(anchor='w')
        actions = ttk.Frame(card, style='Panel.TFrame')
        actions.pack(fill='x', pady=(px(10), 0))
        self.compute_button = ttk.Button(actions, text='Compute agreement', command=self.compute_agreement)
        self.compute_button.pack(side='left')
        files = reading_set.report_files()
        if os.path.exists(files['summary']):
            ttk.Button(actions, text='Show files', style='Ghost.TButton',
                       command=lambda: self.app.open_folder(files['summary'])).pack(side='left', padx=(px(8), 0))
            try:
                when = datetime.datetime.fromtimestamp(os.path.getmtime(files['summary']))
                ttk.Label(actions, text=f'last computed {when:%d %b %Y, %H:%M}', style='Faint.Panel.TLabel').pack(
                    side='left', padx=(px(12), 0))
            except OSError:
                pass
        self._jobs_changed()
        comparisons = validation.load_comparisons(reading_set)
        if comparisons is None:
            return
        if not comparisons:
            ttk.Label(card, text='Nothing to compare yet: no block has been read.', style='Faint.Panel.TLabel').pack(
                anchor='w', pady=(px(10), 0))
            return
        self._comparison_table(card, comparisons)
        cells = ttk.Frame(card, style='Panel.TFrame')
        cells.pack(fill='x', pady=(px(14), 0))
        for column, role in enumerate(('bland_altman', 'scatter')):
            path = files[role]
            if not os.path.exists(path):
                continue
            try:
                photo = ImageTk.PhotoImage(_thumbnail(path, px(THUMB_WIDTH)))
            except OSError:
                continue
            self._photos.append(photo)
            cell = ttk.Frame(cells, style='Panel.TFrame')
            cell.grid(row=0, column=column, sticky='nw', padx=(0, px(16)))
            label = tk.Label(cell, image=photo, bd=0, cursor='hand2', highlightthickness=1,
                             highlightbackground=COLORS['border'])
            label.pack()
            label.bind('<Button-1>', lambda e, p=path, r=role: ImageViewer(
                self, p, title=f'{PLOT_TITLES[r]}  ·  {reading_set.name}', on_open_folder=lambda: self.app.open_folder(p)))
            Tooltip(label, 'Click to enlarge')
            ttk.Label(cell, text=PLOT_TITLES[role], style='Faint.Panel.TLabel').pack(anchor='w', pady=(px(3), 0))

    def _table(self, card, title, headings):
        ttk.Label(card, text=title, style='Bold.Panel.TLabel').pack(anchor='w', pady=(px(16), px(4)))
        table = ttk.Frame(card, style='Panel.TFrame')
        table.pack(fill='x')
        for column, (heading, tip) in enumerate(headings):
            label = ttk.Label(table, text=heading, style='Faint.Panel.TLabel')
            label.grid(row=0, column=column, sticky='w', padx=(0, px(16)), pady=(0, px(2)))
            if tip:
                Tooltip(label, tip, wrap=300)
        return table

    @staticmethod
    def _cell(table, row, column, text, below=None, bold=False):
        cell = ttk.Frame(table, style='Panel.TFrame')
        cell.grid(row=row, column=column, sticky='nw', padx=(0, px(16)), pady=px(3))
        ttk.Label(cell, text=text, style='Bold.Panel.TLabel' if bold else 'Panel.TLabel',
                  wraplength=px(220) if column == 0 else 0, justify='left').pack(anchor='w')
        if below:
            ttk.Label(cell, text=below, style='Faint.Panel.TLabel').pack(anchor='w')

    def _comparison_table(self, card, comparisons):
        velocity = self._table(card, 'Velocity (mm/s; differences are the first minus the second)', (
            ('Comparison', None),
            ('Blocks', 'Blocks with a velocity from both, of the blocks both have judged'),
            ('Bias', 'Mean difference, with its 95% confidence interval below'),
            ('95% limits of agreement', 'Bias ± 1.96 SD of the differences: 95% of the differences lie between them'),
            ('As ratios', 'The limits of agreement on a log scale: how many percent the first lies above or below the '
                          'second, for 95% of blocks'),
            ('ICC (A,1)', 'Intraclass correlation, absolute agreement, single measurement, with its 95% confidence '
                          'interval below'),
            ('Same direction', 'Blocks where both see the flow go the same way along the line')))
        readable = self._table(card, 'Whether a block can be read at all (a velocity resolved, or lines drawn)', (
            ('Comparison', None),
            ('Judged by both', 'Blocks both have judged (an observer may not have finished)'),
            ('Both', 'Both read a velocity'),
            ('Only the first', 'Only the first named read a velocity'),
            ('Only the second', 'Only the second named read a velocity'),
            ('Neither', 'Neither read a velocity'),
            ('Agreement', 'Share of blocks judged the same'),
            ('Kappa', 'Cohen\'s kappa: agreement beyond chance, with its 95% confidence interval below')))
        notes = []
        row = 0
        for comparison in comparisons:
            row += 1
            name = comparison.get('comparison', '')
            pairs, judged = comparison.get('pairs'), comparison.get('judged_by_both')
            blocks = f'{int(pairs)} of {int(judged)}' if _finite(pairs) and _finite(judged) else \
                (str(int(pairs)) if _finite(pairs) else '–')
            self._cell(velocity, row, 0, name, bold=True)
            self._cell(velocity, row, 1, blocks)
            self._cell(velocity, row, 2, _signed(comparison.get('bias')),
                       _between(comparison.get('bias_ci_low'), comparison.get('bias_ci_high')))
            self._cell(velocity, row, 3, _between(comparison.get('loa_low'), comparison.get('loa_high')))
            self._cell(velocity, row, 4, _ratio_limits(comparison.get('ratio_loa_low'),
                                                       comparison.get('ratio_loa_high')))
            self._cell(velocity, row, 5, _with_ci(comparison.get('icc_agreement'), None, None),
                       _between(comparison.get('icc_agreement_ci_low'), comparison.get('icc_agreement_ci_high'), 2)
                       .replace('+', ''))
            self._cell(velocity, row, 6, _percent(comparison.get('same_direction')))
            if _finite(judged):
                self._cell(readable, row, 0, name, bold=True)
                for column, key in enumerate(('judged_by_both', 'readable_both', 'readable_first_only',
                                              'readable_second_only', 'readable_neither'), start=1):
                    value = comparison.get(key)
                    self._cell(readable, row, column, str(int(value)) if _finite(value) else '–')
                self._cell(readable, row, 6, _percent(comparison.get('readable_agreement')))
                self._cell(readable, row, 7, _with_ci(comparison.get('kappa'), None, None),
                           _between(comparison.get('kappa_ci_low'), comparison.get('kappa_ci_high'), 2)
                           .replace('+', ''))
            coefficient = comparison.get('repeatability_coefficient')
            if _finite(coefficient):
                notes.append(f'{name}: repeatability coefficient {coefficient:.4f} mm/s (95% of repeated readings of '
                             'a block differ by less).')
            if _finite(comparison.get('slope_ci_low')) and (comparison['slope_ci_low'] > 0 or
                                                            comparison['slope_ci_high'] < 0):
                notes.append(f'{name}: the difference changes with the velocity (slope {comparison["slope"]:+.2f} '
                             'of the differences on the means); read the limits as ratios.')
        for note in notes:
            ttk.Label(card, text=note, style='Muted.Panel.TLabel', wraplength=px(900), justify='left').pack(
                anchor='w', pady=(px(6), 0))

    def _sources_card(self, body, sources):
        card = self._card(body, 'Blocks drawn from')
        table = ttk.Frame(card, style='Panel.TFrame')
        table.pack(fill='x')
        for column, title in enumerate(('Recording', 'Data set', 'Drawn', 'Of them resolved', 'Blocks measured')):
            ttk.Label(table, text=title, style='Faint.Panel.TLabel').grid(row=0, column=column, sticky='w',
                                                                          padx=(0, px(22)), pady=(0, px(4)))
        for row, source in enumerate(sources, start=1):
            values = (source.get('recording', ''), source.get('dataset', ''), str(source.get('blocks_drawn', '')),
                      str(source.get('resolved_drawn', '')),
                      f'{source.get("blocks_measured", "")} ({source.get("blocks_resolved", "")} resolved)')
            for column, value in enumerate(values):
                ttk.Label(table, text=value, style='Panel.TLabel').grid(row=row, column=column, sticky='w',
                                                                       padx=(0, px(22)), pady=px(1))

    # -------------------------------------------------------------------- actions
    def new_set(self):
        sources = self._line_sources()
        if not sources:
            show_error(self, 'No centre-line data sets', 'A reading set is drawn from centre-line data sets. '
                       'Measure velocity along a centre line on a few capillaries first.')
            return
        options = NewReadingSetDialog(self, sources, self.names).show()
        if options is None:
            return
        name = options['name']
        work = partial(tasks.create_reading_set, folder=self.app.folder, name=name, sources=options['sources'],
                       blocks_per_dataset=options['blocks_per_dataset'], balanced=options['balanced'],
                       seed=options['seed'], mm_per_pixel=self.app.settings.mm_per_pixel)

        def done(created):
            self.app.set_status(f'Reading set "{created}" drawn.')
            self.selected = created
            self.refresh()

        def failed(exc):
            show_error(self, 'The reading set could not be made', str(exc) or type(exc).__name__,
                       'Nothing was written. The details are in capillaroscopy.log.')

        job = self.app.jobs.submit(f'Reading set · {name}', work, lane='analysis', key=('reading set', name),
                                   on_done=done, on_error=failed)
        if job is None:
            self.app.set_status('That reading set is already being drawn.')
        else:
            self.app.set_status(f'Drawing the reading set "{name}"…')

    def ask_reading(self):
        if self.current is None:
            return
        observer = self.app.settings.extra.get('observer', '')
        answer = StartReadingDialog(self, self.current, observer).show()
        if answer is None:
            return
        observer, session = answer
        if self.app.settings.extra.get('observer') != observer:
            self.app.settings.extra['observer'] = observer
            try:
                self.app.settings.save()
            except OSError:
                pass
        self.start_reading(observer, session)

    def start_reading(self, observer, session):
        if self.current is None:
            return
        try:
            reading = self.current.open_reading(observer, session)
            self.current.block(reading.order[0])               # fail here, not in the middle, if blocks are missing
        except (OSError, ValueError, KeyError) as exc:
            show_error(self, 'The reading cannot be opened', str(exc))
            return
        self.reading_mode = True
        self.overview.pack_forget()
        self.reader.pack(fill='both', expand=True)
        self.reader.start(self.current, reading)
        self.app.set_status(f'Reading "{self.current.name}" as {observer}, session {session}.')

    def leave_reading(self):
        self.reading_mode = False
        self.reader.pack_forget()
        self.overview.pack(fill='both', expand=True)
        self.refresh()

    def compute_agreement(self):
        reading_set = self.current
        if reading_set is None:
            return
        name = reading_set.name

        def done(result):
            self._agreement_job = None
            count = len(result['comparisons'])
            self.app.set_status(f'Agreement of "{name}" computed: {count} comparison{"s" if count != 1 else ""}.')
            if self.current is not None and self.current.name == name and not self.reading_mode:
                self._rebuild()

        def failed(exc):
            self._agreement_job = None
            self._jobs_changed()
            show_error(self, 'The agreement could not be computed', str(exc) or type(exc).__name__,
                       'The details are in capillaroscopy.log.')

        self._agreement_job = self.app.jobs.submit(
            f'Agreement · {name}', partial(tasks.agreement_report, folder=self.app.folder, name=name),
            lane='analysis', key=('agreement', name), on_done=done, on_error=failed,
            on_cancel=lambda: setattr(self, '_agreement_job', None))
        self._jobs_changed()

    def _jobs_changed(self):
        button = getattr(self, 'compute_button', None)
        if button is None:
            return
        try:
            running = self._agreement_job is not None and not self._agreement_job.finished
            button.state(['disabled'] if running else ['!disabled'])
            button.configure(text='Computing…' if running else 'Compute agreement')
        except tk.TclError:
            pass                                               # the card was rebuilt
