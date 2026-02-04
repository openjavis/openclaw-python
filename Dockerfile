# OpenClaw Python - Production Docker Image
# Optimized for macOS 12.7.6 (Monterey) + Intel x86_64

FROM python:3.12-slim

LABEL maintainer="OpenClaw"
LABEL version="0.6.0"
LABEL description="OpenClaw AI Assistant Platform"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user
RUN useradd -m -u 1000 openclaw && \
    mkdir -p /app /home/openclaw/.openclaw && \
    chown -R openclaw:openclaw /app /home/openclaw

WORKDIR /app

# Copy dependency files first (for better Docker layer caching)
COPY --chown=openclaw:openclaw pyproject.toml README.md ./

# Switch to non-root user
USER openclaw

# Install Python dependencies using uv
RUN uv venv && \
    uv pip install --no-cache-dir -e .

# Copy application code
COPY --chown=openclaw:openclaw openclaw ./openclaw/
COPY --chown=openclaw:openclaw skills ./skills/
COPY --chown=openclaw:openclaw extensions ./extensions/
COPY --chown=openclaw:openclaw examples ./examples/
COPY --chown=openclaw:openclaw start_full_featured.py ./

# Create workspace directory
RUN mkdir -p /app/workspace

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    VIRTUAL_ENV="/app/.venv" \
    PYTHONUNBUFFERED=1

# Expose ports
# 8765: Gateway WebSocket API
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import openclaw; print('OK')" || exit 1

# Default command - run full-featured server
CMD ["python", "start_full_featured.py"]
