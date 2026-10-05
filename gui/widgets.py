"""Small reusable widgets: scrolling panel, tooltips, banners, charts, sections."""

from __future__ import annotations

import math
import sys
import tkinter as tk
from tkinter import ttk

import numpy as np

from .theme import COLORS, FONTS, icon, px, rounded_rect

# ------------------------------------------------------------------ mouse wheel routing

_WHEEL_TARGETS = {}


def register_wheel(widget, handler) -> None:
    """Send mouse-wheel events over `widget` (or its children) to ``handler(steps, event)``.

    One global binding finds the registered widget under the pointer, so wheel
    events go to whatever the mouse is over, on X11 (buttons 4/5) and on
    Windows/macOS (<MouseWheel>) alike.
    """
    _WHEEL_TARGETS[str(widget)] = handler
    widget.bind('<Destroy>', lambda e, name=str(widget): _WHEEL_TARGETS.pop(name, None)
                if str(e.widget) == name else None, add='+')


def install_wheel_router(root) -> None:
    def route(event):
        if event.num == 4:
            steps = 1
        elif event.num == 5:
            steps = -1
        else:
            delta = event.delta if sys.platform == 'darwin' else event.delta / 120
            steps = 1 if delta > 0 else -1 if delta < 0 else 0
        if not steps:
            return None
        widget = root.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            handler = _WHEEL_TARGETS.get(str(widget))
            if handler is not None:
                handler(steps, event)
                return 'break'
            widget = widget.master
        return None

    for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
        root.bind_all(sequence, route, add='+')


# ---------------------------------------------------------------------- scroll frame

class ScrollFrame(ttk.Frame):
    """A vertically scrolling area; put children into `.body`."""

    def __init__(self, parent, background=None, padding=0):
        super().__init__(parent, style='Panel.TFrame')
        background = background or COLORS['panel']
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview,
                                       style='Slim.Vertical.TScrollbar')
        self.body = ttk.Frame(self.canvas, style='Panel.TFrame', padding=padding)
        self._window = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.body.bind('<Configure>', self._update_region)
        self.canvas.bind('<Configure>', self._fit_width)
        register_wheel(self.canvas, self._wheel)
        register_wheel(self.body, self._wheel)

    def _fit_width(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)
        self._update_region()

    def _update_region(self, _event=None):
        self.canvas.configure(scrollregion=(0, 0, self.body.winfo_reqwidth(), self.body.winfo_reqheight()))

    def _on_scroll(self, first, last):
        self.scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.scrollbar.grid_remove()
        else:
            self.scrollbar.grid()

    def _wheel(self, steps, _event):
        first, last = self.canvas.yview()
        if first > 0.0 or last < 1.0:
            self.canvas.yview_scroll(-3 * steps, 'units')

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)


# ---------------------------------------------------------------------------- tooltip

class Tooltip:
    """Hover text for any widget. `text` may be a function, evaluated on show."""

    def __init__(self, widget, text, delay_ms=500, wrap=320):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.wrap = wrap
        self._after = None
        self._tip = None
        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')

    def _schedule(self, _event=None):
        self._cancel()
        self._after = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._after is not None:
            self.widget.after_cancel(self._after)
            self._after = None

    def _show(self):
        self._after = None
        text = self.text() if callable(self.text) else self.text
        if not text or not self.widget.winfo_viewable():
            return
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        try:
            self._tip.wm_attributes('-type', 'tooltip')
        except tk.TclError:
            pass
        label = tk.Label(self._tip, text=text, justify='left', wraplength=px(self.wrap), bg=COLORS['overlay_bg'],
                         fg=COLORS['overlay_text'], font=FONTS['small'], padx=px(8), pady=px(5))
        label.pack()
        self._tip.update_idletasks()
        x = self.widget.winfo_rootx() + px(4)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + px(6)
        screen_w = self.widget.winfo_screenwidth()
        x = min(x, screen_w - self._tip.winfo_reqwidth() - px(8))
        self._tip.wm_geometry(f'+{x}+{y}')

    def _hide(self, _event=None):
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


# ----------------------------------------------------------------------------- banner

