# Environments and scratch storage

The root filesystem is only about 5 GB and fills especially quickly on GPU machines. Every temporary file, cache, build product, downloaded model, environment, and interactive installation must resolve beneath `/scratch`.

## Runtime layout

```text
/scratch
└── .dotfiles/
    ├── tmp/
    ├── build/
    ├── cache/
    │   ├── conda-pkgs/
    │   ├── pip/
    │   ├── uv/
    │   ├── huggingface/
    │   ├── torch/
    │   ├── cuda/
    │   ├── triton/
    │   └── jax/
    ├── envs/
    │   ├── conda/
    │   ├── venvs/
    │   └── uv-tools/
    ├── python-user/
    ├── R/library/
    └── runtime/
```

At runtime, group tool-managed storage beneath `/scratch/.dotfiles/` and create `TMPDIR` before exporting it; tools can create their other directories on first use. Redirect at least `TMPDIR`, `TMP`, `TEMP`, `XDG_CACHE_HOME`, `CONDA_PKGS_DIRS`, `CONDA_ENVS_PATH`, `MAMBA_ROOT_PREFIX`, `PIP_CACHE_DIR`, and `UV_CACHE_DIR`. When applicable, also redirect Hugging Face, PyTorch, CUDA, Triton, JAX, Numba, CuPy, Keras, Matplotlib, Jupyter, IPython, R, npm, Rust, and Go caches or installation roots. Disable core dumps with `ulimit -c 0` when possible.

Never rely on `/tmp`, `~/.cache`, `~/.conda`, `~/.local`, a root-backed `.venv`, or a tool's implicit default. Before installing packages, compiling extensions, downloading models, or running GPU kernels, verify the destination, temp directory, build directory, and cache location explicitly.

Do not set `/scratch` paths as unconditional Dockerfile `ENV` values. `/scratch` is a runtime mount and may not exist while Code Ocean constructs the image. Set them in a runtime shell profile or in `run` after confirming the mount exists.

## Conda lifecycle

Store recipes and, only when explicitly requested, locks—not installed environments—under `/environment`:

```text
/environment
├── environment.yml       # human-edited direct constraints and channels
├── conda-lock.yml        # generated; do not hand-edit
├── Dockerfile            # Code Ocean environment recipe
└── postInstall           # only for necessary build-time additions
```

1. During exploration, update `environment.yml` as direct dependencies emerge.
2. Avoid exporting every transitive dependency from a mutable environment.
3. Solve and test with the actual environment under `/scratch/.dotfiles/envs/conda/<name>` and package/solver caches under `/scratch/.dotfiles/cache`.
4. When locking is requested, generate it for the capsule's actual platform, normally `linux-64`.
5. Commit `environment.yml` and the requested `conda-lock.yml`; regenerate the lock whenever channels or constraints change.
6. Recreate the finalized environment under `/scratch` from the lock when absent and verify the bootstrap procedure with clean scratch storage when finalization is requested.

Inspect the installed `conda-lock` version before selecting exact CLI flags. A macOS or different-architecture lock is not a Code Ocean Linux lock. Do not mix ad hoc `pip install` operations into a supposedly locked environment. For channel order, solver choice, and pinning, use the `conda-environments` skill.

`/environment` is not visible during a Reproducible Run. Ensure the runtime can reach the lock or an equivalent deterministic bootstrap artifact without relying on leftover workstation state. Persistence of `/scratch` is convenient, not reproducibility.

Use `postInstall` only for steps that truly belong during image construction. It cannot depend on runtime `/data`, `/code`, or `/scratch` content.
