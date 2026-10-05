"""The video canvas: fit-to-window display, zoom and pan, overlays and mouse tools.

Overlays (boxes, regions, hints) are canvas items drawn on top of the picture,
not burned into the frame: the measurement reads the file itself, so what is
drawn can never leak into the data. Pages draw their overlay in a view
listener, using `to_canvas` / `to_video` to convert between screen and video
pixel coordinates.
"""

from __future__ import annotations

import math
import sys
import tkinter as tk
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image, ImageTk

from .theme import COLORS, FONTS, icon, px, rounded_rect
from .widgets import register_wheel

if sys.platform == 'darwin':
    RIGHT_BUTTON, MIDDLE_BUTTON = '2', '3'
else:
    RIGHT_BUTTON, MIDDLE_BUTTON = '3', '2'


def fit_scale(canvas_w, canvas_h, video_w, video_h):
    """Scale at which a video_w x video_h frame fits inside the canvas."""
    return min(canvas_w / video_w, canvas_h / video_h)


def view_origin(center, visible, extent):
    """Left (or top) edge, in video pixels, of a view `visible` pixels wide centred on `center`.

    When the whole frame fits, it is centred (the origin goes negative); when
    zoomed in, the view is kept inside the frame.
    """
    if visible >= extent:
        return -(visible - extent) / 2
    return min(max(center - visible / 2, 0.0), extent - visible)


