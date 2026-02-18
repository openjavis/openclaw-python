#!/bin/bash
set -euo pipefail

echo "--- Step 3: Connectivity Check ---"
MODEL_ENDPOINT="${MODEL_ENDPOINT:-open.bigmodel.cn}"
if timeout 5 bash -c "</dev/tcp/$MODEL_ENDPOINT/443"; then
    echo "Connection to $MODEL_ENDPOINT:443 succeeded."
else
    echo "Connection to $MODEL_ENDPOINT:443 failed."
    # Continue anyway: this can fail due to firewall/proxy while deployment still works.
fi

echo "--- Step 4: Install OpenClaw (Minimal) ---"
REPO_URL="${OPENCLAW_REPO_URL:-https://github.com/openxjarvis/openclaw-python.git}"
INSTALL_DIR="${OPENCLAW_INSTALL_DIR:-openclaw-python}"

if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists. Pulling latest from configured remote..."
    cd "$INSTALL_DIR"
    git pull --ff-only
else
    echo "Cloning $REPO_URL..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo "Setting up virtual environment (.venv)..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt not found; installing minimal deps."
    pip install requests aiohttp python-dotenv
fi

echo "OpenClaw install complete."
