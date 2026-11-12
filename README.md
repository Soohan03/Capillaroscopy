# Capillaroscopy Analysis Tool

A desktop tool (Python, Tkinter and OpenCV) that measures red-cell velocity in
nailfold capillaries from capillaroscopy videos. It stabilizes a recording,
lets an observer draw a line along a capillary, and reads the velocity from
the brightness pattern that moves along that line.

It was built for a degree project in medicine at Karolinska Institutet (2026),
"Nailfold capillary blood cell velocity in healthy individuals: inter-day
reproducibility and response to e-cigarettes and heated tobacco products". The
repository holds the tool, the study's measurement and analysis protocol, and
the analyses behind the results.

## What is here

| Path | What it holds |
| --- | --- |
| `Application.py`, `gui/` | The app: recordings, the Centre line page, the Results page, blind placement |
| `capillary/` | The measurement, without any GUI: stabilizer, space-time diagram, velocity estimators, the study's recordings and statistics, simulator and benchmark |
| `tests/` | Unit tests, on synthetic videos with a known velocity |
| `PROTOCOL.md` | The study's measurement and analysis protocol, fixed before the first line was placed, with every later change dated |
| `analysis/` | The analyses, each with its scripts, result tables and a README; `analysis/README.md` lists them |
| `metadata/` | The official occlusion and release times of every recording, and which recordings the aims use |
| `DEVLOG.md` | The diary of every change: what, why, and how it was checked. The code and the protocol cite its entries by date |
| `CLAUDE.md` | The working instructions for Claude Code, the AI coding assistant the code was written with |

The videos and the measurements made on them are not in the repository. They
stay in the data folder (below), which git ignores.

## The study in brief

- **Recordings:** a retrospective archive of two crossover trials. In ESMOKE
  (2019–2020) participants used an e-cigarette with nicotine (W) and one
  without (Q); in ISMOKE (2020) a heated tobacco product (S) and no exposure
  (C). Each visit has a recording before (före) and after (efter) the exposure.
- **Every recording** is about a minute of rest, a minute of occlusion (a cuff
  at 200 mmHg at the base of the finger) and about a minute after release.
  Resting velocity is measured in the rest before the occlusion.
- **Aim 1 (primary):** the inter-day reproducibility of resting velocity, from
  the two before-exposure recordings of each participant.
- **Aim 2:** the change from before to after exposure on the nicotine visit.
- **The measurement** is fixed in `PROTOCOL.md`: one line round a whole
  capillary loop, placed blind, measured over the official rest, counted from
  a signal-to-noise ratio of 8. The results are in `analysis/`.

## Setup

