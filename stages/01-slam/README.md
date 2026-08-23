# Stage 1 — SLAM

KITTI sequence 00 → LiDAR odometry + GPS pose-graph fusion → global
trajectory + point cloud map. Full pipeline context: `docs/architecture.md`.
Exact file paths/formats: `docs/data-spec.md`. Pass/fail criteria:
`docs/done-criteria.md`. Why things are built this way: `docs/decisions.md`.

## Architecture

```
  KITTI Odometry Benchmark (seq 00)         Raw sync (2011_10_03_drive_0027_sync)
  ┌───────────────────────────┐              ┌───────────────────────────┐
  │  velodyne/*.bin           │              │  oxts/data/*.txt          │
  │  (motion-compensated      │              │  (GPS/IMU, 10Hz,          │
  │   LiDAR, frames 0-4540)   │              │   frames 0-4540)          │
  └────────────┬──────────────┘              └────────────┬──────────────┘
               │                                          │
               ▼                                          ▼
      ┌──────────────────────┐                     ┌─────────────────────┐
      │  KISS-ICP's own      │                     │  lat/lon -> ENU     │
      │  dataset/pipeline API│                     │  local coordinates  │
      │  (not hand-rolled —  │                     └──────────┬──────────┘
      │  see decisions.md)   │                                │
      └────────┬─────────────┘                                │
               │                                              │
               │ relative poses                    absolute positions
               │ (between-factor)                  (prior-factor)
               │  Velodyne frame                    ENU frame
               │                                              │
               │        align coordinate frames (yaw_0)       │
               └────────────────────┬─────────────────────────┘
                                    ▼
                          ┌────────────────────┐
                          │   GTSAM pose graph │
                          │  loosely-coupled   │
                          │  optimization      │
                          └─────────┬──────────┘
                                    │
                                    ▼
                          ┌────────────────────┐
                          │   est_poses.txt    │
                          │  (cam0 frame, via  │
                          │   Tr transform)    │
                          └─────────┬──────────┘
                                    │
                    ┌───────────────┴──────────────────┐
                    ▼                                  ▼
          ┌───────────────────┐              ┌─────────────────────┐
          │   evo_rpe/evo_ape │              │  accumulated point  │
          │  vs poses/00.txt  │              │   cloud map (.pcd)  │
          │  (RPE < 1% ?)     │              │                     │
          └───────────────────┘              └─────────────────────┘
                    │
                    ▼
          ┌───────────────────────────────────┐
          │  Global 3D map + trajectory       │
          │  -> feeds Stage 2 (Road recon.)   │
          │     and Stage 3 (Scene recon.)    │
          └───────────────────────────────────┘
```

## Status

**Baseline established, verified against official KITTI ground truth.**
LiDAR odometry (left branch) uses KISS-ICP's own dataset loader — the
earlier hand-rolled reader was retired, see `docs/decisions.md`
("LiDAR point cloud loading") for what went wrong and why. GPS fusion
(right branch, including the coordinate-frame alignment step where
the two sides merge) is complete and verified.

Verified results on sequence 00 against official ground truth
(`dataset/poses/00.txt`):
- KISS-ICP only: APE rmse 3.52m
- + GTSAM/GPS fused: APE rmse 0.063m
- + GTSAM/GPS fused: RPE 1.28% (`evo_rpe --delta 100 --delta_unit m`)

Fused RPE clears the `docs/done-criteria.md` threshold, which was
revised from 1% to 1.5% by explicit human decision after this result —
see `docs/decisions.md` ("Evaluation") for the recorded reasoning. See
`PROJECT_STATUS.md` for the run log and `stages/01-slam/AGENTS.md` for
the constraints that must hold on any future change to this baseline
(frame convention, GPSFactor sigma source, frame consistency).

## Layout

```
stages/01-slam/
  kitti_kiss_icp_gtsam.py  # reference pipeline for the verified baseline above —
                            # KISS-ICP odometry + GTSAM/GPS fusion, single file.
                            # Supersedes the earlier per-step scripts
                            # (data_loader.py, run_kitti_odometry.py, run_fusion.py,
                            # gps_utils.py, verify_alignment.py), which have been
                            # removed.
  tests/                # long-term-value tests (frame alignment, coordinate
                        # transforms) — see agents/builder.md for what belongs here
  outputs/run_<description>/
    est_poses.txt, map.pcd, eval_report.json, traj_plot.png, map_render_*.png
```

Files not listed above but present in the folder are debugging
artifacts from past investigation rounds — check `PROJECT_STATUS.md`
or `docs/decisions.md` before assuming a file is still needed.
