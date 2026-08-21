# carla-digital-twin-av

Building a CARLA digital twin map from recorded vehicle sensor data
(LiDAR / Camera / GPS-IMU), end to end.

```
Recorded vehicle data
        |
   +----+----+------------+
   |         |            |
 LiDAR    Camera      GPS / IMU
   |         |            |
   +----+----+------------+
        |
  Localization / SLAM              <-- Stage 1 (IN PROGRESS)
        |
  Global 3D map
        |
   +----+----------------------+
   |                            |
 Road reconstruction      Scene reconstruction
   |                            |
 OpenDRIVE (.xodr)          3D Mesh (FBX/OBJ/UE)
   |  Stage 2 (NOT STARTED) |  Stage 3 (NOT STARTED)
   +----+----------------------+
        |
      CARLA                       <-- Stage 4 (NOT STARTED)
        |
  Digital Twin Map
```

CARLA needs two things for a conventional custom map: 3D geometry
(mesh) and an OpenDRIVE (`.xodr`) road definition. Everything upstream
exists to produce those two artifacts from recorded sensor data.

Full diagram and rationale: `docs/architecture.md`. Per-stage
input/output contracts: `docs/roadmap.md`. Why things were decided the
way they were: `docs/decisions.md`.

## Status

Only **Stage 1 (SLAM)** is active — KITTI Odometry Benchmark sequence
00, KISS-ICP + GPS pose-graph fusion, evaluated against official
ground truth. See `stages/01-slam/` and `docs/data-spec.md`.

Stages 2-4 are placeholders (folder + README describing the expected
interface only).

## Working with the agents

This repo uses two [opencode](https://opencode.ai) agents, configured
in `opencode.json`:

- **`builder`** — writes and runs code. Bound to `qwen3-coder-next`.
- **`reviewer`** — visual QA only, no code editing. Bound to
  `qwen3.8:27b-bf16` (vision-capable).

Both are primary agents — switch between them with `Tab` in an
opencode session, or launch directly:

```
opencode --agent builder
opencode --agent reviewer
```

Both automatically read `AGENTS.md` on start, which points them to
their full role instructions (`agents/builder.md` /
`agents/reviewer.md`) and the docs they need for the active stage.

Handoff between the two happens through files, not a shared
conversation: `PROJECT_STATUS.md` at the repo root is a running log —
check it to see what the other agent last did.

## Requirements

Two local Ollama instances must already be running before starting
opencode (see `opencode.json` for the ports/models it expects). This
repo doesn't manage that setup — check the current process is up with
`curl localhost:<port>/api/tags` before starting a session.

Machine-specific data paths go in `config/paths.yaml` (gitignored, no
template committed yet — see `docs/data-spec.md` once it's written).
