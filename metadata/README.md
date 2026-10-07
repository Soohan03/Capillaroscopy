# Study metadata

The official times at which the finger was occluded and released in each
nailfold videocapillaroscopy recording of the ESMOKE and ISMOKE studies. They
were exported from DynCap, where the recordings are archived with their
metadata, and added on 2026-10-07. The files are kept exactly as provided.

| File | Study | Recordings | Participants | Conditions |
| --- | --- | ---: | ---: | --- |
| `ESMOKE_timestamps.csv` | ESMOKE (2019–2020) | 74 | 17 | W = e-cigarette with nicotine, Q = without nicotine |
| `ISMOKE_timestamps.csv` | ISMOKE (2020) | 50 | 13 | S = heated tobacco product, C = no exposure |

## Columns (separated by semicolons, UTF-8)

- `subject`: the participant's code within the study (FP01, FP02, …). The
  same code in ESMOKE and ISMOKE is a different person.
- `occlusion`: seconds from the start of the video when the cuff was inflated
  (200 mmHg at the base of the finger).
- `release`: seconds from the start of the video when it was released. Empty
  where it was not recorded (16 recordings).
- `source_file`: the recording's file name without extension, as the app
  names a recording, built as
  `<subject>_<condition><före|efter>[_försökN]_<date>_<time>`, where före is
  before exposure, efter after, and försök a further attempt. ISMOKE names
  start with `ISMOKE_`.

## Notes from a check on 2026-10-07

- Occlusion usually starts about a minute into the recording (median 60.3 s)
  and lasts about a minute (median 61.2 s, range 47.5–93.8 s).
- Rows that differ from that pattern:

  | Recording | Occlusion (s) | Release (s) | Lasted (s) |
  | --- | ---: | ---: | ---: |
  | `FP01_Wefter_14-Oct-2019_10-07-49` | 158.5 | 230.1 | 71.6 |
  | `FP01_Wefter_14-Oct-2019_10-13-03` | 62.5 | 147.4 | 84.9 |
  | `FP05_Wefter_17-Oct-2019_11-07-45` | 93.9 | 153.8 | 59.9 |
  | `FP05_Wefter_försök2_17-Oct-2019_11-12-45` | 80.8 | 174.6 | 93.8 |
  | `ISMOKE_FP04_Sefter_11-Nov-2020_10-27-46` | 6.4 | 61.4 | 55.0 |
  | `ISMOKE_FP08_Cföre_10-Nov-2020_08-20-24` | 25.5 | 85.2 | 59.7 |
  | `ISMOKE_FP21_Cefter_07-Dec-2020_09-33-41` | 73.1 | 120.6 | 47.5 |

- **`FP01_Wefter_14-Oct-2019_10-07-49` does not fit its video.** The local
  video has 3435 frames: 114.5 s at the 30 fps stamped in the file, but
  229 s at 15 fps, which matches the release at 230.1 s. Either the times use
  another origin or this recording's true frame rate is 15 fps. Every velocity
  scales with the frame rate, so check the recording's length in DynCap.
- `FP21Wföre_20-Nov-2019_09-08-03` has no underscore after `FP21`.
- All 8 recordings in the local `StabilizedVideos/` have times here. For
  `FP01_Qföre_22-Oct-2019_08-16-35` (occlusion 68.3 s, release 130.5 s) the
  video agrees at 30 fps:
  - the centre line resolves slow, slowing flow from 70 to 130 s;
  - blood movement in the vessels jumps at 130 s.

The files hold pseudonymised study metadata (participant codes and visit
dates and times) and live in the private repository.
