# Data spec — Stage 1 (SLAM)

Sequence 00 only. Frame range 0-4540 (see `docs/decisions.md` — Data
alignment). This file is the concrete path/index reference; the
reasoning behind the numbers lives in `docs/decisions.md`, not here.

## Directory layout

Two separate downloads, both required:

```
/mnt/data2/kitti/
├── 2011_10_03/2011_10_03_drive_0027_sync/   <- raw sync (OXTS + LiDAR + cameras)
│   ├── oxts/data/
│   ├── velodyne_points/data/
│   └── image_00-03/data/
├── 2011_10_03/calib_imu_to_velo.txt
├── 2011_10_03/calib_velo_to_cam.txt          <- not used in Stage 1
├── 2011_10_03/calib_cam_to_cam.txt           <- not used in Stage 1
└── dataset/                                  <- KITTI Odometry Benchmark
    ├── sequences/00/velodyne/                <- motion-compensated LiDAR (this is what the pipeline reads)
    └── poses/00.txt                          <- ground truth
```

`dataset/sequences/00/` also includes `calib.txt` and `times.txt`.
`times.txt` (4541 lines, seconds since sequence start) isn't needed —
frame alignment below is index-based, not timestamp-based. `calib.txt`
matters — see the callout below.

## What the pipeline reads

| Sensor | Path | Naming | Frames on disk | Frames used |
|---|---|---|---|---|
| OXTS (GPS/IMU) | `2011_10_03_drive_0027_sync/oxts/data/` | `%010d.txt` (`0000000000.txt`) | 4544 (0–4543) | **0–4540** (4541 files) |
| LiDAR, motion-compensated | `dataset/sequences/00/velodyne/` | `%06d.bin` (`000000.bin`) | 4541 | all 4541 |
| Ground truth poses | `dataset/poses/00.txt` | one line per frame | 4541 lines | all 4541 |

## What the pipeline does NOT read

- `2011_10_03_drive_0027_sync/velodyne_points/data/` — raw
  (uncompensated) LiDAR. Superseded by the motion-compensated version
  above; not loaded anywhere in Stage 1.
- `2011_10_03_drive_0027_sync/image_00-03/data/` — cameras. Not used
  by any stage yet; current SLAM approach is LiDAR + GPS only (see
  `docs/architecture.md`).
- `calib_velo_to_cam.txt`, `calib_cam_to_cam.txt` — no camera use,
  no need for these.

## Frame alignment (fixed — do not re-derive)

For frame index `i` in `0..4540`:

```
oxts/data/{i:010d}.txt  <->  sequences/00/velodyne/{i:06d}.bin  <->  poses/00.txt line (i+1)
```

- `oxts/data/0000004541.txt` through `0000004543.txt` (3 files):
  discarded, no corresponding pose or compensated LiDAR frame.
- Verified via timestamp jitter-pattern matching at the sequence
  start and cumulative elapsed-time matching at the end, confirmed
  against the official devkit `readme.txt` — see `docs/decisions.md`.

## Calibration

`2011_10_03/calib_imu_to_velo.txt`:
```
R: 9.999976e-01 7.553071e-04 -2.035826e-03 -7.854027e-04 9.998898e-01 -1.482298e-02 2.024406e-03 1.482454e-02 9.998881e-01
T: -8.086759e-01 3.195559e-01 -7.997231e-01
```
`R` (3x3, row-major) + `T` (3x1) transform a point from the IMU/GPS
frame into the Velodyne frame: `X_velo = R @ X_imu + T`. Required for
the GPS pose-graph fusion step — this is how OXTS-derived positions
get expressed in the same frame as the LiDAR odometry.

`dataset/sequences/00/calib.txt`:
```
Tr: 4.276802385584e-04 -9.999672484946e-01 -8.084491683471e-03 -1.198459927713e-02 -7.210626507497e-03 8.081198471645e-03 -9.999413164504e-01 -5.403984729748e-02 9.999738645903e-01 4.859485810390e-04 -7.206933692422e-03 -2.921968648686e-01
```
**Required for evaluation, not optional.** `poses/00.txt` ground
truth is expressed in the left camera (cam0) frame, not the Velodyne
frame — a well-known KITTI convention. KISS-ICP's output trajectory
is in the Velodyne frame. Before running `evo_ape`/`evo_rpe` against
`poses/00.txt`, transform the estimated trajectory into the cam0
frame using this `Tr` (3x4, row-major, [R|t] mapping a point from
Velodyne coordinates into cam0 coordinates). Comparing un-transformed
Velodyne-frame poses directly against `poses/00.txt` gives a wrong
RPE/ATE number, not just a noisier one.

`P0`-`P3` (camera projection matrices, also in `calib.txt`): not
used — no camera in Stage 1.

## Pose format (`poses/00.txt`)

Each line: 12 space-separated floats, a 3x4 matrix `[R|t]` flattened
row-major:

```
r11 r12 r13 tx  r21 r22 r23 ty  r31 r32 r33 tz
```

Pose of frame `i` relative to frame 0, in the left camera coordinate
frame (KITTI convention). Line 1 (frame 0) is identity + zero
translation — confirmed on this machine (`head -1 poses/00.txt`
returns the identity matrix).

## Output (Stage 1 pipeline produces, per `agents/builder.md`)

```
stages/01-slam/outputs/run_<description>/
  est_poses.txt          # same 12-float KITTI format as poses/00.txt, one line per frame 0-4540
  map.pcd
  eval_report.json
  traj_plot.png
  map_render_{top,side,front}.png
```
