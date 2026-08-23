# Done criteria — Stage 1 (SLAM)

Pass/fail is decided by these numbers, computed by `evo`. Not a
judgment call by either agent — the threshold is fixed here and the
evaluation script checks against it automatically.

## Pass/fail is a strict comparison, not a judgment call

`RPE < 1.5%` means exactly that: the measured value must be less than
1.5. Do not round, do not describe a value above the threshold as
having "achieved" or "reached" the threshold, and do not report a
failing number alongside language that implies success (e.g.
"non-strictly achieved," "very close"). If a result is close enough
that the threshold itself might be worth revisiting, that's a
conversation to have per the paragraph below — it does not change
whether *this run* passed against whatever threshold was in force at
the time it was scored.

## Only one evaluation method decides pass/fail

The `evo` commands below — run exactly as specified — are the only
numbers that determine pass/fail. This project has repeatedly run
into a variant of the same problem: a tool, library, or alternate
evaluation method produces a more favorable number than the
project-specified `evo` run, and that number gets reported as the
result instead. It doesn't matter how well-reasoned the substitution
sounds in the moment (a different but legitimate evaluation method, a
built-in tool from the SLAM library itself, a hand calculation) — if
it isn't the exact `evo` command specified below, it does not decide
pass/fail. Report it as supplementary context if useful ("KISS-ICP's
built-in evaluator reports 0.528%, included for reference"), but it
cannot substitute for, override, or be presented alongside the
project's number in a way that implies the run passed.

**Pass/fail can only be declared in `eval_report.json` and the
`PROJECT_STATUS.md` line — nowhere else.** Do not create a separate
results/summary file (e.g. `BASELINE_RESULTS.md`) that states its own
PASS/FAIL verdict. If a summary file is useful for narrating what was
tried, it can describe what happened, but the verdict itself lives
only in the two files above, computed only from the specified `evo`
command.

## Before running evo: coordinate frame

`poses/00.txt` ground truth is in the left camera (cam0) frame.
KISS-ICP's output is in the Velodyne frame. **Transform `est_poses.txt`
into the cam0 frame using the `Tr` matrix in
`dataset/sequences/00/calib.txt` before running `evo_ape`/`evo_rpe`.**
Comparing untransformed Velodyne-frame poses against `poses/00.txt`
gives a wrong number, not just a noisier one — see `docs/data-spec.md`
for the matrix and the conversion detail.

Coordinate frames come up more than once in this pipeline — GPS
positions are naturally in ENU (north/east), LiDAR odometry is in the
Velodyne frame, ground truth is in the cam0 frame. Any two of these
being combined (fusion, evaluation, comparison) requires an explicit,
verified alignment first. Don't assume two position/pose streams
share a frame just because both are "roughly forward-facing" —
verify with a small numeric check (a handful of frames, by hand)
before trusting a result built on the combination.

## Metrics

Run against `poses/00.txt` (official ground truth), after the frame
conversion above. **Use these exact commands — do not run with evo's
defaults.** evo's default RPE is meters-per-frame (`--delta 1
--delta_unit frames`), which is a different quantity from the
percentage-per-100m the threshold below is defined against; the two
are not comparable and mixing them up gives a number that looks like
a valid result but isn't. (This project has hit this exact mix-up in
practice — an early "RPE rmse 0.045m" figure recorded elsewhere was
computed with the default delta, not this command, and is not a valid
RPE-percentage number. It has been corrected — see
`stages/01-slam/AGENTS.md` and `docs/decisions.md`.)

```
evo_ape kitti poses/00.txt est_poses.txt -a --save_results eval_ape.zip
evo_rpe kitti poses/00.txt est_poses.txt -a --delta 100 --delta_unit m --save_results eval_rpe.zip
```

`--delta 100 --delta_unit m` gives RPE as translation error per 100m
of travel — this is what "RPE < 1.5%" below means, and matches the
convention KISS-ICP's published KITTI results and the KITTI odometry
benchmark itself use. Record the result as `RPE_percentage` in
`eval_report.json` (a meters-per-100m value is already a percentage;
don't relabel it as meters without also giving the percentage).

Both RPE and ATE must be recorded for every run — in
`eval_report.json` (both numbers, not just the one being checked
against the threshold) and in the `PROJECT_STATUS.md` line (see
`agents/builder.md`). ATE has no hard threshold, but its trend across
runs is one of the signals used below to tell a tuning problem from a
method-ceiling problem.

## Thresholds

| Metric | Threshold | Status |
|---|---|---|
| Relative translation error (RPE, % per 100m) | < 1.5% (revised from 1%, see `docs/decisions.md`) | measured: 1.28% — passes revised threshold |
| ATE (absolute trajectory error, meters) | reference only, no hard threshold yet | measured: APE rmse 0.063m (fused), 3.52m (odom-only) |

The 1% RPE threshold was a starting point based on published KISS-ICP
results on KITTI (roughly 0.5-1% in the original paper), not a
strict spec. It was revised to 1.5% by explicit human decision (the
project owner, not either agent) after the first correctly-computed
RPE (`--delta 100 --delta_unit m`, per the command above) came in at
1.28% and a visual pass on the trajectory/point-cloud output looked
acceptable. See `docs/decisions.md` ("Evaluation threshold") for the
recorded reasoning. This was not a case of a failing run being
reported as passing — the threshold itself was changed, on record,
and the 1.28% run is scored against the threshold that was in force
once the change was made.

**Changing the threshold is a human decision, same tier as changing
SLAM methods (see "If a run doesn't clear the threshold" below).**
Report the number and stop; don't revise the threshold yourself, even
if the case for revising it seems obvious.

## Order of operations

Run KISS-ICP + GPS pose-graph fusion (per `docs/architecture.md` and
`docs/decisions.md`) before tuning anything, and before reporting a
result as final. A pure-LiDAR baseline without GPS fusion is a useful
reference point to record, but:

- it is not the "first attempt" for the purposes of the 3-attempt
  tuning limit below — GPS fusion is part of the designed method, not
  an optional enhancement
- **it is not a substitute for a working fused result.** If fusion
  produces a worse number than the unfused baseline, that's a bug in
  the fusion implementation to debug (see `agents/builder.md`), not a
  reason to report the baseline as the run's result. A regression
  this large (multiple times worse, not marginally worse) is a strong
  signal of a concrete bug — a noise-model sign error, a coordinate
  frame or unit mismatch between the odometry and GPS inputs — not a
  property of loosely-coupled fusion itself.

## Debugging a bug is not the same as tuning — and doesn't count toward the limit below

These are different activities and shouldn't be tracked against the
same counter:

- **Debugging**: the method is producing results that are wrong for a
  concrete, findable reason — a coordinate frame mismatch, a sign
  error, a unit mismatch, an off-by-one. The signature is usually a
  large or qualitative failure (fusion making things *much* worse,
  not marginally worse), and the fix is specific once found, not a
  parameter sweep.
- **Tuning**: the method is implemented correctly and producing
  sensible results, but the specific parameter values (noise models,
  voxel size, correspondence thresholds) haven't been optimized to
  clear the threshold yet.

Only tuning attempts count toward the 3-attempt limit below. Finding
and fixing a concrete bug — even if it takes several rounds of
investigation — is expected debugging work, not a counted attempt.
The distinction isn't a loophole to avoid ever hitting the limit: if
in doubt, the presence of a specific, nameable root cause (like "GPS
ENU and Velodyne-forward differ by heading angle, unrotated") is what
makes something debugging rather than tuning. A vague "results are
worse, not sure why, tried adjusting weights" is tuning-without-a-
diagnosis and does count.

When isolating a fix's contribution (e.g. two changes made together,
like a dtype change and a separate correction applied at the same
time), test them independently before reporting a combined result —
don't report an improvement without knowing which change caused it.

## If a run doesn't clear the threshold

Don't tune indefinitely. After **3 tuning attempts** on the same
method (with GPS fusion already in place, per the order above, and
after known bugs are fixed per the distinction above) without
clearing the RPE threshold, stop and report to the human instead of
continuing to adjust parameters or switching methods — see
`agents/builder.md` for what to report and why this isn't the
Builder's call to make alone.

RPE/ATE trend across those attempts is the signal for what to report:

- **Still decreasing, even slowly** — likely a tuning problem, more
  attempts may still help. Say so when reporting.
- **Flat or oscillating with no clear trend** — likely a method
  ceiling (e.g. KISS-ICP has no loop closure; a sequence with a
  return-to-start segment may not clear a tight RPE threshold no
  matter how it's tuned). Say so when reporting — this is the signal
  that a method change (not just more tuning) may be needed.

## What counts as "done" for Stage 1

1. `evo_rpe` (run with the exact command above, on the full designed
   method per "Order of operations") clears the threshold.
2. Output files exist in the format specified in `docs/data-spec.md`
   (`est_poses.txt`, point cloud map, eval report).
3. Reviewer has done a visual pass on the trajectory plot and point
   cloud render (see `agents/reviewer.md`) — this is a supplementary
   check for problems the RPE number alone might miss (e.g. a
   localized bad segment that doesn't move the aggregate metric much),
   not a substitute for the quantitative threshold.

Passing (1) and (2) without (3) is not done. Passing (3) without (1)
is not done, regardless of how the trajectory plot looks.
