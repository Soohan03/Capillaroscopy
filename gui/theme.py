"""Colours, fonts, ttk styles and the small icons drawn at runtime.

Everything visual is defined here, so the look can be changed in one place.
Icons are painted with Pillow at the screen's scale instead of shipped as image
files, which keeps them sharp on high-DPI displays.
"""
import math
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

COLORS = {
    'bg': '#EAEEF3',            # window background behind the panels
    'panel': '#FFFFFF',         # panels and cards
    'panel_alt': '#F5F7FA',     # hovered rows, inset areas
    'border': '#DDE2E9',
    'border_strong': '#C2CAD5',
    'text': '#16202C',
    'muted': '#5A6676',
    'faint': '#8C96A4',
    'accent': '#2463EB',
    'accent_hover': '#1D53D2',
    'accent_pressed': '#1946B4',
    'accent_soft': '#E3EBFD',
    'accent_disabled': '#A7BCEF',
    'header': '#141B25',
    'header_hover': '#212B39',
    'header_active': '#2C394B',
    'header_text': '#EEF2F7',
    'header_muted': '#98A4B4',
    'video_bg': '#0C1016',
    'overlay_bg': '#1A2330',
    'overlay_text': '#F1F4F8',
    'success': '#1E874B',
    'success_soft': '#E1F3E8',
    'warning': '#A86200',
    'warning_soft': '#FCF0D6',
    'danger': '#C42B2B',
    'danger_hover': '#A82020',
    'danger_soft': '#FBE3E3',
    'box1': '#FF9F1C',          # box 1, downstream (orange)
    'box2': '#29B2FF',          # box 2, upstream (sky blue)
    'region': '#3DDC84',        # Flow tab region
    'marker': '#E5484D',        # time points, red like the lines in the report
    'record': '#E5484D',
}

# Correlation quality bands, the same edges and colours the report uses for its dots.
QUALITY_BANDS = (
    (0.25, 'poor', '#D62F2F'),
    (0.50, 'fair', '#E08A00'),
    (0.75, 'good', '#2463EB'),
    (1.01, 'very good', '#1E874B'),
)

FONTS = {}
UI_SCALE = 1.0


def px(value):
    """`value` pixels at 96 dpi, scaled to the screen."""
    return int(round(value * UI_SCALE))


def quality_of(r):
    """``(label, colour)`` of a correlation coefficient."""
    if r is None or not math.isfinite(r):
        return 'n/a', COLORS['faint']
    for edge, label, color in QUALITY_BANDS:
        if r < edge:
            return label, color
    return QUALITY_BANDS[-1][1], QUALITY_BANDS[-1][2]


def _pick(families, candidates, fallback):
    for name in candidates:
        if name in families:
            return name
    return fallback


