# Done criteria — Stage 1 (SLAM)

Pass/fail is decided by these numbers, computed by `evo`. Not a
judgment call by either agent — the threshold is fixed here and the
evaluation script checks against it automatically.

## Metrics

Run against `poses/00.txt` (official ground truth):

```
evo_ape kitti poses/00.txt est_poses.txt -a
evo_rpe kitti poses/00.txt est_poses.txt -a
```

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
