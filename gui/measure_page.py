"""What the Centre line and Two boxes pages share: video with timeline, a
frame range, time points, naming a data set, running the measurement and
showing its result.

The workflow on both: draw the line (or place the boxes) on the video, choose
the range of frames, name the data set, press Measure. The frames of the range
are read straight from the file in a background job, the data set is saved and
its report written, and the result appears in the panel. `LinePage` and
`AnalyzePage` add their own tool and live preview.

A recording with official occlusion and release times (`metadata/`) offers
its rest, occlusion and the time after release as ranges
(`capillary.inventory.recording_phases`); the timeline marks the occlusion.

During blind placement (`gui.blind`) the recording shows under its code, the
range is the official rest and no result is shown.
"""

from __future__ import annotations

import datetime
import logging
import math
import os
import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Optional

from capillary import datasets, inventory, validation

from . import tasks
from .dialogs import confirm, show_error
from .library import Recording
from .media import FrameSource, format_time
from .theme import COLORS, icon, px
from .transport import Player, Timeline, TransportBar
from .video_view import VideoView
from .widgets import Banner, LineChart, ScrollFrame, Tooltip, section, separator

log = logging.getLogger(__name__)

INSPECTOR_WIDTH = 380
#: What each official phase's range covers, for its button's tooltip.
PHASE_SPANS = {'rest': 'from 2 s after the start to 2 s before the occlusion',
               'occlusion': 'from 2 s after the occlusion to 2 s before the release',
               'after release': 'from 2 s after the release to 2 s before the end of the video'}


