#!/usr/bin/env python3
"""
KISS-ICP + GTSAM loosely-coupled LiDAR + GPS fusion for KITTI raw drives.

Pipeline
--------
1. Run KISS-ICP frame-to-map registration over the Velodyne scans of a KITTI
   raw drive -> per-frame LiDAR odometry poses T_odom (drifts over time,
   but locally very accurate).
2. Read the OXTS (GPS/INS) packets bundled with the same drive and take the
   already-projected local-frame translation (KITTI stores lat/lon plus a
   Mercator-projected pose per frame) as a noisy GPS position observation.
3. Build a GTSAM pose graph:
     - BetweenFactor<Pose3> between consecutive frames, from the *relative*
       KISS-ICP motion (this is what keeps local shape/orientation accurate).
     - GPSFactor (unary, position-only) on every N-th frame, pulling the
       trajectory back toward the global GPS track and killing long-term
       drift.
     - A PriorFactor on frame 0 to fix the gauge freedom.
4. Optimize with Levenberg-Marquardt and dump the result in KITTI poses.txt
   format (3x4 row-major matrices, one line per frame) so it can be scored
   directly with `evo_ape kitti gt.txt poses_fused.txt` / `evo_rpe`.
5. (Unless --skip_map) Accumulate a global point cloud map alongside the
   odometry poses -- see "Point cloud map" below -- and write it to
   map.pcd.

Point cloud map
----------------
KISS-ICP's own KissICP.local_map is a *bounded local* voxel map (its
max_distance is config.data.max_range, and it actively prunes points via
remove_far_away_points as the sensor moves) -- it is used for
frame-to-map registration, not as a growing global map, and reading it at
the end of the run would only return the last few meters of points, not
the whole sequence. Confirmed against the installed kiss_icp source
(kiss_icp.mapping.VoxelHashMap), not assumed from memory.

To get a global map, this script accumulates, once per frame, the same
downsampled point set KISS-ICP itself adds to its internal map
(KissICP.voxelize()'s frame_downsample output -- config.mapping.voxel_size
* 0.5 density), transformed into the global frame using that frame's
estimated pose. This reuses KissICP's own voxelize() method rather than
hand-rolling a downsampler. Points are merged into a running Open3D
PointCloud and re-voxel-downsampled (via Open3D's own voxel_down_sample,
not a hand-rolled one) every --map_accumulate_every frames, to bound
memory growth over a 4500+ frame sequence -- accumulating raw, undownsampled
points for the whole run would be tens of millions of points before any
reduction.

The map is built in the same coordinate frame as the odometry poses at
accumulation time (the Velodyne/LiDAR frame), then converted to whichever
--output_frame the poses are converted to (matching the poses exactly,
same as done for odom/fused/gt poses in lidar_poses_to_cam0()).

IMPORTANT CAVEAT
-----------------
KITTI's official ground-truth trajectory is *itself* derived from the OXTS
GPS/INS unit, the same source used for the GPSFactor here. So a fused result
that closely tracks the KITTI ground truth is exactly what's expected --
that's the fusion doing its job, not a red flag. This only matters if you
later want to claim a generalizable "LiDAR+GPS beats LiDAR-only by X%" number
for a paper/report: on this dataset GPS and ground truth share a source, so
that specific comparison is weaker evidence than it would be with an
independently-sourced GPS receiver. For actually building a working
localization/mapping pipeline (this project's goal), using every GPS frame
and getting a result close to ground truth is correct and desired.

GPS uncertainty is read from the data, not hand-picked: each OXTS record
carries a `pos_accuracy` field -- the GPS/INS unit's own per-epoch estimate
of its position accuracy (varies with satellite geometry, RTK fix/float/
single status, etc.). That per-frame value is used directly as the
GPSFactor sigma via gps_sigmas_from_oxts(), floored at --gps_sigma_floor so
a reported ~0m epoch (RTK-fixed) doesn't collapse the factor's noise model.

FRAME CONVENTION
-----------------
KISS-ICP natively outputs odometry poses in the Velodyne/LiDAR frame, and
this script's GPS positions and internal "gt" are also computed in that
frame. But the *official* KITTI odometry benchmark ground truth (the
poses.txt you'd download separately, or find published in papers) is
defined in the left camera (cam0) frame -- the translational part is the
pose of cam0 relative to cam0 at frame 0. By default (--output_frame cam0),
every trajectory this script writes is converted into that convention via
lidar_poses_to_cam0(), using kiss_icp's own dataset.calibration["T_cam0_velo"]
(the same R_rect_00 @ T_velo_cam extrinsic KITTI's devkit/pykitti compute).
Pass --output_frame lidar to skip this and keep everything in the native
Velodyne frame instead. The point cloud map (map.pcd) is converted the same
way, using the same T_cam0_velo.

Even with --output_frame cam0, poses_gt.txt here is still an OXTS-derived
proxy computed by this script/kiss_icp, not the officially distributed
ground truth file. If you have the real data_odometry_poses.zip poses.txt
for this sequence, use that as the evo reference instead for a true
benchmark-standard comparison.

Usage
-----
  pip install kiss-icp gtsam open3d numpy tqdm --break-system-packages

  python kitti_kiss_icp_gtsam.py \
      --kitti_root /path/to/kitti_raw_root \
      --sequence 00 \
      --out_dir results/seq00 \
      --gps_sigma_floor 0.3 --output_frame cam0

`--kitti_root` must contain the raw drive folders in pykitti/kiss-icp layout,
e.g. <kitti_root>/2011_10_03/2011_10_03_drive_0027_sync/{velodyne_points,oxts}
and the calibration files <kitti_root>/2011_10_03/calib_*.txt.
`--sequence` is the KITTI *odometry benchmark* sequence id (00-10); it is
internally mapped to the corresponding raw drive + frame range, matching the
official benchmark split.

Outputs (written to --out_dir):
  poses_odom.txt   KISS-ICP-only trajectory (no GPS), KITTI format
  poses_fused.txt  KISS-ICP + GTSAM/GPS fused trajectory, KITTI format
  poses_gt.txt     OXTS-derived ground truth, for convenience with evo
  map.pcd          accumulated global point cloud map (unless --skip_map)
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import gtsam
import numpy as np
import open3d as o3d
from gtsam import Pose3, Rot3, Point3
from gtsam.symbol_shorthand import X
from tqdm import tqdm

from kiss_icp.config.parser import load_config
from kiss_icp.datasets.kitti_raw import KITTIRawDataset
from kiss_icp.kiss_icp import KissICP


def run_kiss_icp(
    dataset: KITTIRawDataset,
    build_map: bool = True,
    map_voxel_size: float = 0.2,
    map_accumulate_every: int = 50,
) -> tuple[list[np.ndarray], o3d.geometry.PointCloud | None]:
    """Run KISS-ICP over every scan in the dataset.

    Returns (poses, map_pcd). poses are per-frame 4x4 world<-lidar matrices
    in the native Velodyne/LiDAR frame (not yet converted to cam0). map_pcd
    is the accumulated global point cloud, also in the Velodyne/LiDAR frame,
    or None if build_map is False. See the "Point cloud map" module
    docstring above for why this can't just read KissICP.local_map at the
    end of the run.
    """
    # load_config() (not a bare KISSConfig()) is required: it's the step that
    # resolves mapping.voxel_size from data.max_range when left at its
    # default of None. Constructing KISSConfig() directly and handing it to
    # KissICP fails with a pybind TypeError on voxel_size=None.
    config = load_config(config_file=None)
    odometry = KissICP(config=config)
    poses = []

    map_pcd = o3d.geometry.PointCloud() if build_map else None
    pending_batches: list[np.ndarray] = []

    def flush_batch():
        """Merge pending per-frame point batches into map_pcd and
        re-voxel-downsample, bounding memory instead of letting every raw
        frame's points sit around uncompacted for the whole sequence."""
        nonlocal pending_batches
        if not pending_batches:
            return
        batch = np.concatenate(pending_batches, axis=0)
        batch_pcd = o3d.geometry.PointCloud()
        batch_pcd.points = o3d.utility.Vector3dVector(batch)
        map_pcd.points.extend(batch_pcd.points)
        map_pcd_downsampled = map_pcd.voxel_down_sample(voxel_size=map_voxel_size)
        map_pcd.points = map_pcd_downsampled.points
        pending_batches = []

    for idx in tqdm(range(len(dataset)), desc="KISS-ICP"):
        frame, timestamps = dataset[idx]
        deskewed_frame, _source = odometry.register_frame(frame, timestamps)
        pose = odometry.last_pose.copy()
        poses.append(pose)

        if build_map:
            # Reuse KissICP's own voxelize() so the map density matches what
            # KISS-ICP itself would add to its internal map -- not a
            # hand-rolled downsampler.
            _coarse, frame_downsample = odometry.voxelize(deskewed_frame)
            points_global = (pose[:3, :3] @ frame_downsample.T).T + pose[:3, 3]
            pending_batches.append(points_global)
            if (idx + 1) % map_accumulate_every == 0:
                flush_batch()

    if build_map:
        flush_batch()

    return poses, map_pcd