Python 3.12 with Tk. On Ubuntu Tk comes with `sudo apt install python3-tk`; on
macOS with Homebrew's `python-tk`. No separate ffmpeg is needed, since the
OpenCV wheel brings its own.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 Application.py          # or: bash run_app.sh
```

`requirements.txt` names the versions the study's results were computed with.
On first start the app asks for the data folder and the calibration. Messages
and errors are written to `capillaroscopy.log`.

## Using the app

The window has the list of recordings on the left and two pages. A recording
is everything that shares one video's name: the raw recording, its stabilized
copy and its data sets. The app does not record. Videos are copied into the
data folder.

**Stabilizing.** Right-click a recording, or use the **⋯** menu above the list
for all raw recordings at once. It runs in the background.

**Centre line page.** Click points along the middle of one capillary:

- drag a point to move it, click on the line to add one, right-click a point
  to remove it;
- choose what the line follows: any stretch of a capillary; an **arterial
  limb**, from its base to the apex; or a **whole loop**, from the base of one
  limb over the apex to the base of the other (the study's line);
- choose the frames to measure. For a recording of the study, **Rest**,
  **Occlusion** and **After release** set them from its official times;
- a live preview shows the space-time diagram of the frames around the
  playhead with the slope it found, and the panel shows which velocities the
  line can measure;
- on a stabilized video a dashed outline shows where every frame of the range
  has picture. A line that leaves it is refused (see below);
- the lines already saved for the recording are drawn dashed;
- name the data set, enter the observer's initials, and press **Measure
  velocity and save**.

**Results page.** The files, time points and data sets of a recording, with
their reports. A report can be written again, a data set moved to the trash,
and its line put back on the Centre line page.

**Blind placement** (the button in the header) is for placing the study's
lines with nothing but the anatomy deciding where they go:

- the list shows only the recordings the aims use, each under a code (a hash
  of its name), in the order of the codes;
- the space-time preview and every result are hidden;
- measuring uses the official rest, and every line is saved as a whole loop;
- the Results page is closed;
- it stays on between sessions until it is turned off.

Nothing is deleted outright. Replaced or removed videos and data sets go to
`.trash/` in the data folder, from where they can be put back by hand. **F1**
lists every keyboard and mouse control.

Every data set gets a `…_provenance.json` beside it: the video, the line's
points, the frames, the calibration, the estimator's settings, the observer
and the version of the code. A measurement reads its frames straight from the
video file with the line held fixed, so it can be repeated from that record.

## How a recording is stabilized

The skin moves under the microscope, so every frame is first moved back into
place (`capillary/stabilize.py`). Only translation is corrected.

1. **Following the movement.** Every frame is registered onto the frame before
   it, which gives the path of the picture through the recording. A frame that
   matches the one before it too poorly (the picture went dark, or jumped)
   breaks the path.
2. **What is compared.** Registration works on a band-passed copy of each
   frame (difference of Gaussians, σ 2 and 15 px). It removes pixel noise and
   the uneven lighting, which stays with the camera while the skin moves.
3. **Two references.** The sharpest frame among those where the picture
   usually is, taken from the official rest when the recording has official
   times, and the 12 frames on each side of it are aligned and averaged,
   alternately, into two references. Averaging smooths out the moving blood.
4. **Finding each frame.** Each frame is found in both references: a coarse
   search on frames made four times smaller (reaching about a third of the
   frame), then a fine search by normalized cross-correlation within 12 px of
   the coarse result and of where the path says the frame should be, to a
   fraction of a pixel. The frame's shift is the mean of the two results.
5. **Frames the references miss** (a poor match, references that disagree by
   more than 2 px, or a match at the edge of the search) are carried along the
   path from the frames that were placed. A stretch of path without any placed
   frame is lost and written black.
6. **Writing.** The shifts are centred on their median over the official rest.
   Each original frame is moved by its shift with bicubic interpolation and
   written uncompressed (8-bit grey), frame for frame.

The video is read from disk four times and never held in memory. A recording
of three minutes takes about three minutes. Next to the stabilized video,
`<recording>___stabilization.csv` holds every frame's shift and how sure it is
(how it was placed, how well it matched, how far the two references disagreed),
and `<recording>___stabilization_provenance.json` the settings and a summary.

**Lines must stay in the picture.** Where the picture moved, the frame moved
back into place has a black strip along its edge. A line that reaches the
strip sees its edge move along the line, which reads as flow. So a line on a
stabilized video is measured only if its samples keep 3 px clear of the strip
in every frame of the range (`stabilize.check_picture`). A range with lost
frames is refused as well.

## How velocity is measured

**The space-time diagram.** Along the drawn line the brightness is sampled in
every frame, averaged over 5 pixels across the line. Stacked over time this is
the space-time diagram: red cells and plasma gaps moving along the vessel draw
slanted streaks in it, and the slope of the streaks is their speed.

**Pattern shift, pooled over a stretch** (`capillary/pattern_shift.py`; the
study's measurement). How far the pattern along the line moves between a frame
and the next 1 to 8 frames:

- rows are band-passed along the line (difference of Gaussians, σ 1 and 4 px:
  cells and plasma gaps);
- each row is correlated with the later rows at every shift, forward minus
  backward, pooled over all 3-s blocks of the stretch, such as the minute of
  rest. Still structure, noise and brightness changes of the whole vessel at
  once are the same in both directions and cancel;
- the estimate comes with a signal-to-noise ratio (8 to count) and a 95%
  interval from leaving out one block at a time;
- speeds are searched from 1 px/frame (0.04 mm/s at 30 fps and 1.33 µm per
  pixel) up to half the line's length per frame.

Pooling is what makes the faint flow at rest measurable: single 3-s blocks
mostly miss it.

**The whole loop.** A line from the base of one limb, over the apex, to the
base of the other collects both limbs' signal, since the flow runs one way
round the loop. At rest it resolved more loops than lines on single limbs did
(`analysis/whole_loop/`).

- The direction of the pooled flow says which end of the line lies on the
  arterial limb.
- The line is split at its apex (the point farthest from both ends) and each
  limb is measured on its own. Flow runs the same way along the line in both.
  The picture moving along the loop runs opposite ways, so such a loop is
  marked and not counted.

**3-s blocks** (`capillary/spacetime.py`). The slope of the streaks in blocks
of 3 s, by a Radon-transform method evaluated in the Fourier domain, with a
signal-to-noise ratio and a coherence for each block. It gives the time course
of the velocity and the live preview. At 30 fps a line of *L* pixels follows
flow up to about 0.045 × *L* pixels per frame (0.18 mm/s for 100 px); faster
flow is reported as unresolved, not as a wrong number.

**Options the study does not use:**

- *The arterial limb.* A line drawn from a limb's base to the apex shows by
  the direction of its flow whether it is the arterial limb (towards the
  apex). At rest too few single limbs gave a signal
  (`analysis/aim1_feasibility/`).
- *The slow range.* Asked for, the pattern shift searches from 0.1 px/frame
  (`--slow-flow` in the batch command). Below 1 px/frame a single line cannot
  tell slow flow from the picture moving along it, so it is not the default
  (`analysis/pattern_shift_slow_flow/`).

## From the lines to the aims

```bash
python3 -m capillary.aims [--data <data folder>] [--observer SJ] [--progress] [--unblind]
                          [--value reference|reference-only|mean] [--min-snr 7]
