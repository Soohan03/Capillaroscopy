"""Validation page: observers read space-time blocks by hand, blinded, to check the centre-line velocity.

A real recording has no ground truth, so the estimator is compared with
people (`capillary.validation`). A *reading set* is drawn from saved
centre-line data sets; every observer reads every block of it, one at a time,
without seeing where it comes from or what the estimator found, by drawing
lines along the streaks or marking that there are none; the *agreement*
(Bland-Altman, ICC, kappa) is computed once the readings are done.

The page has two modes: the overview (reading sets, their readings and the
agreement, and the line-placement comparison of `capillary.placement`) and
reading, which fills the page with one block at a time (`gui.reading_view`).
"""

from __future__ import annotations

import datetime
import math
import os
import random
import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Optional

import numpy as np
import pandas as pd
from PIL import Image, ImageTk

from capillary import datasets, placement, validation

from . import tasks
from .dialogs import Dialog, ImageViewer, show_error
from .reading_view import Reader
from .theme import COLORS, FONTS, icon, px
from .widgets import ScrollFrame, Tooltip, register_wheel

SET_LIST_WIDTH = 300
THUMB_WIDTH = 300
PLOT_TITLES = {'bland_altman': 'Bland-Altman plots', 'scatter': 'Against each other'}
#: Key of the line-placement entry in the list (no reading set can have it: '/' is not allowed in names).
PLACEMENT = '/line placement'


# ------------------------------------------------------------------------ dialogs

class NewReadingSetDialog(Dialog):
    """Name, data sets, blocks per data set, sampling and seed of a new reading set."""

    def __init__(self, parent, sources, existing):
        super().__init__(parent, 'New reading set')
        self.existing = set(existing)
        body = self.body
        wrap = px(560)
        ttk.Label(body, text='New reading set', style='Title.Panel.TLabel').pack(anchor='w')
        ttk.Label(body, style='Muted.Panel.TLabel', wraplength=wrap, justify='left', text=(
            'Blocks of 3 s are drawn at random from the chosen centre-line data sets, never overlapping, and '
            'copied into the set. Observers then read them by hand without knowing where they come from or what '
            'the estimator found.')).pack(anchor='w', pady=(px(6), px(14)))

        ttk.Label(body, text='Name', style='Bold.Panel.TLabel').pack(anchor='w')
        self.name = tk.StringVar(value=datasets.suggest_dataset_name(existing, base='reading'))
        self.name_entry = ttk.Entry(body, textvariable=self.name, width=40)
        self.name_entry.pack(anchor='w', pady=(px(3), px(12)))

        head = ttk.Frame(body, style='Panel.TFrame')
        head.pack(fill='x')
        ttk.Label(head, text='Data sets', style='Bold.Panel.TLabel').pack(side='left')
        ttk.Button(head, text='None', style='Link.Ghost.TButton', command=lambda: self._check_all(False)).pack(
            side='right')
        ttk.Button(head, text='All', style='Link.Ghost.TButton', command=lambda: self._check_all(True)).pack(
            side='right')
        box = tk.Frame(body, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'])
        box.pack(fill='x', pady=(px(3), px(12)))
        scroll = ScrollFrame(box)
        scroll.canvas.configure(height=px(min(220, 26 * max(1, len(sources)) + 8)), width=px(540))
        scroll.pack(fill='both', expand=True)
        self.checks = []
        for stem, name in sources:
            variable = tk.BooleanVar(value=True)
            ttk.Checkbutton(scroll.body, text=f'{stem}  ·  {name}', variable=variable, style='Panel.TCheckbutton',
                            command=self._update_summary).pack(anchor='w', padx=px(8), pady=px(2))
            self.checks.append(((stem, name), variable))

        options = ttk.Frame(body, style='Panel.TFrame')
        options.pack(fill='x')
        ttk.Label(options, text='Blocks per data set', style='Bold.Panel.TLabel').grid(row=0, column=0, sticky='w')
        self.count = tk.StringVar(value=str(validation.DEFAULT_BLOCKS_PER_DATASET))
        ttk.Spinbox(options, from_=1, to=40, textvariable=self.count, width=5,
                    command=self._update_summary).grid(row=0, column=1, sticky='w', padx=(px(10), 0))
        self.count.trace_add('write', lambda *_: self._update_summary())
        ttk.Label(options, text='Seed', style='Bold.Panel.TLabel').grid(row=0, column=2, sticky='w', padx=(px(24), 0))
        self.seed = tk.StringVar(value=str(random.SystemRandom().randrange(1, 1_000_000)))
        seed_entry = ttk.Entry(options, textvariable=self.seed, width=10)
        seed_entry.grid(row=0, column=3, sticky='w', padx=(px(10), 0))
        Tooltip(seed_entry, 'Recorded with the set. The same seed and data sets draw the same blocks, and give '
                            'every observer the same order again.')
        self.balanced = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text='Half from blocks the estimator resolved, half from blocks it did not',
                        variable=self.balanced, style='Panel.TCheckbutton').pack(anchor='w', pady=(px(12), 0))
        ttk.Label(body, style='Faint.Panel.TLabel', wraplength=wrap, justify='left', text=(
            'Recommended: agreement on velocity needs resolved blocks, agreement on whether a block can be read '
            'at all needs both kinds.')).pack(anchor='w', padx=(px(22), 0))
        self.summary = ttk.Label(body, text='', style='Muted.Panel.TLabel')
        self.summary.pack(anchor='w', pady=(px(12), 0))
        self.error = ttk.Label(body, text='', style='Danger.Panel.TLabel', wraplength=wrap)
        self.error.pack(anchor='w', pady=(px(6), 0))

        self.button('Draw blocks', self._ok, 'Accent.TButton', default=True)
        self.button('Cancel', self.cancel)
        self._update_summary()

    def _check_all(self, value):
        for _, variable in self.checks:
            variable.set(value)
        self._update_summary()

    def _chosen(self):
        return [source for source, variable in self.checks if variable.get()]

    def _update_summary(self):
        try:
            count = int(self.count.get())
        except ValueError:
            count = 0
        chosen = len(self._chosen())
        self.summary.configure(text=f'Up to {count * chosen} blocks from {chosen} data set'
                                    f'{"s" if chosen != 1 else ""}.' if count > 0 else '')

    def _ok(self):
        name = self.name.get().strip()
        message = validation.validate_set_name(name)
        if message is None and name in self.existing:
            message = f'A reading set named "{name}" already exists.'
        if message:
            self.error.configure(text=message)
            return
        sources = self._chosen()
        if not sources:
            self.error.configure(text='Choose at least one data set.')
            return
        try:
            count = int(self.count.get())
            if not 1 <= count <= 40:
                raise ValueError
        except ValueError:
            self.error.configure(text='Blocks per data set must be a whole number from 1 to 40.')
            return
        try:
            seed = int(self.seed.get())
            if seed < 0:
                raise ValueError
        except ValueError:
            self.error.configure(text='The seed must be a whole number, for example 1234.')
            return
        self.finish({'name': name, 'sources': sources, 'blocks_per_dataset': count,
                     'balanced': bool(self.balanced.get()), 'seed': seed})