def gps_positions_from_oxts(dataset: KITTIRawDataset) -> np.ndarray:
    """Position track derived from the raw OXTS GPS/IMU packets, in the
    LiDAR frame -- sourced from dataset.imu_poses, NOT dataset.gt_poses.

    dataset.imu_poses is the origin-normalized pose per OXTS packet (each
    packet's translation comes from a Mercator projection of that packet's
    raw lat/lon/alt -- see KITTIRawDataset.pose_from_oxts_packet). Applying
    the same calibration transform used internally (imu_pose_to_lidar) gives
    a numeric result identical to dataset.gt_poses -- KITTI's ground truth
    *is* this OXTS-derived track -- but sourcing it from imu_poses instead
    of the gt_poses attribute keeps this function honest about where the
    signal comes from, instead of reading a field literally named "ground
    truth".
    """
    lidar_frame_poses = dataset.imu_pose_to_lidar(dataset.imu_poses)
    return lidar_frame_poses[:, :3, 3]


def gps_sigmas_from_oxts(dataset: KITTIRawDataset, sigma_floor: float = 0.3) -> np.ndarray:
    """Per-frame GPS position sigma (meters), read from the OXTS packet itself
    instead of a single hand-picked constant.

    Each OXTS record carries `pos_accuracy`, the GPS/INS unit's own online
    estimate of its position accuracy for that epoch (varies with satellite
    geometry, RTK fix/float/single status, etc. -- see KITTI's
    dataformat.txt). Using it directly means the GPSFactor trusts each
    reading in proportion to how good the receiver itself says that reading
    is, rather than a single constant sigma for the whole sequence.

    `sigma_floor` guards against the rare epoch where pos_accuracy reads as
    ~0 (RTK-fixed): GTSAM's Isotropic sigma can't be zero, and a literal 0m
    sigma would also be an overstatement of any real receiver's precision.
    """
    accuracies = np.array([oxts.packet.pos_accuracy for oxts in dataset.oxts], dtype=float)
    return np.maximum(accuracies, sigma_floor)


