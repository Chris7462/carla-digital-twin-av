# Roadmap

Four stages, each with a defined input/output contract so later stages
can be implemented against a stable interface even before they start.
See `docs/architecture.md` for the full diagram and rationale.

## Stage 1 — SLAM: Recorded vehicle data -> Global 3D map

**Status**: in progress

| | |
|---|---|
| Input | KITTI Odometry Benchmark seq 00 (LiDAR) + raw sync OXTS (GPS/IMU) |
| Output | `est_poses.txt` (KITTI pose format), accumulated point cloud map (`.pcd`) |
| Pass criteria | see `docs/done-criteria.md` (ATE/RPE vs official ground truth) |
| Folder | `stages/01-slam/` |

## Stage 2 — Road reconstruction: Global 3D map -> OpenDRIVE

**Status**: not started

| | |
|---|---|
| Input | Stage 1 output: point cloud map + trajectory |
| Output | `.xodr` — lanes/centerlines, intersections, signs |
| Pass criteria | TBD when this stage starts |
| Folder | `stages/02-road-reconstruction/` |

## Stage 3 — Scene reconstruction: Global 3D map -> 3D Mesh

**Status**: not started

| | |
|---|---|
| Input | Stage 1 output: point cloud map |
| Output | 3D mesh (FBX/OBJ) — buildings, trees, poles, terrain |
| Pass criteria | TBD when this stage starts |
| Folder | `stages/03-scene-reconstruction/` |

## Stage 4 — CARLA integration

**Status**: not started

| | |
|---|---|
| Input | Stage 2 output (`.xodr`) + Stage 3 output (mesh) |
| Output | Importable CARLA digital twin map |
| Pass criteria | TBD when this stage starts |
| Folder | `stages/04-carla-integration/` |

## Notes

- Stages 2-4 folders exist as placeholders (README only) so the repo
  structure reflects the end-to-end plan without pretending those
  stages are implemented.
- Each stage's actual pass criteria gets written just before that
  stage starts, not upfront — writing it too early risks encoding
  assumptions that don't hold once Stage 1's real output shape is known.
