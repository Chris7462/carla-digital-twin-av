## Stage 01: SLAM (KITTI KISS-ICP + GTSAM fusion)

**Status: baseline established, verified against official KITTI ground truth.
RPE passes under the revised 1.5% threshold (see `docs/decisions.md` —
"Evaluation").**

`kitti_kiss_icp_gtsam.py` is the reference pipeline for this stage:
- KISS-ICP for LiDAR odometry on KITTI raw drives (via kiss_icp's KITTIRawDataset loader)
- Loosely-coupled GTSAM pose graph fusion: BetweenFactor from KISS-ICP relative
  motion + GPSFactor from OXTS positions (per-frame sigma from OXTS pos_accuracy)
- Poses output in cam0 frame (KITTI odometry benchmark convention) via
  lidar_poses_to_cam0(), matching official poses.txt

Verified results on sequence 00 against official ground truth
(dataset/poses/00.txt):
- KISS-ICP only: APE rmse 3.52m
- + GTSAM/GPS fused: APE rmse 0.063m
- + GTSAM/GPS fused: RPE 1.28% (`evo_rpe --delta 100 --delta_unit m`, the
  project-specified command) — passes the revised < 1.5% threshold

An earlier RPE figure ("0.045m") recorded here was computed with
`evo_rpe`'s default delta (`--delta 1 --delta_unit frames`), which is a
meters-per-frame quantity, not the percent-per-100m quantity the
threshold is defined against. It was not a valid comparison to the
threshold. See `docs/decisions.md` ("Evaluation") for the correction
and the record of who revised the threshold and why.

Do not change the frame convention (cam0), the GPSFactor sigma source
(OXTS pos_accuracy, not a hand-picked constant), or the odometry/GPS/gt
frame consistency without re-validating against dataset/poses/<seq>.txt.
Any future RPE number reported for this stage must use
`--delta 100 --delta_unit m` — see `docs/done-criteria.md`.
