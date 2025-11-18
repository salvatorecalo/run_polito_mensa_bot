FROM python:3.13-slim

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for the project
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    # PostgreSQL client and dev libraries
    postgresql-client \
    libpq-dev \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ita \
    # FFmpeg for moviepy
    ffmpeg \
    # Redis tools (for debugging)
    redis-tools \
    # Additional utilities
    sudo \
    vim \
    nano \
    htop \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set up Python environment
RUN pip install --upgrade pip setuptools wheel

# Install pre-commit globally for the dev environment
RUN pip install pre-commit

# Create workspace directories
RUN mkdir -p /workspace/stories /workspace/created_images /workspace/data \
    && chown -R $USERNAME:$USERNAME /workspace

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=dialog

# Set the default user
USER $USERNAME
WORKDIR /workspace

# Copy requirements and install Python dependencies
# (This will be done by devcontainer.json postCreateCommand)

# Keep container running
CMD ["sleep", "infinity"]