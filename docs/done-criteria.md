# Done criteria — Stage 1 (SLAM)

Pass/fail is decided by these numbers, computed by `evo`. Not a
judgment call by either agent — the threshold is fixed here and the
evaluation script checks against it automatically.

## Before running evo: coordinate frame

`poses/00.txt` ground truth is in the left camera (cam0) frame.
KISS-ICP's output is in the Velodyne frame. **Transform `est_poses.txt`
into the cam0 frame using the `Tr` matrix in
`dataset/sequences/00/calib.txt` before running `evo_ape`/`evo_rpe`.**
Comparing untransformed Velodyne-frame poses against `poses/00.txt`
gives a wrong number, not just a noisier one — see `docs/data-spec.md`
for the matrix and the conversion detail.

## Metrics

Run against `poses/00.txt` (official ground truth), after the frame
conversion above:

```
evo_ape kitti poses/00.txt est_poses.txt -a
evo_rpe kitti poses/00.txt est_poses.txt -a
```

Both RPE and ATE must be recorded for every run — in
`eval_report.json` (both numbers, not just the one being checked
against the threshold) and in the `PROJECT_STATUS.md` line (see
`agents/builder.md`). ATE has no hard threshold, but its trend across
runs is one of the signals used below to tell a tuning problem from a
method-ceiling problem.

## Thresholds

| Metric | Threshold | Status |
|---|---|---|
| Relative translation error (RPE) | < 1% | not yet measured |
| ATE (absolute trajectory error) | reference only, no hard threshold yet | not yet measured |

The 1% RPE threshold is a starting point based on published KISS-ICP
results on KITTI (roughly 0.5-1% in the original paper), not a
strict spec. If the first baseline run lands close but doesn't clear
it, that's a discussion point, not an automatic fail — update this
file with the revised threshold and a one-line reason, don't just
lower it silently.

## If a run doesn't clear the threshold

Don't tune indefinitely. After **3 tuning attempts** on the same
method without clearing the RPE threshold, stop and report to the
human instead of continuing to adjust parameters or switching
methods — see `agents/builder.md` for what to report and why this
isn't the Builder's call to make alone.

RPE/ATE trend across those attempts is the signal for what to report:

- **Still decreasing, even slowly** — likely a tuning problem, more
  attempts may still help. Say so when reporting.
- **Flat or oscillating with no clear trend** — likely a method
  ceiling (e.g. KISS-ICP has no loop closure; a sequence with a
  return-to-start segment may not clear a tight RPE threshold no
  matter how it's tuned). Say so when reporting — this is the signal
  that a method change (not just more tuning) may be needed.

## What counts as "done" for Stage 1

1. `evo_rpe` clears the threshold above.
2. Output files exist in the format specified in `docs/data-spec.md`
   (`est_poses.txt`, point cloud map, eval report).
3. Reviewer has done a visual pass on the trajectory plot and point
   cloud render (see `agents/reviewer.md`) — this is a supplementary
   check for problems the RPE number alone might miss (e.g. a
   localized bad segment that doesn't move the aggregate metric much),
   not a substitute for the quantitative threshold.

Passing (1) and (2) without (3) is not done. Passing (3) without (1)
is not done, regardless of how the trajectory plot looks.