class Banner(tk.Frame):
    """A coloured message strip with an optional action button; hidden until `show`."""

    KINDS = {'info': ('accent_soft', 'accent', 'info'), 'warning': ('warning_soft', 'warning', 'warning'),
             'error': ('danger_soft', 'danger', 'warning'), 'success': ('success_soft', 'success', 'ok')}

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'])
        self._icon = tk.Label(self, bd=0)
        self._icon.pack(side='left', padx=(px(10), px(6)), pady=px(8))
        self._text = tk.Label(self, justify='left', anchor='w', font=FONTS['base'], bd=0)
        self._text.pack(side='left', fill='x', expand=True, pady=px(8))
        self._button = ttk.Button(self, style='TButton')
        self._close = ttk.Button(self, image=icon('close', 10, COLORS['muted']), style='Ghost.TButton',
                                 command=self.hide)
        self._visible = False
        self._manager = None

    def show(self, text, kind='info', action=None, action_text='', closable=True):
        background, foreground, icon_name = self.KINDS[kind]
        background, foreground = COLORS[background], COLORS[foreground]
        self.configure(bg=background, highlightbackground=background)
        self._icon.configure(image=icon(icon_name, 16, foreground), bg=background)
        self._text.configure(text=text, bg=background, fg=COLORS['text'])
        self._button.pack_forget()
        self._close.pack_forget()
        if closable:
            self._close.pack(side='right', padx=(0, px(6)))
        if action is not None:
            self._button.configure(text=action_text, command=action)
            self._button.pack(side='right', padx=px(6))
        self._text.bind('<Configure>', lambda e: self._text.configure(wraplength=max(100, e.width - 4)))
        if self._manager is not None:
            self._manager()
        self._visible = True

    def hide(self):
        if self._visible:
            self.grid_remove()
            self._visible = False

    def place_with(self, manager):
        """`manager()` puts the banner on screen (e.g. ``lambda: banner.grid()``)."""
        self._manager = manager


# ---------------------------------------------------------------------------- sections

def section(parent, title, *, help_text=None, padding=(px(16), px(14), px(16), px(14))):
    """A titled block of an inspector panel; returns the frame to fill."""
    outer = ttk.Frame(parent, style='Panel.TFrame', padding=padding)
    outer.pack(fill='x')
    header = ttk.Frame(outer, style='Panel.TFrame')
    header.pack(fill='x', pady=(0, px(8)))
    ttk.Label(header, text=title.upper(), style='Section.Panel.TLabel').pack(side='left')
    if help_text:
        hint = ttk.Label(header, image=icon('info', 12, COLORS['faint']), style='Panel.TLabel', cursor='question_arrow')
        hint.pack(side='left', padx=(px(6), 0))
        Tooltip(hint, help_text, delay_ms=150, wrap=340)
    body = ttk.Frame(outer, style='Panel.TFrame')
    body.pack(fill='x')
    outer.header = header
    return body


def separator(parent):
    ttk.Separator(parent, orient='horizontal').pack(fill='x')


def color_swatch(parent, color, size=12, background=None):
    canvas = tk.Canvas(parent, width=px(size), height=px(size), highlightthickness=0, bd=0,
                       bg=background or COLORS['panel'])
    rounded_rect(canvas, 1, 1, px(size) - 1, px(size) - 1, px(3), fill=color, outline='')
    return canvas


# ------------------------------------------------------------------------------ charts