class MeasurePage(ttk.Frame):
    key = ''
    title = ''
    kind = 'velocity'           # which data sets this page makes: 'velocity' (two boxes) or 'line'
    uses_library = True
    measure_label = 'Measure and save'
    min_frames = 1

    def __init__(self, parent, app):
        super().__init__(parent, style='TFrame')
        self.app = app
        self.recording: Optional[Recording] = None
        self.video_path: Optional[str] = None
        self.phases: Optional[inventory.Phases] = None
        self.range = None
        self.markers: list[float] = []
        self.results = {}
        self.job = None
        self._saved_state = {}
        self.player = Player(self, self._show_frame, self._player_state_changed)
        self._build()
        app.jobs.add_listener(self._jobs_changed)

    # ---------------------------------------------------------------- hooks for pages
    def video_for(self, recording: Recording) -> Optional[str]:
        raise NotImplementedError

    def empty_state(self, recording: Optional[Recording]):
        """``(title, text)`` for the video area when there is nothing to show."""
        if recording is None:
            if not self.app.recordings:
                return ('No recordings yet', 'Copy videos into RecordedVideos/ (to be stabilized) or '
                        'StabilizedVideos/ in the data folder, then refresh the list (Ctrl + R).')
            return 'Select a recording', 'Choose a video from the list on the left.'
        return 'Nothing to show', ''

    def build_sections(self, body):
        """Add the page's own inspector sections (above Measurement)."""

    def after_frame(self, index):
        pass

    def capture_state(self) -> dict:
        return {'range': self.range}

    def restore_state(self, state: Optional[dict]):
        state = state or {}
        self.range = state.get('range')
        if self.range is not None and self.range[1] >= self.player.frame_count:
            self.range = None

    def measure_blockers(self) -> list[str]:
        return []

    def submit_measurement(self, name, start, end):
        raise NotImplementedError

    def describe_result(self, frame, result):
        """Fill `frame` with the page-specific numbers of a result."""

    def suggest_name(self, existing) -> str:
        """The name offered for the next data set, given the recording's `existing` names."""
        return datasets.suggest_dataset_name(existing)

    def handle_page_key(self, event) -> bool:
        return False

    def update_banner(self):
        self.banner.hide()

    # ------------------------------------------------------------------------ layout
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        center = ttk.Frame(self, style='TFrame', padding=(px(14), px(12), px(12), px(12)))
        center.grid(row=0, column=0, sticky='nsew')
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)

        self.banner = Banner(center)
        self.banner.place_with(lambda: self.banner.grid(row=0, column=0, sticky='ew', pady=(0, px(10))))

        self.view = VideoView(center)
        self.view.grid(row=1, column=0, sticky='nsew')
        self.view.add_view_listener(self.draw_overlay)

        controls = tk.Frame(center, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'],
                            bd=0)
        controls.grid(row=2, column=0, sticky='ew')
        self.timeline = Timeline(controls, on_seek=self.player.seek, on_marker_menu=self._marker_menu)
        self.timeline.pack(fill='x', padx=px(6), pady=(px(4), 0))
        self.transport = TransportBar(controls, self.player, on_mark=self.add_marker)
        self.transport.pack(fill='x')

        tk.Frame(self, bg=COLORS['border'], width=1).grid(row=0, column=1, sticky='ns')
        panel = ttk.Frame(self, style='Panel.TFrame')
        panel.grid(row=0, column=2, sticky='ns')
        footer = ttk.Frame(panel, style='Panel.TFrame', padding=(px(16), px(12), px(16), px(14)))
        footer.pack(side='bottom', fill='x')
        tk.Frame(panel, bg=COLORS['border'], height=1).pack(side='bottom', fill='x')
        self.inspector = ScrollFrame(panel)
        self.inspector.canvas.configure(width=px(INSPECTOR_WIDTH))
        self.inspector.pack(side='top', fill='both', expand=True)
        self._build_footer(footer)
        body = self.inspector.body

        head = ttk.Frame(body, style='Panel.TFrame', padding=(px(16), px(16), px(16), px(12)))
        head.pack(fill='x')
        self.title_label = ttk.Label(head, text='No recording selected', style='Subtitle.Panel.TLabel',
                                     wraplength=px(INSPECTOR_WIDTH - 40), justify='left')
        self.title_label.pack(anchor='w')
        self.subtitle_label = ttk.Label(head, text='', style='Muted.Panel.TLabel',
                                        wraplength=px(INSPECTOR_WIDTH - 40), justify='left')
        self.subtitle_label.pack(anchor='w', pady=(px(3), 0))
        separator(body)

        self.build_sections(body)
        self._build_measurement(body)
        self._build_result(body)

    def _build_measurement(self, body):
        frame = section(body, 'Range and time points', help_text=(
            'Measure uses the frames from the start to the end of the range. Set them at the current frame '
            'with the buttons, or with I and O on the keyboard; the range is shaded on the timeline. '
            'For a recording of the study, the official phases set the range from its occlusion and release '
            'times (metadata/), 2 s away from each event: Rest is what the aims measure. The timeline marks '
            'the occlusion with an orange bar. Time points mark events such as a released cuff.'))
        top = ttk.Frame(frame, style='Panel.TFrame')
        top.pack(fill='x')
        ttk.Label(top, text='Range', style='Muted.Panel.TLabel').pack(side='left')
        reset = ttk.Button(top, text='Whole video', style='Link.Ghost.TButton', command=self.reset_range)
        reset.pack(side='right')
        Tooltip(reset, 'Use every frame of the video (R)')
        self.range_label = ttk.Label(frame, text='–', style='Mono.Panel.TLabel')
        self.range_label.pack(anchor='w', pady=(px(2), 0))
        self.range_detail = ttk.Label(frame, text='', style='Faint.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                      justify='left')
        self.range_detail.pack(anchor='w')
        buttons = ttk.Frame(frame, style='Panel.TFrame')
        buttons.pack(fill='x', pady=(px(8), 0))
        start = ttk.Button(buttons, text='Start here', command=self.set_range_start)
        start.pack(side='left', fill='x', expand=True)
        Tooltip(start, 'Start the range at the current frame (I)')
        end = ttk.Button(buttons, text='End here', command=self.set_range_end)
        end.pack(side='left', fill='x', expand=True, padx=(px(8), 0))
        Tooltip(end, 'End the range at the current frame (O)')

        phase_head = ttk.Frame(frame, style='Panel.TFrame')
        phase_head.pack(fill='x', pady=(px(14), 0))
        ttk.Label(phase_head, text='Official phases', style='Muted.Panel.TLabel').pack(side='left')
        self.phase_times = ttk.Label(phase_head, text='', style='Faint.Panel.TLabel')
        self.phase_times.pack(side='right')
        phase_row = ttk.Frame(frame, style='Panel.TFrame')
        phase_row.pack(fill='x', pady=(px(4), 0))
        self.phase_buttons = {}
        for index, phase in enumerate(inventory.PHASES):
            # three equal columns; the theme's minimum button width would push the third out of the panel
            button = ttk.Button(phase_row, text=phase.capitalize(), width=1, padding=(px(4), px(5)),
                                command=partial(self.set_range_to_phase, phase))
            button.grid(row=0, column=index, sticky='ew', padx=(px(6) if index else 0, 0))
            phase_row.columnconfigure(index, weight=1, uniform='phase')
            Tooltip(button, partial(self._phase_tip, phase))
            self.phase_buttons[phase] = button
        self.phase_note = ttk.Label(frame, text='', style='Faint.Panel.TLabel', wraplength=px(INSPECTOR_WIDTH - 40),
                                    justify='left')
        self.phase_note.pack(anchor='w', pady=(px(3), 0))

        marker_head = ttk.Frame(frame, style='Panel.TFrame')
        marker_head.pack(fill='x', pady=(px(14), 0))
        ttk.Label(marker_head, text='Time points', style='Muted.Panel.TLabel').pack(side='left')
        add = ttk.Button(marker_head, text='Mark current frame', style='Link.Ghost.TButton', command=self.add_marker)
        add.pack(side='right')
        Tooltip(add, 'Mark an event (e.g. cuff released) at the current frame (M). Time points are shared '
                     'by all data sets of the recording and drawn as red lines in the velocity report.')
        self.marker_list = ttk.Frame(frame, style='Panel.TFrame')
        self.marker_list.pack(fill='x')
        separator(body)

    def _build_footer(self, footer):
        names = ttk.Frame(footer, style='Panel.TFrame')
        names.pack(fill='x')
        names.columnconfigure(0, weight=1)
        ttk.Label(names, text='Data set name', style='Muted.Panel.TLabel').grid(row=0, column=0, sticky='w',
                                                                              pady=(0, px(3)))
        observer_label = ttk.Label(names, text='Observer', style='Muted.Panel.TLabel')
        observer_label.grid(row=0, column=1, sticky='w', padx=(px(8), 0), pady=(0, px(3)))
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(names, textvariable=self.name_var)
        self.name_entry.grid(row=1, column=0, sticky='ew')
        self.name_var.trace_add('write', lambda *_: self.update_measure_state())
        self.observer_entry = ttk.Entry(names, textvariable=self.app.observer_var, width=7)
        self.observer_entry.grid(row=1, column=1, sticky='w', padx=(px(8), 0))
        self.app.observer_var.trace_add('write', lambda *_: self.update_measure_state())
        for widget in (observer_label, self.observer_entry):
            Tooltip(widget, 'Initials of who measures (optional). They are saved with the data set, so that the '
                            'same capillary measured by different people can be compared on the Validation page.')
        self.name_message = ttk.Label(footer, text='', style='Faint.Panel.TLabel',
                                      wraplength=px(INSPECTOR_WIDTH - 40), justify='left')
        self.name_message.pack(anchor='w', pady=(px(3), 0))

        self.measure_button = ttk.Button(footer, text=self.measure_label, style='Accent.TButton',
                                         command=self.measure, padding=(px(12), px(8)))
        self.measure_button.pack(fill='x', pady=(px(8), 0))
        self.blocker_label = ttk.Label(footer, text='', style='Faint.Panel.TLabel',
                                       wraplength=px(INSPECTOR_WIDTH - 40), justify='left')
        self.blocker_label.pack(anchor='w', pady=(px(6), 0))

        self.progress_frame = ttk.Frame(footer, style='Panel.TFrame')
        self.progress = ttk.Progressbar(self.progress_frame, style='Thin.Horizontal.TProgressbar', maximum=1.0)
        self.progress.pack(fill='x')
        status_row = ttk.Frame(self.progress_frame, style='Panel.TFrame')
        status_row.pack(fill='x', pady=(px(4), 0))
        self.progress_label = ttk.Label(status_row, text='', style='Muted.Panel.TLabel')
        self.progress_label.pack(side='left')
        ttk.Button(status_row, text='Cancel', style='Link.Ghost.TButton', command=self.cancel_measurement).pack(
            side='right')

    def _build_result(self, body):
        self._result_outer = ttk.Frame(body, style='Panel.TFrame')
        self._result_outer.pack(fill='x')
        frame = section(self._result_outer, 'Last result')
        self.result_title = ttk.Label(frame, text='', style='Bold.Panel.TLabel')
        self.result_title.pack(anchor='w')
        self.result_body = ttk.Frame(frame, style='Panel.TFrame')
        self.result_body.pack(fill='x', pady=(px(6), 0))
        self.result_chart = LineChart(frame, height=96, zero_line=True, unit='mm/s')
        self.result_chart.pack(fill='x', pady=(px(10), 0))
        actions = ttk.Frame(frame, style='Panel.TFrame')
        actions.pack(fill='x', pady=(px(10), 0))
        ttk.Button(actions, text='Open in Results', command=self._open_result).pack(side='left')
        ttk.Button(actions, text='Show files', style='Ghost.TButton',
                   command=lambda: self.app.open_folder(self.app.folder.reports)).pack(side='left', padx=(px(8), 0))
        self._result_outer.pack_forget()

    # ------------------------------------------------------------------- recordings
    def show_recording(self, recording: Optional[Recording]):
        previous = self.recording
        path = self.video_for(recording) if recording is not None else None
        changed = (previous is None) != (recording is None) or (
            recording is not None and previous is not None and (recording.stem != previous.stem or path != self.video_path))
        if previous is not None and changed:
            self._saved_state[previous.stem] = self.capture_state()
        self.recording = recording
        if changed or path != self.video_path:
            self.video_path = path
            self._open_video(path)
            self.phases = self._official_phases(recording)
            self.restore_state(self._saved_state.get(recording.stem) if recording else None)
            if self.app.blind and self.rest_window() is not None:
                self.range = self.rest_window()
            self.name_var.set(self.suggest_name(self.existing_names()))
        self.markers = (datasets.load_time_points(datasets.time_points_file(self.app.folder.statistics,
                                                                              recording.stem))
                        if recording is not None else [])
        self.refresh()

    def existing_names(self):
        if self.recording is None:
            return []
        return self.recording.datasets_of(self.kind)

    def _open_video(self, path):
        self.player.close()
        source = None
        if path is not None:
            try:
                source = FrameSource(path)
            except (OSError, ValueError) as exc:
                self.view.clear()
                self.view.set_empty_message('This video cannot be opened', str(exc))
                path = None
        if source is None:
            self.view.clear()
            self.view.set_empty_message(*self.empty_state(self.recording))
            self.timeline.configure_video(0, 30.0)
            self.transport.update_state()
            return
        self.timeline.configure_video(source.frame_count, source.fps)
        self.player.open(source)
        self.transport.update_state()

    def _official_phases(self, recording) -> Optional[inventory.Phases]:
        source = self.player.source
        if recording is None or source is None:
            return None
        try:
            return inventory.recording_phases(recording.stem, source.fps, source.frame_count)
        except (OSError, ValueError, KeyError):
            log.warning('Could not read the official times', exc_info=True)
            return None

    def refresh(self):
        recording = self.recording
        if recording is None:
            self.title_label.configure(text='No recording selected')
            self.subtitle_label.configure(text='')
        else:
            self.title_label.configure(text=self.app.display_name(recording.stem))
            source = self.player.source
            if source is not None:
                folder = os.path.basename(os.path.dirname(source.path))
                self.subtitle_label.configure(
                    text=f'{folder}  ·  {source.frame_count} frames at {source.fps:g} fps  ·  '
                         f'{format_time(source.duration_s)}  ·  {source.width}×{source.height}')
            else:
                self.subtitle_label.configure(text='')
        self.app.update_title()
        self.update_banner()
        self._update_range_ui()
        self._update_markers_ui()
        self.update_measure_state()
        self._update_result_ui()
        self.draw_overlay()

    # ------------------------------------------------------------------------ frames
    def _show_frame(self, index, frame):
        self.view.show(frame)
        self.timeline.set_position(index)
        self.transport.update_state()
        self.after_frame(index)

    def _player_state_changed(self):
        self.transport.update_state()
        self.after_frame(self.player.index)

    def draw_overlay(self):
        pass

    def on_show(self):
        pass

    def on_hide(self):
        self.player.pause()

    # ------------------------------------------------------------------------- range
    def current_range(self):
        if self.player.source is None:
            return None
        return self.range or (0, self.player.frame_count - 1)

    def set_range_start(self):
        if self.player.source is None:
            return
        _, end = self.current_range()
        start = self.player.index
        self.range = (start, end if end > start else self.player.frame_count - 1)
        self._range_changed()

    def set_range_end(self):
        if self.player.source is None:
            return
        start, _ = self.current_range()
        end = self.player.index
        self.range = (start if start < end else 0, end)
        self._range_changed()

    def reset_range(self):
        self.range = None
        self._range_changed()

    def set_range_to_phase(self, phase):
        """Set the range to an official phase of the recording ('rest', 'occlusion', 'after release')."""
        window = (self.phases.windows if self.phases is not None else {}).get(phase)
        if window is None or self.player.source is None:
            return
        self.range = tuple(window)
        self._range_changed()

    def rest_window(self):
        """The official rest's frames (first, last), or None when the recording has none."""
        window = (self.phases.windows if self.phases is not None else {}).get('rest')
        return tuple(window) if window is not None and self.player.source is not None else None

    def range_phase(self) -> str:
        """The official phases the current range lies in ('rest', 'rest + occlusion', ...), '' if unknown."""
        selected = self.current_range()
        if selected is None or self.phases is None:
            return ''
        return self.phases.phase_of(selected[0], selected[1], self.player.fps)

    def _range_changed(self):
        if self.range == (0, self.player.frame_count - 1):
            self.range = None
        self._update_range_ui()
        self.update_measure_state()

    def _update_range_ui(self):
        self._update_phase_ui()
        selected = self.current_range()
        if selected is None:
            self.range_label.configure(text='–')
            self.range_detail.configure(text='')
            self.timeline.set_range(None)
            return
        start, end = selected
        fps = self.player.fps
        count = end - start + 1
        self.range_label.configure(text=f'{format_time(start / fps)}  →  {format_time(end / fps)}')
        scope = 'whole video' if self.range is None else (self.range_phase() or 'part of the video')
        self.range_detail.configure(text=f'frames {start}–{end}  ·  {count} frames ({count / fps:.1f} s)  ·  {scope}')
        self.timeline.set_range(None if self.range is None else self.range)

    def _update_phase_ui(self):
        phases = self.phases
        windows = phases.windows if phases is not None else {}
        for phase, button in self.phase_buttons.items():
            button.state(['!disabled'] if phase in windows else ['disabled'])
        if phases is None:
            self.phase_times.configure(text='')
            self.phase_note.configure(text='No official times for this recording.' if self.player.source else '')
            self.timeline.set_phases(None, None)
            return
        times = f'occlusion {format_time(phases.occlusion_s)}'
        if phases.release_s is not None:
            times += f'  ·  release {format_time(phases.release_s)}'
        self.phase_times.configure(text=times)
        self.phase_note.configure(text=' '.join(phases.notes))
        if windows:
            self.timeline.set_phases(phases.occlusion_s, phases.release_s)
        else:
            self.timeline.set_phases(None, None)

    def _phase_tip(self, phase):
        window = (self.phases.windows if self.phases is not None else {}).get(phase)
        if window is None:
            return f'No official {phase} for this recording.'
        first, last = window
        fps = self.player.fps
        return (f'Set the range to the {phase}, {PHASE_SPANS[phase]}: {format_time(first / fps)} → '
                f'{format_time(last / fps)}, frames {first}–{last} ({(last - first + 1) / fps:.1f} s).')

    # ----------------------------------------------------------------------- markers
    def add_marker(self):
        if self.recording is None or self.player.source is None:
            return
        seconds = round(self.player.index / self.player.fps, 4)
        if any(abs(seconds - existing) < 1e-6 for existing in self.markers):
            return
        self.markers = sorted(self.markers + [seconds])
        self._save_markers()
        self.app.set_status(f'Time point marked at {format_time(seconds)}.')

    def remove_marker(self, index):
        if 0 <= index < len(self.markers):
            del self.markers[index]
            self._save_markers()

    def _save_markers(self):
        path = datasets.time_points_file(self.app.folder.statistics, self.recording.stem)
        try:
            datasets.save_time_points(path, self.markers)
        except OSError as exc:
            show_error(self, 'Time points not saved', str(exc))
        self._update_markers_ui()

    def _marker_menu(self, index, event):
        menu = tk.Menu(self, tearoff=False)
        seconds = self.markers[index]
        menu.add_command(label=f'Go to {format_time(seconds)}',
                         command=lambda: self.player.seek(int(round(seconds * self.player.fps))))
        menu.add_command(label='Remove this time point', command=lambda: self.remove_marker(index))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _update_markers_ui(self):
        for child in self.marker_list.winfo_children():
            child.destroy()
        self.timeline.set_markers(self.markers)
        if not self.markers:
            ttk.Label(self.marker_list, text='None marked', style='Faint.Panel.TLabel').pack(anchor='w', pady=(px(2), 0))
            return
        for index, seconds in enumerate(self.markers):
            row = ttk.Frame(self.marker_list, style='Panel.TFrame')
            row.pack(fill='x', pady=(px(2), 0))
            ttk.Label(row, image=icon('flag', 12, COLORS['marker']), style='Panel.TLabel').pack(side='left')
            go = ttk.Button(row, text=format_time(seconds), style='Link.Ghost.TButton',
                            command=lambda s=seconds: self.player.seek(int(round(s * self.player.fps))))
            go.pack(side='left', padx=(px(4), 0))
            remove = ttk.Button(row, image=icon('close', 9, COLORS['muted']), style='Ghost.TButton',
                                command=lambda i=index: self.remove_marker(i))
            remove.pack(side='right')
            Tooltip(remove, 'Remove this time point')

    # ------------------------------------------------------------------- measuring
    def _blockers(self):
        reasons = []
        if self.player.source is None:
            return ['Select a recording with a video.']
        reasons += self.measure_blockers()
        if self.app.blind:
            rest = self.rest_window()
            if rest is None:
                reasons.append('This recording has no official rest, and blind placement measures only the rest.')
            elif self.current_range() != rest:
                reasons.append('Blind placement measures the official rest: press Rest.')
        start, end = self.current_range()
        if end - start + 1 < self.min_frames:
            reasons.append(f'The range must hold at least {self.min_frames} frames '
                           f'({self.min_frames / self.player.fps:.1f} s); it has {end - start + 1}.')
        message = datasets.validate_dataset_name(self.name_var.get())
        if message:
            reasons.append(message)
        if self.app.observer_var.get().strip():
            message = validation.validate_observer(self.app.observer_var.get())
            if message:
                reasons.append(f'Observer: {message}')
        return reasons

    def observer(self) -> str:
        """The observer's code as saved with a data set ('' if none was entered)."""
        return validation.normalize_observer(self.app.observer_var.get())

    def update_measure_state(self):
        name = self.name_var.get()
        message = datasets.validate_dataset_name(name) if name else None
        if message:
            self.name_message.configure(text=message, style='Danger.Panel.TLabel')
            self.name_entry.state(['invalid'])
        else:
            self.name_entry.state(['!invalid'])
            if name.strip() in self.existing_names():
                self.name_message.configure(text='A data set with this name exists and will be replaced.',
                                            style='Warning.Panel.TLabel')
            elif name.strip():
                prefix = f' as {self.recording.stem}___{name.strip()}___…' if self.recording and not self.app.blind \
                    else ''
                self.name_message.configure(text=f'Saved{prefix} in Statistics/ and Reports/.',
                                            style='Faint.Panel.TLabel')
            else:
                self.name_message.configure(text='')
        running = self.job is not None and not self.job.finished
        blockers = self._blockers() if not running else []
        self.measure_button.state(['disabled'] if (blockers or running) else ['!disabled'])
        self.blocker_label.configure(text=blockers[0] if blockers else '')
        if running:
            self.blocker_label.pack_forget()
            self.progress_frame.pack(fill='x', pady=(px(10), 0))
        else:
            self.progress_frame.pack_forget()
            self.blocker_label.pack(anchor='w', pady=(px(6), 0))

    def measure(self):
        if self._blockers() or self.recording is None:
            return
        name = self.name_var.get().strip()
        recording = self.recording
        shown = self.app.display_name(recording.stem)
        if name in self.existing_names():
            if not confirm(self, 'Replace data set?', f'A data set named "{name}" already exists '
                           f'for {shown}.', 'Its files are moved to the .trash folder in the data folder, '
                           'where you can restore them by hand.', ok='Replace', danger=True):
                return
            folder = self.app.folder
            paths = datasets.dataset_paths(folder.statistics, folder.reports, recording.stem, name, self.kind)
            try:
                tasks.move_to_trash(folder, paths, f'{recording.stem} {name}')
            except OSError as exc:
                show_error(self, 'Could not replace the data set', str(exc))
                return
        start, end = self.current_range()
        stem = recording.stem
        self.app.remember_observer(self.observer())

        def done(result):
            self.results[stem] = dict(result, saved=datetime.datetime.now())
            self.job = None
            summary = '' if self.app.blind else self.result_status(result)
            self.app.set_status(f'Saved data set "{name}" for {shown}{summary}.')
            self.app.refresh_library()
            if self.recording is not None and self.recording.stem == stem:
                self.name_var.set(self.suggest_name(self.existing_names() + [name]))
            self.update_measure_state()
            self._update_result_ui()

        def failed(exc):
            self.job = None
            self.update_measure_state()
            show_error(self, 'The measurement failed', str(exc) or type(exc).__name__,
                       'Nothing was saved. The details are in capillaroscopy.log.')

        def cancelled():
            self.job = None
            self.update_measure_state()
            self.app.set_status('Measurement cancelled; nothing was saved.')

        self.job = self.submit_measurement(name, start, end, done, failed, cancelled)
        self.update_measure_state()
        self._jobs_changed()

    def cancel_measurement(self):
        if self.job is not None:
            self.job.cancel()

    def result_status(self, result) -> str:
        return ''

    def _jobs_changed(self):
        job = self.job
        if job is None or job.finished:
            return
        if job.state == 'queued':
            self.progress.configure(value=0)
            self.progress_label.configure(text='Waiting for another job to finish…')
        else:
            self.progress.configure(value=job.progress or 0)
            percent = f'{100 * (job.progress or 0):.0f}%'
            self.progress_label.configure(text=f'{job.message or "Working"}…  {percent}')

    # ------------------------------------------------------------------------ result
    def _update_result_ui(self):
        result = self.results.get(self.recording.stem) if self.recording else None
        if result is None or self.app.blind:
            self._result_outer.pack_forget()
            return
        self._result_outer.pack(fill='x')
        saved = result.get('saved')
        self.result_title.configure(text=f'"{result["name"]}"' + (f'  ·  saved {saved:%H:%M}' if saved else ''))
        for child in self.result_body.winfo_children():
            child.destroy()
        self.describe_result(self.result_body, result)
        series = result.get('series')
        values = [v for v in (series or {}).get('v', []) if v is not None and math.isfinite(v)]
        if len(values) > 1:
            self.result_chart.set_data([(series['t'], series['v'], COLORS['accent'])])
        else:
            self.result_chart.set_message(self.empty_chart_message(result))

    def empty_chart_message(self, result) -> str:
        """What the result chart says when it has fewer than two values to plot."""
        return 'No value could be resolved in this range, so there is nothing to plot.'

    def _open_result(self):
        result = self.results.get(self.recording.stem) if self.recording else None
        self.app.show_page('results')
        if result is not None:
            self.app.pages['results'].focus_dataset(result['kind'], result['name'])

    # ----------------------------------------------------------------------- keyboard
    def handle_key(self, event) -> bool:
        if self.handle_page_key(event):
            return True
        if self.player.source is None:
            return False
        keysym = event.keysym
        shift = bool(event.state & 0x0001)
        key = keysym.lower()
        fps_step = max(1, int(round(self.player.fps)))
        if keysym == 'space':
            self.player.toggle()
        elif keysym in ('Left', 'KP_Left'):
            self.player.step(-fps_step if shift else -1)
        elif keysym in ('Right', 'KP_Right'):
            self.player.step(fps_step if shift else 1)
        elif key == 'q':
            self.player.step(-500)
        elif key == 'e':
            self.player.step(500)
        elif keysym == 'Home':
            self.player.seek(0)
        elif keysym == 'End':
            self.player.seek(self.player.frame_count - 1)
        elif key == 'i':
            self.set_range_start()
        elif key == 'o':
            self.set_range_end()
        elif key == 'r':
            self.reset_range()
        elif key == 'm':
            self.add_marker()
        elif key == 'f':
            self.view.fit()
        elif keysym in ('plus', 'equal', 'KP_Add'):
            self.view.zoom_by(1.25)
        elif keysym in ('minus', 'KP_Subtract'):
            self.view.zoom_by(1 / 1.25)
        else:
            return False
        return True


def stat(parent, label, value, style='Mono.Panel.TLabel', tooltip=None):
    """A ``label .... value`` line in a result panel."""
    row = ttk.Frame(parent, style='Panel.TFrame')
    row.pack(fill='x', pady=(px(1), px(1)))
    name = ttk.Label(row, text=label, style='Muted.Panel.TLabel')
    name.pack(side='left')
    ttk.Label(row, text=value, style=style).pack(side='right')
    if tooltip:
        Tooltip(name, tooltip, wrap=320)
    return row
