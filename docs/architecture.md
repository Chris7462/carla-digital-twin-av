# Architecture

## Mental model

```
Recorded vehicle data
        |
   +----+----+------------+
   |         |            |
 LiDAR    Camera      GPS / IMU
   |         |            |
   +----+----+------------+
        |
  Localization / SLAM              <-- Stage 1 (IN PROGRESS)
        |
  Global 3D map
        |
   +----+----------------------+
   |                            |
 Road reconstruction      Scene reconstruction
   |                            |
 lanes / centerlines       buildings / trees /
 intersections / signs     poles / terrain etc.
   |                            |
 OpenDRIVE (.xodr)          3D Mesh (FBX/OBJ/UE)
   |  Stage 2 (NOT STARTED) |  Stage 3 (NOT STARTED)
   +----+----------------------+
        |
      CARLA                       <-- Stage 4 (NOT STARTED)
        |
  Digital Twin Map
```

CARLA needs two things for a conventional custom map: 3D geometry (mesh)
and an OpenDRIVE (`.xodr`) road definition. Everything upstream of those
two artifacts exists to produce them from recorded vehicle sensor data.

## Where we are

**Stage 1 (SLAM) is the only stage under active implementation.**
Stages 2-4 are placeholders — folder + README describing the expected
interface only, no implementation yet.

## Stage 1: Recorded vehicle data -> Global 3D map

Detailed spec lives in `docs/data-spec.md` and `docs/decisions.md`.
Summary:

- **Input**: KITTI Odometry Benchmark sequence 00 (LiDAR, motion-compensated,
  official) + raw sync OXTS (GPS/IMU) for the same sequence, frame-aligned
  0-4540.
- **LiDAR odometry**: KISS-ICP (off-the-shelf pip package, not hand-rolled).
- **Fusion**: loosely-coupled pose graph (GTSAM) — LiDAR odometry
  between-factors + GPS prior-factors. Not tightly-coupled LIO (KITTI's
  10Hz OXTS is too low-rate for meaningful IMU preintegration).
- **Output**: `est_poses.txt` (KITTI pose format) + accumulated point
  cloud map.
- **Evaluation**: `evo_ape` / `evo_rpe` against official `poses/00.txt`
  ground truth. Threshold in `docs/done-criteria.md`.

## Stage 2: Global 3D map -> Road reconstruction (not started)

Expected input: Stage 1's point cloud map + trajectory.
Expected output: `.xodr` (lanes, centerlines, intersections, signs).

## Stage 3: Global 3D map -> Scene reconstruction (not started)

Expected input: Stage 1's point cloud map.
Expected output: 3D mesh (FBX/OBJ), buildings/trees/poles/terrain.

## Stage 4: CARLA integration (not started)

Expected input: Stage 2's `.xodr` + Stage 3's mesh.
Expected output: importable CARLA digital twin map.
