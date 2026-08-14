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

Root filesystem is ~5 GB and fills especially quickly on GPU machines. Put all temporary
files, caches, build directories, environments, user installations, models, and compiled
GPU artifacts under `/scratch/.dotfiles/`; finals go to `/results`.
Write analysis outputs to `/scratch` by default: its storage mount is substantially faster
than `/results`. Write analysis outputs to `/results` only when the user explicitly asks
for them there; reserve `/results` for requested final artifacts.
Never use root-backed `/tmp`, `~/.cache`, `~/.local`, `~/.conda`, or `.venv` defaults.
Run `ulimit -c 0` at session start and monitor root usage during installation-heavy work.

## Environment

Keep dependency recipes and locks in `environment/`. Put actual Conda/virtual environments
and interactive installations under `/scratch/.dotfiles/envs/`; recreate them deterministically
from their lock when locking has been explicitly requested; otherwise do not rely on persistent scratch state for anything that must survive.

Redirect caches to `/scratch` at runtime — do **not** use Dockerfile `ENV` (`/scratch` is
empty at build time, so ENV breaks `postInstall` hardlinks and `pip install -e`).
Use a `/etc/profile.d/*.sh` script guarded by `if [ -d /scratch ]`, also sourced from
`/etc/bash.bashrc` for interactive terminals:

```bash
scratch_tools=/scratch/.dotfiles
export CONDA_PKGS_DIRS="$scratch_tools/cache/conda-pkgs"
export MAMBA_PKGS_DIRS="$CONDA_PKGS_DIRS"
export PIP_CACHE_DIR="$scratch_tools/cache/pip"
export XDG_CACHE_HOME="$scratch_tools/cache"
export CONDA_ENVS_PATH="$scratch_tools/envs/conda"
export UV_CACHE_DIR="$scratch_tools/cache/uv"
export HF_HOME="$scratch_tools/cache/huggingface"
export TORCH_HOME="$scratch_tools/cache/torch"
export CUDA_CACHE_PATH="$scratch_tools/cache/cuda"
export TRITON_CACHE_DIR="$scratch_tools/cache/triton"
export TMPDIR="$scratch_tools/tmp"
```

## Reproducibility

- Apply these conventions only after the user explicitly requests reproducibility or finalization.
- Pin environment versions in Dockerfile / postInstall / env yaml when stable.
- Use `run` as the single reproducible entrypoint and write all final artifacts to `/results`.
- Avoid machine-specific paths and verify the workflow from a clean state.