class StartReadingDialog(Dialog):
    """Who reads, and which session."""

    def __init__(self, parent, reading_set, observer=''):
        super().__init__(parent, 'Start reading')
        self.reading_set = reading_set
        body = self.body
        wrap = px(460)
        ttk.Label(body, text='Start reading', style='Title.Panel.TLabel').pack(anchor='w')
        ttk.Label(body, style='Muted.Panel.TLabel', wraplength=wrap, justify='left', text=(
            f'The {len(reading_set.items)} blocks of "{reading_set.name}" are shown one at a time, in an order of '
            'your own, without where they come from or what the estimator found. Everything is saved as you go; '
            'you can stop and continue later.')).pack(anchor='w', pady=(px(6), px(14)))
        grid = ttk.Frame(body, style='Panel.TFrame')
        grid.pack(fill='x')
        ttk.Label(grid, text='Observer', style='Bold.Panel.TLabel').grid(row=0, column=0, sticky='w')
        self.observer = tk.StringVar(value=observer)
        self.entry = ttk.Entry(grid, textvariable=self.observer, width=12)
        self.entry.grid(row=0, column=1, sticky='w', padx=(px(10), 0))
        ttk.Label(grid, text='initials', style='Faint.Panel.TLabel').grid(row=0, column=2, sticky='w',
                                                                          padx=(px(8), 0))
        ttk.Label(grid, text='Session', style='Bold.Panel.TLabel').grid(row=1, column=0, sticky='w', pady=(px(8), 0))
        self.session = tk.StringVar(value='1')
        ttk.Spinbox(grid, from_=1, to=20, textvariable=self.session, width=5).grid(row=1, column=1, sticky='w',
                                                                                   padx=(px(10), 0),
                                                                                   pady=(px(8), 0))
        self.info = ttk.Label(body, text='', style='Muted.Panel.TLabel', wraplength=wrap, justify='left')
        self.info.pack(anchor='w', pady=(px(12), 0))
        ttk.Label(body, style='Faint.Panel.TLabel', wraplength=wrap, justify='left', text=(
            'A second session by the same observer, some days later and in a new order, measures how well '
            'one person repeats their own reading.')).pack(anchor='w', pady=(px(8), 0))
        self.error = ttk.Label(body, text='', style='Danger.Panel.TLabel', wraplength=wrap)
        self.error.pack(anchor='w', pady=(px(6), 0))
        self.observer.trace_add('write', lambda *_: self._observer_changed())
        self.session.trace_add('write', lambda *_: self._update_info())
        self.button('Start', self._ok, 'Accent.TButton', default=True)
        self.button('Cancel', self.cancel)
        self._observer_changed()
        self.entry.focus_set()

    def _observer_changed(self):
        if validation.validate_observer(self.observer.get()) is None:
            self.session.set(str(self.reading_set.next_session(self.observer.get())))
        self._update_info()

    def _update_info(self):
        observer = validation.normalize_observer(self.observer.get())
        try:
            session = int(self.session.get())
        except ValueError:
            self.info.configure(text='')
            return
        if not observer or validation.validate_observer(observer):
            self.info.configure(text='')
            return
        existing = {r.session: r for r in self.reading_set.readings() if r.observer == observer}
        reading = existing.get(session)
        total = len(self.reading_set.items)
        if reading is None:
            done = [s for s in sorted(existing) if existing[s].is_complete]
            text = f'Starts session {session} for {observer}.'
            if done:
                text += f' Finished before: session{"s" if len(done) > 1 else ""} {", ".join(map(str, done))}.'
        elif reading.is_complete:
            text = f'{observer} has finished session {session}: you can look through it and change readings.'
        else:
            text = f'Continues {observer}\'s session {session}: {reading.read_count} of {total} blocks read.'
        self.info.configure(text=text)

    def _ok(self):
        message = validation.validate_observer(self.observer.get())
        if message:
            self.error.configure(text=message)
            return
        try:
            session = int(self.session.get())
            if session < 1:
                raise ValueError
        except ValueError:
            self.error.configure(text='The session must be a whole number from 1.')
            return
        self.finish((validation.normalize_observer(self.observer.get()), session))


