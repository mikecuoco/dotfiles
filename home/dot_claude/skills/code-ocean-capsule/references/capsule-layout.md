# Capsule layout and code promotion

## Default structure

Organize analysis code by scientific arm rather than file type:

```text
/code
├── datasets.yaml
├── DATASETS.md
├── 01_preprocessing/
│   ├── 01_qc.ipynb
│   ├── preprocess.py
│   ├── config.yaml
│   └── utils.py
├── 02_genetics/
│   ├── 01_prepare_annotations.ipynb
│   ├── build_annotations.py
│   └── 02_results.ipynb
├── 03_pathology/
│   ├── 01_explore.ipynb
│   ├── fit_model.py
│   └── model.py
├── 04_integration/
│   └── 01_integrate.ipynb
├── project_package/          # only after cross-arm reuse appears
│   ├── pyproject.toml
│   └── src/project_package/
└── run                       # add or finish late
```

Adapt names to the science. Do not create placeholder arms, empty packages, or unused configuration files.

## Numbering policy

- Prefix every analysis arm with a stable two-digit number: `NN_name`.
- Choose dependency order or intended scientific reading order.
- Keep notebooks and other ordered artifacts numbered within an arm when that improves navigation.
- Preserve useful gaps when inserting an arm.
- Avoid renumbering established arms casually; paths can be embedded in notebooks, scripts, configs, and artifacts.
- Do not number root manifests, `run`, or shared project packages because they are not analysis arms.

## Promotion policy

Keep code at the lightest level that supports the work:

```text
one-off exploration
    → notebook cell

expensive, long-running, unattended, or repeatable operation
    → script beside the notebook

code reused within one arm
    → module or small package inside that arm

code reused across arms
    → shared package under /code

substantial independently reusable software
    → standalone Python library with package metadata and tests
```

Extract work from a notebook when accidental reruns are costly, it must run unattended, multiple notebooks need it, it needs stable parameters/logging/retries/tests, or downstream analysis should consume a saved artifact rather than hidden notebook state.

Keep inexpensive exploration, visualization, diagnostics, and post-run interpretation in notebooks. A neighboring script can write a costly intermediate to `/scratch`, and a notebook in the same arm can inspect it.

## Filesystem roles

| Location | Role |
|---|---|
| `/data` | Immutable attached or local primary inputs |
| `/scratch` | Temporary data, caches, environments, intermediates, checkpoints |
| `/results` | Final deliverables recreated by the reproducible workflow |
| `/code` | Notebooks, scripts, small configs, manifests, reusable source |
| `/environment` | Environment recipes and locks, never built environments |

An output belongs in `/results` because it is a final deliverable, not merely because it was expensive to compute.
