# Decisions

Running log of decisions and the reasoning behind them, so later work
(by either agent, or by future-you) doesn't re-litigate settled
questions. New entries go at the bottom. Each entry: what was decided,
one-line why.

## Repo scope

**Repo named `carla-digital-twin-av`.** Reflects the end goal (a CARLA
digital twin map) rather than the current data source — KITTI is only
Stage 1's input and may change later.

## SLAM method

**Start with KISS-ICP, not LIO-SAM.** Pure LiDAR odometry first, to
validate the pipeline shape before adding IMU-fusion complexity.

**Use KITTI Odometry Benchmark, not raw OXTS-derived ground truth.**
The benchmark ships an official `poses.txt` (RTK-corrected), which is
more reliable than deriving ground truth ourselves from raw GPS/IMU.

**Fuse via a loosely-coupled pose graph (GTSAM), not tightly-coupled
LIO.** KITTI's OXTS is only 10Hz — too low-rate for meaningful IMU
preintegration, which tightly-coupled LIO depends on.

**Use the official motion-compensated LiDAR (Odometry Benchmark
release) exclusively — not the raw sync (uncompensated) LiDAR, and
not hand-rolled compensation from raw scans.** Avoids a class of bug
that runs without error but silently degrades accuracy (same failure
mode seen in the model-comparison testing below). The raw sync
`velodyne_points/` download is not read anywhere in the pipeline —
not even as a validation reference. If a raw-vs-compensated
comparison becomes useful later, that's a new decision to make then,
not a standing use of this data.

**LiDAR point cloud loading uses KISS-ICP's own dataset/pipeline API,
not a hand-rolled reader.** A hand-rolled `data_loader.py` reader for
the `.bin` scans was tried first, despite this already being ruled
out (see "Process checks" below) — it needed a manual per-point
z-coordinate correction (`_correct_kitti_scan`, an intrinsic Velodyne
vertical-angle calibration fix, unrelated to motion compensation)
that KISS-ICP's own loader already handles, and produced measurably
worse odometry (RPE ~1.1% vs ~0.5% with the built-in loader) before
the cause was found. `data_loader.py` keeps its OXTS parsing and
frame-alignment logic (that part was correct); LiDAR reading is
KISS-ICP's own.

## Data alignment

**Raw sync frames 0-4540 map to `poses/00.txt` (4541 entries); frames
4541-4543 are discarded.** Verified two independent ways (timestamp
jitter-pattern matching at the sequence start, cumulative elapsed-time
matching at the end) and confirmed by the official devkit
`readme.txt`. This is fixed in `docs/data-spec.md` — no need to
re-derive it.

**Camera is not used in Stage 1.** The current SLAM approach (KISS-ICP
LiDAR odometry + GPS pose-graph fusion) has no camera input. The four
`image_00-03/` folders and `calib_cam_to_cam.txt` /
`calib_velo_to_cam.txt` sit on disk unused; don't load them.

## Agent roles and workflow

**Agent A (qwen3-coder-next) = Builder, Agent B (qwen3.8:27b-bf16) =
Reviewer.** Chosen from head-to-head testing, not assumption — Agent B
produced code with a repeated syntax error (`noiseModel:Diag`) and
hallucinated APIs (nonexistent GTSAM/Open3D methods) across two test
rounds; Agent A's failures were comparatively less severe.

**Quantitative evaluation always goes through established tools (evo,
Open3D's built-in functions), never hand-rolled.** Same rationale as
above — reduces the risk of a plausible-looking but wrong custom
implementation.

**Reviewer only does visual QA, never writes code.** Applies even to
tasks like point-cloud comparison, where Agent B has a demonstrated
track record of hallucinating library APIs.

**Builder and Reviewer are two peer opencode primary agents (manual
Tab switch), not a primary/subagent orchestration.** Keeps the
decision of *when* review happens under direct control, rather than
letting the Builder agent decide when to invoke review.

## Process checks

**A constraint being correctly written in `agents/builder.md` doesn't
guarantee it's followed — periodically check actual code against it,
don't infer compliance from a clean-looking result.** The
"established libraries, not hand-rolled" rule was in
`docs/architecture.md` and `agents/builder.md` from the start and
correctly named KISS-ICP as the off-the-shelf package to use, but
Stage 1's LiDAR loading was hand-rolled anyway (see "LiDAR point cloud
loading" above) and went unnoticed through several rounds of
debugging (core dump, z-coordinate errors, scan correction chasing)
before the violation itself was caught, not just its symptoms. Reading
the constraint in a document doesn't confirm it's what's actually
running — reviewing what the code does periodically, not just
plausible progress updates, is what catches this.

## Evaluation

**An earlier "RPE rmse 0.045m" figure (recorded in
`stages/01-slam/AGENTS.md`) was computed with `evo_rpe`'s default
delta (`--delta 1 --delta_unit frames`), not the project-specified
`--delta 100 --delta_unit m`.** The two are different quantities
(meters-per-frame vs. percent-per-100m) and are not comparable to the
RPE threshold, which is defined in the percent-per-100m convention.
The figure was not a valid RPE-percentage number and did not actually
establish that the threshold was cleared. Corrected by re-running
`evo_rpe` with the specified flags; see the numbers below.

**RPE threshold revised from 1% to 1.5%.** Decided by the project
owner (Yi-Chen), not by either agent — per `docs/done-criteria.md`,
changing the threshold is a human-tier decision. Reasoning: the first
correctly-computed RPE (`evo_rpe --delta 100 --delta_unit m`) on the
verified fused baseline came in at 1.28%, against APE rmse of 0.063m
(down from 3.52m odom-only). The original 1% threshold was itself a
starting point taken from published KISS-ICP KITTI results, not a
strict spec (see `docs/done-criteria.md`). A visual pass on the
trajectory plot and point cloud render was also done and looked
acceptable. 1.28% was judged close enough, and the fused result good
enough on the metric that does have a hard bar (APE), that revising
the threshold rather than continuing to tune was the better use of
time, given Stage 1's output only needs to be good enough to support
Stage 2/3 (road and scene reconstruction), not to match a published
benchmark number exactly.

**Under the revised 1.5% threshold, Stage 1's fused baseline (RPE
1.28%, APE rmse 0.063m) passes.** Stage 2 (road reconstruction) can
start using this baseline's output (`est_poses.txt`, point cloud map)
per `docs/roadmap.md`.
