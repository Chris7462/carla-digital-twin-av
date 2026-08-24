# Project Status

Plain-text run log. One entry per run/session: what was done, what the
result was. Newest at the bottom.

## Stage 1 (SLAM)

- Baseline established: KISS-ICP + GTSAM/GPS fusion, seq 00. RPE 1.28%
  (`evo_rpe --delta 100 --delta_unit m`), APE rmse 0.063m. Passes the
  < 1.5% threshold. See `docs/reference.md` for full detail.