```

collects the saved data sets into one resting velocity per recording, as
`PROTOCOL.md` fixes it, and computes both aims.

- **A loop counts** when it is a whole loop measured within the official rest,
  its pooled pattern shift is resolved (signal-to-noise 8 or more), its limbs
  did not move opposite ways along the line, it was measured on a stabilized
  video and its line does not cross itself.
- **A recording's value** is its reference capillary (`loop1`) if it counts,
  else the first backup that counts (`loop2`, `loop3`). `--value` and
  `--min-snr` give the protocol's sensitivity analyses.
- **Aim 1**, pooled over both studies (the primary result) and per study: the
  within-subject CV (typical error / mean), the smallest detectable change
  (2.77 × typical error), Bland–Altman and ICC(A,1) with its 95% interval.
- **Aim 2**, per study and pooled: the change after minus before exposure on
  the nicotine visit, with its 95% interval, a paired t-test, the Wilcoxon
  test and the ratio after / before.

The tables go to `Reports/aims/` in the data folder. While the app is in blind
placement the results stay hidden unless `--unblind` is passed, and
`--progress` shows how far placement got, under the codes, without a result.

Which recordings each aim uses comes from their names and official times
(`python3 -m capillary.inventory`, tables in `metadata/derived/`).

## How the method was checked

- **Synthetic recordings with a known velocity.** `capillary/simulate.py`
  renders capillary loops with red cells moving at a chosen speed, with the
  noise, the brightness changes of the whole vessel and the residual movement
  measured in the recordings. `python3 -m capillary.benchmark` measures them
  (about 4 minutes; `--quick` about 12 s). On a 120-px line the 3-s blocks are
  within about 2% from 0.25 to 5 px/frame and report faster flow as
  unresolved. The pooled pattern shift is within 1% from 2 to 8 px/frame and
  about 3% low at 12. Without flow the pooled pattern shift resolves no clip,
  while about 7% of single 3-s blocks still do.
- **Unit tests** (below) check the estimators, the stabilizer and the
  statistics against known answers.
- **On the recordings**, where there is no ground truth: lines through tissue,
  the occlusion (when the blood should stand still), the direction of flow in
  a loop's two limbs, and the same recordings placed a second time. Each is an
  analysis of its own in `analysis/`.

## What the method cannot do

`CLAUDE.md` (Known issues) and the analyses' READMEs give the details.

- **Calibration.** Every velocity scales with the frame rate and the pixel
  size. Both are taken from the recordings and the recording program
  (30 frames per second, 1.33 µm per pixel); neither was calibrated
  independently.
- **Slow flow against movement.** Below 1 px/frame (0.04 mm/s) one line cannot
  tell slow flow from the picture moving along it.
- **Many loops give no value.** More than half of the loops placed for the
  study did not count: most of those showed no moving pattern at rest, the
  others sat at the slowest speed searched (`analysis/primary_endpoint/`).
- **A whole loop reads its dominant limb,** usually the venous one. It is not
  an arterial velocity (`analysis/whole_loop_limbs/`).
- **Stabilization corrects translation only,** not deformation of the skin.

## Batch commands

The measurement lives in the `capillary` package, which imports no GUI
toolkit. The pages and the command line run the same arithmetic.

```bash
# stabilize a recording
python3 -m capillary.stabilize RecordedVideos/clip.avi --out StabilizedVideos/clip.avi

