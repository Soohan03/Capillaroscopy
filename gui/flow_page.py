"""Flow page: optical-flow magnitude in a region drawn over a vessel.

The flow video (computed from the stabilized video, `Caper.FlowVideo`) holds
the motion between consecutive frames. The user drags a region over a vessel;
the report adds up the flow inside it and divides by the number of vessel
pixels in it, as found by the vessel mask computed with the flow. Showing that
mask here makes the denominator of the report visible.
"""

from __future__ import annotations

import collections
import math
import tkinter as tk
from functools import partial
from tkinter import ttk

import numpy as np
from PIL import Image, ImageDraw, ImageTk

from capillary.flow import crop_box, drag_box_bounds, frame_flow, vessel_mask
from capillary.measure import flow_region_size_bytes
from Utilities import pickle_load

from . import tasks
from .measure_page import INSPECTOR_WIDTH, MeasurePage, stat
from .media import FLOW_ROLLING_FRAMES, flow_to_rgb, tint
from .theme import COLORS, px
from .video_view import Tool
from .widgets import Tooltip, section, separator

MAX_FLOW_BYTES = 2_000_000_000


class RegionTool(Tool):
    """Drag to draw a region; drag inside it to move it, on a corner to resize it."""

    def __init__(self, page):
        self.page = page
        self._mode = None

    def _corner(self, event):
        bounds = self.page.bounds
        if bounds is None:
            return None
        view = self.page.view
        x_left, x_right, y_top, y_bottom = bounds
        corners = {'nw': (x_left, y_top), 'ne': (x_right, y_top), 'sw': (x_left, y_bottom), 'se': (x_right, y_bottom)}
        for name, (x, y) in corners.items():
            cx, cy = view.to_canvas(x, y)
            if abs(cx - event.x) <= px(8) and abs(cy - event.y) <= px(8):
                return name
        return None

    def _inside(self, x, y):
        bounds = self.page.bounds
        return bounds is not None and bounds[0] <= x < bounds[1] and bounds[2] <= y < bounds[3]

    def press(self, x, y, event):
        corner = self._corner(event)
        bounds = self.page.bounds
        if corner is not None:
            x_left, x_right, y_top, y_bottom = bounds
            opposite = {'nw': (x_right, y_bottom), 'ne': (x_left, y_bottom), 'sw': (x_right, y_top),
                        'se': (x_left, y_top)}[corner]
            self._mode = ('draw', opposite)
        elif self._inside(x, y):
            self._mode = ('move', (x, y, bounds))
        else:
            self._mode = ('draw', (x, y))
            self.page.set_region((x, y), (x, y), live=True)

    def drag(self, x, y, event):
        if self._mode is None:
            return
        kind, data = self._mode
        if kind == 'draw':
            self.page.set_region(data, (x, y), live=True)
        else:
            x0, y0, (x_left, x_right, y_top, y_bottom) = data
            dx, dy = int(round(x - x0)), int(round(y - y0))
            height, width = self.page.view.frame_shape()
            dx = max(-x_left, min(dx, width - x_right))
            dy = max(-y_top, min(dy, height - y_bottom))
            self.page.set_region((x_left + dx, y_top + dy), (x_right + dx, y_bottom + dy), live=True)

    def release(self, x, y, event):
        if self._mode is not None:
            self._mode = None
            self.page.region_finished()

    def cursor_at(self, x, y, event):
        corner = self._corner(event)
        if corner is not None:
            return 'sizing'
        return 'fleur' if self._inside(x, y) else 'crosshair'