# --------------------------------------------------------------------------- set list

class SetList(tk.Canvas):
    """Rows of (key, title, detail): the reading sets, or the line-placement comparison."""

    def __init__(self, parent, on_select, height=None):
        super().__init__(parent, bg=COLORS['panel'], highlightthickness=0, bd=0, width=px(SET_LIST_WIDTH),
                         **({'height': height} if height else {}))
        self.on_select = on_select
        self.rows: list[tuple[str, str, str]] = []
        self.selected: Optional[str] = None
        self.hover: Optional[str] = None
        self.row_height = px(58)
        self.empty_text = ''
        self.bind('<Configure>', lambda e: self.redraw())
        self.bind('<ButtonPress-1>', self._click)
        self.bind('<Motion>', self._motion)
        self.bind('<Leave>', lambda e: self._set_hover(None))
        register_wheel(self, lambda steps, e: self.yview_scroll(-steps * 2, 'units'))
        self.configure(yscrollincrement=px(20))

    def set_rows(self, rows, selected, empty_text=''):
        self.rows, self.selected, self.empty_text = list(rows), selected, empty_text
        self.redraw()

    def _row_at(self, y):
        index = int(self.canvasy(y) // self.row_height)
        return self.rows[index][0] if 0 <= index < len(self.rows) else None

    def _click(self, event):
        name = self._row_at(event.y)
        if name is not None:
            self.on_select(name)

    def _motion(self, event):
        self._set_hover(self._row_at(event.y))

    def _set_hover(self, name):
        if name != self.hover:
            self.hover = name
            self.redraw()

    def redraw(self):
        self.delete('all')
        width = self.winfo_width()
        if width < 20:
            return
        height = self.row_height
        self.configure(scrollregion=(0, 0, width, max(len(self.rows) * height, self.winfo_height())))
        if not self.rows:
            self.create_text(width / 2, px(50), text=self.empty_text, fill=COLORS['faint'], font=FONTS['small'],
                             width=width - px(40), justify='center')
            return
        for row, (key, title, detail) in enumerate(self.rows):
            top = row * height
            if key == self.selected:
                self.create_rectangle(0, top, width, top + height, fill=COLORS['accent_soft'], outline='')
                self.create_rectangle(0, top, px(3), top + height, fill=COLORS['accent'], outline='')
            elif key == self.hover:
                self.create_rectangle(0, top, width, top + height, fill=COLORS['panel_alt'], outline='')
            if row < len(self.rows) - 1 or len(self.rows) > 1:
                self.create_line(px(12), top + height - 1, width - px(12), top + height - 1, fill=COLORS['border'])
            self.create_text(px(16), top + px(12), text=title, anchor='nw', font=FONTS['bold'], fill=COLORS['text'],
                             width=width - px(28))
            self.create_text(px(16), top + px(32), text=detail, anchor='nw', font=FONTS['small'],
                             fill=COLORS['muted'], width=width - px(28))


# ------------------------------------------------------------------------------ page

def _finite(value) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool) \
        and math.isfinite(value)


def _signed(value, digits=4):
    return f'{value:+.{digits}f}' if _finite(value) else '–'


def _between(low, high, digits=4):
    return f'{low:+.{digits}f} to {high:+.{digits}f}' if _finite(low) and _finite(high) else '–'


def _ratio_limits(low, high):
    if not (_finite(low) and _finite(high)):
        return '–'
    return f'{100 * (low - 1):+.0f} % to {100 * (high - 1):+.0f} %'


def _with_ci(value, low, high, digits=2):
    if not _finite(value):
        return '–'
    text = f'{value:.{digits}f}'
    return text + (f'  ({low:.{digits}f} to {high:.{digits}f})' if _finite(low) and _finite(high) else '')


def _percent(value):
    return f'{100 * value:.0f} %' if _finite(value) else '–'


