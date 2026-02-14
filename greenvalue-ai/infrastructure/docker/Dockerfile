# ============================================================
# GreenValue AI Engine - Production Dockerfile (Multi-Stage)
# ============================================================
# Layer 4: AI Intelligence & Ops (Port: 8000, gRPC: 50051)
# - YOLOv11 Instance Segmentation (Vision/U-Value Calc)
# - GPU Acceleration (CUDA 12.4 - RTX 5070 Ti & GTX 1650 Ti)
# - FastAPI + gRPC Server
# ============================================================

# --- Stage 1: Builder (Compile Dependencies) ---
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS builder

WORKDIR /build
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install Python 3.12 and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    build-essential \
    gcc \
    g++ \
    wget \
    curl \
    git \
    libffi-dev \
    libssl-dev \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Create virtual environment
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Install Python dependencies (Layer-cached)
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA 12.4 first (prevents CPU-only fallback)
RUN pip install torch==2.5.1 torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cu124

# Install remaining dependencies (exclude torch lines from requirements.txt)
RUN grep -v -E "^(torch|torchvision|--extra-index-url|--index-url)" requirements.txt > requirements_no_torch.txt && \
    pip install --no-cache-dir -r requirements_no_torch.txt

# Compile gRPC proto files if present
COPY protos/ ./protos/
RUN find ./protos -name '*.proto' -print -quit | grep -q . && \
    python -m grpc_tools.protoc \
      -I./protos \
      --python_out=./protos \
      --grpc_python_out=./protos \
      $(find ./protos -name '*.proto') \
    || echo 'No .proto files found, skipping gRPC compilation'

# --- Stage 2: Runtime (Minimal Production Image) ---
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS runtime

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime Python (no dev headers needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    libgomp1 \
    libgeos-c1v5 \
    libproj22 \
    libgdal30 \
    libgl1 \
    libglib2.0-0 \
    curl \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-tur \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy compiled proto stubs from builder
COPY --from=builder /build/protos/ ./protos/

# Copy application source code
COPY . .

# Create non-root user and directories
RUN groupadd -r greenvalue && \
    useradd -r -m -d /home/greenvalue -s /bin/bash -g greenvalue greenvalue && \
    # Application directories
    mkdir -p /app/data/models \
             /app/data/yolo_weights \
             /app/logs \
             /app/config \
             /app/temp \
    && \
    # MLflow & cache directories under safe home
    mkdir -p /home/greenvalue/.cache/matplotlib \
             /home/greenvalue/mlflow \
    && \
    # Set permissions
    chown -R greenvalue:greenvalue /opt/venv && \
    chown -R greenvalue:greenvalue /app && \
    chown -R greenvalue:greenvalue /home/greenvalue

# Switch to non-root user
USER greenvalue

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    HOME=/home/greenvalue \
    PATH="/opt/venv/bin:$PATH" \
    # CUDA Configuration
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    # YOLO Model Selection (m=Medium, l=Large, x=Extra Large)
    YOLO_MODEL_SIZE=m \
    # Matplotlib non-interactive backend (no GUI in Docker)
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/home/greenvalue/.cache/matplotlib

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports: API (8000), gRPC (50051), Prometheus Metrics (9090)
EXPOSE 8000 50051 9090

# Start FastAPI server via uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
