FROM python:3.12-slim

# Evita prompt interattivi e output bufferizzato
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/vscode/.local/bin:${PATH}"

# ----------------------------
# Dipendenze di sistema
# ----------------------------
RUN apt-get update && apt-get install -y \
    git curl build-essential libssl-dev libffi-dev python3-dev \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgl1 \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-ita \
    ffmpeg sudo vim tzdata \
    # Librerie necessarie per Playwright/Chromium
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libgtk-3-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Utente non-root
# ----------------------------
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# ----------------------------
# Workdir
# ----------------------------
WORKDIR /workspace
RUN mkdir -p /workspace/stories /workspace/created_images \
    && chown -R $USERNAME:$USERNAME /workspace

# ----------------------------
# Switch to non-root
# ----------------------------
USER $USERNAME

# ----------------------------
# Upgrade pip e installazione dependencies Python
# ----------------------------
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ----------------------------
# Installazione browser Chromium per Playwright
# ----------------------------
RUN python -m playwright install chromium

# ----------------------------
# Copia il codice del progetto
# ----------------------------
COPY . .

# ----------------------------
# Comando di default
# ----------------------------
CMD ["python", "main.py"]
