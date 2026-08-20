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

## Validate

Before finishing a meaningful notebook change, restart the kernel and run all cells in order. Save results only to the `.out.ipynb` copy and report whether fresh-kernel execution succeeded.
