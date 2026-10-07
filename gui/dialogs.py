"""Modal dialogs, the settings and shortcuts windows, and the report image viewer.

Every dialog handles its own close button and Escape key. (The old popups
re-bound the *main* window's close button to themselves, after which the
window's X no longer quit the app.)
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from .settings import APP_DIR, Settings
from .theme import COLORS, FONTS, icon, px


class Dialog(tk.Toplevel):
    def __init__(self, parent, title, width=None):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=COLORS['panel'])
        if parent.winfo_toplevel().winfo_viewable():
            # a transient of a hidden window would stay hidden too (first-run welcome)
            self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.result = None
        self._parent = parent
        self.body = ttk.Frame(self, style='Panel.TFrame', padding=(px(22), px(20), px(22), px(6)))
        self.body.pack(fill='both', expand=True)
        if width:
            self.body.configure(width=px(width))
        self.footer = ttk.Frame(self, style='Panel.TFrame', padding=(px(22), px(12), px(22), px(18)))
        self.footer.pack(fill='x')
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        self.bind('<Escape>', lambda e: self.cancel())

    def button(self, text, command, style='TButton', default=False):
        button = ttk.Button(self.footer, text=text, command=command, style=style)
        button.pack(side='right', padx=(px(8), 0))
        if default:
            self.bind('<Return>', lambda e: command())
        return button

    def show(self):
        """Show modally and return `result` once closed."""
        self.update_idletasks()
        top = self._parent.winfo_toplevel()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        if top.winfo_viewable():
            x = top.winfo_rootx() + (top.winfo_width() - width) // 2
            y = top.winfo_rooty() + (top.winfo_height() - height) // 3
        else:
            x = (self.winfo_screenwidth() - width) // 2
            y = (self.winfo_screenheight() - height) // 3
        self.geometry(f'+{max(0, x)}+{max(0, y)}')
        self.deiconify()
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()
        self.wait_window()
        return self.result

    def finish(self, result):
        self.result = result
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


def _message_body(dialog, title, message, detail='', kind='info'):
    names = {'info': ('info', COLORS['accent']), 'warning': ('warning', COLORS['warning']),
             'danger': ('warning', COLORS['danger']), 'error': ('warning', COLORS['danger']),
             'question': ('info', COLORS['accent'])}
    icon_name, color = names.get(kind, names['info'])
    row = ttk.Frame(dialog.body, style='Panel.TFrame')
    row.pack(fill='x')
    ttk.Label(row, image=icon(icon_name, 28, color), style='Panel.TLabel').pack(side='left', anchor='n',
                                                                               padx=(0, px(14)))
    text = ttk.Frame(row, style='Panel.TFrame')
    text.pack(side='left', fill='both', expand=True)
    ttk.Label(text, text=title, style='Subtitle.Panel.TLabel', wraplength=px(420)).pack(anchor='w')
    if message:
        ttk.Label(text, text=message, style='Panel.TLabel', wraplength=px(420), justify='left').pack(
            anchor='w', pady=(px(6), 0))
    if detail:
        ttk.Label(text, text=detail, style='Muted.Panel.TLabel', wraplength=px(420), justify='left').pack(
            anchor='w', pady=(px(8), 0))
    return text


def confirm(parent, title, message, detail='', ok='OK', cancel='Cancel', danger=False) -> bool:
    dialog = Dialog(parent, title)
    _message_body(dialog, title, message, detail, 'danger' if danger else 'question')
    dialog.button(ok, lambda: dialog.finish(True), 'Danger.TButton' if danger else 'Accent.TButton', default=True)
    dialog.button(cancel, dialog.cancel)
    return bool(dialog.show())


def choose(parent, title, message, options, detail='', cancel='Cancel'):
    """Buttons for each ``(value, text, style)`` in `options`; returns the value or None."""
    dialog = Dialog(parent, title)
    _message_body(dialog, title, message, detail, 'question')
    for value, text, style in reversed(options):
        dialog.button(text, lambda v=value: dialog.finish(v), style)
    if cancel:
        dialog.button(cancel, dialog.cancel)
    return dialog.show()


def show_error(parent, title, message, detail=''):
    dialog = Dialog(parent, title)
    _message_body(dialog, title, message, detail, 'error')
    dialog.button('Close', dialog.cancel, 'Accent.TButton', default=True)
    dialog.show()


def show_info(parent, title, message, detail=''):
    dialog = Dialog(parent, title)
    _message_body(dialog, title, message, detail, 'info')
    dialog.button('OK', dialog.cancel, 'Accent.TButton', default=True)
    dialog.show()


# ------------------------------------------------------------------------------ settings

class SettingsDialog(Dialog):
    """Data folder, spatial calibration and default box size."""

    def __init__(self, parent, settings: Settings, first_run=False):
        super().__init__(parent, 'Welcome' if first_run else 'Settings')
        self.settings = settings
        body = self.body
        if first_run:
            ttk.Label(body, text='Welcome to the capillaroscopy analysis tool', style='Title.Panel.TLabel').pack(
                anchor='w')
            ttk.Label(body, style='Panel.TLabel', wraplength=px(500), justify='left',
                      text='Choose the folder that holds your research data. The app keeps its videos, '
                           'measurements and reports in these subfolders, and creates any that are missing:\n'
                           'RecordedVideos, StabilizedVideos, Statistics and Reports.').pack(
                anchor='w', pady=(px(8), px(14)))
        else:
            ttk.Label(body, text='Settings', style='Title.Panel.TLabel').pack(anchor='w', pady=(0, px(12)))

        grid = ttk.Frame(body, style='Panel.TFrame')
        grid.pack(fill='x')
        grid.columnconfigure(1, weight=1)

        ttk.Label(grid, text='Data folder', style='Bold.Panel.TLabel').grid(row=0, column=0, sticky='w',
                                                                          pady=(0, px(4)))
        self.folder = tk.StringVar(value=settings.data_folder or APP_DIR)
        folder_row = ttk.Frame(grid, style='Panel.TFrame')
        folder_row.grid(row=1, column=0, columnspan=2, sticky='ew')
        entry = ttk.Entry(folder_row, textvariable=self.folder, width=48)
        entry.pack(side='left', fill='x', expand=True)
        ttk.Button(folder_row, text='Browse…', command=self._browse).pack(side='left', padx=(px(8), 0))

        ttk.Label(grid, text='Calibration', style='Bold.Panel.TLabel').grid(row=2, column=0, sticky='w',
                                                                          pady=(px(16), px(4)))
        calibration = ttk.Frame(grid, style='Panel.TFrame')
        calibration.grid(row=3, column=0, columnspan=2, sticky='ew')
        self.mm_per_pixel = tk.StringVar(value=repr(settings.mm_per_pixel))
        self.mm_entry = ttk.Entry(calibration, textvariable=self.mm_per_pixel, width=18)
        self.mm_entry.pack(side='left')
        ttk.Label(calibration, text='mm per pixel', style='Panel.TLabel').pack(side='left', padx=(px(8), 0))
        self.derived = ttk.Label(calibration, text='', style='Muted.Panel.TLabel')
        self.derived.pack(side='left', padx=(px(12), 0))
        ttk.Label(grid, style='Muted.Panel.TLabel', wraplength=px(500), justify='left',
                  text='The size of one video pixel on the skin. It converts pixel distances into mm and '
                       'therefore scales every velocity; measure it again whenever the microscope or its '
                       'magnification changes. Data sets record the value they were made with.').grid(
            row=4, column=0, columnspan=2, sticky='w', pady=(px(4), 0))

        ttk.Label(grid, text='Default box size', style='Bold.Panel.TLabel').grid(row=5, column=0, sticky='w',
                                                                               pady=(px(16), px(4)))
        box_row = ttk.Frame(grid, style='Panel.TFrame')
        box_row.grid(row=6, column=0, columnspan=2, sticky='w')
        self.box_size = tk.StringVar(value=str(settings.box_size))
        ttk.Spinbox(box_row, from_=2, to=200, textvariable=self.box_size, width=6).pack(side='left')
        ttk.Label(box_row, text='pixels (width and height of a new measuring box)',
                  style='Muted.Panel.TLabel').pack(side='left', padx=(px(8), 0))

        self.error = ttk.Label(body, text='', style='Danger.Panel.TLabel', wraplength=px(500))
        self.error.pack(anchor='w', pady=(px(12), 0))

        self.button('Start' if first_run else 'Save', self._save, 'Accent.TButton', default=True)
        if first_run:
            self.button('Quit', self.cancel)
        else:
            self.button('Cancel', self.cancel)
        self.mm_per_pixel.trace_add('write', lambda *_: self._update_derived())
        self._update_derived()

    def _browse(self):
        folder = filedialog.askdirectory(parent=self, initialdir=self.folder.get() or APP_DIR,
                                         title='Choose the data folder')
        if folder:
            self.folder.set(folder)

    def _update_derived(self):
        try:
            value = float(self.mm_per_pixel.get())
        except ValueError:
            self.derived.configure(text='')
            return
        self.derived.configure(text=f'= {value * 1000:.4g} µm per pixel' if value > 0 else '')

    def _save(self):
        folder = self.folder.get().strip()
        if not folder:
            self.error.configure(text='Choose a data folder.')
            return
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            self.error.configure(text=f'The folder cannot be used: {exc}')
            return
        try:
            mm_per_pixel = float(self.mm_per_pixel.get())
            if not 0 < mm_per_pixel < 1:
                raise ValueError
        except ValueError:
            self.error.configure(text='The calibration must be a number of mm per pixel, for example 0.00133.')
            self.mm_entry.state(['invalid'])
            return
        try:
            box_size = int(self.box_size.get())
            if not 2 <= box_size <= 200:
                raise ValueError
        except ValueError:
            self.error.configure(text='The box size must be a whole number between 2 and 200.')
            return
        self.finish(Settings(data_folder=folder, mm_per_pixel=mm_per_pixel, box_size=box_size,
                             path=self.settings.path, extra=dict(self.settings.extra)))


# ------------------------------------------------------------------------------ shortcuts

SHORTCUTS = (
    ('Playback', (
        ('Space', 'Play or pause'),
        ('← / →', 'Previous / next frame'),
        ('Shift + ← / →', 'Back / forward 1 second'),
        ('Q / E', 'Back / forward 500 frames'),
        ('Home / End', 'First / last frame'),
        ('Mouse wheel on the video', 'Zoom in and out around the pointer'),
        ('+ / −', 'Zoom in / out'),
        ('Middle-drag on the video', 'Pan when zoomed in'),
        ('F', 'Fit the video to the window'),
    )),
    ('Centre line', (
        ('Click', 'Add a point (start where the blood comes from)'),
        ('Click on the line', 'Add a point there'),
        ('Drag a point', 'Move it'),
        ('Right-click a point', 'Remove it'),
        ('Backspace', 'Remove the last point'),
        ('X', 'Reverse the line'),
    )),
    ('Boxes (Two boxes)', (
        ('Click', 'Place the selected box (Box 1 first, then Box 2)'),
        ('Right-click or Ctrl + click', 'Place Box 2'),
        ('Drag a box', 'Move it'),
        ('1 / 2', 'Select Box 1 / Box 2'),
        ('W A S D', 'Nudge the selected box by 1 pixel'),
        ('Shift + W A S D', 'Nudge both boxes together'),
        ('X', 'Swap the boxes'),
        ('Delete', 'Remove the selected box'),
    )),
    ('Measurement', (
        ('I / O', 'Start / end the range at the current frame'),
        ('R', 'Reset the range to the whole video'),
        ('M', 'Mark a time point at the current frame'),
        ('Right-click a marker', 'Remove it'),
    )),
    ('Reading blocks (Validation)', (
        ('Drag on the block', 'Draw a line along a streak'),
        ('Drag a line end', 'Move it'),
        ('Right-click a line', 'Remove it'),
        ('Backspace', 'Remove the last line'),
        ('N', 'No clear streaks in this block'),
        ('Enter or →', 'Next block'),
        ('←', 'Previous block'),
        ('Esc', 'Finish later (everything is saved)'),
    )),
    ('Window', (
        ('Ctrl + 1 … 4', 'Centre line, Two boxes, Results, Validation'),
        ('Ctrl + R', 'Look for new videos and data sets'),
        ('Ctrl + ,', 'Settings'),
        ('F1 or ?', 'This list'),
        ('Ctrl + Q', 'Quit'),
        ('Esc', 'Leave a text field'),
    )),
)


class ShortcutsDialog(Dialog):
    def __init__(self, parent):
        super().__init__(parent, 'Keyboard and mouse')
        ttk.Label(self.body, text='Keyboard and mouse', style='Title.Panel.TLabel').pack(anchor='w',
                                                                                      pady=(0, px(10)))
        columns = ttk.Frame(self.body, style='Panel.TFrame')
        columns.pack(fill='both')
        halves = (SHORTCUTS[:3], SHORTCUTS[3:])
        for column, groups in enumerate(halves):
            frame = ttk.Frame(columns, style='Panel.TFrame')
            frame.grid(row=0, column=column, sticky='nw', padx=(0 if column == 0 else px(28), 0))
            row = 0
            for title, items in groups:
                ttk.Label(frame, text=title.upper(), style='Section.Panel.TLabel').grid(
                    row=row, column=0, columnspan=2, sticky='w', pady=(px(10) if row else 0, px(4)))
                row += 1
                for keys, action in items:
                    tk.Label(frame, text=keys, font=FONTS['mono_small'], bg=COLORS['panel_alt'], fg=COLORS['text'],
                             padx=px(6), pady=px(1), bd=0).grid(row=row, column=0, sticky='w', pady=px(2))
                    ttk.Label(frame, text=action, style='Panel.TLabel').grid(row=row, column=1, sticky='w',
                                                                            padx=(px(10), 0))
                    row += 1
        self.button('Close', self.cancel, 'Accent.TButton', default=True)


# ------------------------------------------------------------------------- image viewer

class ImageViewer(tk.Toplevel):
    """A resizable window showing one report image, scaled to fit."""

    def __init__(self, parent, path, title=None, on_open_folder=None):
        super().__init__(parent)
        self.title(title or os.path.basename(path))
        self.configure(bg=COLORS['panel'])
        self.geometry(f'{px(1100)}x{px(640)}')
        self.minsize(px(400), px(260))
        image = Image.open(path).convert('RGBA')
        background = Image.new('RGBA', image.size, (255, 255, 255, 255))
        self._image = Image.alpha_composite(background, image).convert('RGB')
        self._photo = None
        bar = ttk.Frame(self, style='Panel.TFrame', padding=(px(12), px(8)))
        bar.pack(fill='x')
        ttk.Label(bar, text=os.path.basename(path), style='Muted.Panel.TLabel').pack(side='left')
        ttk.Button(bar, text='Close', command=self.destroy).pack(side='right')
        if on_open_folder is not None:
            ttk.Button(bar, text='Show in folder', image=icon('folder', 14, COLORS['muted']), compound='left',
                       command=on_open_folder).pack(side='right', padx=(0, px(8)))
        self.canvas = tk.Canvas(self, bg='#FFFFFF', highlightthickness=0, bd=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', self._fit)
        self.bind('<Escape>', lambda e: self.destroy())

    def _fit(self, event):
        width, height = max(1, event.width - px(16)), max(1, event.height - px(16))
        scale = min(width / self._image.width, height / self._image.height)
        size = (max(1, int(self._image.width * scale)), max(1, int(self._image.height * scale)))
        self._photo = ImageTk.PhotoImage(self._image.resize(size, Image.Resampling.LANCZOS))
        self.canvas.delete('all')
        self.canvas.create_image(event.width // 2, event.height // 2, image=self._photo)
