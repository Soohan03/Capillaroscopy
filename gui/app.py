"""The main window: header with the pages, the recording list, the status bar.

Pages: Centre line (velocity from the space-time diagram along a capillary),
Two boxes (velocity from the delay between two boxes), Results (saved data
sets and reports) and Validation (observers reading blocks by hand, and their
agreement with the estimator). The window owns the selected recording, the
background jobs and the application-wide actions (stabilize, move to trash,
settings).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Optional

from . import library, tasks, theme
from .analyze_page import AnalyzePage
from .dialogs import SettingsDialog, ShortcutsDialog, confirm, show_error
from .jobs import JobManager
from .library_view import LibraryPanel
from .line_page import LinePage
from .results_page import ResultsPage
from .settings import APP_DIR, DataFolder, Settings
from .theme import COLORS, icon, px
from .validation_page import ValidationPage
from .widgets import Tooltip, install_wheel_router

log = logging.getLogger(__name__)

PAGES = (('line', LinePage), ('analyze', AnalyzePage), ('results', ResultsPage), ('validation', ValidationPage))
START_PAGE = 'line'
TEXT_INPUT_CLASSES = ('Entry', 'TEntry', 'Spinbox', 'TSpinbox', 'TCombobox', 'Text', 'Listbox')


def is_wsl() -> bool:
    if os.environ.get('WSL_DISTRO_NAME'):
        return True
    try:
        with open('/proc/version') as handle:
            return 'microsoft' in handle.read().lower()
    except OSError:
        return False


class App:
    def __init__(self, root: tk.Tk, settings: Optional[Settings] = None):
        self.root = root
        theme.apply(root)
        root.title('Capillaroscopy')
        try:
            self._window_icon = tk.PhotoImage(file=os.path.join(APP_DIR, 'Source', 'Capture-Logo.png'))
            root.iconphoto(True, self._window_icon)
        except tk.TclError:
            pass
        install_wheel_router(root)
        root.report_callback_exception = self._report_error
        self._reported = set()

        if settings is None:
            settings = Settings.load()
        if settings is None:
            settings = SettingsDialog(root, Settings(data_folder=APP_DIR), first_run=True).show()
            if settings is None:
                raise SystemExit(0)
            settings.save()
        self.settings = settings
        self.folder = DataFolder(settings.data_folder)
        self.folder.ensure()
        self._clean_partial_outputs()

        self.jobs = JobManager(root)
        self.recordings: list[library.Recording] = []
        self.selected_stem: Optional[str] = None
        self.current_key: Optional[str] = None
        self._status_after = None
        #: who is measuring or reading (initials), shared by the pages and remembered in settings.csv
        self.observer_var = tk.StringVar(value=settings.extra.get('observer', ''))

        self._place_window()
        self._build()
        self.jobs.add_listener(self._update_jobs)
        self.refresh_library()
        self.show_page(START_PAGE)

        root.bind_all('<KeyPress>', self._on_key, add='+')
        root.protocol('WM_DELETE_WINDOW', self.quit)

    # ------------------------------------------------------------------------ layout
    def _place_window(self):
        root = self.root
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        width, height = min(px(1480), int(screen_w * 0.92)), min(px(920), int(screen_h * 0.88))
        root.geometry(f'{width}x{height}+{max(0, (screen_w - width) // 2)}+{max(0, (screen_h - height) // 3)}')
        root.minsize(min(px(1080), width), min(px(660), height))

    def _build(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root, style='Header.TFrame', padding=(px(14), 0, px(10), 0))
        header.grid(row=0, column=0, sticky='ew')
        brand = tk.Canvas(header, width=px(28), height=px(28), bg=COLORS['header'], highlightthickness=0)
        brand.pack(side='left', padx=(0, px(8)))
        brand.create_line(px(8), px(23), px(8), px(10), px(14), px(4), px(20), px(10), px(20), px(23),
                          fill=COLORS['brand'], width=px(3.2), smooth=True, capstyle='round')
        ttk.Label(header, text='Capillaroscopy', style='Brand.Header.TLabel').pack(side='left', padx=(0, px(26)))
        self.nav = tk.StringVar(value=START_PAGE)
        for key, page in PAGES:
            button = ttk.Radiobutton(header, text=page.title, value=key, variable=self.nav, style='Nav.Toolbutton',
                                     command=lambda k=key: self.show_page(k))
            button.pack(side='left')
            Tooltip(button, {'line': 'Velocity along a line drawn on a capillary (Ctrl + 1)',
                             'analyze': 'Velocity between two boxes on a capillary: the original method (Ctrl + 2)',
                             'results': 'Saved data sets and their reports (Ctrl + 3)',
                             'validation': 'Observers read blocks by hand, blinded; their agreement with the '
                                           'estimator (Ctrl + 4)'}[key])
        help_button = ttk.Button(header, text='?', style='Header.TButton', command=self.show_shortcuts, width=2)
        help_button.pack(side='right')
        Tooltip(help_button, 'Keyboard and mouse (F1)')
        settings_button = ttk.Button(header, image=icon('gear', 15, COLORS['header_text']), style='Header.TButton',
                                     command=self.open_settings)
        settings_button.pack(side='right', padx=(0, px(4)))
        Tooltip(settings_button, 'Settings: data folder, calibration, box size')

        self.paned = ttk.Panedwindow(root, orient='horizontal')
        self.paned.grid(row=1, column=0, sticky='nsew')
        self.library = LibraryPanel(self.paned, self)
        self.page_area = ttk.Frame(self.paned, style='TFrame')
        self.page_area.columnconfigure(0, weight=1)
        self.page_area.rowconfigure(0, weight=1)
        self.paned.add(self.library, weight=0)
        self.paned.add(self.page_area, weight=1)
        self.library.configure(width=px(310))
        self._library_shown = True

        self.pages = {key: page(self.page_area, self) for key, page in PAGES}

        status = tk.Frame(root, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'])
        status.grid(row=2, column=0, sticky='ew')
        self.status_label = ttk.Label(status, text='', style='Status.TLabel', padding=(px(14), px(5)))
        self.status_label.pack(side='left', fill='x', expand=True)
        self.folder_label = ttk.Label(status, text='', style='Status.TLabel', padding=(px(10), px(5)), cursor='hand2')
        self.folder_label.pack(side='right')
        self.folder_label.bind('<Button-1>', lambda e: self.open_settings())
        Tooltip(self.folder_label, 'Data folder and spatial calibration. Click to change them.')
        self.job_frame = ttk.Frame(status, style='Panel.TFrame')
        self.job_label = ttk.Label(self.job_frame, text='', style='Status.TLabel')
        self.job_label.pack(side='left', padx=(0, px(8)))
        self.job_progress = ttk.Progressbar(self.job_frame, style='Thin.Horizontal.TProgressbar', length=px(140),
                                            maximum=1.0)
        self.job_progress.pack(side='left')
        self.job_cancel = ttk.Button(self.job_frame, image=icon('close', 9, COLORS['muted']), style='Ghost.TButton',
                                     command=self._cancel_job)
        self.job_cancel.pack(side='left', padx=(px(4), px(6)))
        Tooltip(self.job_cancel, 'Cancel this job')
        self._update_folder_label()

    def _update_folder_label(self):
        root = self.folder.root
        home = os.path.expanduser('~')
        shown = '~' + root[len(home):] if root.startswith(home) else root
        if len(shown) > 48:
            shown = '…' + shown[-47:]
        self.folder_label.configure(text=f'{shown}   ·   {self.settings.um_per_pixel:.4g} µm per pixel')

    # ------------------------------------------------------------------------- pages
    @property
    def current_page(self):
        return self.pages.get(self.current_key)

    def show_page(self, key):
        if key == self.current_key:
            self.nav.set(key)
            return
        current = self.current_page
        if current is not None:
            if hasattr(current, 'can_leave') and not current.can_leave():
                self.nav.set(self.current_key)
                return
            current.on_hide()
            current.grid_remove()
        page = self.pages[key]
        self.current_key = key
        self.nav.set(key)
        self._show_library(page.uses_library)
        page.grid(row=0, column=0, sticky='nsew')
        if page.uses_library:
            page.show_recording(self.current_recording())
        page.on_show()
        self.update_title()

    def _show_library(self, show):
        if show and not self._library_shown:
            self.paned.insert(0, self.library, weight=0)
            self._library_shown = True
        elif not show and self._library_shown:
            self.paned.forget(self.library)
            self._library_shown = False

    def update_title(self):
        page = self.current_page
        stem = self.selected_stem if page is not None and page.uses_library else None
        self.root.title(f'{stem} — Capillaroscopy' if stem else 'Capillaroscopy')

    # -------------------------------------------------------------------- recordings
    def recording_by_stem(self, stem) -> Optional[library.Recording]:
        for recording in self.recordings:
            if recording.stem == stem:
                return recording
        return None

    def current_recording(self):
        return self.recording_by_stem(self.selected_stem)

    def refresh_library(self, select=None):
        self.recordings = library.scan(self.folder)
        stems = [recording.stem for recording in self.recordings]
        if select in stems:
            self.selected_stem = select
        if self.selected_stem not in stems:
            self.selected_stem = stems[0] if stems else None
        self.library.set_recordings(self.recordings, self.selected_stem)
        page = self.current_page
        if page is not None and page.uses_library:
            page.show_recording(self.current_recording())
        self.update_title()

    def select_recording(self, stem):
        if stem == self.selected_stem:
            return
        self.selected_stem = stem
        self.library.set_selected(stem)
        page = self.current_page
        if page is not None and page.uses_library:
            page.show_recording(self.current_recording())
        self.update_title()

    # ---------------------------------------------------------------------- actions
    def stabilize(self, recording):
        if not recording.raw:
            return
        if recording.is_stabilized and not confirm(
                self.root, 'Stabilize again?', f'{recording.stem} already has a stabilized video. Stabilizing it again '
                'replaces it; the current one is moved to the .trash folder.',
                'Data sets measured on the current video keep their numbers, but their box positions may not fit '
                'the new video.', ok='Stabilize again'):
            return
        self._submit_stabilize(recording)

    def _submit_stabilize(self, recording):
        stem = recording.stem
        job = self.jobs.submit(f'Stabilize · {stem}', partial(tasks.stabilize, folder=self.folder,
                                                              raw_path=recording.raw),
                               lane='processing', key=('stabilize', stem),
                               on_done=lambda path: self._processing_done(f'Stabilized {stem}.', stem),
                               on_error=lambda exc: self._processing_failed('Stabilization failed', stem, exc),
                               on_cancel=lambda: self.set_status(f'Stabilization of {stem} cancelled.'))
        if job is None:
            self.set_status(f'{stem} is already being stabilized.')
        else:
            self.set_status(f'Stabilizing {stem} in the background; you can keep working.')

    def stabilize_many(self, recordings):
        if recordings and confirm(self.root, 'Stabilize all raw recordings?',
                                  f'{len(recordings)} recording(s) will be stabilized one after another in the '
                                  'background.', ok='Stabilize'):
            for recording in recordings:
                self._submit_stabilize(recording)

    def _processing_done(self, message, stem):
        self.set_status(message)
        self.refresh_library()

    def _processing_failed(self, title, stem, exc):
        show_error(self.root, title, f'{stem}: {exc}' if str(exc) else f'{stem}: {type(exc).__name__}',
                   'Nothing was written. The details are in capillaroscopy.log.')

    def trash_recording(self, recording):
        paths = tasks.recording_files(self.folder, recording)
        if not paths:
            return
        busy = [job for job in self.jobs.active() if job.key and recording.stem in job.key]
        if busy:
            show_error(self.root, 'Recording in use', 'Wait until the jobs working on this recording have finished.')
            return
        listing = '\n'.join(tasks.relative_path(self.folder, path) for path in paths[:12])
        if len(paths) > 12:
            listing += f'\n… and {len(paths) - 12} more'
        kinds = 'videos, data sets, reports and time points'
        if recording.legacy_flow_files:
            kinds = 'videos, data sets, reports, time points and old optical-flow files'
        if not confirm(self.root, 'Move recording to trash?', f'All {len(paths)} files of {recording.stem} ({kinds}) '
                       'are moved to the .trash folder in the data folder, where you can restore them by hand.',
                       listing, ok='Move to trash', danger=True):
            return
        for page in self.pages.values():
            if getattr(page, 'recording', None) is not None and page.recording.stem == recording.stem:
                page.show_recording(None)
        try:
            target = tasks.move_to_trash(self.folder, paths, recording.stem)
        except OSError as exc:
            show_error(self.root, 'Could not move the files', str(exc))
        else:
            self.set_status(f'Moved {recording.stem} to {os.path.relpath(target, self.folder.root)}.')
        if self.selected_stem == recording.stem:
            self.selected_stem = None
        self.refresh_library()

    def open_folder(self, path):
        """Show `path` (a file is selected in its folder where the platform allows it)."""
        if not path:
            return
        is_file = os.path.isfile(path)
        folder = os.path.dirname(path) if is_file else path
        try:
            if sys.platform.startswith('win'):
                if is_file:
                    subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
                else:
                    os.startfile(folder)  # noqa: S606 - opens the user's own folder
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-R', path] if is_file else ['open', folder])
            elif is_wsl() and shutil.which('explorer.exe') and shutil.which('wslpath'):
                windows = subprocess.run(['wslpath', '-w', path], capture_output=True, text=True,
                                         check=True).stdout.strip()
                subprocess.Popen(['explorer.exe', f'/select,{windows}'] if is_file else ['explorer.exe', windows])
            else:
                subprocess.Popen(['xdg-open', folder])
        except (OSError, subprocess.SubprocessError) as exc:
            self.set_status(f'Could not open the folder ({exc}). It is {folder}')

    def open_settings(self):
        updated = SettingsDialog(self.root, self.settings).show()
        if updated is None:
            return
        try:
            updated.save()
        except OSError as exc:
            show_error(self.root, 'Settings not saved', str(exc))
            return
        folder_changed = os.path.abspath(updated.data_folder) != os.path.abspath(self.settings.data_folder)
        self.settings = updated
        if folder_changed:
            if self.jobs.active():
                show_error(self.root, 'Data folder changed', 'The new folder is used once the running jobs have '
                           'finished their work in the old one.')
            self.folder = DataFolder(updated.data_folder)
            self.folder.ensure()
            self.selected_stem = None
        self._update_folder_label()
        self.refresh_library()
        page = self.current_page
        if page is not None and hasattr(page, 'refresh'):
            page.refresh()
        self.set_status('Settings saved.')

    def show_shortcuts(self):
        ShortcutsDialog(self.root).show()

    def remember_observer(self, code: str):
        """Keep the observer's code for the next start (settings.csv); '' forgets it."""
        if self.observer_var.get() != code:
            self.observer_var.set(code)
        if self.settings.extra.get('observer', '') == code:
            return
        if code:
            self.settings.extra['observer'] = code
        else:
            self.settings.extra.pop('observer', None)
        try:
            self.settings.save()
        except OSError:
            log.warning('Could not save the observer in the settings', exc_info=True)

    # -------------------------------------------------------------------- status bar
    def set_status(self, text, timeout_ms=10000):
        self.status_label.configure(text=text)
        if self._status_after is not None:
            self.root.after_cancel(self._status_after)
        self._status_after = self.root.after(timeout_ms, lambda: self.status_label.configure(text=''))

    def _update_jobs(self):
        running = self.jobs.running()
        queued = [job for job in self.jobs.active() if job.state == 'queued']
        if not running and not queued:
            self.job_frame.pack_forget()
            return
        job = running[0] if running else queued[0]
        text = job.title if job.state == 'running' else f'{job.title} (waiting)'
        if job.message and job.state == 'running':
            text += f'  ·  {job.message}'
        if job.progress is not None:
            text += f'  ·  {100 * job.progress:.0f}%'
        eta = job.eta_s
        if eta is not None and eta > 5:
            text += f'  ·  about {int(eta // 60)} min {int(eta % 60):02d} s left' if eta >= 60 else \
                f'  ·  about {int(eta)} s left'
        others = len(running) + len(queued) - 1
        if others > 0:
            text += f'   (+{others} more)'
        self.job_label.configure(text=text)
        self.job_progress.configure(value=job.progress or 0)
        self._shown_job = job
        if not self.job_frame.winfo_ismapped():
            self.job_frame.pack(side='right', before=self.folder_label)

    def _cancel_job(self):
        job = getattr(self, '_shown_job', None)
        if job is not None and not job.finished:
            job.cancel()
            self.set_status(f'Cancelling: {job.title}…')

    # -------------------------------------------------------------------- keyboard
    def _on_key(self, event):
        widget = event.widget
        if isinstance(widget, str):
            return None
        try:
            widget_class = widget.winfo_class()
            toplevel = widget.winfo_toplevel()
        except (tk.TclError, AttributeError):
            return None
        if toplevel is not self.root:
            return None
        if widget_class in TEXT_INPUT_CLASSES:
            if event.keysym == 'Escape':
                self.root.focus_set()
                return 'break'
            return None
        keysym = event.keysym
        if event.state & 0x0004:
            key = keysym.lower()
            pages = {str(i + 1): key for i, (key, _) in enumerate(PAGES)}
            if key == 'q':
                self.quit()
            elif key in pages:
                self.show_page(pages[key])
            elif key == 'r':
                self.refresh_library()
            elif key == 'comma':
                self.open_settings()
            else:
                return None
            return 'break'
        if keysym in ('F1', 'question'):
            self.show_shortcuts()
            return 'break'
        if widget_class in ('TButton', 'Button', 'TCheckbutton', 'TRadiobutton', 'Toolbutton') and \
                keysym in ('space', 'Return'):
            return None
        page = self.current_page
        if page is not None and page.handle_key(event):
            return 'break'
        return None

    # ---------------------------------------------------------------------- errors
    def _report_error(self, exc_type, value, traceback_):
        log.error('Unhandled error', exc_info=(exc_type, value, traceback_))
        key = f'{exc_type.__name__}: {value}'
        if key in self._reported:
            return
        self._reported.add(key)
        try:
            show_error(self.root, 'Something went wrong', key,
                       'The app keeps running. The full error is in capillaroscopy.log; please mention it if '
                       'the problem persists.')
        except tk.TclError:
            pass

    def _clean_partial_outputs(self):
        partial_dir = self.folder.partial(self.folder.stabilized)
        if os.path.isdir(partial_dir):
            for name in os.listdir(partial_dir):
                path = os.path.join(partial_dir, name)
                try:
                    os.remove(path)
                    log.info('Removed the unfinished output %s', path)
                except OSError:
                    log.warning('Could not remove %s', path)

    # ------------------------------------------------------------------------ quit
    def quit(self):
        page = self.current_page
        if page is not None and hasattr(page, 'can_leave') and not page.can_leave():
            return
        active = self.jobs.active()
        if active:
            titles = '\n'.join(job.title for job in active[:6])
            if not confirm(self.root, 'Quit while work is running?', f'{len(active)} job(s) are not finished. '
                           'Quitting cancels them; their unfinished output is discarded.', titles,
                           ok='Cancel jobs and quit', danger=True):
                return
        self.shutdown()
        self.root.destroy()

    def shutdown(self) -> bool:
        """Stop every background thread; True if all of them ended.

        Threads are waited for because one still inside OpenCV when Python
        exits makes the process abort ("terminate called ...").
        """
        self.status_label.configure(text='Finishing background work…')
        self.root.update_idletasks()
        for page in self.pages.values():
            player = getattr(page, 'player', None)
            if player is not None:
                player.close()
        stopped = self.jobs.close()
        for page in self.pages.values():
            worker = getattr(page, 'preview_worker', None)
            if worker is not None:
                stopped = worker.stop() and stopped
        stopped = self.library.loader.stop() and stopped
        self.pages['results'].shutdown()
        return stopped


def main():
    root = tk.Tk()
    root.withdraw()
    try:
        App(root)
    except SystemExit:
        root.destroy()
        return
    root.deiconify()
    root.mainloop()
    lingering = [thread.name for thread in threading.enumerate()
                 if thread is not threading.main_thread() and thread.is_alive()]
    if lingering:
        # a thread stuck in OpenCV would make the normal exit abort; nothing is left to save
        log.warning('Exiting while threads are still running: %s', ', '.join(lingering))
        logging.shutdown()
        os._exit(0)
