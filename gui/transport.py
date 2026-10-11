"""Playback: the player that paces frames, the timeline and the transport bar.

The old GUI advanced the video from a 1 ms busy loop that also redrew while
paused. Here nothing runs while paused, and playback is scheduled against the
clock, so a video plays at its real frame rate (or the chosen speed).
"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .media import FrameSource, format_time
from .theme import COLORS, FONTS, icon, px, rounded_rect
from .widgets import Tooltip


class Player:
    """Plays a `FrameSource` into ``on_frame(index, frame)``; ``on_state()`` on play/pause changes.

    Faster than real time, frames in between are skipped, not read.
    """

    SPEEDS = (0.25, 0.5, 1.0, 2.0, 4.0)

    def __init__(self, widget, on_frame: Callable, on_state: Optional[Callable] = None):
        self.widget = widget
        self.on_frame = on_frame
        self.on_state = on_state
        self.source: Optional[FrameSource] = None
        self.index = 0
        self.playing = False
        self.speed = 1.0
        self._after = None
        self._due = 0.0

    @property
    def frame_count(self) -> int:
        return self.source.frame_count if self.source else 0

    @property
    def fps(self) -> float:
        return self.source.fps if self.source else 30.0

    @property
    def time_s(self) -> float:
        return self.index / self.fps if self.fps else 0.0

    def open(self, source: Optional[FrameSource]) -> None:
        self.close()
        self.source = source
        self.index = 0
        if source is not None:
            self.show(0)

    def close(self) -> None:
        self.pause()
        if self.source is not None:
            self.source.close()
            self.source = None

    def show(self, index: int) -> bool:
        if self.source is None or self.frame_count == 0:
            return False
        index = max(0, min(int(index), self.frame_count - 1))
        frame = self.source.read(index)
        if frame is None:
            # the file holds fewer frames than its header claims: shorten and show the last good one
            if index == 0:
                return False
            self.source.frame_count = index
            self.pause()
            return self.show(index - 1)
        self.index = index
        self.on_frame(index, frame)
        return True

    def seek(self, index: int) -> None:
        self.show(index)

    def step(self, delta: int) -> None:
        self.pause()
        self.show(self.index + delta)

    def toggle(self) -> None:
        self.pause() if self.playing else self.play()

    def play(self) -> None:
        if self.source is None or self.playing:
            return
        if self.index >= self.frame_count - 1:
            self.show(0)
        self.playing = True
        self._due = time.perf_counter()
        self._after = self.widget.after(1, self._tick)
        if self.on_state:
            self.on_state()

    def pause(self) -> None:
        if self._after is not None:
            self.widget.after_cancel(self._after)
            self._after = None
        if self.playing:
            self.playing = False
            if self.on_state:
                self.on_state()

    def set_speed(self, speed: float) -> None:
        self.speed = speed
        self._due = time.perf_counter()

    def _tick(self) -> None:
        self._after = None
        if not self.playing or self.source is None:
            return
        step = max(1, int(round(self.speed))) if self.speed >= 1 else 1
        interval = (step / (self.fps * self.speed)) if self.fps else 1 / 30
        target = self.index + step
        if target >= self.frame_count:
            self.show(self.frame_count - 1)
            self.pause()
            return
        if not self.show(target):
            self.pause()
            return
        self._due += interval
        now = time.perf_counter()
        if self._due < now - 0.25:  # fell behind (slow disk, busy machine): do not try to catch up
            self._due = now
        self._after = self.widget.after(max(1, int((self._due - now) * 1000)), self._tick)


class Timeline(tk.Canvas):
    """Seek bar with the measurement range, time-point markers, the official occlusion and the playhead."""

    def __init__(self, parent, on_seek: Callable[[int], None], on_marker_menu: Optional[Callable] = None):
        super().__init__(parent, height=px(44), bg=COLORS['panel'], highlightthickness=0, bd=0, cursor='hand2')
        self.on_seek = on_seek
        self.on_marker_menu = on_marker_menu
        self.count = 0
        self.fps = 30.0
        self.position = 0
        self.range = None
        self.markers: list[float] = []
        self.occlusion_s: Optional[float] = None
        self.release_s: Optional[float] = None
        self._hover_x = None
        self._dragging = False
        self.bind('<Configure>', lambda e: self.draw())
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<B1-Motion>', self._drag)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<Motion>', self._hover)
        self.bind('<Leave>', self._leave)
        self.bind('<ButtonPress-3>', self._right)

    # geometry ---------------------------------------------------------------------
    @property
    def _pad(self):
        return px(14)

    def _track_y(self):
        return px(30)

    def x_of(self, index):
        width = self.winfo_width()
        if self.count <= 1:
            return self._pad
        return self._pad + (width - 2 * self._pad) * index / (self.count - 1)

    def index_at(self, x):
        width = self.winfo_width()
        if self.count <= 1:
            return 0
        fraction = (x - self._pad) / max(1, width - 2 * self._pad)
        return int(round(min(max(fraction, 0.0), 1.0) * (self.count - 1)))

    # state --------------------------------------------------------------------------
    def configure_video(self, count, fps):
        self.count, self.fps = count, fps or 30.0
        self.draw()

    def set_position(self, index):
        self.position = index
        self.draw()

    def set_range(self, start_end):
        self.range = start_end
        self.draw()

    def set_markers(self, seconds):
        self.markers = list(seconds)
        self.draw()

    def set_phases(self, occlusion_s: Optional[float], release_s: Optional[float]):
        """The official occlusion and release (seconds), drawn as a bar under the track; None hides it."""
        self.occlusion_s, self.release_s = occlusion_s, release_s
        self.draw()

    def phase_at(self, seconds: float) -> str:
        if self.occlusion_s is None:
            return ''
        if seconds < self.occlusion_s:
            return 'rest'
        if self.release_s is None:
            return 'occlusion or later'
        return 'occlusion' if seconds < self.release_s else 'after release'

    # drawing ------------------------------------------------------------------------
    def draw(self):
        self.delete('all')
        width = self.winfo_width()
        if width < 10:
            return
        y = self._track_y()
        left, right = self._pad, width - self._pad
        thickness = px(6)
        self.create_line(left, y, right, y, fill=COLORS['border'], width=thickness, capstyle='round')
        if self.count <= 0:
            return
        if self.range is not None:
            x0, x1 = self.x_of(self.range[0]), self.x_of(self.range[1])
            rounded_rect(self, x0, y - px(9), max(x1, x0 + 2), y + px(9), px(4), fill=COLORS['accent_soft'],
                         outline='')
            self.create_line(left, y, right, y, fill=COLORS['border'], width=thickness, capstyle='round')
            for x in (x0, x1):
                self.create_line(x, y - px(10), x, y + px(10), fill=COLORS['accent'], width=px(2))
        if self.occlusion_s is not None:
            x0 = self.x_of(self.occlusion_s * self.fps)
            x1 = self.x_of(self.release_s * self.fps) if self.release_s is not None else x0
            self.create_rectangle(x0, y + px(11), max(x1, x0 + px(2)), y + px(14), fill=COLORS['warning'],
                                  outline='')
        x = self.x_of(self.position)
        self.create_line(left, y, x, y, fill=COLORS['accent'], width=thickness, capstyle='round')
        for seconds in self.markers:
            mx = self.x_of(seconds * self.fps)
            self.create_line(mx, px(12), mx, y + px(6), fill=COLORS['marker'], width=px(2))
            self.create_polygon(mx, px(12), mx + px(9), px(15.5), mx, px(19), fill=COLORS['marker'], outline='')
        radius = px(7)
        self.create_oval(x - radius, y - radius, x + radius, y + radius, fill='#FFFFFF', outline=COLORS['accent'],
                         width=px(2))
        if self._hover_x is not None:
            index = self.index_at(self._hover_x)
            phase = self.phase_at(index / self.fps)
            label = f'{format_time(index / self.fps)}  ·  frame {index}' + (f'  ·  {phase}' if phase else '')
            text = self.create_text(0, 0, text=label, font=FONTS['tiny'], fill=COLORS['overlay_text'], anchor='n')
            x0, y0, x1, y1 = self.bbox(text)
            half = (x1 - x0) / 2
            cx = min(max(self._hover_x, left + half), right - half)
            self.coords(text, cx, px(1))
            x0, y0, x1, y1 = self.bbox(text)
            rounded_rect(self, x0 - px(5), y0 - px(1), x1 + px(5), y1 + px(1), px(4), fill=COLORS['overlay_bg'],
                         outline='', tags=('tip',))
            self.tag_raise(text)

    # input --------------------------------------------------------------------------
    def _press(self, event):
        if self.count:
            self._dragging = True
            self.on_seek(self.index_at(event.x))

    def _drag(self, event):
        if self._dragging:
            self._hover_x = event.x
            self.on_seek(self.index_at(event.x))

    def _release(self, _event):
        self._dragging = False

    def _hover(self, event):
        self._hover_x = event.x
        self.draw()

    def _leave(self, _event):
        self._hover_x = None
        self.draw()

    def marker_near(self, x, tolerance=None):
        tolerance = tolerance or px(7)
        best, best_distance = None, tolerance + 1
        for i, seconds in enumerate(self.markers):
            distance = abs(self.x_of(seconds * self.fps) - x)
            if distance <= tolerance and distance < best_distance:
                best, best_distance = i, distance
        return best

    def _right(self, event):
        if self.on_marker_menu is None:
            return
        marker = self.marker_near(event.x)
        if marker is not None:
            self.on_marker_menu(marker, event)


class TransportBar(ttk.Frame):
    """Play/pause and stepping buttons, the time readout, time-point and speed controls."""

    def __init__(self, parent, player: Player, on_mark=None):
        super().__init__(parent, style='Panel.TFrame', padding=(px(6), px(2), px(8), px(6)))
        self.player = player
        for name, tip, command in (
                ('to_start', 'First frame (Home)', lambda: player.seek(0)),
                ('back', 'Back 1 second (Shift + ←)', lambda: player.step(-int(round(player.fps)))),
                ('prev_frame', 'Previous frame (←)', lambda: player.step(-1))):
            self._icon_button(name, tip, command)
        self.play_button = ttk.Button(self, image=icon('play', 18, '#FFFFFF'), style='Accent.TButton',
                                      command=player.toggle, padding=(px(10), px(4)))
        self.play_button.pack(side='left', padx=px(4))
        Tooltip(self.play_button, 'Play / pause (Space)')
        for name, tip, command in (
                ('next_frame', 'Next frame (→)', lambda: player.step(1)),
                ('forward', 'Forward 1 second (Shift + →)', lambda: player.step(int(round(player.fps)))),
                ('to_end', 'Last frame (End)', lambda: player.seek(player.frame_count - 1))):
            self._icon_button(name, tip, command)

        readout = ttk.Frame(self, style='Panel.TFrame')
        readout.pack(side='left', padx=(px(12), 0))
        self.time_label = ttk.Label(readout, text='–', style='Mono.Panel.TLabel')
        self.time_label.pack(anchor='w')
        self.frame_label = ttk.Label(readout, text='', style='MonoSmall.Panel.TLabel')
        self.frame_label.pack(anchor='w')

        self.speed = tk.StringVar(value='1×')
        speed = ttk.Combobox(self, textvariable=self.speed, width=5, state='readonly',
                             values=[f'{s:g}×' for s in Player.SPEEDS])
        speed.pack(side='right')
        speed.bind('<<ComboboxSelected>>', self._speed_changed)
        Tooltip(speed, 'Playback speed')
        if on_mark is not None:
            mark = ttk.Button(self, image=icon('flag', 14, COLORS['marker']), style='Ghost.TButton', command=on_mark)
            mark.pack(side='right', padx=(0, px(10)))
            Tooltip(mark, 'Mark a time point at the current frame (M). Time points are drawn as red lines in '
                          'the velocity report.')

    def _icon_button(self, name, tip, command):
        button = ttk.Button(self, image=icon(name, 14, COLORS['text']), style='Ghost.TButton', command=command)
        button.pack(side='left')
        Tooltip(button, tip)
        return button

    def _speed_changed(self, _event=None):
        try:
            self.player.set_speed(float(self.speed.get().rstrip('×')))
        except ValueError:
            pass

    def update_state(self):
        player = self.player
        self.play_button.configure(image=icon('pause' if player.playing else 'play', 18, '#FFFFFF'))
        if player.source is None:
            self.time_label.configure(text='–')
            self.frame_label.configure(text='')
            return
        total = player.frame_count / player.fps if player.fps else 0
        self.time_label.configure(text=f'{format_time(player.time_s)} / {format_time(total)}')
        self.frame_label.configure(text=f'frame {player.index} of 0–{player.frame_count - 1}')
