"""Pattern-shift estimator on synthetic recordings with known speed (30-s clips), against the centre-line method."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
import numpy as np, pandas as pd
from capillary import simulate
from capillary.spacetime import space_time_diagram, analyze_space_time
from capillary.pattern_shift import pattern_shift
MM, FPS = 0.001328903654, 30.0
conditions = {'as measured': dict(disturbances=simulate.Disturbances()),
              'strong': dict(disturbances=simulate.Disturbances.strong()),
              'faint (1/3 contrast)': dict(disturbances=simulate.Disturbances(), contrast=20 / 3)}
speeds = [0, 0.5, 1, 2, 3, 5, 8, 12, 16, 20, 25, 30, 40]
rows = []
start = time.time()
for cname, kw in conditions.items():
    for v in speeds:
        for seed in range(10 if v == 0 else 3):
            rec = simulate.simulate(simulate.hairpin(), 900, float(v), seed=100 * seed + 7, **kw)
            line = rec.drawn_line(20.0, 140.0, seed=seed)
            d = space_time_diagram(rec.frames, line)
            e = pattern_shift(d)
            blocks = analyze_space_time(d, FPS, MM)
            fourier = blocks.speed_px_per_frame[blocks.resolved]
            rows.append({'condition': cname, 'speed': v, 'seed': seed, 'estimate': e.speed_px_per_frame, 'snr': e.snr,
                         'ci_low': e.ci95[0], 'ci_high': e.ci95[1], 'in_range': e.in_range,
                         'fourier_resolved': blocks.resolved.mean(), 'fourier_median': fourier.median() if len(fourier) else np.nan})
df = pd.DataFrame(rows)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
df.to_csv(os.path.join(HERE, 'out', 'validate_pattern_shift.csv'), index=False)
print(f'{len(df)} clips in {time.time() - start:.0f} s')
none = df[df.speed == 0]
print('\nno flow: highest SNR per condition (the threshold must sit above these):')
print(none.groupby('condition').snr.agg(['median', 'max']).round(1).to_string())
flow = df[df.speed > 0].copy()
flow['error_pct'] = 100 * (flow.estimate / flow.speed - 1)
flow['covered'] = (flow.ci_low <= flow.speed) & (flow.speed <= flow.ci_high)
for cname in conditions:
    f = flow[flow.condition == cname]
    print(f'\n{cname}: speed | estimate error % (median, worst) | SNR (min) | truth inside the 95% CI | centre-line method: blocks resolved, median error %')
    for v, g in f.groupby('speed'):
        fe = 100 * (g.fourier_median / v - 1)
        print(f'  {v:5.1f} px/frame ({v * FPS * MM:.3f} mm/s) | {g.error_pct.median():+6.1f} {g.error_pct.abs().max():6.1f} | '
              f'{g.snr.min():5.1f} | {int(g.covered.sum())}/{len(g)} | {g.fourier_resolved.median():4.0%} {fe.median():+6.1f}')
