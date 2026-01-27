# ClawdBot Python - Secure Docker Image
# Version: 0.3.0

FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 clawdbot && \
    mkdir -p /app /home/clawdbot/.clawdbot && \
    chown -R clawdbot:clawdbot /app /home/clawdbot

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY --chown=clawdbot:clawdbot pyproject.toml ./
COPY --chown=clawdbot:clawdbot README.md ./
COPY --chown=clawdbot:clawdbot LICENSE ./
COPY --chown=clawdbot:clawdbot clawdbot ./clawdbot/
COPY --chown=clawdbot:clawdbot skills ./skills/
COPY --chown=clawdbot:clawdbot extensions ./extensions/
COPY --chown=clawdbot:clawdbot tests ./tests/

# Switch to non-root user
USER clawdbot

# Install Python dependencies
ENV PATH="/home/clawdbot/.local/bin:${PATH}"
RUN pip install --no-cache-dir --user --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user fastapi uvicorn pydantic pydantic-settings \
    websockets typer rich anthropic openai python-telegram-bot discord.py slack-sdk \
    httpx aiofiles pyyaml pyjson5 python-dotenv aiosqlite

# Install optional dependencies for demo
RUN pip install --no-cache-dir --user \
    duckduckgo-search \
    playwright \
    apscheduler \
    psutil

# Expose ports (only what's needed)
# 18789: Gateway WebSocket
# 8080: Web UI (optional)
EXPOSE 18789 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "clawdbot.cli", "gateway", "start"]
