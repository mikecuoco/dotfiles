# HPC Cluster Conventions

Extends the global agent preferences for work on a shared HPC cluster.

## Login nodes

- Do not run analyses, builds, large file operations, or long installations on
  a login node. Submit them to the scheduler or take an interactive allocation.
- Login nodes are shared. Before anything memory-intensive, check available
  memory; `wait_for_mem_available <GB>` blocks until enough is free and is
  exported for use inside Snakemake rules.

## Environments

- There is no root access. Install everything under `$HOME` or scratch storage,
  never system-wide.
- Prefer micromamba, rooted at `$MAMBA_ROOT_PREFIX` (`$HOME/micromamba`).
  User-installed tools belong in `$HOME/bin`.
- Do not assume a package manager, module system, or scheduler is present.
  Check before invoking one.

## Submitted work

- State cores, memory, and walltime explicitly rather than relying on site
  defaults, which are usually wrong for real jobs.
- Prefer array jobs or a workflow manager over shell loops across samples.
- Long or expensive work should be resumable; do not require a multi-hour job
  to succeed on the first attempt.
- Never cancel, modify, or resubmit jobs you did not submit.

## Storage

- Home directories are quota-limited and often slow. Keep large intermediates,
  caches, and environments on scratch or project storage.
- Verify a destination has room before writing large outputs, and prefer
  streaming or chunked processing to materializing whole datasets.
- Scratch storage is frequently purged on a schedule. Do not leave the only
  copy of a result there.
