"""Feasibility of resting CBV: lines on the resting image, snapped to the vessel, measured by both methods.

python analysis/resting_flow_feasibility/measure.py STEM

Lines come from lines.json; writes an overlay PNG to out/ and replaces the recording's rows in results.csv.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
import cv2, numpy as np, pandas as pd
from capillary.video import iter_frames, probe_video
from capillary.spacetime import Centreline, space_time_diagram, analyze_space_time
from capillary.stabilize import enhance
from capillary.pattern_shift import pattern_shift

OUT = os.path.join(HERE, 'out')
MM = 0.001328903654
TIMES = pd.read_csv(os.path.join(REPO, 'metadata', 'ESMOKE_timestamps.csv'), sep=';').set_index('source_file')
LINES = json.load(open(os.path.join(HERE, 'lines.json'), encoding='utf-8'))


def snap(points, vessel, search=4, every=2.0):
    """Move a clicked line onto the vessel's ridge: each sample along the local normal, within `search` px."""
    line = Centreline.from_points(points)
    pos, normal = line.sample_positions(every)
    offsets = np.arange(-search, search + 1, 0.5)
    snapped = []
    for p, n in zip(pos, normal):
        cand = p[None, :] + offsets[:, None] * n[None, :]
        values = cv2.remap(vessel, cand[:, 0:1].astype(np.float32), cand[:, 1:2].astype(np.float32), cv2.INTER_LINEAR).ravel()
        snapped.append(cand[int(np.argmax(values))])
    snapped = np.array(snapped)
    k = 5
    smooth = np.column_stack([np.convolve(snapped[:, i], np.ones(k) / k, 'valid') for i in (0, 1)])
    return smooth[::6].tolist() + [smooth[-1].tolist()]


def windows(stem, fps, n):
    occ = float(TIMES.loc[stem, 'occlusion']); rel = TIMES.loc[stem, 'release']
    w = {'rest': (int(2 * fps), int((occ - 2) * fps))}
    a, b = w['rest']; half = (a + b) // 2
    w['rest 1st half'], w['rest 2nd half'] = (a, half), (half, b)
    if pd.notna(rel):
        w['occlusion'] = (int((occ + 2) * fps), int((float(rel) - 2) * fps))
        w['after release'] = (int((float(rel) + 2) * fps), n - int(2 * fps))
    return w


def main(stem):
    path = os.path.join(REPO, 'StabilizedVideos', f'{stem}.avi')
    fps = probe_video(path).fps
    mean = np.load(os.path.join(OUT, f'{stem}_rest_mean.npy'))
    vessel = cv2.GaussianBlur(-enhance(mean), (0, 0), 1.5)
    lines = {}
    for name, spec in LINES[stem].items():
        pts = spec['points'] if spec['kind'] == 'tissue' else snap(spec['points'], vessel)
        lines[name] = (spec['kind'], Centreline.from_points(pts))
    # overlay to check the placement
    img = -enhance(mean); lo, hi = np.percentile(img[40:-40, 40:-40], [1, 99.7])
    img = cv2.cvtColor(np.clip((img - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    colours = [(0, 0, 255), (255, 80, 0), (0, 200, 0), (0, 200, 255), (255, 0, 255), (255, 255, 0), (120, 120, 255)]
    for (name, (kind, line)), colour in zip(lines.items(), colours):
        p = (2 * line.sample_positions(1.0)[0]).astype(np.int32)
        cv2.polylines(img, [p], False, colour, 1)
        cv2.putText(img, name, tuple(int(v) for v in p[0] + [4, -4]), cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1)
    cv2.imwrite(os.path.join(OUT, f'{stem}_lines.png'), img)
    # measure
    rows = []
    for name, (kind, line) in lines.items():
        diagram = space_time_diagram(iter_frames(path), line)
        row = {'recording': stem, 'line': name, 'kind': kind, 'length_px': round(line.length_px),
               'points': ';'.join(f'{x:.1f},{y:.1f}' for x, y in line.points)}
        for wname, (a, b) in windows(stem, fps, diagram.shape[0]).items():
            e = pattern_shift(diagram[a:b])
            to = fps * MM
            row[f'{wname} mm/s'] = e.speed_px_per_frame * to
            row[f'{wname} ci'] = f'{e.ci95[0] * to:.3f}..{e.ci95[1] * to:.3f}'
            row[f'{wname} snr'] = e.snr
            row[f'{wname} ok'] = e.resolved
        a, b = windows(stem, fps, diagram.shape[0])['rest']
        blocks = analyze_space_time(diagram[a:b], fps, MM)
        row['centre line rest resolved'] = blocks.resolved.mean()
        row['centre line rest median mm/s'] = blocks.velocity_mm_s.median()
        rows.append(row)
        print(f"{name:22s} {kind:6s} {row['length_px']:4d} px | rest {row['rest mm/s']:+.3f} mm/s "
              f"({row['rest ci']}) snr {row['rest snr']:5.1f} {'OK ' if row['rest ok'] else '-- '}| halves "
              f"{row['rest 1st half mm/s']:+.3f} ({row['rest 1st half snr']:4.1f}) {row['rest 2nd half mm/s']:+.3f} "
              f"({row['rest 2nd half snr']:4.1f}) | occl {row.get('occlusion mm/s', np.nan):+.3f} ({row.get('occlusion snr', np.nan):4.1f})"
              f" | after {row.get('after release mm/s', np.nan):+.3f} ({row.get('after release snr', np.nan):4.1f})"
              f" | centre line at rest {row['centre line rest resolved']:.0%} resolved")
    results = os.path.join(HERE, 'results.csv')
    old = pd.read_csv(results) if os.path.exists(results) else pd.DataFrame()
    if len(old):
        old = old[old.recording != stem]
    pd.concat([old, pd.DataFrame(rows)], ignore_index=True).to_csv(results, index=False)


if __name__ == '__main__':
    main(sys.argv[1])