class FlowPage(MeasurePage):
    key = 'flow'
    title = 'Flow'
    kind = 'flow'
    color = True
    measure_label = 'Measure flow and save'
    min_frames = 1

    def __init__(self, parent, app):
        self.bounds = None
        self.mask = None
        self.show_mask = tk.BooleanVar(value=True)
        self._recent = collections.deque(maxlen=FLOW_ROLLING_FRAMES)
        self._recent_index = None
        self._raw = None
        super().__init__(parent, app)
        self.view.tool = RegionTool(self)
        self.view.pixel_text = self._pixel_text
        self.player.on_skipped = self._remember_frame

    # --------------------------------------------------------------------- sections
    def build_sections(self, body):
        frame = section(body, 'Region', help_text=(
            'Drag on the video to draw the region over a vessel; drag inside it to move it and on a corner '
            'to resize it. Every frame of the range contributes the flow inside the region; the report '
            'divides it by the number of vessel pixels (green) in the region, so the region should '
            'contain the vessel and as little else as possible.'))
        self.region_label = ttk.Label(frame, text='', style='Mono.Panel.TLabel')
        self.vessel_label = ttk.Label(frame, text='', style='Mono.Panel.TLabel')
        self.now_label = ttk.Label(frame, text='', style='Mono.Panel.TLabel')
        for label, value, tip in (
                ('Region', self.region_label, 'Size of the region in video pixels.'),
                ('Vessel pixels', self.vessel_label, 'Pixels of the region inside the vessel mask: the '
                                                     'denominator of the flow report.'),
                ('This frame', self.now_label, 'Flow per vessel pixel in the current frame (all directions), in '
                                               'mm per frame, the report\'s unit. The report smooths these values.')):
            row = ttk.Frame(frame, style='Panel.TFrame')
            row.pack(fill='x', pady=(px(2), px(2)))
            name = ttk.Label(row, text=label, style='Muted.Panel.TLabel')
            name.pack(side='left')
            Tooltip(name, tip)
            value.pack(in_=row, side='right')
            value.lift(row)  # created before the row frame, so raise it above it
        toggles = ttk.Frame(frame, style='Panel.TFrame')
        toggles.pack(fill='x', pady=(px(8), 0))
        mask_toggle = ttk.Checkbutton(toggles, text='Show vessel mask', variable=self.show_mask,
                                      style='Panel.TCheckbutton', command=self._redraw_frame)
        mask_toggle.pack(side='left')
        Tooltip(mask_toggle, 'Tint the pixels the flow computation classified as vessel (V).')
        ttk.Button(toggles, text='Clear region', style='Ghost.TButton', command=self.clear_region).pack(side='right')
        self.region_hint = ttk.Label(frame, text='', style='Faint.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                     justify='left')
        self.region_hint.pack(anchor='w', pady=(px(8), 0))
        separator(body)

        legend = section(body, 'Direction colours', help_text=(
            'Colour shows the direction of motion, brightness its speed. The report splits the flow at '
            'horizontal: "up" is motion towards the top of the image, "down" towards the bottom.'))
        row = ttk.Frame(legend, style='Panel.TFrame')
        row.pack(fill='x')
        self._wheel_image = _direction_wheel(px(64))
        tk.Label(row, image=self._wheel_image, bg=COLORS['panel'], bd=0).pack(side='left')
        ttk.Label(row, text='Arrows point the way the blood moves. Black means no motion; the picture is the '
                            'mean of the last 10 frames, brightened.', style='Muted.Panel.TLabel',
                  wraplength=px(INSPECTOR_WIDTH - 140), justify='left').pack(side='left', padx=(px(12), 0))
        separator(body)

    # ------------------------------------------------------------------------ state
    def video_for(self, recording):
        return recording.flow

    def empty_state(self, recording):
        if recording is not None and recording.flow is None:
            if recording.is_stabilized:
                return ('No optical flow yet', 'Compute it with the button above, or from the recording\'s menu '
                                               'in the list. This takes a few minutes for a typical video.')
            return ('No optical flow yet', 'Optical flow is computed from the stabilized video. '
                                           'Stabilize this recording first.')
        return super().empty_state(recording)

    def update_banner(self):
        recording = self.recording
        if recording is None or recording.has_flow:
            self.banner.hide()
        elif recording.is_stabilized:
            job = self.app.jobs.find(('flow', recording.stem))
            if job is not None:
                self.banner.show('The optical flow of this recording is being computed; it appears here when it is '
                                 'done.', 'info', closable=False)
            else:
                self.banner.show('This recording has no optical flow yet.', 'info',
                                 action=lambda: self.app.compute_flow(recording), action_text='Compute optical flow',
                                 closable=False)
        elif recording.raw:
            self.banner.show('Optical flow is computed from the stabilized video, and this recording is not '
                             'stabilized yet.', 'warning', action=lambda: self.app.stabilize(recording),
                             action_text='Stabilize now', closable=False)

    def video_opened(self):
        self.mask = None
        self._recent.clear()
        self._recent_index = None
        recording = self.recording
        if recording is not None and recording.flow_summary:
            try:
                self.mask = vessel_mask(pickle_load(recording.flow_summary))
            except (OSError, EOFError, ValueError, IndexError) as exc:
                self.mask = None
                self.app.set_status(f'The vessel mask of this flow video could not be read: {exc}')

    def capture_state(self):
        state = super().capture_state()
        state['bounds'] = self.bounds
        return state

    def restore_state(self, state):
        super().restore_state(state)
        self.bounds = (state or {}).get('bounds')
        self._update_region_ui()

    def apply_record(self, record):
        region = record.get('region', {})
        try:
            self.bounds = (int(region['x_left']), int(region['x_right']), int(region['y_top']), int(region['y_bottom']))
        except (KeyError, TypeError, ValueError):
            return False
        frames = record.get('frames', {})
        first, last = frames.get('first'), frames.get('last')
        if first is not None and last is not None and self.player.source is not None:
            last = min(int(last), self.player.frame_count - 1)
            self.range = None if (first, last) == (0, self.player.frame_count - 1) else (int(first), last)
        self.refresh()
        return True

    def refresh(self):
        super().refresh()
        self._update_region_ui()

    # ----------------------------------------------------------------------- frames
    def _remember_frame(self, index, frame):
        if self._recent_index is not None and index == self._recent_index + 1:
            self._recent.append(frame)
        else:
            self._recent.clear()
            self._recent.append(frame)
        self._recent_index = index

    def prepare_frame(self, index, frame):
        if self._recent_index is not None and index == self._recent_index + 1:
            self._recent.append(frame)
        elif index != self._recent_index:
            # jumped: read the frames before this one so the picture is the same however it was reached
            self._recent.clear()
            source = self.player.source
            for previous in range(max(0, index - FLOW_ROLLING_FRAMES + 1), index):
                earlier = source.read(previous)
                if earlier is not None:
                    self._recent.append(earlier)
            self._recent.append(frame)
        self._recent_index = index
        self._raw = frame
        return self._display()

    def _display(self):
        rgb = flow_to_rgb(list(self._recent))
        if self.show_mask.get() and self.mask is not None and self.mask.shape == rgb.shape[:2]:
            rgb = tint(rgb, self.mask)
        return rgb

    def _redraw_frame(self):
        if self._recent:
            self.view.show(self._display())

    def after_frame(self, index):
        self._update_now()

    def _pixel_text(self, frame, x, y):
        text = f'x {x}   y {y}'
        if self._raw is not None:
            hue, _, value = (int(v) for v in self._raw[y, x])
            speed = value / 25.5
            if speed > 0:
                # hue * 2 is the angle from +x with y pointing down: 0 right, 90 down, 180 left, 270 up
                arrow = '→↘↓↙←↖↑↗'[int(round(hue * 2 / 45)) % 8]
                text += f'   ·   {arrow} {speed:.2f} px/frame'
        if self.mask is not None and self.mask[y, x]:
            text += '   ·   vessel'
        return text

    # ----------------------------------------------------------------------- region
    def set_region(self, point1, point2, live=False):
        shape = self.view.frame_shape()
        if shape is None:
            return
        self.bounds = drag_box_bounds((int(point1[0]), int(point1[1])), (int(point2[0]), int(point2[1])), shape)
        self.draw_overlay()
        self._update_region_ui()

    def region_finished(self):
        self._update_region_ui()

    def clear_region(self):
        self.bounds = None
        self.draw_overlay()
        self._update_region_ui()

    def _update_region_ui(self):
        if self.bounds is None:
            self.region_label.configure(text='–')
            self.vessel_label.configure(text='–')
            self.now_label.configure(text='–')
        else:
            x_left, x_right, y_top, y_bottom = self.bounds
            width, height = x_right - x_left, y_bottom - y_top
            self.region_label.configure(text=f'{width} × {height} px  at  ({x_left}, {y_top})')
            if self.mask is not None:
                vessel = int(np.sum(crop_box(self.mask, self.bounds)))
                share = vessel / max(1, width * height)
                self.vessel_label.configure(text=f'{vessel}  ({100 * share:.0f} %)',
                                            style='Mono.Panel.TLabel' if vessel else 'Warning.Panel.TLabel')
            else:
                self.vessel_label.configure(text='no mask')
            self._update_now()
        if self.player.source is None:
            hint = ''
            self.view.set_hint(None)
        elif self.bounds is None:
            hint = 'Drag on the video to draw a region over a vessel.'
            self.view.set_hint('Drag over a vessel to select the region to measure')
        else:
            hint = 'Drag inside the region to move it, on a corner to resize it, or outside to draw a new one.'
            self.view.set_hint(None)
        self.region_hint.configure(text=hint)
        self.update_measure_state()

    def _update_now(self):
        if self.bounds is None or self._raw is None or self.mask is None:
            return
        _, _, both = frame_flow(crop_box(self._raw, self.bounds), crop_box(self.mask, self.bounds),
                                self.app.settings.mm_per_pixel)
        self.now_label.configure(text=f'{both:.5f} mm' if math.isfinite(both) else '–')

    def draw_overlay(self):
        canvas = self.view.canvas
        canvas.delete('overlay')
        if self.bounds is None or self.view.frame_shape() is None:
            return
        x_left, x_right, y_top, y_bottom = self.bounds
        left, top = self.view.to_canvas(x_left, y_top)
        right, bottom = self.view.to_canvas(x_right, y_bottom)
        canvas.create_rectangle(left, top, right, bottom, outline='#000000', width=px(4), tags=('overlay',))
        canvas.create_rectangle(left, top, right, bottom, outline=COLORS['region'], width=px(2), tags=('overlay',))
        handle = px(4)
        for x, y in ((left, top), (right, top), (left, bottom), (right, bottom)):
            canvas.create_rectangle(x - handle, y - handle, x + handle, y + handle, fill='#FFFFFF',
                                    outline='#000000', tags=('overlay',))
        canvas.tag_raise('hint')
        canvas.tag_raise('readout')

    # -------------------------------------------------------------------- measuring
    def measure_blockers(self):
        if self.mask is None:
            return ['The vessel mask of this flow video is missing; compute the optical flow again.']
        if self.bounds is None:
            return ['Draw a region over a vessel on the video.']
        if int(np.sum(crop_box(self.mask, self.bounds))) == 0:
            return ['The region holds no vessel pixels (green); the report would divide by zero.']
        start, end = self.current_range()
        size = flow_region_size_bytes(self.bounds, end - start + 1)
        if size > MAX_FLOW_BYTES:
            return [f'This region over this range needs about {size / 1e9:.1f} GB of memory; '
                    'use a smaller region or a shorter range.']
        if self.recording is not None and self.app.jobs.find(('flow-data', self.recording.stem)) is not None:
            return ['A measurement of this recording is already running.']
        return []

    def submit_measurement(self, name, start, end, done, failed, cancelled):
        recording = self.recording
        work = partial(tasks.measure_flow_dataset, folder=self.app.folder, stem=recording.stem, name=name,
                       flow_path=self.player.source.path, mask=self.mask, bounds=self.bounds, start=start, end=end,
                       mm_per_pixel=self.app.settings.mm_per_pixel)
        return self.app.jobs.submit(f'Flow · {recording.stem} · {name}', work, lane='analysis', on_done=done,
                                    on_error=failed, on_cancel=cancelled, key=('flow-data', recording.stem))

    def describe_result(self, frame, result):
        summary = result['summary']
        both = summary.get('median_both', float('nan'))
        big = ttk.Frame(frame, style='Panel.TFrame')
        big.pack(fill='x', pady=(0, px(6)))
        ttk.Label(big, text=f'{both:.5f}' if math.isfinite(both) else '–', style='Big.Panel.TLabel').pack(side='left')
        ttk.Label(big, text=' mm per frame, median', style='Muted.Panel.TLabel').pack(side='left', anchor='s',
                                                                                     pady=(0, px(4)))
        for key, label in (('median_up', 'Up, median'), ('median_down', 'Down, median')):
            value = summary.get(key, float('nan'))
            stat(frame, label, f'{value:.5f} mm' if math.isfinite(value) else '–')
        stat(frame, 'Frames measured', str(summary.get('frames', 0)))

    def handle_page_key(self, event):
        if event.keysym.lower() == 'v':
            self.show_mask.set(not self.show_mask.get())
            self._redraw_frame()
            return True
        return False


def _direction_wheel(size):
    """A colour wheel showing which hue means which direction (y pointing down, as in the image)."""
    import cv2

    radius = size / 2
    yy, xx = np.mgrid[0:size, 0:size]
    dx, dy = xx - radius + 0.5, yy - radius + 0.5
    angle = (np.degrees(np.arctan2(dy, dx)) % 360) / 2
    distance = np.hypot(dx, dy) / radius
    hsv = np.zeros((size, size, 3), np.uint8)
    hsv[..., 0] = angle.astype(np.uint8)
    hsv[..., 1] = 255
    hsv[..., 2] = np.clip(distance * 255, 0, 255).astype(np.uint8)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    alpha = np.where(distance <= 1.0, 255, 0).astype(np.uint8)
    image = Image.fromarray(np.dstack([rgb, alpha]), 'RGBA')
    draw = ImageDraw.Draw(image)
    centre = size / 2
    for dx_, dy_ in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        end = (centre + dx_ * radius * 0.82, centre + dy_ * radius * 0.82)
        draw.line([(centre, centre), end], fill=(255, 255, 255, 200), width=max(1, size // 40))
    background = Image.new('RGBA', image.size, COLORS['panel'])
    return ImageTk.PhotoImage(Image.alpha_composite(background, image))
