# multi-stage build.
#   builder  - installs deps into a venv
#   runtime  - carries the venv + source only
# for Jetson, build with --target jetson on the Jetson itself (uses a different
# base image with JetPack-bundled torch / TensorRT).

# ---- x86 dev image ----
FROM python:3.10-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git curl ffmpeg libgl1 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.10-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH=/workspace
WORKDIR /workspace
COPY . /workspace
EXPOSE 5005 8554 8080
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--config", "configs/inference.yaml"]

# ---- Jetson image ----
FROM nvcr.io/nvidia/l4t-jetpack:r36.2.0 AS jetson
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip ffmpeg libgl1 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt .
# on Jetson, torch / torchvision / TensorRT come from JetPack - strip them.
RUN sed -i '/^torch/d;/^torchvision/d;/^onnxruntime-gpu/d' requirements.txt \
    && pip3 install --no-cache-dir -r requirements.txt
COPY . /workspace
ENV PYTHONPATH=/workspace
EXPOSE 5005 8554 8080
ENTRYPOINT ["python3", "-m", "src.cli"]
CMD ["--config", "configs/inference_jetson.yaml"]
