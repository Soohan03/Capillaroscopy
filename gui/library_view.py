"""The list of recordings on the left of the window."""

from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Callable, Optional

from PIL import Image, ImageTk

from .library import Recording
from .media import format_time, make_thumbnail
from .theme import COLORS, FONTS, icon, px, rounded_rect
from .widgets import Tooltip, register_wheel

log = logging.getLogger(__name__)

THUMB_W, THUMB_H = 84, 63


class ThumbnailLoader:
    """Makes thumbnails and reads video metadata on a background thread."""

    def __init__(self, widget, on_ready: Callable):
        self.widget = widget
        self.on_ready = on_ready
        self._requests: queue.Queue = queue.Queue()
        self._results: queue.Queue = queue.Queue()
        self._cache = {}
        self._pending = 0
        self._thread = threading.Thread(target=self._run, name='thumbnails', daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> bool:
        """Drop the waiting requests and end the thread after the current one."""
        while True:
            try:
                self._requests.get_nowait()
            except queue.Empty:
                break
        self._requests.put(None)
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def request(self, stem: str, path: str):
        try:
            key = (path, os.path.getmtime(path))
        except OSError:
            return
        if key in self._cache:
            self.on_ready(stem, *self._cache[key])
            return
        self._pending += 1
        self._requests.put((stem, path, key))
        if self._pending == 1:
            self.widget.after(80, self._poll)

    def _run(self):
        while True:
            request = self._requests.get()
            if request is None:
                return
            stem, path, key = request
            try:
                image, info = make_thumbnail(path, px(THUMB_W), px(THUMB_H))
            except Exception:  # noqa: BLE001 - an unreadable video just has no thumbnail
                log.warning('No thumbnail for %s', path, exc_info=True)
                image, info = None, None
            self._results.put((stem, key, image, info))

    def _poll(self):
        while True:
            try:
                stem, key, image, info = self._results.get_nowait()
            except queue.Empty:
                break
            self._pending -= 1
            photo = ImageTk.PhotoImage(Image.fromarray(image)) if image is not None else None
            self._cache[key] = (photo, info)
            self.on_ready(stem, photo, info)
        if self._pending > 0:
            self.widget.after(80, self._poll)


class RecordingList(tk.Canvas):
    """A scrolling list drawn on a canvas: thumbnail, name, length and status chips per row."""

    def __init__(self, parent, on_select: Callable, on_context: Callable, on_activate: Callable):
        super().__init__(parent, bg=COLORS['panel'], highlightthickness=0, bd=0, takefocus=1, width=px(300))
        self.on_select, self.on_context, self.on_activate = on_select, on_context, on_activate
        self.items: list[Recording] = []
        self.selected: Optional[str] = None
        self.hover: Optional[str] = None
        self.thumbs = {}
        self.meta = {}
        self.row_height = px(84)
        self._empty_text = ''
        self._name_font = tkfont.Font(font=FONTS['bold'])
        self.bind('<Configure>', lambda e: self.redraw())
        self.bind('<ButtonPress-1>', self._click)
        self.bind('<Double-Button-1>', self._double)
        self.bind('<ButtonPress-3>', self._right)
        self.bind('<Motion>', self._motion)
        self.bind('<Leave>', lambda e: self._set_hover(None))
        self.bind('<Up>', lambda e: self._move(-1))
        self.bind('<Down>', lambda e: self._move(1))
        register_wheel(self, lambda steps, e: self.yview_scroll(-steps * 2, 'units'))
        self.configure(yscrollincrement=px(21))

    def set_items(self, items, empty_text=''):
        self.items = list(items)
        self._empty_text = empty_text
        self.redraw()

    def set_selected(self, stem):
        self.selected = stem
        self.redraw()
        self.see(stem)

    def set_thumbnail(self, stem, photo, info):
        self.thumbs[stem] = photo
        self.meta[stem] = info
        self.redraw()

    def see(self, stem):
        for row, item in enumerate(self.items):
            if item.stem == stem:
                top, bottom = row * self.row_height, (row + 1) * self.row_height
                total = max(1, len(self.items) * self.row_height)
                view_top = self.canvasy(0)
                view_bottom = view_top + self.winfo_height()
                if top < view_top:
                    self.yview_moveto(top / total)
                elif bottom > view_bottom:
                    self.yview_moveto((bottom - self.winfo_height()) / total)
                return

    def _row_at(self, y):
        row = int(self.canvasy(y) // self.row_height)
        return self.items[row] if 0 <= row < len(self.items) else None

    def _click(self, event):
        self.focus_set()
        item = self._row_at(event.y)
        if item is not None:
            self.on_select(item)

    def _double(self, event):
        item = self._row_at(event.y)
        if item is not None:
            self.on_activate(item)

    def _right(self, event):
        item = self._row_at(event.y)
        if item is not None:
            self.on_select(item)
            self.on_context(item, event)

    def _motion(self, event):
        item = self._row_at(event.y)
        self._set_hover(item.stem if item else None)

    def _set_hover(self, stem):
        if stem != self.hover:
            self.hover = stem
            self.redraw()

    def _move(self, delta):
        stems = [item.stem for item in self.items]
        if not stems:
            return 'break'
        index = stems.index(self.selected) + delta if self.selected in stems else 0
        index = max(0, min(len(stems) - 1, index))
        self.on_select(self.items[index])
        return 'break'

    def redraw(self):
        self.delete('all')
        width = self.winfo_width()
        if width < 20:
            return
        height = self.row_height
        total = len(self.items) * height
        self.configure(scrollregion=(0, 0, width, max(total, self.winfo_height())))
        if not self.items:
            self.create_text(width / 2, px(60), text=self._empty_text, fill=COLORS['faint'], font=FONTS['small'],
                             width=width - px(40), justify='center')
            return
        name_font = FONTS['bold']
        for row, item in enumerate(self.items):
            top = row * height
            selected, hovered = item.stem == self.selected, item.stem == self.hover
            if selected:
                self.create_rectangle(0, top, width, top + height, fill=COLORS['accent_soft'], outline='')
                self.create_rectangle(0, top, px(3), top + height, fill=COLORS['accent'], outline='')
            elif hovered:
                self.create_rectangle(0, top, width, top + height, fill=COLORS['panel_alt'], outline='')
            self.create_line(px(12), top + height - 1, width - px(12), top + height - 1, fill=COLORS['border'])

            tx, ty = px(14), top + (height - px(THUMB_H)) / 2
            photo = self.thumbs.get(item.stem)
            if photo is not None:
                self.create_image(tx + px(THUMB_W) / 2, ty + px(THUMB_H) / 2, image=photo)
            else:
                self.create_rectangle(tx, ty, tx + px(THUMB_W), ty + px(THUMB_H), fill=COLORS['video_bg'],
                                      outline='')
            x = tx + px(THUMB_W) + px(12)
            available = width - x - px(10)
            self.create_text(x, top + px(14), text=_ellipsize(item.stem, self._name_font, available), anchor='nw',
                             font=name_font, fill=COLORS['text'])
            info = self.meta.get(item.stem)
            if info is not None:
                details = f'{format_time(info.duration_s, precise=False)}  ·  {info.frame_count} frames'
            else:
                details = '…'
            self.create_text(x, top + px(34), text=details, anchor='nw', font=FONTS['small'], fill=COLORS['muted'])
            chips = []
            if item.is_stabilized:
                chips.append(('Stabilized', COLORS['success'], COLORS['success_soft']))
            elif item.raw:
                chips.append(('Raw only', COLORS['warning'], COLORS['warning_soft']))
            if item.dataset_count:
                label = f'{item.dataset_count} data set' + ('s' if item.dataset_count != 1 else '')
                chips.append((label, COLORS['muted'], COLORS['panel_alt'] if not selected else COLORS['panel']))
            cx = x
            for label, foreground, background in chips:
                text = self.create_text(cx + px(7), top + px(57), text=label, anchor='w', font=FONTS['tiny'],
                                        fill=foreground)
                x0, y0, x1, y1 = self.bbox(text)
                if x1 + px(7) > width - px(6):
                    self.delete(text)
                    break
                rounded_rect(self, cx, y0 - px(2), x1 + px(7), y1 + px(2), px(5), fill=background, outline='')
                self.tag_raise(text)
                cx = x1 + px(12)


def _ellipsize(text, font, width):
    """`text`, shortened with an ellipsis to fit `width` pixels in `font` (a tkfont.Font)."""
    if font.measure(text) <= width:
        return text
    while text and font.measure(text + '…') > width:
        text = text[:-1]
    return text + '…'


class LibraryPanel(ttk.Frame):
    """Title, filter, the recording list and the library actions."""

    def __init__(self, parent, app):
        super().__init__(parent, style='Panel.TFrame')
        self.app = app
        self.recordings: list[Recording] = []

        header = ttk.Frame(self, style='Panel.TFrame', padding=(px(16), px(14), px(10), px(8)))
        header.pack(fill='x')
        ttk.Label(header, text='Recordings', style='Subtitle.Panel.TLabel').pack(side='left')
        self.count = ttk.Label(header, text='', style='Muted.Panel.TLabel')
        self.count.pack(side='left', padx=(px(8), 0), pady=(px(2), 0))
        more = ttk.Menubutton(header, image=icon('more', 14, COLORS['muted']), style='Ghost.TButton')
        more.pack(side='right')
        self.menu = tk.Menu(more, tearoff=False)
        more['menu'] = self.menu
        self.menu.configure(postcommand=self._fill_menu)
        Tooltip(more, 'Process several recordings, open the data folder')
        refresh = ttk.Button(header, image=icon('refresh', 14, COLORS['muted']), style='Ghost.TButton',
                             command=lambda: app.refresh_library())
        refresh.pack(side='right')
        Tooltip(refresh, 'Look for new or changed files (Ctrl + R)')

        search_row = ttk.Frame(self, style='Panel.TFrame', padding=(px(14), 0, px(14), px(10)))
        search_row.pack(fill='x')
        self.filter = tk.StringVar()
        self.filter.trace_add('write', lambda *_: self._apply_filter())
        entry = ttk.Entry(search_row, textvariable=self.filter)
        entry.pack(fill='x')
        self._placeholder = tk.Label(entry, text='Filter by name', fg=COLORS['faint'], bg=COLORS['panel'],
                                     font=FONTS['small'], bd=0)
        self._placeholder.place(x=px(8), rely=0.5, anchor='w')
        self._placeholder.bind('<Button-1>', lambda e: entry.focus_set())
        entry.bind('<FocusIn>', lambda e: self._placeholder.place_forget())
        entry.bind('<FocusOut>', lambda e: self._show_placeholder())

        ttk.Separator(self, orient='horizontal').pack(fill='x')
        body = ttk.Frame(self, style='Panel.TFrame')
        body.pack(fill='both', expand=True)
        self.list = RecordingList(body, on_select=self._select, on_context=self._context,
                                  on_activate=lambda item: app.show_page('line'))
        scrollbar = ttk.Scrollbar(body, orient='vertical', command=self.list.yview, style='Slim.Vertical.TScrollbar')
        self.list.configure(yscrollcommand=scrollbar.set)
        self.list.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        ttk.Separator(self, orient='horizontal').pack(fill='x')
        ttk.Label(self, text='Right-click a recording for more actions.', style='Faint.Panel.TLabel',
                  padding=(px(16), px(8))).pack(fill='x')

        self.loader = ThumbnailLoader(self, self.list.set_thumbnail)

    def _show_placeholder(self):
        if not self.filter.get():
            self._placeholder.place(x=px(8), rely=0.5, anchor='w')

    def set_recordings(self, recordings, selected_stem=None):
        self.recordings = recordings
        self._apply_filter()
        self.list.set_selected(selected_stem)
        for recording in recordings:
            self.loader.request(recording.stem, recording.video)
        total = len(recordings)
        self.count.configure(text=str(total) if total else '')

    def _apply_filter(self):
        text = self.filter.get().strip().lower()
        items = [r for r in self.recordings if text in r.stem.lower()] if text else self.recordings
        if self.recordings:
            empty = f'No recording matches "{self.filter.get()}".'
        else:
            empty = ('No videos yet.\n\nCopy videos into RecordedVideos/ (to be stabilized) or '
                     'StabilizedVideos/ in the data folder and refresh.')
        self.list.set_items(items, empty)
        if text:
            self._placeholder.place_forget()

    def set_selected(self, stem):
        self.list.set_selected(stem)

    def _select(self, recording):
        self.app.select_recording(recording.stem)

    def _context(self, recording, event):
        menu = tk.Menu(self, tearoff=False)
        app = self.app
        menu.add_command(label='Measure velocity along a centre line', command=lambda: app.show_page('line'))
        menu.add_command(label='Measure velocity with two boxes', command=lambda: app.show_page('analyze'))
        menu.add_command(label='Results', command=lambda: app.show_page('results'))
        menu.add_separator()
        menu.add_command(label='Re-stabilize…' if recording.is_stabilized else 'Stabilize',
                         command=lambda: app.stabilize(recording),
                         state='normal' if recording.raw else 'disabled')
        menu.add_separator()
        menu.add_command(label='Show in folder', command=lambda: app.open_folder(recording.video))
        menu.add_command(label='Move to trash…', command=lambda: app.trash_recording(recording))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _fill_menu(self):
        app = self.app
        self.menu.delete(0, 'end')
        pending_stabilize = [r for r in self.recordings if r.raw and not r.is_stabilized]
        self.menu.add_command(label=f'Stabilize all raw recordings ({len(pending_stabilize)})',
                              command=lambda: app.stabilize_many(pending_stabilize),
                              state='normal' if pending_stabilize else 'disabled')
        self.menu.add_separator()
        self.menu.add_command(label='Open the data folder', command=lambda: app.open_folder(app.folder.root))
