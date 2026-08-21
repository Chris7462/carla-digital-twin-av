# AGENTS.md

Project: `carla-digital-twin-av`. Building a CARLA digital twin map
from recorded vehicle sensor data (LiDAR/Camera/GPS-IMU), end to end.
Full picture: `docs/architecture.md`.

## Read this first

1. `docs/architecture.md` — full pipeline, which stage is active
2. `docs/roadmap.md` — per-stage input/output contracts and status
3. `docs/decisions.md` — settled decisions and why. Check here before
   proposing something — it might already be ruled out.

Then read your own role file:
- Builder: `agents/builder.md`
- Reviewer: `agents/reviewer.md`

Each active stage additionally has its own `data-spec.md` and
`done-criteria.md` under `stages/<stage>/` — read those before doing
any work in that stage's folder.

## Current status

Only Stage 1 (`stages/01-slam/`) is active. Stages 2-4 are placeholders
— folder + README describing the expected interface, no implementation.
Don't start work in a placeholder stage without being explicitly asked.

## Two agents, not one

This project uses two separate agents with non-overlapping jobs:
Builder writes and runs code, Reviewer does visual QA only. Neither
substitutes for the other. See `docs/decisions.md` for why they're
split this way instead of one agent doing both.

## Ground rules (apply to both agents)

- Use established libraries for anything with a well-known one
  (KISS-ICP, GTSAM, Open3D, evo). Don't hand-roll numerical algorithms
  that already have a maintained implementation — see
  `docs/decisions.md` for why this matters here specifically.
- Never install packages. If something's missing, stop and report it.
- Don't re-derive settled facts (e.g. KITTI frame alignment) that are
  already fixed in a `data-spec.md`. Follow the spec; flag it if it
  looks wrong instead of reworking it independently.
- Progress handoff happens through files, not memory: append to
  `PROJECT_STATUS.md` at the repo root when you finish something.
