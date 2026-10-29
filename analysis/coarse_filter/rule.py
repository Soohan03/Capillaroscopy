"""The post-hoc rule of PLAN.md: the protocol's measurement, and the coarser filter for a loop it does not resolve.

`measure` gives every number the rule needs from one space-time diagram; `judge` applies the rule to a table
of them. Shared by checks.py (synthetic, occlusion, after release) and aim1.py.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

REPOSITORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPOSITORY)

from capillary import pattern_shift  # noqa: E402

#: Step 2's filter (σ along the line, px) and the slowest speed it searches (px/frame): PLAN.md's rule, then its
#: sensitivity analyses.
COARSE_PX = (4.0, 16.0)
FLOORS = (5.0, 3.0, 8.0)
MAIN_FLOOR = FLOORS[0]
MIN_SNR = pattern_shift.MIN_SNR


def _estimate(diagram, **kwargs) -> tuple:
    found = pattern_shift.pattern_shift(diagram, **kwargs)
    return found.speed_px_per_frame, found.snr, bool(found.in_range)


def measure(diagram, apex_px: float) -> dict:
    """The whole line and each limb (split at `apex_px`, as `pattern_shift.loop_limbs` splits it) by the protocol's
    filter (``s1_``), and by the coarser one from each of `FLOORS` (``s2_<floor>_``)."""
    diagram = np.asarray(diagram, dtype=float)
    split = int(round(apex_px))
    parts = {'': diagram, 'start_': diagram[:, :split + 1], 'end_': diagram[:, split:]}
    out = {}
    for part, values in parts.items():
        out.update(zip((f's1_{part}speed', f's1_{part}snr', f's1_{part}in_range'), _estimate(values)))
        for floor in FLOORS:
            out.update(zip((f's2_{floor:g}_{part}speed', f's2_{floor:g}_{part}snr', f's2_{floor:g}_{part}in_range'),
                           _estimate(values, bandpass_px=COARSE_PX, min_speed=floor)))
    return out


def _resolved(t: pd.DataFrame, prefix: str) -> pd.Series:
    return t[f'{prefix}in_range'].astype(bool) & (t[f'{prefix}snr'] >= MIN_SNR)


def _movement(t: pd.DataFrame, prefix: str) -> pd.Series:
    """Both limbs resolved, with opposite signs along the line (`pattern_shift.loop_limbs`)."""
    both = _resolved(t, f'{prefix}start_') & _resolved(t, f'{prefix}end_')
    return both & (np.sign(t[f'{prefix}start_speed']) != np.sign(t[f'{prefix}end_speed']))


def judge(t: pd.DataFrame, floor: float = MAIN_FLOOR) -> pd.DataFrame:
    """`t` (rows of `measure`, with ``crosses_itself``) judged by the rule with step 2 searching from `floor`.

    Adds ``s1_counts`` (the protocol), ``eligible`` (its sole failure is "not resolved"), ``s2_counts``,
    ``counts`` (by either step), ``step`` (1, 2 or 0) and ``speed_px_per_frame`` (signed, NaN unless it counts).
    """
    out = t.copy()
    crossing = out['crosses_itself'].astype(bool)
    s1_resolved = _resolved(out, 's1_')
    s1_movement = _movement(out, 's1_')
    out['s1_counts'] = s1_resolved & ~s1_movement & ~crossing
    out['eligible'] = ~s1_resolved & ~s1_movement & ~crossing
    prefix = f's2_{floor:g}_'
    out['s2_counts'] = out['eligible'] & _resolved(out, prefix) & ~_movement(out, prefix)
    out['counts'] = out['s1_counts'] | out['s2_counts']
    out['step'] = np.where(out['s1_counts'], 1, np.where(out['s2_counts'], 2, 0))
    out['speed_px_per_frame'] = np.where(out['s1_counts'], out['s1_speed'],
                                         np.where(out['s2_counts'], out[f'{prefix}speed'], math.nan))
    return out