class VideoView(tk.Frame):
    MAX_ZOOM = 32.0

    def __init__(self, parent, empty_title='', empty_text=''):
        super().__init__(parent, bg=COLORS['video_bg'], highlightthickness=0, bd=0)
        self.canvas = tk.Canvas(self, bg=COLORS['video_bg'], highlightthickness=0, bd=0, cursor='crosshair')
        self.canvas.pack(fill='both', expand=True)
        self.frame: Optional[np.ndarray] = None
        self.tool = None
        self.pixel_text: Optional[Callable] = None   # (frame, x, y) -> readout text
        self._photo = None
        self._photo_key = None
        self._image_item = self.canvas.create_image(0, 0, anchor='nw', tags=('image',))
        self._zoom = 1.0
        self._center = None
        self._geometry = None
        self._listeners = []
        self._empty = (empty_title, empty_text)
        self._hint = None
        self._pan = None
        self._pointer = None
        self._tool_active = False

        c = self.canvas
        c.bind('<Configure>', lambda e: self.render())
        c.bind('<ButtonPress-1>', self._press)
        c.bind('<B1-Motion>', self._drag)
        c.bind('<ButtonRelease-1>', self._release)
        c.bind(f'<ButtonPress-{RIGHT_BUTTON}>', self._right)
        c.bind(f'<ButtonPress-{MIDDLE_BUTTON}>', self._pan_start)
        c.bind(f'<B{MIDDLE_BUTTON}-Motion>', self._pan_move)
        c.bind(f'<ButtonRelease-{MIDDLE_BUTTON}>', self._pan_end)
        c.bind('<Motion>', self._motion)
        c.bind('<Leave>', self._leave)
        register_wheel(c, self._wheel)

    # ------------------------------------------------------------------ public API
    def add_view_listener(self, callback):
        """`callback()` after the picture moved or was rescaled: redraw overlays then."""
        self._listeners.append(callback)

    def set_empty_message(self, title, text=''):
        self._empty = (title, text)
        if self.frame is None:
            self.render()

    def show(self, frame: Optional[np.ndarray]):
        """Display `frame` (greyscale or RGB uint8). A new frame size resets the zoom."""
        if frame is not None and (self.frame is None or frame.shape[:2] != self.frame.shape[:2]):
            self._zoom, self._center = 1.0, None
        self.frame = frame
        self.render()

    def clear(self):
        self.show(None)

    @property
    def zoom(self) -> float:
        return self._zoom

    def set_hint(self, text: Optional[str]):
        if text != self._hint:
            self._hint = text
            self._draw_hint()

    def fit(self):
        self._zoom, self._center = 1.0, None
        self.render()
        self._draw_zoom_controls()

    def zoom_by(self, factor, around=None):
        if self.frame is None:
            return
        new_zoom = min(self.MAX_ZOOM, max(1.0, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 1e-9:
            return
        width, height = self._canvas_size()
        cx, cy = around if around is not None else (width / 2, height / 2)
        vx, vy = self.to_video(cx, cy)
        self._zoom = new_zoom
        scale = self.scale
        # keep the video point under the pointer where it is
        self._center = (vx - cx / scale + width / (2 * scale), vy - cy / scale + height / (2 * scale))
        self.render()

    @property
    def scale(self) -> float:
        if self.frame is None:
            return 1.0
        width, height = self._canvas_size()
        return fit_scale(width, height, self.frame.shape[1], self.frame.shape[0]) * self._zoom

    def to_canvas(self, vx, vy):
        scale, left, top = self._view()
        return (vx - left) * scale, (vy - top) * scale

    def to_video(self, cx, cy):
        scale, left, top = self._view()
        return cx / scale + left, cy / scale + top

    def frame_shape(self):
        return None if self.frame is None else self.frame.shape[:2]

    # ------------------------------------------------------------------- rendering
    def _canvas_size(self):
        return max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())

    def _view(self):
        if self.frame is None:
            return 1.0, 0.0, 0.0
        width, height = self._canvas_size()
        frame_h, frame_w = self.frame.shape[:2]
        scale = self.scale
        cx, cy = self._center or (frame_w / 2, frame_h / 2)
        return scale, view_origin(cx, width / scale, frame_w), view_origin(cy, height / scale, frame_h)

    def render(self):
        canvas = self.canvas
        canvas.delete('empty')
        if self.frame is None:
            canvas.itemconfigure(self._image_item, state='hidden')
            width, height = self._canvas_size()
            title, text = self._empty
            if title:
                canvas.create_text(width / 2, height / 2 - px(12), text=title, fill=COLORS['overlay_text'],
                                   font=FONTS['subtitle'], tags=('empty',), width=width - px(40), justify='center')
            if text:
                canvas.create_text(width / 2, height / 2 + px(14), text=text, fill=COLORS['header_muted'],
                                   font=FONTS['base'], tags=('empty',), width=min(width - px(40), px(520)),
                                   justify='center', anchor='n')
            self._geometry = None
            self._notify()
            self._draw_hint()
            self._draw_zoom_controls()
            return

        frame_h, frame_w = self.frame.shape[:2]
        width, height = self._canvas_size()
        scale, left, top = self._view()
        x0, y0 = max(0, int(math.floor(left))), max(0, int(math.floor(top)))
        x1 = min(frame_w, int(math.ceil(left + width / scale)))
        y1 = min(frame_h, int(math.ceil(top + height / scale)))
        if x1 <= x0 or y1 <= y0:
            return
        target = (max(1, int(round((x1 - x0) * scale))), max(1, int(round((y1 - y0) * scale))))
        crop = self.frame[y0:y1, x0:x1]
        if scale >= 3:
            interpolation = cv2.INTER_NEAREST     # show real pixels when zoomed in
        elif scale < 1:
            interpolation = cv2.INTER_AREA
        else:
            interpolation = cv2.INTER_LINEAR
        image = Image.fromarray(np.ascontiguousarray(cv2.resize(crop, target, interpolation=interpolation)))
        key = (target, image.mode)
        if self._photo is not None and self._photo_key == key:
            self._photo.paste(image)
        else:
            self._photo = ImageTk.PhotoImage(image)
            self._photo_key = key
            canvas.itemconfigure(self._image_item, image=self._photo)
        canvas.itemconfigure(self._image_item, state='normal')
        canvas.coords(self._image_item, (x0 - left) * scale, (y0 - top) * scale)
        canvas.tag_lower(self._image_item)

        geometry = (round(scale, 6), round(left, 3), round(top, 3), width, height, frame_w, frame_h)
        if geometry != self._geometry:
            self._geometry = geometry
            self._notify()
            self._draw_hint()
            self._draw_zoom_controls()
        if self._pointer is not None:
            self._draw_readout(*self._pointer)

    def _notify(self):
        for callback in self._listeners:
            callback()

    def _draw_hint(self):
        canvas = self.canvas
        canvas.delete('hint')
        if not self._hint:
            return
        width, _ = self._canvas_size()
        text = canvas.create_text(width / 2, px(22), text=self._hint, fill=COLORS['overlay_text'],
                                  font=FONTS['base'], tags=('hint',), width=min(width - px(60), px(640)),
                                  justify='center', anchor='n')
        x0, y0, x1, y1 = canvas.bbox(text)
        rounded_rect(canvas, x0 - px(14), y0 - px(8), x1 + px(14), y1 + px(8), px(10),
                     fill=COLORS['overlay_bg'], outline='', tags=('hint',))
        canvas.tag_raise(text)

    def _draw_zoom_controls(self):
        canvas = self.canvas
        canvas.delete('zoomui')
        if self.frame is None:
            return
        width, height = self._canvas_size()
        size = px(28)
        label = 'Fit' if self._zoom <= 1.0001 else f'{self._zoom:.1f}×'
        buttons = (('minus', 'zoom_out', lambda: self.zoom_by(1 / 1.25)), (None, 'zoom_label', self.fit),
                   ('plus', 'zoom_in', lambda: self.zoom_by(1.25)), ('fit', 'zoom_fit', self.fit))
        widths = [px(46) if name is None else size for name, _, _ in buttons]
        right, bottom = width - px(12), height - px(10)
        left = right - sum(widths)
        rounded_rect(canvas, left - px(4), bottom - size - px(4), right + px(4), bottom + px(4), px(8),
                     fill=COLORS['overlay_bg'], outline='', tags=('zoomui',))
        x = left
        for (name, tag, command), w in zip(buttons, widths):
            canvas.create_rectangle(x, bottom - size, x + w, bottom, fill=COLORS['overlay_bg'], outline='',
                                    tags=('zoomui', tag))
            if name is None:
                canvas.create_text(x + w / 2, bottom - size / 2, text=label, fill=COLORS['overlay_text'],
                                   font=FONTS['mono_small'], tags=('zoomui', tag))
            else:
                canvas.create_image(x + w / 2, bottom - size / 2, image=icon(name, 12, COLORS['overlay_text']),
                                    tags=('zoomui', tag))
            canvas.tag_bind(tag, '<ButtonRelease-1>', lambda e, c=command: c())
            canvas.tag_bind(tag, '<Enter>', lambda e, t=tag: canvas.itemconfigure(
                canvas.find_withtag(t)[0], fill=COLORS['header_active']))
            canvas.tag_bind(tag, '<Leave>', lambda e, t=tag: canvas.itemconfigure(
                canvas.find_withtag(t)[0], fill=COLORS['overlay_bg']))
            x += w

    def _over_controls(self):
        current = self.canvas.find_withtag('current')
        return bool(current) and 'zoomui' in self.canvas.gettags(current[0])

    def _draw_readout(self, cx, cy):
        canvas = self.canvas
        canvas.delete('readout')
        if self.frame is None:
            return
        vx, vy = self.to_video(cx, cy)
        frame_h, frame_w = self.frame.shape[:2]
        if not (0 <= vx < frame_w and 0 <= vy < frame_h):
            return
        x, y = int(vx), int(vy)
        text = self.pixel_text(self.frame, x, y) if self.pixel_text else f'x {x}   y {y}'
        _, height = self._canvas_size()
        item = canvas.create_text(px(14), height - px(12), text=text, anchor='sw', fill=COLORS['overlay_text'],
                                  font=FONTS['mono_small'], tags=('readout',))
        x0, y0, x1, y1 = canvas.bbox(item)
        rounded_rect(canvas, x0 - px(7), y0 - px(4), x1 + px(7), y1 + px(4), px(6), fill=COLORS['overlay_bg'],
                     outline='', tags=('readout',))
        canvas.tag_raise(item)

    # ------------------------------------------------------------------------ input
    def _event_video_xy(self, event):
        return self.to_video(event.x, event.y)

    def _press(self, event):
        self.canvas.focus_set()
        self._tool_active = not self._over_controls()
        if self._tool_active and self.frame is not None and self.tool is not None:
            self.tool.press(*self._event_video_xy(event), event)

    def _drag(self, event):
        if self._tool_active and self.frame is not None and self.tool is not None:
            self.tool.drag(*self._event_video_xy(event), event)
        self._pointer = (event.x, event.y)
        self._draw_readout(event.x, event.y)

    def _release(self, event):
        if self._tool_active and self.frame is not None and self.tool is not None:
            self.tool.release(*self._event_video_xy(event), event)
        self._tool_active = False

    def _right(self, event):
        self.canvas.focus_set()
        if self.frame is not None and self.tool is not None:
            self.tool.right_click(*self._event_video_xy(event), event)

    def _motion(self, event):
        self._pointer = (event.x, event.y)
        if self._over_controls():
            self.canvas.configure(cursor='hand2')
        elif self.frame is not None and self.tool is not None:
            cursor = self.tool.cursor_at(*self._event_video_xy(event), event)
            if cursor and self.canvas.cget('cursor') != cursor:
                self.canvas.configure(cursor=cursor)
        self._draw_readout(event.x, event.y)

    def _leave(self, _event):
        self._pointer = None
        self.canvas.delete('readout')

    def _wheel(self, steps, event):
        if self.frame is None:
            return
        x = event.x_root - self.canvas.winfo_rootx()
        y = event.y_root - self.canvas.winfo_rooty()
        self.zoom_by(1.25 ** steps, around=(x, y))

    def _pan_start(self, event):
        if self.frame is None or self._zoom <= 1.0:
            return
        self._pan = (event.x, event.y, self._center or (self.frame.shape[1] / 2, self.frame.shape[0] / 2))
        self.canvas.configure(cursor='fleur')

    def _pan_move(self, event):
        if self._pan is None:
            return
        x, y, (cx, cy) = self._pan
        scale = self.scale
        width, height = self._canvas_size()
        frame_h, frame_w = self.frame.shape[:2]
        cx, cy = cx - (event.x - x) / scale, cy - (event.y - y) / scale
        half_w, half_h = width / (2 * scale), height / (2 * scale)
        self._center = (min(max(cx, half_w), frame_w - half_w), min(max(cy, half_h), frame_h - half_h))
        self.render()

    def _pan_end(self, _event):
        self._pan = None
        self.canvas.configure(cursor='crosshair')


class Tool:
    """Mouse behaviour on a `VideoView`; coordinates are video pixels (floats)."""

    def press(self, x, y, event):
        pass

    def drag(self, x, y, event):
        pass

    def release(self, x, y, event):
        pass

    def right_click(self, x, y, event):
        pass

    def cursor_at(self, x, y, event):
        return 'crosshair'
