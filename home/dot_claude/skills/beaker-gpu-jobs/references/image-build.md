# Building the base image

One image serves every project: CUDA and PyTorch from the official `pytorch/pytorch` image, plus micromamba and the `project-env` script. No conda packages are installed at build time; each job builds its project env when it starts (SKILL.md, "Project env"). Build and upload on a Mac with Docker Desktop (the HPC has no Docker), and rebuild only to bump PyTorch, CUDA, or micromamba.

## Files

- [docker/Dockerfile](docker/Dockerfile): `FROM pytorch/pytorch:${TORCH_TAG}`, copies in the static micromamba binary, the channel config, and `project-env`; puts `/opt/env/bin` first on `PATH`.
- [docker/project-env](docker/project-env): creates `/opt/env` with the image's Python version, links the image's site-packages in through a `.pth` file, then installs the env file.
- [docker/condarc](docker/condarc): installed as `/etc/conda/.condarc`; conda-forge then bioconda, strict priority.

Copy all three into an empty build directory so the build context holds nothing else. Never add tokens, AWS credentials, SSH keys, or `.env` files.

## Choosing `TORCH_TAG`

- Use a `-runtime` tag, not `-devel`, unless a project compiles CUDA extensions.
- Since 2.10 the official images have no `/opt/conda`; torch is pip-installed for the system `/usr/bin/python3` into `/usr/local/lib/python3.*/dist-packages`. `project-env` depends on that layout: after changing tags, run the `docker run` check below and one `project-env` in a session.
- The CUDA version must be supported by the node driver. CUDA 12.x builds run on drivers >= 525; CUDA 13 builds need >= 580. On 2026-10-04, `ai1/octo-hub-aws-h200` and `ai1/aipbd-aws-h200` both reported driver 580.105.08 (CUDA 13.0). Re-check with `nvidia-smi` on every cluster a job may land on before moving to a CUDA 13 tag.
- Override without editing the file: `--build-arg TORCH_TAG=<tag>`.

## Build and upload

```bash
docker desktop start && docker info          # Server section must be populated
docker buildx build --builder desktop-linux --platform linux/amd64 --load --tag torch-base:<n> .
docker run --rm --platform linux/amd64 torch-base:<n> bash -c 'micromamba --version; python3 -c "import torch; print(torch.__version__, torch.version.cuda)"'
# Optional: an env file with one conda and one pip: package, mounted read-only as on Beaker.
docker run --rm --platform linux/amd64 -v <test-dir>:/code:ro torch-base:<n> project-env
DOCKER_HOST="unix://$HOME/.docker/run/docker.sock" \
  beaker image create --workspace <workspace> --name torch-base-<torch>-cu<xx>-v<n> torch-base:<n>
beaker image get <user>/torch-base-<torch>-cu<xx>-v<n>
```

- `--platform linux/amd64`: Apple Silicon builds ARM by default; Beaker nodes are x86.
- `--builder desktop-linux`: Docker Desktop's built-in builder loads straight into the local image store; a `docker-container` builder (check `docker buildx ls`) has to export and copy the image.
- `--load`: puts the buildx result in the local image store where `beaker image create` reads it.
- The image is about 11 GB locally and 4 GB compressed; the upload takes a few minutes.
- `DOCKER_HOST`: `beaker` looks for `/var/run/docker.sock`; Docker Desktop's socket is under `~/.docker/run/`.
- Bump the version suffix for every upload and record the new reference with the project's Beaker values.

## Project-specific image (fallback)

Installing the env at job start costs a download per task. If a project runs many short tasks, or its env takes minutes to solve, bake it into an image built on the base:

```dockerfile
FROM <base image tag>
COPY env/environment.yml /tmp/environment.yml
RUN project-env /tmp/environment.yml && micromamba clean --all --yes
```

Then drop `project-env` from the spec. This is the exception; prefer the shared base.

## Errors

| Symptom | Fix |
|---|---|
| `Cannot connect to ... docker.sock` | Start Docker Desktop and set `DOCKER_HOST` as above. |
| Socket missing although Desktop "running" | `docker desktop restart`, then `docker info`. |
| ARM image rejected / `exec format error` | Rebuild with `--platform linux/amd64 --load`. |
| `CUDA driver version is insufficient` | `TORCH_TAG` CUDA is newer than the node driver; pick an older CUDA tag. |
