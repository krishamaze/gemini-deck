# Backend + Gemini CLI Dockerfile
FROM python:3.11-slim

# Install System Dependencies (Node.js, Xvfb, VNC)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    xvfb \
    x11vnc \
    fluxbox \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Gemini CLI
RUN npm install -g @google/gemini-cli

# Set Working Directory
WORKDIR /app

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Application Code
COPY . .

# Expose Ports
# 8000: FastAPI
# 5900: VNC
# 6080: Websockify (managed by start_display.sh)
EXPOSE 8000 5900 6080

# Environment Variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Start Script
# We need to ensure start_display.sh is executable
RUN chmod +x ../scripts/start_display.sh

# We use the run_backend.sh script (modified for Docker) or a new entrypoint
# Let's use a direct command to keep it simple within the container context
CMD ["/bin/bash", "-c", "../scripts/start_display.sh & uvicorn main:app --host 0.0.0.0 --port 8000"]
