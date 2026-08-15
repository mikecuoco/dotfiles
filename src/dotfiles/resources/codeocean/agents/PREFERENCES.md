# Code Ocean Capsule Conventions

Extends the global agent preferences for work inside a Code Ocean capsule.

## Layout

- `/code` — source; `run` or `run.sh` is an opt-in finalized entrypoint
- `/data` — read-only inputs; never write here
- `/results` — all final artifacts
- `/scratch` — large temporary data (much more space than root)
- `/environment` — dependency recipes and optional locks, never built
  environments

## Storage

Root storage is about 5 GB and fills especially quickly on GPU machines. Put
temporary files, caches, builds, user installations, models, environments, and
compiled GPU artifacts under `/scratch/.dotfiles/`. Never use root-backed
`/tmp`, `~/.cache`, `~/.local`, `~/.conda`, or `.venv` defaults. Use `/scratch`
for intermediates and `/results` only for requested final artifacts.

## Reproducibility is opt-in

Do not create, modify, invoke, or require `run`, `run.sh`, or `conda-lock`
until explicitly requested. Missing locks or a run entrypoint do not make an
exploratory capsule deficient.

Use the `code-ocean-capsule` skill for layout, environment, provenance, and
finalization workflows.
