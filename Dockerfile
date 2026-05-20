FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Dipendenze di sistema (Tesseract + Playwright)
RUN apt-get update && apt-get install -y \
    git curl build-essential libssl-dev libffi-dev python3-dev \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgl1 \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-ita \
    ffmpeg sudo vim tzdata dotenv \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libgtk-3-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configurazione utente vscode
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Variabili d'ambiente per forzare pip nella cartella corretta di vscode
ENV PATH="/home/vscode/.local/bin:${PATH}"
ENV PIP_USER=true
ENV PIP_NO_CACHE_DIR=1

# Creazione cartelle con i permessi corretti per lo sviluppo e per il server
RUN mkdir -p /workspace/data /workspace/download/stories \
    && chown -R $USERNAME:$USERNAME /workspace

WORKDIR /workspace
USER $USERNAME

# Installazione pacchetti Python
COPY --chown=$USERNAME:$USERNAME requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --user -r requirements.txt

# Installazione browser Chromium per Playwright
RUN python -m playwright install chromium

# Copia il resto del codice
COPY --chown=$USERNAME:$USERNAME . .

CMD ["python", "main.py"]
