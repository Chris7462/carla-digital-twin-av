## Stage 01: SLAM (KITTI KISS-ICP + GTSAM fusion)

**Status: baseline established, verified against official KITTI ground truth.**

`kitti_kiss_icp_gtsam.py` is the reference pipeline for this stage:
- KISS-ICP for LiDAR odometry on KITTI raw drives (via kiss_icp's KITTIRawDataset loader)
- Loosely-coupled GTSAM pose graph fusion: BetweenFactor from KISS-ICP relative
  motion + GPSFactor from OXTS positions (per-frame sigma from OXTS pos_accuracy)
- Poses output in cam0 frame (KITTI odometry benchmark convention) via
  lidar_poses_to_cam0(), matching official poses.txt

Verified results on sequence 00 against official ground truth
(dataset/poses/00.txt):
- KISS-ICP only: APE rmse 3.52m
- + GTSAM/GPS fused: APE rmse 0.063m, RPE rmse 0.045m

Do not change the frame convention (cam0), the GPSFactor sigma source
(OXTS pos_accuracy, not a hand-picked constant), or the odometry/GPS/gt
frame consistency without re-validating against dataset/poses/<seq>.txt.
