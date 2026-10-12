# Development Log

Diary of all changes made to the capillaroscopy analysis tool. Every session
that changes code gets a dated entry: what branch, what changed, why, and how
it was verified. Newest entries first.

---

## 2026-10-12 — Aim 1 feasibility: resting flow on the arterial limb in 15 before-exposure recordings

**Branch:** `analysis/aim1-feasibility`, from `main` at `17a2770` (after PR #16, the arterial limb on
the Centre line page, was merged).

**Commits:**

- this entry, with `analysis/aim1_feasibility/`, notes in `CLAUDE.md`, and `ESMOKE_Videos/` and
  `ISMOKE_Videos/` in `.gitignore`

The user asked to continue where the last session left off.

- The user merged PR #16 (step 2 of the arterial-limb plan) on GitHub at the start of the session.
  `main` was fast-forwarded to `17a2770` and `feature/arterial-limb` deleted.
- 23 more recordings had arrived in `RecordedVideos/`. The user chose to stabilize them. As the next
  task the user chose aim 1's feasibility: for the participants now on the desktop, can an arterial
  limb's resting flow be measured in the före recordings of both visits?

### The recordings on the desktop

- **35 raw recordings** are in `RecordedVideos/`. The 23 new ones (FP05–FP13) came from
  `OneDrive_2_2026-10-11.zip` and `OneDrive_3_2026-10-11.zip`.
- **Each new one was checked** (scratch script, read only):
  - the name is in NFC and in the official times;
  - rawvideo, 640 × 480, 30 fps;
  - every frame reads and none is black;
  - every official occlusion and release falls inside the video at 30 fps.
- **`FP09_Wefter_23-Oct-2019_10-04-53` is not in the official times.** DynCap has no times for
  any FP09 W after-exposure recording, which is why FP09 is used for aim 1 only.
  - The file holds 2052 frames (68 s), probably an aborted attempt.
  - It was not stabilized.
- **FP09_Qefter** is in the official times but used by no aim, so it was not stabilized either.
- **Clean-up.** The 23 `:Zone.Identifier` files Windows had added were deleted. All were 143 bytes
  and pointed at the two OneDrive zips.
- **Coverage** (`python -m capillary.inventory --have RecordedVideos`):
  - 30 of the 90 recordings the aims use are here, all ESMOKE.
  - 8 ESMOKE participants have both före recordings: FP01, FP03, FP05, FP06, FP07, FP09, FP12
    and FP13.
  - No ISMOKE recording has arrived yet.

### Stabilized

The 21 new recordings the aims use were stabilized with the command line at commit `17a2770`:
`python -m capillary.stabilize RecordedVideos/<name>.avi --out StabilizedVideos/<name>.avi`. They
ran 11 at a time on 16 cores and took 9 minutes (213–349 s each).

| Recording | Used for | Moved (px) | Match at rest | In occlusion | After release | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| FP05_Qföre_försök4 | aims 1, 2 | 107.5 × 33.6 | 0.75 | 0.81 | 0.71 | |
| FP05_Wföre | aims 1, 2 | 87.7 × 192.2 | 0.71 | 0.62 | 0.81 | a 44-px jump after the rest |
| FP05_Wefter_försök2 | aim 2 | 204.7 × 128.9 | 0.67 | 0.59 | 0.62 | |
| FP06_Qföre_försök2 | aims 1, 2 | 35.5 × 12.6 | 0.66 | 0.75 | 0.84 | |
| FP06_Qefter_försök2 | aim 2 | 106.3 × 71.0 | 0.73 | 0.91 | 0.81 | |
| FP06_Wföre | aims 1, 2 | 92.8 × 138.5 | 0.82 | 0.72 | 0.63 | |
| FP06_Wefter | aim 2 | 70.4 × 88.8 | 0.73 | 0.44 | – | no release time |
| FP07_Qföre | aims 1, 2 | 292.0 × 320.9 | 0.76 | 0.75 | – | no release time; jumps of up to 294 px from 134 s on, 9 frames at the search limit |
| FP07_Qefter | aim 2 | 58.9 × 19.2 | 0.83 | 0.65 | – | no release time |
| FP07_Wföre | aims 1, 2 | 68.2 × 15.0 | 0.93 | 0.62 | 0.88 | |
| FP07_Wefter | aim 2 | 46.7 × 25.2 | 0.91 | 0.88 | 0.88 | references disagree by more than 1 px on 3 rest frames |
| FP09_Qföre | aim 1 | 43.1 × 29.4 | 0.48 | 0.85 | 0.48 | |
| FP09_Wföre | aim 1 | 7.0 × 12.0 | 0.83 | 0.75 | – | no release time |
| FP12_Qföre | aims 1, 2 | 10.4 × 19.8 | 0.42 | 0.90 | 0.55 | references disagree by more than 1 px on 78 rest frames (at most 3.0 px) |
| FP12_Qefter | aim 2 | 29.4 × 26.2 | 0.44 | 0.79 | 0.61 | |
| FP12_Wföre | aims 1, 2 | 12.4 × 45.0 | 0.42 | 0.80 | 0.39 | references disagree by more than 1 px on 147 rest frames (at most 6.7 px) |
| FP12_Wefter | aim 2 | 24.7 × 33.5 | 0.50 | 0.85 | 0.49 | |
| FP13_Qföre | aims 1, 2 | 145.3 × 79.0 | 0.94 | 0.90 | 0.87 | |
| FP13_Qefter | aim 2 | 28.0 × 9.7 | 0.94 | 0.91 | 0.96 | |
| FP13_Wföre_försök2 | aims 1, 2 | 27.4 × 117.8 | 0.91 | 0.90 | 0.90 | |
| FP13_Wefter | aim 2 | 33.4 × 107.4 | 0.87 | 0.87 | 0.83 | |

Match is the median normalized cross-correlation with the references, per phase as on 2026-10-11.
Without a release time, "in occlusion" runs to the end of the video.

- **At rest no frame is at the search limit.** FP07_Qföre's one large step at rest (21 px, at
  30 s) was followed: its match stays at 0.71 or more and its references agree within 0.3 px.
- **FP12's two före recordings are the weakest at rest:** match 0.42, and the two references
  disagree by more than 1 px on 78 and 147 frames. Their resting images are still sharp enough to
  place lines on, but the alignment at rest is less certain than in the others.
- **FP09_Qföre** matches only 0.48 at rest; its references agree.

### The folder renamed: `ESMOKE_Videos/`

At 18:22, after the stabilization, the user renamed `StabilizedVideos/` to `ESMOKE_Videos/`, to sort
the stabilized videos by study (`ISMOKE_Videos/` to follow). Asked, the user chose to keep it.

- `ESMOKE_Videos/` holds the 31 stabilized videos (the 10 of 2026-10-11 and the 21 above), each
  with its shift file and provenance.
- **The app does not look there yet.**
  - `gui.settings.DataFolder.stabilized` is `StabilizedVideos/`, and `ensure()` creates it,
    empty, at the next start.
  - So the app lists the 31 recordings as raw only, and would offer to stabilize them again.
  - Teaching it about per-study folders is a separate change.
- `.gitignore` now ignores `ESMOKE_Videos/` and `ISMOKE_Videos/`, as it does the other data
  folders, so 55 GB of video never shows up as untracked.
- The analysis below looks for stabilized videos in `StabilizedVideos/`, `ESMOKE_Videos/` and
  `ISMOKE_Videos/` (`common.VIDEO_FOLDERS`).

### The feasibility check (`analysis/aim1_feasibility/`)

**The question.** Aim 1 compares resting CBV between the two före recordings of each participant,
and the PI wants it from the arterial limb only. Seven of the eight participants have both före
recordings measurable; FP01_W cannot be stabilized. How many of the seven give an arterial limb
with measurable resting flow at both visits?

**Lines** (the folder's README has the details):

- **What:** 109 limbs of 59 loops in the 15 recordings (2–16 limbs per recording, median 6), and
  one line through tissue in each as a control.
- **Who and from what:** placed by Claude Code by eye, not by the study's observer.
  - They were placed on the resting image: the mean of the official rest (52–77 s per
    recording), band-passed with σ 1 and 8 px.
  - No velocity had been seen at that point.
  - FP01_Qföre and FP03_Qföre reuse the lines of 2026-10-08.
- **Which loops:** those whose two limbs could be told apart and followed down from the apex.
  Loops whose limbs cross at once, rings, single bands and loops washed out at the frame's edge
  were left out.
- **Direction:** each limb runs from its base to the apex. In every recording the apexes point
  up, as each loop's U-turn shows.
- **Tracing:** each line follows the vessel's ridge from point to point (the cheapest path
  through the image), and the two limbs of a loop are kept 5 px apart except near the apex.
- **Checks before measuring:** gridded close-ups of every loop, in three rounds. Lines were
  ended above where the limbs cross or merge, a point was added on a thin limb beside a wide
  one, and four loops were dropped.
- **Measurement:** over the official rest window. Per line, the pattern shift pooled over the
  rest and its halves, as a centre-line data set keeps it, plus the centre-line method's 3-s
  blocks. About 7 minutes for the 124 lines.

**When a limb counts as measured**, at three levels (`summarize.py`):

1. **Resolved:** the pooled pattern shift reaches a signal-to-noise ratio of 8, the app's rule.
2. **Robust:** resolved, and also at least 1.5 px/frame (0.06 mm/s), with a 95% interval clear
   of zero. This rule was set before any result was seen:
   - near the slowest speed reported (1 px/frame), slow drift pulls the band-passed estimate
     (2026-10-11);
   - the limb check rests on the direction, which an interval across zero leaves open.
3. **Combined (exploratory):** robust, or else the centre-line blocks, when at least 25% of
   them are resolved and at least 90% of those run the same way. Without flow the benchmark
   resolves 7–11% of blocks under strong jitter. This level was added after the first results,
   for the reason below.

**Results** (art/ven: arterial and venous limbs measured; loops: those with both limbs measured at
the combined level, and in brackets how many of them run opposite ways):

| Participant | Visit | Recording | Limbs (loops) | Resolved: art/ven | Robust: art/ven | Combined: art/ven | Loops (opposite) | Arterial, combined (mm/s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FP01 | W | FP01_W | not measured (stabilizer fails) | | | | | |
| FP01 | Q | FP01_Qföre | 4 (3) | 1/2 | 1/1 | 1/1 | 1 (1) | 0.106 |
| FP03 | Q | FP03_Qföre | 6 (5) | 0/0 | 0/0 | 0/0 | 0 | |
| FP03 | W | FP03_Wföre | 10 (5) | 1/2 | 1/1 | 1/1 | 1 (1) | 0.080 |
| FP05 | W | FP05_Wföre | 8 (4) | 0/0 | 0/0 | 0/0 | 0 | |
| FP05 | Q | FP05_Qföre_försök4 | 4 (2) | 1/1 | 1/1 | 1/1 | 1 (1) | 0.139 |
| FP06 | W | FP06_Wföre | 7 (4) | 1/1 | 0/1 | 0/1 | 0 | |
| FP06 | Q | FP06_Qföre_försök2 | 16 (8) | 1/4 | 1/1 | 2/3 | 2 (2) | 0.068, 0.040 |
| FP07 | Q | FP07_Qföre | 6 (3) | 0/1 | 0/1 | 0/1 | 0 | |
| FP07 | W | FP07_Wföre | 12 (6) | 1/1 | 1/1 | 1/1 | 1 (1) | 0.140 |
| FP09 | W | FP09_Wföre | 6 (3) | 0/0 | 0/0 | 2/2 | 2 (2) | 0.009, 0.014 |
| FP09 | Q | FP09_Qföre | 2 (1) | 0/0 | 0/0 | 0/0 | 0 | |
| FP12 | Q | FP12_Qföre | 2 (2) | 0/0 | 0/0 | 0/1 | 0 | |
| FP12 | W | FP12_Wföre | 4 (2) | 0/0 | 0/0 | 0/1 | 0 | |
| FP13 | W | FP13_Wföre_försök2 | 12 (6) | 0/0 | 0/0 | 1/2 | 1 (1) | 0.038 |
| FP13 | Q | FP13_Qföre | 10 (5) | 3/3 | 2/2 | 3/3 | 3 (3) | 0.066, 0.087, 0.080 |

| Level | Limbs measured (of 109) | Arterial | Recordings with a limb (of 15) | Loops with both limbs (opposite) | Arterial limb at both visits (of 7) | Any limb at both visits (of 7) |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Resolved | 24 | 9 | 8 | 8 (7) | 1 (FP06) | 2 |
| Robust | 16 | 7 | 8 | 6 (6) | 0 | 2 |
| Combined | 30 | 12 | 12 | 12 (12) | 1 (FP13) | 4 (FP06, FP07, FP12, FP13) |

- **No tissue line shows flow.** None of the 15 was resolved by the pattern shift (highest score
  4.4), and the centre-line method resolved none of their blocks.
- **Much resting flow is slower than the pattern shift's range.**
  - 18 limbs in 6 recordings scored 8 or more at its slowest speed (1 px/frame, 0.04 mm/s), which
    the method never reports.
  - Where the two limbs of such a loop moved opposite ways, the centre-line blocks resolved 25–80%
    of the rest, all one way: FP06_Qföre's loop D, FP09_Wföre's loop B, FP13_Wföre's loop D.
  - Where they moved the same way, the blocks resolved 0–5%: FP03_Wföre's loops E and F, all four
    limbs towards the base. That is drift of the image, not flow.
  - The combined level takes 14 limbs from the centre-line blocks, at 0.005–0.087 mm/s, in 6
    recordings. 8 of them were at the pattern shift's edge.
  - All 12 loops with both limbs measured at this level run opposite ways.
- **The space-time pictures** (10 s of 24 lines, scratch script) agree:
  - mirrored slanted streaks in FP13_Qföre's loop A, FP06_Qföre's loop D, and FP13_Wföre's loop A.
    The pattern shift missed the last on its 50-px lines (scores 7.2 and 4.7); the centre-line
    method resolved about 60% of its blocks.
  - Noise on FP03_Qföre's limbs and on FP03_Wföre's B left. The pattern shift resolved that limb
    at 10.2, but its interval spans zero, so it is not robust.
  - Faint texture moving the same way on both limbs of FP03_Wföre's loop E.
  - FP09_Wföre's limbs (0.005–0.02 mm/s) show slowly moving large features, close to standstill.
- **The one loop that broke the rule at the resolved level,** FP06_Qföre's loop H, has both limbs
  venous at 1.1–1.2 px/frame, near the slow edge.
  - Its right limb shows clear streaks towards the base: real venous flow.
  - The left limb's line lies off the ridge (0.25 of the ridge's brightness, against 0.5–0.8 on
    most lines). Its weak score (8.7) is probably the right limb's flow, picked up near the apex.
  - The robust rule drops both, as slower than 1.5 px/frame.
- **The velocities are low:** arterial limbs a median 0.074 mm/s (0.009–0.140), venous 0.067
  (0.005–0.101).
  - That is far below the 0.5–1 mm/s the project expected from the literature.
  - The limbs that can be measured are those whose plasma gaps show, probably the slower ones.
  - The frame rate and the pixel size are still unverified.
- **Measured limbs are longer:** a median of 98 px, against 70 px for the others.
- **Where nothing was measured:** FP03_Qföre, FP05_Wföre and FP09_Qföre give no limb at any
  level. Their space-time pictures are noise.

### What it means for aim 1

To discuss with the supervisors:

- **Resting CBV from the arterial limb only is feasible in at most 1 of these 7 participants.**
  Whether a visit gives an arterial limb depends on which few loops happen to show plasma gaps,
  and each recording gives 0–3 such loops.
- **Any limb, arterial or venous,** gives both visits in 2 participants with the pattern shift
  alone, and in 4 with the centre-line method added for slower flow.
- **The combined rule is exploratory.** If it is to be used, it should be fixed before the real
  analysis and checked on recordings it was not made on: the rest of ESMOKE, and ISMOKE.
- **The lines here are a lower bound on what can be found.**
  - They were placed on clearly visible loops only (2–16 limbs per recording).
  - An observer working in the app, with the video, may find more.
  - The study's observer should place the lines for the real analysis, blind to the visit.

### Verification

- `python -m pytest`: 265 passed; nothing in the package changed.
- flake8: the CI's error selection is clean on the whole repository, and the full set on
  `analysis/aim1_feasibility/`.
- **The measurement ran twice,** the second time with three more centre-line columns. All 30
  earlier columns of the 124 lines agreed exactly.
- **Controls:**
  - the tissue lines (none showed flow);
  - the direction rule in loops (12 of 12 at the combined level);
  - 24 space-time pictures looked at.
