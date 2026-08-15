---
name: conda-environments
description: Create, modify, and troubleshoot Conda or Mamba environments with a strict channel policy. Use when writing or editing environment.yml, creating or updating an environment, choosing a solver, resolving channel conflicts or unsatisfiable solves, registering a Jupyter kernel for an environment, or deciding whether to pin or lock dependencies.
---

# Conda Environments

Keep environment definitions explicit, portable, and solvable. Prefer `mamba`,
or `conda` with the libmamba solver; both resolve the same specifications.

## Apply the channel policy

Channel order is not cosmetic — with strict priority it determines which
channel a package may come from at all.

1. `conda-forge` first.
2. `bioconda` after it, never above it. Bioconda packages are built against
   conda-forge and break when the order is inverted.
3. `nodefaults` last, to exclude the Anaconda default channel.
4. Strict channel priority, so packages are never mixed across channels.

Always write the channel list into `environment.yml` itself, even when the
machine's `~/.condarc` already sets it. The file must solve identically on a
machine without that configuration:

```yaml
name: project-analysis
channels:
  - conda-forge
  - bioconda
  - nodefaults
dependencies:
  - python=3.11
  - numpy
  - scanpy
  - samtools
```

`channel_priority: strict` belongs in `~/.condarc` or a project `.condarc`, not
in `environment.yml`, which has no field for it. Verify it before diagnosing a
confusing solve:

```bash
conda config --show channels channel_priority
```

## Write dependencies

- List direct dependencies only. Do not paste a full `conda env export`, which
  captures transitive packages and platform-specific builds.
- Keep `pip:` dependencies in one block at the end, and only for packages
  genuinely unavailable from conda-forge or bioconda.
- Prefer `package=version` over `package==version=build`; pinning a build
  string makes the file unsolvable on other platforms.

## Pin and lock deliberately

- Pin versions when reproducibility is an explicit goal, or when a specific
  version is required for correctness.
- Do not pin during early exploration without a concrete need — premature pins
  cause unsatisfiable solves later.
- Do not create, refresh, require, or prompt for a lock file unless the user
  explicitly asks for one. A missing lock is not a defect.

## Register a Jupyter kernel

When an environment includes a kernel, register it before finishing; otherwise
the environment is invisible to Jupyter and notebooks silently run against the
wrong interpreter:

```bash
conda run -n <env> python -m ipykernel install --user \
    --name <env> --display-name "Python (<env>)"
```

Verify with `jupyter kernelspec list`, and report the registered kernel name.

## Do not mutate shared state

- Never install into or modify the `base` environment.
- Never modify an environment you did not create without saying so first.
- Create environments in the project's or platform's expected location. On
  storage-constrained systems, confirm the environment and package caches
  resolve outside the root filesystem before solving.

## Troubleshoot solves

For an unsatisfiable solve, check in this order:

1. Channel order and strict priority.
2. An over-constrained pin, especially a build string or a Python version.
3. A package that exists only for another platform or architecture.
4. Mixed `pip` and conda installations of the same package.

Report the actual failing specification rather than retrying the same solve
with a longer timeout.