# measure a line
python3 -m capillary.cli StabilizedVideos/clip.avi \
    --line "372,110;352,160;338,205" --start 1909 --max-frames 900 \
    --out blocks.csv --summary-out summary.csv
```

`--line` lists the points of a centre line in video pixels, from where the
blood comes from. The command prints the 3-s blocks' summary and the pattern
shift pooled over the frames measured. The points and the frames of a data set
made in the app are in its `…_provenance.json`. The calibration comes from
`settings.csv` (`mm_per_pixel`) unless `--mm-per-pixel` gives it. On a
stabilized video a line that reaches the black strip is refused, as in the
app. `python3 -m capillary.cli --help` lists the rest.

## Data folder

`settings.csv`, beside the code, keeps the data folder (`Application_path`),
the calibration (`mm_per_pixel`), the observer's initials and whether blind
placement is on. Each computer has its own; git ignores it. Inside the data
folder:

- `RecordedVideos/`: raw recordings, copied in to be stabilized.
- `StabilizedVideos/`: stabilized copies, each with its shift file and its
  provenance. The app takes every video in this folder as stabilized.
- `Statistics/`: the data sets (`<recording>___<data set>___…`: the space-time
  diagram, the 3-s blocks, the provenance) and each recording's time points.
- `Reports/`: the plots and summary tables written from the data sets, and the
  aims' tables in `Reports/aims/`.
- `.trash/`: what was moved to the trash, one dated folder per action.

## Code layout

| Path | What it holds |
| --- | --- |
| `Application.py` | Entry point: logging, then the window |
| `gui/app.py` | The main window: header, recording list, pages, status bar, keyboard |
| `gui/line_page.py`, `gui/measure_page.py` | The Centre line page: the line tool and its preview; video, timeline, frame range, time points, the Measure footer |
| `gui/results_page.py` | The Results page |
| `gui/blind.py` | Blind placement: what it lists and hides |
| `gui/jobs.py`, `gui/tasks.py`, `gui/reports.py` | Background jobs, the work they run (stabilize, preview, measure, report), and the report's plots |
| `gui/video_view.py`, `gui/transport.py`, `gui/library_view.py`, `gui/widgets.py`, `gui/dialogs.py`, `gui/theme.py` | Video canvas, playback and timeline, the recording list, small widgets, dialogs, colours and icons |
| `gui/library.py`, `gui/settings.py`, `gui/media.py` | Finding recordings, settings, frames for display |
| `capillary/stabilize.py`, `capillary/quality.py`, `capillary/video.py` | The stabilizer, the sharpness score it uses, reading videos frame by frame |
| `capillary/spacetime.py`, `capillary/pattern_shift.py` | The centre line, its space-time diagram and the two velocity estimators |
| `capillary/datasets.py`, `capillary/cli.py` | The files of a saved data set; the batch command |
| `capillary/inventory.py`, `capillary/blinding.py`, `capillary/aims.py`, `capillary/agreement.py`, `capillary/placement.py` | The study: its recordings and official times, the blind codes, the aims' values and statistics, Bland–Altman and ICC, whether two lines follow one capillary |
| `capillary/simulate.py`, `capillary/benchmark.py` | Synthetic recordings with a known velocity, and the benchmark on them |

## Tests

```bash
source venv/bin/activate
pip install pytest
python3 -m pytest          # 197 tests, about 30 s; no display needed
```

A real recording has no ground truth, so the suite checks the engine against
synthetic videos with an exactly known velocity (`tests/synthetic.py`,
`capillary/simulate.py`). Further tests cover the stabilizer, the measurement
as the app runs it, the saved file formats, the study's recordings and
statistics (the intraclass correlation against the published example of
Shrout & Fleiss 1979), blind placement, and the app's logic without a window.

## How it was written

The tool grew out of an earlier capillaroscopy app (`Widaeus/capillaroscopy`).
The measurement, the stabilizer and the study's analysis were written during
the degree project, with Claude Code, Anthropic's AI coding assistant.
`DEVLOG.md` records each step with its reasons and checks, and `CLAUDE.md` is
the assistant's standing instructions.