def apply(root):
    """Set up fonts and ttk styles for `root`. Call once, before building widgets."""
    global UI_SCALE
    UI_SCALE = max(1.0, float(root.tk.call('tk', 'scaling')) / (96 / 72))

    families = set(tkfont.families(root))
    ui = _pick(families, ('Segoe UI', 'Ubuntu', 'Cantarell', 'Noto Sans', 'DejaVu Sans', 'Helvetica Neue',
                          'Helvetica', 'Arial'), tkfont.nametofont('TkDefaultFont').actual('family'))
    mono = _pick(families, ('Cascadia Mono', 'Consolas', 'Ubuntu Mono', 'DejaVu Sans Mono', 'Menlo',
                            'Courier New'), 'TkFixedFont')
    FONTS.update({
        'base': (ui, 10),
        'small': (ui, 9),
        'tiny': (ui, 8),
        'bold': (ui, 10, 'bold'),
        'small_bold': (ui, 9, 'bold'),
        'section': (ui, 8, 'bold'),
        'subtitle': (ui, 11, 'bold'),
        'title': (ui, 13, 'bold'),
        'big': (ui, 18, 'bold'),
        'mono': (mono, 10),
        'mono_small': (mono, 9),
        'mono_big': (mono, 12, 'bold'),
        'nav': (ui, 10, 'bold'),
        'brand': (ui, 12, 'bold'),
    })
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont', 'TkCaptionFont',
                 'TkSmallCaptionFont', 'TkIconFont', 'TkTooltipFont'):
        try:
            tkfont.nametofont(name).configure(family=ui, size=10 if name != 'TkSmallCaptionFont' else 9)
        except tk.TclError:
            pass

    c = COLORS
    root.configure(bg=c['bg'])
    root.option_add('*Menu.background', c['panel'])
    root.option_add('*Menu.foreground', c['text'])
    root.option_add('*Menu.activeBackground', c['accent_soft'])
    root.option_add('*Menu.activeForeground', c['text'])
    root.option_add('*Menu.disabledForeground', c['faint'])
    root.option_add('*Menu.relief', 'flat')
    root.option_add('*Menu.borderWidth', 1)
    root.option_add('*Menu.activeBorderWidth', 0)
    root.option_add('*Menu.font', FONTS['base'])
    root.option_add('*TCombobox*Listbox.background', c['panel'])
    root.option_add('*TCombobox*Listbox.foreground', c['text'])
    root.option_add('*TCombobox*Listbox.selectBackground', c['accent_soft'])
    root.option_add('*TCombobox*Listbox.selectForeground', c['text'])
    root.option_add('*TCombobox*Listbox.font', FONTS['base'])

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=c['bg'], foreground=c['text'], font=FONTS['base'],
                    bordercolor=c['border_strong'], lightcolor=c['panel'], darkcolor=c['panel'],
                    troughcolor=c['panel_alt'], focuscolor=c['accent'], selectbackground=c['accent'],
                    selectforeground='#FFFFFF', insertcolor=c['text'], relief='flat')
    style.map('.', foreground=[('disabled', c['faint'])])

    # frames
    style.configure('TFrame', background=c['bg'])
    style.configure('Panel.TFrame', background=c['panel'])
    style.configure('Alt.TFrame', background=c['panel_alt'])
    style.configure('Header.TFrame', background=c['header'])
    style.configure('Card.TFrame', background=c['panel'], bordercolor=c['border'], lightcolor=c['panel'],
                    darkcolor=c['panel'], relief='solid', borderwidth=1)

    # labels
    style.configure('TLabel', background=c['bg'], foreground=c['text'])
    style.configure('Muted.TLabel', foreground=c['muted'], font=FONTS['small'])
    style.configure('Subtitle.TLabel', font=FONTS['subtitle'])
    style.configure('Title.TLabel', font=FONTS['title'])
    for area, background in (('Panel', c['panel']), ('Alt', c['panel_alt'])):
        style.configure(f'{area}.TLabel', background=background, foreground=c['text'])
        style.configure(f'Muted.{area}.TLabel', foreground=c['muted'], font=FONTS['small'])
        style.configure(f'Faint.{area}.TLabel', foreground=c['faint'], font=FONTS['small'])
        style.configure(f'Section.{area}.TLabel', foreground=c['muted'], font=FONTS['section'])
        style.configure(f'Bold.{area}.TLabel', font=FONTS['bold'])
        style.configure(f'Subtitle.{area}.TLabel', font=FONTS['subtitle'])
        style.configure(f'Title.{area}.TLabel', font=FONTS['title'])
        style.configure(f'Big.{area}.TLabel', font=FONTS['big'])
        style.configure(f'Mono.{area}.TLabel', font=FONTS['mono'])
        style.configure(f'MonoSmall.{area}.TLabel', font=FONTS['mono_small'], foreground=c['muted'])
        style.configure(f'Success.{area}.TLabel', foreground=c['success'], font=FONTS['small'])
        style.configure(f'Warning.{area}.TLabel', foreground=c['warning'], font=FONTS['small'])
        style.configure(f'Danger.{area}.TLabel', foreground=c['danger'], font=FONTS['small'])
    style.configure('Header.TLabel', background=c['header'], foreground=c['header_text'])
    style.configure('Brand.Header.TLabel', font=FONTS['brand'])
    style.configure('Muted.Header.TLabel', foreground=c['header_muted'], font=FONTS['small'])
    style.configure('Status.TLabel', background=c['panel'], foreground=c['muted'], font=FONTS['small'])

    # buttons
    style.configure('TButton', background=c['panel'], foreground=c['text'], bordercolor=c['border_strong'],
                    lightcolor=c['panel'], darkcolor=c['panel'], focuscolor=c['panel'],
                    padding=(px(12), px(5)), anchor='center')
    style.map('TButton',
              background=[('disabled', c['panel']), ('pressed', c['border']), ('active', c['panel_alt'])],
              lightcolor=[('disabled', c['panel']), ('pressed', c['border']), ('active', c['panel_alt'])],
              darkcolor=[('disabled', c['panel']), ('pressed', c['border']), ('active', c['panel_alt'])],
              bordercolor=[('disabled', c['border']), ('focus', c['accent'])],
              foreground=[('disabled', c['faint'])])

    def filled(name, base, hover, pressed, disabled, text='#FFFFFF'):
        style.configure(name, background=base, foreground=text, bordercolor=base, lightcolor=base,
                        darkcolor=base, focuscolor=base, font=FONTS['bold'])
        state_colors = [('disabled', disabled), ('pressed', pressed), ('active', hover)]
        style.map(name, background=state_colors, lightcolor=state_colors, darkcolor=state_colors,
                  bordercolor=state_colors, foreground=[('disabled', '#FFFFFF')])

    filled('Accent.TButton', c['accent'], c['accent_hover'], c['accent_pressed'], c['accent_disabled'])
    filled('Danger.TButton', c['danger'], c['danger_hover'], c['danger_hover'], '#E9A9A9')
    filled('Record.TButton', c['record'], c['danger_hover'], c['danger_hover'], '#E9A9A9')

    style.configure('Ghost.TButton', background=c['panel'], bordercolor=c['panel'], lightcolor=c['panel'],
                    darkcolor=c['panel'], padding=(px(6), px(4)))
    ghost = [('disabled', c['panel']), ('pressed', c['border']), ('active', c['panel_alt'])]
    style.map('Ghost.TButton', background=ghost, lightcolor=ghost, darkcolor=ghost,
              bordercolor=[('disabled', c['panel']), ('pressed', c['border']), ('active', c['border'])])
    style.configure('Small.Ghost.TButton', font=FONTS['small'], padding=(px(6), px(2)))
    style.configure('Link.Ghost.TButton', foreground=c['accent'], font=FONTS['small'], padding=(px(4), px(2)))

    style.configure('Header.TButton', background=c['header'], foreground=c['header_text'],
                    bordercolor=c['header'], lightcolor=c['header'], darkcolor=c['header'],
                    focuscolor=c['header'], padding=(px(10), px(6)))
    header = [('pressed', c['header_active']), ('active', c['header_hover'])]
    style.map('Header.TButton', background=header, lightcolor=header, darkcolor=header, bordercolor=header)

    # navigation tabs in the header and segmented toggles in panels (radio buttons drawn as buttons)
    style.configure('Nav.Toolbutton', background=c['header'], foreground=c['header_muted'],
                    bordercolor=c['header'], lightcolor=c['header'], darkcolor=c['header'],
                    focuscolor=c['header'], padding=(px(16), px(8)), font=FONTS['nav'], anchor='center')
    style.map('Nav.Toolbutton',
              background=[('selected', c['header_active']), ('active', c['header_hover'])],
              lightcolor=[('selected', c['header_active']), ('active', c['header_hover'])],
              darkcolor=[('selected', c['header_active']), ('active', c['header_hover'])],
              bordercolor=[('selected', c['header_active']), ('active', c['header_hover'])],
              foreground=[('selected', c['header_text']), ('active', c['header_text'])])
    style.configure('Seg.Toolbutton', background=c['panel_alt'], foreground=c['muted'],
                    bordercolor=c['border'], lightcolor=c['panel_alt'], darkcolor=c['panel_alt'],
                    focuscolor=c['panel_alt'], padding=(px(10), px(4)), font=FONTS['small_bold'],
                    anchor='center')
    style.map('Seg.Toolbutton',
              background=[('selected', c['accent_soft']), ('active', c['panel'])],
              lightcolor=[('selected', c['accent_soft']), ('active', c['panel'])],
              darkcolor=[('selected', c['accent_soft']), ('active', c['panel'])],
              bordercolor=[('selected', c['accent'])],
              foreground=[('selected', c['accent']), ('active', c['text'])])

    # entry fields
    for name in ('TEntry', 'TSpinbox', 'TCombobox'):
        style.configure(name, fieldbackground=c['panel'], foreground=c['text'], bordercolor=c['border_strong'],
                        lightcolor=c['panel'], darkcolor=c['panel'], padding=(px(6), px(4)),
                        insertcolor=c['text'], arrowcolor=c['muted'], arrowsize=px(11))
        style.map(name,
                  bordercolor=[('invalid', c['danger']), ('focus', c['accent'])],
                  lightcolor=[('invalid', c['danger_soft']), ('focus', c['accent_soft'])],
                  fieldbackground=[('readonly', c['panel']), ('disabled', c['panel_alt'])],
                  foreground=[('disabled', c['faint'])])

    # check and radio buttons on panels
    for name in ('Panel.TCheckbutton', 'Panel.TRadiobutton'):
        style.configure(name, background=c['panel'], foreground=c['text'], indicatorbackground=c['panel'],
                        indicatorforeground='#FFFFFF', upperbordercolor=c['border_strong'],
                        lowerbordercolor=c['border_strong'], indicatormargin=(0, 0, px(6), 0),
                        focuscolor=c['panel'])
        style.map(name,
                  background=[('active', c['panel'])],
                  indicatorbackground=[('selected', c['accent']), ('active', c['panel_alt'])],
                  upperbordercolor=[('selected', c['accent'])],
                  lowerbordercolor=[('selected', c['accent'])])

    # progress bars
    style.configure('Thin.Horizontal.TProgressbar', thickness=px(6), background=c['accent'],
                    troughcolor=c['border'], bordercolor=c['border'], lightcolor=c['accent'],
                    darkcolor=c['accent'])

    # slim scrollbars without arrows
    for orient in ('Vertical', 'Horizontal'):
        name = f'Slim.{orient}.TScrollbar'
        style.layout(name, [(f'{orient}.Scrollbar.trough', {
            'sticky': 'ns' if orient == 'Vertical' else 'ew',
            'children': [(f'{orient}.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})]})])
        style.configure(name, background=c['border_strong'], troughcolor=c['panel'], bordercolor=c['panel'],
                        lightcolor=c['border_strong'], darkcolor=c['border_strong'], gripcount=0,
                        arrowsize=px(9))
        style.map(name, background=[('active', c['faint'])], lightcolor=[('active', c['faint'])],
                  darkcolor=[('active', c['faint'])])

    style.configure('TSeparator', background=c['border'])
    style.configure('TPanedwindow', background=c['bg'])
    style.configure('Sash', sashthickness=px(5), gripcount=0, background=c['bg'], lightcolor=c['bg'],
                    darkcolor=c['bg'], bordercolor=c['bg'])
    return style


# ---------------------------------------------------------------------------- icons

_ICON_CACHE = {}


def _hex_to_rgba(color, alpha=255):
    color = color.lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def _draw_icon(d, name, S, fill):
    """Paint icon `name` on an S x S canvas in coordinates 0..100."""
    def p(*points):
        return [(x * S / 100, y * S / 100) for x, y in points]

    def rect(x0, y0, x1, y1, r=0):
        d.rounded_rectangle(p((x0, y0), (x1, y1)), radius=r * S / 100, fill=fill)

    def line(points, width):
        d.line(p(*points), fill=fill, width=max(1, int(width * S / 100)), joint='curve')

    if name == 'play':
        d.polygon(p((30, 18), (30, 82), (82, 50)), fill=fill)
    elif name == 'pause':
        rect(26, 20, 42, 80, 3)
        rect(58, 20, 74, 80, 3)
    elif name == 'prev_frame':
        d.polygon(p((66, 22), (66, 78), (26, 50)), fill=fill)
        rect(70, 22, 80, 78, 2)
    elif name == 'next_frame':
        d.polygon(p((34, 22), (34, 78), (74, 50)), fill=fill)
        rect(20, 22, 30, 78, 2)
    elif name == 'back':
        d.polygon(p((50, 24), (50, 76), (14, 50)), fill=fill)
        d.polygon(p((86, 24), (86, 76), (50, 50)), fill=fill)
    elif name == 'forward':
        d.polygon(p((14, 24), (14, 76), (50, 50)), fill=fill)
        d.polygon(p((50, 24), (50, 76), (86, 50)), fill=fill)
    elif name == 'to_start':
        rect(14, 22, 24, 78, 2)
        d.polygon(p((56, 24), (56, 76), (26, 50)), fill=fill)
        d.polygon(p((86, 24), (86, 76), (56, 50)), fill=fill)
    elif name == 'to_end':
        rect(76, 22, 86, 78, 2)
        d.polygon(p((44, 24), (44, 76), (74, 50)), fill=fill)
        d.polygon(p((14, 24), (14, 76), (44, 50)), fill=fill)
    elif name == 'record':
        d.ellipse(p((20, 20), (80, 80)), fill=fill)
    elif name == 'stop':
        rect(24, 24, 76, 76, 8)
    elif name == 'flag':
        rect(26, 12, 33, 90, 2)
        d.polygon(p((33, 14), (80, 28), (33, 46)), fill=fill)
    elif name == 'fit':
        for (x, y, dx, dy) in ((14, 14, 1, 1), (86, 14, -1, 1), (14, 86, 1, -1), (86, 86, -1, -1)):
            line([(x, y + 26 * dy), (x, y), (x + 26 * dx, y)], 9)
    elif name == 'plus':
        rect(44, 18, 56, 82, 3)
        rect(18, 44, 82, 56, 3)
    elif name == 'minus':
        rect(18, 44, 82, 56, 3)
    elif name == 'close':
        line([(24, 24), (76, 76)], 11)
        line([(76, 24), (24, 76)], 11)
    elif name == 'check':
        line([(18, 52), (40, 74), (84, 28)], 12)
    elif name == 'swap':
        line([(18, 34), (78, 34)], 9)
        d.polygon(p((66, 18), (88, 34), (66, 50)), fill=fill)
        line([(82, 66), (22, 66)], 9)
        d.polygon(p((34, 50), (12, 66), (34, 82)), fill=fill)
    elif name == 'folder':
        d.polygon(p((10, 24), (40, 24), (48, 32), (90, 32), (90, 80), (10, 80)), fill=fill)
    elif name == 'refresh':
        d.arc(p((18, 18), (82, 82)), start=40, end=330, fill=fill, width=int(10 * S / 100))
        d.polygon(p((66, 10), (90, 30), (62, 40)), fill=fill)
    elif name == 'trash':
        rect(20, 22, 80, 30, 2)
        rect(40, 12, 60, 22, 2)
        d.polygon(p((26, 34), (74, 34), (69, 88), (31, 88)), fill=fill)
    elif name == 'gear':
        cx = cy = 50
        points = []
        for k in range(16):
            angle = math.pi * 2 * k / 16
            radius = 44 if k % 2 == 0 else 33
            points.append((cx + radius * math.cos(angle + math.pi / 16), cy + radius * math.sin(angle + math.pi / 16)))
        d.polygon(p(*points), fill=fill)
        d.ellipse(p((36, 36), (64, 64)), fill=(0, 0, 0, 0))
    elif name == 'search':
        d.ellipse(p((14, 14), (64, 64)), outline=fill, width=int(10 * S / 100))
        line([(58, 58), (86, 86)], 12)
    elif name == 'more':
        for x in (22, 50, 78):
            d.ellipse(p((x - 8, 42), (x + 8, 58)), fill=fill)
    elif name == 'warning':
        d.polygon(p((50, 10), (92, 86), (8, 86)), fill=fill)
        d.rectangle(p((46, 34), (54, 62)), fill=(255, 255, 255, 255))
        d.ellipse(p((45, 68), (55, 78)), fill=(255, 255, 255, 255))
    elif name == 'info':
        d.ellipse(p((8, 8), (92, 92)), fill=fill)
        d.rectangle(p((45, 42), (55, 74)), fill=(255, 255, 255, 255))
        d.ellipse(p((44, 22), (56, 34)), fill=(255, 255, 255, 255))
    elif name == 'ok':
        d.ellipse(p((8, 8), (92, 92)), fill=fill)
        d.line(p((28, 52), (44, 67), (72, 36)), fill=(255, 255, 255, 255), width=int(10 * S / 100), joint='curve')
    elif name == 'camera':
        rect(8, 28, 72, 78, 8)
        d.polygon(p((72, 44), (92, 30), (92, 76), (72, 62)), fill=fill)
    elif name == 'expand':
        line([(30, 40), (50, 60), (70, 40)], 10)
    else:
        raise KeyError(name)


def icon(name, size=16, color=None):
    """A Tk image of icon `name`, `size` px at 96 dpi, in `color` (default: text colour)."""
    color = color or COLORS['text']
    pixels = max(8, px(size))
    key = (name, pixels, color)
    if key not in _ICON_CACHE:
        S = pixels * 4
        image = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        _draw_icon(ImageDraw.Draw(image), name, S, _hex_to_rgba(color))
        image = image.resize((pixels, pixels), Image.Resampling.LANCZOS)
        _ICON_CACHE[key] = ImageTk.PhotoImage(image)
    return _ICON_CACHE[key]


def rounded_rect(canvas, x0, y0, x1, y1, radius, **kwargs):
    """A rounded rectangle on a Tk canvas (a smoothed polygon)."""
    r = max(0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    points = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
              x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return canvas.create_polygon(points, smooth=True, **kwargs)
