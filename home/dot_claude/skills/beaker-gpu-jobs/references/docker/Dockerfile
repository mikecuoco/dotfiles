# Shared Beaker GPU base: CUDA + PyTorch from the official image, plus
# micromamba. No conda packages are installed here: each job runs
# `project-env` to build its project env when it starts (see SKILL.md,
# "Project env"). Build from this directory on a Mac (../image-build.md):
#   docker buildx build --platform linux/amd64 --load --tag torch-base:<n> .
#
# The base image sets PYTORCH_VERSION and the NVIDIA env vars and has no
# ENTRYPOINT. Since 2.10 its torch is pip-installed for the system Python
# (/usr/bin/python3) into /usr/local/lib/python3.*/dist-packages; project-env
# makes that torch visible inside the conda env.
ARG TORCH_TAG=2.14.1-cuda12.6-cudnn9-runtime
FROM pytorch/pytorch:${TORCH_TAG}

COPY --from=mambaorg/micromamba:2.9.0-debian13 /bin/micromamba /usr/local/bin/micromamba
COPY condarc /etc/conda/.condarc
COPY --chmod=755 project-env /usr/local/bin/project-env

ENV MAMBA_ROOT_PREFIX=/opt/micromamba
# The project env, once project-env has built it, comes first.
ENV PATH=/opt/env/bin:${PATH}
WORKDIR /code
CMD ["/bin/bash"]
