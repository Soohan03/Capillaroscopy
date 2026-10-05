"""Capture page: camera preview and recording into RecordedVideos/."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

from capillary import datasets

from .camera import RECORDING_FPS, Camera, recorded_signal
from .dialogs import confirm, show_error
from .measure_page import INSPECTOR_WIDTH
from .media import format_time
from .tasks import new_recording_path, recording_name
from .theme import COLORS, FONTS, icon, px
from .video_view import VideoView
from .widgets import ScrollFrame, Tooltip, section, separator


class CapturePage(ttk.Frame):
    key = 'capture'
    title = 'Capture'
    uses_library = False

    def __init__(self, parent, app):
        super().__init__(parent, style='TFrame')
        self.app = app
        self.camera = Camera()
        self._poll_after = None
        self._shown_frame = -1
        self._shown_status = None
        self._ticks = 0
        self.marks: list[float] = []
        self._recording_stem = None
        self._last_saved = None
        self._build()

    # ------------------------------------------------------------------------ layout
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        center = ttk.Frame(self, style='TFrame', padding=(px(14), px(12), px(12), px(12)))
        center.grid(row=0, column=0, sticky='nsew')
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)
        self.view = VideoView(center, 'Starting the camera…')
        self.view.grid(row=0, column=0, sticky='nsew')
        self.view.pixel_text = lambda frame, x, y: f'x {x}   y {y}'

        tk.Frame(self, bg=COLORS['border'], width=1).grid(row=0, column=1, sticky='ns')
        inspector = ScrollFrame(self)
        inspector.canvas.configure(width=px(INSPECTOR_WIDTH))
        inspector.grid(row=0, column=2, sticky='ns')
        body = inspector.body

        camera = section(body, 'Camera', help_text=(
            'The microscope camera, by device number (usually 0). Recordings are written at 30 frames per '
            'second; if the camera delivers a different rate, playback speed and every velocity measured '
            'from the recording would be off by the same factor.'))
        row = ttk.Frame(camera, style='Panel.TFrame')
        row.pack(fill='x')
        ttk.Label(row, text='Device', style='Muted.Panel.TLabel').pack(side='left')
        self.device = tk.StringVar(value='0')
        ttk.Spinbox(row, from_=0, to=9, width=4, textvariable=self.device, state='readonly',
                    command=self.reconnect).pack(side='left', padx=(px(8), 0))
        ttk.Button(row, text='Reconnect', style='Ghost.TButton', command=self.reconnect).pack(side='right')
        status = ttk.Frame(camera, style='Panel.TFrame')
        status.pack(fill='x', pady=(px(10), 0))
        self.status_dot = tk.Canvas(status, width=px(10), height=px(10), bg=COLORS['panel'], highlightthickness=0)
        self.status_dot.pack(side='left', padx=(0, px(8)))
        self.status_label = ttk.Label(status, text='', style='Panel.TLabel')
        self.status_label.pack(side='left')
        self.camera_detail = ttk.Label(camera, text='', style='Muted.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                       justify='left')
        self.camera_detail.pack(anchor='w', pady=(px(4), 0))
        self.fps_warning = ttk.Label(camera, text='', style='Warning.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                     justify='left')
        self.fps_warning.pack(anchor='w')

        ttk.Label(camera, text='Preview', style='Muted.Panel.TLabel').pack(anchor='w', pady=(px(12), px(4)))
        self.preview_mode = tk.StringVar(value='color')
        modes = ttk.Frame(camera, style='Panel.TFrame')
        modes.pack(fill='x')
        for value, text, tip in (('color', 'Colour', 'The camera image as it is.'),
                                 ('signal', 'Recorded signal', 'What is written to the file: a green-weighted '
                                                               'greyscale image in which capillaries contrast best.')):
            button = ttk.Radiobutton(modes, text=text, value=value, variable=self.preview_mode, style='Seg.Toolbutton')
            button.pack(side='left', fill='x', expand=True)
            Tooltip(button, tip)
        separator(body)

        record = section(body, 'Recording')
        ttk.Label(record, text='Name', style='Muted.Panel.TLabel').pack(anchor='w', pady=(0, px(3)))
        self.prefix = tk.StringVar()
        prefix_entry = ttk.Entry(record, textvariable=self.prefix)
        prefix_entry.pack(fill='x')
        Tooltip(prefix_entry, 'Participant and condition, e.g. FP03_Wföre. The date and time are added, as in the '
                              'existing recordings.')
        self.file_preview = ttk.Label(record, text='', style='Faint.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                      justify='left')
        self.file_preview.pack(anchor='w', pady=(px(3), 0))
        self.prefix.trace_add('write', lambda *_: self._update_file_preview())

        self.record_button = ttk.Button(record, text='Start recording', image=icon('record', 14, '#FFFFFF'),
                                        compound='left', style='Record.TButton', command=self.toggle_recording,
                                        padding=(px(12), px(9)))
        self.record_button.pack(fill='x', pady=(px(14), 0))
        self.running_frame = ttk.Frame(record, style='Panel.TFrame')     # shown while recording
        self.timer = tk.Label(self.running_frame, text='', font=FONTS['mono_big'], bg=COLORS['panel'],
                              fg=COLORS['record'], bd=0)
        self.timer.pack(anchor='w', pady=(px(10), 0))
        self.record_detail = ttk.Label(self.running_frame, text='', style='Muted.Panel.TLabel',
                                       wraplength=px(INSPECTOR_WIDTH - 40), justify='left')
        self.record_detail.pack(anchor='w')

        marks = ttk.Frame(record, style='Panel.TFrame')
        marks.pack(fill='x', pady=(px(12), 0))
        self._marks_row = marks
        ttk.Label(marks, text='Time points', style='Muted.Panel.TLabel').pack(side='left')
        self.mark_button = ttk.Button(marks, text='Mark now', image=icon('flag', 12, COLORS['marker']),
                                      compound='left', style='Ghost.TButton', command=self.mark)
        self.mark_button.pack(side='right')
        Tooltip(self.mark_button, 'Mark an event during the recording (M), e.g. when a cuff is released. The time '
                                  'point is saved with the recording and drawn in its velocity reports.')
        self.marks_label = ttk.Label(record, text='', style='Mono.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                     justify='left')
        self.marks_label.pack(anchor='w')
        separator(body)

        self.saved_frame = ttk.Frame(body, style='Panel.TFrame')
        saved = section(self.saved_frame, 'Last recording')
        self.saved_label = ttk.Label(saved, text='', style='Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                     justify='left')
        self.saved_label.pack(anchor='w')
        actions = ttk.Frame(saved, style='Panel.TFrame')
        actions.pack(fill='x', pady=(px(10), 0))
        ttk.Button(actions, text='Stabilize', command=self._stabilize_last).pack(side='left')
        ttk.Button(actions, text='Show in list', style='Ghost.TButton', command=self._show_last).pack(
            side='left', padx=(px(8), 0))
        self._update_file_preview()
        self._update_recording_ui()

    # --------------------------------------------------------------------- lifecycle
    def show_recording(self, recording):
        pass

    def on_show(self):
        self.reconnect()

    def on_hide(self):
        if self._poll_after is not None:
            self.after_cancel(self._poll_after)
            self._poll_after = None
        self._finish_recording(self.camera.close())
        self.view.clear()

    def can_leave(self) -> bool:
        if self.camera.recording is None:
            return True
        return confirm(self, 'Stop the recording?', 'A recording is running. Leaving this page stops it; the '
                       'video recorded so far is kept.', ok='Stop and leave', danger=True)

    def shutdown(self):
        self._finish_recording(self.camera.close())

    def reconnect(self):
        if self.camera.recording is not None:
            return
        self.camera.open(int(self.device.get() or 0))
        self._shown_frame = -1
        self._shown_status = None
        self.view.clear()
        self.view.set_empty_message('Starting the camera…')
        if self._poll_after is None:
            self._poll_after = self.after(30, self._poll)

    # ------------------------------------------------------------------------- polling
    def _poll(self):
        self._poll_after = self.after(30, self._poll)
        camera = self.camera
        frame, number = camera.latest()
        if frame is not None and number != self._shown_frame:
            self._shown_frame = number
            if self.preview_mode.get() == 'signal':
                frame = recorded_signal(frame)
            self.view.show(frame)
        self._ticks += 1
        if self._ticks % 5 == 0:
            self._update_status()
            self._update_recording_ui()

    def _update_status(self):
        camera = self.camera
        colors = {'live': COLORS['success'], 'opening': COLORS['warning'], 'unavailable': COLORS['danger'],
                  'lost': COLORS['danger'], 'closed': COLORS['faint']}
        texts = {'live': 'Connected', 'opening': 'Connecting…', 'unavailable': 'No camera found',
                 'lost': 'Camera lost', 'closed': 'Off'}
        self.status_dot.delete('all')
        self.status_dot.create_oval(1, 1, px(9), px(9), fill=colors.get(camera.status, COLORS['faint']), outline='')
        self.status_label.configure(text=texts.get(camera.status, camera.status))
        if camera.status == 'live' and camera.size:
            measured = f'{camera.measured_fps:.1f}' if camera.measured_fps else '…'
            self.camera_detail.configure(text=f'{camera.size[0]}×{camera.size[1]} pixels  ·  {measured} frames per '
                                              f'second measured')
            if camera.measured_fps and abs(camera.measured_fps - RECORDING_FPS) > 0.05 * RECORDING_FPS \
                    and camera.frame_number > 60:
                self.fps_warning.configure(text=f'The camera delivers about {camera.measured_fps:.1f} frames per '
                                                f'second, but recordings are stamped {RECORDING_FPS:g}: they would '
                                                f'play {RECORDING_FPS / camera.measured_fps:.2f}× too fast.')
            else:
                self.fps_warning.configure(text='')
        elif camera.status in ('unavailable', 'lost'):
            self.camera_detail.configure(text=f'Device {camera.index} could not be opened. Check the cable and that '
                                              'no other program uses the camera, then reconnect. (Under WSL, '
                                              'USB cameras need to be attached to Linux first.)')
            if self._shown_status != camera.status:
                self.view.set_empty_message('No camera', 'The camera could not be opened. Choose another device or '
                                                         'reconnect.')
            self.fps_warning.configure(text='')
        else:
            self.camera_detail.configure(text='')
        self._shown_status = camera.status

    # ------------------------------------------------------------------------ recording
    def _update_file_preview(self):
        name = recording_name(self.prefix.get().strip(), time_text='hh-mm-ss')
        self.file_preview.configure(text=f'Saved as RecordedVideos/{name}.avi, with the time the recording starts.')

    def toggle_recording(self):
        if self.camera.recording is not None:
            self._finish_recording(self.camera.stop_recording())
            return
        if self.camera.status != 'live':
            show_error(self, 'No camera', 'Connect a camera before recording.')
            return
        path = new_recording_path(self.app.folder, self.prefix.get())
        try:
            self.camera.start_recording(path)
        except (OSError, RuntimeError) as exc:
            show_error(self, 'Recording could not start', str(exc))
            return
        self.marks = []
        self._recording_stem = os.path.splitext(os.path.basename(path))[0]
        self.app.set_status(f'Recording to {os.path.basename(path)}')
        self._update_recording_ui()

    def _finish_recording(self, recorder):
        if recorder is None:
            return
        stem = os.path.splitext(os.path.basename(recorder.path))[0]
        self._last_saved = (stem, recorder.path, recorder.frames, recorder.seconds)
        self.app.set_status(f'Saved {os.path.basename(recorder.path)} ({recorder.frames} frames, '
                            f'{recorder.seconds:.1f} s).')
        self._recording_stem = None
        self.app.refresh_library()
        self._update_recording_ui()

    def mark(self):
        recorder = self.camera.recording
        if recorder is None:
            self.app.set_status('Time points can be marked while recording. In a recorded video, mark them on '
                                'the Analyze page.')
            return
        self.marks.append(round(recorder.seconds, 3))
        path = datasets.time_points_file(self.app.folder.statistics, self._recording_stem)
        try:
            datasets.save_time_points(path, self.marks)
        except OSError as exc:
            show_error(self, 'Time point not saved', str(exc))
        self._update_recording_ui()

    def _update_recording_ui(self):
        recorder = self.camera.recording
        if recorder is not None:
            self.record_button.configure(text='Stop recording', image=icon('stop', 13, '#FFFFFF'))
            self.timer.configure(text=f'● REC  {format_time(recorder.seconds, precise=False)}')
            self.record_detail.configure(text=f'{recorder.frames} frames  ·  {os.path.basename(recorder.path)}')
            self.mark_button.state(['!disabled'])
            if not self.running_frame.winfo_manager():
                self.running_frame.pack(fill='x', before=self._marks_row)
        else:
            self.record_button.configure(text='Start recording', image=icon('record', 14, '#FFFFFF'))
            self.mark_button.state(['disabled'])
            self.running_frame.pack_forget()
        self.record_button.state(['!disabled'] if self.camera.status == 'live' or recorder else ['disabled'])
        self.marks_label.configure(text='  '.join(format_time(m, precise=False) for m in self.marks) or '')
        if self._last_saved is not None:
            stem, path, frames, seconds = self._last_saved
            self.saved_label.configure(text=f'{os.path.basename(path)}\n{frames} frames, {seconds:.1f} s. '
                                            'Stabilize it before measuring.')
            self.saved_frame.pack(fill='x')
        else:
            self.saved_frame.pack_forget()

    def _stabilize_last(self):
        if self._last_saved is None:
            return
        recording = self.app.recording_by_stem(self._last_saved[0])
        if recording is not None:
            self.app.stabilize(recording)

    def _show_last(self):
        if self._last_saved is not None:
            self.app.select_recording(self._last_saved[0])
            self.app.show_page('analyze')

    def handle_key(self, event) -> bool:
        if event.keysym.lower() == 'm':
            self.mark()
            return True
        return False