def pose3_from_matrix(T: np.ndarray) -> Pose3:
    return Pose3(Rot3(T[:3, :3]), Point3(T[:3, 3]))


def lidar_poses_to_cam0(poses: list[np.ndarray], T_cam0_velo: np.ndarray) -> list[np.ndarray]:
    """Re-express a trajectory given in the Velodyne/LiDAR frame in the
    official KITTI odometry benchmark convention: translation is the pose
    of the left camera (cam0) coordinate system relative to cam0 at frame 0.

    T_cam0_velo is the fixed (time-invariant) extrinsic that maps a point
    from the Velodyne frame into the cam0 frame -- kiss_icp's
    KITTIRawDataset already computes this internally as
    dataset.calibration["T_cam0_velo"] using the same R_rect_00 @ T_velo_cam
    formula KITTI's own devkit/pykitti use, so it's read from there rather
    than recomputed.

    Since camera and LiDAR are rigidly mounted (a constant transform for
    every frame), converting a whole trajectory from one sensor's frame
    convention to another is the standard conjugation:
        P_cam0_i = T_cam0_velo @ P_lidar_i @ inv(T_cam0_velo)
    This must be applied identically to odometry, fused, and "gt" poses so
    all three stay in the same frame before scoring with evo -- the official
    KITTI odometry poses.txt files are already in this cam0 convention, so
    this is what makes our output comparable to them.
    """
    T_cam0_velo_inv = np.linalg.inv(T_cam0_velo)
    return [T_cam0_velo @ P @ T_cam0_velo_inv for P in poses]


