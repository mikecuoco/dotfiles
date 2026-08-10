# Code Ocean Capsule Conventions

Extends the global CLAUDE.md for work inside a Code Ocean capsule.

## Layout

- `/code` — source; `run` or `run.sh` is the entrypoint
- `/data` — read-only inputs; never write here
- `/results` — all final artifacts
- `/scratch` — large temporary data (much more space than root)

## Storage

Root filesystem is ~5 GB and fills especially quickly on GPU machines. Put all temporary
files, caches, build directories, environments, user installations, models, and compiled
GPU artifacts in dedicated `/scratch` subdirectories; finals go to `/results`.
Never use root-backed `/tmp`, `~/.cache`, `~/.local`, `~/.conda`, or `.venv` defaults.
Run `ulimit -c 0` at session start and monitor root usage during installation-heavy work.

## Environment

Keep dependency recipes and locks in `environment/`. Put actual Conda/virtual environments
and interactive installations under `/scratch/envs/`; recreate them deterministically from
their lock rather than relying on persistent scratch state.

Redirect caches to `/scratch` at runtime — do **not** use Dockerfile `ENV` (`/scratch` is
empty at build time, so ENV breaks `postInstall` hardlinks and `pip install -e`).
Use a `/etc/profile.d/*.sh` script guarded by `if [ -d /scratch ]`, also sourced from
`/etc/bash.bashrc` for interactive terminals:

```bash
export CONDA_PKGS_DIRS=/scratch/cache/conda-pkgs
export MAMBA_PKGS_DIRS=/scratch/cache/conda-pkgs
export PIP_CACHE_DIR=/scratch/cache/pip
export XDG_CACHE_HOME=/scratch/cache
export CONDA_ENVS_PATH=/scratch/envs/conda
export UV_CACHE_DIR=/scratch/cache/uv
export HF_HOME=/scratch/cache/huggingface
export TORCH_HOME=/scratch/cache/torch
export CUDA_CACHE_PATH=/scratch/cache/cuda
export TRITON_CACHE_DIR=/scratch/cache/triton
export TMPDIR=/scratch/tmp
```

## Reproducibility

- Pin environment versions in Dockerfile / postInstall / env yaml.
- `run` is the single reproducible entrypoint; write all artifacts to `/results`.
- No machine-specific paths; runs must reproduce from a clean state.
