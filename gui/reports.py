"""The report plots, drawn from saved data.

`generate_line_report` turns a saved data set (see `capillary.datasets`) into
its plots and summary row, and `generate_validation_report` plots the
agreement of observers and the estimator on a reading set
(`capillary.validation`) or of repeated line placements
(`capillary.placement`). The measurement itself lives in the GUI-free
`capillary` package. Nothing here imports tkinter; the GUI runs these in
worker threads, with the off-screen matplotlib backend `gui/__init__.py` sets.
"""
import math
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _finite(value):
    """`value` as a float, or None when it is missing or not finite."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def generate_line_report(report_prefix, diagram, blocks, fps, mm_per_pixel, first_frame, time_points=(),
                         summary=None):
    """Plot a centre-line data set and write its summary row (see capillary.datasets).

    `diagram` is the space-time diagram (frames x positions along the line),
    `blocks` the per-block table from capillary.spacetime.analyze_space_time,
    `first_frame` the video frame of the diagram's first row and
    `report_prefix` is ``Reports/<stem>___<name>``. Writes
    ``___line_velocity.png`` (velocity over time, with the pattern shift pooled
    over the range and its 95% interval if the summary has it resolved),
    ``___space_time.png`` (the diagram with the measured slopes) and
    ``___line_summary.csv``.
    """
    fps = fps or 30.0
    summary = summary or {}
    resolved_mask = blocks['resolved'].astype(bool)
    resolved = blocks[resolved_mask]
    unresolved = blocks[~resolved_mask]

    # velocity over time
    f, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.axhline(0, color='#9AA3AF', linewidth=0.6)
    if len(resolved):
        ax.plot(resolved['time_s'], resolved['velocity_mm_s'], 'o', markersize=3, color='#2F6FDE',
                label='3-s blocks')
        median = float(resolved['velocity_mm_s'].median())
        ax.axhline(median, color='#2F6FDE', linestyle='--', linewidth=1, label=f'median {median:.4f} mm/s')
    pooled = _finite(summary.get('pattern_shift_velocity_mm_s'))
    if pooled is not None:
        span = [first_frame / fps, (first_frame + len(diagram)) / fps]
        ci_low, ci_high = (_finite(summary.get(f'pattern_shift_ci95_{end}_mm_s')) for end in ('low', 'high'))
        if ci_low is not None and ci_high is not None:
            ax.fill_between(span, ci_low, ci_high, color='#1E874B', alpha=0.15, linewidth=0,
                            label='95% interval of the pattern shift')
        ax.plot(span, [pooled, pooled], color='#1E874B', linewidth=1.5,
                label=f'pattern shift over the range {pooled:.4f} mm/s')
    if len(unresolved):
        low = ax.get_ylim()[0] if len(resolved) or pooled is not None else 0.0
        ax.plot(unresolved['time_s'], [low] * len(unresolved), '|', color='#9AA3AF', markersize=8,
                label='unresolved blocks')
    for point in time_points:
        ax.axvline(x=float(point), c='r', linewidth=1)
    limb = {'arterial': 'arterial limb, flow towards the apex',
            'venous': 'drawn as the arterial limb, but the flow runs towards the base: venous',
            'unknown': 'arterial limb, direction of flow not resolved'}.get(summary.get('limb_check')) or {
        'start': 'whole loop, arterial limb at its start', 'end': 'whole loop, arterial limb at its end',
        'unknown': 'whole loop, direction of flow not resolved'}.get(summary.get('arterial_end'))
    ax.set_title('Velocity along the centre line' + (f' ({limb})' if limb else ''))
    ax.set_ylabel('mm/s (positive: from the first point towards the last)')
    ax.set_xlabel('Seconds')
    ax.legend(loc='best', fontsize=8)
    f.savefig(report_prefix + '___line_velocity.png', dpi=f.dpi, transparent=True, bbox_inches='tight')
    plt.close(f)

    # the space-time diagram, without still structure and same-moment changes, with the measured slopes
    cleaned = np.asarray(diagram, dtype=float)
    cleaned = cleaned - cleaned.mean(axis=0, keepdims=True)
    cleaned = cleaned - cleaned.mean(axis=1, keepdims=True)
    low, high = np.percentile(cleaned, [1, 99]) if cleaned.size else (0, 1)
    length_um = (cleaned.shape[1] - 1) * mm_per_pixel * 1000.0
    start_s, stop_s = first_frame / fps, (first_frame + cleaned.shape[0]) / fps
    f, ax = plt.subplots(figsize=(12, 4), dpi=200)
    ax.imshow(cleaned.T, cmap='gray', vmin=low, vmax=high, aspect='auto', interpolation='nearest',
              extent=[start_s, stop_s, length_um, 0])
    step = max(1, len(resolved) // 40)
    for frame, row in resolved.iloc[::step].iterrows():
        centre = frame / fps
        slope = float(row['velocity_mm_s']) * 1000.0               # um per second along the line
        ax.plot([centre - 1.0, centre + 1.0], [length_um / 2 - slope, length_um / 2 + slope], color='#FF9F1C',
                linewidth=1)
    for point in time_points:
        ax.axvline(x=float(point), c='r', linewidth=1)
    ax.set_xlim(start_s, stop_s)
    ax.set_ylim(length_um, 0)
    ax.set_xlabel('Seconds')
    ax.set_ylabel('um along the line')
    ax.set_title('Space-time diagram along the centre line (orange: measured slope of the streaks)')
    f.savefig(report_prefix + '___space_time.png', dpi=f.dpi, bbox_inches='tight')
    plt.close(f)

    row = dict(summary or {})
    row['line_length_um'] = length_um
    pd.DataFrame([row]).to_csv(report_prefix + '___line_summary.csv', index=False)


def generate_validation_report(report_dir, table, comparisons, unit='blocks'):
    """Plot agreement comparisons (capillary.validation, capillary.placement); returns the paths written.

    One panel per comparison with at least two pairs of velocities:
    ``bland_altman.png`` (difference against mean, with the bias and the 95%
    limits of agreement) and ``scatter.png`` (first measurement against
    second, with the line of identity). `unit` names what a pair is (blocks of
    a reading set, capillaries). A plot with no panel left is removed, so an
    old one is never shown as if it were current.
    """
    os.makedirs(report_dir, exist_ok=True)
    panels = [c for c in comparisons if c.get('first_column') and (c.get('pairs') or 0) >= 2]
    written = {}
    for kind in ('bland_altman', 'scatter'):
        path = os.path.join(report_dir, kind + '.png')
        if not panels:
            if os.path.exists(path):
                os.remove(path)
            continue
        columns = min(3, len(panels))
        rows = int(math.ceil(len(panels) / columns))
        f, axes = plt.subplots(rows, columns, figsize=(4.8 * columns, 4.1 * rows), dpi=150, squeeze=False)
        for ax, comparison in zip(axes.flat, panels):
            a = table[comparison['first_column']].to_numpy(dtype=float)
            b = table[comparison['second_column']].to_numpy(dtype=float)
            keep = np.isfinite(a) & np.isfinite(b)
            a, b = a[keep], b[keep]
            first, second = comparison['first'], comparison['second']
            if kind == 'bland_altman':
                ax.axhline(0, color='#9AA3AF', linewidth=0.6)
                ax.plot((a + b) / 2, a - b, 'o', markersize=3.5, color='#2F6FDE', alpha=0.8)
                bias, low, high = comparison['bias'], comparison['loa_low'], comparison['loa_high']
                ax.axhline(bias, color='#2F6FDE', linewidth=1.2, label=f'bias {bias:+.4f}')
                ax.axhline(low, color='#E5484D', linestyle='--', linewidth=1,
                           label=f'95% limits {low:+.4f} to {high:+.4f}')
                ax.axhline(high, color='#E5484D', linestyle='--', linewidth=1)
                ax.set_xlabel('mean of both (mm/s)')
                ax.set_ylabel(f'{first} − {second} (mm/s)', fontsize=8)
                ax.legend(loc='best', fontsize=7)
            else:
                ax.plot(b, a, 'o', markersize=3.5, color='#2F6FDE', alpha=0.8)
                low = min(0.0, float(np.min(a)), float(np.min(b)))
                high = max(0.0, float(np.max(a)), float(np.max(b)))
                pad = 0.05 * (high - low or 1.0)
                ax.plot([low - pad, high + pad], [low - pad, high + pad], color='#9AA3AF', linewidth=0.8,
                        label='identity')
                ax.set_xlim(low - pad, high + pad)
                ax.set_ylim(low - pad, high + pad)
                ax.set_aspect('equal')
                ax.set_xlabel(f'{second} (mm/s)', fontsize=8)
                ax.set_ylabel(f'{first} (mm/s)', fontsize=8)
                ax.legend(loc='upper left', fontsize=7)
            ax.set_title(f'{comparison["comparison"]}\n{len(a)} {unit} with a velocity from both', fontsize=8)
            ax.tick_params(labelsize=7)
            ax.locator_params(axis='both', nbins=5)
        for ax in list(axes.flat)[len(panels):]:
            ax.axis('off')
        f.tight_layout()
        f.savefig(path, dpi=f.dpi, bbox_inches='tight')
        plt.close(f)
        written[kind] = path
    return written