def _thumbnail(path, width):
    image = Image.open(path).convert('RGBA')
    background = Image.new('RGBA', image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert('RGB')
    image.thumbnail((width, width), Image.Resampling.LANCZOS)
    return image


class ValidationPage(ttk.Frame):
    key = 'validation'
    title = 'Validation'
    uses_library = False

    def __init__(self, parent, app):
        super().__init__(parent, style='TFrame')
        self.app = app
        self.names: list[str] = []
        self.selected: Optional[str] = None
        self.current: Optional[validation.ReadingSet] = None
        self.reading_mode = False
        self._photos = []
        self._agreement_job = None

        self.overview = ttk.Frame(self, style='TFrame')
        self.overview.columnconfigure(2, weight=1)
        self.overview.rowconfigure(0, weight=1)
        side = ttk.Frame(self.overview, style='Panel.TFrame')
        side.grid(row=0, column=0, sticky='ns')
        self.placement_row = SetList(side, self.select, height=px(58))
        self.placement_row.pack(fill='x')
        ttk.Separator(side, orient='horizontal').pack(fill='x')
        header = ttk.Frame(side, style='Panel.TFrame', padding=(px(16), px(14), px(10), px(8)))
        header.pack(fill='x')
        ttk.Label(header, text='Reading sets', style='Subtitle.Panel.TLabel').pack(side='left')
        self.count = ttk.Label(header, text='', style='Muted.Panel.TLabel')
        self.count.pack(side='left', padx=(px(8), 0), pady=(px(2), 0))
        new = ttk.Button(header, text='New…', command=self.new_set)
        new.pack(side='right')
        Tooltip(new, 'Draw a new reading set from centre-line data sets')
        ttk.Separator(side, orient='horizontal').pack(fill='x')
        self.set_list = SetList(side, self.select)
        self.set_list.pack(fill='both', expand=True)
        ttk.Separator(side, orient='horizontal').pack(fill='x')
        ttk.Label(side, text='Observers read the blocks of a set by hand,\nblinded; the agreement shows how '
                             'well\nthe estimator matches them.', style='Faint.Panel.TLabel',
                  padding=(px(16), px(8))).pack(fill='x')
        tk.Frame(self.overview, bg=COLORS['border'], width=1).grid(row=0, column=1, sticky='ns')
        self.details = ScrollFrame(self.overview, background=COLORS['bg'])
        self.details.canvas.configure(bg=COLORS['bg'])
        self.details.body.configure(style='TFrame', padding=(px(24), px(18), px(24), px(24)))
        self.details.grid(row=0, column=2, sticky='nsew')
        self.overview.pack(fill='both', expand=True)

        self.reader = Reader(self, self)
        app.jobs.add_listener(self._jobs_changed)

    # ---------------------------------------------------------------- page protocol
    def show_recording(self, recording):
        pass

    def on_show(self):
        if self.reading_mode:
            self.reader.resume()
        else:
            self.refresh()

    def on_hide(self):
        if self.reading_mode:
            self.reader.pause()

    def handle_key(self, event) -> bool:
        if self.reading_mode:
            return self.reader.handle_key(event)
        return False

    def refresh(self):
        folder = self.app.folder.validation
        self.names = validation.list_reading_sets(folder)
        if self.selected not in self.names and self.selected != PLACEMENT:
            self.selected = self.names[0] if self.names else None
        rows = []
        for name in self.names:
            try:
                reading_set = validation.load_reading_set(folder, name)
                readings = reading_set.readings()
                observers = sorted({r.observer for r in readings})
                detail = f'{len(reading_set.items)} blocks  ·  ' + (
                    f'{len(readings)} reading{"s" if len(readings) != 1 else ""} by {", ".join(observers)}'
                    if readings else 'not read yet')
            except (OSError, ValueError, KeyError) as exc:
                detail = f'cannot be read: {exc}'
            rows.append((name, name, detail))
        self.count.configure(text=str(len(self.names)) if self.names else '')
        self.set_list.set_rows(rows, self.selected, 'No reading sets yet.')
        self.placement_row.set_rows([(PLACEMENT, 'Line placement', 'one capillary, several observers')],
                                    self.selected)
        self._load_selected()
        self._rebuild()

    def select(self, key):
        if key != self.selected:
            self.selected = key
            self.set_list.set_rows(self.set_list.rows, key, self.set_list.empty_text)
            self.placement_row.set_rows(self.placement_row.rows, key)
            self._load_selected()
            self._rebuild()

    def _load_selected(self):
        self.current = None
        self._load_error = ''
        if self.selected is not None and self.selected != PLACEMENT:
            try:
                self.current = validation.load_reading_set(self.app.folder.validation, self.selected)
                if not self.current.items:
                    raise ValueError('it holds no blocks')
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.current = None
                self._load_error = str(exc) or type(exc).__name__

    # ------------------------------------------------------------------- overview
    def _card(self, parent, title=None):
        outer = tk.Frame(parent, bg=COLORS['panel'], highlightthickness=1, highlightbackground=COLORS['border'], bd=0)
        outer.pack(fill='x', pady=(px(12), 0))
        inner = ttk.Frame(outer, style='Panel.TFrame', padding=(px(16), px(14)))
        inner.pack(fill='both', expand=True)
        if title:
            ttk.Label(inner, text=title.upper(), style='Section.Panel.TLabel').pack(anchor='w', pady=(0, px(8)))
        return inner

    def _line_sources(self):
        return [(recording.stem, name) for recording in self.app.recordings for name in recording.line_sets]

    def _rebuild(self):
        body = self.details.body
        for child in body.winfo_children():
            child.destroy()
        self._photos = []
        if self.selected == PLACEMENT:
            self._placement_view(body)
            return
        reading_set = self.current
        if reading_set is None and self.selected is not None:
            ttk.Label(body, text=self.selected, style='Title.TLabel').pack(anchor='w')
            ttk.Label(body, text=f'This reading set cannot be read: {self._load_error}', style='Danger.TLabel',
                      wraplength=px(900), justify='left').pack(anchor='w', pady=(px(8), 0))
            return
        if reading_set is None:
            self._empty_state(body)
            return
        header = ttk.Frame(body, style='TFrame')
        header.pack(fill='x')
        ttk.Label(header, text=reading_set.name, style='Title.TLabel').pack(side='left')
        ttk.Button(header, text='Show in folder', image=icon('folder', 14, COLORS['muted']), compound='left',
                   command=lambda: self.app.open_folder(os.path.join(reading_set.directory,
                                                                     validation.SET_FILE))).pack(side='right')
        record = reading_set.record
        sources = reading_set.source_summary()
        recordings = {source['recording'] for source in sources}
        sampling = record.get('sampling') or {}
        created = record.get('created', '')
        try:
            created = f'{datetime.datetime.fromisoformat(created):%d %b %Y, %H:%M}'
        except ValueError:
            pass
        resolved = sum(1 for item in reading_set.items if item.estimate.get('resolved'))
        first = reading_set.items[0]
        balanced = (' (half of each data set\'s blocks drawn from resolved ones, where it had enough)'
                    if sampling.get('balanced') else '')
        ttk.Label(body, style='Muted.TLabel', wraplength=px(900), justify='left', text=(
            f'{len(reading_set.items)} blocks of {first.frames / first.fps:.1f} s from {len(sources)} '
            f'centre-line data set{"s" if len(sources) != 1 else ""} of {len(recordings)} '
            f'recording{"s" if len(recordings) != 1 else ""}  ·  {resolved} resolved by the estimator when drawn'
            f'{balanced}  ·  drawn {created}  ·  seed {record.get("seed")}')).pack(anchor='w', pady=(px(4), 0))

        self._readings_card(body, reading_set)
        self._agreement_card(body, reading_set)
        self._sources_card(body, sources)

    def _empty_state(self, body):
        ttk.Label(body, text='Validation by observers', style='Title.TLabel').pack(anchor='w')
        card = self._card(body)
        sources = self._line_sources()
        text = ('A recording has no ground truth, so the centre-line velocity is checked against people: blocks '
                'of 3 s are drawn from your centre-line data sets into a reading set, every observer reads them by '
                'hand (blinded: without seeing where a block comes from or what the estimator found), and the '
                'agreement between the estimator and the observers, between observers, and between two sessions '
                'of one observer is computed with Bland-Altman limits of agreement, intraclass correlation and '
                'kappa.')
        ttk.Label(card, text=text, style='Panel.TLabel', wraplength=px(820), justify='left').pack(anchor='w')
        if sources:
            ttk.Label(card, text=f'{len(sources)} centre-line data set{"s" if len(sources) != 1 else ""} '
                                 'available.', style='Muted.Panel.TLabel').pack(anchor='w', pady=(px(10), 0))
            ttk.Button(card, text='New reading set…', style='Accent.TButton', command=self.new_set).pack(
                anchor='w', pady=(px(12), 0))
        else:
            ttk.Label(card, text='There are no centre-line data sets yet. Measure velocity along a centre line on a '
                                 'few capillaries first (Centre line page); a reading set is drawn from those '
                                 'data sets.', style='Warning.Panel.TLabel', wraplength=px(820),
                      justify='left').pack(anchor='w', pady=(px(10), 0))
            ttk.Button(card, text='Go to the Centre line page', command=lambda: self.app.show_page('line')).pack(
                anchor='w', pady=(px(12), 0))

    def _readings_card(self, body, reading_set):
        card = self._card(body, 'Readings')
        readings = reading_set.readings()
        total = len(reading_set.items)
        if not readings:
            ttk.Label(card, text='No one has read this set yet.', style='Muted.Panel.TLabel').pack(anchor='w')
        else:
            table = ttk.Frame(card, style='Panel.TFrame')
            table.pack(fill='x')
            for column, title in enumerate(('Observer', 'Session', 'Read', 'No clear streaks', 'Last saved', '')):
                ttk.Label(table, text=title, style='Faint.Panel.TLabel').grid(row=0, column=column, sticky='w',
                                                                              padx=(0, px(22)), pady=(0, px(4)))
            for row, reading in enumerate(readings, start=1):
                none = sum(1 for item in reading_set.items if reading.outcome(item.id) == validation.NO_STREAKS)
                try:
                    saved = f'{datetime.datetime.fromisoformat(reading.updated):%d %b %Y, %H:%M}'
                except ValueError:
                    saved = reading.updated or '–'
                values = (reading.observer, str(reading.session), f'{reading.read_count} of {total}', str(none), saved)
                for column, value in enumerate(values):
                    style = 'Bold.Panel.TLabel' if column == 0 else 'Panel.TLabel'
                    if column == 2:
                        style = 'Success.Panel.TLabel' if reading.is_complete else 'Warning.Panel.TLabel'
                    ttk.Label(table, text=value, style=style).grid(row=row, column=column, sticky='w',
                                                                  padx=(0, px(22)), pady=px(2))
                text = 'Look through' if reading.is_complete else 'Continue'
                ttk.Button(table, text=text, style='Small.Ghost.TButton',
                           command=partial(self.start_reading, reading.observer, reading.session)).grid(
                    row=row, column=5, sticky='w')
        start = ttk.Button(card, text='Start reading…', style='Accent.TButton', command=self.ask_reading)
        start.pack(anchor='w', pady=(px(12), 0))
        Tooltip(start, 'Read the blocks as an observer: a new observer, a new session, or continue one')

    def _compute_row(self, card, command, summary_path):
        actions = ttk.Frame(card, style='Panel.TFrame')
        actions.pack(fill='x', pady=(px(10), 0))
        self.compute_button = ttk.Button(actions, text='Compute agreement', command=command)
        self.compute_button.pack(side='left')
        if os.path.exists(summary_path):
            ttk.Button(actions, text='Show files', style='Ghost.TButton',
                       command=lambda: self.app.open_folder(summary_path)).pack(side='left', padx=(px(8), 0))
            try:
                when = datetime.datetime.fromtimestamp(os.path.getmtime(summary_path))
                ttk.Label(actions, text=f'last computed {when:%d %b %Y, %H:%M}', style='Faint.Panel.TLabel').pack(
                    side='left', padx=(px(12), 0))
            except OSError:
                pass
        self._jobs_changed()

    def _plots(self, card, files, title):
        cells = ttk.Frame(card, style='Panel.TFrame')
        cells.pack(fill='x', pady=(px(14), 0))
        for column, role in enumerate(('bland_altman', 'scatter')):
            path = files[role]
            if not os.path.exists(path):
                continue
            try:
                photo = ImageTk.PhotoImage(_thumbnail(path, px(THUMB_WIDTH)))
            except OSError:
                continue
            self._photos.append(photo)
            cell = ttk.Frame(cells, style='Panel.TFrame')
            cell.grid(row=0, column=column, sticky='nw', padx=(0, px(16)))
            label = tk.Label(cell, image=photo, bd=0, cursor='hand2', highlightthickness=1,
                             highlightbackground=COLORS['border'])
            label.pack()
            label.bind('<Button-1>', lambda e, p=path, r=role: ImageViewer(
                self, p, title=f'{PLOT_TITLES[r]}  ·  {title}', on_open_folder=lambda: self.app.open_folder(p)))
            Tooltip(label, 'Click to enlarge')
            ttk.Label(cell, text=PLOT_TITLES[role], style='Faint.Panel.TLabel').pack(anchor='w', pady=(px(3), 0))

    def _agreement_card(self, body, reading_set):
        card = self._card(body, 'Agreement')
        ttk.Label(card, style='Muted.Panel.TLabel', wraplength=px(900), justify='left', text=(
            'Measures every block again with the current estimator and compares it with every reading, the '
            'observers with each other, and each observer\'s sessions with each other. It shows the estimator\'s '
            'results, so compute it once everyone has finished reading.')).pack(anchor='w')
        files = reading_set.report_files()
        self._compute_row(card, self.compute_agreement, files['summary'])
        comparisons = validation.load_comparisons(reading_set)
        if comparisons is None:
            return
        if not comparisons:
            ttk.Label(card, text='Nothing to compare yet: no block has been read.', style='Faint.Panel.TLabel').pack(
                anchor='w', pady=(px(10), 0))
            return
        self._comparison_table(card, comparisons)
        self._plots(card, files, reading_set.name)

    def _placement_view(self, body):
        ttk.Label(body, text='Line placement', style='Title.TLabel').pack(anchor='w')
        ttk.Label(body, style='Muted.TLabel', wraplength=px(900), justify='left', text=(
            'How much a velocity depends on who draws the line: the same capillary measured over the same frames by '
            'different observers, or twice by one. Centre-line data sets are matched automatically: lines on the '
            f'same recording that run along each other (at least {placement.MIN_LINE_OVERLAP:.0%} of one line within '
            f'{placement.MATCH_PX:g} px of the other) over frame ranges sharing at least '
            f'{placement.MIN_FRAME_OVERLAP:.0%} of their frames. The observer of a data set is the one entered next '
            'to its name when it was measured.')).pack(anchor='w', pady=(px(4), 0))
        measurements = placement.load_measurements(self.app.folder.statistics, self._line_sources())
        without = sum(1 for m in measurements if not m.observer)
        observers = sorted({m.observer for m in measurements if m.observer})
        text = (f'{len(measurements)} centre-line data set{"s" if len(measurements) != 1 else ""}'
                + (f' by {", ".join(observers)}' if observers else '')
                + (f'; {without} without an observer, which take part in no comparison' if without else '') + '.')
        ttk.Label(body, text=text, style='Muted.TLabel', wraplength=px(900), justify='left').pack(
            anchor='w', pady=(px(6), 0))

        report_dir = os.path.join(self.app.folder.validation, placement.REPORT_DIR)
        files = {role: os.path.join(report_dir, name) for role, name in placement.REPORT_FILES.items()}
        card = self._card(body, 'Agreement')
        ttk.Label(card, style='Muted.Panel.TLabel', wraplength=px(900), justify='left', text=(
            'Compares the median velocity of each capillary between every two observers, and between the first and '
            'second measurement of one observer. Compute it again after new measurements.')).pack(anchor='w')
        self._compute_row(card, self.compute_placement, files['summary'])
        comparisons = validation.read_comparisons(files['summary'])
        if comparisons is not None:
            if comparisons:
                self._comparison_table(card, comparisons, unit='Capillaries', readability=False)
                self._plots(card, files, 'line placement')
            else:
                ttk.Label(card, text='Nothing to compare: no capillary was measured by two observers, or twice by '
                                     'one.', style='Faint.Panel.TLabel').pack(anchor='w', pady=(px(10), 0))
        try:
            rows = pd.read_csv(files['measurements']) if os.path.exists(files['measurements']) else None
        except pd.errors.EmptyDataError:
            rows = pd.DataFrame()                               # computed, but nothing was measured twice
        except (OSError, ValueError):
            rows = None
        if rows is None:
            return
        card = self._card(body, 'Capillaries measured more than once')
        if not len(rows):
            ttk.Label(card, text='None found.', style='Muted.Panel.TLabel').pack(anchor='w')
            return
        table = ttk.Frame(card, style='Panel.TFrame')
        table.pack(fill='x')
        for column, title in enumerate(('Capillary', 'Recording', 'Observer', 'Data set', 'Frames',
                                        'Median (mm/s)', 'Resolved')):
            ttk.Label(table, text=title, style='Faint.Panel.TLabel').grid(row=0, column=column, sticky='w',
                                                                          padx=(0, px(18)), pady=(0, px(4)))
        previous = None
        for row, record in enumerate(rows.to_dict('records'), start=1):
            reversed_note = '  (line the other way: sign reversed)' if record.get('reversed') else ''
            values = (record['capillary'] if record['capillary'] != previous else '', record['recording'],
                      record.get('observer') if isinstance(record.get('observer'), str) else '–',
                      f'{record["dataset"]}{reversed_note}',
                      f'{int(record["first_frame"])}–{int(record["last_frame"])}',
                      _signed(record.get('median_velocity_mm_s')), _percent(record.get('resolved_fraction')))
            previous = record['capillary']
            for column, value in enumerate(values):
                ttk.Label(table, text=value, style='Bold.Panel.TLabel' if column == 0 else 'Panel.TLabel').grid(
                    row=row, column=column, sticky='w', padx=(0, px(18)), pady=px(1))

    def _table(self, card, title, headings):
        ttk.Label(card, text=title, style='Bold.Panel.TLabel').pack(anchor='w', pady=(px(16), px(4)))
        table = ttk.Frame(card, style='Panel.TFrame')
        table.pack(fill='x')
        for column, (heading, tip) in enumerate(headings):
            label = ttk.Label(table, text=heading, style='Faint.Panel.TLabel')
            label.grid(row=0, column=column, sticky='w', padx=(0, px(16)), pady=(0, px(2)))
            if tip:
                Tooltip(label, tip, wrap=300)
        return table

    @staticmethod
    def _cell(table, row, column, text, below=None, bold=False):
        cell = ttk.Frame(table, style='Panel.TFrame')
        cell.grid(row=row, column=column, sticky='nw', padx=(0, px(16)), pady=px(3))
        ttk.Label(cell, text=text, style='Bold.Panel.TLabel' if bold else 'Panel.TLabel',
                  wraplength=px(220) if column == 0 else 0, justify='left').pack(anchor='w')
        if below and below != '–':
            ttk.Label(cell, text=below, style='Faint.Panel.TLabel').pack(anchor='w')

    def _comparison_table(self, card, comparisons, unit='Blocks', readability=True):
        things = unit.lower()
        velocity = self._table(card, 'Velocity (mm/s; differences are the first minus the second)', (
            ('Comparison', None),
            (unit, f'{unit} with a velocity from both' + (', of the blocks both have judged' if readability else '')),
            ('Bias', 'Mean difference, with its 95% confidence interval below'),
            ('95% limits of agreement', 'Bias ± 1.96 SD of the differences: 95% of the differences lie between them'),
            ('As ratios', 'The limits of agreement on a log scale: how many percent the first lies above or below the '
                          f'second, for 95% of {things}'),
            ('ICC (A,1)', 'Intraclass correlation, absolute agreement, single measurement, with its 95% confidence '
                          'interval below'),
            ('Same direction', f'{unit} where both see the flow go the same way along the line')))
        readable = None
        if readability:
            readable = self._table(card, 'Whether a block can be read at all (a velocity resolved, or lines drawn)', (
                ('Comparison', None),
                ('Judged by both', 'Blocks both have judged (an observer may not have finished)'),
                ('Both', 'Both read a velocity'),
                ('Only the first', 'Only the first named read a velocity'),
                ('Only the second', 'Only the second named read a velocity'),
                ('Neither', 'Neither read a velocity'),
                ('Agreement', 'Share of blocks judged the same'),
                ('Kappa', 'Cohen\'s kappa: agreement beyond chance, with its 95% confidence interval below')))
        notes = []
        row = 0
        for comparison in comparisons:
            row += 1
            name = comparison.get('comparison', '')
            pairs, judged = comparison.get('pairs'), comparison.get('judged_by_both')
            blocks = f'{int(pairs)} of {int(judged)}' if _finite(pairs) and _finite(judged) else \
                (str(int(pairs)) if _finite(pairs) else '–')
            self._cell(velocity, row, 0, name, bold=True)
            self._cell(velocity, row, 1, blocks)
            self._cell(velocity, row, 2, _signed(comparison.get('bias')),
                       _between(comparison.get('bias_ci_low'), comparison.get('bias_ci_high')))
            self._cell(velocity, row, 3, _between(comparison.get('loa_low'), comparison.get('loa_high')))
            self._cell(velocity, row, 4, _ratio_limits(comparison.get('ratio_loa_low'),
                                                       comparison.get('ratio_loa_high')))
            self._cell(velocity, row, 5, _with_ci(comparison.get('icc_agreement'), None, None),
                       _between(comparison.get('icc_agreement_ci_low'), comparison.get('icc_agreement_ci_high'), 2)
                       .replace('+', ''))
            self._cell(velocity, row, 6, _percent(comparison.get('same_direction')))
            if readable is not None and _finite(judged):
                self._cell(readable, row, 0, name, bold=True)
                for column, key in enumerate(('judged_by_both', 'readable_both', 'readable_first_only',
                                              'readable_second_only', 'readable_neither'), start=1):
                    value = comparison.get(key)
                    self._cell(readable, row, column, str(int(value)) if _finite(value) else '–')
                self._cell(readable, row, 6, _percent(comparison.get('readable_agreement')))
                self._cell(readable, row, 7, _with_ci(comparison.get('kappa'), None, None),
                           _between(comparison.get('kappa_ci_low'), comparison.get('kappa_ci_high'), 2)
                           .replace('+', ''))
            coefficient = comparison.get('repeatability_coefficient')
            if _finite(coefficient):
                notes.append(f'{name}: repeatability coefficient {coefficient:.4f} mm/s (95% of repeated readings of '
                             'a block differ by less).')
            if _finite(comparison.get('slope_ci_low')) and (comparison['slope_ci_low'] > 0 or
                                                            comparison['slope_ci_high'] < 0):
                notes.append(f'{name}: the difference changes with the velocity (slope {comparison["slope"]:+.2f} '
                             'of the differences on the means); read the limits as ratios.')
        for note in notes:
            ttk.Label(card, text=note, style='Muted.Panel.TLabel', wraplength=px(900), justify='left').pack(
                anchor='w', pady=(px(6), 0))

    def _sources_card(self, body, sources):
        card = self._card(body, 'Blocks drawn from')
        table = ttk.Frame(card, style='Panel.TFrame')
        table.pack(fill='x')
        for column, title in enumerate(('Recording', 'Data set', 'Drawn', 'Of them resolved', 'Blocks measured')):
            ttk.Label(table, text=title, style='Faint.Panel.TLabel').grid(row=0, column=column, sticky='w',
                                                                          padx=(0, px(22)), pady=(0, px(4)))
        for row, source in enumerate(sources, start=1):
            values = (source.get('recording', ''), source.get('dataset', ''), str(source.get('blocks_drawn', '')),
                      str(source.get('resolved_drawn', '')),
                      f'{source.get("blocks_measured", "")} ({source.get("blocks_resolved", "")} resolved)')
            for column, value in enumerate(values):
                ttk.Label(table, text=value, style='Panel.TLabel').grid(row=row, column=column, sticky='w',
                                                                       padx=(0, px(22)), pady=px(1))

    # -------------------------------------------------------------------- actions
    def new_set(self):
        sources = self._line_sources()
        if not sources:
            show_error(self, 'No centre-line data sets', 'A reading set is drawn from centre-line data sets. '
                       'Measure velocity along a centre line on a few capillaries first.')
            return
        options = NewReadingSetDialog(self, sources, self.names).show()
        if options is None:
            return
        name = options['name']
        work = partial(tasks.create_reading_set, folder=self.app.folder, name=name, sources=options['sources'],
                       blocks_per_dataset=options['blocks_per_dataset'], balanced=options['balanced'],
                       seed=options['seed'], mm_per_pixel=self.app.settings.mm_per_pixel)

        def done(created):
            self.app.set_status(f'Reading set "{created}" drawn.')
            self.selected = created
            self.refresh()

        def failed(exc):
            show_error(self, 'The reading set could not be made', str(exc) or type(exc).__name__,
                       'Nothing was written. The details are in capillaroscopy.log.')

        job = self.app.jobs.submit(f'Reading set · {name}', work, lane='analysis', key=('reading set', name),
                                   on_done=done, on_error=failed)
        if job is None:
            self.app.set_status('That reading set is already being drawn.')
        else:
            self.app.set_status(f'Drawing the reading set "{name}"…')

    def ask_reading(self):
        if self.current is None:
            return
        answer = StartReadingDialog(self, self.current, validation.normalize_observer(
            self.app.observer_var.get())).show()
        if answer is None:
            return
        observer, session = answer
        self.app.remember_observer(observer)
        self.start_reading(observer, session)

    def start_reading(self, observer, session):
        if self.current is None:
            return
        try:
            reading = self.current.open_reading(observer, session)
            self.current.block(reading.order[0])               # fail here, not in the middle, if blocks are missing
        except (OSError, ValueError, KeyError) as exc:
            show_error(self, 'The reading cannot be opened', str(exc))
            return
        self.reading_mode = True
        self.overview.pack_forget()
        self.reader.pack(fill='both', expand=True)
        self.reader.start(self.current, reading)
        self.app.set_status(f'Reading "{self.current.name}" as {observer}, session {session}.')

    def leave_reading(self):
        self.reading_mode = False
        self.reader.pack_forget()
        self.overview.pack(fill='both', expand=True)
        self.refresh()

    def compute_agreement(self):
        reading_set = self.current
        if reading_set is None:
            return
        name = reading_set.name

        def done(result):
            self._agreement_job = None
            count = len(result['comparisons'])
            self.app.set_status(f'Agreement of "{name}" computed: {count} comparison{"s" if count != 1 else ""}.')
            if self.current is not None and self.current.name == name and not self.reading_mode:
                self._rebuild()

        def failed(exc):
            self._agreement_job = None
            self._jobs_changed()
            show_error(self, 'The agreement could not be computed', str(exc) or type(exc).__name__,
                       'The details are in capillaroscopy.log.')

        self._agreement_job = self.app.jobs.submit(
            f'Agreement · {name}', partial(tasks.agreement_report, folder=self.app.folder, name=name),
            lane='analysis', key=('agreement', name), on_done=done, on_error=failed,
            on_cancel=lambda: setattr(self, '_agreement_job', None))
        self._jobs_changed()

    def compute_placement(self):
        def done(result):
            self._agreement_job = None
            count = result['capillaries']
            self.app.set_status(f'Line placement: {count} capillar{"ies" if count != 1 else "y"} measured more than '
                                f'once, among {result["measurements"]} centre-line data sets.')
            if self.selected == PLACEMENT and not self.reading_mode:
                self._rebuild()

        def failed(exc):
            self._agreement_job = None
            self._jobs_changed()
            show_error(self, 'The comparison could not be computed', str(exc) or type(exc).__name__,
                       'The details are in capillaroscopy.log.')

        self._agreement_job = self.app.jobs.submit(
            'Line placement', partial(tasks.placement_report, folder=self.app.folder, sources=self._line_sources()),
            lane='analysis', key=('placement',), on_done=done, on_error=failed,
            on_cancel=lambda: setattr(self, '_agreement_job', None))
        self._jobs_changed()

    def _jobs_changed(self):
        button = getattr(self, 'compute_button', None)
        if button is None:
            return
        try:
            running = self._agreement_job is not None and not self._agreement_job.finished
            button.state(['disabled'] if running else ['!disabled'])
            button.configure(text='Computing…' if running else 'Compute agreement')
        except tk.TclError:
            pass                                               # the card was rebuilt
