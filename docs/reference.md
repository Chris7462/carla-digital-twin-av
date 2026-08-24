# Stage 1 Reference — Data, Method, Evaluation

Settled facts for Stage 1 (SLAM). Don't re-derive these — if something
here looks wrong, flag it before reworking it.

## Data paths (soc006)

Two separate KITTI downloads, both required:

```
/mnt/data2/kitti/
├── 2011_10_03/2011_10_03_drive_0027_sync/   <- raw sync (OXTS + LiDAR + cameras)
│   ├── oxts/data/                           <- used (GPS/IMU)
│   ├── velodyne_points/data/                <- NOT used (raw/uncompensated LiDAR)
│   └── image_00-03/data/                    <- NOT used (no camera in Stage 1)
├── 2011_10_03/calib_imu_to_velo.txt         <- used (IMU->Velodyne extrinsic)
├── 2011_10_03/calib_velo_to_cam.txt         <- NOT used
├── 2011_10_03/calib_cam_to_cam.txt          <- NOT used
└── dataset/                                  <- KITTI Odometry Benchmark
    ├── sequences/00/velodyne/                <- used (motion-compensated LiDAR)
    ├── sequences/00/calib.txt                <- used (Tr: Velodyne->cam0)
    └── poses/00.txt                          <- used (ground truth)
```

| Sensor | Path | Naming | Frames used |
|---|---|---|---|
| OXTS (GPS/IMU) | `2011_10_03_drive_0027_sync/oxts/data/` | `%010d.txt` | 0–4540 (of 4544 on disk) |
| LiDAR, motion-compensated | `dataset/sequences/00/velodyne/` | `%06d.bin` | all 4541 |
| Ground truth poses | `dataset/poses/00.txt` | one line/frame | all 4541 |

Frame `i` (0..4540) maps: `oxts/data/{i:010d}.txt` <-> `velodyne/{i:06d}.bin`
<-> `poses/00.txt` line `i+1`. OXTS frames 4541–4543 are discarded (no
corresponding pose or LiDAR frame). Verified against the official KITTI
devkit readme.

**LiDAR loading always goes through KISS-ICP's own dataset API** — not a
hand-rolled `.bin` reader. A hand-rolled reader was tried once, missed an
intrinsic Velodyne vertical-angle correction that KISS-ICP's loader
already applies, and degraded RPE from ~0.5% to ~1.1% without erroring.

The raw sync `velodyne_points/` data and all four camera folders are
never read by any part of this pipeline.

## Calibration

`calib_imu_to_velo.txt` — IMU/GPS frame -> Velodyne frame, `X_velo = R @
X_imu + T`. Used for GPS fusion (expresses OXTS positions in the LiDAR
frame).

```
R: 9.999976e-01 7.553071e-04 -2.035826e-03 -7.854027e-04 9.998898e-01 -1.482298e-02 2.024406e-03 1.482454e-02 9.998881e-01
T: -8.086759e-01 3.195559e-01 -7.997231e-01
```

`dataset/sequences/00/calib.txt` — `Tr` (3x4, [R|t]): Velodyne frame ->
cam0 frame. **Required before evaluation** — `poses/00.txt` ground truth
is in cam0, KISS-ICP output is in Velodyne. Comparing untransformed
poses against ground truth gives a wrong RPE/ATE, not just a noisier one.

```
Tr: 4.276802385584e-04 -9.999672484946e-01 -8.084491683471e-03 -1.198459927713e-02 -7.210626507497e-03 8.081198471645e-03 -9.999413164504e-01 -5.403984729748e-02 9.999738645903e-01 4.859485810390e-04 -7.206933692422e-03 -2.921968648686e-01
```

## Method

- LiDAR odometry: **KISS-ICP**, off-the-shelf, own dataset API.
- Fusion: **loosely-coupled GTSAM pose graph** (LiDAR between-factors +
  GPS prior-factors), not tightly-coupled LIO — OXTS is only 10Hz, too
  low-rate for meaningful IMU preintegration. GPS fusion is a required
  step, not optional.
- GPS factor sigma: read per-frame from OXTS `pos_accuracy`, not a
  hand-picked constant.
- Ground truth source: official KITTI Odometry Benchmark `poses.txt`
  (RTK-corrected), not self-derived from raw OXTS.

## Evaluation

Run against `poses/00.txt`, after converting `est_poses.txt` to the cam0
frame via `Tr` above:

```
evo_ape kitti poses/00.txt est_poses.txt -a --save_results eval_ape.zip
evo_rpe kitti poses/00.txt est_poses.txt -a --delta 100 --delta_unit m --save_results eval_rpe.zip
```

`--delta 100 --delta_unit m` gives RPE as % translation error per 100m —
this is the number the threshold is defined against. evo's default delta
(`--delta 1 --delta_unit frames`) is a different, non-comparable
quantity (meters/frame) — don't use defaults.

**Current threshold: RPE < 1.5%** (revised from an initial 1% starting
point taken from published KISS-ICP KITTI numbers, after the first
correctly-computed run came in at 1.28% with an acceptable visual pass).
ATE/APE has no hard threshold — record it for reference and to spot
regressions.

## Current baseline (Stage 1)

| | KISS-ICP only | + GTSAM/GPS fused |
|---|---|---|
| APE rmse | 3.52 m | 0.063 m |
| RPE (%/100m) | — | 1.28% (passes < 1.5%) |

Passes the current threshold. Stage 2/3 can build on this output
(`est_poses.txt`, `map.pcd`).

## Output layout

```
stages/01-slam/outputs/run_<description>/
  est_poses.txt          # KITTI 12-float format, cam0 frame, frames 0-4540
  map.pcd
  eval_report.json       # both RPE and ATE
  traj_plot.png
  map_render_{top,side,front}.png
```
