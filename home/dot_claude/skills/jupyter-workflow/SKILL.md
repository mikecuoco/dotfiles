---
name: jupyter-workflow
description: Create, edit, organize, execute, and review Jupyter notebooks with a linear, reproducible workflow. Use for .ipynb work, notebook refactoring, fresh-kernel validation, output management, or extracting reusable notebook logic into scripts or modules.
---

# Jupyter Workflow

Keep notebooks linear, fresh-kernel runnable, and composed of short, single-purpose cells. Put imports and configuration near the top. Use Markdown for intent, assumptions, and conclusions; prefer rich previews to verbose output.

## Work safely

- Never overwrite source data. Keep derived outputs separate.
- Keep the source notebook unexecuted in version control unless the project explicitly requires stored outputs.
- Save an executed copy as `<name>.out.ipynb`; regenerate it after source changes and never edit it directly.
- Keep executed copies out of Git unless the project explicitly says otherwise.
- Seed randomness, address warnings, and make important parameters explicit.

## Promote reusable work

Keep inexpensive exploration, visualization, diagnostics, and interpretation in the notebook. Extract logic when it is expensive, must run unattended, needs tests or retries, or is reused elsewhere:

1. Move repeatable work into a neighboring script.
2. Move within-project reusable logic into a module or package.
3. Keep the notebook focused on orchestration, inspection, and explanation.

## Pair with a script when reviewing

`.ipynb` diffs are unreadable. When a notebook is under active review or frequent change, pair it with a `.py` percent-format file using jupytext and edit either side:

```bash
jupytext --set-formats ipynb,py:percent <name>.ipynb   # pair once
jupytext --sync <name>.ipynb                           # after editing either side
```

Commit the paired script when the project uses this workflow; it is what makes review possible.

## Validate

Before finishing a meaningful notebook change, execute the notebook end to end in a fresh kernel. There is no interactive kernel to restart, so run it headlessly:

```bash
jupyter nbconvert --execute --to notebook --output <name>.out.ipynb <name>.ipynb
```

Add `--ExecutePreprocessor.timeout=-1` only when cells are legitimately long-running. Pass `--ExecutePreprocessor.kernel_name=<kernel>` when the notebook must run in a specific environment; if that kernel is unregistered, register it using the `conda-environments` skill rather than falling back to whichever kernel happens to be default.

Write results only to the `.out.ipynb` copy. Report whether fresh-kernel execution succeeded, and name the first failing cell if it did not.
