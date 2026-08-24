# Stage 1 — SLAM

KITTI sequence 00 → LiDAR odometry + GPS pose-graph fusion → global
trajectory + point cloud map. Full pipeline context: `docs/architecture.md`.
Data paths, calibration, method, evaluation: `docs/reference.md`.

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
      └────────┬─────────────┘                     └──────────┬──────────┘
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

- KISS-ICP only: APE rmse 3.52m
- + GTSAM/GPS fused: APE rmse 0.063m
- + GTSAM/GPS fused: RPE 1.28% (`evo_rpe --delta 100 --delta_unit m`) —
  passes the < 1.5% threshold

See `docs/reference.md` for the full method/data/evaluation detail and
`PROJECT_STATUS.md` for the run log.

## Layout

```
stages/01-slam/
  kitti_kiss_icp_gtsam.py  # reference pipeline for the verified baseline —
                            # KISS-ICP odometry + GTSAM/GPS fusion, single file.
  outputs/run_<description>/
    est_poses.txt, map.pcd, eval_report.json, traj_plot.png, map_render_*.png
```
