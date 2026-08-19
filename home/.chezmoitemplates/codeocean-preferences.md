# Code Ocean Capsule Conventions

Extends the global agent preferences for work inside a Code Ocean capsule.

## Layout

- `/code` — source; `run` or `run.sh` is an opt-in finalized entrypoint
- `/data` — read-only inputs; never write here
- `/results` — all final artifacts
- `/scratch` — large temporary data (much more space than root)

## Development stage

- During exploration, prioritize robust, logical code and fast iteration.
- Do not create, modify, invoke, or require `run` or `run.sh` until explicitly requested.
- Do not create, refresh, require, or prompt for `conda-lock` until explicitly requested.
- Missing locks or a run entrypoint do not make an exploratory capsule deficient.
- Always consider memory, CPU concurrency, runtime, storage, and recomputation.

## Storage

Root storage is about 5 GB and fills especially quickly on GPU machines. Put
temporary files, caches, builds, user installations, models, environments, and
compiled GPU artifacts under `/scratch/.dotfiles/`. Never use root-backed
`/tmp`, `~/.cache`, `~/.local`, `~/.conda`, or `.venv` defaults. Use `/scratch`
for intermediates and `/results` only for requested final artifacts.

## Environment

Keep dependency recipes and optional locks in `environment/`, but put actual
environments under `/scratch/.dotfiles/envs/`. Redirect caches at runtime; do
not put `/scratch` paths in Dockerfile `ENV` because the mount is unavailable
during image construction. Use the `code-ocean-capsule` skill for detailed
layout, environment, provenance, and finalization workflows.
