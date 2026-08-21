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
release), not hand-rolled compensation from raw scans.** Avoids a
class of bug that runs without error but silently degrades accuracy
(same failure mode seen in the model-comparison testing below). The
raw (uncompensated) download is kept only as a validation reference,
not used in the pipeline itself.

## Data alignment

**Raw sync frames 0-4540 map to `poses/00.txt` (4541 entries); frames
4541-4543 are discarded.** Verified two independent ways (timestamp
jitter-pattern matching at the sequence start, cumulative elapsed-time
matching at the end) and confirmed by the official devkit
`readme.txt`. This is fixed in `docs/data-spec.md` — no need to
re-derive it.

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