- **Scratch scripts** (in the session's scratchpad, not in the repository):
  - the read-only check of the raw recordings;
  - the parallel stabilization and its quality per phase;
  - the gridded close-ups for placing and checking lines;
  - the space-time pictures.

### Open

- **The app and `ESMOKE_Videos/`:** let the app read per-study folders. Until then it lists the 31
  recordings as raw only.
- **Decide with the supervisors:** arterial limb only, or any limb, for aim 1; and whether to
  combine the two methods, and by which rule.
- **Line placement by the study's observer** in the app, blind to the visit, then compared with
  these lines (`capillary/placement.py` should compare the pooled velocity at rest, not the
  blocks).
- **If the combined rule is kept,** the Centre line page should show it, since it now gives the
  pooled pattern shift as the headline.
- **More recordings:** 60 of the 90 the aims use are still to come, all of ISMOKE among them.
- **The stabilizer fix for large movements:** FP01's active visit (FP01_W) cannot be measured
  until then.
- **Still unverified:** the frame rate, the pixel size and the exposure time.

---

## 2026-10-11 — The arterial limb on the Centre line page: pattern shift, official phases, direction check

**Branch:** `feature/arterial-limb`, from `main` at `06700a0` (after PR #15, the band-pass of step 1,
was merged).

**Commits:**

- this entry, with the change and its tests

This is step 2 of the plan in the entry below: the user's PI wants resting CBV from the arterial limb
only. After step 1 the user said "Lets start". Step 2 puts the pattern shift on the Centre line page,
takes the rest from the official times, and checks whether a line lies on the arterial limb.

### How the arterial limb is recognized

- **Blood flows up the arterial limb to the apex and down the venous limb.** So the direction of
  flow along a limb tells which limb it is, once the apex end of the line is known.
- **The line runs from the limb's base to the apex.** That fixes the apex end independently of the
  flow. If the user marks the line as an arterial limb, the page labels its first point "base" and
  its last "apex", so a line drawn the wrong way shows at once. Flow along the line (positive) is
  then the arterial limb, and flow against it the venous limb.
- **The check uses the pattern shift pooled over the range.**
  - At rest single 3-s blocks rarely resolve.
  - A few resolved blocks give no reliable direction: with no flow but strong jitter, the benchmark
    resolves 7–11% of blocks.
  - Pooled scores without flow stayed at or below 5.4 (synthetic) and 3.6 (tissue lines). A
    resolved pooled estimate (8 or more) gives a reliable sign.
- **Outcomes:**
  - *arterial:* resolved and towards the apex;
  - *venous:* resolved and towards the base, so the venous limb, or a line drawn from the apex;
  - *unknown:* not resolved.

### The change

- **`capillary/inventory.py`: the official phases as frames.**
  - `recording_phases(name, fps, frame_count)` returns a `Phases`, with these windows:
    - the rest, from 2 s after the start to 2 s before the occlusion;
    - the occlusion, from 2 s after it to 2 s before the release;
    - after release, from 2 s after the release to 2 s before the end of the video.
  - The 2-s margins are `REST_MARGIN_S`, as in the inventory's rest and the earlier analyses.
  - Without a release time, only the rest is given.
  - If an official time lies after the end of the video, no window is given and a note says the
    times do not fit. This is the case of `FP01_Wefter_14-Oct-2019_10-07-49` (metadata/README).
  - Notes also flag a rest under 30 s and a missing release.
  - `Phases.phase_of(first, last, fps)` labels a range by the official times themselves (no
    margins): rest, occlusion, after release, several joined by " + ", or "occlusion or later"
    without a release time.
  - The times are read once per folder (`lru_cache`).
- **`capillary/pattern_shift.py`:**
  - `summarize(diagram, fps, mm_per_pixel)` returns what a data set keeps, all keys starting with
    `pattern_shift_`:
    - the pooled velocity (NaN unless resolved, as the blocks do, so nothing downstream averages
      unresolved values in) and the best speed (also when unresolved);
    - the signal-to-noise ratio, whether resolved, and the blocks pooled;
    - the 95% interval (NaN unless resolved);
    - each half of the range in time, pooled on its own, when a half holds at least
      `MIN_HALF_BLOCKS` (3) blocks.
  - Why the halves: the jackknife interval held the truth in only 63% of synthetic cases (step 1),
    and the halves were the stability check of the validation. They also measure within-recording
    repeatability, next to aim 1's between-day repeatability.
  - `limb_from_direction(velocity)` returns arterial, venous or unknown.
  - `ARTERIAL_LIMB = 'arterial limb'` is the role of such a line.
- **`gui/tasks.py`:**
  - `measure_line_dataset(..., role=None)` pools the pattern shift after the blocks
    (`summarize_line`).
  - The summary gains the `pattern_shift_...` keys, plus:
    - `line_role` ("arterial limb" or empty);
    - `limb_check` (arterial, venous or unknown, for an arterial limb);
    - `phase` (the range's official phase; empty without usable times).
  - The provenance gains `line.role` and the pattern-shift settings (`pattern_shift`).
  - `regenerate_line_report` recomputes all of it from the saved diagram and keeps the role. Older
    centre-line data sets get the pattern shift when their report is regenerated.
  - Two-box data sets get `phase` too (`range_phase`).
- **`Caper.generate_line_report`:**
  - the velocity plot draws the pooled velocity and its 95% interval across the range;
  - the title states the limb check;
  - the summary CSV in `Reports/` carries all the new columns.
- **Range section (`gui/measure_page.py`, both measure pages):**
  - "Official phases" with the occlusion and release times, and buttons Rest, Occlusion and After
    release that set the range. The buttons are disabled where a window is missing.
  - A note when the recording has no official times, or when they do not fit.
  - The range's detail names its phase ("rest", "rest + occlusion").
  - The timeline (`gui/transport.py`) marks the occlusion with an orange bar under the track. Its
    hover label adds the phase ("1:40.000 · frame 3000 · occlusion").
- **Centre line page (`gui/line_page.py`):**
  - **Option:** a checkbox "Arterial limb, from its base to the apex".
    - It stays on for further recordings.
    - It is kept with each recording's line, and restored with a data set's line.
    - The overlay labels base and apex; the hints ask for the base first.
  - **Pooled row:** a new row says the pooled method measures from 0.04 mm/s. Its tooltip gives
    the validated range.
  - **Result panel:**
    - the check, with an icon;
    - the pooled velocity as the headline (the blocks' median when the pooled one is not resolved);
    - the pattern shift's velocity, 95% interval, signal-to-noise ratio and halves;
    - the 3-s blocks as before;
    - notes when the range mixes phases, the halves run opposite ways, or few blocks were resolved.
    - When fewer than two blocks are resolved, the chart says the pooled velocity is above it.
  - **Preview:** when 4 s show no clear streaks, the message now says that Measure pools the whole
    range.
- **Results page:** a centre-line card shows:
  - the pooled velocity with its interval, signal-to-noise ratio and halves;
  - the blocks;
  - the limb check;
  - the phase, and the role in the description.
  - A data set without pattern shift says to regenerate its report.
- **`capillary/cli.py`** prints the halves after the pooled estimate.
- **Docs:** README (the page table, the pattern shift, a paragraph on the arterial limb), CLAUDE.md,
  the data set formats (`capillary/datasets.py` docstring).

### Verification

**Tests:** 265 pass (259 + 6 new):

- `test_the_official_phases_as_frames_of_a_video`: FP01_Qföre's windows (60–1988, 2109–3854,
  3975–5339 for 5400 frames), the phase labels, the macOS spelling.
- `test_phases_without_a_release_or_that_do_not_fit_the_video`: rest only; a 2-s rest
  (ISMOKE_FP04_Sefter); FP01_Wefter 10-07-49's times after the video's end; an unknown name.
- `test_a_data_set_keeps_the_pooled_speed_and_each_half`: flow slowing from 5 to 4 px/frame
  halfway; each half finds its own speed within 3%.
- `test_a_short_or_unresolved_range_keeps_no_velocity_it_cannot_support`.
- `test_the_direction_of_flow_tells_the_limbs_of_a_loop_apart`: on a simulated loop, a line from
  the base to the apex on the left limb reads arterial, on the right limb venous.
- `test_an_arterial_limb_is_checked_by_the_direction_of_its_flow` (through `measure_line_dataset`):
  - the role, check and phase in the provenance and the summary CSV;
  - the same line reversed reads venous;
  - regenerating keeps the check.
- Existing tests check that a line without a role saves `role: null` and no check, and that
  regenerating recomputes the pooled velocity.
- **Planted bugs:** with arterial and venous swapped, 2 tests fail; with the rest windows without
  margins, 2 tests fail.
- **flake8:** the CI's error selection is clean on the whole repository. The full set reports
  nothing on the lines this branch changed; older lines keep their earlier warnings.

**On the recordings** (scratch script, not in the repository; written to a scratch data folder).
All 35 feasibility lines were measured through `measure_line_dataset`:

- each snapped to the vessel as in step 1;
- each turned to run from its lower end (base) to its upper end (apex);
- each marked as an arterial limb;
- the range set to the official rest window.

Results:

- **The same 5 of 29 limbs resolved as in step 1.** Their pooled velocities agree with step 1's
  within 0.0004 mm/s (the sign turned with the line).
- **The check:** 2 arterial, 3 venous, 24 unknown. All 6 tissue lines were unknown.
- **Time:** about 3.5 s per line (median), reading a minute of video.

| Line | px | Pooled (mm/s) | 95% interval | Signal-to-noise | Halves | Check |
| --- | ---: | ---: | --- | ---: | --- | --- |
| FP01_Qföre, tall loop, right limb | 63 | +0.108 | 0.098–0.117 | 9.1 | – / +0.102 | arterial |
| FP01_Qföre, tall loop, left limb | 104 | −0.083 | −0.091 to −0.075 | 19.9 | −0.085 / −0.081 | venous |
| FP03_Qefter, loop P, right limb | 147 | +0.042 | 0.036–0.048 | 18.7 | +0.043 / +0.040 | arterial |
| FP03_Qefter, loop P, left limb | 122 | −0.058 | −0.083 to −0.032 | 15.8 | −0.067 / −0.051 | venous |
| FP03_Qefter, loop S | 120 | −0.051 | −0.059 to −0.044 | 10.8 | −0.055 / −0.054 | venous |

- **Both loops with clear flow show one limb up and the other down,** as a loop must.
- **The arterial limb is not always the faster one.**
  - In FP01_Qföre's tall loop it is (0.108 against 0.083 mm/s).
  - In loop P it is the slower (0.042 against 0.058). Its speed lies at 1.05 px/frame, near the
    slowest speed reported, where step 1 found that slow drift can pull the estimate.
- **Only 2 arterial resting velocities in 6 recordings.** At rest most limbs show no moving
  pattern (step 1).

**The window** (scripted under WSLg, no window taking focus, scratch data folder with links to the
videos):

- **FP01_Qföre:**
  - occlusion 1:08.300 and release 2:10.500 shown;
  - Rest set frames 60–1988, labelled "rest";
  - the arterial-limb hints and labels appeared.
- **The tall loop's right limb,** with the line as clicked (not snapped): 0.0986 mm/s
  (0.078–0.119, signal-to-noise 9.6), arterial.
  - The snapped line gave 0.108. The 8% difference comes from where the line lies across the
    limb.
- **The other limb:** venous, with the warning.
- **Results page:** the cards and the report plot (pooled line and interval band, title with the
  check) look right.
- **A recording without official times** (a renamed link): disabled buttons, with a note.
- **Two boxes page:** After release set frames 3975–5668.
- No Tk errors; the app shut down cleanly.
- Two fixes came from the screenshots:
  - The theme's minimum button width pushed "After release" out of the panel; the three buttons now
    share three equal columns with less padding.
  - The chart said "no value could be resolved" when only the blocks were unresolved.
- **The batch command** on the same arterial limb printed the same numbers.

### Open

- **Line placement** (Validation page, `capillary/placement.py`) compares the blocks' medians. At
  rest those are mostly unresolved, so it should compare the pooled velocity. The placement
  sensitivity seen above (8%) is what it should quantify.
- **A table across data sets** for the aims: recording, limb, pooled velocity and interval,
  halves, check, phase, observer.
- **Blinding:** the page shows velocities while the line is placed. For aim 1, decide with the
  supervisors whether the observer should be blind to the visit.
- **Step 3:** the arterial limb's speed from a line over the apex (a simulator with different
  speeds per limb).
- **The exposure time,** which the user is checking.
- **New recordings:** `RecordedVideos/` now holds 28 recordings, 16 more than when 10 were
  stabilized earlier today. They are not stabilized yet; the user will say when all have arrived.

## 2026-10-11 — Pattern shift on band-passed rows; no hidden fast flow at rest

**Branch:** `feature/pattern-shift-bandpass`, from `main` at `a6f9b4a`.

**Commits:**

- this entry, with the estimator change, its tests and `analysis/pattern_shift_bandpass/`

The user and their PI agreed on how resting CBV should be measured:

- on the arterial limb only, since the velocity changes towards the venous side;
- if that is not feasible, over a longer distance.

The user asked to work on measuring faster velocities. A look at what limits them came first. The
user then chose step 1 of three proposed steps, a more sensitive estimator. The user will check the
camera's exposure time, which decides how much fast flow is blurred.

### What limits faster velocities

- **Not the search.** Pattern shift (2026-10-08) searches up to half the line's length per frame:
  60 px/frame (2.4 mm/s) on a 120-px line.
- **Blur and line length.** The simulated loops had the shutter open for the whole frame interval
  (the simulator's default and its worst case).
  - A 120-px line on the arterial limb measured up to about 12 px/frame (0.48 mm/s).
  - A 300-px line round the loop measured 12–40 px/frame (0.48–1.6 mm/s) within about 1%
    (`validate_long_line.py`, below).
  - A longer line lets the pattern be followed over more frame distances (at 25 px/frame, six
    instead of one or two), with more positions overlapping.
- **The recordings hide no fast flow.**
  - All 35 lines of the feasibility check were scored at rest and after release, and so were
    lines round 7 whole loops (173–328 px).
  - Everything resolved was slow, 0.04–0.15 mm/s. Nothing faster appeared on any line, though
    the loop lines would reach 1.6 mm/s in simulation.
  - Most capillaries show no moving pattern at all, so at rest the limit is visibility rather
    than speed.
  - The capillaries that can be measured may be the slower ones, whose plasma gaps show. The
    thesis should state this selection.
- **Which limb is arterial.** In every loop with clear flow, blood goes up one limb towards the
  apex (arterial) and down the other. On FP01_Qföre's tall loop the arterial limb is the faster:
  −0.116 mm/s on a 64-px line, against +0.083 on the venous limb (differenced rows).
- **Space-time diagrams** (scratch plots):
  - FP01_Qföre's tall loop shows clear streaks.
  - FP03_Qföre's curly loop shows them only faintly. Coarse filters suggested 0.2–0.3 mm/s
    there; the loop line found nothing, so this is not confirmed.

### Why band-pass

Differencing a row along the line weights each spatial frequency k by (2 sin πk)², most at the
finest scale (2-px patterns). In the recordings that scale is mostly noise, and motion blur erases
it first.

A first comparison (scratch scripts, pattern shift's scores only) found the following:

- **On the recordings,** band-passed rows gave 2–3 times the signal-to-noise on limbs with flow
  (FP01_Qföre's left limb 11.4 → 21.2; FP03_Qefter's loop P 9.6 → 23.9). Lines through tissue
  stayed lower.
- **On the simulator,** the opposite: its cells are crisp 6-px blobs, sharper than the real
  pattern.

### The change (`capillary/pattern_shift.py`)

- **The filter.** `_prepared` band-passes each row along the line with a difference of Gaussians,
  σ 1 and 4 px (`BANDPASS_PX`, `scipy.ndimage.gaussian_filter1d`, reflected at the ends). The
  still structure and the same-moment change are removed first, as before.
  - It passes patterns of about 4–30 px, most strongly near 10 px (gain 0.78).
  - It passes almost nothing at 2 px or 200 px (0.007).
- **The old method stays available.** `bandpass_px=None` differences the rows as before
  (`_block_sums`, `pattern_shift`, `shift_time_course`), to reproduce earlier results.
- **Unchanged:** `MIN_SNR` (8), `MIN_SHIFT_PX` (2 px), `MIN_SPEED` (1 px/frame).
- **Docstrings:** how it works, the range, and the threshold's levels without flow.

### Choosing the band (`analysis/pattern_shift_bandpass/`)

Five bands were compared with the differenced rows: 1–4, 1–6 (the first candidate, from the
scratch comparison), 1–8, 1.5–6 and 2–8 px.

**Synthetic** (`validate_synthetic.py`). 234 clips of 30 s, with a 120-px line drawn on the
simulated arterial limb:

- 12 speeds from 0.5 to 30 px/frame;
- 3 conditions: as measured, strong, and faint (a third of the contrast);
- 3 seeds each;
- the shutter open the whole frame, and at 8–30 px/frame also half the frame;
- 30 clips without flow per condition.

Columns, for the 108 clips with flow and the shutter open the whole frame:

- **Resolved:** clips resolved, out of the 108.
- **Error of those:** median and worst error of the resolved clips.
- **At 1–1.5 px/frame:** median error at the two slowest speeds reported.
- **No flow:** the highest score inside the searched range, with the highest at its slow edge in
  brackets.

| Filter | Resolved | Error of those | At 1–1.5 px/frame | No flow |
| --- | ---: | --- | --- | --- |
| difference | 49 | 0.6% / 4.8% | −1.0 to 0.0% | 4.4 (4.4) |
| band 1–4 | 60 | 0.4% / 5.6% | 0.0 to +0.2% | 5.4 (7.3) |
| band 1–6 | 55 | 0.4% / 6.2% | +0.8 to +1.4% | 6.2 (9.7) |
| band 1–8 | 54 | 0.7% / 12.4% | +2.8 to +6.9% | 6.5 (8.2) |
| band 1.5–6 | 57 | 0.5% / 7.0% | +1.1 to +2.4% | 6.3 (10.5) |
| band 2–8 | 54 | 0.9% / 23.2% | +6.4 to +19.3% | 7.2 (7.6) |

The highest no-flow scores of the band-passes all lie at 1.0–1.5 px/frame, mostly in the strong
condition (three times the measured image jitter). Whole-image jitter moves the still background,
and a band-pass keeps more of it than differencing does. None reached 8 inside the searched range;
the edge itself is never reported.

**Real** (`validate_real.py`). The 35 feasibility lines (29 limbs, 6 through tissue) in 6
recordings, scored over five windows. Columns:

- **Tissue:** the highest score on the tissue lines, over 30 estimates.
- **Limbs resolved:** out of 29, at rest, in the rest's first and second halves, and after release.
  In occlusion, none for any filter.

| Filter | Tissue | Limbs resolved: rest, 1st half, 2nd half, after release |
| --- | ---: | --- |
| difference | 5.6 | 3, 0, 0, 1 |
| band 1–4 | 3.6 | 5, 4, 7, 1 |
| band 1–6 | 4.0 | 5, 5, 7, 4 |
| band 1–8 | 4.7 | 6, 5, 7, 5 |
| band 1.5–6 | 4.7 | 5, 5, 7, 5 |
| band 2–8 | 5.1 | 5, 5, 6, 5 |

**Band 1–4 was chosen, after the validation:**

- **It is the only band that keeps every limb resolved before,** namely FP01_Qföre's 64-px
  arterial limb: differenced 8.7, band 1–4 8.8, the wider bands 5.6–6.6. Arterial limbs are
  short, and they are what the PI asked for.
- **It did best on the synthetic recordings:** the most clips resolved, the smallest error at
  the slow end, and the lowest scores on tissue.
- **The wider bands' extra limbs after release are not faster flow.** All lie at 1.0–1.4
  px/frame (0.040–0.055 mm/s). That is the slow edge, where those bands read 3–19% high on
  synthetic recordings and where no-flow clips scored highest. Band 1–4 put the same limbs at the
  edge, which is not reported.
- **It was chosen on the same data it is validated on;** check it on new recordings.

### Results with the chosen band

**Synthetic, shutter open the whole frame.** Each cell gives the clips resolved (of 3) and the
median error. The two filters are each shown at the measured disturbances and at a third of the
contrast (faint).

| px/frame (mm/s) | Difference, as measured | Band 1–4, as measured | Difference, faint | Band 1–4, faint |
| --- | --- | --- | --- | --- |
| 1.0 (0.040) | 2, 0.0% | 1, 0.0% | 1, 0.0% | 1, 0.0% |
| 1.5 (0.060) | 3, −1.0% | 3, +0.1% | 3, −0.6% | 3, +0.2% |
| 2 (0.080) | 3, +0.2% | 3, +0.1% | 3, +0.3% | 3, +0.1% |
| 3 (0.120) | 3, −0.7% | 3, −0.5% | 3, −1.3% | 3, −0.5% |
| 5 (0.199) | 3, +0.2% | 3, −0.1% | 3, +0.2% | 3, 0.0% |
| 8 (0.319) | 3, +0.4% | 3, −0.4% | 3, +0.8% | 3, −0.4% |
| 12 (0.478) | 2, −3.6% | 3, −4.8% | 0 | 2, −3.9% |
| 16–25 (0.64–1.0) | 0 | 0 | 0 | 0 |
| 30 (1.20) | 0 | 2, −2.9% | 0 | 0 |

- **Faint pattern:** the lowest scores at 1.5–8 px/frame were 14–23 with band 1–4, against 10–18
  for differenced rows.
- **Shutter open half the frame:** both resolve 16 px/frame (band 1–4 in all six clips,
  differenced rows in five). At 20 px/frame, band 1–4 resolves two of six and differenced rows
  one.
- **Intervals:** the truth lay inside the 95% interval for 63% of resolved estimates (differenced
  rows: 69%). The intervals cover the scatter of the blocks only (docstring); systematic errors of
  0.5–5% are not in them.

**Long line** (`validate_long_line.py`). 60-s clips, shutter open the whole frame, 3 seeds; the
lowest score in brackets.

| px/frame (mm/s) | Limb 120 px: differenced | Limb: band 1–4 | Loop 300 px: differenced | Loop: band 1–4 |
| --- | --- | --- | --- | --- |
| 12 (0.48) | 2, −4.2% | 2, −3.6% | 3, −0.6% (35) | 3, −0.3% (36) |
| 16 (0.64) | 0 | 0 | 3, −0.1% (37) | 3, −0.2% (31) |
| 20 (0.80) | 0 | 0 | 3, −0.1% (29) | 3, −0.4% (27) |
| 25 (1.00) | 0 | 0 | 3, −0.8% (18) | 3, −1.1% (15) |
| 30 (1.20) | 0 | 2, −3.5% | 3, −1.7% (14) | 3, −1.2% (14) |
| 40 (1.59) | 0 | 0 | 3, +0.7% (9) | 3, −0.3% (12) |

- **No flow** (8 clips): at most 5.4 (limb, band 1–4) and 4.4 (loop, differenced); none resolved.
- **The simulated loop has one speed all round.** In a real loop the venous limb is slower.

**Real limbs at rest, band 1–4.** In mm/s, with the score in brackets and the differenced rows'
result after "differenced":

- **FP01_Qföre, tall loop, left limb (venous):** +0.084 (18.6); differenced +0.083 (11.4).
  Halves +0.086 and +0.081.
- **FP01_Qföre, tall loop, right limb (arterial, 64 px):** −0.107 (8.8); differenced −0.116 (8.7).
- **FP03_Qefter, loop P, left limb:** +0.058 (15.7); differenced +0.079 (9.6). Halves +0.067 and
  +0.051.
- **FP03_Qefter, loop P, right limb:** −0.042 (18.9); differenced −0.040, at the edge (9.4).
  Halves −0.043 and −0.040.
- **FP03_Qefter, loop S:** +0.051 (10.8); differenced +0.068 (6.2), unresolved. Halves +0.055
  and +0.054.

Notes:

- Three of the five lie at 1.05–1.45 px/frame, near the slowest speed reported.
- On loop P's left limb the two filters disagree, 0.058 against 0.079 mm/s.
  - Its halves differ by 24%, so the flow changes within the minute, and the two filters weight
    the blocks differently.
  - Which is closer is unresolved.

**Loops** (`real_loops.py`):

- **FP01_Qföre's tall loop:** +0.087 mm/s at rest (32.4; differenced 15.7) and +0.145 after
  release (9.5; differenced 4.8, unresolved). The faster flow after the cuff is now measured.
- **FP03_Qefter's loop P:** +0.044 at rest (43.6).
- **The others:** at the slow edge (1 px/frame, scores 8–23: slow flow or drift), or nothing
  (FP03_Qföre's curly loop).
- No loop showed faster flow.

**Benchmark** (`python -m capillary.benchmark`, before and after the change):

- The centre line and the two boxes are identical (216 rows).
- Pattern shift resolved 57 of the 99 cases with flow (56 before) and none without.
- Its errors stay within 1% at 2–8 px/frame, and are −3.1 to −3.6% at 12 (−2.8 to −3.6% before).
- Its scores are higher at 2–3 px/frame (25.7–39.6, against 14.9–31.2) and lower at 5–8
  (14.9–24.1, against 18.5–30.9).

### Tests

- **`test_the_correlation_sums_equal_a_direct_computation`:** now runs for both filters, through
  `_prepared`.
- **New, `test_rows_are_prepared_without_still_structure_and_band_passed`:**
  - a 10-px pattern passes (gain over 0.7);
  - 2-px and 200-px patterns do not;
  - still structure and the same-moment change vanish;
  - `None` differences.
- **`test_pooling_makes_a_faint_pattern_measurable`:** the pattern's contrast went from 1.3 to
  0.4. With band-passed rows, a single 3-s block resolved the old pattern (13.8). Differenced rows
  need about three times this contrast, even pooled.
- **`test_the_interval_holds_the_estimate_and_narrows_with_more_blocks`:** now uses the median
  width over 4 seeds.
  - With band-passed rows the intervals are 5–10 times narrower: 0.013–0.036 px/frame at
    4 px/frame.
  - They narrow less with more blocks: the median ratio of 90-s to 30-s width is 0.83, against
    0.61 for differenced rows, and one seed of eight came out wider.
- **Planted bug:** with the band-pass switched off, 2 tests fail.
- **Totals:** 259 tests pass (257 + 2).
- **flake8:** the CI's error selection is clean on the whole repository, and the full set is
  clean on the changed and new files.

### Open

- **Step 2:** pattern shift on the Centre line page for the arterial limb.
  - the rest window taken from the official times;
  - a direction check;
  - saved as "arterial limb".
- **Step 3:** the arterial limb's speed from a line that continues over the apex. This needs a
  simulator with different speeds in the two limbs.
- **The exposure time,** which the user is checking, decides how much fast flow is blurred.
- **The band on new recordings.** It was chosen and validated on the same 6 recordings. Check it
  on FP03_Wföre, FP04 and FP05 when lines are drawn there.
- **Near the slow edge** (1–1.5 px/frame), band-passed rows are pulled by slow drift; without
  flow, synthetic clips reached 5.4 there. The centre-line method measures that range better.
- **The centre-line method** also differences its rows ("whitening"). Band-passing may help it
  too; not done.
- **Intervals:** the truth lay inside them for 63% of synthetic estimates, so systematic errors
  dominate. Consider an interval that includes them before reporting intervals in the thesis.

---

## 2026-10-11 — The desktop's "stabilized" videos were raw; recordings copied in and stabilized

**Branch:** `docs/unstabilized-desktop-videos`, from `main` at `fc2fc7e`.

**Commits:**

- this entry, with corrections to `CLAUDE.md` and `metadata/README.md` (no code changed)

The user had worked on the Mac and asked to bring the desktop up to date.

- `main` was fast-forwarded from `bb597e2` to `fc2fc7e` (pull requests #9–#13), and the
  merged local branch `data/occlusion-times` was deleted.
- The 257 tests pass under WSL: Python 3.12.3, OpenCV 4.13.0, NumPy 2.4.6, SciPy 1.17.1
  (the Mac has OpenCV 5.0).
- No package was added; `image-registration` is no longer needed.

The user then said the videos in the desktop's `StabilizedVideos/` were probably not
stabilized.

### What the 8 videos were

The 8 files in `StabilizedVideos/` were copied in on 2026-06-11. The app calls every
video in that folder stabilized, and every desktop analysis of 2026-10-06 and 2026-10-07
used them. The 2026-10-08 entries guessed they were the old stabilizer's MPEG-4 output.
They were the raw DynCap recordings, never stabilized:

- **Format** (ffprobe): `rawvideo` without a FourCC, 8-bit palettized grey (`pal8`),
  640 × 480, stamped 30 fps.
  - That is 307 200 bytes a frame plus about 40 bytes of AVI overhead, 0.75–2.3 GB a
    file, the format of the raw downloads on the Mac.
  - The old stabilizer wrote MPEG-4 (FMP4), about 33 MB for a recording.
- **Frame counts** equal those of the Mac's raw downloads for the 5 recordings on both
  computers: FP01_Qföre 5729, FP01_Qefter_försök2 5102, FP01_W 4528, FP01_Wefter 10-13-03
  7524, FP02_Wföre 5765.
- **Movement.** The registration of `capillary.stabilize` was run on each, with the video
  writer replaced by one that writes nothing (scratch script).
  - It gives the movement and median match that the Mac measured on its raw downloads
    (2026-10-08), to 0.1 px and 0.01, despite the different OpenCV.
  - FP01_Qföre: 18.7 × 27.6 px, 0.74. FP01_Qefter_försök2: 25.8 × 24.7, 0.70. FP01_W:
    340.6 × 338.3, 0.08. FP01_Wefter 10-13-03: 47.9 × 90.8, 0.85. FP02_Wföre:
    148.3 × 166.7, 0.47.
  - A stabilized video would hardly move.
- **No trace of a stabilizer.**
  - Frame 0 is not black (the old stabilizer wrote every frame one late).
  - Frames have no black edges where a move would uncover them (13 of FP01_W's 4528
    frames have a dark edge strip).
  - There are no shift files.

### How far they move at rest

Rest is 2 s after the start to 2 s before the official occlusion; registration as above.

| Recording | Used for | Range at rest, x × y (px) | Furthest from the median position (px) | Rest frames > 4 px off | Most within 15 s (px) |
| --- | --- | --- | ---: | ---: | ---: |
| FP01_Qföre | aims 1, 2 | 15.9 × 14.7 | 12.2 | 19% | 18.4 |
| FP01_Qefter_försök2 | aim 2 | 10.3 × 9.1 | 6.5 | 6% | 12.1 |
| FP01_Wefter 10-13-03 | aim 2 | 28.9 × 24.5 | 22.1 | 76% | 30.2 |
| FP01_W 08-36-26 | aims 1, 2 | registration fails (match 0.08) | | | |
| FP02_Wföre | – | 115.3 × 143.0 | 94.4 | 89% | 100.5 |
| FP01_Qefter 09-46-17 | – | 24.3 × 10.7 | 17.3 | 36% | 25.1 |
| FP01_Wefter 10-04-19 | – | 24.4 × 14.5 | 14.1 | 72% | 22.7 |
| FP01_Wefter 10-07-49 | – | registration fails (match 0.09) | | | |

A capillary limb here is 8–15 px wide. So on every recording, a line or box placed on one
frame leaves the vessel during the rest.

### What it changes

- **Measured on a moving picture:**
  - the two-box data sets `Test` and `Test2` of FP01_Qefter 09-46-17 and `set1` of
    FP01_Wefter 10-13-03;
  - the centre-line data sets `set1` and `set2` of FP01_Qefter 09-46-17;
  - the reading set `Validation/reading1` (drawn from `set1`).

  They stay where they are.
- **The two-box verdict** (2026-10-06).
  - About 70% of a box's signal changed along the whole vessel at once. That entry named
    "small movements of the vessel or focus" as the likely cause.
  - A vessel drifting under fixed boxes does exactly that. Test the method again on
    stabilized video before ruling it out.
- **The simulator** was calibrated on the same measurements: the same-moment share, its
  size and its unevenness along the line. The synthetic benchmark may be harder than
  stabilized recordings are; measure these again on stabilized video.
- **Resting flow.**
  - The 2026-10-07 observations were on unstabilized video: near-horizontal streaks at
    rest, and no moving pattern in a row-to-row comparison.
  - The 2026-10-08 entries explained the difference from the re-stabilized video by
    MPEG-4 compression. The files were lossless, so the movement is the likelier
    explanation.
  - The occlusion result on FP01_Qföre (slow, slowing flow from 70 to 130 s) was measured
    on unstabilized video too; measure it again.
- **The app** knows a video is stabilized only by its folder. These showed as stabilized,
  the measure pages gave no warning, and "Stabilize" was greyed out, since it needs a raw
  video.

### The recordings on the desktop now

- **The 8 old files.** The user moved them to `RecordedVideos/` and removed
  `StabilizedVideos/`.
  - FP01_Qefter 09-46-17, FP01_Wefter 10-04-19 and FP01_Wefter 10-07-49 are no longer in
    the data folder. They are earlier attempts that no aim uses.
  - The data sets of FP01_Qefter 09-46-17 are still in `Statistics/`, but the app lists
    only recordings that have a video.
- **Seven new recordings** came from OneDrive (`OneDrive_1_2026-10-11.zip`): the four FP03
  ones downloaded on the Mac, both of FP04's, and FP05_Qefter. The user added "the best",
  the one with the most quality. More are on the way.
- **Each was checked** (scratch script):
  - the name is in NFC and in the official times;
  - rawvideo, 640 × 480, 30 fps;
  - every frame reads and none is black (a copy cut short can hold black frames);
  - the FP03 recordings have the Mac's frame counts;
  - every official occlusion and release falls inside the video at 30 fps.
- **Clean-up.** The 15 `:Zone.Identifier` files Windows had added were deleted.
- **Coverage.** `python -m capillary.inventory --have RecordedVideos`:
  - 9 of the 90 recordings the aims use are here: all of FP01 and FP03, and FP05's
    control efter;
  - 81 are still to come, 44 of them for aim 1;
  - FP02_Wföre and FP04's two recordings are used by no aim. FP02 has one visit, and FP04
    has no W visit.

### Stabilized

Ten recordings were stabilized with the command line, ten at a time, in about 5 minutes:
`python -m capillary.stabilize RecordedVideos/<name>.avi --out StabilizedVideos/<name>.avi`.

- `capillary/stabilize.py` is unchanged since `af1dce6`, the version the Mac used.
- FP01_W and FP03_Wefter were left raw. The stabilizer fails on their large movements
  (2026-10-08), and the app would call a failed output stabilized.

| Recording | Used for | Moved (px) | Match at rest | In occlusion | After release | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| FP01_Qföre | aims 1, 2 | 18.7 × 27.6 | 0.88 | 0.70 | 0.74 | |
| FP01_Qefter_försök2 | aim 2 | 25.8 × 24.7 | 0.70 | 0.84 | 0.65 | |
| FP01_Wefter 10-13-03 | aim 2 | 47.9 × 90.8 | 0.93 | 0.64 | 0.86 | |
| FP03_Qföre | aims 1, 2 | 446.1 × 360.5 | 0.68 | 0.14 | 0.11 | fails once the cuff is on: 419 frames at the search limit |
| FP03_Wföre | aims 1, 2 | 138.8 × 265.4 | 0.60 | 0.66 | 0.59 | 1 frame at the search limit |
| FP03_Qefter_försök2 | aim 2 | 105.7 × 162.1 | 0.63 | 0.66 | 0.61 | |
| FP05_Qefter | aim 2 | 38.0 × 15.9 | 0.88 | 0.81 | 0.80 | |
| FP02_Wföre | – | 148.3 × 166.7 | 0.51 | 0.41 | 0.48 | blurry; references disagree by more than 1 px on 38 frames |
| FP04_Qefter | – | 69.8 × 58.4 | 0.89 | 0.67 | 0.84 | |
| FP04_Qföre | – | 57.6 × 17.1 | 0.88 | 0.85 | 0.82 | |

Match is the median normalized cross-correlation with the references in each phase:

- rest: from 2 s after the start to 2 s before the occlusion;
- occlusion: from 2 s after it to 2 s before the release;
- after release: from 2 s after it.

Results:

- **At rest**, the window both aims use, no frame of the ten is at the search limit, and
  none has references that disagree by more than 1 px.
- **FP03_Qföre's** stabilized video is usable for its rest only.
- **Same as on the Mac.** Where the Mac stabilized the same recording (FP01's three,
  FP02_Wföre, FP03's three), the movement and median match agree to the precision of its
  DEVLOG entry, despite the different OpenCV.
- **The outputs** are rawvideo, 8-bit grey, 640 × 480, 30 fps, each with the raw video's
  frame count, its shift file and its provenance. About 18 GB in all; 916 GB are left on
  the WSL disk.
- **The app.** `gui.library.scan` now lists the ten as "Stabilized" and FP01_W and
  FP03_Wefter as "Raw only".
  - The old two-box `set1` of FP01_Wefter 10-13-03 is now shown over the stabilized
    video.
  - Its boxes were placed on the moving one (and in still tissue, 2026-10-06), so they do
    not fit.
- **Provenance.** The files record commit `fc2fc7e` with uncommitted changes. While the
  runs finished, the working tree held this entry's documentation edits; `capillary/` was
  unchanged.

### Documentation

- `CLAUDE.md`:
  - the data layout and the session start describe raw recordings in `RecordedVideos/`
    and stabilized ones in `StabilizedVideos/`;
  - the known issue about the 8 videos says what they were and what was measured on them;
  - the notes on resting flow, the two-box method, the simulator and `reading1` say they
    rest on unstabilized video.
- `metadata/README.md`: the note on the 8 local recordings says they were raw.

### Verification

- `python -m pytest`: 257 passed after the update, before any change here.
- The checks above, with scratch scripts in the session's scratchpad (not in the
  repository):
  - ffprobe;
  - the registration without writing;
  - a full read of every new recording;
  - `gui.library.scan` on the data folder: before stabilizing, all 12 recordings were
    "Raw only"; after, as above;
  - ffprobe on the ten outputs: format and frame counts;
  - the stabilizer's own summary of each run, read per phase from its shift file.

### Open

- Stabilize the recordings still arriving, after the same checks.
- FP01_W and FP03_Wefter wait for the stabilizer to follow large movements, as do
  FP03_Qföre's occlusion and release.
- Redo the work done on unstabilized video:
  - test the two-box method again;
  - recalibrate the simulator's disturbances;
  - measure FP01_Qföre's occlusion flow again.
- **"The best" recording.** If it means choosing between a visit's attempts by image
  quality, write the rule down before measuring. The inventory takes the last attempt
  with 30 s of rest; so far every recording added agrees with it.

---

## 2026-10-09 — Recording inventory: which recordings the aims use

**Branch:** `feature/recording-inventory`, from `main` at `70b9b12`.

**Commits:**

- this entry, with `capillary/inventory.py`, its tests and `metadata/derived/`

The laptop was overheating, so the user asked for work that does not process
videos. They chose an inventory of the study's recordings, built from the
official times in `metadata/`. It answers how many participants each aim can
use, and which videos to download from DynCap next.

### How (`capillary/inventory.py`)

- **Names.**
  - Each name is parsed: study, subject, condition (W/Q, S/C), role (active
    or control), före or efter, attempt (`_försökN`, or a trailing digit in
    ISMOKE), and start date and time.
  - `FP21Wföre` (no underscore) and `FP01_W_…` (neither före nor efter) are
    understood.
  - Names are compared in Unicode NFC. macOS spells the ö in file names as o
    plus a combining mark, so the first run matched only 1 of the 8 needed
    videos already downloaded.
- **Usable means enough rest.** Both aims use resting CBV, from the rest
  before the occlusion, so a recording needs 30 s of rest (2 s after the start
  to 2 s before the occlusion). A missing release time does not matter.
- **Flags**, not corrections:
  - a name without före or efter (the phase is taken from the time of day);
  - a day with two conditions;
  - a före more than 45 min after the day's first recording (probably an
    efter);
  - a condition recorded on more than one day;
  - too little rest.
- **The choice.** For each participant, the active and the control day each
  get a före and an efter: the last attempt with enough rest, on the
  assumption that a recording was repeated because the earlier attempt failed.
  The other attempts are listed.
  - **Aim 1** needs both före recordings, aim 2 all four.
  - Each aim is "yes", "check" (a chosen recording has an issue) or "no".

### Result

The table and the five recordings to check are in `metadata/README.md`:

- **Aim 1:** 13 + 1 (check) ESMOKE and 9 + 1 (check) ISMOKE participants.
  Visits are a median of 20 days apart in ESMOKE (6–68) and 7 in ISMOKE
  (7–16), and the order of the conditions is balanced.
- **Aim 2:** 12 + 1 ESMOKE and 8 ISMOKE participants.
- **Recordings:** the aims use 90 recordings, 48 for aim 1. Of the 9
  downloaded so far, 8 are among them; FP02_Wföre belongs to a participant
  with one visit only.
- **The checks most likely to change the numbers:**
  - ISMOKE FP02 (an `Sföre` and a `Cefter` on one day) would join both aims
    if the före is a C recording;
  - ISMOKE FP08 (two `Cföre` 107 min apart) would drop out of aim 1 if the
    second is the efter.

### Verification

- `tests/test_inventory.py`, 9 tests on the real metadata:
  - parsing, including the odd names and a decomposed ö;
  - all 124 recordings understood;
  - each kind of flag;
  - the last usable attempt chosen (FP05's fourth before-recording, FP01's
    third after-recording, none for ISMOKE FP04's 6-s rest);
  - the counts per aim and study;
  - the `used_for` marks;
  - matching downloaded videos;
  - the command line.
- Suite: 257 tests. flake8 is clean on the new files.

### Open

- Check the five flagged recordings in DynCap, and correct the choice if the
  labels are wrong.
- Download the 82 recordings still needed (44 for aim 1).
  `python -m capillary.inventory --have <video folder> --out <folder>` writes
  the list (`to_download.csv`).

---

## 2026-10-08 — Resting CBV: a first feasibility check (interrupted)

**Branch:** `feature/fast-flow-estimator`, after `bbf3089` (the entry below).

**Commits:**

- this entry, with two fixes to `capillary/pattern_shift.py`, their tests, and
  `analysis/resting_flow_feasibility/`

The user asked to confirm the finding below on more data: in how many
capillaries can resting flow be measured? The session stopped part-way
because the laptop overheated. It continues on the desktop;
`analysis/resting_flow_feasibility/README.md` says how.

### Two fixes to the pattern-shift estimator

- **The estimate snapped to 2 px/frame.**
  - On FP03_Qefter_försök2, both limbs of loop P came out at exactly
    ±0.080 mm/s (2.00 px/frame), with 95% intervals of zero width.
  - Cause: the rule "count a frame distance only from a 2-px shift" switched
    the consecutive-frame comparison on at exactly 2 px/frame, so the score
    jumped there and the maximum stuck to it. Without the rule, loop P's left
    limb also peaks at about 2.0 px/frame, so the speed was right but the
    interval was false.
  - Each frame distance now fades in between 1 and 2 px of shift and out over
    the last 10% of the largest shift. The score is divided by the root of
    the summed squared weights, so it stays in noise units. Loop P's left limb
    now reads 1.996 px/frame (95% CI 1.951–2.041).
- **A meaningless speed at the edge.** When the best score lay at the slowest
  speed searched (−1.00 px/frame), the parabola that refines the peak used the
  next grid point across the gap, at +1.00, and reported −1.99. The peak is
  now refined only from neighbours on the same side of the grid; such an
  estimate reports the edge, flagged out of range, as before.
- **Tests:** two new ones:
  - speeds of 1.85 and 2.15 px/frame are recovered within 5% (single 30-s
    clips of the test pattern scatter by 2–4% there), with an interval wider
    than zero;
  - flow below the range reports exactly the edge.
  - Suite: 248 passed.
- **Not yet rerun:** the synthetic validation of the fixed version
  (`validate_pattern_shift.py`); it was stopped when the laptop overheated.
  The table in the entry below is for the version before these fixes.

### Stabilizing the other 8 recordings

All were stabilized with the stabilizer of `af1dce6`:

| Recording | Moved (px) | Median match | Result |
| --- | --- | --- | --- |
| FP01_Qföre (from before) | 18.7 × 27.6 | 0.74 | good |
| FP01_Qefter_försök2 | 25.8 × 24.7 | 0.70 | good |
| FP01_W_14-Oct-2019_08-36-26 | 341 × 338 | 0.08 | **failed throughout** |
| FP01_Wefter_14-Oct-2019_10-13-03 | 47.9 × 90.8 | 0.85 | good |
| FP02_Wföre | 148 × 167 | 0.47 | aligned; the recording itself is blurry |
| FP03_Qefter_försök2 | 106 × 162 | 0.64 | good |
| FP03_Qföre | 446 × 361 | 0.15 | rest good (0.68); occlusion and after release failed |
| FP03_Wefter | 343 × 380 | 0.26 | rest mostly failed (0.24) |
| FP03_Wföre | 139 × 265 | 0.61 | good (the breathing-swing recording) |

The three failures are large movements of the finger:

- **FP01_W** drifts steadily by about 200 px over the recording. Its reference
  frame is near the end (141 s), and the early frames are beyond the coarse
  search, so following the previous frame never locks on. It is also the only
  file named without före or efter.
- **FP03_Qföre** jumps when the cuff goes on.
- **FP03_Wefter's** capillaries jump 100–200 px around the frame at rest.

The fix planned: follow the movement outwards from the reference frame in
both directions in time, so no frame is ever searched far from its
neighbour's position.

### The feasibility check

- **Line placement:** on each recording's resting image (the band-passed
  mean between 2 s and 2 s before the official occlusion), points were placed
  by eye along clearly visible capillary limbs. They were moved onto the
  vessel's ridge (within 4 px across) and smoothed. One tissue control line
  per recording runs beside the loops. Lines were chosen from the image alone.
- **Measurements:** each line was measured with the pattern shift over the
  rest window and its two halves, in occlusion and after release, and with
  the centre-line method in 3-s blocks at rest.
- **Files:** `analysis/resting_flow_feasibility/lines.json` and
  `results.csv`. FP03_Qefter_försök2's rows there predate the fixes above.

Six recordings were measured (FP01_W and FP03_Wefter could not be, and
FP03_Wföre is not done yet): 24 limbs and 6 tissue lines.

| Recording | Limbs | Resolved at rest (pattern shift) | Other signs |
| --- | ---: | --- | --- |
| FP01_Qföre | 4 | tall loop: left limb +0.083 mm/s (signal-to-noise 11.6, halves 0.085 / 0.080), right limb −0.116 (9.0) | the 44- and 30-px limbs: none |
| FP01_Qefter_försök2 | 5 | none | loop A: centre line resolved 40% of rest blocks (+0.014 mm/s) on the left limb and 20% (−0.007) on the right: very slow flow, opposite directions |
| FP01_Wefter | 3 | none | right loop at the method's lower edge (slower than 0.04 mm/s) |
| FP02_Wföre | 4 | none | blurry recording |
| FP03_Qefter_försök2 | 7 | loop P left limb: about +0.08 mm/s (9.5) | loop P right limb at the lower edge (score 9.7); loop S +0.068 at 5.7 |
| FP03_Qföre | 6 | none | none, though the limbs are long (up to 139 px) and the rest is well stabilized |

- **Tissue lines** reached at most signal-to-noise 5.3 (FP03_Qefter_försök2);
  none was resolved.
- **Where resting flow was measured,** it was 0.08–0.12 mm/s, on limbs of
  63–122 px. No limb shorter than 50 px was resolved.
- **Why most limbs show nothing.** 5-s space-time pictures at rest show it:
  - where flow was measured, diagonal streaks of plasma gaps run across the
    diagram;
  - on FP03_Qföre's limbs there is only noise. Their brightness changes over
    time with an SD of 1.1–1.2 grey levels, against 1.3 on the tissue line and
    1.5–1.6 on the limbs with flow.

  So at rest these capillaries show no moving pattern in the video. The blood
  column may be too uniform, or the flow fast enough to smear within a frame.
  No image method can measure them at 30 fps.
- **For aim 1:** resting CBV can be measured only in capillaries that show
  plasma gaps, which so far is a minority (3 of 24 limbs resolved, a few more
  near the threshold). Aim 1 needs a rule for choosing capillaries and enough
  of them per recording, and the measurement needs a rule for combining the
  two methods (the pattern shift from about 0.04 mm/s, the centre line below).

### Open (to continue on the desktop)

- Fix the stabilizer for large movements (above), then stabilize FP01_W and
  FP03_Wefter again.
- Measure FP03_Wföre, and remeasure FP03_Qefter_försök2.
- Rerun the synthetic validation of the fixed estimator.
- Decide the measurement protocol: a rule for choosing capillaries (length,
  visible plasma gaps), and a rule for combining the two methods.
- The frame rate (unverified) and the camera's exposure time decide whether
  fast resting flow is invisible or absent.

---

## 2026-10-08 — Resting flow is faint, not fast: the pattern-shift estimator

**Branch:** `feature/fast-flow-estimator`, from `main` at `c2ac5dd`.

**Commits:**

- this entry, with the estimator, its tests, the benchmark and the CLI

Aim 1 (resting CBV) was blocked by the known issue "resting flow is beyond
the centre line's range". The plan was a fast-flow estimator: measure how far
the pattern along a centre line moves between consecutive frames. Testing the
idea on real data first changed the diagnosis.

### Otsu thresholding, considered and not used

The user asked about Otsu thresholding. Otsu was tried on the stabilized
FP01_Qföre in three ways:

- **Raw frame:** it split the picture by the uneven lighting, marking 56% of
  it, half of that background.
- **Band-passed image:** the vessels are too small a share of the picture for
  Otsu to find a split.
- **Temporal SD over 10 s at rest:** rings fixed to the camera optics dominate
  it. They move once the video is stabilized, and Otsu marked 38%, mostly
  rings.

Binarizing the space-time diagram would throw away what the estimators use. So
Otsu was not implemented. Finding vessels automatically (for line placement)
would need a vessel filter and a local threshold, and its own validation.

### Real data first

On 2026-10-07 a crude row-to-row comparison found no moving pattern at rest
(best match always at zero shift, r = 0.06–0.19). That was on the old
stabilized video, which was probably MPEG-4: such compression kept only about
14% of the frame-to-frame change (entry below). It was repeated on the
lossless video from the new stabilizer.

**The first line**, placed by eye (6 points, 119 px), ran partly between the
two limbs of the tall loop. Per-block results were noise, though the
centre-line method still found the occlusion flow on it (12 of 20 blocks at
80–90 s, median 0.011 mm/s).

**A line traced along the left limb's centre** in the resting mean image (10
points, 112 px) showed a forward shift once the correlation was pooled over
2–66 s, rest only:

| Frames apart (k) | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Rest: shift (strength) | +2 px (13.7× noise) | +4 px (7.7×) | +6 px (5.6×) |
| After release | +4 px | +7 px | lost |

So about 2 px/frame (0.08 mm/s) at rest, and about 3.5 px/frame after release.
During occlusion the peak sat near 2 px at every k, so the flow there is under
a pixel per frame.

**The centre-line method on the same line** agreed:
- in 3-s blocks, 8 of 123 rest blocks were resolved, median 0.082 mm/s
  (2.07 px/frame);
- the median slope over all rest blocks was +1.77 px/frame, at signal-to-noise
  4.2, below the threshold of 8;
- with 10-s and 30-s blocks it found +2.15 and +2.77 px/frame, at 3.8 and 5.7.

**Controls**, pooled over the rest, for k = 1, 2, 3:
- the right limb, also drawn top to bottom: −2, −7, −9 px (6.9×, 3.5×, 3.5×),
  the opposite direction;
- tissue 22 px beside the limb: −33, −1, +16 px (2.5×, 4.0×, 2.0×), no
  pattern.

So on this capillary the blood goes down one limb at about 0.08 mm/s and up the
other at about 0.12 mm/s, within the centre line's range (up to 0.2 mm/s on
112 px). It is too faint for single 3-s blocks. The 2026-10-07 reading of
"faint, almost horizontal streaks, roughly 0.5–1 mm/s" was probably the change
of the whole vessel at once, which draws horizontal lines, seen in the
compressed video. The known issue in CLAUDE.md is revised accordingly. This is
one capillary of one recording.

### The estimator (`capillary/pattern_shift.py`)

On the same space-time diagram:

1. In each 3-s block, the still structure and the same-moment change are
   removed and the rows differenced, as in `capillary.spacetime`.
2. For frame distances k = 1–8, row t is correlated with row t + k at every
   shift up to half the line. Numerators and energies are pooled over every row
   of every block (an FFT per row, checked against a direct sum in a test).
3. Forward minus backward correlation (direction contrast), in units of each
   k's own spread over shifts.
4. A speed's score is the sum over the k where it needs a shift of 2 px to half
   the line, divided by the square root of their number. The best speed (step
   0.01 px/frame, refined by a parabola) is the estimate, and its score the
   signal-to-noise ratio.
5. A 95% interval comes from leaving out one block at a time (jackknife).

Settings, each checked on data:

- **Signal-to-noise of 8 to count:** without flow it reached at most 3.9 on 30
  synthetic recordings (5.2 before the minimum-shift rule below), and at most
  4.3 on two tissue lines of FP01_Qföre in any phase.
- **Slowest speed 1 px/frame:** at 0.5 px/frame it read 4–8% high, where the
  centre-line method is exact.
- **Minimum shift of 2 px per frame distance:** on synthetic recordings 2 and
  3 px both lowered the error near 1 px/frame slightly (worst 0.8–0.9% against
  1.3% with none). On the real limb, 3 px dropped the comparison of
  consecutive frames at 2 px/frame. That one is the strongest there, because
  the blood rearranges within a few frames, and dropping it lowered the
  signal-to-noise from 13.7 to 9.7 and left both 30-s halves unresolved. With
  2 px the real results are unchanged.
- **The intervals cover the statistical scatter only.** In the synthetic runs
  they often missed the truth by about 1%, a systematic error probably from
  the drawn line's geometry. This is said in the docstring.

**Validation on synthetic recordings** (final settings): 138 clips of the
simulated loop, 30 s each, a 120-px hand-drawn line, motion blur for the whole
frame interval, 3 seeds per speed. The conditions are "as measured", "strong",
and "faint" (a third of the cells' contrast). Each cell shows the median error
with the worst in brackets, then the lowest signal-to-noise:

| Speed px/frame (mm/s) | As measured | Strong | Faint | Centre line, blocks resolved (as measured) |
| --- | --- | --- | --- | --- |
| 0.5 (0.020) | not reported, 2.1 | not reported, 2.0 | not reported, 2.2 | 100%, +0.1% |
| 1 (0.040) | +0.5% (0.5), 14.2 | +0.5% (0.5), 15.7 | +0.5% (0.5), 12.0 | 100%, +0.1% |
| 2 (0.080) | +0.2% (0.6), 13.9 | +0.2% (0.3), 14.6 | +0.8% (2.2), 12.8 | 100%, +0.5% |
| 3 (0.120) | −1.1% (1.2), 25.7 | −1.3% (1.5), 24.0 | −0.6% (1.3), 20.6 | 100%, +0.5% |
| 5 (0.199) | +0.2% (0.6), 25.8 | +0.6% (1.3), 21.3 | 0.0% (2.1), 18.1 | 80%, −1.5% |
| 8 (0.319) | +0.4% (0.7), 15.9 | +0.3% (0.7), 14.9 | +0.4% (3.5), 10.7 | 0% |
| 12 (0.478) | −0.1% (0.1), 9.5 | −0.1% (0.1), 9.1 | −3.1% (6.5), 5.8 | 0% |
| 16 (0.638) | −6.3% (6.3), 5.5 | −6.3% (6.3), 5.0 | −9.4% (9.6), 4.0 | 0% |
| 20–40 (0.80–1.60) | signal-to-noise 2.7–5.2 | 2.5–4.7 | 2.8–4.1 | 0% |

- **No flow** (10 clips per condition): the signal-to-noise reached at most 3.4,
  3.9 and 3.7.
- **Resolved in every seed:** from 1 to 12 px/frame as measured and strong,
  and up to 8 px/frame when faint.
- **Truth inside the 95% interval:** in 1 to 3 of the 3 seeds, mostly missed by
  about 1%. The intervals are statistical only (above).

### On FP01_Qföre with the final version

- **Left limb:**
  - rest: 0.0819 mm/s (95% CI 0.0747–0.0891), signal-to-noise 13.7;
  - first 30 s: 0.084 mm/s (8.5); second 30 s: 0.080 mm/s (9.1);
  - one 3-s block: 3.8, not resolved;
  - occlusion: below the method's range, which is right; the centre line
    measures it;
  - after release: 0.145 mm/s at 4.5, not resolved.
- **Right limb:** −0.116 mm/s at rest (5.8, not resolved; a 76-px line).
- **Tissue lines:** at most 4.3, with random speeds.

### What changed

- `capillary/pattern_shift.py` (new): `pattern_shift` for one stretch,
  `shift_time_course` for successive windows.
- `tests/test_pattern_shift.py` (new, 18 tests), checking:
  - the FFT sums against a direct computation;
  - known speeds from 1.5 to 14 px/frame despite same-moment changes;
  - reversed flow;
  - no flow, and a much stronger same-moment change, not resolved;
  - a pattern flickering in place not read as flow;
  - flow slower than the method not reported;
  - pooling making a faint pattern measurable;
  - the interval holding the estimate and narrowing;
  - unusable input; the time course;
  - a synthetic recording with motion blur, where fast flow is either right or
    unreported.
- `capillary/benchmark.py`: a third method, and speeds 16 and 25 px/frame
  added.
- `capillary/cli.py`: for a line, it also prints the pooled pattern-shift
  velocity, its interval and signal-to-noise.
- README ("Pattern shift"), CLAUDE.md (the engine, and the resting-flow known
  issue revised).

### Verification

- 246 tests pass. flake8's CI selection is clean, as is a full run on the new
  and changed files.
- Planted bugs:
  - a flipped sign fails 7 tests;
  - no conversion to noise units fails the faint-pattern test;
  - no direction contrast fails the reversed-flow test. Without it the
    flickering pattern did read as 10.0 px/frame, but at signal-to-noise 2.6,
    so that test passes either way.
- `python -m capillary.benchmark --quick` runs with the new method. In 10-s
  clips it resolves 2 and 6 px/frame within 1%. At 6 px/frame the centre line
  resolves at most 13% of blocks, 16% low.

### Open

- **The app:** show the pooled velocity on the Centre line page (the rest
  window as default stretch), and save it with the data set.
- **More recordings:** more capillaries and recordings. Stabilize the other 8
  downloaded recordings and repeat the left-limb check on several capillaries
  each.
- **Frame rate:** still unverified. Every velocity scales with it.
- **Above about 16 px/frame** the synthetic signal-to-noise falls below the
  threshold, probably from motion blur. The real exposure time is unknown.
- **The camera-fixed rings** drift through the stabilized picture. They look
  like near-zero flow and could bias slow-flow measurements; worth checking.

---

## 2026-10-08 — A new registration for the stabilizer

**Branch:** `fix/stabilizer-registration`, from `feature/streaming-stabilizer` at
`dde2fd7` (the entry below); merge `fix/macos-tk9` and that branch first.

**Commits:**

- `98f74ba` Stabilizer registration: band-pass, averaged references, template matching
- `af1dce6` Stabilizer: follow large movements, references from the sharpest frame's neighbours, re-centre
- this entry, with README and CLAUDE.md

The entry below found that the stabilizer's registration falls short by
several pixels where the image has moved far. The user asked for it to be
fixed. The method changed in two steps: first against FP01_Qföre, then again
after a second recording, FP03_Wföre, broke the first version. All scratch
scripts are outside the repository; the numbers here are what they printed.

### Choosing the method on known shifts

**The synthetic test.** One real frame of FP01_Qföre was used as the scene.
Its own lighting was divided out (by its 40-px blur), it was moved by known
sub-pixel amounts and cropped to 560 × 400. It was then multiplied by lighting
that stays with the camera (darker to the corners, a left-right gradient), and
smooth changing content and noise were added. Each method registered every
frame against an unmoved one. Error against the truth (mean |x|, mean |y|,
largest), and the time per registration:

| Method | Moves up to ±6 px | x ±10, y ±25 px | ms |
| --- | --- | --- | ---: |
| Old: CLAHE + median, circular upsampled | 0.19, 0.32, 0.66 | 0.32, 0.73, 1.98 (mean y error +0.46: too short) | 18 |
| DoG + window, circular upsampled | 0.05, 0.05, 0.18 | 0.04, 0.06, 0.15 | 23 |
| DoG + template match, parabola | 0.06, 0.06, 0.20 | 0.05, 0.06, 0.17 | 8 |
| DoG + template match, Gaussian peak fit | 0.06, 0.06, 0.20 | 0.04, 0.06, 0.16 | 8 |
| DoG + template match, ECC refinement | 0.06, 0.06, 0.20 | 0.05, 0.06, 0.14 | 16 |
| DoG + template match, upsampled refinement | 0.05, 0.06, 0.23 | 0.05, 0.06, 0.16 | 23 |

DoG is a difference of Gaussians with σ 1 and 10 px; the band-pass removes the
lighting without depending on position.

**On real frames.** Every 30th frame of FP01_Qföre was registered against its
three sharpest single frames. The references disagree (median px, rest /
occlusion / after release), and the edge similarity to frame 63 (mean, same
order):

| Method | Disagreement | Edge similarity | Closure 63→210→463 |
| --- | --- | --- | ---: |
| Old | 2.19 / 3.55 / 3.32 | 0.548 / 0.345 / 0.354 | 1.47 px |
| DoG + window, upsampled | 0.60 / 0.83 / 0.78 | 0.560 / 0.393 / 0.419 | 0.27 px |
| DoG + match, parabola | 0.56 / 0.79 / 0.71 | 0.559 / 0.393 / 0.418 | 0.28 px |
| DoG + match, ECC | 0.68 / 1.01 / 0.92 | 0.559 / 0.392 / 0.419 | 0.26 px |

Template matching with a parabola was as good as any other method and the
fastest, so it was chosen.

**Averaged references.** The remaining ~0.6 px came from the references:
single frames differ by the blood moving in them. Noise of one estimate was
measured split-half. Each frame was registered against two references made
from different frames, and the spread of the difference (robust, divided
by √2) was taken. This measures only the reference's share of the noise.
Results (x/y px, rest / occlusion / after release):

| Band-pass σ (px) | Single sharp frames | Mean of 12 aligned sharp frames each |
| --- | --- | --- |
| 1 and 10 | 0.20/0.18, 0.26/0.44, 0.31/0.32 | 0.08/0.05, 0.04/0.07, 0.10/0.05 |
| 1.5 and 6 | 0.20/0.21, 0.29/0.30, 0.34/0.43 | 0.05/0.05, 0.04/0.07, 0.06/0.06 |
| **2 and 15** | 0.12/0.19, 0.12/0.32, 0.15/0.16 | **0.02/0.02, 0.02/0.02, 0.03/0.02** |
| 1 and 5 | 0.25/0.37, 0.63/0.79, 0.61/0.51 | 0.13/0.08, 0.11/0.16, 0.15/0.14 |

**Interpolation.** Moving a frame by a fraction of a pixel with bilinear
interpolation blurs it by an amount that depends on the fraction. The share of
detail kept on a real frame, for shifts of 0, 0.25 and 0.5 px:

| Scale | Bilinear | Bicubic |
| --- | --- | --- |
| Finest, 0.5–1.5 px | 1.00, 0.72, 0.62 | 1.00, 0.94, 0.88 |
| Fine, 1–3 px | 1.00, 0.92, 0.89 | 1.00, 1.01, 1.02 |
| Cell scale, 2–6 px | 1.00, 0.99, 0.98 | 1.00, 1.00, 1.01 |

So the output now uses bicubic interpolation.

### First version (`98f74ba`) and what FP03_Wföre showed

The first version used:
- the band-pass with σ 2 and 15 px;
- two references, each the mean of every other one of the 24 sharpest frames,
  moved onto the sharpest;
- template matching of the frame's centre over ±64 px;
- a parabola for the fraction of a pixel;
- bicubic output.

It also wrote three new columns: a match score, the disagreement between the
two references, and a flag when the best offset lies at the edge of the
search. The edge flag alone caught only 2 of 17 synthetic frames moved beyond
the search; a frame far beyond lands on a false peak inside it, with a low
match. On FP01_Qföre it was good: the references disagreed by a median of
0.03 px, and there were no flags. It took 136 s.

Stabilizing a second recording as a check, FP03_Wföre, failed on most frames:
- median match 0.23;
- 3366 of 5819 frames at the search limit;
- shifts over the whole ±64 px.

The recording is dark (grey level about 53, SD about 4). A coarse wide search
on quarter-size frames showed the image moving 72 px up and 104 px down at
rest and during occlusion. The montage confirmed this. The movement swings
regularly, about every 3 s (a breath), by around 200 px. Its sharpest frames
all lay around 100 s, during the occlusion, at one extreme; the sharpness
hardly varies in this recording (0.0082–0.0084), so they were close to an
arbitrary choice.

### Second version (`af1dce6`)

- **Coarse then fine.** A coarse search on frames reduced 4 times reaches a
  third of the frame (±160 px). The fine search then looks within 12 px of two
  candidates, the coarse result and the previous frame's position, and keeps
  the better match; a match inside its search beats one at its edge.
  - The previous frame lets the search follow movement beyond the coarse
    reach. Each frame is still registered against the fixed references, so
    errors do not add up.
  - The fine search compares the largest part of the frame that stays inside
    the reference.
- **The references** are now built from the sharpest frame and the 12 frames
  on each side of it, aligned outwards from it with the previous position as a
  guide.
  - A frame is kept only if aligning it onto the sharpest frame and back gives
    opposite shifts, to within 1 px.
  - Without that check, a synthetic test with random jumps beyond the coarse
    reach put falsely aligned frames into the reference. The reference then
    held the scene twice, 35 and 47 px apart, and half the frames were
    silently 47 px off with a believable match of 0.65–0.70.
- **Re-centring.** The shifts are re-centred on their median before writing,
  so the picture sits where the recording usually is. This needs a third
  reading.
- **The edge preference.** The first run of the tests caught one frame found
  correctly (match 0.98) and still flagged. The search around the previous
  position had reached the same peak at its edge, with a match higher in the
  fourth decimal.

### Verification

- **Tests:** `tests/test_stabilize.py` now has 16 tests (228 in the suite).
  The new and rewritten ones check:
  - the band-pass moves with the image and drops a lighting field;
  - the shifts undo moves of ±5 px to within 0.15 px (largest error 0.06–0.08
    px over 4 seeds, against 0.31–0.39 for the old registration);
  - moves of x ±10, y ±25 px under camera-fixed lighting are undone to within
    0.15 px (0.05–0.07);
  - following the previous frame tracks a 130-px drift where the coarse search
    reaches 80 px, which fails without it;
  - with random jumps beyond the reach, every frame is either right (under
    0.15 px) or marked (low match or at the limit), and none within reach is
    marked;
  - the references are the sharpest frame and its neighbours;
  - memory does not grow from 60 to 180 frames.

  Each of five planted bugs fails at least one test: CLAHE tiles back in front
  of the band-pass, whole pixels only, a wrong direction, no edge flag, and no
  following of the previous frame. flake8 is clean.
- **FP01_Qföre** (5729 frames), with the final version:
  - 135 s, at most 194 MB of memory;
  - the image moved over 18.7 × 27.6 px; the references disagree by a median of
    0.03 px (0 frames over 1 px); median match 0.74 (lowest 0.66);
  - every frame equals its recorded frame moved by its saved shift.

  Edge similarity to frame 63, mean (worst):

  | Phase | Unaligned | Old registration | New registration | New better on |
  | --- | --- | --- | --- | --- |
  | Rest | 0.406 (0.219) | 0.565 (0.418) | 0.560 (0.420) | 43 of 137 |
  | Occlusion | 0.304 (0.221) | 0.366 (0.323) | 0.384 (0.346) | 118 of 124 |
  | After release | 0.325 (0.210) | 0.386 (0.322) | 0.411 (0.347) | 121 of 121 |

  - At rest the two registrations differ by a median of 0.9 px vertically. On
    the two rest frames where they differ most (2.2 and 3.7 px), the new one
    matches better (0.537 vs 0.521, 0.415 vs 0.403). Overlays show the old
    alignment offset and the new one overlapping.
  - The small average preference for the old one at rest is unexplained. A
    measure that favours small shifts, through anything fixed to the camera,
    is a guess.
  - Movement left between consecutive output frames, by phase correlation
    (robust SD, x/y px):

    | Phase | Unstabilized | Old | New |
    | --- | --- | --- | --- |
    | Rest | 0.077/0.064 | 0.069/0.067 | 0.072/0.070 |
    | Occlusion | 0.082/0.074 | 0.090/0.107 | 0.092/0.102 |
    | After release | 0.085/0.073 | 0.082/0.096 | 0.088/0.088 |

    The recordings drift rather than shake: both registrations leave about the
    raw video's own frame-to-frame movement, well below the 0.2–0.3 px that
    troubled the centre line.
- **FP03_Wföre** (5819 frames), stabilized into the scratch folder (not the
  data folder):
  - 135 s, at most 181 MB;
  - the image moved over 139 × 265 px;
  - by phase:

    | Phase | Match median (lowest) | Disagreement median | Frames over 1 px |
    | --- | --- | --- | --- |
    | Rest | 0.60 (0.53) | 0.14 px | 0 |
    | Occlusion | 0.66 (0.49) | 0.10 px | 0 |
    | After release | 0.59 (0.36) | 0.13 px | 6 |

  - 1 frame at the search limit (frame 3224);
  - frame-to-frame jumps: median 1.5 px, 99th percentile 8.0 px.
  - The 12–16 px jumps (70.5 s just before the cuff, 107, 158, 178, 192 s) keep
    normal match and low disagreement.
  - The largest, 42 px from frame 0 to frame 1, is real: frame 0 shows the
    capillaries clearly lower and to the right. It is probably a camera
    start-up artefact.
  - A montage of the stabilized output at 0–180 s shows the same capillary
    loop in the same place throughout.
- `FP01_Qföre` in `StabilizedVideos/` was stabilized again with the final
  version (provenance at `af1dce6`).

### Open

- Checked on two recordings only. The settings (σ 2 and 15 px, 25 reference
  frames, a coarse reach of a third of the frame, a fine reach of 12 px) were
  chosen on them. Check each recording's summary in its shift file: match,
  disagreement, frames at the search limit.
- Translation only. FP03_Wföre's movement is so large that up to about half of
  some frames is lost at the edges; a capillary near the top or bottom may be
  out of view for part of each breath.
- A recording that starts more than a third of the frame away from its
  sharpest frame loses its first frames until the movement comes within reach;
  those frames are marked by a low match.
- On the desktop: run the tests, since the uncompressed grey writer was checked
  only with OpenCV 5.0 on macOS. Check the codec of the 8 old stabilized videos.

---

## 2026-10-08 — The stabilizer reworked: read from disk, lossless, in step

**Branch:** `feature/streaming-stabilizer`, from `fix/macos-tk9` at `55f201e` (the
entry below); merge that branch first.

**Commits:**

- `0a1988b` Stabilizer read from disk, lossless and in step (capillary.stabilize)
- this entry

The user asked whether the stabilizer needed work before stabilizing the
downloaded recordings, and then to make it use less memory. The method stays
the same; how it runs, what it writes and how fast it is changed.

### What a review and tests found

Tests on FP01_Qföre (scratch scripts, not in the repository) showed:

- **Memory.** `Caper.VideoStabilization` held two float64 copies of the whole
  video: 22–37 GB for the 9 downloaded recordings (4528–7524 frames). That was
  impossible on the 8 GB Mac and probably on the desktop too, since WSL gets
  half of the PC's memory by default.
- **Lossy output.** It wrote MP4V into an `.avi`; FFmpeg falls back to the
  FMP4 tag, which is the same MPEG-4 Part 2 codec. On the first 15 s of
  FP01_Qföre:
  - 207 MB became 3.0 MB;
  - the error against the same shifts written uncompressed was 4.6 grey levels
    RMS (PSNR 34.9 dB), larger than the raw video's own frame-to-frame change
    (3.05);
  - the frame-to-frame change correlated only r = 0.38 with the uncompressed
    one (r² ≈ 0.14), and the moving cells show up in that change.
- **One frame late** (known since 2026-10-05): frame 0 black, frame k holding
  recorded frame k−1, the last frame dropped. This was confirmed again.
- The writer was fixed at 30 fps and 640 × 480; a video of another size would
  have been written empty without an error.
- **Slow:** 239 ms a frame, two-thirds of it in `scipy.signal.medfilt`.
- **The registration itself works.**
  - On a synthetic clip (one real frame moved by known shifts) the direction
    is right: the correction correlates −0.999 with the movement, leaving
    about 0.3 px.
  - On the real clip its alignment matches a reference frame better than plain
    phase correlation (similarity 0.980 against 0.964, and 0.959 unaligned).
    It is never worse by more than 0.02 and better on 120 of 450 frames.
  - FP01_Qföre drifts by up to about 11 px at rest within those 15 s. A
    capillary limb is about 8–15 px wide here, so the recordings need
    stabilizing before a centre line is drawn.
  - A first check by phase correlation had suggested the stabilizer added
    motion, and the interim report to the user said so. That check was the
    one failing: its peak response fell to about 0.01 on the frames in
    question.

Also found, and **not changed** here because it changes the results: the
contrast enhancement before the registration (CLAHE on a fixed 3 × 3 grid of
tiles) changes as the image moves. On known shifts of one real frame the error
was 0.21 px (x) and 0.50 px (y) on average, up to 0.87 px, against 0.08 px
without the enhancement. That is close to the slowest speeds the centre line
measures (about 0.2 px/frame). It needs its own change and verification
(CLAUDE.md, known issues).

Side finding: the DynCap downloads are uncompressed 8-bit grey AVI, so the
archive is stored losslessly. That answers an open point in the entry on the
Capture page's removal (the thesis draft says the recordings were stored
losslessly).

### What changed

- **`capillary/stabilize.py`** (new) runs the same method in two readings of
  the file:
  1. Every frame's sharpness (`quality.calculate_blur`) is computed, and the
     three sharpest frames are kept as they come along.
  2. Each frame is enhanced (CLAHE 7.65, 3 × 3 tiles; 7 × 7 median), registered
     against the three enhanced references to 1/100 px, moved by the mean of
     the three shifts (bilinear) and written.

  Only a few frames are in memory at a time. Differences from the old code:
  - **Median filter:** OpenCV's median on a zero-padded copy, equal to
    `scipy.signal.medfilt` (checked on real frames and in a test) and much
    faster.
  - **Rounding:** the moved frame is rounded to whole grey levels; the old
    code truncated, which darkened every frame by half a grey level on
    average.
  - **Output:** uncompressed 8-bit grey AVI at the source's frame rate and
    size. Output frame k is recorded frame k.
  - **Record:** next to the video, `<stem>___stabilization.csv` holds every
    frame's shift, how far the three references disagree once their fixed
    offsets are removed, its sharpness, and whether it is a reference.
    `<stem>___stabilization_provenance.json` holds the settings, the
    reference frames, a summary (how far the image moved, the largest jump
    between frames, the disagreement) and the git commit.
  - **Robustness:** progress and cancel work as in the measurements, and a
    failed or cancelled run removes its partial output.
  - **Command line:** `python3 -m capillary.stabilize <raw> --out <stabilized.avi>`.
- **`capillary/registration.py`** is `SingleStepDFT.py`, moved into the package
  (`git mv`) with only its docstring changed.
- **`Caper.py`** loses `Video` and `VideoStabilization`, and the imports only
  they used.
- **`Utilities.py`** is removed: `clahe` and `median_filter` are replaced in
  `stabilize.py`, and nothing used its re-export of `calculate_blur` (its test
  in `test_velocity.py` goes too).
- **`gui/tasks.py`:**
  - `stabilize` runs the new module and always writes `<stem>.avi`.
  - Stabilizing again moves the previous video and its two files to the trash.
  - `recording_files` includes the two files, so moving a recording to the
    trash takes them along.
  - A disk-space check replaces the memory check. The memory check's macOS
    fallback from `a71f270` goes with it; there is nothing left to check.
- **Docs:** the README gains "How a recording is stabilized", the command
  line, the new files and the code layout. CLAUDE.md gets the data layout, the
  engine, the test count and the known issues, and docstrings in `quality.py`
  and `video.py` were updated.

### Verification

- **Same shifts as before.** A lossless 450-frame clip of FP01_Qföre (frames
  0–449) was run through the old `VideoStabilization` (before any change, at
  `55f201e`) and through the new code:
  - the same reference frames (63, 210, 27);
  - shifts bit-identical for recorded frames 0–448 (the old code's frames
    1–449);
  - enhancement identical to scipy's on 20 real frames;
  - every output frame equal to its recorded frame moved by its shift, 450
    frames, frame 0 no longer black;
  - 105 s for the old code, 40 s (88 ms a frame) for the new.
- **Tests:** 13 new tests in `tests/test_stabilize.py`. A textured scene moved
  by known sub-pixel amounts (±5 px), written losslessly, then:
  - the shifts undo the movement to within 0.5 px (largest error 0.31–0.39 px
    over 4 seeds);
  - every frame is written in its place and losslessly, at the source's frame
    rate and size;
  - the stabilized frames line up;
  - the references are the sharpest frames;
  - traced memory does not grow with the length (+0.01 MB from 30 to 150
    frames, against 2.3 MB if the frames were kept);
  - the record files; cancelling; `.avi` only; the command line;
  - the GUI job: where it files the video and its record, the trash on a
    second run, cancelling, too little disk space.

  Three bugs were planted to check that the tests catch them:
  - a wrong shift direction was caught by the line-up test;
  - keeping every frame in memory was caught by the memory test;
  - the old one-frame lag was caught by three tests.

  Suite: 225 passed (215 before, minus the 2 memory tests and the
  `Utilities` test, plus the 13 new tests). The CI's flake8 selection is
  clean, and so are the new and changed files under a full flake8 run.
- **A full recording.** FP01_Qföre (5729 frames, 191 s) was stabilized through
  the GUI's job (`gui.tasks.stabilize`) into the data folder on the Mac:
  - 537 s (94 ms a frame), with at most **278 MB** of memory (macOS
    `time -l`), against about 28 GB for the old code;
  - 5729 frames at 30 fps, 1.76 GB like the raw file, and every frame equal to
    its recorded frame moved by the shift saved in the CSV (0 of 5729 differ);
  - similarity to the frame at 30 s improved in every phase (mean, and worst
    frame in brackets):

    | Phase | Unaligned | Stabilized |
    | --- | ---: | ---: |
    | Rest | 0.972 (0.912) | 0.981 (0.955) |
    | Occlusion | 0.891 (0.851) | 0.940 (0.930) |
    | After release | 0.902 (0.836) | 0.953 (0.934) |

  - the image moved up to 11.4 px from its resting position at rest, and up to
    about 20 px during occlusion and after release, mostly vertically; the
    largest jump between two frames was 4.5 px.

### The registration's accuracy on the full recording

The CSV's first definition of `disagreement_px` removed the references'
offsets as their median over all frames. It came out above 1 px on 4069 of
5729 frames: 4.9 px (median) close to the references and about 1 px far
from them, changing smoothly from frame to frame. That pointed to a
registration bias that depends on where the image is, so 12 frames were
checked against an independent estimate:

- **The independent estimate:** a template match of the frame's centre
  (580 × 420 px) after a high-pass filter (frame minus its 10-px Gaussian
  blur), which removes the uneven lighting and does not depend on position.
- **Self-consistency.** Across the three references, the independent
  estimates agree with the references' own offsets to within about 0.8 px.
  The stabilizer's contradict each other by up to 3 px.
- **During occlusion and after release** (80–187 s) the two differ by
  2.8–5.6 px vertically: the stabilizer's correction is too small.
- **At rest** they differ by 1.3 px at most (0.4–0.9 px on most frames).
- **A third measure decided between them:** the correlation of edge strength
  (Sobel magnitude) with the reference frame, used by neither method.
  - It favours the independent alignment on all 9 frames compared:
    slightly at rest (0.558 against 0.554, for example) and clearly during
    occlusion (0.403 against 0.343 at 100 s, with 0.328 unaligned).
  - An overlay of the 100-s frame on the reference shows the capillary loop
    offset with the stabilizer's correction and overlapping with the
    independent one.

So the method, old and new alike, falls short by several pixels when the
image has moved 15–20 px from the references, and is good to about a pixel at
rest. The likely cause is the enhancement before the registration (fixed CLAHE
tiles, see above), possibly together with the circular cross-correlation of
unwindowed frames. Resting CBV (aim 1) is measured at rest, where the error is
smallest. Lines drawn for the occlusion phase would drift off a vessel by up
to 5 px.

`disagreement_px` was redefined to remove the offsets between the references
as measured on the sharpest reference, where the registration is reliable.

FP01_Qföre was then stabilized again from the command line with the committed
code (`0a1988b`), replacing the first output:
- 555 s, 275 MB at most;
- the video is unchanged, and the CSV has the new column;
- its provenance says `git_uncommitted_changes: true` only because this
  DEVLOG entry was being edited during the run.

The column now reads, as a median (90th percentile in brackets):

| Phase | Disagreement |
| --- | ---: |
| Rest | 2.1 px (3.2) |
| Occlusion | 3.5 px (4.3) |
| After release | 3.3 px (4.0) |

It is highest where the shift falls shortest. It is also well above 1 px at
rest: there the estimate against the reference that lies 9 px from the other
two (frame 463) is off by up to about 1.8 px. That is still about 1 px in the
mean shift, as found above. Until the registration is fixed, the column shows
how unreliable it is rather than singling out a few bad frames.

### Also found: a video stabilized with the old code

At 10:50 the app, started at 10:27 and still running, stabilized
`FP01_Qefter_försök2_22-Oct-2019_09-50-15` with the old code. That output is
FMP4 (lossy), 33 MB, with a black frame 0. The app was started before the
memory check got its macOS fallback, so nothing stopped the run (about 25 GB
asked of an 8 GB Mac). It is still in `StabilizedVideos/`: stabilizing it
again in a restarted app moves it to the trash.

### Open

- **The registration's accuracy (above):** the next step. Use a translation-
  invariant enhancement (such as a high-pass filter instead of fixed CLAHE
  tiles) and a windowed or non-circular correlation. Check it with the three
  measures used here: an independent estimate, self-consistency across the
  references, and edge similarity. Add synthetic tests with moves of 15–20 px.
- Speed: about 88 ms a frame (about 8 minutes for a 3-minute recording),
  mostly the three registrations per frame with their 2 × upsampled
  cross-correlation. Computing the references' FFTs once would save part of
  it.
- On the desktop: run the tests there, since the uncompressed grey writer was
  checked only with OpenCV 5.0 on macOS. Check the codec of the 8 old
  stabilized videos.
- Lines drawn on an old stabilized video may not fit a newly stabilized one
  (different reference frames, and the one-frame shift is gone).

---

## 2026-10-08 — First run on macOS with the downloaded study recordings

**Branch:** `fix/macos-tk9`, from `main` at `f9e0917`.

**Commits:**

- `a71f270` Run on macOS with Tk 9: clamp canvas text widths, memory guard without /proc

The user downloaded 9 raw ESMOKE recordings from DynCap into
`Video_inventory/` (untracked) on a new computer, a MacBook with an Apple M2
and 8 GB of memory, and asked whether the program works with them. Until now
the app had only run under WSL on Windows.

### The recordings

All 9 open with OpenCV 5.0: 640 × 480, 8-bit grey stored uncompressed (no
FourCC, 307 200 bytes a frame), stamped 30 fps, 4528–7524 frames (151–251 s).
They are raw, not stabilized. All 9 are in `metadata/ESMOKE_timestamps.csv`,
and each official release falls well inside the video at 30 fps, so the
frame-rate mismatch of `FP01_Wefter_14-Oct-2019_10-07-49` does not show here.
`FP03_Wefter_21-Oct-2019_10-21-58` has no release time.

| Recording | Frames | Length at 30 fps (s) | Occlusion (s) | Release (s) |
| --- | ---: | ---: | ---: | ---: |
| `FP01_Qefter_försök2_22-Oct-2019_09-50-15` | 5102 | 170.1 | 65.9 | 125.7 |
| `FP01_Qföre_22-Oct-2019_08-16-35` | 5729 | 191.0 | 68.3 | 130.5 |
| `FP01_W_14-Oct-2019_08-36-26` | 4528 | 150.9 | 37.6 | 102.3 |
| `FP01_Wefter_14-Oct-2019_10-13-03` | 7524 | 250.8 | 62.5 | 147.4 |
| `FP02_Wföre_15-Oct-2019_08-29-10` | 5765 | 192.2 | 72.9 | 130.1 |
| `FP03_Qefter_försök2_15-Oct-2019_11-06-33` | 5746 | 191.5 | 60.0 | 134.9 |
| `FP03_Qföre_15-Oct-2019_09-15-49` | 5220 | 174.0 | 60.5 | 123.3 |
| `FP03_Wefter_21-Oct-2019_10-21-58` | 6102 | 203.4 | 74.7 | — |
| `FP03_Wföre_21-Oct-2019_08-58-40` | 5819 | 194.0 | 72.0 | 133.0 |

To avoid copying 16 GB, `RecordedVideos/` holds symbolic links to the files in
`Video_inventory/`; the library follows them. A raw recording without a
stabilized copy is analysed as it is (`Recording.video`).

### Setup on macOS

Homebrew's Python had no Tk. `brew install python-tk@3.12`, then a `venv/`
from Python 3.12 with `requirements.txt` and pytest (numpy 2.5, OpenCV 5.0,
SciPy 1.18, Tk 9.1). `settings.csv` points the data folder at the repository.

### Fixes

- **Crash on start under Tk 9.** The overlay hint on the video is drawn
  before the canvas is laid out, when its width is 1 px, so its wrap width
  `width - 60 px` was negative. Tk 8.6 (WSL) accepted that; Tk 9.1 raises
  `TclError: expected screen distance but got "-59"`. The same arithmetic was
  in the empty recording list and the reading view's message. All three are
  now at least 1 (`gui/video_view.py`, `gui/library_view.py`,
  `gui/reading_view.py`).
- **The stabilization memory guard was off on macOS.** It read only
  `/proc/meminfo`, which macOS does not have, and treated memory as unknown.
  Stabilizing one of these recordings needs about 28 GB (two float64 copies),
  more than three times this computer's memory. `available_memory_bytes` now
  falls back to the total physical memory (`os.sysconf`), so the app refuses
  instead of swapping or crashing. These recordings cannot be stabilized on
  this computer with the current stabilizer.

### Verification

- `python -m pytest`: 215 passed (213 before, plus the 2 new tests in
  `tests/test_stabilization_memory.py`: the memory is known on this platform,
  and a 5729-frame recording is refused at 8 GB with "28.2 GB").
- The app starts and stays up with the 9 recordings listed (it crashed on
  start before the fix).
- The batch CLI read 450 frames of the raw `FP01_Qföre` with an arbitrary
  3-point line (126.5 px) without errors; 0 of 25 blocks resolved, as expected
  for resting flow on a line that does not follow a capillary.

---

## 2026-10-07 — Official occlusion and release times added; the "slow flow" was the occlusion

**Branch:** `data/occlusion-times`, from `main` at `bb597e2`.

**Commits:**

- `3fbfd6d` Add the official occlusion and release times of the ESMOKE and ISMOKE recordings

The user shared the study progress report of the degree project, which the
repository's `Thesis/report_draft.tex` (July) predates. The report covers:

- **Data:** a retrospective archive of two crossover trials, stored in DynCap.
  - ESMOKE: W = e-cigarette with nicotine, Q = without nicotine.
  - ISMOKE: S = heated tobacco, C = no exposure.
- **Recordings:** each visit has one before (före) and one after (efter) the
  exposure.
- **Aims:** aim 1 is the inter-day reproducibility of resting capillary blood cell
  velocity from the two före recordings; aim 2 is the acute effect.
- **Protocol:** every recording holds about 1 min of rest, 1 min of occlusion at
  200 mmHg, and about 1 min after release.

The user then provided the "official times" of occlusion and release, exported
from DynCap.

### The data (`metadata/`)

`ESMOKE_timestamps.csv` and `ISMOKE_timestamps.csv` are kept exactly as
provided: semicolon-separated, UTF-8, columns `subject`, `occlusion`,
`release` (seconds from the start of the video) and `source_file` (the
recording's stem). A check with pandas:

- 74 + 50 recordings, 17 + 13 participants, no duplicate file names;
- 16 recordings without a release time;
- occlusion at a median 60.3 s, lasting a median 61.2 s (47.5–93.8 s);
- all 8 recordings in the local `StabilizedVideos/` are covered.

`metadata/README.md` lists the rows that differ from the pattern. Two of them:

- **`FP01_Wefter_14-Oct-2019_10-07-49`:** occlusion at 158.5 s and release at
  230.1 s, but the local video has 3435 frames: 114.5 s at the stamped 30 fps,
  and 229 s at 15 fps. Either the times use another origin, or this
  recording's true frame rate is 15 fps. A crude measure of blood movement in
  the vessels, frame to frame, was too noisy to decide. Check in DynCap.
- `FP21Wföre_…` has no underscore after the code.

### Correction: the "slow flow" of 2026-10-06 was the occlusion

The centre line along the FP01_Qföre limb (145 px) was measured over the
whole recording instead of 63–94 s. Resolved 3-s blocks per 10-s window, and
the official times:

| Window (s) | Resolved | Median (mm/s) | Phase (official 68.3 / 130.5 s) |
| --- | --- | --- | --- |
| 0–70 | 0 of 105 | – | rest |
| 70–80 | 6 of 15 | +0.017 | occlusion |
| 80–90 | 14 of 15 | +0.012 | occlusion |
| 90–100 | 15 of 15 | +0.005 | occlusion |
| 100–130 | 16 of 45 | +0.009 to −0.007 | occlusion |
| 130–190 | 3 of 90 | – (one block at +0.247) | after release |

Space-time pictures of 5-s stretches show what happens in each phase:

- **Occlusion:** the steep, curving streaks of slow, decelerating flow.
- **Rest:** faint, almost horizontal streaks; the pattern crosses the line in a
  few frames, roughly 0.5–1 mm/s.
- **After release:** crisp, almost horizontal streaks, faster still.

A crude measure of blood movement in the vessels jumps at 130 s, at the
official release. Comparing each row with the next found no pattern moving
within ±60 px at rest: the best match was always at zero shift, with weak
correlation (r = 0.06–0.19).

So the "slow flow, 0.01–0.04 mm/s" reported on 2026-10-06, and its reading
that "slow flow is expected with this protocol", describe the occlusion. That
holds for the 63–94-s stretch of the before limb, and the after-loop stretch
(47.8–77.8 s) straddles rest and occlusion. At rest and after release the
flow is faster than the centre line can measure at 30 fps: about 0.26 mm/s
for this line, from the Fourier limit |ω| ≤ 0.45 cycles/frame.

**Aim 1 needs resting CBV, so a fast-flow estimator is now the main open
item.** The streaks at rest are motion-blurred and continuous, so fitting their
slope in the image itself (Radon or Hough in the time domain) should work
while a streak still spans about 3 frames. Longer lines would help further.

### Correction: who recorded the videos

The Capture-removal entry (below) said the 2019 recordings were "most likely"
made with this app's recorder, because of their names. That evidence was
circular: the rebuilt recorder had been written to reproduce the archive's
names. The recordings were archived in DynCap, so its format (green-weighted
grey, MP4V, 30-fps stamp) need not describe them. Their frame rate remains
unverified (see `FP01_Wefter…10-07-49` above).

**Documentation:**

- `CLAUDE.md` gains a short "The study" section and the `metadata/` folder,
  and puts "resting flow is beyond the centre line's range" first among the
  known issues. Its frame-rate note no longer mentions the recorder, and it
  marks `Thesis/` as outdated.
- `README.md` lists `metadata/`.

**Verification:** both files parse as described above. The check scripts are
not in the repository. No code changed.

---

## 2026-10-07 — Capture page removed: the app no longer records

**Branch:** `refactor/remove-capture`, from `main` at `a6b367c` (after pull
request #7 was merged).

**Commits:**

- `3832afa` Remove the Capture page: the app no longer records
- `80eaab6` Update README and CLAUDE.md for the app without recording

The user asked what the Capture page was for and whether it could go. It
showed the microscope camera's live image and recorded into `RecordedVideos/`
under names like `FP03_Wföre_07-Oct-2026_14-03-22.avi` (participant and
condition, date, time), with time points marked during the recording. The
program began as the recording station for the capillaroscope: it has had a
recorder since its first commit. The 2019 recordings carry exactly the names
it produced, so they were most likely recorded with an earlier version of it.
The computer the app now runs on has no camera, and the user confirmed that no
new recordings for the thesis will be made with this app.

**How the recorder wrote videos.** This is kept here because it probably
describes how the 2019 recordings were made, which the data-acquisition
section of the thesis needs. `gui/camera.py` said it wrote "as before":

- every camera frame turned into one green-weighted grey image,
  (−0.5·R + 1.5·G + 127.5) / 2 (`Utilities.rgb_to_negR_posG`), because
  capillaries contrast best in green;
- written as three identical channels with the MP4V codec (MPEG-4 Part 2,
  lossy) into an `.avi`;
- every file stamped 30 fps, whatever the camera delivered. The rebuilt page
  warned when the measured rate differed by more than 5%.

The thesis draft says the recordings were stored losslessly. If they came from
this recorder they were not, and their true frame rate is unknown. Both are
open points (CLAUDE.md, known issues).

**Removed:**

- `gui/capture_page.py` and `gui/camera.py` (471 lines);
- the recording-name helpers in `gui/tasks.py` (`recording_name`,
  `new_recording_path`) and their two tests;
- `Utilities.rgb_to_negR_posG`;
- the record, stop and camera icons and the Record button style.

**Changed:**

- The logo colour (the red capillary loop in the header) is renamed from
  `record` to `brand`.
- Messages that pointed to the Capture page now say to copy videos into
  `RecordedVideos/` (raw, to be stabilized) or `StabilizedVideos/`.
- The pages are Ctrl+1–4: Centre line, Two boxes, Results, Validation.
- `RecordedVideos/` stays: raw videos copied there can still be stabilized.
- The module list in `gui/__init__.py` also gained the two Validation modules
  added earlier today.

**Verification:**

- 213 tests pass (215 before, less the two recording-name tests).
- pyflakes reports only the two old notes, and the CI flake8 selection is
  clean.
- Scripted GUI session: four tabs, Ctrl+1–4 open the right pages, Ctrl+5 does
  nothing, F1 lists Ctrl+1…4, the app shuts down cleanly, and there were no Tk
  errors.

**A mistake while starting this branch (no code).** Switching to the old
`main` and then updating to the new one deleted the local `settings.csv`.

- The old `main` still tracked the file, so checking it out replaced the
  ignored local copy with the tracked one.
- The new `main` untracks it, so fast-forwarding removed it.

It was restored byte for byte: the last tracked version plus the two rows the
app had added (`box_size,12` and `observer,1`), and the app reads it back.
After a commit stops tracking a file, back it up before checking out anything
older.

---

## 2026-10-07 — Pull requests #5 and #6 merged; `settings.csv` and `Validation/` no longer tracked

**Branch:** `chore/untrack-local-data`, from `main` at `2186904`.

**Merged.** The user merged #5 (`feat/centreline-velocity`, the centre-line
method) and #6 (`feat/observer-validation`, the Validation page) on GitHub,
both with merge commits, and GitHub deleted the two branches. Locally, `main`
was fast-forwarded to `2186904`. Every local branch already merged into it
was deleted (`git branch -d`, which refuses unmerged ones):
`feat/centreline-velocity`, `feat/observer-validation`, `feat/gui-rebuild`,
`refactor/remove-dead-code` and `refactor/remove-optical-flow`. The 215 tests
pass on `main`.

**Untracked.** The user's first try of the Validation page on the real data
worked: a reading set of 6 blocks from `set1` of `FP01_Qefter`, read by
observer "1" (5 with streaks, 1 without), and the agreement computed, with no
errors in the log. It also showed two things in `git status`:

1. **`Validation/`** was not in `.gitignore`, unlike the other data folders,
   so reading sets showed up as files to commit. It is now ignored.
2. **`settings.csv`** was tracked, although the app rewrites it: the data
   folder, the calibration, the box size (since the 2026-10-05 rebuild) and,
   since today, the observer. It therefore always showed as modified, and the
   tracked copy only held this computer's path. The user chose to stop
   tracking it. It is removed from the index (the local file stays as it is)
   and ignored.
   - A fresh copy of the repository has no `settings.csv`, so the app's
     welcome dialog asks for the data folder and calibration.
   - `python -m capillary.cli` then uses the default calibration unless
     `--mm-per-pixel` is given.
   - On another computer with a copy, pulling this change removes its
     `settings.csv` once.

**Verification:** the 215 tests pass. `git check-ignore` confirms both paths
are ignored, `git status` no longer lists them, and the local `settings.csv`
is unchanged.

---

## 2026-10-07 — Validation on real recordings: blinded reading by observers, and line placement

**Branch:** `feat/observer-validation`, from `feat/centreline-velocity` at
`c56d495`. That branch's pull request was not merged yet; once it is, the pull
request of this branch shows only the commits below.

**Commits:**

- `1a3c78b` Validation page: observers read space-time blocks blinded; agreement with the estimator
- `42a99b6` Line placement: the same capillary measured by different observers
- `cc4e66c` Update README and CLAUDE.md for the Validation page
- `67d4e56` Move the Validation page's reading mode into gui/reading_view.py

The user asked to keep building. Of the open items (validation on real data,
a null control for jitter near stasis, pairing before/after recordings,
calibration and frame rate) they chose validation on real data. The benchmark
of 2026-10-06 shows the centre line is accurate on synthetic recordings, but a
real recording has no ground truth. The thesis needs evidence on real data for
two questions:

1. Does the estimator read the slope a person reads from the same space-time
   diagram? Reading the slope of the streaks by hand is how line-shift
   diagrams have been read in capillaroscopy (Cap-Image), so it is the natural
   reference.
2. How much does a velocity depend on who measures it, that is on where the
   line is drawn (inter- and intra-observer reproducibility of the whole
   measurement)?

The Validation page (Ctrl+5) does both. Nothing has been read on the real
data yet; everything below was tested with simulated observers.

### Blinded reading (`capillary/validation.py`)

- **What is read.** Exactly the 3-s blocks (90 frames) the estimator
  measures: rows `start … start + 89` of a saved space-time diagram, `start`
  one of the estimator's block starts (every 15 frames). Blocks drawn from one
  data set never overlap (starts at least 90 frames apart), so no two items
  share frames.
- **How blocks are drawn.** From each chosen centre-line data set, *k* blocks
  (default 6) at random. By default balanced: ⌈k/2⌉ from the blocks the
  estimator resolved and the rest from unresolved ones, either kind making up
  a shortage of the other. Agreement on velocity needs resolved blocks;
  agreement on whether a block can be read at all needs both kinds. The seed
  is recorded (default from the system's random source); the same seed and
  data sets draw the same set (tested).
- **Frozen.** The blocks are copied (float32) into
  `Validation/<set>/blocks.npz`; `set.json` records for each its recording,
  data set, rows, video frames, fps, calibration and the estimate when drawn.
  Measuring a data set again or deleting it does not change the set. Item
  numbers are given in a random order, so they say nothing about the source.
- **Blinding.** An observer sees "Block 12 of 60", the block and their own
  lines: not the recording, the data set or the estimate. Every observer and
  session gets its own order (a shuffle seeded by the set's seed, the
  observer's code and the session; reproducible, different for each).
- **Display.** The block with the mean of every position over time and the
  mean of every frame along the line removed (still structure and changes of
  the whole line at once, as in the preview and the report), contrast from the
  1st to the 99th percentile, position along the line across (first point on
  the left), time downwards. One pixel along the line is drawn as wide as one
  frame is tall, so a streak at 45° is 1 px/frame. The scale depends only on
  the block's size, never on the estimate.
- **Reading.** The observer drags lines along streaks (the instructions say
  two or three); the block's slope is the mean of the lines' slopes,
  Δposition/Δframe. A line spanning fewer than 4 frames is refused (too flat in
  time to give a slope; on a 120-px line that is over 30 px/frame, far beyond
  what can be measured). Or "No clear streaks" (N). Lines are stored in block
  coordinates, with the time spent on each block (time away from the page not
  counted). Everything is saved after every change (the JSON is written to a
  temporary file and moved into place), so a session can stop and continue.
- **Sessions.** A second session by the same observer, some days later and in
  a new order, gives the repeatability of one person's reading.

### Statistics (`capillary/agreement.py`)

Velocities in mm/s (slope × fps × mm/px of the source data set); differences
are first minus second.

- **Bland–Altman** (Bland & Altman, Lancet 1986; Stat Methods Med Res 1999):
  bias with its 95% confidence interval (t, SE s/√n); 95% limits of agreement,
  bias ± 1.96 SD, each with an approximate 95% interval (SE √(3s²/n));
  proportional bias as the slope of the differences on the means, with its
  95% interval. The same on a log scale, as ratios (pairs of the same sign,
  magnitudes compared): geometric-mean ratio and ratio limits. Velocities span
  an order of magnitude, so differences are likely to grow with velocity; the
  page then says to read the ratio limits.
- **ICC** (McGraw & Wong, Psychol Methods 1996): two-way model, single
  measurement, absolute agreement ICC(A,1) (= Shrout & Fleiss ICC(2,1)) and
  consistency ICC(C,1) (= ICC(3,1)), with their F-distribution intervals.
- **Same direction**: share of pairs with the same sign.
- **Readability**: Cohen's kappa (yes = a velocity: the estimator resolved
  the block, or the observer drew lines), large-sample interval cut at ±1, and
  the 2×2 counts.
- **Within an observer**: repeatability coefficient 1.96 × SD of the
  differences (= 2.77 × the within-subject SD).

Checks of the arithmetic:

- Shrout & Fleiss (Psychol Bull 1979) table 2, six targets by four judges:
  ICC(2,1) = 0.290 and ICC(3,1) = 0.715, the paper's 0.29 and 0.71. The
  intervals, 0.019–0.761 and 0.342–0.946, match the values I remember R's
  psych::ICC reporting for this table; confirm with R before citing them.
- Bland–Altman and kappa against values worked by hand (in the tests).
- Coverage of the 95% intervals in 2000 simulations each (scratch script, not
  in the repository): ICC(C,1) 94–95%. ICC(A,1) 93% (n = 20) and 96% (n = 40)
  with two raters, but 90% with three raters and a large rater effect. That is
  a known weakness of this approximate interval when there are few raters, not
  a bug: the point values and the published example match. Bland–Altman bias
  95%; upper limit 93.5% (n = 20), 95% (n = 50), the approximate limit
  interval being slightly narrow for small n. Kappa 94%.

### The comparisons

The agreement report measures every block again with the current estimator,
from the frozen blocks, so it always reflects the code that runs (the
estimate when drawn is kept in `set.json`). It compares:

- the estimator against every reading;
- the estimator against the mean of the observers' first sessions, on blocks
  where all of them drew lines (for readability: yes where all drew lines, no
  where none did, left out where they disagree);
- the observers' first sessions pairwise and, with three or more observers,
  the ICC of all of them;
- each observer's first session against each later one.

Written to `Validation/<set>/report/`: `agreement_items.csv` (one row per
block: source, the estimate, every reading), `agreement_summary.csv` (one row
per comparison, every statistic above), `readings.csv` (per reading: blocks
read, with streaks, no clear streaks, median seconds per block),
`bland_altman.png` and `scatter.png`.

Caution for reading the results: the Bland–Altman comparison of estimator and
observer uses only blocks the estimator resolved and the observer read, a
sample selected by both. The readability counts and kappa describe the rest.

### Line placement (`capillary/placement.py`)

- **Observer.** The measure pages have an Observer field (initials) next to
  the data set name, shared with the reading dialog and remembered in
  `settings.csv` (`observer`). It is saved in every new data set's provenance
  (`observer`), and the Results page shows it ("by SJ"). Older data sets have
  none.
- **Matching.** Two centre-line data sets measure the same capillary if they
  are on the same recording, at least half of one line lies within 5 px of
  the other (lines sampled every pixel), and their frame ranges share at least
  80% of the frames either covers. A line drawn the other way round is
  compared with its sign reversed (the tangents where the lines meet decide).
  Connected matches form one capillary.
- **Comparison.** Per capillary, each observer's first data set and their
  second, if any. The median velocities are compared between every two
  observers (and all of them with three or more) and between an observer's
  first and second measurement, with the same statistics. Data sets without
  an observer are listed but take part in no comparison. Written to
  `Validation/line_placement/` (`measurements.csv`, `capillaries.csv`,
  `summary.csv`, the plots); the name `line_placement` is reserved and cannot
  be used for a reading set.

### The app

- **Validation page.** The left column holds "Line placement" and the reading
  sets (**New…** draws one). A reading set shows its readings (observer,
  session, blocks read, no clear streaks, last saved; Continue / Look
  through), **Start reading…** (observer and session, with the next session
  suggested), the agreement (two tables: velocity, then readability; Bland–
  Altman and scatter plots, which open full size on click) and the data sets
  it was drawn from.
- **Reading mode** fills the page: the block on the left; on the right the
  observer and session, block *n* of *N*, progress, instructions, **No clear
  streaks**, **Remove lines**, **Next block** (Enter or →), **Previous** (←),
  **Finish later** (Esc). Backspace removes the last line. F1 lists the keys.
  Leaving the page keeps the reading open.
- `Caper.generate_validation_report` draws the plots; `gui/tasks.py` has the
  background jobs; the reading mode is `gui/reading_view.py`.

### Verification

- **Unit tests:** 215 pass (184 before). `test_agreement.py` 10 (Shrout &
  Fleiss, hand-worked Bland–Altman and kappa, proportional bias found and
  removed on the ratio scale, missing values, too few pairs).
  `test_validation.py` 13: synthetic centre-line data sets with flow at 1.0
  and 0.4 px/frame and without flow; blocks identical to the data set's rows;
  the saved estimate equal to the one computed again; seeding; name rules;
  orders per observer and session; saving and resuming; simulated observers
  (5% scatter, no streaks without flow) giving bias near 0, ICC > 0.8 and
  kappa 1; three observers; report files. `test_placement.py` 6: overlap and
  direction of lines, frame overlap, grouping with reversed lines, the
  comparisons (an observer reading 10% higher gives ratio limits of exactly
  1.1), the report from saved provenance. Two in `test_gui_logic.py`: the
  reading canvas's coordinates both ways; the image observers see (no still
  structure or same-moment change left). `test_line_tasks.py` checks that the
  observer is saved.
- **Lint and imports:** pyflakes reports only the two old notes; the CI
  flake8 selection is clean; the venv was not touched.
- **Scripted GUI sessions** on a scratch data folder (links to the real
  videos, copies of the data sets), the windows never taking keyboard focus.
  Three centre-line data sets on real capillaries were measured first:
  - the before limb (`FP01_Qföre`, 145 px, frames 1909–2808): 33 of 55
    blocks resolved, median 0.0138 mm/s;
  - a line through tissue 25 px beside it: 0 of 55;
  - the after loop's left limb (`FP01_Qefter`, 126 px, frames 1435–2334): 5 of
    55, 0.0081 mm/s.

  These match 2026-10-06. Then:
  - a reading set of 18 blocks drawn through the dialog;
  - reading with every control: Next with nothing drawn (refused), too flat a
    line (refused), three lines, right-click removal, Backspace, Previous,
    switching pages and back (the reading stays open), Esc and Continue;
  - three complete readings (SJ ×2, AB) by a simulated observer that draws
    the estimator's own slope with 8% scatter;
  - the agreement report and its plots, F1;
  - the Observer field (lower case saved as upper case, an invalid code
    blocks Measure, both pages share it), "by SJ" on the Results page;
  - Line placement on seven more data sets by two pretend observers. All
    groups were found correctly: three capillaries, the reversed line, the
    tissue line kept apart, data sets without an observer listed but not
    compared.

  Screenshots were reviewed; no Tk errors. The agreement table was first
  wider than the page (kappa cut off) and was split in two, with intervals on
  a second line.

### What the real blocks look like (pilot, not a study)

A contact sheet of the 18 pilot blocks, as observers see them, with the
estimate overlaid (scratch only):

- **Before limb.** The resolved blocks show clear diagonal streaks, and the
  estimated slope runs parallel to them by eye. Some unresolved blocks also
  show faint streaks; this is the disagreement the study will measure.
- **After limb.** Blotches and sudden jumps (whole-line shifts between frames)
  and hardly any visible streak, consistent with 9% resolved. Observers will
  mostly answer "no clear streaks" there.
- **Tissue line.** Noise, plus the edge of a vessel it crosses; usable as
  negative controls if wanted.
- **Line placement on the before limb.** Two lines with different click
  spacing and up to 1.5 px off the middle gave 0.0137 and 0.0138 mm/s; a third
  drawn the other way gave −0.0140 (matched, sign reversed). These lines came
  from the same extracted skeleton, so this says little about real observers.

### Limitations and next steps

- **No real reading yet.** The readings in the checks were simulated from the
  estimator's own slopes; they test the mechanics, not the method.
- **Suggested protocol (to agree with the supervisors):**
  1. Choose capillaries with visible flow, about 2 per recording, and measure
     each over the whole recording with the Observer field filled.
  2. Draw a reading set (6 blocks per data set, balanced).
  3. Two observers read session 1 independently; one reads session 2 at
     least a week later.
  4. For line placement, a second observer measures the same capillaries
     over the same frames without seeing the first observer's line. They
     identify the capillary from a frame with an arrow, not from the line.
  5. Compute the agreement.
- **Sample size.** Bland & Altman suggest about 100 pairs for precise limits;
  15–30 capillaries give wide ICC intervals.
- **Display.** Fixed (cleaned, percentile contrast); observers cannot change
  the contrast. A control could be added if blocks are too faint, but it would
  have to be recorded.
- **Slow flow.** At 0.2 px/frame a 3-s block shows streaks moving only about
  18 px over its 90 frames: readable, but shallow.
- **References.** Bland & Altman 1986 and 1999, McGraw & Wong 1996, Shrout &
  Fleiss 1979 and Cohen 1960 need checking before they go into the thesis, as
  do Drew 2010 and Klyscz 1997 from 2026-10-06.

---

## 2026-10-06 — Velocity along a centre line (space-time diagram), validated on calibrated synthetic recordings

**Branch:** `feat/centreline-velocity`, from `main` at `bbec82a` (after the
optical-flow removal was merged as pull request #4).

**Commits:**

- `43cc549` Add the centre-line velocity estimator, a calibrated simulator and a benchmark
- `0cef0c3` Centre line page: draw a line along a capillary and measure its velocity
- `5c4e5b3` Update README and CLAUDE.md for the centre-line method

The user asked to work on the velocity estimator. Before changing anything,
the existing method was measured on the real recordings. The findings changed
the plan from "refine the two-box method" to "measure along the vessel", and
the user chose: first a benchmark, then a centre-line method.

### What the two-box method measures on real capillaries

All of this was read-only analysis with scripts outside the repository.

1. **`set1` measured tissue, not blood.** The only data set with recorded box
   positions (`FP01_Wefter_14-Oct-2019_10-13-03___set1`, made while trying out
   the new GUI on 2026-10-05) has its boxes at (433, 316) and (463, 290), about
   25 px to the right of the nearest capillary, in still tissue. A map of
   frame-to-frame variation and a space-time diagram between the boxes show
   no movement there. Its result (median −0.02 mm/s, 37% lag 0, 36% positive)
   is noise and should not be used.
2. **On a real capillary the flow is visible and slow.** The centre line of
   the tall loop in `FP01_Qefter_22-Oct-2019_09-46-17` ("after", frames
   1435–2334) and `FP01_Qföre_22-Oct-2019_08-16-35` ("before", frames
   1909–2808) was extracted from the mean image (vessel darker than the local
   background, thinned to a skeleton). Space-time diagrams along it show red
   cells and plasma gaps as slanted streaks of about 0.2–1 px/frame, roughly
   0.01–0.04 mm/s. The user confirmed that slow flow is expected with this
   protocol.
3. **Brightness changes along the whole vessel at once dominate.** Along the
   limbs, the part of the signal that is the same at every position at the
   same moment has a standard deviation of 3.1–6.3 grey levels, nearly the same
   all along the vessel (gain 1.00 ± 0.14 after, ± 0.41 before). It makes up
   71–73% (median) of the variance of a 12-px stretch, the size of a box, in
   both recordings. The likely cause is small movements of the vessel or
   focus; the per-pixel sensor noise is 3.05 grey levels.
4. **That is why the boxes find a lag of 0.** Two boxes 30 px apart on the
   after loop's left limb gave lag 0 in 44 of 70 windows, which the report
   calls "too fast to resolve", although the flow is slow. Subtracting the
   limb's mean brightness removed the lag-0 peak; lags of −19/−20 frames
   appeared (consistent with the streaks), but the estimates stayed scattered.
5. **Consequences for the earlier plan.** Rounding the lag to whole frames
   costs only 2–5% here, since the true lags are 20–70 frames. Treating lag 0
   as "faster than measurable" (an item on the plan) would have turned the
   same-moment changes into high velocities. "Too fast to resolve" in existing
   two-box reports should not be read as fast flow.

### The method (`capillary/spacetime.py`)

The user clicks points along the middle of one capillary, from where the blood
comes from to where it goes. The line is the uniform Catmull-Rom curve through
the points, sampled every pixel of arc length. In every frame the brightness
at 5 points across the line (±2 px along the normal, bilinear) is averaged;
the rows stacked over time form the space-time diagram. A pattern moving
along the vessel at `v` px/frame draws streaks of slope `v` and puts all its
power on the line `ω = −v·k` of the diagram's 2-D power spectrum (`k` in
cycles/px, `ω` in cycles/frame). Velocity = `v` × fps × mm/px, positive from
the first point towards the last.

The slope is estimated in blocks of 90 frames (3 s), every 15 frames:

1. Remove the time mean of every position (still structure) and the position
   mean of every frame (a same-moment change of the whole line).
2. Difference the block along the line (whitening, see below), apply Hann
   windows in space and time, and Fourier-transform along the line; keep
   patterns from 3 cycles per line length up to 0.3 cycles/px.
3. For candidate speeds ±0.05 to 30 px/frame (400 log-spaced, then 41 around
   the best), evaluate exactly (a direct transform in time at arbitrary
   frequency) the power at `ω = −v·k` and at the mirror `ω = +v·k`. Each
   pattern counts with weight 1 up to |ω| = 0.3 cycles/frame, fading (cos²) to
   0 at 0.45 (the unaliased part of its line). The score is the weighted mean
   of forward minus mirror power; the speed is the best score.
4. Quality: the signal-to-noise ratio is the weighted forward-minus-mirror
   power over its spread under "no flow", from a noise floor estimated locally
   (median power within ±5 temporal-frequency bins of both signs, ÷ ln 2). The
   coherence is the share of the block's energy (in the patterns used) on the
   chosen line, 1 for a clean pattern at one speed.
5. A block is resolved if the signal-to-noise ratio is at least 8, the
   coherence at least 0.03, and the speed lies in the measurable range. The
   slowest speed is 1.5 cycles of the finest pattern per block. The fastest is
   0.65 × the speed at which the unaliased patterns weigh three full patterns;
   at 30 fps that is about 0.045 × line length px/frame. Finally, if any speed
   beyond that range, scored on whatever unaliased patterns it has, beats the
   chosen one, the block is flagged "faster than measurable".

The core is the Radon-transform velocity method for space-time images (Drew
et al., J Comput Neurosci 2010;29:5–11), evaluated through the Fourier slice
theorem. The space-time ("line-shift") diagram itself is established in
capillaroscopy: Cap-Image (Klyscz et al., Biomed Tech 1997) has the user read
the slope. Both references need checking before they go into the thesis. The
direction contrast is the addition that matters for these recordings: noise,
still structure and any change that is a shape along the line times a time
course (the same-moment change, unevenly strong) have a spectrum symmetric in
`ω`, so they cancel in forward-minus-mirror, while flow does not.

### How the design was arrived at

Each choice was tested on synthetic space-time diagrams first (a moving
pattern plus the same-moment change, its unevenness, jitter along the line and
noise, at the measured levels), then on the video-level simulator below.

- **Direction contrast works where the boxes fail.** On the same synthetic
  diagrams two boxes 30 px apart gave lag 0 in 61–100% of windows at
  0.25–4 px/frame; the centre line measured them within 3%.
- **Bias −2 to −3%.** Reading the spectrum by interpolation was ruled out (an
  exact transform kept the bias). The cause is the spatial window: cell
  patterns have more power at coarse scales, and leakage into finer patterns
  reads as slower. Differencing along the line flattens the spectrum: bias
  within ±1.7%.
- **Quality score.** A first z-score was capped by the number of patterns
  (flow 3–5, no flow up to 3.6) and was dropped. The signal-to-noise ratio
  against a noise floor separates them (no flow at most 6.1, flow 9 to several
  hundred), hence the threshold of 8.
- **Aliased lines** (letting fast speeds use patterns past the Nyquist limit,
  wrapped) were tested and dropped: worse with motion blur and weak cells.
- **Speed limit.** With a hard cut-off, wrong estimates clustered at the
  speeds where one more pattern became unaliased (5.0, 6.0, 6.75, 7.7 px/frame
  on a 120-px line); the cos² fade removed that. Single blocks stay within 10%
  of the truth in all but 0–7% of cases up to about 0.6 of the limit (5 px/frame
  on a 120-px line), but 19–25% at 7–8 px/frame, hence reporting only up to
  0.65 of the limit.
- **Flow faster than the line can follow** (15 px/frame on a 120-px line)
  came back as −4.4 px/frame with a signal-to-noise ratio of 10 and was
  counted as resolved; the "faster than measurable" check fixes that. Raising
  the coherence threshold to 0.05 would also have caught it, but would also
  have dropped real flow (before limb: 57% → 49% of blocks resolved).
- **Jitter.** With a global noise floor, blocks without flow but with jitter
  were resolved as slow flow (about 0.2 px/frame) in 29% (measured
  disturbances) and 74% (strong) of cases. Jitter crowds the slow temporal
  frequencies; the local floor brought this to 7% and 11%.
- **Coherence threshold.** 0.03 and 0.05 gave identical results on the
  simulations; 0.05 dropped real resolved blocks, so 0.03 (no-flow coherence
  is about 0.015–0.02).

### Synthetic recordings (`capillary/simulate.py`)

A capillary loop (limbs 150 px, 26 px apart, 10 px wide, the limbs leaning a
little) on a textured background, with red cells of about 6 px following each
other closely and a plasma gap of 6–30 px after 10% of them. The pattern moves
along the loop at a set speed (optionally pulsing with a 1.1 Hz heart beat) and
is averaged over the distance it moves while the shutter is open (motion
blur). On top: a same-moment darkening of the whole vessel (Ornstein-Uhlenbeck,
τ = 8 frames, plus a 1.1 Hz component), uneven along the vessel; whole-image
jitter (τ = 4 frames, SD 0.3 px); optical blur (σ 1.2 px); noise. Calibrated
against the two real limbs:

| Measure (same method for both) | Real | Simulated |
| --- | ---: | ---: |
| sensor noise per pixel (grey levels) | 3.05 | 3.03 |
| same-moment change, SD along the line | 3.1–6.3 | 5.2 |
| its unevenness along the line (gain SD) | 0.14–0.41 | 0.13 |
| everything else, SD | 2.8–5.0 | 4.0 |
| same-moment share of a 12-px stretch | 71% | 70% |
| vessel darker than local background | ~10 | 13 |

The simulator reproduces the box failure: two boxes 30 px apart see lag 0 in
at least half the windows where the true lag is 30 frames (pinned by a test).

### Benchmark (`python -m capillary.benchmark`)

Each case renders a loop and measures it twice, as the app would: two 12-px
boxes 30 px apart through the two-box report arithmetic (`analyze_trace`,
windows 201–301 frames), and a 120-px line clicked every 15 px up to 1 px off
the centre through `capillary.spacetime`. Medians over 3 seeds of 30-s clips
(30 fps, 1.329 µm/px; the line can measure 0.002–0.212 mm/s; 6.5 min):

| Disturbances | True speed | Centre line: error, blocks resolved | Two boxes: error, windows resolved (lag 0) |
| --- | --- | --- | --- |
| clean | no flow | none resolved | **0.039 mm/s** reported, 100% |
| as measured | no flow | 7% falsely resolved | none (100% lag 0) |
| as measured | 0.25 px/frame (0.010 mm/s) | −0.0%, 100% | +8.1%, 64% (47%) |
| as measured | 1 (0.040) | +0.1%, 100% | +3.7%, 100% (1%) |
| as measured | 2 (0.080) | +0.4%, 100% | −9.7%, 50% (54%) |
| as measured | 4 (0.159) | +0.1%, 100% | +7.4%, 100% (0%) |
| as measured | 5 (0.199) | −2.1%, 85% | +0.2%, 100% (0%) |
| as measured | 8 / 12 (0.32 / 0.48) | unresolved (beyond range) | −6.0% / +25.3% |
| strong | no flow | 7% falsely resolved | none (100% lag 0) |
| strong | 0.25 (0.010) | −0.2%, 98% | −93%, 45%, half the wrong sign |
| strong | 2 (0.080) | +0.4%, 100% | −118%, 21% (89%), half the wrong sign |
| strong | 5 (0.199) | −1.9%, 82% | +3.6%, 100% (2%) |

Within its range the centre line's median is within −2.1% to +0.4% in every
condition, with 0–4% of resolved blocks pointing the wrong way; beyond its
range it reports nothing rather than a wrong number. The two boxes are off by
up to ±10% under the measured disturbances, fail outright under strong ones,
report velocity where there is no flow, and are coarse at high speed (−6% to
+25% at 8–12 px/frame). A shorter run (one seed, 10-s clips) once showed 20%
false resolution without flow under strong jitter, so that number varies.

### On the real recordings

Lines from the extracted centre lines, clicked every 15 px; two 30-s stretches
each; nothing to compare with except each other and lines through tissue:

- **Before limb** (145 px): 57% of blocks resolved, median 0.23 px/frame
  (0.0091 mm/s), 92% pointing down the limb. In the GUI session the first
  stretch alone (frames 1909–2808) gave 0.0138 mm/s (middle half
  0.0095–0.0173), 60% resolved, median signal-to-noise 10.
- **After loop:** weak; 12% resolved on the left limb (+0.20 px/frame, 92%
  down the limb), 15% on the other limb (−0.23, all upwards, consistent with
  flow round the loop), 17% on the whole arch with mixed directions.
- **Still tissue,** lines 25 px from the vessel: 0 of 110 blocks resolved in
  both recordings (median signal-to-noise 3.3–3.6). Two lines first
  thought to be tissue resolved some blocks; on inspection one crossed the
  apex and one ran along the other limb.

These numbers are not validated (there is no ground truth in a recording); the
benchmark is what says the method is accurate.

### The app (`0cef0c3`)

- **Centre line page** (first page, Ctrl+1): click points along the vessel
  (start where the blood comes from); click on the line inserts a point, drag
  moves one, right-click removes one, Backspace removes the last, X reverses.
  The panel shows the line's length and measurable range, and a live
  space-time diagram of the 120 frames around the playhead with the slope
  found in orange, its velocity and signal-to-noise ratio, and a message when
  the flow is unresolved, seems too fast or too slow for the line, or runs
  against it (with a Reverse button).
- **Data set** (`capillary.datasets`): `___space_time.npy` (the diagram,
  float32, loaded without pickle), `___line_velocity.csv` (one row per block:
  centre frame, time, speed, velocity, signal-to-noise, coherence, resolved),
  `___line_provenance.json` (video, the points, frames, calibration, measurable
  range, all estimator settings, summary, git commit). Reports:
  `___line_velocity.png` (velocity over time, unresolved blocks marked, median,
  time points), `___space_time.png` (the diagram with the measured slopes) and
  a one-row `___line_summary.csv` for collecting results across recordings.
- **Results page** shows both kinds (CENTRE LINE / TWO BOXES), warns when
  fewer than 25% of blocks were resolved, restores the line on its page, and
  regenerates a centre-line report from the saved diagram without the video.
- **Two boxes page** is the old Analyze page, renamed, unchanged otherwise.
- **CLI**: `python -m capillary.cli <video> --line "x1,y1;x2,y2;..."` measures
  along a line; `--start` picks the first frame for both methods.

### Verification

- **Unit tests:** 184 pass (141 this morning): `test_spacetime.py` 24 (the
  estimator on diagrams with known speed, both directions, no flow, a tenfold
  same-moment change, flow beyond the range, the line geometry, the sampler,
  block analysis, a simulated recording end to end), `test_simulate.py` 9,
  `test_line_tasks.py` 7 (the page's measurement, saving, report, results
  info, regeneration without the video, preview, clean-up after a failure),
  and new cases in `test_pipeline.py` (CLI `--line`), `test_datasets.py` and
  `test_gui_logic.py`. Each code commit passes on its own (176 and 184).
- **Lint:** pyflakes reports only the two earlier notes; the CI flake8
  selection is clean.
- **Benchmark:** the full run above (6.5 min) and `--quick` (12 s).
- **Scripted GUI session** on a scratch data folder, screenshots reviewed, no
  Tk errors: four pages and Ctrl+1–4; 11 clicks along the before limb (145 px,
  measurable 0.0022–0.256 mm/s); preview resolved at 0.0169 mm/s,
  signal-to-noise 19; inserting, dragging, right-click removal, Backspace,
  and X (velocity −0.0169 with the "against the line" message); measuring
  frames 1909–2808 (3.1 s); the Results card, restoring the line and range,
  regenerating, moving to the trash; the Two boxes page, F1, the right-click
  menu. The direction arrow, first drawn at the line's end where the last
  point hid it, was moved to the middle.

### Limitations and next steps

- **Speed limit at 30 fps.** A line follows flow up to about 0.0018 × its
  length in px, in mm/s; normal resting velocities (0.3–1 mm/s) need lines of
  170–560 px or a faster camera. Worth stating in the thesis; it also makes
  checking the real frame rate (still open) more important.
- **Jitter near stasis.** Without flow, 7–11% of blocks (up to 20% in a short
  clip) are resolved as about 0.2 px/frame under jitter, which is the speed of
  the slow real flows here. A near-stasis vessel shows as "few blocks
  resolved"; the Results page warns below 25%. A per-recording control (the
  same measurement on a parallel line through tissue) or local stabilization
  would make this stronger.
- **Real-data validation is still to do:** two observers reading the slopes
  of the same diagrams, repeated measurements, Bland–Altman against manual
  reading.
- The existing two-box data sets (`Test`, `Test2` of `FP01_Qefter`, `set1` of
  `FP01_Wefter`) are unreliable for the reasons above.
- The two-box report still sets negative velocities to 0 in
  `___report_summary.csv`; left as it was, since that method is now
  secondary.
- Frame rate and spatial calibration are still unverified.

---

## 2026-10-06 — Optical-flow measurement removed

**Branch:** `refactor/remove-optical-flow`, from `main` at `95472ee` (the GUI
rebuild, merged as pull request #3).

**Commits:**

- `284d67e` Remove the optical-flow measurement
- `38ddd3a` Update README and CLAUDE.md for the velocity-only app

### Why

At the end of the 2026-10-05 session we agreed to build the tool around the
primary endpoint, red-cell velocity, and to drop the optical-flow measurement
first. The flow measure was not a planned endpoint, and as implemented it was
not a valid one:

- **Fast motion was discarded.** Magnitudes above 10 px/frame were set to 0
  before anything else. At 1.329 µm/px and 30 fps that is about 0.4 mm/s,
  well inside the range of capillary red-cell velocities.
- **Lossy storage.** The flow was multiplied by 25.5, saved as an 8-bit MP4V
  video and read back for the measurement. That quantizes it and adds
  compression artefacts.
- **Wrong denominator.** The flow summed over the whole region (vessel and
  background) was divided by the number of vessel pixels in it.
- **Direction and unit.** "Up" and "down" meant towards the top or bottom of
  the image, not along the vessel. The unit was mm per frame, not mm/s.

### What the app no longer has

- The **Flow** page. The pages are now Analyze, Capture and Results, and
  Ctrl + 1 … 3 switches between them. Ctrl + 4 now does nothing.
- *Compute optical flow* / *Recompute optical flow…* in a recording's
  right-click menu and on the Results page, and *Compute missing optical flow*
  in the **⋯** menu above the list.
- *Measure flow* in the right-click menu and on the Results page, the "Flow"
  chip in the recording list, the "Optical flow" row of the Results page's
  Files card, and flow data set cards.
- The "Region (Flow)" section of the F1 list.

### Code removed (`284d67e`)

- `gui/flow_page.py` (426 lines), `capillary/flow.py` (138) and
  `tests/test_flow.py` (162).
- `Caper.FlowVideo` (the Farneback flow and the vessel-mask pickle) and
  `Caper.generate_flow_report`.
- From `capillary/measure.py`: `measure_flow` and `flow_region_size_bytes`.
  From `capillary/datasets.py`: the flow file names, writers, readers and
  listing. From `gui/tasks.py`: the flow job, the flow measurement and the flow
  report.
- `pickle_save` and `pickle_load` from `Utilities.py`.
- `scikit-image` from `requirements.txt`; only `FlowVideo` used it. It can be
  removed from an existing venv with `pip uninstall scikit-image`, but it does
  no harm there.
- Things only the Flow page needed:
  - colour frames in `FrameSource`
  - the skipped-frame callback of the player
  - the `prepare_frame` / `video_opened` hooks of the measure page
  - the green region colour
  - `iter_frames(single_channel=False)`
  - the second capture handle in `tasks._release`
- With one kind of data set left, the "velocity or flow" switch went too.
  `datasets.dataset_paths`, `tasks.dataset_info` and the Results page's card
  actions now take just the data set name. The measure page has no `kind` or
  `color` attribute.

In all: 28 files, 270 lines added, 1,461 removed.

### Old flow files

Nothing on disk was deleted or moved. The real data folder still holds:

- `Flows/FP01_Qefter_22-Oct-2019_09-46-17.avi` and its `.pickle`
- two flow data sets of that recording: `Test_1` and an unnamed one
  (`…______flow.pickle`, `…______mask.pickle`)
- the two plots of `Test_1` in `Reports/`

The app stops listing these, but it still knows where they are. Each recording
gets a `legacy_flow_files` list: its files in `Flows/`, plus the files of any
old flow data set in `Statistics/` and `Reports/` (found by
`datasets.legacy_flow_dataset_paths`).

- **Move recording to trash** therefore still takes them along. The
  confirmation then says "… and old optical-flow files".
- A recording that has only a flow video and no raw or stabilized video is
  no longer listed, since nothing can be done with it. No such recording
  exists at the moment.
- New data folders no longer get an empty `Flows/` folder. An existing one is
  left alone.

### Effect on measurements

None. `capillary/velocity.py`, `intensity.py`, `roi.py`, `quality.py`,
`cli.py` and `SingleStepDFT.py` are unchanged. In `Caper.py` the
`VideoStabilization` and `CrossCorrelation` classes are identical apart from
blank lines, and so is `measure_velocity`; this was checked by diffing them
between `95472ee` and `284d67e`. Provenance files of new velocity data sets
still record `"kind": "velocity"`, so the file format is unchanged.

### Verification

- **Unit tests:** 141 pass, down from 154.
  - 15 flow tests went: the 11 in `test_flow.py`, 3 in `test_measure.py` and
    the flow round trip in `test_datasets.py`.
  - 2 new tests check that old flow data sets are found with their plots
    (including the unnamed one) and that old flow files belong to their
    recording without being listed. A flow-only recording is not listed.
  - The trash test now puts an old flow video, its summary, a flow data set
    and its plots beside a recording. It checks that all of them reach the
    trash in their own subfolders.
- **Lint:** pyflakes reports only the two notes it reported before (the
  deliberate re-export in `Utilities.py`, an unused import in the vendored
  `SingleStepDFT.py`). The CI's flake8 selection is clean. `capillary.cli` and
  `Application` import.
- **Scripted GUI session.** This ran the real window under WSLg on a scratch
  data folder: links to the 8 real videos and the real flow video, plus copies
  of the flow summary, `Statistics/` and `Reports/`. The screenshots were
  reviewed, and the session ended with no Tk errors.
  - The header shows Analyze, Capture and Results. Ctrl + 1, 2 and 3 switch
    pages; Ctrl + 4 does nothing.
  - The list shows no flow chip. `FP01_Qefter_22-Oct-2019_09-46-17` shows its
    2 velocity data sets and carries its 8 old flow files.
  - The right-click menu holds *Measure velocity*, *Results*, *Stabilize*,
    *Show in folder* and *Move to trash…*. The **⋯** menu holds *Stabilize
    all raw recordings* and *Open the data folder*.
  - Frames 1000–1400 of that recording were measured as `noflow_test` in
    2.3 s, writing its five files. The boxes were placed at fixed test
    coordinates, not on a chosen capillary, so this range resolved no
    velocity; that does not bear on this change.
  - The data set was then replaced (the old files went to `.trash/`), opened in
    Results (its card highlighted), its report regenerated, its positions
    restored (both boxes and the range 1000–1400 came back), and moved to the
    trash.
  - The F1 list shows no flow section and "Ctrl + 1 … 3".
  - *Move recording to trash* listed 22 files and named the old optical-flow
    files. All 22 ended up in one `.trash/` folder with their subfolders: both
    `Flows/` files, the four flow pickles and the two flow plots. No file of
    that recording was left behind, and the real `Flows/` folder was
    untouched.

### Not done

- The old flow files in the real data folder are still there. Deleting them, or
  moving them somewhere for the record, is the user's call.
- Next, as planned: improve the velocity estimator. The list in last session's
  notes includes:
  - verify the real frame rate and the calibration
  - sub-frame lag
  - trend removal
  - treat lag 0 as censored instead of dropping it
  - path length along the vessel
  - the negative-to-zero clipping in `report_summary.csv`
  - validation

---

## 2026-10-05 — GUI rebuilt from scratch

**Branch:** `feat/gui-rebuild`, based on `refactor/remove-dead-code` (`4f785bc`),
which is not merged yet. Merge that pull request first, then this one.

**Commits:**

- `24543cf` Add frame-range measurement, data set files and flow arithmetic to capillary
- `5a1784c` Rebuild the GUI from scratch as the gui package
- `f6ccea7` Remove the old GUI
- `d7a3a1a` Update README and CLAUDE.md for the new GUI
- `45a15ac` Analyze: say so when a measurement resolved no velocity

### Why

The user asked for the GUI to be rebuilt from scratch: it was outdated and
not intuitive. Concretely, the old window had these problems:

- **Measuring meant playing the video.** Each frame shown with the boxes on it
  added one sample. A measurement took as long as the clip. Moving a box
  half-way silently mixed two positions into one data set. Frames played
  before the boxes were placed were recorded too.
- The two boxes differed only by colour (white, black) and a modifier key.
  Nothing said that box 1 must be the downstream one, although the sign of
  every velocity depends on it.
- Nothing showed whether the boxes were placed well until a report had been
  saved and generated.
- Stabilization and optical flow ran one frame per tick of the window's main
  loop, so the window was unusable for minutes.
- Six of the seven known issues listed after the clean-up were GUI defects:
  popups took over the close button, the Capture tab broke the keyboard
  controls, the save popup warned falsely, Generate report and the
  "all videos" options crashed, and the camera was never released.
- Deleting a video deleted it permanently.

### The new GUI (`5a1784c`)

One window: a list of recordings on the left, and four pages. A recording is
everything that shares one video's name: raw capture, stabilized copy,
optical flow, data sets, time points. `Application.py` only sets up logging
(now a rotating `capillaroscopy.log`) and opens the window from the new `gui/`
package (19 modules; `README.md` has the table).

- **Analyze.** Box 1 (orange) is labelled downstream and box 2 (blue)
  upstream. A dashed arrow from box 2 to box 1 shows the flow direction that
  counts as positive. A click places the selected box, and selection then
  moves on to box 2. Right-click or Ctrl+click places box 2, dragging moves a
  box, WASD nudges it, X swaps the boxes.
  - The panel shows the box separation (px and µm) and the velocities that
    separation can resolve. The fastest is a lag of 1 frame, the slowest a lag
    of 100 frames in the 201-frame window. For example, boxes 29.1 px apart
    cannot resolve anything faster than 1.16 mm/s.
  - A live **signal preview** reads the 201 frames around the playhead in the
    background and runs the report's own `lag_and_correlation` on them. It
    plots both box signals and shows the correlation, the lag and the velocity.
    It warns when the lag is 0 (too fast for this separation, or a brightness
    change over the whole image), when the lag hits the window limit, when the
    correlation is weak, or when the boxes look swapped.
- **Measure.** The user sets a frame range on the timeline (I/O), names the
  data set and presses *Measure velocity and save*.
  - `capillary.measure` reads that range straight from the file, with the
    boxes fixed, in a background job: 401 frames of a real clip took 2.9 s,
    against 13 s of playback before.
  - The data set is saved in the existing file formats, and the report is
    written by the unchanged report code. Old and new data sets therefore go
    through the same arithmetic.
  - Each data set also gets a `___velocity_provenance.json` (or
    `___flow_provenance.json`). It records the video, box centres and size,
    frame range, separation, calibration, report settings, a summary of the
    result and the git commit. The numbers can be traced to their inputs, and
    the Results page uses this file to put the boxes back.
- **Flow.** The user draws a region over a vessel on the optical-flow video.
  The vessel mask can be shown as an overlay, and a colour wheel explains the
  direction colours. The region and the current frame's flow are read out
  live. *Measure flow and save* works like velocity. Two errors in the old
  flow display are fixed: a brightness boost that wrapped around in uint8, so
  fast flow looked dark, and swapped red and blue. Only the picture changed;
  measurements read the raw frames.
- **Capture.** The camera is read on its own thread, so recording keeps the
  camera's pace, not the window's redraw rate. The page warns if the camera's
  measured frame rate is more than 5% away from the 30 fps written into every
  recording. Time points marked during recording are saved at once. The
  camera is released when the page is left.
- **Results.** For one recording: its files, time points and data sets. Each
  data set card shows a summary (median velocity and interquartile range,
  share of windows resolved, share too fast to resolve, median correlation)
  and its settings, if it has a provenance file. Its report plots open in a
  viewer. The report can be regenerated, for example after adding time points,
  and the boxes can be restored on the Analyze page. Data sets made before this
  change are marked as having no recorded settings.
- **Background work.** Stabilize, optical flow, measurements and reports run as
  jobs in two lanes, so a measurement never waits behind a long flow
  computation. Each job shows progress and time left and can be cancelled.
  Videos are written into a hidden `.partial/` folder and moved into place only
  when complete. A stabilization that would need more than 85% of the
  available memory is refused instead of crashing the app (see Not done).
- **Nothing is deleted outright.** Replacing a data set, re-stabilizing,
  recomputing flow, and removing a data set or a whole recording all move the
  old files to `.trash/<date-time>_<label>/` in the data folder. Each file
  keeps its subfolder, so it can be put back by hand. Each of these actions
  asks for confirmation first.
- **Keyboard and settings.** Keys are routed in one place and ignored while
  typing in a text field. F1 lists every control. A settings dialog holds the
  data folder, the calibration (shown in µm per pixel as well) and the default
  box size. The new `box_size` row is added to `settings.csv`, and rows the app
  does not know are kept.

### Engine additions (`24543cf`)

Everything the GUI computes goes through GUI-free code in `capillary/`:

- `measure.py`: `measure_velocity` and `measure_flow`. The first is
  `extract_traces` (the same sampling as the CLI) plus the per-frame sharpness
  score, computed on worker threads with an identical result. Both report
  progress and can be cancelled.
- `datasets.py`: file names and formats, data set names (validated, so the
  old "not saved" false alarm cannot recur), time points, the writers, and the
  provenance file.
- `flow.py`: drag-box bounds and flow magnitudes. These are copied verbatim
  from `Caper.Rectangle` and `FrameClasses.FlowFrame`, and tests check them
  against frozen copies of the originals.
- `quality.py`: `calculate_blur`, moved from `Utilities.py`, which still
  re-exports it.
- `velocity.py`: `resolvable_range` and `velocity_summary`.
- `video.py`: `iter_frames` can start at any frame.

### Caper.py (`5a1784c`)

`Caper.py` keeps stabilization, optical flow and the reports, and drops what
only the old GUI used:

- `Rectangle`, `ColorVideo`, `VideoCamera`, the `…Multiple` classes, and the
  live-recording half of `CrossCorrelation`.
- `CrossCorrelation` now takes `fps` and `mm_per_pixel` instead of a video and
  two GUI rectangles. Report generation can report its progress and closes its
  figures, so a long session does not accumulate them.
- The flow report moved here from `FrameClasses.FlowFrame` as
  `generate_flow_report`.

None of this changes a single output byte; see Verification.

### Removed (`f6ccea7`)

- `Analyze_Frame`, `Flow_Frame`, `Camera_Frame`, `FrameClasses`, `Popup_Frame`,
  `Save_Data_Popup`, `Choose_Report_Popup` and `Process_Frame`. Together with
  the old `Application.py` that is 1,897 lines, replaced by 6,542 lines in
  `gui/`.
- Five icons only they used; `Source/` keeps `Capture-Logo.png` as the window
  icon.
- The `Utilities` helpers only they called.
- `.gitlab-ci.yml` imports `gui.app` instead of `FrameClasses`. `.gitignore`
  covers `.trash/`, `.partial/` and the rotated log files.

### Differences between old and new data sets

Methods-relevant. The report arithmetic is unchanged, but the inputs are now
collected differently:

1. **Frame index.** The old Analyze tab read the next frame, then stored it
   under the previous frame's number, so frame k+1 sat at index k. Times in
   old data sets therefore read one frame (33 ms) early. New data sets store
   frame k at index k. Velocities are unaffected, since both boxes share the
   shift.
2. **Frame rate.** The old report used the integer part of the file's frame
   rate; the new one uses the exact value. This makes no difference for the
   existing videos, which are all exactly 30 fps.
3. **Box separation.** The old tab stored, per frame, the distance between the
   raw click points. The new tab stores one constant distance between the box
   centres after they are kept inside the image, as the CLI always did. The two
   differ only for a box touching the image edge.
4. **Which frames.** Old data sets contain every frame that happened to be
   played, including frames before the boxes were placed, and a replayed
   stretch overwrote the earlier samples. New data sets contain exactly the
   chosen range; all other frames are NaN. The intensity table now has a
   column for every frame; the old one dropped the last.
5. **Flow units.** The flow report's values are optical-flow displacement per
   frame (mm/frame), not per second. This is unchanged and now stated in the
   provenance file.

### Verification

- **Unit tests:** 154 pass, up from 78 before this work. New tests cover:
  - `measure_velocity`: exactly equal to `extract_traces_from_video` on MP4V
    and uncompressed video, plus ranges, the sharpness cache, progress and
    cancelling.
  - End to end: a synthetic clip is measured, saved and run through the
    unchanged report, which recovers the known velocity within 5%.
  - File formats and data set names.
  - The flow arithmetic against the original code, for all 8⁴ drag
    combinations.
  - The GUI's non-visual logic: settings, the recording list, the trash,
    recording names and background jobs.

  Each of the three code commits was also tested on its own, from a checkout of
  exactly that commit (141, 154 and 154 pass). At the first one the old GUI
  still imports.
- **Reports are byte-identical:** the refactored `Caper` regenerated the
  velocity reports of `…___Test` and `…___Test2` and the flow reports of
  `…___Test_1` and the unnamed flow data set. All 26 files are identical to the
  output of the code at `4f785bc`.
- **Scripted GUI sessions.** These ran the real window under WSLg on a scratch
  data folder: links to the real videos plus copies of `Statistics/` and
  `Reports/`. Screenshots were reviewed after each round, and every session
  ended with no Tk errors.
  - Placing boxes and checking the preview.
  - Measuring a range of a real recording.
  - Stabilizing and computing flow for a synthetic jittered recording, then
    measuring flow on it.
  - The Results page, report viewer, dialogs, and Capture without a camera.
  - Replacing a data set and moving a recording to the trash.
  - 30 keyboard checks through the key router.
  - Starting through `main()` and quitting while a preview was reading frames.
- **Two bugs found by those sessions and fixed before committing:**
  - Moving a recording to the trash flattened the folders. Its raw, stabilized
    and flow videos share a file name, so they would have overwritten each
    other. This was caught on the scratch copy of the synthetic recording. Files
    now keep their subfolders, and a test pins it.
  - Quitting while a background thread was inside OpenCV aborted the process
    ("terminate called…"). Shutdown now stops every thread and waits for it.
- **One false alarm.** In one session a "Replace data set?" confirmation seemed
  never to appear. The scripts had kept only the main test window from taking
  keyboard focus, not its dialogs, so keys typed on the desktop at that moment
  could close a dialog. With the dialogs made unfocusable as well, the
  confirmation stays open until the script answers it, and the replacement
  then runs. The app was not at fault.
- **Static checks:** pyflakes reports only the intentional `calculate_blur`
  re-export and the old unused import in `SingleStepDFT.py`. The CI's flake8
  error selection finds nothing.
- **Real data untouched:** no file in `RecordedVideos/`, `StabilizedVideos/`,
  `Flows/`, `Statistics/` or `Reports/` was modified during this session. The
  newest, the `…___Test` report written at 16:46, predates the session.
  There is no `.trash/` or `.partial/` in the repository folder.

### Not done

- **Stabilization still has its two problems.** It is off by one frame (see
  Known issues). It also keeps the whole video in memory twice as float64:
  about 21 GB for the 4,306-frame clip and 37 GB for the longest, 7,524
  frames. The new memory check refuses such runs instead of letting them crash
  the app. On a typical machine, recordings as long as the existing ones
  therefore cannot be stabilized in the app until `VideoStabilization` is
  reworked. That rework changes its output, so it needs its own verification.
- Recording has not been tried with a real camera; none is reachable under
  WSL.
- The GUI has been driven by scripts and checked on screenshots, but not yet by
  hand. A hands-on session should come first: dragging boxes, zoom, playback,
  the general feel.
- The `.thumbnails/` caches of the old GUI in `StabilizedVideos/` and `Flows/`
  are no longer used and can be deleted by hand.
- CI is still defined only in `.gitlab-ci.yml`, which GitHub ignores.

---

## 2026-10-05 — Clean-up: remove dead code and unused files

**Branch:** `refactor/remove-dead-code` (off `main` at `f87891c`), to be merged through a pull request.

**Commits:**

- `839626e` Normalize line endings to LF
- `cc99fb4` Remove dead code, unused files and leftover debugging
- `a7e53dd` Fix "Stabilize all videos" and "Calculate flow for all" on NumPy 2
- `9feb83b` Update docs and config after the clean-up

### Why

The GUI code carried a lot of material that no longer did anything: an
unreachable tab, a scratch script, never-instantiated classes, broken methods
nobody called, hundreds of lines of commented-out code, copy-pasted imports and
debug prints. It made the code hard to read and hid which parts actually run.
The aim was to remove that **without changing behaviour**, and to prove it.

Python code went from **6,426 to 4,346 lines (−32%)**; 15 unused binary
assets (about 7 MB) left the working tree. Everything removed stays in the git
history.

### Line endings first

The original modules were stored with Windows (CRLF) line endings; the newer
code uses LF. `839626e` converts them on its own, with no content changes
(`git diff --ignore-cr-at-eol` is empty), so the following commits show only
real changes. A `.gitattributes` keeps text files LF from now on.

### What was removed (`cc99fb4`)

Files:

| File | Why it was dead |
| --- | --- |
| `Stabilization.py` | Scratch script; ran on import against a hard-coded `Data/FP07_…avi` that does not exist |
| `Stabilize_Frame.py` | The Stabilize tab: its menu button was commented out and nothing else selected it. Stabilizing runs through a video's options popup and `Process_Frame` |
| `ProgressMonitor.py` | Its time-remaining text was only displayed on that unreachable tab |
| `Logo/` (12 files) | Photoshop sources and PNG/BMP icons; nothing references them |
| `Source/Capture.png`, `Source/Capture2.png`, `Source/Quicksand-Regular.ttf` | Not referenced (the font only in commented-out code) |

Code: `MatplotlibFrame` (never instantiated); `VideoStabilization.stabilize()`
(unreachable, and would have crashed: it called methods with missing
arguments); `CrossCorrelation.test()` (broken); `Video.load()` and
`ColorVideo.load()` (used only by the removed script and method); a shadowed
duplicate `Menu._resize`; unused methods, attributes and parameters; all
commented-out code; debug prints (`print('here mate')`, the correlation value
every 20 frames, the canvas size, the video list); duplicate and unused
imports, including `seaborn` and `scikit-video`. The `from Utilities import *`
star imports are now explicit, so static checks can see every name.

One removal saves work every frame: `Video.get_frame` ran a sharpness FFT on
each frame into a vector that nothing read (the blur vector that *is* saved is
computed separately in `VideoFrame.update`). Playback in the test run reached
frame 320 about 20% sooner.

### Refactors (same commit)

- `Utilities.list_videos` / `video_stem` replace three copies of the video
  listing and the Windows/Linux path splitting. For file names with a single
  dot (all current data) the result is identical; names with extra dots are
  now matched by their full stem instead of the last dot-separated part.
- `FrameClasses.load_icon` replaces five copies of the icon loading code.
- The Analyze tab maps a click to video pixels with
  `canvas_to_video_coordinates`, the function the Flow tab fix introduced; it is
  the same arithmetic the Analyze tab had inline.
- `EntryWithSet` moved from `Caper.py` to `FrameClasses.py`, so `Caper.py` no
  longer imports tkinter.
- The Swedish notes on which box is which in `CrossCorrelation` contradicted
  the code (they called rectangle 1 black; it is drawn white). They are replaced by
  an English summary that matches the report's column names and
  `capillary/velocity.py`: rectangle 1 (white) is the box the blood reaches
  last, hence `velocity = distance / -lag`.
- `SingleStepDFT.py` is a modified copy of `image_registration.register_images`
  (different defaults and a different embedding index range). Only its unused
  imports were removed, and a docstring now records where it came from and why it
  must not be swapped for the package version unchecked.

### The one intentional behaviour change (`a7e53dd`)

"Stabilize all videos" and "Calculate flow for all" used `np.in1d`, which
NumPy 2.4 (the version in the venv) no longer has. On `main` both options
showed "AttributeError: module 'numpy' has no attribute 'in1d'" and processed
nothing. `np.isin` is NumPy's documented replacement and gives the same result
for these lists. With it, both options process the pending video and return
to the Analyze tab, and the output is byte-identical to processing that clip
on its own.

### Docs and config (`9feb83b`)

`requirements.txt` drops `seaborn` and `sk-video`. The README loses the stale
`/home/jacob-widaeus/...` paths and the ffmpeg install step (only scikit-video
needed it; OpenCV ships its own), and gains a code-layout table.
`settings.csv` loses an unused `logo2,test2` row, `.gitignore` the `ffmpeg/`
entry. `CLAUDE.md` now lists the controls and the known issues below.

### Verification

Baselines were recorded on `main` *before* any change, then compared with the
cleaned code. The harness scripts lived outside the repository and only read
real data; all outputs went to a scratch folder.

- **Unit tests:** 78/78 pass before and after.
- **Report pipeline:** `CrossCorrelation.calculate_cross_correlation` and
  `generate_report` regenerated both saved data sets in `Statistics/`
  (`…___Test` and `…___Test2`). All report CSVs are **byte-identical** to
  `main` and all plots **pixel-identical**, so dropping the seaborn import did
  not change the plot style.
- **Stabilization and optical flow:** a synthetic 640×480 clip (known jitter
  plus a moving blob) was stabilized and flow-processed, singly and through the
  "all videos" classes. The registration vectors, the stabilized video, the
  flow video and the flow pickle are all **byte-identical** to `main`.
- **Whole GUI:** a scripted session drove every reachable part of the app
  through Tk. On the Analyze tab: ROI click and Ctrl+click, WASD, the box size
  field, Save data, Generate report, Register time, pause, ±500 frames and the
  video bar. On the Flow tab: drag-select, Save data and Generate report. On
  the Capture tab: recording start and stop and Register time. From the options
  popup: Stabilize, Calculate flow and Delete, the latter on scratch copies.
  Before and after, the run produced the same files, the same box positions,
  the same correlation readout and **no errors**. Stabilize and flow run from
  the GUI produced byte-identical files.
- Static checks: pyflakes is clean apart from one unused import inside the
  vendored registration function; every module imports and compiles.
- The real data folders were checked afterwards: no file modified.

### Found, not fixed (listed in CLAUDE.md under Known issues)

These are real defects, left alone so that this change stays
behaviour-preserving. Each needs its own fix and check.

- **Stabilization is off by one frame.** `load_stabilization` reopens the
  video on its first step without reading a frame. As a result frame 0 of every
  video stabilized by the app is black, stabilized frame k is recorded frame
  k−1, and the last recorded frame is dropped. This was verified on the
  synthetic clip: frame 0 has mean intensity 0, and frame k matches input frame
  k−1 exactly. The 8 videos in `StabilizedVideos/` do **not** start with a
  black frame, so they were not produced by this code. Velocities from the
  cross-correlation are unaffected, since both boxes see the same delay, but
  timestamps are shifted by one frame (33 ms at 30 fps).
- Opening any popup re-binds the **main** window's close button to that
  popup, so the window's X no longer quits the app (Escape still does).
- Visiting the Capture tab replaces the window's key bindings, so the
  Analyze/Flow keyboard controls stop working until restart. P/space on the
  Capture tab raises an AttributeError, because the camera object has no `pause`.
- The Save-report popup says "the file was not saved" for names with spaces or
  non-ASCII characters, but the data is saved under that name anyway.
- Flow tab "Generate report" with no saved flow data raises `UnboundLocalError`.
- "Stabilize all videos" / "Calculate flow for all" with nothing left to process
  raise `IndexError`; `RecordedVideos/` is currently empty, so the former
  would.
- The camera is never released when leaving the Capture tab.

### Not done

- No restructuring into packages; file names and the tab/widget split are
  unchanged. `VideoFrame` and `FlowFrame` still duplicate their canvas and
  progress-bar code, and the four popup classes their window set-up.
- CI is still defined only in `.gitlab-ci.yml`, which GitHub ignores.

---

## 2026-10-05 — Merge the 2026-09-17 branches into `main`; work moved to own GitHub copy

**Branch:** `main`

**Repository.** Work now happens in a separate private copy,
`Soohan03/Capillaroscopy` (remote `origin`), so thesis work is independent of
the shared repo. The original `Widaeus/capillaroscopy` is kept as remote
`upstream` for pulling updates. All branches were copied with full history,
except `dev`, which was dropped as not relevant.

**Merges:**

- `53f1e4e` Merge `feat/analysis-engine-extraction`: the `capillary` engine package,
  the cross-correlation lag off-by-one fix and the unit tests (2026-09-17 entry
  below).
- `c2150be` Merge `fix/flow-tab-roi-selection`: Flow tab drag-rectangle and
  paused-frame fixes (2026-09-17 entry below).

`fix/short-term-improvements` needed no merge: PR #1 (`c3e57f4`) already
brought it into `main`.

**Conflict.** Only `DEVLOG.md`, where both branches added their entry at the
top. Both entries were kept, newest first. There were no code conflicts: the
branches touch disjoint files (`Caper.py` plus the new `capillary/` and
`tests/`, versus `FrameClasses.py`). The Flow tab still passes video-pixel
coordinates into `Rectangle.calculate_corners`, which now delegates to
`capillary.roi.ROI`, so the two changes compose.

### Verification

- Before merging, both merge orders were dry-run with `git merge-tree`. Both
  give the same single `DEVLOG.md` conflict.
- The final merge tree is byte-identical to the dry-run tree checked
  beforehand. It differs from each branch only by the other branch's changes.
- On merged `main`, all unit tests pass (`python -m pytest`), `capillary`,
  `Caper`, `FrameClasses` and `Application` import, and `compileall` is
  clean.
- The Flow tab coordinate fix survives the merge: a click at (350, 200) on a
  700x400 canvas showing a 1400x800 video maps to (700, 400).

### Not done

- CI exists only as `.gitlab-ci.yml`, which GitHub ignores, so the unit tests
  do not run automatically on the new repository.
- The Flow tab drag has not yet been confirmed interactively since its fix. One
  manual drag test is worth doing.

---

## 2026-09-17 — Flow tab: drag-rectangle lands in the wrong place, paused frame double-converted

**Branch:** `fix/flow-tab-roi-selection` (off `main` at `c3e57f4`). Independent
of `feat/analysis-engine-extraction`, which is still open as a PR; both branches
add an entry at the top of this file, so expect a trivial merge conflict here.

**Context:** the 2026-07-23 entry fixed Ctrl+click on the Analyze tab and
deliberately left the Flow tab's video frame class (`FlowFrame`,
`FrameClasses.py`) alone. This session went back to it. The stated suspicion —
that Flow tab needed the same Ctrl+click fix — turned out to be wrong: the Flow
tab has only one rectangle, selected by click-and-drag, so the Ctrl branch there
was dead code. Reading the handlers properly found three real defects instead.

### Defect 1 — the drag rectangle was stored in canvas pixels, not video pixels

`FlowFrame` shows the video resized to fit the window: a 1150x770 window gives a
805x539 area, and a 640x480 clip is aspect-fitted into that as **718x539**. So a
canvas pixel is not a video pixel (scale 1.122 in both axes).

The press handler (`callback`) correctly divided `event.x/y` by that scale. But
the release handler (`callback_release`) stored the raw `event.x/y`, and then
set `rectangle1.point1 = self.clickevent` — which the press handler had *also*
stored raw, alongside the scaled copy it never used. `Rectangle.calculate_corners_drag`
then clamped and sliced those canvas coordinates against the *frame*. Result:
the box the user dragged and the box the tool sampled were different boxes —
offset towards the bottom-right by up to ~12%, and 12% too large. A drag over a
vessel near the right or bottom edge sampled a region partly or wholly off it.

This matters for the thesis: the flow report divides flow by vessel-pixel count
inside the selection (see the 2026-07-07 entry). A mis-placed selection changes
that count and therefore every value in the report.

**Fix:** both handlers now go through one mapping,
`canvas_to_video_coordinates()` (a plain module-level function in
`FrameClasses.py`, kept GUI-free so it can be checked headlessly), wrapped by
`FlowFrame._canvas_to_video()`. `point1` and `point2` are both video pixels.

### Defect 2 — dead Ctrl detection

The press handler still carried the `self.master.current_key` /
platform-magic-number test (`[4,6]` / `[8,12]`) that the 2026-07-23 entry showed
never fires under X11. Here it guarded nothing — the `else` branch was `pass`
and there is no second rectangle — so it was removed rather than ported.

### Defect 3 — paused frames were HSV->BGR converted twice

`update()` stored the *processed* frame (`process_flow_frame` = HSV->BGR, x4)
as `self.previous_frame`, and the paused branch then ran `process_flow_frame`
on it again. Every flow video loads paused (`pause = 1` in `set_video`), and the
user pauses to drag the selection, so the still image people actually work on
had a colour conversion applied twice. `previous_frame` now holds the raw
rolling-average frame; both branches convert exactly once.

### Not changed

- Flow videos still load paused. Unlike the Analyze tab, that is the right
  default here: the selection is drawn on a still frame.
- `process_flow_frame` multiplies a `uint8` frame by 4, which wraps rather than
  saturates. Pre-existing, visual only, left alone.
- `CLAUDE.md` says `Flows/` is empty; it isn't (one generated flow video and
  its mask pickle from 2026-07-07). The file lives on the engine branch; fix the
  note there when that merges.

### Verification

- `python3 -m py_compile FrameClasses.py` passes.
- **Headless, against the real class.** A script constructed an actual
  `FlowFrame` under the WSLg display on the flow video in `Flows/`, confirmed
  the canvas came out 718x539 for the 640x480 clip (so the bug is visible, not
  masked by a coincidental 1:1 size), ran the paused branch first (as the app
  does), then one played tick, then paused again — `previous_frame` stayed a
  raw `uint8 (480, 640, 3)` frame throughout. It then delivered a synthetic
  press at canvas (100,100) and release at (400,300) through Tk's own event
  queue so the real bound handlers ran. Stored endpoints: `point1=(89, 89)`,
  `point2=(356, 267)` — the correct video pixels. The old code would have stored
  `(100,100)` and `(400,300)`. A further paused tick drew the box at
  x 89..356, y 89..267 and sliced a `(178, 267, 3)` region from the frame.
- The pure mapping was checked at the corners and centre, and for the identity
  case (canvas == video size).
- Note for reproducing: Tk silently drops synthetic button events aimed at an
  unmapped window; the frame has to be packed and the root shown first.
- App relaunched under WSLg after the change; the user was asked to try a drag
  on the Flow tab interactively.

---

## 2026-09-17 — Extract the analysis engine, and fix an off-by-one in the lag

**Branch:** `feat/analysis-engine-extraction` (off `main` at `c3e57f4`, the merge
of PR #1 `fix/short-term-improvements`)

**Commits:**

- `e002558` Add CLAUDE.md project instructions
- `e85763a` Extract the analysis engine into a GUI-free `capillary` package
- `5eb538f` Fix off-by-one in the cross-correlation lag and route the GUI through the engine
- `7a29e47` Document batch analysis and run the unit tests in CI

This is item 1 of the long-term list at the bottom of this file ("extract the
analysis engine into a GUI-free module with a CLI batch mode and unit tests
against synthetic videos with known velocity"). Writing the tests immediately
turned up a measurement bug, described in full below — it affects every velocity
this tool has ever reported, so read that section before using any earlier
report in the thesis.

### Why extract the engine

The measurement was only reachable by clicking. ROI geometry lived in
`Caper.Rectangle` interleaved with cv2 drawing calls; the velocity estimate
lived in `CrossCorrelation.calculate_cross_correlation`, which read its inputs
back from CSV files the GUI had written moments earlier and could not be invoked
without a Tk canvas. Nothing about the arithmetic could be run, checked, or
re-run on a different day with the same parameters.

For a methods section that has to defend its numbers, that is the wrong shape:
a result should be reproducible from recorded parameters, and the estimator
should be checkable against a signal whose answer is known in advance.

### The new package (`capillary/`)

No module in it imports tkinter, PIL or matplotlib.

| Module | What it holds |
| --- | --- |
| `roi.py` | `ROI`: the centred, frame-clamped sampling box as a value object |
| `video.py` | `probe_video` / `iter_frames`: streaming frame access |
| `intensity.py` | `IntensityTrace`, `extract_traces`: per-frame mean ROI intensity |
| `velocity.py` | `signed_lag`, `lag_and_correlation`, `sliding_lag`, `analyze_trace` |
| `cli.py` | `python -m capillary.cli` batch entry point |

Design decisions worth recording:

- **`ROI` reproduces `Rectangle.calculate_corners` exactly**, including its
  `int(w / 2)` halves (an 11-px box samples 10 columns) and its `>=` edge test.
  Those quirks were kept deliberately: "fixing" them would silently move every
  historical measurement by a pixel. The equivalence was verified mechanically
  (see Verification) rather than by eye.
- **Frames are streamed, not loaded.** `Caper.Video.load` allocates two float64
  arrays covering the whole clip (~26 GB for 60 s at 640x480), which is why
  batch analysis of a long recording was never possible. `iter_frames` holds one
  frame at a time. This is a partial answer to item 2 of the long-term list —
  the *analysis* path no longer has the problem; stabilisation still does.
- **Sliding windows are indexed by their centre frame.** The legacy report
  assigned each window's estimate to the frame at its *end* and then applied two
  compensating shifts (`(window - st) / 2`, then `-ceil(st / 2)`) to push the
  index back towards the middle. The engine just uses the centre directly, so a
  velocity is attributed to the moment it actually describes.
- **Explicit sign convention.** `signed_lag(a, b)` is positive when trace `b`
  lags `a`, so `velocity_from_lag` returns velocity along A -> B. The Analyze tab
  names its boxes the other way round (rectangle 1, the white box, is the one
  the blood reaches *last* — hence the legacy `/ -lag`), so `analyze_trace`
  defaults to `positive_flow='b_to_a'` and batch reports carry the same sign as
  GUI reports. This was previously only recoverable from Swedish comments and a
  column name reading `firstvec_white_islast_rect1_0`.

### The bug: every reported lag was one frame too large

`np.correlate(a, b, 'same')` places zero displacement at index `n // 2`. The
estimator computed

```python
lag = int(np.ceil(len(window) / 2) - np.argmax(correlation))
```

`ceil(n / 2)` equals `n // 2` for an even `n` and exceeds it by one for an odd
`n`. Every window length the report uses — `np.arange(201, 311, 20)` = 201, 221,
241, 261, 281, 301 — is odd. So every lag the tool has ever produced was one
frame too large, and velocity goes as `1 / lag`.

The bias is not a constant scale factor; it is a shift of the whole lag axis,
so its size depends on how fast the flow was:

- A true lag of -5 frames was reported as -4: **25% too fast**.
- A true lag of -1 frame was reported as 0: an infinite velocity.
- A true lag of -50 frames was reported as -49: 2% too fast, negligible.

It systematically **over**estimates the speeds the report plots as positive
(those come from negative lags, whose magnitude the shift shrinks).

`capillary.velocity.signed_lag` uses `n // 2`. `legacy=True` (and `--legacy-lag`
on the CLI) reproduces the old behaviour for comparison against existing
reports.

### What that means for the data already collected

Regenerating the saved `FP01_Qefter_22-Oct-2019_09-46-17___Test` report with the
fixed estimator (read-only; nothing in `Statistics/` was overwritten):

- All **5824** lag values move by exactly **1.0** frame, and nothing else
  changes — so the correction is the only behavioural difference, and the
  refactor itself is inert.
- **22.4%** of that recording's window estimates (1690 of 7542) had a true lag
  of **zero**: the plug crossed both boxes within one frame. The old code
  recorded these as a definite 1-frame lag, i.e. a spurious velocity of
  ~1.16 mm/s — which is simply the fastest that ROI separation (median 29.1 px)
  can express at 30 fps. They now report as unresolvable instead of as a
  measurement.
- Of the estimates that do resolve, the median absolute lag is 59 frames — about
  2 s to cross 29 px, i.e. genuinely slow flow — where a 1-frame error is under
  2%. That is why the *median* positive velocity only moves +3.7% while the mean
  and the upper tail move a lot (positive-sample mean 0.145 -> 0.100 mm/s,
  p95 0.605 -> 0.322 mm/s): the bias is concentrated in the fast samples.

**Implication for the thesis, to discuss with the supervisors:** the sizeable
zero-lag fraction is a real limitation of the method as configured, not a
software fault. At 30 fps with boxes ~29 px apart, anything faster than
~1.16 mm/s is unmeasurable. If faster flows matter, the boxes need to sit
further apart, or the lag needs sub-frame interpolation. Any velocity previously
reported at or near ~1.16 mm/s for this configuration should be treated as
"too fast to measure" rather than as a value.

### Other corrections made in passing

- A correlation window containing missing samples now yields NaN. Previously
  `np.argmax` of an all-NaN array returned 0, which silently produced a lag of
  `ceil(n / 2)` — a fabricated estimate. It is rare in the saved report (31 of
  7542 values) but indistinguishable from a real measurement when it happens.
- A zero lag yields NaN rather than an infinite velocity. The saved report
  contains 12 infinities, each of which drags any mean computed over its column
  to infinity.

### Single source of truth

`Caper.py` now calls into the package rather than keeping its own copies:
`Rectangle.calculate_corners` delegates to `ROI`, and both
`estimate_cross_correlation` (the live "Correlation" readout) and
`calculate_cross_correlation` (the saved report) call
`capillary.velocity.lag_and_correlation`. The GUI, the batch CLI and the tests
cannot drift apart.

### Batch mode

```bash
python3 -m capillary.cli StabilizedVideos/clip.avi \
    --roi1 320,240 --roi2 320,300 --size 10x10 \
    --out report.csv --summary-out summary.csv
```

`mm_per_pixel` is read from `settings.csv` unless `--mm-per-pixel` overrides it.
The point is reproducibility: the ROI coordinates, box size, window lengths and
calibration that produced a report are all on the command line, instead of
living in where somebody clicked.

### Verification

- **78 unit tests pass** (`python3 -m pytest`, 8 s). They cover ROI geometry and
  clamping, lag recovery, the velocity formula, NaN and zero-lag handling, the
  sliding window, CLI argument handling, and an end-to-end run.
- **Ground truth.** `tests/synthetic.py` generates clips in which an intensity
  pattern is translated at a chosen pixels-per-frame rate, so the true lag
  between two boxes and the true mm/s are both known exactly. A real clip cannot
  do this job — nobody knows how fast the blood in it was moving. The pipeline
  recovers the planted velocity to within 5%, and doubling the planted speed
  doubles the measured one (within 10%).
- **The off-by-one is pinned by tests** in both directions: `legacy=True` must
  return `true_lag + 1` on odd windows and `true_lag` on even ones, and on a
  synthetic clip the legacy path must land further from the known truth.
- **The refactor is inert.** `Rectangle.calculate_corners` was compared against
  a verbatim copy of the pre-refactor arithmetic over 768 combinations of click
  position, box size and frame size (including boxes clamped against all four
  edges): 768/768 identical, and the selected pixel patch is unmoved.
- **Real data.** The saved report regeneration described above: 5824/5824 lag
  values differ by exactly 1.0 and nothing else changed.
- **The app still runs.** Relaunched under WSLg after the rewiring: the update
  loop runs and the Analyze tab's correlation readout works, with no traceback.
  (The `RuntimeWarning: Mean of empty slice` at `Caper.py:828` is the
  pre-existing benign one — `nanmean` over an empty ROI before boxes are placed.)
- `python3 -m py_compile` passes on `Caper.py`, `Application.py`,
  `FrameClasses.py` and every new module.
- CI (`.gitlab-ci.yml`) gained a `unit-tests` job running pytest. The existing
  job could only prove the modules import.

### Not done

- The legacy report path still round-trips through `Statistics/*.csv` files and
  still applies its own index shifts; only the estimator inside it was replaced.
  Rewriting `generate_report` on top of `analyze_trace` is the natural follow-up.
- `Video.load` (stabilisation) still allocates whole-clip arrays — long-term
  item 2 remains open for that path.
- No provenance sidecar yet (long-term item 3); the CLI makes parameters
  explicit but does not yet record them alongside the output.
- Flow/stabilisation are still GUI-bound. Only the cross-correlation velocity
  path was extracted.

---

## 2026-07-23 — Fix Ctrl+click (2nd ROI box) and video-not-playing on Analyze tab

**Branch:** `fix/short-term-improvements` (continued)

**Symptoms reported by user:** on the Analyze tab, (1) Ctrl + left-click did
not place the second ROI box, and (2) a loaded video did not appear to play.

**Diagnosis:**

1. *Ctrl+click.* The video-canvas click handler in `FrameClasses.py`
   (`VideoFrame.callback`) decided whether Ctrl was held by reading a
   separately-tracked keyboard state (`self.master.current_key`, set from
   `<Key>`/`<KeyRelease>` events) and comparing it against platform-specific
   magic numbers (`[4,6]` on Linux/darwin, `[8,12]` on win32). Under X11/WSLg
   `current_key` never actually holds the Control value at click time
   (`<KeyRelease>` resets it to `None`, and a Control key-press reports the
   modifier state *before* the press), so the test was always false and every
   click — Ctrl or not — fell through to `rectangle1`. Box 2 could never be
   placed.

2. *Video not playing.* Three compounding causes:
   - `VideoFrame.set_video()` ended by setting `self.master.video.pause = 1`,
     so every freshly loaded video started **frozen on frame 0**.
   - `Application._resize` (bound to `<Configure>`) set `video.pause = 1` on
     *every* configure event — which fires during normal window setup and
     redraws — and never reset it. So even after pressing P/Space, any window
     move/resize re-froze the video.
   - The main update loop's `delay` was hard-pinned to 1 ms, so once a video
     did advance it ran at hundreds of fps and flashed past in a fraction of a
     second (also reading as "not playing").
   The frozen state was visible in the console as a flood of identical `N/A`
   lines (~26+/sec): `estimate_cross_correlation` prints on
   `frame_number % 20 == 0`, and with the counter stuck at frame 0 that fired
   on essentially every tick.

**Fixes:**
- `FrameClasses.py` (`VideoFrame.callback`): detect Ctrl directly from the
  mouse event's modifier mask — `bool(event.state & 0x0004)` (0x0004 is the
  Control bit on both X11 and Windows). Removed the `current_key` /
  platform-magic-number path.
- `FrameClasses.py` (`VideoFrame.set_video`): load videos **playing**
  (`pause = 0`) instead of paused. Users pause with P/Space to position ROI
  boxes on a still frame.
- `Application.py` (`_resize`): removed the unconditional `video.pause = 1` on
  `<Configure>`. The video canvas is a fixed size, so there is nothing to
  protect by pausing on resize.
- `Application.py` (`_update_body`): pace the loop to the video's native frame
  rate — `delay = max(1, round(1000 / video.fps_))` — instead of a hard 1 ms,
  so playback runs at real (~30 fps) speed.

**Verification:** `python -m py_compile Application.py FrameClasses.py` passes.
Relaunched the app under WSLg. *Before* the fixes the console flooded with
~26 identical `N/A`/sec (counter frozen at frame 0); *after*, that flood stops
and the log shows advancing, varied output including real correlation estimates
(e.g. `0.5`, `0.8`) with no traceback — i.e. frames now advance at a sane rate.
The Ctrl+click fix was verified by inspection (standard X11/Windows Control
mask `0x0004`); the actual GUI click is not scriptable in this environment, so
the user was asked to confirm it interactively.

**Notes / not changed:**
- The `RuntimeWarning: Mean of empty slice` at `Caper.py:831` is pre-existing
  and benign (numpy `nanmean` over an empty ROI selection before boxes are
  placed); it is unrelated to these changes.
- The second video frame class (`FrameClasses.py:1194`, used by the crash-prone
  Flow tab) still loads paused and still uses the old `current_key` click path.
  Left untouched deliberately — see Known Issues (Flow tab).

---

## 2026-07-07 — Fix Flow tab drag-rectangle crash (empty reports)

**Branch:** `fix/short-term-improvements` (continued)

**Symptom reported by user:** after calculating flow for a video and
saving the selection as "Test_1", the generated flow report chart was
empty.

**Diagnosis:** inspected the saved pickles in `Statistics/`. Of 4,306
frames only 1 had flow data, and that frame's region was the default
10x10 corner box with 0 vessel pixels in its mask. The report divides
flow by vessel-pixel count, so every value was NaN and the plot was
blank. Root cause in `capillaroscopy.log`: `UnboundLocalError: 'ltr'` in
`Rectangle.calculate_corners_drag` (Caper.py). The function only set its
left-to-right flag when the drag's x-coordinates differed and only set
corners when the y-coordinates differed, so a pure click or a
vertical/horizontal drag either crashed or returned None (resetting to
the 10x10 default). The crash was caught by the new update-loop guard but
stopped flow recording after the first frame.

**Fix (commit — Caper.py):** rewrote `calculate_corners_drag` to
normalize any two drag endpoints into an axis-aligned rectangle
regardless of direction, enforce a minimum size so the region is never
degenerate, and clamp to the frame bounds. Always returns True. Corner
naming kept consistent with `get_selected_data_for_flow`/`_for_mask`
(image coordinates, y down).

**Verification:** headless test over pure click, vertical drag,
horizontal drag, both diagonal directions, and off-edge points — every
case yields a valid non-empty box and no exception; the two opposite
diagonals produce the identical rectangle.

**User-facing note:** on the Flow tab the ROI is selected by click-and-
drag over a vessel (not a single click as on the Analyze tab). The old
"Test_1" data was captured with an empty region and should be re-recorded
after this fix.

---

## 2026-07-06 — Codebase audit + short-term fixes

**Branch:** `fix/short-term-improvements` (pushed to GitLab, 7 commits)
**Context:** Full audit of the codebase (~5,100 lines, 15 modules) identified
correctness bugs, performance problems, and thesis-relevant scientific issues.
The "short-term list" from that audit was then implemented. The audit's
long-term recommendations are listed at the end of this entry.

### Commit 1 — `93adccd` WIP fixes (pre-existing work, committed separately)

Uncommitted changes that were already in the working tree, committed on their
own so they stay distinguishable from the new fixes:

- Removed a leftover `pdb.set_trace()` in `Application.py` that dropped the
  app into the debugger on start.
- `VideoCamera` (Caper.py): falls back to 640x480 @ 30 fps and a black frame
  when no camera is connected, instead of crashing.
- `ParticipantList` (FrameClasses.py): the Analyze tab falls back to
  `StabilizedVideos/` when `RecordedVideos/` is empty.
- `settings.csv`: `Application_path` updated for this machine.
- Added `run_app.sh` helper to launch the app under WSL.

### Commit 2 — `5b30edb` Crash-proof the main update loop and add logging

**Problem:** the entire UI is driven by one `master.after()` chain in
`Application.update()`. Any uncaught exception anywhere in a tab's `update()`
killed that chain and silently froze the whole app — this is exactly how the
Flow tab crash used to lock everything up.

**Change (Application.py):**
- The loop body moved into `_update_body()`; `update()` wraps it in
  try/except and always reschedules itself.
- Errors are logged with a full traceback to `capillaroscopy.log` and shown
  in a dialog once per unique error (deduplicated so a recurring error does
  not spam dialogs every millisecond).
- Replaced the commented-out logging experiments with a real
  `logging.basicConfig` (file + console) in `__main__`.

### Commit 3 — `ee10cd7` Fix Flow tab crash when Flows/ is empty

**Problem:** opening the Flow tab with no flow videos passed
`selected_item=None` into `Video.__init__`, which crashed on
`path.replace()` (the known issue from CLAUDE.md).

**Change:**
- `Video.__init__` (Caper.py) tolerates `path=None`.
- `Flow_Frame` only builds a `FlowFrame` when a video is actually selected,
  and shows an explanatory empty-state label otherwise ("No flow videos
  found in Flows/ ..."), mirroring the pattern already used by the Analyze
  tab. The `FlowFrame` is created lazily once a video is chosen.

### Commit 4 — `a1a2db9` Fix TypeError in Capture tab "Register time"

**Problem:** `Camera_Frame.register_time_point` appended `self.frame/30`,
but `self.frame` is a Tk `PhotoImage` — every click raised `TypeError`.

**Change (Camera_Frame.py):** time points are now recorded as seconds since
the recording started (from `recording_timestamp`), and the button shows an
error dialog when no recording is running. Added explicit `pandas` and
`messagebox` imports instead of relying on star-imports.

### Commit 5 — `8dddbf4` Real frame rate + configurable spatial calibration

**Problem (scientifically the most important fix):** the velocity pipeline
assumed 30 fps everywhere — velocity formula, time displays, time-point
markers, flow reports. Any video not recorded at exactly 30 fps produced
proportionally wrong velocities. The magnification coefficient
(`1.328903654e-06 * 1000`) was hardcoded in two places with no provenance.

**Changes:**
- All fps reads in Caper.py fall back to 30 only when the file reports none
  (`... or 30`); `CrossCorrelation` now takes the video's real `fps_` and
  uses it in the velocity formula and the seconds index.
- Magnification is now `mm_per_pixel` in `settings.csv` (default
  `0.001328903654`, the original value). Missing settings keys are
  auto-filled and persisted on startup. `Application` exposes it as
  `master.mm_per_pixel`; `VideoFrame` passes it into `CrossCorrelation`;
  the flow report in `FrameClasses.py` reads it too.
- Fixed the report summary CSV `time` column, which divided an index that
  was already in seconds by 30 a second time.
- Collapsed the duplicated settings/mkdir blocks in `Application.__init__`
  (ten try/except `os.mkdir` blocks) into one `os.makedirs(exist_ok=True)`
  loop; the first-run branch no longer writes the legacy `logo2` junk row.

**Note:** the existing StabilizedVideos are 30 fps, so results for current
data are unchanged; this matters for future recordings.

### Commit 6 — `8ee6fa6` Cleanup: no rename-on-listing, narrowed bare excepts

- `get_items_from_path` (two copies: FrameClasses.py, Process_Frame.py)
  renamed files on disk (stripping commas) as a side effect of *listing* a
  directory. It now just returns a sorted listing.
- `ProgressMonitor.py` ran test code at import time; removed.
- Application key handler: the q/e/p video controls were unguarded and
  raised `AttributeError` when no video was loaded; the handler now
  tolerates the no-video state explicitly.
- Narrowed several bare `except:` blocks to the exceptions they actually
  expect (missing time-point CSV, non-numeric entry text, missing flow
  pickle, first fps-ticker tick) so real bugs are no longer swallowed.
- Flow save errors are logged with a traceback instead of only showing
  "An unknown error has occured".

### Commit 7 — `247bda6` Cache video thumbnails and durations on disk

**Problem:** `ParticipantList` reopened and decoded every video on every
list refresh (each click, selection, repack) to regenerate thumbnails.

**Change (FrameClasses.py):** thumbnails + durations are cached as pickles
in a `.thumbnails/` folder next to the videos, invalidated by file mtime.
The capture handle is released after thumbnail generation (was leaked).
`.gitignore` now covers `.thumbnails/` and `capillaroscopy.log`.

### Verification

- App launched via `run_app.sh` under WSLg: no tracebacks, update loop ran,
  thumbnail cache was built on first launch, `capillaroscopy.log` stayed
  empty (0 bytes) through a full run and clean exit.
- Headless smoke test: `Video(None)` constructs without crashing;
  `CrossCorrelation` picks up fps=30.0 from a real stabilized video and the
  configured `mm_per_pixel`.
- Every commit was syntax-checked with `py_compile` before committing.

### Audit findings deliberately NOT fixed yet (long-term list)

1. Extract the analysis engine (CrossCorrelation, stabilization, flow) into
   a GUI-free module with a CLI batch mode and unit tests against synthetic
   videos with known velocity — key for thesis reproducibility.
   *Done for the cross-correlation velocity path on 2026-09-17 (`capillary/`);
   stabilization and flow are still GUI-bound.*
2. Stream video processing: `Video.load` still allocates two float64 arrays
   covering the whole video (~26 GB for a 60 s clip) — stabilization of
   long videos will exhaust memory. *The analysis path now streams
   (`capillary.video.iter_frames`, 2026-09-17); stabilization still does not.*
3. Save analysis provenance (ROI coordinates, rectangle size, window
   parameters, git hash) as a JSON sidecar with every report.
4. Worker thread/process for stabilization/flow instead of one frame per
   UI tick.
5. Consider `skimage.registration.phase_cross_correlation` to replace the
   custom DFT registration, and `cv2.DISOpticalFlow` to replace Farneback.
6. Statistics layer: aggregate per-participant results into one tidy CSV.
7. Retire the 1 ms `after()` busy-loop (renders even when paused; pins a
   CPU core) in favor of fps-paced, redraw-on-change updates.
