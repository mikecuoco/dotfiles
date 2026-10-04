---
name: jupyter-workflow
description: Create, edit, organize, execute, and review Jupyter notebooks with a linear, reproducible workflow. Use for .ipynb work, notebook refactoring, fresh-kernel validation, timestamped executed-notebook runs, companion scripts for expensive steps, figure output, large-data handling, output management, or notebook review.
---

# Jupyter Workflow

Keep notebooks linear, fresh-kernel runnable, and composed of short, single-purpose cells. Put imports and configuration near the top. Use Markdown for intent, assumptions, and conclusions; prefer rich previews to verbose output.

## Work safely

- Never overwrite source data. Keep derived outputs in the project's results or scratch tree, not beside the source notebook.
- Keep the source notebook unexecuted in version control unless the project explicitly requires stored outputs.
- Executed copies are timestamped runs (see below): never edit them, never overwrite them, and keep them out of Git unless the project says otherwise.
- Seed randomness, address warnings, and make important parameters explicit in one top cell.

## Companion scripts for expensive work

Keep inexpensive exploration, visualization, diagnostics, and interpretation in the notebook. Move work into a neighboring script when it is expensive, must run unattended, needs tests or retries, or is reused elsewhere. Reusable within-project logic goes in a module. The notebook then orchestrates, inspects, and explains.

Write the script so a rerun is cheap and the notebook can trust its outputs:

- The docstring defines every output column or score and shows the CLI, so the notebook does not re-explain the method.
- Parameters are constants at the top; named stages (`knn`, `score`) can run separately.
- A `SMOKE=1` mode runs a small subsample end to end; use it before a full run.
- Stages cache intermediates and reuse them; write outputs atomically (temp file, then rename).
- Emit a `<name>.meta.json` beside the outputs: input paths, parameters, seed, sample counts, elapsed seconds, UTC timestamp, and a `smoke` flag.
- Pair it with an `sbatch` wrapper that states partition, GPUs, cores, memory, walltime, and log paths explicitly. Put the exact invocations (full, stage reuse, smoke, fallbacks) and the reason for the partition choice in its header comment. Use `set -euo pipefail` and log `free -g`. Do not run the script on a login node.

The notebook reads the artifacts and meta file only, does not recompute them, and opens with `assert not META["smoke"]`.

## Timestamped runs

Each execution gets its own directory under the project's results tree:

```
<results>/<run_key>/<YYYYmmddTHHMMSSZ>/
├── <name>.ipynb      # executed copy
├── figures/
└── run.meta.json
<results>/<run_key>/latest -> <stamp>
```

`run.meta.json` records the stamp, source notebook path and sha256, executed notebook sha256, git commit and dirty flag, hostname, SLURM job id, and figure count. Move `latest` only after execution succeeds.

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT=<results>/<run_key>/$STAMP; mkdir -p "$OUT"
jupyter nbconvert --execute --to notebook --output-dir "$OUT" --output <name>.ipynb <name>.ipynb
ln -sfn "$STAMP" <results>/<run_key>/latest
```

## Validate

Before finishing a meaningful notebook change, execute the notebook end to end in a fresh kernel. There is no interactive kernel to restart, so run it headlessly with the command above. On a shared cluster, submit anything beyond a trivial notebook with `sbatch` or `srun` rather than running it on a login node.

Add `--ExecutePreprocessor.timeout=-1` only when cells are legitimately long-running. Pass `--ExecutePreprocessor.kernel_name=<kernel>` when the notebook must run in a specific environment; if that kernel is unregistered, register it using the `conda-environments` skill rather than falling back to whichever kernel happens to be default.

Check that the executed copy has zero cells with `output_type == "error"`. Report whether fresh-kernel execution succeeded, give the run directory, and name the first failing cell if it did not.

## Large data and memory

- Open large files lazily or backed, and read only the columns, rows, or layers needed.
- Check free memory before heavy cells; on a cluster, wait for it rather than risk the node.
- For scattered random reads from a large file on a network filesystem, stage a copy onto node-local scratch first.
- `del` large objects and call `gc.collect()` between sections; prefer reading a precomputed artifact to recomputing it.

## Keep outputs small

- Cap printed rows and lines; show `.head()` or a summary, and write full tables to TSV files.
- Disable progress bars and verbose library logging.
- Rasterize dense scatter plots; avoid embedding many-point vector graphics or images over about 1 MB.
- An executed notebook that is tens of MB is a defect: fix the cell, not the viewer.

## Figures

- Apply one style cell near the top and define one canonical color mapping once.
- Save through a single `save_fig(fig, "NN_name")` helper that writes PNG and PDF into the run's `figures/`; number files to match section numbers.
- Put a Markdown cell before each figure stating the question and how to read it.

## Pair with a script when reviewing

`.ipynb` diffs are unreadable. When a notebook is under active review or frequent change, pair it with a `.py` percent-format file using jupytext and edit either side:

```bash
jupytext --set-formats ipynb,py:percent <name>.ipynb   # pair once
jupytext --sync <name>.ipynb                           # after editing either side
```

Commit the paired script when the project uses this workflow; it is what makes review possible.

## Review checklist

- Fresh-kernel run passes with zero error cells.
- Paths and parameters are in the top cell; seeds are set.
- No hidden state or out-of-order cells; no reliance on variables defined later.
- Smoke or partial artifacts are rejected, not silently consumed.
- Outputs are small; figures are saved in the run's `figures/`.
- `run.meta.json` is present and the paired `.py`, if any, is in sync.
