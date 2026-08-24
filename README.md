# carla-digital-twin-av

Building a CARLA digital twin map from recorded vehicle sensor data
(LiDAR / Camera / GPS-IMU), end to end.

```
   Recorded vehicle data
             |
   +---------+------------+
   |         |            |
 LiDAR    Camera      GPS / IMU
   |         |            |
   +---------+------------+
             |
       Localization / SLAM             <-- Stage 1 (baseline established)
             |
       Global 3D map
             |
   +---------+-----------------+
   |                           |
 Road reconstruction      Scene reconstruction
   |                           |
 OpenDRIVE (.xodr)          3D Mesh (FBX/OBJ/UE)
   |  Stage 2 (NOT STARTED)    |  Stage 3 (NOT STARTED)
   +---------+-----------------+
             |
           CARLA                       <-- Stage 4 (NOT STARTED)
             |
       Digital Twin Map
```

CARLA needs two things for a conventional custom map: 3D geometry
(mesh) and an OpenDRIVE (`.xodr`) road definition. Everything upstream
exists to produce those two artifacts from recorded sensor data.

Full diagram and rationale: `docs/architecture.md`. Per-stage
input/output contracts: `docs/roadmap.md`. Data paths, calibration,
method, and evaluation details for the active stage: `docs/reference.md`.

## Status

**Stage 1 (SLAM): baseline established, passes threshold.** KITTI
Odometry Benchmark sequence 00, KISS-ICP + GTSAM/GPS pose-graph fusion,
evaluated against official ground truth (RPE 1.28%, threshold < 1.5%).
See `stages/01-slam/README.md` and `docs/reference.md`.

Stages 2-4 are placeholders (folder + README describing the expected
interface only).

## Machines

- **soc006** — project execution environment, accessed via SSH. Has the
  KITTI data mounted at `/mnt/data2/kitti/`.
- **exxact** — dual RTX PRO 6000 Blackwell workstation, 96GB VRAM/card,
  available for heavier compute if needed.

Machine-specific data paths go in `config/paths.yaml` (gitignored).
