"""Reading one space-time block after another, blinded: the observer's view on the Validation page.

`BlockCanvas` shows a block as observers see it (`validation.DISPLAY`) and
lets them draw lines along its streaks; `Reader` walks an observer through
the blocks of a reading set in their own order, saving every change to their
reading (`capillary.validation.Reading`).
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

import numpy as np
from PIL import Image, ImageTk

from capillary import validation

from .dialogs import show_error
from .theme import COLORS, FONTS, px
from .widgets import Tooltip

READER_PANEL_WIDTH = 330

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