class LineChart(tk.Canvas):
    """A compact line chart on a canvas.

    `set_data` takes series of ``(x, y, colour)``. With ``normalize`` each
    series is scaled to its own range (to compare shapes, as for the two box
    signals); otherwise all share a y axis and its range is labelled.
    """

    def __init__(self, parent, height=110, normalize=False, zero_line=False, unit='', background=None):
        background = background or COLORS['panel']
        super().__init__(parent, height=px(height), bg=background, highlightthickness=0, bd=0)
        self.normalize = normalize
        self.zero_line = zero_line
        self.unit = unit
        self._series = []
        self._vlines = []
        self._message = 'No data'
        self._x_range = None
        self.bind('<Configure>', lambda e: self._draw())

    def set_message(self, message):
        self._series = []
        self._message = message
        self._draw()

    def set_data(self, series, vlines=(), x_range=None):
        self._series = [(np.asarray(x, dtype=float), np.asarray(y, dtype=float), color) for x, y, color in series]
        self._vlines = list(vlines)
        self._x_range = x_range
        self._message = None
        self._draw()

    def _draw(self):
        self.delete('all')
        width, height = self.winfo_width(), self.winfo_height()
        if width < 20 or height < 20:
            return
        self.create_rectangle(0, 0, width - 1, height - 1, outline=COLORS['border'], fill=COLORS['panel_alt'])
        if self._message or not self._series:
            self.create_text(width / 2, height / 2, text=self._message or 'No data', fill=COLORS['faint'],
                             font=FONTS['small'], width=width - px(20), justify='center')
            return
        left = px(8) if self.normalize else px(44)
        right, top, bottom = width - px(8), px(10), height - px(10)
        xs = np.concatenate([x[np.isfinite(y)] for x, y, _ in self._series if np.isfinite(y).any()] or [np.array([0.0, 1.0])])
        x0, x1 = self._x_range or (float(np.nanmin(xs)), float(np.nanmax(xs)))
        if x1 <= x0:
            x1 = x0 + 1

        def sx(x):
            return left + (x - x0) / (x1 - x0) * (right - left)

        if not self.normalize:
            ys = np.concatenate([y[np.isfinite(y)] for _, y, _ in self._series] or [np.array([0.0])])
            ys = ys if ys.size else np.array([0.0])
            y0, y1 = float(np.min(ys)), float(np.max(ys))
            if self.zero_line:
                y0, y1 = min(y0, 0.0), max(y1, 0.0)
            if y1 - y0 < 1e-12:
                y0, y1 = y0 - 1, y1 + 1
            # leave a margin only on the sides where there is data (not below a zero baseline)
            pad = (y1 - y0) * 0.08
            if not (self.zero_line and y0 == 0):
                y0 -= pad
            if not (self.zero_line and y1 == 0):
                y1 += pad
            for value, anchor_y in ((y1, top), (y0, bottom)):
                self.create_text(left - px(6), anchor_y, text=_short(value), anchor='e', fill=COLORS['faint'],
                                 font=FONTS['tiny'])
            if self.unit:
                self.create_text(left - px(6), (top + bottom) / 2, text=self.unit, anchor='e', fill=COLORS['faint'],
                                 font=FONTS['tiny'])
            if self.zero_line and y0 < 0 < y1:
                zero = bottom - (0 - y0) / (y1 - y0) * (bottom - top)
                self.create_line(left, zero, right, zero, fill=COLORS['border_strong'], dash=(3, 3))

        for x_value, color in self._vlines:
            if x0 <= x_value <= x1:
                self.create_line(sx(x_value), top - px(4), sx(x_value), bottom + px(4), fill=color, width=1)

        for x, y, color in self._series:
            finite = np.isfinite(y)
            if not finite.any():
                continue
            if self.normalize:
                low, high = np.percentile(y[finite], 2), np.percentile(y[finite], 98)
                if high - low < 1e-9:
                    low, high = low - 1, high + 1
            else:
                low, high = y0, y1
            # break the line at gaps (NaN) so missing data is not bridged
            start = None
            for i in range(len(y) + 1):
                if i < len(y) and finite[i]:
                    if start is None:
                        start = i
                    continue
                if start is not None:
                    segment = range(start, i)
                    points = []
                    for j in segment:
                        value = min(max(y[j], low), high)
                        points += [sx(x[j]), bottom - (value - low) / (high - low) * (bottom - top)]
                    if len(points) >= 4:
                        self.create_line(*points, fill=color, width=px(1.6) or 1)
                    elif len(points) == 2:
                        self.create_oval(points[0] - 1, points[1] - 1, points[0] + 1, points[1] + 1, fill=color,
                                         outline=color)
                    start = None


def _short(value):
    if not math.isfinite(value):
        return ''
    magnitude = abs(value)
    if magnitude < 1e-12:
        return '0'
    if magnitude >= 100:
        return f'{value:.0f}'
    if magnitude >= 10:
        return f'{value:.1f}'
    if magnitude >= 1:
        return f'{value:.2f}'
    return f'{value:.2g}'


# ------------------------------------------------------------------------------- rows

class InfoRow(ttk.Frame):
    """``label ........ value`` on one line, the value updatable via `set`."""

    def __init__(self, parent, label, value='–', value_style='Mono.Panel.TLabel', tooltip=None):
        super().__init__(parent, style='Panel.TFrame')
        self.label = ttk.Label(self, text=label, style='Muted.Panel.TLabel')
        self.label.pack(side='left')
        self.value = ttk.Label(self, text=value, style=value_style, anchor='e', justify='right')
        self.value.pack(side='right')
        if tooltip:
            Tooltip(self.label, tooltip, wrap=320)

    def set(self, text, style=None):
        self.value.configure(text=text)
        if style:
            self.value.configure(style=style)
