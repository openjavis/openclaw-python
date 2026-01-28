# ClawdBot Python - Production Docker Image
# Version: 0.4.0

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (as root, before switching users)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user
RUN useradd -m -u 1000 clawdbot && \
    mkdir -p /app /home/clawdbot/.clawdbot && \
    chown -R clawdbot:clawdbot /app /home/clawdbot

WORKDIR /app

# Copy dependency files first (for better caching)
COPY --chown=clawdbot:clawdbot pyproject.toml uv.lock* README.md LICENSE ./

# Switch to non-root user
USER clawdbot

# Install dependencies using uv
# Use --no-cache to avoid cache issues in Docker
RUN uv venv && \
    uv sync --no-cache --no-dev

# Copy application code
COPY --chown=clawdbot:clawdbot clawdbot ./clawdbot/
COPY --chown=clawdbot:clawdbot skills ./skills/
COPY --chown=clawdbot:clawdbot extensions ./extensions/

# Set PATH to use venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    VIRTUAL_ENV="/app/.venv"

# Expose ports
# 18789: Gateway WebSocket
# 8080: Web UI (optional)
EXPOSE 18789 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import clawdbot; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "clawdbot.cli", "gateway", "start"]