def map_to_cam0(map_pcd: o3d.geometry.PointCloud, T_cam0_velo: np.ndarray) -> o3d.geometry.PointCloud:
    """Convert the accumulated map's points from the Velodyne frame into the
    cam0 frame using the same T_cam0_velo extrinsic as lidar_poses_to_cam0().

    Unlike a trajectory (a sequence of poses, which needs the conjugation
    above so relative motion stays correct), a point cloud is just a set of
    static points in space -- transforming it into a different frame is a
    single direct application of T_cam0_velo, not a conjugation.
    """
    converted = o3d.geometry.PointCloud(map_pcd)
    converted.transform(T_cam0_velo)
    return converted


def build_and_optimize_graph(
    odom_poses: list[np.ndarray],
    gps_xyz: np.ndarray,
    gps_sigmas: np.ndarray,
    odom_rot_sigma_deg: float = 0.5,
    odom_trans_sigma: float = 0.05,
) -> gtsam.Values:
    graph = gtsam.NonlinearFactorGraph()
    initial = gtsam.Values()

    prior_noise = gtsam.noiseModel.Diagonal.Sigmas(
        np.array([1e-6] * 3 + [1e-6] * 3)
    )
    odom_noise = gtsam.noiseModel.Diagonal.Sigmas(
        np.array(
            [np.deg2rad(odom_rot_sigma_deg)] * 3
            + [odom_trans_sigma] * 3
        )
    )

    n = len(odom_poses)
    poses = [pose3_from_matrix(T) for T in odom_poses]

    # anchor the first pose so the graph has a fixed gauge
    graph.add(gtsam.PriorFactorPose3(X(0), poses[0], prior_noise))

    for i in range(n):
        initial.insert(X(i), poses[i])
        if i > 0:
            relative = poses[i - 1].between(poses[i])
            graph.add(gtsam.BetweenFactorPose3(X(i - 1), X(i), relative, odom_noise))
        # Per-frame sigma from the OXTS receiver's own accuracy estimate
        # (see gps_sigmas_from_oxts) -- not a single sequence-wide constant.
        gps_noise = gtsam.noiseModel.Isotropic.Sigma(3, float(gps_sigmas[i]))
        graph.add(gtsam.GPSFactor(X(i), gps_xyz[i], gps_noise))

    params = gtsam.LevenbergMarquardtParams()
    params.setVerbosityLM("SILENT")
    optimizer = gtsam.LevenbergMarquardtOptimizer(graph, initial, params)
    result = optimizer.optimize()
    return result


def poses_to_kitti_lines(pose_matrices: list[np.ndarray]) -> list[str]:
    lines = []
    for T in pose_matrices:
        vals = T[:3, :4].reshape(-1)
        lines.append(" ".join(f"{v:.9e}" for v in vals))
    return lines


def write_kitti_poses(path: Path, pose_matrices: list[np.ndarray]) -> None:
    path.write_text("\n".join(poses_to_kitti_lines(pose_matrices)) + "\n")


