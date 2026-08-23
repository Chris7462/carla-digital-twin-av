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
      ┌────────────── ───────┐                     ┌──────────────────── ┐
      │  KISS-ICP's own      │                     │  lat/lon -> ENU     │
      │  dataset/pipeline API│                     │  local coordinates  │
      │  (not hand-rolled —  │                     └─ ────────┬──────────┘
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
                    ┌───────────────┴────────────────┐
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

**In progress, being rebuilt.** LiDAR odometry (left branch) was
initially hand-rolled instead of using KISS-ICP's own dataset loader
— see `docs/decisions.md` ("LiDAR point cloud loading") for what went
wrong and why it's being redone. GPS fusion (right branch, and the
coordinate-frame alignment step where the two sides merge) is not yet
verified working; the known root cause so far is a heading offset
between GPS's ENU frame and the Velodyne forward frame (~60° at frame
0 for this sequence) that must be corrected before fusion, plus GPS
prior weighting that needs to be sparse enough not to overwhelm the
LiDAR odometry's relative accuracy.

Current numbers (see `PROJECT_STATUS.md` for the latest): pure LiDAR
odometry (no GPS fusion) has reached RPE ≈ 1.0%, just above the 1%
threshold — GPS fusion, once correctly aligned, is expected to correct
enough long-term drift to clear it. Fused results so far have been
worse than the unfused baseline, which per `docs/done-criteria.md` is
treated as a bug to fix, not a result to report.

## Layout

```
stages/01-slam/
  data_loader.py       # OXTS parsing + frame alignment (0-4540). LiDAR reading
                        # delegates to KISS-ICP's own dataset API, not hand-rolled.
  run_kitti_odometry.py  # pure LiDAR odometry baseline (no GPS fusion)
  run_fusion.py         # GPS pose-graph fusion (GTSAM)
  gps_utils.py          # lat/lon -> ENU conversion, coordinate-frame alignment
  verify_alignment.py   # sanity-checks frame/index alignment against poses/00.txt
  tests/                # long-term-value tests (frame alignment, coordinate
                        # transforms) — see agents/builder.md for what belongs here
  outputs/run_<description>/
    est_poses.txt, map.pcd, eval_report.json, traj_plot.png, map_render_*.png
```

Files not listed above but present in the folder are debugging
artifacts from past investigation rounds — check `PROJECT_STATUS.md`
or `docs/decisions.md` before assuming a file is still needed.