def read_kitti_poses(path: Path) -> list[np.ndarray]:
    """Read a KITTI-format poses.txt (3x4 matrix per line, cam0 frame) into
    a list of 4x4 homogeneous matrices."""
    poses = []
    for line in path.read_text().strip().splitlines():
        vals = np.array([float(v) for v in line.split()])
        T = np.eye(4)
        T[:3, :4] = vals.reshape(3, 4)
        poses.append(T)
    return poses


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kitti_root", required=True, type=Path)
    ap.add_argument("--sequence", required=True, help="KITTI odometry benchmark sequence id, e.g. 00")
    ap.add_argument("--out_dir", required=True, type=Path)
    ap.add_argument(
        "--gps_sigma_floor",
        type=float,
        default=0.3,
        help="minimum GPSFactor sigma (m), applied even when OXTS reports a smaller pos_accuracy",
    )
    ap.add_argument(
        "--official_gt_poses",
        type=Path,
        default=None,
        help=(
            "path to the OFFICIAL KITTI odometry benchmark ground truth for this "
            "sequence (e.g. dataset/poses/00.txt from data_odometry_poses.zip). "
            "Already in cam0 frame. When given, this is written out as poses_gt.txt "
            "verbatim (not the self-computed OXTS proxy) so evo scores against the "
            "real benchmark reference. Forces --output_frame cam0 for odom/fused so "
            "everything lines up."
        ),
    )
    ap.add_argument(
        "--output_frame",
        choices=["lidar", "cam0"],
        default="cam0",
        help=(
            "coordinate frame for the written poses and map. 'cam0' matches the "
            "official KITTI odometry benchmark ground-truth convention (left camera "
            "frame) so results are directly comparable to poses.txt / published "
            "numbers. 'lidar' keeps everything in the Velodyne frame KISS-ICP "
            "natively works in."
        ),
    )
    ap.add_argument(
        "--skip_map",
        action="store_true",
        help="skip building/writing map.pcd (poses only, faster) -- e.g. for quick tuning runs",
    )
    ap.add_argument(
        "--map_voxel_size",
        type=float,
        default=0.2,
        help=(
            "voxel size (m) for the final accumulated map.pcd, and for the "
            "periodic incremental downsampling used to bound memory while "
            "accumulating. Not a settled project value -- tune per how the "
            "map is used downstream (Stage 2/3); 0.2m is a starting point "
            "for KITTI-scale outdoor scenes."
        ),
    )
    ap.add_argument(
        "--map_accumulate_every",
        type=int,
        default=50,
        help="merge+downsample the map every N frames while accumulating, to bound memory",
    )
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading KITTI raw drive for odometry sequence {args.sequence} ...")
    dataset = KITTIRawDataset(args.kitti_root, args.sequence)
    print(f"{len(dataset)} scans loaded.")

    t0 = time.time()
    odom_poses, map_pcd = run_kiss_icp(
        dataset,
        build_map=not args.skip_map,
        map_voxel_size=args.map_voxel_size,
        map_accumulate_every=args.map_accumulate_every,
    )
    print(f"KISS-ICP done in {time.time() - t0:.1f}s")
    if map_pcd is not None:
        print(f"Accumulated map (pre cam0-conversion): {len(map_pcd.points)} points "
              f"after {args.map_voxel_size}m voxel downsampling")

    gps_xyz = gps_positions_from_oxts(dataset)
    gps_sigmas = gps_sigmas_from_oxts(dataset, sigma_floor=args.gps_sigma_floor)
    assert len(gps_xyz) == len(odom_poses), "OXTS/GPS track and odometry length mismatch"
    print(
        f"OXTS pos_accuracy over sequence: "
        f"min={gps_sigmas.min():.2f}m median={np.median(gps_sigmas):.2f}m max={gps_sigmas.max():.2f}m"
    )

    print("Building GTSAM pose graph and optimizing ...")
    result = build_and_optimize_graph(
        odom_poses,
        gps_xyz,
        gps_sigmas,
    )

    fused_poses = [result.atPose3(X(i)).matrix() for i in range(len(odom_poses))]

    output_frame = args.output_frame
    if args.official_gt_poses is not None:
        official_gt = read_kitti_poses(args.official_gt_poses)
        if len(official_gt) != len(odom_poses):
            print(
                f"[WARNING] official ground truth has {len(official_gt)} poses, "
                f"but this run has {len(odom_poses)} frames -- check that "
                f"--official_gt_poses matches --sequence."
            )
        output_frame = "cam0"  # official poses.txt is always cam0; keep odom/fused matching

    gt_poses = list(dataset.gt_poses)  # self-computed OXTS proxy, in LiDAR frame

    if output_frame == "cam0":
        T_cam0_velo = dataset.calibration["T_cam0_velo"]
        odom_poses = lidar_poses_to_cam0(odom_poses, T_cam0_velo)
        fused_poses = lidar_poses_to_cam0(fused_poses, T_cam0_velo)
        gt_poses = lidar_poses_to_cam0(gt_poses, T_cam0_velo)
        if map_pcd is not None:
            map_pcd = map_to_cam0(map_pcd, T_cam0_velo)
        print(
            "Poses converted to cam0 (left camera) frame -- matches the official "
            "KITTI odometry poses.txt convention."
        )
    else:
        print("Poses left in the native Velodyne/LiDAR frame (--output_frame lidar).")

    if args.official_gt_poses is not None:
        # Use the real benchmark file verbatim as poses_gt.txt (already cam0-frame,
        # no conversion needed); keep our self-computed proxy alongside for reference.
        write_kitti_poses(args.out_dir / "poses_gt_selfcomputed.txt", gt_poses)
        gt_poses = official_gt
        print(
            f"Using official ground truth {args.official_gt_poses} as poses_gt.txt. "
            f"Self-computed OXTS-proxy ground truth also saved to "
            f"poses_gt_selfcomputed.txt for comparison."
        )
    else:
        print(
            "Note: poses_gt.txt is OUR OWN OXTS-derived proxy, not an officially "
            "downloaded ground truth file. Pass --official_gt_poses "
            "dataset/poses/<seq>.txt for a true benchmark-standard comparison."
        )

    write_kitti_poses(args.out_dir / "poses_odom.txt", odom_poses)
    write_kitti_poses(args.out_dir / "poses_fused.txt", fused_poses)
    write_kitti_poses(args.out_dir / "poses_gt.txt", gt_poses)
    print(f"Wrote poses_odom.txt / poses_fused.txt / poses_gt.txt to {args.out_dir}")

    if map_pcd is not None:
        map_path = args.out_dir / "map.pcd"
        ok = o3d.io.write_point_cloud(str(map_path), map_pcd)
        if not ok:
            raise RuntimeError(f"Open3D failed to write {map_path}")
        print(f"Wrote map.pcd to {map_path} ({len(map_pcd.points)} points)")
    else:
        print("Skipped map.pcd (--skip_map).")

    print()
    print("Evaluate with evo, e.g.:")
    print(f"  evo_ape kitti {args.out_dir/'poses_gt.txt'} {args.out_dir/'poses_odom.txt'} -a --save_plot {args.out_dir/'odom_ape.pdf'}")
    print(f"  evo_ape kitti {args.out_dir/'poses_gt.txt'} {args.out_dir/'poses_fused.txt'} -a --save_plot {args.out_dir/'fused_ape.pdf'}")
    print(f"  evo_rpe kitti {args.out_dir/'poses_gt.txt'} {args.out_dir/'poses_fused.txt'} -a --delta 100 --delta_unit m --save_results {args.out_dir/'eval_rpe.zip'}")
    print("(headless server: run `evo_config set plot_backend Agg` once first, or --plot will crash on missing tkinter)")


if __name__ == "__main__":
    main()
